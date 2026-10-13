"""
trendlines.py — метод трендових ліній TrendAssist v1.23 для CrowdFade.

Порт логіки (не індикатора): структура головного ТФ (H4) + лінія корекції CorrTF (H1)
з віялом до 3 ліній, хибним зламом і перезапуском, + тригер зламу на робочому ТФ (M5).
Безперервний автомат від першого бару даних (як v1.23): результат не залежить від вікна.

Відповідність MQL5 (TrendAssist_v1.23.mq5):
  Structure.step        <- CStructure::Step
  compute_main          <- UpdateMain
  main_trend_at         <- MainTrendAt   (лише ЗАКРИТИЙ бар H4 до бару, що містить t)
  CorrEngine.step       <- CorrStep
  compute_corr          <- UpdateCorr
  cl_break_signals      <- ProcessBar, блок 7 (сигнал зламу лінії корекції)

Використання в CrowdFade (стан, а не сигнал індикатора):
  main = compute_main(h4)                 # тренд H4 після кожного закритого H4
  corr = compute_corr(h1, main)           # стан лінії корекції після кожного закритого H1
  sig  = cl_break_signals(m5, corr, main) # події зламу на M5
Кожен рядок corr/main містить тільки те, що було відомо на закритті цього бару.

Час: усі індекси — час ВІДКРИТТЯ бару. H4/H1 треба будувати з M5 у часі сервера брокера
(resample_server_time), бо межі H4 залежать від часового поясу.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- параметри
@dataclass
class TLParams:
    main_swing_left: int = 2
    main_swing_right: int = 2
    atr_period: int = 14
    cl_lookback: int = 120
    cl_min_bars: int = 3
    cl_min_atr: float = 1.5
    cl_break_atr: float = 0.25
    cl_signal_fan: int = 2
    # тригер на робочому ТФ
    cl_max_sl_atr: float = 4.0
    cl_sl_bars: int = 10
    sl_buffer_atr: float = 0.3
    min_sl_atr: float = 0.5
    cooldown_bars: int = 6
    use_main_filter: bool = True


# ---------------------------------------------------------------- дані
def resample_server_time(m5: pd.DataFrame, rule: str, server_offset_hours: float = 0.0) -> pd.DataFrame:
    """M5 (індекс = час відкриття, UTC) -> бари `rule` з межами за часом сервера.
    server_offset_hours: зсув сервера від UTC (напр. 2 або 3; для DST передай Series у m5 вручну)."""
    x = m5.copy()
    x.index = x.index + pd.Timedelta(hours=server_offset_hours)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in x.columns:
        agg["volume"] = "sum"
    out = x.resample(rule, label="left", closed="left").agg(agg).dropna(subset=["open"])
    return out


def atr_mt5(df: pd.DataFrame, period: int = 14) -> np.ndarray:
    """ATR як у вбудованому iATR MT5: просте середнє True Range (не Wilder).
    Перевір на колонці atr з логу TrendAssist v1.23."""
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    pc = np.roll(c, 1)
    tr = np.maximum(h, pc) - np.minimum(l, pc)
    tr[0] = h[0] - l[0]
    atr = pd.Series(tr).rolling(period, min_periods=period).mean().to_numpy()
    return np.nan_to_num(atr, nan=0.0)


# ---------------------------------------------------------------- структура (CStructure)
@dataclass
class Structure:
    L: int
    R: int
    trend: int = 0
    paused: bool = False
    hi1: float = 0.0
    hi2: float = 0.0
    lo1: float = 0.0
    lo2: float = 0.0
    hi1Idx: int = -1
    hi2Idx: int = -1
    lo1Idx: int = -1
    lo2Idx: int = -1
    brokenHi: int = -1
    brokenLo: int = -1
    evBreak: int = 0

    def _line_value(self, i: int):
        if self.trend == -1 and self.hi2Idx >= 0 and self.hi1 < self.hi2 and self.hi1Idx > self.hi2Idx:
            s = (self.hi1 - self.hi2) / (self.hi1Idx - self.hi2Idx)
            return self.hi1 + s * (i - self.hi1Idx)
        if self.trend == 1 and self.lo2Idx >= 0 and self.lo1 > self.lo2 and self.lo1Idx > self.lo2Idx:
            s = (self.lo1 - self.lo2) / (self.lo1Idx - self.lo2Idx)
            return self.lo1 + s * (i - self.lo1Idx)
        return None

    def step(self, i: int, h: np.ndarray, l: np.ndarray, c: np.ndarray) -> None:
        self.evBreak = 0
        p = i - self.R
        if p - self.L >= 0:
            if self._pivot_high(p, h):
                lbl_lh = self.hi1Idx >= 0 and not (h[p] > self.hi1)
                self.hi2, self.hi2Idx, self.hi1, self.hi1Idx = self.hi1, self.hi1Idx, h[p], p
                if lbl_lh and self.trend == -1:
                    self.paused = False
            if self._pivot_low(p, l):
                lbl_hl = self.lo1Idx >= 0 and not (l[p] < self.lo1)
                self.lo2, self.lo2Idx, self.lo1, self.lo1Idx = self.lo1, self.lo1Idx, l[p], p
                if lbl_hl and self.trend == 1:
                    self.paused = False
        if self.hi1Idx >= 0 and self.brokenHi != self.hi1Idx and c[i] > self.hi1:
            self.brokenHi = self.hi1Idx
            self.evBreak = 1 if self.trend == 1 else 2
            self.trend, self.paused = 1, False
        if self.lo1Idx >= 0 and self.brokenLo != self.lo1Idx and c[i] < self.lo1:
            self.brokenLo = self.lo1Idx
            self.evBreak = -1 if self.trend == -1 else -2
            self.trend, self.paused = -1, False
        v = self._line_value(i)
        if v is not None:
            if self.trend == -1 and c[i] > v:
                self.paused = True
            if self.trend == 1 and c[i] < v:
                self.paused = True

    def _pivot_high(self, p, h):
        return not (np.any(h[p - self.L:p] >= h[p]) or np.any(h[p + 1:p + self.R + 1] > h[p]))

    def _pivot_low(self, p, l):
        return not (np.any(l[p - self.L:p] <= l[p]) or np.any(l[p + 1:p + self.R + 1] < l[p]))


def compute_main(h4: pd.DataFrame, prm: TLParams = TLParams()) -> pd.DataFrame:
    """Тренд H4 ПІСЛЯ закриття кожного бару (trend_after_close) + подія BOS/CHoCH."""
    h, l, c = (h4[k].to_numpy(float) for k in ("high", "low", "close"))
    s = Structure(prm.main_swing_left, prm.main_swing_right)
    tr = np.zeros(len(h4), int)
    ev = np.zeros(len(h4), int)
    for k in range(len(h4)):
        s.step(k, h, l, c)
        tr[k], ev[k] = s.trend, s.evBreak
    return pd.DataFrame({"trend_after_close": tr, "break_event": ev}, index=h4.index)


def main_trend_at(main: pd.DataFrame, t) -> int:
    """Тренд H4 на момент t: останній ЗАКРИТИЙ H4 до бару, що містить t (без заглядання)."""
    idx = main.index
    j = idx.searchsorted(t, side="right") - 1      # бар H4, що містить t
    k = j - 1
    if k < 0:
        return 0
    return int(main["trend_after_close"].iat[k])


# ---------------------------------------------------------------- лінія корекції (CorrStep)
@dataclass
class CorrEngine:
    prm: TLParams
    ct: np.ndarray  # час відкриття, секунди
    ch: np.ndarray
    cl: np.ndarray
    cc: np.ndarray
    catr: np.ndarray
    dir: int = 0
    A: int = -1
    K: int = -1
    brk: int = -1
    floor: int = 0
    fail: int = -1
    fan: int = 1
    prevN: int = 0
    broken: bool = False
    Ap: float = 0.0
    slope: float = 0.0           # ціна за секунду
    ext: float = 0.0
    prev_lines: list = field(default_factory=list)  # (slope, K_time) зламаних ліній віяла

    def _clv(self, k):
        return self.Ap + self.slope * float(self.ct[k] - self.ct[self.A])

    def _better(self, d, j, best):
        if best < 0:
            return True
        return self.cl[j] < self.cl[best] if d < 0 else self.ch[j] > self.ch[best]

    def _save_fan(self):
        if self.K < 0 or self.A < 0:
            return
        if self.prevN >= 2:
            self.prev_lines = self.prev_lines[1:]
            self.prevN = 1
        self.prev_lines = self.prev_lines[: self.prevN] + [(self.slope, int(self.ct[self.K]))]
        self.prevN += 1

    def step(self, k: int, d: int) -> bool:
        """Один закритий бар CorrTF. d = MainTrendAt(ct[k]). Повертає True, якщо лінія валідна."""
        P = self.prm
        cl, ch, cc = self.cl, self.ch, self.cc
        atr = self.catr[k]
        if d != self.dir:
            self.dir, self.A, self.K, self.broken, self.brk, self.floor, self.fail = d, -1, -1, False, -1, 0, -1
            self.fan, self.prevN = 1, 0
        if d == 0 or atr <= 0:
            self.K = -1
            return self.valid()
        dpt = P.cl_break_atr * atr

        if self.broken:
            vb = self._clv(k)
            seg = range(self.brk + 1, k + 1)
            new_ext = any((d < 0 and cl[j] < self.Ap) or (d > 0 and ch[j] > self.Ap) for j in seg)
            failed = (d < 0 and (cc[k] > vb + dpt or cc[k] > self.ext)) or \
                     (d > 0 and (cc[k] < vb - dpt or cc[k] < self.ext))
            new_piv = False
            for j in range(self.brk + 1, k - 1):
                if d < 0 and cl[j] <= cl[j - 1] and cl[j] < cl[j + 1] and cl[j] > self.Ap:
                    new_piv = True
                if d > 0 and ch[j] >= ch[j - 1] and ch[j] > ch[j + 1] and ch[j] < self.Ap:
                    new_piv = True
            if new_ext:
                self.broken, self.floor, self.A, self.fail, self.fan, self.prevN = False, self.brk + 1, -1, -1, 1, 0
            elif failed:
                self.broken, self.fail, self.floor = False, k, self.A
            elif new_piv and self.fan < 3:
                self._save_fan()
                self.broken, self.floor = False, self.A
                self.fan += 1
            elif self.fan >= 3:
                A2 = -1
                for j in range(self.brk + 1, k + 1):
                    if self._better(d, j, A2):
                        A2 = j
                fresh = False
                if A2 >= 0 and k - A2 >= P.cl_min_bars:
                    if d < 0:
                        bounce = max(ch[A2:k + 1] - cl[A2])
                    else:
                        bounce = max(ch[A2] - cl[A2:k + 1])
                    fresh = bounce >= P.cl_min_atr * atr
                if not fresh:
                    return self.valid()
                self.broken, self.floor, self.A, self.fail, self.fan, self.prevN = False, self.brk + 1, -1, -1, 1, 0
            else:
                return self.valid()

        # якір A
        frm = max(self.floor, k - P.cl_lookback, 0)
        A = -1
        for j in range(frm, k + 1):
            if self._better(d, j, A):
                A = j
        if A != self.A:
            self.A, self.K, self.fan, self.prevN = A, -1, 1, 0
            self.Ap = cl[A] if d < 0 else ch[A]
        if k - 1 - self.A < P.cl_min_bars:
            self.K = -1
            return self.valid()

        # дотична через свінги 1/1 від якоря
        best, bk = np.inf, -1
        for j in range(self.A + 2, k - 1):
            if d < 0 and not (cl[j] <= cl[j - 1] and cl[j] < cl[j + 1]):
                continue
            if d > 0 and not (ch[j] >= ch[j - 1] and ch[j] > ch[j + 1]):
                continue
            dt = float(self.ct[j] - self.ct[self.A])
            if dt <= 0:
                continue
            sl = (cl[j] - self.Ap) / dt if d < 0 else (self.Ap - ch[j]) / dt
            if sl < best:
                best, bk = sl, j
        if bk < 0 or best <= 0:
            self.K = -1
            return self.valid()

        if d < 0:
            ext = float(np.max(ch[self.A:k] - self.Ap)) if k > self.A else 0.0
        else:
            ext = float(np.max(self.Ap - cl[self.A:k])) if k > self.A else 0.0
        ext = max(ext, 0.0)
        if ext < P.cl_min_atr * atr:
            self.K = -1
            return self.valid()

        self.slope = best if d < 0 else -best
        self.K = bk
        self.ext = self.Ap + ext if d < 0 else self.Ap - ext

        v = self._clv(k)
        if (d < 0 and cc[k] < v - dpt) or (d > 0 and cc[k] > v + dpt):
            self.broken, self.brk = True, k
        return self.valid()

    def valid(self) -> bool:
        return self.A >= 0 and self.K > self.A and self.dir != 0


def compute_corr(h1: pd.DataFrame, main: pd.DataFrame, prm: TLParams = TLParams()) -> pd.DataFrame:
    """Стан лінії корекції ПІСЛЯ закриття кожного бару H1 (рядок k = бар з часом відкриття k).
    line(t) = A_price + slope_per_sec * (t - A_time).  Колонки = колонки логу corr.csv v1.23."""
    ct = np.asarray((h1.index - pd.Timestamp(0)) // pd.Timedelta(seconds=1), dtype=np.int64)
    eng = CorrEngine(prm, ct, h1["high"].to_numpy(float), h1["low"].to_numpy(float),
                     h1["close"].to_numpy(float), atr_mt5(h1, prm.atr_period))
    n = len(h1)
    rows = []
    for k in range(n):
        d = main_trend_at(main, h1.index[k]) if k >= 1 else 0
        ok = eng.step(k, d) if k >= 1 else False
        rows.append(dict(
            main_trend=d, valid=int(ok), dir=eng.dir, broken=int(eng.broken),
            break_time=h1.index[eng.brk] if eng.brk >= 0 else pd.NaT,
            fail_time=h1.index[eng.fail] if eng.fail >= 0 else pd.NaT,
            fan=eng.fan,
            A_time=h1.index[eng.A] if ok else pd.NaT,
            A_price=eng.Ap if ok else np.nan,
            K_time=h1.index[eng.K] if ok else pd.NaT,
            slope_per_sec=eng.slope if ok else np.nan,
            corr_extreme=eng.ext,
            atr=eng.catr[k],
        ))
    out = pd.DataFrame(rows, index=h1.index)
    # подія: лінію зламано закриттям саме цього H1
    out["h1_break_now"] = (out["broken"] == 1) & (out["break_time"] == out.index)
    return out


def line_at(corr_row: pd.Series, t) -> float:
    return float(corr_row["A_price"] + corr_row["slope_per_sec"] * (pd.Timestamp(t) - corr_row["A_time"]).total_seconds())


# ---------------------------------------------------------------- тригер на робочому ТФ (ProcessBar, блок 7)
def cl_break_signals(m5: pd.DataFrame, corr: pd.DataFrame, main: pd.DataFrame,
                     prm: TLParams = TLParams()) -> pd.DataFrame:
    """Сигнал зламу лінії корекції на закритті свічки M5 (як стрілка TrendAssist CL_BREAK).
    Вхід у бектесті — open наступної M5. Кулдаун рахується лише між цими сигналами
    (в індикаторі він спільний із сигналами ретесту — тут ретест не відтворено)."""
    t = m5.index
    o, h, l, c = (m5[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    atr = atr_mt5(m5, prm.atr_period)
    cidx = corr.index
    last_buy = last_sell = -10**9
    last_line = None
    out = []
    for i in range(1, len(m5)):
        if atr[i] <= 0:
            continue
        j = cidx.searchsorted(t[i], side="right") - 1
        ci = j - 1
        if ci < 0:
            continue
        r = corr.iloc[ci]
        if r["valid"] != 1 or r["broken"] != 0:
            continue
        d = int(r["dir"])
        key = (r["A_time"], r["K_time"])
        if key == last_line or r["fan"] < prm.cl_signal_fan:
            continue
        mtr = main_trend_at(main, t[i])
        v, v1 = line_at(r, t[i]), line_at(r, t[i - 1])
        dpt = prm.cl_break_atr * atr[i]
        if d < 0 and c[i] < v - dpt and c[i - 1] >= v1 - dpt and c[i] < o[i] \
                and i - last_sell >= prm.cooldown_bars and (not prm.use_main_filter or mtr == -1):
            hi = h[max(0, i - prm.cl_sl_bars):i + 1].max()
            sl = hi + prm.sl_buffer_atr * atr[i]
            risk = sl - c[i]
            if prm.min_sl_atr * atr[i] <= risk <= prm.cl_max_sl_atr * atr[i]:
                last_sell, last_line = i, key
                out.append(dict(time=t[i], dir=-1, close=c[i], sl=sl, atr=atr[i],
                                A_time=r["A_time"], K_time=r["K_time"], fan=int(r["fan"]), main_trend=mtr))
        if d > 0 and c[i] > v + dpt and c[i - 1] <= v1 + dpt and c[i] > o[i] \
                and i - last_buy >= prm.cooldown_bars and (not prm.use_main_filter or mtr == 1):
            lo = l[max(0, i - prm.cl_sl_bars):i + 1].min()
            sl = lo - prm.sl_buffer_atr * atr[i]
            risk = c[i] - sl
            if prm.min_sl_atr * atr[i] <= risk <= prm.cl_max_sl_atr * atr[i]:
                last_buy, last_line = i, key
                out.append(dict(time=t[i], dir=1, close=c[i], sl=sl, atr=atr[i],
                                A_time=r["A_time"], K_time=r["K_time"], fan=int(r["fan"]), main_trend=mtr))
    return pd.DataFrame(out)


# ---------------------------------------------------------------- самоперевірка
if __name__ == "__main__":
    rng = np.random.default_rng(1)
    n = 60 * 24 * 12 * 2                       # ~2 місяці M5
    idx = pd.date_range("2024-01-01", periods=n, freq="5min")
    ret = rng.normal(0, 0.0015, n) + 0.00002 * np.sin(np.arange(n) / 3000)
    close = 40000 * np.exp(np.cumsum(ret))
    op = np.r_[close[0], close[:-1]]
    hi = np.maximum(op, close) * (1 + np.abs(rng.normal(0, 0.0007, n)))
    lo = np.minimum(op, close) * (1 - np.abs(rng.normal(0, 0.0007, n)))
    m5 = pd.DataFrame({"open": op, "high": hi, "low": lo, "close": close}, index=idx)
    h4 = resample_server_time(m5, "4h", 2)
    h1 = resample_server_time(m5, "1h", 2)
    m5s = m5.copy(); m5s.index = m5s.index + pd.Timedelta(hours=2)
    main = compute_main(h4)
    corr = compute_corr(h1, main)
    sig = cl_break_signals(m5s, corr, main)
    print("H4", len(h4), "trend counts", main.trend_after_close.value_counts().to_dict())
    print("H1", len(h1), "valid", int(corr.valid.sum()), "h1 breaks", int(corr.h1_break_now.sum()),
          "fan dist", corr[corr.valid == 1].fan.value_counts().to_dict())
    print("M5 CL_BREAK signals", len(sig))
    print(sig.head())
