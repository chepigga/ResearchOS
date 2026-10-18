//+------------------------------------------------------------------+
//| CrowdFade_LAB157_CORE_v005.mq5                                   |
//| v006 (LAB271/272): двигун L — каскад ліквідацій: натовп перекошений,|
//|   OI(монети) -1% за 15 хв і ціна >=0.3 ATR проти натовпу; SL 2 ATR, |
//|   трейл пік-1.5R після +1.5R, 12 год; magic base+30; InpL_Mode=1 —   |
//|   лише журнал з віртуальною угодою (L_SHADOW_ENTRY/EXIT з R).       |
//| v005.1: повтори HTTP (InpHttpRetries), лог затримки — кожна нова  |
//|   точка + batch/http_fails/skipped_polls; ratio до перевірки фідера.|
//| v005 (LAB268): виходи на початку контртренду (перемикачі 0/1/2): |
//|   D: компас (-sign z24, |z24|>=1) розвернувся проти і MTM>=+1R.  |
//|   S: EMA9 перетнула EMA20 на H1 (брокер) проти позиції.          |
//| v004:                                                            |
//| v004 (LAB265/266): + двигун S — Supertrend H2 (ohlc4, ATR10,     |
//|   1.3) з M5 фідера (UTC), HTF H1 EMA150>EMA250, пропуск коли     |
//|   натовп у бік угоди (|z24|>=1), SL 2.2 ATR14 H2, без TP, вихід  |
//|   на протилежному фліпі; magic base+20; ризик 0.10%.             |
//| v003 (LAB255-258): ядро A + B3_HIGH + двигун D (пороги D2).      |
//|   - EARLY вимкнено (дублює A), R48 у тіньовому режимі (лог).     |
//|   - InpMaxHoldHours=72 для A/B3.                                 |
//|   - D: |z6| перетинає 1.5, z24 того ж знаку |z24|>=0.5, H4 у бік |
//|     угоди, 1 вхід на епізод; SL 3 H1ATR, трейл 3R від піку після |
//|     +2R, 48 год; окремий magic, свій ліміт 2 позиції; ризик 0.10%.|
//|   - Тіньовий лог сигналів D(2.0/1.0/H4) і D'(2.0/1.0/без H4).    |
//|   - Лог затримки Binance L/S (CrowdFade_v003_LATENCY.csv).       |
//| v005: модуль трендових ліній прибрано (LAB251/259: не допомагає).|
//| Forward/demo EA for frozen LAB157 candidate architecture.        |
//| Uses existing BinanceLAB093 feeder for M5 + OI FILE_COMMON data.  |
//| Ratio/Z stays direct from Binance, as in previous CrowdFade EA.   |
//| RESEARCH / DEMO ONLY.                                             |
//+------------------------------------------------------------------+
#property strict
#property version   "1.060"
#property description "CrowdFade core v006: + engine L (liquidation cascade, shadow by default). A+B3 (72h) + D2 (+ exit when crowd compass turns against at >=+1R) + S Supertrend H2 (+ exit on EMA9/20 H1 cross against). EARLY off, R48 shadow."

#include <Trade/Trade.mqh>
CTrade trade;

//---------------- Inputs ---------------------------------------------
input group "=== SYMBOLS / DATA ==="
input string InpBrokerSymbol       = "BTCUSD";      // Broker CFD symbol
input string InpBinanceSymbol      = "BTCUSDT";     // Binance Futures symbol
input string InpBinanceApiKey      = "";            // Kept for parity with previous EA
input string InpFeederFolder       = "BinanceLAB093";// FILE_COMMON folder used by existing feeder
input int    InpRefreshSec         = 15;
input int    InpWebTimeoutMs       = 4000;
input int    InpHttpRetries        = 2;              // повтори запиту до Binance при збої (пауза 0.5 с)
input int    InpMaxDataAgeMinutes  = 15;             // Reject stale M5/OI snapshots
input int    InpRequiredHistoryHrs = 220;            // H4 EMA50 needs ~200h. Set feeder InpHistoryHours >= 240.

input group "=== FROZEN LAB157 SIGNAL ==="
input int    InpZWindowBars        = 72;             // 72 x M5 = 6h, population SD
input double InpExtremeZ           = 1.0;
input int    InpH1ATRPeriod        = 14;
input int    InpH1EMAPeriod        = 20;
input int    InpH4EMAPeriod        = 50;
input int    InpH4EMALagBars       = 6;
input double InpA_ExtensionATR     = 1.529;          // Frozen TRAIN threshold
input double InpA_OI4hMin          = 0.00867;        // +0.867%
input int    InpSwingSearchBars    = 72;             // 6h
input int    InpEarlyMaxMinutes    = 5;
input bool   InpEarlyEnable        = false;          // v003: EARLY вимкнено (95% сигналів = A)

input group "=== B3_HIGH ==="
input int    InpB3MinTrendAgeH4    = 4;
input double InpB3DepthATR         = 0.50;
input double InpB3ZStrengthMin     = 0.25;
input int    InpB3AttackMaxBars    = 72;
input int    InpB3ReclaimMaxBars   = 72;

input group "=== R48_HIGH ==="
input int    InpR48LookbackBars    = 576;            // 48h on M5
input int    InpR48AcceptanceBars  = 6;
input int    InpR48MinOutside      = 4;
input double InpR48MeanMarginATR   = 0.689;
input double InpR48OIChangeMin     = 0.00350;        // +0.350%
input int    InpR48Mode            = 1;              // 0 = вимк., 1 = тінь (лише лог), 2 = торгувати

input group "=== LAB157 EXECUTION ==="
input double InpRiskPct            = 0.25;           // Risk per position, % equity
input double InpStopH1ATR          = 1.00;
input double InpPartialAtR         = 3.00;           // Close 50% at +3R
input double InpPartialFraction    = 0.50;
input double InpRunnerLockR        = 2.00;           // Remaining 50% stop -> +2R
input int    InpMaxHoldHours       = 72;             // v003: 72 год (LAB253)
input int    InpMaxPositions       = 2;              // Frozen = 2
input double InpAddonFirstLockR    = 0.25;           // On add-on, first SL -> max(current,+0.25R)
input double InpMaxVolumeLots      = 1.00;           // Hard safety cap. 0 = disabled
input double InpMaxMarginUsePct    = 90.0;
input int    InpSlippagePts        = 50;
input double InpMaxSpreadATR       = 0.0;            // 0 disabled, else spread <= fraction of H1ATR
input bool   InpDryRun             = false;

input group "=== ENGINE D (LAB254/256, пороги D2) ==="
input bool   InpDEnable            = true;
input int    InpD_Z24WindowBars    = 288;            // 24h, population SD
input double InpD_Z6Cross          = 1.5;            // |z6| перетинає цей рівень (prev < рівня)
input double InpD_Z24Min           = 0.5;            // |z24| >= і той самий знак, що z6
input bool   InpD_UseH4            = true;           // H4 EMA50 тренд у бік угоди
input double InpD_EpisodeResetZ    = 1.0;            // новий епізод після |z6| < 1
input double InpD_RiskPct          = 0.10;           // % equity на угоду D
input double InpD_StopATR          = 3.0;            // 1R = 3 x H1 ATR
input double InpD_TrailStartR      = 2.0;            // трейл вмикається після піку +2R
input double InpD_TrailDistR       = 3.0;            // стоп = пік - 3R
input int    InpD_MaxHoldHours     = 48;
input int    InpD_MaxPositions     = 2;              // окремий ліміт D; 2-га лише в той самий бік і MTM>=0
input int    InpD_MaxSignalAgeMin  = 10;             // не входити, якщо сигнал старший (затримка даних)
input bool   InpD_ShadowLog        = true;           // лог сигналів D(2.0/1.0/H4) і D'(без H4)

input group "=== ENGINE S: Supertrend H2 + компас натовпу (LAB265/266) ==="
input bool   InpSEnable            = true;
input int    InpS_TFHours          = 2;              // ТФ Supertrend: H2 з M5 фідера, кошики UTC (як у дослідженні)
input int    InpS_ATRPeriod        = 10;             // ATR для смуг Supertrend (RMA)
input double InpS_Factor           = 1.3;            // чутливість
input bool   InpS_UseHTF           = true;           // H1 EMA150 vs EMA250 (символ брокера) у бік угоди
input double InpS_CrowdAgainstZ    = 1.0;            // пропуск, якщо натовп у бік угоди: sign(z24)==side і |z24|>=цього
input double InpS_StopATR          = 2.2;            // SL = 2.2 x ATR14(H2, RMA); TP немає
input double InpS_RiskPct          = 0.10;           // % equity
input bool   InpS_LiveTrade        = true;           // false = лише лог сигналів S (тінь)

input group "=== ВИХОДИ НА ПОЧАТКУ КОНТРТРЕНДУ (LAB268) ==="
input int    InpD_CrowdExitMode    = 2;              // D: 0 вимк., 1 лише лог, 2 закривати
input double InpD_CrowdExitZ       = 1.0;            // компас = -sign(z24) при |z24|>=цього
input double InpD_CrowdExitMinR    = 1.0;            // закривати лише якщо угода >= +1R у момент розвороту компаса
input int    InpS_EMAExitMode      = 2;              // S: 0 вимк., 1 лише лог, 2 закривати
input int    InpS_EMAFast          = 9;              // EMA9 vs EMA20 на H1 (символ брокера), останній закритий H1
input int    InpS_EMASlow          = 20;

input group "=== ENGINE L: каскад ліквідацій (LAB271/272) ==="
input int    InpL_Mode             = 1;              // 0 вимк., 1 лише журнал (віртуальна угода), 2 торгувати
input int    InpL_OIBars           = 3;              // вікно OI/ціни: 3 x M5 = 15 хв
input double InpL_OIDropPct        = 1.0;            // OI (монети) впав >= 1% за вікно
input double InpL_PriceATR         = 0.3;            // ціна пройшла >= 0.3 H1ATR проти натовпу за вікно
input double InpL_Z24Min           = 0.5;            // стан натовпу: |z6|>=1, z24 той самий знак |z24|>=0.5
input double InpL_StopATR          = 2.0;            // 1R = 2 x H1ATR
input double InpL_TrailStartR      = 1.5;            // трейл після піку +1.5R
input double InpL_TrailDistR       = 1.5;            // стоп = пік - 1.5R
input int    InpL_MaxHoldHours     = 12;
input double InpL_RiskPct          = 0.10;

input group "=== IDS / LOGGING ==="
input long   InpMagicBase          = 157000;         // D magic = base + 10
input bool   InpVerbose            = true;
input string InpLogFile            = "CrowdFade_LAB157_FORWARD_v006.csv";
input string InpLatencyLogFile     = "CrowdFade_v005_LATENCY.csv";


//---------------- Binance API ----------------------------------------
#define API        "https://fapi.binance.com"
#define RATIO_PATH "/futures/data/globalLongShortAccountRatio"

//---------------- Engine IDs ----------------------------------------
enum ENUM_CF157_ENGINE
{
   ENG_A     = 1,
   ENG_B3    = 2,
   ENG_R48   = 3,
   ENG_EARLY = 4,
   ENG_D     = 10
};

string EngineName(const int e)
{
   if(e==ENG_A) return "A";
   if(e==ENG_B3) return "B3_HIGH";
   if(e==ENG_R48) return "R48_HIGH";
   if(e==ENG_EARLY) return "EARLY_EPISODE";
   if(e==ENG_D) return "D";
   if(e==11) return "D_SHADOW_2.0_1.0_H4";
   if(e==12) return "DPRIME_SHADOW_NO_H4";
   if(e==20) return "S_SUPERTREND_H2";
   if(e==30) return "L_CASCADE";
   return "UNKNOWN";
}
long EngineMagic(const int e){ return InpMagicBase + e; }

//---------------- Data structures -----------------------------------
struct M5Bar
{
   long   ms;
   double o,h,l,c;
};
struct OIPoint
{
   long   ms;
   double oi;
};
struct H1Ctx
{
   bool   ok;
   double atr;
   double ema20;
   double extension;
};
struct H4Ctx
{
   bool   ok;
   int    trend;
   int    trend_age;
   int    impulse_age;
   double ema50;
   double atr14;
   string phase;
};
struct SignalCandidate
{
   bool   valid;
   int    engine;
   int    side;
   double atr;
   double z;
   double ext;
   double oi4h;
   string detail;
};

M5Bar  g_m5[];
OIPoint g_oi[];
long   g_lastProcessedBarMs=0;
long   g_lastRatioTs=0;
double g_lastZ=0.0;
double g_prevZ=0.0;
bool   g_havePrevZ=false;
bool   g_episodeActive=false;
int    g_episodeSign=0;
long   g_episodeStartMs=0;

// A / EARLY pending SWING3 state
bool   g_aArmed=false;
int    g_aEngine=0;
int    g_aSide=0;
long   g_aAnchorMs=0;
int    g_aAnchorIndex=-1;
double g_aATR=0.0;
double g_aZ=0.0;
double g_aExt=0.0;
double g_aOI4h=0.0;

// Fresh episode rescue watch
bool   g_rescueWatch=false;
int    g_rescueSide=0;
int    g_rescueSign=0;
long   g_rescueStartMs=0;

// B3 state
bool   g_b3Active=false;
int    g_b3Trend=0;
int    g_b3CrowdDir=0;
long   g_b3StartMs=0;
int    g_b3StartIndex=-1;
double g_b3Anchor=0.0;
double g_b3ATR=0.0;
double g_b3Z0=0.0;
double g_b3OI0=0.0;
int    g_b3HitIndex[5];
double g_b3Level[5];
bool   g_b3DepthQualified=false;
int    g_b3DepthHitIndex=-1;

// R48 pending slots
#define MAX_R48_PENDING 8
struct R48Pending
{
   bool active;
   int  side;
   int  signalIndex;
   long signalMs;
   double boundary;
   double atr;
   double oi0;
};
R48Pending g_r48[MAX_R48_PENDING];
int g_lastR48SignalIndex=-999999;

// Ratio series from the latest fetch (shared by core Z and engine D)
double g_ratio[];
long   g_ratioTs[];

// Engine D episode state (one per rule variant: 0 = live D2, 1 = shadow D, 2 = shadow D')
struct DEpisode
{
   int  sign;     // 0 = no active episode (|z6| < reset)
   bool used;     // signal already taken in this episode
};
DEpisode g_dEp[3];
long   g_lastDRatioTs=0;   // last ratio timestamp processed by engine D
string g_dPanel="-";

// panel
string g_state="INIT";
string g_lastSignal="-";
double g_panelZ=0.0;
double g_panelOI4h=0.0;
double g_panelATR=0.0;
string g_panelPhase="-";

//---------------- Basic helpers -------------------------------------
double JsonNum(const string s,const int p,const string key,int &endp)
{
   int k=StringFind(s,"\""+key+"\"",p); if(k<0){endp=-1;return 0.0;}
   int c=StringFind(s,":",k); if(c<0){endp=-1;return 0.0;}
   int i=c+1,n=StringLen(s);
   while(i<n && (StringGetCharacter(s,i)==' ' || StringGetCharacter(s,i)=='\"')) i++;
   int j=i;
   while(j<n)
   {
      ushort ch=StringGetCharacter(s,j);
      if((ch>='0'&&ch<='9')||ch=='-'||ch=='+'||ch=='.'||ch=='e'||ch=='E') j++; else break;
   }
   endp=j;
   return StringToDouble(StringSubstr(s,i,j-i));
}

int g_httpFails=0;      // failed WebRequest attempts since last latency row
int g_skipPolls=0;      // timer cycles without a successful ratio fetch since last latency row
bool HttpGet(const string url,string &body)
{
   char data[],res[]; string hdr="";
   string reqhdr="";
   if(StringLen(InpBinanceApiKey)>0) reqhdr="X-MBX-APIKEY: "+InpBinanceApiKey+"\r\n";
   int code=-1;
   for(int attempt=0;attempt<=InpHttpRetries;attempt++)
   {
      if(attempt>0) Sleep(500);
      ResetLastError();
      code=WebRequest("GET",url,reqhdr,InpWebTimeoutMs,data,res,hdr);
      if(code==200) break;
      g_httpFails++;
      PrintFormat("CF157 HTTP FAIL code=%d err=%d attempt=%d/%d url=%s",code,GetLastError(),attempt+1,InpHttpRetries+1,url);
   }
   if(code!=200) return false;
   body=CharArrayToString(res,0,WHOLE_ARRAY,CP_UTF8);
   return StringLen(body)>10;
}

bool FetchRatioSeries(double &r[],long &t[])
{
   string body,url=API+RATIO_PATH+"?symbol="+InpBinanceSymbol+"&period=5m&limit=500";
   if(!HttpGet(url,body)) return false;
   ArrayResize(r,0); ArrayResize(t,0);
   int p=0;
   while(true)
   {
      int k=StringFind(body,"\"longShortRatio\"",p); if(k<0) break;
      int e=-1,et=-1;
      double x=JsonNum(body,k,"longShortRatio",e);
      double td=JsonNum(body,k,"timestamp",et);
      if(e<0 || et<0) break;
      if(x>0.0 && td>0.0)
      {
         int n=ArraySize(r);
         ArrayResize(r,n+1); ArrayResize(t,n+1);
         r[n]=x; t[n]=(long)td;
      }
      p=MathMax(e,et);
   }
   return ArraySize(r)>=InpZWindowBars;
}

double ZAt(const double &r[],const int j,const int win)
{
   if(j<win-1) return EMPTY_VALUE;
   double sm=0.0,ss=0.0;
   for(int i=j-win+1;i<=j;i++){sm+=r[i];ss+=r[i]*r[i];}
   double m=sm/win,v=ss/win-m*m;
   if(v<=0.0) return EMPTY_VALUE;
   return (r[j]-m)/MathSqrt(v);
}

bool FetchLatestZ(double &z,long &ts)
{
   double r[]; long t[];
   if(!FetchRatioSeries(r,t)) return false;
   int n=ArraySize(r);
   z=ZAt(r,n-1,InpZWindowBars);
   if(z==EMPTY_VALUE) return false;
   ts=t[n-1];
   ArrayCopy(g_ratio,r,0,0,WHOLE_ARRAY); ArrayResize(g_ratio,n);
   ArrayCopy(g_ratioTs,t,0,0,WHOLE_ARRAY); ArrayResize(g_ratioTs,n);
   return true;
}

string FeederPath(const string suffix)
{
   string sym=InpBinanceSymbol;
   StringTrimLeft(sym); StringTrimRight(sym); StringToUpper(sym);
   return InpFeederFolder+"\\"+sym+suffix;
}

bool LoadM5()
{
   string path=FeederPath("_5m.csv");
   int h=FileOpen(path,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE)
   {
      PrintFormat("CF157 feeder M5 missing: %s err=%d",path,GetLastError());
      return false;
   }
   ArrayResize(g_m5,0);
   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      if(StringLen(line)<5) continue;
      string f[]; int n=StringSplit(line,',',f);
      if(n<5) continue;
      M5Bar b;
      b.ms=(long)StringToInteger(f[0]);
      b.o=StringToDouble(f[1]); b.h=StringToDouble(f[2]); b.l=StringToDouble(f[3]); b.c=StringToDouble(f[4]);
      if(b.ms<=0 || b.o<=0 || b.h<=0 || b.l<=0 || b.c<=0) continue;
      int k=ArraySize(g_m5); ArrayResize(g_m5,k+1); g_m5[k]=b;
   }
   FileClose(h);
   return ArraySize(g_m5)>0;
}

bool LoadOI()
{
   string path=FeederPath("_oi_5m.csv");
   int h=FileOpen(path,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE)
   {
      PrintFormat("CF157 feeder OI missing: %s err=%d",path,GetLastError());
      return false;
   }
   ArrayResize(g_oi,0);
   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      if(StringLen(line)<5) continue;
      string f[]; int n=StringSplit(line,',',f);
      if(n<2) continue;
      OIPoint q; q.ms=(long)StringToInteger(f[0]); q.oi=StringToDouble(f[1]);
      if(q.ms<=0 || q.oi<=0) continue;
      int k=ArraySize(g_oi); ArrayResize(g_oi,k+1); g_oi[k]=q;
   }
   FileClose(h);
   return ArraySize(g_oi)>0;
}

int LatestCompletedM5Index()
{
   int n=ArraySize(g_m5); if(n<2) return -1;
   long now=(long)TimeGMT()*1000;
   // feeder rows store Binance kline OPEN time. Completed if open+5m <= now.
   for(int i=n-1;i>=0;i--)
      if(g_m5[i].ms+300000<=now) return i;
   return -1;
}

double OIAtOrBefore(const long ms)
{
   for(int i=ArraySize(g_oi)-1;i>=0;i--)
      if(g_oi[i].ms<=ms) return g_oi[i].oi;
   return 0.0;
}

double OIChange4h(const long ms)
{
   double a=OIAtOrBefore(ms);
   double b=OIAtOrBefore(ms-48*300000);
   if(a<=0 || b<=0) return EMPTY_VALUE;
   return a/b-1.0;
}

bool DataFresh(const int idx)
{
   if(idx<0) return false;
   long now=(long)TimeGMT()*1000;
   long ageM5=now-(g_m5[idx].ms+300000);
   long oiMs=(ArraySize(g_oi)>0 ? g_oi[ArraySize(g_oi)-1].ms : 0);
   long ageOI=(oiMs>0 ? now-oiMs : 999999999);
   if(ageM5>InpMaxDataAgeMinutes*60000 || ageOI>InpMaxDataAgeMinutes*60000)
   {
      g_state=StringFormat("STALE M5 %.1fm OI %.1fm",(double)ageM5/60000.0,(double)ageOI/60000.0);
      return false;
   }
   return true;
}

//---------------- Context aggregation -------------------------------
double EMAFromArray(const double &v[],const int n,const int period)
{
   if(n<=0) return 0.0;
   double a=2.0/(period+1.0),ema=v[0];
   for(int i=1;i<n;i++) ema=a*v[i]+(1.0-a)*ema;
   return ema;
}

bool BuildH1(const int uptoM5,H1Ctx &ctx)
{
   ctx.ok=false;
   if(uptoM5<InpH1ATRPeriod*12+12) return false;
   long lastMs=g_m5[uptoM5].ms;
   long lastHour=(lastMs/3600000)*3600000;
   // use only COMPLETED H1 bars: bucket start < current hour start
   double O[],H[],L[],C[]; long T[];
   ArrayResize(O,0);ArrayResize(H,0);ArrayResize(L,0);ArrayResize(C,0);ArrayResize(T,0);
   long cur=-1; double o=0,h=0,l=0,c=0; bool have=false;
   for(int i=0;i<=uptoM5;i++)
   {
      long bucket=(g_m5[i].ms/3600000)*3600000;
      if(bucket>=lastHour) break;
      if(bucket!=cur)
      {
         if(have)
         {
            int k=ArraySize(C);ArrayResize(O,k+1);ArrayResize(H,k+1);ArrayResize(L,k+1);ArrayResize(C,k+1);ArrayResize(T,k+1);
            O[k]=o;H[k]=h;L[k]=l;C[k]=c;T[k]=cur;
         }
         cur=bucket;o=g_m5[i].o;h=g_m5[i].h;l=g_m5[i].l;c=g_m5[i].c;have=true;
      }
      else
      {
         h=MathMax(h,g_m5[i].h); l=MathMin(l,g_m5[i].l); c=g_m5[i].c;
      }
   }
   if(have)
   {
      int k=ArraySize(C);ArrayResize(O,k+1);ArrayResize(H,k+1);ArrayResize(L,k+1);ArrayResize(C,k+1);ArrayResize(T,k+1);
      O[k]=o;H[k]=h;L[k]=l;C[k]=c;T[k]=cur;
   }
   int n=ArraySize(C);
   if(n<MathMax(InpH1ATRPeriod+1,InpH1EMAPeriod+2)) return false;

   double trsum=0.0;
   for(int i=n-InpH1ATRPeriod;i<n;i++)
   {
      double pc=(i>0?C[i-1]:C[i]);
      double tr=MathMax(H[i]-L[i],MathMax(MathAbs(H[i]-pc),MathAbs(L[i]-pc)));
      trsum+=tr;
   }
   double atr=trsum/InpH1ATRPeriod;
   double ema=EMAFromArray(C,n,InpH1EMAPeriod);
   if(atr<=0 || ema<=0) return false;
   ctx.atr=atr;ctx.ema20=ema;ctx.extension=(C[n-1]-ema)/atr;ctx.ok=true;
   return true;
}

bool BuildH4(const int uptoM5,H4Ctx &ctx)
{
   ctx.ok=false; ctx.phase="-";
   if(uptoM5<12*4*(InpH4EMAPeriod+InpH4EMALagBars+2)) return false;
   long lastMs=g_m5[uptoM5].ms;
   long bucketSize=4*3600000;
   long currentBucket=(lastMs/bucketSize)*bucketSize;

   double O[],H[],L[],C[]; long T[];
   ArrayResize(O,0);ArrayResize(H,0);ArrayResize(L,0);ArrayResize(C,0);ArrayResize(T,0);
   long cur=-1; double o=0,h=0,l=0,c=0; bool have=false;
   for(int i=0;i<=uptoM5;i++)
   {
      long bucket=(g_m5[i].ms/bucketSize)*bucketSize;
      if(bucket>=currentBucket) break;
      if(bucket!=cur)
      {
         if(have)
         {
            int k=ArraySize(C);ArrayResize(O,k+1);ArrayResize(H,k+1);ArrayResize(L,k+1);ArrayResize(C,k+1);ArrayResize(T,k+1);
            O[k]=o;H[k]=h;L[k]=l;C[k]=c;T[k]=cur;
         }
         cur=bucket;o=g_m5[i].o;h=g_m5[i].h;l=g_m5[i].l;c=g_m5[i].c;have=true;
      }
      else
      {
         h=MathMax(h,g_m5[i].h); l=MathMin(l,g_m5[i].l); c=g_m5[i].c;
      }
   }
   if(have)
   {
      int k=ArraySize(C);ArrayResize(O,k+1);ArrayResize(H,k+1);ArrayResize(L,k+1);ArrayResize(C,k+1);ArrayResize(T,k+1);
      O[k]=o;H[k]=h;L[k]=l;C[k]=c;T[k]=cur;
   }
   int n=ArraySize(C);
   if(n<InpH4EMAPeriod+InpH4EMALagBars+16) return false;

   // EMA series needed for lag6 comparison.
   double ema[]; ArrayResize(ema,n);
   double a=2.0/(InpH4EMAPeriod+1.0); ema[0]=C[0];
   for(int i=1;i<n;i++) ema[i]=a*C[i]+(1.0-a)*ema[i-1];

   double prev=C[n-2];
   double trsum=0.0;
   for(int i=n-14;i<n;i++)
   {
      double pc=(i>0?C[i-1]:C[i]);
      double tr=MathMax(H[i]-L[i],MathMax(MathAbs(H[i]-pc),MathAbs(L[i]-pc)));
      trsum+=tr;
   }
   double atr14=trsum/14.0;
   int trend=0;
   if(C[n-1]>ema[n-1] && ema[n-1]>ema[n-1-InpH4EMALagBars]) trend=1;
   else if(C[n-1]<ema[n-1] && ema[n-1]<ema[n-1-InpH4EMALagBars]) trend=-1;

   // trend age from full H4 series
   int age=0;
   if(trend!=0)
   {
      for(int k=n-1;k>=0;k--)
      {
         int tk=0;
         if(k>=InpH4EMALagBars)
         {
            if(C[k]>ema[k] && ema[k]>ema[k-InpH4EMALagBars]) tk=1;
            else if(C[k]<ema[k] && ema[k]<ema[k-InpH4EMALagBars]) tk=-1;
         }
         if(tk==trend) age++; else break;
      }
   }

   // impulse age: most recent H4 body >=0.8 ATR14 in trend direction.
   int impulse_age=999;
   if(trend!=0)
   {
      for(int back=0;back<50 && n-1-back>=14;back++)
      {
         int k=n-1-back;
         double tsum=0.0;
         for(int q=k-13;q<=k;q++)
         {
            double pc=(q>0?C[q-1]:C[q]);
            tsum+=MathMax(H[q]-L[q],MathMax(MathAbs(H[q]-pc),MathAbs(L[q]-pc)));
         }
         double at=tsum/14.0;
         if(at>0)
         {
            double body=(C[k]-O[k])/at;
            if(MathAbs(body)>=0.8 && (body>0?1:-1)==trend){impulse_age=back;break;}
         }
      }
   }

   string ph="LATE";
   if(age<=3) ph="BIRTH";
   else if(impulse_age<=2) ph="REACCEL";
   else if(age<=12) ph="CONT";
   else if(age<=24) ph="MATURE";

   ctx.ok=true;ctx.trend=trend;ctx.trend_age=age;ctx.impulse_age=impulse_age;ctx.ema50=ema[n-1];ctx.atr14=atr14;ctx.phase=ph;
   return true;
}

bool ContextAOK(const int idx,const int side,H1Ctx &h1,H4Ctx &h4,double &oi4h,string &why)
{
   if(!BuildH1(idx,h1)){why="H1_NOT_READY";return false;}
   if(!BuildH4(idx,h4)){why="H4_NOT_READY";return false;}
   oi4h=OIChange4h(g_m5[idx].ms);
   if(oi4h==EMPTY_VALUE){why="OI4H_NOT_READY";return false;}
   bool phase=(h4.phase=="CONT" || h4.phase=="REACCEL");
   bool opp=(h4.trend!=0 && h4.trend!=side);
   bool ext=((side>0 && h1.extension<0) || (side<0 && h1.extension>0)) && MathAbs(h1.extension)>=InpA_ExtensionATR;
   bool oi=(oi4h>=InpA_OI4hMin);
   why=StringFormat("PH=%s T=%d EXT=%.3f OI4H=%.3f%%",h4.phase,h4.trend,h1.extension,oi4h*100.0);
   return phase && opp && ext && oi;
}

//---------------- Broker / risk helpers -----------------------------
double NormVolume(const double v)
{
   double mn=SymbolInfoDouble(InpBrokerSymbol,SYMBOL_VOLUME_MIN);
   double mx=SymbolInfoDouble(InpBrokerSymbol,SYMBOL_VOLUME_MAX);
   double st=SymbolInfoDouble(InpBrokerSymbol,SYMBOL_VOLUME_STEP);
   if(st<=0) st=mn;
   double x=MathFloor(v/st+1e-9)*st;
   x=MathMax(0.0,MathMin(x,mx));
   if(x<mn) return 0.0;
   return NormalizeDouble(x,8);
}
double NormalizePriceToTick(const double p)
{
   double tick=SymbolInfoDouble(InpBrokerSymbol,SYMBOL_TRADE_TICK_SIZE);
   int digits=(int)SymbolInfoInteger(InpBrokerSymbol,SYMBOL_DIGITS);
   if(tick<=0) return NormalizeDouble(p,digits);
   return NormalizeDouble(MathRound(p/tick)*tick,digits);
}
double MinStopDistance()
{
   double pt=SymbolInfoDouble(InpBrokerSymbol,SYMBOL_POINT);
   long st=SymbolInfoInteger(InpBrokerSymbol,SYMBOL_TRADE_STOPS_LEVEL);
   long fr=SymbolInfoInteger(InpBrokerSymbol,SYMBOL_TRADE_FREEZE_LEVEL);
   return MathMax((double)st,(double)fr)*pt;
}
double RiskLots(const int side,const double entry,const double sl,const double riskPct)
{
   ENUM_ORDER_TYPE type=(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);
   double pnl=0.0;
   if(!OrderCalcProfit(type,InpBrokerSymbol,1.0,entry,sl,pnl)) return 0.0;
   double loss=MathAbs(pnl); if(loss<=0) return 0.0;
   double money=AccountInfoDouble(ACCOUNT_EQUITY)*riskPct/100.0;
   double lots=NormVolume(money/loss);
   if(InpMaxVolumeLots>0) lots=NormVolume(MathMin(lots,InpMaxVolumeLots));
   return lots;
}
double MarginSafeLots(const int side,const double entry,const double requested)
{
   double lot=NormVolume(requested); if(lot<=0) return 0.0;
   ENUM_ORDER_TYPE type=(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);
   double free=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double budget=free*InpMaxMarginUsePct/100.0;
   double mn=SymbolInfoDouble(InpBrokerSymbol,SYMBOL_VOLUME_MIN);
   double st=SymbolInfoDouble(InpBrokerSymbol,SYMBOL_VOLUME_STEP);
   if(st<=0) st=mn;
   while(lot>=mn && lot>0)
   {
      double m=0.0;
      if(OrderCalcMargin(type,InpBrokerSymbol,lot,entry,m) && m<=budget) return lot;
      lot=NormVolume(lot-st);
   }
   return 0.0;
}
int MyPositionCount()
{
   int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      long mg=PositionGetInteger(POSITION_MAGIC);
      if(PositionGetString(POSITION_SYMBOL)==InpBrokerSymbol && mg>=InpMagicBase+1 && mg<=InpMagicBase+4) n++;
   }
   return n;
}
bool FirstMyPosition(ulong &ticket,int &side,double &mtmR,double &riskDist)
{
   ticket=0;side=0;mtmR=0;riskDist=0;
   datetime earliest=D'2099.12.31';
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      long mg=PositionGetInteger(POSITION_MAGIC);
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || mg<InpMagicBase+1 || mg>InpMagicBase+4) continue;
      datetime ot=(datetime)PositionGetInteger(POSITION_TIME);
      if(ot>=earliest) continue;
      earliest=ot;ticket=tk;
   }
   if(ticket==0 || !PositionSelectByTicket(ticket)) return false;
   long tp=PositionGetInteger(POSITION_TYPE); side=(tp==POSITION_TYPE_BUY?1:-1);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   string key=StringFormat("CF157_RISK_%I64u",ticket);
   if(GlobalVariableCheck(key)) riskDist=GlobalVariableGet(key);
   if(riskDist<=0)
   {
      double sl=PositionGetDouble(POSITION_SL);
      riskDist=MathAbs(open-sl);
   }
   MqlTick q;if(!SymbolInfoTick(InpBrokerSymbol,q) || riskDist<=0) return false;
   double px=(side>0?q.bid:q.ask);
   mtmR=side*(px-open)/riskDist;
   return true;
}
void SavePositionState(const ulong tk,const double risk,const double initVol,const int engine)
{
   GlobalVariableSet(StringFormat("CF157_RISK_%I64u",tk),risk);
   GlobalVariableSet(StringFormat("CF157_VOL_%I64u",tk),initVol);
   GlobalVariableSet(StringFormat("CF157_PART_%I64u",tk),0.0);
   GlobalVariableSet(StringFormat("CF157_ENG_%I64u",tk),(double)engine);
}
double GV(const string k,const double d=0.0){return GlobalVariableCheck(k)?GlobalVariableGet(k):d;}
void SetGV(const string k,const double v){GlobalVariableSet(k,v);}

void AppendLog(const string event,const int engine,const int side,const string detail)
{
   int h=FileOpen(InpLogFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE) return;
   if(FileSize(h)==0) FileWrite(h,"time","event","engine","side","z","atr","oi4h","phase","detail");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),event,EngineName(engine),
             side>0?"BUY":(side<0?"SELL":"-"),DoubleToString(g_panelZ,4),DoubleToString(g_panelATR,2),
             DoubleToString(g_panelOI4h*100.0,3),g_panelPhase,detail);
   FileClose(h);
}

//---------------- Position execution / management -------------------
bool MoveStopToR(const ulong tk,const double targetR)
{
   if(!PositionSelectByTicket(tk)) return false;
   long type=PositionGetInteger(POSITION_TYPE);
   int side=(type==POSITION_TYPE_BUY?1:-1);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double current=PositionGetDouble(POSITION_SL);
   double tp=PositionGetDouble(POSITION_TP);
   double risk=GV(StringFormat("CF157_RISK_%I64u",tk),0.0);
   if(risk<=0) return false;
   double desired=NormalizePriceToTick(open+side*targetR*risk);
   if(current>0)
   {
      if(side>0 && desired<=current) return true;
      if(side<0 && desired>=current) return true;
   }
   MqlTick q;if(!SymbolInfoTick(InpBrokerSymbol,q)) return false;
   double dist=MinStopDistance()+SymbolInfoDouble(InpBrokerSymbol,SYMBOL_POINT);
   if(side>0 && desired>q.bid-dist) desired=NormalizePriceToTick(q.bid-dist);
   if(side<0 && desired<q.ask+dist) desired=NormalizePriceToTick(q.ask+dist);
   if((side>0 && desired<=open-risk) || (side<0 && desired>=open+risk)) return false;
   trade.SetExpertMagicNumber(PositionGetInteger(POSITION_MAGIC));
   bool ok=trade.PositionModify(tk,desired,tp);
   if(!ok) PrintFormat("CF157 SL MODIFY FAIL tk=%I64u ret=%u %s",tk,trade.ResultRetcode(),trade.ResultRetcodeDescription());
   return ok;
}

bool OpenTrade(const SignalCandidate &s)
{
   int count=MyPositionCount();
   if(count>=InpMaxPositions){AppendLog("REJECT_MAXPOS",s.engine,s.side,s.detail);return false;}

   bool isAddon=false;
   ulong first=0;int firstSide=0;double firstR=0,firstRisk=0;
   if(count==1)
   {
      if(!FirstMyPosition(first,firstSide,firstR,firstRisk)) return false;
      if(firstSide!=s.side || firstR<0.0)
      {
         AppendLog("REJECT_ADDON",s.engine,s.side,StringFormat("same=%s firstMTM=%.3fR | %s",firstSide==s.side?"Y":"N",firstR,s.detail));
         return false;
      }
      isAddon=true;
   }

   MqlTick q;if(!SymbolInfoTick(InpBrokerSymbol,q)) return false;
   double entry=(s.side>0?q.ask:q.bid);
   double dist=InpStopH1ATR*s.atr;
   double minDist=MinStopDistance()+SymbolInfoDouble(InpBrokerSymbol,SYMBOL_POINT);
   if(dist<minDist) dist=minDist;
   if(InpMaxSpreadATR>0 && (q.ask-q.bid)>InpMaxSpreadATR*s.atr)
   {
      AppendLog("REJECT_SPREAD",s.engine,s.side,s.detail); return false;
   }
   double sl=NormalizePriceToTick(entry-s.side*dist);
   double lots=MarginSafeLots(s.side,entry,RiskLots(s.side,entry,sl,InpRiskPct));
   if(lots<=0){AppendLog("REJECT_SIZE",s.engine,s.side,s.detail);return false;}

   if(InpDryRun)
   {
      PrintFormat("CF157 DRY %s %s lot=%.4f entry=%.2f sl=%.2f %s",EngineName(s.engine),s.side>0?"BUY":"SELL",lots,entry,sl,s.detail);
      AppendLog("DRY_ENTRY",s.engine,s.side,s.detail);return true;
   }

   trade.SetExpertMagicNumber(EngineMagic(s.engine));
   trade.SetDeviationInPoints(InpSlippagePts);
   string comment="CF157_"+EngineName(s.engine);
   bool ok=(s.side>0 ? trade.Buy(lots,InpBrokerSymbol,0.0,sl,0.0,comment)
                     : trade.Sell(lots,InpBrokerSymbol,0.0,sl,0.0,comment));
   if(!ok)
   {
      PrintFormat("CF157 ENTRY FAIL %s ret=%u %s",EngineName(s.engine),trade.ResultRetcode(),trade.ResultRetcodeDescription());
      AppendLog("ENTRY_FAIL",s.engine,s.side,s.detail); return false;
   }

   // find newest matching position
   ulong newTk=0;datetime newest=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i);if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || PositionGetInteger(POSITION_MAGIC)!=EngineMagic(s.engine)) continue;
      datetime ot=(datetime)PositionGetInteger(POSITION_TIME);
      if(ot>=newest){newest=ot;newTk=tk;}
   }
   if(newTk>0) SavePositionState(newTk,dist,lots,s.engine);

   if(isAddon && first>0)
      MoveStopToR(first,InpAddonFirstLockR);

   g_lastSignal=EngineName(s.engine)+" "+(s.side>0?"BUY":"SELL");
   AppendLog(isAddon?"ADDON_ENTRY":"ENTRY",s.engine,s.side,s.detail);
   return true;
}

void ManagePositions()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      long magic=PositionGetInteger(POSITION_MAGIC);
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || magic<InpMagicBase+1 || magic>InpMagicBase+4) continue;

      long type=PositionGetInteger(POSITION_TYPE); int side=(type==POSITION_TYPE_BUY?1:-1);
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double vol=PositionGetDouble(POSITION_VOLUME);
      double risk=GV(StringFormat("CF157_RISK_%I64u",tk),0.0);
      double initVol=GV(StringFormat("CF157_VOL_%I64u",tk),vol);
      bool partial=(GV(StringFormat("CF157_PART_%I64u",tk),0.0)>0.5);
      if(risk<=0 || open<=0 || vol<=0) continue;

      MqlTick q;if(!SymbolInfoTick(InpBrokerSymbol,q)) continue;
      double favorable=side*((side>0?q.bid:q.ask)-open);

      if(!partial && favorable>=InpPartialAtR*risk)
      {
         double closeVol=NormVolume(initVol*InpPartialFraction);
         double minVol=SymbolInfoDouble(InpBrokerSymbol,SYMBOL_VOLUME_MIN);
         if(closeVol>0 && vol-closeVol>=minVol-1e-9)
         {
            trade.SetExpertMagicNumber(magic);
            if(trade.PositionClosePartial(tk,closeVol))
            {
               SetGV(StringFormat("CF157_PART_%I64u",tk),1.0);
               MoveStopToR(tk,InpRunnerLockR);
               AppendLog("PARTIAL_TP3",(int)(magic-InpMagicBase),side,StringFormat("close=%.4f remain=%.4f lock=%.2fR",closeVol,vol-closeVol,InpRunnerLockR));
            }
            else PrintFormat("CF157 PARTIAL FAIL tk=%I64u ret=%u %s",tk,trade.ResultRetcode(),trade.ResultRetcodeDescription());
         }
         else
         {
            // If half cannot be represented, close full at +3R rather than create an uncontrolled runner.
            trade.SetExpertMagicNumber(magic);
            if(trade.PositionClose(tk))
               AppendLog("FULL_TP3_GRANULARITY",(int)(magic-InpMagicBase),side,"partial volume impossible");
         }
      }

      datetime ot=(datetime)PositionGetInteger(POSITION_TIME);
      if(InpMaxHoldHours>0 && TimeCurrent()-ot>=InpMaxHoldHours*3600)
      {
         trade.SetExpertMagicNumber(magic);
         if(trade.PositionClose(tk))
            AppendLog("TIME_EXIT",(int)(magic-InpMagicBase),side,StringFormat("%dh max hold",InpMaxHoldHours));
      }
   }
}

//---------------- Signal state machines ------------------------------
void ResetA(){g_aArmed=false;g_aEngine=0;g_aSide=0;g_aAnchorMs=0;g_aAnchorIndex=-1;}
void ArmA(const int engine,const int side,const int idx,const double atr,const double z,const double ext,const double oi4h)
{
   g_aArmed=true;g_aEngine=engine;g_aSide=side;g_aAnchorIndex=idx;g_aAnchorMs=g_m5[idx].ms;
   g_aATR=atr;g_aZ=z;g_aExt=ext;g_aOI4h=oi4h;
   if(InpVerbose) PrintFormat("CF157 ARM %s %s idx=%d Z=%.3f ATR=%.2f ext=%.3f oi4h=%.3f%%",
                             EngineName(engine),side>0?"BUY":"SELL",idx,z,atr,ext,oi4h*100.0);
}
bool CheckSwing3(const int idx,SignalCandidate &out)
{
   out.valid=false;
   if(!g_aArmed) return false;
   if(idx<=g_aAnchorIndex) return false;
   if(idx-g_aAnchorIndex>InpSwingSearchBars){ResetA();return false;}
   int lo=MathMax(g_aAnchorIndex,idx-3);
   double ref=(g_aSide>0?-DBL_MAX:DBL_MAX);
   if(g_aSide>0)
   {
      for(int j=lo;j<idx;j++) ref=MathMax(ref,g_m5[j].h);
      if(g_m5[idx].c<=ref) return false;
   }
   else
   {
      for(int j=lo;j<idx;j++) ref=MathMin(ref,g_m5[j].l);
      if(g_m5[idx].c>=ref) return false;
   }
   out.valid=true;out.engine=g_aEngine;out.side=g_aSide;out.atr=g_aATR;out.z=g_aZ;out.ext=g_aExt;out.oi4h=g_aOI4h;
   out.detail=StringFormat("SWING3 ref=%.2f close=%.2f anchor=%s",ref,g_m5[idx].c,TimeToString((datetime)(g_aAnchorMs/1000),TIME_DATE|TIME_MINUTES));
   ResetA();
   return true;
}

void StartB3(const int idx,const int trend,const int crowdDir,const double z,const double oi,const double atr)
{
   g_b3Active=true;g_b3Trend=trend;g_b3CrowdDir=crowdDir;g_b3StartIndex=idx;g_b3StartMs=g_m5[idx].ms;
   g_b3Anchor=g_m5[idx].c;g_b3ATR=atr;g_b3Z0=z;g_b3OI0=oi;g_b3DepthQualified=false;g_b3DepthHitIndex=-1;
   for(int k=0;k<5;k++){g_b3HitIndex[k]=-1;g_b3Level[k]=g_b3Anchor-trend*(0.1*(k+1))*atr;}
}
void ResetB3(){g_b3Active=false;g_b3DepthQualified=false;g_b3DepthHitIndex=-1;for(int k=0;k<5;k++)g_b3HitIndex[k]=-1;}

bool ProcessB3(const int idx,const double z,SignalCandidate &out)
{
   out.valid=false;if(!g_b3Active) return false;
   if(!g_b3DepthQualified && idx-g_b3StartIndex>InpB3AttackMaxBars){ResetB3();return false;}
   if(g_b3DepthQualified && idx-g_b3DepthHitIndex>InpB3ReclaimMaxBars){ResetB3();return false;}

   // Record first touch of each 0.1 ATR milestone. Multiple levels may be hit in one M5 bar.
   for(int k=0;k<5;k++)
   {
      if(g_b3HitIndex[k]>=0) continue;
      bool touched=(g_b3Trend>0 ? g_m5[idx].l<=g_b3Level[k] : g_m5[idx].h>=g_b3Level[k]);
      if(touched) g_b3HitIndex[k]=idx; else break;
   }

   if(!g_b3DepthQualified && g_b3HitIndex[4]>=0)
   {
      double oi=OIAtOrBefore(g_m5[idx].ms);
      int sign=(z>0?1:-1);
      double zStrength=(sign==g_b3CrowdDir ? MathAbs(z)-MathAbs(g_b3Z0) : -MathAbs(g_b3Z0));
      bool oiUp=(oi>g_b3OI0);
      int d03=g_b3HitIndex[2]-g_b3HitIndex[1];
      int d04=g_b3HitIndex[3]-g_b3HitIndex[2];
      int d05=g_b3HitIndex[4]-g_b3HitIndex[3];
      if(zStrength>=InpB3ZStrengthMin && oiUp && d04>d03 && d05>d04)
      {
         g_b3DepthQualified=true;g_b3DepthHitIndex=g_b3HitIndex[4];
         if(InpVerbose) PrintFormat("CF157 B3 QUALIFIED d03=%d d04=%d d05=%d zStr=%.3f oiUp=%s",d03,d04,d05,zStrength,oiUp?"Y":"N");
      }
      else
      {
         ResetB3(); return false;
      }
   }

   if(g_b3DepthQualified)
   {
      double reclaimLevel=g_b3Level[3]; // previous 0.4 ATR milestone
      bool reclaim=(g_b3Trend>0 ? g_m5[idx].c>reclaimLevel : g_m5[idx].c<reclaimLevel);
      if(reclaim)
      {
         H1Ctx h1; if(!BuildH1(idx,h1)){ResetB3();return false;}
         out.valid=true;out.engine=ENG_B3;out.side=g_b3Trend;out.atr=h1.atr;out.z=z;out.ext=h1.extension;out.oi4h=OIChange4h(g_m5[idx].ms);
         out.detail=StringFormat("B3 reclaim %.2f d=[%d,%d,%d,%d,%d]",reclaimLevel,
             g_b3HitIndex[0]-g_b3StartIndex,g_b3HitIndex[1]-g_b3HitIndex[0],g_b3HitIndex[2]-g_b3HitIndex[1],
             g_b3HitIndex[3]-g_b3HitIndex[2],g_b3HitIndex[4]-g_b3HitIndex[3]);
         ResetB3(); return true;
      }
   }
   return false;
}

void AddR48Pending(const int idx,const int side,const double boundary,const double atr,const double oi)
{
   for(int k=0;k<MAX_R48_PENDING;k++)
   {
      if(!g_r48[k].active)
      {
         g_r48[k].active=true;g_r48[k].side=side;g_r48[k].signalIndex=idx;g_r48[k].signalMs=g_m5[idx].ms;
         g_r48[k].boundary=boundary;g_r48[k].atr=atr;g_r48[k].oi0=oi;return;
      }
   }
}
void DetectR48Breakout(const int idx,const double atr)
{
   if(idx<InpR48LookbackBars) return;
   // Frozen LAB136 R48 event spacing: at least 24 M5 bars between raw breakout events.
   if(idx-g_lastR48SignalIndex<24) return;
   double hi=-DBL_MAX,lo=DBL_MAX;
   for(int j=idx-InpR48LookbackBars;j<idx;j++){hi=MathMax(hi,g_m5[j].h);lo=MathMin(lo,g_m5[j].l);}
   double oi=OIAtOrBefore(g_m5[idx].ms); if(oi<=0) return;
   bool fired=false;
   if(g_m5[idx].c>hi){ AddR48Pending(idx,+1,hi,atr,oi); fired=true; }
   if(g_m5[idx].c<lo){ AddR48Pending(idx,-1,lo,atr,oi); fired=true; }
   if(fired) g_lastR48SignalIndex=idx;
}
bool ProcessR48(const int idx,SignalCandidate &out)
{
   out.valid=false;
   for(int k=0;k<MAX_R48_PENDING;k++)
   {
      if(!g_r48[k].active) continue;
      int age=idx-g_r48[k].signalIndex;
      if(age<InpR48AcceptanceBars) continue;
      if(age>InpR48AcceptanceBars+2){g_r48[k].active=false;continue;}

      int outside=0;bool retest=false;double sumMargin=0.0;
      for(int q=1;q<=InpR48AcceptanceBars;q++)
      {
         int j=g_r48[k].signalIndex+q;
         if(j>idx) break;
         if(g_r48[k].side>0)
         {
            if(g_m5[j].c>g_r48[k].boundary) outside++;
            if(g_m5[j].l<=g_r48[k].boundary) retest=true;
            sumMargin+=(g_m5[j].c-g_r48[k].boundary)/g_r48[k].atr;
         }
         else
         {
            if(g_m5[j].c<g_r48[k].boundary) outside++;
            if(g_m5[j].h>=g_r48[k].boundary) retest=true;
            sumMargin+=(g_r48[k].boundary-g_m5[j].c)/g_r48[k].atr;
         }
      }
      double meanMargin=sumMargin/InpR48AcceptanceBars;
      double oiNow=OIAtOrBefore(g_m5[idx].ms);
      double oiCh=(g_r48[k].oi0>0 && oiNow>0 ? oiNow/g_r48[k].oi0-1.0 : -999.0);
      bool pass=(outside>=InpR48MinOutside && !retest && meanMargin>=InpR48MeanMarginATR && oiCh>=InpR48OIChangeMin);
      if(pass)
      {
         out.valid=true;out.engine=ENG_R48;out.side=g_r48[k].side;out.atr=g_r48[k].atr;out.z=g_panelZ;
         H1Ctx h1;H4Ctx h4;double dummy=0;string why="";
         if(BuildH1(idx,h1)) out.ext=h1.extension; else out.ext=0;
         out.oi4h=OIChange4h(g_m5[idx].ms);
         out.detail=StringFormat("R48 boundary=%.2f outside=%d/6 mean=%.3fATR OIch=%.3f%%",g_r48[k].boundary,outside,meanMargin,oiCh*100.0);
         g_r48[k].active=false; return true;
      }
      g_r48[k].active=false;
   }
   return false;
}

bool FreshExtreme(const double z)
{
   if(!g_havePrevZ) return false;
   return (MathAbs(z)>=InpExtremeZ && MathAbs(g_prevZ)<InpExtremeZ);
}

void ProcessNewCompletedBar(const int idx,const double z,const long ratioTs)
{
   if(idx<0) return;
   H1Ctx h1;H4Ctx h4;
   bool h1ok=BuildH1(idx,h1),h4ok=BuildH4(idx,h4);
   double oi4h=OIChange4h(g_m5[idx].ms);
   if(h1ok){g_panelATR=h1.atr;}
   if(h4ok){g_panelPhase=h4.phase;}
   if(oi4h!=EMPTY_VALUE) g_panelOI4h=oi4h;
   g_panelZ=z;

   SignalCandidate ca,cb,cr,ce;
   ca.valid=false;cb.valid=false;cr.valid=false;ce.valid=false;

   // Existing pending states first. Priority at execution stage will be A > B3 > R48 > EARLY.
   CheckSwing3(idx,ca);
   ProcessB3(idx,z,cb);
   if(InpR48Mode>0) ProcessR48(idx,cr);
   if(cr.valid && InpR48Mode==1)
   {
      AppendLog("SHADOW_R48",ENG_R48,cr.side,cr.detail);   // тінь: лише лог
      cr.valid=false;
   }

   bool fresh=FreshExtreme(z);
   int sign=(z>0?1:-1);
   int side=-sign;

   if(MathAbs(z)<InpExtremeZ)
   {
      g_episodeActive=false;g_episodeSign=0;g_episodeStartMs=0;g_rescueWatch=false;
   }
   else
   {
      if(!g_episodeActive || sign!=g_episodeSign)
      {
         g_episodeActive=true;g_episodeSign=sign;g_episodeStartMs=g_m5[idx].ms;
      }
   }

   if(fresh && h1ok && h4ok)
   {
      string why="";double xoi=0;H1Ctx ah1;H4Ctx ah4;
      bool aok=ContextAOK(idx,side,ah1,ah4,xoi,why);
      if(aok)
      {
         ArmA(ENG_A,side,idx,ah1.atr,z,ah1.extension,xoi);
         g_rescueWatch=false;
      }
      else
      {
         g_rescueWatch=true;g_rescueSide=side;g_rescueSign=sign;g_rescueStartMs=g_m5[idx].ms;
         if(InpVerbose) Print("CF157 A fresh not valid -> rescue watch: ",why);
      }

      // B3 starts only if established H4 trend and crowd direction attacks countertrend.
      int crowdDir=sign;
      if(h4.trend!=0 && h4.trend_age>=InpB3MinTrendAgeH4 && crowdDir==-h4.trend)
      {
         double oi=OIAtOrBefore(g_m5[idx].ms);
         if(oi>0 && h1.atr>0) StartB3(idx,h4.trend,crowdDir,z,oi,h1.atr);
      }
   }

   // EARLY_EPISODE: first later bar within <=5m where canonical A context becomes valid.
   if(!InpEarlyEnable) g_rescueWatch=false;   // v003: EARLY off
   if(g_rescueWatch && g_m5[idx].ms>g_rescueStartMs)
   {
      double ageMin=(double)(g_m5[idx].ms-g_rescueStartMs)/60000.0;
      if(ageMin>InpEarlyMaxMinutes) g_rescueWatch=false;
      else if(MathAbs(z)>=InpExtremeZ && sign==g_rescueSign)
      {
         string why="";double xoi=0;H1Ctx eh1;H4Ctx eh4;
         if(ContextAOK(idx,g_rescueSide,eh1,eh4,xoi,why))
         {
            ArmA(ENG_EARLY,g_rescueSide,idx,eh1.atr,z,eh1.extension,xoi);
            g_rescueWatch=false;
         }
      }
   }

   // Detect new R48 breakout after processing any mature pending R48.
   if(h1ok && InpR48Mode>0) DetectR48Breakout(idx,h1.atr);

   // Execute at most one new signal on this cycle in frozen priority.
   // If A/EARLY trigger was armed on this same bar, SWING3 cannot occur until a later bar.
   if(ca.valid) OpenTrade(ca);
   else if(cb.valid) OpenTrade(cb);
   else if(cr.valid) OpenTrade(cr);
   else if(ce.valid) OpenTrade(ce);

   g_prevZ=z;g_havePrevZ=true;g_lastRatioTs=ratioTs;
}

void WarmStart()
{
   double z=0;long ts=0;
   if(FetchLatestZ(z,ts))
   {
      g_prevZ=z;g_lastZ=z;g_havePrevZ=true;g_lastRatioTs=ts;g_panelZ=z;
      if(MathAbs(z)>=InpExtremeZ)
      {
         g_episodeActive=true;g_episodeSign=(z>0?1:-1);g_state="WARM EXTREME SKIPPED";
      }
      else g_state="READY";
   }
}

//---------------- Engine D (LAB254/256) -------------------------------
long DMagic(){ return InpMagicBase + ENG_D; }

int M5IndexAtOrBefore(const long ms)
{
   for(int i=ArraySize(g_m5)-1;i>=0;i--)
      if(g_m5[i].ms<=ms) return i;
   return -1;
}

int DPosCount()
{
   int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)==InpBrokerSymbol && PositionGetInteger(POSITION_MAGIC)==DMagic()) n++;
   }
   return n;
}

// MTM in R of the oldest open D position (for the same-side add-on rule)
bool DFirstPos(int &side,double &mtmR)
{
   side=0; mtmR=0.0;
   ulong best=0; datetime earliest=D'2099.12.31';
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || PositionGetInteger(POSITION_MAGIC)!=DMagic()) continue;
      datetime ot=(datetime)PositionGetInteger(POSITION_TIME);
      if(ot<earliest){earliest=ot;best=tk;}
   }
   if(best==0 || !PositionSelectByTicket(best)) return false;
   side=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double risk=GV(StringFormat("CF157_RISK_%I64u",best),0.0);
   if(risk<=0) risk=MathAbs(open-PositionGetDouble(POSITION_SL));
   MqlTick q; if(risk<=0 || !SymbolInfoTick(InpBrokerSymbol,q)) return false;
   mtmR=side*((side>0?q.bid:q.ask)-open)/risk;
   return true;
}

bool OpenTradeD(const int side,const double atr,const string detail)
{
   int n=DPosCount();
   if(n>=InpD_MaxPositions){AppendLog("D_REJECT_MAXPOS",ENG_D,side,detail);return false;}
   if(n>=1)
   {
      int fs=0; double fr=0.0;
      if(!DFirstPos(fs,fr)) return false;
      if(fs!=side || fr<0.0)
      {
         AppendLog("D_REJECT_ADDON",ENG_D,side,StringFormat("same=%s firstMTM=%.3fR | %s",fs==side?"Y":"N",fr,detail));
         return false;
      }
   }
   MqlTick q; if(!SymbolInfoTick(InpBrokerSymbol,q)) return false;
   double entry=(side>0?q.ask:q.bid);
   double dist=InpD_StopATR*atr;
   double minDist=MinStopDistance()+SymbolInfoDouble(InpBrokerSymbol,SYMBOL_POINT);
   if(dist<minDist) dist=minDist;
   if(InpMaxSpreadATR>0 && (q.ask-q.bid)>InpMaxSpreadATR*atr){AppendLog("D_REJECT_SPREAD",ENG_D,side,detail);return false;}
   double sl=NormalizePriceToTick(entry-side*dist);
   double lots=MarginSafeLots(side,entry,RiskLots(side,entry,sl,InpD_RiskPct));
   if(lots<=0){AppendLog("D_REJECT_SIZE",ENG_D,side,detail);return false;}

   if(InpDryRun)
   {
      PrintFormat("CF157 DRY D %s lot=%.4f entry=%.2f sl=%.2f %s",side>0?"BUY":"SELL",lots,entry,sl,detail);
      AppendLog("D_DRY_ENTRY",ENG_D,side,detail); return true;
   }
   trade.SetExpertMagicNumber(DMagic());
   trade.SetDeviationInPoints(InpSlippagePts);
   bool ok;
   if(side>0) ok=trade.Buy(lots,InpBrokerSymbol,0.0,sl,0.0,"CF157_D");
   else       ok=trade.Sell(lots,InpBrokerSymbol,0.0,sl,0.0,"CF157_D");
   if(!ok)
   {
      PrintFormat("CF157 D ENTRY FAIL ret=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());
      AppendLog("D_ENTRY_FAIL",ENG_D,side,detail); return false;
   }
   ulong newTk=0; datetime newest=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || PositionGetInteger(POSITION_MAGIC)!=DMagic()) continue;
      datetime ot=(datetime)PositionGetInteger(POSITION_TIME);
      if(ot>=newest){newest=ot;newTk=tk;}
   }
   if(newTk>0)
   {
      SavePositionState(newTk,dist,lots,ENG_D);
      SetGV(StringFormat("CF157_DPK_%I64u",newTk),0.0);
   }
   g_lastSignal="D "+(side>0?"BUY":"SELL");
   AppendLog(n>=1?"D_ADDON_ENTRY":"D_ENTRY",ENG_D,side,detail);
   return true;
}

// Trail: stop = peak - TrailDistR once peak >= TrailStartR; time exit after InpD_MaxHoldHours.
void ManageD()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || PositionGetInteger(POSITION_MAGIC)!=DMagic()) continue;
      int side=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double risk=GV(StringFormat("CF157_RISK_%I64u",tk),0.0);
      if(risk<=0 || open<=0) continue;
      datetime ot=(datetime)PositionGetInteger(POSITION_TIME);
      if(InpD_MaxHoldHours>0 && TimeCurrent()-ot>=InpD_MaxHoldHours*3600)
      {
         trade.SetExpertMagicNumber(DMagic());
         if(trade.PositionClose(tk)) AppendLog("D_TIME_EXIT",ENG_D,side,StringFormat("%dh max hold",InpD_MaxHoldHours));
         continue;
      }
      MqlTick q; if(!SymbolInfoTick(InpBrokerSymbol,q)) continue;
      double r=side*((side>0?q.bid:q.ask)-open)/risk;
      string pk=StringFormat("CF157_DPK_%I64u",tk);
      double peak=MathMax(GV(pk,0.0),r);
      if(peak>GV(pk,0.0)) SetGV(pk,peak);
      if(peak>=InpD_TrailStartR)
      {
         double target=peak-InpD_TrailDistR;
         if(target>-1.0+1e-6) MoveStopToR(tk,target);
      }
   }
}

// LAB268: exit D when the crowd compass turns AGAINST the position (transition), only if open MTM >= MinR.
int g_dPrevCmp=0;
void DCrowdExit(const int cmp,const int prevCmp,const string det)
{
   if(InpD_CrowdExitMode<=0) return;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || PositionGetInteger(POSITION_MAGIC)!=DMagic()) continue;
      int side=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);
      if(!(cmp==-side && prevCmp!=-side)) continue;
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double risk=GV(StringFormat("CF157_RISK_%I64u",tk),0.0);
      MqlTick q; if(risk<=0 || !SymbolInfoTick(InpBrokerSymbol,q)) continue;
      double r=side*((side>0?q.bid:q.ask)-open)/risk;
      if(r<InpD_CrowdExitMinR) continue;
      string why=StringFormat("compass turned against, MTM=%.2fR | %s",r,det);
      if(InpD_CrowdExitMode==1){AppendLog("D_SHADOW_CROWD_EXIT",ENG_D,side,why);continue;}
      trade.SetExpertMagicNumber(DMagic());
      if(trade.PositionClose(tk)) AppendLog("D_CROWD_EXIT",ENG_D,side,why);
      else PrintFormat("CF157 D CROWD EXIT FAIL tk=%I64u ret=%u %s",tk,trade.ResultRetcode(),trade.ResultRetcodeDescription());
   }
}

//---------------- Engine L: liquidation cascade (LAB271/272) ----------
// State: |z6|>=1 and z24 same sign |z24|>=Z24Min; side = against crowd. One entry per state episode.
// Trigger at M5 close: coin OI over last N bars dropped >= X% AND price moved >= Y H1ATR in trade side.
#define ENG_L 30
long LMagic(){ return InpMagicBase + ENG_L; }
int  g_lSide=0; bool g_lUsed=false; string g_lPanel="-";
struct LVirt { bool on; int side; double e,R,stp,pk; datetime t0; double spreadR; };
LVirt g_lv;

int LPosCount()
{
   int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)==InpBrokerSymbol && PositionGetInteger(POSITION_MAGIC)==LMagic()) n++;
   }
   return n;
}

bool OpenTradeL(const int side,const double atr,const string detail)
{
   MqlTick q; if(!SymbolInfoTick(InpBrokerSymbol,q)) return false;
   double entry=(side>0?q.ask:q.bid);
   double dist=InpL_StopATR*atr;
   double minDist=MinStopDistance()+SymbolInfoDouble(InpBrokerSymbol,SYMBOL_POINT);
   if(dist<minDist) dist=minDist;
   if(InpL_Mode==1 || InpDryRun)
   {
      if(g_lv.on){AppendLog("L_SHADOW_SKIP_BUSY",ENG_L,side,detail);return false;}
      g_lv.on=true; g_lv.side=side; g_lv.e=entry; g_lv.R=dist; g_lv.stp=entry-side*dist; g_lv.pk=0; g_lv.t0=TimeCurrent();
      g_lv.spreadR=(q.ask-q.bid)/dist;
      AppendLog("L_SHADOW_ENTRY",ENG_L,side,StringFormat("entry=%.2f R=%.2f | %s",entry,dist,detail));
      return true;
   }
   if(LPosCount()>=1){AppendLog("L_REJECT_BUSY",ENG_L,side,detail);return false;}
   double sl=NormalizePriceToTick(entry-side*dist);
   double lots=MarginSafeLots(side,entry,RiskLots(side,entry,sl,InpL_RiskPct));
   if(lots<=0){AppendLog("L_REJECT_SIZE",ENG_L,side,detail);return false;}
   trade.SetExpertMagicNumber(LMagic());
   trade.SetDeviationInPoints(InpSlippagePts);
   bool ok;
   if(side>0) ok=trade.Buy(lots,InpBrokerSymbol,0.0,sl,0.0,"CF157_L");
   else       ok=trade.Sell(lots,InpBrokerSymbol,0.0,sl,0.0,"CF157_L");
   if(!ok){PrintFormat("CF157 L ENTRY FAIL ret=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());AppendLog("L_ENTRY_FAIL",ENG_L,side,detail);return false;}
   ulong newTk=0; datetime newest=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || PositionGetInteger(POSITION_MAGIC)!=LMagic()) continue;
      datetime ot=(datetime)PositionGetInteger(POSITION_TIME); if(ot>=newest){newest=ot;newTk=tk;}
   }
   if(newTk>0){SavePositionState(newTk,dist,lots,ENG_L);SetGV(StringFormat("CF157_LPK_%I64u",newTk),0.0);}
   g_lastSignal="L "+(side>0?"BUY":"SELL");
   AppendLog("L_ENTRY",ENG_L,side,detail);
   return true;
}

// Real positions: trail stop = peak - DistR after peak >= StartR; time exit. Virtual position: same rules on bid/ask.
void ManageL()
{
   MqlTick q; if(!SymbolInfoTick(InpBrokerSymbol,q)) return;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || PositionGetInteger(POSITION_MAGIC)!=LMagic()) continue;
      int side=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double risk=GV(StringFormat("CF157_RISK_%I64u",tk),0.0); if(risk<=0) continue;
      datetime ot=(datetime)PositionGetInteger(POSITION_TIME);
      if(TimeCurrent()-ot>=InpL_MaxHoldHours*3600)
      {
         trade.SetExpertMagicNumber(LMagic());
         if(trade.PositionClose(tk)) AppendLog("L_TIME_EXIT",ENG_L,side,StringFormat("%dh",InpL_MaxHoldHours));
         continue;
      }
      double r=side*((side>0?q.bid:q.ask)-open)/risk;
      string pk=StringFormat("CF157_LPK_%I64u",tk);
      double peak=MathMax(GV(pk,0.0),r); if(peak>GV(pk,0.0)) SetGV(pk,peak);
      if(peak>=InpL_TrailStartR && peak-InpL_TrailDistR>-1.0+1e-6) MoveStopToR(tk,peak-InpL_TrailDistR);
   }
   if(g_lv.on)
   {
      int sd=g_lv.side; double px=(sd>0?q.bid:q.ask);
      double r=sd*(px-g_lv.e)/g_lv.R;
      string why="";
      if((sd>0 && px<=g_lv.stp) || (sd<0 && px>=g_lv.stp)) why="stop";
      else if(TimeCurrent()-g_lv.t0>=InpL_MaxHoldHours*3600) why="time";
      if(why!="")
      {
         AppendLog("L_SHADOW_EXIT",ENG_L,sd,StringFormat("%s R=%.2f peak=%.2fR hold=%.1fh spreadR=%.3f",why,r,g_lv.pk,(double)(TimeCurrent()-g_lv.t0)/3600.0,g_lv.spreadR));
         g_lv.on=false; return;
      }
      g_lv.pk=MathMax(g_lv.pk,r);
      if(g_lv.pk>=InpL_TrailStartR)
      {
         double ns=g_lv.e+sd*(g_lv.pk-InpL_TrailDistR)*g_lv.R;
         if(sd>0) g_lv.stp=MathMax(g_lv.stp,ns); else g_lv.stp=MathMin(g_lv.stp,ns);
      }
   }
}

// Called for every new ratio point (bar bi) from ProcessEngineD. trading=false -> state warm-up only.
void EvalL(const double z6,const double z24,const int bi,const bool trading,const double ageMin,const string det)
{
   if(InpL_Mode<=0) return;
   int st=0;
   if(MathAbs(z6)>=1.0 && z24!=EMPTY_VALUE && (z24>0?1:-1)==(z6>0?1:-1) && MathAbs(z24)>=InpL_Z24Min) st=(z6>0?-1:1);
   if(st!=g_lSide){g_lSide=st;g_lUsed=false;}
   if(st==0 || g_lUsed || bi<InpL_OIBars) return;
   long ms=g_m5[bi].ms, ms0=g_m5[bi-InpL_OIBars].ms;
   double oi=OIAtOrBefore(ms), oi0=OIAtOrBefore(ms0);
   if(oi<=0 || oi0<=0) return;
   double oich=oi/oi0-1.0;
   H1Ctx h1; if(!BuildH1(bi,h1) || h1.atr<=0) return;
   double pmove=st*(g_m5[bi].c-g_m5[bi-InpL_OIBars].c)/h1.atr;
   g_lPanel=StringFormat("state %s OI%d %.2f%% px %.2fATR",st>0?"LONG":"SHORT",InpL_OIBars*5,oich*100.0,pmove);
   if(!(oich<=-InpL_OIDropPct/100.0 && pmove>=InpL_PriceATR)) return;
   g_lUsed=true;
   if(!trading) return;
   string d=StringFormat("OI%dm=%.2f%% px=%.2fATR age=%.1fmin | %s",InpL_OIBars*5,oich*100.0,pmove,ageMin,det);
   if(ageMin>InpD_MaxSignalAgeMin){AppendLog("L_SIGNAL_STALE",ENG_L,st,d);return;}
   OpenTradeL(st,h1.atr,d);
}

// Episode logic identical to research (dtune.build): episode = run of |z6|>=reset with one sign;
// signal when |z6| crosses x upward, z24 same sign & |z24|>=zmin, optional H4 trend == side.
// Trend failure does NOT consume the episode; a signal does.
int EvalDRule(const int v,const double z6,const double z6p,const double z24,const int h4trend,
              const double x,const double zmin,const bool useH4)
{
   if(MathAbs(z6)<InpD_EpisodeResetZ){g_dEp[v].sign=0;g_dEp[v].used=false;return 0;}
   int sg=(z6>0?1:-1);
   if(g_dEp[v].sign!=sg){g_dEp[v].sign=sg;g_dEp[v].used=false;}
   if(g_dEp[v].used) return 0;
   if(!(MathAbs(z6)>=x && MathAbs(z6p)<x)) return 0;
   if(z24==EMPTY_VALUE || (z24>0?1:-1)!=sg || MathAbs(z24)<zmin) return 0;
   int side=-sg;
   if(useH4 && h4trend!=side) return 0;
   g_dEp[v].used=true;
   return side;
}

// Process every new ratio point in order. trading=false -> warm-up (state only).
void ProcessEngineD(const bool trading)
{
   int n=ArraySize(g_ratio);
   if(n<InpD_Z24WindowBars+2) {g_dPanel="ratio history < 24h";return;}
   long now=(long)TimeGMT()*1000;
   for(int k=InpD_Z24WindowBars;k<n;k++)
   {
      long ts=g_ratioTs[k];
      if(ts<=g_lastDRatioTs) continue;
      if(ts+300000>now) break;                         // its M5 bar not closed yet
      int bi=M5IndexAtOrBefore(ts);
      if(bi<0 || g_m5[bi].ms+300000>now) break;
      double z6=ZAt(g_ratio,k,InpZWindowBars), z6p=ZAt(g_ratio,k-1,InpZWindowBars);
      double z24=ZAt(g_ratio,k,InpD_Z24WindowBars);
      g_lastDRatioTs=ts;
      if(z6==EMPTY_VALUE || z6p==EMPTY_VALUE) continue;
      H4Ctx h4; int tr=0; if(BuildH4(bi,h4)) tr=h4.trend;
      g_dPanel=StringFormat("z6 %.2f z24 %.2f H4 %d ep %s",z6,(z24==EMPTY_VALUE?0.0:z24),tr,g_dEp[0].used?"used":"open");

      int sLive=EvalDRule(0,z6,z6p,z24,tr,InpD_Z6Cross,InpD_Z24Min,InpD_UseH4);
      int sD   =EvalDRule(1,z6,z6p,z24,tr,2.0,1.0,true);
      int sDp  =EvalDRule(2,z6,z6p,z24,tr,2.0,1.0,false);
      int cmp=0;
      if(z24!=EMPTY_VALUE && MathAbs(z24)>=InpD_CrowdExitZ) cmp=(z24>0?-1:1);
      int prevCmp=g_dPrevCmp; g_dPrevCmp=cmp;
      double ageL=(double)(now-(ts+300000))/60000.0;
      if(!trading){EvalL(z6,z24,bi,false,ageL,"");continue;}

      string det=StringFormat("ratioTs=%s z6=%.3f z6prev=%.3f z24=%.3f H4=%d",
                 TimeToString((datetime)(ts/1000),TIME_DATE|TIME_MINUTES),z6,z6p,(z24==EMPTY_VALUE?0.0:z24),tr);
      DCrowdExit(cmp,prevCmp,det);
      EvalL(z6,z24,bi,true,ageL,det);
      if(InpD_ShadowLog)
      {
         if(sD!=0)  AppendLog("SHADOW_SIGNAL",11,sD,det);
         if(sDp!=0) AppendLog("SHADOW_SIGNAL",12,sDp,det+(tr==sDp?" H4=with":" H4=against/flat"));
      }
      if(sLive!=0 && InpDEnable)
      {
         double ageMin=(double)(now-(ts+300000))/60000.0;
         H1Ctx h1;
         if(ageMin>InpD_MaxSignalAgeMin) AppendLog("D_SIGNAL_STALE",ENG_D,sLive,StringFormat("age=%.1fmin | %s",ageMin,det));
         else if(!BuildH1(bi,h1)) AppendLog("D_REJECT_H1",ENG_D,sLive,det);
         else OpenTradeD(sLive,h1.atr,StringFormat("age=%.1fmin ATR=%.2f | %s",ageMin,h1.atr,det));
      }
   }
}

// First time each new ratio timestamp is seen -> publication latency.
long g_lastSeenRatioTs=0;
void LogLatency()
{
   int n=ArraySize(g_ratioTs); if(n==0) return;
   if(g_lastSeenRatioTs==0){g_lastSeenRatioTs=g_ratioTs[n-1];g_httpFails=0;g_skipPolls=0;return;}   // attach: not a measurement
   int k0=n;
   for(int k=n-1;k>=0 && g_ratioTs[k]>g_lastSeenRatioTs;k--) k0=k;
   if(k0>=n) return;
   int batch=n-k0;                                    // >1 = several new points arrived at once
   long now=(long)TimeGMT()*1000;
   int h=FileOpen(InpLatencyLogFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h!=INVALID_HANDLE)
   {
      if(FileSize(h)==0) FileWrite(h,"seen_gmt","ratio_ts_gmt","sec_after_ratio_ts","sec_after_ts_plus_5m","poll_sec","batch","http_fails","skipped_polls");
      FileSeek(h,0,SEEK_END);
      for(int k=k0;k<n;k++)
      {
         long ts=g_ratioTs[k];
         FileWrite(h,TimeToString((datetime)(now/1000),TIME_DATE|TIME_SECONDS),TimeToString((datetime)(ts/1000),TIME_DATE|TIME_SECONDS),
                   DoubleToString((now-ts)/1000.0,1),DoubleToString((now-ts-300000)/1000.0,1),IntegerToString(InpRefreshSec),
                   IntegerToString(batch),IntegerToString(g_httpFails),IntegerToString(g_skipPolls));
      }
      FileClose(h);
   }
   g_lastSeenRatioTs=g_ratioTs[n-1];
   g_httpFails=0; g_skipPolls=0;
}

//---------------- Engine S: Supertrend H2 + crowd compass -------------
// Research parity (LAB265): Supertrend(src=ohlc4, ATR RMA(10), factor) on UTC H2 bars built from feeder M5;
// flip at completed H2 close -> close current S position; open new one if HTF and crowd filters pass.
// SL 2.2 x ATR14 (RMA) of H2, no TP; exit only on the next flip or SL.
#define ENG_S 20
int    g_hE150=INVALID_HANDLE, g_hE250=INVALID_HANDLE;
long   g_sLastBarMs=0;      // open time of the last completed H2 bar processed
int    g_sDir=0;            // current Supertrend direction
string g_sPanel="-";
long SMagic(){ return InpMagicBase + ENG_S; }

// Builds completed TF bars from feeder M5 and returns Supertrend direction of the last two bars.
bool SupertrendState(const int uptoM5,int &dirNow,int &dirPrev,double &atr14,long &barMs)
{
   long tfMs=(long)InpS_TFHours*3600000;
   long curBucket=(g_m5[uptoM5].ms/tfMs)*tfMs;
   double O[],H[],L[],C[]; long T[];
   ArrayResize(O,0);ArrayResize(H,0);ArrayResize(L,0);ArrayResize(C,0);ArrayResize(T,0);
   long cur=-1; double o=0,h=0,l=0,c=0; bool have=false;
   for(int i=0;i<=uptoM5;i++)
   {
      long b=(g_m5[i].ms/tfMs)*tfMs;
      if(b>=curBucket) break;                     // only completed TF bars
      if(b!=cur)
      {
         if(have){int k=ArraySize(C);ArrayResize(O,k+1);ArrayResize(H,k+1);ArrayResize(L,k+1);ArrayResize(C,k+1);ArrayResize(T,k+1);O[k]=o;H[k]=h;L[k]=l;C[k]=c;T[k]=cur;}
         cur=b;o=g_m5[i].o;h=g_m5[i].h;l=g_m5[i].l;c=g_m5[i].c;have=true;
      }
      else {h=MathMax(h,g_m5[i].h);l=MathMin(l,g_m5[i].l);c=g_m5[i].c;}
   }
   if(have){int k=ArraySize(C);ArrayResize(O,k+1);ArrayResize(H,k+1);ArrayResize(L,k+1);ArrayResize(C,k+1);ArrayResize(T,k+1);O[k]=o;H[k]=h;L[k]=l;C[k]=c;T[k]=cur;}
   int n=ArraySize(C);
   if(n<40) return false;
   double a10=0,a14=0,fu=0,fd=0; int d=1;
   for(int k=0;k<n;k++)
   {
      double pc=(k>0?C[k-1]:C[k]);
      double tr=MathMax(H[k]-L[k],MathMax(MathAbs(H[k]-pc),MathAbs(L[k]-pc)));
      if(k==0){a10=tr;a14=tr;}
      else {a10=a10+(tr-a10)/InpS_ATRPeriod; a14=a14+(tr-a14)/14.0;}
      double src=(O[k]+H[k]+L[k]+C[k])/4.0;
      double up=src-InpS_Factor*a10, dn=src+InpS_Factor*a10;
      if(k==0){fu=up;fd=dn;d=1;dirPrev=d;continue;}
      double fuP=fu, fdP=fd; int dP=d;
      if(C[k-1]>fuP) fu=MathMax(up,fuP); else fu=up;
      if(C[k-1]<fdP) fd=MathMin(dn,fdP); else fd=dn;
      if(dP==-1 && C[k]>fdP) d=1;
      else if(dP==1 && C[k]<fuP) d=-1;
      else d=dP;
      dirPrev=dP;
   }
   dirNow=d; atr14=a14; barMs=T[n-1];
   return true;
}

int HTFDir()
{
   if(g_hE150==INVALID_HANDLE || g_hE250==INVALID_HANDLE) return 0;
   double a[1],b[1];
   if(CopyBuffer(g_hE150,0,1,1,a)<1 || CopyBuffer(g_hE250,0,1,1,b)<1) return 0;   // last closed H1
   if(a[0]>b[0]) return 1;
   if(a[0]<b[0]) return -1;
   return 0;
}

double Z24AtOrBefore(const long ms)
{
   for(int k=ArraySize(g_ratioTs)-1;k>=InpD_Z24WindowBars;k--)
      if(g_ratioTs[k]<=ms) return ZAt(g_ratio,k,InpD_Z24WindowBars);
   return EMPTY_VALUE;
}

void CloseSPositions(const string why)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || PositionGetInteger(POSITION_MAGIC)!=SMagic()) continue;
      int side=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);
      trade.SetExpertMagicNumber(SMagic());
      if(trade.PositionClose(tk)) AppendLog("S_EXIT_FLIP",ENG_S,side,why);
      else PrintFormat("CF157 S CLOSE FAIL tk=%I64u ret=%u %s",tk,trade.ResultRetcode(),trade.ResultRetcodeDescription());
   }
}

bool OpenTradeS(const int side,const double atr,const string detail)
{
   MqlTick q; if(!SymbolInfoTick(InpBrokerSymbol,q)) return false;
   double entry=(side>0?q.ask:q.bid);
   double dist=InpS_StopATR*atr;
   double minDist=MinStopDistance()+SymbolInfoDouble(InpBrokerSymbol,SYMBOL_POINT);
   if(dist<minDist) dist=minDist;
   double sl=NormalizePriceToTick(entry-side*dist);
   double lots=MarginSafeLots(side,entry,RiskLots(side,entry,sl,InpS_RiskPct));
   if(lots<=0){AppendLog("S_REJECT_SIZE",ENG_S,side,detail);return false;}
   if(InpDryRun || !InpS_LiveTrade){AppendLog("S_SHADOW_ENTRY",ENG_S,side,detail);return true;}
   trade.SetExpertMagicNumber(SMagic());
   trade.SetDeviationInPoints(InpSlippagePts);
   bool ok;
   if(side>0) ok=trade.Buy(lots,InpBrokerSymbol,0.0,sl,0.0,"CF157_S");
   else       ok=trade.Sell(lots,InpBrokerSymbol,0.0,sl,0.0,"CF157_S");
   if(!ok)
   {
      PrintFormat("CF157 S ENTRY FAIL ret=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());
      AppendLog("S_ENTRY_FAIL",ENG_S,side,detail); return false;
   }
   g_lastSignal="S "+(side>0?"BUY":"SELL");
   AppendLog("S_ENTRY",ENG_S,side,detail);
   return true;
}

void ProcessEngineS(const int idx)
{
   if(!InpSEnable || idx<0) return;
   int dNow=0,dPrev=0; double atr=0; long barMs=0;
   if(!SupertrendState(idx,dNow,dPrev,atr,barMs)){g_sPanel="history short";return;}
   g_sPanel=StringFormat("ST %s | ATR14 %.0f | HTF %d",dNow>0?"UP":"DOWN",atr,HTFDir());
   if(g_sLastBarMs==0){g_sLastBarMs=barMs;g_sDir=dNow;return;}     // attach: no retroactive signal
   if(barMs<=g_sLastBarMs) return;
   g_sLastBarMs=barMs;
   bool flip=(dNow!=dPrev);
   g_sDir=dNow;
   if(!flip) return;

   long closeMs=barMs+(long)InpS_TFHours*3600000;
   double z24=Z24AtOrBefore(closeMs-300000);                       // ratio paired with the last M5 bar of the TF bar
   int htf=HTFDir();
   string det=StringFormat("flip %s H2open=%s ATR14=%.2f z24=%.3f HTF=%d",dNow>0?"UP":"DOWN",
              TimeToString((datetime)(barMs/1000),TIME_DATE|TIME_MINUTES),atr,(z24==EMPTY_VALUE?0.0:z24),htf);
   CloseSPositions(det);                                           // every flip ends the previous trade
   if(InpS_UseHTF && htf!=dNow){AppendLog("S_SKIP_HTF",ENG_S,dNow,det);return;}
   if(z24!=EMPTY_VALUE && MathAbs(z24)>=InpS_CrowdAgainstZ && (z24>0?1:-1)==dNow)
   {
      AppendLog("S_SKIP_CROWD",ENG_S,dNow,det);                     // crowd on our side = compass against
      return;
   }
   OpenTradeS(dNow,atr,det);
}

// LAB268: exit S when EMA9 crosses EMA20 on H1 against the position (checked once per closed H1 bar).
int      g_hEf=INVALID_HANDLE, g_hEs=INVALID_HANDLE;
datetime g_sEmaLastH1=0;
void SEmaExit()
{
   if(InpS_EMAExitMode<=0 || g_hEf==INVALID_HANDLE || g_hEs==INVALID_HANDLE) return;
   datetime h1=iTime(InpBrokerSymbol,PERIOD_H1,1);
   if(h1==0 || h1==g_sEmaLastH1) return;
   double f[2],s[2];
   if(CopyBuffer(g_hEf,0,1,2,f)<2 || CopyBuffer(g_hEs,0,1,2,s)<2) return;   // [0]=bar 2 (older), [1]=bar 1 (last closed)
   g_sEmaLastH1=h1;
   int now=0,prev=0;
   if(f[1]>s[1]) now=1; else if(f[1]<s[1]) now=-1;
   if(f[0]>s[0]) prev=1; else if(f[0]<s[0]) prev=-1;
   if(now==prev || now==0) return;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpBrokerSymbol || PositionGetInteger(POSITION_MAGIC)!=SMagic()) continue;
      int side=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);
      if(now!=-side) continue;
      string why=StringFormat("EMA%d/%d H1 crossed against at %s",InpS_EMAFast,InpS_EMASlow,TimeToString(h1,TIME_DATE|TIME_MINUTES));
      if(InpS_EMAExitMode==1){AppendLog("S_SHADOW_EMA_EXIT",ENG_S,side,why);continue;}
      trade.SetExpertMagicNumber(SMagic());
      if(trade.PositionClose(tk)) AppendLog("S_EMA_EXIT",ENG_S,side,why);
      else PrintFormat("CF157 S EMA EXIT FAIL tk=%I64u ret=%u %s",tk,trade.ResultRetcode(),trade.ResultRetcodeDescription());
   }
}

int SPosCount()
{
   int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetString(POSITION_SYMBOL)==InpBrokerSymbol && PositionGetInteger(POSITION_MAGIC)==SMagic()) n++;
   }
   return n;
}

//---------------- UI / lifecycle ------------------------------------
void UpdatePanel()
{
   int n=MyPositionCount();
   Comment(
      "CrowdFade CORE v005 [DEMO]  A+B3 + D + S | exits D-crowd ",IntegerToString(InpD_CrowdExitMode)," S-EMA ",IntegerToString(InpS_EMAExitMode)," | EARLY ",(InpEarlyEnable?"on":"off")," | R48 ",(InpR48Mode==2?"trade":(InpR48Mode==1?"shadow":"off")),"\n",
      "Broker: ",InpBrokerSymbol," | Binance: ",InpBinanceSymbol,"\n",
      "A/B3 positions: ",IntegerToString(n),"/",IntegerToString(InpMaxPositions),
      " | Risk: ",DoubleToString(InpRiskPct,2),"% | hold ",IntegerToString(InpMaxHoldHours),"h\n",
      "D positions: ",IntegerToString(DPosCount()),"/",IntegerToString(InpD_MaxPositions)," | Risk: ",DoubleToString(InpD_RiskPct,2),
      "% | cross ",DoubleToString(InpD_Z6Cross,2)," z24>=",DoubleToString(InpD_Z24Min,2)," | ",g_dPanel,"\n",
      "S positions: ",IntegerToString(SPosCount())," | Risk: ",DoubleToString(InpS_RiskPct,2),"% | ",(InpS_LiveTrade?"live":"shadow")," | ",g_sPanel,"\n",
      "L: ",(InpL_Mode==2?"live":(InpL_Mode==1?"shadow":"off"))," | pos ",IntegerToString(LPosCount()),(g_lv.on?" | virtual open":"")," | ",g_lPanel,"\n",
      "Z: ",DoubleToString(g_panelZ,3)," | H4 phase: ",g_panelPhase,
      " | H1 ATR: ",DoubleToString(g_panelATR,2),"\n",
      "OI4h: ",DoubleToString(g_panelOI4h*100.0,3),"%",
      " | Last signal: ",g_lastSignal,"\n",
      "Exit: 50% @3R, runner SL +2R | add-on first SL +0.25R\n",
      "State: ",g_state
   );
}

int OnInit()
{
   if(InpRiskPct<=0 || InpStopH1ATR<=0 || InpPartialAtR<1.5 || InpPartialFraction<=0 || InpPartialFraction>=1 ||
      InpRunnerLockR<0 || InpMaxPositions<1 || InpMaxPositions>2 || InpA_ExtensionATR<=0 || InpA_OI4hMin<0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpD_RiskPct<=0 || InpD_StopATR<=0 || InpD_Z6Cross<=InpD_EpisodeResetZ || InpD_Z24Min<0 ||
      InpD_TrailDistR<=0 || InpD_MaxPositions<1 || InpD_Z24WindowBars<InpZWindowBars || InpD_Z24WindowBars>480)
      return INIT_PARAMETERS_INCORRECT;
   for(int k=0;k<3;k++){g_dEp[k].sign=0;g_dEp[k].used=false;}
   g_lv.on=false; g_lSide=0; g_lUsed=false;
   if(InpL_OIBars<1 || InpL_OIBars>24 || InpL_OIDropPct<=0 || InpL_StopATR<=0 || InpL_TrailDistR<=0 || InpL_MaxHoldHours<1 || InpL_RiskPct<=0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpS_TFHours<1 || InpS_TFHours>12 || InpS_ATRPeriod<2 || InpS_Factor<=0 || InpS_StopATR<=0 || InpS_RiskPct<=0)
      return INIT_PARAMETERS_INCORRECT;

   if(!SymbolSelect(InpBrokerSymbol,true))
   {
      Print("CF157 cannot select broker symbol ",InpBrokerSymbol);
      return INIT_FAILED;
   }
   if(InpSEnable && InpS_UseHTF)
   {
      g_hE150=iMA(InpBrokerSymbol,PERIOD_H1,150,0,MODE_EMA,PRICE_CLOSE);
      g_hE250=iMA(InpBrokerSymbol,PERIOD_H1,250,0,MODE_EMA,PRICE_CLOSE);
      if(g_hE150==INVALID_HANDLE || g_hE250==INVALID_HANDLE){Print("CF157 S: EMA150/250 H1 init failed");return INIT_FAILED;}
   }
   if(InpSEnable && InpS_EMAExitMode>0)
   {
      g_hEf=iMA(InpBrokerSymbol,PERIOD_H1,InpS_EMAFast,0,MODE_EMA,PRICE_CLOSE);
      g_hEs=iMA(InpBrokerSymbol,PERIOD_H1,InpS_EMASlow,0,MODE_EMA,PRICE_CLOSE);
      if(g_hEf==INVALID_HANDLE || g_hEs==INVALID_HANDLE){Print("CF157 S: EMA fast/slow H1 init failed");return INIT_FAILED;}
   }
   trade.SetDeviationInPoints(InpSlippagePts);

   long mode=AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   if(mode!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
      Print("CF157 WARNING: account is not hedging. Two independent same-symbol positions may be impossible; add-on parity will differ.");

   Print("CF157 uses existing BinanceLAB093 feeder. IMPORTANT: set feeder InpHistoryHours >= 240.");
   Print("CF157 also needs https://fapi.binance.com in MT5 WebRequest allow-list for ratio/Z.");

   LoadM5();LoadOI();
   int idx=LatestCompletedM5Index();
   if(idx>=0)
   {
      g_lastProcessedBarMs=g_m5[idx].ms; // no retroactive entries on attach
      long hrs=(g_m5[idx].ms-g_m5[0].ms)/3600000;
      if(hrs<InpRequiredHistoryHrs)
         PrintFormat("CF157 WARNING: feeder history only %d h; need >=%d h. Set feeder InpHistoryHours >=240.",(int)hrs,InpRequiredHistoryHrs);
   }
   WarmStart();
   EventSetTimer(MathMax(1,InpRefreshSec));
   UpdatePanel();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();Comment("");
   if(g_hE150!=INVALID_HANDLE) IndicatorRelease(g_hE150);
   if(g_hE250!=INVALID_HANDLE) IndicatorRelease(g_hE250);
   if(g_hEf!=INVALID_HANDLE) IndicatorRelease(g_hEf);
   if(g_hEs!=INVALID_HANDLE) IndicatorRelease(g_hEs);
}
void OnTick(){ManagePositions();ManageD();ManageL();}

void OnTimer()
{
   ManagePositions();
   ManageD();
   ManageL();

   // Ratio first: latency is measured independently of the feeder state.
   double z=0.0;long zts=0;
   bool zok=FetchLatestZ(z,zts);
   if(zok) LogLatency(); else g_skipPolls++;

   if(!LoadM5() || !LoadOI())
   {
      g_state="FEEDER READ FAIL";UpdatePanel();return;
   }
   int idx=LatestCompletedM5Index();
   if(idx<0 || !DataFresh(idx)){UpdatePanel();return;}
   if(!zok)
   {
      g_state="RATIO/Z FETCH FAIL";UpdatePanel();return;
   }
   g_lastZ=z;

   // Engine D works on every new ratio point, independently of the core bar gate below.
   static bool dWarm=false;
   if(!dWarm){ProcessEngineD(false);dWarm=true;}
   else ProcessEngineD(true);
   ProcessEngineS(idx);
   SEmaExit();

   // Process only once per completed M5 bar, and require a fresh/equal-latest ratio sample.
   if(g_m5[idx].ms<=g_lastProcessedBarMs)
   {
      g_state="WAIT NEW M5";UpdatePanel();return;
   }

   // Avoid processing a bar before Binance ratio feed has advanced near that bar.
   if(zts+300000 < g_m5[idx].ms)
   {
      g_state="WAIT RATIO SYNC";UpdatePanel();return;
   }

   g_state="PROCESS";
   ProcessNewCompletedBar(idx,z,zts);
   g_lastProcessedBarMs=g_m5[idx].ms;
   g_state="READY";
   UpdatePanel();
}
//+------------------------------------------------------------------+
