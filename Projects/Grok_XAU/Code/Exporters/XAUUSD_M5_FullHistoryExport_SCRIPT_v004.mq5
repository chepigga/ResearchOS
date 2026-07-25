//+------------------------------------------------------------------+
//| XAUUSD_M5_FullHistoryExport_SCRIPT_v004.mq5                      |
//| One-shot MQL5 Script: exports complete XAUUSD M5 history to CSV. |
//|                                                                  |
//| IMPORTANT:                                                       |
//| Before launch set MT5:                                           |
//| Tools -> Options -> Charts -> Max bars in chart = 1000000        |
//| Then restart MetaTrader 5.                                       |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs
#property version   "1.00"
#property description "Exports complete M5 OHLC history with hard coverage checks."

input string   InpSymbol             = "XAUUSD";
input datetime InpFrom               = D'2022.06.01 00:00';
input datetime InpToExclusive        = D'2026.07.24 00:00';
input string   InpFileName           = "XAUUSD_M5_20220601_20260723_SCRIPT_FULL.csv";
input bool     InpUseCommonFolder    = true;

// Hard safeguards against another truncated 100k-bar export.
input long     InpRequiredMaxBars    = 500000;
input long     InpMinimumRows        = 250000;
input datetime InpLatestAllowedFirst = D'2022.06.03 23:59';
input datetime InpEarliestAllowedLast= D'2026.07.23 23:45';
input bool     InpAllowIncomplete    = false;

// History synchronization settings.
input int      InpRetries            = 30;
input int      InpRetryDelayMs       = 1000;
input int      InpFlushEvery         = 10000;

string OutputPath()
{
   if(InpUseCommonFolder)
      return TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\" + InpFileName;

   return TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL5\\Files\\" + InpFileName;
}

bool CoverageIsComplete(const int copied,
                        const datetime first_bar,
                        const datetime last_bar)
{
   if((long)copied < InpMinimumRows)
      return false;
   if(first_bar <= 0 || first_bar > InpLatestAllowedFirst)
      return false;
   if(last_bar <= 0 || last_bar < InpEarliestAllowedLast)
      return false;

   return true;
}

int LoadFullHistory(MqlRates &rates[])
{
   ArrayFree(rates);
   ArraySetAsSeries(rates, false);

   int best_copied = -1;
   datetime best_first = 0;
   datetime best_last  = 0;

   for(int attempt = 1; attempt <= InpRetries; attempt++)
   {
      ResetLastError();
      int copied = CopyRates(InpSymbol,
                             PERIOD_M5,
                             InpFrom,
                             InpToExclusive - 1,
                             rates);
      int error_code = GetLastError();

      datetime first_bar = 0;
      datetime last_bar  = 0;
      if(copied > 0)
      {
         first_bar = rates[0].time;
         last_bar  = rates[copied - 1].time;
      }

      if(copied > best_copied)
      {
         best_copied = copied;
         best_first  = first_bar;
         best_last   = last_bar;
      }

      PrintFormat("EXPORT_SYNC attempt=%d/%d copied=%d first=%s last=%s err=%d synchronized=%s",
                  attempt,
                  InpRetries,
                  copied,
                  first_bar > 0 ? TimeToString(first_bar, TIME_DATE | TIME_MINUTES) : "NONE",
                  last_bar  > 0 ? TimeToString(last_bar,  TIME_DATE | TIME_MINUTES) : "NONE",
                  error_code,
                  (bool)SeriesInfoInteger(InpSymbol, PERIOD_M5, SERIES_SYNCHRONIZED) ? "true" : "false");

      if(CoverageIsComplete(copied, first_bar, last_bar))
         return copied;

      if(attempt < InpRetries)
         Sleep(InpRetryDelayMs);
   }

   PrintFormat("EXPORT_HISTORY_INCOMPLETE best_copied=%d best_first=%s best_last=%s",
               best_copied,
               best_first > 0 ? TimeToString(best_first, TIME_DATE | TIME_MINUTES) : "NONE",
               best_last  > 0 ? TimeToString(best_last,  TIME_DATE | TIME_MINUTES) : "NONE");

   return best_copied;
}

bool WriteCsv(const MqlRates &rates[], const int copied)
{
   int flags = FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ;
   if(InpUseCommonFolder)
      flags |= FILE_COMMON;

   ResetLastError();
   int file_handle = FileOpen(InpFileName, flags, ';');
   if(file_handle == INVALID_HANDLE)
   {
      PrintFormat("EXPORT_FILE_FAIL file=%s err=%d", InpFileName, GetLastError());
      return false;
   }

   FileWrite(file_handle,
             "time", "open", "high", "low", "close",
             "tick_volume", "spread", "real_volume");

   int digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   datetime previous_time = 0;
   long rows_written = 0;
   long duplicate_rows = 0;
   long invalid_ohlc_rows = 0;

   for(int i = 0; i < copied; i++)
   {
      MqlRates bar = rates[i];

      if(bar.time < InpFrom || bar.time >= InpToExclusive)
         continue;

      if(previous_time > 0 && bar.time <= previous_time)
      {
         duplicate_rows++;
         continue;
      }

      bool valid_ohlc = (bar.high >= bar.low &&
                         bar.high >= bar.open &&
                         bar.high >= bar.close &&
                         bar.low  <= bar.open &&
                         bar.low  <= bar.close);
      if(!valid_ohlc)
      {
         invalid_ohlc_rows++;
         continue;
      }

      FileWrite(file_handle,
                TimeToString(bar.time, TIME_DATE | TIME_MINUTES),
                DoubleToString(bar.open,  digits),
                DoubleToString(bar.high,  digits),
                DoubleToString(bar.low,   digits),
                DoubleToString(bar.close, digits),
                bar.tick_volume,
                bar.spread,
                bar.real_volume);

      previous_time = bar.time;
      rows_written++;

      if(InpFlushEvery > 0 && (rows_written % InpFlushEvery) == 0)
      {
         FileFlush(file_handle);
         PrintFormat("EXPORT_PROGRESS rows=%I64d last=%s",
                     rows_written,
                     TimeToString(previous_time, TIME_DATE | TIME_MINUTES));
      }
   }

   FileFlush(file_handle);
   FileClose(file_handle);

   PrintFormat("EXPORT_DONE rows=%I64d duplicates_skipped=%I64d invalid_ohlc_skipped=%I64d path=%s",
               rows_written,
               duplicate_rows,
               invalid_ohlc_rows,
               OutputPath());

   if(rows_written < InpMinimumRows)
   {
      PrintFormat("EXPORT_FAIL written rows=%I64d below minimum=%I64d",
                  rows_written,
                  InpMinimumRows);
      return false;
   }

   if(duplicate_rows > 0 || invalid_ohlc_rows > 0)
      Print("EXPORT_WARNING some invalid rows were skipped; review Journal before research use");

   return true;
}

void OnStart()
{
   Print("============================================================");
   Print("XAUUSD M5 FULL HISTORY EXPORT SCRIPT v004");
   Print("============================================================");

   if(InpFrom >= InpToExclusive)
   {
      Print("EXPORT_ABORT invalid date interval");
      return;
   }

   if(InpRetries < 1 || InpRetryDelayMs < 0)
   {
      Print("EXPORT_ABORT invalid retry settings");
      return;
   }

   if(!SymbolSelect(InpSymbol, true))
   {
      PrintFormat("EXPORT_ABORT SymbolSelect failed symbol=%s err=%d",
                  InpSymbol,
                  GetLastError());
      return;
   }

   long terminal_max_bars = TerminalInfoInteger(TERMINAL_MAXBARS);
   datetime server_first = (datetime)SeriesInfoInteger(InpSymbol,
                                                       PERIOD_M5,
                                                       SERIES_SERVER_FIRSTDATE);
   datetime local_first = (datetime)SeriesInfoInteger(InpSymbol,
                                                      PERIOD_M5,
                                                      SERIES_FIRSTDATE);

   PrintFormat("EXPORT_ENV symbol=%s max_bars=%I64d required=%I64d server_first=%s local_first=%s",
               InpSymbol,
               terminal_max_bars,
               InpRequiredMaxBars,
               server_first > 0 ? TimeToString(server_first, TIME_DATE | TIME_MINUTES) : "UNKNOWN",
               local_first  > 0 ? TimeToString(local_first,  TIME_DATE | TIME_MINUTES) : "UNKNOWN");

   if(terminal_max_bars < InpRequiredMaxBars && !InpAllowIncomplete)
   {
      PrintFormat("EXPORT_ABORT TERMINAL_MAXBARS=%I64d is too low. Set Tools -> Options -> Charts -> Max bars in chart to 1000000, restart MT5, then run this script again.",
                  terminal_max_bars);
      return;
   }

   MqlRates rates[];
   int copied = LoadFullHistory(rates);
   if(copied <= 0)
   {
      PrintFormat("EXPORT_ABORT no M5 history copied err=%d", GetLastError());
      return;
   }

   datetime first_bar = rates[0].time;
   datetime last_bar  = rates[copied - 1].time;
   bool complete = CoverageIsComplete(copied, first_bar, last_bar);

   PrintFormat("EXPORT_AUDIT copied=%d first=%s last=%s complete=%s",
               copied,
               TimeToString(first_bar, TIME_DATE | TIME_MINUTES),
               TimeToString(last_bar,  TIME_DATE | TIME_MINUTES),
               complete ? "true" : "false");

   if(!complete && !InpAllowIncomplete)
   {
      Print("EXPORT_ABORT history is incomplete. No CSV was created.");
      Print("Check broker history depth and Max bars in chart, then restart MT5.");
      return;
   }

   if(!WriteCsv(rates, copied))
   {
      Print("EXPORT_ABORT CSV write or validation failed");
      return;
   }

   Print("EXPORT_SUCCESS upload this file for FT_REJECTED_001:");
   Print(OutputPath());
}
//+------------------------------------------------------------------+
