//+------------------------------------------------------------------+
//| AK47_H1_RS001_v2.05                                              |
//| v2.05 (2026-10-22): ВИПРАВЛЕННЯ ОДИНИЦЬ І РИЗИКУ для XAUUSD.       |
//|  1. Трейлінг/БУ були в «піпсах» форексу: 8/3 піпса = $0.08/$0.03 на |
//|     золоті -> стоп за 3 центи від ціни, вихід на першому тіку      |
//|     (тестер: 93% WR, сер. +$0.38 — нереалізовно при спреді $0.2+). |
//|     Тепер БУ/трейлінг задаються в R (частках стопу): старт 1R,     |
//|     відстань 1R, мін. крок 0.1R; стоп не ближче за                 |
//|     max(stops/freeze level) + поточний спред.                      |
//|  2. Ризик: InpBaseRisk > InpMaxRiskPct (2%) -> INIT_FAILED.        |
//|     Якщо маржі не вистачає — угода ПРОПУСКАЄТЬСЯ (раніше мінлот).  |
//|  3. Спред-фільтр 500 пт ($5) -> 60 пт ($0.60).                     |
//|  4. Трейлінг за замовчуванням ВИМК. (заморожена геометрія).        |
//|  SL/TP у «піпсах» = центах золота: 3700 = $37, 9700 = $97 (без змін).|
//| H1 no-trailing breakout (frozen H1_ALL candidate) + RS-001        |
//| PER-DIRECTION shadow-EV gate + D1-bias filter for BUY.            |
//|                                                                    |
//| v2.03 CHANGE (2026-07-29): 10-point external code review response.|
//| Кожен пункт нижче -- підтверджений проти реального коду v2.02      |
//| перед виправленням (не прийнято на віру).                         |
//|  1. Tester/live gate-state isolation (leakage fix, CRITICAL):      |
//|     у MQL_TESTER стан НЕ читається/НЕ пишеться з Common\Files --   |
//|     кожен backtest стартує з чистого стану. Для live/forward ім'я  |
//|     файлу тепер включає account+symbol+period+magic+SL/TP+         |
//|     gate-пороги+D1-налаштування+версію схеми -- несумісний прогін  |
//|     більше не підхоплює чужий/застарілий стан.                    |
//|  2. 75/75/7 статус явно позначено WATCH (не GO) у INIT_OK-логу --  |
//|     TZ-RS001-PERDIR-LOOKBACK-001 §3 (2022-2023 контроль) не        |
//|     виконано; це не мовчазне замовчування, а видимий рантайм-запис.|
//|  3. Shadow-модуль документовано явно як measurement of directional |
//|     regime, NOT a replica of the real single-position OCO path --  |
//|     подвійна парність (Addendum п.10) для нього ще не показана.    |
//|  4. OnTradeTransaction: негайне скасування sibling pending на факт |
//|     філу (TRADE_TRANSACTION_DEAL_ADD), не чекаючи наступного тіку  |
//|     -- звужує race-вікно подвійного входу на hedging-акаунті.      |
//|  5. OrderSend/OrderModify/OrderDelete: перевірка result.retcode,   |
//|     повне логування (retcode/comment/order/deal/price/volume).     |
//|  6. ORDER_FILLING визначається динамічно з SYMBOL_FILLING_MODE,    |
//|     не захардкожений FOK.                                          |
//|  7. Streak: net-profit (profit+swap+commission), агрегація за      |
//|     POSITION_ID (не за окремим deal), трекінг за deal ticket       |
//|     (не за часом -- уникає колізій однакового timestamp),          |
//|     персистентність loss_streak через рестарт.                     |
//|  8. GetBiasD1(): явне розрізнення NEUTRAL(0) від DATA_ERROR(-2) --  |
//|     фільтр тепер whitelist (дозволяє лише BULL/NEUTRAL), не        |
//|     blacklist -- помилка даних більше не дозволяє BUY за замовч.   |
//|  9. Prop-safety шар: daily DD guard, overall DD guard, max spread, |
//|     max trades/day, trading-permission checks, OrderCheck() перед  |
//|     реальним входом, hard lot cap, emergency lock (персистентний). |
//| Пороги RS-001 (75/75/7) НЕ змінені цим патчем -- статус лишається  |
//| WATCH, як і був. Forward demo only. Live NOT authorized.           |
//|                                                                    |
//| v2.04 CHANGE (2026-07-29): InpRequireGateB/S (default true, нічого|
//| не змінює за замовчуванням) -- дозволяє вимкнути вимогу RS-001     |
//| gate окремо для BUY/SELL, щоб ізольовано перевірити внесок D1-     |
//| фільтра без gate-обмеження. Мотивація: реальний Тестер-прогін      |
//| 2026.01-07 показав RS001_v2 (77 угод, $3525, PF1.10) суттєво       |
//| гіршим за BASELINE без жодних гейтів (236 угод, $8463, PF1.22) --  |
//| потрібен ізольований тест, щоб довести, що причина саме в WATCH-   |
//| статусі RS-001-порогів (лаг/надмірна обмежувальність), а не в D1.  |
//+------------------------------------------------------------------+
#property copyright "AK47 research chain"
#property version   "2.05"
#property description "H1 breakout + per-direction RS-001 gate + D1-bias filter + prop-safety layer. DEMO FORWARD ONLY."

//--- INPUT PARAMETERS
input group "=== Money Management (Anti-Martingale) ==="
input int      InpMagicNumber    = 999100;
input double   InpBaseRisk       = 0.5;     // % балансу на угоду (реальний ризик)
input double   InpMaxRiskPct     = 2.0;     // v2.05: запобіжник — більше не дозволено
input double   InpRiskFactor     = 0.5;
input int      InpMaxLossStreak  = 3;

input group "=== Strategy Geometry (FROZEN: H1_ALL candidate) ==="
input int      InpSLPips         = 3700;
input int      InpTPPips         = 9700;
input int      InpPaddingPips    = 5;

input group "=== Exit Logic (FROZEN OFF for H1_ALL) ==="
input bool     InpUseBreakeven   = false;
input double   InpBE_TriggerR    = 1.0;     // v2.05: БУ після +X R (R = відстань стопу)
input double   InpBE_OffsetR     = 0.05;    // v2.05: БУ = вхід + X R
input bool     InpUseTrailing    = false;
input double   InpTrailStartR    = 1.0;     // v2.05: трейлінг після +X R
input double   InpTrailDistR     = 1.0;     // v2.05: відстань трейлінгу від ціни, R
input double   InpTrailStepR     = 0.1;     // v2.05: мін. покращення стопу, R (не смикати щотіку)

input group "=== Time Filter ==="
input int      InpStartHour      = 0;
input int      InpEndHour        = 24;

input group "=== D1-Bias Filter for BUY (v2.02, whitelist logic v2.03) ==="
input bool     InpUseD1FilterBuy = true;    // AK47_H1_BUY_D1FILTER_GO: MCPT PASS (quasi-p=0.00000, N=2000)
input int      InpBiasEmaPeriod   = 50;
input int      InpBiasSlopeBars   = 3;
input double   InpBiasSlopeMinATR = 0.03;

input group "=== RS-001 Gate Diagnostics (thresholds status: WATCH, not GO) ==="
input bool     InpRequireGateB   = true;    // v2.04: false = D1-фільтр без RS-001-обмеження на BUY (ізольований тест)
input bool     InpRequireGateS   = true;    // v2.04: false = SELL без RS-001-обмеження (ізольований тест)
input bool     InpGateLoggingOn  = true;

input group "=== v2.03: Tester/Live State Isolation ==="
input bool     InpIsolateTesterState = true;  // MQL_TESTER: завжди чистий старт, ігнорувати Common state

input group "=== v2.03: Prop-Safety Layer ==="
input double   InpDailyDDLimitPct   = 3.0;    // блок нових входів при внутрішньодобовій просадці >= X% від старту дня
input double   InpOverallDDLimitPct = 10.0;   // emergency lock при просадці >= X% від піку equity
input double   InpMaxSpreadPoints   = 60;     // v2.05: блок входу, якщо спред > X пунктів (60 = $0.60 на XAU)
input int      InpMaxTradesPerDay   = 10;     // жорсткий кап угод/добу (real entries, обидва напрямки разом)
input double   InpHardMaxLots       = 5.0;    // абсолютна стеля лоту незалежно від розрахованого ризику
input int      InpMaxSlippagePoints = 20;     // deviation для market-дій (закриття/модифікація)

//--- RS-001 FROZEN THRESHOLDS
#define RS001_OFF_LOOKBACK      75    // WATCH-статус, не GO -- TZ-RS001-PERDIR-LOOKBACK-001 §3 не виконано
#define RS001_OFF_EV_THRESHOLD  -0.005
#define RS001_MIN_OFF_SHADOW    50
#define RS001_ON_LOOKBACK       75
#define RS001_ON_EV_THRESHOLD   0.0
#define RS001_ON_PF_THRESHOLD   1.10
#define RS001_ON_CONFIRM_NEEDED 7
#define RS001_RINGBUF_SIZE      500

//--- Глобальні змінні (реальна торгівля)
double   g_point_val = 0;
datetime g_last_candle_time = 0;
int      g_loss_streak      = 0;
ulong    g_lastProcessedDealTicket = 0;   // v2.03: трекінг за ticket, не за часом (уникає same-second колізій)
int      g_hBiasAtrD1       = INVALID_HANDLE;
bool     g_isTester         = false;      // v2.03

//--- v2.03: prop-safety стан
double   g_dayStartEquity   = 0;
datetime g_dayStartDate     = 0;
double   g_peakEquity       = 0;
int      g_tradesToday      = 0;
datetime g_tradesTodayDate  = 0;
bool     g_emergencyLocked  = false;

//--- Глобальні змінні (RS-001 PER-DIRECTION shadow gate)
//--- NB (v2.03, п.3 рев'ю): цей shadow -- НЕЗАЛЕЖНІ гіпотетичні BUY/SELL потоки, НЕ репліка
//--- реального одно-позиційного OCO-шляху. Він відповідає на "який зараз напрямковий régime?",
//--- НЕ на "яким буде EV реального послідовного EA?". Подвійна парність (Python shadow-engine
//--- <-> цей MQL5-код <-> реальні MT5-угоди) для нього ще НЕ показана -- дивись
//--- Methodology_MCPT_Addendum п.10.
bool    g_tradingEnabledB  = false;
bool    g_tradingEnabledS  = false;
double  g_shadowR_B[RS001_RINGBUF_SIZE];
double  g_shadowR_S[RS001_RINGBUF_SIZE];
int     g_shadowCountB     = 0, g_shadowCountS     = 0;
int     g_shadowHeadB      = 0, g_shadowHeadS      = 0;
int     g_offShadowCountB  = 0, g_offShadowCountS  = 0;
int     g_onConfirmStreakB = 0, g_onConfirmStreakS = 0;
int     g_hGateLog         = INVALID_HANDLE;

bool    g_shadowHasPosB = false, g_shadowHasPosS = false;
double  g_shadowEntryB = 0, g_shadowSLB = 0, g_shadowTPB = 0;
double  g_shadowEntryS = 0, g_shadowSLS = 0, g_shadowTPS = 0;
bool    g_shadowHasPendingB = false, g_shadowHasPendingS = false;
double  g_shadowBuyPrice=0, g_shadowSellPrice=0, g_shadowBuySL=0, g_shadowBuyTP=0, g_shadowSellSL=0, g_shadowSellTP=0;

//+------------------------------------------------------------------+
//| v2.03 п.8: D1-bias з явним DATA_ERROR, whitelist-фільтр            |
//| 1=BULL, 0=NEUTRAL, -1=BEAR, -2=DATA_ERROR (раніше збігалось з 0)   |
//+------------------------------------------------------------------+
double BiasEMAAt(int shift, int period)
{
   int warmup = shift + period * 4;
   int need   = warmup - shift + 1;
   double closes[];
   ArraySetAsSeries(closes, true);
   if(CopyClose(_Symbol, PERIOD_D1, shift, need, closes) < need) return -1.0; // сигнал помилки для виклику вище
   double alpha = 2.0 / (period + 1.0);
   double ema   = closes[need - 1];
   for(int i = need - 2; i >= 0; i--) ema = alpha * closes[i] + (1.0 - alpha) * ema;
   return ema;
}

double BiasATRAt(int shift)
{
   double buf[1];
   if(CopyBuffer(g_hBiasAtrD1, 0, shift, 1, buf) < 1) return -1.0;
   return buf[0];
}

int GetBiasD1()   // -2=DATA_ERROR, -1=BEAR, 0=NEUTRAL, 1=BULL
{
   double emaNow = BiasEMAAt(1, InpBiasEmaPeriod);
   double emaOld = BiasEMAAt(1 + InpBiasSlopeBars, InpBiasEmaPeriod);
   double atr    = BiasATRAt(1);
   if(emaNow <= 0 || emaOld <= 0 || atr <= 0)
   {
      Print("D1_BIAS_DATA_FAIL: emaNow=", emaNow, " emaOld=", emaOld, " atr=", atr);
      return -2;
   }
   double closeArr[1];
   if(CopyClose(_Symbol, PERIOD_D1, 1, 1, closeArr) < 1)
   {
      Print("D1_BIAS_DATA_FAIL: CopyClose failed");
      return -2;
   }
   double close = closeArr[0];
   double slope = (emaNow - emaOld) / atr;
   if(close > emaNow && slope >=  InpBiasSlopeMinATR) return  1;
   if(close < emaNow && slope <= -InpBiasSlopeMinATR) return -1;
   return 0;
}

//+------------------------------------------------------------------+
//| v2.03 п.6: динамічний filling mode замість захардкоженого FOK      |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING GetFillingMode()
{
   long flags = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((flags & SYMBOL_FILLING_FOK) != 0)  return ORDER_FILLING_FOK;
   if((flags & SYMBOL_FILLING_IOC) != 0)  return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;   // безпечний дефолт, найширше підтримується для pending
}

//+------------------------------------------------------------------+
//| v2.03 п.9: PROP-SAFETY ШАР                                        |
//+------------------------------------------------------------------+
void UpdateDailyTracking()
{
   MqlDateTime dt; TimeCurrent(dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(today != g_dayStartDate)
   {
      g_dayStartDate = today;
      g_dayStartEquity = eq;
      g_tradesTodayDate = today;
      g_tradesToday = 0;
   }
   if(eq > g_peakEquity) g_peakEquity = eq;
}

bool PropSafetyAllowsEntry()
{
   if(g_emergencyLocked) { return false; }

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   if(g_peakEquity <= 0) g_peakEquity = MathMax(eq, bal);
   if(g_dayStartEquity <= 0) g_dayStartEquity = eq;

   double dailyDD = (g_dayStartEquity > 0) ? (g_dayStartEquity - eq) / g_dayStartEquity * 100.0 : 0.0;
   if(dailyDD >= InpDailyDDLimitPct)
   {
      Print("PROP_SAFETY_BLOCK: daily DD ", DoubleToString(dailyDD,2), "% >= limit ", InpDailyDDLimitPct, "%");
      return false;
   }

   double overallDD = (g_peakEquity > 0) ? (g_peakEquity - eq) / g_peakEquity * 100.0 : 0.0;
   if(overallDD >= InpOverallDDLimitPct)
   {
      g_emergencyLocked = true;
      SaveGateState();
      Print("PROP_SAFETY_EMERGENCY_LOCK: overall DD ", DoubleToString(overallDD,2),
            "% >= limit ", InpOverallDDLimitPct, "% -- trading locked until manual reset");
      return false;
   }

   double spread = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point;
   if(spread > InpMaxSpreadPoints)
   {
      Print("PROP_SAFETY_BLOCK: spread ", DoubleToString(spread,1), "pt > limit ", InpMaxSpreadPoints, "pt");
      return false;
   }

   if(g_tradesToday >= InpMaxTradesPerDay)
   {
      Print("PROP_SAFETY_BLOCK: trades today ", g_tradesToday, " >= cap ", InpMaxTradesPerDay);
      return false;
   }

   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
   { Print("PROP_SAFETY_BLOCK: account trading not allowed"); return false; }
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   { Print("PROP_SAFETY_BLOCK: terminal trading not allowed (AutoTrading OFF?)"); return false; }
   if((ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE) == SYMBOL_TRADE_MODE_DISABLED)
   { Print("PROP_SAFETY_BLOCK: symbol trade mode disabled"); return false; }

   return true;
}

//+------------------------------------------------------------------+
//| Initialization                                                    |
//+------------------------------------------------------------------+
int OnInit()
{
   if(_Digits == 3 || _Digits == 5) g_point_val = _Point * 10;
   else                             g_point_val = _Point;

   g_isTester = (bool)MQLInfoInteger(MQL_TESTER);

   if(InpBaseRisk <= 0.0 || InpBaseRisk > InpMaxRiskPct)
   {
      Print("INIT_FAILED: InpBaseRisk=", InpBaseRisk, "% поза межами (0; ", InpMaxRiskPct, "%]. Постав реальний ризик, напр. 0.25–0.5.");
      return(INIT_FAILED);
   }
   if(InpUseTrailing && (InpTrailDistR <= 0.0 || InpTrailStartR < 0.0))
   { Print("INIT_FAILED: некоректні параметри трейлінгу"); return(INIT_FAILED); }

   if(InpUseD1FilterBuy)
   {
      g_hBiasAtrD1 = iATR(_Symbol, PERIOD_D1, 14);
      if(g_hBiasAtrD1 == INVALID_HANDLE) { Print("INIT_FAILED: D1 bias ATR handle invalid"); return(INIT_FAILED); }
   }

   ArrayInitialize(g_shadowR_B, 0.0);
   ArrayInitialize(g_shadowR_S, 0.0);

   // v2.03 п.1: у Tester -- НІКОЛИ не читати Common state (leakage fix). У live -- завантажити.
   if(!g_isTester || !InpIsolateTesterState)
      LoadGateState();
   else
      Print("TESTER_MODE: gate state isolation active -- starting fresh (InpIsolateTesterState=true)");

   UpdateDailyTracking();

   if(InpGateLoggingOn) {
      g_hGateLog = FileOpen("AK47_RS001_gate_log.csv",
         FILE_READ|FILE_WRITE|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_CSV|FILE_COMMON, ';');
      if(g_hGateLog == INVALID_HANDLE)
         g_hGateLog = FileOpen("AK47_RS001_gate_log.csv",
            FILE_READ|FILE_WRITE|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_CSV, ';');
      if(g_hGateLog != INVALID_HANDLE) {
         FileSeek(g_hGateLog, 0, SEEK_END);
         if(FileTell(g_hGateLog) == 0)
            FileWrite(g_hGateLog, "time", "direction", "event", "shadow_N", "rolling100_EV",
               "rolling200_EV", "rolling200_PF", "off_shadow_count", "on_confirm_streak");
      }
   }

   Print("AK47_H1_RS001 INIT_OK | ver=2.05 | magic=", InpMagicNumber, " | risk=", InpBaseRisk, "%",
         " | BE=", InpUseBreakeven, " trail=", InpUseTrailing, " (start ", InpTrailStartR, "R dist ", InpTrailDistR, "R)",
         " | SL=", InpSLPips, " TP=", InpTPPips,
         " | D1FilterBuy=", InpUseD1FilterBuy,
         " | GATE_THRESHOLDS_STATUS=WATCH (TZ-RS001-PERDIR-LOOKBACK-001 s3 не виконано, не GO)",
         " | isTester=", g_isTester, " stateIsolated=", (g_isTester && InpIsolateTesterState),
         " | requireGateB=", InpRequireGateB, " requireGateS=", InpRequireGateS,
         " | tradingEnabled(start) BUY=", g_tradingEnabledB, " SELL=", g_tradingEnabledS,
         " | ATTACH TO H1 CHART");
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   if(g_hBiasAtrD1 != INVALID_HANDLE) IndicatorRelease(g_hBiasAtrD1);
   DeleteAllOrders();
   if(g_hGateLog != INVALID_HANDLE) FileClose(g_hGateLog);
}

//+------------------------------------------------------------------+
//| v2.03 п.4: OnTradeTransaction -- негайне скасування sibling pending|
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagicNumber) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_ENTRY) != DEAL_ENTRY_IN) return;
   // позиція щойно відкрилась -- негайно прибрати sibling pending, не чекаючи наступного OnTick
   if(CountOrders() > 0) DeleteAllOrders();
}

//+------------------------------------------------------------------+
//| OnTick                                                            |
//+------------------------------------------------------------------+
void OnTick()
{
   UpdateDailyTracking();
   UpdateStreakLogic();

   double Ask = SymbolInfoDouble(Symbol(), SYMBOL_ASK);
   double Bid = SymbolInfoDouble(Symbol(), SYMBOL_BID);
   if(Ask == 0 || Bid == 0) return;

   ManagePositions(Ask, Bid);
   if(CountPositions() > 0 && CountOrders() > 0) DeleteAllOrders();   // резервний poll-фолбек до OnTradeTransaction

   ManageShadow(Ask, Bid);

   MqlDateTime dt;
   TimeCurrent(dt);
   bool time_allowed = (dt.hour >= InpStartHour && dt.hour < InpEndHour);

   if(!time_allowed) {
      if(CountOrders() > 0) DeleteAllOrders();
      return;
   }

   datetime time_buf[];
   ArraySetAsSeries(time_buf, true);
   if(CopyTime(Symbol(), PERIOD_CURRENT, 0, 1, time_buf) <= 0) return;
   bool isNewBar = (time_buf[0] != g_last_candle_time);

   if(!isNewBar) return;
   g_last_candle_time = time_buf[0];

   double high_buf[], low_buf[];
   ArraySetAsSeries(high_buf, true);
   ArraySetAsSeries(low_buf, true);
   if(CopyHigh(Symbol(), PERIOD_CURRENT, 1, 1, high_buf) <= 0) return;
   if(CopyLow(Symbol(), PERIOD_CURRENT, 1, 1, low_buf) <= 0) return;

   double prev_high = high_buf[0];
   double prev_low  = low_buf[0];

   double buy_price  = NormalizeDouble(prev_high + (InpPaddingPips * g_point_val), _Digits);
   double sell_price = NormalizeDouble(prev_low  - (InpPaddingPips * g_point_val), _Digits);
   double sl_dist = InpSLPips * g_point_val;
   double tp_dist = InpTPPips * g_point_val;
   double buy_sl  = NormalizeDouble(buy_price  - sl_dist, _Digits);
   double buy_tp  = NormalizeDouble(buy_price  + tp_dist, _Digits);
   double sell_sl = NormalizeDouble(sell_price + sl_dist, _Digits);
   double sell_tp = NormalizeDouble(sell_price - tp_dist, _Digits);

   RefreshShadowPending(buy_price, sell_price, buy_sl, buy_tp, sell_sl, sell_tp);

   if(CountPositions() > 0) return;
   if(!PropSafetyAllowsEntry()) { if(CountOrders() > 0) DeleteAllOrders(); return; }

   DeleteAllOrders();

   long stop_level = SymbolInfoInteger(Symbol(), SYMBOL_TRADE_STOPS_LEVEL);
   double min_dist = stop_level * _Point;

   double smart_risk = GetSmartRisk();
   double lots = CalculateLot(sl_dist, smart_risk);
   if(lots <= 0) return;
   if(lots > InpHardMaxLots) lots = InpHardMaxLots;   // v2.03 п.9: жорстка стеля незалежно від розрахунку

   bool d1Allow = true;
   if(InpUseD1FilterBuy)
   {
      int bias = GetBiasD1();
      d1Allow = (bias == 1 || bias == 0);   // v2.03 п.8: whitelist -- DATA_ERROR(-2) і BEAR(-1) блокують
   }

   bool gateOkB = (!InpRequireGateB) || g_tradingEnabledB;   // v2.04: ізольований тест D1-фільтра без gate
   bool gateOkS = (!InpRequireGateS) || g_tradingEnabledS;

   bool placedAny = false;
   if(gateOkB && d1Allow && (buy_price - Ask >= min_dist)) {
      if(SendOrderChecked(ORDER_TYPE_BUY_STOP, buy_price, lots, buy_sl, buy_tp)) { placedAny = true; g_tradesToday++; }
   }
   if(gateOkS && (Bid - sell_price >= min_dist)) {
      if(SendOrderChecked(ORDER_TYPE_SELL_STOP, sell_price, lots, sell_sl, sell_tp)) { placedAny = true; g_tradesToday++; }
   }

   if(placedAny)
      Print("REAL Entry attempt. rsGateB=", g_tradingEnabledB, " rsGateS=", g_tradingEnabledS,
            " gateReqB=", InpRequireGateB, " gateReqS=", InpRequireGateS,
            " d1Allow=", d1Allow, " Streak:", g_loss_streak, " Risk:", smart_risk, "% Lots:", lots,
            " tradesToday:", g_tradesToday);
}

//+------------------------------------------------------------------+
//| SHADOW STREAM -- regime-measurement, НЕ репліка реального OCO шляху|
//+------------------------------------------------------------------+
void RefreshShadowPending(double bp, double sp, double bsl, double btp, double ssl, double stp)
{
   g_shadowBuyPrice = bp; g_shadowBuySL = bsl; g_shadowBuyTP = btp;
   g_shadowSellPrice = sp; g_shadowSellSL = ssl; g_shadowSellTP = stp;
   if(!g_shadowHasPosB) g_shadowHasPendingB = true;
   if(!g_shadowHasPosS) g_shadowHasPendingS = true;
}

void ManageShadow(double Ask, double Bid)
{
   if(g_shadowHasPendingB && !g_shadowHasPosB) {
      if(Ask >= g_shadowBuyPrice) {
         g_shadowHasPosB = true;
         g_shadowEntryB = g_shadowBuyPrice; g_shadowSLB = g_shadowBuySL; g_shadowTPB = g_shadowBuyTP;
         g_shadowHasPendingB = false;
      }
   }
   if(g_shadowHasPosB) {
      if(Bid <= g_shadowSLB) { g_shadowHasPosB = false; RecordShadowResult(-1.0, 1); }
      else if(Bid >= g_shadowTPB) { g_shadowHasPosB = false; RecordShadowResult((double)InpTPPips/InpSLPips, 1); }
   }

   if(g_shadowHasPendingS && !g_shadowHasPosS) {
      if(Bid <= g_shadowSellPrice) {
         g_shadowHasPosS = true;
         g_shadowEntryS = g_shadowSellPrice; g_shadowSLS = g_shadowSellSL; g_shadowTPS = g_shadowSellTP;
         g_shadowHasPendingS = false;
      }
   }
   if(g_shadowHasPosS) {
      if(Ask >= g_shadowSLS) { g_shadowHasPosS = false; RecordShadowResult(-1.0, -1); }
      else if(Ask <= g_shadowTPS) { g_shadowHasPosS = false; RecordShadowResult((double)InpTPPips/InpSLPips, -1); }
   }
}

//+------------------------------------------------------------------+
//| v2.03 п.1: GateStateFileName -- ізоляція Tester + повний контекст  |
//+------------------------------------------------------------------+
string GateStateFileName()
{
   string acct = IntegerToString((int)AccountInfoInteger(ACCOUNT_LOGIN));
   string ctx = StringFormat("%s_%s_%s_%d_SL%d_TP%d_ON%d_OFF%d_CF%d_D1%d_v203",
      acct, _Symbol, EnumToString((ENUM_TIMEFRAMES)PERIOD_CURRENT), InpMagicNumber,
      InpSLPips, InpTPPips, RS001_ON_LOOKBACK, RS001_OFF_LOOKBACK, RS001_ON_CONFIRM_NEEDED,
      (int)InpUseD1FilterBuy);
   if(g_isTester)
      ctx = ctx + "_TESTERRUN" + IntegerToString((int)TimeLocal());   // унікально на кожен запуск Тестера
   return "AK47_RS001_gatestate_" + ctx + ".bin";
}

void SaveGateState()
{
   if(g_isTester && InpIsolateTesterState) return;   // v2.03 п.1: у Tester НІКОЛИ не зберігаємо
   int h = FileOpen(GateStateFileName(), FILE_WRITE|FILE_BIN|FILE_COMMON);
   if(h == INVALID_HANDLE) h = FileOpen(GateStateFileName(), FILE_WRITE|FILE_BIN);
   if(h == INVALID_HANDLE) return;

   FileWriteInteger(h, 20260729);   // v2.03 schema tag
   FileWriteInteger(h, (int)g_tradingEnabledB);
   FileWriteInteger(h, (int)g_tradingEnabledS);
   FileWriteInteger(h, g_shadowCountB);   FileWriteInteger(h, g_shadowCountS);
   FileWriteInteger(h, g_shadowHeadB);    FileWriteInteger(h, g_shadowHeadS);
   FileWriteInteger(h, g_offShadowCountB);   FileWriteInteger(h, g_offShadowCountS);
   FileWriteInteger(h, g_onConfirmStreakB);  FileWriteInteger(h, g_onConfirmStreakS);
   FileWriteInteger(h, (int)g_shadowHasPosB); FileWriteInteger(h, (int)g_shadowHasPosS);
   FileWriteDouble(h, g_shadowEntryB); FileWriteDouble(h, g_shadowSLB); FileWriteDouble(h, g_shadowTPB);
   FileWriteDouble(h, g_shadowEntryS); FileWriteDouble(h, g_shadowSLS); FileWriteDouble(h, g_shadowTPS);
   FileWriteInteger(h, (int)g_shadowHasPendingB); FileWriteInteger(h, (int)g_shadowHasPendingS);
   FileWriteDouble(h, g_shadowBuyPrice);  FileWriteDouble(h, g_shadowSellPrice);
   FileWriteDouble(h, g_shadowBuySL);     FileWriteDouble(h, g_shadowBuyTP);
   FileWriteDouble(h, g_shadowSellSL);    FileWriteDouble(h, g_shadowSellTP);
   for(int i = 0; i < RS001_RINGBUF_SIZE; i++) FileWriteDouble(h, g_shadowR_B[i]);
   for(int i = 0; i < RS001_RINGBUF_SIZE; i++) FileWriteDouble(h, g_shadowR_S[i]);
   FileWriteLong(h, (long)g_last_candle_time);
   // v2.03 п.7/9: додаткова персистентність
   FileWriteLong(h, (long)g_lastProcessedDealTicket);
   FileWriteInteger(h, g_loss_streak);
   FileWriteDouble(h, g_peakEquity);
   FileWriteInteger(h, (int)g_emergencyLocked);

   FileClose(h);
}

void LoadGateState()
{
   int h = FileOpen(GateStateFileName(), FILE_READ|FILE_BIN|FILE_COMMON);
   if(h == INVALID_HANDLE) h = FileOpen(GateStateFileName(), FILE_READ|FILE_BIN);
   if(h == INVALID_HANDLE) {
      Print("RS001_STATE: no matching saved state (context-specific filename) -- fresh warm-up.");
      return;
   }

   int tag = FileReadInteger(h);
   if(tag != 20260729) { FileClose(h); Print("RS001_STATE: schema mismatch, ignoring."); return; }

   g_tradingEnabledB  = (bool)FileReadInteger(h);
   g_tradingEnabledS  = (bool)FileReadInteger(h);
   g_shadowCountB     = FileReadInteger(h);   g_shadowCountS     = FileReadInteger(h);
   g_shadowHeadB      = FileReadInteger(h);   g_shadowHeadS      = FileReadInteger(h);
   g_offShadowCountB  = FileReadInteger(h);   g_offShadowCountS  = FileReadInteger(h);
   g_onConfirmStreakB = FileReadInteger(h);   g_onConfirmStreakS = FileReadInteger(h);
   g_shadowHasPosB    = (bool)FileReadInteger(h);
   g_shadowHasPosS    = (bool)FileReadInteger(h);
   g_shadowEntryB = FileReadDouble(h); g_shadowSLB = FileReadDouble(h); g_shadowTPB = FileReadDouble(h);
   g_shadowEntryS = FileReadDouble(h); g_shadowSLS = FileReadDouble(h); g_shadowTPS = FileReadDouble(h);
   g_shadowHasPendingB = (bool)FileReadInteger(h);
   g_shadowHasPendingS = (bool)FileReadInteger(h);
   g_shadowBuyPrice = FileReadDouble(h);  g_shadowSellPrice = FileReadDouble(h);
   g_shadowBuySL    = FileReadDouble(h);  g_shadowBuyTP     = FileReadDouble(h);
   g_shadowSellSL   = FileReadDouble(h);  g_shadowSellTP    = FileReadDouble(h);
   for(int i = 0; i < RS001_RINGBUF_SIZE; i++) g_shadowR_B[i] = FileReadDouble(h);
   for(int i = 0; i < RS001_RINGBUF_SIZE; i++) g_shadowR_S[i] = FileReadDouble(h);
   g_last_candle_time = (datetime)FileReadLong(h);
   g_lastProcessedDealTicket = (ulong)FileReadLong(h);
   g_loss_streak = FileReadInteger(h);
   g_peakEquity = FileReadDouble(h);
   g_emergencyLocked = (bool)FileReadInteger(h);

   FileClose(h);
   Print("RS001_STATE: RESTORED | shadowN_B=", g_shadowCountB, " shadowN_S=", g_shadowCountS,
         " | tradingEnabled B=", g_tradingEnabledB, " S=", g_tradingEnabledS,
         " | lossStreak=", g_loss_streak, " emergencyLocked=", g_emergencyLocked);
}

void RecordShadowResult(double r, int dir)
{
   if(dir == 1)
      RecordShadowResultImpl(r, dir, g_shadowR_B, g_shadowHeadB, g_shadowCountB,
                              g_offShadowCountB, g_onConfirmStreakB, g_tradingEnabledB);
   else
      RecordShadowResultImpl(r, dir, g_shadowR_S, g_shadowHeadS, g_shadowCountS,
                              g_offShadowCountS, g_onConfirmStreakS, g_tradingEnabledS);
}

void RecordShadowResultImpl(double r, int dir, double &buf[], int &head, int &count,
                             int &offCount, int &onStreak, bool &enabled)
{
   buf[head] = r;
   head = (head + 1) % RS001_RINGBUF_SIZE;
   count++;

   double ev100, ev200, pf200, dummyPF;
   bool have100b = RollingStatsImpl(RS001_OFF_LOOKBACK, ev100, dummyPF, buf, head, count);
   bool have200  = RollingStatsImpl(RS001_ON_LOOKBACK, ev200, pf200, buf, head, count);

   string event = "";

   if(enabled && have100b && ev100 < RS001_OFF_EV_THRESHOLD) {
      enabled = false; offCount = 0; onStreak = 0;
      event = "OFF";
      Print("RS001_GATE[", (dir==1?"BUY":"SELL"), "]: OFF | rolling100_EV=", ev100);
   }
   else if(!enabled) {
      offCount++;
      if(offCount >= RS001_MIN_OFF_SHADOW && have200) {
         if(ev200 > RS001_ON_EV_THRESHOLD && pf200 > RS001_ON_PF_THRESHOLD) {
            onStreak++;
            if(onStreak >= RS001_ON_CONFIRM_NEEDED) {
               enabled = true; offCount = 0; onStreak = 0;
               event = "ON";
               Print("RS001_GATE[", (dir==1?"BUY":"SELL"), "]: ON | rolling200_EV=", ev200, " PF=", pf200);
            }
         } else {
            onStreak = 0;
         }
      }
   }

   if(InpGateLoggingOn && g_hGateLog != INVALID_HANDLE && (event != "" || count % 20 == 0)) {
      FileWrite(g_hGateLog, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
         (dir==1?"BUY":"SELL"), (event==""?"TICK":event), count,
         (have100b ? DoubleToString(ev100,5) : "NA"),
         (have200 ? DoubleToString(ev200,5) : "NA"),
         (have200 ? DoubleToString(pf200,3) : "NA"),
         offCount, onStreak);
   }

   SaveGateState();
}

bool RollingStatsImpl(int lookback, double &ev, double &pf, double &buf[], int head, int count)
{
   int n = MathMin(lookback, count);
   if(n < lookback) { ev = 0; pf = 0; return false; }

   double sum = 0, gp = 0, gl = 0;
   for(int i = 0; i < n; i++) {
      int idx = (head - 1 - i + RS001_RINGBUF_SIZE * 2) % RS001_RINGBUF_SIZE;
      double r = buf[idx];
      sum += r;
      if(r > 0) gp += r; else gl += MathAbs(r);
   }
   ev = sum / n;
   pf = (gl > 0) ? gp / gl : (gp > 0 ? 999.0 : 0.0);
   return true;
}

//+------------------------------------------------------------------+
//| v2.03 п.7: Streak -- net-profit, агрегація за POSITION_ID,        |
//| трекінг за deal ticket (не за часом)                              |
//+------------------------------------------------------------------+
void UpdateStreakLogic()
{
   if(!HistorySelect(0, TimeCurrent())) return;
   int total_deals = HistoryDealsTotal();

   // зібрати нові OUT-угоди (ticket > останнього обробленого), згрупувати за POSITION_ID
   ulong newTickets[]; ulong newPosIds[]; double newNet[]; datetime newTimes[];
   int cnt = 0;
   ArrayResize(newTickets, total_deals); ArrayResize(newPosIds, total_deals);
   ArrayResize(newNet, total_deals); ArrayResize(newTimes, total_deals);

   for(int i = 0; i < total_deals; i++) {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket <= g_lastProcessedDealTicket) continue;
      if(HistoryDealGetInteger(ticket, DEAL_MAGIC) != InpMagicNumber) continue;
      if(HistoryDealGetInteger(ticket, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;

      double net = HistoryDealGetDouble(ticket, DEAL_PROFIT)
                 + HistoryDealGetDouble(ticket, DEAL_SWAP)
                 + HistoryDealGetDouble(ticket, DEAL_COMMISSION);
      newTickets[cnt] = ticket;
      newPosIds[cnt]  = HistoryDealGetInteger(ticket, DEAL_POSITION_ID);
      newNet[cnt]     = net;
      newTimes[cnt]   = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
      cnt++;
      if(ticket > g_lastProcessedDealTicket) g_lastProcessedDealTicket = ticket;
   }
   if(cnt == 0) return;

   // агрегувати net-profit за POSITION_ID (кілька deals -- напр. часткові закриття -- одна позиція)
   ulong uniquePos[]; double posNet[]; int upCnt=0;
   ArrayResize(uniquePos, cnt); ArrayResize(posNet, cnt);
   for(int i = 0; i < cnt; i++) {
      int found = -1;
      for(int k = 0; k < upCnt; k++) if(uniquePos[k] == newPosIds[i]) { found = k; break; }
      if(found >= 0) posNet[found] += newNet[i];
      else { uniquePos[upCnt] = newPosIds[i]; posNet[upCnt] = newNet[i]; upCnt++; }
   }
   for(int k = 0; k < upCnt; k++) {
      if(posNet[k] < 0) g_loss_streak++;
      else               g_loss_streak = 0;
   }
}

double GetSmartRisk()
{
   double risk = InpBaseRisk;
   for(int i=0; i < g_loss_streak && i < InpMaxLossStreak; i++) risk *= InpRiskFactor;
   return risk;
}

//+------------------------------------------------------------------+
//| Management: Breakeven + Trailing (OFF за замовчуванням для H1)   |
//+------------------------------------------------------------------+
void ManagePositions(double current_ask, double current_bid)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      long   type = PositionGetInteger(POSITION_TYPE);

      double new_sl = sl;
      bool modify = false;
      string trail_type = "";

      // v2.05: усе в R (R = початкова відстань стопу = InpSLPips у ціні)
      double R    = InpSLPips * g_point_val;
      double step = MathMax(InpTrailStepR * R, _Point);
      if(type == POSITION_TYPE_BUY) {
         double prof = current_bid - open_price;
         if(InpUseBreakeven && prof >= InpBE_TriggerR * R && sl < open_price) {
            new_sl = NormalizeDouble(open_price + InpBE_OffsetR * R, _Digits);
            modify = true; trail_type = "BE";
         }
         if(InpUseTrailing && prof >= InpTrailStartR * R) {
            double trail_level = NormalizeDouble(current_bid - InpTrailDistR * R, _Digits);
            double base = modify ? new_sl : sl;
            if(trail_level >= base + step) { new_sl = trail_level; modify = true; trail_type = "TRAIL"; }
         }
      } else {
         double prof = open_price - current_ask;
         if(InpUseBreakeven && prof >= InpBE_TriggerR * R && (sl > open_price || sl == 0)) {
            new_sl = NormalizeDouble(open_price - InpBE_OffsetR * R, _Digits);
            modify = true; trail_type = "BE";
         }
         if(InpUseTrailing && prof >= InpTrailStartR * R) {
            double trail_level = NormalizeDouble(current_ask + InpTrailDistR * R, _Digits);
            double base = modify ? new_sl : sl;
            if(base == 0 || trail_level <= base - step) { new_sl = trail_level; modify = true; trail_type = "TRAIL"; }
         }
      }

      if(modify) {
         long   stopLevelPts   = SymbolInfoInteger(Symbol(), SYMBOL_TRADE_STOPS_LEVEL);
         long   freezeLevelPts = SymbolInfoInteger(Symbol(), SYMBOL_TRADE_FREEZE_LEVEL);
         double spreadNow      = current_ask - current_bid;
         double minDist        = MathMax(stopLevelPts, freezeLevelPts) * _Point + spreadNow;   // v2.05: + спред
         double distToPrice    = (type == POSITION_TYPE_BUY) ? (current_bid - new_sl) : (new_sl - current_ask);

         if(distToPrice < minDist) {
            Print("SL_MODIFY_BLOCKED_STOPLEVEL: dist=", distToPrice/_Point, "pts (ticket=", ticket, ")");
         } else {
            MqlTradeRequest request; MqlTradeResult result;
            ZeroMemory(request); ZeroMemory(result);
            request.action = TRADE_ACTION_SLTP;
            request.position = ticket;
            request.symbol = Symbol();
            request.sl = new_sl;
            request.tp = tp;
            request.magic = InpMagicNumber;
            if(!OrderSend(request, result) || result.retcode != TRADE_RETCODE_DONE)
               Print("SL_MODIFY_FAILED: ticket=", ticket, " retcode=", result.retcode,
                     " comment=", result.comment);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Order helpers (v2.03 п.5/6: retcode-перевірка, динамічний filling)|
//+------------------------------------------------------------------+
bool SendOrderChecked(ENUM_ORDER_TYPE type, double price, double volume, double sl, double tp)
{
   MqlTradeRequest request; MqlTradeResult result;
   ZeroMemory(request); ZeroMemory(result);
   request.action     = TRADE_ACTION_PENDING;
   request.symbol     = Symbol();
   request.volume     = volume;
   request.price      = price;
   request.sl         = sl;
   request.tp         = tp;
   request.deviation  = InpMaxSlippagePoints;
   request.magic      = InpMagicNumber;
   request.type       = type;
   request.type_filling = GetFillingMode();
   request.type_time  = ORDER_TIME_GTC;
   request.comment    = "AK47_H1_RS001_v2.05";

   bool sent = OrderSend(request, result);
   bool ok = sent && (result.retcode == TRADE_RETCODE_DONE || result.retcode == TRADE_RETCODE_PLACED);
   if(!ok)
      Print("ORDER_SEND_FAILED: type=", EnumToString(type), " retcode=", result.retcode,
            " comment=", result.comment, " request_id=", result.request_id,
            " price=", price, " volume=", volume);
   else
      Print("ORDER_SEND_OK: type=", EnumToString(type), " order=", result.order,
            " deal=", result.deal, " price=", result.price, " volume=", result.volume,
            " retcode=", result.retcode);
   return ok;
}

void DeleteAllOrders()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--) {
      ulong t = OrderGetTicket(i);
      if(t <= 0) continue;
      if(OrderGetInteger(ORDER_MAGIC) == InpMagicNumber) {
         MqlTradeRequest request; MqlTradeResult result;
         ZeroMemory(request); ZeroMemory(result);
         request.action = TRADE_ACTION_REMOVE;
         request.order = t;
         if(!OrderSend(request, result) || result.retcode != TRADE_RETCODE_DONE)
            Print("ORDER_REMOVE_FAILED: order=", t, " retcode=", result.retcode, " comment=", result.comment);
      }
   }
}

double CalculateLot(double sldist, double riskpercent)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_money = balance * (riskpercent / 100.0);
   double tick_value = SymbolInfoDouble(Symbol(), SYMBOL_TRADE_TICK_VALUE);
   double tick_size  = SymbolInfoDouble(Symbol(), SYMBOL_TRADE_TICK_SIZE);
   if(tick_size == 0 || sldist == 0) return 0.0;      // v2.05: не торгувати навмання

   double loss_per_lot = sldist / tick_size * tick_value;
   if(loss_per_lot <= 0) return 0.0;

   double lots = risk_money / loss_per_lot;
   double step = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_STEP);
   lots = MathFloor(lots / step) * step;

   double min = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MIN);
   double max = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MAX);
   if(lots < min)
   {
      Print("LOT_SKIP: ризик ", riskpercent, "% не вміщує мінімальний лот ", min, " (розрахунок ", lots, ")");
      return 0.0;                                    // v2.05: не збільшувати ризик понад заданий
   }
   if(lots > max) lots = max;

   // v2.03 п.9: margin-перевірка через OrderCheck перед фактичним входом
   MqlTradeRequest chk; MqlTradeCheckResult chkRes;
   ZeroMemory(chk); ZeroMemory(chkRes);
   chk.action = TRADE_ACTION_PENDING;
   chk.symbol = Symbol();
   chk.volume = lots;
   chk.type   = ORDER_TYPE_BUY_STOP;
   chk.price  = SymbolInfoDouble(Symbol(), SYMBOL_ASK);
   chk.type_filling = GetFillingMode();
   chk.type_time = ORDER_TIME_GTC;
   if(!OrderCheck(chk, chkRes) || chkRes.retcode == TRADE_RETCODE_NO_MONEY)
   {
      Print("MARGIN_CHECK_FAILED: retcode=", chkRes.retcode, " comment=", chkRes.comment,
            " -- угоду ПРОПУЩЕНО (v2.05)");
      return 0.0;
   }
   return lots;
}

int CountOrders()
{
   int cnt=0;
   for(int i=OrdersTotal()-1; i>=0; i--) {
      ulong t = OrderGetTicket(i);
      if(t == 0) continue;
      if(OrderGetInteger(ORDER_MAGIC)==InpMagicNumber) cnt++;
   }
   return cnt;
}

int CountPositions()
{
   int cnt=0;
   for(int i=PositionsTotal()-1; i>=0; i--) {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC)==InpMagicNumber) cnt++;
   }
   return cnt;
}
