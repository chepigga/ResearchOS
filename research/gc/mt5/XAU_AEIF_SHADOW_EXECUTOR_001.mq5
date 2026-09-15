#property strict
#property version   "1.00"
#property description "XAU shadow execution simulator for AMP-native AEIF. ZERO ORDER FUNCTIONS."

// XAU_AEIF_SHADOW_EXECUTOR_001
// Safety invariant: this EA contains no trading API calls. It only reads live quotes and simulates.

input string InpXAUSymbol          = "XAUUSD";   // Set exact FTMO symbol if suffix differs
input int    InpPollMilliseconds   = 200;
input int    InpMaxSignalAgeMs     = 5000;       // Pre-registered stale-signal gate
input int    InpSessionGapMs       = 90000;      // Retroactive shadow session-gap exit
input string InpSignalFile         = "AEIF_SHADOW_001\\signals.csv";
input string InpEventFile          = "AEIF_SHADOW_001\\xau_shadow_events.csv";
input string InpHeartbeatFile      = "AEIF_SHADOW_001\\xau_heartbeat.csv";
input bool   InpVerboseLog         = true;

#define PROTOCOL_VERSION "AEIF_SHADOW_V1"
#define TP_R 3.0
#define HOLD_MS 14400000ULL

struct SSignal
{
   string protocol,spec_id,spec_sha,session_id,side;
   long seq_id;
   ulong core_bar_msc,confirm_bar_msc,entry_eligible_msc,emit_gc_tick_msc;
   int confirm_offset,cooldown_keep;
   double core_delta_frac,core_loc,core_impact,confirm_open,confirm_close,confirm_delta;
};

bool    g_active=false;
SSignal g_trade_signal;
double  g_entry=0.0,g_atr=0.0,g_sl=0.0,g_tp=0.0;
double  g_mfe_r=0.0,g_mae_r=0.0;
ulong   g_entry_msc=0,g_expiry_msc=0;
ulong   g_last_quote_msc=0;
double  g_last_bid=0.0,g_last_ask=0.0;
ulong   g_xau_cursor_msc=0;
int     g_xau_seen_at_cursor=0;
string  g_last_seen_key="";
ulong   g_last_heartbeat_local=0;
long    g_accepted=0,g_closed=0,g_rejected=0;
int     g_xau_digits=2;

string SignalKey(const SSignal &s)
{
   return s.session_id+":"+IntegerToString(s.seq_id);
}

void LogEvent(const string event_type,const SSignal &s,const ulong xau_msc,const double bid,const double ask,
              const string reason,const double r_value=0.0)
{
   int h=FileOpen(InpEventFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE)
   {
      Print("XAU shadow: cannot open event log err=",GetLastError());
      return;
   }
   if(FileSize(h)==0)
      FileWrite(h,"event","session_id","seq_id","spec_id","side","core_bar_msc","confirm_bar_msc","entry_eligible_msc",
                  "emit_gc_tick_msc","xau_tick_msc","transport_ms","signal_age_ms","bid","ask","spread","atr20_prev_m5",
                  "entry","sl","tp","mfe_r","mae_r","r","reason","cooldown30_keep");
   FileSeek(h,0,SEEK_END);
   long transport=(long)xau_msc-(long)s.emit_gc_tick_msc;
   long age=(long)xau_msc-(long)s.entry_eligible_msc;
   FileWrite(h,event_type,s.session_id,s.seq_id,s.spec_id,s.side,(long)s.core_bar_msc,(long)s.confirm_bar_msc,
             (long)s.entry_eligible_msc,(long)s.emit_gc_tick_msc,(long)xau_msc,transport,age,
             DoubleToString(bid,g_xau_digits),DoubleToString(ask,g_xau_digits),DoubleToString(ask-bid,g_xau_digits),
             DoubleToString(g_atr,g_xau_digits),DoubleToString(g_entry,g_xau_digits),DoubleToString(g_sl,g_xau_digits),DoubleToString(g_tp,g_xau_digits),
             DoubleToString(g_mfe_r,6),DoubleToString(g_mae_r,6),DoubleToString(r_value,6),reason,s.cooldown_keep);
   FileFlush(h);
   FileClose(h);
}

bool ComputeATR20PrevClosed(double &atr)
{
   MqlRates r[];
   // start_pos=1 excludes current incomplete M5. Oldest copied bar is placed first in memory.
   int n=CopyRates(InpXAUSymbol,PERIOD_M5,1,400,r);
   if(n<25) return false;
   double a=0.0;
   bool seeded=false;
   int valid=0;
   for(int i=1;i<n;i++)
   {
      double tr=MathMax(r[i].high-r[i].low,
                        MathMax(MathAbs(r[i].high-r[i-1].close),MathAbs(r[i].low-r[i-1].close)));
      if(!seeded)
      {
         a=tr;
         seeded=true;
      }
      else a=((19.0*a)+tr)/20.0;
      valid++;
   }
   if(valid<20 || a<=0.0) return false;
   atr=a;
   return true;
}

bool ReadFieldString(const int h,string &v)
{
   if(FileIsEnding(h)) return false;
   v=FileReadString(h);
   return true;
}

bool ReadSignalRow(const int h,SSignal &s)
{
   string v;
   if(!ReadFieldString(h,s.protocol)) return false;
   if(!ReadFieldString(h,s.spec_id)) return false;
   if(!ReadFieldString(h,s.spec_sha)) return false;
   if(!ReadFieldString(h,s.session_id)) return false;
   if(!ReadFieldString(h,v)) return false; s.seq_id=(long)StringToInteger(v);
   if(!ReadFieldString(h,v)) return false; s.core_bar_msc=(ulong)StringToInteger(v);
   if(!ReadFieldString(h,v)) return false; s.confirm_bar_msc=(ulong)StringToInteger(v);
   if(!ReadFieldString(h,v)) return false; s.entry_eligible_msc=(ulong)StringToInteger(v);
   if(!ReadFieldString(h,v)) return false; s.emit_gc_tick_msc=(ulong)StringToInteger(v);
   if(!ReadFieldString(h,s.side)) return false;
   if(!ReadFieldString(h,v)) return false; s.confirm_offset=(int)StringToInteger(v);
   if(!ReadFieldString(h,v)) return false; s.core_delta_frac=StringToDouble(v);
   if(!ReadFieldString(h,v)) return false; s.core_loc=StringToDouble(v);
   if(!ReadFieldString(h,v)) return false; s.core_impact=StringToDouble(v);
   if(!ReadFieldString(h,v)) return false; s.confirm_open=StringToDouble(v);
   if(!ReadFieldString(h,v)) return false; s.confirm_close=StringToDouble(v);
   if(!ReadFieldString(h,v)) return false; s.confirm_delta=StringToDouble(v);
   if(!ReadFieldString(h,v)) return false; s.cooldown_keep=(int)StringToInteger(v);
   return true;
}

void RejectSignal(const SSignal &s,const MqlTick &q,const string reason)
{
   g_rejected++;
   double old_atr=g_atr,old_entry=g_entry,old_sl=g_sl,old_tp=g_tp,old_mfe=g_mfe_r,old_mae=g_mae_r;
   g_atr=g_entry=g_sl=g_tp=0.0;
   g_mfe_r=g_mae_r=0.0;
   LogEvent("REJECT",s,q.time_msc,q.bid,q.ask,reason,0.0);
   g_atr=old_atr;
   g_entry=old_entry;
   g_sl=old_sl;
   g_tp=old_tp;
   g_mfe_r=old_mfe;
   g_mae_r=old_mae;
   if(InpVerboseLog) Print("XAU SHADOW REJECT ",SignalKey(s)," ",reason);
}

void AcceptSignal(const SSignal &s,const MqlTick &q)
{
   if(g_active)
   {
      RejectSignal(s,q,"BUSY_SINGLE_POSITION");
      return;
   }
   long age=(long)q.time_msc-(long)s.entry_eligible_msc;
   if(age>InpMaxSignalAgeMs)
   {
      RejectSignal(s,q,"STALE_SIGNAL");
      return;
   }
   if(age < -1000)
   {
      RejectSignal(s,q,"XAU_QUOTE_BEHIND_ENTRY_CLOCK");
      return;
   }
   if(q.bid<=0.0 || q.ask<=0.0 || q.ask<q.bid)
   {
      RejectSignal(s,q,"INVALID_XAU_QUOTE");
      return;
   }
   if(!ComputeATR20PrevClosed(g_atr))
   {
      RejectSignal(s,q,"ATR20_NOT_READY");
      return;
   }

   g_trade_signal=s;
   g_entry=(s.side=="LONG" ? q.ask : q.bid);
   g_sl=(s.side=="LONG" ? g_entry-g_atr : g_entry+g_atr);
   g_tp=(s.side=="LONG" ? g_entry+TP_R*g_atr : g_entry-TP_R*g_atr);
   g_entry_msc=q.time_msc;
   g_expiry_msc=s.entry_eligible_msc+HOLD_MS;
   g_mfe_r=0.0;
   g_mae_r=0.0;
   g_active=true;
   g_accepted++;
   LogEvent("OPEN",s,q.time_msc,q.bid,q.ask,"SHADOW_ONLY",0.0);
   if(InpVerboseLog)
      PrintFormat("XAU SHADOW OPEN %s #%I64d entry=%.2f ATR=%.2f SL=%.2f TP=%.2f",s.side,s.seq_id,g_entry,g_atr,g_sl,g_tp);
}

void CloseShadow(const MqlTick &q,const double px,const string reason,const ulong exit_msc)
{
   if(!g_active) return;
   double r=(g_trade_signal.side=="LONG" ? (px-g_entry)/g_atr : (g_entry-px)/g_atr);
   LogEvent("CLOSE",g_trade_signal,exit_msc,q.bid,q.ask,reason,r);
   if(InpVerboseLog)
      PrintFormat("XAU SHADOW CLOSE %s #%I64d %s R=%+.3f",g_trade_signal.side,g_trade_signal.seq_id,reason,r);
   g_active=false;
   g_closed++;
}

void ManageQuote(const MqlTick &q)
{
   if(q.time_msc==0 || q.bid<=0.0 || q.ask<=0.0) return;

   if(g_active && g_last_quote_msc!=0 && q.time_msc-g_last_quote_msc>(ulong)InpSessionGapMs)
   {
      double px=(g_trade_signal.side=="LONG" ? g_last_bid : g_last_ask);
      MqlTick prev=q;
      prev.bid=g_last_bid;
      prev.ask=g_last_ask;
      prev.time_msc=g_last_quote_msc;
      CloseShadow(prev,px,"SESSION_GAP",g_last_quote_msc);
   }

   if(g_active && q.time_msc>g_expiry_msc)
   {
      double px=(g_trade_signal.side=="LONG" ? g_last_bid : g_last_ask);
      MqlTick prev=q;
      prev.bid=g_last_bid;
      prev.ask=g_last_ask;
      prev.time_msc=g_last_quote_msc;
      CloseShadow(prev,px,"TIME240",g_last_quote_msc);
   }

   if(g_active)
   {
      double px=(g_trade_signal.side=="LONG" ? q.bid : q.ask);
      double move=(g_trade_signal.side=="LONG" ? (px-g_entry)/g_atr : (g_entry-px)/g_atr);
      if(move>g_mfe_r) g_mfe_r=move;
      if(move<g_mae_r) g_mae_r=move;
      bool sl_hit=(g_trade_signal.side=="LONG" ? px<=g_sl : px>=g_sl);
      bool tp_hit=(g_trade_signal.side=="LONG" ? px>=g_tp : px<=g_tp);
      if(sl_hit)
         CloseShadow(q,g_sl,"SL",q.time_msc);
      else if(tp_hit)
         CloseShadow(q,g_tp,"TP3R",q.time_msc);
   }

   g_last_quote_msc=q.time_msc;
   g_last_bid=q.bid;
   g_last_ask=q.ask;
}

void UpdateXAUCursor(const MqlTick &q)
{
   if(q.time_msc>g_xau_cursor_msc)
   {
      g_xau_cursor_msc=q.time_msc;
      g_xau_seen_at_cursor=1;
   }
   else if(q.time_msc==g_xau_cursor_msc)
      g_xau_seen_at_cursor++;
}

void PollXAUTicks()
{
   if(g_xau_cursor_msc==0) return;
   MqlTick ticks[];
   int n=CopyTicks(InpXAUSymbol,ticks,COPY_TICKS_ALL,g_xau_cursor_msc,5000);
   if(n<=0) return;
   int skip_same=g_xau_seen_at_cursor;
   int seen_same=0;
   for(int i=0;i<n;i++)
   {
      if(ticks[i].time_msc<g_xau_cursor_msc) continue;
      if(ticks[i].time_msc==g_xau_cursor_msc && seen_same<skip_same)
      {
         seen_same++;
         continue;
      }
      ManageQuote(ticks[i]);
      UpdateXAUCursor(ticks[i]);
   }
}

void PollSignals(const MqlTick &q)
{
   int h=FileOpen(InpSignalFile,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE) return;

   if(!FileIsEnding(h))
      for(int i=0;i<18;i++) FileReadString(h);

   bool after_last=(g_last_seen_key=="");
   while(!FileIsEnding(h))
   {
      SSignal s;
      if(!ReadSignalRow(h,s)) break;
      string key=SignalKey(s);
      if(!after_last)
      {
         if(key==g_last_seen_key) after_last=true;
         continue;
      }
      if(key==g_last_seen_key) continue;
      g_last_seen_key=key;
      if(s.protocol!=PROTOCOL_VERSION)
      {
         RejectSignal(s,q,"PROTOCOL_MISMATCH");
         continue;
      }
      AcceptSignal(s,q);
   }
   FileClose(h);
}

void WriteHeartbeat()
{
   ulong now=(ulong)GetTickCount64();
   if(g_last_heartbeat_local!=0 && now-g_last_heartbeat_local<1000) return;
   g_last_heartbeat_local=now;
   MqlTick q;
   q.time_msc=0;
   q.bid=0.0;
   q.ask=0.0;
   SymbolInfoTick(InpXAUSymbol,q);
   int h=FileOpen(InpHeartbeatFile,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE) return;
   FileWrite(h,"protocol","xau_symbol","xau_tick_msc","bid","ask","active","accepted","closed","rejected","last_signal_key","status");
   FileWrite(h,PROTOCOL_VERSION,InpXAUSymbol,(long)q.time_msc,DoubleToString(q.bid,g_xau_digits),DoubleToString(q.ask,g_xau_digits),
             (g_active?1:0),g_accepted,g_closed,g_rejected,g_last_seen_key,"SHADOW_ZERO_ORDER_FUNCTIONS");
   FileFlush(h);
   FileClose(h);
}

int OnInit()
{
   if(InpPollMilliseconds<50 || InpMaxSignalAgeMs<1000 || InpSessionGapMs<10000)
      return INIT_PARAMETERS_INCORRECT;
   if(!SymbolSelect(InpXAUSymbol,true))
   {
      Print("XAU shadow: cannot select symbol ",InpXAUSymbol," err=",GetLastError());
      return INIT_FAILED;
   }
   g_xau_digits=(int)SymbolInfoInteger(InpXAUSymbol,SYMBOL_DIGITS);
   MqlTick q;
   if(SymbolInfoTick(InpXAUSymbol,q))
   {
      g_last_quote_msc=q.time_msc;
      g_last_bid=q.bid;
      g_last_ask=q.ask;
      g_xau_cursor_msc=q.time_msc;
      MqlTick same[];
      int ns=CopyTicksRange(InpXAUSymbol,same,COPY_TICKS_ALL,q.time_msc,q.time_msc);
      g_xau_seen_at_cursor=(ns>0 ? ns : 1);
   }
   if(!EventSetMillisecondTimer(InpPollMilliseconds))
   {
      Print("XAU shadow: timer setup failed err=",GetLastError());
      return INIT_FAILED;
   }
   WriteHeartbeat();
   Print("XAU_AEIF_SHADOW_EXECUTOR_001 started. ZERO ORDER FUNCTIONS. symbol=",InpXAUSymbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   WriteHeartbeat();
}

void OnTimer()
{
   PollXAUTicks();
   MqlTick q;
   if(!SymbolInfoTick(InpXAUSymbol,q)) return;
   PollSignals(q);
   WriteHeartbeat();
}

// Intentionally no trade/order/position-management API calls.
