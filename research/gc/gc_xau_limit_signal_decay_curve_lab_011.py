#!/usr/bin/env python3
"""GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011

Post-discovery signal-age study for the frozen GC BUYER_BREAKOUT_LONG_001 ->
FTMO XAUUSD limit candidate. See preregistration for governance.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
LAB006_EVENTS = ROOT / "GC_BUYER_BREAKOUT_LONG_TO_FTMO_XAU_TRANSFER_LAB_006_EVENTS.csv"
XAU_DIR = ROOT / "_lab011_xau"
OUT_JSON = ROOT / "GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011.json"
OUT_MD = ROOT / "GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011.md"
OUT_EXPIRY = ROOT / "GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011_EXPIRY.csv"
OUT_BUCKETS = ROOT / "GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011_DELAY_BUCKETS.csv"
OUT_EVENTS = ROOT / "GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011_EVENTS.csv"

DEPTH_ATR = 1.00
STOP_ATR = 1.50
RR = 3.00
POST_FILL_MIN = 30
EXTRA_COST_R = 0.05
EXPIRIES = (1, 3, 5, 10, 15, 30, 60)
RESP_H = (5, 15, 30)
MAX_GAP_MS = 5 * 60 * 1000
END_LAG_MS = 5000
SEED = 20260916
BOOT_N = 5000

BUCKETS = [
    ("0-1m", 0.0, 1.0),
    ("1-3m", 1.0, 3.0),
    ("3-5m", 3.0, 5.0),
    ("5-10m", 5.0, 10.0),
    ("10-15m", 10.0, 15.0),
    ("15-30m", 15.0, 30.0),
    ("30-60m", 30.0, 60.0000001),
]


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def read_xau_ticks():
    files = sorted(p for p in XAU_DIR.glob("XAUUSD_raw_ticks_*.csv") if ".meta." not in p.name)
    if not files:
        raise SystemExit(f"No XAU raw ticks in {XAU_DIR}")
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
        frames.append(d[["time_msc", "bid", "ask"]])
        stats.append({
            "file": p.name,
            "rows": int(len(d)),
            "first_time_msc": int(d.time_msc.iloc[0]),
            "last_time_msc": int(d.time_msc.iloc[-1]),
        })
    if not frames:
        raise SystemExit("No quote-valid ticks")
    x = pd.concat(frames, ignore_index=True)
    x = x.sort_values("time_msc", kind="mergesort").drop_duplicates(["time_msc", "bid", "ask"]).reset_index(drop=True)
    t = x.time_msc.to_numpy(np.int64)
    b = x.bid.to_numpy(float)
    a = x.ask.to_numpy(float)
    if np.any(np.diff(t) < 0):
        raise SystemExit("XAU timestamps non-monotonic")
    return t, b, a, stats


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
    common_times = sorted(set(r.signal_time_utc) & set(a.signal_time_utc))
    p = r[r.signal_time_utc.isin(common_times)].drop_duplicates("signal_time_utc").copy()
    p = p[p.executable_bool & p.xau_atr14_m1.gt(0) & p.entry_tick_msc.notna() & p.entry_ask.gt(0)].copy()
    s = a[a.executable_bool & a.xau_atr14_m1.gt(0) & a.entry_tick_msc.notna() & a.entry_ask.gt(0)].drop_duplicates("signal_time_utc").copy()
    p["cohort"] = "COMMON_CLOCK"
    s["cohort"] = "AMP_ALL"
    return p.sort_values("signal_time_utc").reset_index(drop=True), s.sort_values("signal_time_utc").reset_index(drop=True), len(common_times)


def exact_market_idx(times: np.ndarray, event):
    ts = int(event.entry_tick_msc)
    i = int(np.searchsorted(times, ts, side="left"))
    if i >= len(times) or int(times[i]) != ts:
        return None
    return i


def has_large_gap(times: np.ndarray, i0: int, i1: int) -> bool:
    if i1 <= i0:
        return False
    return bool(np.any(np.diff(times[i0:i1 + 1]) > MAX_GAP_MS))


def first_at_or_after(times: np.ndarray, target_ms: int, max_lag_ms: int = END_LAG_MS):
    i = int(np.searchsorted(times, target_ms, side="left"))
    if i >= len(times):
        return None, None
    lag = int(times[i] - target_ms)
    if lag < 0 or lag > max_lag_ms:
        return None, lag
    return i, lag


def event_record(times, bids, asks, event):
    mi = exact_market_idx(times, event)
    rec = {
        "cohort": event.cohort,
        "signal_time_utc": event.signal_time_utc.isoformat(),
        "broker_target_msc": int(event.broker_target_msc),
        "market_tick_msc": int(event.entry_tick_msc),
        "market_ask": float(event.entry_ask),
        "atr": float(event.xau_atr14_m1),
        "limit_price": float(event.entry_ask - DEPTH_ATR * event.xau_atr14_m1),
        "fill60": False,
        "fill_time_msc": np.nan,
        "fill_delay_min": np.nan,
        "fill_price": np.nan,
        "fill_gap_reject": False,
        "outcome_known": False,
        "status": "NO_FILL_60M",
        "raw_r": np.nan,
        "net_r": np.nan,
        "exit_time_msc": np.nan,
        "exit_price": np.nan,
    }
    for h in RESP_H:
        rec[f"resp_{h}m_atr"] = np.nan
    if mi is None:
        rec["status"] = "MARKET_REFERENCE_NOT_FOUND"
        return rec

    end60 = int(event.broker_target_msc) + 60 * 60000
    j_end = int(np.searchsorted(times, end60, side="right"))
    if j_end <= mi:
        return rec
    hits = np.flatnonzero(asks[mi:j_end] <= rec["limit_price"] + 1e-12)
    if len(hits) == 0:
        return rec
    fi = mi + int(hits[0])
    if has_large_gap(times, mi, fi):
        rec["fill_gap_reject"] = True
        rec["status"] = "PRE_FILL_GAP_REJECT"
        return rec

    rec["fill60"] = True
    rec["fill_time_msc"] = int(times[fi])
    rec["fill_delay_min"] = float((times[fi] - int(event.broker_target_msc)) / 60000.0)
    rec["fill_price"] = rec["limit_price"]

    # Diagnostic fixed-horizon responses from actual fill.
    for h in RESP_H:
        target = int(times[fi]) + h * 60000
        ei, _ = first_at_or_after(times, target)
        if ei is None or has_large_gap(times, fi, ei):
            continue
        rec[f"resp_{h}m_atr"] = float((bids[ei] - rec["fill_price"]) / rec["atr"])

    trade_end = int(times[fi]) + POST_FILL_MIN * 60000
    ei, _ = first_at_or_after(times, trade_end)
    if ei is None or has_large_gap(times, fi, ei):
        rec["status"] = "POST_FILL_DATA_GAP"
        return rec

    entry = rec["fill_price"]
    atr = rec["atr"]
    stop = entry - STOP_ATR * atr
    target = entry + (RR * STOP_ATR) * atr
    path = bids[fi:ei + 1]
    sh = np.flatnonzero(path <= stop + 1e-12)
    th = np.flatnonzero(path >= target - 1e-12)
    si = int(sh[0]) if len(sh) else None
    ti = int(th[0]) if len(th) else None
    if si is not None and (ti is None or si <= ti):
        k = fi + si
        raw_r = -1.0
        rec.update(status="SL", exit_time_msc=int(times[k]), exit_price=float(stop))
    elif ti is not None:
        k = fi + ti
        raw_r = RR
        rec.update(status="TP", exit_time_msc=int(times[k]), exit_price=float(target))
    else:
        raw_r = float((bids[ei] - entry) / (STOP_ATR * atr))
        rec.update(status="TIMEOUT", exit_time_msc=int(times[ei]), exit_price=float(bids[ei]))
    rec["outcome_known"] = True
    rec["raw_r"] = raw_r
    rec["net_r"] = raw_r - EXTRA_COST_R
    return rec


def max_dd(rs: np.ndarray) -> float:
    if len(rs) == 0:
        return np.nan
    eq = np.cumsum(np.nan_to_num(rs, nan=0.0))
    eq0 = np.r_[0.0, eq]
    peaks = np.maximum.accumulate(eq0)
    return float(np.max(peaks - eq0))


def pf_of(v: np.ndarray):
    if len(v) == 0:
        return np.nan
    pos = float(v[v > 0].sum())
    neg = float(-v[v < 0].sum())
    if neg == 0:
        return np.inf if pos > 0 else np.nan
    return pos / neg


def day_boot_ci(z: pd.DataFrame, col="signal_r"):
    q = z.dropna(subset=[col]).copy()
    if q.empty:
        return [None, None]
    q["day"] = pd.to_datetime(q.signal_time_utc, utc=True).dt.date
    groups = [g[col].to_numpy(float) for _, g in q.groupby("day")]
    if len(groups) < 2:
        return [None, None]
    rng = np.random.default_rng(SEED)
    vals = np.empty(BOOT_N)
    k = len(groups)
    for j in range(BOOT_N):
        picks = rng.integers(0, k, k)
        vals[j] = np.concatenate([groups[i] for i in picks]).mean()
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def expiry_summary(ev: pd.DataFrame, expiry: int):
    q = ev.copy().sort_values("signal_time_utc").reset_index(drop=True)
    eligible = q.fill60 & q.outcome_known & q.fill_delay_min.le(expiry + 1e-12)
    q["filled_expiry"] = eligible
    q["signal_r"] = np.where(eligible, q.net_r, 0.0)
    fills = q[eligible].copy()
    v = fills.net_r.to_numpy(float)
    n = len(q)
    split = n // 2
    early = float(q.iloc[:split].signal_r.mean()) if split else np.nan
    late = float(q.iloc[split:].signal_r.mean()) if n - split else np.nan
    return {
        "signals": int(n),
        "fills": int(len(fills)),
        "fill_rate_pct": float(100 * len(fills) / n) if n else None,
        "ev_r_per_signal": float(q.signal_r.mean()) if n else None,
        "ev_r_per_fill": float(v.mean()) if len(v) else None,
        "pf": float(pf_of(v)) if len(v) else None,
        "wr_fill_pct": float(100 * (v > 0).mean()) if len(v) else None,
        "max_dd_r": max_dd(q.signal_r.to_numpy(float)),
        "early_ev_r_signal": early,
        "late_ev_r_signal": late,
        "day_ci95_r_signal": day_boot_ci(q),
    }


def bucket_summary(ev: pd.DataFrame, name: str, lo: float, hi: float):
    q = ev[ev.fill60 & ev.outcome_known & ev.fill_delay_min.ge(lo) & ev.fill_delay_min.lt(hi)].copy()
    v = q.net_r.to_numpy(float)
    if len(q):
        q = q.sort_values("signal_time_utc").reset_index(drop=True)
        split = len(q) // 2
        early = float(q.iloc[:split].net_r.mean()) if split else np.nan
        late = float(q.iloc[split:].net_r.mean()) if len(q) - split else np.nan
    else:
        early = late = np.nan
    row = {
        "bucket": name,
        "lo_min": lo,
        "hi_min": hi,
        "n": int(len(q)),
        "ev_r_fill": float(v.mean()) if len(v) else None,
        "pf": float(pf_of(v)) if len(v) else None,
        "wr_pct": float(100 * (v > 0).mean()) if len(v) else None,
        "early_ev_r": early,
        "late_ev_r": late,
        "day_ci95_r": day_boot_ci(q.assign(signal_r=q.net_r)) if len(q) else [None, None],
        "resp_5m_atr": float(q.resp_5m_atr.dropna().mean()) if len(q.resp_5m_atr.dropna()) else None,
        "resp_15m_atr": float(q.resp_15m_atr.dropna().mean()) if len(q.resp_15m_atr.dropna()) else None,
        "resp_30m_atr": float(q.resp_30m_atr.dropna().mean()) if len(q.resp_30m_atr.dropna()) else None,
    }
    return row


def fmt(x, d=3):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{x:+.{d}f}"


def main():
    times, bids, asks, stats = read_xau_ticks()
    common, amp, common_raw = load_cohorts()
    event_frames = []
    for cohort in (common, amp):
        rows = [event_record(times, bids, asks, r) for r in cohort.itertuples(index=False)]
        event_frames.append(pd.DataFrame(rows))
    ev = pd.concat(event_frames, ignore_index=True)
    ev.to_csv(OUT_EVENTS, index=False)

    expiry_rows = []
    bucket_rows = []
    result = {
        "lab": "GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011",
        "status": "POST_DISCOVERY_SIGNAL_DECAY_MAP_NOT_OOS",
        "frozen": {
            "depth_atr": DEPTH_ATR,
            "stop_atr": STOP_ATR,
            "rr": RR,
            "post_fill_minutes": POST_FILL_MIN,
            "extra_cost_r_per_fill": EXTRA_COST_R,
            "expiries_min": list(EXPIRIES),
        },
        "common_raw_signal_times": common_raw,
        "xau_files": len(stats),
        "xau_quote_valid_ticks": int(len(times)),
        "cohorts": {},
    }

    for cname in ("COMMON_CLOCK", "AMP_ALL"):
        z = ev[ev.cohort.eq(cname)].copy()
        ex = {}
        for e in EXPIRIES:
            s = expiry_summary(z, e)
            ex[str(e)] = s
            expiry_rows.append({"cohort": cname, "expiry_min": e, **{k: v for k, v in s.items() if k != "day_ci95_r_signal"}, "ci_lo": s["day_ci95_r_signal"][0], "ci_hi": s["day_ci95_r_signal"][1]})
        bs = []
        for name, lo, hi in BUCKETS:
            s = bucket_summary(z, name, lo, hi)
            bs.append(s)
            bucket_rows.append({"cohort": cname, **{k: v for k, v in s.items() if k != "day_ci95_r"}, "ci_lo": s["day_ci95_r"][0], "ci_hi": s["day_ci95_r"][1]})
        result["cohorts"][cname] = {
            "signals": int(len(z)),
            "filled_within_60m": int((z.fill60 & z.outcome_known).sum()),
            "pre_fill_gap_rejects": int(z.fill_gap_reject.sum()),
            "post_fill_data_gaps": int((z.status == "POST_FILL_DATA_GAP").sum()),
            "expiry_curve": ex,
            "delay_buckets": bs,
        }

    pd.DataFrame(expiry_rows).to_csv(OUT_EXPIRY, index=False)
    pd.DataFrame(bucket_rows).to_csv(OUT_BUCKETS, index=False)
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        "# GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011",
        "",
        "**Status: POST_DISCOVERY_SIGNAL_DECAY_MAP_NOT_OOS**",
        "",
        f"Frozen geometry: depth **{DEPTH_ATR:.2f} ATR**, SL **{STOP_ATR:.2f} ATR**, TP **{RR:.1f}R**, +**{EXTRA_COST_R:.2f}R/fill** stress cost. Each filled limit receives a fixed **{POST_FILL_MIN}m post-fill evaluation window** so late fills can be compared on equal footing.",
        "",
        "## Cumulative expiry curve",
        "",
        "| Cohort | Expiry | Fill | EV R/signal | EV R/fill | PF | WR | MaxDD R | EARLY EV | LATE EV | CI95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cname in ("COMMON_CLOCK", "AMP_ALL"):
        for e in EXPIRIES:
            s = result["cohorts"][cname]["expiry_curve"][str(e)]
            ci = s["day_ci95_r_signal"]
            lines.append(
                f"| {cname} | {e}m | {s['fill_rate_pct']:.1f}% | {fmt(s['ev_r_per_signal'])} | {fmt(s['ev_r_per_fill'])} | {s['pf']:.2f} | {s['wr_fill_pct']:.1f}% | {s['max_dd_r']:.2f} | {fmt(s['early_ev_r_signal'])} | {fmt(s['late_ev_r_signal'])} | [{fmt(ci[0])},{fmt(ci[1])}] |"
            )
    lines += [
        "",
        "## First-fill delay buckets",
        "",
        "| Cohort | Delay | N | EV R/fill | PF | WR | EARLY | LATE | Resp5 ATR | Resp15 ATR | Resp30 ATR | CI95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cname in ("COMMON_CLOCK", "AMP_ALL"):
        for s in result["cohorts"][cname]["delay_buckets"]:
            ci = s["day_ci95_r"]
            pf = "NA" if s["pf"] is None or not np.isfinite(s["pf"]) else f"{s['pf']:.2f}"
            wr = "NA" if s["wr_pct"] is None else f"{s['wr_pct']:.1f}%"
            lines.append(
                f"| {cname} | {s['bucket']} | {s['n']} | {fmt(s['ev_r_fill'])} | {pf} | {wr} | {fmt(s['early_ev_r'])} | {fmt(s['late_ev_r'])} | {fmt(s['resp_5m_atr'])} | {fmt(s['resp_15m_atr'])} | {fmt(s['resp_30m_atr'])} | [{fmt(ci[0])},{fmt(ci[1])}] |"
            )
    lines += [
        "",
        "## Governance",
        "",
        "This LAB measures decay on the already-exposed historical sample. It does not choose a production expiry and is not independent OOS. A late re-improvement is not promoted as the same edge without separate replication.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
