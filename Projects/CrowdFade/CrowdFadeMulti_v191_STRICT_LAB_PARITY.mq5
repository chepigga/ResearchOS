//+------------------------------------------------------------------+
//|  CrowdFadeMulti.mq5                                               |
//|  Мультивалютний EA: торгівля ПРОТИ позиції роздрібу на Binance.   |
//|                                                                   |
//|  СИГНАЛ                                                           |
//|    z = (L/S зараз − середнє за задане вікно) / стандартне відхилення    |
//|    z >= +поріг  натовп перекошений у ЛОНГИ -> SELL LIMIT          |
//|    z <= -поріг  перекошений у ШОРТИ        -> BUY  LIMIT          |
//|    вхід: ліміт на 1 ATR ПРОТИ напрямку, дійсний 3 години          |
//|    стоп: 1.5 ATR   вихід: signal/time/trailing, БЕЗ фіксованої цілі               |
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
//|    InpUseConfirm=true, InpConfirmATR=0.30, InpConfirmMarket=true |
//|    InpStopATR=1.50, InpExitZ=0.00, InpEntryOffsetATR=0 (не викор.)|
//|    InpPauseMode=ATR, InpPauseATR=1.0, InpMaxTradesPerDay=3       |
//|    v1.91f: v1.91d risk shell + NO default Z exit + same-side confirm gate. |
//|                                                                   |
//+------------------------------------------------------------------+
#property copyright "ResearchOS"
#property version   "1.93"
#property strict
#property description "CrowdFade V191 STRICT LAB046-049 parity / BALANCED 3.5-0.5."

#include <Trade\Trade.mqh>

//--- символи -------------------------------------------------------
input group "=== СИМВОЛИ ==="
input string InpPairs = "BTCUSD:BTCUSDT"; // LAB046-049 validated default universe
                                          // брокер:Binance через ;

//--- сигнал --------------------------------------------------------
input group "=== СИГНАЛ (заморожено дослідженням) ==="
input int    InpZWindowHours  = 6;        // [v1.10] Вікно смуги, годин (було 24)
input double InpZThreshold    = 1.00;     // v1.91 live baseline: symmetric |z| threshold
input double InpEntryOffsetATR= 0.00;     // [v1.91] не використовується при InpUseConfirm=true
input int    InpOrderValidHrs = 3;        // Життя заявки, годин
input double InpStopATR       = 1.50;     // [v1.91] краще з confirm (було 1.00)
input int    InpHoldHours     = 6;        // [v1.10] Тримання, годин (було 24)
input int    InpPauseHours    = 6;        // [v1.91] мін. години (для Hours / hybrid)
input int    InpAtrPeriod     = 14;       // ATR на M15
input double InpExitZ         = 0.75;     // STRICT LAB parity
input bool   InpChaseOrder    = false;    // [v1.80] ВИМКНЕНО: шкодить (див. шапку)
input int    InpChaseAfterBars= 4;        // [v1.30] через скільки барів M15
input double InpChaseToATR    = 0.40;     // [v1.30] новий відступ від ціни, ATR

input group "=== [v1.91] ПІДТВЕРДЖЕННЯ ВІДКАТУ ==="
input bool   InpUseConfirm     = true;     // вмикати підтвердження відкату
input double InpConfirmATR     = 0.30;     // live v1.91 setting seen in journal: 0.30 ATR
input int    InpConfirmMaxBars = 9;        // display/diagnostic only; strict freshness is wall-clock 45m
input int    InpConfirmMaxAgeMin = 45;       // [v1.91f] wall-clock cap; broker-session/sparse-bar safe
input double InpConfirmMinAbsZ = 0.00;       // STRICT parity: disabled; LAB uses only opposite ExitZ contradiction
input double InpConfirmMaxAdverseATR = 0.75; // [v1.91f] cancel if price first runs too far WITH crowd
input double InpConfirmMinResponseRatio = 0.00; // STRICT parity: disabled
input bool   InpConfirmMarket  = true;     // true=market після confirm, false=limit
input double InpConfirmLimitATR= 0.10;     // додатковий відступ якщо limit

input group "=== [v1.91] ПАУЗА / ЛІМІТ УГОД ==="
input string InpPauseMode      = "ATR";    // Hours | ATR | Hours+ATR
input double InpPauseATR       = 1.00;     // для ATR: мін. рух ціни від last entry
input int    InpMaxTradesPerDay= 3;        // макс угод на пару за день (0=без ліміту)

input group "=== [v1.40] Вага позиції за багатофакторною моделлю ==="
input bool   InpUseScore      = false;    // STRICT LAB parity: fixed risk, no research-external score weighting
input double InpScoreGain     = 0.60;     // сила зважування (0 = вимкнено)
input double InpScoreMinW     = 0.40;     // мін множник лота
input double InpScoreMaxW     = 2.00;     // макс множник лота

input group "=== [v1.50] Частковий вихід ==="
input bool   InpPartialClose  = false;    // вмикати частковий вихід
input double InpPartialAtATR  = 1.50;     // рівень у ATR від входу
input double InpPartialFrac   = 0.50;     // яку частку закрити (0.1..0.9)

input group "=== [v1.70] Беззбиток ==="
input double InpBreakEvenAtATR= 0.50;     // [v1.80] було 1.00
input double InpBreakEvenLock = 0.15;     // [v1.80] МУСИТЬ бути > спреду в ATR!

input group "=== [v1.60] Трейлінг-стоп ==="
input bool   InpTrailOn       = true;     // вмикати трейлінг
input double InpTrailATR      = 0.50;     // відстань від піку, ATR
input double InpTrailArmATR   = 3.50;     // LAB048/049 BALANCED candidate; use 2.50 for LAB047 control

//--- ризик ---------------------------------------------------------
input group "=== РИЗИК ==="
input double InpRiskPct       = 0.25;     // Ризик на угоду, % балансу
input int    InpMaxPositions  = 3;        // МАКС одночасних позицій (крипта корельована!)
input int    InpMaxPerSide    = 2;        // Макс позицій в один бік
input double InpMaxSpreadATR  = 0.00;     // STRICT: disabled as signal gate; >0 enables execution-only safety gate
input double InpMaxDailyDDPct = 3.00;     // Денна просадка -> стоп на день
input double InpMaxTotalDDPct = 8.00;     // Загальна просадка -> стоп EA
input double InpMaxLot        = 0.0;      // Optional manual lot ceiling; 0 = DISABLED (critical for broker parity)
input bool   InpAutoBrokerCostProfile = true; // FTMO=>6.5 bps RT, GetLeveraged=>0; otherwise use manual input
input double InpCommissionRoundTurnBps = 0.0; // Manual fallback/override when auto profile is OFF
input double InpMaxNotionalPctEquity = 15.0;  // HARD CAP: ONE new position notional <= 15% of equity (broker-neutral; 0=off)
input bool   InpAdaptiveMarginLot = true;     // Reduce lot instead of inflating exposure / hard blocking
input double InpMarginSafetyPct = 90.0;       // Keep this % check against FREE margin as final safety headroom
input double InpMaxNewTradeMarginPct = 5.0;   // HARD CAP: margin of ONE new trade <= 5% of equity (0=off)
input double InpMaxAccountMarginPct = 12.0;   // HARD CAP: projected TOTAL account margin <= 12% of equity (0=off)
input double InpMinMarginLotFrac = 0.00;      // 0=allow under-risking after safety clamp; never inflate notional to hit risk target
input double InpMinVolumeLotFrac = 0.00;      // 0=allow broker cap but LOUDLY log under-sizing; >0 can enforce minimum fraction
input int    InpSlippagePts   = 50;       // Прослизання
input long   InpMagic         = 77001;    // Magic

//--- безпека -------------------------------------------------------
input group "=== БЕЗПЕКА ==="
input bool   InpDemoOnly      = false;    // [v1.70] дефолт: реальний рахунок ДОЗВОЛЕНО
input bool   InpDryRun        = false;    // true = тільки лог, без ордерів
input int    InpRefreshSec    = 15;       // flow poll; completed 5m source is still processed only once
input bool   InpWriteCsv      = true;     // Журнал сигналів у CSV
input bool   InpVerbose       = true;     // Детальний лог

input group "=== [v1.62] EXECUTION PARITY ==="
input int    InpExecTimerMs        = 1000;    // Детермінований management scheduler, мс
input int    InpWebTimeoutMs       = 4000;    // Timeout for flow/history; ticker uses <=1000ms
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
#define TICKER_PATH "/fapi/v1/ticker/price"
#define LAB_M5_MS   300000
#define LAB_M15_MS  900000
#define LAB_VOL_WIN 8640
#define LAB_VOL_MIN 2880
#define LAB_FETCH_BARS 8725
#define MAX_POINTS  500
#define BIN_PERIOD  "5m"
#define BIN_STEP_S  300
#define MAX_SYM     32
#define ORDER_TAG   "CrowdFade"

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

struct SymState
  {
   string   broker;
   string   binance;
   bool     ok;                 // хоча б один валідний fetch
   int      atrHandle;
   double   z;
   double   ratio;
   double   mean;
   double   sd;
   datetime lastFetch;          // останній УСПІШНИЙ локальний fetch
   datetime lastAttempt;        // остання спроба WebRequest
   long     sourceTimeMs;       // timestamp останньої Binance flow 5m точки
   long     lastSignalSourceMs;   // source point already processed by strict signal state machine
   bool     rapidRepeat30;        // LAB046 exact same-sign prior extreme <=30m
   double   priorSameExtremeGapMin;
   double   refLastPrice;         // current Binance last trade price
   long     refLastPriceMs;
   datetime lastTrade;          // час постановки останньої заявки (cooldown anchor)
   datetime lastBar;
   datetime sigSince;
   double   z40;
   int      durBars;
   string   err;
   // [v1.91] confirmation state
   bool     confActive;         // чекаємо підтвердження відкату
   int      confSide;           // +1 long / -1 short
   double   confSignalPrice;    // execution-side price at signal
   double   confSignalMid;      // [v1.91f] broker-neutral mid snapshot for response quality
   double   confAtr;            // ATR snapshot на сигналі
   double   confZ;              // Z snapshot на момент постановки confirmation thesis
   double   confMaxFavATR;      // [v1.91f] max thesis-direction excursion since arm
   double   confMaxAdvATR;      // [v1.91f] max crowd-direction excursion since arm
   datetime confSignalTime;      // STRICT: LAB decision time = source period start + 300s
   long     confSourceTimeMs;      // ORIGINAL flow source timestamp frozen at arm
   double   confVolQ67;            // causal lagged q67 ATR%
   double   confAtrPct;            // current signal ATR%
   bool     confHighVol;
   int      confBarsLeft;       // скільки M5 барів залишилось
   // [v1.91] adaptive pause + daily limit
   double   lastEntryPrice;     // ціна останнього входу (для ATR-паузи)
   double   lastEntryAtr;       // ATR на момент входу
   int      dayTradeCount;      // угод сьогодні по цій парі
   int      dayTradeCode;       // YYYYMMDD останнього підрахунку
  };

struct BrokerSpec
  {
   int      digits;
   double   point;
   double   tickSize;
   double   volumeMin;
   double   volumeMax;
   double   volumeStep;
   double   contractSize;
   long     stopsLevelPts;
   long     freezeLevelPts;
   long     tradeMode;
  };

SymState g_sym[MAX_SYM];
int      g_symCount   = 0;
int      g_fetchIdx   = 0;
int      g_csv        = INVALID_HANDLE;
int      g_execCsv    = INVALID_HANDLE;

double   g_eqPeak     = 0.0;
double   g_dayStart   = 0.0;
int      g_dayCode    = -1;
bool     g_haltDay    = false;
bool     g_haltAll    = false;
long     c_sig=0, c_thr=0, c_pause=0, c_maxpos=0, c_side=0,
         c_spread=0, c_lot=0, c_sent=0, c_fail=0, c_sigexit=0, c_timeexit=0,
         c_chased=0, c_chasefail=0, c_partial=0, c_trail=0, c_be=0;

//--- persistent keys ------------------------------------------------
string GVPrefix()
  {
   return StringFormat("CF162_%I64d_%I64d_", AccountInfoInteger(ACCOUNT_LOGIN), InpMagic);
  }
string GVKey(const string suffix) { return GVPrefix() + suffix; }
string GVOrderKey(const ulong ticket,const string suffix)
  { return GVPrefix()+"O"+IntegerToString((long)ticket)+"_"+suffix; }
string GVPosKey(const ulong posId,const string suffix)
  { return GVPrefix()+"P"+IntegerToString((long)posId)+"_"+suffix; }
string GVLastTradeKey(const string sym) { return GVPrefix()+"LT_"+sym; }

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
   sp.contractSize   =SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE);
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
   PrintFormat("SPEC %s | digits=%d point=%g tick=%g vol=%.8g..%.8g step=%.8g contract=%.8g stops=%d freeze=%d trade_mode=%d",
               sym,sp.digits,sp.point,sp.tickSize,sp.volumeMin,sp.volumeMax,sp.volumeStep,sp.contractSize,
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
      if(hnd == INVALID_HANDLE)
        {
         PrintFormat("  ПРОПУСК %s: ATR-хендл не створено (немає історії M15?)", b);
         continue;
        }

      g_sym[cnt].broker    = b;
      g_sym[cnt].binance   = x;
      g_sym[cnt].ok        = false;
      g_sym[cnt].atrHandle = hnd;
      g_sym[cnt].z = 0; g_sym[cnt].ratio = 0; g_sym[cnt].mean = 0; g_sym[cnt].sd = 0;
      g_sym[cnt].lastFetch = 0; g_sym[cnt].lastAttempt = 0; g_sym[cnt].sourceTimeMs = 0; g_sym[cnt].lastSignalSourceMs=0;
      g_sym[cnt].rapidRepeat30=false; g_sym[cnt].priorSameExtremeGapMin=-1.0;
      g_sym[cnt].refLastPrice=0.0; g_sym[cnt].refLastPriceMs=0;
      g_sym[cnt].lastTrade = 0; g_sym[cnt].lastBar = 0;
      g_sym[cnt].sigSince = 0;
      g_sym[cnt].z40 = 0.0; g_sym[cnt].durBars = 0;
      g_sym[cnt].err = "";
      g_sym[cnt].confActive = false;
      g_sym[cnt].confSide = 0;
      g_sym[cnt].confSignalPrice = 0;
      g_sym[cnt].confSignalMid = 0;
      g_sym[cnt].confAtr = 0;
      g_sym[cnt].confZ = 0;
      g_sym[cnt].confMaxFavATR = 0;
      g_sym[cnt].confMaxAdvATR = 0;
      g_sym[cnt].confSignalTime = 0;
      g_sym[cnt].confSourceTimeMs = 0;
      g_sym[cnt].confVolQ67 = 0.0; g_sym[cnt].confAtrPct=0.0; g_sym[cnt].confHighVol=false;
      g_sym[cnt].confBarsLeft = 0;
      g_sym[cnt].lastEntryPrice = 0;
      g_sym[cnt].lastEntryAtr = 0;
      g_sym[cnt].dayTradeCount = 0;
      g_sym[cnt].dayTradeCode = -1;
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

int OnInit()
  {
   if(InpDemoOnly && AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL)
     {
      Print("ЗУПИНЕНО: InpDemoOnly=true, а рахунок РЕАЛЬНИЙ.");
      return INIT_FAILED;
     }
   if(InpZWindowHours < 2 || InpZWindowHours > 40)
     { Print("ПОМИЛКА: InpZWindowHours поза [2..40]"); return INIT_PARAMETERS_INCORRECT; }
   if(InpZThreshold <= 0.0 || InpStopATR <= 0.0 || InpRiskPct <= 0.0)
     { Print("ПОМИЛКА: некоректні параметри ризику"); return INIT_PARAMETERS_INCORRECT; }
   if(InpMaxPositions < 1 || InpMaxPerSide < 1 || InpExecTimerMs < 100)
     { Print("ПОМИЛКА: ліміти позицій/таймера"); return INIT_PARAMETERS_INCORRECT; }

   // STRICT LAB parity guard: refuse accidental strategy drift.
   string pm=InpPauseMode; StringToUpper(pm); StringReplace(pm," ","");
   bool armOk=(MathAbs(InpTrailArmATR-2.50)<1e-9 || MathAbs(InpTrailArmATR-3.50)<1e-9 || MathAbs(InpTrailArmATR-5.00)<1e-9);
   bool strictOk=
      MathAbs(InpZThreshold-1.00)<1e-9 &&
      MathAbs(InpConfirmATR-0.30)<1e-9 &&
      InpConfirmMaxAgeMin==45 &&
      MathAbs(InpConfirmMaxAdverseATR-0.75)<1e-9 &&
      MathAbs(InpConfirmMinAbsZ)<1e-12 &&
      MathAbs(InpConfirmMinResponseRatio)<1e-12 &&
      InpUseConfirm && InpConfirmMarket &&
      MathAbs(InpStopATR-1.50)<1e-9 &&
      MathAbs(InpBreakEvenAtATR-0.50)<1e-9 &&
      MathAbs(InpBreakEvenLock-0.15)<1e-9 &&
      InpTrailOn && MathAbs(InpTrailATR-0.50)<1e-9 && armOk &&
      MathAbs(InpExitZ-0.75)<1e-9 &&
      InpHoldHours==6 &&
      pm=="ATR" && MathAbs(InpPauseATR-1.00)<1e-9 &&
      InpMaxTradesPerDay==3 &&
      !InpPartialClose && !InpChaseOrder && !InpUseScore &&
      MathAbs(InpMaxSpreadATR)<1e-12;
   if(!strictOk)
     {
      Print("STRICT_PARITY_CONFIG_FAIL: parameters differ from LAB046-049 frozen shell.");
      Print("Allowed trail arms: 2.5 / 3.5 / 5.0, gap fixed 0.5; default build uses 3.5.");
      return INIT_PARAMETERS_INCORRECT;
     }

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints((ulong)InpSlippagePts);
   g_trade.SetAsyncMode(false);
   g_trade.SetMarginMode();

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
     }

   if(InpWriteCsv)
     {
      string fn="CrowdFade_signals_v191_STRICT_LAB_PARITY.csv";
      g_csv=FileOpen(fn,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,';');
      if(g_csv==INVALID_HANDLE) PrintFormat("CSV не відкрито, error=%d",GetLastError());
      else
        {
         bool empty=(FileSize(g_csv)==0);
         FileSeek(g_csv,0,SEEK_END);
         if(empty) FileWrite(g_csv,"time_server","time_utc","source_ms","signal_decision","broker","binance","ratio","mean","sd","z","signal_atr","ref_price","side","broker_entry","stop","lot","action","order_ticket");
         FileFlush(g_csv);
        }
     }
   if(InpWriteExecutionCsv)
     {
      g_execCsv=FileOpen("CrowdFade_execution_v191_STRICT_LAB_PARITY.csv",FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,';');
      if(g_execCsv==INVALID_HANDLE) PrintFormat("Execution CSV не відкрито, error=%d",GetLastError());
      else
        {
         bool empty=(FileSize(g_execCsv)==0);
         FileSeek(g_execCsv,0,SEEK_END);
         if(empty) FileWrite(g_execCsv,"utc","server","event","symbol","ticket","side","req_price","req_sl","actual_price","actual_sl","retcode","source_ms","note");
         FileFlush(g_execCsv);
        }
     }

   EventSetMillisecondTimer(InpExecTimerMs);
   PrintFormat("INIT_OK CrowdFade V191 STRICT_LAB_PARITY | symbols=%d | z=%.2f | max exposure=%d | scheduler=%dms",
               g_symCount,InpZThreshold,InpMaxPositions,InpExecTimerMs);
   PrintFormat("  state signal: window %dh | pause %dh | hold %dh | exit z=%.2f",
               InpZWindowHours,InpPauseHours,InpHoldHours,InpExitZ);
   if(InpChaseOrder) PrintFormat("  CHASE ONCE: after %d M15 bars -> %.2f ATR",InpChaseAfterBars,InpChaseToATR);
   if(InpUseConfirm)
      PrintFormat("  CONFIRM: %.2f ATR, max %d M5 bars / %d min, |Z|>=%.2f, adv<=%.2fATR, response>=%.2f, %s",
                  InpConfirmATR,InpConfirmMaxBars,InpConfirmMaxAgeMin,InpConfirmMinAbsZ,
                  InpConfirmMaxAdverseATR,InpConfirmMinResponseRatio,InpConfirmMarket?"MARKET":"LIMIT");
   PrintFormat("  PAUSE mode=%s | hours=%d | ATR=%.2f | max/day/symbol=%d",
               InpPauseMode,InpPauseHours,InpPauseATR,InpMaxTradesPerDay);
   if(InpTrailOn) PrintFormat("  TRAIL: %.2f ATR from REAL peak, arm %.2f ATR, ATR snapshot at entry/chase",InpTrailATR,InpTrailArmATR);
   PrintFormat("  RISK_PARITY: manualMaxLot=%.2f | commissionRT=%.2fbps | maxNotional=%.1f%%eq | adaptiveMargin=%s freeSafety=%.1f%% | maxNewMargin=%.1f%%eq | maxAccountMargin=%.1f%%eq",
               InpMaxLot,EffectiveCommissionRoundTurnBps(),InpMaxNotionalPctEquity,InpAdaptiveMarginLot?"ON":"OFF",InpMarginSafetyPct,InpMaxNewTradeMarginPct,InpMaxAccountMarginPct);
   Print("  STRICT: LAB046 dual gate + frozen signal ATR + continuous Binance-price confirm + ExitZ0.75.");
   Print("  IMPORTANT: LAB046-049 statistical validation is BTCUSDT only; extra configured symbols are algorithmic extrapolation.");
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   for(int i = 0; i < g_symCount; i++)
      if(g_sym[i].atrHandle != INVALID_HANDLE) IndicatorRelease(g_sym[i].atrHandle);
   if(g_csv != INVALID_HANDLE) { FileFlush(g_csv); FileClose(g_csv); }
   if(g_execCsv != INVALID_HANDLE) { FileFlush(g_execCsv); FileClose(g_execCsv); }
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
//+------------------------------------------------------------------+
//| STRICT LAB046-049 Binance reference helpers                      |
//+------------------------------------------------------------------+
string CleanJsonToken(string x)
  {
   StringReplace(x,"\"","");
   StringReplace(x," ","");
   StringReplace(x,"\r","");
   StringReplace(x,"\n","");
   return x;
  }

bool ParseKlineBody(const string body,long &ot[],double &hh[],double &ll[],double &cc[])
  {
   ArrayResize(ot,0);ArrayResize(hh,0);ArrayResize(ll,0);ArrayResize(cc,0);
   int pos=0,n=StringLen(body);
   while(pos<n)
     {
      int a=StringFind(body,"[",pos);
      if(a<0) break;
      if(a+1<n && StringGetCharacter(body,a+1)==91){pos=a+1;continue;} // outer [[
      int b=StringFind(body,"]",a+1);
      if(b<0) break;
      string row=StringSubstr(body,a+1,b-a-1);
      string f[];
      int nf=StringSplit(row,',',f);
      if(nf>=5)
        {
         string t0=CleanJsonToken(f[0]);
         string th=CleanJsonToken(f[2]);
         string tl=CleanJsonToken(f[3]);
         string tc=CleanJsonToken(f[4]);
         long tm=(long)StringToInteger(t0);
         double h=StringToDouble(th),l=StringToDouble(tl),c=StringToDouble(tc);
         if(tm>0 && h>0.0 && l>0.0 && c>0.0)
           {
            int k=ArraySize(ot);
            ArrayResize(ot,k+1);ArrayResize(hh,k+1);ArrayResize(ll,k+1);ArrayResize(cc,k+1);
            ot[k]=tm;hh[k]=h;ll[k]=l;cc[k]=c;
           }
        }
      pos=b+1;
     }
   return ArraySize(ot)>0;
  }

bool FetchBinanceM5History(const string bin,const long endMs,long &ot[],double &hh[],double &ll[],double &cc[])
  {
   ArrayResize(ot,0);ArrayResize(hh,0);ArrayResize(ll,0);ArrayResize(cc,0);
   long span=(long)LAB_FETCH_BARS*(long)LAB_M5_MS;
   long cursor=endMs-span;
   if(cursor<0) cursor=0;
   for(int page=0;page<8 && cursor<=endMs;page++)
     {
      string url=API_HOST+KLINE_PATH+"?symbol="+bin+"&interval=5m&startTime="+IntegerToString(cursor)
                +"&endTime="+IntegerToString(endMs)+"&limit=1500";
      char post[],result[];string rh="";
      ResetLastError();
      int code=WebRequest("GET",url,"",InpWebTimeoutMs,post,result,rh);
      if(code!=200)
        {
         PrintFormat("STRICT_KLINE_FETCH_FAIL %s page=%d http=%d err=%d",bin,page,code,GetLastError());
         return false;
        }
      string body=CharArrayToString(result,0,WHOLE_ARRAY,CP_UTF8);
      long pt[];double ph[],pl[],pc[];
      if(!ParseKlineBody(body,pt,ph,pl,pc)) return false;
      int got=ArraySize(pt);
      for(int i=0;i<got;i++)
        {
         int k=ArraySize(ot);
         if(k>0 && pt[i]<=ot[k-1]) continue;
         ArrayResize(ot,k+1);ArrayResize(hh,k+1);ArrayResize(ll,k+1);ArrayResize(cc,k+1);
         ot[k]=pt[i];hh[k]=ph[i];ll[k]=pl[i];cc[k]=pc[i];
        }
      if(got<1500) break;
      cursor=pt[got-1]+LAB_M5_MS;
     }
   return ArraySize(ot)>=LAB_VOL_MIN+50;
  }

double Quantile67(double &a[])
  {
   int n=ArraySize(a);
   if(n<=0) return 0.0;
   ArraySort(a);
   double p=(n-1)*0.67;
   int lo=(int)MathFloor(p),hi=(int)MathCeil(p);
   if(lo<0) lo=0;if(hi>=n) hi=n-1;
   if(lo==hi) return a[lo];
   double w=p-lo;
   return a[lo]*(1.0-w)+a[hi]*w;
  }

// Exact LAB046 HIGH_VOL construction from Binance 5m price history.
// Signal decision time = flow source period start + 300s.
// ATR% = latest completed M15 ATR14 / completed signal M5 close.
// q67 uses prior 8640 M5 ATR% observations only (shift 1), min history 2880.
bool BuildStrictSignalMarketState(const int idx,const long sourceMs,
                                  double &signalClose,double &signalAtr,
                                  double &atrPct,double &q67,bool &highVol)
  {
   signalClose=0.0;signalAtr=0.0;atrPct=0.0;q67=0.0;highVol=false;
   long decisionMs=sourceMs+LAB_M5_MS;
   long endMs=decisionMs-1;

   long ot[];double hh[],ll[],cc[];
   if(!FetchBinanceM5History(g_sym[idx].binance,endMs,ot,hh,ll,cc)) return false;
   int n=ArraySize(ot);
   if(n<LAB_VOL_MIN+50) return false;

   int sig=-1;
   for(int i=n-1;i>=0;i--)
     {
      if(ot[i]<=sourceMs){sig=i;break;}
     }
   if(sig<0) return false;
   signalClose=cc[sig];

   // Aggregate complete Binance M15 bars from M5 history.
   long e15[];double h15[],l15[],c15[];
   long curBucket=-1;double gh=0.0,gl=0.0,gc=0.0;int gcnt=0;
   for(int i=0;i<n;i++)
     {
      long bucket=ot[i]/LAB_M15_MS;
      if(curBucket<0){curBucket=bucket;gh=hh[i];gl=ll[i];gc=cc[i];gcnt=1;}
      else if(bucket==curBucket)
        {
         if(hh[i]>gh) gh=hh[i];
         if(ll[i]<gl) gl=ll[i];
         gc=cc[i];gcnt++;
        }
      else
        {
         if(gcnt==3)
           {
            int k=ArraySize(e15);
            ArrayResize(e15,k+1);ArrayResize(h15,k+1);ArrayResize(l15,k+1);ArrayResize(c15,k+1);
            e15[k]=(curBucket+1)*LAB_M15_MS;h15[k]=gh;l15[k]=gl;c15[k]=gc;
           }
         curBucket=bucket;gh=hh[i];gl=ll[i];gc=cc[i];gcnt=1;
        }
     }
   if(gcnt==3)
     {
      int k=ArraySize(e15);
      ArrayResize(e15,k+1);ArrayResize(h15,k+1);ArrayResize(l15,k+1);ArrayResize(c15,k+1);
      e15[k]=(curBucket+1)*LAB_M15_MS;h15[k]=gh;l15[k]=gl;c15[k]=gc;
     }

   int m=ArraySize(e15);
   if(m<20) return false;
   double atr15[];ArrayResize(atr15,m);
   for(int i=0;i<m;i++) atr15[i]=0.0;
   double tr[];ArrayResize(tr,m);
   for(int i=0;i<m;i++)
     {
      double pc=(i>0)?c15[i-1]:c15[i];
      tr[i]=MathMax(h15[i]-l15[i],MathMax(MathAbs(h15[i]-pc),MathAbs(l15[i]-pc)));
      if(i>=13)
        {
         double sm=0.0;
         for(int j=i-13;j<=i;j++) sm+=tr[j];
         atr15[i]=sm/14.0;
        }
     }

   double ap[];ArrayResize(ap,n);
   int mi=0,last=-1;
   for(int j=0;j<n;j++)
     {
      long avail=ot[j]+LAB_M5_MS;
      while(mi<m && e15[mi]<=avail){last=mi;mi++;}
      if(last>=0 && atr15[last]>0.0 && cc[j]>0.0) ap[j]=atr15[last]/cc[j];
      else ap[j]=0.0;
     }

   // signal ATR mapped from latest completed M15 at signal clock
   int smi=-1;
   for(int i=m-1;i>=0;i--) if(e15[i]<=decisionMs){smi=i;break;}
   if(smi<0 || atr15[smi]<=0.0) return false;
   signalAtr=atr15[smi];
   atrPct=signalAtr/signalClose;

   int from=MathMax(0,sig-LAB_VOL_WIN);
   double hist[];ArrayResize(hist,0);
   for(int i=from;i<sig;i++)
     {
      if(ap[i]>0.0 && MathIsValidNumber(ap[i]))
        {
         int k=ArraySize(hist);ArrayResize(hist,k+1);hist[k]=ap[i];
        }
     }
   if(ArraySize(hist)<LAB_VOL_MIN)
     {
      // LAB046: UNKNOWN is not HIGH_VOL.
      q67=0.0;highVol=false;
      return true;
     }
   q67=Quantile67(hist);
   highVol=(q67>0.0 && atrPct>=q67);
   return true;
  }

bool FetchStrictRefPrice(const int idx,double &px,long &tm)
  {
   px=0.0;tm=0;
   string url=API_HOST+TICKER_PATH+"?symbol="+g_sym[idx].binance;
   char post[],result[];string rh="";
   int timeout=MathMin(InpWebTimeoutMs,1000);
   ResetLastError();
   int code=WebRequest("GET",url,"",timeout,post,result,rh);
   if(code!=200) return false;
   string body=CharArrayToString(result,0,WHOLE_ARRAY,CP_UTF8);
   int e=-1,et=-1;
   px=JsonNum(body,0,"price",e);
   double td=JsonNum(body,0,"time",et);
   if(td>0.0) tm=(long)td; else tm=(long)TimeGMT()*1000;
   if(px<=0.0) return false;
   g_sym[idx].refLastPrice=px;g_sym[idx].refLastPriceMs=tm;
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
   if(code!=200){g_sym[idx].err=StringFormat("HTTP %d",code);return false;}

   string body=CharArrayToString(result,0,WHOLE_ARRAY,CP_UTF8);
   if(StringLen(body)<20){g_sym[idx].err="порожня відповідь";return false;}

   double rr[];ArrayResize(rr,MAX_POINTS);
   long tsms[];ArrayResize(tsms,MAX_POINTS);
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
         rr[cnt]=r;tsms[cnt]=(et>0)?(long)td:0;cnt++;
        }
      pos=e2;
     }
   if(cnt<80){g_sym[idx].err=StringFormat("лише %d точок",cnt);return false;}

   int win=(InpZWindowHours*3600)/BIN_STEP_S;
   if(win<10) win=10;
   int from=cnt-win;if(from<0) from=0;
   double sum=0.0,sum2=0.0;int n=0;
   for(int i=from;i<cnt;i++){sum+=rr[i];sum2+=rr[i]*rr[i];n++;}
   double mean=sum/n,var=sum2/n-mean*mean;
   if(n<10 || var<=0.0){g_sym[idx].err="invalid z window";return false;}
   double sd=MathSqrt(var);
   if(sd<1e-12){g_sym[idx].err="sd=0";return false;}
   double zNew=(rr[cnt-1]-mean)/sd;

   // Exact RAPID_REPEAT_30 from completed M5 crowd stream, independent of trade reachability.
   double zhist[];ArrayResize(zhist,cnt);
   for(int i=0;i<cnt;i++) zhist[i]=0.0;
   for(int i=win-1;i<cnt;i++)
     {
      double sm=0.0,sm2=0.0;
      for(int j=i-win+1;j<=i;j++){sm+=rr[j];sm2+=rr[j]*rr[j];}
      double mu=sm/win,v=sm2/win-mu*mu;
      if(v>0.0) zhist[i]=(rr[i]-mu)/MathSqrt(v);
     }
   bool rapid=false;double gap=-1.0;
   int sign=(zNew>=1.0)?1:((zNew<=-1.0)?-1:0);
   if(sign!=0)
     {
      for(int i=cnt-2;i>=win-1;i--)
        {
         bool same=(sign>0 && zhist[i]>=1.0) || (sign<0 && zhist[i]<=-1.0);
         if(same)
           {
            gap=(double)(tsms[cnt-1]-tsms[i])/60000.0;
            rapid=(gap<=30.0);
            break;
           }
        }
     }

   int win40=(40*3600)/BIN_STEP_S;if(win40>cnt) win40=cnt;
   double s40=0.0,s40b=0.0;int n40=0;
   for(int i=cnt-win40;i<cnt;i++) if(i>=0){s40+=rr[i];s40b+=rr[i]*rr[i];n40++;}
   double z40=0.0;
   if(n40>=20)
     {
      double m40=s40/n40,v40=s40b/n40-m40*m40;
      if(v40>0.0){double sd40=MathSqrt(v40);if(sd40>1e-12) z40=(rr[cnt-1]-m40)/sd40;}
     }

   bool wasActive=((g_sym[idx].z>=InpZThreshold)||(g_sym[idx].z<=-InpZThreshold)) && g_sym[idx].ok;
   bool nowActive=((zNew>=InpZThreshold)||(zNew<=-InpZThreshold));
   if(nowActive && !wasActive){g_sym[idx].sigSince=TimeCurrent();g_sym[idx].durBars=0;GVWrite(GVKey("SIG_"+g_sym[idx].broker),(double)g_sym[idx].sigSince);}
   if(!nowActive){g_sym[idx].sigSince=0;g_sym[idx].durBars=0;GVWrite(GVKey("SIG_"+g_sym[idx].broker),0.0);}
   if(nowActive && wasActive)
     {
      if(g_sym[idx].sigSince<=0) g_sym[idx].sigSince=TimeCurrent();
      long secs=(long)(TimeCurrent()-g_sym[idx].sigSince);
      int bb=(int)(secs/PeriodSeconds(PERIOD_M15));
      g_sym[idx].durBars=(bb>40)?40:((bb<0)?0:bb);
     }

   g_sym[idx].ratio=rr[cnt-1];g_sym[idx].mean=mean;g_sym[idx].sd=sd;
   g_sym[idx].z40=z40;g_sym[idx].z=zNew;
   g_sym[idx].rapidRepeat30=rapid;g_sym[idx].priorSameExtremeGapMin=gap;
   g_sym[idx].ok=true;g_sym[idx].err="";
   g_sym[idx].lastFetch=TimeCurrent();g_sym[idx].sourceTimeMs=tsms[cnt-1];
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
int CountExposure(int &nBuy,int &nSell)
  {
   nBuy=0;nSell=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
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

double EffectiveCommissionRoundTurnBps()
  {
   if(!InpAutoBrokerCostProfile) return MathMax(0.0,InpCommissionRoundTurnBps);
   string profile=AccountInfoString(ACCOUNT_COMPANY)+" "+AccountInfoString(ACCOUNT_SERVER);
   StringToUpper(profile);
   if(StringFind(profile,"FTMO")>=0) return 6.50;
   if(StringFind(profile,"GETLEVERAGED")>=0 || StringFind(profile,"GET LEVERAGED")>=0) return 0.0;
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

// Raw risk lot BEFORE broker/manual caps. OrderCalcProfit returns P/L in account currency,
// so different contract sizes (FTMO vs GetLeveraged) are normalized automatically.
double RawLotForRisk(const string sym,const int side,const double entry,const double stop,const double weight,
                     double &lossPerLot,double &commissionPerLot,double &riskCash)
  {
   lossPerLot=0.0; commissionPerLot=0.0; riskCash=0.0;
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
   lossPerLot=MathAbs(pnl);
   if(lossPerLot<=0.0) return 0.0;

   double contract=SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE);
   double bps=EffectiveCommissionRoundTurnBps();
   if(bps>0.0 && contract>0.0)
      commissionPerLot=entry*contract*(bps/10000.0);

   double totalLossPerLot=lossPerLot+commissionPerLot;
   if(totalLossPerLot<=0.0) return 0.0;
   riskCash=AccountInfoDouble(ACCOUNT_EQUITY)*(InpRiskPct/100.0)*MathMax(weight,0.0);
   if(riskCash<=0.0) return 0.0;
   return riskCash/totalLossPerLot;
  }

// Estimate the economic notional of 1.0 lot in ACCOUNT currency.
// For linear CFDs, a +100% price move on one BUY lot equals approximately one full notional.
// OrderCalcProfit also handles broker contract size and quote->account currency conversion.
double NotionalPerLotAccount(const string sym,const double entry)
  {
   if(entry<=0.0) return 0.0;
   double pnl=0.0;
   ResetLastError();
   if(OrderCalcProfit(ORDER_TYPE_BUY,sym,1.0,entry,entry*2.0,pnl) && MathAbs(pnl)>0.0)
      return MathAbs(pnl);

   // Fallback for standard USD/USDT quoted linear CFDs.
   double contract=SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract<=0.0) return 0.0;
   return entry*contract;
  }

// Broker-neutral economic-exposure cap. This is intentionally independent of leverage/margin.
// Example at SOL=$111 and 100k equity with 15% cap:
//   contract=1   => ~135 lots; contract=100 => ~1.35 lots.
double ClampLotToNotional(const string sym,const double desiredLot,const double entry,
                          double &notionalPerLot,double &desiredNotional,double &actualNotional,bool &clamped)
  {
   notionalPerLot=0.0; desiredNotional=0.0; actualNotional=0.0; clamped=false;
   if(desiredLot<=0.0 || entry<=0.0) return 0.0;
   if(InpMaxNotionalPctEquity<=0.0) return desiredLot;

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
   double capCash=equity*MathMax(0.0,InpMaxNotionalPctEquity)/100.0;
   if(capCash<=0.0) return 0.0;
   if(desiredNotional<=capCash)
     {
      actualNotional=desiredNotional;
      return desiredLot;
     }

   BrokerSpec sp; if(!GetBrokerSpec(sym,sp)) return 0.0;
   double capped=capCash/notionalPerLot;
   capped=MathMin(capped,desiredLot);
   capped=MathFloor((capped+1e-12)/sp.volumeStep)*sp.volumeStep;
   if(capped<sp.volumeMin)
     {
      PrintFormat("NOTIONAL_BLOCK %s desiredLot=%.4f desiredNotional=%.2f cap=%.2f minLot=%.4f notionalPerLot=%.2f",
                  sym,desiredLot,desiredNotional,capCash,sp.volumeMin,notionalPerLot);
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

double CapLotToBroker(const string sym,const double rawLot,
                      bool &brokerClamped,bool &manualClamped)
  {
   brokerClamped=false; manualClamped=false;
   if(rawLot<=0.0) return 0.0;
   BrokerSpec sp; if(!GetBrokerSpec(sym,sp)) return 0.0;
   double capped=rawLot;
   if(capped>sp.volumeMax){capped=sp.volumeMax;brokerClamped=true;}
   if(InpMaxLot>0.0 && capped>InpMaxLot){capped=InpMaxLot;manualClamped=true;}
   capped=MathFloor((capped+1e-12)/sp.volumeStep)*sp.volumeStep;
   if(capped<sp.volumeMin) return 0.0;
   int prec=0;double t=sp.volumeStep;
   while(t<1.0 && prec<8){t*=10.0;prec++;}
   return NormalizeDouble(capped,prec);
  }

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
      // Risk parity without a margin estimate is unsafe when hard exposure caps are enabled.
      if(InpMaxNewTradeMarginPct>0.0 || InpMaxAccountMarginPct>0.0)
        {
         PrintFormat("MARGIN_CALC_BLOCK %s desiredLot=%.4f error=%d",sym,desiredLot,GetLastError());
         return 0.0;
        }
      return desiredLot;
     }

   // Three independent budgets. The tightest one wins:
   // 1) free-margin safety, 2) one-trade margin/equity cap, 3) projected total margin/equity cap.
   double freePct=MathMax(0.0,MathMin(100.0,InpMarginSafetyPct));
   double freeBudget=freeMargin*freePct/100.0;
   double tradeBudget=freeBudget;
   if(InpMaxNewTradeMarginPct>0.0)
      tradeBudget=equity*MathMax(0.0,InpMaxNewTradeMarginPct)/100.0;

   double totalHeadroom=freeBudget;
   if(InpMaxAccountMarginPct>0.0)
     {
      double totalCap=equity*MathMax(0.0,InpMaxAccountMarginPct)/100.0;
      totalHeadroom=MathMax(0.0,totalCap-currentMargin);
     }

   double budget=freeBudget;
   if(InpMaxNewTradeMarginPct>0.0) budget=MathMin(budget,tradeBudget);
   if(InpMaxAccountMarginPct>0.0)  budget=MathMin(budget,totalHeadroom);

   if(needDesired<=budget){needActual=needDesired;return desiredLot;}
   if(!InpAdaptiveMarginLot || budget<=0.0)
     {
      PrintFormat("MARGIN_CAP_BLOCK %s desiredLot=%.4f need=%.2f budget=%.2f eq=%.2f margin=%.2f free=%.2f",
                  sym,desiredLot,needDesired,budget,equity,currentMargin,freeMargin);
      return 0.0;
     }

   if(InpVerbose)
      PrintFormat("MARGIN_CAP %s desiredLot=%.4f need=%.2f budget=%.2f freeBudget=%.2f tradeBudget=%.2f totalHeadroom=%.2f eq=%.2f currentMargin=%.2f",
                  sym,desiredLot,needDesired,budget,freeBudget,tradeBudget,totalHeadroom,equity,currentMargin);

   BrokerSpec sp; if(!GetBrokerSpec(sym,sp)) return 0.0;
   long minUnits=(long)MathCeil((sp.volumeMin-1e-12)/sp.volumeStep);
   long maxUnits=(long)MathFloor((desiredLot+1e-12)/sp.volumeStep);
   if(maxUnits<minUnits) return 0.0;
   long lo=minUnits,hi=maxUnits,best=0; double bestNeed=0.0;
   while(lo<=hi)
     {
      long mid=lo+(hi-lo)/2;
      double test=(double)mid*sp.volumeStep;
      double nm=0.0;
      if(!OrderCalcMargin(mt,sym,test,price,nm) || nm<=0.0){hi=mid-1;continue;}
      if(nm<=budget){best=mid;bestNeed=nm;lo=mid+1;} else hi=mid-1;
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
   clamped=(actual+1e-12<desiredLot); needActual=bestNeed;
   return actual;
  }

// Unified broker-neutral lot preparation used by BOTH confirm and legacy entry paths.
double PrepareRiskLot(const string sym,const int side,const double entry,const double stop,const double weight,
                      double &rawLot,double &brokerLot,double &actualRiskPct)
  {
   double lossPerLot=0.0,commPerLot=0.0,riskCash=0.0;
   rawLot=RawLotForRisk(sym,side,entry,stop,weight,lossPerLot,commPerLot,riskCash);
   brokerLot=0.0; actualRiskPct=0.0;
   if(rawLot<=0.0) return 0.0;

   bool brokerClamped=false,manualClamped=false;
   brokerLot=CapLotToBroker(sym,rawLot,brokerClamped,manualClamped);
   if(brokerLot<=0.0)
     {
      PrintFormat("VOLUME_SKIP %s raw=%.4f brokerMax=%.4f manualMax=%.4f",
                  sym,rawLot,SymbolInfoDouble(sym,SYMBOL_VOLUME_MAX),InpMaxLot);
      return 0.0;
     }
   double volFrac=brokerLot/rawLot;
   if(brokerClamped || manualClamped)
      PrintFormat("VOLUME_CLAMP %s raw=%.4f brokerLot=%.4f frac=%.3f brokerMax=%.4f manualMax=%.4f contract=%.4f baseUnits=%.4f",
                  sym,rawLot,brokerLot,volFrac,SymbolInfoDouble(sym,SYMBOL_VOLUME_MAX),InpMaxLot,
                  SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE),brokerLot*SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE));
   double minVolFrac=MathMax(0.0,MathMin(1.0,InpMinVolumeLotFrac));
   if(minVolFrac>0.0 && brokerLot+1e-12<rawLot*minVolFrac)
     {
      PrintFormat("VOLUME_UNDERSIZE_SKIP %s raw=%.4f brokerLot=%.4f frac=%.3f minFrac=%.3f",sym,rawLot,brokerLot,volFrac,minVolFrac);
      return 0.0;
     }

   // First cap the same ECONOMIC exposure on every broker, regardless of contract size/leverage.
   double notionalPerLot=0.0,desiredNotional=0.0,actualNotional=0.0; bool notionalClamped=false;
   double notionalLot=ClampLotToNotional(sym,brokerLot,entry,notionalPerLot,desiredNotional,actualNotional,notionalClamped);
   if(notionalLot<=0.0)
     {
      PrintFormat("NOTIONAL_BLOCK_FINAL %s raw=%.4f brokerLot=%.4f maxNotional=%.1f%%eq",
                  sym,rawLot,brokerLot,InpMaxNotionalPctEquity);
      return 0.0;
     }

   ENUM_ORDER_TYPE mt=(side>0)?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   double needDesired=0.0,needActual=0.0,freeMargin=0.0; bool marginClamped=false;
   double lot=ClampLotToMargin(sym,mt,notionalLot,entry,needDesired,needActual,freeMargin,marginClamped);
   if(lot<=0.0)
     {
      PrintFormat("MARGIN_BLOCK %s raw=%.4f brokerLot=%.4f notionalLot=%.4f need=%.2f free=%.2f freeSafety=%.1f%% maxNew=%.1f%%eq maxAccount=%.1f%%eq",
                  sym,rawLot,brokerLot,notionalLot,needDesired,freeMargin,InpMarginSafetyPct,InpMaxNewTradeMarginPct,InpMaxAccountMarginPct);
      return 0.0;
     }
   if(marginClamped)
      PrintFormat("MARGIN_CLAMP %s raw=%.4f brokerLot=%.4f notionalLot=%.4f actual=%.4f need=%.2f->%.2f free=%.2f",
                  sym,rawLot,brokerLot,notionalLot,lot,needDesired,needActual,freeMargin);

   double actualRiskCash=(lossPerLot+commPerLot)*lot;
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   actualRiskPct=(eq>0.0)?actualRiskCash/eq*100.0:0.0;
   double contract=SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE);
   double finalNotionalPerLot=NotionalPerLotAccount(sym,entry);
   double finalNotional=(finalNotionalPerLot>0.0)?lot*finalNotionalPerLot:0.0;
   double finalNotionalPct=(eq>0.0)?finalNotional/eq*100.0:0.0;
   PrintFormat("RISK_LOT %s raw=%.4f broker=%.4f notionalLot=%.4f actual=%.4f contract=%.4f baseUnits=%.4f notional=%.2f (%.2f%%eq) stopLoss/lot=%.2f comm/lot=%.2f reqRisk=%.2f actualRisk=%.3f%% costRT=%.2fbps",
               sym,rawLot,brokerLot,notionalLot,lot,contract,lot*contract,finalNotional,finalNotionalPct,lossPerLot,commPerLot,riskCash,actualRiskPct,EffectiveCommissionRoundTurnBps());
   return lot;
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
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      string sym=PositionGetString(POSITION_SYMBOL);
      bool b=g_trade.PositionClose(tk);uint rc=g_trade.ResultRetcode();
      LogExec("FORCE_CLOSE",sym,tk,"",0,0,0,0,rc,why);
      if(!(b && RetcodeAccepted(rc))) PrintFormat("FORCE_CLOSE %s fail ret=%u %s",sym,rc,g_trade.ResultRetcodeDescription());
     }
  }

void ExpireFallbackPending()
  {
   if(InpOrderValidHrs<=0) return;
   datetime now=TimeCurrent();
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i);if(!OrderSelect(tk)) continue;
      if(OrderGetInteger(ORDER_MAGIC)!=InpMagic) continue;
      long ot=OrderGetInteger(ORDER_TYPE);
      if(ot!=ORDER_TYPE_BUY_LIMIT && ot!=ORDER_TYPE_SELL_LIMIT) continue;
      datetime setup=(datetime)OrderGetInteger(ORDER_TIME_SETUP);
      if(setup<=0 || now-setup<(datetime)(InpOrderValidHrs*3600)) continue;
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
      if(StringFind(cm,"CF191")!=0 && StringFind(cm,"CF162")!=0) continue; // support v191 + legacy v162 pending tags
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
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      string s=PositionGetString(POSITION_SYMBOL);
      int si=SymIndex(s);if(si<0) continue;
      long ptype=PositionGetInteger(POSITION_TYPE);
      int side=(ptype==POSITION_TYPE_BUY)?1:-1;
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      ulong posId=PositionIdSelected();
      double op=PositionGetDouble(POSITION_PRICE_OPEN);
      double csl=PositionGetDouble(POSITION_SL);
      double tp=PositionGetDouble(POSITION_TP);
      MqlTick q;if(!SymbolInfoTick(s,q)) continue;
      double closePx=(ptype==POSITION_TYPE_BUY)?q.bid:q.ask;
      if(op<=0.0 || closePx<=0.0) continue;
      double baseAtr=PositionBaseAtr(posId,s,op,csl);

      // STRICT LAB geometry is driven by Binance reference excursion, not broker CFD excursion.
      double refPx=0.0;long refMs=0;
      bool refOk=FetchStrictRefPrice(si,refPx,refMs);
      double refEntry=GVRead(GVPosKey(posId,"REF_ENTRY"),0.0);
      if(refEntry<=0.0 && refOk){refEntry=refPx;GVWrite(GVPosKey(posId,"REF_ENTRY"),refEntry);}
      double fav=0.0;
      if(refOk && refEntry>0.0 && baseAtr>0.0)
        {
         string kp=GVPosKey(posId,"REF_PEAK");
         double refPeak=GVRead(kp,refEntry);
         if(side>0){if(refPx>refPeak) refPeak=refPx;fav=(refPeak-refEntry)/baseAtr;}
         else      {if(refPx<refPeak) refPeak=refPx;fav=(refEntry-refPeak)/baseAtr;}
         GVWrite(kp,refPeak);

         // Frozen BE: arm +0.50 ATR, lock +0.15 ATR.
         if(InpBreakEvenAtATR>0.0 && InpBreakEvenLock>0.0 && fav>=InpBreakEvenAtATR)
           {
            double lvl=op+side*InpBreakEvenLock*baseAtr;
            lvl=NormalizePriceTick(s,lvl,(side>0)?-1:+1);
            bool better=(side>0)?(csl<=0.0 || lvl>csl):(csl<=0.0 || lvl<csl);
            double tick=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE);if(tick<=0.0) tick=SymbolInfoDouble(s,SYMBOL_POINT);
            if(csl>0.0 && MathAbs(lvl-csl)<tick*0.51) better=false;
            double md=MinTradeDistance(s,true);
            bool dist=(side>0)?(q.bid-lvl>=md):(lvl-q.ask>=md);
            if(better && dist)
              {
               g_trade.SetTypeFillingBySymbol(s);
               bool b=g_trade.PositionModify(tk,lvl,tp);uint rc=g_trade.ResultRetcode();
               double actual=0.0;bool verified=(b && RetcodeAccepted(rc) && VerifyPositionSL(tk,lvl,actual));
               LogExec("BREAKEVEN",s,tk,(side>0)?"BUY":"SELL",0,lvl,0,actual,rc,
                       verified?StringFormat("OK ref=%.8f fav=%.3f",refPx,fav):"FAIL");
               if(verified){c_be++;csl=actual;}
              }
           }

         // LAB048/049 family: frozen 0.50 ATR gap; arm is configured (default BALANCED=3.50).
         if(InpTrailOn && InpTrailATR>0.0 && fav>=InpTrailArmATR)
           {
            double protectedMove=(fav-InpTrailATR)*baseAtr;
            double lvl=op+side*protectedMove;
            lvl=NormalizePriceTick(s,lvl,(side>0)?-1:+1);
            bool better=(side>0)?(csl<=0.0 || lvl>csl):(csl<=0.0 || lvl<csl);
            double tick=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE);if(tick<=0.0) tick=SymbolInfoDouble(s,SYMBOL_POINT);
            if(csl>0.0 && MathAbs(lvl-csl)<tick*0.51) better=false;
            double md=MinTradeDistance(s,true);
            bool dist=(side>0)?(q.bid-lvl>=md):(lvl-q.ask>=md);
            if(better && dist)
              {
               g_trade.SetTypeFillingBySymbol(s);
               bool b=g_trade.PositionModify(tk,lvl,tp);uint rc=g_trade.ResultRetcode();
               double actual=0.0;bool verified=(b && RetcodeAccepted(rc) && VerifyPositionSL(tk,lvl,actual));
               LogExec("TRAIL",s,tk,(side>0)?"BUY":"SELL",0,lvl,0,actual,rc,
                       verified?StringFormat("OK ref=%.8f fav=%.3f arm=%.2f",refPx,fav,InpTrailArmATR):"FAIL");
               if(verified){c_trail++;csl=actual;}
              }
           }
        }

      // Frozen ExitZ=0.75: use causal latest Binance crowd state.
      bool closed=false;
      if(InpExitZ>0.0 && IsFeedFresh(si))
        {
         double z=g_sym[si].z;
         bool hit=(side>0)?(z>=InpExitZ):(z<=-InpExitZ);
         if(hit)
           {
            bool b=g_trade.PositionClose(tk);uint rc=g_trade.ResultRetcode();
            LogExec("SIGNAL_EXIT",s,tk,(side>0)?"BUY":"SELL",0,0,0,0,rc,StringFormat("z=%+.3f",z));
            if(b && RetcodeAccepted(rc)){c_sigexit++;closed=true;}
           }
        }
      if(closed) continue;

      // Frozen max hold H6 from actual execution time.
      if(TimeCurrent()-opened>=(datetime)(InpHoldHours*3600))
        {
         bool b=g_trade.PositionClose(tk);uint rc=g_trade.ResultRetcode();
         LogExec("TIME_EXIT",s,tk,(side>0)?"BUY":"SELL",0,0,0,0,rc,"hold");
         if(b && RetcodeAccepted(rc)) c_timeexit++;
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
   TimeToStruct(TimeGMT(),dt); // STRICT LAB daily cap is UTC-day based
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

//+------------------------------------------------------------------+
void TryEnter(const int idx)
  {
   if(g_haltDay || g_haltAll) return;
   if(!IsFeedFresh(idx)) return;

   string sym=g_sym[idx].broker;
   double z=g_sym[idx].z;

   // A. Active strict confirmation is evaluated EVERY scheduler pass (~1s),
   // not only on a new broker M5 bar.
   if(g_sym[idx].confActive)
     {
      int side=g_sym[idx].confSide;
      double sigPx=g_sym[idx].confSignalPrice;
      double sigAtr=g_sym[idx].confAtr;
      long decisionSec=(long)g_sym[idx].confSignalTime;
      long ageSec=(long)TimeGMT()-decisionSec;

      if(ageSec>2700)
        {
         g_sym[idx].confActive=false;
         LogExec("STRICT_CONFIRM_TIMEOUT",sym,0,(side>0)?"BUY":"SELL",0,0,0,0,0,
                 StringFormat("signal=%I64d source=%I64d age=%I64d",decisionSec,g_sym[idx].confSourceTimeMs,ageSec));
         return;
        }

      double refPx=0.0;long refMs=0;
      if(!FetchStrictRefPrice(idx,refPx,refMs)) return;

      double adverse=(side<0)?((refPx-sigPx)/sigAtr):((sigPx-refPx)/sigAtr);
      if(adverse>g_sym[idx].confMaxAdvATR) g_sym[idx].confMaxAdvATR=adverse;
      if(g_sym[idx].confMaxAdvATR>InpConfirmMaxAdverseATR)
        {
         g_sym[idx].confActive=false;
         LogExec("STRICT_CONFIRM_CANCEL_ADVERSE",sym,0,(side>0)?"BUY":"SELL",0,0,0,0,0,
                 StringFormat("signal=%I64d source=%I64d adv=%.3f",decisionSec,g_sym[idx].confSourceTimeMs,g_sym[idx].confMaxAdvATR));
         return;
        }

      double target=sigPx+side*InpConfirmATR*sigAtr;
      bool confirmed=(side>0)?(refPx>=target):(refPx<=target);
      if(!confirmed) return;

      // Exact v191d confirmation consistency: only opposite ExitZ contradiction cancels.
      bool contradict=(side>0)?(z>=InpExitZ):(z<=-InpExitZ);
      if(contradict)
        {
         g_sym[idx].confActive=false;
         LogExec("STRICT_CONFIRM_CANCEL_Z",sym,0,(side>0)?"BUY":"SELL",0,0,0,0,0,
                 StringFormat("signal=%I64d origZ=%+.3f confirmZ=%+.3f",decisionSec,g_sym[idx].confZ,z));
         return;
        }

      // From here the signal is valid. Any remaining block is execution/risk transport, not signal retuning.
      g_sym[idx].confActive=false;
      if(HasAnyFor(sym)) return;
      int nb,ns;int tot=CountExposure(nb,ns);
      if(tot>=InpMaxPositions){c_maxpos++;return;}
      if(side<0 && ns>=InpMaxPerSide){c_side++;return;}
      if(side>0 && nb>=InpMaxPerSide){c_side++;return;}

      MqlTick q;if(!SymbolInfoTick(sym,q) || q.ask<=0.0 || q.bid<=0.0) return;
      double spr=q.ask-q.bid;
      if(InpMaxSpreadATR>0.0 && (spr<=0.0 || spr>InpMaxSpreadATR*sigAtr))
        {
         c_spread++;
         LogExec("STRICT_EXEC_SPREAD_SKIP",sym,0,(side>0)?"BUY":"SELL",0,0,0,0,0,
                 StringFormat("spread=%.8f signalATR=%.8f",spr,sigAtr));
         return;
        }

      double entry=(side<0)?q.bid:q.ask;
      double stop=entry-side*InpStopATR*sigAtr;
      entry=NormalizePriceTick(sym,entry,(side<0)?+1:-1);
      stop =NormalizePriceTick(sym,stop,(side<0)?+1:-1);
      if(MathAbs(stop-entry)<MinTradeDistance(sym,false)) return;

      double rawLot=0.0,brokerLot=0.0,actualRiskPct=0.0;
      double lot=PrepareRiskLot(sym,side,entry,stop,1.0,rawLot,brokerLot,actualRiskPct);
      if(lot<=0.0){c_lot++;return;}

      string sig=StringFormat("CF191%s%I64d",(side<0)?"S":"B",decisionSec);
      g_trade.SetTypeFillingBySymbol(sym);
      c_sent++;
      bool basic=(side<0)?g_trade.Sell(lot,sym,0.0,stop,0.0,sig)
                         :g_trade.Buy (lot,sym,0.0,stop,0.0,sig);
      uint rc=g_trade.ResultRetcode();ulong ord=g_trade.ResultOrder();
      bool ok=basic && RetcodeAccepted(rc) && ord>0;
      if(!ok)
        {
         c_fail++;
         LogExec("STRICT_ORDER_SEND",sym,ord,(side>0)?"BUY":"SELL",entry,stop,0,0,rc,
                 StringFormat("FAIL signal=%I64d source=%I64d",decisionSec,g_sym[idx].confSourceTimeMs));
         return;
        }

      RegisterEntry(idx,refPx,sigAtr); // LAB pause anchor = reference entry, frozen signal ATR.
      GVWrite(GVOrderKey(ord,"ATR"),sigAtr);
      GVWrite(GVOrderKey(ord,"REF_ENTRY"),refPx);
      GVWrite(GVOrderKey(ord,"SIG_SOURCE_MS"),(double)g_sym[idx].confSourceTimeMs);
      GVWrite(GVOrderKey(ord,"SIG_DECISION"),(double)decisionSec);

      LogExec("STRICT_ORDER_SEND",sym,ord,(side>0)?"BUY":"SELL",entry,stop,0,0,rc,
              StringFormat("OK signal=%I64d source=%I64d refEntry=%.8f signalATR=%.8f origZ=%+.3f confirmZ=%+.3f adv=%.3f q67=%.8f atrPct=%.8f",
                           decisionSec,g_sym[idx].confSourceTimeMs,refPx,sigAtr,g_sym[idx].confZ,z,
                           g_sym[idx].confMaxAdvATR,g_sym[idx].confVolQ67,g_sym[idx].confAtrPct));
      return;
     }

   // B. New signal state is keyed by the completed Binance flow source point, not broker M5.
   long sourceMs=g_sym[idx].sourceTimeMs;
   if(sourceMs<=0 || sourceMs==g_sym[idx].lastSignalSourceMs) return;
   long decisionSec=sourceMs/1000+300; // LAB dt5 availability clock
   long nowUtc=(long)TimeGMT();
   if(nowUtc<decisionSec) return;

   int side=0;
   if(z>=InpZThreshold) side=-1;
   else if(z<=-InpZThreshold) side=1;

   // Every completed source point is processed exactly once.
   if(side==0){g_sym[idx].lastSignalSourceMs=sourceMs;c_thr++;return;}

   // LAB046 gate 1: same-sign previous completed M5 extreme <=30m.
   if(g_sym[idx].rapidRepeat30)
     {
      g_sym[idx].lastSignalSourceMs=sourceMs;
      LogExec("STRICT_SKIP_RAPID30",sym,0,(side>0)?"BUY":"SELL",0,0,0,0,0,
              StringFormat("signal=%I64d source=%I64d gap=%.1fm z=%+.3f",decisionSec,sourceMs,g_sym[idx].priorSameExtremeGapMin,z));
      return;
     }

   // Exact Binance signal close + completed M15 ATR14 + lagged 30d q67.
   double sigClose=0.0,sigAtr=0.0,atrPct=0.0,q67=0.0;bool highVol=false;
   if(!BuildStrictSignalMarketState(idx,sourceMs,sigClose,sigAtr,atrPct,q67,highVol))
     {
      LogExec("STRICT_STATE_RETRY",sym,0,(side>0)?"BUY":"SELL",0,0,0,0,0,
              StringFormat("signal=%I64d source=%I64d",decisionSec,sourceMs));
      return; // retry same source next scheduler pass
     }

   // LAB046 gate 2: HIGH_VOL; UNKNOWN is not HIGH_VOL.
   if(highVol)
     {
      g_sym[idx].lastSignalSourceMs=sourceMs;
      LogExec("STRICT_SKIP_HIGHVOL",sym,0,(side>0)?"BUY":"SELL",0,0,0,0,0,
              StringFormat("signal=%I64d atrPct=%.8f q67=%.8f z=%+.3f",decisionSec,atrPct,q67,z));
      return;
     }

   // Frozen freshness <=45m measured from LAB decision time.
   if(nowUtc-decisionSec>2700)
     {
      g_sym[idx].lastSignalSourceMs=sourceMs;
      LogExec("STRICT_SKIP_STALE_SIGNAL",sym,0,(side>0)?"BUY":"SELL",0,0,0,0,0,
              StringFormat("signal=%I64d age=%I64d",decisionSec,nowUtc-decisionSec));
      return;
     }

   // Frozen pause=1 signal ATR and max 3 trades / UTC day.
   if(!CanEnterByPauseAndDay(idx,sigClose)){g_sym[idx].lastSignalSourceMs=sourceMs;return;}
   if(HasAnyFor(sym)){g_sym[idx].lastSignalSourceMs=sourceMs;return;}
   int nb,ns;int tot=CountExposure(nb,ns);
   if(tot>=InpMaxPositions){g_sym[idx].lastSignalSourceMs=sourceMs;c_maxpos++;return;}
   if(side<0 && ns>=InpMaxPerSide){g_sym[idx].lastSignalSourceMs=sourceMs;c_side++;return;}
   if(side>0 && nb>=InpMaxPerSide){g_sym[idx].lastSignalSourceMs=sourceMs;c_side++;return;}

   // Arm the one deployable real-time confirmation thesis from this exact LAB signal state.
   g_sym[idx].confActive=true;
   g_sym[idx].confSide=side;
   g_sym[idx].confSignalPrice=sigClose;
   g_sym[idx].confSignalMid=sigClose;
   g_sym[idx].confAtr=sigAtr;
   g_sym[idx].confZ=z;
   g_sym[idx].confMaxFavATR=0.0;
   g_sym[idx].confMaxAdvATR=0.0;
   g_sym[idx].confSignalTime=(datetime)decisionSec;
   g_sym[idx].confSourceTimeMs=sourceMs;
   g_sym[idx].confVolQ67=q67;
   g_sym[idx].confAtrPct=atrPct;
   g_sym[idx].confHighVol=highVol;
   g_sym[idx].confBarsLeft=InpConfirmMaxBars;
   g_sym[idx].lastSignalSourceMs=sourceMs;

   LogExec("STRICT_CONFIRM_ARM",sym,0,(side>0)?"BUY":"SELL",sigClose,0,0,0,0,
           StringFormat("signal=%I64d source=%I64d z=%+.3f atr=%.8f atrPct=%.8f q67=%.8f rapidGap=%.1f",
                        decisionSec,sourceMs,z,sigAtr,atrPct,q67,g_sym[idx].priorSameExtremeGapMin));
  }

void DrawPanel()
  {
   int nb=0,ns=0;int ex=CountExposure(nb,ns);
   string t=StringFormat("CrowdFade v1.91e SAME-SIDE  z=%.2f  exposure %d/%d%s\n",
                         InpZThreshold,ex,InpMaxPositions,
                         (g_haltAll?"  [STOP EA]":(g_haltDay?"  [DAY HALT]":"")));
   for(int i=0;i<g_symCount;i++)
     {
      bool fresh=IsFeedFresh(i);
      if(!g_sym[i].ok)
        {t+=StringFormat("  %-9s %s\n",g_sym[i].broker,g_sym[i].err);continue;}
      string mark="  ";bool active=false;
      if(g_sym[i].z>=InpZThreshold){mark="S ";active=true;}
      else if(g_sym[i].z<=-InpZThreshold){mark="L ";active=true;}
      string state=fresh?"":" [STALE]";
      if(g_sym[i].confActive)
         state+=StringFormat(" [CONF %s %d]",(g_sym[i].confSide<0?"S":"L"),g_sym[i].confBarsLeft);
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
         FetchOne(idx);
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
        for(int i=0;i<g_symCount;i++) TryEnter(i);
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
   if(HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic) return;
   long entry=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT) return;

   ulong posId=(ulong)HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID);
   ulong order=(ulong)HistoryDealGetInteger(trans.deal,DEAL_ORDER);
   string sym=HistoryDealGetString(trans.deal,DEAL_SYMBOL);
   double px=HistoryDealGetDouble(trans.deal,DEAL_PRICE);

   double atr=GVRead(GVOrderKey(order,"ATR"),0.0);
   double refEntry=GVRead(GVOrderKey(order,"REF_ENTRY"),0.0);
   double sourceMs=GVRead(GVOrderKey(order,"SIG_SOURCE_MS"),0.0);
   double decision=GVRead(GVOrderKey(order,"SIG_DECISION"),0.0);

   if(posId>0)
     {
      if(atr>0.0) GVWrite(GVPosKey(posId,"ATR"),atr);
      if(refEntry>0.0)
        {
         GVWrite(GVPosKey(posId,"REF_ENTRY"),refEntry);
         GVWrite(GVPosKey(posId,"REF_PEAK"),refEntry);
        }
      if(sourceMs>0.0) GVWrite(GVPosKey(posId,"SIG_SOURCE_MS"),sourceMs);
      if(decision>0.0) GVWrite(GVPosKey(posId,"SIG_DECISION"),decision);
      GVWrite(GVPosKey(posId,"PARTIAL"),0.0);

      // Market fill may differ from pre-send quote. Re-anchor initial 1.5 ATR SL to ACTUAL fill,
      // while preserving the frozen Binance signal ATR.
      if(atr>0.0 && px>0.0 && PositionSelect(sym))
        {
         long ptype=PositionGetInteger(POSITION_TYPE);
         int side=(ptype==POSITION_TYPE_BUY)?1:-1;
         ulong ptk=(ulong)PositionGetInteger(POSITION_TICKET);
         double tp=PositionGetDouble(POSITION_TP);
         double desired=px-side*InpStopATR*atr;
         desired=NormalizePriceTick(sym,desired,(side>0)?-1:+1);
         MqlTick q;
         if(SymbolInfoTick(sym,q))
           {
            double md=MinTradeDistance(sym,true);
            bool dist=(side>0)?(q.bid-desired>=md):(desired-q.ask>=md);
            if(dist)
              {
               g_trade.SetTypeFillingBySymbol(sym);
               bool b=g_trade.PositionModify(ptk,desired,tp);uint rc=g_trade.ResultRetcode();
               double actual=0.0;bool verified=(b && RetcodeAccepted(rc) && VerifyPositionSL(ptk,desired,actual));
               LogExec("STRICT_FILL_SL_ALIGN",sym,ptk,(side>0)?"BUY":"SELL",px,desired,px,actual,rc,verified?"OK":"FAIL");
              }
           }
        }
     }

   LogExec("FILL",sym,order,"",px,0,px,0,(uint)result.retcode,
           StringFormat("pos=%I64u signalATR=%.8f refEntry=%.8f source=%.0f decision=%.0f",posId,atr,refEntry,sourceMs,decision));
  }
//+------------------------------------------------------------------+