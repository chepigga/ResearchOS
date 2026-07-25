//+------------------------------------------------------------------+
//| XAUUSD_M5_TesterStreamExporter_v003.mq5                          |
//| Streams every CLOSED M5 bar while running inside Strategy Tester.|
//| This bypasses terminal "Max bars in chart" / 100k history limits. |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"

input string   InpSymbol      = "XAUUSD";
input datetime InpFrom        = D'2022.06.01 00:00';
input datetime InpToExclusive = D'2026.07.24 00:00';
input string   InpFileName    = "XAUUSD_M5_20220601_20260723_TESTER_FULL.csv";
input bool     InpUseCommon   = true;
input int      InpFlushEvery  = 1000;

int      g_file          = INVALID_HANDLE;
datetime g_currentBar    = 0;
datetime g_lastWritten   = 0;
datetime g_firstWritten  = 0;
long     g_rows          = 0;
int      g_digits        = 2;

bool OpenOutput()
{
   int flags = FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE;
   if(InpUseCommon)
      flags |= FILE_COMMON;

   ResetLastError();
   g_file = FileOpen(InpFileName, flags, ';');
   if(g_file == INVALID_HANDLE && InpUseCommon)
   {
      int common_error = GetLastError();
      PrintFormat("EXPORT_COMMON_FAIL err=%d; retrying agent-local", common_error);
      flags = FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE;
      ResetLastError();
      g_file = FileOpen(InpFileName, flags, ';');
   }

   if(g_file == INVALID_HANDLE)
   {
      PrintFormat("EXPORT_FILE_FAIL file=%s err=%d", InpFileName, GetLastError());
      return false;
   }

   FileWrite(g_file,
             "time", "open", "high", "low", "close",
             "tick_volume", "spread", "real_volume");
   FileFlush(g_file);
   return true;
}

bool WriteRate(const MqlRates &bar)
{
   if(bar.time < InpFrom || bar.time >= InpToExclusive)
      return true;
   if(g_lastWritten > 0 && bar.time <= g_lastWritten)
      return true;

   FileWrite(g_file,
             TimeToString(bar.time, TIME_DATE | TIME_MINUTES),
             DoubleToString(bar.open,  g_digits),
             DoubleToString(bar.high,  g_digits),
             DoubleToString(bar.low,   g_digits),
             DoubleToString(bar.close, g_digits),
             (long)bar.tick_volume,
             bar.spread,
             (long)bar.real_volume);

   if(g_firstWritten == 0)
      g_firstWritten = bar.time;
   g_lastWritten = bar.time;
   g_rows++;

   if(InpFlushEvery > 0 && (g_rows % InpFlushEvery) == 0)
   {
      FileFlush(g_file);
      PrintFormat("EXPORT_PROGRESS rows=%I64d last=%s",
                  g_rows, TimeToString(g_lastWritten, TIME_DATE | TIME_MINUTES));
   }
   return true;
}

// Write every bar that is already CLOSED before `exclusive_end`.
void FlushClosedBars(datetime exclusive_end)
{
   if(g_file == INVALID_HANDLE || exclusive_end <= InpFrom)
      return;

   datetime from_time = InpFrom;
   if(g_lastWritten > 0)
      from_time = g_lastWritten + PeriodSeconds(PERIOD_M5);

   datetime to_time = exclusive_end - 1;
   if(to_time < from_time)
      return;
   if(from_time >= InpToExclusive)
      return;
   if(to_time >= InpToExclusive)
      to_time = InpToExclusive - 1;

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   ResetLastError();
   int copied = CopyRates(InpSymbol, PERIOD_M5, from_time, to_time, rates);
   if(copied <= 0)
   {
      int err = GetLastError();
      // Normal before the first requested bar; otherwise log for diagnosis.
      if(exclusive_end > InpFrom)
         PrintFormat("EXPORT_COPY_FAIL from=%s to=%s copied=%d err=%d",
                     TimeToString(from_time, TIME_DATE | TIME_MINUTES),
                     TimeToString(to_time, TIME_DATE | TIME_MINUTES), copied, err);
      return;
   }

   for(int i = 0; i < copied; i++)
      WriteRate(rates[i]);
}

int OnInit()
{
   if(InpFrom >= InpToExclusive)
   {
      Print("EXPORT_INIT_FAIL invalid date interval");
      return INIT_PARAMETERS_INCORRECT;
   }

   if(!SymbolSelect(InpSymbol, true))
   {
      PrintFormat("EXPORT_INIT_FAIL SymbolSelect %s err=%d", InpSymbol, GetLastError());
      return INIT_FAILED;
   }

   g_digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   if(!OpenOutput())
      return INIT_FAILED;

   g_currentBar = iTime(InpSymbol, PERIOD_M5, 0);
   PrintFormat("EXPORT_INIT_OK symbol=%s from=%s toExclusive=%s file=%s",
               InpSymbol,
               TimeToString(InpFrom, TIME_DATE | TIME_MINUTES),
               TimeToString(InpToExclusive, TIME_DATE | TIME_MINUTES),
               InpFileName);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   datetime bar0 = iTime(InpSymbol, PERIOD_M5, 0);
   if(bar0 <= 0)
      return;

   if(g_currentBar == 0)
   {
      g_currentBar = bar0;
      return;
   }

   if(bar0 != g_currentBar)
   {
      // `bar0` is the open time of the new/current bar, so everything before it is closed.
      FlushClosedBars(bar0);
      g_currentBar = bar0;
   }
}

void OnDeinit(const int reason)
{
   // Do not export the current unfinished bar. The test must continue at least
   // one M5 bar beyond InpToExclusive so the final requested bar is flushed.
   datetime bar0 = iTime(InpSymbol, PERIOD_M5, 0);
   if(bar0 > 0)
      FlushClosedBars(bar0);

   if(g_file != INVALID_HANDLE)
   {
      FileFlush(g_file);
      FileClose(g_file);
      g_file = INVALID_HANDLE;
   }

   string first_text = (g_firstWritten > 0)
                       ? TimeToString(g_firstWritten, TIME_DATE | TIME_MINUTES)
                       : "NONE";
   string last_text  = (g_lastWritten > 0)
                       ? TimeToString(g_lastWritten, TIME_DATE | TIME_MINUTES)
                       : "NONE";

   PrintFormat("EXPORT_DONE reason=%d rows=%I64d first=%s last=%s file=%s",
               reason, g_rows, first_text, last_text, InpFileName);

   if(g_firstWritten > D'2022.06.01 00:00')
      Print("EXPORT_WARNING first bar is later than requested warmup start");
   if(g_lastWritten < D'2026.07.23 23:45')
      Print("EXPORT_WARNING tail is incomplete; run tester through at least 2026.07.24");
}
//+------------------------------------------------------------------+
