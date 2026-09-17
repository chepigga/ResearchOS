#!/usr/bin/env python3
"""LAB003 — GC SHORT Chris/AEIF buy-failure discovery.

Frozen mechanism:
extreme BUY effort + upper location + weak upward result -> bearish confirmation <=2 M1 -> SHORT.
Historical bounded discovery only; no XAU execution tuning.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
BASE = ROOT / "gc_m1_orderflow_edge_discovery_003.py"
OUT_JSON = ROOT / "GC_SHORT_CHRIS_AEIF_BUY_FAILURE_LAB_003.json"
OUT_MD = ROOT / "GC_SHORT_CHRIS_AEIF_BUY_FAILURE_LAB_003.md"
OUT_EVENTS = ROOT / "GC_SHORT_CHRIS_AEIF_BUY_FAILURE_LAB_003_EVENTS.csv"

TRAIN_END = pd.Timestamp("2026-08-20T00:00:00Z")
VALID_END = pd.Timestamp("2026-09-06T22:00:00Z")
LATE_END = pd.Timestamp("2026-09-11T12:46:00Z")
HORIZONS = (15, 30)


def load_base():
    spec = importlib.util.spec_from_file_location("edge003_chris003", BASE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def contiguous(b, i, j):
    return b.iloc[j].time == b.iloc[i].time + pd.Timedelta(minutes=j-i)


def build_events(b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    seed = (
        b.a_buy
        & b.q75_buyloc.notna()
        & (b.buy_loc >= b.q75_buyloc)
        & b.impact_q20.notna()
        & (b.impact <= b.impact_q20)
    )
    idxs = np.flatnonzero(seed.to_numpy())
    for i in idxs:
        if i + 3 >= len(b):
            continue
        if not contiguous(b, i, i+1):
            continue
        atr = float(b.iloc[i].atr14)
        if not np.isfinite(atr) or atr <= 0:
            continue
        seed_close = float(b.iloc[i].close)
        confirm_i = None
        for k in (1, 2):
            j = i + k
            if j >= len(b) or not contiguous(b, i, j):
                break
            r = b.iloc[j]
            if float(r.close) < float(r.open) and float(r.close) < seed_close and float(r.close_pos) <= 0.50:
                confirm_i = j
                break
        if confirm_i is None:
            continue
        entry_i = confirm_i + 1
        if entry_i >= len(b) or not contiguous(b, confirm_i, entry_i):
            continue
        ep = float(b.iloc[entry_i].open)
        row = {
            "feed": b.iloc[i].feed,
            "seed_time": b.iloc[i].time,
            "confirm_time": b.iloc[confirm_i].time,
            "confirm_lag_m1": int(confirm_i-i),
            "entry_time": b.iloc[entry_i].time,
            "entry": ep,
            "seed_atr14": atr,
            "seed_delta_frac": float(b.iloc[i].delta_frac),
            "seed_buy_vol": float(b.iloc[i].buy_vol),
            "seed_buy_loc": float(b.iloc[i].buy_loc),
            "seed_impact": float(b.iloc[i].impact),
            "seed_impact_q20": float(b.iloc[i].impact_q20),
            "seed_close_pos": float(b.iloc[i].close_pos),
        }
        for h in HORIZONS:
            j = entry_i + h - 1
            if j < len(b) and b.iloc[j].time == b.iloc[entry_i].time + pd.Timedelta(minutes=h-1):
                px = float(b.iloc[j].close)
                row[f"fwd_{h}m_atr"] = (ep - px) / atr
            else:
                row[f"fwd_{h}m_atr"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def period(df, name):
    t = pd.to_datetime(df.seed_time, utc=True)
    if name == "TRAIN": return df[t < TRAIN_END]
    if name == "VALID": return df[(t >= TRAIN_END) & (t < VALID_END)]
    if name == "LATE_CHECK": return df[(t >= VALID_END) & (t <= LATE_END)]
    if name == "POST_CHECK": return df[t > LATE_END]
    if name == "FULL": return df
    raise ValueError(name)


def metric(df, h):
    v = df[f"fwd_{h}m_atr"].dropna().to_numpy(float)
    if not len(v):
        return {"n": 0, "ev": None, "median": None, "wr": None, "sum": None}
    return {
        "n": int(len(v)),
        "ev": float(v.mean()),
        "median": float(np.median(v)),
        "wr": float((v > 0).mean()*100),
        "sum": float(v.sum()),
    }


def summarize(df):
    return {p: {str(h): metric(period(df, p), h) for h in HORIZONS}
            for p in ("TRAIN","VALID","LATE_CHECK","POST_CHECK","FULL")}


def gate(r, a):
    def ev(s,p,h): return s[p][str(h)]["ev"]
    def n(s,p,h): return s[p][str(h)]["n"]
    checks = {
        "rithmic_full_n15_ge25": n(r,"FULL",15) >= 25,
        "rithmic_train_n15_ge10": n(r,"TRAIN",15) >= 10,
        "rithmic_valid_n15_ge8": n(r,"VALID",15) >= 8,
        "rithmic_train_ev15_pos": ev(r,"TRAIN",15) is not None and ev(r,"TRAIN",15) > 0,
        "rithmic_valid_ev15_pos": ev(r,"VALID",15) is not None and ev(r,"VALID",15) > 0,
        "rithmic_valid_ev30_pos": ev(r,"VALID",30) is not None and ev(r,"VALID",30) > 0,
        "rithmic_full_ev15_pos": ev(r,"FULL",15) is not None and ev(r,"FULL",15) > 0,
        "rithmic_full_ev30_pos": ev(r,"FULL",30) is not None and ev(r,"FULL",30) > 0,
        "rithmic_late_conditional_positive": (
            n(r,"LATE_CHECK",15) < 3 or
            ((ev(r,"LATE_CHECK",15) is not None and ev(r,"LATE_CHECK",15) > 0) and
             (ev(r,"LATE_CHECK",30) is not None and ev(r,"LATE_CHECK",30) > 0))
        ),
        "amp_valid_ev15_pos": ev(a,"VALID",15) is not None and ev(a,"VALID",15) > 0,
        "amp_valid_ev30_pos": ev(a,"VALID",30) is not None and ev(a,"VALID",30) > 0,
    }
    checks["pass"] = all(checks.values())
    return checks


def fmt(x):
    return "NA" if x is None else f"{x:+.5f}"


def main():
    m = load_base()
    work = ROOT / "_chris003_work"
    work.mkdir(parents=True, exist_ok=True)
    rz = work / "rithmic.zip"
    az = work / "amp.zip"
    if not rz.exists(): m.download(m.RITH_URL, rz)
    if not az.exists(): m.download(m.AMP_URL, az)
    if m.sha(rz) != m.RITH_SHA or m.sha(az) != m.AMP_SHA:
        raise SystemExit("source SHA mismatch")

    rb = m.load_rithmic(rz)
    ab = m.load_amp(az)
    re = build_events(rb)
    ae = build_events(ab)
    all_events = pd.concat([re, ae], ignore_index=True)
    all_events.to_csv(OUT_EVENTS, index=False)

    rs, aas = summarize(re), summarize(ae)
    g = gate(rs, aas)
    status = "HISTORICAL_CHRIS_AEIF_SHORT_CANDIDATE_NOT_OOS" if g["pass"] else "HISTORICAL_CHRIS_AEIF_SHORT_REJECT_NOT_OOS"
    result = {
        "status": status,
        "mechanism": "EXTREME BUY + UPPER LOCATION + WEAK RESULT -> BEARISH CONFIRM <=2 M1 -> SHORT",
        "rithmic": rs,
        "amp": aas,
        "gates": g,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# GC SHORT CHRIS/AEIF BUY FAILURE LAB003", "",
        f"**Status:** `{status}`", "",
        "Mechanism: `EXTREME BUY -> UPPER LOCATION -> WEAK UPWARD RESULT -> BEARISH CONFIRMATION <=2 M1 -> SHORT`.",
        "Historical bounded discovery only; not independent OOS. No XAU execution tuning here.", "",
        "## Key periods", "",
        "| Feed | Period | N15 | EV15 ATR | N30 | EV30 ATR |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for feed, s in (("RITHMIC",rs),("AMP",aas)):
        for p in ("TRAIN","VALID","LATE_CHECK","POST_CHECK","FULL"):
            lines.append(f"| {feed} | {p} | {s[p]['15']['n']} | {fmt(s[p]['15']['ev'])} | {s[p]['30']['n']} | {fmt(s[p]['30']['ev'])} |")
    lines += ["", "## Frozen gates", ""]
    for k,v in g.items():
        if k != "pass": lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", "## Decision", ""]
    if g["pass"]:
        lines.append("Advance this exact historical Chris/AEIF SHORT definition to a separate GC->XAU transfer lab. Do not retune thresholds before transfer.")
    else:
        lines.append("Reject this exact definition. Do not tune its thresholds post hoc; any continuation requires a separately preregistered mechanism.")
    OUT_MD.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(status)
    print(json.dumps(g, indent=2))

if __name__ == "__main__":
    main()
