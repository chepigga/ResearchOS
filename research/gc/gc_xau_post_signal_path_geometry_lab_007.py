#!/usr/bin/env python3
"""GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007

Post-discovery execution/path study on frozen LAB006 GC->FTMO XAU events.
This script does NOT change the GC signal and does NOT claim OOS validation.
See GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007_PREREG.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
LAB006_EVENTS = ROOT / "GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006_EVENTS.csv"
XAU_DIR = ROOT / "_lab007_xau"
OUT_JSON = ROOT / "GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007.json"
OUT_MD = ROOT / "GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007.md"
OUT_CONFIGS = ROOT / "GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007_CONFIGS.csv"
OUT_TRADES = ROOT / "GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007_TRADES.csv"
OUT_FP = ROOT / "GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007_FIRST_PASSAGE.csv"
OUT_PATH = ROOT / "GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007_PATH_DIAGNOSTICS.csv"

HARD_HORIZON_MIN = 30
STALE_MS = 5000
SEED = 20260916
BOOT_N = 5000

GEOMETRIES = {
    "MARKET": (0.0, 0),
    "LIM_025ATR_5M": (0.25, 5),
    "LIM_050ATR_5M": (0.50, 5),
    "LIM_050ATR_10M": (0.50, 10),
    "LIM_075ATR_10M": (0.75, 10),
    "LIM_100ATR_10M": (1.00, 10),
}
STOP_ATR = (1.0, 1.5)
RR = (1.5, 2.0, 3.0)
FP_WINDOWS = (15, 30)


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def read_xau_ticks():
    files = sorted(p for p in XAU_DIR.glob("XAUUSD_raw_ticks_*.csv") if ".meta." not in p.name)
    if not files:
        raise SystemExit(f"No raw XAU files found in {XAU_DIR}")
    frames = []
    stats = []
    for p in files:
        d = pd.read_csv(
            p,
            usecols=lambda c: c in {"time_msc", "bid", "ask", "quote_valid"},
            low_memory=False,
        )
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
        stats.append({
            "file": p.name,
            "rows": int(len(d)),
            "first_time_msc": int(d.time_msc.iloc[0]),
            "last_time_msc": int(d.time_msc.iloc[-1]),
        })
        frames.append(d[["time_msc", "bid", "ask"]])
    if not frames:
        raise SystemExit("No quote-valid XAU ticks")
    x = pd.concat(frames, ignore_index=True)
    x = x.sort_values("time_msc", kind="mergesort").drop_duplicates(["time_msc", "bid", "ask"]).reset_index(drop=True)
    t = x.time_msc.to_numpy(np.int64)
    b = x.bid.to_numpy(float)
    a = x.ask.to_numpy(float)
    if np.any(np.diff(t) < 0):
        raise SystemExit("Tick times non-monotonic after sort")
    return t, b, a, stats


def first_at_or_after(times: np.ndarray, target_ms: int, max_lag_ms: int = STALE_MS):
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


def load_cohorts():
    if not LAB006_EVENTS.exists():
        raise SystemExit(f"Missing {LAB006_EVENTS}")
    e = pd.read_csv(LAB006_EVENTS, low_memory=False)
    e = e[e.rule.eq("BUYER_BREAKOUT_LONG") & e.source_feed.isin(["RITHMIC", "AMP"])].copy()
    e["executable_bool"] = as_bool(e.executable)
    e["signal_time_utc"] = pd.to_datetime(e.signal_time_utc, utc=True)
    for c in ("broker_target_msc", "entry_tick_msc", "entry_ask", "entry_bid", "xau_atr14_m1"):
        e[c] = pd.to_numeric(e[c], errors="coerce")
    r = e[e.source_feed.eq("RITHMIC")].copy()
    a = e[e.source_feed.eq("AMP")].copy()
    common = sorted(set(r.signal_time_utc) & set(a.signal_time_utc))
    p = r[r.signal_time_utc.isin(common)].drop_duplicates("signal_time_utc").copy()
    p = p[p.executable_bool & p.xau_atr14_m1.gt(0) & p.entry_tick_msc.notna() & p.entry_ask.gt(0)].copy()
    s = a[a.executable_bool & a.xau_atr14_m1.gt(0) & a.entry_tick_msc.notna() & a.entry_ask.gt(0)].drop_duplicates("signal_time_utc").copy()
    p["cohort"] = "COMMON_CLOCK"
    s["cohort"] = "AMP_ALL"
    return p.sort_values("signal_time_utc").reset_index(drop=True), s.sort_values("signal_time_utc").reset_index(drop=True), len(common)


def market_index(times: np.ndarray, event) -> int | None:
    target = int(event.entry_tick_msc)
    i = int(np.searchsorted(times, target, side="left"))
    if i >= len(times):
        return None
    # Require exact LAB006 entry tick timestamp; if duplicate timestamp exists, first quote at it is accepted.
    if int(times[i]) != target:
        return None
    return i


def geometry_fill(times, bids, asks, event, geom_name):
    atr = float(event.xau_atr14_m1)
    mi = market_index(times, event)
    if mi is None:
        return {"filled": False, "reason": "MARKET_REFERENCE_NOT_FOUND"}
    market_ask = float(event.entry_ask)
    target0 = int(event.broker_target_msc)
    depth_atr, wait_min = GEOMETRIES[geom_name]
    if geom_name == "MARKET":
        return {
            "filled": True,
            "fill_idx": mi,
            "fill_time_msc": int(times[mi]),
            "fill_price": float(asks[mi]),
            "fill_delay_ms": int(times[mi] - target0),
            "limit_price": np.nan,
            "market_ref_ask": market_ask,
        }
    limit_price = market_ask - depth_atr * atr
    wait_end = target0 + wait_min * 60000
    j_end = int(np.searchsorted(times, wait_end, side="right"))
    if j_end <= mi:
        return {"filled": False, "reason": "NO_WAIT_WINDOW", "limit_price": limit_price, "market_ref_ask": market_ask}
    hits = np.flatnonzero(asks[mi:j_end] <= limit_price + 1e-12)
    if len(hits) == 0:
        return {"filled": False, "reason": "NO_FILL", "limit_price": limit_price, "market_ref_ask": market_ask}
    fi = mi + int(hits[0])
    return {
        "filled": True,
        "fill_idx": fi,
        "fill_time_msc": int(times[fi]),
        "fill_price": float(limit_price),
        "fill_delay_ms": int(times[fi] - target0),
        "limit_price": float(limit_price),
        "market_ref_ask": market_ask,
    }


def path_slice(times, bids, fill_idx: int, hard_end_ms: int):
    last = last_before_or_at(times, hard_end_ms)
    if last is None or last < fill_idx:
        return np.array([], dtype=float), None
    return bids[fill_idx:last + 1], last


def geometry_record(times, bids, asks, event, geom_name):
    atr = float(event.xau_atr14_m1)
    hard_end = int(event.broker_target_msc) + HARD_HORIZON_MIN * 60000
    g = geometry_fill(times, bids, asks, event, geom_name)
    rec = {
        "cohort": event.cohort,
        "signal_time_utc": event.signal_time_utc.isoformat(),
        "geometry": geom_name,
        "atr": atr,
        "broker_target_msc": int(event.broker_target_msc),
        "filled": bool(g.get("filled", False)),
        "reason": g.get("reason", ""),
        "fill_time_msc": g.get("fill_time_msc", np.nan),
        "fill_price": g.get("fill_price", np.nan),
        "fill_delay_ms": g.get("fill_delay_ms", np.nan),
        "market_ref_ask": g.get("market_ref_ask", float(event.entry_ask)),
        "limit_price": g.get("limit_price", np.nan),
        "mfe30_atr": np.nan,
        "mae30_atr": np.nan,
        "timeout_bid": np.nan,
        "timeout_lag_ms": np.nan,
        "timeout_available": False,
    }
    if not rec["filled"]:
        return rec, None
    fi = int(g["fill_idx"])
    path, _ = path_slice(times, bids, fi, hard_end)
    if len(path):
        fp = float(g["fill_price"])
        rec["mfe30_atr"] = float((np.nanmax(path) - fp) / atr)
        rec["mae30_atr"] = float((np.nanmin(path) - fp) / atr)
    ti, lag = first_at_or_after(times, hard_end, STALE_MS)
    if ti is not None and ti >= fi:
        rec["timeout_bid"] = float(bids[ti])
        rec["timeout_lag_ms"] = int(lag)
        rec["timeout_available"] = True
    return rec, fi


def bracket_outcome(times, bids, geom_rec, fill_idx, stop_atr, rr):
    out = {
        "stop_atr": float(stop_atr),
        "rr": float(rr),
        "status": "NO_FILL",
        "r": 0.0,
        "filled_trade_r": np.nan,
        "exit_time_msc": np.nan,
        "exit_price": np.nan,
    }
    if not geom_rec["filled"] or fill_idx is None:
        return out
    atr = float(geom_rec["atr"])
    entry = float(geom_rec["fill_price"])
    stop = entry - stop_atr * atr
    target = entry + rr * stop_atr * atr
    hard_end = int(geom_rec["broker_target_msc"]) + HARD_HORIZON_MIN * 60000
    last = last_before_or_at(times, hard_end)
    if last is None or last < fill_idx:
        out.update(status="DATA_GAP", r=np.nan)
        return out
    p = bids[fill_idx:last + 1]
    s_hit = np.flatnonzero(p <= stop + 1e-12)
    t_hit = np.flatnonzero(p >= target - 1e-12)
    si = int(s_hit[0]) if len(s_hit) else None
    ti = int(t_hit[0]) if len(t_hit) else None
    if si is not None and (ti is None or si <= ti):
        k = fill_idx + si
        out.update(status="SL", r=-1.0, filled_trade_r=-1.0, exit_time_msc=int(times[k]), exit_price=float(stop))
        return out
    if ti is not None:
        k = fill_idx + ti
        out.update(status="TP", r=float(rr), filled_trade_r=float(rr), exit_time_msc=int(times[k]), exit_price=float(target))
        return out
    if not geom_rec["timeout_available"]:
        out.update(status="DATA_GAP", r=np.nan)
        return out
    timeout_bid = float(geom_rec["timeout_bid"])
    rval = (timeout_bid - entry) / (stop_atr * atr)
    out.update(
        status="TIMEOUT",
        r=float(rval),
        filled_trade_r=float(rval),
        exit_time_msc=int(geom_rec["broker_target_msc"] + HARD_HORIZON_MIN * 60000 + int(geom_rec["timeout_lag_ms"])),
        exit_price=timeout_bid,
    )
    return out


def first_passage(times, bids, event, stop_atr, rr, window_min):
    mi = market_index(times, event)
    if mi is None:
        return "DATA_GAP"
    atr = float(event.xau_atr14_m1)
    entry = float(event.entry_ask)
    stop = entry - stop_atr * atr
    target = entry + rr * stop_atr * atr
    end = int(event.broker_target_msc) + window_min * 60000
    last = last_before_or_at(times, end)
    if last is None or last < mi:
        return "DATA_GAP"
    p = bids[mi:last + 1]
    sh = np.flatnonzero(p <= stop + 1e-12)
    th = np.flatnonzero(p >= target - 1e-12)
    si = int(sh[0]) if len(sh) else None
    ti = int(th[0]) if len(th) else None
    if si is not None and (ti is None or si <= ti):
        return "SL_FIRST"
    if ti is not None:
        return "TP_FIRST"
    return "NEITHER"


def retracement_record(times, asks, event):
    mi = market_index(times, event)
    if mi is None:
        return None
    atr = float(event.xau_atr14_m1)
    ref = float(event.entry_ask)
    row = {"cohort": event.cohort, "signal_time_utc": event.signal_time_utc.isoformat()}
    for w in (5, 10):
        end = int(event.broker_target_msc) + w * 60000
        last = last_before_or_at(times, end)
        if last is None or last < mi:
            row[f"min_ask_retrace_{w}m_atr"] = np.nan
        else:
            row[f"min_ask_retrace_{w}m_atr"] = float((np.nanmin(asks[mi:last + 1]) - ref) / atr)
    return row


def max_dd(v):
    a = np.asarray(v, float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return None
    eq = np.cumsum(a)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = peak - eq
    return float(np.max(dd)) if len(dd) else 0.0


def day_cluster_ci(df, col="r", n=BOOT_N):
    z = df.dropna(subset=[col]).copy()
    if z.empty:
        return [None, None]
    z["day"] = pd.to_datetime(z.signal_time_utc, utc=True).dt.date
    g = z.groupby("day")[col].agg(["sum", "count"])
    if len(g) < 2:
        return [None, None]
    sums = g["sum"].to_numpy(float)
    counts = g["count"].to_numpy(float)
    rng = np.random.default_rng(SEED)
    k = len(g)
    vals = np.empty(n)
    for j in range(n):
        picks = rng.integers(0, k, k)
        vals[j] = sums[picks].sum() / counts[picks].sum()
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def config_summary(df, total_signals):
    known = df[df.status.ne("DATA_GAP")].copy()
    filled = known[known.status.ne("NO_FILL")].copy()
    per_signal = known.r.to_numpy(float)
    per_trade = filled.filled_trade_r.dropna().to_numpy(float)
    pos = per_trade[per_trade > 0].sum() if len(per_trade) else 0.0
    neg = -per_trade[per_trade < 0].sum() if len(per_trade) else 0.0
    return {
        "signals": int(total_signals),
        "known_signals": int(len(known)),
        "filled": int(len(filled)),
        "fill_rate_pct": float(len(filled) / total_signals * 100) if total_signals else None,
        "tp": int((filled.status == "TP").sum()),
        "sl": int((filled.status == "SL").sum()),
        "timeout": int((filled.status == "TIMEOUT").sum()),
        "data_gap": int((df.status == "DATA_GAP").sum()),
        "ev_r_per_filled_trade": float(np.mean(per_trade)) if len(per_trade) else None,
        "ev_r_per_signal": float(np.mean(per_signal)) if len(per_signal) else None,
        "wr_filled_pct": float((per_trade > 0).mean() * 100) if len(per_trade) else None,
        "pf": float(pos / neg) if neg > 0 else (float("inf") if pos > 0 else None),
        "max_dd_r_per_signal": max_dd(per_signal),
        "ci95_day_ev_r_per_signal": day_cluster_ci(known, "r"),
    }


def qstats(s):
    v = pd.to_numeric(s, errors="coerce").dropna().to_numpy(float)
    if not len(v):
        return {"n": 0}
    return {
        "n": int(len(v)),
        "mean": float(np.mean(v)),
        "q10": float(np.quantile(v, .10)),
        "q25": float(np.quantile(v, .25)),
        "median": float(np.median(v)),
        "q75": float(np.quantile(v, .75)),
        "q90": float(np.quantile(v, .90)),
    }


def main():
    times, bids, asks, file_stats = read_xau_ticks()
    primary, amp_all, common_raw_n = load_cohorts()
    cohorts = {"COMMON_CLOCK": primary, "AMP_ALL": amp_all}

    geometry_rows = []
    trade_rows = []
    fp_rows = []
    retr_rows = []

    for cname, cohort in cohorts.items():
        for ev in cohort.itertuples(index=False):
            rr0 = retracement_record(times, asks, ev)
            if rr0 is not None:
                retr_rows.append(rr0)
            # Market first-passage diagnostics
            for w in FP_WINDOWS:
                for s in STOP_ATR:
                    for rr in RR:
                        fp_rows.append({
                            "cohort": cname,
                            "signal_time_utc": ev.signal_time_utc.isoformat(),
                            "window_min": w,
                            "stop_atr": s,
                            "rr": rr,
                            "outcome": first_passage(times, bids, ev, s, rr, w),
                        })
            # Entry geometry and bracket map
            for geom in GEOMETRIES:
                grec, fi = geometry_record(times, bids, asks, ev, geom)
                geometry_rows.append(grec)
                for s in STOP_ATR:
                    for rr in RR:
                        bout = bracket_outcome(times, bids, grec, fi, s, rr)
                        trade_rows.append({
                            "cohort": cname,
                            "signal_time_utc": ev.signal_time_utc.isoformat(),
                            "geometry": geom,
                            "fill_delay_ms": grec.get("fill_delay_ms", np.nan),
                            "mfe30_atr": grec.get("mfe30_atr", np.nan),
                            "mae30_atr": grec.get("mae30_atr", np.nan),
                            **bout,
                        })

    gdf = pd.DataFrame(geometry_rows)
    tdf = pd.DataFrame(trade_rows)
    fdf = pd.DataFrame(fp_rows)
    rdf = pd.DataFrame(retr_rows)
    tdf.to_csv(OUT_TRADES, index=False)
    fdf.to_csv(OUT_FP, index=False)
    rdf.to_csv(OUT_PATH, index=False)

    config_rows = []
    summaries = {}
    for cname, cohort in cohorts.items():
        summaries[cname] = {"n_signals": int(len(cohort)), "entries": {}, "first_passage": {}, "retrace": {}}
        cg = gdf[gdf.cohort.eq(cname)].copy()
        ct = tdf[tdf.cohort.eq(cname)].copy()
        for geom in GEOMETRIES:
            gg = cg[cg.geometry.eq(geom)].copy()
            fill = gg[gg.filled == True].copy()
            summaries[cname]["entries"][geom] = {
                "filled": int(len(fill)),
                "fill_rate_pct": float(len(fill) / len(cohort) * 100) if len(cohort) else None,
                "median_fill_delay_ms": float(pd.to_numeric(fill.fill_delay_ms, errors="coerce").median()) if len(fill) else None,
                "mfe30_atr": qstats(fill.mfe30_atr),
                "mae30_atr": qstats(fill.mae30_atr),
            }
            for s in STOP_ATR:
                for rr in RR:
                    z = ct[(ct.geometry.eq(geom)) & (ct.stop_atr.eq(s)) & (ct.rr.eq(rr))].copy()
                    sm = config_summary(z, len(cohort))
                    row = {"cohort": cname, "geometry": geom, "stop_atr": s, "rr": rr, **sm}
                    config_rows.append(row)
        cr = rdf[rdf.cohort.eq(cname)]
        for w in (5, 10):
            summaries[cname]["retrace"][f"{w}m"] = qstats(cr[f"min_ask_retrace_{w}m_atr"])
        cf = fdf[fdf.cohort.eq(cname)]
        for w in FP_WINDOWS:
            summaries[cname]["first_passage"][str(w)] = {}
            for s in STOP_ATR:
                for rr in RR:
                    z = cf[(cf.window_min.eq(w)) & (cf.stop_atr.eq(s)) & (cf.rr.eq(rr))]
                    counts = z.outcome.value_counts().to_dict()
                    n = int(len(z))
                    summaries[cname]["first_passage"][str(w)][f"S{s:.1f}_RR{rr:.1f}"] = {
                        "n": n,
                        "tp_first": int(counts.get("TP_FIRST", 0)),
                        "sl_first": int(counts.get("SL_FIRST", 0)),
                        "neither": int(counts.get("NEITHER", 0)),
                        "data_gap": int(counts.get("DATA_GAP", 0)),
                        "tp_first_pct": float(counts.get("TP_FIRST", 0) / n * 100) if n else None,
                        "sl_first_pct": float(counts.get("SL_FIRST", 0) / n * 100) if n else None,
                    }

    cfg = pd.DataFrame(config_rows)
    cfg.to_csv(OUT_CONFIGS, index=False)

    # Observed leaders are descriptive only; never call them validated winners.
    leaders = {}
    for cname in cohorts:
        z = cfg[cfg.cohort.eq(cname)].copy()
        z = z[np.isfinite(pd.to_numeric(z.ev_r_per_signal, errors="coerce"))]
        if len(z):
            r = z.sort_values("ev_r_per_signal", ascending=False).iloc[0]
            leaders[cname] = {
                "geometry": r.geometry,
                "stop_atr": float(r.stop_atr),
                "rr": float(r.rr),
                "fill_rate_pct": float(r.fill_rate_pct),
                "ev_r_per_signal": float(r.ev_r_per_signal),
                "ev_r_per_filled_trade": float(r.ev_r_per_filled_trade),
                "pf": float(r.pf) if np.isfinite(r.pf) else "inf",
                "max_dd_r_per_signal": float(r.max_dd_r_per_signal),
                "ci95_day_ev_r_per_signal": r.ci95_day_ev_r_per_signal,
            }

    result = {
        "lab": "GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007",
        "status": "POST_DISCOVERY_GEOMETRY_MAP_COMPLETED_NOT_OOS",
        "governance": {
            "gc_signal_changed": False,
            "same_historical_window_as_lab006": True,
            "production_rule_selected": False,
            "spread_included": True,
            "commission_included": False,
            "slippage_included": False,
            "hard_horizon_min_from_original_signal": HARD_HORIZON_MIN,
        },
        "source": {
            "xau_raw_files": len(file_stats),
            "quote_valid_ticks": int(len(times)),
            "first_tick_msc": int(times[0]),
            "last_tick_msc": int(times[-1]),
            "lab006_common_raw_signal_times": int(common_raw_n),
        },
        "summaries": summaries,
        "observed_leaders_not_validated": leaders,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    def f(x, d=3):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "NA"
        return f"{x:+.{d}f}"

    lines = [
        "# GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007",
        "",
        "**Status: POST_DISCOVERY_GEOMETRY_MAP_COMPLETED_NOT_OOS**",
        "",
        f"Primary exact common-clock executable cohort: **N={len(primary)}** (raw common signal times before executable/ATR gate: {common_raw_n}). Secondary AMP cohort: **N={len(amp_all)}**.",
        "",
        "No GC threshold/session/regime parameter was changed. All entries use FTMO Ask; exits/path use Bid. Quoted spread is included. Commission/slippage are not included.",
        "",
        "## Retest depth from market-reference Ask",
        "",
        "| Cohort | Window | Mean ATR | Q25 | Median | Q75 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cname in ("COMMON_CLOCK", "AMP_ALL"):
        for w in (5, 10):
            q = summaries[cname]["retrace"][f"{w}m"]
            lines.append(f"| {cname} | {w}m | {f(q.get('mean'))} | {f(q.get('q25'))} | {f(q.get('median'))} | {f(q.get('q75'))} |")

    lines += [
        "",
        "## Entry geometry",
        "",
        "| Cohort | Geometry | Fill | Fill rate | Median delay | Median MFE30 | Median MAE30 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for cname in ("COMMON_CLOCK", "AMP_ALL"):
        for geom in GEOMETRIES:
            x = summaries[cname]["entries"][geom]
            delay = x["median_fill_delay_ms"]
            delay_s = "NA" if delay is None else f"{delay/1000:.1f}s"
            lines.append(f"| {cname} | {geom} | {x['filled']} | {x['fill_rate_pct']:.1f}% | {delay_s} | {f(x['mfe30_atr'].get('median'))} ATR | {f(x['mae30_atr'].get('median'))} ATR |")

    lines += [
        "",
        "## First passage from MARKET entry",
        "",
        "Primary/common-clock only. Percentages are path order, not optimized trade results.",
        "",
        "| Window | Stop | RR | TP first | SL first | Neither |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for w in FP_WINDOWS:
        for s in STOP_ATR:
            for rr in RR:
                x = summaries["COMMON_CLOCK"]["first_passage"][str(w)][f"S{s:.1f}_RR{rr:.1f}"]
                lines.append(f"| {w}m | {s:.1f} ATR | {rr:.1f} | {x['tp_first_pct']:.1f}% | {x['sl_first_pct']:.1f}% | {x['neither']} |")

    lines += [
        "",
        "## Observed leaders — descriptive only, NOT validated",
        "",
        "| Cohort | Geometry | Stop | RR | Fill | EV R/signal | EV R/filled | PF | MaxDD R | Day CI95 R/signal |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cname in ("COMMON_CLOCK", "AMP_ALL"):
        x = leaders.get(cname)
        if not x:
            continue
        ci = x["ci95_day_ev_r_per_signal"]
        cis = "NA" if not isinstance(ci, (list, tuple)) or ci[0] is None else f"[{ci[0]:+.3f},{ci[1]:+.3f}]"
        pf = x["pf"] if isinstance(x["pf"], str) else f"{x['pf']:.2f}"
        lines.append(f"| {cname} | {x['geometry']} | {x['stop_atr']:.1f} ATR | {x['rr']:.1f} | {x['fill_rate_pct']:.1f}% | {f(x['ev_r_per_signal'])} | {f(x['ev_r_per_filled_trade'])} | {pf} | {x['max_dd_r_per_signal']:.2f} | {cis} |")

    lines += [
        "",
        "Full configuration grid is in `GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007_CONFIGS.csv`. A favorable observed configuration is only a candidate to freeze for a later untouched forward/OOS test.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT_MD.read_text())


if __name__ == "__main__":
    main()
