//+------------------------------------------------------------------+
//|  CrowdFadeMulti.mq5                                               |
//|  Мультивалютний EA: торгівля ПРОТИ позиції роздрібу на Binance.   |
//|                                                                   |
//|  СИГНАЛ                                                           |
//|    z = (L/S зараз − середнє за задане вікно) / стандартне відхилення    |
//|    z >= +поріг  натовп перекошений у ЛОНГИ -> SELL LIMIT          |
//|    z <= -поріг  перекошений у ШОРТИ        -> BUY  LIMIT          |
//|    вхід: ліміт на 1 ATR ПРОТИ напрямку, дійсний 3 години          |
//|    v2.00: SL 4.5 ATR; TP 10 ATR; max hold 24h; BE/trailing OFF                 |
//|                                                                   |
//|  ВИМІРЯНО v1.10 (BTCUSDT, 2021-01..2026-08, N=11631):             |
//|    вікно z=6год, пауза 3год, тримання 6год                        |
//|    EV +0.419 ATR, t=14.50, 2075 угод/рік, R/рік=869               |
//|    перемішаний сигнал z=15.43 PASS, блочний сурогат z=4.92 PASS   |
//|    6/6 років: EV 0.344..0.507, половини 0.425/0.413               |
//|    G0.2: топ-10 = 5.9% прибутку                                   |
//|  v1.00 було 24/12/24: EV 0.636 але R/рік лише 380, DD вдвічі більша|
//|                                                                   |
//|  v1.20 ВИХІД ЗА РОЗВОРОТОМ СИГНАЛУ                                |
//|    через 6 год після входу z змінює бік у 43.0% випадків.         |
//|    вихід при z проти нас >= 1.0:  EV 0.425  t 16.54  WR 45.7%     |
//|    база без цього:                EV 0.419  t 14.50  WR 40.6%     |
//|    EV не падає, t і WR ростуть.                                   |
//|    Вихід за ЦІНОЮ навпаки ГІРШИЙ:                                 |
//|      беззбиток після +1 ATR       EV 0.378                        |
//|      вихід якщо за 2 год не пішло EV 0.403                        |
//|    Індикатори не додають: ADX/BB/Donchian/RSI від -39% до +4%.    |
//|                                                                   |
//|  v1.30 ПІДТЯГУВАННЯ НЕВИКОНАНОЇ ЗАЯВКИ                            |
//|    3803 з 16066 заявок не заповнювались — це випадки, де ціна     |
//|    одразу пішла в наш бік. Сигнал підтверджений рухом.            |
//|    підтягування через 4 бари M15 до 0.40 ATR:                     |
//|      EV 0.487 (база 0.389), t 23.85 (19.13), R/рік 748 (568)      |
//|      R/DD 35.0 (25.4), просадка навіть менша: 21.4 проти 22.4     |
//|    плато монотонне: 4 бари краще за 8/12/16, 0.2-0.4 краще за 0.8 |
//|    перемішаний сигнал z=17.58 PASS                                |
//|    УВАГА: брати ринком по закінченні — КАТАСТРОФА, EV 0.048.      |
//|                                                                   |
//|  v1.40 БАГАТОФАКТОРНА ВАГА ПОЗИЦІЇ                                |
//|    Поодинці кожен фактор тоне в шумі, РАЗОМ дають сигнал.         |
//|    Лінійна модель, навчена на 1-й половині, перевірена на 2-й:    |
//|      R2 навчання 0.00652, перевірка 0.00553 (перенос 85%)         |
//|      квартилі прогнозу на ПЕРЕВІРЦІ: 0.255 / 0.438 / 0.506 / 0.707|
//|      R/рік 732 -> 876 (+20%) при середній вазі 1.01               |
//|    Вага змінює тільки РОЗПОДІЛ ризику, не середній рівень.        |
//|    УВАГА: коефіцієнти навчені на BTC. Перенос на ETH/SOL не       |
//|    перевірявся — InpUseScore=false вимикає все.                   |
//|                                                                   |
//|  v1.50 ЧАСТКОВИЙ ВИХІД (за замовчуванням ВИМКНЕНО)                |
//|    закрити 50% на +1.5 ATR:                                       |
//|      WR 53.8% -> 56.2%,  t 23.85 -> 26.39,  DD 21.4 -> 16.8       |
//|      R/DD 35.0 -> 35.1 (без змін), R/рік 748 -> 590 (-21%)        |
//|    Це ОБМІН, не покращення: платиш прибутком за меншу просадку.   |
//|    Вмикати, якщо просадка на демо болючіша за очікувану.          |
//|    Гірші варіанти (НЕ брати): 70% на +1.0 -> WR 68% але R/DD 25.7 |
//|                                                                   |
//|  v1.60 ТРЕЙЛІНГ-СТОП (УВІМКНЕНО за замовчуванням)                 |
//|    Виміряно: забираємо лише 23% від піку руху (MFE 2.10 ATR при   |
//|    EV 0.487). Серед ПРОГРАШНИХ угод середній MFE 0.85 ATR, а 31%  |
//|    з них мали хід у наш бік понад 1 ATR — прибуток був і зник.    |
//|    трейлінг 0.50 ATR від піку:                                    |
//|      WR 53.8% -> 73.7%,  t 23.85 -> 28.96                         |
//|      DD 21.4 -> 11.2 R,  R/DD 35.0 -> 45.2  (+29%)                |
//|      R/рік 748 -> 507, але при DD удвічі меншій                   |
//|      контроль: перемішаний 0.113 проти 0.330, z=18.89 PASS        |
//|      6/6 років, розкид EV 0.31..0.35, половини 0.341/0.319        |
//|    НЕ беремо 0.20 ATR (R/DD 85.3): це 2-3 спреди, бектест на M15  |
//|    завищує якість тісного трейлінга — реальні тики його виб'ють.  |
//|                                                                   |
//|  v1.61 ПЕРЕРАХОВАНІ КОЕФІЦІЄНТИ МОДЕЛІ                            |
//|    Коефіцієнти v1.40 рахувались БЕЗ трейлінга і застаріли:        |
//|    dstr -0.114 -> -0.075, hract перевернув знак, z40 зник.        |
//|    Перераховано на тій самій логіці, що в коді.                   |
//|    out-of-sample R2 0.00523, R/рік з вагою +16%.                  |
//|    Восьма фіча (тренд ret3h) НЕ додає: коеф +0.0097, дублює dstr. |
//|    ринком замість ліміту: t падає 6.73 -> 1.23                    |
//|    з фіксованою ціллю:    t падає до 0.23                         |
//|                                                                   |
//|  v1.62 EXECUTION PARITY                                             |
//|    - CHASE рівно один раз після InpChaseAfterBars, не на кожному тіку|
//|    - management усіх символів по таймеру, не від BTC OnTick          |
//|    - реальний peak price + ATR snapshot для трейлінга                 |
//|    - broker specs читаються через SymbolInfo*/OrderCalcProfit         |
//|    - перевірка ResultRetcode + фактичного SL/order після modify       |
//|    - stale Binance guard, pending exposure, DD halt cancels pending   |
//|    - persistent cooldown/risk/trailing state через Terminal Globals  |
//|                                                                   |
//|  СТАТУС: ПЕРЕВІРЕНО ЛИШЕ НА BTC.                                  |
//|    Крос-інструментна реплікація НЕ пройдена.                      |
//|    Це ДОСЛІДНИЦЬКИЙ прогін для збору даних, не готова система.    |
//|    Крипта сильно корельована: N позицій != N незалежних ставок.   |
//|                                                                   |
//|  НАЛАШТУВАННЯ ТЕРМІНАЛУ                                           |
//|    Сервіс -> Налаштування -> Радники:                             |
//|      [x] Дозволити алгоритмічну торгівлю                          |
//|      [x] WebRequest -> додати https://fapi.binance.com            |
//|    Кнопка "Алготрейдинг" має бути УВІМКНЕНА.                      |
//|                                                                   |
//|  === v1.80 ФІНАЛЬНА КОНФІГУРАЦІЯ (еталонний симулятор sim.py) ===  |
//|                                                                   |
//|  ВСІ попередні числа були ЗАВИЩЕНІ: симулятор дозволяв заповнення |
//|  на старому рівні після того, як chase мав його замінити, тобто   |
//|  брав кращий із двох варіантів заднім числом. Виправлено.         |
//|                                                                   |
//|  Портфель BTC+SOL, 2021-01..2026-08:                              |
//|    N=20139 (3564/рік)  WR 65.7%  R/рік 881  DD 21.4 R  R/DD 41.1  |
//|    найдовша серія програшів 11                                    |
//|    роки: 2021:+0.293 2022:+0.245 2023:+0.242                      |
//|           2024:+0.241 2025:+0.230 2026:+0.259                     |
//|                                                                   |
//|  Окремо:                                                          |
//|    BTC N=10857 заповн 31% WR 66.0% EV +0.281 t 19.01 R/DD 33.2    |
//|    SOL N= 9282 заповн 32% WR 65.4% EV +0.207 t 14.48 R/DD 27.9    |
//|  Контролі:                                                        |
//|    перемішаний сигнал -6% / -36%   z 19.92 / 19.40  PASS          |
//|    блочний сурогат    82% / 78%    z  3.15 /  2.75  PASS          |
//|    6/6 років на обох, половини рівні, G0.2 топ-10 6.0-6.4%        |
//|                                                                   |
//|  УВАГА: сурогат 78-82% означає, що БІЛЬШІСТЬ результату дає       |
//|  механіка входу (відкат 1.5 ATR), а не бік сигналу. Сигнал додає  |
//|  надійно (z~3), але він не основне джерело.                       |
//|                                                                   |
//|  ЧОМУ CHASE ВИМКНЕНО (виміряно на BTC, розклад 13756 сигналів):   |
//|    A: угоди тільки завдяки chase  21%  EV +1.062 WR 80%  +553 R/р |
//|    B: chase перехоплює те, що спрацювало б на 1.5  38%            |
//|         через chase EV -0.722 WR 14%  проти  на 1.5 EV +0.083     |
//|         втрата -743 R/рік                                         |
//|    ЧИСТО: -190 R/рік. Умовне підтягування (тільки якщо ціна пішла |
//|    в наш бік) краще (R/DD 20.4 проти 3.0), але все одно гірше за  |
//|    вимкнене (33.2).                                               |
//|                                                                   |
//|  === v1.90 БАР РІШЕННЯ M5 ===                                     |
//|  Перевірено на СЕКУНДНИХ даних Binance (184 дні, 15.1 млн секунд),|
//|  де заповнення видно точно, а не моделюється по high/low бару:    |
//|    бар рішення   N     WR     EV      t    R/рік  R/DD            |
//|    M15 (було)   889   70.4%  0.105   2.83   185    9.1            |
//|    M5  (стало) 1005   71.9%  0.206   5.46   411   30.9            |
//|    M1          1127   70.1%  0.311   7.96   696   42.5            |
//|  Причина: рівень лімітки рахується від СВІЖІШОЇ ціни. За 15 хв    |
//|  ціна встигає піти, і рівень 1.5 ATR від старої ціни опиняється   |
//|  або надто близько (токсичне заповнення), або надто далеко.       |
//|  M1 не беремо: заповнюваність лише 6%, а L/S оновлюється раз на   |
//|  5 хв — M5 збігається з частотою джерела даних.                   |
//|  Контроль перемішування: реальний +0.206, перемішаний -0.014,     |
//|  z=+5.71 PASS.                                                    |
//|  Заявка 3 год і пауза 3 год ПЕРЕВІРЕНІ на M5 сіткою 2-6 x 1-4 год:|
//|  коротша заявка дає МІНУС (15 хв -> EV -0.089), плато 2-4 год.    |
//|                                                                   |
//|  УВАГА ПРО ОЧІКУВАННЯ: модель на барах M15 завищувала. Секундна   |
//|  оцінка R/DD ~31, з поправкою на прослизання і чергу лімітки      |
//|  реалістично 15-20, тобто при ризику 0.25% це 50-70% на рік.      |
//|                                                                   |
//|  ETH ВИКЛЮЧЕНО: спред 0.230 ATR проти 0.054 у BTC.                |
//|    R/DD 6.6 проти 33.2. Плюс при lock<спреду беззбиток ЛАМАЄТЬСЯ: |
//|    на ETH з lock 0.15 WR падав до 23.9%, серія програшів 28.      |
//|                                                                   |
//|  === v1.91 ПІДТВЕРДЖЕННЯ ВІДКАТУ (Confirm) ===                     |
//|  Проблема v1.80/v1.90: лімітка 1.5 ATR часто заповнюється на      |
//|  продовженні руху → миттєвий стоп (токсичний fill).               |
//|  Рішення: після сигналу z чекаємо, поки ціна пройде               |
//|  InpConfirmATR (0.25–0.50) ПРОТИ натовпу, і тільки тоді           |
//|  входимо по ринку (або дуже близьким лімітом).                    |
//|                                                                   |
//|  Тест Jun–Aug 2026 (BTC+SOL, спрощений симулятор):                |
//|    Original (entry 1.5 / stop 1.0): EV -0.218, R/DD -0.94         |
//|    Confirm 0.25 + stop 1.50:       EV +0.042, R/DD +8.02         |
//|    Confirm 0.50 + stop 1.25:       EV +0.025, R/DD +3.08         |
//|  Додатковий limit після confirm знову погіршує результат.        |
//|                                                                   |
//|  Рекомендовані стартові параметри:                                |
//|    M15 confirm 0.25 ATR; passive limit retrace 0.60 ATR |
//|    InpStopATR=4.50, InpTakeProfitATR=10.0, max hold 24h       |
//|    InpPauseMode=ATR, InpPauseATR=1.0, InpMaxTradesPerDay=3       |
//|    v2.00: LONG z<=-2.05; SHORT z>=+2.05; LAB032 flat risk        |
//|                                                                   |
//+------------------------------------------------------------------+
//|  === v2.00 LIVE CANDIDATE ===                                     |
//|  BTC+ETH+SOL by default. Signal logic frozen except Z candidate.  |
//|  Z 2.05/2.05; M15 confirm 0.25 ATR; confirm TTL 60m;              |
//|  passive retrace 0.60 ATR; pending TTL 20m; SL 4.5 ATR;           |
//|  fixed TP 10 ATR; max hold 24h; BE/trailing/signal-exit OFF.      |
//|  LAB032: FLAT risk 1.00x for HIGH/NORMAL/LOW.                     |
//|  Quality state remains diagnostic/audit only; no lot multiplier.  |
//|  Optional research overlays remain OFF by default.                |
//+------------------------------------------------------------------+
#property copyright "ResearchOS"
#property version   "2.01"
//|  === v2.00 FROZEN ENTRY ===                                      |
//|    LONG  (BUY):  z <= -InpZThresholdLong   default 2.05              |
//|    SHORT (SELL): z >= +InpZThresholdShort  default 2.05              |
//|    Live candidate 2.05/2.05 thresholds; LAB032 flat risk.                 |
//+------------------------------------------------------------------+
#property strict
#property description "CrowdFade v2.00b DEMO: frozen v200 core + staged G1 FAST lane (20% @0.10ATR, 80% @0.30ATR)."

#include <Trade\Trade.mqh>

//--- символи -------------------------------------------------------
input group "=== СИМВОЛИ ==="
input string InpPairs = "BTCUSD:BTCUSDT;ETHUSD:ETHUSDT;SOLUSD:SOLUSDT";
                                          // брокер:Binance через ;

//--- сигнал --------------------------------------------------------
input group "=== СИГНАЛ (заморожено дослідженням) ==="
input int    InpZWindowHours  = 6;        // [v1.10] Вікно смуги, годин (було 24)
input double InpZThresholdLong = 2.05;     // [v1.93] BUY: crowd extremely SHORT, z <= -threshold
input double InpZThresholdShort= 2.05;     // [v1.93] SELL: crowd extremely LONG,  z >= +threshold
input int    InpOrderValidMin = 20;       // Pending limit TTL, minutes
input double InpStopATR       = 4.50;     // Frozen robust hard stop
input double InpTakeProfitATR = 10.00;    // Frozen robust fixed TP (TP10)
input int    InpHoldHours     = 24;        // [v1.10] Тримання, годин (було 24)
input int    InpPauseHours    = 3;        // [v1.91] мін. години (для Hours / hybrid)
input int    InpAtrPeriod     = 14;       // ATR на M15
input double InpExitZ         = 0.00;     // Frozen core: signal reversal exit OFF     // [v1.91] м'якший вихід (було 1.00)
input bool   InpChaseOrder    = false;    // [v1.80] ВИМКНЕНО: шкодить (див. шапку)
input int    InpChaseAfterBars= 4;        // [v1.30] через скільки барів M15
input double InpChaseToATR    = 0.40;     // [v1.30] новий відступ від ціни, ATR

input group "=== [v1.91] ПІДТВЕРДЖЕННЯ ВІДКАТУ ==="
input double InpConfirmATR     = 0.25;     // скільки ATR має пройти ціна проти натовпу
input int    InpConfirmMaxBars = 4;        // max 4 completed M15 bars = 60 minutes
input double InpConfirmLimitATR= 0.60;     // passive retrace from confirmation close     // додатковий відступ якщо limit

input group "=== v2.00b DEMO FAST LANE — LAB041D FROZEN ==="
input bool   InpFastLaneEnabled        = true;  // Demo candidate: add lower-Z G1 FAST lane without changing CORE
input double InpFastZMin               = 1.00;  // FAST lower bound: 1.00 <= |Z|
input double InpFastZMax               = 2.05;  // FAST upper bound: |Z| < 2.05 (CORE owns >=2.05)
input double InpFastRiskMult           = 0.25;  // Total FAST event risk = 0.25x CORE risk
input double InpFastProbeFraction      = 0.20;  // 20% of FAST risk at +0.10 ATR probe
input double InpFastProbeATR           = 0.10;  // Early causal response trigger
input double InpFastConfirmATR         = 0.30;  // Add remaining 80% only after full confirmation
input int    InpFastConfirmTimeoutMin  = 180;   // Probe/event timeout from original signal
input double InpFastResponseMidMin     = 0.50;  // G1 response branch A lower bound
input double InpFastResponseMidMax     = 1.00;  // G1 response branch A upper bound (exclusive)
input double InpFastResponseStrongMin  = 2.50;  // G1 response branch B lower bound
input double InpFastPauseATR           = 1.00;  // Independent FAST re-entry pause
input int    InpFastMaxTradesPerDay    = 3;     // Accepted FAST events per symbol/day
input int    InpFastSignalMaxAgeSec    = 600;   // Latest completed canonical M5 signal bar freshness
input long   InpFastMagic              = 77201; // Separate magic so CORE and FAST can overlap safely

input group "=== [v1.91] ПАУЗА / ЛІМІТ УГОД ==="
input string InpPauseMode      = "ATR";    // Hours | ATR | Hours+ATR
input double InpPauseATR       = 1.00;     // для ATR: мін. рух ціни від last entry
input int    InpMaxTradesPerDay= 3;        // макс угод на пару за день (0=без ліміту)

input group "=== LEGACY SCORE (NOT USED BY v2.00 ENTRY) ==="
input bool   InpUseScore      = false;    // Legacy model disabled in v2.00     // вмикати зважування
input double InpScoreGain     = 0.60;     // сила зважування (0 = вимкнено)
input double InpScoreMinW     = 0.40;     // мін множник лота
input double InpScoreMaxW     = 2.00;     // макс множник лота

input group "=== [v1.50] Частковий вихід ==="
input bool   InpPartialClose  = false;    // вмикати частковий вихід
input double InpPartialAtATR  = 1.50;     // рівень у ATR від входу
input double InpPartialFrac   = 0.50;     // яку частку закрити (0.1..0.9)

input group "=== [v1.70] Беззбиток ==="
input double InpBreakEvenAtATR= 0.00;     // Frozen core: OFF     // [v1.80] було 1.00
input double InpBreakEvenLock = 0.00;     // [v1.80] МУСИТЬ бути > спреду в ATR!

input group "=== v2.00 OPTIONAL TRAILING (OFF BY DEFAULT) ==="
input bool   InpTrailOn        = false;    // Frozen base: OFF; optional research overlay only
input double InpTrailDistanceR = 2.50;     // Distance from real peak in INITIAL R
input double InpTrailArmR      = 1.00;     // Arm tracking logic after +1R MFE

//--- ризик ---------------------------------------------------------
input group "=== РИЗИК ==="
input double InpRiskPct       = 0.10;     // Flat risk per trade, % balance/equity sizing basis
input group "=== v2.00 QUALITY STATE (LAB032: DIAGNOSTIC ONLY) ==="
input bool   InpUseQualityRisk          = false; // LAB032: OFF; HIGH/NORMAL/LOW must not change lot
input double InpHighRiskMult            = 1.00;  // diagnostic override only
input double InpNormalRiskMult          = 1.00;  // diagnostic override only
input double InpLowRiskMult             = 1.00;  // diagnostic override only
input double InpCrowdContinuationATR    = 0.75; // classification retained for audit/logging only
input bool   InpAutoBrokerCostProfile    = true; // FTMO=>6.5bps RT; IC Markets/GetLeveraged=>0; otherwise manual fallback
input double InpCommissionRoundTurnBps   = 0.00; // Manual fallback/override when auto profile is OFF
input double InpMaxNotionalPctEquity     = 15.0; // HARD CAP: one new position notional <= 15% equity; 0=off
input bool   InpAdaptiveMarginLot         = true; // Reduce lot instead of hard MARGIN_BLOCK
input double InpMarginSafetyPct           = 90.0; // Free-margin safety ceiling
input double InpMaxNewTradeMarginPct      = 5.0;  // HARD CAP: margin of one new trade <= 5% equity; 0=off
input double InpMaxAccountMarginPct       = 12.0; // HARD CAP: projected total account margin <= 12% equity; 0=off
input double InpMinMarginLotFrac          = 0.25; // Skip only if margin clamp leaves <25% of notional-capped lot
input double InpMinVolumeLotFrac          = 0.25; // Skip only if broker/manual cap leaves <25% of raw risk lot
input int    InpMaxPositions  = 3;        // МАКС одночасних позицій (крипта корельована!)
input int    InpMaxPerSide    = 2;        // Макс позицій в один бік
input double InpMaxSpreadATR  = 0.30;     // Спред-гейт у частках ATR
input double InpMaxDailyDDPct = 3.00;     // Денна просадка -> стоп на день
input double InpMaxTotalDDPct = 8.00;     // Загальна просадка -> стоп EA
input double InpMaxLot        = 0.0;      // Optional manual lot ceiling; 0 = disabled (use broker max + margin clamp)
input int    InpSlippagePts   = 50;       // Прослизання
input long   InpMagic         = 77200;    // v2.00 isolated magic    // Magic

//--- безпека -------------------------------------------------------
input group "=== БЕЗПЕКА ==="
input bool   InpDemoOnly      = true;     // Forward phase safety: demo only by default    // [v1.70] дефолт: реальний рахунок ДОЗВОЛЕНО
input bool   InpDryRun        = false;    // true = тільки лог, без ордерів
input int    InpRefreshSec    = 60;       // Період опитування Binance

input group "=== v2.00 CANONICAL BINANCE PRICE ==="
input bool   InpUseCanonicalBinancePrice = true;  // Signal/ATR/confirmation from Binance USD-M futures
input bool   InpCanonicalStrict          = true;  // If canonical price is stale/unavailable: do NOT fall back to broker candles
input int    InpCanonicalMaxAgeSec       = 1200;  // Latest completed M15 bar may naturally be up to ~15m old
input bool   InpWriteCsv      = true;     // Журнал сигналів у CSV
input bool   InpVerbose       = true;     // Детальний лог

input group "=== [v1.62] EXECUTION PARITY ==="
input int    InpExecTimerMs        = 1000;    // Детермінований management scheduler, мс
input int    InpWebTimeoutMs       = 4000;    // Timeout WebRequest
input int    InpMaxFeedAgeSec      = 900;     // Не відкривати/не signal-exit на старих Binance даних
input int    InpChaseMaxRetries    = 3;       // Повтори ТОГО САМОГО chase target при технічній відмові
input bool   InpCloseOnDailyHalt   = true;    // Prop safety: закрити позиції при daily DD stop
input bool   InpPersistState       = true;    // Зберігати cooldown/DD/trailing між restart/VPS sync
input bool   InpResetRiskState     = false;   // Разово скинути persistent DD state на старті
input bool   InpWriteExecutionCsv  = true;    // Детальний execution trace у FILE_COMMON

//--- константи -----------------------------------------------------
#define API_HOST    "https://fapi.binance.com"
#define API_PATH    "/futures/data/globalLongShortAccountRatio"
#define KLINE_PATH  "/fapi/v1/klines"
#define MAX_POINTS  500
#define BIN_PERIOD  "5m"
#define BIN_STEP_S  300
#define MAX_SYM     32
#define ORDER_TAG   "CrowdFade_v200b"

//--- [v1.40] модель: коефіцієнти, середні та sd з навчальної вибірки --
#define SC_CONST      0.3301
#define SC_B_ABSZ     0.0099
#define SC_B_Z40      0.0007
#define SC_B_ABSZ40  -0.0271
#define SC_B_DUR      0.0225
#define SC_B_VOLZ     0.0454
#define SC_B_DSTR    -0.0751
#define SC_B_HRACT    0.0230
#define SC_M_ABSZ     1.5798
#define SC_S_ABSZ     0.5177
#define SC_M_Z40      0.6680
#define SC_S_Z40      0.4709
#define SC_M_ABSZ40   1.2505
#define SC_S_ABSZ40   0.8240
#define SC_M_DUR      5.8770
#define SC_S_DUR      8.5729
#define SC_M_VOLZ     0.2025
#define SC_S_VOLZ     1.3152
#define SC_M_DSTR     1.9042
#define SC_S_DSTR     1.7401
#define SC_M_HRACT    0.3875
#define SC_S_HRACT    0.4872
#define SC_SD         0.1078
CTrade g_trade;
CTrade g_fastTrade;

struct SymState
  {
   string   broker;
   string   binance;
   bool     ok;                 // хоча б один валідний fetch
   int      atrHandle;
   int      emaH1Handle;
   int      emaH4Handle;
   double   z;
   double   ratio;
   double   mean;
   double   sd;
   datetime lastFetch;          // останній УСПІШНИЙ локальний fetch
   datetime lastAttempt;        // остання спроба WebRequest
   long     sourceTimeMs;       // timestamp останньої Binance 5m точки
   datetime lastTrade;          // час постановки останньої заявки (cooldown anchor)
   datetime lastBar;
   datetime sigSince;
   double   z40;
   int      durBars;
   string   err;
   // [v1.91] confirmation state
   bool     confActive;         // чекаємо підтвердження відкату
   int      confSide;           // +1 long / -1 short
   double   confSignalPrice;    // ціна в момент сигналу
   double   confZ;              // original crowd Z snapshot; audit only in v2.00a
   double   confAtr;            // ATR snapshot на сигналі
   datetime confSignalTime;
   int      confBarsLeft;       // remaining completed M15 bars
   double   confMaxCrowdExcATR; // max price excursion in CROWD direction before confirm
   int      confH1State;        // H1 trend state frozen at original signal
   int      confH4State;        // H4 trend state frozen at original signal
   long     confSourceTimeMs;    // frozen Binance crowd timestamp at ORIGINAL signal arm
   // v2.00 canonical Binance price state
   bool     canonOk;
   datetime canonLastFetch;
   long     canonM15OpenMs;
   long     canonM15CloseMs;
   double   canonM15Open;
   double   canonM15High;
   double   canonM15Low;
   double   canonM15Close;
   double   canonAtr14;
   long     canonM5OpenMs;
   long     canonM5CloseMs;
   double   canonM5Open;
   double   canonM5High;
   double   canonM5Low;
   double   canonM5Close;
   int      canonH1State;
   int      canonH4State;
   string   canonErr;
   // [v1.91] adaptive pause + daily limit
   double   lastEntryPrice;     // ціна останнього входу (для ATR-паузи)
   double   lastEntryAtr;       // ATR на момент входу
   int      dayTradeCount;      // угод сьогодні по цій парі
   int      dayTradeCode;       // YYYYMMDD останнього підрахунку

   // v2.00b staged FAST lane state (independent from CORE confirmation)
   bool     fastActive;
   bool     fastProbeOpen;
   int      fastSide;
   double   fastSignalPrice;    // canonical Binance M5 close at arm
   double   fastSignalAtr;      // frozen canonical M15 ATR
   double   fastOrigZ;
   datetime fastSignalTime;
   long     fastSourceTimeMs;
   long     fastLastArmM5Ms;
   double   fastBasis;          // broker mid - canonical signal price
   double   fastMaxThesisATR;
   double   fastMaxCrowdATR;
   int      fastH1State;
   int      fastH4State;
   datetime fastProbeTime;
   double   fastProbeEntry;
   datetime fastLastTrade;
   double   fastLastEntryPrice;
   double   fastLastEntryAtr;
   int      fastDayTradeCount;
   int      fastDayTradeCode;
  };

struct BrokerSpec
  {
   int      digits;
   double   point;
   double   tickSize;
   double   volumeMin;
   double   volumeMax;
   double   volumeStep;
   long     stopsLevelPts;
   long     freezeLevelPts;
   long     tradeMode;
  };

SymState g_sym[MAX_SYM];
int      g_symCount   = 0;
int      g_fetchIdx   = 0;
int      g_csv        = INVALID_HANDLE;
int      g_execCsv    = INVALID_HANDLE;
int      g_fastCsv    = INVALID_HANDLE;

double   g_eqPeak     = 0.0;
double   g_dayStart   = 0.0;
int      g_dayCode    = -1;
bool     g_haltDay    = false;
bool     g_haltAll    = false;
long     c_sig=0, c_thr=0, c_pause=0, c_maxpos=0, c_side=0,
         c_spread=0, c_lot=0, c_sent=0, c_fail=0, c_sigexit=0, c_timeexit=0,
         c_chased=0, c_chasefail=0, c_partial=0, c_trail=0, c_be=0,
         c_fast_arm=0, c_fast_probe=0, c_fast_confirm=0, c_fast_abort=0, c_fast_fail=0;

//--- persistent keys ------------------------------------------------
string GVPrefix()
  {
   return StringFormat("CF200_%I64d_%I64d_", AccountInfoInteger(ACCOUNT_LOGIN), InpMagic);
  }
string GVKey(const string suffix) { return GVPrefix() + suffix; }
string GVOrderKey(const ulong ticket,const string suffix)
  { return GVPrefix()+"O"+IntegerToString((long)ticket)+"_"+suffix; }
string GVPosKey(const ulong posId,const string suffix)
  { return GVPrefix()+"P"+IntegerToString((long)posId)+"_"+suffix; }
string GVLastTradeKey(const string sym) { return GVPrefix()+"LT_"+sym; }
string GVFastKey(const string sym,const string suffix) { return GVPrefix()+"FAST_"+sym+"_"+suffix; }

bool IsFastMagic(const long magic) { return(magic==InpFastMagic); }
bool IsManagedMagic(const long magic) { return(magic==InpMagic || IsFastMagic(magic)); }

double GVRead(const string key,const double def=0.0)
  {
   if(!InpPersistState || !GlobalVariableCheck(key)) return def;
   return GlobalVariableGet(key);
  }
void GVWrite(const string key,const double value)
  {
   if(InpPersistState) GlobalVariableSet(key,value);
  }

int CurrentDayCode()
  {
   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   return dt.year*10000 + dt.mon*100 + dt.day;
  }

bool GetBrokerSpec(const string sym,BrokerSpec &sp)
  {
   sp.digits         =(int)SymbolInfoInteger(sym,SYMBOL_DIGITS);
   sp.point          =SymbolInfoDouble(sym,SYMBOL_POINT);
   sp.tickSize       =SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_SIZE);
   sp.volumeMin      =SymbolInfoDouble(sym,SYMBOL_VOLUME_MIN);
   sp.volumeMax      =SymbolInfoDouble(sym,SYMBOL_VOLUME_MAX);
   sp.volumeStep     =SymbolInfoDouble(sym,SYMBOL_VOLUME_STEP);
   sp.stopsLevelPts  =SymbolInfoInteger(sym,SYMBOL_TRADE_STOPS_LEVEL);
   sp.freezeLevelPts =SymbolInfoInteger(sym,SYMBOL_TRADE_FREEZE_LEVEL);
   sp.tradeMode      =SymbolInfoInteger(sym,SYMBOL_TRADE_MODE);
   return(sp.digits>=0 && sp.point>0.0 && sp.tickSize>0.0 && sp.volumeStep>0.0);
  }

double NormalizePriceTick(const string sym,const double price,const int dir)
  {
   BrokerSpec sp; if(!GetBrokerSpec(sym,sp)) return price;
   double q=price/sp.tickSize;
   double nq=(dir>0)?MathCeil(q-1e-12):((dir<0)?MathFloor(q+1e-12):MathRound(q));
   return NormalizeDouble(nq*sp.tickSize,sp.digits);
  }

double MinTradeDistance(const string sym,const bool forModify)
  {
   BrokerSpec sp; if(!GetBrokerSpec(sym,sp)) return 0.0;
   long p=sp.stopsLevelPts;
   if(forModify && sp.freezeLevelPts>p) p=sp.freezeLevelPts;
   return (double)p*sp.point;
  }

bool RetcodeAccepted(const uint rc)
  {
   return(rc==TRADE_RETCODE_DONE || rc==TRADE_RETCODE_PLACED ||
          rc==TRADE_RETCODE_DONE_PARTIAL || rc==TRADE_RETCODE_NO_CHANGES);
  }

void LogExec(const string event,const string sym,const ulong ticket,const string side,
             const double reqPrice,const double reqSL,const double actualPrice,
             const double actualSL,const uint retcode,const string note="")
  {
   if(g_execCsv==INVALID_HANDLE) return;
   long src=0;
   int si=-1;
   for(int i=0;i<g_symCount;i++) if(g_sym[i].broker==sym){si=i;break;}
   if(si>=0) src=g_sym[si].sourceTimeMs;
   FileWrite(g_execCsv,
             TimeToString(TimeGMT(),TIME_DATE|TIME_SECONDS),
             TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
             event,sym,IntegerToString((long)ticket),side,
             DoubleToString(reqPrice,8),DoubleToString(reqSL,8),
             DoubleToString(actualPrice,8),DoubleToString(actualSL,8),
             IntegerToString((int)retcode),IntegerToString(src),note);
   FileFlush(g_execCsv);
  }

void PrintBrokerSpecs(const string sym)
  {
   BrokerSpec sp;
   if(!GetBrokerSpec(sym,sp)) { PrintFormat("SPEC %s: не вдалося прочитати",sym); return; }
   PrintFormat("SPEC %s | digits=%d point=%g tick=%g vol=%.8g..%.8g step=%.8g stops=%d freeze=%d trade_mode=%d",
               sym,sp.digits,sp.point,sp.tickSize,sp.volumeMin,sp.volumeMax,sp.volumeStep,
               (int)sp.stopsLevelPts,(int)sp.freezeLevelPts,(int)sp.tradeMode);
  }

//+------------------------------------------------------------------+
int ParsePairs()
  {
   PrintFormat("InpPairs = [%s]", InpPairs);
   PrintFormat("довжина рядка: %d символів", StringLen(InpPairs));

   string items[];
   int n = StringSplit(InpPairs, (ushort)';', items);
   PrintFormat("розбито на %d елементів", n);
   if(n <= 0)
     {
      Print("ПОМИЛКА: StringSplit по ';' повернув 0. Перевірте формат InpPairs.");
      return 0;
     }

   int cnt = 0;
   for(int i = 0; i < n && cnt < MAX_SYM; i++)
     {
      string it = items[i];
      StringTrimLeft(it); StringTrimRight(it);
      if(StringLen(it) == 0) continue;

      string b = "", x = "";
      string kv[];
      int m = StringSplit(it, (ushort)':', kv);
      if(m == 2)
        {
         b = kv[0]; x = kv[1];
        }
      else if(m == 1)
        {
         // [v1.11] двокрапки немає: виводимо назву Binance автоматично
         b = kv[0];
         x = b;
         if(StringFind(x, "USDT") < 0)
           {
            int pu = StringFind(x, "USD");
            if(pu >= 0) x = StringSubstr(x, 0, pu) + "USDT";
            else        x = x + "USDT";
           }
         PrintFormat("  [%s] двокрапки немає -> Binance підставлено як %s", b, x);
        }
      else
        {
         PrintFormat("  ПРОПУСК [%s]: очікував формат брокер:binance", it);
         continue;
        }

      StringTrimLeft(b); StringTrimRight(b);
      StringTrimLeft(x); StringTrimRight(x);
      if(StringLen(b) == 0 || StringLen(x) == 0)
        {
         PrintFormat("  ПРОПУСК [%s]: порожня частина", it);
         continue;
        }

      if(!SymbolSelect(b, true))
        {
         PrintFormat("  ПРОПУСК %s: SymbolSelect=false. Перевірте точну назву у Market Watch.", b);
         continue;
        }
      if(SymbolInfoDouble(b, SYMBOL_BID) <= 0.0 && SymbolInfoInteger(b, SYMBOL_DIGITS) <= 0)
        {
         PrintFormat("  ПРОПУСК %s: символ без котирувань", b);
         continue;
        }

      int hnd = iATR(b, PERIOD_M15, InpAtrPeriod);
      int h1h = iMA(b, PERIOD_H1, 50, 0, MODE_EMA, PRICE_CLOSE);
      int h4h = iMA(b, PERIOD_H4, 50, 0, MODE_EMA, PRICE_CLOSE);
      if(hnd == INVALID_HANDLE || h1h == INVALID_HANDLE || h4h == INVALID_HANDLE)
        {
         PrintFormat("  ПРОПУСК %s: ATR/EMA handles not created", b);
         if(hnd!=INVALID_HANDLE) IndicatorRelease(hnd);
         if(h1h!=INVALID_HANDLE) IndicatorRelease(h1h);
         if(h4h!=INVALID_HANDLE) IndicatorRelease(h4h);
         continue;
        }

      g_sym[cnt].broker    = b;
      g_sym[cnt].binance   = x;
      g_sym[cnt].ok        = false;
      g_sym[cnt].atrHandle = hnd;
      g_sym[cnt].emaH1Handle = h1h;
      g_sym[cnt].emaH4Handle = h4h;
      g_sym[cnt].z = 0; g_sym[cnt].ratio = 0; g_sym[cnt].mean = 0; g_sym[cnt].sd = 0;
      g_sym[cnt].lastFetch = 0; g_sym[cnt].lastAttempt = 0; g_sym[cnt].sourceTimeMs = 0; g_sym[cnt].lastTrade = 0; g_sym[cnt].lastBar = 0;
      g_sym[cnt].canonOk=false; g_sym[cnt].canonLastFetch=0; g_sym[cnt].canonM15OpenMs=0; g_sym[cnt].canonM15CloseMs=0;
      g_sym[cnt].canonM15Open=0; g_sym[cnt].canonM15High=0; g_sym[cnt].canonM15Low=0; g_sym[cnt].canonM15Close=0; g_sym[cnt].canonAtr14=0;
      g_sym[cnt].canonM5OpenMs=0; g_sym[cnt].canonM5CloseMs=0; g_sym[cnt].canonM5Open=0; g_sym[cnt].canonM5High=0; g_sym[cnt].canonM5Low=0; g_sym[cnt].canonM5Close=0;
      g_sym[cnt].canonH1State=0; g_sym[cnt].canonH4State=0; g_sym[cnt].canonErr=""; g_sym[cnt].confSourceTimeMs=0;
      g_sym[cnt].sigSince = 0;
      g_sym[cnt].z40 = 0.0; g_sym[cnt].durBars = 0;
      g_sym[cnt].err = "";
      g_sym[cnt].confActive = false;
      g_sym[cnt].confSide = 0;
      g_sym[cnt].confSignalPrice = 0;
      g_sym[cnt].confZ = 0;
      g_sym[cnt].confAtr = 0;
      g_sym[cnt].confSignalTime = 0;
      g_sym[cnt].confBarsLeft = 0;
      g_sym[cnt].confMaxCrowdExcATR = 0.0;
      g_sym[cnt].confH1State = 0;
      g_sym[cnt].confH4State = 0;
      g_sym[cnt].lastEntryPrice = 0;
      g_sym[cnt].lastEntryAtr = 0;
      g_sym[cnt].dayTradeCount = 0;
      g_sym[cnt].dayTradeCode = -1;
      g_sym[cnt].fastActive=false; g_sym[cnt].fastProbeOpen=false; g_sym[cnt].fastSide=0;
      g_sym[cnt].fastSignalPrice=0; g_sym[cnt].fastSignalAtr=0; g_sym[cnt].fastOrigZ=0; g_sym[cnt].fastSignalTime=0;
      g_sym[cnt].fastSourceTimeMs=0; g_sym[cnt].fastLastArmM5Ms=0; g_sym[cnt].fastBasis=0;
      g_sym[cnt].fastMaxThesisATR=0; g_sym[cnt].fastMaxCrowdATR=0; g_sym[cnt].fastH1State=0; g_sym[cnt].fastH4State=0;
      g_sym[cnt].fastProbeTime=0; g_sym[cnt].fastProbeEntry=0; g_sym[cnt].fastLastTrade=0;
      g_sym[cnt].fastLastEntryPrice=0; g_sym[cnt].fastLastEntryAtr=0; g_sym[cnt].fastDayTradeCount=0; g_sym[cnt].fastDayTradeCode=-1;
      PrintFormat("  OK %-12s -> %s", b, x);
      cnt++;
     }
   return cnt;
  }

//+------------------------------------------------------------------+
datetime RecoverLastOrderTime(const string sym)
  {
   datetime best=0;
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i);if(!OrderSelect(tk)) continue;
      if(OrderGetInteger(ORDER_MAGIC)!=InpMagic || OrderGetString(ORDER_SYMBOL)!=sym) continue;
      datetime t=(datetime)OrderGetInteger(ORDER_TIME_SETUP);if(t>best) best=t;
     }
   int n=HistoryOrdersTotal();
   for(int i=n-1;i>=0;i--)
     {
      ulong tk=HistoryOrderGetTicket(i);if(tk==0) continue;
      if(HistoryOrderGetInteger(tk,ORDER_MAGIC)!=InpMagic || HistoryOrderGetString(tk,ORDER_SYMBOL)!=sym) continue;
      datetime t=(datetime)HistoryOrderGetInteger(tk,ORDER_TIME_SETUP);if(t>best) best=t;
     }
   return best;
  }

void PersistFastState(const int idx)
  {
   if(!InpPersistState || idx<0 || idx>=g_symCount) return;
   string s=g_sym[idx].broker;
   GVWrite(GVFastKey(s,"ACTIVE"),g_sym[idx].fastActive?1.0:0.0);
   GVWrite(GVFastKey(s,"PROBE"),g_sym[idx].fastProbeOpen?1.0:0.0);
   GVWrite(GVFastKey(s,"SIDE"),(double)g_sym[idx].fastSide);
   GVWrite(GVFastKey(s,"SIGPX"),g_sym[idx].fastSignalPrice);
   GVWrite(GVFastKey(s,"ATR"),g_sym[idx].fastSignalAtr);
   GVWrite(GVFastKey(s,"ORIGZ"),g_sym[idx].fastOrigZ);
   GVWrite(GVFastKey(s,"SIGTIME"),(double)g_sym[idx].fastSignalTime);
   GVWrite(GVFastKey(s,"SRCMS"),(double)g_sym[idx].fastSourceTimeMs);
   GVWrite(GVFastKey(s,"LASTM5"),(double)g_sym[idx].fastLastArmM5Ms);
   GVWrite(GVFastKey(s,"BASIS"),g_sym[idx].fastBasis);
   GVWrite(GVFastKey(s,"MAXTH"),g_sym[idx].fastMaxThesisATR);
   GVWrite(GVFastKey(s,"MAXCR"),g_sym[idx].fastMaxCrowdATR);
   GVWrite(GVFastKey(s,"H1"),(double)g_sym[idx].fastH1State);
   GVWrite(GVFastKey(s,"H4"),(double)g_sym[idx].fastH4State);
   GVWrite(GVFastKey(s,"PTIME"),(double)g_sym[idx].fastProbeTime);
   GVWrite(GVFastKey(s,"PENTRY"),g_sym[idx].fastProbeEntry);
   GVWrite(GVFastKey(s,"LASTTRADE"),(double)g_sym[idx].fastLastTrade);
   GVWrite(GVFastKey(s,"LASTPX"),g_sym[idx].fastLastEntryPrice);
   GVWrite(GVFastKey(s,"LASTATR"),g_sym[idx].fastLastEntryAtr);
   GVWrite(GVFastKey(s,"DAYCNT"),(double)g_sym[idx].fastDayTradeCount);
   GVWrite(GVFastKey(s,"DAYCODE"),(double)g_sym[idx].fastDayTradeCode);
  }

void LoadFastState(const int idx)
  {
   if(!InpPersistState || !InpFastLaneEnabled || idx<0 || idx>=g_symCount) return;
   string s=g_sym[idx].broker;
   g_sym[idx].fastActive=(GVRead(GVFastKey(s,"ACTIVE"),0.0)>0.5);
   g_sym[idx].fastProbeOpen=(GVRead(GVFastKey(s,"PROBE"),0.0)>0.5);
   g_sym[idx].fastSide=(int)GVRead(GVFastKey(s,"SIDE"),0.0);
   g_sym[idx].fastSignalPrice=GVRead(GVFastKey(s,"SIGPX"),0.0);
   g_sym[idx].fastSignalAtr=GVRead(GVFastKey(s,"ATR"),0.0);
   g_sym[idx].fastOrigZ=GVRead(GVFastKey(s,"ORIGZ"),0.0);
   g_sym[idx].fastSignalTime=(datetime)GVRead(GVFastKey(s,"SIGTIME"),0.0);
   g_sym[idx].fastSourceTimeMs=(long)GVRead(GVFastKey(s,"SRCMS"),0.0);
   g_sym[idx].fastLastArmM5Ms=(long)GVRead(GVFastKey(s,"LASTM5"),0.0);
   g_sym[idx].fastBasis=GVRead(GVFastKey(s,"BASIS"),0.0);
   g_sym[idx].fastMaxThesisATR=GVRead(GVFastKey(s,"MAXTH"),0.0);
   g_sym[idx].fastMaxCrowdATR=GVRead(GVFastKey(s,"MAXCR"),0.0);
   g_sym[idx].fastH1State=(int)GVRead(GVFastKey(s,"H1"),0.0);
   g_sym[idx].fastH4State=(int)GVRead(GVFastKey(s,"H4"),0.0);
   g_sym[idx].fastProbeTime=(datetime)GVRead(GVFastKey(s,"PTIME"),0.0);
   g_sym[idx].fastProbeEntry=GVRead(GVFastKey(s,"PENTRY"),0.0);
   g_sym[idx].fastLastTrade=(datetime)GVRead(GVFastKey(s,"LASTTRADE"),0.0);
   g_sym[idx].fastLastEntryPrice=GVRead(GVFastKey(s,"LASTPX"),0.0);
   g_sym[idx].fastLastEntryAtr=GVRead(GVFastKey(s,"LASTATR"),0.0);
   g_sym[idx].fastDayTradeCount=(int)GVRead(GVFastKey(s,"DAYCNT"),0.0);
   g_sym[idx].fastDayTradeCode=(int)GVRead(GVFastKey(s,"DAYCODE"),-1.0);
  }

void ResetFastEvent(const int idx,const bool keepLastM5=true)
  {
   if(idx<0 || idx>=g_symCount) return;
   long lm5=g_sym[idx].fastLastArmM5Ms;
   g_sym[idx].fastActive=false;
   g_sym[idx].fastProbeOpen=false;
   g_sym[idx].fastSide=0;
   g_sym[idx].fastSignalPrice=0.0;
   g_sym[idx].fastSignalAtr=0.0;
   g_sym[idx].fastOrigZ=0.0;
   g_sym[idx].fastSignalTime=0;
   g_sym[idx].fastSourceTimeMs=0;
   g_sym[idx].fastBasis=0.0;
   g_sym[idx].fastMaxThesisATR=0.0;
   g_sym[idx].fastMaxCrowdATR=0.0;
   g_sym[idx].fastH1State=0;
   g_sym[idx].fastH4State=0;
   g_sym[idx].fastProbeTime=0;
   g_sym[idx].fastProbeEntry=0.0;
   if(keepLastM5) g_sym[idx].fastLastArmM5Ms=lm5;
   else g_sym[idx].fastLastArmM5Ms=0;
   PersistFastState(idx);
  }

int OnInit()
  {
   if(InpDemoOnly && AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
     {
      Print("ЗУПИНЕНО: InpDemoOnly=true, а рахунок РЕАЛЬНИЙ.");
      return INIT_FAILED;
     }
   if(InpZWindowHours < 2 || InpZWindowHours > 40)
     { Print("ПОМИЛКА: InpZWindowHours поза [2..40]"); return INIT_PARAMETERS_INCORRECT; }
   if(InpZThresholdLong <= 0.0 || InpZThresholdShort <= 0.0 || InpStopATR <= 0.0 || InpTakeProfitATR <= 0.0 || InpRiskPct <= 0.0)
     { Print("ERROR: invalid signal/risk parameters"); return INIT_PARAMETERS_INCORRECT; }
   if(InpTrailOn && (InpTrailDistanceR<=0.0 || InpTrailArmR<0.0))
     { Print("ERROR: invalid dynamic trailing parameters"); return INIT_PARAMETERS_INCORRECT; }
   if(InpConfirmMaxBars<1 || InpOrderValidMin<1 || InpHighRiskMult<=0.0 || InpNormalRiskMult<=0.0 || InpLowRiskMult<=0.0)
     { Print("ERROR: invalid confirmation/TTL/quality-risk parameters"); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxNotionalPctEquity<0.0 || InpMaxNewTradeMarginPct<0.0 || InpMaxAccountMarginPct<0.0 ||
      InpMaxNotionalPctEquity>100.0 || InpMaxNewTradeMarginPct>100.0 || InpMaxAccountMarginPct>100.0)
     { Print("ERROR: invalid notional/margin caps"); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxPositions < 1 || InpMaxPerSide < 1 || InpExecTimerMs < 100)
     { Print("ПОМИЛКА: ліміти позицій/таймера"); return INIT_PARAMETERS_INCORRECT; }
   if(InpFastLaneEnabled)
     {
      if(InpFastMagic==InpMagic || InpFastZMin<=0.0 || InpFastZMax<=InpFastZMin ||
         InpFastRiskMult<=0.0 || InpFastProbeFraction<=0.0 || InpFastProbeFraction>=1.0 ||
         InpFastProbeATR<=0.0 || InpFastConfirmATR<=InpFastProbeATR || InpFastConfirmTimeoutMin<1 ||
         InpFastResponseMidMin<0.0 || InpFastResponseMidMax<=InpFastResponseMidMin ||
         InpFastResponseStrongMin<=InpFastResponseMidMax || InpFastPauseATR<0.0)
        { Print("ERROR: invalid v2.00b FAST-lane parameters"); return INIT_PARAMETERS_INCORRECT; }
      if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
        { Print("STOP: v2.00b staged FAST lane requires a HEDGING MT5 account for independent 20/80 tranches."); return INIT_FAILED; }
     }

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints((ulong)InpSlippagePts);
   g_trade.SetAsyncMode(false);
   g_trade.SetMarginMode();
   g_fastTrade.SetExpertMagicNumber((ulong)InpFastMagic);
   g_fastTrade.SetDeviationInPoints((ulong)InpSlippagePts);
   g_fastTrade.SetAsyncMode(false);
   g_fastTrade.SetMarginMode();

   PrintFormat("ACCOUNT | company=%s | server=%s | login=%I64d | leverage=1:%d | margin_mode=%d | trade_mode=%d",
               AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_SERVER),
               AccountInfoInteger(ACCOUNT_LOGIN),(int)AccountInfoInteger(ACCOUNT_LEVERAGE),
               (int)AccountInfoInteger(ACCOUNT_MARGIN_MODE),(int)AccountInfoInteger(ACCOUNT_TRADE_MODE));

   Print("--- розбір списку символів ---");
   g_symCount = ParsePairs();
   if(g_symCount == 0)
     {
      Print("ПОМИЛКА: жодного валідного символу.");
      return INIT_FAILED;
     }

   // Broker/prop specs: НІЧОГО не хардкодимо, читаємо з самого MT5.
   for(int i=0;i<g_symCount;i++) PrintBrokerSpecs(g_sym[i].broker);

   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   int dc=CurrentDayCode();
   if(InpResetRiskState)
     {
      GlobalVariableDel(GVKey("EQPEAK"));
      GlobalVariableDel(GVKey("DAYEQ"));
      GlobalVariableDel(GVKey("DAYCODE"));
      GlobalVariableDel(GVKey("HALTALL"));
      GlobalVariableDel(GVKey("HALTDAY"));
     }
   g_eqPeak=MathMax(eq,GVRead(GVKey("EQPEAK"),eq));
   int storedDay=(int)GVRead(GVKey("DAYCODE"),-1.0);
   if(storedDay==dc)
     {
      g_dayCode=dc;
      g_dayStart=GVRead(GVKey("DAYEQ"),eq);
      g_haltDay=(GVRead(GVKey("HALTDAY"),0.0)>0.5);
     }
   else
     {
      g_dayCode=dc; g_dayStart=eq; g_haltDay=false;
     }
   g_haltAll=(GVRead(GVKey("HALTALL"),0.0)>0.5);
   GVWrite(GVKey("EQPEAK"),g_eqPeak);
   GVWrite(GVKey("DAYEQ"),g_dayStart);
   GVWrite(GVKey("DAYCODE"),(double)g_dayCode);

   // Cooldown anchor зберігається між рестартами; на першому запуску v1.62 відновлюємо з history.
   HistorySelect(TimeCurrent()-(datetime)(30*86400),TimeCurrent());
   for(int i=0;i<g_symCount;i++)
     {
      double saved=GVRead(GVLastTradeKey(g_sym[i].broker),0.0);
      g_sym[i].lastTrade=(saved>0.0)?(datetime)saved:RecoverLastOrderTime(g_sym[i].broker);
      if(g_sym[i].lastTrade>0) GVWrite(GVLastTradeKey(g_sym[i].broker),(double)g_sym[i].lastTrade);
      g_sym[i].sigSince=(datetime)GVRead(GVKey("SIG_"+g_sym[i].broker),0.0);
      LoadFastState(i);
     }

   if(InpWriteCsv)
     {
      string fn="CrowdFade_signals_v200a_broker_vol_diag.csv";
      g_csv=FileOpen(fn,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,';');
      if(g_csv==INVALID_HANDLE) PrintFormat("CSV не відкрито, error=%d",GetLastError());
      else
        {
         bool empty=(FileSize(g_csv)==0);
         FileSeek(g_csv,0,SEEK_END);
         if(empty) FileWrite(g_csv,"time_server","time_utc","signal_id","source_ms","broker","binance","ratio","mean","sd","z",
                                 "canon_close","canon_atr","broker_ref","basis","broker_bid","broker_ask","spread","side",
                                 "entry","stop","tp","raw_desired_lot","broker_capped_lot","notional_capped_lot","actual_lot","desired_risk_pct","actual_risk_pct","est_comm_rt",
                                 "notional","notional_pct_eq","margin_pct_eq","cost_rt_bps","orig_z","current_z","signal_atr","current_atr","atr_expansion","confirm_age_min",
                                 "h1","h4","crowd_exc_atr","quality","risk_mult","broker_clamped","manual_clamped","notional_clamped","margin_clamped","action","order_ticket");
         FileFlush(g_csv);
        }
     }
   if(InpWriteExecutionCsv)
     {
      g_execCsv=FileOpen("CrowdFade_execution_v200a_broker_vol_diag.csv",FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,';');
      if(g_execCsv==INVALID_HANDLE) PrintFormat("Execution CSV не відкрито, error=%d",GetLastError());
      else
        {
         bool empty=(FileSize(g_execCsv)==0);
         FileSeek(g_execCsv,0,SEEK_END);
         if(empty) FileWrite(g_execCsv,"utc","server","event","symbol","ticket","side","req_price","req_sl","actual_price","actual_sl","retcode","source_ms","note");
         FileFlush(g_execCsv);
        }
     }

   if(InpFastLaneEnabled && InpWriteExecutionCsv)
     {
      g_fastCsv=FileOpen("CrowdFade_fast_v200b_staged_demo.csv",FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,';');
      if(g_fastCsv==INVALID_HANDLE) PrintFormat("FAST CSV not opened, error=%d",GetLastError());
      else
        {
         bool empty=(FileSize(g_fastCsv)==0);
         FileSeek(g_fastCsv,0,SEEK_END);
         if(empty) FileWrite(g_fastCsv,"server","utc","event","symbol","source_ms","side","orig_z","current_z","signal_px","proxy_px","signal_atr","fav_atr","crowd_atr","response","h1","h4","risk_weight","lot","order","note");
         FileFlush(g_fastCsv);
        }
     }

   EventSetMillisecondTimer(InpExecTimerMs);
   PrintFormat("INIT_OK CrowdFadeMulti v2.00b DEMO_STAGED_FAST | symbols=%d | zLong=%.2f | zShort=%.2f | max exposure=%d | scheduler=%dms",
               g_symCount,InpZThresholdLong,InpZThresholdShort,InpMaxPositions,InpExecTimerMs);
   PrintFormat("  core: zwin=%dh | hold=%dh | SL=%.2f ATR | TP=%.2f ATR | signal-exit=%.2f",
               InpZWindowHours,InpHoldHours,InpStopATR,InpTakeProfitATR,InpExitZ);
   if(InpChaseOrder) PrintFormat("  CHASE ONCE: after %d M15 bars -> %.2f ATR",InpChaseAfterBars,InpChaseToATR);
   PrintFormat("  CONFIRM: %.2f ATR, max %d M15 bars, passive retrace %.2f ATR, TTL=%dmin",
               InpConfirmATR,InpConfirmMaxBars,InpConfirmLimitATR,InpOrderValidMin);
   PrintFormat("  PAUSE mode=%s | hours=%d | ATR=%.2f | max/day/symbol=%d",
               InpPauseMode,InpPauseHours,InpPauseATR,InpMaxTradesPerDay);
   PrintFormat("  EXIT: SL %.2f ATR | TP %.2f ATR | hold %dh | trail=%s",InpStopATR,InpTakeProfitATR,InpHoldHours,(InpTrailOn?"ON":"OFF"));
   PrintFormat("  QUALITY STATE: risk=%s | HIGH %.2fx | NORMAL %.2fx | LOW %.2fx | crowd continuation %.2f ATR | effective commission RT %.2f bps",
               (InpUseQualityRisk?"ENABLED":"FLAT/OFF"),InpHighRiskMult,InpNormalRiskMult,InpLowRiskMult,InpCrowdContinuationATR,EffectiveCommissionRoundTurnBps());
   if(InpFastLaneEnabled)
      PrintFormat("  FAST DEMO: %.2f<=|z|<%.2f | G1 ONE_ALIGN response[%.2f,%.2f) or >=%.2f | probe %.0f%% @%.2fATR + %.0f%% @%.2fATR | FAST risk %.2fx CORE | timeout=%dmin | magic=%I64d",
                  InpFastZMin,InpFastZMax,InpFastResponseMidMin,InpFastResponseMidMax,InpFastResponseStrongMin,
                  100.0*InpFastProbeFraction,InpFastProbeATR,100.0*(1.0-InpFastProbeFraction),InpFastConfirmATR,
                  InpFastRiskMult,InpFastConfirmTimeoutMin,InpFastMagic);
   PrintFormat("  RISK SHELL: notional<=%.1f%%eq | new-margin<=%.1f%%eq | total-margin<=%.1f%%eq | free-margin safety=%.1f%%",
               InpMaxNotionalPctEquity,InpMaxNewTradeMarginPct,InpMaxAccountMarginPct,InpMarginSafetyPct);
   Print("  v2.00a: frozen Z2.05 core; broker-neutral exposure caps + volatility/Z-state diagnostics only.");
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   for(int i = 0; i < g_symCount; i++)
     {
      if(g_sym[i].atrHandle != INVALID_HANDLE) IndicatorRelease(g_sym[i].atrHandle);
      if(g_sym[i].emaH1Handle != INVALID_HANDLE) IndicatorRelease(g_sym[i].emaH1Handle);
      if(g_sym[i].emaH4Handle != INVALID_HANDLE) IndicatorRelease(g_sym[i].emaH4Handle);
      PersistFastState(i);
     }
   if(g_csv != INVALID_HANDLE) { FileFlush(g_csv); FileClose(g_csv); }
   if(g_execCsv != INVALID_HANDLE) { FileFlush(g_execCsv); FileClose(g_execCsv); }
   if(g_fastCsv != INVALID_HANDLE) { FileFlush(g_fastCsv); FileClose(g_fastCsv); }
   Comment("");
   Print("=== КАСКАД ===");
   PrintFormat("  сигналів перевірено   %d", c_sig);
   PrintFormat("  |z| нижче порогу      %d", c_thr);
   PrintFormat("  пауза після угоди     %d", c_pause);
   PrintFormat("  ліміт позицій         %d", c_maxpos);
   PrintFormat("  ліміт на бік          %d", c_side);
   PrintFormat("  спред                 %d", c_spread);
   PrintFormat("  обсяг = 0             %d", c_lot);
   PrintFormat("  ВІДПРАВЛЕНО           %d  (відмов %d)", c_sent, c_fail);
   PrintFormat("  вихід за сигналом     %d", c_sigexit);
   PrintFormat("  вихід за часом        %d", c_timeexit);
   PrintFormat("  підтягнуто заявок     %d  (не вдалось %d)", c_chased, c_chasefail);
   PrintFormat("  часткових виходів     %d", c_partial);
   PrintFormat("  переставлень трейлінга %d", c_trail);
   PrintFormat("  беззбитків            %d", c_be);
   PrintFormat("  FAST arm/probe/confirm %d / %d / %d  abort=%d fail=%d",c_fast_arm,c_fast_probe,c_fast_confirm,c_fast_abort,c_fast_fail);
  }

//+------------------------------------------------------------------+
double JsonNum(const string src, const int from, const string key, int &endPos)
  {
   endPos = -1;
   int k = StringFind(src, "\"" + key + "\":", from);
   if(k < 0) return 0.0;
   int p = k + StringLen(key) + 3;
   if(StringGetCharacter(src, p) == 34) p++;
   int q = p, n = StringLen(src);
   while(q < n)
     {
      ushort ch = StringGetCharacter(src, q);
      bool isNum = (ch >= 48 && ch <= 57) || ch == 46 || ch == 45 || ch == 43 || ch == 101 || ch == 69;
      if(!isNum) break;
      q++;
     }
   endPos = q;
   return StringToDouble(StringSubstr(src, p, q - p));
  }

//+------------------------------------------------------------------+
//| v2.00 canonical Binance USD-M futures klines                     |
//+------------------------------------------------------------------+
bool FetchBinanceKlines(const string symbol,const string interval,const int limit,
                        long &openMs[],double &oo[],double &hh[],double &ll[],double &cc[],long &closeMs[],
                        string &err)
  {
   string url=API_HOST+KLINE_PATH+"?symbol="+symbol+"&interval="+interval+"&limit="+IntegerToString(limit);
   char post[],result[]; string rh="";
   ResetLastError();
   int code=WebRequest("GET",url,"",InpWebTimeoutMs,post,result,rh);
   if(code==-1)
     {
      int e=GetLastError(); err=StringFormat("kline WebRequest error=%d",e);
      if(e==4014) err+=" — add "+API_HOST+" to WebRequest allow-list";
      return false;
     }
   if(code!=200){err=StringFormat("kline HTTP %d",code);return false;}
   string body=CharArrayToString(result,0,WHOLE_ARRAY,CP_UTF8);
   if(StringLen(body)<10){err="empty kline response";return false;}

   ArrayResize(openMs,limit);ArrayResize(oo,limit);ArrayResize(hh,limit);ArrayResize(ll,limit);ArrayResize(cc,limit);ArrayResize(closeMs,limit);
   int cnt=0,pos=0;
   while(cnt<limit)
     {
      int rs=StringFind(body,"[",pos); if(rs<0) break;
      int re=StringFind(body,"]",rs+1); if(re<0) break;
      string row=StringSubstr(body,rs,re-rs+1);
      StringReplace(row,"[",""); StringReplace(row,"]",""); StringReplace(row,"\"","");
      string col[]; int n=StringSplit(row,(ushort)',',col);
      if(n>=7)
        {
         for(int j=0;j<n;j++){StringTrimLeft(col[j]);StringTrimRight(col[j]);}
         long ot=(long)StringToDouble(col[0]);
         double o=StringToDouble(col[1]),h=StringToDouble(col[2]),l=StringToDouble(col[3]),c=StringToDouble(col[4]);
         long ct=(long)StringToDouble(col[6]);
         if(ot>0 && ct>0 && o>0.0 && h>0.0 && l>0.0 && c>0.0)
           {
            openMs[cnt]=ot;oo[cnt]=o;hh[cnt]=h;ll[cnt]=l;cc[cnt]=c;closeMs[cnt]=ct;cnt++;
           }
        }
      pos=re+1;
     }
   ArrayResize(openMs,cnt);ArrayResize(oo,cnt);ArrayResize(hh,cnt);ArrayResize(ll,cnt);ArrayResize(cc,cnt);ArrayResize(closeMs,cnt);
   if(cnt<20){err=StringFormat("only %d klines",cnt);return false;}
   err="";return true;
  }

int LastCompletedKline(const long &closeMs[])
  {
   long nowMs=(long)TimeGMT()*1000;
   for(int i=ArraySize(closeMs)-1;i>=0;i--) if(closeMs[i]<=nowMs) return i;
   return -1;
  }

bool CanonicalM5(const string symbol,long &openMs,long &closeMs,double &o,double &h,double &l,double &c,string &err)
  {
   long ot[],ct[];double oo[],hh[],ll[],cc[];
   if(!FetchBinanceKlines(symbol,"5m",40,ot,oo,hh,ll,cc,ct,err)) return false;
   int last=LastCompletedKline(ct);
   if(last<1){err="not enough completed M5 bars";return false;}
   openMs=ot[last];closeMs=ct[last];o=oo[last];h=hh[last];l=ll[last];c=cc[last];
   return true;
  }

bool CanonicalM15(const string symbol,long &openMs,long &closeMs,double &o,double &h,double &l,double &c,double &atr,string &err)
  {
   long ot[],ct[];double oo[],hh[],ll[],cc[];
   if(!FetchBinanceKlines(symbol,"15m",40,ot,oo,hh,ll,cc,ct,err)) return false;
   int last=LastCompletedKline(ct);
   if(last<14){err="not enough completed M15 bars";return false;}
   double sum=0.0;
   for(int i=last-13;i<=last;i++)
     {
      double pc=cc[i-1];
      double tr=MathMax(hh[i]-ll[i],MathMax(MathAbs(hh[i]-pc),MathAbs(ll[i]-pc)));
      sum+=tr;
     }
   atr=sum/14.0;
   if(!MathIsValidNumber(atr) || atr<=0.0){err="canonical ATR invalid";return false;}
   openMs=ot[last];closeMs=ct[last];o=oo[last];h=hh[last];l=ll[last];c=cc[last];
   return true;
  }

bool CanonicalTrend(const string symbol,const string interval,int &state,string &err)
  {
   long ot[],ct[];double oo[],hh[],ll[],cc[];
   if(!FetchBinanceKlines(symbol,interval,220,ot,oo,hh,ll,cc,ct,err)) return false;
   int last=LastCompletedKline(ct);
   if(last<55){err="not enough completed trend bars";return false;}
   double alpha=2.0/51.0;
   double ema[];ArrayResize(ema,last+1);
   ema[0]=cc[0];
   for(int i=1;i<=last;i++) ema[i]=alpha*cc[i]+(1.0-alpha)*ema[i-1];
   int lag=last-4;
   state=0;
   if(cc[last]>ema[last] && ema[last]>ema[lag]) state=1;
   else if(cc[last]<ema[last] && ema[last]<ema[lag]) state=-1;
   return true;
  }

bool FetchCanonicalOne(const int idx)
  {
   if(!InpUseCanonicalBinancePrice){g_sym[idx].canonOk=true;return true;}
   string e=""; long om=0,cm=0,m5om=0,m5cm=0; double o=0,h=0,l=0,c=0,a=0,m5o=0,m5h=0,m5l=0,m5c=0; int h1=0,h4=0;
   if(!CanonicalM5(g_sym[idx].binance,m5om,m5cm,m5o,m5h,m5l,m5c,e))
     {g_sym[idx].canonOk=false;g_sym[idx].canonErr="M5 "+e;return false;}
   if(!CanonicalM15(g_sym[idx].binance,om,cm,o,h,l,c,a,e))
     {g_sym[idx].canonOk=false;g_sym[idx].canonErr=e;return false;}
   if(!CanonicalTrend(g_sym[idx].binance,"1h",h1,e))
     {g_sym[idx].canonOk=false;g_sym[idx].canonErr="H1 "+e;return false;}
   if(!CanonicalTrend(g_sym[idx].binance,"4h",h4,e))
     {g_sym[idx].canonOk=false;g_sym[idx].canonErr="H4 "+e;return false;}
   g_sym[idx].canonM15OpenMs=om;g_sym[idx].canonM15CloseMs=cm;
   g_sym[idx].canonM15Open=o;g_sym[idx].canonM15High=h;g_sym[idx].canonM15Low=l;g_sym[idx].canonM15Close=c;g_sym[idx].canonAtr14=a;
   g_sym[idx].canonM5OpenMs=m5om;g_sym[idx].canonM5CloseMs=m5cm;
   g_sym[idx].canonM5Open=m5o;g_sym[idx].canonM5High=m5h;g_sym[idx].canonM5Low=m5l;g_sym[idx].canonM5Close=m5c;
   g_sym[idx].canonH1State=h1;g_sym[idx].canonH4State=h4;
   g_sym[idx].canonLastFetch=TimeCurrent();g_sym[idx].canonOk=true;g_sym[idx].canonErr="";
   return true;
  }


//+------------------------------------------------------------------+
bool FetchOne(const int idx)
  {
   g_sym[idx].lastAttempt=TimeCurrent();
   string url=API_HOST+API_PATH+"?symbol="+g_sym[idx].binance
             +"&period="+BIN_PERIOD+"&limit="+IntegerToString(MAX_POINTS);
   char post[],result[];
   string rh="";
   ResetLastError();
   int code=WebRequest("GET",url,"",InpWebTimeoutMs,post,result,rh);

   if(code==-1)
     {
      int e=GetLastError();
      g_sym[idx].err=StringFormat("WebRequest error=%d",e);
      if(e==4014) g_sym[idx].err+=" — додайте "+API_HOST+" у WebRequest";
      return false;
     }
   if(code!=200)
     {
      g_sym[idx].err=StringFormat("HTTP %d",code);
      return false;
     }

   string body=CharArrayToString(result,0,WHOLE_ARRAY,CP_UTF8);
   if(StringLen(body)<20){g_sym[idx].err="порожня відповідь";return false;}

   double rr[]; ArrayResize(rr,MAX_POINTS);
   long tsms[]; ArrayResize(tsms,MAX_POINTS);
   int cnt=0,pos=0,e2=0;
   while(cnt<MAX_POINTS)
     {
      int k=StringFind(body,"\"longShortRatio\"",pos);
      if(k<0) break;
      double r=JsonNum(body,k,"longShortRatio",e2);
      if(e2<0) break;
      int et=-1;
      double td=JsonNum(body,k,"timestamp",et);
      if(r>0.0)
        {
         rr[cnt]=r;
         tsms[cnt]=(et>0)?(long)td:0;
         cnt++;
        }
      pos=e2;
     }
   if(cnt<20){g_sym[idx].err=StringFormat("лише %d точок",cnt);return false;}

   int win=(InpZWindowHours*3600)/BIN_STEP_S;
   if(win<10) win=10;
   int from=cnt-win; if(from<0) from=0;
   double sum=0.0,sum2=0.0; int n=0;
   for(int i=from;i<cnt;i++){sum+=rr[i];sum2+=rr[i]*rr[i];n++;}
   if(n<10){g_sym[idx].err="замало для смуги";return false;}
   double mean=sum/n;
   double var=sum2/n-mean*mean;
   if(var<=0.0){g_sym[idx].err="нульова дисперсія";return false;}
   double sd=MathSqrt(var);
   if(sd<1e-12){g_sym[idx].err="sd=0";return false;}

   int win40=(40*3600)/BIN_STEP_S; if(win40>cnt) win40=cnt;
   double s40=0.0,s40b=0.0; int n40=0;
   for(int i=cnt-win40;i<cnt;i++) if(i>=0){s40+=rr[i];s40b+=rr[i]*rr[i];n40++;}
   double z40=0.0;
   if(n40>=20)
     {
      double m40=s40/n40,v40=s40b/n40-m40*m40;
      if(v40>0.0){double sd40=MathSqrt(v40);if(sd40>1e-12) z40=(rr[cnt-1]-m40)/sd40;}
     }

   double zNew=(rr[cnt-1]-mean)/sd;
   bool wasActive=((g_sym[idx].z>=InpZThresholdShort) || (g_sym[idx].z<=-InpZThresholdLong)) && g_sym[idx].ok;
   bool nowActive=((zNew>=InpZThresholdShort) || (zNew<=-InpZThresholdLong));
   if(nowActive && !wasActive){g_sym[idx].sigSince=TimeCurrent();g_sym[idx].durBars=0;GVWrite(GVKey("SIG_"+g_sym[idx].broker),(double)g_sym[idx].sigSince);}
   if(!nowActive){g_sym[idx].sigSince=0;g_sym[idx].durBars=0;GVWrite(GVKey("SIG_"+g_sym[idx].broker),0.0);}
   if(nowActive && wasActive)
     {
      if(g_sym[idx].sigSince<=0) g_sym[idx].sigSince=TimeCurrent();
      long secs=(long)(TimeCurrent()-g_sym[idx].sigSince);
      int bb=(int)(secs/PeriodSeconds(PERIOD_M15));
      g_sym[idx].durBars=(bb>40)?40:((bb<0)?0:bb);
     }

   g_sym[idx].ratio=rr[cnt-1];
   g_sym[idx].mean=mean;
   g_sym[idx].sd=sd;
   g_sym[idx].z40=z40;
   g_sym[idx].z=zNew;
   g_sym[idx].ok=true;
   g_sym[idx].err="";
   g_sym[idx].lastFetch=TimeCurrent();
   g_sym[idx].sourceTimeMs=tsms[cnt-1];
   return true;
  }

bool IsFeedFresh(const int idx)
  {
   if(idx<0 || idx>=g_symCount || !g_sym[idx].ok) return false;
   if(g_sym[idx].lastFetch<=0 || TimeCurrent()-g_sym[idx].lastFetch>InpMaxFeedAgeSec) return false;
   if(g_sym[idx].sourceTimeMs>0)
     {
      long nowMs=(long)TimeGMT()*1000;
      long ageMs=nowMs-g_sym[idx].sourceTimeMs;
      if(ageMs<0) ageMs=0;
      if(ageMs>(long)InpMaxFeedAgeSec*1000) return false;
     }
   if(InpUseCanonicalBinancePrice)
     {
      if(!g_sym[idx].canonOk) return !InpCanonicalStrict;
      long nowMs=(long)TimeGMT()*1000;
      long ageMs=nowMs-g_sym[idx].canonM15CloseMs;
      if(ageMs<0) ageMs=0;
      if(ageMs>(long)InpCanonicalMaxAgeSec*1000) return !InpCanonicalStrict;
     }
   return true;
  }

//+------------------------------------------------------------------+
double AtrOf(const int idx)
  {
   double b[]; ArraySetAsSeries(b, true);
   if(CopyBuffer(g_sym[idx].atrHandle, 0, 1, 1, b) < 1) return 0.0;
   if(!MathIsValidNumber(b[0]) || b[0] <= 0.0) return 0.0;
   return b[0];
  }

//+------------------------------------------------------------------+
//| LAB022/025: trend state from COMPLETED H1/H4 bars only.          |
//+------------------------------------------------------------------+
int TrendState(const int idx,const ENUM_TIMEFRAMES tf,const int emaHandle)
  {
   if(emaHandle==INVALID_HANDLE) return 0;
   double eNow[],eOld[],cl[];
   ArraySetAsSeries(eNow,true); ArraySetAsSeries(eOld,true); ArraySetAsSeries(cl,true);
   if(CopyBuffer(emaHandle,0,1,1,eNow)<1) return 0;
   if(CopyBuffer(emaHandle,0,5,1,eOld)<1) return 0; // four completed TF bars earlier
   if(CopyClose(g_sym[idx].broker,tf,1,1,cl)<1) return 0;
   if(!MathIsValidNumber(eNow[0]) || !MathIsValidNumber(eOld[0]) || !MathIsValidNumber(cl[0])) return 0;
   if(cl[0]>eNow[0] && eNow[0]>eOld[0]) return 1;
   if(cl[0]<eNow[0] && eNow[0]<eOld[0]) return -1;
   return 0;
  }

string QualityName(const int q)
  {
   if(q>0) return "HIGH";
   if(q<0) return "LOW";
   return "NORMAL";
  }

int QualityState(const int side,const int h1,const int h4,const double crowdExcAtr)
  {
   bool aligned=(h1!=0 && h4!=0 && h1==h4);
   if(aligned && side==h1 && crowdExcAtr<=InpCrowdContinuationATR) return 1;
   if(aligned && crowdExcAtr>InpCrowdContinuationATR) return -1;
   return 0;
  }

double QualityRiskMultiplier(const int quality)
  {
   // LAB032 current candidate: flat risk. Quality is still computed/logged,
   // but InpUseQualityRisk=false by default makes every state 1.00x.
   if(!InpUseQualityRisk) return 1.0;
   if(quality>0) return InpHighRiskMult;
   if(quality<0) return InpLowRiskMult;
   return InpNormalRiskMult;
  }

//+------------------------------------------------------------------+
int CountExposure(int &nBuy,int &nSell)
  {
   nBuy=0;nSell=0;
   // CORE exposures are counted exactly as before.
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      long mg=PositionGetInteger(POSITION_MAGIC);
      if(mg!=InpMagic) continue;
      if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY) nBuy++; else nSell++;
     }
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i); if(!OrderSelect(tk)) continue;
      if(OrderGetInteger(ORDER_MAGIC)!=InpMagic) continue;
      long t=OrderGetInteger(ORDER_TYPE);
      if(t==ORDER_TYPE_BUY_LIMIT || t==ORDER_TYPE_BUY_STOP || t==ORDER_TYPE_BUY_STOP_LIMIT) nBuy++;
      else if(t==ORDER_TYPE_SELL_LIMIT || t==ORDER_TYPE_SELL_STOP || t==ORDER_TYPE_SELL_STOP_LIMIT) nSell++;
     }

   // FAST 20/80 tranches are one logical exposure per symbol+side.
   string seenBuy="|",seenSell="|";
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      if(!IsFastMagic(PositionGetInteger(POSITION_MAGIC))) continue;
      string sym=PositionGetString(POSITION_SYMBOL);
      string key="|"+sym+"|";
      if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)
        { if(StringFind(seenBuy,key)<0){nBuy++;seenBuy+=sym+"|";} }
      else
        { if(StringFind(seenSell,key)<0){nSell++;seenSell+=sym+"|";} }
     }
   return nBuy+nSell;
  }

bool HasAnyFor(const string sym)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)==InpMagic && PositionGetString(POSITION_SYMBOL)==sym) return true;
     }
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i); if(!OrderSelect(tk)) continue;
      if(OrderGetInteger(ORDER_MAGIC)==InpMagic && OrderGetString(ORDER_SYMBOL)==sym) return true;
     }
   return false;
  }

bool HasFastFor(const string sym)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      if(IsFastMagic(PositionGetInteger(POSITION_MAGIC)) && PositionGetString(POSITION_SYMBOL)==sym) return true;
     }
   return false;
  }

int FastPositionCountFor(const string sym)
  {
   int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      if(IsFastMagic(PositionGetInteger(POSITION_MAGIC)) && PositionGetString(POSITION_SYMBOL)==sym) n++;
     }
   return n;
  }

double EffectiveCommissionRoundTurnBps()
  {
   if(!InpAutoBrokerCostProfile) return MathMax(0.0,InpCommissionRoundTurnBps);
   string profile=AccountInfoString(ACCOUNT_COMPANY)+" "+AccountInfoString(ACCOUNT_SERVER);
   StringToUpper(profile);
   if(StringFind(profile,"FTMO")>=0) return 6.50;
   if(StringFind(profile,"GETLEVERAGED")>=0 || StringFind(profile,"GET LEVERAGED")>=0) return 0.0;
   if(StringFind(profile,"ICMARKETS")>=0 || StringFind(profile,"IC MARKETS")>=0 || StringFind(profile,"IC MARKET")>=0) return 0.0;
   return MathMax(0.0,InpCommissionRoundTurnBps);
  }

double NormVol(const string sym,double lot)
  {
   BrokerSpec sp; if(!GetBrokerSpec(sym,sp)) return 0.0;
   double maxAllowed=sp.volumeMax;
   if(InpMaxLot>0.0) maxAllowed=MathMin(maxAllowed,InpMaxLot);
   lot=MathMin(lot,maxAllowed);
   lot=MathFloor((lot+1e-12)/sp.volumeStep)*sp.volumeStep;
   if(lot<sp.volumeMin) return 0.0;
   int prec=0;double t=sp.volumeStep;
   while(t<1.0 && prec<8){t*=10.0;prec++;}
   return NormalizeDouble(lot,prec);
  }

// Raw risk lot BEFORE any broker/manual volume cap or step normalization.
// This preserves the true requested risk so under-sizing can be audited explicitly.
double LotForRisk(const string sym,const int side,const double entry,const double stop,const double weight)
  {
   if(entry<=0.0 || stop<=0.0 || MathAbs(entry-stop)<=0.0) return 0.0;
   double pnl=0.0;
   ENUM_ORDER_TYPE mt=(side>0)?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   ResetLastError();
   if(!OrderCalcProfit(mt,sym,1.0,entry,stop,pnl) || pnl==0.0)
     {
      double tv=SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_VALUE_LOSS);
      if(tv<=0.0) tv=SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_VALUE);
      double ts=SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_SIZE);
      if(tv<=0.0 || ts<=0.0) return 0.0;
      pnl=-(MathAbs(entry-stop)/ts)*tv;
     }
   double lossPerLot=MathAbs(pnl);
   if(lossPerLot<=0.0) return 0.0;

   // Approximate percentage commission in the maximum-loss budget.
   // v2.00a resolves broker profile automatically when enabled.
   double contract=SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE);
   double commissionPerLot=0.0;
   double costBps=EffectiveCommissionRoundTurnBps();
   if(costBps>0.0 && contract>0.0)
      commissionPerLot=entry*contract*(costBps/10000.0);

   double totalLossPerLot=lossPerLot+commissionPerLot;
   if(totalLossPerLot<=0.0) return 0.0;
   double risk=AccountInfoDouble(ACCOUNT_EQUITY)*(InpRiskPct/100.0)*MathMax(weight,0.0);
   return risk/totalLossPerLot;
  }

// Estimate economic notional of 1 lot in account currency.
// For the current linear crypto CFDs this is broker-neutral across different contract sizes.
double NotionalPerLotAccount(const string sym,const double entry)
  {
   if(entry<=0.0) return 0.0;
   double pnl=0.0;
   ResetLastError();
   // A +100% price move on one BUY lot gives the account-currency economic exposure for a linear CFD.
   if(OrderCalcProfit(ORDER_TYPE_BUY,sym,1.0,entry,entry*2.0,pnl) && MathAbs(pnl)>0.0)
      return MathAbs(pnl);
   double contract=SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract<=0.0) return 0.0;
   return entry*contract;
  }

// Broker-neutral economic exposure cap; independent of broker leverage/margin.
double ClampLotToNotional(const string sym,const double desiredLot,const double entry,
                          double &notionalPerLot,double &desiredNotional,double &actualNotional,bool &clamped)
  {
   notionalPerLot=0.0; desiredNotional=0.0; actualNotional=0.0; clamped=false;
   if(desiredLot<=0.0 || entry<=0.0) return 0.0;

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0.0) return 0.0;
   notionalPerLot=NotionalPerLotAccount(sym,entry);
   if(notionalPerLot<=0.0)
     {
      PrintFormat("NOTIONAL_CALC_BLOCK %s desiredLot=%.4f entry=%.8f contract=%.4f error=%d",
                  sym,desiredLot,entry,SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE),GetLastError());
      return 0.0;
     }

   desiredNotional=desiredLot*notionalPerLot;
   if(InpMaxNotionalPctEquity<=0.0)
     {
      actualNotional=desiredNotional;
      return desiredLot;
     }

   double capCash=equity*InpMaxNotionalPctEquity/100.0;
   if(capCash<=0.0) return 0.0;
   if(desiredNotional<=capCash)
     {
      actualNotional=desiredNotional;
      return desiredLot;
     }

   BrokerSpec sp;if(!GetBrokerSpec(sym,sp)) return 0.0;
   double capped=MathMin(desiredLot,capCash/notionalPerLot);
   capped=MathFloor((capped+1e-12)/sp.volumeStep)*sp.volumeStep;
   if(capped<sp.volumeMin)
     {
      PrintFormat("NOTIONAL_BLOCK %s desiredLot=%.4f desiredNotional=%.2f cap=%.2f minLot=%.4f",
                  sym,desiredLot,desiredNotional,capCash,sp.volumeMin);
      return 0.0;
     }
   int prec=0;double t=sp.volumeStep;
   while(t<1.0 && prec<8){t*=10.0;prec++;}
   capped=NormalizeDouble(capped,prec);
   actualNotional=capped*notionalPerLot;
   clamped=(capped+1e-12<desiredLot);
   if(clamped)
      PrintFormat("NOTIONAL_CLAMP %s desiredLot=%.4f actualLot=%.4f notional=%.2f->%.2f cap=%.2f (%.1f%%eq) contract=%.4f baseUnits=%.4f",
                  sym,desiredLot,capped,desiredNotional,actualNotional,capCash,InpMaxNotionalPctEquity,
                  SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE),capped*SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE));
   return capped;
  }

// Apply broker SYMBOL_VOLUME_MAX and optional manual ceiling AFTER raw risk sizing.
// Returns a broker-valid stepped volume and exposes why it was reduced.
double CapLotToBroker(const string sym,const double rawLot,bool &brokerClamped,bool &manualClamped)
  {
   brokerClamped=false; manualClamped=false;
   if(rawLot<=0.0) return 0.0;
   BrokerSpec sp; if(!GetBrokerSpec(sym,sp)) return 0.0;

   double capped=rawLot;
   if(capped>sp.volumeMax)
     {
      capped=sp.volumeMax;
      brokerClamped=true;
     }
   if(InpMaxLot>0.0 && capped>InpMaxLot)
     {
      capped=InpMaxLot;
      manualClamped=true;
     }

   capped=MathFloor((capped+1e-12)/sp.volumeStep)*sp.volumeStep;
   if(capped<sp.volumeMin) return 0.0;
   int prec=0; double t=sp.volumeStep;
   while(t<1.0 && prec<8){t*=10.0;prec++;}
   return NormalizeDouble(capped,prec);
  }

//+------------------------------------------------------------------+
//| Margin-adaptive lot: keep signal, reduce size instead of skipping |
//+------------------------------------------------------------------+
double ClampLotToMargin(const string sym,const ENUM_ORDER_TYPE mt,const double desiredLot,const double price,
                        double &needDesired,double &needActual,double &freeMargin,bool &clamped)
  {
   needDesired=0.0;needActual=0.0;freeMargin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);clamped=false;
   if(desiredLot<=0.0 || price<=0.0) return 0.0;

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double currentMargin=AccountInfoDouble(ACCOUNT_MARGIN);
   if(equity<=0.0 || freeMargin<=0.0) return 0.0;

   ResetLastError();
   if(!OrderCalcMargin(mt,sym,desiredLot,price,needDesired) || needDesired<=0.0)
     {
      // With hard margin caps enabled, unknown margin economics is unsafe: block instead of pass-through.
      if(InpMaxNewTradeMarginPct>0.0 || InpMaxAccountMarginPct>0.0)
        {
         PrintFormat("MARGIN_CALC_BLOCK %s desiredLot=%.4f error=%d",sym,desiredLot,GetLastError());
         return 0.0;
        }
      return desiredLot;
     }

   double freePct=MathMax(0.0,MathMin(100.0,InpMarginSafetyPct));
   double freeBudget=freeMargin*freePct/100.0;
   double tradeBudget=freeBudget;
   if(InpMaxNewTradeMarginPct>0.0) tradeBudget=equity*InpMaxNewTradeMarginPct/100.0;

   double totalHeadroom=freeBudget;
   if(InpMaxAccountMarginPct>0.0)
     {
      double totalCap=equity*InpMaxAccountMarginPct/100.0;
      totalHeadroom=MathMax(0.0,totalCap-currentMargin);
     }

   double budget=freeBudget;
   if(InpMaxNewTradeMarginPct>0.0) budget=MathMin(budget,tradeBudget);
   if(InpMaxAccountMarginPct>0.0)  budget=MathMin(budget,totalHeadroom);

   if(needDesired<=budget)
     {
      needActual=needDesired;
      return desiredLot;
     }
   if(!InpAdaptiveMarginLot || budget<=0.0)
     {
      PrintFormat("MARGIN_CAP_BLOCK %s desiredLot=%.4f need=%.2f budget=%.2f eq=%.2f margin=%.2f free=%.2f",
                  sym,desiredLot,needDesired,budget,equity,currentMargin,freeMargin);
      return 0.0;
     }

   if(InpVerbose)
      PrintFormat("MARGIN_CAP %s desiredLot=%.4f need=%.2f budget=%.2f freeBudget=%.2f tradeBudget=%.2f totalHeadroom=%.2f eq=%.2f currentMargin=%.2f",
                  sym,desiredLot,needDesired,budget,freeBudget,tradeBudget,totalHeadroom,equity,currentMargin);

   BrokerSpec sp;if(!GetBrokerSpec(sym,sp)) return 0.0;
   long minUnits=(long)MathCeil((sp.volumeMin-1e-12)/sp.volumeStep);
   long maxUnits=(long)MathFloor((desiredLot+1e-12)/sp.volumeStep);
   if(maxUnits<minUnits) return 0.0;
   long lo=minUnits,hi=maxUnits,best=0;
   double bestNeed=0.0;
   while(lo<=hi)
     {
      long mid=lo+(hi-lo)/2;
      double test=NormVol(sym,(double)mid*sp.volumeStep);
      if(test<=0.0){hi=mid-1;continue;}
      double nm=0.0;
      if(!OrderCalcMargin(mt,sym,test,price,nm) || nm<=0.0){hi=mid-1;continue;}
      if(nm<=budget){best=mid;bestNeed=nm;lo=mid+1;}
      else hi=mid-1;
     }
   if(best<=0) return 0.0;
   double actual=NormVol(sym,(double)best*sp.volumeStep);
   if(actual<=0.0) return 0.0;
   double minFrac=MathMax(0.0,MathMin(1.0,InpMinMarginLotFrac));
   if(minFrac>0.0 && actual+1e-12<desiredLot*minFrac)
     {
      PrintFormat("MARGIN_UNDERSIZE_SKIP %s desiredLot=%.4f actual=%.4f frac=%.3f minFrac=%.3f",
                  sym,desiredLot,actual,actual/desiredLot,minFrac);
      return 0.0;
     }
   needActual=bestNeed;
   clamped=(actual+1e-12<desiredLot);
   return actual;
  }

//+------------------------------------------------------------------+
void UpdateGuards()
  {
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq>g_eqPeak){g_eqPeak=eq;GVWrite(GVKey("EQPEAK"),g_eqPeak);}
   int dc=CurrentDayCode();
   if(dc!=g_dayCode)
     {
      g_dayCode=dc;g_dayStart=eq;g_haltDay=false;
      GVWrite(GVKey("DAYCODE"),(double)dc);
      GVWrite(GVKey("DAYEQ"),g_dayStart);
      GVWrite(GVKey("HALTDAY"),0.0);
     }
   if(g_dayStart>0.0)
     {
      double dd=(g_dayStart-eq)/g_dayStart*100.0;
      if(dd>=InpMaxDailyDDPct && !g_haltDay)
        {
         g_haltDay=true;GVWrite(GVKey("HALTDAY"),1.0);
         for(int ci=0;ci<g_symCount;ci++) g_sym[ci].confActive=false;
         PrintFormat("СТОП НА ДЕНЬ: %.2f%%",dd);
        }
     }
   if(g_eqPeak>0.0)
     {
      double dd=(g_eqPeak-eq)/g_eqPeak*100.0;
      if(dd>=InpMaxTotalDDPct && !g_haltAll)
        {
         g_haltAll=true;GVWrite(GVKey("HALTALL"),1.0);
         for(int ci=0;ci<g_symCount;ci++) g_sym[ci].confActive=false;
         PrintFormat("СТОП EA: загальна просадка %.2f%%",dd);
        }
     }
  }

ulong PositionIdSelected()
  { return (ulong)PositionGetInteger(POSITION_IDENTIFIER); }

double PositionBaseAtr(const ulong posId,const string sym,const double op,const double sl)
  {
   string k=GVPosKey(posId,"ATR");
   double a=GVRead(k,0.0);
   if(a>0.0) return a;
   if(sl>0.0 && InpStopATR>0.0) a=MathAbs(op-sl)/InpStopATR;
   if(a<=0.0)
     {
      int si=SymIndex(sym);
      if(si>=0) a=AtrOf(si);
     }
   if(a>0.0) GVWrite(k,a);
   return a;
  }

double PositionPeakPrice(const ulong posId,const long ptype,const double op,const double marketPx)
  {
   string k=GVPosKey(posId,"PEAK");
   double p=GVRead(k,0.0);
   if(p<=0.0) p=op;
   if(ptype==POSITION_TYPE_BUY)
     {
      if(marketPx>p) p=marketPx;
     }
   else
     {
      if(marketPx<p || p<=0.0) p=marketPx;
     }
   GVWrite(k,p);
   return p;
  }

bool VerifyOrderState(const ulong tk,const double reqPrice,const double reqSL,double &actualPrice,double &actualSL)
  {
   actualPrice=0.0;actualSL=0.0;
   if(!OrderSelect(tk)) return false;
   actualPrice=OrderGetDouble(ORDER_PRICE_OPEN);
   actualSL=OrderGetDouble(ORDER_SL);
   string sym=OrderGetString(ORDER_SYMBOL);
   double tick=SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_SIZE);if(tick<=0.0) tick=SymbolInfoDouble(sym,SYMBOL_POINT);
   return(MathAbs(actualPrice-reqPrice)<=tick*0.51 && MathAbs(actualSL-reqSL)<=tick*0.51);
  }

bool VerifyPositionSL(const ulong tk,const double reqSL,double &actualSL)
  {
   actualSL=0.0;
   if(!PositionSelectByTicket(tk)) return false;
   actualSL=PositionGetDouble(POSITION_SL);
   string sym=PositionGetString(POSITION_SYMBOL);
   double tick=SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_SIZE);if(tick<=0.0) tick=SymbolInfoDouble(sym,SYMBOL_POINT);
   return(MathAbs(actualSL-reqSL)<=tick*0.51);
  }

void CancelAllPending(const string why)
  {
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i);if(!OrderSelect(tk)) continue;
      if(OrderGetInteger(ORDER_MAGIC)!=InpMagic) continue;
      string sym=OrderGetString(ORDER_SYMBOL);
      bool b=g_trade.OrderDelete(tk);uint rc=g_trade.ResultRetcode();
      if(b && RetcodeAccepted(rc)) LogExec("ORDER_CANCEL",sym,tk,"",0,0,0,0,rc,why);
      else PrintFormat("ORDER_CANCEL %s #%I64u fail ret=%u %s",sym,tk,rc,g_trade.ResultRetcodeDescription());
     }
  }

void CloseAllPositions(const string why)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i);if(!PositionSelectByTicket(tk)) continue;
      if(!IsManagedMagic(PositionGetInteger(POSITION_MAGIC))) continue;
      string sym=PositionGetString(POSITION_SYMBOL);
      bool b=g_trade.PositionClose(tk);uint rc=g_trade.ResultRetcode();
      LogExec("FORCE_CLOSE",sym,tk,"",0,0,0,0,rc,why);
      if(!(b && RetcodeAccepted(rc))) PrintFormat("FORCE_CLOSE %s fail ret=%u %s",sym,rc,g_trade.ResultRetcodeDescription());
     }
  }

void ExpireFallbackPending()
  {
   if(InpOrderValidMin<=0) return;
   datetime now=TimeCurrent();
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i);if(!OrderSelect(tk)) continue;
      if(OrderGetInteger(ORDER_MAGIC)!=InpMagic) continue;
      long ot=OrderGetInteger(ORDER_TYPE);
      if(ot!=ORDER_TYPE_BUY_LIMIT && ot!=ORDER_TYPE_SELL_LIMIT) continue;
      datetime setup=(datetime)OrderGetInteger(ORDER_TIME_SETUP);
      if(setup<=0 || now-setup<(datetime)(InpOrderValidMin*60)) continue;
      bool b=g_trade.OrderDelete(tk);uint rc=g_trade.ResultRetcode();
      if(b && RetcodeAccepted(rc)) LogExec("ORDER_EXPIRE_MANUAL",OrderGetString(ORDER_SYMBOL),tk,"",0,0,0,0,rc,"TTL");
     }
  }

//+------------------------------------------------------------------+
//| [v1.30] Підтягування невиконаних лімітних заявок ближче до ринку. |
//| Заявка живе InpChaseAfterBars барів M15 -> переставляємо на       |
//| InpChaseToATR від поточної ціни. Стоп перераховується від нового  |
//| рівня, щоб ризик у ATR лишився тим самим.                         |
//+------------------------------------------------------------------+
void ChasePendingOrders()
  {
   if(!InpChaseOrder || InpChaseAfterBars<=0) return;
   long ageSec=(long)InpChaseAfterBars*PeriodSeconds(PERIOD_M15);

   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i);if(!OrderSelect(tk)) continue;
      if(OrderGetInteger(ORDER_MAGIC)!=InpMagic) continue;
      long ot=OrderGetInteger(ORDER_TYPE);
      if(ot!=ORDER_TYPE_BUY_LIMIT && ot!=ORDER_TYPE_SELL_LIMIT) continue;
      if(GVRead(GVOrderKey(tk,"CHASE_DONE"),0.0)>0.5) continue;

      datetime setup=(datetime)OrderGetInteger(ORDER_TIME_SETUP);
      if(TimeCurrent()-setup<(datetime)ageSec) continue;

      string sym=OrderGetString(ORDER_SYMBOL);
      string cm=OrderGetString(ORDER_COMMENT);
      if(StringFind(cm,"CF162")!=0) continue; // legacy v161 pending не переслідуємо повторно
      int si=SymIndex(sym);if(si<0) continue;
      int side=(ot==ORDER_TYPE_SELL_LIMIT)?-1:1;
      double old=OrderGetDouble(ORDER_PRICE_OPEN);

      // На ПЕРШОМУ due-tick фіксуємо chase target. Усі retries використовують той самий target.
      string kt=GVOrderKey(tk,"CHASE_PX"), ks=GVOrderKey(tk,"CHASE_SL"), ka=GVOrderKey(tk,"CHASE_ATR"), kr=GVOrderKey(tk,"CHASE_TRY");
      double price=GVRead(kt,0.0),stop=GVRead(ks,0.0),atr=GVRead(ka,0.0);
      if(price<=0.0 || stop<=0.0 || atr<=0.0)
        {
         atr=AtrOf(si);if(atr<=0.0) continue;
         MqlTick q;if(!SymbolInfoTick(sym,q) || q.bid<=0.0 || q.ask<=0.0) continue;
         double ref=(side<0)?q.bid:q.ask;
         price=(side<0)?ref+InpChaseToATR*atr:ref-InpChaseToATR*atr;
         stop =(side<0)?price+InpStopATR*atr:price-InpStopATR*atr;
         price=NormalizePriceTick(sym,price,(side<0)?+1:-1);
         stop =NormalizePriceTick(sym,stop,(side<0)?+1:-1);
         GVWrite(kt,price);GVWrite(ks,stop);GVWrite(ka,atr);GVWrite(kr,0.0);
        }

      // Один chase-event: якщо target не ближчий, завершити без подальшого переслідування.
      if((side<0 && price>=old) || (side>0 && price<=old))
        {
         GVWrite(GVOrderKey(tk,"CHASE_DONE"),1.0);
         LogExec("CHASE_SKIP",sym,tk,(side<0)?"SELL":"BUY",price,stop,old,OrderGetDouble(ORDER_SL),0,"target_not_closer");
         continue;
        }

      MqlTick q;if(!SymbolInfoTick(sym,q) || q.bid<=0.0 || q.ask<=0.0) continue;
      double md=MinTradeDistance(sym,true);
      bool valid=true;
      if(side<0 && price-q.ask<md) valid=false;
      if(side>0 && q.bid-price<md) valid=false;
      if(MathAbs(stop-price)<md) valid=false;
      if(!valid)
        {
         GVWrite(GVOrderKey(tk,"CHASE_DONE"),1.0);
         LogExec("CHASE_SKIP",sym,tk,(side<0)?"SELL":"BUY",price,stop,old,OrderGetDouble(ORDER_SL),0,"frozen_target_invalid_now");
         continue;
        }

      int tries=(int)GVRead(kr,0.0);
      if(tries>=InpChaseMaxRetries)
        {
         GVWrite(GVOrderKey(tk,"CHASE_DONE"),1.0);
         continue;
        }
      GVWrite(kr,(double)(tries+1));
      datetime exp=(datetime)OrderGetInteger(ORDER_TIME_EXPIRATION);
      ENUM_ORDER_TYPE_TIME ttime=(exp>0)?ORDER_TIME_SPECIFIED:ORDER_TIME_GTC;
      g_trade.SetTypeFillingBySymbol(sym);
      bool b=g_trade.OrderModify(tk,price,stop,0.0,ttime,exp);
      uint rc=g_trade.ResultRetcode();
      double ap=0.0,asl=0.0;
      bool verified=(b && RetcodeAccepted(rc) && VerifyOrderState(tk,price,stop,ap,asl));
      LogExec("CHASE",sym,tk,(side<0)?"SELL":"BUY",price,stop,ap,asl,rc,verified?"OK":"FAIL");
      if(verified)
        {
         GVWrite(GVOrderKey(tk,"CHASE_DONE"),1.0);
         GVWrite(GVOrderKey(tk,"ATR"),atr);
         c_chased++;
         int dg=(int)SymbolInfoInteger(sym,SYMBOL_DIGITS);
         PrintFormat("CHASE_ONCE %s #%I64u: %.*f -> %.*f stop=%.*f",sym,tk,dg,old,dg,price,dg,stop);
        }
      else
        {
         c_chasefail++;
         PrintFormat("CHASE %s #%I64u fail try=%d/%d ret=%u %s",sym,tk,tries+1,InpChaseMaxRetries,rc,g_trade.ResultRetcodeDescription());
        }
     }
  }

//+------------------------------------------------------------------+
//| [v1.20] Індекс символу за брокерською назвою. -1 якщо немає.      |
//+------------------------------------------------------------------+
int SymIndex(const string s)
  {
   for(int i = 0; i < g_symCount; i++)
      if(g_sym[i].broker == s) return i;
   return -1;
  }

//+------------------------------------------------------------------+
void ManagePositions()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i);if(!PositionSelectByTicket(tk)) continue;
      if(!IsManagedMagic(PositionGetInteger(POSITION_MAGIC))) continue;
      string s=PositionGetString(POSITION_SYMBOL);
      long ptype=PositionGetInteger(POSITION_TYPE);
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      ulong posId=PositionIdSelected();
      double op=PositionGetDouble(POSITION_PRICE_OPEN);
      double csl=PositionGetDouble(POSITION_SL);
      double tp=PositionGetDouble(POSITION_TP);
      MqlTick q;if(!SymbolInfoTick(s,q)) continue;
      double closePx=(ptype==POSITION_TYPE_BUY)?q.bid:q.ask;
      if(op<=0.0 || closePx<=0.0) continue;
      double baseAtr=PositionBaseAtr(posId,s,op,csl);

      // Live path audit sampled by the 1-second management scheduler.
      double auditRisk=GVRead(GVPosKey(posId,"RISK_DIST"),0.0);
      if(auditRisk<=0.0 && baseAtr>0.0) auditRisk=InpStopATR*baseAtr;
      if(auditRisk>0.0)
        {
         double moveR=(ptype==POSITION_TYPE_BUY)?(closePx-op)/auditRisk:(op-closePx)/auditRisk;
         double mfe=GVRead(GVPosKey(posId,"MFE_R"),0.0);
         double mae=GVRead(GVPosKey(posId,"MAE_R"),0.0);
         if(moveR>mfe) GVWrite(GVPosKey(posId,"MFE_R"),moveR);
         if(moveR<mae) GVWrite(GVPosKey(posId,"MAE_R"),moveR);
        }

      // [v1.70] БЕЗЗБИТОК: після руху InpBreakEvenAtATR перенести стоп у ПЛЮС.
      // Виміряно (BTC/SOL/ETH, 1.25/1.0/arm2.5): +1.0 -> +0.3 ATR дає
      //   WR 51.2% -> 61.1%, найдовша серія програшів 16 -> 11,
      //   R/DD 60.4 -> 53.3 (-12%). Це ОБМІН комфорту на прибуток.
      // УВАГА: перенесення рівно в НУЛЬ робить гірше (WR падає до 37-47%),
      // бо вихід у нуль не рахується виграшем. Lock має бути > 0.
      if(InpBreakEvenAtATR>0.0 && InpBreakEvenLock>0.0 && baseAtr>0.0)
        {
         double prof=(ptype==POSITION_TYPE_BUY)?(closePx-op):(op-closePx);
         if(prof>=InpBreakEvenAtATR*baseAtr)
           {
            double lvl=(ptype==POSITION_TYPE_BUY)?(op+InpBreakEvenLock*baseAtr)
                                                 :(op-InpBreakEvenLock*baseAtr);
            lvl=NormalizePriceTick(s,lvl,(ptype==POSITION_TYPE_BUY)?-1:+1);
            bool better=(ptype==POSITION_TYPE_BUY)?(csl<=0.0 || lvl>csl):(csl<=0.0 || lvl<csl);
            double tick=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE);
            if(tick<=0.0) tick=SymbolInfoDouble(s,SYMBOL_POINT);
            if(csl>0.0 && MathAbs(lvl-csl)<tick*0.51) better=false;
            double md=MinTradeDistance(s,true);
            bool dist=(ptype==POSITION_TYPE_BUY)?(q.bid-lvl>=md):(lvl-q.ask>=md);
            if(better && dist)
              {
               g_trade.SetTypeFillingBySymbol(s);
               bool b=g_trade.PositionModify(tk,lvl,tp);uint rc=g_trade.ResultRetcode();
               double actual=0.0;
               bool verified=(b && RetcodeAccepted(rc) && VerifyPositionSL(tk,lvl,actual));
               LogExec("BREAKEVEN",s,tk,(ptype==POSITION_TYPE_BUY)?"BUY":"SELL",0,lvl,0,actual,rc,verified?"OK":"FAIL");
               if(verified){c_be++;csl=actual;}
               else if(InpVerbose) PrintFormat("BREAKEVEN %s #%I64u fail ret=%u %s",s,tk,rc,g_trade.ResultRetcodeDescription());
              }
           }
        }

      // Optional R-based trailing overlay. Frozen production candidate keeps it OFF.
      // If manually enabled, it preserves the broker-side fixed TP.
      if(InpTrailOn && InpTrailDistanceR>0.0 && baseAtr>0.0)
        {
         double initialRisk=GVRead(GVPosKey(posId,"RISK_DIST"),0.0);
         if(initialRisk<=0.0)
           {
            initialRisk=InpStopATR*baseAtr;
            if(initialRisk>0.0) GVWrite(GVPosKey(posId,"RISK_DIST"),initialRisk);
           }

         if(initialRisk>0.0)
           {
            double peak=PositionPeakPrice(posId,ptype,op,closePx);
            double mfeR=(ptype==POSITION_TYPE_BUY)?(peak-op)/initialRisk:(op-peak)/initialRisk;
            if(mfeR>=InpTrailArmR)
              {
               double lvl=(ptype==POSITION_TYPE_BUY)?peak-InpTrailDistanceR*initialRisk
                                                        :peak+InpTrailDistanceR*initialRisk;
               lvl=NormalizePriceTick(s,lvl,(ptype==POSITION_TYPE_BUY)?-1:+1);
               bool better=(ptype==POSITION_TYPE_BUY)?(csl<=0.0 || lvl>csl):(csl<=0.0 || lvl<csl);
               double tick=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE);
               if(tick<=0.0) tick=SymbolInfoDouble(s,SYMBOL_POINT);
               if(csl>0.0 && MathAbs(lvl-csl)<tick*0.51) better=false;
               double md=MinTradeDistance(s,true);
               bool dist=(ptype==POSITION_TYPE_BUY)?(q.bid-lvl>=md):(lvl-q.ask>=md);
               if(better && dist)
                 {
                  g_trade.SetTypeFillingBySymbol(s);
                  bool b=g_trade.PositionModify(tk,lvl,tp);uint rc=g_trade.ResultRetcode();
                  double actual=0.0;bool verified=(b && RetcodeAccepted(rc) && VerifyPositionSL(tk,lvl,actual));
                  string note=StringFormat("mfe=%.3fR peak=%.8f trail=%.2fR riskDist=%.8f",
                                           mfeR,peak,InpTrailDistanceR,initialRisk);
                  LogExec("TRAIL_R",s,tk,(ptype==POSITION_TYPE_BUY)?"BUY":"SELL",0,lvl,0,actual,rc,verified?("OK "+note):("FAIL "+note));
                  if(verified){c_trail++;csl=actual;}
                  else if(InpVerbose) PrintFormat("TRAIL_R %s #%I64u fail ret=%u %s",s,tk,rc,g_trade.ResultRetcodeDescription());
                 }
              }
           }
        }

      // Partial exit: one-shot flag is persistent; no repeated partial closes.
      if(InpPartialClose && InpPartialFrac>0.05 && InpPartialFrac<0.95 && baseAtr>0.0)
        {
         string kp=GVPosKey(posId,"PARTIAL");
         if(GVRead(kp,0.0)<0.5)
           {
            double prof=(ptype==POSITION_TYPE_BUY)?closePx-op:op-closePx;
            if(prof>=InpPartialAtATR*baseAtr)
              {
               double vol=PositionGetDouble(POSITION_VOLUME);
               double part=NormVol(s,vol*InpPartialFrac);
               double vmin=SymbolInfoDouble(s,SYMBOL_VOLUME_MIN);
               if(part>=vmin && (vol-part)>=vmin)
                 {
                  bool b=g_trade.PositionClosePartial(tk,part);uint rc=g_trade.ResultRetcode();
                  LogExec("PARTIAL",s,tk,(ptype==POSITION_TYPE_BUY)?"BUY":"SELL",0,0,0,0,rc,b?"sent":"fail");
                  if(b && RetcodeAccepted(rc)){GVWrite(kp,1.0);c_partial++;}
                 }
              }
           }
        }

      bool closed=false;
      if(InpExitZ>0.0)
        {
         int si=SymIndex(s);
         if(si>=0 && IsFeedFresh(si))
           {
            double z=g_sym[si].z;
            bool against=(ptype==POSITION_TYPE_SELL)?(z<=-InpExitZ):(z>=InpExitZ);
            if(against)
              {
               GVWrite(GVPosKey(posId,"EXIT_CODE"),1.0); // SIGNAL
               bool b=g_trade.PositionClose(tk);uint rc=g_trade.ResultRetcode();
               LogExec("SIGNAL_EXIT",s,tk,(ptype==POSITION_TYPE_BUY)?"BUY":"SELL",0,0,0,0,rc,StringFormat("z=%+.3f",z));
               if(b && RetcodeAccepted(rc)){c_sigexit++;PrintFormat("SIGNAL_EXIT %s: z=%+.2f",s,z);closed=true;}
               else PrintFormat("SIGNAL_EXIT %s fail ret=%u %s",s,rc,g_trade.ResultRetcodeDescription());
              }
           }
        }
      if(closed) continue;

      if(TimeCurrent()-opened>=(datetime)(InpHoldHours*3600))
        {
         GVWrite(GVPosKey(posId,"EXIT_CODE"),2.0); // TIME
         bool b=g_trade.PositionClose(tk);uint rc=g_trade.ResultRetcode();
         LogExec("TIME_EXIT",s,tk,(ptype==POSITION_TYPE_BUY)?"BUY":"SELL",0,0,0,0,rc,"hold");
         if(b && RetcodeAccepted(rc)){c_timeexit++;PrintFormat("TIME_EXIT %s after %dh",s,InpHoldHours);}
         else PrintFormat("TIME_EXIT %s fail ret=%u %s",s,rc,g_trade.ResultRetcodeDescription());
        }
     }
  }

//+------------------------------------------------------------------+
//| [v1.40] Множник лота за багатофакторною моделлю.                  |
//| Повертає 1.0, якщо модель вимкнена або даних бракує.              |
//+------------------------------------------------------------------+
double ScoreWeight(const int idx, const int side, const double atr, const double px)
  {
   if(!InpUseScore || InpScoreGain <= 0.0) return(1.0);

   string sym = g_sym[idx].broker;
   double z   = g_sym[idx].z;
   double z40 = g_sym[idx].z40;

   // --- ознаки ---
   double f_absz   = MathAbs(z);
   double f_z40    = ((z40 > 0.0) == (z > 0.0)) ? 1.0 : 0.0;
   double f_absz40 = MathAbs(z40);
   double f_dur    = (double)g_sym[idx].durBars;

   // обсяг: z-оцінка за 96 барів M15
   long vb[];
   ArraySetAsSeries(vb, true);
   double f_volz = 0.0;
   if(CopyTickVolume(sym, PERIOD_M15, 1, 96, vb) == 96)
     {
      double s = 0.0, s2 = 0.0;
      for(int i = 0; i < 96; i++) { double v = (double)vb[i]; s += v; s2 += v * v; }
      double m = s / 96.0;
      double vr = (s2 / 96.0) - m * m;
      if(vr > 0.0)
        {
         double sdv = MathSqrt(vr);
         if(sdv > 1e-12) f_volz = ((double)vb[0] - m) / sdv;
        }
     }

   // відстань до структури: до мінімуму (для шорту) чи максимуму (для лонгу), 24 бари
   double f_dstr = 2.0;
   double hb[], lb[];
   ArraySetAsSeries(hb, true); ArraySetAsSeries(lb, true);
   if(CopyHigh(sym, PERIOD_M15, 1, 24, hb) == 24 && CopyLow(sym, PERIOD_M15, 1, 24, lb) == 24)
     {
      int ih = ArrayMaximum(hb, 0, 24);
      int il = ArrayMinimum(lb, 0, 24);
      double ref = (side < 0) ? (px - lb[il]) : (hb[ih] - px);
      if(atr > 0.0 && MathIsValidNumber(ref)) f_dstr = ref / atr;
     }

   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   double f_hract = (dt.hour >= 8 && dt.hour < 17) ? 1.0 : 0.0;

   // --- лінійна модель на стандартизованих ознаках ---
   double sc = SC_CONST
             + SC_B_ABSZ   * ((f_absz   - SC_M_ABSZ)   / SC_S_ABSZ)
             + SC_B_Z40    * ((f_z40    - SC_M_Z40)    / SC_S_Z40)
             + SC_B_ABSZ40 * ((f_absz40 - SC_M_ABSZ40) / SC_S_ABSZ40)
             + SC_B_DUR    * ((f_dur    - SC_M_DUR)    / SC_S_DUR)
             + SC_B_VOLZ   * ((f_volz   - SC_M_VOLZ)   / SC_S_VOLZ)
             + SC_B_DSTR   * ((f_dstr   - SC_M_DSTR)   / SC_S_DSTR)
             + SC_B_HRACT  * ((f_hract  - SC_M_HRACT)  / SC_S_HRACT);

   if(!MathIsValidNumber(sc)) return(1.0);

   // sc близько 0.50 у середньому, розкид приблизно 0.11
   double w = 1.0 + InpScoreGain * ((sc - SC_CONST) / SC_SD);
   if(w < InpScoreMinW) w = InpScoreMinW;
   if(w > InpScoreMaxW) w = InpScoreMaxW;
   return(w);
  }

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| [v1.91] День у форматі YYYYMMDD (серверний час)                  |
//+------------------------------------------------------------------+
int DayCodeNow()
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(),dt);
   return dt.year*10000+dt.mon*100+dt.day;
  }

//+------------------------------------------------------------------+
//| [v1.91] Чи дозволена нова угода: пауза + ліміт/день               |
//+------------------------------------------------------------------+
bool CanEnterByPauseAndDay(const int idx, const double priceNow)
  {
   // --- daily limit per symbol ---
   int dc=DayCodeNow();
   if(g_sym[idx].dayTradeCode!=dc)
     {
      g_sym[idx].dayTradeCode=dc;
      g_sym[idx].dayTradeCount=0;
     }
   if(InpMaxTradesPerDay>0 && g_sym[idx].dayTradeCount>=InpMaxTradesPerDay)
     {
      c_pause++;
      return false;
     }

   // --- adaptive pause ---
   if(g_sym[idx].lastTrade<=0)
      return true;

   string mode=InpPauseMode;
   StringToUpper(mode);
   StringReplace(mode," ","");
   StringReplace(mode,"_","");
   StringReplace(mode,"+","");

   bool needHours=(mode=="HOURS" || mode=="HOURSATR" || mode=="ATRHOURS");
   bool needAtr  =(mode=="ATR" || mode=="HOURSATR" || mode=="ATRHOURS");
   // default / unknown → Hours behavior
   if(mode!="HOURS" && mode!="ATR" && mode!="HOURSATR" && mode!="ATRHOURS")
     { needHours=true; needAtr=false; }

   bool hoursOk=true;
   bool atrOk=true;

   if(needHours)
     {
      long elapsed=TimeCurrent()-g_sym[idx].lastTrade;
      hoursOk=(elapsed >= (long)InpPauseHours*3600);
     }
   if(needAtr)
     {
      if(g_sym[idx].lastEntryAtr<=0.0 || g_sym[idx].lastEntryPrice<=0.0)
         atrOk=true; // немає референсу — не блокуємо
      else
        {
         double moved=MathAbs(priceNow-g_sym[idx].lastEntryPrice)/g_sym[idx].lastEntryAtr;
         atrOk=(moved >= InpPauseATR);
        }
     }

   // Hours      → тільки години
   // ATR        → тільки ATR-рух
   // Hours+ATR  → обидва умови (AND)
   bool ok=true;
   if(needHours && needAtr) ok=(hoursOk && atrOk);
   else if(needHours)       ok=hoursOk;
   else if(needAtr)         ok=atrOk;

   if(!ok){ c_pause++; return false; }
   return true;
  }

//+------------------------------------------------------------------+
//| [v1.91] Зафіксувати вхід для паузи/ліміту                        |
//+------------------------------------------------------------------+
void RegisterEntry(const int idx, const double entryPrice, const double atr)
  {
   g_sym[idx].lastTrade=TimeCurrent();
   GVWrite(GVLastTradeKey(g_sym[idx].broker),(double)g_sym[idx].lastTrade);
   g_sym[idx].lastEntryPrice=entryPrice;
   g_sym[idx].lastEntryAtr=(atr>0.0)?atr:g_sym[idx].lastEntryAtr;

   int dc=DayCodeNow();
   if(g_sym[idx].dayTradeCode!=dc)
     {
      g_sym[idx].dayTradeCode=dc;
      g_sym[idx].dayTradeCount=0;
     }
   g_sym[idx].dayTradeCount++;
  }

bool CanEnterFastByPauseAndDay(const int idx,const double priceNow)
  {
   int dc=DayCodeNow();
   if(g_sym[idx].fastDayTradeCode!=dc)
     {
      g_sym[idx].fastDayTradeCode=dc;
      g_sym[idx].fastDayTradeCount=0;
     }
   if(InpFastMaxTradesPerDay>0 && g_sym[idx].fastDayTradeCount>=InpFastMaxTradesPerDay) return false;
   if(g_sym[idx].fastLastTrade<=0) return true;
   if(g_sym[idx].fastLastEntryAtr<=0.0 || g_sym[idx].fastLastEntryPrice<=0.0) return true;
   double moved=MathAbs(priceNow-g_sym[idx].fastLastEntryPrice)/g_sym[idx].fastLastEntryAtr;
   return(moved>=InpFastPauseATR);
  }

void RegisterFastEntry(const int idx,const double entryPrice,const double atr)
  {
   g_sym[idx].fastLastTrade=TimeCurrent();
   g_sym[idx].fastLastEntryPrice=entryPrice;
   g_sym[idx].fastLastEntryAtr=atr;
   int dc=DayCodeNow();
   if(g_sym[idx].fastDayTradeCode!=dc)
     {g_sym[idx].fastDayTradeCode=dc;g_sym[idx].fastDayTradeCount=0;}
   g_sym[idx].fastDayTradeCount++;
   PersistFastState(idx);
  }

void LogFast(const string event,const int idx,const double proxyPx,const double response,
             const double riskWeight,const double lot,const ulong order,const string note="")
  {
   if(g_fastCsv==INVALID_HANDLE || idx<0 || idx>=g_symCount) return;
   FileWrite(g_fastCsv,
             TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),TimeToString(TimeGMT(),TIME_DATE|TIME_SECONDS),
             event,g_sym[idx].broker,IntegerToString(g_sym[idx].fastSourceTimeMs),
             (g_sym[idx].fastSide>0)?"BUY":"SELL",
             DoubleToString(g_sym[idx].fastOrigZ,4),DoubleToString(g_sym[idx].z,4),
             DoubleToString(g_sym[idx].fastSignalPrice,8),DoubleToString(proxyPx,8),DoubleToString(g_sym[idx].fastSignalAtr,8),
             DoubleToString(g_sym[idx].fastMaxThesisATR,4),DoubleToString(g_sym[idx].fastMaxCrowdATR,4),DoubleToString(response,4),
             IntegerToString(g_sym[idx].fastH1State),IntegerToString(g_sym[idx].fastH4State),
             DoubleToString(riskWeight,4),DoubleToString(lot,4),IntegerToString((long)order),note);
   FileFlush(g_fastCsv);
  }

bool FastG1Valid(const int idx,const double response)
  {
   int side=g_sym[idx].fastSide;
   bool a1=(g_sym[idx].fastH1State==side);
   bool a4=(g_sym[idx].fastH4State==side);
   bool oneAlign=(a1!=a4);
   if(!oneAlign) return false;
   bool mid=(response>=InpFastResponseMidMin && response<InpFastResponseMidMax);
   bool strong=(response>=InpFastResponseStrongMin);
   return(mid || strong);
  }

bool FastCanonicalFresh(const int idx)
  {
   if(!InpUseCanonicalBinancePrice || !g_sym[idx].canonOk || g_sym[idx].canonM5CloseMs<=0) return false;
   long nowMs=(long)TimeGMT()*1000;
   long age=nowMs-g_sym[idx].canonM5CloseMs;
   return(age>=0 && age<=(long)InpFastSignalMaxAgeSec*1000);
  }

void CloseFastPositionsForSymbol(const int idx,const string why)
  {
   string sym=g_sym[idx].broker;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i);if(!PositionSelectByTicket(tk)) continue;
      if(!IsFastMagic(PositionGetInteger(POSITION_MAGIC)) || PositionGetString(POSITION_SYMBOL)!=sym) continue;
      bool b=g_fastTrade.PositionClose(tk);uint rc=g_fastTrade.ResultRetcode();
      LogExec("FAST_ABORT_CLOSE",sym,tk,"",0,0,0,0,rc,why);
      if(!(b && RetcodeAccepted(rc))) PrintFormat("FAST_ABORT_CLOSE %s #%I64u fail ret=%u %s",sym,tk,rc,g_fastTrade.ResultRetcodeDescription());
     }
  }

bool PlaceFastMarketTranche(const int idx,const double riskWeight,const bool isConfirm,const double response)
  {
   string sym=g_sym[idx].broker;
   int side=g_sym[idx].fastSide;
   double atr=g_sym[idx].fastSignalAtr;
   if(side==0 || atr<=0.0 || riskWeight<=0.0) return false;

   MqlTick q;if(!SymbolInfoTick(sym,q) || q.bid<=0.0 || q.ask<=0.0) return false;
   double entry=(side>0)?q.ask:q.bid;
   double stop=(side>0)?entry-InpStopATR*atr:entry+InpStopATR*atr;
   double tp=(side>0)?entry+InpTakeProfitATR*atr:entry-InpTakeProfitATR*atr;
   stop=NormalizePriceTick(sym,stop,(side>0)?-1:+1);
   tp=NormalizePriceTick(sym,tp,(side>0)?+1:-1);
   double md=MinTradeDistance(sym,false);
   if(MathAbs(stop-entry)<md || MathAbs(tp-entry)<md)
     {LogFast("FAST_DISTANCE_BLOCK",idx,g_sym[idx].fastSignalPrice,response,riskWeight,0,0,"stop/tp distance");return false;}

   // Probe creates a new logical exposure. Confirm add belongs to the existing FAST event.
   if(!isConfirm)
     {
      int nb=0,ns=0;int tot=CountExposure(nb,ns);
      if(tot>=InpMaxPositions || (side>0 && nb>=InpMaxPerSide) || (side<0 && ns>=InpMaxPerSide))
        {LogFast("FAST_EXPOSURE_BLOCK",idx,g_sym[idx].fastSignalPrice,response,riskWeight,0,0,"portfolio cap");return false;}
     }

   double rawLot=LotForRisk(sym,side,entry,stop,riskWeight);
   if(rawLot<=0.0){LogFast("FAST_LOT_BLOCK",idx,g_sym[idx].fastSignalPrice,response,riskWeight,0,0,"raw lot <=0");return false;}
   bool brokerClamped=false,manualClamped=false;
   double brokerLot=CapLotToBroker(sym,rawLot,brokerClamped,manualClamped);
   if(brokerLot<=0.0)
     {LogFast("FAST_MINLOT_SKIP",idx,g_sym[idx].fastSignalPrice,response,riskWeight,0,0,StringFormat("raw=%.4f min=%.4f",rawLot,SymbolInfoDouble(sym,SYMBOL_VOLUME_MIN)));return false;}
   double minFrac=MathMax(0.0,MathMin(1.0,InpMinVolumeLotFrac));
   if(minFrac>0.0 && brokerLot+1e-12<rawLot*minFrac)
     {LogFast("FAST_VOLUME_UNDERSIZE",idx,g_sym[idx].fastSignalPrice,response,riskWeight,brokerLot,0,"below min fraction");return false;}

   double npl=0,dn=0,an=0;bool nc=false;
   double nl=ClampLotToNotional(sym,brokerLot,entry,npl,dn,an,nc);
   if(nl<=0.0){LogFast("FAST_NOTIONAL_BLOCK",idx,g_sym[idx].fastSignalPrice,response,riskWeight,0,0,"notional");return false;}
   ENUM_ORDER_TYPE mt=(side>0)?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   double needD=0,needA=0,freeM=0;bool mc=false;
   double lot=ClampLotToMargin(sym,mt,nl,entry,needD,needA,freeM,mc);
   if(lot<=0.0){LogFast("FAST_MARGIN_BLOCK",idx,g_sym[idx].fastSignalPrice,response,riskWeight,0,0,"margin");return false;}

   string stage=isConfirm?"CF2FCF":"CF2FPR";
   string comment=StringFormat("%s%I64d",stage,g_sym[idx].fastSourceTimeMs/1000);
   g_fastTrade.SetTypeFillingBySymbol(sym);
   bool basic=(side>0)?g_fastTrade.Buy(lot,sym,0.0,stop,tp,comment):g_fastTrade.Sell(lot,sym,0.0,stop,tp,comment);
   uint rc=g_fastTrade.ResultRetcode();
   ulong ord=g_fastTrade.ResultOrder();
   ulong deal=g_fastTrade.ResultDeal();
   bool ok=basic && RetcodeAccepted(rc) && (ord>0 || deal>0);
   ulong ref=(ord>0)?ord:deal;
   if(!ok)
     {
      c_fast_fail++;
      LogFast(isConfirm?"FAST_CONFIRM_FAIL":"FAST_PROBE_FAIL",idx,g_sym[idx].fastSignalPrice,response,riskWeight,lot,ref,g_fastTrade.ResultRetcodeDescription());
      LogExec("FAST_ORDER_FAIL",sym,ref,(side>0)?"BUY":"SELL",entry,stop,0,0,rc,isConfirm?"CONFIRM":"PROBE");
      return false;
     }

   if(ord>0)
     {
      GVWrite(GVOrderKey(ord,"ATR"),atr);
      GVWrite(GVOrderKey(ord,"QUALITY"),0.0);
      GVWrite(GVOrderKey(ord,"RISK_MULT"),riskWeight);
      GVWrite(GVOrderKey(ord,"CROWD_EXC"),g_sym[idx].fastMaxCrowdATR);
      GVWrite(GVOrderKey(ord,"FAST_STAGE"),isConfirm?2.0:1.0);
      GVWrite(GVOrderKey(ord,"ORIG_Z"),g_sym[idx].fastOrigZ);
     }
   double actual=g_fastTrade.ResultPrice();if(actual<=0.0) actual=entry;
   LogFast(isConfirm?"FAST_CONFIRM_ADD":"FAST_PROBE_OPEN",idx,g_sym[idx].fastSignalPrice,response,riskWeight,lot,ref,
           StringFormat("actual=%.8f stop=%.8f tp=%.8f rawLot=%.4f",actual,stop,tp,rawLot));
   LogExec(isConfirm?"FAST_CONFIRM_ADD":"FAST_PROBE_OPEN",sym,ref,(side>0)?"BUY":"SELL",entry,stop,actual,stop,rc,
           StringFormat("riskWeight=%.4f response=%.3f",riskWeight,response));

   if(!isConfirm)
     {
      RegisterFastEntry(idx,actual,atr);
      g_sym[idx].fastProbeOpen=true;
      g_sym[idx].fastProbeTime=TimeCurrent();
      g_sym[idx].fastProbeEntry=actual;
      c_fast_probe++;
      PersistFastState(idx);
     }
   else c_fast_confirm++;
   return true;
  }

void TryFastLane(const int idx)
  {
   if(!InpFastLaneEnabled || idx<0 || idx>=g_symCount || g_haltDay || g_haltAll) return;
   if(!g_sym[idx].ok || !IsFeedFresh(idx)) return;
   string sym=g_sym[idx].broker;

   // If a confirmed FAST event still has positions open, it owns the lane until flat.
   if(!g_sym[idx].fastActive && HasFastFor(sym)) return;

   // Active event management uses live broker mid mapped back to canonical signal space by frozen basis.
   if(g_sym[idx].fastActive)
     {
      double atr=g_sym[idx].fastSignalAtr;
      if(atr<=0.0 || g_sym[idx].fastSignalTime<=0){ResetFastEvent(idx);return;}
      MqlTick q;if(!SymbolInfoTick(sym,q) || q.bid<=0.0 || q.ask<=0.0) return;
      double mid=0.5*(q.bid+q.ask);
      double proxy=mid-g_sym[idx].fastBasis;
      int side=g_sym[idx].fastSide;
      double fav=(side>0)?(proxy-g_sym[idx].fastSignalPrice)/atr:(g_sym[idx].fastSignalPrice-proxy)/atr;
      double crowd=(side>0)?(g_sym[idx].fastSignalPrice-proxy)/atr:(proxy-g_sym[idx].fastSignalPrice)/atr;
      if(fav>g_sym[idx].fastMaxThesisATR) g_sym[idx].fastMaxThesisATR=fav;
      if(crowd>g_sym[idx].fastMaxCrowdATR) g_sym[idx].fastMaxCrowdATR=crowd;
      double response=g_sym[idx].fastMaxThesisATR/(g_sym[idx].fastMaxCrowdATR+1e-9);

      bool timeout=(TimeCurrent()-g_sym[idx].fastSignalTime >= (datetime)(InpFastConfirmTimeoutMin*60));
      bool flip=(g_sym[idx].fastOrigZ*g_sym[idx].z<0.0);
      if(timeout || flip)
        {
         if(g_sym[idx].fastProbeOpen && HasFastFor(sym)) CloseFastPositionsForSymbol(idx,flip?"sign_flip":"timeout");
         LogFast(flip?"FAST_ABORT_SIGN_FLIP":"FAST_ABORT_TIMEOUT",idx,proxy,response,0,0,0,"");
         c_fast_abort++;ResetFastEvent(idx);return;
        }

      if(g_sym[idx].fastProbeOpen && !HasFastFor(sym))
        {
         LogFast("FAST_PROBE_GONE",idx,proxy,response,0,0,0,"SL/TP/manual before 0.30 confirm");
         c_fast_abort++;ResetFastEvent(idx);return;
        }

      if(!g_sym[idx].fastProbeOpen)
        {
         if(fav>=InpFastProbeATR && FastG1Valid(idx,response))
           {
            double w=InpFastRiskMult*InpFastProbeFraction;
            if(!PlaceFastMarketTranche(idx,w,false,response))
              {
               // A risk/min-lot/execution block invalidates this event for the current M5 signal.
               c_fast_fail++;ResetFastEvent(idx);
              }
           }
         PersistFastState(idx);
         return;
        }

      if(fav>=InpFastConfirmATR && FastG1Valid(idx,response))
        {
         double w=InpFastRiskMult*(1.0-InpFastProbeFraction);
         bool added=PlaceFastMarketTranche(idx,w,true,response);
         LogFast(added?"FAST_EVENT_CONFIRMED":"FAST_CONFIRM_ADD_BLOCKED",idx,proxy,response,w,0,0,"");
         // Either way, selection is complete. If add is blocked, keep the 20% probe under broker SL/TP/H24.
         ResetFastEvent(idx);
        }
      else PersistFastState(idx);
      return;
     }

   // Arm only on a new completed Binance M5 bar and only in the lower-Z FAST zone.
   if(!FastCanonicalFresh(idx)) return;
   if(g_sym[idx].canonM5CloseMs<=g_sym[idx].fastLastArmM5Ms) return;
   double az=MathAbs(g_sym[idx].z);
   if(az<InpFastZMin || az>=InpFastZMax) return;
   int side=(g_sym[idx].z>0.0)?-1:1;
   bool a1=(g_sym[idx].canonH1State==side);
   bool a4=(g_sym[idx].canonH4State==side);
   if(a1==a4) // G1 requires exactly ONE aligned timeframe.
     {g_sym[idx].fastLastArmM5Ms=g_sym[idx].canonM5CloseMs;PersistFastState(idx);return;}

   MqlTick q;if(!SymbolInfoTick(sym,q) || q.bid<=0.0 || q.ask<=0.0) return;
   double mid=0.5*(q.bid+q.ask);
   if(!CanEnterFastByPauseAndDay(idx,mid)) return;

   // Freeze broker-vs-Binance basis from the latest COMPLETED broker M5 close.
   // This preserves the price move that may already have happened after the canonical signal close.
   double fastBasis=mid-g_sym[idx].canonM5Close;
   MqlRates br5[];ArraySetAsSeries(br5,true);
   if(CopyRates(sym,PERIOD_M5,1,1,br5)>=1 && br5[0].close>0.0)
      fastBasis=br5[0].close-g_sym[idx].canonM5Close;

   g_sym[idx].fastActive=true;
   g_sym[idx].fastProbeOpen=false;
   g_sym[idx].fastSide=side;
   g_sym[idx].fastSignalPrice=g_sym[idx].canonM5Close;
   g_sym[idx].fastSignalAtr=g_sym[idx].canonAtr14;
   g_sym[idx].fastOrigZ=g_sym[idx].z;
   g_sym[idx].fastSignalTime=(datetime)(g_sym[idx].canonM5CloseMs/1000);
   g_sym[idx].fastSourceTimeMs=g_sym[idx].sourceTimeMs;
   g_sym[idx].fastLastArmM5Ms=g_sym[idx].canonM5CloseMs;
   g_sym[idx].fastBasis=fastBasis;
   g_sym[idx].fastMaxThesisATR=0.0;
   g_sym[idx].fastMaxCrowdATR=0.0;
   g_sym[idx].fastH1State=g_sym[idx].canonH1State;
   g_sym[idx].fastH4State=g_sym[idx].canonH4State;
   c_fast_arm++;
   PersistFastState(idx);
   LogFast("FAST_ARM",idx,g_sym[idx].fastSignalPrice,0.0,0,0,0,StringFormat("basis=%.8f",g_sym[idx].fastBasis));
   if(InpVerbose) PrintFormat("FAST_ARM %s side=%s z=%+.2f M5=%.8f ATR=%.8f H1=%d H4=%d",sym,(side>0)?"BUY":"SELL",g_sym[idx].z,g_sym[idx].fastSignalPrice,g_sym[idx].fastSignalAtr,g_sym[idx].fastH1State,g_sym[idx].fastH4State);
  }


//+------------------------------------------------------------------+
void TryEnter(const int idx)
  {
   if(g_haltDay || g_haltAll) return;
   if(!IsFeedFresh(idx)) return;

   string sym=g_sym[idx].broker;

   // v2.00 decision clock: one pass per NEW COMPLETED M15 bar.
   // Canonical mode uses Binance USD-M futures M15/ATR so all brokers see the same setup.
   datetime bt=0,barTime=0;
   double barOpen=0.0,barHigh=0.0,barLow=0.0,barClose=0.0,atr=0.0;
   if(InpUseCanonicalBinancePrice)
     {
      if(!g_sym[idx].canonOk) return;
      bt=(datetime)(g_sym[idx].canonM15CloseMs/1000);
      barTime=(datetime)(g_sym[idx].canonM15OpenMs/1000);
      barOpen=g_sym[idx].canonM15Open;barHigh=g_sym[idx].canonM15High;barLow=g_sym[idx].canonM15Low;barClose=g_sym[idx].canonM15Close;
      atr=g_sym[idx].canonAtr14;
     }
   else
     {
      bt=iTime(sym,PERIOD_M15,0);
      MqlRates bar[];ArraySetAsSeries(bar,true);
      if(CopyRates(sym,PERIOD_M15,1,1,bar)<1) return;
      barTime=(datetime)bar[0].time;barOpen=bar[0].open;barHigh=bar[0].high;barLow=bar[0].low;barClose=bar[0].close;
      atr=AtrOf(idx);
     }
   if(bt==0 || bt==g_sym[idx].lastBar) return;
   g_sym[idx].lastBar=bt;
   c_sig++;
   if(barClose<=0.0 || atr<=0.0) return;
   MqlTick q;
   if(!SymbolInfoTick(sym,q) || q.ask<=0.0 || q.bid<=0.0) return;
   double spr=q.ask-q.bid;
   if(spr<=0.0 || spr>InpMaxSpreadATR*atr){c_spread++;return;}

   double z=g_sym[idx].z;

   // ===== Frozen M15 confirmation state machine =====
   if(g_sym[idx].confActive)
     {
      int side=g_sym[idx].confSide;
      double sigPx=g_sym[idx].confSignalPrice;
      double sigAtr=g_sym[idx].confAtr;
      if(sigAtr<=0.0){g_sym[idx].confActive=false;return;}

      // Price-response feature: maximum excursion in CROWD direction
      // from original signal until this completed confirmation bar.
      double exc=0.0;
      if(side<0) exc=(barHigh-sigPx)/sigAtr;       // crowd LONG
      else       exc=(sigPx-barLow)/sigAtr;        // crowd SHORT
      if(exc<0.0) exc=0.0;
      if(exc>g_sym[idx].confMaxCrowdExcATR) g_sym[idx].confMaxCrowdExcATR=exc;

      double confDist=InpConfirmATR*sigAtr;
      bool confirmed=(side<0)?(barClose<=sigPx-confDist):(barClose>=sigPx+confDist);

      if(!confirmed)
        {
         g_sym[idx].confBarsLeft--;
         if(g_sym[idx].confBarsLeft<=0)
           {
            double expRatio=(sigAtr>0.0)?atr/sigAtr:0.0;
            double ageMin=MathMax(0.0,(double)(barTime-g_sym[idx].confSignalTime)/60.0);
            string tnote=StringFormat("origZ=%+.3f currentZ=%+.3f sigATR=%.8f curATR=%.8f expansion=%.3f ageMin=%.1f crowdExc=%.3f",
                                      g_sym[idx].confZ,z,sigAtr,atr,expRatio,ageMin,g_sym[idx].confMaxCrowdExcATR);
            if(InpVerbose) PrintFormat("CONFIRM_TIMEOUT %s side=%d %s",sym,side,tnote);
            LogExec("CONFIRM_TIMEOUT",sym,0,(side<0)?"SELL":"BUY",barClose,0.0,barClose,0.0,0,tnote);
            g_sym[idx].confActive=false;
           }
         return;
        }

      // Confirmation succeeded. v2.00a records regime diagnostics but DOES NOT
      // alter the frozen event side, ATR geometry, retrace, TTL or Z logic.
      double atrExpansion=(sigAtr>0.0)?atr/sigAtr:0.0;
      double confirmAgeMin=MathMax(0.0,(double)(barTime-g_sym[idx].confSignalTime)/60.0);
      bool zSignFlip=(g_sym[idx].confZ*z<0.0);
      string cnote=StringFormat("origZ=%+.3f currentZ=%+.3f signFlip=%s sigATR=%.8f curATR=%.8f expansion=%.3f ageMin=%.1f crowdExc=%.3f",
                                g_sym[idx].confZ,z,(zSignFlip?"YES":"NO"),sigAtr,atr,atrExpansion,confirmAgeMin,g_sym[idx].confMaxCrowdExcATR);
      if(InpVerbose) PrintFormat("CONFIRM_OK %s side=%s %s",sym,(side<0?"SELL":"BUY"),cnote);
      LogExec("CONFIRM_OK",sym,0,(side<0)?"SELL":"BUY",barClose,0.0,barClose,0.0,0,cnote);

      // Quality state is frozen from ORIGINAL signal H1/H4
      // and causal crowd excursion known at this confirmation close.
      g_sym[idx].confActive=false;
      int quality=QualityState(side,g_sym[idx].confH1State,g_sym[idx].confH4State,g_sym[idx].confMaxCrowdExcATR);
      double riskMult=QualityRiskMultiplier(quality);
      string qualityName=QualityName(quality);

      // Pause/anti-repeat gate is evaluated at ORIGINAL signal arm only.
      // Do not re-evaluate here: doing so changes research reachability after confirmation.
      if(HasAnyFor(sym)) return;

      int nb,ns;int tot=CountExposure(nb,ns);
      if(tot>=InpMaxPositions){c_maxpos++;return;}
      if(side<0 && ns>=InpMaxPerSide){c_side++;return;}
      if(side>0 && nb>=InpMaxPerSide){c_side++;return;}

      // Confirmation is canonical. Execution level is translated into broker coordinates
      // using the broker's completed M15 close as a basis anchor; broker feed never decides PASS/FAIL.
      double brokerRef=(q.bid+q.ask)*0.5;
      MqlRates bbar[];ArraySetAsSeries(bbar,true);
      if(CopyRates(sym,PERIOD_M15,1,1,bbar)>=1 && bbar[0].close>0.0) brokerRef=bbar[0].close;
      double brokerBasis=brokerRef-barClose;
      double entry=(side<0)?brokerRef+InpConfirmLimitATR*sigAtr:brokerRef-InpConfirmLimitATR*sigAtr;
      double stop =(side<0)?entry+InpStopATR*sigAtr:entry-InpStopATR*sigAtr;
      double tp   =(side<0)?entry-InpTakeProfitATR*sigAtr:entry+InpTakeProfitATR*sigAtr;
      entry=NormalizePriceTick(sym,entry,(side<0)?+1:-1);
      stop =NormalizePriceTick(sym,stop,(side<0)?+1:-1);
      tp   =NormalizePriceTick(sym,tp,(side<0)?-1:+1);

      double md=MinTradeDistance(sym,false);
      if(side<0 && entry-q.ask<md) return;
      if(side>0 && q.bid-entry<md) return;
      if(MathAbs(stop-entry)<md) return;
      if(MathAbs(tp-entry)<md) return;

      double rawDesiredLot=LotForRisk(sym,side,entry,stop,riskMult);
      if(rawDesiredLot<=0.0){c_lot++;return;}

      bool brokerClamped=false,manualClamped=false;
      double desiredLot=CapLotToBroker(sym,rawDesiredLot,brokerClamped,manualClamped);
      if(desiredLot<=0.0)
        {
         PrintFormat("VOLUME_SKIP %s rawDesired=%.4f brokerMax=%.4f manualMax=%.4f",
                     sym,rawDesiredLot,SymbolInfoDouble(sym,SYMBOL_VOLUME_MAX),InpMaxLot);
         c_lot++;return;
        }
      if(brokerClamped || manualClamped)
         PrintFormat("VOLUME_CLAMP %s rawDesired=%.4f brokerCapped=%.4f brokerMax=%.4f manualMax=%.4f brokerClamp=%s manualClamp=%s",
                     sym,rawDesiredLot,desiredLot,SymbolInfoDouble(sym,SYMBOL_VOLUME_MAX),InpMaxLot,
                     brokerClamped?"YES":"NO",manualClamped?"YES":"NO");

      double minVolumeFrac=MathMax(0.0,MathMin(1.0,InpMinVolumeLotFrac));
      if(minVolumeFrac>0.0 && desiredLot+1e-12 < rawDesiredLot*minVolumeFrac)
        {
         PrintFormat("VOLUME_UNDERSIZE_SKIP %s rawDesired=%.4f brokerCapped=%.4f frac=%.3f minFrac=%.3f brokerMax=%.4f manualMax=%.4f",
                     sym,rawDesiredLot,desiredLot,desiredLot/rawDesiredLot,minVolumeFrac,SymbolInfoDouble(sym,SYMBOL_VOLUME_MAX),InpMaxLot);
         c_lot++;return;
        }

      double notionalPerLot=0.0,desiredNotional=0.0,cappedNotional=0.0;bool notionalClamped=false;
      double notionalLot=ClampLotToNotional(sym,desiredLot,entry,notionalPerLot,desiredNotional,cappedNotional,notionalClamped);
      if(notionalLot<=0.0)
        {
         PrintFormat("NOTIONAL_SKIP %s rawDesired=%.4f brokerCapped=%.4f maxNotional=%.1f%%eq",
                     sym,rawDesiredLot,desiredLot,InpMaxNotionalPctEquity);
         c_lot++;return;
        }

      ENUM_ORDER_TYPE mt=(side>0)?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
      double needDesired=0.0,needActual=0.0,freeMargin=0.0;bool marginClamped=false;
      double lot=ClampLotToMargin(sym,mt,notionalLot,entry,needDesired,needActual,freeMargin,marginClamped);
      if(lot<=0.0)
        {
         PrintFormat("MARGIN_SKIP %s rawDesired=%.4f brokerCapped=%.4f notionalLot=%.4f need=%.2f free=%.2f safety=%.1f%% maxNew=%.1f%%eq maxTotal=%.1f%%eq",
                     sym,rawDesiredLot,desiredLot,notionalLot,needDesired,freeMargin,InpMarginSafetyPct,InpMaxNewTradeMarginPct,InpMaxAccountMarginPct);
         c_lot++;return;
        }
      if(marginClamped)
         PrintFormat("MARGIN_CLAMP %s rawDesired=%.4f brokerCapped=%.4f notionalLot=%.4f actual=%.4f needDesired=%.2f needActual=%.2f free=%.2f",
                     sym,rawDesiredLot,desiredLot,notionalLot,lot,needDesired,needActual,freeMargin);

      double eqNow=AccountInfoDouble(ACCOUNT_EQUITY);
      double finalNotional=(notionalPerLot>0.0)?lot*notionalPerLot:0.0;
      double finalNotionalPct=(eqNow>0.0)?finalNotional/eqNow*100.0:0.0;
      double marginPct=(eqNow>0.0)?needActual/eqNow*100.0:0.0;
      double desiredRiskPct=InpRiskPct*riskMult;
      double actualRiskPct=(rawDesiredLot>0.0)?desiredRiskPct*(lot/rawDesiredLot):0.0;
      double costBps=EffectiveCommissionRoundTurnBps();
      double contract=SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE);
      double estComm=(contract>0.0)?entry*contract*lot*(costBps/10000.0):0.0;
      PrintFormat("RISK_LOT %s raw=%.4f broker=%.4f notionalLot=%.4f actual=%.4f contract=%.4f baseUnits=%.4f notional=%.2f (%.2f%%eq) margin=%.2f%%eq reqRisk=%.3f%% actualRisk=%.3f%% costRT=%.2fbps",
                  sym,rawDesiredLot,desiredLot,notionalLot,lot,contract,lot*contract,finalNotional,finalNotionalPct,marginPct,desiredRiskPct,actualRiskPct,costBps);

      string act="DRYRUN";ulong ord=0;uint rc=0;
      datetime exp=TimeCurrent()+(datetime)(InpOrderValidMin*60);
      string qtag=(quality>0)?"H":((quality<0)?"L":"N");
      string sig=StringFormat("CF200%s%s%I64d",(side<0)?"S":"B",qtag,g_sym[idx].confSourceTimeMs/1000);

      if(!InpDryRun)
        {
         g_trade.SetTypeFillingBySymbol(sym);
         c_sent++;
         bool basic=(side<0)
            ?g_trade.SellLimit(lot,entry,sym,stop,tp,ORDER_TIME_SPECIFIED,exp,sig)
            :g_trade.BuyLimit (lot,entry,sym,stop,tp,ORDER_TIME_SPECIFIED,exp,sig);
         rc=g_trade.ResultRetcode();ord=g_trade.ResultOrder();
         bool ok=basic && RetcodeAccepted(rc) && ord>0;
         if(!ok)
           {
            c_fail++;act="FAIL";
            PrintFormat("%s v200 order fail ret=%u %s",sym,rc,g_trade.ResultRetcodeDescription());
            LogExec("ORDER_SEND",sym,ord,(side<0)?"SELL":"BUY",entry,stop,0,0,rc,"FAIL");
           }
         else
           {
            double ap=0.0,asl=0.0;bool verified=VerifyOrderState(ord,entry,stop,ap,asl);
            GVWrite(GVOrderKey(ord,"ATR"),sigAtr);
            GVWrite(GVOrderKey(ord,"QUALITY"),(double)quality);
            GVWrite(GVOrderKey(ord,"RISK_MULT"),riskMult);
            GVWrite(GVOrderKey(ord,"CROWD_EXC"),g_sym[idx].confMaxCrowdExcATR);
            GVWrite(GVOrderKey(ord,"CANON_CLOSE"),barClose);
            GVWrite(GVOrderKey(ord,"CANON_ATR"),sigAtr);
            GVWrite(GVOrderKey(ord,"BROKER_REF"),brokerRef);
            GVWrite(GVOrderKey(ord,"BASIS"),brokerBasis);
            GVWrite(GVOrderKey(ord,"RAW_DESIRED_LOT"),rawDesiredLot);
            GVWrite(GVOrderKey(ord,"DESIRED_LOT"),desiredLot);
            GVWrite(GVOrderKey(ord,"NOTIONAL_LOT"),notionalLot);
            GVWrite(GVOrderKey(ord,"ACTUAL_LOT"),lot);
            GVWrite(GVOrderKey(ord,"ORIG_Z"),g_sym[idx].confZ);
            GVWrite(GVOrderKey(ord,"CURRENT_Z"),z);
            GVWrite(GVOrderKey(ord,"SIGNAL_ATR"),sigAtr);
            GVWrite(GVOrderKey(ord,"CURRENT_ATR"),atr);
            GVWrite(GVOrderKey(ord,"ATR_EXPANSION"),atrExpansion);
            GVWrite(GVOrderKey(ord,"CHASE_DONE"),1.0); // v2.00 chase frozen OFF
            act=(side<0)?"SELL_LIMIT":"BUY_LIMIT";
            string note=StringFormat("quality=%s riskMult=%.2f h1=%d h4=%d crowdExc=%.3fATR origZ=%+.3f currentZ=%+.3f sigATR=%.8f curATR=%.8f expansion=%.3f ageMin=%.1f canonClose=%.8f brokerRef=%.8f basis=%.8f rawDesired=%.4f brokerCapped=%.4f notionalLot=%.4f actualLot=%.4f notional=%.2f notionalPctEq=%.2f marginPctEq=%.2f costRT=%.2fbps brokerClamp=%s manualClamp=%s notionalClamp=%s marginClamp=%s TP=%.2fATR trail=%s",
                                     qualityName,riskMult,g_sym[idx].confH1State,g_sym[idx].confH4State,
                                     g_sym[idx].confMaxCrowdExcATR,g_sym[idx].confZ,z,sigAtr,atr,atrExpansion,confirmAgeMin,
                                     barClose,brokerRef,brokerBasis,rawDesiredLot,desiredLot,notionalLot,lot,finalNotional,finalNotionalPct,marginPct,costBps,
                                     (brokerClamped?"YES":"NO"),(manualClamped?"YES":"NO"),(notionalClamped?"YES":"NO"),(marginClamped?"YES":"NO"),InpTakeProfitATR,(InpTrailOn?"ON":"OFF"));
            LogExec("ORDER_SEND",sym,ord,(side<0)?"SELL":"BUY",entry,stop,ap,asl,rc,verified?("OK "+note):("VERIFY_FAIL "+note));
            int dg=(int)SymbolInfoInteger(sym,SYMBOL_DIGITS);
            PrintFormat("%s %s #%I64u lot=%.4f @%.*f SL=%.*f TP=%.*f z=%+.2f %s x%.2f H1=%d H4=%d crowdExc=%.3fATR",
                        sym,act,ord,lot,dg,entry,dg,stop,dg,tp,z,qualityName,riskMult,
                        g_sym[idx].confH1State,g_sym[idx].confH4State,g_sym[idx].confMaxCrowdExcATR);
           }
        }

      if(g_csv!=INVALID_HANDLE)
        {
         FileWrite(g_csv,
                   TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
                   TimeToString(TimeGMT(),TIME_DATE|TIME_SECONDS),sig,
                   IntegerToString(g_sym[idx].confSourceTimeMs),sym,g_sym[idx].binance,
                   DoubleToString(g_sym[idx].ratio,6),DoubleToString(g_sym[idx].mean,6),
                   DoubleToString(g_sym[idx].sd,6),DoubleToString(z,4),
                   DoubleToString(barClose,8),DoubleToString(sigAtr,8),DoubleToString(brokerRef,8),DoubleToString(brokerBasis,8),
                   DoubleToString(q.bid,8),DoubleToString(q.ask,8),DoubleToString(spr,8),(side<0)?"SELL":"BUY",
                   DoubleToString(entry,8),DoubleToString(stop,8),DoubleToString(tp,8),
                   DoubleToString(rawDesiredLot,4),DoubleToString(desiredLot,4),DoubleToString(notionalLot,4),DoubleToString(lot,4),DoubleToString(desiredRiskPct,4),DoubleToString(actualRiskPct,4),DoubleToString(estComm,8),
                   DoubleToString(finalNotional,2),DoubleToString(finalNotionalPct,4),DoubleToString(marginPct,4),DoubleToString(costBps,4),
                   DoubleToString(g_sym[idx].confZ,4),DoubleToString(z,4),DoubleToString(sigAtr,8),DoubleToString(atr,8),DoubleToString(atrExpansion,4),DoubleToString(confirmAgeMin,2),
                   IntegerToString(g_sym[idx].confH1State),IntegerToString(g_sym[idx].confH4State),
                   DoubleToString(g_sym[idx].confMaxCrowdExcATR,4),qualityName,DoubleToString(riskMult,2),
                   (brokerClamped?"YES":"NO"),(manualClamped?"YES":"NO"),(notionalClamped?"YES":"NO"),(marginClamped?"YES":"NO"),act,IntegerToString((long)ord));
         FileFlush(g_csv);
        }
      return;
     }

   // No active confirmation: arm from current STATE if |z| is extreme.
   if(HasAnyFor(sym)) return;
   int side=0;
   if(z>=InpZThresholdShort) side=-1;
   else if(z<=-InpZThresholdLong) side=1;
   if(side==0){c_thr++;return;}

   if(!CanEnterByPauseAndDay(idx,barClose)) return;
   int nb,ns;int tot=CountExposure(nb,ns);
   if(tot>=InpMaxPositions){c_maxpos++;return;}
   if(side<0 && ns>=InpMaxPerSide){c_side++;return;}
   if(side>0 && nb>=InpMaxPerSide){c_side++;return;}

   g_sym[idx].confActive=true;
   g_sym[idx].confSide=side;
   g_sym[idx].confSignalPrice=barClose;
   g_sym[idx].confZ=z;
   g_sym[idx].confAtr=atr;
   g_sym[idx].confSignalTime=barTime;
   g_sym[idx].confSourceTimeMs=g_sym[idx].sourceTimeMs;
   g_sym[idx].confBarsLeft=InpConfirmMaxBars;
   g_sym[idx].confMaxCrowdExcATR=0.0;
   if(InpUseCanonicalBinancePrice)
     {
      g_sym[idx].confH1State=g_sym[idx].canonH1State;
      g_sym[idx].confH4State=g_sym[idx].canonH4State;
     }
   else
     {
      g_sym[idx].confH1State=TrendState(idx,PERIOD_H1,g_sym[idx].emaH1Handle);
      g_sym[idx].confH4State=TrendState(idx,PERIOD_H4,g_sym[idx].emaH4Handle);
     }

   if(InpVerbose)
      PrintFormat("CONFIRM_WAIT %s side=%s z=%+.2f signalClose=%.5f atr=%.5f need=%.5f bars=%d H1=%d H4=%d",
                  sym,(side<0?"SELL":"BUY"),z,barClose,atr,InpConfirmATR*atr,InpConfirmMaxBars,
                  g_sym[idx].confH1State,g_sym[idx].confH4State);
  }

//+------------------------------------------------------------------+
void DrawPanel()
  {
   int nb=0,ns=0;int ex=CountExposure(nb,ns);
   string t=StringFormat("CrowdFade v2.00b DEMO  zL=%.2f zS=%.2f  exposure %d/%d%s\n",
                         InpZThresholdLong,InpZThresholdShort,ex,InpMaxPositions,
                         (g_haltAll?"  [STOP EA]":(g_haltDay?"  [DAY HALT]":"")));
   for(int i=0;i<g_symCount;i++)
     {
      bool fresh=IsFeedFresh(i);
      if(!g_sym[i].ok)
        {t+=StringFormat("  %-9s %s\n",g_sym[i].broker,g_sym[i].err);continue;}
      string mark="  ";bool active=false;
      if(g_sym[i].z>=InpZThresholdShort){mark="S ";active=true;}
      else if(g_sym[i].z<=-InpZThresholdLong){mark="L ";active=true;}
      string state=fresh?"":" [STALE]";
      if(g_sym[i].confActive)
         state+=StringFormat(" [CONF %s %d exc=%.2f]",(g_sym[i].confSide<0?"S":"L"),g_sym[i].confBarsLeft,g_sym[i].confMaxCrowdExcATR);
      if(g_sym[i].fastActive)
         state+=StringFormat(" [FAST %s %s th=%.2f cr=%.2f]",(g_sym[i].fastSide<0?"S":"L"),(g_sym[i].fastProbeOpen?"PROBE":"WAIT"),g_sym[i].fastMaxThesisATR,g_sym[i].fastMaxCrowdATR);
      if(InpMaxTradesPerDay>0)
        {
         int dc=DayCodeNow();
         int cnt=(g_sym[i].dayTradeCode==dc)?g_sym[i].dayTradeCount:0;
         state+=StringFormat(" [%d/%d day]",cnt,InpMaxTradesPerDay);
        }
      if(active)
        {
         if(g_sym[i].lastTrade>0)
           {
            long since=(long)(TimeCurrent()-g_sym[i].lastTrade);
            long need=(long)InpPauseHours*3600;
            string mode=InpPauseMode; StringToUpper(mode);
            if(StringFind(mode,"HOUR")>=0 && since<need)
              {
               long left=need-since;
               state+=StringFormat(" [pause %d:%02d]",(int)(left/3600),(int)((left%3600)/60));
              }
            else if(StringFind(mode,"ATR")>=0 && g_sym[i].lastEntryAtr>0.0)
              {
               MqlTick tq; double px=g_sym[i].lastEntryPrice;
               if(SymbolInfoTick(g_sym[i].broker,tq))
                  px=0.5*(tq.bid+tq.ask);
               double moved=MathAbs(px-g_sym[i].lastEntryPrice)/g_sym[i].lastEntryAtr;
               if(moved<InpPauseATR)
                  state+=StringFormat(" [ATR %.2f/%.2f]",moved,InpPauseATR);
              }
           }
         if(HasAnyFor(g_sym[i].broker)) state+=" [in market]";
         else if(!g_sym[i].confActive) state+=" [ready]";
        }
      t+=StringFormat("%s%-9s z%+6.2f L/S %.4f%s\n",mark,g_sym[i].broker,g_sym[i].z,g_sym[i].ratio,state);
     }
   Comment(t);
  }

void FetchDueOne()
  {
   if(g_symCount<=0) return;
   datetime now=TimeCurrent();
   for(int k=0;k<g_symCount;k++)
     {
      int idx=(g_fetchIdx+k)%g_symCount;
      if(g_sym[idx].lastAttempt==0 || now-g_sym[idx].lastAttempt>=InpRefreshSec)
        {
         g_fetchIdx=(idx+1)%g_symCount;
         bool crowdOk=FetchOne(idx);
         bool canonOk=FetchCanonicalOne(idx);
         if(InpVerbose && (!crowdOk || !canonOk))
            PrintFormat("FETCH %s crowd=%s canonical=%s err=%s canonErr=%s",g_sym[idx].broker,(crowdOk?"OK":"FAIL"),(canonOk?"OK":"FAIL"),g_sym[idx].err,g_sym[idx].canonErr);
         return;
        }
     }
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   UpdateGuards();

   // Safety first. Daily halt can optionally flatten; total halt always flattens.
   if(g_haltAll)
     {
      CancelAllPending("overall_dd_halt");
      CloseAllPositions("overall_dd_halt");
      DrawPanel();
      return;
     }
   if(g_haltDay)
     {
      CancelAllPending("daily_dd_halt");
      if(InpCloseOnDailyHalt) CloseAllPositions("daily_dd_halt");
     }

   // Position/order management is TIMER-driven, not dependent on BTC chart ticks.
   ManagePositions();
   ExpireFallbackPending();
   if(!g_haltDay) ChasePendingOrders();

   // Network fetch after risk management so a slow HTTP request cannot precede safety work.
   FetchDueOne();

   if(!g_haltDay && !g_haltAll)
     {
      if(MQLInfoInteger(MQL_TESTER) ||
         (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && MQLInfoInteger(MQL_TRADE_ALLOWED) && AccountInfoInteger(ACCOUNT_TRADE_EXPERT)))
        for(int i=0;i<g_symCount;i++)
          {
           TryFastLane(i);
           TryEnter(i);
          }
     }
   DrawPanel();
  }

// v1.62 intentionally does not manage the portfolio from the chart symbol's tick stream.
void OnTick() {}

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0) return;
   if(!HistoryDealSelect(trans.deal)) return;
   long dealMagic=HistoryDealGetInteger(trans.deal,DEAL_MAGIC);
   if(!IsManagedMagic(dealMagic)) return;
   bool isFastDeal=IsFastMagic(dealMagic);

   long entryType=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   ulong posId=(ulong)HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID);
   ulong order=(ulong)HistoryDealGetInteger(trans.deal,DEAL_ORDER);
   string sym=HistoryDealGetString(trans.deal,DEAL_SYMBOL);
   double px=HistoryDealGetDouble(trans.deal,DEAL_PRICE);
   double commission=HistoryDealGetDouble(trans.deal,DEAL_COMMISSION);
   double fee=HistoryDealGetDouble(trans.deal,DEAL_FEE);
   double profit=HistoryDealGetDouble(trans.deal,DEAL_PROFIT);
   double swap=HistoryDealGetDouble(trans.deal,DEAL_SWAP);
   double dealVol=HistoryDealGetDouble(trans.deal,DEAL_VOLUME);
   long dealType=HistoryDealGetInteger(trans.deal,DEAL_TYPE);
   long dealReason=HistoryDealGetInteger(trans.deal,DEAL_REASON);

   if(entryType==DEAL_ENTRY_IN || entryType==DEAL_ENTRY_INOUT)
     {
      double atr=GVRead(GVOrderKey(order,"ATR"),0.0);
      if(atr<=0.0)
        {
         int si0=SymIndex(sym);
         if(isFastDeal && si0>=0 && g_sym[si0].fastSignalAtr>0.0) atr=g_sym[si0].fastSignalAtr;
         else if(si0>=0) atr=AtrOf(si0);
        }
      int si=SymIndex(sym);
      if(posId>0)
        {
         if(atr>0.0)
           {
            GVWrite(GVPosKey(posId,"ATR"),atr);
            GVWrite(GVPosKey(posId,"RISK_DIST"),InpStopATR*atr);
           }
         if(px>0.0) GVWrite(GVPosKey(posId,"PEAK"),px);
         GVWrite(GVPosKey(posId,"PARTIAL"),0.0);
         GVWrite(GVPosKey(posId,"ENTRY_PRICE"),px);
         GVWrite(GVPosKey(posId,"SIDE"),(dealType==DEAL_TYPE_BUY)?1.0:-1.0);
         GVWrite(GVPosKey(posId,"MFE_R"),0.0);
         GVWrite(GVPosKey(posId,"MAE_R"),0.0);
         GVWrite(GVPosKey(posId,"ENTRY_COMM"),commission);
         GVWrite(GVPosKey(posId,"ENTRY_FEE"),fee);
         if(atr>0.0 && dealVol>0.0 && px>0.0)
           {
            int sd=(dealType==DEAL_TYPE_BUY)?1:-1;
            ENUM_ORDER_TYPE omt=(sd>0)?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
            double riskCash=0.0;
            if(OrderCalcProfit(omt,sym,dealVol,px,px-sd*InpStopATR*atr,riskCash))
               GVWrite(GVPosKey(posId,"RISK_CASH"),MathAbs(riskCash));
           }
         double quality=GVRead(GVOrderKey(order,"QUALITY"),0.0);
         double riskMult=GVRead(GVOrderKey(order,"RISK_MULT"),1.0);
         double crowdExc=GVRead(GVOrderKey(order,"CROWD_EXC"),0.0);
         GVWrite(GVPosKey(posId,"QUALITY"),quality);
         GVWrite(GVPosKey(posId,"RISK_MULT"),riskMult);
         GVWrite(GVPosKey(posId,"CROWD_EXC"),crowdExc);

         // v2.00 parity: cooldown/day-count starts on first ACTUAL fill.
         if(!isFastDeal && si>=0 && GVRead(GVPosKey(posId,"ENTRY_REGISTERED"),0.0)<0.5)
           {
            RegisterEntry(si,px,atr);
            GVWrite(GVPosKey(posId,"ENTRY_REGISTERED"),1.0);
           }
         GVWrite(GVPosKey(posId,"LANE"),isFastDeal?1.0:0.0);
        }
      double qv=GVRead(GVOrderKey(order,"QUALITY"),0.0);
      double rm=GVRead(GVOrderKey(order,"RISK_MULT"),1.0);
      double ce=GVRead(GVOrderKey(order,"CROWD_EXC"),0.0);
      LogExec("FILL",sym,order,"",px,0,px,0,(uint)result.retcode,
              StringFormat("lane=%s pos=%I64u atr=%.8f quality=%s riskMult=%.2f crowdExc=%.3fATR commission=%.8f fee=%.8f",
                           isFastDeal?"FAST":"CORE",posId,atr,QualityName((int)qv),rm,ce,commission,fee));
      return;
     }

   if(entryType==DEAL_ENTRY_OUT || entryType==DEAL_ENTRY_OUT_BY)
     {
      double qv=GVRead(GVPosKey(posId,"QUALITY"),0.0);
      double rm=GVRead(GVPosKey(posId,"RISK_MULT"),1.0);
      double ce=GVRead(GVPosKey(posId,"CROWD_EXC"),0.0);
      double ep=GVRead(GVPosKey(posId,"ENTRY_PRICE"),0.0);
      int sd=(int)GVRead(GVPosKey(posId,"SIDE"),0.0);
      double rd=GVRead(GVPosKey(posId,"RISK_DIST"),0.0);
      double riskCash=GVRead(GVPosKey(posId,"RISK_CASH"),0.0);
      double entryComm=GVRead(GVPosKey(posId,"ENTRY_COMM"),0.0);
      double entryFee=GVRead(GVPosKey(posId,"ENTRY_FEE"),0.0);
      double mfe=GVRead(GVPosKey(posId,"MFE_R"),0.0);
      double mae=GVRead(GVPosKey(posId,"MAE_R"),0.0);
      if(ep>0.0 && rd>0.0 && sd!=0)
        {
         double moveR=sd*(px-ep)/rd;
         if(moveR>mfe) mfe=moveR;
         if(moveR<mae) mae=moveR;
        }
      double grossPriceR=(ep>0.0 && rd>0.0 && sd!=0)?sd*(px-ep)/rd:0.0;
      double netCashR=(riskCash>0.0)?(profit+commission+entryComm+fee+entryFee+swap)/riskCash:0.0;
      string reason="OTHER";
      if(dealReason==DEAL_REASON_SL) reason="SL";
      else if(dealReason==DEAL_REASON_TP) reason="TP";
      else
        {
         int ec=(int)GVRead(GVPosKey(posId,"EXIT_CODE"),0.0);
         if(ec==1) reason="SIGNAL"; else if(ec==2) reason="TIME"; else if(dealReason==DEAL_REASON_EXPERT) reason="EXPERT";
        }
      LogExec("DEAL_OUT",sym,order,"",px,0,px,0,(uint)result.retcode,
              StringFormat("pos=%I64u reason=%s reasonCode=%d quality=%s riskMult=%.2f crowdExc=%.3fATR MFE=%.3fR MAE=%.3fR grossPrice=%.3fR netCash=%.3fR profit=%.8f entryComm=%.8f entryFee=%.8f exitComm=%.8f exitFee=%.8f swap=%.8f",
                           posId,reason,(int)dealReason,QualityName((int)qv),rm,ce,mfe,mae,grossPriceR,netCashR,profit,entryComm,entryFee,commission,fee,swap));
     }
  }
//+------------------------------------------------------------------+