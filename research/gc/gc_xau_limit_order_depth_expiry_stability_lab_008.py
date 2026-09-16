#!/usr/bin/env python3
"""GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008

Post-discovery limit-entry stability map on the frozen LAB006 GC->FTMO XAU cohort.
The GC signal is unchanged. Only limit depth and expiry vary. Exit geometry is
frozen to SL=1.5 ATR, TP=3R, hard timeout=30m from original signal timestamp.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
LAB006_EVENTS = ROOT / "GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006_EVENTS.csv"
XAU_DIR = ROOT / "_lab008_xau"
OUT_JSON = ROOT / "GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008.json"
OUT_MD = ROOT / "GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008.md"
OUT_CONFIGS = ROOT / "GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008_CONFIGS.csv"
OUT_TRADES = ROOT / "GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008_TRADES.csv"

DEPTHS = (0.50, 0.75, 1.00, 1.25, 1.50)
EXPIRIES = (3, 5, 10, 15)
STOP_ATR = 1.5
RR = 3.0
HARD_HORIZON_MIN = 30
STALE_MS = 5000
SPLIT = pd.Timestamp("2026-09-01T00:00:00Z")
SEED = 20260916
BOOT_N = 5000


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def read_xau_ticks():
    files = sorted(p for p in XAU_DIR.glob("XAUUSD_raw_ticks_*.csv") if ".meta." not in p.name)
    if not files:
        raise SystemExit(f"No raw XAU files in {XAU_DIR}")
    frames = []
    stats = []
    for p in files:
        d = pd.read_csv(p, usecols=lambda c: c in {"time_msc", "bid", "ask", "quote_valid"}, low_memory=False)
        if d.empty:
            continue
        for c in ("time_msc", "bid", "ask"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        if "quote_valid" in d.columns:
            q = pd.to_numeric(d.quote_valid, errors="coerce").fillna(0).eq(1)
        else:
            q = d.bid.gt(0) & d.ask.gt(0)
        d = d[q & d.time_msc.notna() & d.bid.gt(0) & d.ask.gt(0) & d.ask.ge(d.bid)].copy()
        if d.empty:
            continue
        stats.append({"file": p.name, "rows": int(len(d)), "first": int(d.time_msc.iloc[0]), "last": int(d.time_msc.iloc[-1])})
        frames.append(d[["time_msc", "bid", "ask"]])
    x = pd.concat(frames, ignore_index=True)
    x = x.sort_values("time_msc", kind="mergesort").drop_duplicates(["time_msc", "bid", "ask"]).reset_index(drop=True)
    t = x.time_msc.to_numpy(np.int64)
    b = x.bid.to_numpy(float)
    a = x.ask.to_numpy(float)
    if np.any(np.diff(t) < 0):
        raise SystemExit("Non-monotonic ticks")
    return t, b, a, stats


def load_cohorts():
    e = pd.read_csv(LAB006_EVENTS, low_memory=False)
    e = e[e.rule.eq("BUYER_BREAKOUT_LONG") & e.source_feed.isin(["RITHMIC", "AMP"])].copy()
    e["executable_bool"] = as_bool(e.executable)
    e["signal_time_utc"] = pd.to_datetime(e.signal_time_utc, utc=True)
    for c in ("broker_target_msc", "entry_tick_msc", "entry_ask", "entry_bid", "xau_atr14_m1"):
        e[c] = pd.to_numeric(e[c], errors="coerce")
    r = e[e.source_feed.eq("RITHMIC")].copy()
    a = e[e.source_feed.eq("AMP")].copy()
    common_times = sorted(set(r.signal_time_utc) & set(a.signal_time_utc))
    common = r[r.signal_time_utc.isin(common_times)].drop_duplicates("signal_time_utc").copy()
    common = common[common.executable_bool & common.xau_atr14_m1.gt(0) & common.entry_tick_msc.notna() & common.entry_ask.gt(0)].copy()
    amp = a[a.executable_bool & a.xau_atr14_m1.gt(0) & a.entry_tick_msc.notna() & a.entry_ask.gt(0)].drop_duplicates("signal_time_utc").copy()
    common["cohort"] = "COMMON_CLOCK"
    amp["cohort"] = "AMP_ALL"
    return common.sort_values("signal_time_utc").reset_index(drop=True), amp.sort_values("signal_time_utc").reset_index(drop=True), len(common_times)


def exact_market_index(times: np.ndarray, ts: int):
    i = int(np.searchsorted(times, ts, side="left"))
    if i >= len(times) or int(times[i]) != int(ts):
        return None
    return i


def first_at_or_after(times: np.ndarray, target_ms: int, max_lag_ms=STALE_MS):
    i = int(np.searchsorted(times, target_ms, side="left"))
    if i >= len(times):
        return None, None
    lag = int(times[i] - target_ms)
    if lag < 0 or lag > max_lag_ms:
        return None, lag
    return i, lag


def last_before_or_at(times: np.ndarray, target_ms: int):
    i = int(np.searchsorted(times, target_ms, side="right")) - 1
    return i if i >= 0 else None


def simulate_one(times, bids, asks, event, depth_atr: float, expiry_min: int):
    signal0 = int(event.broker_target_msc)
    market_ts = int(event.entry_tick_msc)
    mi = exact_market_index(times, market_ts)
    base = {
        "cohort": event.cohort,
        "signal_time_utc": event.signal_time_utc.isoformat(),
        "depth_atr": float(depth_atr),
        "expiry_min": int(expiry_min),
        "filled": False,
        "fill_time_msc": np.nan,
        "fill_delay_sec": np.nan,
        "fill_price": np.nan,
        "status": "NO_FILL",
        "r": 0.0,
        "exit_time_msc": np.nan,
        "exit_price": np.nan,
    }
    if mi is None:
        base["status"] = "MARKET_REFERENCE_NOT_FOUND"
        base["r"] = np.nan
        return base
    atr = float(event.xau_atr14_m1)
    market_ref = float(event.entry_ask)
    limit_price = market_ref - depth_atr * atr
    expiry_ms = signal0 + expiry_min * 60000
    j_end = int(np.searchsorted(times, expiry_ms, side="right"))
    if j_end <= mi:
        return base
    hits = np.flatnonzero(asks[mi:j_end] <= limit_price + 1e-12)
    if len(hits) == 0:
        return base
    fi = mi + int(hits[0])
    fill_ts = int(times[fi])
    base.update(filled=True, fill_time_msc=fill_ts, fill_delay_sec=(fill_ts - signal0) / 1000.0, fill_price=float(limit_price))

    stop = limit_price - STOP_ATR * atr
    target = limit_price + RR * STOP_ATR * atr
    hard_end = signal0 + HARD_HORIZON_MIN * 60000
    last = last_before_or_at(times, hard_end)
    if last is None or last < fi:
        base.update(status="DATA_GAP", r=np.nan)
        return base
    path = bids[fi:last + 1]
    s = np.flatnonzero(path <= stop + 1e-12)
    t = np.flatnonzero(path >= target - 1e-12)
    si = int(s[0]) if len(s) else None
    ti = int(t[0]) if len(t) else None
    if si is not None and (ti is None or si <= ti):
        k = fi + si
        base.update(status="SL", r=-1.0, exit_time_msc=int(times[k]), exit_price=float(stop))
        return base
    if ti is not None:
        k = fi + ti
        base.update(status="TP", r=RR, exit_time_msc=int(times[k]), exit_price=float(target))
        return base
    xi, lag = first_at_or_after(times, hard_end, STALE_MS)
    if xi is None or xi < fi:
        base.update(status="DATA_GAP", r=np.nan)
        return base
    exit_bid = float(bids[xi])
    rval = (exit_bid - limit_price) / (STOP_ATR * atr)
    base.update(status="TIMEOUT", r=float(rval), exit_time_msc=int(times[xi]), exit_price=exit_bid)
    return base


def pf(v: np.ndarray):
    pos = float(v[v > 0].sum())
    neg = float(-v[v < 0].sum())
    if neg == 0:
        return float("inf") if pos > 0 else np.nan
    return pos / neg


def max_dd(v: np.ndarray):
    eq = np.cumsum(np.nan_to_num(v, nan=0.0))
    if len(eq) == 0:
        return np.nan
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return float(dd.max()) if len(dd) else 0.0


def cluster_ci(df: pd.DataFrame, n=BOOT_N):
    z = df.dropna(subset=["r"]).copy()
    if z.empty:
        return [None, None]
    z["day"] = pd.to_datetime(z.signal_time_utc, utc=True).dt.date
    groups = [g.r.to_numpy(float) for _, g in z.groupby("day")]
    if len(groups) < 2:
        return [None, None]
    rng = np.random.default_rng(SEED)
    out = np.empty(n)
    k = len(groups)
    for j in range(n):
        picks = rng.integers(0, k, k)
        out[j] = np.concatenate([groups[i] for i in picks]).mean()
    return [float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))]


def summarize(df: pd.DataFrame):
    z = df.dropna(subset=["r"]).copy()
    vals = z.r.to_numpy(float)
    filled = z[z.filled].copy()
    fv = filled.r.to_numpy(float)
    return {
        "signals": int(len(z)),
        "filled": int(filled.shape[0]),
        "fill_rate_pct": float(filled.shape[0] / len(z) * 100.0) if len(z) else None,
        "tp": int((filled.status == "TP").sum()),
        "sl": int((filled.status == "SL").sum()),
        "timeout": int((filled.status == "TIMEOUT").sum()),
        "ev_r_per_signal": float(vals.mean()) if len(vals) else None,
        "ev_r_per_filled": float(fv.mean()) if len(fv) else None,
        "wr_filled_pct": float((fv > 0).mean() * 100.0) if len(fv) else None,
        "pf": float(pf(vals)) if len(vals) else None,
        "max_dd_r": max_dd(vals),
        "median_fill_delay_sec": float(filled.fill_delay_sec.median()) if len(filled) else None,
        "day_ci95_r_per_signal": cluster_ci(z),
    }


def config_key(depth, expiry):
    return f"D{depth:.2f}_E{expiry}M"


def neighbor_keys(depth, expiry):
    di = DEPTHS.index(depth)
    ei = EXPIRIES.index(expiry)
    out = []
    for dj, ej in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        ni, nj = di + dj, ei + ej
        if 0 <= ni < len(DEPTHS) and 0 <= nj < len(EXPIRIES):
            out.append(config_key(DEPTHS[ni], EXPIRIES[nj]))
    return out


def main():
    times, bids, asks, stats = read_xau_ticks()
    primary, secondary, raw_common = load_cohorts()
    all_rows = []
    for cohort in (primary, secondary):
        for ev in cohort.itertuples(index=False):
            for depth in DEPTHS:
                for expiry in EXPIRIES:
                    all_rows.append(simulate_one(times, bids, asks, ev, depth, expiry))
    trades = pd.DataFrame(all_rows)
    trades.to_csv(OUT_TRADES, index=False)

    rows = []
    detail = {}
    for cohort_name in ("COMMON_CLOCK", "AMP_ALL"):
        detail[cohort_name] = {}
        cdf = trades[trades.cohort == cohort_name].copy()
        for depth in DEPTHS:
            for expiry in EXPIRIES:
                k = config_key(depth, expiry)
                d = cdf[(cdf.depth_atr == depth) & (cdf.expiry_min == expiry)].copy()
                full = summarize(d)
                early = summarize(d[pd.to_datetime(d.signal_time_utc, utc=True) < SPLIT])
                late = summarize(d[pd.to_datetime(d.signal_time_utc, utc=True) >= SPLIT])
                detail[cohort_name][k] = {"depth_atr": depth, "expiry_min": expiry, "full": full, "early": early, "late": late}
                rows.append({
                    "cohort": cohort_name,
                    "key": k,
                    "depth_atr": depth,
                    "expiry_min": expiry,
                    **{f"full_{a}": b for a, b in full.items() if a != "day_ci95_r_per_signal"},
                    "full_ci_lo": full["day_ci95_r_per_signal"][0],
                    "full_ci_hi": full["day_ci95_r_per_signal"][1],
                    "early_ev_r_per_signal": early["ev_r_per_signal"],
                    "early_pf": early["pf"],
                    "early_fill_rate_pct": early["fill_rate_pct"],
                    "late_ev_r_per_signal": late["ev_r_per_signal"],
                    "late_pf": late["pf"],
                    "late_fill_rate_pct": late["fill_rate_pct"],
                })
    cfg = pd.DataFrame(rows)

    # Stable-candidate gates on primary cohort only, with AMP cross-feed confirmation.
    pmap = detail["COMMON_CLOCK"]
    amap = detail["AMP_ALL"]
    candidates = []
    for depth in DEPTHS:
        for expiry in EXPIRIES:
            k = config_key(depth, expiry)
            p = pmap[k]
            a = amap[k]
            neigh = neighbor_keys(depth, expiry)
            positive_neighbors = sum((pmap[n]["full"]["ev_r_per_signal"] or -999) > 0 for n in neigh)
            gates = {
                "common_full_pos": (p["full"]["ev_r_per_signal"] or -999) > 0,
                "amp_full_pos": (a["full"]["ev_r_per_signal"] or -999) > 0,
                "common_early_pos": (p["early"]["ev_r_per_signal"] or -999) > 0,
                "common_late_pos": (p["late"]["ev_r_per_signal"] or -999) > 0,
                "common_fill_ge40": (p["full"]["fill_rate_pct"] or 0) >= 40.0,
                "common_pf_gt1": (p["full"]["pf"] or 0) > 1.0,
                "positive_adjacent_neighbor": positive_neighbors >= 1,
            }
            if all(gates.values()):
                candidates.append({
                    "key": k,
                    "depth_atr": depth,
                    "expiry_min": expiry,
                    "common_ev": p["full"]["ev_r_per_signal"],
                    "amp_ev": a["full"]["ev_r_per_signal"],
                    "common_pf": p["full"]["pf"],
                    "common_fill": p["full"]["fill_rate_pct"],
                    "common_early_ev": p["early"]["ev_r_per_signal"],
                    "common_late_ev": p["late"]["ev_r_per_signal"],
                    "positive_neighbors": positive_neighbors,
                    "gates": gates,
                })
    candidates.sort(key=lambda x: (x["common_ev"], x["amp_ev"]), reverse=True)
    selected = candidates[0] if candidates else None

    # Add stability columns to CSV.
    stable_keys = {c["key"] for c in candidates}
    cfg["stable_gate_pass"] = cfg.apply(lambda r: bool(r.cohort == "COMMON_CLOCK" and r.key in stable_keys), axis=1)
    cfg.to_csv(OUT_CONFIGS, index=False)

    result = {
        "lab": "GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008",
        "status": "POST_DISCOVERY_LIMIT_STABILITY_MAP_NOT_OOS",
        "frozen_exit": {"stop_atr": STOP_ATR, "rr": RR, "hard_horizon_min_from_signal": HARD_HORIZON_MIN},
        "grid": {"depth_atr": list(DEPTHS), "expiry_min": list(EXPIRIES), "n_geometries": len(DEPTHS) * len(EXPIRIES)},
        "cohorts": {"raw_common_signal_times": raw_common, "common_executable": int(len(primary)), "amp_executable": int(len(secondary))},
        "source": {"raw_xau_files": len(stats), "quote_valid_ticks": int(len(times))},
        "stable_candidates": candidates,
        "selected_descriptive_candidate": selected,
        "detail": detail,
        "governance": {"gc_signal_changed": False, "exit_swept": False, "limit_grid_bounded_and_preregistered": True, "independent_oos": False},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        "# GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008",
        "",
        "**Status: POST_DISCOVERY_LIMIT_STABILITY_MAP_NOT_OOS**",
        "",
        f"Frozen exit for every test: **SL {STOP_ATR:.1f} ATR / TP {RR:.1f}R / hard timeout {HARD_HORIZON_MIN}m from original signal**.",
        "",
        f"Primary common-clock executable cohort: **N={len(primary)}**. AMP-native secondary cohort: **N={len(secondary)}**.",
        "",
        "Only limit depth and expiry were varied. Unfilled limits count as 0R in EV per signal.",
        "",
        "## Primary COMMON_CLOCK grid",
        "",
        "| Depth | Expiry | Fill | EV R/signal | EV R/fill | PF | MaxDD R | EARLY EV | LATE EV | CI95 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for depth in DEPTHS:
        for expiry in EXPIRIES:
            d = pmap[config_key(depth, expiry)]
            f, e, l = d["full"], d["early"], d["late"]
            ci = f["day_ci95_r_per_signal"]
            lines.append(
                f"| {depth:.2f} ATR | {expiry}m | {f['fill_rate_pct']:.1f}% | {f['ev_r_per_signal']:+.3f} | {f['ev_r_per_filled']:+.3f} | {f['pf']:.2f} | {f['max_dd_r']:.2f} | {e['ev_r_per_signal']:+.3f} | {l['ev_r_per_signal']:+.3f} | [{ci[0]:+.3f},{ci[1]:+.3f}] |"
            )
    lines += ["", "## Stable-gate candidates", ""]
    if candidates:
        lines += [
            "| Geometry | COMMON EV | AMP EV | PF | Fill | EARLY | LATE | Positive neighbors |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for c in candidates:
            lines.append(
                f"| {c['key']} | {c['common_ev']:+.3f} | {c['amp_ev']:+.3f} | {c['common_pf']:.2f} | {c['common_fill']:.1f}% | {c['common_early_ev']:+.3f} | {c['common_late_ev']:+.3f} | {c['positive_neighbors']} |"
            )
    else:
        lines.append("No geometry passed all descriptive stability gates.")
    lines += ["", "## Descriptive candidate", ""]
    if selected:
        lines.append(
            f"Observed stable-surface leader: **{selected['key']}** — depth {selected['depth_atr']:.2f} ATR, expiry {selected['expiry_min']}m, COMMON EV {selected['common_ev']:+.3f}R/signal, AMP EV {selected['amp_ev']:+.3f}R/signal."
        )
    else:
        lines.append("No candidate selected. Do not promote a blind-limit execution rule from this LAB.")
    lines += [
        "",
        "## Governance",
        "",
        "This is not independent OOS. LAB007 already exposed part of this historical execution surface. The purpose of LAB008 is to determine whether a broad, mechanically stable limit-entry plateau exists rather than a single lucky parameter point. Any candidate must be frozen before untouched forward/OOS evaluation.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "stable_candidates": len(candidates), "selected": selected}, indent=2, default=str))


if __name__ == "__main__":
    main()
