#property strict
#property version   "1.00"
#property description "AMP-native GC AEIF shadow sensor. NO TRADING. Emits frozen AEIF confirmations via FILE_COMMON."

// AMP_GC_AEIF_SHADOW_SENSOR_001
// Port of research/gc/amp_gc_oos_001_one_shot.py signal semantics.
// IMPORTANT: 30m cooldown is LOGGED as a diagnostic branch only. It does NOT suppress
// confirmation/transfer signals, matching the frozen historical transfer lineage.

input string InpGCSymbol             = "GCEZ26";  // AMP/CQG GC contract symbol
input int    InpWarmupDays           = 7;          // Historical tick bootstrap window
input int    InpPollMilliseconds     = 200;        // Tick database polling interval
input string InpSignalFile           = "AEIF_SHADOW_001\\signals.csv";
input string InpHeartbeatFile        = "AEIF_SHADOW_001\\sensor_heartbeat.csv";
input string InpSensorEventFile      = "AEIF_SHADOW_001\\sensor_events.csv";
input bool   InpVerboseLog           = true;

#define M5_MS 300000ULL
#define DAY_MS 86400000ULL
#define MAX_PENDING 16
#define SPEC_ID "AEIF_FROZEN_SPEC_001"
#define SPEC_BLOB_SHA "604cc57ca51bb2f990b3cc49282af6d05c262d11"
#define PROTOCOL_VERSION "AEIF_SHADOW_V1"

struct SPriceLevel
{
   double price;
   double buy_only;
   double sell_only;
};

struct SPendingCore
{
   bool   active;
   ulong  core_bar_msc;
   ulong  expected_bar_msc;
   int    offset;
   int    side; // +1 LONG, -1 SHORT
   double delta_frac;
   double loc;
   double impact_atr;
   int    cooldown30_keep;
};

bool   g_have_bar=false;
ulong  g_bar_start=0;
double g_open=0.0,g_high=0.0,g_low=0.0,g_close=0.0;
double g_buy_only=0.0,g_sell_only=0.0;
SPriceLevel g_levels[];

bool   g_have_prev_close=false;
double g_prev_close=0.0;
bool   g_atr_seeded=false;
double g_atr14=0.0;
int    g_atr_valid_count=0;

double g_hist_delta[];
double g_hist_sell_loc[];
double g_hist_buy_loc[];
SPendingCore g_pending[MAX_PENDING];

ulong g_last_raw_msc=0;
int   g_seen_at_last_msc=0;
ulong g_last_tick_msc=0;
ulong g_completed_bars=0;
ulong g_signal_seq=0;
ulong g_last_cooldown_kept_core=0;
bool  g_emit_enabled=false;
string g_session_id="";
ulong g_last_heartbeat_local=0;

string SideText(const int side){ return side>0 ? "LONG" : "SHORT"; }

string MakeSessionId()
{
   string t=TimeToString(TimeLocal(),TIME_DATE|TIME_SECONDS);
   StringReplace(t,".","");
   StringReplace(t,":","");
   StringReplace(t," ","_");
   return t+"_"+IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
}

void ResetCurrentBar()
{
   g_have_bar=false;
   g_bar_start=0;
   g_open=g_high=g_low=g_close=0.0;
   g_buy_only=g_sell_only=0.0;
   ArrayResize(g_levels,0);
}

int FindLevel(const double price)
{
   const int n=ArraySize(g_levels);
   for(int i=0;i<n;i++)
      if(MathAbs(g_levels[i].price-price)<=1e-10) return i;
   return -1;
}

void AddLevel(const double price,const double buy_only,const double sell_only)
{
   int i=FindLevel(price);
   if(i<0)
   {
      i=ArraySize(g_levels);
      ArrayResize(g_levels,i+1);
      g_levels[i].price=price;
      g_levels[i].buy_only=0.0;
      g_levels[i].sell_only=0.0;
   }
   g_levels[i].buy_only += buy_only;
   g_levels[i].sell_only += sell_only;
}

void StartBar(const ulong bar_start,const double price,const double volume,const bool is_buy,const bool is_sell)
{
   ResetCurrentBar();
   g_have_bar=true;
   g_bar_start=bar_start;
   g_open=g_high=g_low=g_close=price;
   if(is_buy && !is_sell)
   {
      g_buy_only+=volume;
      AddLevel(price,volume,0.0);
   }
   else if(is_sell && !is_buy)
   {
      g_sell_only+=volume;
      AddLevel(price,0.0,volume);
   }
   else AddLevel(price,0.0,0.0);
}

void AddToBar(const double price,const double volume,const bool is_buy,const bool is_sell)
{
   if(price>g_high) g_high=price;
   if(price<g_low)  g_low=price;
   g_close=price;
   if(is_buy && !is_sell)
   {
      g_buy_only+=volume;
      AddLevel(price,volume,0.0);
   }
   else if(is_sell && !is_buy)
   {
      g_sell_only+=volume;
      AddLevel(price,0.0,volume);
   }
   else AddLevel(price,0.0,0.0);
}

void PushLast240(double &arr[],const double v)
{
   int n=ArraySize(arr);
   if(n<240)
   {
      ArrayResize(arr,n+1);
      arr[n]=v;
      return;
   }
   for(int i=1;i<n;i++) arr[i-1]=arr[i];
   arr[n-1]=v;
}

bool Quantile240(const double &src[],const double q,double &out)
{
   if(ArraySize(src)<240) return false;
   double a[];
   ArrayResize(a,240);
   for(int i=0;i<240;i++) a[i]=src[i];
   ArraySort(a);
   double pos=239.0*q;
   int lo=(int)MathFloor(pos), hi=(int)MathCeil(pos);
   if(lo==hi)
   {
      out=a[lo];
      return true;
   }
   double w=pos-lo;
   out=a[lo]*(1.0-w)+a[hi]*w;
   return true;
}

void AppendSensorEvent(const string event_type,const ulong bar_msc,const int side,const string detail)
{
   int h=FileOpen(InpSensorEventFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE) return;
   if(FileSize(h)==0)
      FileWrite(h,"session_id","event_type","bar_msc","side","detail");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session_id,event_type,(long)bar_msc,(side==0?"":SideText(side)),detail);
   FileFlush(h);
   FileClose(h);
}

bool WriteSignal(const SPendingCore &p,const ulong confirm_bar_msc,const int confirm_offset,
                 const double copen,const double cclose,const double cdelta,const ulong emit_tick_msc)
{
   g_signal_seq++;
   int h=FileOpen(InpSignalFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE)
   {
      Print("AEIF shadow: cannot open signal bridge. err=",GetLastError());
      g_signal_seq--;
      return false;
   }
   if(FileSize(h)==0)
      FileWrite(h,"protocol","spec_id","spec_blob_sha","session_id","seq_id","core_bar_msc","confirm_bar_msc",
                  "entry_eligible_msc","emit_gc_tick_msc","side","confirm_offset","core_delta_frac","core_loc",
                  "core_impact_atr","confirm_open","confirm_close","confirm_delta","cooldown30_keep");
   FileSeek(h,0,SEEK_END);
   int digits=(int)SymbolInfoInteger(InpGCSymbol,SYMBOL_DIGITS);
   FileWrite(h,PROTOCOL_VERSION,SPEC_ID,SPEC_BLOB_SHA,g_session_id,(long)g_signal_seq,(long)p.core_bar_msc,
             (long)confirm_bar_msc,(long)(confirm_bar_msc+M5_MS),(long)emit_tick_msc,SideText(p.side),confirm_offset,
             DoubleToString(p.delta_frac,10),DoubleToString(p.loc,10),DoubleToString(p.impact_atr,10),
             DoubleToString(copen,digits),DoubleToString(cclose,digits),DoubleToString(cdelta,4),p.cooldown30_keep);
   FileFlush(h);
   FileClose(h);
   AppendSensorEvent("SIGNAL_EMIT",confirm_bar_msc,p.side,"seq="+IntegerToString((long)g_signal_seq)+";offset="+IntegerToString(confirm_offset));
   if(InpVerboseLog)
      PrintFormat("AEIF SHADOW SIGNAL #%I64u %s core=%I64u confirm=%I64u eligible=%I64u",g_signal_seq,SideText(p.side),p.core_bar_msc,confirm_bar_msc,confirm_bar_msc+M5_MS);
   return true;
}

void ProcessPendingConfirmations(const ulong bar_msc,const double o,const double c,const double delta,const ulong emit_tick_msc)
{
   for(int i=0;i<MAX_PENDING;i++)
   {
      if(!g_pending[i].active) continue;
      if(bar_msc!=g_pending[i].expected_bar_msc)
      {
         AppendSensorEvent("CONFIRM_EXPIRE_GAP",bar_msc,g_pending[i].side,"core="+IntegerToString((long)g_pending[i].core_bar_msc));
         g_pending[i].active=false;
         continue;
      }
      bool ok=(g_pending[i].side>0 && c>o && delta>0.0) ||
              (g_pending[i].side<0 && c<o && delta<0.0);
      if(ok)
      {
         if(g_emit_enabled)
            WriteSignal(g_pending[i],bar_msc,g_pending[i].offset,o,c,delta,emit_tick_msc);
         g_pending[i].active=false;
      }
      else if(g_pending[i].offset>=2)
      {
         AppendSensorEvent("CONFIRM_EXPIRE_2",bar_msc,g_pending[i].side,"core="+IntegerToString((long)g_pending[i].core_bar_msc));
         g_pending[i].active=false;
      }
      else
      {
         g_pending[i].offset=2;
         g_pending[i].expected_bar_msc += M5_MS;
      }
   }
}

void AddPendingCore(const ulong bar_msc,const int side,const double delta_frac,const double loc,const double impact,const int cooldown_keep)
{
   int slot=-1;
   for(int i=0;i<MAX_PENDING;i++)
      if(!g_pending[i].active)
      {
         slot=i;
         break;
      }
   if(slot<0)
   {
      Print("AEIF shadow: pending buffer full; core not queued");
      AppendSensorEvent("ERROR_PENDING_FULL",bar_msc,side,"");
      return;
   }
   g_pending[slot].active=true;
   g_pending[slot].core_bar_msc=bar_msc;
   g_pending[slot].expected_bar_msc=bar_msc+M5_MS;
   g_pending[slot].offset=1;
   g_pending[slot].side=side;
   g_pending[slot].delta_frac=delta_frac;
   g_pending[slot].loc=loc;
   g_pending[slot].impact_atr=impact;
   g_pending[slot].cooldown30_keep=cooldown_keep;
}

void FinalizeCurrentBar(const ulong emit_tick_msc)
{
   if(!g_have_bar) return;
   const double range=g_high-g_low;
   const double lower_cut=g_low+0.20*range;
   const double upper_cut=g_high-0.20*range;
   double lower_sell_only=0.0, upper_buy_only=0.0;
   for(int i=0;i<ArraySize(g_levels);i++)
   {
      if(g_levels[i].price<=lower_cut+1e-12)
         lower_sell_only += g_levels[i].sell_only;
      if(g_levels[i].price>=upper_cut-1e-12)
         upper_buy_only += g_levels[i].buy_only;
   }
   const double sell_loc=(g_sell_only>0.0 ? lower_sell_only/g_sell_only : 0.0);
   const double buy_loc =(g_buy_only >0.0 ? upper_buy_only/g_buy_only : 0.0);
   const double den=g_buy_only+g_sell_only;
   const double delta=g_buy_only-g_sell_only;
   const double delta_frac=(den>0.0 ? delta/den : 0.0);

   double tr=0.0;
   bool atr_ready=false;
   if(g_have_prev_close)
   {
      tr=MathMax(range,MathMax(MathAbs(g_high-g_prev_close),MathAbs(g_low-g_prev_close)));
      if(!g_atr_seeded)
      {
         g_atr14=tr;
         g_atr_seeded=true;
      }
      else g_atr14=((13.0*g_atr14)+tr)/14.0;
      g_atr_valid_count++;
      atr_ready=(g_atr_valid_count>=14 && g_atr14>0.0);
   }

   ProcessPendingConfirmations(g_bar_start,g_open,g_close,delta,emit_tick_msc);

   double q10=0,q90=0,q75_sell=0,q75_buy=0;
   bool ref_ready=Quantile240(g_hist_delta,0.10,q10) &&
                  Quantile240(g_hist_delta,0.90,q90) &&
                  Quantile240(g_hist_sell_loc,0.75,q75_sell) &&
                  Quantile240(g_hist_buy_loc,0.75,q75_buy);

   if(ref_ready && atr_ready)
   {
      const double dn_eff=MathMax(0.0,g_open-g_close)/g_atr14;
      const double up_eff=MathMax(0.0,g_close-g_open)/g_atr14;
      const bool is_long=(delta_frac<=q10 && sell_loc>=q75_sell && dn_eff<=0.15);
      const bool is_short=(delta_frac>=q90 && buy_loc>=q75_buy && up_eff<=0.15);
      if(is_long || is_short)
      {
         const int side=is_long?1:-1;
         const double loc=is_long?sell_loc:buy_loc;
         const double impact=is_long?dn_eff:up_eff;
         int cooldown_keep=0;
         if(g_last_cooldown_kept_core==0 || g_bar_start-g_last_cooldown_kept_core>=1800000ULL)
         {
            cooldown_keep=1;
            g_last_cooldown_kept_core=g_bar_start;
         }
         AddPendingCore(g_bar_start,side,delta_frac,loc,impact,cooldown_keep);
         AppendSensorEvent("CORE",g_bar_start,side,"cooldown_keep="+IntegerToString(cooldown_keep));
      }
   }

   PushLast240(g_hist_delta,delta_frac);
   PushLast240(g_hist_sell_loc,sell_loc);
   PushLast240(g_hist_buy_loc,buy_loc);
   g_prev_close=g_close;
   g_have_prev_close=true;
   g_completed_bars++;
}

void ProcessTradeTick(const MqlTick &tick)
{
   double volume=(tick.volume_real>0.0 ? tick.volume_real : (double)tick.volume);
   if(tick.last<=0.0 || volume<=0.0) return;
   const bool is_buy =((tick.flags&TICK_FLAG_BUY )==TICK_FLAG_BUY );
   const bool is_sell=((tick.flags&TICK_FLAG_SELL)==TICK_FLAG_SELL);
   const ulong bucket=(tick.time_msc/M5_MS)*M5_MS;
   if(!g_have_bar)
      StartBar(bucket,tick.last,volume,is_buy,is_sell);
   else if(bucket==g_bar_start)
      AddToBar(tick.last,volume,is_buy,is_sell);
   else if(bucket>g_bar_start)
   {
      FinalizeCurrentBar(tick.time_msc);
      StartBar(bucket,tick.last,volume,is_buy,is_sell);
   }
}

void UpdateCursorAfterTick(const MqlTick &tick)
{
   if(tick.time_msc>g_last_raw_msc)
   {
      g_last_raw_msc=tick.time_msc;
      g_seen_at_last_msc=1;
   }
   else if(tick.time_msc==g_last_raw_msc)
      g_seen_at_last_msc++;
   if(tick.time_msc>g_last_tick_msc)
      g_last_tick_msc=tick.time_msc;
}

bool BootstrapHistory()
{
   MqlTick last;
   if(!SymbolInfoTick(InpGCSymbol,last) || last.time_msc==0)
   {
      Print("AEIF shadow: no current GC tick for bootstrap. err=",GetLastError());
      return false;
   }
   ulong to=last.time_msc;
   ulong from=(to>(ulong)InpWarmupDays*DAY_MS ? to-(ulong)InpWarmupDays*DAY_MS : 0);
   const ulong chunk=6ULL*60ULL*60ULL*1000ULL;
   g_emit_enabled=false;
   for(ulong s=from;s<=to;)
   {
      ulong candidate=s+chunk-1;
      ulong e=(candidate<to ? candidate : to);
      MqlTick ticks[];
      ResetLastError();
      int n=CopyTicksRange(InpGCSymbol,ticks,COPY_TICKS_TRADE,s,e);
      if(n<0)
      {
         PrintFormat("AEIF shadow: CopyTicksRange bootstrap failed %I64u..%I64u err=%d",s,e,GetLastError());
         return false;
      }
      for(int i=0;i<n;i++)
      {
         ProcessTradeTick(ticks[i]);
         UpdateCursorAfterTick(ticks[i]);
      }
      if(e>=to) break;
      s=e+1;
   }
   g_emit_enabled=true;
   if(ArraySize(g_hist_delta)<240)
      PrintFormat("AEIF shadow WARNING: only %d completed traded M5 bars in warmup; sensor waits until 240.",ArraySize(g_hist_delta));
   PrintFormat("AEIF shadow bootstrap complete: bars=%I64u refs=%d cursor=%I64u",g_completed_bars,ArraySize(g_hist_delta),g_last_raw_msc);
   return true;
}

void PollNewTicks()
{
   if(g_last_raw_msc==0) return;
   MqlTick ticks[];
   int n=CopyTicks(InpGCSymbol,ticks,COPY_TICKS_TRADE,g_last_raw_msc,5000);
   if(n<=0) return;
   int skip_same=g_seen_at_last_msc;
   int seen_same_this_call=0;
   for(int i=0;i<n;i++)
   {
      if(ticks[i].time_msc<g_last_raw_msc) continue;
      if(ticks[i].time_msc==g_last_raw_msc && seen_same_this_call<skip_same)
      {
         seen_same_this_call++;
         continue;
      }
      ProcessTradeTick(ticks[i]);
      UpdateCursorAfterTick(ticks[i]);
   }
}

void WriteHeartbeat()
{
   ulong now=(ulong)GetTickCount64();
   if(g_last_heartbeat_local!=0 && now-g_last_heartbeat_local<1000) return;
   g_last_heartbeat_local=now;
   int h=FileOpen(InpHeartbeatFile,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE) return;
   FileWrite(h,"protocol","session_id","gc_symbol","last_gc_tick_msc","current_bar_msc","completed_bars","rolling_refs","signals_emitted","status");
   FileWrite(h,PROTOCOL_VERSION,g_session_id,InpGCSymbol,(long)g_last_tick_msc,(long)g_bar_start,(long)g_completed_bars,ArraySize(g_hist_delta),(long)g_signal_seq,"SHADOW_NO_TRADING");
   FileFlush(h);
   FileClose(h);
}

int OnInit()
{
   if(InpWarmupDays<2 || InpPollMilliseconds<50)
   {
      Print("AEIF shadow: invalid inputs");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!SymbolSelect(InpGCSymbol,true))
   {
      Print("AEIF shadow: cannot select symbol ",InpGCSymbol," err=",GetLastError());
      return INIT_FAILED;
   }
   g_session_id=MakeSessionId();
   for(int i=0;i<MAX_PENDING;i++) g_pending[i].active=false;
   if(!BootstrapHistory()) return INIT_FAILED;
   if(!EventSetMillisecondTimer(InpPollMilliseconds))
   {
      Print("AEIF shadow: timer setup failed err=",GetLastError());
      return INIT_FAILED;
   }
   WriteHeartbeat();
   AppendSensorEvent("START",g_bar_start,0,"symbol="+InpGCSymbol+";NO_TRADING");
   Print("AMP_GC_AEIF_SHADOW_SENSOR_001 started. NO TRADING. session=",g_session_id);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   WriteHeartbeat();
   AppendSensorEvent("STOP",g_bar_start,0,"reason="+IntegerToString(reason));
}

void OnTimer()
{
   PollNewTicks();
   WriteHeartbeat();
}

// No OnTick trading logic by design. All raw GC trades are consumed through CopyTicks.
