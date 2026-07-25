//+------------------------------------------------------------------+
#property strict
#property script_show_inputs
void OnStart()
{
   long stops  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freeze = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   PrintFormat("AK47_SYMBOL_META symbol=%s stops_level=%I64d freeze_level=%I64d max=%I64d",
               _Symbol, stops, freeze, MathMax(stops, freeze));
}
//+------------------------------------------------------------------+
