//+------------------------------------------------------------------+
//|  BinanceLSZ_v1.08.mq5                                             |
//|  Індикатор: z-рівень Long/Short Ratio (Accounts) з Binance.       |
//|  Окреме вікно. Торгових функцій НЕМАЄ.                            |
//|                                                                   |
//|  ЩО ПОКАЗУЄ                                                       |
//|    z = (L/S зараз − середнє за вікно) / стандартне відхилення     |
//|    z >= +1.0  натовп перекошений у ЛОНГИ  -> сигнал SHORT         |
//|    z <= -1.0  перекошений у ШОРТИ         -> сигнал LONG          |
//|                                                                   |
//|  ВИМІРЯНО (BTCUSDT, 2021-01..2026-08, N=3352):                    |
//|    EV +0.636 ATR на угоду, t = 6.73, 6/6 прибуткових років        |
//|    контроль перемішаного сигналу  z = 6.48  PASS                  |
//|    блочний сурогат                z = 3.53  PASS                  |
//|  СТАТУС: перевірено ЛИШЕ на BTC. Крос-інструмент не пройдено.     |
//|                                                                   |
//|  ДЖЕРЕЛО ДАНИХ (обов'язково):                                     |
//|    сервіс BinanceLS_Feeder (MQL5\Services), період 5m,            |
//|    той самий символ. Він пише Common\Files\BinanceLS\SYM_5m.csv   |
//|                                                                   |
//|  v1.08 (2026-10-19) - ПАНЕЛЬ ЧИТАБЕЛЬНА                         |
//|   - Непрозора підкладка під текстом (лінії не просвічують).       |
//|   - Розмір шрифту, кут, відступи й колір фону - параметри.        |
//|   - Висота рядка від розміру шрифту, ширина фону - від тексту.    |
//|  v1.07 (2026-10-19) - ТОЧНІСТЬ НА СТАРШИХ ТФ + ДРУГА ЛІНІЯ      |
//|   - FIX: бар показує z на своєму ЗАКРИТТІ (остання точка, що     |
//|     вже опублікована до кінця бару: ts+5хв <= кінець бару).       |
//|     v1.06 брав точку на ВІДКРИТТІ бару -> на M30 лінія            |
//|     запізнювалась до 25 хв, на H1 до 55 хв (штучний «лаг»).       |
//|   - Нова лінія z6 (швидка, вікно InpZFastHours, як тригер D2      |
//|     у боті). Основна лінія = z24 (компас бота).                   |
//|   - Рівні ±1.5 (поріг перетину D2).                               |
//|   - Панель: сирий ratio + % лонг-акаунтів, z24, z6, компас.       |
//|  v1.06 (2026-10-05) - FIX FAIL: потрібне ще й закриття за        |
//|   відкриттям тригерної свічки (тіло пробою повністю перекрите).  |
//|   v1.05 давав FAIL на мікро-поверненні на кілька доларів.        |
//|  v1.05 (2026-10-05) - FAIL: хибний пробій після TRIGGER          |
//|   Протягом InpFailBars барів після TRIGGER LONG свічка закрилась |
//|   назад нижче рівня пробою -> червона стрілка вниз (FAIL).        |
//|   Дзеркально для SHORT -> синя стрілка вгору.                     |
//|   Підказка: чи це поглинання, стоп (екстремум TRIGGER/FAIL).     |
//|   SHORT TRIGGER з ARMED тепер OrangeRed (червоний = лише FAIL).   |
//|   FAIL = вихід з угоди. Розворот за FAIL - торгівля ЗА натовпом,  |
//|   окрема гіпотеза, потребує окремої перевірки.                    |
//|  v1.04 (2026-10-05) - СТАДІЇ ВХОДУ + СТРІЛКИ TRIGGER             |
//|   1 SETUP   z за порогом (з пам'яттю InpSetupMemory барів)        |
//|   2 ARMED   натовп САМ додає позиції проти нас понад свою         |
//|             звичайну реакцію на ціну (залишок регресії змін z     |
//|             на зміни ціни InpResidLag барів тому, β і α - лише    |
//|             з минулих барів, ковзне вікно InpResidWindow)         |
//|   3 TRIGGER закриття бару за макс/мін останніх InpStructBars      |
//|             барів проти натовпу (перший пробій, лише закриті      |
//|             бари - без перемальовування)                          |
//|   Стрілки: яскраві = TRIGGER при ARMED, тьмяні = без ARMED.       |
//|   Підказка стрілки: z, ARMED, стоп (мін/макс структури).          |
//|   Це ГІПОТЕЗА, не валідована система - перевіряти на історії.    |
//|  v1.03 (2026-10-05) - FIX: панель розбита на рядки (OBJ_LABEL   |
//|     обрізає текст після 63 символів), позначка "вище/в межах     |
//|     шуму" для лагу.                                               |
//|  v1.02 (2026-10-04) - ДІАГНОСТИКА ЛАГУ                            |
//|   - InpShiftBars: зсув лінії z у барах.                           |
//|       +N  вправо (z показується пізніше, ніж був)                 |
//|       -N  вліво  (z показується раніше = ЗАГЛЯДАННЯ ВПЕРЕД,       |
//|                    лише для аналізу, не для торгівлі)             |
//|     Сигнальні кольори й поріг рахуються від НЕзсунутого z.        |
//|   - Друга лінія: z ціни за те саме вікно, в тому ж масштабі -     |
//|     лінії можна порівнювати без ручного масштабування.            |
//|   - Друга панель: кореляція змін z натовпу зі змінами ціни        |
//|     при поточному зсуві + автопошук найсильнішого лагу.           |
//|       лаг > 0  z натовпу ВИПЕРЕДЖАЄ ціну                          |
//|       лаг < 0  z натовпу ЗАПІЗНЮЄТЬСЯ за ціною                    |
//|     + показ GMT-зсуву, який застосовано (діагностика часу).       |
//|  v1.01 - дані з CSV фідера, переведення UTC -> час сервера.       |
//+------------------------------------------------------------------+
#property copyright   "ResearchOS"
#property version     "1.08"
#property description "z-рівень Long/Short Ratio з Binance + зсув і аналіз лагу. Потрібен сервіс BinanceLS_Feeder."

#property indicator_separate_window
#property indicator_buffers 4
#property indicator_plots   3

#property indicator_label1  "L/S z (основне вікно)"
#property indicator_type1   DRAW_COLOR_LINE
#property indicator_color1  clrGray, clrTomato, clrMediumSeaGreen
#property indicator_style1  STYLE_SOLID
#property indicator_width1  2

#property indicator_label2  "Price z-score"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrGold
#property indicator_style2  STYLE_SOLID
#property indicator_width2  1

#property indicator_label3  "L/S z6 (швидке вікно)"
#property indicator_type3   DRAW_LINE
#property indicator_color3  clrDeepSkyBlue
#property indicator_style3  STYLE_DOT
#property indicator_width3  1

#property indicator_level1   1.0
#property indicator_level2  -1.0
#property indicator_level3   0.0
#property indicator_level4   1.5
#property indicator_level5  -1.5
#property indicator_levelcolor clrDimGray
#property indicator_levelstyle STYLE_DOT

input string InpBinanceSymbol  = "BTCUSDT"; // Символ на Binance Futures (як у фідері)
input int    InpZWindowHours   = 24;        // Вікно z-score, годин (і для ціни)
input int    InpZFastHours     = 6;         // Швидке вікно z (лінія z6), годин; 0 = вимк.
input double InpZThreshold     = 1.0;       // Поріг сигналу
input int    InpShiftBars      = 0;         // Зсув лінії z, барів (+ вправо, - вліво = look-ahead)
input bool   InpShowPriceZ     = false;      // Показати z ціни
input bool   InpLagScan        = true;      // Аналіз лагу на панелі
input int    InpLagScanBars    = 48;        // Діапазон пошуку лагу, ± барів
input int    InpLagScanDepth   = 3000;      // Скільки останніх барів брати в аналіз
input int    InpRefreshSec     = 30;        // Перевірка файлу, секунд
input bool   InpShowPanel      = true;      // Панель зі значеннями
input int    InpPanelFontSize  = 9;         // Панель: розмір шрифту
input ENUM_BASE_CORNER InpPanelCorner = CORNER_LEFT_UPPER; // Панель: кут вікна
input int    InpPanelX         = 6;         // Панель: відступ по X, px
input int    InpPanelY         = 14;        // Панель: відступ по Y, px
input color  InpPanelBg        = C'20,20,20'; // Панель: колір фону (clrNONE = без фону)
input color  InpPanelBorder    = clrDimGray;  // Панель: колір рамки
input bool   InpAutoGmtOffset  = true;      // Авто GMT-зсув сервера
input int    InpGmtOffsetHours = 3;         // Ручний GMT-зсув сервера, год
input bool   InpVerbose        = false;     // Лог завантажень
input int    InpResidLag       = 4;         // Лаг реакції натовпу на ціну, барів
input int    InpResidWindow    = 288;       // Вікно оцінки реакції (β), барів
input int    InpArmedBars      = 12;        // Вікно ARMED, барів
input int    InpStructBars     = 12;        // Структура: макс/мін за N барів
input int    InpSetupMemory    = 12;        // SETUP діє ще N барів після виходу z із зони
input bool   InpShowArrows     = true;      // Стрілки TRIGGER на графіку
input int    InpArrowDepth     = 3000;      // Стрілки на останніх N барах
input bool   InpAlerts         = false;     // Alert на новий TRIGGER / FAIL
input bool   InpShowFail       = true;      // Стрілки FAIL (хибний пробій)
input int    InpFailBars       = 3;         // FAIL: скільки барів після TRIGGER перевіряти

double g_zBuf[];
double g_colBuf[];
double g_pzBuf[];
double g_z6Buf[];

#define BIN_PERIOD  "5m"
#define BIN_STEP_S  300
#define PANEL_NAME  "LSZ_panel"
#define PANEL2_NAME "LSZ_panel2"

long   g_ts[];
double g_v[];
double g_z[];
double g_z6[];
double g_mean[];
double g_sd[];

string g_file    = "";
long   g_lastMod = 0;
bool   g_hasFile = false;

double g_curRatio = 0.0;
double g_curZ     = 0.0;
double g_curZ6    = EMPTY_VALUE;
double g_curMean  = 0.0;
double g_curStd   = 0.0;
long   g_curTs    = 0;
bool   g_curOk    = false;

// стадії (поточний бар) і останній TRIGGER
int      g_stDir        = 0;      // +1 LONG setup, -1 SHORT setup, 0 немає
bool     g_stArmed      = false;
bool     g_stArmedOk    = false;  // чи є достатньо даних для ARMED
double   g_stLevel      = 0.0;    // рівень пробою для TRIGGER
datetime g_lastTrgTime  = 0;
int      g_lastTrgDir   = 0;
double   g_lastTrgStop  = 0.0;
bool     g_lastTrgArmed = false;
bool     g_lastTrgFail  = false;
datetime g_lastFailTime = 0;
datetime g_alertedTime  = 0;
bool     g_sigInit      = false;

#define TRG_PREFIX "LSZ_trg_"

// результати аналізу лагу
bool   g_scanOk    = false;
int    g_bestK     = 0;
double g_bestR     = 0.0;
int    g_bestN     = 0;
bool   g_shiftOk   = false;
double g_shiftR    = 0.0;
int    g_shiftN    = 0;

//+------------------------------------------------------------------+
long GmtShift()
  {
   if(!InpAutoGmtOffset) return (long)InpGmtOffsetHours * 3600;
   long d = (long)(TimeTradeServer() - TimeGMT());
   return (long)MathRound(d / 900.0) * 900;
  }

int WindowPoints()
  {
   int win = (InpZWindowHours * 3600) / BIN_STEP_S;
   if(win < 10) win = 10;
   return win;
  }

//+------------------------------------------------------------------+
void ClearData()
  {
   ArrayResize(g_ts, 0);
   ArrayResize(g_v, 0);
   ArrayResize(g_z, 0);
   ArrayResize(g_z6, 0);
   ArrayResize(g_mean, 0);
   ArrayResize(g_sd, 0);
  }

bool LoadIfChanged(const bool force)
  {
   if(!FileIsExist(g_file, FILE_COMMON))
     {
      bool changed = (g_hasFile || force);
      ClearData();
      g_hasFile = false;
      g_lastMod = 0;
      return changed;
     }

   long mod = FileGetInteger(g_file, FILE_MODIFY_DATE, true);
   if(!force && g_hasFile && mod == g_lastMod) return false;

   int h = FileOpen(g_file, FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE) return false;

   ClearData();
   int n = 0;
   while(!FileIsEnding(h))
     {
      string line = FileReadString(h);
      StringTrimRight(line);
      if(StringLen(line) < 5) continue;
      string f[];
      if(StringSplit(line, ',', f) < 2) continue;
      long   ts = StringToInteger(f[0]);
      double v  = StringToDouble(f[1]);
      if(ts <= 0 || v <= 0.0) continue;
      ArrayResize(g_ts, n + 1, 4096);
      ArrayResize(g_v,  n + 1, 4096);
      g_ts[n] = ts;
      g_v[n]  = v;
      n++;
     }
   FileClose(h);

   g_lastMod = mod;
   g_hasFile = true;
   if(InpVerbose && n > 0)
      PrintFormat("BinanceLSZ: %d точок, остання %s UTC ratio=%.4f",
                  n, TimeToString((datetime)g_ts[n - 1], TIME_DATE | TIME_MINUTES), g_v[n - 1]);
   return true;
  }

//+------------------------------------------------------------------+
//| z натовпу на кожній точці (формула без змін з v1.00)             |
//+------------------------------------------------------------------+
void ComputeZ()
  {
   int m = ArraySize(g_ts);
   ArrayResize(g_z, m);
   ArrayResize(g_mean, m);
   ArrayResize(g_sd, m);

   int  win     = WindowPoints();
   long maxSpan = ((long)(win - 1) * BIN_STEP_S * 3) / 2;

   double s = 0.0, s2 = 0.0;
   for(int i = 0; i < m; i++)
     {
      g_z[i] = EMPTY_VALUE;
      g_mean[i] = 0.0;
      g_sd[i] = 0.0;

      double v = g_v[i];
      s += v; s2 += v * v;
      if(i >= win) { s -= g_v[i - win]; s2 -= g_v[i - win] * g_v[i - win]; }

      if(i >= win - 1 && (i % 2000) == 0)
        {
         s = 0.0; s2 = 0.0;
         for(int k = i - win + 1; k <= i; k++) { s += g_v[k]; s2 += g_v[k] * g_v[k]; }
        }

      if(i < win - 1) continue;
      if(g_ts[i] - g_ts[i - win + 1] > maxSpan) continue;

      double mean = s / win;
      double var  = (s2 / win) - (mean * mean);
      if(var <= 0.0) continue;
      double sd = MathSqrt(var);
      if(sd < 1e-12) continue;

      g_z[i]    = (v - mean) / sd;
      g_mean[i] = mean;
      g_sd[i]   = sd;
     }

   g_curOk = false;
   for(int i = m - 1; i >= 0; i--)
     {
      if(g_z[i] == EMPTY_VALUE) continue;
      g_curRatio = g_v[i];
      g_curZ     = g_z[i];
      g_curMean  = g_mean[i];
      g_curStd   = g_sd[i];
      g_curTs    = g_ts[i];
      g_curOk    = true;
      break;
     }
   ComputeZFast();
  }

//+------------------------------------------------------------------+
//| z6: та сама формула, коротше вікно (лінія і панель)              |
//+------------------------------------------------------------------+
void ComputeZFast()
  {
   int m = ArraySize(g_ts);
   ArrayResize(g_z6, m);
   g_curZ6 = EMPTY_VALUE;
   int win = (InpZFastHours * 3600) / BIN_STEP_S;
   for(int i = 0; i < m; i++) g_z6[i] = EMPTY_VALUE;
   if(InpZFastHours <= 0 || win < 10) return;
   long maxSpan = ((long)(win - 1) * BIN_STEP_S * 3) / 2;
   double s = 0.0, s2 = 0.0;
   for(int i = 0; i < m; i++)
     {
      double v = g_v[i];
      s += v; s2 += v * v;
      if(i >= win) { s -= g_v[i - win]; s2 -= g_v[i - win] * g_v[i - win]; }
      if(i >= win - 1 && (i % 2000) == 0)
        {
         s = 0.0; s2 = 0.0;
         for(int k = i - win + 1; k <= i; k++) { s += g_v[k]; s2 += g_v[k] * g_v[k]; }
        }
      if(i < win - 1) continue;
      if(g_ts[i] - g_ts[i - win + 1] > maxSpan) continue;
      double mean = s / win;
      double var  = (s2 / win) - (mean * mean);
      if(var <= 0.0) continue;
      double sd = MathSqrt(var);
      if(sd < 1e-12) continue;
      g_z6[i] = (v - mean) / sd;
     }
   for(int i = m - 1; i >= 0; i--)
      if(g_z6[i] != EMPTY_VALUE) { g_curZ6 = g_z6[i]; break; }
  }

//+------------------------------------------------------------------+
//| Кореляція змін z натовпу (бар i-k) зі змінами ціни (бар i).      |
//| k > 0: натовп випереджає ціну; k < 0: запізнюється.              |
//+------------------------------------------------------------------+
bool CorrAtLag(const int k, const int off, const double &c[], const int cnt,
               const int start, double &r, int &n)
  {
   double sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0;
   n = 0;
   for(int i = start; i < cnt; i++)
     {
      int j = i - k;
      if(j < 1 || j >= cnt) continue;
      double a = g_zBuf[off + j];
      double b = g_zBuf[off + j - 1];
      if(a == EMPTY_VALUE || b == EMPTY_VALUE) continue;
      double x = a - b;
      double y = c[i] - c[i - 1];
      sx += x; sy += y; sxx += x * x; syy += y * y; sxy += x * y;
      n++;
     }
   if(n < 50) return false;
   double cov = sxy - (sx * sy) / n;
   double vx  = sxx - (sx * sx) / n;
   double vy  = syy - (sy * sy) / n;
   if(vx <= 0.0 || vy <= 0.0) return false;
   r = cov / MathSqrt(vx * vy);
   return true;
  }

void ScanLags(const double &c[], const int cnt, const int off)
  {
   g_scanOk  = false;
   g_shiftOk = false;
   if(!InpLagScan || cnt < 100) return;

   int L = MathMax(1, InpLagScanBars);
   if(MathAbs(InpShiftBars) > L) L = MathAbs(InpShiftBars);
   int start = MathMax(1, cnt - MathMax(200, InpLagScanDepth));

   double bestR = 0.0;
   for(int k = -L; k <= L; k++)
     {
      double r; int n;
      if(!CorrAtLag(k, off, c, cnt, start, r, n)) continue;
      if(k == InpShiftBars) { g_shiftOk = true; g_shiftR = r; g_shiftN = n; }
      if(!g_scanOk || MathAbs(r) > MathAbs(bestR))
        {
         bestR    = r;
         g_bestK  = k;
         g_bestR  = r;
         g_bestN  = n;
         g_scanOk = true;
        }
     }
  }

//+------------------------------------------------------------------+
//| Стадії SETUP / ARMED / TRIGGER                                   |
//+------------------------------------------------------------------+
void DrawTrigger(const datetime t, const int dir, const double price,
                 const double z, const bool armed, const double stop)
  {
   string name = TRG_PREFIX + IntegerToString((long)t);
   if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
   if(!ObjectCreate(0, name, OBJ_ARROW, 0, t, price)) return;

   color col;
   string side;
   if(dir > 0)
     {
      ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 233);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_TOP);
      if(armed) col = clrLime; else col = clrSeaGreen;
      side = "LONG";
     }
   else
     {
      ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 234);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_BOTTOM);
      if(armed) col = clrOrangeRed; else col = clrSienna;
      side = "SHORT";
     }
   ObjectSetInteger(0, name, OBJPROP_COLOR, col);
   if(armed) ObjectSetInteger(0, name, OBJPROP_WIDTH, 3);
   else      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);

   string armTxt = "ні";
   if(armed) armTxt = "так";
   ObjectSetString(0, name, OBJPROP_TOOLTIP,
                   StringFormat("%s TRIGGER | z %+.2f | ARMED %s | стоп %s",
                                side, z, armTxt, DoubleToString(stop, _Digits)));
  }

void DrawFail(const datetime t, const int trgDir, const double price,
              const bool engulf, const double stop, const double level)
  {
   string name = TRG_PREFIX + "f_" + IntegerToString((long)t);
   if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
   if(!ObjectCreate(0, name, OBJ_ARROW, 0, t, price)) return;

   string txt;
   string eng = "ні";
   if(engulf) eng = "так";
   if(trgDir > 0)
     {
      // провал LONG-пробою -> стрілка вниз над свічкою
      ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 234);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_BOTTOM);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clrRed);
      txt = StringFormat("FAIL LONG-пробою | закриття < %s і < відкриття тригера | поглинання %s | стоп для шорту %s",
                         DoubleToString(level, _Digits), eng, DoubleToString(stop, _Digits));
     }
   else
     {
      ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 233);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_TOP);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clrDodgerBlue);
      txt = StringFormat("FAIL SHORT-пробою | закриття > %s і > відкриття тригера | поглинання %s | стоп для лонгу %s",
                         DoubleToString(level, _Digits), eng, DoubleToString(stop, _Digits));
     }
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 3);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, txt);
  }

void ComputeSignals(const datetime &t[], const double &o[], const double &h[], const double &l[],
                    const double &c[], const int cnt, const int off)
  {
   g_stDir     = 0;
   g_stArmed   = false;
   g_stArmedOk = false;

   int N = MathMax(2, InpStructBars);
   int L = MathMax(0, InpResidLag);
   int W = MathMax(30, InpResidWindow);
   int A = MathMax(1, InpArmedBars);
   int M = MathMax(0, InpSetupMemory);

   if(InpShowArrows) ObjectsDeleteAll(0, TRG_PREFIX, 0, OBJ_ARROW);
   if(cnt < N + L + 5) return;

   // --- 1. залишок реакції натовпу (β, α тільки з минулих пар)
   double resid[];
   int    ready[];
   double px[], py[];
   int    pv[];
   ArrayResize(resid, cnt); ArrayResize(ready, cnt);
   ArrayResize(px, cnt);    ArrayResize(py, cnt); ArrayResize(pv, cnt);

   double Sx = 0, Sy = 0, Sxx = 0, Sxy = 0;
   int    Sn = 0;
   for(int i = 0; i < cnt; i++)
     {
      resid[i] = 0.0; ready[i] = 0; pv[i] = 0; px[i] = 0.0; py[i] = 0.0;

      int r = i - W;
      if(r >= 0 && pv[r] == 1)
        {
         Sx -= px[r]; Sy -= py[r]; Sxx -= px[r] * px[r]; Sxy -= px[r] * py[r]; Sn--;
        }

      int k = i - L;
      if(i < 1 || k < 1) continue;
      double z1 = g_zBuf[off + i];
      double z0 = g_zBuf[off + i - 1];
      if(z1 == EMPTY_VALUE || z0 == EMPTY_VALUE) continue;

      double x = c[k] - c[k - 1];
      double y = z1 - z0;

      if(Sn >= 30)
        {
         double vx = Sxx - (Sx * Sx) / Sn;
         double beta = 0.0;
         if(vx > 0.0) beta = (Sxy - (Sx * Sy) / Sn) / vx;
         double alpha = (Sy - beta * Sx) / Sn;
         resid[i] = y - (alpha + beta * x);
         ready[i] = 1;
        }

      px[i] = x; py[i] = y; pv[i] = 1;
      Sx += x; Sy += y; Sxx += x * x; Sxy += x * y; Sn++;
     }

   // --- 2. сума залишку за A барів (ARMED)
   double cr[];
   int    crOk[];
   ArrayResize(cr, cnt); ArrayResize(crOk, cnt);
   double run = 0.0;
   int    runN = 0;
   for(int i = 0; i < cnt; i++)
     {
      if(ready[i] == 1) { run += resid[i]; runN++; }
      if(i - A >= 0 && ready[i - A] == 1) { run -= resid[i - A]; runN--; }
      cr[i]   = run;
      crOk[i] = 0;
      if(runN >= (A + 1) / 2) crOk[i] = 1;
     }

   // --- 3. SETUP з пам'яттю + TRIGGER на закритих барах
   int lastLong = -1000000, lastShort = -1000000;
   int lastTrgL = -1000000, lastTrgS = -1000000;
   double lvlL = 0.0, lvlS = 0.0;            // рівень пробою останнього TRIGGER
   double opL  = 0.0, opS  = 0.0;            // відкриття тригерної свічки
   bool   failL = false, failS = false;
   datetime failTL = 0, failTS = 0;
   int    K = MathMax(1, InpFailBars);
   datetime newestFailT = 0;
   int      newestFailI = -1;
   int      newestFailDir = 0;
   int depthStart = MathMax(0, cnt - MathMax(100, InpArrowDepth));

   datetime newestT = 0;
   int      newestI = -1;
   int      newestDir = 0;
   double   newestStop = 0.0;
   bool     newestArmed = false;
   double   newestZ = 0.0;

   for(int i = 0; i < cnt; i++)
     {
      double z = g_zBuf[off + i];
      if(z != EMPTY_VALUE)
        {
         if(z <= -InpZThreshold) lastLong  = i;
         if(z >=  InpZThreshold) lastShort = i;
        }

      int dir = 0;
      if(i - lastLong <= M && lastLong >= lastShort)       dir = 1;
      else if(i - lastShort <= M && lastShort > lastLong)  dir = -1;

      if(i < N + 1) continue;

      // структура попередніх N барів
      double hh = h[i - N], ll = l[i - N];
      for(int q = i - N + 1; q <= i - 1; q++)
        {
         if(h[q] > hh) hh = h[q];
         if(l[q] < ll) ll = l[q];
        }

      // поточний (незакритий) бар - лише для панелі
      if(i == cnt - 1)
        {
         g_stDir = dir;
         if(dir > 0) g_stLevel = hh;
         if(dir < 0) g_stLevel = ll;
         if(crOk[i] == 1)
           {
            g_stArmedOk = true;
            if(dir > 0 && cr[i] < 0.0) g_stArmed = true;
            if(dir < 0 && cr[i] > 0.0) g_stArmed = true;
           }
         continue;
        }

      // --- FAIL: хибний пробій після останнього TRIGGER (не залежить від SETUP)
      if(InpShowFail && i >= 1)
        {
         bool engDown = (c[i] < o[i] && c[i - 1] > o[i - 1] && o[i] >= c[i - 1] && c[i] <= o[i - 1]);
         bool engUp   = (c[i] > o[i] && c[i - 1] < o[i - 1] && o[i] <= c[i - 1] && c[i] >= o[i - 1]);
         int dL = i - lastTrgL;
         if(!failL && dL >= 1 && dL <= K && c[i] < lvlL && c[i] < opL)
           {
            failL = true; failTL = t[i];
            double stop = MathMax(h[i], h[lastTrgL]);
            if(InpShowArrows && i >= depthStart) DrawFail(t[i], 1, h[i], engDown, stop, lvlL);
            newestFailT = t[i]; newestFailI = i; newestFailDir = 1;
           }
         int dS = i - lastTrgS;
         if(!failS && dS >= 1 && dS <= K && c[i] > lvlS && c[i] > opS)
           {
            failS = true; failTS = t[i];
            double stop = MathMin(l[i], l[lastTrgS]);
            if(InpShowArrows && i >= depthStart) DrawFail(t[i], -1, l[i], engUp, stop, lvlS);
            newestFailT = t[i]; newestFailI = i; newestFailDir = -1;
           }
        }

      if(dir == 0) continue;

      // попередня структура для "першого пробою"
      double hhP = h[i - N - 1], llP = l[i - N - 1];
      for(int q = i - N; q <= i - 2; q++)
        {
         if(h[q] > hhP) hhP = h[q];
         if(l[q] < llP) llP = l[q];
        }

      double zShow = 0.0;
      if(z != EMPTY_VALUE) zShow = z;

      bool armed = false;
      if(crOk[i - 1] == 1)
        {
         if(dir > 0 && cr[i - 1] < 0.0) armed = true;
         if(dir < 0 && cr[i - 1] > 0.0) armed = true;
        }

      if(dir > 0 && c[i] > hh && !(c[i - 1] > hhP) && i - lastTrgL > N)
        {
         lastTrgL = i; lvlL = hh; opL = o[i]; failL = false; failTL = 0;
         double stop = MathMin(ll, l[i]);
         if(InpShowArrows && i >= depthStart) DrawTrigger(t[i], 1, l[i], zShow, armed, stop);
         newestT = t[i]; newestI = i; newestDir = 1; newestStop = stop; newestArmed = armed; newestZ = zShow;
        }
      if(dir < 0 && c[i] < ll && !(c[i - 1] < llP) && i - lastTrgS > N)
        {
         lastTrgS = i; lvlS = ll; opS = o[i]; failS = false; failTS = 0;
         double stop = MathMax(hh, h[i]);
         if(InpShowArrows && i >= depthStart) DrawTrigger(t[i], -1, h[i], zShow, armed, stop);
         newestT = t[i]; newestI = i; newestDir = -1; newestStop = stop; newestArmed = armed; newestZ = zShow;
        }
     }

   if(newestI >= 0)
     {
      g_lastTrgTime  = newestT;
      g_lastTrgDir   = newestDir;
      g_lastTrgStop  = newestStop;
      g_lastTrgArmed = newestArmed;
      if(newestDir > 0) { g_lastTrgFail = failL; g_lastFailTime = failTL; }
      else              { g_lastTrgFail = failS; g_lastFailTime = failTS; }

      if(g_sigInit && InpAlerts && newestT > g_alertedTime && newestI == cnt - 2)
        {
         string side = "LONG";
         if(newestDir < 0) side = "SHORT";
         string arm = "без ARMED";
         if(newestArmed) arm = "ARMED";
         Alert(StringFormat("BinanceLSZ %s: TRIGGER %s (%s), z %+.2f, стоп %s",
                            _Symbol, side, arm, newestZ, DoubleToString(newestStop, _Digits)));
        }
      if(newestT > g_alertedTime) g_alertedTime = newestT;
     }
   if(g_sigInit && InpAlerts && newestFailI >= 0 && newestFailI == cnt - 2 && newestFailT > g_alertedTime)
     {
      string side = "LONG";
      if(newestFailDir < 0) side = "SHORT";
      Alert(StringFormat("BinanceLSZ %s: FAIL %s-пробою (хибний пробій)", _Symbol, side));
      g_alertedTime = newestFailT;
     }
   g_sigInit = true;
  }

//+------------------------------------------------------------------+
//| Заповнення буферів: z натовпу (as-of), z ціни, аналіз лагу       |
//+------------------------------------------------------------------+
void FillBars(const datetime &t[], const double &o[], const double &h[], const double &l[], const double &c[], const int cnt, const int off)
  {
   long shift    = GmtShift();
   long chartSec = PeriodSeconds(_Period);
   long maxGap   = 3 * MathMax(chartSec, (long)BIN_STEP_S);
   int  m        = ArraySize(g_ts);
   int  j        = 0;
   int  last     = -1;

   // --- z натовпу
   for(int i = 0; i < cnt; i++)
     {
      int bi = off + i;
      g_zBuf[bi]   = EMPTY_VALUE;
      g_colBuf[bi] = 0;
      g_z6Buf[bi]  = EMPTY_VALUE;
      if(m == 0) continue;

      // кінець бару в UTC; беремо останню точку, опубліковану до кінця бару
      // (точка Binance з ts покриває [ts, ts+5хв) і з'являється після ts+5хв)
      long barEndUtc = (long)t[i] + chartSec - shift;
      while(j < m && g_ts[j] + BIN_STEP_S <= barEndUtc) { last = j; j++; }
      if(last < 0) continue;
      if(barEndUtc - (g_ts[last] + BIN_STEP_S) > maxGap) continue;

      if(ArraySize(g_z6) == m && g_z6[last] != EMPTY_VALUE) g_z6Buf[bi] = g_z6[last];
      double z = g_z[last];
      if(z == EMPTY_VALUE) continue;

      g_zBuf[bi] = z;
      if(z >= InpZThreshold)       g_colBuf[bi] = 1;
      else if(z <= -InpZThreshold) g_colBuf[bi] = 2;
      else                         g_colBuf[bi] = 0;
     }

   // --- z ціни (те саме вікно в годинах, у барах графіка)
   int winP = (int)((long)InpZWindowHours * 3600 / MathMax(1, chartSec));
   if(winP < 10) winP = 10;
   double ref = 0.0;
   if(cnt > 0) ref = c[0];
   double s = 0.0, s2 = 0.0;
   for(int i = 0; i < cnt; i++)
     {
      int bi = off + i;
      g_pzBuf[bi] = EMPTY_VALUE;

      double x = c[i] - ref;
      s += x; s2 += x * x;
      if(i >= winP) { double y = c[i - winP] - ref; s -= y; s2 -= y * y; }

      if(i >= winP - 1 && (i % 2000) == 0)
        {
         s = 0.0; s2 = 0.0;
         for(int k = i - winP + 1; k <= i; k++) { double y = c[k] - ref; s += y; s2 += y * y; }
        }

      if(!InpShowPriceZ || i < winP - 1) continue;
      double mean = s / winP;
      double var  = (s2 / winP) - (mean * mean);
      if(var <= 0.0) continue;
      double sd = MathSqrt(var);
      if(sd <= 0.0) continue;
      g_pzBuf[bi] = (x - mean) / sd;
     }

   // --- аналіз лагу (на незсунутому z)
   ScanLags(c, cnt, off);

   // --- стадії і стрілки
   ComputeSignals(t, o, h, l, c, cnt, off);
  }

//+------------------------------------------------------------------+
// OBJ_LABEL у MT5 показує максимум 63 символи - кожен рядок окремою міткою
#define PANEL_PREFIX "LSZ_panel_"
#define PANEL_MAX    12

void DrawLines(const string &lines[], const color &cols[], const int count)
  {
   int win   = ChartWindowFind();
   int fs    = MathMax(6, InpPanelFontSize);
   int lineH = (int)MathRound(fs * 1.75);
   int pad   = 5;
   string bg = PANEL_PREFIX + "bg";

   // ширина фону за найдовшим рядком
   TextSetFont("Arial", -fs * 10);
   uint maxW = 0, th = 0;
   for(int i = 0; i < count; i++)
     {
      uint w = 0;
      TextGetSize(lines[i], w, th);
      if(w > maxW) maxW = w;
     }
   bool right = (InpPanelCorner == CORNER_RIGHT_UPPER || InpPanelCorner == CORNER_RIGHT_LOWER);
   bool lower = (InpPanelCorner == CORNER_LEFT_LOWER  || InpPanelCorner == CORNER_RIGHT_LOWER);
   int  bgW = (int)maxW + 2 * pad;
   int  bgH = count * lineH + 2 * pad;

   // фон створюється ПЕРШИМ, щоб текст був над ним (об'єкти малюються в порядку створення)
   if(InpPanelBg != clrNONE && count > 0)
     {
      if(ObjectFind(0, bg) < 0)
        {
         for(int i = 0; i < PANEL_MAX; i++) ObjectDelete(0, PANEL_PREFIX + IntegerToString(i));
         ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, win, 0, 0);
         ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, bg, OBJPROP_BACK, false);
         ObjectSetInteger(0, bg, OBJPROP_BORDER_TYPE, BORDER_FLAT);
         ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);
        }
      ObjectSetInteger(0, bg, OBJPROP_CORNER, InpPanelCorner);
      ObjectSetInteger(0, bg, OBJPROP_XDISTANCE, right ? InpPanelX + bgW : InpPanelX);
      ObjectSetInteger(0, bg, OBJPROP_YDISTANCE, lower ? InpPanelY + bgH : InpPanelY);
      ObjectSetInteger(0, bg, OBJPROP_XSIZE, bgW);
      ObjectSetInteger(0, bg, OBJPROP_YSIZE, bgH);
      ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, InpPanelBg);
      ObjectSetInteger(0, bg, OBJPROP_COLOR, InpPanelBorder);
     }
   else if(ObjectFind(0, bg) >= 0) ObjectDelete(0, bg);

   for(int i = 0; i < PANEL_MAX; i++)
     {
      string name = PANEL_PREFIX + IntegerToString(i);
      if(i >= count)
        {
         if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
         continue;
        }
      if(ObjectFind(0, name) < 0)
        {
         ObjectCreate(0, name, OBJ_LABEL, win, 0, 0);
         ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
        }
      ObjectSetString(0, name, OBJPROP_FONT, "Arial");
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fs);
      ObjectSetInteger(0, name, OBJPROP_CORNER, InpPanelCorner);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, right ? (lower ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER)
                                                      : (lower ? ANCHOR_LEFT_LOWER  : ANCHOR_LEFT_UPPER));
      int row = lower ? (count - 1 - i) : i;
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, InpPanelX + pad);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, InpPanelY + pad + row * lineH);
      ObjectSetInteger(0, name, OBJPROP_COLOR, cols[i]);
      ObjectSetString(0, name, OBJPROP_TEXT, lines[i]);
     }
  }

void DrawPanel()
  {
   if(!InpShowPanel) return;

   string lines[PANEL_MAX];
   color  cols[PANEL_MAX];
   int    n = 0;

   // --- стан натовпу
   if(!g_curOk)
     {
      if(ArraySize(g_ts) == 0)
        {
         lines[n] = "L/S: немає даних"; cols[n] = clrGray; n++;
         lines[n] = StringFormat("запусти сервіс BinanceLS_Feeder (%s, %s)", InpBinanceSymbol, BIN_PERIOD);
         cols[n] = clrGray; n++;
        }
      else
        {
         lines[n] = "L/S: замало даних для вікна z"; cols[n] = clrGray; n++;
        }
     }
   else
     {
      string sig = "—";
      color  col = clrGray;
      if(g_curZ >= InpZThreshold)       { sig = "SHORT"; col = clrTomato; }
      else if(g_curZ <= -InpZThreshold) { sig = "LONG";  col = clrMediumSeaGreen; }
      double pctLong = 100.0 * g_curRatio / (1.0 + g_curRatio);
      lines[n] = StringFormat("L/S %.4f (%.0f%% лонг)   z%d %+.2f   компас: %s", g_curRatio, pctLong, InpZWindowHours, g_curZ, sig);
      cols[n] = col; n++;
      if(InpZFastHours > 0 && g_curZ6 != EMPTY_VALUE)
        {
         color c6 = clrSilver;
         if(MathAbs(g_curZ6) >= 1.5) c6 = (g_curZ6 > 0 ? clrTomato : clrMediumSeaGreen);
         lines[n] = StringFormat("z%d %+.2f  (|z6|>=1.5 - зона тригера D2)", InpZFastHours, g_curZ6);
         cols[n] = c6; n++;
        }
      lines[n] = StringFormat("смуга %.4f±%.4f   дані %s UTC", g_curMean, g_curStd,
                              TimeToString((datetime)g_curTs, TIME_MINUTES));
      cols[n] = clrSilver; n++;
      if((long)TimeGMT() - g_curTs > 3 * BIN_STEP_S)
        {
         lines[n] = "! дані застаріли - перевір фідер"; cols[n] = clrGold; n++;
        }
     }

   // --- зсув, лаг, GMT
   long gmt       = GmtShift();
   int  minPerBar = PeriodSeconds(_Period) / 60;
   string sh = "n/a";
   if(g_shiftOk) sh = StringFormat("%+.3f", g_shiftR);
   lines[n] = StringFormat("зсув %+d бар (%+d хв): r=%s   GMT %+.2gh",
                           InpShiftBars, InpShiftBars * minPerBar, sh, gmt / 3600.0);
   cols[n] = clrSilver; n++;

   if(InpLagScan)
     {
      if(!g_scanOk)
        {
         lines[n] = "лаг: замало даних"; cols[n] = clrSilver; n++;
        }
      else
        {
         double noise = 2.0 / MathSqrt((double)MathMax(1, g_bestN));
         lines[n] = StringFormat("найсильніший лаг %+d бар (%+d хв): r=%+.3f",
                                 g_bestK, g_bestK * minPerBar, g_bestR);
         cols[n] = clrSilver; n++;

         string who = "синхронно";
         if(g_bestK > 0)      who = "z ВИПЕРЕДЖАЄ ціну";
         else if(g_bestK < 0) who = "z ЗАПІЗНЮЄТЬСЯ за ціною";
         string sig2 = "в межах шуму";
         color  c2   = clrGray;
         if(MathAbs(g_bestR) > noise) { sig2 = "вище шуму"; c2 = clrSilver; }
         lines[n] = StringFormat("%s, %s (±%.3f, N=%d)", who, sig2, noise, g_bestN);
         cols[n] = c2; n++;
        }
     }

   // --- стадії входу
   if(g_curOk)
     {
      if(g_stDir == 0)
        {
         lines[n] = "стадії: немає SETUP (|z| нижче порогу)"; cols[n] = clrGray; n++;
        }
      else
        {
         string side = "LONG";
         string cmp  = ">";
         color  cs   = clrMediumSeaGreen;
         if(g_stDir < 0) { side = "SHORT"; cmp = "<"; cs = clrTomato; }
         string arm = "?";
         if(g_stArmedOk)
           {
            if(g_stArmed) arm = "+";
            else          arm = "-";
           }
         if(!g_stArmed) cs = clrSilver;
         lines[n] = StringFormat("%s: SETUP+  ARMED%s  TRIGGER: close %s %s",
                                 side, arm, cmp, DoubleToString(g_stLevel, _Digits));
         cols[n] = cs; n++;
        }
     }
   if(g_lastTrgTime > 0)
     {
      string side = "LONG";
      color  ct   = clrMediumSeaGreen;
      if(g_lastTrgDir < 0) { side = "SHORT"; ct = clrTomato; }
      string arm = "";
      if(g_lastTrgArmed) arm = " ARMED";
      lines[n] = StringFormat("TRIGGER %s %s стоп %s%s", side,
                              TimeToString(g_lastTrgTime, TIME_DATE | TIME_MINUTES),
                              DoubleToString(g_lastTrgStop, _Digits), arm);
      cols[n] = ct; n++;
      if(g_lastTrgFail)
        {
         lines[n] = StringFormat("  -> FAIL %s: хибний пробій, вихід",
                                 TimeToString(g_lastFailTime, TIME_MINUTES));
         cols[n] = clrRed; n++;
        }
     }

   DrawLines(lines, cols, n);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpZWindowHours < 2 || InpZWindowHours > 720)
     {
      Print("ПОМИЛКА: InpZWindowHours поза [2..720]");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpZThreshold <= 0.0)
     {
      Print("ПОМИЛКА: InpZThreshold має бути > 0");
      return INIT_PARAMETERS_INCORRECT;
     }

   SetIndexBuffer(0, g_zBuf,   INDICATOR_DATA);
   SetIndexBuffer(1, g_colBuf, INDICATOR_COLOR_INDEX);
   SetIndexBuffer(2, g_pzBuf,  INDICATOR_DATA);
   SetIndexBuffer(3, g_z6Buf,  INDICATOR_DATA);
   ArraySetAsSeries(g_z6Buf,  false);
   PlotIndexSetDouble(2, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   ArraySetAsSeries(g_zBuf,   false);
   ArraySetAsSeries(g_colBuf, false);
   ArraySetAsSeries(g_pzBuf,  false);
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetInteger(0, PLOT_SHIFT, InpShiftBars);   // зсув лише лінії натовпу

   string sn = StringFormat("L/S z  %s  %dh", InpBinanceSymbol, InpZWindowHours);
   if(InpZFastHours > 0) sn += StringFormat(" + %dh", InpZFastHours);
   if(InpShiftBars != 0) sn += StringFormat("  shift %+d", InpShiftBars);
   IndicatorSetString(INDICATOR_SHORTNAME, sn);
   IndicatorSetInteger(INDICATOR_DIGITS, 2);

   string sym = InpBinanceSymbol;
   StringTrimLeft(sym);
   StringTrimRight(sym);
   StringToUpper(sym);
   g_file = "BinanceLS\\" + sym + "_" + BIN_PERIOD + ".csv";

   LoadIfChanged(true);
   ComputeZ();
   EventSetTimer(MathMax(5, InpRefreshSec));

   PrintFormat("BinanceLSZ v1.08 | %s | вікно %d год | поріг %.2f | зсув %+d бар | GMT %+d с | файл Common\\Files\\%s",
               InpBinanceSymbol, InpZWindowHours, InpZThreshold, InpShiftBars, (int)GmtShift(), g_file);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   ObjectsDeleteAll(0, "LSZ_panel");
   ObjectsDeleteAll(0, TRG_PREFIX);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   if(LoadIfChanged(false))
     {
      ComputeZ();
      int n = ArraySize(g_zBuf);
      if(n > 0)
        {
         datetime t[];
         double   c[], hi[], lo[], op[];
         ArraySetAsSeries(t, false);
         ArraySetAsSeries(c, false);
         ArraySetAsSeries(hi, false);
         ArraySetAsSeries(lo, false);
         ArraySetAsSeries(op, false);
         int gotT = CopyTime(_Symbol, _Period, 0, n, t);
         int gotC = CopyClose(_Symbol, _Period, 0, n, c);
         int gotH = CopyHigh(_Symbol, _Period, 0, n, hi);
         int gotL = CopyLow(_Symbol, _Period, 0, n, lo);
         int gotO = CopyOpen(_Symbol, _Period, 0, n, op);
         if(gotT > 0 && gotT == gotC && gotT == gotH && gotT == gotL && gotT == gotO)
            FillBars(t, op, hi, lo, c, gotT, n - gotT);
        }
     }
   DrawPanel();
   ChartRedraw();
  }

int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   if(rates_total <= 0) return 0;
   if(prev_calculated == 0 || rates_total != prev_calculated)
     {
      FillBars(time, open, high, low, close, rates_total, 0);
      DrawPanel();
     }
   return rates_total;
  }
//+------------------------------------------------------------------+
