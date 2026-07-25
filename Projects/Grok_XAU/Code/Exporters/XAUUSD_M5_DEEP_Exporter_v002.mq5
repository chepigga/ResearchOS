//+------------------------------------------------------------------+
//| XAUUSD_M5_DEEP_Exporter_v002.mq5                                |
//| Chunked same-feed XAUUSD M5 export for FT_DEEP_001.             |
//| Avoids the 100,000-bar truncation seen with one large CopyRates. |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input string   InpSymbol       = "XAUUSD";
input datetime InpFrom         = D'2022.06.01 00:00';
input datetime InpToExclusive  = D'2026.07.24 00:00';
input int      InpChunkDays    = 30;
input int      InpRetries      = 10;
input int      InpRetryDelayMs = 500;
input string   InpFileName     = "XAUUSD_M5_20220601_20260723_FULL.csv";

bool CopyChunk(datetime from_time, datetime to_time, MqlRates &rates[])
{
   ArrayFree(rates);
   ArraySetAsSeries(rates,false);
   for(int attempt=1; attempt<=InpRetries; attempt++)
   {
      ResetLastError();
      int copied=CopyRates(InpSymbol,PERIOD_M5,from_time,to_time,rates);
      if(copied>0) return true;
      int err=GetLastError();
      PrintFormat("EXPORT_RETRY attempt=%d/%d from=%s to=%s copied=%d err=%d",
                  attempt,InpRetries,
                  TimeToString(from_time,TIME_DATE|TIME_MINUTES),
                  TimeToString(to_time,TIME_DATE|TIME_MINUTES),copied,err);
      Sleep(InpRetryDelayMs);
   }
   return false;
}

void OnStart()
{
   if(InpFrom>=InpToExclusive)
   {
      Print("EXPORT_FAIL invalid interval");
      return;
   }
   if(InpChunkDays<1)
   {
      Print("EXPORT_FAIL InpChunkDays must be >=1");
      return;
   }
   if(!SymbolSelect(InpSymbol,true))
   {
      PrintFormat("EXPORT_FAIL SymbolSelect %s err=%d",InpSymbol,GetLastError());
      return;
   }

   int h=FileOpen(InpFileName,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h==INVALID_HANDLE)
   {
      PrintFormat("EXPORT_FAIL FileOpen file=%s err=%d",InpFileName,GetLastError());
      return;
   }
   FileWriteString(h,"time;open;high;low;close;tick_volume;spread;real_volume\r\n");

   const int digits=(int)SymbolInfoInteger(InpSymbol,SYMBOL_DIGITS);
   const int chunk_seconds=InpChunkDays*86400;
   datetime cursor=InpFrom;
   datetime last_written=0;
   datetime first_written=0;
   long total_rows=0;
   int failed_chunks=0;

   while(cursor<InpToExclusive)
   {
      datetime chunk_end=cursor+chunk_seconds;
      if(chunk_end>InpToExclusive) chunk_end=InpToExclusive;
      datetime request_end=chunk_end-1;
      MqlRates rates[];

      if(!CopyChunk(cursor,request_end,rates))
      {
         failed_chunks++;
         PrintFormat("EXPORT_CHUNK_FAIL from=%s to=%s",
                     TimeToString(cursor,TIME_DATE|TIME_MINUTES),
                     TimeToString(request_end,TIME_DATE|TIME_MINUTES));
         cursor=chunk_end;
         continue;
      }

      int copied=ArraySize(rates);
      long written_chunk=0;
      for(int i=0;i<copied;i++)
      {
         datetime bt=rates[i].time;
         if(bt<InpFrom || bt>=InpToExclusive) continue;
         if(last_written>0 && bt<=last_written) continue;

         string line=
            TimeToString(bt,TIME_DATE|TIME_MINUTES)+";"+
            DoubleToString(rates[i].open,digits)+";"+
            DoubleToString(rates[i].high,digits)+";"+
            DoubleToString(rates[i].low,digits)+";"+
            DoubleToString(rates[i].close,digits)+";"+
            IntegerToString((long)rates[i].tick_volume)+";"+
            IntegerToString(rates[i].spread)+";"+
            IntegerToString((long)rates[i].real_volume)+"\r\n";
         FileWriteString(h,line);

         if(first_written==0) first_written=bt;
         last_written=bt;
         total_rows++;
         written_chunk++;
      }

      PrintFormat("EXPORT_CHUNK_OK from=%s to=%s copied=%d written=%I64d total=%I64d",
                  TimeToString(cursor,TIME_DATE|TIME_MINUTES),
                  TimeToString(request_end,TIME_DATE|TIME_MINUTES),
                  copied,written_chunk,total_rows);
      FileFlush(h);
      cursor=chunk_end;
   }

   FileFlush(h);
   FileClose(h);

   PrintFormat("EXPORT_DONE file=%s rows=%I64d first=%s last=%s failed_chunks=%d path=%s\\MQL5\\Files\\%s",
               InpFileName,total_rows,
               first_written>0 ? TimeToString(first_written,TIME_DATE|TIME_MINUTES) : "NONE",
               last_written>0 ? TimeToString(last_written,TIME_DATE|TIME_MINUTES) : "NONE",
               failed_chunks,TerminalInfoString(TERMINAL_DATA_PATH),InpFileName);

   if(total_rows<=100000)
      Print("EXPORT_WARNING rows<=100000: verify terminal/broker history depth; expected full 2022-06..2026-07 is materially larger.");
   if(first_written>D'2022.07.01 00:00')
      Print("EXPORT_WARNING insufficient 200-D1 warmup before 2023-01-01.");
   if(last_written<D'2026.07.23 23:45')
      Print("EXPORT_WARNING tail incomplete through 2026-07-23.");
   if(failed_chunks>0)
      Print("EXPORT_WARNING one or more chunks failed; do not use this file for FT_DEEP until repaired.");
}
//+------------------------------------------------------------------+
