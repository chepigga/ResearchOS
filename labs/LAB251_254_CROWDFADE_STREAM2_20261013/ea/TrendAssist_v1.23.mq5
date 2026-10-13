//+------------------------------------------------------------------+
//|                                          TrendAssist_v1.23.mq5   |
//|  Помічник для ручної торгівлі по трендових лініях                |
//|  v1.23: БЕЗПЕРЕРВНИЙ АВТОМАТ — структура головного ТФ і лінія     |
//|         корекції рахуються від ФІКСОВАНОГО старту і далі лише по  |
//|         нових закритих барах (без перерахунку 500 барів з нуля).  |
//|         Результат не залежить від того, де почалось вікно.       |
//|         Пошук бару по часу — бінарний пошук по власних масивах.  |
//|         CSV-лог стану H4/H1 і сигналів для паритету з симулятором|
//|  v1.22: ШВИДКОДІЯ — кеш об'єктів замість ObjectFind, об'єкт      |
//|         оновлюється лише коли змінився, ChartRedraw лише за потреби|
//|  v1.21: віяло ліній корекції (до 3 від одного якоря), трендова   |
//|         лінія H1, мінімалістична панель + профіль об'єму        |
//|  v1.20: ЛІНІЯ КОРЕКЦІЇ рахується на CorrTF (H1), однакова на всіх  |
//|         ТФ, оновлюється щогодини; після зламу — нова лінія від  |
//|         наступного відскоку; вхід — закриття свічки графіка (M1-M15)|
//|  v1.16: корекція оновила екстремум після зламу → нова (пологіша)  |
//|         лінія корекції, як віяло ліній                         |
//|  v1.15: хибний злам лінії корекції → лінія перебудовується        |
//|  v1.14: панель одним кольором (сигнал — зелений/червоний),     |
//|         більший міжрядковий інтервал                           |
//|  v1.13: статус сигналу (SL/TP), попередження по поточній свічці, |
//|         фільтр хибного зламу лінії корекції, ChartRedraw       |
//|  v1.12: контр-трендова лінія корекції + сигнал на її зламі       |
//|  v1.11: найближчий внутрішній свінг головного ТФ, менше шуму,  |
//|         рівні зламу робочого ТФ на панелі, профіль справа      |
//|  v1.10: ГОЛОВНИЙ ТФ (структура H4/D1) малюється на всіх ТФ і     |
//|         фільтрує сигнали; робочий ТФ = поточний графік           |
//|  EMA20 + структура (HH/HL/LH/LL, BOS/CHoCH) + авто-трендлінія    |
//|  + фільтр вичерпання (ATR, кульмінаційний об'єм)                 |
//|  + Volume Profile + сигнали входу на ретесті з SL/TP/лотом       |
//+------------------------------------------------------------------+
#property copyright   "Oleksandr Chepiha"
#property version     "1.23"
#property description "Головний ТФ + робочий ТФ: структура, авто-трендлінії, EMA20, Volume Profile, сигнали входу"
#property indicator_chart_window
#property indicator_buffers 9
#property indicator_plots   6

//--- plot 0: EMA, колір = стан тренду робочого ТФ
#property indicator_label1  "EMA"
#property indicator_type1   DRAW_COLOR_LINE
#property indicator_color1  clrSilver,clrMediumSeaGreen,clrTomato,clrOrange
#property indicator_style1  STYLE_SOLID
#property indicator_width1  2
#property indicator_label2  "EMA + K*ATR"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrIndianRed
#property indicator_style2  STYLE_DOT
#property indicator_width2  1
#property indicator_label3  "EMA - K*ATR"
#property indicator_type3   DRAW_LINE
#property indicator_color3  clrIndianRed
#property indicator_style3  STYLE_DOT
#property indicator_width3  1
#property indicator_label4  "BUY"
#property indicator_type4   DRAW_ARROW
#property indicator_color4  clrLime
#property indicator_width4  3
#property indicator_label5  "SELL"
#property indicator_type5   DRAW_ARROW
#property indicator_color5  clrRed
#property indicator_width5  3
#property indicator_label6  "Climax"
#property indicator_type6   DRAW_ARROW
#property indicator_color6  clrMagenta
#property indicator_width6  2

#include <Generic\HashMap.mqh>

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
input group "=== Головний ТФ (напрямок) ==="
input ENUM_TIMEFRAMES MainTF          = PERIOD_CURRENT; // Головний ТФ (CURRENT = авто: <H4→H4, H4→D1, D1→W1)
input bool            UseMainFilter   = true;        // Сигнали тільки в бік головного ТФ
input int             MainSwingLeft   = 2;           // Свінг головного ТФ: барів зліва
input int             MainSwingRight  = 2;           // Свінг головного ТФ: барів справа
input int             MainBars        = 600;         // Розігрів: барів головного ТФ до старту лінії корекції
input bool            ShowMainLevels  = true;        // Малювати лінію і рівні головного ТФ
input bool            ShowMainInternal= true;        // Найближчий внутрішній LH/HL головного ТФ (свінг 1/1)

input group "=== Робочий ТФ (поточний графік) ==="
input int             EMA_Period      = 20;          // Період EMA
input int             ATR_Period      = 14;          // Період ATR
input int             SwingLeft       = 3;           // Свінг: барів зліва
input int             SwingRight      = 3;           // Свінг: барів справа (= затримка підтвердження)

input group "=== Контр-трендова лінія (лінія корекції) ==="
input bool            ShowCounterLine = true;        // Малювати лінію корекції (від LL через мінімуми відскоку)
input bool            CounterSignals  = true;        // Сигнал на зламі лінії корекції закриттям
input ENUM_TIMEFRAMES CorrTF          = PERIOD_H1;   // ТФ лінії корекції (якщо графік старший — береться ТФ графіка)
input int             CorrBars        = 3000;        // Старт розрахунку: барів CorrTF назад (якщо CalcFrom = 0)
input datetime        CalcFrom        = 0;           // Фіксований старт розрахунку (0 = авто по CorrBars)
input int             CL_Lookback     = 120;         // Шукати екстремум імпульсу за N барів CorrTF
input int             CL_MinBars      = 3;           // Мін. барів CorrTF від якоря до першої лінії
input int             CL_SignalFan    = 2;           // Сигнал з лінії віяла №N (1 = з першої, 2 = з другої...)
input bool            ShowCorrTrend   = true;        // Трендова лінія CorrTF (від вершини імпульсу через LH)
input double          CL_MinATR       = 1.5;         // Мін. розмір корекції (ATR CorrTF)
input double          CL_MaxSL_ATR    = 4.0;         // Макс. стоп для сигналу зламу (ATR графіка)
input int             CL_SLBars       = 10;          // Стоп за максимумом/мінімумом останніх N барів графіка
input color           CL_Color        = clrLime;     // Колір лінії корекції
input double          CL_BreakATR     = 0.25;        // Злам: закриття за лінією ≥ X × ATR (ATR свого ТФ)

input group "=== Фільтр вичерпання ==="
input double          MaxExtATR       = 2.0;         // Макс. відстань close↔EMA для входу (ATR)
input double          BandATR         = 2.0;         // Межі розтягнутості на графіку (ATR)
input double          ClimaxVolMult   = 2.5;         // Кульмінація: об'єм ≥ X × середній(20)
input double          ClimaxRangeATR  = 1.5;         // Кульмінація: діапазон свічки ≥ X × ATR
input int             ExhBlockBars    = 8;           // Блок входів після кульмінації (барів)

input group "=== Сигнали ==="
input double          RetestTolATR    = 0.25;        // Допуск ретесту лінії/EMA (ATR)
input double          SL_BufferATR    = 0.3;         // Буфер стопу за свінгом (ATR)
input double          MinSL_ATR       = 0.5;         // Мін. стоп (ATR)
input double          MaxSL_ATR       = 3.0;         // Макс. стоп (ATR) — ширше = пропуск
input double          MinRR           = 2.0;         // Мін. RR для TP2
input int             CooldownBars    = 6;           // Мін. барів між сигналами в один бік
input double          RiskPct         = 0.5;         // Ризик на угоду, % балансу (для лоту)
input bool            AlertsOn        = true;        // Alert на новий сигнал
input bool            PushOn          = false;       // Push-сповіщення на телефон

input group "=== Volume Profile ==="
input bool            VP_Show         = true;        // Показувати профіль
input int             VP_Bars         = 200;         // Діапазон профілю (останні N барів)
input int             VP_Rows         = 48;          // Кількість рядків
input int             VP_WidthBars    = 30;          // Ширина найтовщого рядка (барів)
input bool            VP_Right        = true;        // Профіль справа від ціни (вмикає зсув графіка)
input double          VP_ValueArea    = 0.70;        // Value Area
input double          HVN_Ratio       = 0.60;        // HVN: рядок ≥ X × POC (для TP2)
input color           VP_ColorNormal  = C'70,70,100';
input color           VP_ColorVA      = C'110,90,170';
input color           VP_ColorPOC     = clrMediumPurple;

input group "=== Відображення ==="
input int             MaxBars         = 3000;        // Скільки барів історії рахувати
input bool            ShowSwings      = true;        // Підписи HH/HL/LH/LL
input bool            ShowCHoCH       = true;        // Лінії CHoCH (зміна тренду)
input bool            ShowBOS         = false;       // Лінії BOS (продовження) — багато шуму у флеті
input int             LabelBars       = 300;         // Підписи свінгів/зламів лише за останні N барів
input bool            ShowTrendline   = true;        // Авто-трендлінія робочого ТФ
input bool            ShowPanel       = true;        // Інфо-панель
input int             PanelX          = 10;
input int             PanelY          = 25;          // Збільш, якщо панель перекриває коментар EA

input group "=== CSV-лог (паритет із симулятором) ==="
input bool            LogCSV          = false;       // Писати лог у Common\Files\TrendAssist\

//+------------------------------------------------------------------+
//| Рушій структури: свінги, BOS/CHoCH, швидка лінія, пауза          |
//+------------------------------------------------------------------+
class CStructure
{
public:
   int    L, R;
   int    trend;          // +1 / -1 / 0
   bool   paused;
   double hi1, hi2, lo1, lo2;
   int    hi1Idx, hi2Idx, lo1Idx, lo2Idx;
   int    brokenHi, brokenLo;
   // події останнього Step()
   string evSwH, evSwL;
   int    evSwHIdx, evSwLIdx;
   int    evBreak;        // +1 BOS up, +2 CHoCH up, -1 BOS dn, -2 CHoCH dn, 0 немає
   int    evBreakSwingIdx;
   double evBreakLevel;

   void Init(const int l, const int r) { L = l; R = r; Reset(); }

   void Reset()
   {
      trend = 0; paused = false;
      hi1 = 0; hi2 = 0; lo1 = 0; lo2 = 0;
      hi1Idx = -1; hi2Idx = -1; lo1Idx = -1; lo2Idx = -1;
      brokenHi = -1; brokenLo = -1;
      evSwH = ""; evSwL = ""; evSwHIdx = -1; evSwLIdx = -1;
      evBreak = 0; evBreakSwingIdx = -1; evBreakLevel = 0;
   }

   bool LineValid()
   {
      if(trend == -1 && hi2Idx >= 0 && hi1 < hi2 && hi1Idx > hi2Idx) return true;
      if(trend ==  1 && lo2Idx >= 0 && lo1 > lo2 && lo1Idx > lo2Idx) return true;
      return false;
   }

   bool LineValue(const int i, double &v)
   {
      v = 0;
      if(!LineValid()) return false;
      if(trend == -1)
      {
         double s = (hi1 - hi2) / (double)(hi1Idx - hi2Idx);
         v = hi1 + s * (i - hi1Idx);
      }
      else
      {
         double s = (lo1 - lo2) / (double)(lo1Idx - lo2Idx);
         v = lo1 + s * (i - lo1Idx);
      }
      return true;
   }

   void Step(const int i, const double &h[], const double &l[], const double &c[])
   {
      evSwH = ""; evSwL = ""; evBreak = 0;
      int p = i - R;
      if(p - L >= 0)
      {
         if(PivotHigh(p, h)) SwingHigh(p, h[p]);
         if(PivotLow(p, l))  SwingLow(p, l[p]);
      }
      if(hi1Idx >= 0 && brokenHi != hi1Idx && c[i] > hi1)
      {
         brokenHi = hi1Idx; evBreakSwingIdx = hi1Idx; evBreakLevel = hi1;
         if(trend != 1) evBreak = 2; else evBreak = 1;
         trend = 1; paused = false;
      }
      if(lo1Idx >= 0 && brokenLo != lo1Idx && c[i] < lo1)
      {
         brokenLo = lo1Idx; evBreakSwingIdx = lo1Idx; evBreakLevel = lo1;
         if(trend != -1) evBreak = -2; else evBreak = -1;
         trend = -1; paused = false;
      }
      double v;
      if(LineValue(i, v))
      {
         if(trend == -1 && c[i] > v) paused = true;
         if(trend ==  1 && c[i] < v) paused = true;
      }
   }

   double Code()   // ±2 тренд, ±1 пауза, 0 немає
   {
      if(trend == 0) return 0;
      if(paused)     return trend * 1.0;
      return trend * 2.0;
   }

private:
   bool PivotHigh(const int p, const double &h[])
   {
      for(int k = p - L; k < p; k++)       if(h[k] >= h[p]) return false;
      for(int k = p + 1; k <= p + R; k++)  if(h[k] >  h[p]) return false;
      return true;
   }
   bool PivotLow(const int p, const double &l[])
   {
      for(int k = p - L; k < p; k++)       if(l[k] <= l[p]) return false;
      for(int k = p + 1; k <= p + R; k++)  if(l[k] <  l[p]) return false;
      return true;
   }
   void SwingHigh(const int p, const double v)
   {
      string lbl;
      if(hi1Idx < 0)   lbl = "H";
      else if(v > hi1) lbl = "HH";
      else             lbl = "LH";
      hi2 = hi1; hi2Idx = hi1Idx; hi1 = v; hi1Idx = p;
      if(lbl == "LH" && trend == -1) paused = false;   // новий LH = структура ціла
      evSwH = lbl; evSwHIdx = p;
   }
   void SwingLow(const int p, const double v)
   {
      string lbl;
      if(lo1Idx < 0)   lbl = "L";
      else if(v < lo1) lbl = "LL";
      else             lbl = "HL";
      lo2 = lo1; lo2Idx = lo1Idx; lo1 = v; lo1Idx = p;
      if(lbl == "HL" && trend == 1) paused = false;
      evSwL = lbl; evSwLIdx = p;
   }
};

//+------------------------------------------------------------------+
//| Buffers & globals                                                |
//+------------------------------------------------------------------+
double EmaBuf[], EmaClr[], UpBuf[], DnBuf[], BuyBuf[], SellBuf[], ClxBuf[], AtrBuf[], TrBuf[];

#define PFX "TA_"

CHashMap<string, string> g_obj;   // кеш: ім'я об'єкта → підпис його параметрів
bool   g_dirty = false;             // чи змінювався хоч один об'єкт у цьому виклику

int    hEMA = INVALID_HANDLE, hATR = INVALID_HANDLE;

CStructure g_s;            // робочий ТФ
CStructure g_m;            // головний ТФ
CStructure g_mi;           // головний ТФ, внутрішні свінги 1/1 (найближчі рівні)
ENUM_TIMEFRAMES g_mainTF;
bool   g_mainOn;           // головний ТФ старший за поточний
datetime g_mt[];
double g_mh[], g_ml[], g_mc[];
int    g_mTrend[];         // стан тренду головного ТФ після кожного його закритого бару
int    g_mEv[];            // подія зламу головного ТФ на кожному закритому барі (для логу)
int    g_mN = 0;
int    g_mDone = 0;        // скільки закритих барів головного ТФ уже пройдено автоматом
datetime g_mainBarTime = 0;
datetime g_mainStart = 0;  // фіксований старт головного ТФ (розігрів перед g_corrStart)
datetime g_corrStart = 0;  // фіксований старт CorrTF
bool   g_mainReset = false; // головний ТФ перераховано з нуля → лінію корекції теж

int    g_exhBar, g_exhDir;
int    g_lastBuy, g_lastSell;
int    g_next;
int    g_lastMain;

//--- останній сигнал
int    g_sigBar;
string g_sigKind;
//--- лінія корекції
ENUM_TIMEFRAMES g_corrTF;
int    hCorrATR = INVALID_HANDLE;
datetime g_ct[]; double g_ch[], g_cl[], g_cc[], g_catr[];
int    g_cN = 0;
int    g_cDone = 0;        // наступний індекс CorrTF для CorrStep
datetime g_corrBarTime = 0;
double g_cExtA[];          // екстремум корекції (для логу)
//--- CSV-лог
string g_logSig[];         // рядки сигналів, що чекають запису
int    g_logCi = -1;       // індекс CorrTF для поточного бару (для логу сигналу)
bool   g_logSigRewrite = false;
//--- стан лінії корекції після кожного закритого бару CorrTF
int      g_cValid[], g_cDir[], g_cBrk[], g_cBrkIdx[], g_cFail[], g_cFan[];
datetime g_cAt[], g_cKt[];
double   g_cAp[], g_cSl[];
datetime g_lastCLA = 0, g_lastCLK = 0;   // лінія, по якій уже був сигнал
datetime time_last_g = 0;                // час поточного бару графіка (для панелі)
int    g_sigDir;
double g_sigEntry, g_sigSL, g_sigTP1, g_sigTP2;
datetime g_sigTime;

//--- volume profile
double g_vp[];
double g_vpLo, g_vpStep, g_vpMax;
int    g_vpPOC, g_vaUp, g_vaDn;
bool   g_vpReady;
datetime g_vpBarTime;

//+------------------------------------------------------------------+
ENUM_TIMEFRAMES ResolveMainTF()
{
   if(MainTF != PERIOD_CURRENT) return MainTF;
   int s = PeriodSeconds(PERIOD_CURRENT);
   if(s < PeriodSeconds(PERIOD_H4)) return PERIOD_H4;
   if(s < PeriodSeconds(PERIOD_D1)) return PERIOD_D1;
   return PERIOD_W1;
}

//+------------------------------------------------------------------+
int OnInit()
{
   if(SwingLeft < 1 || SwingRight < 1 || MainSwingLeft < 1 || MainSwingRight < 1 ||
      EMA_Period < 2 || ATR_Period < 2 || VP_Rows < 5 || MainBars < 50)
   {
      Print("TrendAssist: невірні параметри");
      return INIT_PARAMETERS_INCORRECT;
   }

   SetIndexBuffer(0, EmaBuf, INDICATOR_DATA);
   SetIndexBuffer(1, EmaClr, INDICATOR_COLOR_INDEX);
   SetIndexBuffer(2, UpBuf,  INDICATOR_DATA);
   SetIndexBuffer(3, DnBuf,  INDICATOR_DATA);
   SetIndexBuffer(4, BuyBuf, INDICATOR_DATA);
   SetIndexBuffer(5, SellBuf,INDICATOR_DATA);
   SetIndexBuffer(6, ClxBuf, INDICATOR_DATA);
   SetIndexBuffer(7, AtrBuf, INDICATOR_CALCULATIONS);
   SetIndexBuffer(8, TrBuf,  INDICATOR_CALCULATIONS);

   PlotIndexSetInteger(3, PLOT_ARROW, 233);
   PlotIndexSetInteger(4, PLOT_ARROW, 234);
   PlotIndexSetInteger(5, PLOT_ARROW, 251);
   for(int p = 0; p < 6; p++)
      PlotIndexSetDouble(p, PLOT_EMPTY_VALUE, EMPTY_VALUE);

   hEMA = iMA(_Symbol, PERIOD_CURRENT, EMA_Period, 0, MODE_EMA, PRICE_CLOSE);
   hATR = iATR(_Symbol, PERIOD_CURRENT, ATR_Period);
   if(hEMA == INVALID_HANDLE || hATR == INVALID_HANDLE)
   {
      Print("TrendAssist: не вдалося створити EMA/ATR");
      return INIT_FAILED;
   }

   g_mainTF = ResolveMainTF();
   g_mainOn = (PeriodSeconds(g_mainTF) > PeriodSeconds(PERIOD_CURRENT));
   if(!g_mainOn)
      Print("TrendAssist: головний ТФ не старший за поточний — фільтр головного ТФ вимкнено");

   g_corrTF = CorrTF;
   if(PeriodSeconds(g_corrTF) < PeriodSeconds(PERIOD_CURRENT)) g_corrTF = (ENUM_TIMEFRAMES)_Period;
   hCorrATR = iATR(_Symbol, g_corrTF, ATR_Period);
   if(hCorrATR == INVALID_HANDLE)
   {
      Print("TrendAssist: не вдалося створити ATR для ТФ лінії корекції");
      return INIT_FAILED;
   }

   g_s.Init(SwingLeft, SwingRight);
   g_m.Init(MainSwingLeft, MainSwingRight);
   g_mi.Init(1, 1);
   if(VP_Show && VP_Right)
   {
      ChartSetInteger(0, CHART_SHIFT, true);
      ChartSetDouble(0, CHART_SHIFT_SIZE, 25.0);
   }

   IndicatorSetString(INDICATOR_SHORTNAME, "TrendAssist v1.23");
   g_corrStart = 0; g_mainStart = 0;
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);
   ResetState();
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0, PFX); g_obj.Clear();
   if(hEMA != INVALID_HANDLE) IndicatorRelease(hEMA);
   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
   if(hCorrATR != INVALID_HANDLE) IndicatorRelease(hCorrATR);
   ChartRedraw();
}

//+------------------------------------------------------------------+
void ResetState()
{
   g_s.Reset();
   g_exhBar = -100000; g_exhDir = 0;
   g_lastBuy = -100000; g_lastSell = -100000;
   g_next = 0;
   g_lastMain = 0;
   g_sigBar = -1; g_sigDir = 0; g_sigKind = "";
   g_lastCLA = 0; g_lastCLK = 0;
   g_sigEntry = 0; g_sigSL = 0; g_sigTP1 = 0; g_sigTP2 = 0; g_sigTime = 0;
   g_vpReady = false; g_vpBarTime = 0;
}

//+------------------------------------------------------------------+
//| Перерахунок структури головного ТФ (тільки закриті бари)         |
//+------------------------------------------------------------------+
//--- фіксований старт розрахунку (один раз на екземпляр індикатора)
bool EnsureStarts()
{
   if(g_corrStart > 0) return true;
   datetime cs = CalcFrom;
   if(cs <= 0)
   {
      int avail = Bars(_Symbol, g_corrTF);
      if(avail < CL_MinBars + 30) return false;
      int back = MathMin(avail - 1, MathMax(CorrBars, CL_MinBars + 30) - 1);
      cs = iTime(_Symbol, g_corrTF, back);
      if(cs == 0) return false;
   }
   g_corrStart = cs;
   g_mainStart = cs - (datetime)((long)MathMax(MainBars, 50) * PeriodSeconds(g_mainTF));
   return true;
}

//--- бари ТФ від start до поточного включно (хронологічно)
int LoadTF(const ENUM_TIMEFRAMES tf, const datetime start,
           datetime &t[], double &h[], double &l[], double &c[])
{
   MqlRates r[];
   ArraySetAsSeries(r, false);
   datetime stop = iTime(_Symbol, tf, 0);
   if(stop == 0) return -1;
   int n = CopyRates(_Symbol, tf, start, stop, r);
   if(n <= 0) return -1;
   ArraySetAsSeries(t, false); ArraySetAsSeries(h, false);
   ArraySetAsSeries(l, false); ArraySetAsSeries(c, false);
   ArrayResize(t, n); ArrayResize(h, n); ArrayResize(l, n); ArrayResize(c, n);
   for(int k = 0; k < n; k++)
   {
      t[k] = r[k].time; h[k] = r[k].high; l[k] = r[k].low; c[k] = r[k].close;
   }
   return n;
}

//--- останній індекс з t[idx] <= x (бінарний пошук), -1 якщо немає
int FindBar(const datetime &t[], const int n, const datetime x)
{
   if(n <= 0 || x < t[0]) return -1;
   int lo = 0, hi = n - 1;
   while(lo < hi)
   {
      int mid = (lo + hi + 1) / 2;
      if(t[mid] <= x) lo = mid; else hi = mid - 1;
   }
   return lo;
}

//+------------------------------------------------------------------+
//| CSV-лог                                                          |
//+------------------------------------------------------------------+
string LogName(const string kind, const ENUM_TIMEFRAMES tf)
{
   return "TrendAssist\\" + _Symbol + "_" + TFName(tf) + "_" + kind + ".csv";
}

int LogOpen(const string fname, const bool rewrite, const string header)
{
   int flags = FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ;
   int h;
   if(rewrite) h = FileOpen(fname, flags | FILE_WRITE);
   else        h = FileOpen(fname, flags | FILE_READ | FILE_WRITE);
   if(h == INVALID_HANDLE)
   {
      Print("TrendAssist: не вдалося відкрити лог ", fname, " err=", GetLastError());
      return INVALID_HANDLE;
   }
   if(rewrite || FileSize(h) == 0) FileWriteString(h, header + "\r\n");
   else FileSeek(h, 0, SEEK_END);
   return h;
}

void LogMeta()
{
   int h = LogOpen("TrendAssist\\" + _Symbol + "_meta.txt", true, "TrendAssist v1.23 meta");
   if(h == INVALID_HANDLE) return;
   long gmt = (long)(TimeTradeServer() - TimeGMT());
   gmt = (long)MathRound(gmt / 900.0) * 900;
   FileWriteString(h, "symbol=" + _Symbol + "\r\n");
   FileWriteString(h, "chart_tf=" + TFName(PERIOD_CURRENT) + "\r\n");
   FileWriteString(h, "main_tf=" + TFName(g_mainTF) + "\r\n");
   FileWriteString(h, "corr_tf=" + TFName(g_corrTF) + "\r\n");
   FileWriteString(h, "main_start=" + TimeToString(g_mainStart, TIME_DATE | TIME_MINUTES) + "\r\n");
   FileWriteString(h, "corr_start=" + TimeToString(g_corrStart, TIME_DATE | TIME_MINUTES) + "\r\n");
   FileWriteString(h, "server_gmt_offset_sec_now=" + (string)gmt + "  (all log times are SERVER time; DST changes the offset)\r\n");
   FileWriteString(h, StringFormat("inputs: MainSwing=%d/%d Swing=%d/%d ATR=%d CL_Lookback=%d CL_MinBars=%d CL_MinATR=%.2f CL_BreakATR=%.2f CL_SignalFan=%d CL_MaxSL_ATR=%.2f CL_SLBars=%d SL_BufferATR=%.2f MinSL_ATR=%.2f Cooldown=%d UseMainFilter=%d\r\n",
                                   MainSwingLeft, MainSwingRight, SwingLeft, SwingRight, ATR_Period, CL_Lookback, CL_MinBars,
                                   CL_MinATR, CL_BreakATR, CL_SignalFan, CL_MaxSL_ATR, CL_SLBars, SL_BufferATR, MinSL_ATR,
                                   CooldownBars, (int)UseMainFilter));
   FileClose(h);
}

string TS(const datetime t) { if(t <= 0) return ""; return TimeToString(t, TIME_DATE | TIME_MINUTES); }

//+------------------------------------------------------------------+
//| Структура головного ТФ: безперервний автомат від g_mainStart     |
//| (лише закриті бари; нові бари доступні — лише нові кроки)        |
//+------------------------------------------------------------------+
bool UpdateMain()
{
   if(!g_mainOn) return true;
   datetime t0 = iTime(_Symbol, g_mainTF, 0);
   if(t0 == 0) return false;
   if(t0 == g_mainBarTime && g_mN > 0) return true;

   //--- контроль попереднього стану: ті самі бари в тих самих індексах?
   datetime chkT0 = 0, chkT = 0; double chkC = 0;
   int done = g_mDone;
   if(done > 0) { chkT0 = g_mt[0]; chkT = g_mt[done - 1]; chkC = g_mc[done - 1]; }

   int cnt = LoadTF(g_mainTF, g_mainStart, g_mt, g_mh, g_ml, g_mc);
   if(cnt < MainSwingLeft + MainSwingRight + 10) return false;

   bool reset = (done <= 0 || cnt < done + 1 || g_mt[0] != chkT0 || g_mt[done - 1] != chkT || g_mc[done - 1] != chkC);
   if(reset)
   {
      g_m.Reset(); g_mi.Reset();
      done = 0;
      g_mainReset = true;
   }
   g_mN = cnt;
   ArrayResize(g_mTrend, cnt);
   ArrayResize(g_mEv, cnt);

   for(int k = done; k <= cnt - 2; k++)      // останній (cnt-1) ще формується
   {
      g_m.Step(k, g_mh, g_ml, g_mc);
      g_mi.Step(k, g_mh, g_ml, g_mc);
      g_mTrend[k] = g_m.trend;
      g_mEv[k]    = g_m.evBreak;
   }
   g_mTrend[cnt - 1] = g_m.trend;
   g_mEv[cnt - 1]    = 0;

   if(LogCSV)
   {
      int h = LogOpen(LogName("main", g_mainTF), reset, "time_srv,high,low,close,trend_after_close,break_event");
      if(h != INVALID_HANDLE)
      {
         for(int k = done; k <= cnt - 2; k++)
            FileWriteString(h, TS(g_mt[k]) + "," + DoubleToString(g_mh[k], _Digits) + "," +
                               DoubleToString(g_ml[k], _Digits) + "," + DoubleToString(g_mc[k], _Digits) + "," +
                               (string)g_mTrend[k] + "," + (string)g_mEv[k] + "\r\n");
         FileClose(h);
      }
   }
   g_mDone = cnt - 1;
   g_mainBarTime = t0;
   return true;
}

//--- тренд головного ТФ на момент бару робочого ТФ (по закритому бару головного, без заглядання)
int MainTrendAt(const datetime t)
{
   if(!g_mainOn || g_mN <= 0) return 0;
   int j = FindBar(g_mt, g_mN, t);      // бар головного ТФ, що містить t
   int k = j - 1;                       // попередній, уже закритий
   if(k < 0 || k >= g_mN) return 0;
   return g_mTrend[k];
}

//+------------------------------------------------------------------+
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
   int minBars = SwingLeft + SwingRight + EMA_Period + ATR_Period + 25;
   if(rates_total < minBars) return 0;
   if(BarsCalculated(hEMA) < rates_total || BarsCalculated(hATR) < rates_total) return 0;

   bool full = (prev_calculated == 0 || prev_calculated > rates_total || g_next <= 0);

   int n;
   if(full) n = rates_total;
   else     n = MathMin(rates_total, rates_total - prev_calculated + 2);

   double tmpE[], tmpA[];
   if(CopyBuffer(hEMA, 0, 0, n, tmpE) < n) return 0;
   if(CopyBuffer(hATR, 0, 0, n, tmpA) < n) return 0;
   int base = rates_total - n;
   for(int k = 0; k < n; k++)
   {
      int i = base + k;
      EmaBuf[i] = tmpE[k];
      AtrBuf[i] = tmpA[k];
      UpBuf[i]  = EmaBuf[i] + BandATR * AtrBuf[i];
      DnBuf[i]  = EmaBuf[i] - BandATR * AtrBuf[i];
   }

   if(!EnsureStarts()) return 0;         // історія CorrTF ще не завантажена
   if(full) g_mainBarTime = 0;
   if(!UpdateMain()) return 0;           // дані головного ТФ ще не завантажені — повтор на наступному тіку
   if(full) g_corrBarTime = 0;
   if(!UpdateCorr()) return 0;           // лінія корекції H1 — лише нові закриті свічки H1
   if(full && LogCSV) LogMeta();

   if(full)
   {
      ObjectsDeleteAll(0, PFX); g_obj.Clear();
      ResetState();
      ArrayInitialize(BuyBuf,  EMPTY_VALUE);
      ArrayInitialize(SellBuf, EMPTY_VALUE);
      ArrayInitialize(ClxBuf,  EMPTY_VALUE);
      ArrayInitialize(EmaClr,  0);
      ArrayInitialize(TrBuf,   0);
      int first = minBars;
      if(MaxBars > 0) first = MathMax(first, rates_total - MaxBars);
      g_next = first;
      ArrayResize(g_logSig, 0);
      g_logSigRewrite = true;
   }
   else
   {
      for(int i = MathMax(prev_calculated - 1, 0); i < rates_total; i++)
      {
         if(i >= g_next) { BuyBuf[i] = EMPTY_VALUE; SellBuf[i] = EMPTY_VALUE; ClxBuf[i] = EMPTY_VALUE; }
      }
   }

   bool live = !full;
   for(int i = g_next; i <= rates_total - 2; i++)
      ProcessBar(i, rates_total, live, time, open, high, low, close, tick_volume);
   g_next = rates_total - 1;

   EmaClr[rates_total - 1] = StateColor();
   TrBuf[rates_total - 1]  = g_s.Code();

   if(VP_Show && time[rates_total - 1] != g_vpBarTime)
   {
      BuildVP(rates_total, time, high, low, tick_volume);
      g_vpBarTime = time[rates_total - 1];
      UpdateSignalTargets();
   }
   time_last_g = time[rates_total - 1];
   DrawTrendline(time, rates_total);
   DrawCounterLine(time, rates_total);
   DrawCorrTrend(time, rates_total);
   DrawMain(time, rates_total);
   DrawSignalLevels(time, rates_total);
   if(ShowPanel) DrawPanel(rates_total, open, high, low, close);

   if(LogCSV) FlushSignalLog();
   if(g_dirty) { ChartRedraw(); g_dirty = false; }
   return rates_total;
}

//--- записати накопичені сигнали робочого ТФ
void FlushSignalLog()
{
   int n = ArraySize(g_logSig);
   if(n == 0 && !g_logSigRewrite) return;
   int h = LogOpen(LogName("signals", PERIOD_CURRENT), g_logSigRewrite,
                   "time_srv,dir,kind,entry,sl,tp1_1R,corr_A_time,corr_K_time,corr_fan,main_trend");
   if(h == INVALID_HANDLE) return;
   for(int k = 0; k < n; k++) FileWriteString(h, g_logSig[k] + "\r\n");
   FileClose(h);
   ArrayResize(g_logSig, 0);
   g_logSigRewrite = false;
}

//+------------------------------------------------------------------+
//| Обробка одного закритого бару робочого ТФ                        |
//+------------------------------------------------------------------+
void ProcessBar(const int i, const int rates_total, const bool live,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[], const long &tick_volume[])
{
   double atr = AtrBuf[i];
   double ema = EmaBuf[i];
   g_logCi = -1;
   if(atr <= 0 || ema <= 0 || ema == EMPTY_VALUE)
   {
      EmaClr[i] = StateColor();
      return;
   }

   //--- 1-3. структура (свінги, BOS/CHoCH, пауза по швидкій лінії)
   g_s.Step(i, high, low, close);
   bool showLbl = (LabelBars <= 0 || i >= rates_total - LabelBars);
   if(ShowSwings && showLbl)
   {
      if(g_s.evSwH != "")
      {
         color c = clrTomato;
         if(g_s.evSwH == "HH") c = clrMediumSeaGreen;
         DrawText(PFX + "SW_H_" + (string)(long)time[g_s.evSwHIdx], time[g_s.evSwHIdx], high[g_s.evSwHIdx], g_s.evSwH, c, ANCHOR_LOWER);
      }
      if(g_s.evSwL != "")
      {
         color c = clrMediumSeaGreen;
         if(g_s.evSwL == "LL") c = clrTomato;
         DrawText(PFX + "SW_L_" + (string)(long)time[g_s.evSwLIdx], time[g_s.evSwLIdx], low[g_s.evSwLIdx], g_s.evSwL, c, ANCHOR_UPPER);
      }
   }
   if(showLbl && g_s.evBreak != 0)
   {
      int dir = 1;
      if(g_s.evBreak < 0) dir = -1;
      bool choch = (MathAbs(g_s.evBreak) == 2);
      if((choch && ShowCHoCH) || (!choch && ShowBOS))
         DrawBreak(time[g_s.evBreakSwingIdx], time[i], g_s.evBreakLevel, choch, dir);
   }

   double lineV = 0;
   bool lineValid = g_s.LineValue(i, lineV);

   //--- 4. кульмінаційний об'єм
   double avgVol = 0;
   for(int k = i - 20; k < i; k++) avgVol += (double)tick_volume[k];
   avgVol /= 20.0;
   if(avgVol > 0 && (double)tick_volume[i] >= ClimaxVolMult * avgVol && (high[i] - low[i]) >= ClimaxRangeATR * atr)
   {
      if(close[i] < open[i]) { g_exhDir = -1; ClxBuf[i] = low[i]  - 0.3 * atr; }
      else                   { g_exhDir =  1; ClxBuf[i] = high[i] + 0.3 * atr; }
      g_exhBar = i;
      if(g_exhDir == g_s.trend) g_s.paused = true;
   }

   //--- 5. головний ТФ
   int mainTr = MainTrendAt(time[i]);
   g_lastMain = mainTr;
   bool mainOkSell = (!UseMainFilter || !g_mainOn || mainTr == -1);
   bool mainOkBuy  = (!UseMainFilter || !g_mainOn || mainTr ==  1);

   //--- 6. сигнали
   if(g_s.trend == -1 && !g_s.paused && mainOkSell && close[i] < open[i]
      && i - g_lastSell >= CooldownBars && !(g_exhDir == -1 && i - g_exhBar <= ExhBlockBars))
   {
      bool retLine = lineValid && high[i] >= lineV - RetestTolATR * atr && close[i] < lineV;
      bool retEma  = high[i] >= ema - RetestTolATR * atr && close[i] < ema;
      double ext   = (ema - close[i]) / atr;
      if((retLine || retEma) && ext <= MaxExtATR)
      {
         double sl = MathMax(g_s.hi1, high[i]) + SL_BufferATR * atr;
         double r  = sl - close[i];
         if(r >= MinSL_ATR * atr && r <= MaxSL_ATR * atr)
         {
            SellBuf[i] = high[i] + 0.4 * atr;
            g_lastSell = i;
            RecordSignal(i, -1, close[i], sl, time[i], live && i == rates_total - 2, "ретест");
         }
      }
   }
   if(g_s.trend == 1 && !g_s.paused && mainOkBuy && close[i] > open[i]
      && i - g_lastBuy >= CooldownBars && !(g_exhDir == 1 && i - g_exhBar <= ExhBlockBars))
   {
      bool retLine = lineValid && low[i] <= lineV + RetestTolATR * atr && close[i] > lineV;
      bool retEma  = low[i] <= ema + RetestTolATR * atr && close[i] > ema;
      double ext   = (close[i] - ema) / atr;
      if((retLine || retEma) && ext <= MaxExtATR)
      {
         double lowRef = g_s.lo1;
         if(g_s.lo1Idx < 0 || low[i] < lowRef) lowRef = low[i];
         double sl = lowRef - SL_BufferATR * atr;
         double r  = close[i] - sl;
         if(r >= MinSL_ATR * atr && r <= MaxSL_ATR * atr)
         {
            BuyBuf[i] = low[i] - 0.4 * atr;
            g_lastBuy = i;
            RecordSignal(i, 1, close[i], sl, time[i], live && i == rates_total - 2, "ретест");
         }
      }
   }

   //--- 7. сигнал: свічка РОБОЧОГО ТФ закрилась за лінією корекції CorrTF (H1)
   int ci = CorrIdxAt(time[i]);
   g_logCi = ci;
   if(CounterSignals && ci >= 0 && g_cValid[ci] == 1 && g_cBrk[ci] == 0 && i > 0)
   {
      int d = g_cDir[ci];
      double v   = CorrLineAt(ci, time[i]);
      double v1  = CorrLineAt(ci, time[i - 1]);
      double dpt = CL_BreakATR * atr;
      bool newLine = (g_cAt[ci] != g_lastCLA || g_cKt[ci] != g_lastCLK) && g_cFan[ci] >= CL_SignalFan;
      if(d < 0 && newLine && close[i] < v - dpt && close[i - 1] >= v1 - dpt && close[i] < open[i]
         && i - g_lastSell >= CooldownBars && (!UseMainFilter || !g_mainOn || mainTr == -1))
      {
         double hiRef = high[i];
         for(int k = MathMax(0, i - CL_SLBars); k <= i; k++) if(high[k] > hiRef) hiRef = high[k];
         double sl = hiRef + SL_BufferATR * atr;
         double r  = sl - close[i];
         if(r >= MinSL_ATR * atr && r <= CL_MaxSL_ATR * atr)
         {
            SellBuf[i] = high[i] + 0.4 * atr;
            g_lastSell = i; g_lastCLA = g_cAt[ci]; g_lastCLK = g_cKt[ci];
            RecordSignal(i, -1, close[i], sl, time[i], live && i == rates_total - 2, "злам лінії корекції " + TFName(g_corrTF));
         }
      }
      if(d > 0 && newLine && close[i] > v + dpt && close[i - 1] <= v1 + dpt && close[i] > open[i]
         && i - g_lastBuy >= CooldownBars && (!UseMainFilter || !g_mainOn || mainTr == 1))
      {
         double loRef = low[i];
         for(int k = MathMax(0, i - CL_SLBars); k <= i; k++) if(low[k] < loRef) loRef = low[k];
         double sl = loRef - SL_BufferATR * atr;
         double r  = close[i] - sl;
         if(r >= MinSL_ATR * atr && r <= CL_MaxSL_ATR * atr)
         {
            BuyBuf[i] = low[i] - 0.4 * atr;
            g_lastBuy = i; g_lastCLA = g_cAt[ci]; g_lastCLK = g_cKt[ci];
            RecordSignal(i, 1, close[i], sl, time[i], live && i == rates_total - 2, "злам лінії корекції " + TFName(g_corrTF));
         }
      }
   }

   EmaClr[i] = StateColor();
   TrBuf[i]  = g_s.Code();
}

//+------------------------------------------------------------------+
//| ЛІНІЯ КОРЕКЦІЇ на CorrTF (H1): рахується по свічках H1, однакова |
//| на всіх ТФ графіка, перебудовується на кожній новій свічці H1.   |
//| dir = напрямок головного ТФ. Для dir<0: від мінімуму імпульсу (A) |
//| дотична під мінімумами відскоку. Після зламу наступний відскок    |
//| отримує нову лінію від свого мінімуму (не чекаємо нового LL H4).  |
//+------------------------------------------------------------------+
double CorrLineAt(const int ci, const datetime t)
{
   return g_cAp[ci] + g_cSl[ci] * (double)(t - g_cAt[ci]);
}

//--- індекс останнього ЗАКРИТОГО бару CorrTF перед часом t
int CorrIdxAt(const datetime t)
{
   if(g_cN <= 0) return -1;
   int j = FindBar(g_ct, g_cN, t);      // бар CorrTF, що містить t
   int k = j - 1;                       // попередній, уже закритий
   if(k < 0 || k >= g_cN) return -1;
   return k;
}

//--- стан послідовного розрахунку
int    s_cDir, s_cA, s_cK, s_cBreak, s_cFloor, s_cFail, s_cFan = 1, s_cPrevN = 0;
double s_prevSl[2];
datetime s_prevKt[2];
bool   s_cBroken;
double s_cAp, s_cSlope, s_cExt;

double CLv(const int k)
{
   return s_cAp + s_cSlope * (double)(g_ct[k] - g_ct[s_cA]);
}

void CorrStore(const int k)
{
   g_cValid[k] = 0;
   if(s_cA >= 0 && s_cK > s_cA && s_cDir != 0) g_cValid[k] = 1;
   g_cDir[k] = s_cDir;
   g_cBrk[k] = 0;
   if(s_cBroken) g_cBrk[k] = 1;
   g_cBrkIdx[k] = s_cBreak;
   g_cFail[k]   = s_cFail;
   g_cFan[k]    = s_cFan;
   g_cExtA[k]   = s_cExt;
   if(g_cValid[k] == 1)
   {
      g_cAt[k] = g_ct[s_cA]; g_cAp[k] = s_cAp; g_cSl[k] = s_cSlope; g_cKt[k] = g_ct[s_cK];
   }
   else
   {
      g_cAt[k] = 0; g_cAp[k] = 0; g_cSl[k] = 0; g_cKt[k] = 0;
   }
}

bool BetterExtreme(const int dir, const int j, const int best)
{
   if(best < 0) return true;
   if(dir < 0) return (g_cl[j] < g_cl[best]);
   return (g_ch[j] > g_ch[best]);
}

void CorrStep(const int k)
{
   int dir = MainTrendAt(g_ct[k]);
   if(!g_mainOn) dir = 0;
   double atr = g_catr[k];
   if(dir != s_cDir)
   {
      s_cDir = dir; s_cA = -1; s_cK = -1; s_cBroken = false; s_cBreak = -1; s_cFloor = 0; s_cFail = -1;
      s_cFan = 1; s_cPrevN = 0;
   }
   if(dir == 0 || atr <= 0) { s_cK = -1; CorrStore(k); return; }
   double dpt = CL_BreakATR * atr;

   //--- лінія зламана
   if(s_cBroken)
   {
      double vb = CLv(k);
      //--- (а) ціна оновила екстремум під якорем → імпульс продовжився: нове віяло від нового дна
      bool newExtreme = false;
      for(int j = s_cBreak + 1; j <= k; j++)
      {
         if(dir < 0 && g_cl[j] < s_cAp) newExtreme = true;
         if(dir > 0 && g_ch[j] > s_cAp) newExtreme = true;
      }
      //--- (б) хибний злам: закриття назад за лінію або за екстремум корекції
      bool failed = false;
      if(dir < 0 && (g_cc[k] > vb + dpt || g_cc[k] > s_cExt)) failed = true;
      if(dir > 0 && (g_cc[k] < vb - dpt || g_cc[k] < s_cExt)) failed = true;
      //--- (в) новий свінг після зламу (вище якоря) → наступна лінія віяла від того самого якоря
      bool newPivot = false;
      for(int j = s_cBreak + 1; j <= k - 2; j++)
      {
         if(dir < 0 && g_cl[j] <= g_cl[j - 1] && g_cl[j] < g_cl[j + 1] && g_cl[j] > s_cAp) newPivot = true;
         if(dir > 0 && g_ch[j] >= g_ch[j - 1] && g_ch[j] > g_ch[j + 1] && g_ch[j] < s_cAp) newPivot = true;
      }

      if(newExtreme)
      {
         s_cBroken = false; s_cFloor = s_cBreak + 1; s_cA = -1; s_cFail = -1; s_cFan = 1; s_cPrevN = 0;
      }
      else if(failed)
      {
         s_cBroken = false; s_cFail = k; s_cFloor = s_cA;      // той самий номер лінії, нова дотична
      }
      else if(newPivot && s_cFan < 3)
      {
         SaveFanLine();                                          // зламана лінія → у віяло (пунктир)
         s_cBroken = false; s_cFan++; s_cFloor = s_cA;
      }
      else if(s_cFan >= 3)
      {
         //--- віяло вичерпано: корекцію завершено. Нова корекція — від нового екстремуму після зламу
         int A2 = -1;
         for(int j = s_cBreak + 1; j <= k; j++) if(BetterExtreme(dir, j, A2)) A2 = j;
         bool fresh = false;
         if(A2 >= 0 && k - A2 >= CL_MinBars)
         {
            double bounce = 0;
            for(int j = A2; j <= k; j++)
            {
               if(dir < 0 && g_ch[j] - g_cl[A2] > bounce) bounce = g_ch[j] - g_cl[A2];
               if(dir > 0 && g_ch[A2] - g_cl[j] > bounce) bounce = g_ch[A2] - g_cl[j];
            }
            if(bounce >= CL_MinATR * atr) fresh = true;
         }
         if(!fresh) { CorrStore(k); return; }
         s_cBroken = false; s_cFloor = s_cBreak + 1; s_cA = -1; s_cFail = -1; s_cFan = 1; s_cPrevN = 0;
      }
      else { CorrStore(k); return; }
   }

   //--- якір A
   int from = MathMax(s_cFloor, k - CL_Lookback);
   if(from < 0) from = 0;
   int A = -1;
   for(int j = from; j <= k; j++) if(BetterExtreme(dir, j, A)) A = j;
   if(A != s_cA)
   {
      s_cA = A; s_cK = -1; s_cFan = 1; s_cPrevN = 0;
      if(dir < 0) s_cAp = g_cl[A]; else s_cAp = g_ch[A];
   }
   if(k - 1 - s_cA < CL_MinBars) { s_cK = -1; CorrStore(k); return; }

   //--- дотична через свінги (1/1) від якоря
   double best = DBL_MAX; int bk = -1;
   for(int j = s_cA + 2; j <= k - 2; j++)
   {
      if(dir < 0 && !(g_cl[j] <= g_cl[j - 1] && g_cl[j] < g_cl[j + 1])) continue;
      if(dir > 0 && !(g_ch[j] >= g_ch[j - 1] && g_ch[j] > g_ch[j + 1])) continue;
      double dt = (double)(g_ct[j] - g_ct[s_cA]);
      if(dt <= 0) continue;
      double sl;
      if(dir < 0) sl = (g_cl[j] - s_cAp) / dt;
      else        sl = (s_cAp - g_ch[j]) / dt;
      if(sl < best) { best = sl; bk = j; }
   }
   if(bk < 0 || best <= 0) { s_cK = -1; CorrStore(k); return; }

   double ext = 0;
   for(int j = s_cA; j < k; j++)
   {
      if(dir < 0 && g_ch[j] - s_cAp > ext) ext = g_ch[j] - s_cAp;
      if(dir > 0 && s_cAp - g_cl[j] > ext) ext = s_cAp - g_cl[j];
   }
   if(ext < CL_MinATR * atr) { s_cK = -1; CorrStore(k); return; }

   if(dir < 0) s_cSlope = best; else s_cSlope = -best;
   s_cK = bk;
   if(dir < 0) s_cExt = s_cAp + ext; else s_cExt = s_cAp - ext;

   //--- злам закриттям свічки CorrTF
   double v = CLv(k);
   if((dir < 0 && g_cc[k] < v - dpt) || (dir > 0 && g_cc[k] > v + dpt))
   {
      s_cBroken = true; s_cBreak = k;
   }
   CorrStore(k);
}

//--- зберегти поточну (зламану) лінію у віяло для відображення пунктиром
void SaveFanLine()
{
   if(s_cK < 0 || s_cA < 0) return;
   if(s_cPrevN >= 2)
   {
      s_prevSl[0] = s_prevSl[1]; s_prevKt[0] = s_prevKt[1]; s_cPrevN = 1;
   }
   s_prevSl[s_cPrevN] = s_cSlope;
   s_prevKt[s_cPrevN] = g_ct[s_cK];
   s_cPrevN++;
}

bool UpdateCorr()
{
   datetime t0 = iTime(_Symbol, g_corrTF, 0);
   if(t0 == 0) return false;
   if(t0 == g_corrBarTime && g_cN > 0) return true;

   //--- контроль попереднього стану: ті самі бари в тих самих індексах?
   datetime chkT0 = 0, chkT = 0; double chkC = 0;
   int done = g_cDone;                                   // перший ще не пройдений індекс
   if(done > 1) { chkT0 = g_ct[0]; chkT = g_ct[done - 1]; chkC = g_cc[done - 1]; }

   int cnt = LoadTF(g_corrTF, g_corrStart, g_ct, g_ch, g_cl, g_cc);
   if(cnt < CL_MinBars + 30) return false;
   if(BarsCalculated(hCorrATR) < Bars(_Symbol, g_corrTF)) return false;
   ArraySetAsSeries(g_catr, false);
   if(CopyBuffer(hCorrATR, 0, g_ct[0], g_ct[cnt - 1], g_catr) != cnt) return false;

   bool reset = (g_mainReset || done <= 1 || cnt < done + 1 ||
                 g_ct[0] != chkT0 || g_ct[done - 1] != chkT || g_cc[done - 1] != chkC);
   g_mainReset = false;

   g_cN = cnt;
   ArrayResize(g_cValid, cnt); ArrayResize(g_cDir, cnt); ArrayResize(g_cBrk, cnt);
   ArrayResize(g_cBrkIdx, cnt); ArrayResize(g_cFail, cnt); ArrayResize(g_cFan, cnt);
   ArrayResize(g_cAt, cnt); ArrayResize(g_cAp, cnt); ArrayResize(g_cSl, cnt); ArrayResize(g_cKt, cnt);
   ArrayResize(g_cExtA, cnt);

   if(reset)
   {
      s_cDir = 0; s_cA = -1; s_cK = -1; s_cBreak = -1; s_cFloor = 0; s_cFail = -1;
      s_cBroken = false; s_cAp = 0; s_cSlope = 0; s_cExt = 0; s_cFan = 1; s_cPrevN = 0;
      g_cValid[0] = 0; g_cDir[0] = 0; g_cBrk[0] = 0; g_cBrkIdx[0] = -1; g_cFail[0] = -1; g_cFan[0] = 1;
      g_cAt[0] = 0; g_cAp[0] = 0; g_cSl[0] = 0; g_cKt[0] = 0; g_cExtA[0] = 0;
      done = 1;
   }
   for(int k = done; k <= cnt - 2; k++) CorrStep(k);   // лише нові закриті; останній (cnt-1) ще формується
   int L = cnt - 1;
   g_cValid[L] = g_cValid[L - 1]; g_cDir[L] = g_cDir[L - 1]; g_cBrk[L] = g_cBrk[L - 1];
   g_cBrkIdx[L] = g_cBrkIdx[L - 1]; g_cFail[L] = g_cFail[L - 1]; g_cFan[L] = g_cFan[L - 1];
   g_cAt[L] = g_cAt[L - 1]; g_cAp[L] = g_cAp[L - 1]; g_cSl[L] = g_cSl[L - 1]; g_cKt[L] = g_cKt[L - 1];
   g_cExtA[L] = g_cExtA[L - 1];

   if(LogCSV) LogCorr(done, cnt - 2, reset);
   g_cDone = cnt - 1;
   g_corrBarTime = t0;
   return true;
}

//--- лог стану лінії корекції по закритих барах CorrTF [k1..k2]
void LogCorr(const int k1, const int k2, const bool rewrite)
{
   int h = LogOpen(LogName("corr", g_corrTF), rewrite,
                   "time_srv,high,low,close,atr,main_trend,valid,dir,broken,break_time,fail_time,fan," +
                   "A_time,A_price,K_time,slope_per_hour,line_at_open,line_at_close,corr_extreme");
   if(h == INVALID_HANDLE) return;
   int ps = PeriodSeconds(g_corrTF);
   for(int k = k1; k <= k2; k++)
   {
      string bt = "", ft = "", at = "", ap = "", kt = "", sl = "", lo = "", lc = "";
      if(g_cBrkIdx[k] >= 0 && g_cBrkIdx[k] < g_cN) bt = TS(g_ct[g_cBrkIdx[k]]);
      if(g_cFail[k] >= 0 && g_cFail[k] < g_cN)     ft = TS(g_ct[g_cFail[k]]);
      if(g_cValid[k] == 1)
      {
         at = TS(g_cAt[k]); ap = DoubleToString(g_cAp[k], _Digits); kt = TS(g_cKt[k]);
         sl = DoubleToString(g_cSl[k] * 3600.0, 8);
         lo = DoubleToString(CorrLineAt(k, g_ct[k]), _Digits);
         lc = DoubleToString(CorrLineAt(k, g_ct[k] + ps), _Digits);
      }
      FileWriteString(h, TS(g_ct[k]) + "," + DoubleToString(g_ch[k], _Digits) + "," +
                         DoubleToString(g_cl[k], _Digits) + "," + DoubleToString(g_cc[k], _Digits) + "," +
                         DoubleToString(g_catr[k], _Digits) + "," + (string)MainTrendAt(g_ct[k]) + "," +
                         (string)g_cValid[k] + "," + (string)g_cDir[k] + "," + (string)g_cBrk[k] + "," +
                         bt + "," + ft + "," + (string)g_cFan[k] + "," + at + "," + ap + "," + kt + "," +
                         sl + "," + lo + "," + lc + "," + DoubleToString(g_cExtA[k], _Digits) + "\r\n");
   }
   FileClose(h);
}

//+------------------------------------------------------------------+
void DrawCounterLine(const datetime &time[], const int rates_total)
{
   string n = PFX + "CL", nt = PFX + "CL_T";
   string nP0 = PFX + "CL_P0", nP1 = PFX + "CL_P1";
   int ci = g_cN - 2;                         // останній закритий бар CorrTF
   datetime tNow = time[rates_total - 1];
   bool show = ShowCounterLine && ci >= 0 && g_cValid[ci] == 1;
   if(show && g_cBrk[ci] == 1 && ci - g_cBrkIdx[ci] > 10 && s_cFan >= 3) show = false;
   if(!show)
   {
      ObjDel(n); ObjDel(nt); ObjDel(nP0); ObjDel(nP1);
      return;
   }
   //--- попередні (зламані) лінії віяла — тонкий пунктир
   for(int p = 0; p < 2; p++)
   {
      string np = PFX + "CL_P" + (string)p;
      if(p < s_cPrevN && s_cA >= 0)
      {
         double pk = s_cAp + s_prevSl[p] * (double)(s_prevKt[p] - g_ct[s_cA]);
         SetTrend(np, g_ct[s_cA], s_cAp, s_prevKt[p], pk, CL_Color, STYLE_DOT, 1, true);
      }
      else ObjDel(np);
   }
   ENUM_LINE_STYLE st = STYLE_SOLID;
   if(g_cBrk[ci] == 1) st = STYLE_DASH;
   SetTrend(n, g_cAt[ci], g_cAp[ci], g_cKt[ci], CorrLineAt(ci, g_cKt[ci]), CL_Color, st, 2, true);
   string txt = TFName(g_corrTF) + " корекція " + (string)g_cFan[ci] + "/3";
   if(g_cBrk[ci] == 1) txt += " ЗЛАМАНА";
   ENUM_ANCHOR_POINT an = ANCHOR_LEFT_UPPER;
   if(g_cDir[ci] > 0) an = ANCHOR_LEFT_LOWER;
   DrawText(nt, tNow, CorrLineAt(ci, tNow), txt, CL_Color, an);
}

//+------------------------------------------------------------------+
//| Трендова лінія CorrTF (H1): від вершини імпульсу (найвищий max    |
//| перед дном корекції) дотичною над пізнішими свінг-максимумами.    |
//| Разом з лінією корекції утворює трикутник.                        |
//+------------------------------------------------------------------+
void DrawCorrTrend(const datetime &time[], const int rates_total)
{
   string n = PFX + "CT", nt = PFX + "CT_T";
   int ci = g_cN - 2;
   if(!ShowCorrTrend || ci < 2 || s_cA < 1 || s_cDir == 0)
   { ObjDel(n); ObjDel(nt); return; }
   int dir = s_cDir;
   //--- вершина імпульсу H: екстремум ДО якоря корекції
   int from = MathMax(0, s_cA - CL_Lookback);
   int H = -1;
   for(int j = from; j < s_cA; j++)
   {
      if(dir < 0 && (H < 0 || g_ch[j] > g_ch[H])) H = j;
      if(dir > 0 && (H < 0 || g_cl[j] < g_cl[H])) H = j;
   }
   if(H < 0) { ObjDel(n); ObjDel(nt); return; }
   double Hp;
   if(dir < 0) Hp = g_ch[H]; else Hp = g_cl[H];
   //--- дотична: для dir<0 — найбільший (найменш від'ємний) нахил над усіма свінг-максимумами
   double best = -DBL_MAX; int bk = -1;
   for(int j = H + 2; j <= ci - 1; j++)
   {
      if(dir < 0 && !(g_ch[j] >= g_ch[j - 1] && g_ch[j] > g_ch[j + 1])) continue;
      if(dir > 0 && !(g_cl[j] <= g_cl[j - 1] && g_cl[j] < g_cl[j + 1])) continue;
      double dt = (double)(g_ct[j] - g_ct[H]);
      if(dt <= 0) continue;
      double sl;
      if(dir < 0) sl = (g_ch[j] - Hp) / dt;     // від'ємний для низхідної лінії
      else        sl = (Hp - g_cl[j]) / dt;
      if(sl > best) { best = sl; bk = j; }
   }
   if(bk < 0 || best >= 0) { ObjDel(n); ObjDel(nt); return; }
   double slope = best;
   if(dir > 0) slope = -best;
   double pK = Hp + slope * (double)(g_ct[bk] - g_ct[H]);
   color c = clrTomato;
   if(dir > 0) c = clrMediumSeaGreen;
   SetTrend(n, g_ct[H], Hp, g_ct[bk], pK, c, STYLE_SOLID, 2, true);
   datetime tNow = time[rates_total - 1];
   double vNow = Hp + slope * (double)(tNow - g_ct[H]);
   ENUM_ANCHOR_POINT an = ANCHOR_LEFT_LOWER;
   if(dir > 0) an = ANCHOR_LEFT_UPPER;
   DrawText(nt, tNow, vNow, TFName(g_corrTF) + " тренд", c, an);
}

//+------------------------------------------------------------------+
//| Профіль об'єму простими словами                                  |
//+------------------------------------------------------------------+
string VPText(const double price, const int dir)
{
   if(!g_vpReady) return "профіль ще не розраховано";
   double poc = g_vpLo + (g_vpPOC + 0.5) * g_vpStep;
   double vah = g_vpLo + (g_vaUp + 1) * g_vpStep;
   double val = g_vpLo + g_vaDn * g_vpStep;
   string s;
   if(price > vah)      s = "над зоною вартості (VAH " + DoubleToString(vah, _Digits) + " = підтримка) — сила покупців";
   else if(price < val) s = "під зоною вартості (VAL " + DoubleToString(val, _Digits) + " = опір) — сила продавців";
   else
   {
      s = "всередині зони вартості — баланс";
      if(price < poc) s += ", POC " + DoubleToString(poc, _Digits) + " над ціною = опір";
      else            s += ", POC " + DoubleToString(poc, _Digits) + " під ціною = підтримка";
   }
   if(dir != 0)
   {
      double hv = FindHVN(dir, price + dir * 0.5 * g_vpStep);
      if(hv > 0)
      {
         if(dir < 0) s += " | ціль ↓ " + DoubleToString(hv, _Digits);
         else        s += " | ціль ↑ " + DoubleToString(hv, _Digits);
      }
   }
   return s;
}


//+------------------------------------------------------------------+
int StateColor()
{
   if(g_s.trend == 0) return 0;
   if(g_s.paused)     return 3;
   if(g_s.trend == 1) return 1;
   return 2;
}

string StateText(const int tr, const bool paused)
{
   if(tr == 0)            return "НЕВИЗНАЧЕНО";
   if(paused && tr < 0)   return "ПАУЗА (даунтренд)";
   if(paused)             return "ПАУЗА (аптренд)";
   if(tr < 0)             return "ДАУНТРЕНД (LH/LL)";
   return "АПТРЕНД (HH/HL)";
}

color StateClr(const int tr, const bool paused)
{
   if(tr == 0)  return clrSilver;
   if(paused)   return clrOrange;
   if(tr > 0)   return clrMediumSeaGreen;
   return clrTomato;
}


//+------------------------------------------------------------------+
void RecordSignal(const int i, const int dir, const double entry, const double sl,
                  const datetime t, const bool fireAlert, const string kind)
{
   g_sigBar = i; g_sigDir = dir; g_sigTime = t; g_sigKind = kind;
   g_sigEntry = entry; g_sigSL = sl;
   double r = MathAbs(entry - sl);
   g_sigTP1 = entry + dir * r;
   g_sigTP2 = entry + dir * MinRR * r;
   UpdateSignalTargets();

   if(LogCSV)
   {
      string ca = "", ck = "", cf = "";
      if(g_logCi >= 0 && g_logCi < g_cN && StringFind(kind, "корекції") >= 0)
      {
         ca = TS(g_cAt[g_logCi]); ck = TS(g_cKt[g_logCi]); cf = (string)g_cFan[g_logCi];
      }
      string k2 = "RETEST";                                  // ANSI-файл: без кирилиці
      if(StringFind(kind, "корекції") >= 0) k2 = "CL_BREAK";
      int n = ArraySize(g_logSig);
      ArrayResize(g_logSig, n + 1, 256);
      g_logSig[n] = TS(t) + "," + (string)dir + "," + k2 + "," + DoubleToString(entry, _Digits) + "," +
                    DoubleToString(sl, _Digits) + "," + DoubleToString(g_sigTP1, _Digits) + "," +
                    ca + "," + ck + "," + cf + "," + (string)g_lastMain;
   }

   if(fireAlert)
   {
      string side;
      if(dir > 0) side = "BUY"; else side = "SELL";
      string msg = StringFormat("TrendAssist %s %s: %s (%s) @ %s  SL %s  TP1 %s  TP2 %s  лот %.2f",
                                _Symbol, TFName(PERIOD_CURRENT), side, kind,
                                DoubleToString(entry, _Digits), DoubleToString(sl, _Digits),
                                DoubleToString(g_sigTP1, _Digits), DoubleToString(g_sigTP2, _Digits),
                                CalcLot(r));
      if(AlertsOn) Alert(msg);
      if(PushOn)   SendNotification(msg);
   }
}

//+------------------------------------------------------------------+
//| TP2: найближча товста зона профілю за TP1 (ставимо ПЕРЕД нею)    |
//+------------------------------------------------------------------+
void UpdateSignalTargets()
{
   if(g_sigBar < 0 || !g_vpReady) return;
   double r = MathAbs(g_sigEntry - g_sigSL);
   double hvn = FindHVN(g_sigDir, g_sigTP1);
   if(hvn > 0) g_sigTP2 = hvn;
   else        g_sigTP2 = g_sigEntry + g_sigDir * MinRR * r;
}

double FindHVN(const int dir, const double from)
{
   if(!g_vpReady || g_vpMax <= 0) return 0;
   int rows = ArraySize(g_vp);
   if(dir < 0)
   {
      for(int rr = rows - 1; rr >= 0; rr--)
      {
         double top = g_vpLo + (rr + 1) * g_vpStep;
         if(top > from) continue;
         if(g_vp[rr] >= HVN_Ratio * g_vpMax) return top;
      }
   }
   else
   {
      for(int rr = 0; rr < rows; rr++)
      {
         double bot = g_vpLo + rr * g_vpStep;
         if(bot < from) continue;
         if(g_vp[rr] >= HVN_Ratio * g_vpMax) return bot;
      }
   }
   return 0;
}

//+------------------------------------------------------------------+
double CalcLot(const double riskPrice)
{
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double vMin     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vMax     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double vStep    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double balance  = AccountInfoDouble(ACCOUNT_BALANCE);
   if(tickVal <= 0 || tickSize <= 0 || riskPrice <= 0 || vStep <= 0) return 0;

   double riskMoney = balance * RiskPct / 100.0;
   double lot = riskMoney / (riskPrice / tickSize * tickVal);
   lot = MathFloor(lot / vStep) * vStep;
   if(lot < vMin) lot = vMin;
   if(lot > vMax) lot = vMax;
   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
//| Volume Profile (тіковий об'єм, рівномірно по діапазону свічки)   |
//+------------------------------------------------------------------+
void BuildVP(const int rates_total, const datetime &time[], const double &high[],
             const double &low[], const long &tick_volume[])
{
   int last  = rates_total - 1;
   int start = MathMax(0, last - VP_Bars + 1);
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int k = start; k <= last; k++)
   {
      if(high[k] > hi) hi = high[k];
      if(low[k]  < lo) lo = low[k];
   }
   if(hi <= lo) { g_vpReady = false; return; }

   ArrayResize(g_vp, VP_Rows);
   ArrayInitialize(g_vp, 0);
   double step = (hi - lo) / VP_Rows;
   for(int k = start; k <= last; k++)
   {
      int r1 = (int)MathFloor((low[k]  - lo) / step);
      int r2 = (int)MathFloor((high[k] - lo) / step);
      if(r1 < 0) r1 = 0;
      if(r2 > VP_Rows - 1) r2 = VP_Rows - 1;
      if(r1 > VP_Rows - 1) r1 = VP_Rows - 1;
      if(r2 < r1) r2 = r1;
      double v = (double)tick_volume[k] / (r2 - r1 + 1);
      for(int rr = r1; rr <= r2; rr++) g_vp[rr] += v;
   }

   int poc = ArrayMaximum(g_vp);
   double total = 0;
   for(int rr = 0; rr < VP_Rows; rr++) total += g_vp[rr];
   double target = total * VP_ValueArea;
   double acc = g_vp[poc];
   int up = poc, dn = poc;
   while(acc < target && (up < VP_Rows - 1 || dn > 0))
   {
      double vu = -1, vd = -1;
      if(up < VP_Rows - 1) vu = g_vp[up + 1];
      if(dn > 0)           vd = g_vp[dn - 1];
      if(vu >= vd) { up++; acc += vu; }
      else         { dn--; acc += vd; }
   }

   g_vpLo = lo; g_vpStep = step; g_vpMax = g_vp[poc];
   g_vpPOC = poc; g_vaUp = up; g_vaDn = dn;
   g_vpReady = true;

   //--- малюємо
   int ps = PeriodSeconds(PERIOD_CURRENT);
   for(int rr = 0; rr < VP_Rows; rr++)
   {
      string name = PFX + "VP_" + (string)rr;
      int wBars = (int)MathRound(g_vp[rr] / g_vpMax * VP_WidthBars);
      if(wBars < 1) { ObjDel(name); continue; }
      datetime t1, t2;
      if(VP_Right)
      {
         t1 = time[last] + (datetime)(3 * ps);
         t2 = t1 + (datetime)(wBars * ps);
      }
      else
      {
         int idx2 = MathMin(start + wBars, last);
         t1 = time[start];
         t2 = time[idx2];
      }
      color c = VP_ColorNormal;
      if(rr >= dn && rr <= up) c = VP_ColorVA;
      if(rr == poc)            c = VP_ColorPOC;
      double p1 = lo + rr * step;
      double p2 = p1 + step * 0.9;
      SetRect(name, t1, p1, t2, p2, c);
   }
   double pocPrice = lo + (poc + 0.5) * step;
   double vah = lo + (up + 1) * step;
   double val = lo + dn * step;
   datetime tEnd = time[last] + (datetime)((VP_WidthBars + 3) * ps);
   SetTrend(PFX + "VP_POC", time[start], pocPrice, tEnd, pocPrice, VP_ColorPOC, STYLE_SOLID, 2, false);
   SetTrend(PFX + "VP_VAH", time[start], vah, tEnd, vah, VP_ColorVA, STYLE_DOT, 1, false);
   SetTrend(PFX + "VP_VAL", time[start], val, tEnd, val, VP_ColorVA, STYLE_DOT, 1, false);
   DrawText(PFX + "VP_POC_T", tEnd, pocPrice, "POC", VP_ColorPOC, ANCHOR_LEFT);
   ObjTip(PFX + "VP_POC", "POC " + DoubleToString(pocPrice, _Digits));
}

//+------------------------------------------------------------------+
void DrawTrendline(const datetime &time[], const int rates_total)
{
   string name = PFX + "TL";
   if(!ShowTrendline || !g_s.LineValid()) { ObjDel(name); return; }
   if(g_s.trend == -1)
      SetTrend(name, time[g_s.hi2Idx], g_s.hi2, time[g_s.hi1Idx], g_s.hi1, clrTomato, STYLE_SOLID, 1, true);
   else
      SetTrend(name, time[g_s.lo2Idx], g_s.lo2, time[g_s.lo1Idx], g_s.lo1, clrMediumSeaGreen, STYLE_SOLID, 1, true);
}

//+------------------------------------------------------------------+
//| Лінія і ключові рівні ГОЛОВНОГО ТФ на поточному графіку          |
//+------------------------------------------------------------------+
void DrawMain(const datetime &time[], const int rates_total)
{
   string nTL = PFX + "M_TL", nTLt = PFX + "M_TL_T";
   string nBR = PFX + "M_BRK", nBRt = PFX + "M_BRK_T";
   string nCT = PFX + "M_CNT", nCTt = PFX + "M_CNT_T";
   if(!ShowMainLevels || !g_mainOn || g_mN <= 0)
   {
      ObjDel(nTL); ObjDel(nTLt); ObjDel(nBR);
      ObjDel(nBRt); ObjDel(nCT); ObjDel(nCTt);
      ObjDel(PFX + "M_INT"); ObjDel(PFX + "M_INT_T");
      return;
   }
   string tf = TFName(g_mainTF);
   datetime tNow = time[rates_total - 1];

   //--- трендова лінія головного ТФ (товста)
   if(g_m.LineValid())
   {
      if(g_m.trend == -1)
      {
         SetTrend(nTL, g_mt[g_m.hi2Idx], g_m.hi2, g_mt[g_m.hi1Idx], g_m.hi1, clrCrimson, STYLE_SOLID, 3, true);
         double lv = 0;
         g_m.LineValue(g_mN - 1, lv);
         DrawText(nTLt, tNow, lv, tf + " лінія", clrCrimson, ANCHOR_LEFT_LOWER);
      }
      else
      {
         SetTrend(nTL, g_mt[g_m.lo2Idx], g_m.lo2, g_mt[g_m.lo1Idx], g_m.lo1, clrSeaGreen, STYLE_SOLID, 3, true);
         double lv = 0;
         g_m.LineValue(g_mN - 1, lv);
         DrawText(nTLt, tNow, lv, tf + " лінія", clrSeaGreen, ANCHOR_LEFT_UPPER);
      }
   }
   else { ObjDel(nTL); ObjDel(nTLt); }

   //--- рівень зламу тренду головного ТФ і рівень продовження
   if(g_m.trend == -1 && g_m.hi1Idx >= 0 && g_m.lo1Idx >= 0)
   {
      SetTrend(nBR, g_mt[g_m.hi1Idx], g_m.hi1, tNow, g_m.hi1, clrGold, STYLE_DASH, 2, true);
      DrawText(nBRt, tNow, g_m.hi1, tf + " злам ↑ " + DoubleToString(g_m.hi1, _Digits), clrGold, ANCHOR_LEFT_LOWER);
      SetTrend(nCT, g_mt[g_m.lo1Idx], g_m.lo1, tNow, g_m.lo1, clrCrimson, STYLE_DOT, 1, true);
      DrawText(nCTt, tNow, g_m.lo1, tf + " LL (продовження ↓) " + DoubleToString(g_m.lo1, _Digits), clrCrimson, ANCHOR_LEFT_UPPER);
   }
   else if(g_m.trend == 1 && g_m.hi1Idx >= 0 && g_m.lo1Idx >= 0)
   {
      SetTrend(nBR, g_mt[g_m.lo1Idx], g_m.lo1, tNow, g_m.lo1, clrGold, STYLE_DASH, 2, true);
      DrawText(nBRt, tNow, g_m.lo1, tf + " злам ↓ " + DoubleToString(g_m.lo1, _Digits), clrGold, ANCHOR_LEFT_UPPER);
      SetTrend(nCT, g_mt[g_m.hi1Idx], g_m.hi1, tNow, g_m.hi1, clrSeaGreen, STYLE_DOT, 1, true);
      DrawText(nCTt, tNow, g_m.hi1, tf + " HH (продовження ↑) " + DoubleToString(g_m.hi1, _Digits), clrSeaGreen, ANCHOR_LEFT_LOWER);
   }
   else
   {
      ObjDel(nBR); ObjDel(nBRt); ObjDel(nCT); ObjDel(nCTt);
   }

   //--- найближчий внутрішній свінг головного ТФ (перший сигнал, що корекція стає серйозною)
   string nIN = PFX + "M_INT", nINt = PFX + "M_INT_T";
   double lvl = 0; datetime tl = 0;
   if(ShowMainInternal && MainInternal(lvl, tl))
   {
      SetTrend(nIN, tl, lvl, tNow, lvl, clrOrange, STYLE_DASHDOT, 1, true);
      string t;
      if(g_m.trend < 0) t = tf + " найближчий LH " + DoubleToString(lvl, _Digits);
      else              t = tf + " найближчий HL " + DoubleToString(lvl, _Digits);
      ENUM_ANCHOR_POINT an = ANCHOR_LEFT_LOWER;
      if(g_m.trend > 0) an = ANCHOR_LEFT_UPPER;
      DrawText(nINt, tNow, lvl, t, clrOrange, an);
   }
   else { ObjDel(nIN); ObjDel(nINt); }
}

//--- внутрішній свінг (1/1) головного ТФ, що лежить між ціною і рівнем зламу
bool MainInternal(double &lvl, datetime &t)
{
   lvl = 0; t = 0;
   if(!g_mainOn || g_mN <= 0) return false;
   if(g_m.trend < 0 && g_mi.hi1Idx >= 0 && g_mi.hi1Idx > g_m.hi1Idx && g_mi.hi1 < g_m.hi1)
   {
      lvl = g_mi.hi1; t = g_mt[g_mi.hi1Idx]; return true;
   }
   if(g_m.trend > 0 && g_mi.lo1Idx >= 0 && g_mi.lo1Idx > g_m.lo1Idx && g_mi.lo1 > g_m.lo1)
   {
      lvl = g_mi.lo1; t = g_mt[g_mi.lo1Idx]; return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
void DrawPanel(const int rates_total, const double &open[], const double &high[], const double &low[], const double &close[])
{
   int last = rates_total - 1;
   double atr = AtrBuf[last - 1];
   double c0  = close[last];
   double ext = 0;
   if(atr > 0) ext = (c0 - EmaBuf[last]) / atr;
   string tf  = TFName(PERIOD_CURRENT);
   string mtf = TFName(g_mainTF);
   string ctf = TFName(g_corrTF);
   int mTr = g_m.trend;
   if(!g_mainOn) mTr = 0;

   //--- рядок 1: головний тренд
   string l1 = _Symbol + " " + tf + "   |   " + mtf + ": ";
   if(mTr < 0)      l1 += "↓ ДАУНТРЕНД  (злам вище " + DoubleToString(g_m.hi1, _Digits) + ")";
   else if(mTr > 0) l1 += "↑ АПТРЕНД  (злам нижче " + DoubleToString(g_m.lo1, _Digits) + ")";
   else             l1 += "тренду немає";

   //--- рядок 2: що робити
   string side = "SELL";
   if(mTr > 0) side = "BUY";
   string l2;
   int ci = g_cN - 2;
   bool cValid = (ci >= 0 && g_cValid[ci] == 1 && g_cDir[ci] == mTr);
   if(mTr == 0)
      l2 = "НЕ ТОРГУВАТИ — на " + mtf + " немає тренду";
   else if((mTr < 0 && ext < -MaxExtATR) || (mTr > 0 && ext > MaxExtATR))
      l2 = "ЧЕКАТИ ВІДКАТУ — ціна розтягнута (" + DoubleToString(MathAbs(ext), 1) + " ATR від EMA20)";
   else if(cValid && g_cBrk[ci] == 0)
   {
      double v = CorrLineAt(ci, time_last_g);
      string rel = "нижче ";
      if(mTr > 0) rel = "вище ";
      if(g_cFan[ci] >= CL_SignalFan)
         l2 = side + " при закритті " + rel + DoubleToString(v, _Digits) + "  (лінія корекції " + ctf + " " + (string)g_cFan[ci] + "/3)";
      else
         l2 = "Лінія корекції " + ctf + " 1/3 (" + DoubleToString(v, _Digits) + "): її злам — попередження, вхід з лінії " + (string)CL_SignalFan;
   }
   else if(cValid && g_cBrk[ci] == 1 && s_cFan < 3)
      l2 = "Лінію корекції " + ctf + " " + (string)g_cFan[ci] + "/3 зламано — чекаємо наступну лінію віяла";
   else if(g_s.trend == mTr && !g_s.paused)
      l2 = side + " на ретесті EMA20 / лінії " + tf;
   else if(g_s.trend == mTr)
      l2 = "ЧЕКАТИ — " + tf + " на паузі";
   else
      l2 = "КОРЕКЦІЯ проти " + mtf + " — чекати лінію корекції " + ctf;

   //--- рядок 3: профіль об'єму
   string l3 = "Профіль: " + VPText(c0, mTr);

   //--- рядки 4-5: сигнал (кольорові)
   string l4 = "Сигнал: немає", l5 = " ";
   color cSig = clrSilver;
   if(g_sigBar >= 0 && last - g_sigBar <= 40)
   {
      string sd;
      if(g_sigDir > 0) sd = "BUY"; else sd = "SELL";
      double r = MathAbs(g_sigEntry - g_sigSL);
      l4 = sd + " @ " + DoubleToString(g_sigEntry, _Digits) + "  (" + g_sigKind + ", " + (string)(last - g_sigBar) + " бар. тому)  →  " + SignalStatus(high, low, last);
      l5 = "SL " + DoubleToString(g_sigSL, _Digits) + "   TP1 " + DoubleToString(g_sigTP1, _Digits) +
           "   TP2 " + DoubleToString(g_sigTP2, _Digits) + "   лот " + DoubleToString(CalcLot(r), 2);
      if(g_sigDir > 0) cSig = clrLime; else cSig = clrRed;
   }

   //--- рядок 6: що відбувається на поточній свічці
   string l6 = " ";
   double atr0 = AtrBuf[last - 1];
   if(cValid && g_cBrk[ci] == 0 && atr0 > 0)
   {
      double v0 = CorrLineAt(ci, time_last_g);
      if((mTr < 0 && c0 < v0 - CL_BreakATR * atr0) || (mTr > 0 && c0 > v0 + CL_BreakATR * atr0))
         l6 = "ЗАРАЗ: ціна за лінією корекції — сигнал після закриття свічки";
   }

   int y = PanelY, dy = 30;
   color cTxt = clrWhiteSmoke;
   SetPanelBg(PFX + "P_BG", PanelX - 8, PanelY - 8, 720, dy * 6 + 12);
   SetLabel(PFX + "P_1", l1, PanelX, y, cTxt, 10);  y += dy;
   SetLabel(PFX + "P_2", "▶ " + l2, PanelX, y, cTxt, 10);  y += dy;
   SetLabel(PFX + "P_3", l3, PanelX, y, cTxt, 10);  y += dy;
   SetLabel(PFX + "P_4", l4, PanelX, y, cSig, 10);  y += dy;
   SetLabel(PFX + "P_5", l5, PanelX, y, cSig, 10);  y += dy;
   SetLabel(PFX + "P_6", l6, PanelX, y, cTxt, 10);
}

//+------------------------------------------------------------------+
//| Статус останнього сигналу по ціні після входу (включно з поточною)|
//+------------------------------------------------------------------+
string SignalStatus(const double &high[], const double &low[], const int last)
{
   if(g_sigBar < 0) return "";
   bool tp1 = false;
   for(int k = g_sigBar + 1; k <= last; k++)
   {
      if(g_sigDir < 0)
      {
         double stopNow = g_sigSL;
         if(tp1) stopNow = g_sigEntry;                       // після TP1 стоп у беззбиток
         if(high[k] >= stopNow)
         {
            if(tp1) return "TP1 взято, решта закрита в беззбиток";
            return "SL — сигнал відпрацював у збиток, неактуальний";
         }
         if(low[k] <= g_sigTP2) return "TP2 взято — угода завершена";
         if(low[k] <= g_sigTP1) tp1 = true;
      }
      else
      {
         double stopNow = g_sigSL;
         if(tp1) stopNow = g_sigEntry;
         if(low[k] <= stopNow)
         {
            if(tp1) return "TP1 взято, решта закрита в беззбиток";
            return "SL — сигнал відпрацював у збиток, неактуальний";
         }
         if(high[k] >= g_sigTP2) return "TP2 взято — угода завершена";
         if(high[k] >= g_sigTP1) tp1 = true;
      }
   }
   if(tp1) return "TP1 взято, стоп у беззбитку, ціль TP2";
   return "АКТИВНИЙ";
}

//+------------------------------------------------------------------+
void DrawSignalLevels(const datetime &time[], const int rates_total)
{
   string n1 = PFX + "SIG_E", n2 = PFX + "SIG_SL", n3 = PFX + "SIG_TP1", n4 = PFX + "SIG_TP2";
   if(g_sigBar < 0 || rates_total - 1 - g_sigBar > 40)
   {
      ObjDel(n1); ObjDel(n2); ObjDel(n3); ObjDel(n4);
      return;
   }
   datetime t1 = time[g_sigBar];
   datetime t2 = t1 + (datetime)(20 * PeriodSeconds(PERIOD_CURRENT));
   SetTrend(n1, t1, g_sigEntry, t2, g_sigEntry, clrWhite,          STYLE_SOLID, 1, false);
   SetTrend(n2, t1, g_sigSL,    t2, g_sigSL,    clrRed,            STYLE_DASH,  1, false);
   SetTrend(n3, t1, g_sigTP1,   t2, g_sigTP1,   clrMediumSeaGreen, STYLE_DASH,  1, false);
   SetTrend(n4, t1, g_sigTP2,   t2, g_sigTP2,   clrLime,           STYLE_DASH,  1, false);
   ObjTip(n1, "Вхід " + DoubleToString(g_sigEntry, _Digits));
   ObjTip(n2, "SL "   + DoubleToString(g_sigSL, _Digits));
   ObjTip(n3, "TP1 (1R, закрити 50%, стоп у БУ) " + DoubleToString(g_sigTP1, _Digits));
   ObjTip(n4, "TP2 "  + DoubleToString(g_sigTP2, _Digits));
}


//+------------------------------------------------------------------+
//| Хелпери для об'єктів                                             |
//+------------------------------------------------------------------+
//--- кеш об'єктів: sig — підпис параметрів. Якщо об'єкт уже є і підпис той самий —
//--- повертає false (нічого не робимо). isNew = true, якщо об'єкт треба створити.
bool ObjNeedsUpdate(const string name, const string sig, bool &isNew)
{
   string old;
   isNew = !g_obj.TryGetValue(name, old);
   if(!isNew && old == sig) return false;
   if(isNew) g_obj.Add(name, sig); else g_obj.TrySetValue(name, sig);
   g_dirty = true;
   return true;
}

void ObjDel(const string name)
{
   if(!g_obj.ContainsKey(name)) return;
   ObjectDelete(0, name);
   g_obj.Remove(name);
   g_obj.Remove(name + "#tip");
   g_dirty = true;
}

void ObjTip(const string name, const string tip)
{
   string k = name + "#tip", old;
   if(g_obj.TryGetValue(k, old) && old == tip) return;
   if(!g_obj.ContainsKey(name)) return;
   ObjectSetString(0, name, OBJPROP_TOOLTIP, tip);
   if(!g_obj.TrySetValue(k, tip)) g_obj.Add(k, tip);
}

void SetRect(const string name, const datetime t1, const double p1, const datetime t2, const double p2, const color c)
{
   string sig = StringFormat("%I64d|%.8f|%I64d|%.8f|%d", (long)t1, p1, (long)t2, p2, (int)c);
   bool isNew;
   if(!ObjNeedsUpdate(name, sig, isNew)) return;
   if(isNew)
   {
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_FILL, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   }
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t1);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 0, p1);
   ObjectSetInteger(0, name, OBJPROP_TIME, 1, t2);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 1, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
}

void SetTrend(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
              const color c, const ENUM_LINE_STYLE st, const int w, const bool ray)
{
   string sig = StringFormat("%I64d|%.8f|%I64d|%.8f|%d|%d|%d|%d", (long)t1, p1, (long)t2, p2, (int)c, (int)st, w, (int)ray);
   bool isNew;
   if(!ObjNeedsUpdate(name, sig, isNew)) return;
   if(isNew)
   {
      ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   }
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t1);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 0, p1);
   ObjectSetInteger(0, name, OBJPROP_TIME, 1, t2);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 1, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, w);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, ray);
}

void DrawText(const string name, const datetime t, const double price, const string txt,
              const color c, const ENUM_ANCHOR_POINT anchor, const int fsz = 8)
{
   string sig = StringFormat("%I64d|%.8f|%s|%d|%d|%d", (long)t, price, txt, (int)c, (int)anchor, fsz);
   bool isNew;
   if(!ObjNeedsUpdate(name, sig, isNew)) return;
   if(isNew)
   {
      ObjectCreate(0, name, OBJ_TEXT, 0, t, price);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetString (0, name, OBJPROP_FONT, "Arial Bold");
   }
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t);
   ObjectSetDouble (0, name, OBJPROP_PRICE, 0, price);
   ObjectSetString (0, name, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fsz);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
}

void DrawBreak(const datetime tSwing, const datetime tBreak, const double level, const bool choch, const int dir)
{
   string base = PFX + "BR_" + (string)(long)tBreak + "_" + (string)dir;
   color c = clrMediumSeaGreen;
   if(dir < 0) c = clrTomato;
   ENUM_LINE_STYLE st = STYLE_DOT;
   if(choch) st = STYLE_DASH;
   SetTrend(base, tSwing, level, tBreak, level, c, st, 1, false);
   string txt = "BOS";
   if(choch) txt = "CHoCH";
   ENUM_ANCHOR_POINT an = ANCHOR_LOWER;
   if(dir < 0) an = ANCHOR_UPPER;
   ENUM_ANCHOR_POINT an2 = ANCHOR_RIGHT_LOWER;
   if(dir < 0) an2 = ANCHOR_RIGHT_UPPER;
   DrawText(base + "_T", tBreak, level, txt, c, an2, 7);
}

void SetLabel(const string name, const string txt, const int x, const int y, const color c, const int size)
{
   string sig = StringFormat("%s|%d|%d|%d|%d", txt, x, y, (int)c, size);
   bool isNew;
   if(!ObjNeedsUpdate(name, sig, isNew)) return;
   if(isNew)
   {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetString (0, name, OBJPROP_FONT, "Arial");
   }
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString (0, name, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
}

void SetPanelBg(const string name, const int x, const int y, const int w, const int h)
{
   string sig = StringFormat("%d|%d|%d|%d", x, y, w, h);
   bool isNew;
   if(!ObjNeedsUpdate(name, sig, isNew)) return;
   if(isNew)
   {
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, C'20,20,30');
      ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, name, OBJPROP_COLOR, C'60,60,80');
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
   }
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
}

string TFName(ENUM_TIMEFRAMES tf)
{
   if(tf == PERIOD_CURRENT) tf = (ENUM_TIMEFRAMES)_Period;
   return StringSubstr(EnumToString(tf), 7);
}
//+------------------------------------------------------------------+
