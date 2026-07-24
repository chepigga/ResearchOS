//+------------------------------------------------------------------+
//| XAUUSD_M15_Exporter_v001.mq5                                    |
//| Project: Grok XAU / BH_OOS_001v2                                |
//| Purpose: export same-broker M15 OHLCV bars for frozen OOS test   |
//| Date: 2026-07-24                                                 |
//| Status: experimental exporter; causal raw-data extraction        |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input string          InpSymbol       = "XAUUSD";
input ENUM_TIMEFRAMES InpTimeframe    = PERIOD_M15;
input string          InpStart        = "2024.12.01 00:00";
input string          InpEndExclusive = "2026.07.24 00:00";
input string          InpFileName     = "XAUUSD_M15_2024-12-01_2026-07-23.csv";
input bool            InpUseCommon    = false; // false = Terminal Data Folder/MQL5/Files

string TfName(const ENUM_TIMEFRAMES tf)
{
   return EnumToString(tf);
}

void OnStart()
{
   ResetLastError();

   datetime from = StringToTime(InpStart);
   datetime to_exclusive = StringToTime(InpEndExclusive);
   if(from <= 0 || to_exclusive <= from)
   {
      PrintFormat("EXPORT_FAIL invalid range: from=%s to_exclusive=%s error=%d",
                  InpStart, InpEndExclusive, GetLastError());
      return;
   }

   if(!SymbolSelect(InpSymbol, true))
   {
      PrintFormat("EXPORT_FAIL SymbolSelect(%s) error=%d", InpSymbol, GetLastError());
      return;
   }

   MqlRates rates[];
   ArraySetAsSeries(rates, false);

   // End is exclusive by specification; CopyRates end is inclusive.
   int copied = CopyRates(InpSymbol, InpTimeframe, from, to_exclusive - 1, rates);
   if(copied <= 0)
   {
      PrintFormat("EXPORT_FAIL CopyRates symbol=%s tf=%s copied=%d error=%d",
                  InpSymbol, TfName(InpTimeframe), copied, GetLastError());
      return;
   }

   int flags = FILE_WRITE | FILE_CSV | FILE_ANSI;
   if(InpUseCommon)
      flags |= FILE_COMMON;

   int handle = FileOpen(InpFileName, flags, ',');
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("EXPORT_FAIL FileOpen(%s) error=%d", InpFileName, GetLastError());
      return;
   }

   int digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   FileWrite(handle,
             "time", "open", "high", "low", "close",
             "tick_volume", "spread_points", "real_volume");

   int written = 0;
   datetime first_time = 0;
   datetime last_time = 0;

   for(int i = 0; i < copied; i++)
   {
      if(rates[i].time < from || rates[i].time >= to_exclusive)
         continue;

      FileWrite(handle,
                TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES),
                DoubleToString(rates[i].open, digits),
                DoubleToString(rates[i].high, digits),
                DoubleToString(rates[i].low, digits),
                DoubleToString(rates[i].close, digits),
                (long)rates[i].tick_volume,
                rates[i].spread,
                (long)rates[i].real_volume);

      if(written == 0)
         first_time = rates[i].time;
      last_time = rates[i].time;
      written++;
   }

   FileFlush(handle);
   FileClose(handle);

   string base_path = InpUseCommon
                      ? TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\"
                      : TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL5\\Files\\";

   PrintFormat("EXPORT_OK file=%s rows=%d first=%s last=%s broker=%s account=%I64d",
               base_path + InpFileName,
               written,
               TimeToString(first_time, TIME_DATE | TIME_MINUTES),
               TimeToString(last_time, TIME_DATE | TIME_MINUTES),
               AccountInfoString(ACCOUNT_SERVER),
               AccountInfoInteger(ACCOUNT_LOGIN));

   if(written != copied)
      PrintFormat("EXPORT_NOTE CopyRates=%d written=%d after explicit range filter", copied, written);
}
//+------------------------------------------------------------------+
