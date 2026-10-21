//+------------------------------------------------------------------+
//|                                            ZOS_Multi_v212.mq5    |
//|  ZoneOrdinalStruct — ОДИН бот, ТРИ ноги, різні Magic             |
//|                                                                  |
//|  Логіка кожної ноги = ZoneOrdinalStruct_EA v1.07 (без змін):     |
//|   власний каузальний ZigZag (поріг DevATR*ATR) -> рівні ->       |
//|   пробій тілом >= 0.3 ATR -> ordinal <= 2 -> фільтр структури ->  |
//|   фільтр тренду N днів -> лімітний ордер на ретест рівня          |
//|   (InpRetestBars барів) -> SL за екстремумом, TP = RR * ризик.   |
//|                                                                  |
//|  Ноги (за замовчуванням, з досліду 2026-10-08):                  |
//|   A: M15  DevATR 5  MinAtr% 0.09  MaxPos 2  Magic 771001          |
//|   B: M15  DevATR 8  MinAtr% 0.00  MaxPos 4  Magic 771002          |
//|   C: H1   DevATR 5  MinAtr% 0.00  MaxPos 2  Magic 771003          |
//|  Дедуп: якщо будь-яка нога увійшла в бік dir < InpDedupSec тому, |
//|  інші ноги цей бік пропускають (DD портфеля 34R -> 22R у сим.).   |
//|                                                                  |
//|  Симуляція (Python-репліка, паритет з MT5 98%, M1 bid/ask, свопи)|
//|  2022-06..2026-07: 7.6 угод/міс, +123R, DD 21.9R, усі роки > 0,  |
//|  IS R/DD 3.01 / OOS R/DD 2.86. DEMO-ONLY до MT5-підтвердження.   |
//|                                                                  |
//|  Ставити на ОДИН графік XAUUSD (будь-який ТФ). Ноги самі читають |
//|  свої ТФ. Перевіряти в тестері: модель «Every tick real ticks»,  |
//|  символ XAUUSD, ТФ графіка M15.                                  |
//|                                                                  |
//|  v2.01: дедуп за ЦІНОЮ. MT5 v2.00 (2026-01..08): 12 пар лімітів  |
//|   одного напрямку на майже однаковій ціні виконались в одну      |
//|   хвилину = подвійний ризик на один рух. Тепер: (1) новий ліміт  |
//|   не ставиться, якщо в групі вже є однонапрямлений ліміт ближче  |
//|   InpDedupATR*ATR; (2) після заповнення будь-якого ліміту групи  |
//|   знімаються однонапрямлені ліміти ближче InpDedupATR*ATR.       |
//|   Так EA збігається з симуляцією (DD 22R замість 34R).           |
//|                                                                  |
//|  v2.02: НОГА D — M1, DevATR 5, MinAtr% 0.09, вхід ПО РИНКУ, без  |
//|   фільтра тренду, Magic 771004. Торгує лише сплески волатильності|
//|   (ATR M1 >= 0.09% ціни), утримання ~1 год. Кореляція з A+B+C    |
//|   0.24 (місячна). Симуляція A+B+C+D: 12.8 угод/міс, +168R,        |
//|   DD 29.9R (A+B+C: 7.7/міс, +121R, DD 21.9R). Тому ризик за      |
//|   замовчуванням 0.27% (≈ та сама просадка в %, що 0.36% без D).  |
//|                                                                  |
//|  v2.03: ВИПРАВЛЕНО запобіжник рахунку. v2.02 рахував просадку від |
//|   ПІКУ equity і зупиняв входи назавжди: у тесті 2022–2026 «all»   |
//|   бот став у липні 2022 і більше не торгував (equity не може      |
//|   відновитись без угод). Тепер InpMaxLossPct рахується від        |
//|   ПОЧАТКОВОГО балансу (як ліміт FTMO max loss), InpInitialBalance |
//|   = 0 -> баланс на момент старту EA. Денний стоп без змін.        |
//|                                                                  |
//|  v2.04: ЧАСТКОВА ФІКСАЦІЯ (для рівнішої кривої). Коли ціна       |
//|   проходить InpPartialR*R від входу — закривається InpPartialFrac|
//|   позиції, решта йде до TP (SL не рухається). Ноги A–C за         |
//|   замовчуванням, D — окремий прапор (не тестувалось, вимк.).     |
//|   Симуляція A+B+C 2022-06..2026-07: макс. серія збитків 21 -> 11,|
//|   WR 35% -> 48%, місячне σ 8.1R -> 5.8R, сума -20%;              |
//|   дохід/σ ~ той самий (0.32 -> 0.34) => можна підняти ризик.     |
//|                                                                  |
//|  v2.05: НОГА E = LAB_XAU_MTF_TRAIL v1.00 (інший механізм):       |
//|   режим DI_diff(14) D1 і H4 в один бік -> пробій 1-год екстремуму|
//|   на M15 у бік режиму -> гейт обсягу H4 > 1.2*SMA120 -> SL       |
//|   2*ATR(H4), трейлінг 2*ATR(H4) від піку, без TP, макс. 14 днів, |
//|   пауза 12 барів M15, 1 позиція. Magic 771005, ризик 0.5%.       |
//|   НЕ входить у дедуп ZOS-ніг (незалежний механізм). Спільний     |
//|   запобіжник рахунку. Портфель (MT5-звіти 2022-01..2026-08):     |
//|   ZOS +37.5% DD 10.3% -> ZOS+TRAIL(0.5%) +53.3% DD 9.7%;         |
//|   у провалах ZOS (2022 літо, 2025 весна) TRAIL +0.9% / +1.7%.    |
//|  InpD_Partial за замовчуванням true (сим.: краще на обох періодах).|
//|                                                                  |
//|  v2.06: РЕЖИМ «ПЛАТО ПІСЛЯ ШОКУ» (діагностика кві–сер 2025).      |
//|   Стан = за останні 60 днів був вибух волатильності (ATR D1 у %   |
//|   ціни > 1.5 x медіани за 120 днів) І зараз ціна стоїть           |
//|   (ефективність руху за 20 днів ER < 0.15). Рахується раз на день |
//|   по закритих барах D1. У цьому стані перевага ВСІХ трендових ніг |
//|   зникає (сим.: +0.27R поза станом -> 0.00R у стані, на всіх ногах)|
//|   1) ризик ніг A–E множиться на InpPC_RiskMult (0.5);             |
//|   2) НОГА F (Magic 771006) торгує ПОВЕРНЕННЯ від меж 10-денного   |
//|      діапазону ЛИШЕ в цьому стані: дотик верхніх/нижніх 15%,      |
//|      відбій бару (close не в крайніх 30% бару), вхід по ринку,    |
//|      SL за екстремумом + 0.5 ATR D1, TP = середина діапазону,     |
//|      макс. 3 дні, 1 позиція. Поза станом фейд системно збитковий  |
//|      (-0.17R, IS і OOS), у стані +0.11R (IS +0.08 / OOS +0.14).    |
//|   Сим. портфеля 2022-06..2026-07: +50.5% DD 9.2% ->               |
//|   x0.5 +53.2% DD 7.5% -> x0.5 + F(0.27%) +56.4% DD 7.5%;          |
//|   вікно кві–сер 2025: -5.1% -> -2.5% -> 0.0%. Перевага F мала,    |
//|   вибірка ~100 угод — DEMO/тестер до MT5-підтвердження.           |
//|                                                                  |
//|  v2.07: нога D (M1, задумана на ~1 год) більше НЕ тримає угоди    |
//|   через вихідні. MT5 FTMO 2022-02-28: шорт D з п'ятниці, геп      |
//|   понеділка, SL виконано на 22 пункти гірше = -1112$ (-4.2R).     |
//|   v2.04 MT5: D через вихідні 12 угод, -0.36R/угоду; без них D       |
//|   +4.4R. Ноги A–C через вихідні НЕ чіпаємо (+1.2R/угоду).          |
//|   П'ятниця >= InpD_FriCloseHour (час сервера): D закриває позиції |
//|   і не відкриває нових до понеділка.                             |
//|                                                                  |
//|  v2.08: СЕСІЙНІСТЬ + опція закриття всього в п'ятницю.           |
//|   1) Ноги A і C не входять з InpSesFrom до InpSesTo (час сервера,  |
//|      за замовч. 10–15 = Лондон до відкриття NY) і знімають свої    |
//|      ліміти в цьому вікні. MT5 2022–2026: A+C у цьому вікні        |
//|      73 угоди, -0.32R (t=-2.3), мінус у 4 з 5 років (обидві        |
//|      половини історії). Портфель +50.5% DD 9.2% -> +56.8% DD 8.4%. |
//|      Пробої ранкового Лондона часто хибні; NY 15–19 найкращий.     |
//|   2) InpFriCloseAll: у п'ятницю з InpD_FriCloseHour закрити ВСІ    |
//|      позиції бота, зняти ліміти й не входити до понеділка.        |
//|      За замовч. false: сим. +51.3% -> +41.1% при тій самій DD,     |
//|      бо трендові ноги A/C/E заробляють саме на утриманні через     |
//|      вихідні. Увімкнути, якщо правила рахунку забороняють.         |
//|                                                                  |
//|  v2.12: РЕЖИМ «БЕЗ НАПРЯМКУ» (LAB_ZOS_REG_001, MT5-звіт 2022-26). |
//|   ER = |close вчора - close N днів тому| / сума |денних змін| за N  |
//|   (D1, лише закриті бари, раз на день). Якщо ER < InpER_Max      |
//|   (0.20 при N=20) — ризик ніг A–E x InpER_RiskMult (0.5).         |
//|   Факт MT5 A+D+F 2022.01-2026.10: 39% угод у цьому режимі дають   |
//|   0.00R/угоду (обидві половини історії ~0), поза ним +0.19R.      |
//|   Пост-аналіз x0.5 + F вимк.: прибуток той самий (+24.7k),        |
//|   DD за місяцями 5.2k -> 3.1k, мінус-місяців 25 -> 22,            |
//|   жовтень 2026 -1123 -> -624. Сусідні N/пороги: 15-30 днів і      |
//|   0.15-0.20 теж ~0R у режимі; 0.25-0.30 - ні (режим ширший).      |
//|   Нога F за замовчуванням ВИМК. (у режимі ER20 -1.6k за 4 роки).  |
//|   Нога G за замовчуванням ВИМК. (MT5: свопи з'їли перевагу).      |
//|  v2.11: НОГА G — ДРЕЙФ за 40-денним імпульсом (LAB_ZOS_LEG_002).  |
//|   Раз на годину (нова свічка H1), якщо в ноги G немає позиції:    |
//|   напрям = знак (close D1 вчора - close D1 40 днів тому), лише    |
//|   якщо |рух| >= 0.5 x ATR_D1(14) x sqrt(40). Вхід по ринку,       |
//|   SL = 3 x ATR(14, H1, SMA TR), TP немає, вихід через 48 год.     |
//|   Ризик InpG_Risk (0.13% = половина звичайного), magic 771007,    |
//|   НЕ в дедупі ZOS-ніг, НЕ множиться на PC; спільний запобіжник.   |
//|   Сим. XAUUSD 2022-07..2026-10 (ризик 0.27%): 7.8 угод/міс,       |
//|   +0.155R/угоду, обидві половини > 0, кор. з ZOS +0.28;           |
//|   ZOS(A+D+F)+G: DD $4.7k -> $3.7k, мінус-місяців 22 -> 19.        |
//|   Застереження: найкращий з 5 варіантів (20/60 днів, SL 2/4       |
//|   слабші), по суті бета бичачого золота 2022-26 -> DEMO, пів-ризик.|
//|   Детектор імпульсу з беклогу v2.10 сюди НЕ включено.             |
//|                                                                  |
//|  v2.09: ДІАГНОСТИКА. Торгова логіка і порядок фільтрів БЕЗ ЗМІН.  |
//|   1) HB ніг A–D: лічильник КОЖНОЇ причини пропуску живого сигналу:|
//|      струк, тренд, ризик, atr, спред, maxPos, дедупT (час),        |
//|      дедупЦ (ціна), guard, env, пт, сесія, лот, інше, відмов       |
//|      (брокер). Плюс «сильн» = бари з тілом >= InpBodyATR*ATR і     |
//|      «канд» = пробої живого рівня (ordinal <= N) — сирі сигнали.   |
//|   2) InpLogSkips: кожен відкинутий кандидат = 1 рядок з причиною  |
//|      і значенням (працює без InpVerboseLog). Кандидатів мало,      |
//|      лог не засмічується.                                         |
//|   3) HB ноги E раз на InpDiagHBMin хв: DI D1/H4, пробій, обсяг H4,|
//|      пауза, множник PC + лічильники причин. Лог кожного випадку,  |
//|      коли режим і пробій збіглись, але вхід відсік гейт.           |
//|   4) HB ноги F раз на InpDiagHBMin хв: стан PC, шок, ER, діапазон,|
//|      де ціна в діапазоні + лічильники причин.                     |
//|   5) Запобіжник рахунку: лог при вмиканні/знятті блоку з причиною |
//|      і нагадування раз на InpGuardLogMin хв (раніше LogV на       |
//|      кожному тіку). Equity = ВЕСЬ рахунок, разом з іншими EA.      |
//+------------------------------------------------------------------+
#property copyright "AK47 research"
#property version   "2.12"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>

#define BUFSZ 512
#define NLEGS 4

//==================== ВХОДИ: НОГИ ===================================
input group "=== Нога A ==="
input bool            InpA_On      = true;
input ENUM_TIMEFRAMES InpA_TF      = PERIOD_M15;
input double          InpA_DevATR  = 5.0;
input double          InpA_MinAtr  = 0.09;     // мін. ATR у % ціни (0 = вимк.)
input int             InpA_MaxPos  = 2;
input long            InpA_Magic   = 771001;

input group "=== Нога B ==="
input bool            InpB_On      = true;
input ENUM_TIMEFRAMES InpB_TF      = PERIOD_M15;
input double          InpB_DevATR  = 8.0;
input double          InpB_MinAtr  = 0.0;
input int             InpB_MaxPos  = 4;
input long            InpB_Magic   = 771002;

input group "=== Нога C ==="
input bool            InpC_On      = true;
input ENUM_TIMEFRAMES InpC_TF      = PERIOD_H1;
input double          InpC_DevATR  = 5.0;
input double          InpC_MinAtr  = 0.0;
input int             InpC_MaxPos  = 2;
input long            InpC_Magic   = 771003;

input group "=== Нога D (M1, сплески волатильності) ==="
input bool            InpD_On      = true;
input ENUM_TIMEFRAMES InpD_TF      = PERIOD_M1;
input double          InpD_DevATR  = 5.0;
input double          InpD_MinAtr  = 0.09;     // ключовий для D: пропускає лише сплески
input int             InpD_MaxPos  = 2;
input long            InpD_Magic   = 771004;
input bool            InpD_Retest  = false;    // false = вхід по ринку (як у тесті)
input bool            InpD_Trend   = false;    // false = без фільтра тренду (як у тесті)
input int             InpD_FriCloseHour = 22;  // v2.07: п'ятниця, година сервера: закрити D і не входити (-1 = вимк.)
input bool            InpFriCloseAll    = false; // v2.08: те саме для ВСІХ ніг (A–F)
input bool            InpSesBlockAC     = true;  // v2.08: ноги A і C не входять у вікні нижче
input int             InpSesFrom        = 10;    // година сервера, від (включно)
input int             InpSesTo          = 15;    // година сервера, до (не включно)

//==================== ВХОДИ: СПІЛЬНА КОНСТРУКЦІЯ ====================
input group "=== Конструкція (спільна, не рухати) ==="
input int    InpDepth          = 8;       // мін. барів від екстремуму до підтвердження
input double InpBodyATR        = 0.30;    // мін. тіло бару пробою, в ATR
input int    InpLifeBars       = 200;     // життя рівня, барів
input int    InpMaxOrdinal     = 2;       // ordinal <= N
input bool   InpUseStructure   = true;    // відсікати контрструктурні пробої
input int    InpExtBars        = 10;      // вікно екстремуму для ризику
input double InpBufATR         = 0.10;    // буфер до SL, в ATR
input double InpMinRiskATR     = 0.15;
input double InpMaxRiskATR     = 4.00;
input double InpRR             = 3.0;     // TP = RR * ризик
input int    InpATRPeriod      = 14;

input group "=== Вхід, режим, дедуп ==="
input int    InpRetestBars     = 8;       // життя лімітного ордера, барів ТФ ноги
input int    InpTrendDays      = 90;      // тренд за N календарних днів (0 = вимк.)
input int    InpDedupSec       = 120;     // дедуп однонапрямлених входів між ногами, сек
input double InpDedupATR       = 0.30;    // v2.01: дедуп лімітів за ціною, в ATR ноги

input group "=== [v2.04] Часткова фіксація ==="
input double InpPartialR       = 1.5;     // при +X R закрити частину (0 = вимк.)
input double InpPartialFrac    = 0.5;     // яку частку закрити
input bool   InpD_Partial      = true;    // застосовувати до ноги D (M1); v2.05: true

input group "=== [v2.05] Нога E: TRAIL (DI-режим D1/H4 + пробій M15 + трейлінг) ==="
input bool   InpE_On           = true;
input double InpE_Risk         = 0.50;    // ризик ноги E, % балансу
input long   InpE_Magic        = 771005;
input int    InpE_DIPeriod     = 14;
input int    InpE_BreakBars    = 4;       // барів M15 для екстремуму (4 = 1 год)
input bool   InpE_UseVolGate   = true;
input double InpE_VolMult      = 1.20;
input int    InpE_VolMA        = 120;
input double InpE_SL_ATR4      = 2.0;
input double InpE_Trail_ATR4   = 2.0;
input int    InpE_MaxHoldDays  = 14;
input int    InpE_CooldownM15  = 12;

input group "=== [v2.06] Режим «плато після шоку» + нога F ==="
input double InpPC_RiskMult    = 0.50;    // множник ризику ніг A–E у стані (1.0 = вимк.)
input int    InpPC_AtrDays     = 14;      // ATR D1 (SMA TR), днів
input int    InpPC_MedDays     = 120;     // база для медіани ATR%, днів
input double InpPC_ShockMult   = 1.50;    // шок: ATR% > X * медіана
input int    InpPC_ShockLook   = 60;      // шок мав бути за останні N днів
input int    InpPC_ErDays      = 20;      // ефективність руху за N днів
input double InpPC_ErMax       = 0.15;    // плато: ER < X
input bool   InpF_On           = false;   // v2.12: за замовч. вимк.    // нога F: повернення в діапазон (лише в стані)
input double InpF_Risk         = 0.27;    // ризик ноги F, % балансу
input long   InpF_Magic        = 771006;
input int    InpF_RangeDays    = 10;      // діапазон = max/min останніх N закритих днів
input double InpF_Zone         = 0.15;    // зона біля межі, частка ширини діапазону
input double InpF_SL_ATRD      = 0.50;    // SL за екстремумом, в ATR D1
input int    InpF_MaxHoldDays  = 3;

input group "=== [v2.11] Нога G: ДРЕЙФ (40-денний імпульс, H1) ==="
input bool   InpG_On           = false;   // v2.12: вимк. (MT5-тестер: не пройшла)
input double InpG_Risk         = 0.13;    // ризик ноги G, % балансу (половина звичайного)
input long   InpG_Magic        = 771007;
input int    InpG_LookDays     = 40;      // імпульс: close D1 вчора проти close D1 N торгових днів тому
input double InpG_MinZ         = 0.5;     // мін. |рух| / (ATR_D1 * sqrt(N))
input double InpG_SL_ATRH1     = 3.0;     // SL = X * ATR(14, H1)
input int    InpG_MaxHoldHours = 48;      // вихід за часом

input group "=== [v2.12] Режим без напрямку (ER) ==="
input bool   InpER_On          = true;
input int    InpER_Days        = 20;      // ER за N закритих днів D1
input double InpER_Max         = 0.20;    // ER < X -> режим «без напрямку»
input double InpER_RiskMult    = 0.50;    // множник ризику ніг A–E у цьому режимі

input group "=== Ризик і виконання ==="
input double InpRiskPercent    = 0.27;    // ризик на угоду, % балансу (v2.02: з ногою D)
input double InpMaxSpreadATR   = 1.00;    // спред-гейт у частках ATR ноги
input int    InpSlippagePts    = 30;
input double InpDailyStopPct   = 3.0;     // денна просадка (від equity на початок дня), % (0 = вимк.)
input double InpMaxLossPct     = 8.0;     // v2.03: макс. збиток від ПОЧАТКОВОГО балансу, % (0 = вимк.)
input double InpInitialBalance = 0.0;     // v2.03: початковий баланс пропу (0 = баланс на старті EA)

input group "=== Стан, VPS, діагностика ==="
input int    InpRebuildBars    = 3000;    // барів історії для відновлення стану ноги
input int    InpTimerSec       = 60;
input int    InpHeartbeatBars  = 16;      // heartbeat кожні N барів ноги (0 = вимк.)
input bool   InpAllowLiveTrading = true;
input bool   InpDryRun         = false;
input bool   InpVerboseLog     = false;

input group "=== [v2.09] Діагностика ==="
input bool   InpLogSkips       = true;    // рядок у лог на кожен відкинутий кандидат (A–F)
input int    InpDiagHBMin      = 60;      // heartbeat ніг E і F, хв (0 = вимк.)
input int    InpGuardLogMin    = 15;      // нагадування про блок запобіжника, хв

//==================== СТРУКТУРИ ====================================
struct Pivot
  {
   long     extIdx;
   double   price;
   int      kind;        // +1 максимум (опір), -1 мінімум (підтримка)
   long     confIdx;
  };

struct Level
  {
   double   price;
   int      kind;
   int      side;        // -kind
   long     availIdx;
   int      ordinal;
   bool     dead;
  };

//==================== СПІЛЬНІ ГЛОБАЛЬНІ ============================
CTrade         g_trade;
CSymbolInfo    g_sym;
string         g_version = "v2.12";
datetime       g_lastDirEntry[2];         // [0]=sell, [1]=buy — дедуп між ногами
double         g_dayStartEq = 0.0;
int            g_dayStamp   = -1;
double         g_initBal    = 0.0;
bool           g_guardBlocked = false;    // v2.09
datetime       g_guardLastLog = 0;        // v2.09

void Log(const string msg)  { Print("[ZOSM ", g_version, "] ", msg); }
void LogV(const string msg) { if(InpVerboseLog) Log(msg); }
string DirStr(const int dir) { return(dir > 0 ? "BUY" : "SELL"); }

//==================== v2.06: РЕЖИМ «ПЛАТО ПІСЛЯ ШОКУ» ==============
bool     g_pcState = false;
bool     g_pcReady = false;
datetime g_pcDay   = 0;
double   g_pcHi = 0.0, g_pcLo = 0.0, g_pcAtrD = 0.0;   // для ноги F (дані по вчора)
double   g_pcRatio = 0.0, g_pcEr = 0.0;

double PCMult() { return(g_pcState ? InpPC_RiskMult : 1.0); }

// v2.12: режим «без напрямку» (ER D1)
bool     g_erLow = false;
double   g_erVal = 0.0;
datetime g_erDay = 0;
double ERMult() { return((InpER_On && g_erLow) ? InpER_RiskMult : 1.0); }
double RiskMult() { return(PCMult() * ERMult()); }
void UpdateERState()
  {
   if(!InpER_On) { g_erLow = false; return; }
   datetime d0 = iTime(_Symbol, PERIOD_D1, 0);
   if(d0 == 0 || d0 == g_erDay) return;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int need = InpER_Days + 1;
   int n = CopyRates(_Symbol, PERIOD_D1, 1, need, r);   // r[n-1] = вчора
   g_erDay = d0;
   if(n < need) { g_erLow = false; Log(StringFormat("ER: історії D1 мало (%d з %d) - режим вимк.", n, need)); return; }
   double path = 0.0;
   for(int i = 1; i < n; i++) path += MathAbs(r[i].close - r[i - 1].close);
   g_erVal = (path > 0.0) ? MathAbs(r[n - 1].close - r[0].close) / path : 1.0;
   bool was = g_erLow;
   g_erLow = (g_erVal < InpER_Max);
   Log(StringFormat("ER%d=%.3f (поріг %.2f) -> %s, множник ризику A–E = %.2f (з PC %.2f)",
                    InpER_Days, g_erVal, InpER_Max, (g_erLow ? "БЕЗ НАПРЯМКУ" : "звичайний"), ERMult(), RiskMult()));
   if(was != g_erLow) Log(g_erLow ? "ER: вхід у режим без напрямку - ризик знижено" : "ER: вихід з режиму без напрямку - ризик повний");
  }

// v2.08: п'ятниця після години закриття (для всіх ніг, якщо InpFriCloseAll)
bool FriLateAll()
  {
   if(!InpFriCloseAll || InpD_FriCloseHour < 0) return(false);
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return(dt.day_of_week == 5 && dt.hour >= InpD_FriCloseHour);
  }

// v2.08: закрити позиції одного magic (вихідні)
void CloseMagic(const long mg, const string tag)
  {
   if(InpDryRun) return;
   g_trade.SetExpertMagicNumber(mg);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != mg) continue;
      if(g_trade.PositionClose(tk, (ulong)InpSlippagePts))
         Log(StringFormat("%s WEEKEND close %I64u", tag, tk));
     }
  }

double MedianOf(const double &src[], const int from, const int cnt)
  {
   double tmp[];
   ArrayResize(tmp, cnt);
   for(int k = 0; k < cnt; k++) tmp[k] = src[from + k];
   ArraySort(tmp);
   if(cnt % 2 == 1) return(tmp[cnt / 2]);
   return(0.5 * (tmp[cnt / 2 - 1] + tmp[cnt / 2]));
  }

// раз на новий день D1; усі дані — закриті бари (shift >= 1)
void UpdatePCState()
  {
   datetime d0 = iTime(_Symbol, PERIOD_D1, 0);
   if(d0 == 0 || d0 == g_pcDay) return;
   int need = InpPC_ShockLook + InpPC_MedDays + InpPC_AtrDays + 2;
   if(need < InpPC_ErDays + 2) need = InpPC_ErDays + 2;
   if(need < InpF_RangeDays + 2) need = InpF_RangeDays + 2;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_D1, 1, need, r);
   g_pcDay = d0;
   if(n < need)
     {
      g_pcState = false; g_pcReady = false;
      Log(StringFormat("PC: історії D1 мало (%d з %d) — стан вимк., нога F не торгує", n, need));
      return;
     }
   double tr[], a[];
   ArrayResize(tr, n); ArrayResize(a, n);
   for(int i = 0; i < n; i++)
     {
      double v = r[i].high - r[i].low;
      if(i > 0)
        {
         double v2 = MathAbs(r[i].high - r[i - 1].close);
         double v3 = MathAbs(r[i].low - r[i - 1].close);
         if(v2 > v) v = v2;
         if(v3 > v) v = v3;
        }
      tr[i] = v;
     }
   for(int i = 0; i < n; i++)
     {
      a[i] = 0.0;
      if(i < InpPC_AtrDays - 1 || r[i].close <= 0.0) continue;
      double s = 0.0;
      for(int k = i - InpPC_AtrDays + 1; k <= i; k++) s += tr[k];
      a[i] = s / InpPC_AtrDays / r[i].close;
     }
   bool recent = false;
   double best = 0.0;
   for(int i = n - 1; i >= n - InpPC_ShockLook; i--)
     {
      int from = i - InpPC_MedDays + 1;
      if(from < InpPC_AtrDays - 1) break;
      double med = MedianOf(a, from, InpPC_MedDays);
      if(med <= 0.0) continue;
      double ratio = a[i] / med;
      if(ratio > best) best = ratio;
      if(ratio > InpPC_ShockMult) recent = true;
     }
   double path = 0.0;
   for(int k = n - InpPC_ErDays; k <= n - 1; k++) path += MathAbs(r[k].close - r[k - 1].close);
   double er = (path > 0.0) ? MathAbs(r[n - 1].close - r[n - 1 - InpPC_ErDays].close) / path : 1.0;
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int k = n - InpF_RangeDays; k <= n - 1; k++)
     {
      if(r[k].high > hi) hi = r[k].high;
      if(r[k].low < lo)  lo = r[k].low;
     }
   bool prev = g_pcState;
   g_pcState = (recent && er < InpPC_ErMax);
   g_pcReady = true;
   g_pcRatio = best; g_pcEr = er;
   g_pcHi = hi; g_pcLo = lo; g_pcAtrD = a[n - 1] * r[n - 1].close;
   if(g_pcState != prev)
      Log(StringFormat("PC: стан %s | шок max=%.2f ER%d=%.2f | діапазон %.2f–%.2f ATR_D1=%.2f | множник ризику A–E=%.2f",
                       (g_pcState ? "УВІМКНЕНО (плато після шоку)" : "вимкнено"), best, InpPC_ErDays, er,
                       lo, hi, g_pcAtrD, PCMult()));
   else
      LogV(StringFormat("PC: день %s стан=%s шок=%.2f ER=%.2f", TimeToString(d0, TIME_DATE),
                        (g_pcState ? "on" : "off"), best, er));
  }

//==================== СПІЛЬНІ ФУНКЦІЇ ==============================
double NormalizeVolume(double vol)
  {
   double vmin  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double vstep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(vstep <= 0.0) vstep = 0.01;
   if(vmin <= 0.0)  vmin = vstep;
   vol = MathFloor(vol / vstep) * vstep;
   if(vol < vmin) return(0.0);
   if(vol > vmax) vol = vmax;
   int digits = 0;
   double s = vstep;
   while(s < 1.0 && digits < 8) { s *= 10.0; digits++; }
   return(NormalizeDouble(vol, digits));
  }

double CalcLot(const double slDist, const double riskPct = -1.0)
  {
   if(slDist <= 0.0) return(0.0);
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0.0 || ts <= 0.0) return(0.0);
   double riskMoney  = AccountInfoDouble(ACCOUNT_BALANCE) * ((riskPct > 0.0) ? riskPct : InpRiskPercent) / 100.0;
   double lossPerLot = (slDist / ts) * tv;
   if(lossPerLot <= 0.0) return(0.0);
   double lot = NormalizeVolume(riskMoney / lossPerLot);
   if(lot <= 0.0) return(0.0);
   double margin = 0.0;
   if(OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, lot, SymbolInfoDouble(_Symbol, SYMBOL_ASK), margin))
      if(margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.9)
        {
         Log(StringFormat("CalcLot: маржа %.2f > 90%% вільної — SKIP", margin));
         return(0.0);
        }
   return(lot);
  }

bool ClampStops(const bool isBuy, const double entry, double &sl, double &tp)
  {
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   long   stl   = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long   frl   = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double minDist = (double)((stl > frl) ? stl : frl) * point;
   if(minDist <= 0.0) minDist = point;
   if(isBuy)
     {
      if(entry - sl < minDist) sl = entry - minDist;
      if(tp - entry < minDist) tp = entry + minDist;
     }
   else
     {
      if(sl - entry < minDist) sl = entry + minDist;
      if(entry - tp < minDist) tp = entry - minDist;
     }
   int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, dg);
   tp = NormalizeDouble(tp, dg);
   if(isBuy && (sl >= entry || tp <= entry))  return(false);
   if(!isBuy && (sl <= entry || tp >= entry)) return(false);
   return(true);
  }

// тренд: close бару сигналу проти D1 close N календарних днів тому
bool TrendOK(const int dir, const datetime barTime, const double refPrice, double &pct)
  {
   pct = 0.0;
   if(InpTrendDays <= 0) return(true);
   datetime past = barTime - (datetime)((long)InpTrendDays * 86400);
   int sh = iBarShift(_Symbol, PERIOD_D1, past, false);
   if(sh < 0) return(false);
   double base = iClose(_Symbol, PERIOD_D1, sh);
   if(base <= 0.0 || refPrice <= 0.0) return(false);
   pct = (refPrice / base - 1.0) * 100.0;
   return(dir * pct > 0.0);
  }

// рахунковий запобіжник (денний і загальний), спільний для всіх ніг
// v2.09: та сама логіка; лог при зміні стану + нагадування раз на InpGuardLogMin хв
bool AccountGuardOK()
  {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(dt.day_of_year != g_dayStamp)
     {
      g_dayStamp = dt.day_of_year;
      g_dayStartEq = eq;
     }
   string why = "";
   if(InpDailyStopPct > 0.0 && g_dayStartEq > 0.0)
     {
      double dd = (g_dayStartEq - eq) / g_dayStartEq * 100.0;
      if(dd >= InpDailyStopPct)
         why = StringFormat("денний стоп: -%.2f%% від equity початку дня %.2f (ліміт %.1f%%)",
                            dd, g_dayStartEq, InpDailyStopPct);
     }
   if(why == "" && InpMaxLossPct > 0.0 && g_initBal > 0.0)
     {
      double ml = (g_initBal - eq) / g_initBal * 100.0;
      if(ml >= InpMaxLossPct)
         why = StringFormat("загальна просадка: -%.2f%% від початкового балансу %.2f (ліміт %.1f%%)",
                            ml, g_initBal, InpMaxLossPct);
     }
   bool blocked = (why != "");
   datetime now = TimeCurrent();
   if(blocked != g_guardBlocked)
     {
      if(blocked) Log("GUARD: входи ЗАБЛОКОВАНО — " + why + StringFormat(" | equity рахунку=%.2f (усі EA)", eq));
      else        Log(StringFormat("GUARD: блок знято | equity=%.2f", eq));
      g_guardLastLog = now;
     }
   else if(blocked && InpGuardLogMin > 0 && now - g_guardLastLog >= (long)InpGuardLogMin * 60)
     {
      Log("GUARD: досі заблоковано — " + why);
      g_guardLastLog = now;
     }
   g_guardBlocked = blocked;
   return(!blocked);
  }

bool TradeEnvOK()
  {
   if(InpDryRun) return(true);
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))      { Log("SKIP: немає з'єднання");          return(false); }
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))  { Log("SKIP: торгівля заборонена (термінал)"); return(false); }
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))            { Log("SKIP: торгівля заборонена (EA)");  return(false); }
   return(true);
  }

// v2.01: чи належить magic групі
bool IsGroupMagic(const long mg)
  {
   return(mg == InpA_Magic || mg == InpB_Magic || mg == InpC_Magic || mg == InpD_Magic);
  }

// v2.01: чи є в групі ліміт того ж напрямку ближче dist
bool GroupPendingNear(const int dir, const double price, const double dist)
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol || !IsGroupMagic(OrderGetInteger(ORDER_MAGIC))) continue;
      ENUM_ORDER_TYPE t = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(dir > 0 && t != ORDER_TYPE_BUY_LIMIT) continue;
      if(dir < 0 && t != ORDER_TYPE_SELL_LIMIT) continue;
      if(MathAbs(OrderGetDouble(ORDER_PRICE_OPEN) - price) <= dist) return(true);
     }
   return(false);
  }

// v2.01: зняти однонапрямлені ліміти групи біля ціни заповнення
void CancelGroupPendingNear(const int dir, const double price, const double dist)
  {
   if(InpDryRun || dist <= 0.0) return;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      long mg = OrderGetInteger(ORDER_MAGIC);
      if(!IsGroupMagic(mg)) continue;
      ENUM_ORDER_TYPE t = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(dir > 0 && t != ORDER_TYPE_BUY_LIMIT) continue;
      if(dir < 0 && t != ORDER_TYPE_SELL_LIMIT) continue;
      if(MathAbs(OrderGetDouble(ORDER_PRICE_OPEN) - price) > dist) continue;
      g_trade.SetExpertMagicNumber(mg);
      if(g_trade.OrderDelete(tk))
         Log(StringFormat("DEDUP: знято ліміт %I64u (дубль заповненого входу @%.2f)", tk, price));
     }
  }

//+------------------------------------------------------------------+
//| НОГА                                                             |
//+------------------------------------------------------------------+
class CLeg
  {
public:
   string            name;
   bool              on;
   ENUM_TIMEFRAMES   tf;
   double            devATR;
   double            minAtrPct;
   int               maxPos;
   long              magic;
   bool              retest;     // v2.02: true = ліміт на ретесті, false = ринок
   bool              useTrend;   // v2.02: фільтр тренду N днів

   int               atrHandle;
   datetime          lastBarTime;
   long              barIdx;
   int               zzTrend;
   long              zzExtIdx;
   double            zzExtPrice;
   Pivot             piv[];
   Level             lvl[];
   double            bufH[BUFSZ];
   double            bufL[BUFSZ];
   bool              rebuilding;
   long              lastHB;
   int               entries;
   double            lastAtr;

   // v2.09: діагностичні лічильники (лише живі бари)
   long              sBig;       // бари з тілом >= InpBodyATR*ATR
   long              sCand;      // пробої живого рівня, ordinal <= N
   long              skStruct, skTrend, skRisk, skAtr, skSpread, skPos;
   long              skDedT, skDedP, skGuard, skEnv, skFri, skSes, skLot, skOther;
   long              nFail;      // відмови брокера

                     CLeg() { on = false; atrHandle = INVALID_HANDLE; }

   void              ResetStats()
     {
      sBig = 0; sCand = 0;
      skStruct = 0; skTrend = 0; skRisk = 0; skAtr = 0; skSpread = 0; skPos = 0;
      skDedT = 0; skDedP = 0; skGuard = 0; skEnv = 0; skFri = 0; skSes = 0; skLot = 0; skOther = 0;
      nFail = 0;
     }

   void              Setup(const string nm, const bool o, const ENUM_TIMEFRAMES t, const double dev,
                           const double ma, const int mp, const long mg,
                           const bool rt = true, const bool tr = true)
     {
      name = nm; on = o; tf = t; devATR = dev; minAtrPct = ma; maxPos = mp; magic = mg;
      retest = rt; useTrend = tr;
      lastBarTime = 0; barIdx = 0; zzTrend = 0; zzExtIdx = 0; zzExtPrice = 0.0;
      ArrayFree(piv); ArrayFree(lvl);
      ArrayInitialize(bufH, 0.0); ArrayInitialize(bufL, 0.0);
      rebuilding = false; lastHB = 0; entries = 0;
      lastAtr = 0.0;
      ResetStats();
     }

   bool              Init()
     {
      if(!on) return(true);
      atrHandle = iATR(_Symbol, tf, InpATRPeriod);
      if(atrHandle == INVALID_HANDLE)
        {
         Log(name + ": iATR INVALID_HANDLE");
         return(false);
        }
      Rebuild();
      return(true);
     }

   void              Release()
     {
      if(atrHandle != INVALID_HANDLE) IndicatorRelease(atrHandle);
      atrHandle = INVALID_HANDLE;
     }

   string            Tag() { return(name + "/" + EnumToString(tf)); }

   // v2.09: рядок лічильників (для HB і DEINIT)
   string            Stats()
     {
      return(StringFormat("сильн=%I64d канд=%I64d | струк=%I64d тренд=%I64d ризик=%I64d atr=%I64d спред=%I64d maxPos=%I64d дедупT=%I64d дедупЦ=%I64d guard=%I64d env=%I64d пт=%I64d сесія=%I64d лот=%I64d інше=%I64d відмов=%I64d",
                          sBig, sCand, skStruct, skTrend, skRisk, skAtr, skSpread, skPos,
                          skDedT, skDedP, skGuard, skEnv, skFri, skSes, skLot, skOther, nFail));
     }

   // v2.09: облік і лог відкинутого кандидата
   void              Skip(long &cnt, const string why, const int dir, const double lp, const int ordn,
                          const string extra = "")
     {
      cnt++;
      if(InpLogSkips)
         Log(StringFormat("%s SKIP %s | %s рівень=%.2f o%d%s", Tag(), why, DirStr(dir), lp, ordn, extra));
     }

   //--- буфер H/L
   void              BufPut(const long idx, const double h, const double l)
     {
      int p = (int)(idx & (BUFSZ - 1));
      bufH[p] = h; bufL[p] = l;
     }
   bool              BufExtreme(const long fromIdx, const long toIdx, const bool wantHigh, double &res)
     {
      if(toIdx < fromIdx || toIdx - fromIdx >= BUFSZ - 1 || barIdx - fromIdx >= BUFSZ - 1)
         return(false);
      double best = wantHigh ? -DBL_MAX : DBL_MAX;
      for(long i = fromIdx; i <= toIdx; i++)
        {
         int p = (int)(i & (BUFSZ - 1));
         double v = wantHigh ? bufH[p] : bufL[p];
         if(v <= 0.0) return(false);
         if(wantHigh) { if(v > best) best = v; }
         else         { if(v < best) best = v; }
        }
      res = best;
      return(true);
     }

   //--- позиції/ордери ноги
   int               CountPos()
     {
      int c = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         if(PositionGetInteger(POSITION_MAGIC) != magic) continue;
         c++;
        }
      return(c);
     }

   void              ManagePending()
     {
      if(!on || InpDryRun) return;
      bool full = (CountPos() >= maxPos);
      long life = (long)InpRetestBars * PeriodSeconds(tf);
      datetime now = TimeCurrent();
      for(int i = OrdersTotal() - 1; i >= 0; i--)
        {
         ulong tk = OrderGetTicket(i);
         if(tk == 0) continue;
         if(OrderGetString(ORDER_SYMBOL) != _Symbol || OrderGetInteger(ORDER_MAGIC) != magic) continue;
         bool expired = (now - (datetime)OrderGetInteger(ORDER_TIME_SETUP) >= life);
         bool blocked = (SessionBlocked() || FridayLate());     // v2.08
         if(!expired && !full && !blocked) continue;
         g_trade.SetExpertMagicNumber(magic);
         if(g_trade.OrderDelete(tk))
            LogV(StringFormat("%s PENDING DEL %I64u (%s)", Tag(), tk, (expired ? "тайм-аут ретесту" : (blocked ? "сесія/вихідні" : "ліміт позицій"))));
        }
     }

   //--- v2.04: часткова фіксація
   ulong             doneIds[];
   bool              PartialDone(const ulong posId, const double curVol)
     {
      for(int q = 0; q < ArraySize(doneIds); q++)
         if(doneIds[q] == posId) return(true);
      if(!HistorySelectByPosition(posId)) return(false);
      for(int k = 0; k < HistoryDealsTotal(); k++)
        {
         ulong dt = HistoryDealGetTicket(k);
         if(HistoryDealGetInteger(dt, DEAL_ENTRY) == DEAL_ENTRY_IN)
           {
            bool done = (curVol < HistoryDealGetDouble(dt, DEAL_VOLUME) - 1e-8);
            if(done)
              {
               int n = ArraySize(doneIds);
               if(n > 200) { ArrayRemove(doneIds, 0, 100); n = ArraySize(doneIds); }
               ArrayResize(doneIds, n + 1); doneIds[n] = posId;
              }
            return(done);
           }
        }
      return(false);
     }

   void              ManagePartial()
     {
      if(!on || InpDryRun || InpPartialR <= 0.0 || InpPartialFrac <= 0.0 || InpPartialFrac >= 1.0) return;
      if(name == "D" && !InpD_Partial) return;
      double vmin  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double vstep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      if(vstep <= 0.0) vstep = 0.01;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != magic) continue;
         double op  = PositionGetDouble(POSITION_PRICE_OPEN);
         double sl  = PositionGetDouble(POSITION_SL);
         double vol = PositionGetDouble(POSITION_VOLUME);
         if(sl <= 0.0) continue;
         double r = MathAbs(op - sl);
         if(r <= 0.0) continue;
         bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
         double px = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double gain = isBuy ? (px - op) : (op - px);
         if(gain < InpPartialR * r) continue;
         if(PartialDone((ulong)PositionGetInteger(POSITION_IDENTIFIER), vol)) continue;
         double cv = MathFloor(vol * InpPartialFrac / vstep) * vstep;
         if(cv < vmin || vol - cv < vmin - 1e-8) continue;      // замало обсягу для поділу
         g_trade.SetExpertMagicNumber(magic);
         ulong pid = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
         if(g_trade.PositionClosePartial(tk, cv, (ulong)InpSlippagePts))
           {
            int n = ArraySize(doneIds); ArrayResize(doneIds, n + 1); doneIds[n] = pid;
            Log(StringFormat("%s PARTIAL %I64u закрито %.2f з %.2f при +%.2fR", Tag(), tk, cv, vol, gain / r));
           }
        }
     }

   //--- структура
   int               StructureState(const long cur)
     {
      double hi[2], lo[2];
      int nh = 0, nl = 0;
      for(int i = ArraySize(piv) - 1; i >= 0; i--)
        {
         if(piv[i].confIdx >= cur) continue;
         if(piv[i].kind > 0 && nh < 2) { hi[nh] = piv[i].price; nh++; }
         else if(piv[i].kind < 0 && nl < 2) { lo[nl] = piv[i].price; nl++; }
         if(nh >= 2 && nl >= 2) break;
        }
      if(nh < 2 || nl < 2) return(0);
      if(hi[0] > hi[1] && lo[0] > lo[1]) return(1);
      if(hi[0] < hi[1] && lo[0] < lo[1]) return(-1);
      return(0);
     }

   void              AddPivot(const double price, const int kind, const long conf)
     {
      int n = ArraySize(piv);
      ArrayResize(piv, n + 1);
      piv[n].extIdx = zzExtIdx; piv[n].price = price; piv[n].kind = kind; piv[n].confIdx = conf;
      int m = ArraySize(lvl);
      ArrayResize(lvl, m + 1);
      lvl[m].price = price; lvl[m].kind = kind; lvl[m].side = -kind;
      lvl[m].availIdx = conf + 1; lvl[m].ordinal = 0; lvl[m].dead = false;
     }

   void              ZigZagStep(const long bi, const double h, const double l, const double c, const double atr)
     {
      if(atr <= 0.0 || !MathIsValidNumber(atr)) return;
      double thr = devATR * atr;
      if(zzTrend == 0)
        {
         if(zzExtPrice <= 0.0) { zzExtPrice = c; zzExtIdx = bi; return; }
         if(h >= zzExtPrice + thr)      { zzTrend = 1;  zzExtIdx = bi; zzExtPrice = h; }
         else if(l <= zzExtPrice - thr) { zzTrend = -1; zzExtIdx = bi; zzExtPrice = l; }
         return;
        }
      if(zzTrend > 0)
        {
         if(h > zzExtPrice) { zzExtIdx = bi; zzExtPrice = h; return; }
         if(l <= zzExtPrice - thr && (bi - zzExtIdx) >= InpDepth)
           {
            AddPivot(zzExtPrice, 1, bi);
            zzTrend = -1; zzExtIdx = bi; zzExtPrice = l;
           }
         return;
        }
      if(l < zzExtPrice) { zzExtIdx = bi; zzExtPrice = l; return; }
      if(h >= zzExtPrice + thr && (bi - zzExtIdx) >= InpDepth)
        {
         AddPivot(zzExtPrice, -1, bi);
         zzTrend = 1; zzExtIdx = bi; zzExtPrice = h;
        }
     }

   void              Purge(const long cur)
     {
      int n = ArraySize(lvl), w = 0;
      for(int i = 0; i < n; i++)
        {
         if(lvl[i].dead) continue;
         if(cur > lvl[i].availIdx + InpLifeBars) continue;
         if(w != i) lvl[w] = lvl[i];
         w++;
        }
      if(w != n) ArrayResize(lvl, w);
      int np = ArraySize(piv);
      if(np > 500)
        {
         Pivot tmp[];
         ArrayResize(tmp, 500);
         for(int i = 0; i < 500; i++) tmp[i] = piv[np - 500 + i];
         ArrayFree(piv);
         ArrayResize(piv, 500);
         for(int i = 0; i < 500; i++) piv[i] = tmp[i];
        }
     }

   //--- обробка закритого бару
   //    v2.09: логіка і порядок фільтрів без змін; кожен вихід з кандидата — лічильник + лог
   void              ProcessBar(const long bi, const datetime bt, const double o, const double h,
                                const double l, const double c, const double atr, const bool live)
     {
      if(atr <= 0.0 || !MathIsValidNumber(atr)) return;
      if(live) lastAtr = atr;
      if(MathAbs(c - o) < InpBodyATR * atr) return;
      if(live) sBig++;

      int nLv = ArraySize(lvl);
      for(int i = 0; i < nLv; i++)
        {
         if(lvl[i].dead || bi < lvl[i].availIdx) continue;
         if(bi > lvl[i].availIdx + InpLifeBars) { lvl[i].dead = true; continue; }

         double price = lvl[i].price;
         int    side  = lvl[i].side;
         bool beyond = (side > 0) ? (c < price) : (c > price);
         if(!beyond) continue;

         lvl[i].ordinal++;
         int ordn = lvl[i].ordinal;
         if(ordn >= InpMaxOrdinal) lvl[i].dead = true;
         if(ordn > InpMaxOrdinal) continue;

         int dir = -side;
         if(live) sCand++;
         int st = StructureState(bi);
         int wt = (st == 0) ? 0 : ((dir == st) ? 1 : -1);
         if(InpUseStructure && wt < 0)
           {
            if(live) Skip(skStruct, "структура", dir, price, ordn, StringFormat(" стр=%d", st));
            continue;
           }
         if(!live) continue;

         double trPct = 0.0;
         if(useTrend && !TrendOK(dir, bt, c, trPct))
           { Skip(skTrend, "тренд", dir, price, ordn, StringFormat(" %dд=%.2f%%", InpTrendDays, trPct)); continue; }

         long fromIdx = lvl[i].availIdx;
         long lowIdx  = bi - InpExtBars;
         if(lowIdx < fromIdx) lowIdx = fromIdx;
         double ext = 0.0;
         if(!BufExtreme(lowIdx, bi, (dir < 0), ext)) { Skip(skOther, "буфер H/L неповний", dir, price, ordn); continue; }

         if(!g_sym.RefreshRates()) { Skip(skOther, "котирування", dir, price, ordn); continue; }
         double mkt = (dir > 0) ? g_sym.Ask() : g_sym.Bid();
         double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
         long   stl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
         long   frl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
         long   lp  = (stl > frl) ? stl : frl;
         double gap = ((lp > 1) ? (double)lp : 1.0) * point;
         double entry = NormalizeDouble(price, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
         bool atLevel = (dir > 0) ? (mkt <= entry + gap) : (mkt >= entry - gap);
         bool pend = retest && !atLevel;
         if(!pend) entry = mkt;

         double risk = (dir > 0) ? (entry - ext) + InpBufATR * atr : (ext - entry) + InpBufATR * atr;
         if(!MathIsValidNumber(risk) || risk <= InpMinRiskATR * atr || risk > InpMaxRiskATR * atr)
           {
            Skip(skRisk, "ризик", dir, price, ordn,
                 StringFormat(" %.2fATR (межі %.2f–%.2f)", (atr > 0.0 ? risk / atr : 0.0), InpMinRiskATR, InpMaxRiskATR));
            continue;
           }

         if(minAtrPct > 0.0 && atr / price * 100.0 < minAtrPct)
           { Skip(skAtr, "minATR", dir, price, ordn, StringFormat(" atr%%=%.3f < %.2f", atr / price * 100.0, minAtrPct)); continue; }

         double spr = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * point;
         if(InpMaxSpreadATR > 0.0 && spr / atr > InpMaxSpreadATR)
           { Skip(skSpread, "спред", dir, price, ordn, StringFormat(" %.2fATR > %.2f", spr / atr, InpMaxSpreadATR)); continue; }
         if(CountPos() >= maxPos) { Skip(skPos, "maxPos", dir, price, ordn, StringFormat(" %d", maxPos)); continue; }

         int di = (dir > 0) ? 1 : 0;
         if(InpDedupSec > 0 && g_lastDirEntry[di] > 0 &&
            TimeCurrent() - g_lastDirEntry[di] < InpDedupSec)
           { Skip(skDedT, "дедуп між ногами (час)", dir, price, ordn); continue; }

         if(pend && InpDedupATR > 0.0 && GroupPendingNear(dir, entry, InpDedupATR * atr))
           { Skip(skDedP, "дедуп (ліміт групи поруч)", dir, price, ordn); continue; }

         if(!AccountGuardOK()) { Skip(skGuard, "запобіжник рахунку", dir, price, ordn); continue; }
         if(!TradeEnvOK())     { Skip(skEnv, "середовище торгівлі", dir, price, ordn); continue; }
         if(FridayLate())      { Skip(skFri, "п'ятниця", dir, price, ordn); continue; }                 // v2.07
         if(SessionBlocked())  { Skip(skSes, "сесійне вікно", dir, price, ordn,
                                      StringFormat(" %d–%d сервер", InpSesFrom, InpSesTo)); continue; }  // v2.08

         double sl = (dir > 0) ? entry - risk : entry + risk;
         double tp = (dir > 0) ? entry + InpRR * risk : entry - InpRR * risk;
         if(!ClampStops(dir > 0, entry, sl, tp)) { Skip(skOther, "стопи (stops level)", dir, price, ordn); continue; }
         double lot = CalcLot(MathAbs(entry - sl), InpRiskPercent * RiskMult());   // v2.06 PC, v2.12 ER
         if(lot <= 0.0) { Skip(skLot, "лот=0", dir, price, ordn); continue; }

         string cmt = StringFormat("ZOSM %s o%d w%d%s", name, ordn, wt, (pend ? " R" : ""));
         bool sent = Send(dir > 0, pend, lot, entry, sl, tp, cmt);
         if(sent)
           {
            g_lastDirEntry[di] = TimeCurrent();
            entries++;
            break;
           }
         nFail++;
        }
     }

   bool              Send(const bool isBuy, const bool pend, const double lot, const double price,
                          const double sl, const double tp, const string cmt)
     {
      if(InpDryRun)
        {
         Log(StringFormat("%s DRY %s %s lot=%.2f @%.5f sl=%.5f tp=%.5f", Tag(),
                          (isBuy ? "BUY" : "SELL"), (pend ? "LIMIT" : "MKT"), lot, price, sl, tp));
         return(true);
        }
      g_trade.SetExpertMagicNumber(magic);
      g_trade.SetDeviationInPoints((ulong)InpSlippagePts);
      bool ok;
      if(pend)
         ok = isBuy ? g_trade.BuyLimit(lot, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, cmt)
                    : g_trade.SellLimit(lot, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, cmt);
      else
         ok = isBuy ? g_trade.Buy(lot, _Symbol, 0.0, sl, tp, cmt)
                    : g_trade.Sell(lot, _Symbol, 0.0, sl, tp, cmt);
      uint ret = g_trade.ResultRetcode();
      if(ok && (ret == TRADE_RETCODE_DONE || ret == TRADE_RETCODE_PLACED || ret == TRADE_RETCODE_DONE_PARTIAL))
        {
         Log(StringFormat("%s %s %s lot=%.2f @%.5f sl=%.5f tp=%.5f ticket=%I64u", Tag(),
                          (pend ? "PENDING" : "OPEN"), (isBuy ? "BUY" : "SELL"), lot, price, sl, tp,
                          g_trade.ResultOrder()));
         return(true);
        }
      Log(StringFormat("%s ВІДМОВА ret=%u (%s) lot=%.2f @%.5f", Tag(), ret,
                       g_trade.ResultRetcodeDescription(), lot, price));
      return(false);
     }

   //--- відновлення стану з історії
   void              Rebuild()
     {
      int want = InpRebuildBars;
      if(want < InpLifeBars + 300) want = InpLifeBars + 300;
      MqlRates r[];
      ArraySetAsSeries(r, false);
      int got = CopyRates(_Symbol, tf, 1, want, r);
      if(got <= InpATRPeriod + InpDepth + 10)
        {
         Log(StringFormat("%s Rebuild: історії мало (%d) — старт з нуля", Tag(), got));
         lastBarTime = iTime(_Symbol, tf, 0);
         return;
        }
      double a[];
      ArraySetAsSeries(a, false);
      int gotA = CopyBuffer(atrHandle, 0, 1, got, a);
      if(gotA != got)
        {
         Log(StringFormat("%s Rebuild: ATR %d != барів %d — старт з нуля", Tag(), gotA, got));
         lastBarTime = iTime(_Symbol, tf, 0);
         return;
        }
      rebuilding = true;
      for(int i = 0; i < got; i++)
        {
         barIdx++;
         BufPut(barIdx, r[i].high, r[i].low);
         ProcessBar(barIdx, r[i].time, r[i].open, r[i].high, r[i].low, r[i].close, a[i], false);
         ZigZagStep(barIdx, r[i].high, r[i].low, r[i].close, a[i]);
         Purge(barIdx);
        }
      rebuilding = false;
      lastBarTime = iTime(_Symbol, tf, 0);
      Log(StringFormat("%s Rebuild: %d барів | півотів %d | рівнів %d | zz=%d",
                       Tag(), got, ArraySize(piv), ArraySize(lvl), zzTrend));
     }

   //--- новий бар ноги
   // v2.07: нога D — п'ятниця після InpD_FriCloseHour
   bool              FridayLate()
     {
      if(FriLateAll()) return(true);
      if(name != "D" || InpD_FriCloseHour < 0) return(false);
      MqlDateTime dt;
      TimeToStruct(TimeCurrent(), dt);
      return(dt.day_of_week == 5 && dt.hour >= InpD_FriCloseHour);
     }

   void              CloseWeekend()
     {
      if(!on || InpDryRun || !FridayLate()) return;
      CloseMagic(magic, Tag());
     }

   // v2.08: сесійне вікно без входів для A і C
   bool              SessionBlocked()
     {
      if(!InpSesBlockAC || (name != "A" && name != "C")) return(false);
      MqlDateTime dt;
      TimeToStruct(TimeCurrent(), dt);
      return(dt.hour >= InpSesFrom && dt.hour < InpSesTo);
     }

   void              OnTickLeg()
     {
      if(!on) return;
      datetime bt = iTime(_Symbol, tf, 0);
      if(bt == 0 || bt == lastBarTime) return;
      bool first = (lastBarTime == 0);
      lastBarTime = bt;
      if(first) return;

      MqlRates r[];
      ArraySetAsSeries(r, true);
      if(CopyRates(_Symbol, tf, 1, 1, r) != 1) return;
      if(r[0].open <= 0.0 || r[0].close <= 0.0) return;

      barIdx++;
      BufPut(barIdx, r[0].high, r[0].low);

      double a[];
      ArraySetAsSeries(a, true);
      if(CopyBuffer(atrHandle, 0, 1, 1, a) != 1)
        {
         ZigZagStep(barIdx, r[0].high, r[0].low, r[0].close, 0.0);
         Purge(barIdx);
         return;
        }
      // ПОРЯДОК: спершу сигнали на рівнях, відомих ДО бару, потім ZigZag цим баром
      ProcessBar(barIdx, r[0].time, r[0].open, r[0].high, r[0].low, r[0].close, a[0], true);
      ZigZagStep(barIdx, r[0].high, r[0].low, r[0].close, a[0]);
      Purge(barIdx);

      if(InpHeartbeatBars > 0 && barIdx - lastHB >= InpHeartbeatBars)
        {
         lastHB = barIdx;
         Log(StringFormat("HB %s рівнів=%d поз=%d входів=%d | %s | екв=%.2f",
                          Tag(), ArraySize(lvl), CountPos(), entries, Stats(),
                          AccountInfoDouble(ACCOUNT_EQUITY)));
        }
     }
  };

CLeg g_legs[NLEGS];

//+------------------------------------------------------------------+
//| v2.05: НОГА E — TRAIL                                            |
//+------------------------------------------------------------------+
class CTrailLeg
  {
public:
   bool              on;
   int               hATR4, hADX1, hADX4;
   datetime          lastBarM15, lastEntry;
   int               entries;
   // v2.09: діагностика
   datetime          lastHB;
   long              cBars, cPos, cFri, cCool, cNoReg, cNoBrk, cAgainst, cVol, cGuard, cLot, cOther, cFail;

                     CTrailLeg() { on = false; hATR4 = hADX1 = hADX4 = INVALID_HANDLE; }

   bool              Init()
     {
      on = InpE_On; lastBarM15 = 0; lastEntry = 0; entries = 0;
      lastHB = 0;
      cBars = 0; cPos = 0; cFri = 0; cCool = 0; cNoReg = 0; cNoBrk = 0; cAgainst = 0;
      cVol = 0; cGuard = 0; cLot = 0; cOther = 0; cFail = 0;
      if(!on) return(true);
      hATR4 = iATR(_Symbol, PERIOD_H4, 14);
      hADX1 = iADX(_Symbol, PERIOD_D1, InpE_DIPeriod);
      hADX4 = iADX(_Symbol, PERIOD_H4, InpE_DIPeriod);
      if(hATR4 == INVALID_HANDLE || hADX1 == INVALID_HANDLE || hADX4 == INVALID_HANDLE)
        { Log("E: INIT FAIL хендли індикаторів"); return(false); }
      // пауза після рестарту: час останнього входу ноги E з відкритих позицій
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpE_Magic) continue;
         datetime t = (datetime)PositionGetInteger(POSITION_TIME);
         if(t > lastEntry) lastEntry = t;
        }
      Log(StringFormat("LEG E TRAIL risk=%.2f%% SL=%.1fxATR4 trail=%.1fxATR4 vol=%s magic=%I64d",
                       InpE_Risk, InpE_SL_ATR4, InpE_Trail_ATR4, (InpE_UseVolGate ? "on" : "off"), InpE_Magic));
      return(true);
     }

   void              Release()
     {
      if(hATR4 != INVALID_HANDLE) IndicatorRelease(hATR4);
      if(hADX1 != INVALID_HANDLE) IndicatorRelease(hADX1);
      if(hADX4 != INVALID_HANDLE) IndicatorRelease(hADX4);
     }

   double            ATR4()
     {
      double b[1];
      if(CopyBuffer(hATR4, 0, 1, 1, b) < 1) return(0.0);
      return(b[0]);
     }

   bool              DIDiff(const int h, double &out)
     {
      double p[1], m[1];
      if(CopyBuffer(h, 1, 1, 1, p) < 1) return(false);
      if(CopyBuffer(h, 2, 1, 1, m) < 1) return(false);
      out = p[0] - m[0];
      return(true);
     }

   int               RegimeEx(double &d1, double &d4)
     {
      d1 = 0.0; d4 = 0.0;
      if(!DIDiff(hADX1, d1) || !DIDiff(hADX4, d4)) return(0);
      if(d1 > 0.0 && d4 > 0.0) return(1);
      if(d1 < 0.0 && d4 < 0.0) return(-1);
      return(0);
     }

   int               Regime() { double d1, d4; return(RegimeEx(d1, d4)); }

   // v2.09: відношення обсягу останнього закритого H4 до SMA (як у VolOK v2.05)
   bool              VolRatio(double &ratio)
     {
      ratio = 0.0;
      long v[];
      ArraySetAsSeries(v, true);
      int need = InpE_VolMA + 2;
      if(CopyTickVolume(_Symbol, PERIOD_H4, 1, need, v) < need) return(false);
      double sum = 0.0;
      for(int i = 0; i < InpE_VolMA; i++) sum += (double)v[i];
      double avg = sum / (double)InpE_VolMA;
      if(avg <= 0.0) return(false);
      ratio = (double)v[0] / avg;
      return(true);
     }

   int               Breakout()
     {
      double hh = -DBL_MAX, ll = DBL_MAX;
      for(int i = 2; i <= InpE_BreakBars + 1; i++)
        {
         double h = iHigh(_Symbol, PERIOD_M15, i), l = iLow(_Symbol, PERIOD_M15, i);
         if(h <= 0.0 || l <= 0.0) return(0);
         if(h > hh) hh = h;
         if(l < ll) ll = l;
        }
      double c1 = iClose(_Symbol, PERIOD_M15, 1);
      if(c1 <= 0.0) return(0);
      if(c1 > hh) return(1);
      if(c1 < ll) return(-1);
      return(0);
     }

   int               CountPos()
     {
      int c = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpE_Magic) c++;
        }
      return(c);
     }

   string            Stats()
     {
      return(StringFormat("барів=%I64d нема_режиму=%I64d нема_пробою=%I64d пробій_проти=%I64d обсяг=%I64d пауза=%I64d поз=%I64d пт=%I64d guard=%I64d лот=%I64d інше=%I64d відмов=%I64d входів=%d",
                          cBars, cNoReg, cNoBrk, cAgainst, cVol, cCool, cPos, cFri, cGuard, cLot, cOther, cFail, entries));
     }

   void              SkipLog(const string why, const int rg)
     {
      if(InpLogSkips) Log(StringFormat("E SKIP %s | %s (режим і пробій збіглись)", why, DirStr(rg)));
     }

   // v2.09: heartbeat раз на InpDiagHBMin хв
   void              HB()
     {
      if(InpDiagHBMin <= 0) return;
      datetime now = TimeCurrent();
      if(lastHB > 0 && now - lastHB < (long)InpDiagHBMin * 60) return;
      lastHB = now;
      double d1 = 0.0, d4 = 0.0;
      int rg = RegimeEx(d1, d4);
      int bo = Breakout();
      double vr = 0.0;
      bool vok = VolRatio(vr);
      long cd = 0;
      if(lastEntry > 0)
        {
         cd = (long)InpE_CooldownM15 * 900 - (long)(now - lastEntry);
         if(cd < 0) cd = 0;
        }
      Log(StringFormat("HB E/TRAIL режим=%s DI_D1=%.1f DI_H4=%.1f пробій=%s обсяг=%s/%.2f%s поз=%d пауза=%dхв множ=%.2f | %s",
                       (rg > 0 ? "UP" : (rg < 0 ? "DOWN" : "немає")), d1, d4,
                       (bo > 0 ? "UP" : (bo < 0 ? "DOWN" : "немає")),
                       (vok ? DoubleToString(vr, 2) : "н/д"), InpE_VolMult, (InpE_UseVolGate ? "" : " (гейт вимк.)"),
                       CountPos(), (int)(cd / 60), PCMult(), Stats()));
     }

   void              Manage()
     {
      if(!on || InpDryRun) return;
      double a4 = ATR4();
      if(a4 <= 0.0) return;
      double trail = InpE_Trail_ATR4 * a4;
      int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      double guard = (double)MathMax(SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
                                     SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL)) * pt;
      if(FriLateAll()) { CloseMagic(InpE_Magic, "E"); return; }   // v2.08
      g_trade.SetExpertMagicNumber(InpE_Magic);
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpE_Magic) continue;
         datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
         if(TimeCurrent() - opened >= (long)InpE_MaxHoldDays * 86400)
           {
            if(g_trade.PositionClose(tk)) Log(StringFormat("E TIMEOUT close %I64u", tk));
            continue;
           }
         double cur = PositionGetDouble(POSITION_SL);
         if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
           {
            double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            double nsl = NormalizeDouble(bid - trail, dg);
            if(nsl > cur && (bid - nsl) > guard)
               g_trade.PositionModify(tk, nsl, 0.0);
           }
         else
           {
            double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double nsl = NormalizeDouble(ask + trail, dg);
            if((cur <= 0.0 || nsl < cur) && (nsl - ask) > guard)
               g_trade.PositionModify(tk, nsl, 0.0);
           }
        }
     }

   void              OnTickLeg()
     {
      if(!on) return;
      datetime b = iTime(_Symbol, PERIOD_M15, 0);
      if(b == 0 || b == lastBarM15) return;
      bool first = (lastBarM15 == 0);
      lastBarM15 = b;
      if(first) return;
      HB();                                                        // v2.09
      cBars++;
      double a4 = ATR4();
      if(a4 <= 0.0) { cOther++; return; }
      if(CountPos() >= 1) { cPos++; return; }
      if(FriLateAll()) { cFri++; return; }                         // v2.08
      if(lastEntry > 0 && TimeCurrent() - lastEntry < (long)InpE_CooldownM15 * 900) { cCool++; return; }
      int rg = Regime();
      if(rg == 0) { cNoReg++; return; }
      int bo = Breakout();
      if(bo == 0)  { cNoBrk++; return; }
      if(bo != rg) { cAgainst++; return; }
      if(InpE_UseVolGate)
        {
         double vr = 0.0;
         if(!VolRatio(vr) || vr <= InpE_VolMult)
           {
            cVol++;
            SkipLog(StringFormat("обсяг H4 %.2f <= %.2f x SMA%d", vr, InpE_VolMult, InpE_VolMA), rg);
            return;
           }
        }
      if(!AccountGuardOK() || !TradeEnvOK()) { cGuard++; SkipLog("запобіжник/середовище", rg); return; }

      double slDist = InpE_SL_ATR4 * a4;
      double lot = CalcLot(slDist, InpE_Risk * RiskMult());   // v2.06 PC, v2.12 ER
      if(lot <= 0.0) { cLot++; SkipLog("лот=0", rg); return; }
      int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      g_trade.SetExpertMagicNumber(InpE_Magic);
      g_trade.SetDeviationInPoints((ulong)InpSlippagePts);
      bool ok;
      if(InpDryRun)
        {
         Log(StringFormat("E DRY %s lot=%.2f slDist=%.2f", (rg > 0 ? "BUY" : "SELL"), lot, slDist));
         lastEntry = TimeCurrent();
         return;
        }
      if(rg > 0)
        {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         ok = g_trade.Buy(lot, _Symbol, 0.0, NormalizeDouble(ask - slDist, dg), 0.0, "ZOSM E TRAIL");
        }
      else
        {
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         ok = g_trade.Sell(lot, _Symbol, 0.0, NormalizeDouble(bid + slDist, dg), 0.0, "ZOSM E TRAIL");
        }
      if(ok && (g_trade.ResultRetcode() == TRADE_RETCODE_DONE || g_trade.ResultRetcode() == TRADE_RETCODE_PLACED))
        {
         lastEntry = TimeCurrent(); entries++;
         Log(StringFormat("E OPEN %s lot=%.2f slDist=%.2f atr4=%.2f", (rg > 0 ? "BUY" : "SELL"), lot, slDist, a4));
        }
      else
        {
         cFail++;
         Log(StringFormat("E ВІДМОВА ret=%u (%s)", g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription()));
        }
     }
  };

CTrailLeg g_trail;

//+------------------------------------------------------------------+
//| v2.06: НОГА F — повернення в діапазон (лише «плато після шоку»)  |
//+------------------------------------------------------------------+
class CRangeLeg
  {
public:
   bool              on;
   datetime          lastBarM15;
   int               entries;
   // v2.09: діагностика
   datetime          lastHB;
   long              cBars, cOff, cFri, cPos, cNoTouch, cGuard, cRisk, cLot, cOther, cFail;

                     CRangeLeg() { on = false; }

   bool              Init()
     {
      on = InpF_On; lastBarM15 = 0; entries = 0;
      lastHB = 0;
      cBars = 0; cOff = 0; cFri = 0; cPos = 0; cNoTouch = 0; cGuard = 0; cRisk = 0; cLot = 0; cOther = 0; cFail = 0;
      if(!on) return(true);
      if(InpF_RangeDays < 2 || InpF_Zone <= 0.0 || InpF_Zone >= 0.5 || InpF_SL_ATRD <= 0.0 || InpF_Risk <= 0.0)
        { Log("F: INIT FAIL некоректні параметри"); return(false); }
      Log(StringFormat("LEG F RANGE risk=%.2f%% діапазон=%dд зона=%.2f SL=%.2fxATR_D1 hold=%dд magic=%I64d",
                       InpF_Risk, InpF_RangeDays, InpF_Zone, InpF_SL_ATRD, InpF_MaxHoldDays, InpF_Magic));
      return(true);
     }

   int               CountPos()
     {
      int c = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpF_Magic) c++;
        }
      return(c);
     }

   string            Stats()
     {
      return(StringFormat("барів=%I64d поза_станом=%I64d поз=%I64d пт=%I64d нема_дотику=%I64d guard=%I64d ризик=%I64d лот=%I64d інше=%I64d відмов=%I64d входів=%d",
                          cBars, cOff, cPos, cFri, cNoTouch, cGuard, cRisk, cLot, cOther, cFail, entries));
     }

   void              SkipLog(const string why, const int dir)
     {
      if(InpLogSkips) Log(StringFormat("F SKIP %s | %s (дотик межі з відбоєм)", why, DirStr(dir)));
     }

   // v2.09: heartbeat раз на InpDiagHBMin хв (заодно показує стан режиму PC)
   void              HB()
     {
      if(InpDiagHBMin <= 0) return;
      datetime now = TimeCurrent();
      if(lastHB > 0 && now - lastHB < (long)InpDiagHBMin * 60) return;
      lastHB = now;
      string st = (!g_pcReady ? "не готовий" : (g_pcState ? "ПЛАТО (F торгує)" : "вимк."));
      double W = g_pcHi - g_pcLo;
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double posPct = (W > 0.0) ? (bid - g_pcLo) / W * 100.0 : 0.0;
      Log(StringFormat("HB F/RANGE стан=%s шок=%.2f (поріг %.2f) ER%d=%.2f (поріг %.2f) діапазон=%.2f–%.2f ціна=%.0f%% зони<%.0f%%/>%.0f%% ATR_D1=%.2f поз=%d | %s",
                       st, g_pcRatio, InpPC_ShockMult, InpPC_ErDays, g_pcEr, InpPC_ErMax,
                       g_pcLo, g_pcHi, posPct, InpF_Zone * 100.0, 100.0 - InpF_Zone * 100.0,
                       g_pcAtrD, CountPos(), Stats()));
     }

   void              Manage()
     {
      if(!on || InpDryRun) return;
      if(FriLateAll()) { CloseMagic(InpF_Magic, "F"); return; }   // v2.08
      if(InpF_MaxHoldDays <= 0) return;
      g_trade.SetExpertMagicNumber(InpF_Magic);
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpF_Magic) continue;
         datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
         if(TimeCurrent() - opened >= (long)InpF_MaxHoldDays * 86400)
            if(g_trade.PositionClose(tk, (ulong)InpSlippagePts))
               Log(StringFormat("F TIMEOUT close %I64u", tk));
        }
     }

   void              OnTickLeg()
     {
      if(!on) return;
      datetime b = iTime(_Symbol, PERIOD_M15, 0);
      if(b == 0 || b == lastBarM15) return;
      bool first = (lastBarM15 == 0);
      lastBarM15 = b;
      if(first) return;
      HB();                                                        // v2.09
      cBars++;
      if(!g_pcReady || !g_pcState) { cOff++; return; }
      if(FriLateAll()) { cFri++; return; }                         // v2.08
      if(CountPos() >= 1) { cPos++; return; }
      double hi = g_pcHi, lo = g_pcLo, atrD = g_pcAtrD;
      double W = hi - lo;
      if(W <= 0.0 || atrD <= 0.0) { cOther++; return; }

      MqlRates r[];
      ArraySetAsSeries(r, true);
      if(CopyRates(_Symbol, PERIOD_M15, 1, 1, r) != 1) { cOther++; return; }
      double h = r[0].high, l = r[0].low, c = r[0].close, rng = h - l;
      double top = hi - InpF_Zone * W, bot = lo + InpF_Zone * W, mid = 0.5 * (hi + lo);
      int dir = 0;
      if(h >= top && c < h - 0.3 * rng && c > mid)      dir = -1;
      else if(l <= bot && c > l + 0.3 * rng && c < mid) dir = 1;
      if(dir == 0) { cNoTouch++; return; }
      if(!AccountGuardOK() || !TradeEnvOK()) { cGuard++; SkipLog("запобіжник/середовище", dir); return; }
      if(!g_sym.RefreshRates()) { cOther++; return; }

      double entry = (dir > 0) ? g_sym.Ask() : g_sym.Bid();
      double ext   = (dir > 0) ? MathMin(l, lo) : MathMax(h, hi);
      double sl    = (dir > 0) ? ext - InpF_SL_ATRD * atrD : ext + InpF_SL_ATRD * atrD;
      double risk  = MathAbs(entry - sl);
      if(risk <= 0.2 * atrD) { cRisk++; SkipLog(StringFormat("ризик %.2f <= 0.2xATR_D1", risk), dir); return; }
      if((dir > 0 && sl >= entry) || (dir < 0 && sl <= entry)) { cRisk++; SkipLog("SL з неправильного боку", dir); return; }
      double tp = mid;
      if(dir > 0 && tp <= entry + 0.5 * risk) tp = entry + risk;
      if(dir < 0 && tp >= entry - 0.5 * risk) tp = entry - risk;
      if(!ClampStops(dir > 0, entry, sl, tp)) { cRisk++; SkipLog("стопи (stops level)", dir); return; }
      double lot = CalcLot(MathAbs(entry - sl), InpF_Risk);
      if(lot <= 0.0) { cLot++; SkipLog("лот=0", dir); return; }

      if(InpDryRun)
        {
         Log(StringFormat("F DRY %s lot=%.2f @%.2f sl=%.2f tp=%.2f", (dir > 0 ? "BUY" : "SELL"), lot, entry, sl, tp));
         return;
        }
      g_trade.SetExpertMagicNumber(InpF_Magic);
      g_trade.SetDeviationInPoints((ulong)InpSlippagePts);
      bool ok;
      if(dir > 0) ok = g_trade.Buy(lot, _Symbol, 0.0, sl, tp, "ZOSM F RANGE");
      else        ok = g_trade.Sell(lot, _Symbol, 0.0, sl, tp, "ZOSM F RANGE");
      uint ret = g_trade.ResultRetcode();
      if(ok && (ret == TRADE_RETCODE_DONE || ret == TRADE_RETCODE_PLACED))
        {
         entries++;
         Log(StringFormat("F OPEN %s lot=%.2f @%.2f sl=%.2f tp=%.2f | діапазон %.2f–%.2f", (dir > 0 ? "BUY" : "SELL"),
                          lot, entry, sl, tp, lo, hi));
        }
      else
        {
         cFail++;
         Log(StringFormat("F ВІДМОВА ret=%u (%s)", ret, g_trade.ResultRetcodeDescription()));
        }
     }
  };

CRangeLeg g_range;

//==================== v2.11: НОГА G — ДРЕЙФ ========================
class CDriftLeg
  {
public:
   bool              on;
   datetime          lastBarH1, lastDay, lastHB;
   int               dirToday, entries;
   double            zToday;
   long              cBars, cFlat, cPos, cGuard, cLot, cFail, cFri;

                     CDriftLeg() { on = false; }

   bool              Init()
     {
      on = InpG_On; lastBarH1 = 0; lastDay = 0; lastHB = 0; dirToday = 0; zToday = 0.0; entries = 0;
      cBars = 0; cFlat = 0; cPos = 0; cGuard = 0; cLot = 0; cFail = 0; cFri = 0;
      if(!on) return(true);
      if(InpG_Risk <= 0.0 || InpG_LookDays < 5 || InpG_SL_ATRH1 <= 0.0 || InpG_MaxHoldHours < 1)
        { Log("G: INIT FAIL некоректні параметри"); return(false); }
      Log(StringFormat("LEG G DRIFT risk=%.2f%% look=%dд minZ=%.2f SL=%.1fxATR_H1 hold=%dг magic=%I64d",
                       InpG_Risk, InpG_LookDays, InpG_MinZ, InpG_SL_ATRH1, InpG_MaxHoldHours, InpG_Magic));
      return(true);
     }

   string            Stats()
     {
      return(StringFormat("барів=%I64d без_імпульсу=%I64d поз=%I64d пт=%I64d guard=%I64d лот=%I64d відмов=%I64d входів=%d",
                          cBars, cFlat, cPos, cFri, cGuard, cLot, cFail, entries));
     }

   int               CountPos()
     {
      int c = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpG_Magic) c++;
        }
      return(c);
     }

   // напрям дня з закритих D1 (вчора і раніше), рахується раз на день
   void              UpdateDir()
     {
      datetime d0 = iTime(_Symbol, PERIOD_D1, 0);
      if(d0 == 0 || d0 == lastDay) return;
      MqlRates r[];
      ArraySetAsSeries(r, true);
      int need = MathMax(InpG_LookDays, 15) + 2;
      if(CopyRates(_Symbol, PERIOD_D1, 1, need, r) < need) return;   // r[0] = вчора
      double atr = 0.0;
      for(int k = 1; k <= 14; k++) atr += (r[k].high - r[k].low);
      atr /= 14.0;
      if(atr <= 0.0) return;
      double mv = r[0].close - r[InpG_LookDays].close;
      zToday = mv / (atr * MathSqrt((double)InpG_LookDays));
      dirToday = (zToday >= InpG_MinZ) ? 1 : ((zToday <= -InpG_MinZ) ? -1 : 0);
      lastDay = d0;
      Log(StringFormat("G DAY напрям=%s z=%.2f (поріг %.2f) рух%dд=%.2f ATR_D1=%.2f",
                       (dirToday > 0 ? "BUY" : (dirToday < 0 ? "SELL" : "немає")), zToday, InpG_MinZ, InpG_LookDays, mv, atr));
     }

   double            AtrH1()
     {
      MqlRates r[];
      ArraySetAsSeries(r, true);
      if(CopyRates(_Symbol, PERIOD_H1, 1, 15, r) < 15) return(0.0);
      double s = 0.0;
      for(int k = 0; k < 14; k++)
        {
         double pc = r[k + 1].close;
         s += MathMax(r[k].high - r[k].low, MathMax(MathAbs(r[k].high - pc), MathAbs(r[k].low - pc)));
        }
      return(s / 14.0);
     }

   void              Manage()
     {
      if(!on || InpDryRun) return;
      if(FriLateAll()) { CloseMagic(InpG_Magic, "G"); return; }
      g_trade.SetExpertMagicNumber(InpG_Magic);
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong tk = PositionGetTicket(i);
         if(tk == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol || PositionGetInteger(POSITION_MAGIC) != InpG_Magic) continue;
         datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
         if(TimeCurrent() - opened >= (long)InpG_MaxHoldHours * 3600)
            if(g_trade.PositionClose(tk, (ulong)InpSlippagePts))
               Log(StringFormat("G TIMEOUT close %I64u (%dг)", tk, InpG_MaxHoldHours));
        }
     }

   void              OnTickLeg()
     {
      if(!on) return;
      datetime b = iTime(_Symbol, PERIOD_H1, 0);
      if(b == 0 || b == lastBarH1) return;
      bool first = (lastBarH1 == 0);
      lastBarH1 = b;
      UpdateDir();
      if(InpDiagHBMin > 0 && (lastHB == 0 || TimeCurrent() - lastHB >= (long)InpDiagHBMin * 60))
        {
         lastHB = TimeCurrent();
         Log(StringFormat("HB G/DRIFT напрям=%s z=%.2f поз=%d | %s", (dirToday > 0 ? "BUY" : (dirToday < 0 ? "SELL" : "немає")),
                          zToday, CountPos(), Stats()));
        }
      if(first) return;
      cBars++;
      if(FriLateAll()) { cFri++; return; }
      if(dirToday == 0) { cFlat++; return; }
      if(CountPos() >= 1) { cPos++; return; }
      if(!AccountGuardOK() || !TradeEnvOK()) { cGuard++; return; }
      if(!g_sym.RefreshRates()) return;
      double atr = AtrH1();
      if(atr <= 0.0) return;
      int dir = dirToday;
      double entry = (dir > 0) ? g_sym.Ask() : g_sym.Bid();
      if(InpMaxSpreadATR > 0.0 && (g_sym.Ask() - g_sym.Bid()) > InpMaxSpreadATR * atr) { cGuard++; return; }
      double sl = (dir > 0) ? entry - InpG_SL_ATRH1 * atr : entry + InpG_SL_ATRH1 * atr;
      double tp = 0.0;
      int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      sl = NormalizeDouble(sl, dg);
      double lot = CalcLot(MathAbs(entry - sl), InpG_Risk);
      if(lot <= 0.0) { cLot++; return; }
      if(InpDryRun)
        {
         Log(StringFormat("G DRY %s lot=%.2f @%.2f sl=%.2f z=%.2f", DirStr(dir), lot, entry, sl, zToday));
         return;
        }
      g_trade.SetExpertMagicNumber(InpG_Magic);
      g_trade.SetDeviationInPoints((ulong)InpSlippagePts);
      bool ok;
      if(dir > 0) ok = g_trade.Buy(lot, _Symbol, 0.0, sl, tp, "ZOSM G DRIFT");
      else        ok = g_trade.Sell(lot, _Symbol, 0.0, sl, tp, "ZOSM G DRIFT");
      uint ret = g_trade.ResultRetcode();
      if(ok && (ret == TRADE_RETCODE_DONE || ret == TRADE_RETCODE_PLACED))
        {
         entries++;
         Log(StringFormat("G OPEN %s lot=%.2f @%.2f sl=%.2f ATR_H1=%.2f z=%.2f вихід через %dг",
                          DirStr(dir), lot, entry, sl, atr, zToday, InpG_MaxHoldHours));
        }
      else
        {
         cFail++;
         Log(StringFormat("G ВІДМОВА ret=%u (%s)", ret, g_trade.ResultRetcodeDescription()));
        }
     }
  };

CDriftLeg g_drift;

//==================== СТАНДАРТНІ ОБРОБНИКИ =========================
int OnInit()
  {
   Log(StringFormat("INIT_START %s symbol=%s", g_version, _Symbol));
   if((ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL && !InpAllowLiveTrading)
     {
      Log("INIT_FAILED: реальний рахунок, InpAllowLiveTrading=false");
      return(INIT_FAILED);
     }
   if(!g_sym.Name(_Symbol)) { Log("INIT_FAILED: символ недоступний"); return(INIT_FAILED); }
   g_sym.RefreshRates();
   if(InpRiskPercent <= 0.0 || InpRR <= 0.0 || InpDepth < 1 || InpLifeBars < 1 ||
      InpRetestBars < 1 || InpMinRiskATR >= InpMaxRiskATR || InpExtBars + 2 >= BUFSZ)
     {
      Log("INIT_FAILED: некоректні вхідні параметри");
      return(INIT_FAILED);
     }
   if(InpA_Magic == InpB_Magic || InpA_Magic == InpC_Magic || InpB_Magic == InpC_Magic ||
      InpD_Magic == InpA_Magic || InpD_Magic == InpB_Magic || InpD_Magic == InpC_Magic)
     {
      Log("INIT_FAILED: Magic ніг мають бути різні");
      return(INIT_FAILED);
     }

   long fm = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((fm & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)      g_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((fm & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC) g_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else                                                     g_trade.SetTypeFilling(ORDER_FILLING_RETURN);
   g_trade.SetAsyncMode(false);

   g_lastDirEntry[0] = 0; g_lastDirEntry[1] = 0;
   g_dayStamp = -1; g_initBal = (InpInitialBalance > 0.0) ? InpInitialBalance : AccountInfoDouble(ACCOUNT_BALANCE);
   g_guardBlocked = false; g_guardLastLog = 0;

   g_legs[0].Setup("A", InpA_On, InpA_TF, InpA_DevATR, InpA_MinAtr, InpA_MaxPos, InpA_Magic);
   g_legs[1].Setup("B", InpB_On, InpB_TF, InpB_DevATR, InpB_MinAtr, InpB_MaxPos, InpB_Magic);
   g_legs[2].Setup("C", InpC_On, InpC_TF, InpC_DevATR, InpC_MinAtr, InpC_MaxPos, InpC_Magic);
   g_legs[3].Setup("D", InpD_On, InpD_TF, InpD_DevATR, InpD_MinAtr, InpD_MaxPos, InpD_Magic,
                   InpD_Retest, InpD_Trend);
   for(int i = 0; i < NLEGS; i++)
     {
      if(!g_legs[i].Init()) return(INIT_FAILED);
      if(g_legs[i].on)
         Log(StringFormat("LEG %s tf=%s dev=%.1f minAtr%%=%.2f maxPos=%d magic=%I64d entry=%s trend=%s",
                          g_legs[i].name, EnumToString(g_legs[i].tf), g_legs[i].devATR,
                          g_legs[i].minAtrPct, g_legs[i].maxPos, g_legs[i].magic,
                          (g_legs[i].retest ? "RETEST" : "MARKET"), (g_legs[i].useTrend ? "on" : "off")));
     }
   if(!g_trail.Init()) return(INIT_FAILED);
   if(InpE_On && (InpE_Magic == InpA_Magic || InpE_Magic == InpB_Magic || InpE_Magic == InpC_Magic || InpE_Magic == InpD_Magic))
     { Log("INIT_FAILED: InpE_Magic збігається з magic іншої ноги"); return(INIT_FAILED); }
   if(InpF_On && (InpF_Magic == InpA_Magic || InpF_Magic == InpB_Magic || InpF_Magic == InpC_Magic ||
                  InpF_Magic == InpD_Magic || InpF_Magic == InpE_Magic))
     { Log("INIT_FAILED: InpF_Magic збігається з magic іншої ноги"); return(INIT_FAILED); }
   if(InpPC_RiskMult < 0.0 || InpPC_RiskMult > 1.0 || InpPC_AtrDays < 2 || InpPC_MedDays < 10 ||
      InpPC_ShockLook < 1 || InpPC_ErDays < 2)
     { Log("INIT_FAILED: некоректні параметри режиму PC"); return(INIT_FAILED); }
   if(!g_range.Init()) return(INIT_FAILED);
   if(InpG_On && (InpG_Magic == InpA_Magic || InpG_Magic == InpB_Magic || InpG_Magic == InpC_Magic ||
                  InpG_Magic == InpD_Magic || InpG_Magic == InpE_Magic || InpG_Magic == InpF_Magic))
     { Log("INIT_FAILED: InpG_Magic збігається з magic іншої ноги"); return(INIT_FAILED); }
   if(!g_drift.Init()) return(INIT_FAILED);
   UpdatePCState();
   UpdateERState();                        // v2.12
   Log(StringFormat("PC: старт стан=%s шок=%.2f ER=%.2f множник=%.2f", (g_pcState ? "on" : "off"), g_pcRatio, g_pcEr, PCMult()));
   if(InpTimerSec > 0) EventSetTimer(InpTimerSec);
   Log(StringFormat("INIT_OK %s | risk=%.2f%% RR=%.1f retest=%d trend=%dд dedup=%ds/%.2fATR dayStop=%.1f%% maxLoss(від старт.)=%.1f%% initBal=%.2f dry=%s logSkips=%s diagHB=%dхв",
                    g_version, InpRiskPercent, InpRR, InpRetestBars, InpTrendDays, InpDedupSec, InpDedupATR,
                    InpDailyStopPct, InpMaxLossPct, g_initBal, (InpDryRun ? "true" : "false"),
                    (InpLogSkips ? "on" : "off"), InpDiagHBMin));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   for(int i = 0; i < NLEGS; i++)
     {
      if(g_legs[i].on)
         Log(StringFormat("DEINIT %s входів=%d | %s", g_legs[i].Tag(), g_legs[i].entries, g_legs[i].Stats()));
      g_legs[i].Release();
     }
   if(g_trail.on) Log("DEINIT E/TRAIL | " + g_trail.Stats());
   g_trail.Release();
   if(g_range.on) Log("DEINIT F/RANGE | " + g_range.Stats());
   if(g_drift.on) Log("DEINIT G/DRIFT | " + g_drift.Stats());
   Log("DEINIT reason=" + IntegerToString(reason));
  }

//+------------------------------------------------------------------+
//| v2.01: заповнення ліміту групи -> зняти однонапрямлені дублікати |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || trans.symbol != _Symbol) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_ENTRY) != DEAL_ENTRY_IN) return;
   long mg = HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
   if(!IsGroupMagic(mg)) return;
   int dir = (HistoryDealGetInteger(trans.deal, DEAL_TYPE) == DEAL_TYPE_BUY) ? 1 : -1;
   double px = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
   double atr = 0.0;
   for(int i = 0; i < NLEGS; i++)
      if(g_legs[i].on && g_legs[i].magic == mg) atr = g_legs[i].lastAtr;
   if(atr <= 0.0) atr = g_legs[0].lastAtr;
   CancelGroupPendingNear(dir, px, InpDedupATR * atr);
   if(InpDedupSec > 0) g_lastDirEntry[(dir > 0) ? 1 : 0] = TimeCurrent();
  }

void OnTimer()
  {
   for(int i = 0; i < NLEGS; i++)
      g_legs[i].ManagePending();
  }

void OnTick()
  {
   AccountGuardOK();                       // оновлює денний якір; v2.09: логує зміну стану блоку
   UpdatePCState();                        // v2.06: раз на день D1
   UpdateERState();                        // v2.12: раз на день D1
   for(int i = 0; i < NLEGS; i++)
     {
      g_legs[i].ManagePending();
      g_legs[i].ManagePartial();
      g_legs[i].CloseWeekend();             // v2.07
      g_legs[i].OnTickLeg();
     }
   g_trail.Manage();
   g_trail.OnTickLeg();
   g_range.Manage();
   g_range.OnTickLeg();
   g_drift.Manage();                       // v2.11
   g_drift.OnTickLeg();
  }
//+------------------------------------------------------------------+
