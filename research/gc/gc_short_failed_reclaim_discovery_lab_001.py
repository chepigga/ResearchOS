#!/usr/bin/env python3
"""GC_SHORT_FAILED_RECLAIM_DISCOVERY_LAB_001

Separate bounded historical SHORT discovery lineage.
Primary mechanism:
SELLER BREAKDOWN -> RECOVERY ATTEMPT -> FAILED RECLAIM -> SHORT.

No XAU execution tuning. No threshold sweep. Not independent OOS.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
BASE = ROOT / "gc_m1_orderflow_edge_discovery_003.py"
WORK = ROOT / "_short001_work"
OUT_JSON = ROOT / "GC_SHORT_FAILED_RECLAIM_DISCOVERY_LAB_001.json"
OUT_MD = ROOT / "GC_SHORT_FAILED_RECLAIM_DISCOVERY_LAB_001.md"
OUT_EVENTS = ROOT / "GC_SHORT_FAILED_RECLAIM_DISCOVERY_LAB_001_EVENTS.csv"
OUT_METRICS = ROOT / "GC_SHORT_FAILED_RECLAIM_DISCOVERY_LAB_001_METRICS.csv"

TRAIN_END = pd.Timestamp("2026-08-20T00:00:00Z")
VALID_END = pd.Timestamp("2026-09-06T22:00:00Z")
LATE_END = pd.Timestamp("2026-09-11T12:46:00Z")
HORIZONS = (5, 15, 30)


def load_base():
    spec = importlib.util.spec_from_file_location("edge003_short001", BASE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def ensure_sources(m):
    WORK.mkdir(parents=True, exist_ok=True)
    rz = WORK / "rithmic.zip"
    az = WORK / "amp.zip"
    if not rz.exists():
        m.download(m.RITH_URL, rz)
    if not az.exists():
        m.download(m.AMP_URL, az)
    if m.sha(rz) != m.RITH_SHA:
        raise SystemExit("Rithmic source SHA mismatch")
    if m.sha(az) != m.AMP_SHA:
        raise SystemExit("AMP source SHA mismatch")
    return rz, az


def contiguous(b: pd.DataFrame, i: int, j: int) -> bool:
    return 0 <= i < len(b) and 0 <= j < len(b) and b.iloc[j].time == b.iloc[i].time + pd.Timedelta(minutes=j - i)


def breakdown_mask(b: pd.DataFrame) -> pd.Series:
    return (
        b.a_sell
        & b.prior20_low.notna()
        & (b.low <= b.prior20_low)
        & (b.close < b.prior20_low)
        & (b.close_pos <= 0.25)
        & (b.body_atr < 0)
        & b.atr14.notna()
        & (b.atr14 > 0)
    )


def add_outcomes(row: dict, b: pd.DataFrame, entry_i: int, atr: float):
    ep = float(b.iloc[entry_i].open)
    row["entry_time"] = b.iloc[entry_i].time
    row["entry_price"] = ep
    for h in HORIZONS:
        j = entry_i + h - 1
        col = f"fwd_{h}m_atr"
        if j >= len(b) or not contiguous(b, entry_i, j):
            row[col] = np.nan
        else:
            row[col] = float((ep - float(b.iloc[j].close)) / atr)
    return row


def build_primary(b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    idxs = np.flatnonzero(breakdown_mask(b).to_numpy())
    for bi in idxs:
        B = b.iloc[bi]
        level = float(B.prior20_low)
        ci = None
        for k in (1, 2):
            j = bi + k
            if j >= len(b) or not contiguous(b, bi, j):
                break
            C = b.iloc[j]
            if float(C.high) >= level and float(C.close) < level and float(C.delta_frac) < 0:
                ci = j
                break
        if ci is None:
            continue
        ei = ci + 1
        if ei >= len(b) or not contiguous(b, ci, ei):
            continue
        C = b.iloc[ci]
        atr = float(C.atr14)
        if not np.isfinite(atr) or atr <= 0:
            continue
        r = {
            "feed": str(B.feed),
            "candidate": "FAILED_RECLAIM_SHORT_001",
            "breakdown_time": B.time,
            "confirmation_time": C.time,
            "confirmation_lag_bars": int(ci - bi),
            "broken_level": level,
            "breakdown_close": float(B.close),
            "breakdown_delta_frac": float(B.delta_frac),
            "breakdown_sell_vol": float(B.sell_vol),
            "breakdown_body_atr": float(B.body_atr),
            "breakdown_close_pos": float(B.close_pos),
            "confirmation_high": float(C.high),
            "confirmation_close": float(C.close),
            "confirmation_delta_frac": float(C.delta_frac),
            "atr14": atr,
        }
        rows.append(add_outcomes(r, b, ei, atr))
    return pd.DataFrame(rows)


def build_reference(b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    idxs = np.flatnonzero(breakdown_mask(b).to_numpy())
    for bi in idxs:
        ei = bi + 1
        if ei >= len(b) or not contiguous(b, bi, ei):
            continue
        B = b.iloc[bi]
        atr = float(B.atr14)
        if not np.isfinite(atr) or atr <= 0:
            continue
        r = {
            "feed": str(B.feed),
            "candidate": "MIRROR_BREAKDOWN_SHORT_REF",
            "breakdown_time": B.time,
            "confirmation_time": B.time,
            "confirmation_lag_bars": 0,
            "broken_level": float(B.prior20_low),
            "breakdown_close": float(B.close),
            "breakdown_delta_frac": float(B.delta_frac),
            "breakdown_sell_vol": float(B.sell_vol),
            "breakdown_body_atr": float(B.body_atr),
            "breakdown_close_pos": float(B.close_pos),
            "confirmation_high": np.nan,
            "confirmation_close": np.nan,
            "confirmation_delta_frac": np.nan,
            "atr14": atr,
        }
        rows.append(add_outcomes(r, b, ei, atr))
    return pd.DataFrame(rows)


def period_mask(t: pd.Series, p: str) -> pd.Series:
    tt = pd.to_datetime(t, utc=True)
    if p == "TRAIN":
        return tt < TRAIN_END
    if p == "VALID":
        return (tt >= TRAIN_END) & (tt < VALID_END)
    if p == "LATE_CHECK":
        return (tt >= VALID_END) & (tt <= LATE_END)
    if p == "POST_CHECK":
        return tt > LATE_END
    if p == "FULL":
        return pd.Series(True, index=tt.index)
    raise ValueError(p)


def metrics(events: pd.DataFrame, feed_label: str, candidate: str):
    rows = []
    if events.empty:
        for p in ("TRAIN", "VALID", "LATE_CHECK", "POST_CHECK", "FULL"):
            for h in HORIZONS:
                rows.append({"feed": feed_label, "candidate": candidate, "period": p, "horizon_min": h, "n": 0, "ev_atr": np.nan, "median_atr": np.nan, "wr_pct": np.nan, "days": 0, "positive_days": 0})
        return rows
    clock = events.confirmation_time
    for p in ("TRAIN", "VALID", "LATE_CHECK", "POST_CHECK", "FULL"):
        d = events[period_mask(clock, p)].copy()
        for h in HORIZONS:
            col = f"fwd_{h}m_atr"
            x = pd.to_numeric(d[col], errors="coerce").dropna()
            dd = d.loc[x.index].copy() if len(x) else d.iloc[:0].copy()
            if len(dd):
                dd["day"] = pd.to_datetime(dd.confirmation_time, utc=True).dt.date
                daily = dd.groupby("day")[col].mean()
            else:
                daily = pd.Series(dtype=float)
            rows.append({
                "feed": feed_label,
                "candidate": candidate,
                "period": p,
                "horizon_min": h,
                "n": int(len(x)),
                "ev_atr": float(x.mean()) if len(x) else np.nan,
                "median_atr": float(x.median()) if len(x) else np.nan,
                "wr_pct": float((x > 0).mean() * 100) if len(x) else np.nan,
                "days": int(len(daily)),
                "positive_days": int((daily > 0).sum()),
            })
    return rows


def get_metric(mdf: pd.DataFrame, feed: str, candidate: str, period: str, h: int):
    d = mdf[(mdf.feed == feed) & (mdf.candidate == candidate) & (mdf.period == period) & (mdf.horizon_min == h)]
    if len(d) != 1:
        raise SystemExit(f"Missing metric {feed} {candidate} {period} {h}")
    return d.iloc[0]


def scalar(v):
    return None if pd.isna(v) else float(v)


def main():
    m = load_base()
    rz, az = ensure_sources(m)
    rb = m.load_rithmic(rz)
    ab = m.load_amp(az)

    datasets = []
    all_metric_rows = []
    for label, bars in (("RITHMIC", rb), ("AMP", ab)):
        p = build_primary(bars)
        r = build_reference(bars)
        datasets.extend([p, r])
        all_metric_rows += metrics(p, label, "FAILED_RECLAIM_SHORT_001")
        all_metric_rows += metrics(r, label, "MIRROR_BREAKDOWN_SHORT_REF")

    events = pd.concat(datasets, ignore_index=True) if datasets else pd.DataFrame()
    if not events.empty:
        events = events.sort_values(["candidate", "feed", "confirmation_time"]).reset_index(drop=True)
    events.to_csv(OUT_EVENTS, index=False)
    mdf = pd.DataFrame(all_metric_rows)
    mdf.to_csv(OUT_METRICS, index=False)

    P = "FAILED_RECLAIM_SHORT_001"
    rf = get_metric(mdf, "RITHMIC", P, "FULL", 15)
    rv15 = get_metric(mdf, "RITHMIC", P, "VALID", 15)
    rv30 = get_metric(mdf, "RITHMIC", P, "VALID", 30)
    rl15 = get_metric(mdf, "RITHMIC", P, "LATE_CHECK", 15)
    rl30 = get_metric(mdf, "RITHMIC", P, "LATE_CHECK", 30)
    afv15 = get_metric(mdf, "AMP", P, "VALID", 15)
    afv30 = get_metric(mdf, "AMP", P, "VALID", 30)
    rf30 = get_metric(mdf, "RITHMIC", P, "FULL", 30)

    gates = {
        "rithmic_full_n_ge30": int(rf.n) >= 30,
        "rithmic_valid_n_ge8": int(rv15.n) >= 8,
        "rithmic_valid_15m_ev_pos": pd.notna(rv15.ev_atr) and float(rv15.ev_atr) > 0,
        "rithmic_valid_30m_ev_pos": pd.notna(rv30.ev_atr) and float(rv30.ev_atr) > 0,
        "rithmic_late_n_ge3_and_15m_ev_pos": int(rl15.n) >= 3 and pd.notna(rl15.ev_atr) and float(rl15.ev_atr) > 0,
        "rithmic_late_30m_ev_pos": pd.notna(rl30.ev_atr) and float(rl30.ev_atr) > 0,
        "amp_valid_15m_ev_pos": pd.notna(afv15.ev_atr) and float(afv15.ev_atr) > 0,
        "amp_valid_30m_ev_pos": pd.notna(afv30.ev_atr) and float(afv30.ev_atr) > 0,
        "rithmic_full_15m_ev_pos": pd.notna(rf.ev_atr) and float(rf.ev_atr) > 0,
        "rithmic_full_30m_ev_pos": pd.notna(rf30.ev_atr) and float(rf30.ev_atr) > 0,
    }
    passed = all(bool(v) for v in gates.values())
    status = "HISTORICAL_SHORT_MECHANISM_CANDIDATE_PASS_NOT_OOS" if passed else "HISTORICAL_SHORT_MECHANISM_REJECT_NOT_OOS"

    def pack(feed, cand, period):
        out = {}
        for h in HORIZONS:
            rr = get_metric(mdf, feed, cand, period, h)
            out[str(h)] = {"n": int(rr.n), "ev_atr": scalar(rr.ev_atr), "median_atr": scalar(rr.median_atr), "wr_pct": scalar(rr.wr_pct), "days": int(rr.days), "positive_days": int(rr.positive_days)}
        return out

    result = {
        "lab": "GC_SHORT_FAILED_RECLAIM_DISCOVERY_LAB_001",
        "status": status,
        "primary": {
            "RITHMIC": {p: pack("RITHMIC", P, p) for p in ("TRAIN", "VALID", "LATE_CHECK", "FULL")},
            "AMP": {p: pack("AMP", P, p) for p in ("TRAIN", "VALID", "LATE_CHECK", "POST_CHECK", "FULL")},
        },
        "reference_mirror_breakdown": {
            "RITHMIC": {p: pack("RITHMIC", "MIRROR_BREAKDOWN_SHORT_REF", p) for p in ("TRAIN", "VALID", "LATE_CHECK", "FULL")},
            "AMP": {p: pack("AMP", "MIRROR_BREAKDOWN_SHORT_REF", p) for p in ("TRAIN", "VALID", "LATE_CHECK", "POST_CHECK", "FULL")},
        },
        "gates": gates,
        "governance": {
            "xau_tuning": False,
            "threshold_search": False,
            "confirmation_window_search": False,
            "new_market_data": False,
            "independent_oos": False,
        },
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    def fm(x):
        return "NA" if x is None else f"{x:+.5f}"
    md = [
        "# GC SHORT FAILED-RECLAIM DISCOVERY LAB001",
        "",
        f"**Status:** `{status}`",
        "",
        "Primary mechanism: `SELLER BREAKDOWN -> RECOVERY ATTEMPT -> FAILED RECLAIM -> SHORT`.",
        "This is historical bounded discovery only; not independent OOS.",
        "",
        "## Primary key periods",
        "",
        "| Feed | Period | N15 | EV15 ATR | N30 | EV30 ATR |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for feed, periods in (("RITHMIC", ("TRAIN", "VALID", "LATE_CHECK", "FULL")), ("AMP", ("VALID", "LATE_CHECK", "POST_CHECK", "FULL"))):
        for p in periods:
            a = result["primary"][feed][p]["15"]
            z = result["primary"][feed][p]["30"]
            md.append(f"| {feed} | {p} | {a['n']} | {fm(a['ev_atr'])} | {z['n']} | {fm(z['ev_atr'])} |")
    md += ["", "## Frozen gates", ""]
    for k, v in gates.items():
        md.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    md += [
        "",
        "## Decision",
        "",
        ("Primary failed-reclaim mechanism passes the preregistered historical discovery gates and may advance to a separate GC->FTMO XAU transfer LAB. It is not OOS or production-proven." if passed else "Reject this exact failed-reclaim definition. Do not tune its thresholds post hoc. If SHORT research continues, preregister a different bearish mechanism."),
    ]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
