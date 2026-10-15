//+------------------------------------------------------------------+
//| BinanceLAB093_DataFeeder_VPS_EA_v1.08.mq5                      |
//| VPS EA: Binance OI + 1m/5m klines + L/S ratio (5m).              |
//| NO TRADING. Writes FILE_COMMON snapshots only.                   |
//|                                                                  |
//| v1.08 changes (data logic unchanged):                            |
//| - atomic file writes: write *.tmp, then FileMove over target     |
//|   (readers never see a truncated/half-written snapshot)          |
//| - duplicate lock no longer fails init: EA waits and retries the  |
//|   lock every cycle; reason shown on panel + journal (once)       |
//| - heartbeat inside backfill loops; lock stale = max(90s,4xrefresh)|
//| - defaults: refresh 15 s, HTTP timeout 4000 ms                   |
//| - panel: last OK time per dataset (OI/M1/M5/LS) + HTTP fails     |
//|                                                                  |
//| v1.07 changes:                                                   |
//| - + globalLongShortAccountRatio 5m -> Common\Files\BinanceLS\   |
//|   SYM_5m.csv ("ts_seconds,ratio") for BinanceLSZ indicator.      |
//|   Replaces BinanceLS_Feeder service (services do not run on      |
//|   MQL5 VPS). Do NOT run that service together with this EA.      |
//| - L/S is independent: its failure never blocks OI/M1/M5 and     |
//|   never changes g_historyReady.                                  |
//| - OI/M1/M5 logic unchanged from v1.06.                           |
//|                                                                  |
//| v1.05 changes:                                                   |
//| - one full backfill on startup, then only latest-500 refreshes   |
//| - 3 HTTP retries with backoff                                    |
//| - NEVER truncates a good snapshot after failed HTTP              |
//| - merges/deduplicates/prunes history in memory before rewrite    |
//| - default history 240h, refresh 60s, timeout 8000ms              |
//| - duplicate-instance heartbeat lock                              |
//| - VPS-compatible EA lifecycle: OnInit/OnTimer/OnDeinit           |
//+------------------------------------------------------------------+
#property strict
#property version   "1.080"
#property description "VPS feeder EA: Binance OI + 1m/5m klines + L/S ratio 5m to FILE_COMMON. No trading."

input string InpBinanceSymbol = "BTCUSDT";
input int    InpRefreshSec    = 15;
input int    InpWebTimeoutMs  = 4000;
input int    InpHttpRetries   = 3;
input bool   InpVerbose       = false;
input int    InpHistoryHours  = 240;    // LAB157 needs ~200h+ for causal H4 EMA50 context
input bool   InpFeedLS        = true;   // v1.07: also write L/S ratio for BinanceLSZ
input string InpLSFolder      = "BinanceLS"; // FILE_COMMON folder read by BinanceLSZ
input int    InpLSHistoryHours= 240;    // L/S history kept (Binance serves max ~30 days)

#define API                     "https://fapi.binance.com"
#define KLINE_PATH              "/fapi/v1/klines"
#define OPEN_INTEREST_HIST_PATH "/futures/data/openInterestHist"
#define LS_RATIO_PATH           "/futures/data/globalLongShortAccountRatio"

struct OIRow
{
   long   ts;
   double oi;
};

struct KRow
{
   long   ts;
   double o,h,l,c;
};

struct LSRow
{
   long   ts;      // milliseconds in memory; SECONDS in file (BinanceLSZ format)
   double r;
};

string g_lockKey="";
int    g_httpFails=0;                 // failed HTTP attempts since start
datetime g_okOI=0,g_okM1=0,g_okM5=0,g_okLS=0;   // last successful write per dataset (GMT)
bool   g_waitLock=false;
double g_lockAge=0;
bool   g_lockOwned=false;

//---------------- HTTP -----------------------------------------------
bool HttpGetOnce(const string url,string &body,int &httpCode,int &errCode)
{
   char data[],res[];
   string hdr="";
   body="";
   ResetLastError();
   httpCode=WebRequest("GET",url,"",InpWebTimeoutMs,data,res,hdr);
   errCode=GetLastError();

   if(httpCode!=200)
      return false;

   body=CharArrayToString(res,0,WHOLE_ARRAY,CP_UTF8);
   return StringLen(body)>10;
}

bool HttpGet(const string url,string &body)
{
   int attempts=MathMax(1,InpHttpRetries);
   for(int a=1;a<=attempts && !IsStopped();a++)
   {
      int code=0,err=0;
      if(HttpGetOnce(url,body,code,err))
         return true;

      g_httpFails++;
      PrintFormat("LAB093_FEED HTTP FAIL attempt=%d/%d code=%d err=%d url=%s",
                  a,attempts,code,err,url);

      if(a<attempts)
         Sleep(750*a); // 0.75s, 1.5s, ...
   }
   return false;
}

//---------------- JSON helpers --------------------------------------
double JsonNum(const string s,const int p,const string key,int &endp)
{
   int k=StringFind(s,"\""+key+"\"",p);
   if(k<0){endp=-1;return 0.0;}

   int c=StringFind(s,":",k);
   if(c<0){endp=-1;return 0.0;}

   int i=c+1,n=StringLen(s);
   while(i<n && (StringGetCharacter(s,i)==' ' || StringGetCharacter(s,i)=='\"')) i++;

   int j=i;
   while(j<n)
   {
      ushort ch=StringGetCharacter(s,j);
      if((ch>='0'&&ch<='9')||ch=='-'||ch=='+'||ch=='.'||ch=='e'||ch=='E')
         j++;
      else
         break;
   }

   endp=j;
   return StringToDouble(StringSubstr(s,i,j-i));
}

string SafeSymbol()
{
   string s=InpBinanceSymbol;
   StringTrimLeft(s);
   StringTrimRight(s);
   StringToUpper(s);
   return s;
}

string BaseFolder()
{
   return "BinanceLAB093\\";
}

string OIPath()
{
   return BaseFolder()+SafeSymbol()+"_oi_5m.csv";
}

string KlinePath(const string interval)
{
   return BaseFolder()+SafeSymbol()+"_"+interval+".csv";
}

string LSPath()
{
   string f=InpLSFolder;
   StringTrimLeft(f);
   StringTrimRight(f);
   if(StringLen(f)==0) f="BinanceLS";
   return f+"\\"+SafeSymbol()+"_5m.csv";
}

int LSHistoryHours()
{
   int h=InpLSHistoryHours;
   if(h<24)  h=24;
   if(h>720) h=720;
   return h;
}

//---------------- Duplicate-service lock -----------------------------
bool AcquireLock()
{
   g_lockKey="LAB093_FEED_LOCK_"+SafeSymbol();
   double now=(double)TimeLocal();
   double staleAfter=(double)MathMax(90,InpRefreshSec*4);

   if(GlobalVariableCheck(g_lockKey))
   {
      double last=GlobalVariableGet(g_lockKey);
      if(last>0 && now-last<staleAfter)
      {
         g_lockAge=now-last;
         if(!g_waitLock)
            PrintFormat("LAB093_FEED another feeder holds the lock (heartbeat age=%.0fs, key=%s). Waiting; will take over when it is older than %.0fs. If no other feeder runs, delete this global variable (F3).",
                        g_lockAge,g_lockKey,staleAfter);
         return false;
      }
   }

   GlobalVariableSet(g_lockKey,now);
   g_lockOwned=true;
   return true;
}

void Heartbeat()
{
   if(g_lockOwned && StringLen(g_lockKey)>0)
      GlobalVariableSet(g_lockKey,(double)TimeLocal());
}

void ReleaseLock()
{
   if(g_lockOwned && StringLen(g_lockKey)>0)
      GlobalVariableDel(g_lockKey);
   g_lockOwned=false;
}

//---------------- Sort / merge --------------------------------------
void SortOI(OIRow &a[])
{
   int n=ArraySize(a);
   for(int i=1;i<n;i++)
   {
      OIRow key=a[i];
      int j=i-1;
      while(j>=0 && a[j].ts>key.ts)
      {
         a[j+1]=a[j];
         j--;
      }
      a[j+1]=key;
   }
}

void SortK(KRow &a[])
{
   int n=ArraySize(a);
   for(int i=1;i<n;i++)
   {
      KRow key=a[i];
      int j=i-1;
      while(j>=0 && a[j].ts>key.ts)
      {
         a[j+1]=a[j];
         j--;
      }
      a[j+1]=key;
   }
}

void UpsertOI(OIRow &dst[],const OIRow &row)
{
   int n=ArraySize(dst);
   for(int i=n-1;i>=0;i--)
   {
      if(dst[i].ts==row.ts)
      {
         dst[i]=row;
         return;
      }
      if(dst[i].ts<row.ts)
         break;
   }
   ArrayResize(dst,n+1);
   dst[n]=row;
}

void UpsertK(KRow &dst[],const KRow &row)
{
   int n=ArraySize(dst);
   for(int i=n-1;i>=0;i--)
   {
      if(dst[i].ts==row.ts)
      {
         dst[i]=row;
         return;
      }
      if(dst[i].ts<row.ts)
         break;
   }
   ArrayResize(dst,n+1);
   dst[n]=row;
}

void PruneOI(OIRow &a[],const long cutoff)
{
   SortOI(a);
   int n=ArraySize(a),start=0;
   while(start<n && a[start].ts<cutoff) start++;
   if(start<=0) return;

   int keep=n-start;
   for(int i=0;i<keep;i++) a[i]=a[start+i];
   ArrayResize(a,keep);
}

void PruneK(KRow &a[],const long cutoff)
{
   SortK(a);
   int n=ArraySize(a),start=0;
   while(start<n && a[start].ts<cutoff) start++;
   if(start<=0) return;

   int keep=n-start;
   for(int i=0;i<keep;i++) a[i]=a[start+i];
   ArrayResize(a,keep);
}

//---------------- Existing snapshots --------------------------------
bool ReadOIFile(OIRow &rows[])
{
   ArrayResize(rows,0);
   int h=FileOpen(OIPath(),FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE)
      return false;

   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      if(StringLen(line)<3) continue;

      string f[];
      if(StringSplit(line,',',f)<2) continue;

      OIRow r;
      r.ts=(long)StringToInteger(f[0]);
      r.oi=StringToDouble(f[1]);
      if(r.ts<=0 || r.oi<=0) continue;

      int n=ArraySize(rows);
      ArrayResize(rows,n+1);
      rows[n]=r;
   }
   FileClose(h);
   SortOI(rows);
   return ArraySize(rows)>0;
}

bool ReadKFile(const string interval,KRow &rows[])
{
   ArrayResize(rows,0);
   int h=FileOpen(KlinePath(interval),FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE)
      return false;

   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      if(StringLen(line)<3) continue;

      string f[];
      if(StringSplit(line,',',f)<5) continue;

      KRow r;
      r.ts=(long)StringToInteger(f[0]);
      r.o =StringToDouble(f[1]);
      r.h =StringToDouble(f[2]);
      r.l =StringToDouble(f[3]);
      r.c =StringToDouble(f[4]);

      if(r.ts<=0 || r.o<=0 || r.h<=0 || r.l<=0 || r.c<=0) continue;

      int n=ArraySize(rows);
      ArrayResize(rows,n+1);
      rows[n]=r;
   }
   FileClose(h);
   SortK(rows);
   return ArraySize(rows)>0;
}

//---------------- Parse Binance responses ----------------------------
bool ParseOIResponse(const string body,OIRow &rows[])
{
   ArrayResize(rows,0);
   int p=0;

   while(true)
   {
      int k=StringFind(body,"\"sumOpenInterest\"",p);
      if(k<0) break;

      int e=-1,et=-1;
      double oi=JsonNum(body,k,"sumOpenInterest",e);
      double td=JsonNum(body,k,"timestamp",et);
      if(e<0 || et<0) break;

      OIRow r;
      r.ts=(long)td;
      r.oi=oi;

      if(r.ts>0 && r.oi>0)
      {
         int n=ArraySize(rows);
         ArrayResize(rows,n+1);
         rows[n]=r;
      }

      p=MathMax(e,et);
   }

   SortOI(rows);
   return ArraySize(rows)>0;
}

bool ParseKlineResponse(const string body,KRow &rows[])
{
   ArrayResize(rows,0);

   int p=0,n=StringLen(body);
   while(true)
   {
      int a=StringFind(body,"[",p);
      if(a<0) break;

      int b=StringFind(body,"]",a);
      if(b<0) break;

      string row=StringSubstr(body,a+1,b-a-1);
      if(StringFind(row,",")>=0)
      {
         string q=row;
         StringReplace(q,"\"","");
         string f[];
         int k=StringSplit(q,',',f);

         if(k>=5)
         {
            KRow r;
            r.ts=(long)StringToInteger(f[0]);
            r.o=StringToDouble(f[1]);
            r.h=StringToDouble(f[2]);
            r.l=StringToDouble(f[3]);
            r.c=StringToDouble(f[4]);

            if(r.ts>0 && r.o>0 && r.h>0 && r.l>0 && r.c>0)
            {
               int z=ArraySize(rows);
               ArrayResize(rows,z+1);
               rows[z]=r;
            }
         }
      }

      p=b+1;
      if(p>=n) break;
   }

   SortK(rows);
   return ArraySize(rows)>0;
}

//---------------- Safe writes ----------------------------------------
// IMPORTANT: final snapshot is opened ONLY after all HTTP calls for that
// dataset completed successfully. A failed HTTP request leaves the old
// snapshot intact.

//---------------- Atomic write helpers (v1.08) -----------------------
int OpenTmp(const string path)
{
   int h=FileOpen(path+".tmp",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h==INVALID_HANDLE)
      PrintFormat("LAB093_FEED cannot write %s.tmp err=%d",path,GetLastError());
   return h;
}

bool CommitTmp(const string path)
{
   string tmp=path+".tmp";
   for(int a=0;a<3;a++)
   {
      ResetLastError();
      if(FileMove(tmp,FILE_COMMON,path,FILE_COMMON|FILE_REWRITE)) return true;
      Sleep(100);                       // a reader may hold the target for a moment
   }
   // Fallback: copy over the target, then remove tmp.
   bool ok=FileCopy(tmp,FILE_COMMON,path,FILE_COMMON|FILE_REWRITE);
   if(!ok) PrintFormat("LAB093_FEED commit failed %s err=%d (old snapshot kept)",path,GetLastError());
   FileDelete(tmp,FILE_COMMON);
   return ok;
}

bool SaveOI(const OIRow &rows[])
{
   if(ArraySize(rows)<4)
      return false;

   int h=OpenTmp(OIPath());
   if(h==INVALID_HANDLE)
      return false;

   for(int i=0;i<ArraySize(rows);i++)
      FileWriteString(h,StringFormat("%I64d,%.10f\r\n",rows[i].ts,rows[i].oi));

   FileFlush(h);
   FileClose(h);
   if(!CommitTmp(OIPath())) return false;
   g_okOI=TimeGMT();
   return true;
}

bool SaveK(const string interval,const KRow &rows[])
{
   if(ArraySize(rows)<4)
      return false;

   string path=KlinePath(interval);
   int h=OpenTmp(path);
   if(h==INVALID_HANDLE)
      return false;

   for(int i=0;i<ArraySize(rows);i++)
      FileWriteString(h,StringFormat("%I64d,%.10f,%.10f,%.10f,%.10f\r\n",
                                    rows[i].ts,rows[i].o,rows[i].h,rows[i].l,rows[i].c));

   FileFlush(h);
   FileClose(h);
   if(!CommitTmp(path)) return false;
   if(interval=="1m") g_okM1=TimeGMT();
   if(interval=="5m") g_okM5=TimeGMT();
   return true;
}

//---------------- L/S ratio (v1.07) ----------------------------------
void SortLS(LSRow &a[])
{
   int n=ArraySize(a);
   for(int i=1;i<n;i++)
   {
      LSRow key=a[i];
      int j=i-1;
      while(j>=0 && a[j].ts>key.ts)
      {
         a[j+1]=a[j];
         j--;
      }
      a[j+1]=key;
   }
}

void UpsertLS(LSRow &dst[],const LSRow &row)
{
   int n=ArraySize(dst);
   for(int i=n-1;i>=0;i--)
   {
      if(dst[i].ts==row.ts)
      {
         dst[i]=row;
         return;
      }
      if(dst[i].ts<row.ts)
         break;
   }
   ArrayResize(dst,n+1);
   dst[n]=row;
}

void PruneLS(LSRow &a[],const long cutoff)
{
   SortLS(a);
   int n=ArraySize(a),start=0;
   while(start<n && a[start].ts<cutoff) start++;
   if(start<=0) return;

   int keep=n-start;
   for(int i=0;i<keep;i++) a[i]=a[start+i];
   ArrayResize(a,keep);
}

bool ReadLSFile(LSRow &rows[])
{
   ArrayResize(rows,0);
   int h=FileOpen(LSPath(),FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE)
      return false;

   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      StringTrimRight(line);
      if(StringLen(line)<3) continue;

      string f[];
      if(StringSplit(line,',',f)<2) continue;

      LSRow r;
      r.ts=(long)StringToInteger(f[0]);
      r.r =StringToDouble(f[1]);
      if(r.ts<=0 || r.r<=0) continue;

      // File format is seconds. Tolerate a legacy millisecond file.
      if(r.ts<100000000000)
         r.ts*=1000;

      int n=ArraySize(rows);
      ArrayResize(rows,n+1);
      rows[n]=r;
   }
   FileClose(h);
   SortLS(rows);
   return ArraySize(rows)>0;
}

bool ParseLSResponse(const string body,LSRow &rows[])
{
   ArrayResize(rows,0);
   int p=0;

   while(true)
   {
      int k=StringFind(body,"\"longShortRatio\"",p);
      if(k<0) break;

      int e=-1,et=-1;
      double x =JsonNum(body,k,"longShortRatio",e);
      double td=JsonNum(body,k,"timestamp",et);
      if(e<0 || et<0) break;

      LSRow r;
      r.ts=(long)td;
      r.r =x;

      if(r.ts>0 && r.r>0)
      {
         int n=ArraySize(rows);
         ArrayResize(rows,n+1);
         rows[n]=r;
      }

      p=MathMax(e,et);
   }

   SortLS(rows);
   return ArraySize(rows)>0;
}

bool SaveLS(const LSRow &rows[])
{
   if(ArraySize(rows)<4)
      return false;

   int h=OpenTmp(LSPath());
   if(h==INVALID_HANDLE)
      return false;

   // BinanceLSZ expects "timestamp_seconds,ratio".
   for(int i=0;i<ArraySize(rows);i++)
      FileWriteString(h,StringFormat("%I64d,%.6f\r\n",rows[i].ts/1000,rows[i].r));

   FileFlush(h);
   FileClose(h);
   if(!CommitTmp(LSPath())) return false;
   g_okLS=TimeGMT();
   return true;
}

bool LSHistoryEnough()
{
   LSRow ls[];
   if(!ReadLSFile(ls) || ArraySize(ls)<2)
      return false;

   long nowMs=(long)TimeGMT()*1000;
   long span=ls[ArraySize(ls)-1].ts-ls[0].ts;
   long required=(long)LSHistoryHours()*3600000;
   long age=nowMs-ls[ArraySize(ls)-1].ts;

   // Need the requested span AND no gap longer than one 500-row refresh (~41h).
   return span >= (long)(required*0.95) && age < 40*3600000;
}

bool BackfillLS()
{
   long nowMs=(long)TimeGMT()*1000;
   long cutoff=nowMs-(long)LSHistoryHours()*3600000;

   LSRow all[];
   ReadLSFile(all);               // keep any good existing rows

   long cursor=cutoff;
   while(cursor<nowMs && !IsStopped())
   {
      string url=API+LS_RATIO_PATH+
                 "?symbol="+SafeSymbol()+
                 "&period=5m&limit=500&startTime="+StringFormat("%I64d",cursor);

      string body;
      if(!HttpGet(url,body))
         return false;            // existing file untouched

      LSRow page[];
      if(!ParseLSResponse(body,page))
         break;

      long lastTs=0;
      for(int i=0;i<ArraySize(page);i++)
      {
         if(page[i].ts>=cutoff && page[i].ts<=nowMs)
         {
            UpsertLS(all,page[i]);
            lastTs=MathMax(lastTs,page[i].ts);
         }
      }

      if(lastTs<=cursor)
         break;

      cursor=lastTs+300000;
      if(ArraySize(page)<500)
         break;

      Heartbeat();
   }

   PruneLS(all,cutoff);
   if(ArraySize(all)<4)
      return false;

   return SaveLS(all);
}

bool RefreshLSLatest()
{
   string body;
   string url=API+LS_RATIO_PATH+
              "?symbol="+SafeSymbol()+"&period=5m&limit=500";

   if(!HttpGet(url,body))
      return false;

   LSRow latest[];
   if(!ParseLSResponse(body,latest))
      return false;

   LSRow current[];
   ReadLSFile(current);

   for(int i=0;i<ArraySize(latest);i++)
      UpsertLS(current,latest[i]);

   long nowMs=(long)TimeGMT()*1000;
   long cutoff=nowMs-(long)LSHistoryHours()*3600000;
   PruneLS(current,cutoff);

   return SaveLS(current);
}

// Independent L/S step: never affects OI/M1/M5 or g_historyReady.
bool g_lsReady=false;
bool g_lsLastOk=false;

void ServiceLS()
{
   if(!InpFeedLS)
      return;

   if(!g_lsReady)
   {
      if(LSHistoryEnough())
         g_lsReady=true;
      else
      {
         PrintFormat("LAB093_FEED L/S backfill: symbol=%s history=%dh file=Common\\Files\\%s",
                     SafeSymbol(),LSHistoryHours(),LSPath());
         g_lsReady=BackfillLS();
         g_lsLastOk=g_lsReady;
         PrintFormat("LAB093_FEED L/S backfill result=%s",g_lsReady?"OK":"FAIL");
         Heartbeat();
         return;
      }
   }

   g_lsLastOk=RefreshLSLatest();
   Heartbeat();
   if(InpVerbose || !g_lsLastOk)
      PrintFormat("LAB093_FEED incremental L/S=%s",g_lsLastOk?"OK":"FAIL");
}

string LSStateText()
{
   if(!InpFeedLS) return "off";
   if(!g_lsReady) return "BACKFILL PENDING";
   return g_lsLastOk ? "OK" : "LAST REFRESH FAILED (old file kept)";
}

//---------------- Full startup backfill ------------------------------
bool BackfillOI()
{
   long nowMs=(long)TimeGMT()*1000;
   long cutoff=nowMs-(long)MathMax(24,InpHistoryHours)*3600000;

   OIRow all[];
   ArrayResize(all,0);

   long cursor=cutoff;
   while(cursor<nowMs && !IsStopped())
   {
      string url=API+OPEN_INTEREST_HIST_PATH+
                 "?symbol="+SafeSymbol()+
                 "&period=5m&limit=500&startTime="+StringFormat("%I64d",cursor);

      string body;
      if(!HttpGet(url,body))
         return false;

      OIRow page[];
      if(!ParseOIResponse(body,page))
         break;

      long lastTs=0;
      for(int i=0;i<ArraySize(page);i++)
      {
         if(page[i].ts>=cutoff && page[i].ts<=nowMs)
         {
            UpsertOI(all,page[i]);
            lastTs=MathMax(lastTs,page[i].ts);
         }
      }

      if(lastTs<=cursor)
         break;

      cursor=lastTs+300000;
      if(ArraySize(page)<500)
         break;
      Heartbeat();
   }

   PruneOI(all,cutoff);
   if(ArraySize(all)<4)
      return false;

   return SaveOI(all);
}

bool BackfillK(const string interval,const int tfMinutes)
{
   long nowMs=(long)TimeGMT()*1000;
   long cutoff=nowMs-(long)MathMax(24,InpHistoryHours)*3600000;
   long step=(long)tfMinutes*60000;

   KRow all[];
   ArrayResize(all,0);

   long cursor=cutoff;
   while(cursor<nowMs && !IsStopped())
   {
      string url=API+KLINE_PATH+
                 "?symbol="+SafeSymbol()+
                 "&interval="+interval+
                 "&limit=1000&startTime="+StringFormat("%I64d",cursor);

      string body;
      if(!HttpGet(url,body))
         return false;

      KRow page[];
      if(!ParseKlineResponse(body,page))
         break;

      long lastTs=0;
      for(int i=0;i<ArraySize(page);i++)
      {
         if(page[i].ts>=cutoff && page[i].ts<=nowMs)
         {
            UpsertK(all,page[i]);
            lastTs=MathMax(lastTs,page[i].ts);
         }
      }

      if(lastTs<=cursor)
         break;

      cursor=lastTs+step;
      if(ArraySize(page)<1000)
         break;
      Heartbeat();
   }

   PruneK(all,cutoff);
   if(ArraySize(all)<4)
      return false;

   return SaveK(interval,all);
}

//---------------- Incremental refresh -------------------------------
// One request per dataset. We merge latest 500 rows into the good
// existing snapshot, prune to the requested horizon, then rewrite.

bool RefreshOILatest()
{
   string body;
   string url=API+OPEN_INTEREST_HIST_PATH+
              "?symbol="+SafeSymbol()+"&period=5m&limit=500";

   if(!HttpGet(url,body))
      return false;

   OIRow latest[];
   if(!ParseOIResponse(body,latest))
      return false;

   OIRow current[];
   ReadOIFile(current);

   for(int i=0;i<ArraySize(latest);i++)
      UpsertOI(current,latest[i]);

   long nowMs=(long)TimeGMT()*1000;
   long cutoff=nowMs-(long)MathMax(24,InpHistoryHours)*3600000;
   PruneOI(current,cutoff);

   return SaveOI(current);
}

bool RefreshKLatest(const string interval,const int tfMinutes)
{
   string body;
   string url=API+KLINE_PATH+
              "?symbol="+SafeSymbol()+
              "&interval="+interval+
              "&limit=1000";

   if(!HttpGet(url,body))
      return false;

   KRow latest[];
   if(!ParseKlineResponse(body,latest))
      return false;

   KRow current[];
   ReadKFile(interval,current);

   for(int i=0;i<ArraySize(latest);i++)
      UpsertK(current,latest[i]);

   long nowMs=(long)TimeGMT()*1000;
   long cutoff=nowMs-(long)MathMax(24,InpHistoryHours)*3600000;
   PruneK(current,cutoff);

   return SaveK(interval,current);
}

//---------------- Health / refresh orchestration --------------------
bool ExistingHistoryEnough()
{
   KRow m5[];
   if(!ReadKFile("5m",m5) || ArraySize(m5)<2)
      return false;

   long span=m5[ArraySize(m5)-1].ts-m5[0].ts;
   long required=(long)MathMax(24,InpHistoryHours)*3600000;

   // Allow 95% to tolerate boundary alignment.
   return span >= (long)(required*0.95);
}

bool FullBackfill()
{
   PrintFormat("LAB093_FEED startup backfill: symbol=%s history=%dh",
               SafeSymbol(),InpHistoryHours);

   // Each dataset is written only after its own complete successful fetch.
   bool oi=BackfillOI();
   Heartbeat();

   bool m1=BackfillK("1m",1);
   Heartbeat();

   bool m5=BackfillK("5m",5);
   Heartbeat();

   PrintFormat("LAB093_FEED backfill result OI=%s M1=%s M5=%s",
               oi?"OK":"FAIL",m1?"OK":"FAIL",m5?"OK":"FAIL");

   return oi && m1 && m5;
}

void IncrementalRefresh()
{
   bool oi=RefreshOILatest();
   Heartbeat();

   bool m1=RefreshKLatest("1m",1);
   Heartbeat();

   bool m5=RefreshKLatest("5m",5);
   Heartbeat();

   if(InpVerbose || !oi || !m1 || !m5)
      PrintFormat("LAB093_FEED incremental OI=%s M1=%s M5=%s",
                  oi?"OK":"FAIL",m1?"OK":"FAIL",m5?"OK":"FAIL");
}

//---------------- Panel (v1.08) --------------------------------------
string AgeText(const datetime t)
{
   if(t==0) return "never";
   long a=(long)(TimeGMT()-t);
   if(a<120) return IntegerToString(a)+"s ago";
   return IntegerToString(a/60)+"m ago";
}

void ShowPanel(const string state)
{
   Comment(
      "BinanceLAB093 VPS FEEDER v1.08\n",
      "Symbol: ",SafeSymbol(),"  History: ",IntegerToString(InpHistoryHours),"h  Refresh: ",IntegerToString(InpRefreshSec),"s\n",
      "State: ",state,"\n",
      "Last OK  OI: ",AgeText(g_okOI),"  M1: ",AgeText(g_okM1),"  M5: ",AgeText(g_okM5),"  L/S: ",AgeText(g_okLS),"\n",
      "L/S: ",LSStateText(),"  |  HTTP fails since start: ",IntegerToString(g_httpFails)
   );
}

//---------------- VPS EA lifecycle -----------------------------------
bool g_historyReady=false;

void StartFeeding()
{
   // If a previous valid snapshot already exists on THIS terminal/VPS,
   // avoid a full backfill on every migration/restart.
   if(!ExistingHistoryEnough())
   {
      bool ok=FullBackfill();
      if(!ok)
         Print("LAB093_FEED VPS WARNING: startup backfill incomplete. Existing good files were preserved where requests failed.");
      g_historyReady=ok || ExistingHistoryEnough();
   }
   else
   {
      Print("LAB093_FEED VPS existing history is sufficient; skipping full startup backfill.");
      IncrementalRefresh();
      g_historyReady=true;
   }
   ServiceLS();
   ShowPanel(g_historyReady ? "READY" : "DEGRADED / RETRYING");
}

int OnInit()
{
   Print("BinanceLAB093 DataFeeder VPS EA v1.08 started. Add https://fapi.binance.com to allowed WebRequest URLs.");
   EventSetTimer(MathMax(15,InpRefreshSec));

   if(!AcquireLock())
   {
      g_waitLock=true;                  // v1.08: do not fail init; retry every cycle
      ShowPanel(StringFormat("WAITING: another feeder holds lock (age %.0fs). Delete GV %s if none runs.",g_lockAge,g_lockKey));
      return INIT_SUCCEEDED;
   }
   StartFeeding();
   return INIT_SUCCEEDED;
}

void OnTimer()
{
   if(g_waitLock)
   {
      if(!AcquireLock())
      {
         ShowPanel(StringFormat("WAITING: another feeder holds lock (age %.0fs). Delete GV %s if none runs.",g_lockAge,g_lockKey));
         return;
      }
      g_waitLock=false;
      Print("LAB093_FEED lock acquired, starting.");
      StartFeeding();
      return;
   }

   Heartbeat();

   if(!g_historyReady)
   {
      // Recovery path: retry a full backfill only while history is still insufficient.
      if(!ExistingHistoryEnough())
      {
         bool ok=FullBackfill();
         g_historyReady=ok || ExistingHistoryEnough();
         if(!g_historyReady)
         {
            ServiceLS();   // L/S is independent of OI/M1/M5 backfill state
            ShowPanel("BACKFILL FAILED - old snapshots preserved");
            return;
         }
      }
      else
         g_historyReady=true;
   }

   IncrementalRefresh();
   ServiceLS();
   ShowPanel("READY");
}

void OnTick()
{
   // No trading and no tick dependency. All work is timer-driven.
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
   ReleaseLock();
   PrintFormat("BinanceLAB093 DataFeeder VPS EA v1.08 stopped. reason=%d",reason);
}
//+------------------------------------------------------------------+
