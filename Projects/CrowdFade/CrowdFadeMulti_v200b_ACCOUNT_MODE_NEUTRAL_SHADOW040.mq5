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
#property version   "2.03"
//|  === v2.00 FROZEN ENTRY ===                                      |
//|    LONG  (BUY):  z <= -InpZThresholdLong   default 2.05              |
//|    SHORT (SELL): z >= +InpZThresholdShort  default 2.05              |
//|    Live candidate 2.05/2.05 thresholds; LAB032 flat risk.                 |
//+------------------------------------------------------------------+
#property strict
#property description "CrowdFade v2.00b: frozen V200 core + staged G1 FAST lane; broker/account-mode neutral."

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

input group "=== V200 CORE SHADOW RETRACE (NO REAL ORDERS) ==="
input bool   InpShadowRetraceEnabled = true;   // Observe hypothetical shallower retrace only; NEVER sends orders
input double InpShadowRetraceATR     = 0.40;   // Shadow candidate; real CORE remains InpConfirmLimitATR=0.60
input bool   InpShadowWriteCsv       = true;   // Detailed hypothetical fills/exits/PnL in FILE_COMMON

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
#define MAX_SHADOW  32
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

struct ShadowTrade
  {
   bool     used;
   bool     filled;
   bool     closed;
   bool     realFilled;
   bool     extraFinalized;
   int      symIndex;
   long     sourceMs;
   ulong    realOrder;
   int      side;
   datetime created;
   datetime expiry;
   datetime fillTime;
   double   brokerRef;
   double   atr;
   double   entry;
   double   sl;
   double   tp;
   double   lot;
   double   riskCash;
   double   exitPx;
   double   grossR;
   double   netR;
   double   netCash;
   int      exitCode; // 1=SL 2=TP 3=TIME
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
int      g_shadowCsv  = INVALID_HANDLE;
ShadowTrade g_shadow[MAX_SHADOW];
long     c_shadow_arm=0, c_shadow_fill=0, c_shadow_additional=0, c_shadow_same=0, c_shadow_nofill=0, c_shadow_exit=0;
double   c_shadow_net_cash=0.0, c_shadow_net_r=0.0, c_shadow_additional_cash=0.0, c_shadow_additional_r=0.0;

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

string GVShadowKey(const int slot,const string suffix)
  { return GVPrefix()+"SH"+IntegerToString(slot)+"_"+suffix; }

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

void ClearShadowSlot(const int k)
  {
   if(k<0 || k>=MAX_SHADOW) return;
   g_shadow[k].used=false;
   if(InpPersistState)
     {
      GVWrite(GVShadowKey(k,"USED"),0.0);
     }
  }

void PersistShadowSlot(const int k)
  {
   if(!InpPersistState || k<0 || k>=MAX_SHADOW) return;
   GVWrite(GVShadowKey(k,"USED"),g_shadow[k].used?1.0:0.0);
   if(!g_shadow[k].used) return;
   GVWrite(GVShadowKey(k,"FILLED"),g_shadow[k].filled?1.0:0.0);
   GVWrite(GVShadowKey(k,"CLOSED"),g_shadow[k].closed?1.0:0.0);
   GVWrite(GVShadowKey(k,"REALFILLED"),g_shadow[k].realFilled?1.0:0.0);
   GVWrite(GVShadowKey(k,"EXTRAFIN"),g_shadow[k].extraFinalized?1.0:0.0);
   GVWrite(GVShadowKey(k,"SI"),(double)g_shadow[k].symIndex);
   GVWrite(GVShadowKey(k,"SRC"),(double)g_shadow[k].sourceMs);
   GVWrite(GVShadowKey(k,"ORD"),(double)g_shadow[k].realOrder);
   GVWrite(GVShadowKey(k,"SIDE"),(double)g_shadow[k].side);
   GVWrite(GVShadowKey(k,"CREATED"),(double)g_shadow[k].created);
   GVWrite(GVShadowKey(k,"EXPIRY"),(double)g_shadow[k].expiry);
   GVWrite(GVShadowKey(k,"FILLTIME"),(double)g_shadow[k].fillTime);
   GVWrite(GVShadowKey(k,"REF"),g_shadow[k].brokerRef);
   GVWrite(GVShadowKey(k,"ATR"),g_shadow[k].atr);
   GVWrite(GVShadowKey(k,"ENTRY"),g_shadow[k].entry);
   GVWrite(GVShadowKey(k,"SL"),g_shadow[k].sl);
   GVWrite(GVShadowKey(k,"TP"),g_shadow[k].tp);
   GVWrite(GVShadowKey(k,"LOT"),g_shadow[k].lot);
   GVWrite(GVShadowKey(k,"RISK"),g_shadow[k].riskCash);
   GVWrite(GVShadowKey(k,"EXITPX"),g_shadow[k].exitPx);
   GVWrite(GVShadowKey(k,"GROSSR"),g_shadow[k].grossR);
   GVWrite(GVShadowKey(k,"NETR"),g_shadow[k].netR);
   GVWrite(GVShadowKey(k,"NETCASH"),g_shadow[k].netCash);
   GVWrite(GVShadowKey(k,"EXITCODE"),(double)g_shadow[k].exitCode);
  }

void LoadShadowSlots()
  {
   for(int k=0;k<MAX_SHADOW;k++)
     {
      g_shadow[k].used=(GVRead(GVShadowKey(k,"USED"),0.0)>0.5);
      if(!g_shadow[k].used) continue;
      g_shadow[k].filled=(GVRead(GVShadowKey(k,"FILLED"),0.0)>0.5);
      g_shadow[k].closed=(GVRead(GVShadowKey(k,"CLOSED"),0.0)>0.5);
      g_shadow[k].realFilled=(GVRead(GVShadowKey(k,"REALFILLED"),0.0)>0.5);
      g_shadow[k].extraFinalized=(GVRead(GVShadowKey(k,"EXTRAFIN"),0.0)>0.5);
      g_shadow[k].symIndex=(int)GVRead(GVShadowKey(k,"SI"),-1.0);
      g_shadow[k].sourceMs=(long)GVRead(GVShadowKey(k,"SRC"),0.0);
      g_shadow[k].realOrder=(ulong)GVRead(GVShadowKey(k,"ORD"),0.0);
      g_shadow[k].side=(int)GVRead(GVShadowKey(k,"SIDE"),0.0);
      g_shadow[k].created=(datetime)GVRead(GVShadowKey(k,"CREATED"),0.0);
      g_shadow[k].expiry=(datetime)GVRead(GVShadowKey(k,"EXPIRY"),0.0);
      g_shadow[k].fillTime=(datetime)GVRead(GVShadowKey(k,"FILLTIME"),0.0);
      g_shadow[k].brokerRef=GVRead(GVShadowKey(k,"REF"),0.0);
      g_shadow[k].atr=GVRead(GVShadowKey(k,"ATR"),0.0);
      g_shadow[k].entry=GVRead(GVShadowKey(k,"ENTRY"),0.0);
      g_shadow[k].sl=GVRead(GVShadowKey(k,"SL"),0.0);
      g_shadow[k].tp=GVRead(GVShadowKey(k,"TP"),0.0);
      g_shadow[k].lot=GVRead(GVShadowKey(k,"LOT"),0.0);
      g_shadow[k].riskCash=GVRead(GVShadowKey(k,"RISK"),0.0);
      g_shadow[k].exitPx=GVRead(GVShadowKey(k,"EXITPX"),0.0);
      g_shadow[k].grossR=GVRead(GVShadowKey(k,"GROSSR"),0.0);
      g_shadow[k].netR=GVRead(GVShadowKey(k,"NETR"),0.0);
      g_shadow[k].netCash=GVRead(GVShadowKey(k,"NETCASH"),0.0);
      g_shadow[k].exitCode=(int)GVRead(GVShadowKey(k,"EXITCODE"),0.0);
      if(g_shadow[k].symIndex<0 || g_shadow[k].symIndex>=g_symCount || g_shadow[k].side==0 || g_shadow[k].atr<=0.0)
         ClearShadowSlot(k);
     }
  }

void LogShadow(const string event,const int k,const double bid,const double ask,const string reason="",
               const double exitPx=0.0,const double grossR=0.0,const double netR=0.0,const double netCash=0.0,const string note="")
  {
   if(g_shadowCsv==INVALID_HANDLE || k<0 || k>=MAX_SHADOW || !g_shadow[k].used) return;
   string sym=(g_shadow[k].symIndex>=0 && g_shadow[k].symIndex<g_symCount)?g_sym[g_shadow[k].symIndex].broker:"?";
   FileWrite(g_shadowCsv,
             TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),TimeToString(TimeGMT(),TIME_DATE|TIME_SECONDS),
             event,sym,IntegerToString(g_shadow[k].sourceMs),IntegerToString((long)g_shadow[k].realOrder),(g_shadow[k].side>0)?"BUY":"SELL",
             DoubleToString(InpConfirmLimitATR,4),DoubleToString(InpShadowRetraceATR,4),
             DoubleToString(g_shadow[k].brokerRef,8),DoubleToString(g_shadow[k].atr,8),DoubleToString(g_shadow[k].entry,8),
             DoubleToString(g_shadow[k].sl,8),DoubleToString(g_shadow[k].tp,8),DoubleToString(g_shadow[k].lot,4),DoubleToString(g_shadow[k].riskCash,8),
             g_shadow[k].realFilled?"YES":"NO",g_shadow[k].extraFinalized?"YES":"NO",
             DoubleToString(bid,8),DoubleToString(ask,8),reason,DoubleToString(exitPx,8),
             DoubleToString(grossR,6),DoubleToString(netR,6),DoubleToString(netCash,8),note);
   FileFlush(g_shadowCsv);
  }

int FindFreeShadowSlot()
  {
   for(int k=0;k<MAX_SHADOW;k++) if(!g_shadow[k].used) return k;
   return -1;
  }

void ArmShadowRetrace(const int idx,const long sourceMs,const ulong realOrder,const int side,
                      const double brokerRef,const double sigAtr,const double realLot,const double riskMult)
  {
   if(!InpShadowRetraceEnabled || idx<0 || idx>=g_symCount || side==0 || sigAtr<=0.0) return;
   int k=FindFreeShadowSlot();
   if(k<0)
     {
      Print("SHADOW_R040_CAPACITY: no free shadow slot");
      return;
     }
   string sym=g_sym[idx].broker;
   double entry=(side<0)?brokerRef+InpShadowRetraceATR*sigAtr:brokerRef-InpShadowRetraceATR*sigAtr;
   double sl=entry-side*InpStopATR*sigAtr;
   double tp=entry+side*InpTakeProfitATR*sigAtr;
   entry=NormalizePriceTick(sym,entry,(side<0)?+1:-1);
   sl=NormalizePriceTick(sym,sl,(side<0)?+1:-1);
   tp=NormalizePriceTick(sym,tp,(side<0)?-1:+1);

   // Pure retrace counterfactual: use EXACTLY the same lot as the accepted real 0.60 order.
   // This prevents shadow sizing/margin from becoming a second changed variable.
   double lot=realLot;
   ENUM_ORDER_TYPE mt=(side>0)?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   double riskCash=0.0;
   if(lot>0.0) OrderCalcProfit(mt,sym,lot,entry,sl,riskCash);
   riskCash=MathAbs(riskCash);

   g_shadow[k].used=true;
   g_shadow[k].filled=false;
   g_shadow[k].closed=false;
   g_shadow[k].realFilled=false;
   g_shadow[k].extraFinalized=false;
   g_shadow[k].symIndex=idx;
   g_shadow[k].sourceMs=sourceMs;
   g_shadow[k].realOrder=realOrder;
   g_shadow[k].side=side;
   g_shadow[k].created=TimeCurrent();
   g_shadow[k].expiry=TimeCurrent()+(datetime)(InpOrderValidMin*60);
   g_shadow[k].fillTime=0;
   g_shadow[k].brokerRef=brokerRef;
   g_shadow[k].atr=sigAtr;
   g_shadow[k].entry=entry;
   g_shadow[k].sl=sl;
   g_shadow[k].tp=tp;
   g_shadow[k].lot=lot;
   g_shadow[k].riskCash=riskCash;
   g_shadow[k].exitPx=0.0;g_shadow[k].grossR=0.0;g_shadow[k].netR=0.0;g_shadow[k].netCash=0.0;g_shadow[k].exitCode=0;
   PersistShadowSlot(k);
   c_shadow_arm++;
   MqlTick q;ZeroMemory(q);SymbolInfoTick(sym,q);
   LogShadow("SHADOW_ARM",k,q.bid,q.ask,"",0,0,0,0,
             StringFormat("NO_ORDER_SENT riskMult=%.2f realEntryRetrace=%.2f shadowRetrace=%.2f",riskMult,InpConfirmLimitATR,InpShadowRetraceATR));
  }

void MarkShadowRealFill(const ulong realOrder)
  {
   if(realOrder==0) return;
   for(int k=0;k<MAX_SHADOW;k++)
     {
      if(!g_shadow[k].used || g_shadow[k].realOrder!=realOrder) continue;
      g_shadow[k].realFilled=true;
      PersistShadowSlot(k);
      MqlTick q;ZeroMemory(q);string sym=g_sym[g_shadow[k].symIndex].broker;SymbolInfoTick(sym,q);
      LogShadow("SHADOW_REAL_FILL_SEEN",k,q.bid,q.ask);
     }
  }

void CloseShadow(const int k,const string reason,const double exitPx,const double bid,const double ask)
  {
   if(k<0 || k>=MAX_SHADOW || !g_shadow[k].used || !g_shadow[k].filled || g_shadow[k].closed || g_shadow[k].atr<=0.0) return;
   string sym=g_sym[g_shadow[k].symIndex].broker;
   double rd=InpStopATR*g_shadow[k].atr;
   double grossR=(rd>0.0)?g_shadow[k].side*(exitPx-g_shadow[k].entry)/rd:0.0;
   ENUM_ORDER_TYPE mt=(g_shadow[k].side>0)?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   double grossCash=0.0;
   if(g_shadow[k].lot>0.0) OrderCalcProfit(mt,sym,g_shadow[k].lot,g_shadow[k].entry,exitPx,grossCash);
   double contract=SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE);
   double estCost=(g_shadow[k].lot>0.0 && contract>0.0)?g_shadow[k].entry*contract*g_shadow[k].lot*(EffectiveCommissionRoundTurnBps()/10000.0):0.0;
   double netCash=grossCash-estCost;
   double netR=(g_shadow[k].riskCash>0.0)?netCash/g_shadow[k].riskCash:grossR;
   g_shadow[k].closed=true;
   g_shadow[k].exitPx=exitPx;
   g_shadow[k].grossR=grossR;
   g_shadow[k].netR=netR;
   g_shadow[k].netCash=netCash;
   g_shadow[k].exitCode=(reason=="SL")?1:((reason=="TP")?2:3);
   c_shadow_exit++;c_shadow_net_cash+=netCash;c_shadow_net_r+=netR;
   if(g_shadow[k].extraFinalized && !g_shadow[k].realFilled)
     { c_shadow_additional_cash+=netCash;c_shadow_additional_r+=netR; }
   PersistShadowSlot(k);
   LogShadow("SHADOW_EXIT",k,bid,ask,reason,exitPx,grossR,netR,netCash,
             StringFormat("holdMin=%d additionalFinal=%s",(int)((TimeCurrent()-g_shadow[k].fillTime)/60),(g_shadow[k].extraFinalized && !g_shadow[k].realFilled)?"YES":"NO"));
   if(g_shadow[k].extraFinalized) ClearShadowSlot(k); // if TTL already elapsed, classification is final
  }

void ManageShadowRetrace()
  {
   if(!InpShadowRetraceEnabled) return;
   datetime now=TimeCurrent();
   for(int k=0;k<MAX_SHADOW;k++)
     {
      if(!g_shadow[k].used) continue;
      if(g_shadow[k].symIndex<0 || g_shadow[k].symIndex>=g_symCount){ClearShadowSlot(k);continue;}
      string sym=g_sym[g_shadow[k].symIndex].broker;
      MqlTick q;if(!SymbolInfoTick(sym,q) || q.bid<=0.0 || q.ask<=0.0) continue;

      if(!g_shadow[k].filled)
        {
         bool hit=(g_shadow[k].side>0)?(q.ask<=g_shadow[k].entry):(q.bid>=g_shadow[k].entry);
         if(hit && now<=g_shadow[k].expiry)
           {
            g_shadow[k].filled=true;g_shadow[k].fillTime=now;c_shadow_fill++;
            PersistShadowSlot(k);
            LogShadow("SHADOW_FILL",k,q.bid,q.ask,"",g_shadow[k].entry,0,0,0,"hypothetical fill only; NO REAL ORDER");
           }
         if(!g_shadow[k].filled && now>g_shadow[k].expiry)
           {
            c_shadow_nofill++;
            LogShadow("SHADOW_EXPIRE_NO_FILL",k,q.bid,q.ask,"TTL",0,0,0,0,"shadow retrace also would not fill");
            ClearShadowSlot(k);
            continue;
           }
        }

      if(g_shadow[k].used && !g_shadow[k].extraFinalized && now>g_shadow[k].expiry+5)
        {
         g_shadow[k].extraFinalized=true;
         if(g_shadow[k].filled && !g_shadow[k].realFilled)
           {
            c_shadow_additional++;
            if(g_shadow[k].closed)
              { c_shadow_additional_cash+=g_shadow[k].netCash;c_shadow_additional_r+=g_shadow[k].netR; }
           }
         else if(g_shadow[k].filled && g_shadow[k].realFilled) c_shadow_same++;
         PersistShadowSlot(k);
         LogShadow("SHADOW_CLASSIFY",k,q.bid,q.ask,(g_shadow[k].filled && !g_shadow[k].realFilled)?"ADDITIONAL_FILL":((g_shadow[k].filled && g_shadow[k].realFilled)?"SAME_SETUP_FILLED":"OTHER"),
                   g_shadow[k].closed?g_shadow[k].exitPx:0.0,g_shadow[k].grossR,g_shadow[k].netR,g_shadow[k].netCash);
         if(g_shadow[k].closed){ClearShadowSlot(k);continue;}
        }

      if(!g_shadow[k].used || !g_shadow[k].filled || g_shadow[k].closed) continue;
      double exitPx=0.0;string reason="";
      if(g_shadow[k].side>0)
        {
         if(q.bid<=g_shadow[k].sl){exitPx=g_shadow[k].sl;reason="SL";}
         else if(q.bid>=g_shadow[k].tp){exitPx=g_shadow[k].tp;reason="TP";}
        }
      else
        {
         if(q.ask>=g_shadow[k].sl){exitPx=g_shadow[k].sl;reason="SL";}
         else if(q.ask<=g_shadow[k].tp){exitPx=g_shadow[k].tp;reason="TP";}
        }
      if(reason=="" && now-g_shadow[k].fillTime>=(datetime)(InpHoldHours*3600))
        { exitPx=(g_shadow[k].side>0)?q.bid:q.ask;reason="TIME"; }
      if(reason!="") CloseShadow(k,reason,exitPx,q.bid,q.ask);
     }
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