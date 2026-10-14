//+------------------------------------------------------------------+
//| CF_TrendLines.mqh                                                |
//| Метод трендових ліній TrendAssist v1.23 як модуль для CrowdFade. |
//| Не індикатор: без об'єктів і буферів, лише стан.                 |
//|  - структура головного ТФ (H4): свінги 2/2, BOS/CHoCH, тренд     |
//|  - лінія корекції CorrTF (H1): якір, дотична, віяло 1..3, злам,  |
//|    хибний злам, перезапуск                                       |
//| Безперервний автомат від фіксованого старту: на кожній новій     |
//| закритій свічці — один крок. Тільки закриті бари (без заглядання).|
//| Логіка рядок-у-рядок = TrendAssist_v1.23.mq5 і trendlines.py.     |
//+------------------------------------------------------------------+
#ifndef CF_TRENDLINES_MQH
#define CF_TRENDLINES_MQH

//--- структура (= CStructure з TrendAssist, без підписів)
class CTLStructure
{
public:
   int    L, R, trend;
   bool   paused;
   double hi1, hi2, lo1, lo2;
   int    hi1Idx, hi2Idx, lo1Idx, lo2Idx, brokenHi, brokenLo, evBreak;

   void Init(const int l, const int r) { L = l; R = r; Reset(); }
   void Reset()
   {
      trend = 0; paused = false; hi1 = hi2 = lo1 = lo2 = 0;
      hi1Idx = hi2Idx = lo1Idx = lo2Idx = -1; brokenHi = brokenLo = -1; evBreak = 0;
   }
   void Step(const int i, const double &h[], const double &l[], const double &c[])
   {
      evBreak = 0;
      int p = i - R;
      if(p - L >= 0)
      {
         if(PivotHigh(p, h))
         {
            bool lh = (hi1Idx >= 0 && !(h[p] > hi1));
            hi2 = hi1; hi2Idx = hi1Idx; hi1 = h[p]; hi1Idx = p;
            if(lh && trend == -1) paused = false;
         }
         if(PivotLow(p, l))
         {
            bool hl = (lo1Idx >= 0 && !(l[p] < lo1));
            lo2 = lo1; lo2Idx = lo1Idx; lo1 = l[p]; lo1Idx = p;
            if(hl && trend == 1) paused = false;
         }
      }
      if(hi1Idx >= 0 && brokenHi != hi1Idx && c[i] > hi1)
      { brokenHi = hi1Idx; evBreak = (trend != 1 ? 2 : 1); trend = 1; paused = false; }
      if(lo1Idx >= 0 && brokenLo != lo1Idx && c[i] < lo1)
      { brokenLo = lo1Idx; evBreak = (trend != -1 ? -2 : -1); trend = -1; paused = false; }
   }
private:
   bool PivotHigh(const int p, const double &h[])
   {
      for(int k = p - L; k < p; k++)      if(h[k] >= h[p]) return false;
      for(int k = p + 1; k <= p + R; k++) if(h[k] >  h[p]) return false;
      return true;
   }
   bool PivotLow(const int p, const double &l[])
   {
      for(int k = p - L; k < p; k++)      if(l[k] <= l[p]) return false;
      for(int k = p + 1; k <= p + R; k++) if(l[k] <  l[p]) return false;
      return true;
   }
};

//--- знімок стану лінії корекції після закритого бару CorrTF
struct TLState
{
   bool     ok;          // є дані
   datetime barTime;     // час відкриття останнього закритого бару CorrTF
   int      mainTrend;   // тренд H4 (останній закритий H4)
   int      valid;       // 1 = лінія корекції існує
   int      dir;         // напрям головного ТФ, для якого будується лінія
   int      broken;      // 1 = лінію зламано (закриттям CorrTF)
   bool     breakNow;    // зламано закриттям САМЕ цього бару
   int      fan;         // номер лінії віяла 1..3
   datetime aTime, kTime;
   double   aPrice, slope; // ціна/сек
   double   corrExt;     // екстремум корекції (рівень хибного зламу)
   double   atr;         // ATR CorrTF (SMA TR, як iATR)
};

class CTLEngine
{
private:
   string          m_sym;
   ENUM_TIMEFRAMES m_mainTF, m_corrTF;
   //--- параметри
   int    m_mainL, m_mainR, m_atrP, m_lookback, m_minBars;
   double m_minATR, m_breakATR;
   //--- старти
   datetime m_mainStart, m_corrStart;
   int      m_corrBack, m_mainWarm;
   //--- H4
   datetime m_mt[]; double m_mh[], m_ml[], m_mc[]; int m_mTrend[]; int m_mN, m_mDone;
   datetime m_mainBarTime; bool m_mainReset;
   CTLStructure m_s;
   //--- H1
   datetime m_ct[]; double m_ch[], m_cl[], m_cc[], m_catr[]; int m_cN, m_cDone;
   datetime m_corrBarTime;
   int    m_valid[], m_dir[], m_brk[], m_brkIdx[], m_fan[];
   datetime m_at[], m_kt[]; double m_ap[], m_sl[], m_ext[];
   //--- стан автомата
   int    s_dir, s_A, s_K, s_brk, s_floor, s_fail, s_fan, s_prevN;
   bool   s_broken;
   double s_Ap, s_slope, s_ext;

public:
   bool Init(const string sym, const ENUM_TIMEFRAMES mainTF, const ENUM_TIMEFRAMES corrTF,
             const int corrBarsBack, const int mainWarmBars,
             const int mainL = 2, const int mainR = 2, const int atrP = 14,
             const int lookback = 120, const int minBars = 3, const double minATR = 1.5, const double breakATR = 0.25)
   {
      m_sym = sym; m_mainTF = mainTF; m_corrTF = corrTF;
      m_mainL = mainL; m_mainR = mainR; m_atrP = atrP; m_lookback = lookback; m_minBars = minBars;
      m_minATR = minATR; m_breakATR = breakATR;
      m_corrStart = 0; m_mainStart = 0;
      m_mN = 0; m_mDone = 0; m_cN = 0; m_cDone = 0; m_mainBarTime = 0; m_corrBarTime = 0; m_mainReset = false;
      m_s.Init(mainL, mainR);
      m_corrBack = corrBarsBack; m_mainWarm = mainWarmBars;
      return true;
   }

   //--- викликати з OnTimer: працює лише на нових закритих барах. false = дані ще не готові
   bool Update()
   {
      if(!EnsureStarts()) return false;
      if(!UpdateMain()) return false;
      if(!UpdateCorr()) return false;
      return true;
   }

   //--- тренд H4 на момент t (останній ЗАКРИТИЙ H4 до бару, що містить t)
   int MainTrendAt(const datetime t)
   {
      if(m_mN <= 0) return 0;
      int k = FindBar(m_mt, m_mN, t) - 1;
      if(k < 0 || k >= m_mN) return 0;
      return m_mTrend[k];
   }

   //--- стан лінії корекції на момент t (останній закритий бар CorrTF до t)
   bool StateAt(const datetime t, TLState &st)
   {
      st.ok = false;
      if(m_cN <= 1) return false;
      int k = FindBar(m_ct, m_cN, t) - 1;
      if(k < 0 || k > m_cN - 2) k = MathMin(k, m_cN - 2);
      if(k < 0) return false;
      Fill(k, st);
      return true;
   }

   double LineAt(const TLState &st, const datetime t)
   {
      return st.aPrice + st.slope * (double)(t - st.aTime);
   }

   //--- CSV-рядок стану (для логів CrowdFade)
   string StateCSV(const TLState &st)
   {
      if(!st.ok) return ",,,,,,,,,";
      string s = TimeToString(st.barTime, TIME_DATE | TIME_MINUTES) + "," + (string)st.mainTrend + "," +
                 (string)st.valid + "," + (string)st.dir + "," + (string)st.broken + "," +
                 (string)(int)st.breakNow + "," + (string)st.fan + ",";
      if(st.valid == 1)
         s += TimeToString(st.aTime, TIME_DATE | TIME_MINUTES) + "," + DoubleToString(st.aPrice, _Digits) + "," +
              DoubleToString(st.slope * 3600.0, 6);
      else s += ",,";
      return s;
   }
   static string StateCSVHeader() { return "tl_bar,tl_main,tl_valid,tl_dir,tl_broken,tl_break_now,tl_fan,tl_A_time,tl_A_price,tl_slope_h"; }

private:
   void Fill(const int k, TLState &st)
   {
      st.ok = true; st.barTime = m_ct[k]; st.mainTrend = MainTrendAt(m_ct[k]);
      st.valid = m_valid[k]; st.dir = m_dir[k]; st.broken = m_brk[k];
      st.breakNow = (m_brk[k] == 1 && m_brkIdx[k] == k);
      st.fan = m_fan[k]; st.aTime = m_at[k]; st.kTime = m_kt[k]; st.aPrice = m_ap[k]; st.slope = m_sl[k];
      st.corrExt = m_ext[k]; st.atr = m_catr[k];
   }

   bool EnsureStarts()
   {
      if(m_corrStart > 0) return true;
      int avail = Bars(m_sym, m_corrTF);
      if(avail < m_minBars + 30) return false;
      int back = MathMin(avail - 1, MathMax(m_corrBack, m_minBars + 30) - 1);
      datetime cs = iTime(m_sym, m_corrTF, back);
      if(cs == 0) return false;
      m_corrStart = cs;
      m_mainStart = cs - (datetime)((long)MathMax(m_mainWarm, 50) * PeriodSeconds(m_mainTF));
      return true;
   }

   int LoadTF(const ENUM_TIMEFRAMES tf, const datetime start, datetime &t[], double &h[], double &l[], double &c[])
   {
      MqlRates r[]; ArraySetAsSeries(r, false);
      datetime stop = iTime(m_sym, tf, 0);
      if(stop == 0) return -1;
      int n = CopyRates(m_sym, tf, start, stop, r);
      if(n <= 0) return -1;
      ArrayResize(t, n); ArrayResize(h, n); ArrayResize(l, n); ArrayResize(c, n);
      for(int k = 0; k < n; k++) { t[k] = r[k].time; h[k] = r[k].high; l[k] = r[k].low; c[k] = r[k].close; }
      return n;
   }

   int FindBar(const datetime &t[], const int n, const datetime x)
   {
      if(n <= 0 || x < t[0]) return -1;
      int lo = 0, hi = n - 1;
      while(lo < hi) { int mid = (lo + hi + 1) / 2; if(t[mid] <= x) lo = mid; else hi = mid - 1; }
      return lo;
   }

   //--- ATR як iATR MT5: просте середнє True Range
   void CalcATR(const int n)
   {
      ArrayResize(m_catr, n);
      double tr[]; ArrayResize(tr, n);
      for(int k = 0; k < n; k++)
      {
         if(k == 0) tr[k] = m_ch[k] - m_cl[k];
         else tr[k] = MathMax(m_ch[k], m_cc[k - 1]) - MathMin(m_cl[k], m_cc[k - 1]);
      }
      double sum = 0;
      for(int k = 0; k < n; k++)
      {
         sum += tr[k];
         if(k >= m_atrP) sum -= tr[k - m_atrP];
         m_catr[k] = (k >= m_atrP - 1 ? sum / m_atrP : 0.0);
      }
   }

   bool UpdateMain()
   {
      datetime t0 = iTime(m_sym, m_mainTF, 0);
      if(t0 == 0) return false;
      if(t0 == m_mainBarTime && m_mN > 0) return true;
      datetime chkT0 = 0, chkT = 0; double chkC = 0; int done = m_mDone;
      if(done > 0) { chkT0 = m_mt[0]; chkT = m_mt[done - 1]; chkC = m_mc[done - 1]; }
      int cnt = LoadTF(m_mainTF, m_mainStart, m_mt, m_mh, m_ml, m_mc);
      if(cnt < m_mainL + m_mainR + 10) return false;
      bool reset = (done <= 0 || cnt < done + 1 || m_mt[0] != chkT0 || m_mt[done - 1] != chkT || m_mc[done - 1] != chkC);
      if(reset) { m_s.Reset(); done = 0; m_mainReset = true; }
      m_mN = cnt; ArrayResize(m_mTrend, cnt);
      for(int k = done; k <= cnt - 2; k++) { m_s.Step(k, m_mh, m_ml, m_mc); m_mTrend[k] = m_s.trend; }
      m_mTrend[cnt - 1] = m_s.trend;
      m_mDone = cnt - 1; m_mainBarTime = t0;
      return true;
   }

   bool UpdateCorr()
   {
      datetime t0 = iTime(m_sym, m_corrTF, 0);
      if(t0 == 0) return false;
      if(t0 == m_corrBarTime && m_cN > 0 && !m_mainReset) return true;
      datetime chkT0 = 0, chkT = 0; double chkC = 0; int done = m_cDone;
      if(done > 1) { chkT0 = m_ct[0]; chkT = m_ct[done - 1]; chkC = m_cc[done - 1]; }
      int cnt = LoadTF(m_corrTF, m_corrStart, m_ct, m_ch, m_cl, m_cc);
      if(cnt < m_minBars + 30) return false;
      CalcATR(cnt);
      bool reset = (m_mainReset || done <= 1 || cnt < done + 1 ||
                    m_ct[0] != chkT0 || m_ct[done - 1] != chkT || m_cc[done - 1] != chkC);
      m_mainReset = false;
      m_cN = cnt;
      ArrayResize(m_valid, cnt); ArrayResize(m_dir, cnt); ArrayResize(m_brk, cnt); ArrayResize(m_brkIdx, cnt);
      ArrayResize(m_fan, cnt); ArrayResize(m_at, cnt); ArrayResize(m_kt, cnt); ArrayResize(m_ap, cnt);
      ArrayResize(m_sl, cnt); ArrayResize(m_ext, cnt);
      if(reset)
      {
         s_dir = 0; s_A = -1; s_K = -1; s_brk = -1; s_floor = 0; s_fail = -1; s_fan = 1; s_prevN = 0;
         s_broken = false; s_Ap = 0; s_slope = 0; s_ext = 0;
         m_valid[0] = 0; m_dir[0] = 0; m_brk[0] = 0; m_brkIdx[0] = -1; m_fan[0] = 1;
         m_at[0] = 0; m_kt[0] = 0; m_ap[0] = 0; m_sl[0] = 0; m_ext[0] = 0;
         done = 1;
      }
      for(int k = done; k <= cnt - 2; k++) Step(k);
      int L = cnt - 1;
      m_valid[L] = m_valid[L - 1]; m_dir[L] = m_dir[L - 1]; m_brk[L] = m_brk[L - 1]; m_brkIdx[L] = m_brkIdx[L - 1];
      m_fan[L] = m_fan[L - 1]; m_at[L] = m_at[L - 1]; m_kt[L] = m_kt[L - 1]; m_ap[L] = m_ap[L - 1];
      m_sl[L] = m_sl[L - 1]; m_ext[L] = m_ext[L - 1];
      m_cDone = cnt - 1; m_corrBarTime = t0;
      return true;
   }

   double CLv(const int k) { return s_Ap + s_slope * (double)(m_ct[k] - m_ct[s_A]); }

   bool Better(const int d, const int j, const int best)
   {
      if(best < 0) return true;
      if(d < 0) return (m_cl[j] < m_cl[best]);
      return (m_ch[j] > m_ch[best]);
   }

   void Store(const int k)
   {
      m_valid[k] = (s_A >= 0 && s_K > s_A && s_dir != 0) ? 1 : 0;
      m_dir[k] = s_dir; m_brk[k] = (s_broken ? 1 : 0); m_brkIdx[k] = s_brk; m_fan[k] = s_fan; m_ext[k] = s_ext;
      if(m_valid[k] == 1) { m_at[k] = m_ct[s_A]; m_ap[k] = s_Ap; m_sl[k] = s_slope; m_kt[k] = m_ct[s_K]; }
      else { m_at[k] = 0; m_ap[k] = 0; m_sl[k] = 0; m_kt[k] = 0; }
   }

   //--- = CorrStep з TrendAssist v1.23
   void Step(const int k)
   {
      int d = MainTrendAt(m_ct[k]);
      double atr = m_catr[k];
      if(d != s_dir)
      {
         s_dir = d; s_A = -1; s_K = -1; s_broken = false; s_brk = -1; s_floor = 0; s_fail = -1;
         s_fan = 1; s_prevN = 0;
      }
      if(d == 0 || atr <= 0) { s_K = -1; Store(k); return; }
      double dpt = m_breakATR * atr;

      if(s_broken)
      {
         double vb = CLv(k);
         bool newExtreme = false;
         for(int j = s_brk + 1; j <= k; j++)
         {
            if(d < 0 && m_cl[j] < s_Ap) newExtreme = true;
            if(d > 0 && m_ch[j] > s_Ap) newExtreme = true;
         }
         bool failed = false;
         if(d < 0 && (m_cc[k] > vb + dpt || m_cc[k] > s_ext)) failed = true;
         if(d > 0 && (m_cc[k] < vb - dpt || m_cc[k] < s_ext)) failed = true;
         bool newPivot = false;
         for(int j = s_brk + 1; j <= k - 2; j++)
         {
            if(d < 0 && m_cl[j] <= m_cl[j - 1] && m_cl[j] < m_cl[j + 1] && m_cl[j] > s_Ap) newPivot = true;
            if(d > 0 && m_ch[j] >= m_ch[j - 1] && m_ch[j] > m_ch[j + 1] && m_ch[j] < s_Ap) newPivot = true;
         }
         if(newExtreme)
         { s_broken = false; s_floor = s_brk + 1; s_A = -1; s_fail = -1; s_fan = 1; s_prevN = 0; }
         else if(failed)
         { s_broken = false; s_fail = k; s_floor = s_A; }
         else if(newPivot && s_fan < 3)
         { s_broken = false; s_fan++; s_floor = s_A; }
         else if(s_fan >= 3)
         {
            int A2 = -1;
            for(int j = s_brk + 1; j <= k; j++) if(Better(d, j, A2)) A2 = j;
            bool fresh = false;
            if(A2 >= 0 && k - A2 >= m_minBars)
            {
               double bounce = 0;
               for(int j = A2; j <= k; j++)
               {
                  if(d < 0 && m_ch[j] - m_cl[A2] > bounce) bounce = m_ch[j] - m_cl[A2];
                  if(d > 0 && m_ch[A2] - m_cl[j] > bounce) bounce = m_ch[A2] - m_cl[j];
               }
               if(bounce >= m_minATR * atr) fresh = true;
            }
            if(!fresh) { Store(k); return; }
            s_broken = false; s_floor = s_brk + 1; s_A = -1; s_fail = -1; s_fan = 1; s_prevN = 0;
         }
         else { Store(k); return; }
      }

      int from = MathMax(s_floor, k - m_lookback); if(from < 0) from = 0;
      int A = -1;
      for(int j = from; j <= k; j++) if(Better(d, j, A)) A = j;
      if(A != s_A)
      {
         s_A = A; s_K = -1; s_fan = 1; s_prevN = 0;
         s_Ap = (d < 0 ? m_cl[A] : m_ch[A]);
      }
      if(k - 1 - s_A < m_minBars) { s_K = -1; Store(k); return; }

      double best = DBL_MAX; int bk = -1;
      for(int j = s_A + 2; j <= k - 2; j++)
      {
         if(d < 0 && !(m_cl[j] <= m_cl[j - 1] && m_cl[j] < m_cl[j + 1])) continue;
         if(d > 0 && !(m_ch[j] >= m_ch[j - 1] && m_ch[j] > m_ch[j + 1])) continue;
         double dt = (double)(m_ct[j] - m_ct[s_A]);
         if(dt <= 0) continue;
         double sl = (d < 0 ? (m_cl[j] - s_Ap) / dt : (s_Ap - m_ch[j]) / dt);
         if(sl < best) { best = sl; bk = j; }
      }
      if(bk < 0 || best <= 0) { s_K = -1; Store(k); return; }

      double ext = 0;
      for(int j = s_A; j < k; j++)
      {
         if(d < 0 && m_ch[j] - s_Ap > ext) ext = m_ch[j] - s_Ap;
         if(d > 0 && s_Ap - m_cl[j] > ext) ext = s_Ap - m_cl[j];
      }
      if(ext < m_minATR * atr) { s_K = -1; Store(k); return; }

      s_slope = (d < 0 ? best : -best);
      s_K = bk;
      s_ext = (d < 0 ? s_Ap + ext : s_Ap - ext);

      double v = CLv(k);
      if((d < 0 && m_cc[k] < v - dpt) || (d > 0 && m_cc[k] > v + dpt)) { s_broken = true; s_brk = k; }
      Store(k);
   }
};

#endif
