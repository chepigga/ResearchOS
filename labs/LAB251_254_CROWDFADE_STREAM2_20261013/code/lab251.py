"""LAB251 — v157 (A+B3_HIGH+R48_HIGH+EARLY, HALF TP3 + LOCK2 + LOCK025 add-on transfer)
+ TrendAssist trendline method roles R1..R4. Exact port of LAB155.replay with hooks."""
from __future__ import annotations
import pickle, sys, json, time
import numpy as np, pandas as pd

sys.path.insert(0, "/home/claude/lab251")
import trendlines as TL

import os
C = pickle.load(open(os.environ.get("LAB_CACHE","/home/claude/lab251/cache.pkl"), "rb"))
BT = pd.DatetimeIndex(C["BT"])
BO, BH, BL, BC, BA = (np.asarray(C[k], float) for k in ("BO", "BH", "BL", "BC", "BA"))
N = len(BT)
RISK = 0.25
MAX_H_BARS = 48 * 12
RUNNER_H_BARS = 96 * 12
PRI = {"A": 0, "B3_HIGH": 1, "R48_HIGH": 2, "EARLY_EPISODE": 3, "T": 4}


# ------------------------------------------------------------------ server time
def server_index(utc_idx: pd.DatetimeIndex, mode: str) -> pd.DatetimeIndex:
    if mode == "UTC":
        return utc_idx.tz_convert("UTC").tz_localize(None)
    # MT5 broker convention: server midnight = 17:00 New York  -> server = NY local + 7h
    return utc_idx.tz_convert("America/New_York").tz_localize(None) + pd.Timedelta(hours=7)


def build_tl(mode: str):
    sidx = server_index(BT, mode)
    m5 = pd.DataFrame({"open": BO, "high": BH, "low": BL, "close": BC}, index=sidx)
    m5 = m5[~m5.index.duplicated(keep="first")]          # DST fall-back overlap (1h/yr)
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    h1 = m5.resample("1h", label="left", closed="left").agg(agg).dropna()
    h4 = m5.resample("4h", label="left", closed="left").agg(agg).dropna()
    t0 = time.time()
    main = TL.compute_main(h4)
    corr = TL.compute_corr(h1, main)
    print(f"[{mode}] H1={len(h1)} H4={len(h4)} tl {time.time()-t0:.0f}s", flush=True)

    # per-M5 (UTC order) mapping to last CLOSED H1 / H4
    h1t = h1.index.values
    j = np.searchsorted(h1t, sidx.values, side="right") - 1
    ci = j - 1                                             # last closed H1
    h4t = main.index.values
    j4 = np.searchsorted(h4t, sidx.values, side="right") - 1
    mtr = np.where(j4 - 1 >= 0, main["trend_after_close"].to_numpy()[np.maximum(j4 - 1, 0)], 0)

    # H1 swings 1/1 (as CorrEngine), confirmed after close of j+1
    hl, hh = h1["low"].to_numpy(), h1["high"].to_numpy()
    n1 = len(h1)
    swl = np.full(n1, np.nan); swh = np.full(n1, np.nan)
    lastL = np.nan; lastH = np.nan
    for k in range(n1):          # value known at close of bar k
        jj = k - 1
        if jj >= 1:
            if hl[jj] <= hl[jj - 1] and hl[jj] < hl[jj + 1]: lastL = hl[jj]
            if hh[jj] >= hh[jj - 1] and hh[jj] > hh[jj + 1]: lastH = hh[jj]
        swl[k] = lastL; swh[k] = lastH
    catr = corr["atr"].to_numpy(float)

    # R3 events: first M5 bar after an H1 close that broke the correction line
    brk = corr["h1_break_now"].to_numpy(bool)
    cdir = corr["dir"].to_numpy(int)
    ev_add = np.zeros(N, int)
    prev = -2
    for i in range(N):
        k = ci[i]
        if k != prev and k >= 0 and brk[k]:
            ev_add[i] = cdir[k]
        prev = k

    # R4 events: M5 close-cross of the correction line (= cl_break_signals), fast port
    T_sig = cl_break_fast(sidx, ci, corr, mtr)
    return dict(sidx=sidx, ci=ci, mtr=mtr, swl=swl, swh=swh, catr=catr, ev_add=ev_add,
                corr=corr, main=main, T=T_sig, h1=h1)


def cl_break_fast(sidx, ci, corr, mtr, prm=TL.TLParams()):
    """Same logic as trendlines.cl_break_signals, numpy arrays. Signal at M5 close i -> entry i+1."""
    tsec = ((sidx - pd.Timestamp(0)) // pd.Timedelta(seconds=1)).to_numpy(np.int64)
    atr5 = TL.atr_mt5(pd.DataFrame({"high": BH, "low": BL, "close": BC}), prm.atr_period)
    valid = corr["valid"].to_numpy(int); broken = corr["broken"].to_numpy(int)
    cdir = corr["dir"].to_numpy(int); fan = corr["fan"].to_numpy(int)
    ap = corr["A_price"].to_numpy(float); sl = corr["slope_per_sec"].to_numpy(float)
    at = corr["A_time"]; kt = corr["K_time"]
    atsec = np.where(at.notna(), ((at - pd.Timestamp(0)) // pd.Timedelta(seconds=1)).fillna(0).astype(np.int64), 0)
    ktsec = np.where(kt.notna(), ((kt - pd.Timestamp(0)) // pd.Timedelta(seconds=1)).fillna(0).astype(np.int64), 0)
    last_buy = last_sell = -10**9; last_line = None; out = []
    for i in range(1, N - 1):
        k = ci[i]
        if k < 0 or atr5[i] <= 0 or valid[k] != 1 or broken[k] != 0: continue
        key = (atsec[k], ktsec[k])
        if key == last_line or fan[k] < prm.cl_signal_fan: continue
        d = cdir[k]
        v = ap[k] + sl[k] * (tsec[i] - atsec[k]); v1 = ap[k] + sl[k] * (tsec[i - 1] - atsec[k])
        dpt = prm.cl_break_atr * atr5[i]; m = mtr[i]
        if d < 0 and BC[i] < v - dpt and BC[i - 1] >= v1 - dpt and BC[i] < BO[i] \
                and i - last_sell >= prm.cooldown_bars and m == -1:
            risk = BH[max(0, i - prm.cl_sl_bars):i + 1].max() + prm.sl_buffer_atr * atr5[i] - BC[i]
            if prm.min_sl_atr * atr5[i] <= risk <= prm.cl_max_sl_atr * atr5[i]:
                last_sell, last_line = i, key; out.append((i + 1, -1))
        if d > 0 and BC[i] > v + dpt and BC[i - 1] <= v1 + dpt and BC[i] > BO[i] \
                and i - last_buy >= prm.cooldown_bars and m == 1:
            risk = BC[i] - (BL[max(0, i - prm.cl_sl_bars):i + 1].min() - prm.sl_buffer_atr * atr5[i])
            if prm.min_sl_atr * atr5[i] <= risk <= prm.cl_max_sl_atr * atr5[i]:
                last_buy, last_line = i, key; out.append((i + 1, 1))
    return out


# ------------------------------------------------------------------ replay (= LAB155, mode LOCK2_LOCK025)
def init_pos(src, pri, ei, side, atr, cost):
    entry = BO[ei]
    return dict(source=src, pri=pri, entry_i=ei, side=side, atr=atr, entry=entry, stop_r=-1.0, partial=False,
                cost_r=(cost / 10000.0) * entry / atr, end_i=min(ei + MAX_H_BARS - 1, N - 1),
                addon_parent=False, exit_i=None, net_r=None, reason=None, tl_main=0)


def mtm_open(p, i):
    r = p["side"] * (BO[i] - p["entry"]) / p["atr"]
    return (1.5 + 0.5 * r - p["cost_r"]) if p["partial"] else (r - p["cost_r"])


def mtm_close(p, i):
    r = p["side"] * (BC[i] - p["entry"]) / p["atr"]
    return (1.5 + 0.5 * r - p["cost_r"]) if p["partial"] else (r - p["cost_r"])


def finish(p, i, gross, reason):
    p["exit_i"] = i; p["net_r"] = float(gross - p["cost_r"]); p["reason"] = reason
    return p


def eval_bar(p, i, cfg):
    side, entry, atr = p["side"], p["entry"], p["atr"]
    if not p["partial"]:
        sp = entry + side * p["stop_r"] * atr
        tp = entry + side * 3 * atr
        hs = (BL[i] <= sp) if side > 0 else (BH[i] >= sp)
        ht = (BH[i] >= tp) if side > 0 else (BL[i] <= tp)
        if hs and ht: return finish(p, i, p["stop_r"], "BOTH_STOP_FIRST")
        if hs: return finish(p, i, p["stop_r"], "SL")
        if ht:
            p["partial"] = True
            p["stop_r"] = max(p["stop_r"], 2.0)
            if cfg.get("runner_h"):
                p["end_i"] = min(p["entry_i"] + cfg["runner_h"] * 12 - 1, N - 1)
            return None
    else:
        sp = entry + side * p["stop_r"] * atr
        hs = (BL[i] <= sp) if side > 0 else (BH[i] >= sp)
        if hs: return finish(p, i, 1.5 + 0.5 * p["stop_r"], "RUNNER_STOP")
    if i >= p["end_i"]:
        rr = side * (BC[i] - entry) / atr
        return finish(p, i, rr if not p["partial"] else 1.5 + 0.5 * rr, "TIME" if not p["partial"] else "TIME_RUNNER")
    return None


def replay(cost, cfg, tl, extra_sigs=None, veto=None, add_events=None, raw=None, max_pos=2):
    """cfg: dict(trail=bool, runner_h=int|None). extra_sigs: list (ei, side, src).
    veto(set of raw row ids). add_events: array per bar with side (+1/-1/0) for TL add-on."""
    raw = C["raw"][cost] if raw is None else raw
    sigs = {}
    for rid, r in enumerate(raw.itertuples(index=False)):
        if veto is not None and rid in veto: continue
        sigs.setdefault(int(r.entry_i), []).append((PRI.get(r.source, 5), r.source, int(r.side), float(r.atr), rid))
    if extra_sigs:
        for ei, side, src in extra_sigs:
            if 0 <= ei < N and BA[ei] > 0:
                sigs.setdefault(int(ei), []).append((PRI.get(src, 4), src, int(side), float(BA[ei]), -1))
    sig_idx = np.array(sorted(sigs))
    lo = int(raw.entry_i.min()); hi_sig = int(raw.entry_i.max())
    sig_idx = sig_idx[(sig_idx >= lo) & (sig_idx <= hi_sig)]
    active, closed, eq = [], [], []
    realized = 0.0; skipped = 0; addons = 0
    ptr = 0; i = int(sig_idx[0])
    swl, swh, catr, ci = tl["swl"], tl["swh"], tl["catr"], tl["ci"]
    while i < N:
        # trailing update (known at bar open: last closed H1)
        if cfg.get("trail"):
            k = ci[i]
            if k >= 0:
                for p in active:
                    if p["partial"]:
                        if p["side"] > 0 and not np.isnan(swl[k]):
                            cand = (swl[k] - 0.1 * catr[k] - p["entry"]) / p["atr"]
                        elif p["side"] < 0 and not np.isnan(swh[k]):
                            cand = (p["entry"] - (swh[k] + 0.1 * catr[k])) / p["atr"]
                        else:
                            continue
                        if cand > p["stop_r"]: p["stop_r"] = cand
        # entries
        todo = sigs.get(i, []) if (lo <= i <= hi_sig) else []
        if add_events is not None and add_events[i] != 0 and len(active) == 1 and lo <= i <= hi_sig:
            todo = todo + [(PRI["T"] + 1, "TL_ADD", int(add_events[i]), float(BA[i]), -1)]
        for pri, src, side, atr, rid in sorted(todo, key=lambda x: x[0]):
            if src == "TL_ADD" and len(active) != 1: continue
            allow = False; is_add = False
            if len(active) == 0:
                allow = src != "TL_ADD"
            elif len(active) < max_pos:
                allow = all(p0["side"] == side and mtm_open(p0, i) >= 0 for p0 in active); is_add = allow
            if allow:
                if is_add:
                    addons += 1
                    for p0 in active: p0["stop_r"] = max(p0["stop_r"], 0.25)
                q = init_pos(src, pri, i, side, atr, cost); q["addon_parent"] = is_add
                q["tl_main"] = int(tl["mtr"][i]); active.append(q)
            else:
                skipped += 1
        still = []
        for p in active:
            d = eval_bar(p, i, cfg)
            if d is None: still.append(p)
            else: closed.append(d); realized += d["net_r"]
        active = still
        eq.append((i, realized + sum(mtm_close(p, i) for p in active), len(active)))
        # advance
        if active:
            i += 1
        else:
            while ptr < len(sig_idx) and sig_idx[ptr] <= i: ptr += 1
            nxt = int(sig_idx[ptr]) if ptr < len(sig_idx) else N
            if add_events is not None:
                pass  # add-ons require an open position
            i = nxt
            if i > hi_sig: break
    t = pd.DataFrame(closed)
    if len(t):
        t["entry_time"] = BT[t.entry_i.to_numpy(int)]; t["exit_time"] = BT[t.exit_i.to_numpy(int)]
    e = pd.DataFrame(eq, columns=["i", "equity_r", "open_count"]); e["time"] = BT[e.i.to_numpy(int)]
    return t, e, skipped, addons


def stats(t, e):
    x = t.net_r.to_numpy(float); pos = x[x > 0].sum(); neg = -x[x < 0].sum()
    a = t.entry_time.min(); b = t.exit_time.max()
    months = max((b.year - a.year) * 12 + b.month - a.month + 1, 1)
    eq = e.equity_r.to_numpy(float); dd = float(np.max(np.maximum.accumulate(eq) - eq))
    return dict(n=len(t), trades_month=len(t) / months, ev=float(x.mean()), pf=float(pos / neg) if neg > 0 else np.inf,
                total_r=float(x.sum()), r_month=float(x.sum() / months), mtm_dd_r=dd, mtm_dd_pct=dd * RISK,
                r_per_dd=float(x.sum() / dd) if dd > 0 else np.inf, months=months)


def monthly(t):
    m = t.groupby(t.exit_time.dt.tz_convert("UTC").dt.strftime("%Y-%m")).net_r.sum()
    return m


def yearly(t):
    return t.groupby(t.exit_time.dt.year).net_r.sum()
