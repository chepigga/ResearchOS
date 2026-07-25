//+------------------------------------------------------------------+
//| XAUUSD_M5_DEEP_Exporter_v001.mq5                                |
//| Export same-feed XAUUSD M5 with 200-D1 warmup for FT_DEEP_001.  |
//| Research tool only; no trading logic.                            |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input string InpSymbol = "XAUUSD";
input datetime InpFrom = D'2022.06.01 00:00'; // >=200 D1 warmup before 2023-01-01
input datetime InpTo   = D'2026.07.24 00:00'; // exclusive; last requested day 2026-07-23
input string InpFileName = "XAUUSD_M5_20220601_20260723.csv";

void OnStart()
{
   if(!SymbolSelect(InpSymbol,true))
   {
      PrintFormat("EXPORT_FAIL SymbolSelect %s err=%d",InpSymbol,GetLastError());
      return;
   }

   MqlRates rates[];
   ArraySetAsSeries(rates,false);
   ResetLastError();
   int copied=CopyRates(InpSymbol,PERIOD_M5,InpFrom,InpTo,rates);
   if(copied<=0)
   {
      PrintFormat("EXPORT_FAIL CopyRates rows=%d err=%d",copied,GetLastError());
      return;
   }

   int h=FileOpen(InpFileName,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h==INVALID_HANDLE)
   {
      PrintFormat("EXPORT_FAIL FileOpen file=%s err=%d",InpFileName,GetLastError());
      return;
   }

   FileWriteString(h,"time;open;high;low;close;tick_volume;spread;real_volume\r\n");
   int digits=(int)SymbolInfoInteger(InpSymbol,SYMBOL_DIGITS);
   for(int i=0;i<copied;i++)
   {
      string line=
         TimeToString(rates[i].time,TIME_DATE|TIME_MINUTES)+";"+
         DoubleToString(rates[i].open,digits)+";"+
         DoubleToString(rates[i].high,digits)+";"+
         DoubleToString(rates[i].low,digits)+";"+
         DoubleToString(rates[i].close,digits)+";"+
         IntegerToString((long)rates[i].tick_volume)+";"+
         IntegerToString(rates[i].spread)+";"+
         IntegerToString((long)rates[i].real_volume)+"\r\n";
      FileWriteString(h,line);
   }
   FileFlush(h);
   FileClose(h);

   PrintFormat("EXPORT_OK file=%s rows=%d first=%s last=%s path=%s\\MQL5\\Files\\%s",
      InpFileName,copied,
      TimeToString(rates[0].time,TIME_DATE|TIME_MINUTES),
      TimeToString(rates[copied-1].time,TIME_DATE|TIME_MINUTES),
      TerminalInfoString(TERMINAL_DATA_PATH),InpFileName);

   if(rates[0].time>D'2022.07.01 00:00')
      Print("EXPORT_WARNING: insufficient 200-D1 warmup before 2023-01-01; load older M5 history and rerun.");
   if(rates[copied-1].time<D'2026.07.23 23:45')
      Print("EXPORT_WARNING: OOS tail incomplete; load history through 2026-07-23 and rerun.");
}
//+------------------------------------------------------------------+
