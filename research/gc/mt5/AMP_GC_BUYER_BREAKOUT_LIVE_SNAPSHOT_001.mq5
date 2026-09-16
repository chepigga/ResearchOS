//+------------------------------------------------------------------+
//| AMP_GC_BUYER_BREAKOUT_LIVE_SNAPSHOT_001.mq5                     |
//| Non-trading realtime observer for LAB013 parity audit.           |
//| It NEVER sends orders.                                           |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Realtime BUYER_BREAKOUT_LONG_001 decision snapshot logger"

input int    InpHistoryHours = 12;  // Tick history requested to reconstruct causal M1 state
input string InpOutputFile   = "GC_LAB013\\AMP_GC_LIVE_SNAPSHOTS.csv"; // FILE_COMMON CSV
input bool   InpVerbose      = true;

#define LOGGER_VERSION "AMP_GC_BUYER_BREAKOUT_LIVE_SNAPSHOT_001"
#define FREEZE_COMMIT  "80334cb9550682a1d2e440f73ee4b70033f052e9"

const ulong FREEZE_UTC_MS = 1789592772000;

struct BarRec
{
   ulong  bar_ms;
   double open;
   double high;
   double low;
   double close;
   double buy_vol;
   double sell_vol;
   int    exclusive_ticks;
};

int   g_file = INVALID_HANDLE;
ulong g_last_processed_bar_ms = 0;

ulong MinuteStart(const ulong tms)
{
   return (tms / 60000) * 60000;
}

double TickVolume(const MqlTick &tk)
{
   if(tk.volume_real > 0.0)
      return tk.volume_real;
   return (double)tk.volume;
}

bool IsExclusiveBuy(const MqlTick &tk)
{
   const bool b = ((tk.flags & TICK_FLAG_BUY) != 0);
   const bool s = ((tk.flags & TICK_FLAG_SELL) != 0);
   return (b && !s);
}

bool IsExclusiveSell(const MqlTick &tk)
{
   const bool b = ((tk.flags & TICK_FLAG_BUY) != 0);
   const bool s = ((tk.flags & TICK_FLAG_SELL) != 0);
   return (s && !b);
}

double LinearQuantile(double &src[], const double q)
{
   const int n = ArraySize(src);
   if(n <= 0)
      return EMPTY_VALUE;

   double a[];
   ArrayResize(a,n);
   for(int i=0;i<n;i++)
      a[i]=src[i];
   ArraySort(a);

   if(n == 1)
      return a[0];

   const double pos = (n-1)*q;
   const int lo = (int)MathFloor(pos);
   const int hi = (int)MathCeil(pos);
   if(lo == hi)
      return a[lo];
   const double w = pos-lo;
   return a[lo]*(1.0-w)+a[hi]*w;
}

bool EnsureOutput()
{
   if(g_file != INVALID_HANDLE)
      return true;

   ResetLastError();
   g_file = FileOpen(InpOutputFile,
                     FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,
                     ',');
   if(g_file == INVALID_HANDLE)
   {
      PrintFormat("LAB013 FileOpen failed: %s error=%d",InpOutputFile,GetLastError());
      return false;
   }

   if(FileSize(g_file) == 0)
   {
      FileWrite(g_file,
         "record_version","logger_version","freeze_commit","symbol",
         "bar_time_utc_ms","decision_time_utc_ms","warmup_ok",
         "open","high","low","close","buy_vol","sell_vol","volume","delta",
         "delta_frac","atr14","body_atr","close_pos","q90_delta","q75_buy",
         "prior20_high","a_buy","signal_bool","raw_tick_count",
         "exclusive_tick_count","dual_flag_count","excluded_flag_count","void_record");
      FileFlush(g_file);
   }
   FileSeek(g_file,0,SEEK_END);
   return true;
}

bool BuildAndWriteSnapshot(const ulong target_bar_ms,const ulong decision_ms)
{
   if(target_bar_ms <= FREEZE_UTC_MS)
      return false;

   const ulong history_span = (ulong)MathMax(InpHistoryHours,6) * 60 * 60 * 1000;
   const ulong from_ms = (target_bar_ms > history_span ? target_bar_ms-history_span : 0);
   const ulong to_ms = target_bar_ms + 59999;

   MqlTick ticks[];
   ResetLastError();
   const int copied = CopyTicksRange(_Symbol,ticks,COPY_TICKS_ALL,from_ms,to_ms);
   if(copied <= 0)
   {
      if(InpVerbose)
         PrintFormat("LAB013 CopyTicksRange failed/empty bar=%I64u copied=%d err=%d",
                     target_bar_ms,copied,GetLastError());
      return false;
   }

   BarRec bars[];
   int nb=0;
   int raw_target=0, exclusive_target=0, dual_target=0, excluded_target=0;

   for(int i=0;i<copied;i++)
   {
      const MqlTick tk=ticks[i];
      const double vol=TickVolume(tk);
      if(tk.last<=0.0 || vol<=0.0)
         continue;

      const ulong bm=MinuteStart(tk.time_msc);
      const bool buy=IsExclusiveBuy(tk);
      const bool sell=IsExclusiveSell(tk);
      const bool fb=((tk.flags&TICK_FLAG_BUY)!=0);
      const bool fs=((tk.flags&TICK_FLAG_SELL)!=0);

      if(bm==target_bar_ms)
      {
         raw_target++;
         if(fb && fs) dual_target++;
         if(buy || sell) exclusive_target++;
         else excluded_target++;
      }

      if(!(buy || sell))
         continue;

      if(nb==0 || bars[nb-1].bar_ms!=bm)
      {
         const int newsize=ArrayResize(bars,nb+1);
         if(newsize<nb+1)
            return false;
         bars[nb].bar_ms=bm;
         bars[nb].open=tk.last;
         bars[nb].high=tk.last;
         bars[nb].low=tk.last;
         bars[nb].close=tk.last;
         bars[nb].buy_vol=0.0;
         bars[nb].sell_vol=0.0;
         bars[nb].exclusive_ticks=0;
         nb++;
      }

      if(tk.last>bars[nb-1].high) bars[nb-1].high=tk.last;
      if(tk.last<bars[nb-1].low)  bars[nb-1].low=tk.last;
      bars[nb-1].close=tk.last;
      if(buy) bars[nb-1].buy_vol+=vol;
      else    bars[nb-1].sell_vol+=vol;
      bars[nb-1].exclusive_ticks++;
   }

   int cur=-1;
   for(int i=nb-1;i>=0;i--)
   {
      if(bars[i].bar_ms==target_bar_ms)
      {
         cur=i;
         break;
      }
   }
   if(cur<0)
      return false; // no reconstructed directional-trade M1 bar on this minute

   // Need 240 prior reconstructed bars plus enough bars for ATR/TR.
   if(cur<240 || cur<14)
   {
      if(InpVerbose)
         PrintFormat("LAB013 warmup insufficient bar=%I64u prior_bars=%d",target_bar_ms,cur);
      return false;
   }

   double q_delta[240];
   double q_buy[240];
   for(int j=0;j<240;j++)
   {
      const int k=cur-240+j;
      const double v=bars[k].buy_vol+bars[k].sell_vol;
      q_delta[j]=(v>0.0 ? (bars[k].buy_vol-bars[k].sell_vol)/v : 0.0);
      q_buy[j]=bars[k].buy_vol;
   }
   const double q90_delta=LinearQuantile(q_delta,0.90);
   const double q75_buy=LinearQuantile(q_buy,0.75);

   double prior20_high=bars[cur-20].high;
   for(int k=cur-19;k<=cur-1;k++)
      if(bars[k].high>prior20_high) prior20_high=bars[k].high;

   double trsum=0.0;
   for(int k=cur-13;k<=cur;k++)
   {
      if(k<=0)
         return false;
      const double r1=bars[k].high-bars[k].low;
      const double r2=MathAbs(bars[k].high-bars[k-1].close);
      const double r3=MathAbs(bars[k].low-bars[k-1].close);
      trsum += MathMax(r1,MathMax(r2,r3));
   }
   const double atr14=trsum/14.0;
   if(!(atr14>0.0))
      return false;

   const BarRec c=bars[cur];
   const double volume=c.buy_vol+c.sell_vol;
   if(!(volume>0.0))
      return false;
   const double delta=c.buy_vol-c.sell_vol;
   const double delta_frac=delta/volume;
   const double range=c.high-c.low;
   const double close_pos=(range>0.0 ? (c.close-c.low)/range : 0.5);
   const double body_atr=(c.close-c.open)/atr14;
   const bool a_buy=(delta_frac>=q90_delta && c.buy_vol>=q75_buy);
   const bool signal=(a_buy && c.close>c.open && close_pos>=0.75 &&
                      c.high>=prior20_high && body_atr>0.0);

   if(!EnsureOutput())
      return false;

   FileSeek(g_file,0,SEEK_END);
   const uint written=FileWrite(g_file,
      1,LOGGER_VERSION,FREEZE_COMMIT,_Symbol,
      (long)target_bar_ms,(long)decision_ms,true,
      c.open,c.high,c.low,c.close,c.buy_vol,c.sell_vol,volume,delta,
      delta_frac,atr14,body_atr,close_pos,q90_delta,q75_buy,
      prior20_high,a_buy,signal,raw_target,
      exclusive_target,dual_target,excluded_target,false);
   FileFlush(g_file);

   if(written==0)
   {
      PrintFormat("LAB013 FileWrite failed bar=%I64u err=%d",target_bar_ms,GetLastError());
      return false;
   }

   if(InpVerbose && signal)
      PrintFormat("LAB013 SIGNAL %s bar=%I64u delta_frac=%.10f q90=%.10f buy=%.6f q75=%.6f",
                  _Symbol,target_bar_ms,delta_frac,q90_delta,c.buy_vol,q75_buy);
   return true;
}

void ProcessClock()
{
   MqlTick latest;
   if(!SymbolInfoTick(_Symbol,latest) || latest.time_msc==0)
      return;

   const ulong current_minute=MinuteStart(latest.time_msc);
   if(current_minute<60000)
      return;
   const ulong completed=current_minute-60000;

   if(g_last_processed_bar_ms==0)
   {
      // Do not retroactively manufacture a "realtime" snapshot on attach/restart.
      g_last_processed_bar_ms=completed;
      if(InpVerbose)
         PrintFormat("LAB013 armed at %s. First future completed M1 will be logged.",_Symbol);
      return;
   }

   if(completed<=g_last_processed_bar_ms)
      return;

   // If the terminal/feed skipped several clock minutes, do not backfill them as
   // realtime decisions. Missing bars are intentionally visible to the audit.
   BuildAndWriteSnapshot(completed,latest.time_msc);
   g_last_processed_bar_ms=completed;
}

int OnInit()
{
   if(!SymbolSelect(_Symbol,true))
      return INIT_FAILED;
   if(!EnsureOutput())
      return INIT_FAILED;
   EventSetTimer(1);
   ProcessClock();
   PrintFormat("%s started on %s. NON-TRADING observer; output=%s",
               LOGGER_VERSION,_Symbol,InpOutputFile);
   return INIT_SUCCEEDED;
}

void OnTimer()
{
   ProcessClock();
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_file!=INVALID_HANDLE)
   {
      FileFlush(g_file);
      FileClose(g_file);
      g_file=INVALID_HANDLE;
   }
}
