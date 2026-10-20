#!/usr/bin/env python3
"""
LAB_LSR_SNAP_001 — CrowdFade research: L/S peak "snap" as a move trigger.

Hypotheses tested (BTCUSDT, Binance, 5m):
  H1  Entry: L/S z-score reaches a peak extreme, then snaps back fast -> a move has started.
      Direction variants: PRICE (side of the price move during the snap) vs FADE (anti-crowd).
  H2  Bigger peak |z| and faster snap -> bigger move (MFE).
  H3  Exit: compare fixed 2R, Z0, opposite z-extreme (OPP), L/S slope reversal (SLOPE), COMBO.
  H4  Path question: when the skew unwinds, what decides price up vs down?
      Candidates: basis sign, spot CVD slope, taker ratio, OI change.
  H5  Lead/lag: does dL/S lead or lag price? (with publication delay)

Data (public archive, no keys): https://data.binance.vision
  futures/um/daily/metrics/BTCUSDT               5m: OI, L/S accounts, top trader accts/positions, taker ratio
  futures/um/monthly|daily/klines/BTCUSDT/5m     futures OHLC
  futures/um/monthly|daily/premiumIndexKlines/BTCUSDT/5m   premium index (basis proxy)
  spot/monthly|daily/klines/BTCUSDT/5m           spot taker buy volume -> spot delta / CVD

No look-ahead: every feature at bar i uses data with close_time <= i.
Metrics are treated as usable DELAY bars after their timestamp (default 1 = next bar).
Same-bar stop+target -> stop first (conservative).

Usage:
  pip install pandas numpy requests
  python LAB_LSR_SNAP_001.py --start 2022-01-01 --end 2026-10-19
  python LAB_LSR_SNAP_001.py --synthetic          # plumbing self-test, no network
Outputs: ./lab_out/report.md, events.csv, trades.csv
"""
import argparse, io, math, os, sys, time, zipfile
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

BASE = "https://data.binance.vision/data"
SYM = "BTCUSDT"
BAR = pd.Timedelta(minutes=5)

# ----------------------------------------------------------------------------- params
P = dict(
    Z_WIN=288,        # z-score window (bars) = 24h
    Z_PEAK=1.5,       # |z| peak threshold
    PEAK_LOOK=12,     # peak must be within last N bars (1h)
    SNAP_K=3,         # snap measured over K bars
    SNAP_MIN=0.5,     # z must move back by >= this over K bars
    COOLDOWN=48,      # bars between events (4h)
    DELAY=1,          # metric usable after N bars (publication delay)
    ATR_N=48,         # ATR window (bars)
    SL_ATR=1.0,       # stop = 1 ATR -> 1R
    FT_HORIZON=48,    # first-touch horizon (bars)
    MFE_HORIZON=48,   # MFE/MAE horizon (bars)
    MAX_HOLD=288,     # time stop for exit models (bars) = 24h
    COST_BPS=4.0,     # round-trip cost in bps (spread+slippage+fees)
    LEVEL_LOOK=288,   # "significant level" proxy: prior 24h high/low
    FEAT_LOOK=12,     # lookback for flow features (1h)
    OOS_FROM="2025-01-01",
)

# ----------------------------------------------------------------------------- download
def _get(url, cache_dir, retries=3):
    os.makedirs(cache_dir, exist_ok=True)
    fn = os.path.join(cache_dir, url.split("/")[-1])
    if os.path.exists(fn):
        return fn if os.path.getsize(fn) > 0 else None
    import requests
    for a in range(retries):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 404:
                open(fn, "wb").close()          # remember missing
                return None
            r.raise_for_status()
            with open(fn, "wb") as f:
                f.write(r.content)
            return fn
        except Exception as e:
            if a == retries - 1:
                print(f"  ! failed {url}: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (a + 1))


def _read_zip_csv(fn, header):
    with zipfile.ZipFile(fn) as z:
        name = z.namelist()[0]
        raw = z.read(name)
    df = pd.read_csv(io.BytesIO(raw), header=None)
    # some archive files carry a header row, some don't
    first = str(df.iloc[0, 0])
    if not first.replace(".", "").isdigit() and not first[:4].isdigit():
        df = df.iloc[1:].reset_index(drop=True)
    elif header == "metrics" and not first[:4].isdigit():
        df = df.iloc[1:].reset_index(drop=True)
    return df


def _months(start, end):
    d = date(start.year, start.month, 1)
    while d <= end:
        yield d
        d = date(d.year + (d.month // 12), d.month % 12 + 1, 1)


def _days(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def load_klines(kind, start, end, cache):
    """kind: 'futures', 'spot', 'premium'. Monthly files for full months, daily for the rest."""
    if kind == "futures":
        root, sub = f"{BASE}/futures/um", "klines"
    elif kind == "premium":
        root, sub = f"{BASE}/futures/um", "premiumIndexKlines"
    else:
        root, sub = f"{BASE}/spot", "klines"
    frames = []
    today_month = date(end.year, end.month, 1)
    for m in _months(start, end):
        tag = f"{m.year}-{m.month:02d}"
        fn = None
        if m < today_month:
            fn = _get(f"{root}/monthly/{sub}/{SYM}/5m/{SYM}-5m-{tag}.zip", os.path.join(cache, kind))
        if fn:
            frames.append(_read_zip_csv(fn, "klines"))
        else:  # current month or missing monthly -> daily files
            last = min(end, date(m.year + (m.month // 12), m.month % 12 + 1, 1) - timedelta(days=1))
            for d in _days(max(start, m), last):
                fn = _get(f"{root}/daily/{sub}/{SYM}/5m/{SYM}-5m-{d.isoformat()}.zip", os.path.join(cache, kind))
                if fn:
                    frames.append(_read_zip_csv(fn, "klines"))
        print(f"  {kind} {tag}: files so far {len(frames)}")
    if not frames:
        raise RuntimeError(f"no {kind} kline data")
    df = pd.concat(frames, ignore_index=True)
    df = df.iloc[:, :11]
    df.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time_raw",
                  "quote_vol", "trades", "taker_buy_base", "taker_buy_quote"]
    ot = pd.to_numeric(df["open_time"], errors="coerce")
    ot = np.where(ot > 1e14, ot / 1000, ot)   # spot 2025+ uses microseconds
    df["t"] = pd.to_datetime(ot, unit="ms", utc=True) + BAR   # index by bar CLOSE time
    for c in ["open", "high", "low", "close", "volume", "taker_buy_base"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["t"]).drop_duplicates("t").set_index("t").sort_index()


def load_metrics(start, end, cache):
    from concurrent.futures import ThreadPoolExecutor
    urls = [f"{BASE}/futures/um/daily/metrics/{SYM}/{SYM}-metrics-{d.isoformat()}.zip"
            for d in _days(start, end)]
    with ThreadPoolExecutor(16) as ex:   # parallel prefetch into cache
        list(ex.map(lambda u: _get(u, os.path.join(cache, "metrics")), urls))
    frames = []
    for d in _days(start, end):
        fn = _get(f"{BASE}/futures/um/daily/metrics/{SYM}/{SYM}-metrics-{d.isoformat()}.zip",
                  os.path.join(cache, "metrics"))
        if fn:
            with zipfile.ZipFile(fn) as z:
                frames.append(pd.read_csv(io.BytesIO(z.read(z.namelist()[0]))))
        if d.day == 1:
            print(f"  metrics {d:%Y-%m}: days so far {len(frames)}")
    if not frames:
        raise RuntimeError("no metrics data")
    m = pd.concat(frames, ignore_index=True)
    m["t"] = pd.to_datetime(m["create_time"], utc=True)
    keep = {
        "sum_open_interest": "oi",
        "count_toptrader_long_short_ratio": "top_acc",
        "sum_toptrader_long_short_ratio": "top_pos",
        "count_long_short_ratio": "ls",
        "sum_taker_long_short_vol_ratio": "taker",
    }
    m = m[["t"] + list(keep)].rename(columns=keep)
    for c in keep.values():
        m[c] = pd.to_numeric(m[c], errors="coerce")
    m["t"] = m["t"].dt.floor("5min")
    return m.drop_duplicates("t").set_index("t").sort_index()


def build_dataset(start, end, cache):
    print("Downloading / loading from cache ...")
    fut = load_klines("futures", start, end, cache)
    spot = load_klines("spot", start, end, cache)
    prem = load_klines("premium", start, end, cache)
    met = load_metrics(start, end, cache)
    df = fut[["open", "high", "low", "close"]].copy()
    df["spot_delta"] = (2 * spot["taker_buy_base"] - spot["volume"]).reindex(df.index)
    df["premium"] = prem["close"].reindex(df.index)
    # metrics usable DELAY bars after timestamp
    met = met.reindex(df.index).ffill(limit=2)
    met = met.shift(P["DELAY"])
    df = df.join(met)
    return df


# ----------------------------------------------------------------------------- synthetic
def synthetic(n=60000, seed=7):
    """Plumbing test only. Crowd L/S mean-reverts and reacts to price; no real edge implied."""
    rng = np.random.default_rng(seed)
    t = pd.date_range("2023-01-01", periods=n, freq="5min", tz="UTC") + BAR
    ret = rng.standard_t(4, n) * 0.0012
    close = 30000 * np.exp(np.cumsum(ret))
    high = close * (1 + np.abs(rng.normal(0, 0.0008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.0008, n)))
    open_ = np.r_[close[0], close[:-1]]
    ls = np.empty(n); ls[0] = 1.6
    for i in range(1, n):   # crowd buys dips (contrarian retail), mean-reverts
        ls[i] = ls[i-1] + 0.02 * (1.6 - ls[i-1]) - 8 * ret[i] + rng.normal(0, 0.006)
    df = pd.DataFrame(dict(open=open_, high=np.maximum(high, close), low=np.minimum(low, close),
                           close=close), index=t)
    df["ls"] = ls
    df["top_acc"] = ls * 1.05 + rng.normal(0, 0.01, n)
    df["top_pos"] = 1.5 + rng.normal(0, 0.05, n)
    df["taker"] = np.exp(rng.normal(0, 0.15, n) + 40 * ret)
    df["oi"] = 90000 + np.cumsum(rng.normal(0, 30, n))
    df["spot_delta"] = rng.normal(0, 50, n) + 30000 * ret
    df["premium"] = rng.normal(-0.0001, 0.0002, n)
    for c in ["ls", "top_acc", "top_pos", "taker", "oi"]:
        df[c] = df[c].shift(P["DELAY"])
    return df


# ----------------------------------------------------------------------------- features
def features(df):
    d = df.copy()
    w = P["Z_WIN"]
    mu = d["ls"].rolling(w, min_periods=w // 2).mean()
    sd = d["ls"].rolling(w, min_periods=w // 2).std()
    d["z"] = (d["ls"] - mu) / sd
    d["dz_k"] = d["z"].diff(P["SNAP_K"])
    d["zmax"] = d["z"].rolling(P["PEAK_LOOK"]).max()
    d["zmin"] = d["z"].rolling(P["PEAK_LOOK"]).min()
    tr = pd.concat([d["high"] - d["low"],
                    (d["high"] - d["close"].shift()).abs(),
                    (d["low"] - d["close"].shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(P["ATR_N"]).mean()
    d["ret_k"] = d["close"].diff(P["SNAP_K"])
    L, F = P["LEVEL_LOOK"], P["FEAT_LOOK"]
    d["prior_hi"] = d["high"].shift(P["SNAP_K"] + 1).rolling(L).max()
    d["prior_lo"] = d["low"].shift(P["SNAP_K"] + 1).rolling(L).min()
    d["broke_hi"] = d["high"].rolling(P["SNAP_K"] + 1).max() > d["prior_hi"]
    d["broke_lo"] = d["low"].rolling(P["SNAP_K"] + 1).min() < d["prior_lo"]
    d["f_basis"] = d["premium"].rolling(F).mean()
    d["f_spotcvd"] = d["spot_delta"].rolling(F).sum()
    d["f_taker"] = np.log(d["taker"]).rolling(F).mean()
    d["f_oi"] = d["oi"].pct_change(F)
    d["f_toppos"] = d["top_pos"].diff(F)
    return d


def find_events(d):
    zp, sm = P["Z_PEAK"], P["SNAP_MIN"]
    long_skew = (d["zmax"] >= zp) & (d["dz_k"] <= -sm)     # crowd long, now unwinding
    short_skew = (d["zmin"] <= -zp) & (d["dz_k"] >= sm)    # crowd short, now unwinding
    idx = np.where((long_skew | short_skew).values & d["atr"].notna().values)[0]
    ev, last = [], -10**9
    for i in idx:
        if i - last < P["COOLDOWN"]:
            continue
        last = i
        row = d.iloc[i]
        skew = 1 if long_skew.iloc[i] else -1
        ev.append(dict(i=i, t=d.index[i], skew=skew,
                       peak=row["zmax"] if skew == 1 else row["zmin"],
                       snap=row["dz_k"], ret_k=row["ret_k"], atr=row["atr"],
                       level=bool(row["broke_hi"] or row["broke_lo"]),
                       f_basis=row["f_basis"], f_spotcvd=row["f_spotcvd"],
                       f_taker=row["f_taker"], f_oi=row["f_oi"], f_toppos=row["f_toppos"]))
    return pd.DataFrame(ev)


# ----------------------------------------------------------------------------- outcomes
def first_touch(d, i0, side, mult, horizon):
    """+1 target first, -1 stop first, 0 neither. side +1 long / -1 short. Entry close[i0]."""
    e, a = d["close"].iat[i0], d["atr"].iat[i0]
    up, dn = e + mult * a, e - mult * a
    H, L = d["high"].values, d["low"].values
    for j in range(i0 + 1, min(i0 + 1 + horizon, len(d))):
        hit_up, hit_dn = H[j] >= up, L[j] <= dn
        if hit_up and hit_dn:
            return -1            # conservative: adverse first
        if hit_up:
            return 1 if side == 1 else -1
        if hit_dn:
            return -1 if side == 1 else 1
    return 0


def mfe_mae(d, i0, side, horizon):
    e, a = d["close"].iat[i0], d["atr"].iat[i0]
    sl = slice(i0 + 1, min(i0 + 1 + horizon, len(d)))
    hi, lo = d["high"].values[sl], d["low"].values[sl]
    if len(hi) == 0:
        return np.nan, np.nan
    if side == 1:
        return (hi.max() - e) / a, (e - lo.min()) / a
    return (e - lo.min()) / a, (hi.max() - e) / a


def simulate_exit(d, i0, side, skew, model):
    """Returns R (after cost). Stop = SL_ATR*ATR always on. Entry at close[i0]."""
    e, a = d["close"].iat[i0], d["atr"].iat[i0]
    risk = P["SL_ATR"] * a
    stop = e - side * risk
    H, L, C = d["high"].values, d["low"].values, d["close"].values
    Z, DZ = d["z"].values, d["dz_k"].values
    zp, sm = P["Z_PEAK"], P["SNAP_MIN"]
    cost_r = P["COST_BPS"] / 1e4 * e / risk
    half_done, booked, best = False, 0.0, e
    end = min(i0 + 1 + P["MAX_HOLD"], len(d))
    for j in range(i0 + 1, end):
        # stop first (conservative)
        if (side == 1 and L[j] <= stop) or (side == -1 and H[j] >= stop):
            r = side * (stop - e) / risk
            return (booked + (0.5 if half_done else 1.0) * r) - cost_r
        if model == "R2":
            tgt = e + side * 2 * risk
            if (side == 1 and H[j] >= tgt) or (side == -1 and L[j] <= tgt):
                return 2.0 - cost_r
            continue
        z, dz = Z[j], DZ[j]
        if np.isnan(z):
            continue
        r_now = side * (C[j] - e) / risk
        z0 = (z <= 0) if skew == 1 else (z >= 0)
        if model == "Z0" and z0:
            return r_now - cost_r
        if model == "OPP" and ((skew == 1 and z <= -zp) or (skew == -1 and z >= zp)):
            return r_now - cost_r
        if model == "SLOPE" and ((skew == 1 and dz >= sm) or (skew == -1 and dz <= -sm)):
            return r_now - cost_r
        if model == "COMBO":
            if not half_done and z0:
                booked, half_done = 0.5 * r_now, True
                stop = max(stop, e) if side == 1 else min(stop, e)   # runner to breakeven
            if half_done:
                best = max(best, C[j]) if side == 1 else min(best, C[j])
                trail = best - side * 1.5 * a
                stop = max(stop, trail) if side == 1 else min(stop, trail)
    r_now = side * (C[end - 1] - e) / risk
    return (booked + (0.5 if half_done else 1.0) * r_now) - cost_r


# ----------------------------------------------------------------------------- stats
def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, c - h, c + h


def boot_mean(x, n=2000, seed=1):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 5:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    bs = rng.choice(x, (n, len(x))).mean(1)
    return x.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def spearman(a, b):
    s = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(s) < 10:
        return np.nan
    return s["a"].rank().corr(s["b"].rank())


def fmt_p(p, lo, hi, n):
    if n == 0 or np.isnan(p):
        return f"n=0"
    return f"{p*100:5.1f}% [{lo*100:4.1f}–{hi*100:4.1f}] n={n}"


def fmt_m(m, lo, hi):
    if np.isnan(m):
        return "—"
    return f"{m:+.3f} [{lo:+.3f}…{hi:+.3f}]"


# ----------------------------------------------------------------------------- main analysis
def analyze(d, outdir):
    os.makedirs(outdir, exist_ok=True)
    d = features(d)
    ev = find_events(d)
    if ev.empty:
        print("No events found — loosen Z_PEAK / SNAP_MIN.")
        return
    oos = pd.Timestamp(P["OOS_FROM"], tz="UTC")
    ev["split"] = np.where(ev["t"] >= oos, "OOS", "IS")
    ev["dir_price"] = np.sign(ev["ret_k"]).astype(int)
    ev["dir_fade"] = -ev["skew"]
    entry_i = ev["i"].values

    # base rate: random bars, first-touch +-1ATR long
    rng = np.random.default_rng(3)
    valid = np.where(d["atr"].notna().values)[0]
    valid = valid[valid < len(d) - P["FT_HORIZON"] - 2]
    samp = rng.choice(valid, min(5000, len(valid)), replace=False)
    base = [first_touch(d, i, 1, 1.0, P["FT_HORIZON"]) for i in samp]
    base = np.array([b for b in base if b != 0])
    base_up = (base == 1).mean() if len(base) else np.nan

    rows = []
    for _, e in ev.iterrows():
        i = int(e["i"])
        rec = dict(t=e["t"], split=e["split"], skw=e["skew"], peak=e["peak"], snap=e["snap"],
                   level=e["level"], dir_price=e["dir_price"], dir_fade=e["dir_fade"],
                   f_basis=e["f_basis"], f_spotcvd=e["f_spotcvd"], f_taker=e["f_taker"],
                   f_oi=e["f_oi"], f_toppos=e["f_toppos"])
        rec["ft_up_1atr"] = first_touch(d, i, 1, 1.0, P["FT_HORIZON"])
        for name in ["price", "fade"]:
            side = int(e[f"dir_{name}"])
            if side == 0:
                continue
            rec[f"ft1_{name}"] = first_touch(d, i, side, 1.0, P["FT_HORIZON"])
            rec[f"ft2_{name}"] = first_touch(d, i, side, 2.0, P["FT_HORIZON"])
            mfe, mae = mfe_mae(d, i, side, P["MFE_HORIZON"])
            rec[f"mfe_{name}"], rec[f"mae_{name}"] = mfe, mae
            for m in ["R2", "Z0", "OPP", "SLOPE", "COMBO"]:
                rec[f"R_{m}_{name}"] = simulate_exit(d, i, side, int(e["skew"]), m)
        rows.append(rec)
    tr = pd.DataFrame(rows)
    tr.to_csv(os.path.join(outdir, "trades.csv"), index=False)
    ev.to_csv(os.path.join(outdir, "events.csv"), index=False)

    # lead/lag
    dz1 = d["z"].diff()
    r1 = d["close"].pct_change()
    lags = {lag: dz1.corr(r1.shift(-lag)) for lag in range(-6, 7)}

    L = []
    w = L.append
    w("# LAB_LSR_SNAP_001 — L/S peak snap\n")
    w(f"Data: {d.index[0]:%Y-%m-%d} → {d.index[-1]:%Y-%m-%d}, bars={len(d):,}. "
      f"OOS from {P['OOS_FROM']}.\n")
    w("Params: " + ", ".join(f"{k}={v}" for k, v in P.items()) + "\n")
    w(f"Events: {len(tr)} (long-skew {int((tr.skw==1).sum())}, short-skew {int((tr.skw==-1).sum())}); "
      f"with level break: {int(tr.level.sum())}\n")
    w(f"Base rate (random bar, long, ±1 ATR first touch): {base_up*100:.1f}% n={len(base)}\n")

    w("\n## H1 — Direction after snap (first touch ±1 ATR / ±2 ATR, horizon "
      f"{P['FT_HORIZON']} bars)\n")
    w("| Variant | Split | Win ±1ATR | Win ±2ATR | MFE mean (ATR) | MAE mean (ATR) |")
    w("|---|---|---|---|---|---|")
    for name in ["price", "fade"]:
        for sp in ["IS", "OOS", "ALL"]:
            s = tr if sp == "ALL" else tr[tr.split == sp]
            for lvl in [None, True]:
                ss = s if lvl is None else s[s.level]
                lab = name.upper() + (" + level" if lvl else "")
                c1 = ss[f"ft1_{name}"].dropna(); c1 = c1[c1 != 0]
                c2 = ss[f"ft2_{name}"].dropna(); c2 = c2[c2 != 0]
                p1 = wilson(int((c1 == 1).sum()), len(c1))
                p2 = wilson(int((c2 == 1).sum()), len(c2))
                w(f"| {lab} | {sp} | {fmt_p(*p1, len(c1))} | {fmt_p(*p2, len(c2))} | "
                  f"{ss[f'mfe_{name}'].mean():.2f} | {ss[f'mae_{name}'].mean():.2f} |")
    w("\nWin ±1ATR: 50% = coin. Win ±2ATR is symmetric too (target 2ATR vs stop 2ATR).")

    w("\n## H2 — Magnitude: peak |z| and snap speed vs MFE (Spearman)\n")
    for name in ["price", "fade"]:
        w(f"- {name.upper()}: ρ(|peak|, MFE) = {spearman(tr.peak.abs(), tr[f'mfe_{name}']):+.3f}; "
          f"ρ(|snap|, MFE) = {spearman(tr.snap.abs(), tr[f'mfe_{name}']):+.3f}")
    q = pd.qcut(tr.peak.abs(), 3, labels=["low", "mid", "high"], duplicates="drop")
    w("\n| |peak| tercile | n | MFE price | MFE fade |")
    w("|---|---|---|---|")
    for g, s in tr.groupby(q, observed=True):
        w(f"| {g} | {len(s)} | {s.mfe_price.mean():.2f} | {s.mfe_fade.mean():.2f} |")

    w(f"\n## H3 — Exit models (R after {P['COST_BPS']} bps cost, stop {P['SL_ATR']} ATR, "
      f"max hold {P['MAX_HOLD']} bars)\n")
    w("| Variant | Exit | IS mean R [95% CI] | OOS mean R [95% CI] | win% ALL |")
    w("|---|---|---|---|---|")
    for name in ["price", "fade"]:
        for m in ["R2", "Z0", "OPP", "SLOPE", "COMBO"]:
            col = f"R_{m}_{name}"
            a = boot_mean(tr.loc[tr.split == "IS", col])
            b = boot_mean(tr.loc[tr.split == "OOS", col])
            wr = (tr[col] > 0).mean() * 100
            w(f"| {name.upper()} | {m} | {fmt_m(*a)} | {fmt_m(*b)} | {wr:.1f}% |")

    w("\n## H4 — Path: P(price up first, ±1 ATR) by flow feature at the snap\n")
    w("Long-skew = crowd long and unwinding. Base rate above.\n")
    ft = tr[tr.ft_up_1atr != 0].copy()
    ft["up"] = (ft.ft_up_1atr == 1).astype(int)
    feats = {"basis<0 (perp discount)": ft.f_basis < 0,
             "spot CVD 1h > 0": ft.f_spotcvd > 0,
             "taker 1h > 1 (buyers)": ft.f_taker > 0,
             "OI 1h falling": ft.f_oi < 0,
             "top positions 1h falling": ft.f_toppos < 0}
    w("| Skew | Feature | TRUE | FALSE |")
    w("|---|---|---|---|")
    for sk, lab in [(1, "long"), (-1, "short")]:
        s = ft[ft["skw"] == sk]
        for fname, mask in feats.items():
            mk = mask.loc[s.index]
            a, b = s[mk], s[~mk]
            pa = wilson(int(a.up.sum()), len(a)); pb = wilson(int(b.up.sum()), len(b))
            w(f"| {lab} | {fname} | {fmt_p(*pa, len(a))} | {fmt_p(*pb, len(b))} |")
    w("\nSignal = the TRUE/FALSE intervals don't overlap and both differ from the base rate.")

    w("\n## H5 — Lead/lag: corr(Δz[t], return[t+lag]), 5m, metric delay "
      f"{P['DELAY']} bar(s)\n")
    w("| lag | corr |")
    w("|---|---|")
    for lag, c in lags.items():
        w(f"| {lag:+d} | {c:+.4f} |")
    w("\nNegative lags = price before Δz (L/S reacts to price). Positive lags = Δz predicts price.")

    w("\n## Reading guide\n")
    w("- Edge only if OOS confirms IS and the CI excludes 0 (R) or 50% (win rate).")
    w("- Prop rule: a variant is worth an EA only with OOS mean R > 0 after costs AND enough events.")
    rep = "\n".join(L)
    with open(os.path.join(outdir, "report.md"), "w") as f:
        f.write(rep)
    print(rep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2022-01-01")
    ap.add_argument("--end", default=(date.today() - timedelta(days=2)).isoformat())
    ap.add_argument("--cache", default="./binance_cache")
    ap.add_argument("--out", default="./lab_out")
    ap.add_argument("--synthetic", action="store_true")
    for k, v in P.items():
        ap.add_argument(f"--{k.lower()}", type=type(v), default=v)
    a = ap.parse_args()
    for k in P:
        P[k] = getattr(a, k.lower())
    if a.synthetic:
        d = synthetic()
        P["OOS_FROM"] = "2023-05-01"
    else:
        s, e = date.fromisoformat(a.start), date.fromisoformat(a.end)
        d = build_dataset(s, e, a.cache)
    d = d.dropna(subset=["close", "ls"])
    analyze(d, a.out)


if __name__ == "__main__":
    main()
