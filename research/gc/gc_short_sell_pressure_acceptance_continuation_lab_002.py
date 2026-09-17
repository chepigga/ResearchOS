#!/usr/bin/env python3
"""LAB002 — GC SHORT sell-pressure acceptance continuation.

Historical bounded discovery only; not OOS.
Preregistered mechanism:
extreme seller flow -> break/close below prior20 low -> next M1 accepts below -> SHORT.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
BASE = ROOT / "gc_m1_orderflow_edge_discovery_003.py"
OUT_JSON = ROOT / "GC_SHORT_SELL_PRESSURE_ACCEPTANCE_CONTINUATION_LAB_002.json"
OUT_MD = ROOT / "GC_SHORT_SELL_PRESSURE_ACCEPTANCE_CONTINUATION_LAB_002.md"
OUT_EVENTS = ROOT / "GC_SHORT_SELL_PRESSURE_ACCEPTANCE_CONTINUATION_LAB_002_EVENTS.csv"

RITH_URL = "https://github.com/chepigga/ResearchOS/releases/download/GC/GC_RITHMIC_40D_003_GCZ6.zip"
AMP_URL = "https://github.com/chepigga/ResearchOS/releases/download/GC/AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip"
RITH_SHA = "b12465a783f36aac41b82a9f2a5c4e74bd2dcf7024ffc3636e8c41a8fd01e803"
AMP_SHA = "81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b"

TRAIN_END = pd.Timestamp("2026-08-20T00:00:00Z")
VALID_END = pd.Timestamp("2026-09-06T22:00:00Z")
LATE_END = pd.Timestamp("2026-09-11T12:46:00Z")
HORIZONS = (5, 15, 30)


def load_base():
    spec = importlib.util.spec_from_file_location("gc_edge003_lab002", BASE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def download(url: str, p: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "ResearchOS-GC-SHORT-LAB002/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, p.open("wb") as f:
        shutil.copyfileobj(r, f, 1024 * 1024)


def period(df: pd.DataFrame, label: str) -> pd.DataFrame:
    t = pd.to_datetime(df.signal_time, utc=True)
    if label == "TRAIN":
        return df[t < TRAIN_END]
    if label == "VALID":
        return df[(t >= TRAIN_END) & (t < VALID_END)]
    if label == "LATE_CHECK":
        return df[(t >= VALID_END) & (t <= LATE_END)]
    if label == "POST_CHECK":
        return df[t > LATE_END]
    if label == "FULL":
        return df
    raise ValueError(label)


def metric(df: pd.DataFrame, h: int) -> dict:
    c = f"fwd_{h}m_atr"
    v = df[c].dropna().to_numpy(float)
    if not len(v):
        return {"n": 0, "ev": None, "median": None, "wr": None, "days": 0, "positive_days": 0}
    tmp = df.dropna(subset=[c]).copy()
    tmp["day"] = pd.to_datetime(tmp.signal_time, utc=True).dt.date
    daily = tmp.groupby("day")[c].mean()
    return {
        "n": int(len(v)),
        "ev": float(v.mean()),
        "median": float(np.median(v)),
        "wr": float((v > 0).mean() * 100),
        "days": int(len(daily)),
        "positive_days": int((daily > 0).sum()),
    }


def summarize(df: pd.DataFrame) -> dict:
    return {
        p: {str(h): metric(period(df, p), h) for h in HORIZONS}
        for p in ("TRAIN", "VALID", "LATE_CHECK", "POST_CHECK", "FULL")
    }


def build_events(b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i in range(len(b) - 2):
        s = b.iloc[i]
        if not bool(s.a_sell):
            continue
        vals = [s.prior20_low, s.close_pos, s.impact, s.atr14]
        if not all(np.isfinite(float(x)) for x in vals):
            continue
        if not (
            float(s.low) <= float(s.prior20_low)
            and float(s.close) < float(s.prior20_low)
            and float(s.close_pos) <= 0.25
            and float(s.impact) > 0.0
        ):
            continue

        c = b.iloc[i + 1]
        e = b.iloc[i + 2]
        if c.time != s.time + pd.Timedelta(minutes=1):
            continue
        if e.time != c.time + pd.Timedelta(minutes=1):
            continue
        if not np.isfinite(float(c.delta_frac)) or not np.isfinite(float(c.close_pos)):
            continue
        if not (
            float(c.close) < float(s.prior20_low)
            and float(c.close_pos) <= 0.50
            and float(c.delta_frac) < 0.0
        ):
            continue

        atr = float(s.atr14)
        entry = float(e.open)
        row = {
            "feed": s.feed,
            "signal_time": s.time,
            "confirm_time": c.time,
            "entry_time": e.time,
            "side": "SHORT",
            "entry": entry,
            "seed_atr14": atr,
            "seed_prior20_low": float(s.prior20_low),
            "seed_delta_frac": float(s.delta_frac),
            "seed_sell_vol": float(s.sell_vol),
            "seed_body_atr": float(s.body_atr),
            "seed_range_atr": float(s.range_atr),
            "seed_close_pos": float(s.close_pos),
            "confirm_delta_frac": float(c.delta_frac),
            "confirm_close_pos": float(c.close_pos),
            "confirm_close_vs_level_atr": float((c.close - s.prior20_low) / atr),
        }
        for h in HORIZONS:
            j = i + 1 + h
            if j >= len(b):
                row[f"fwd_{h}m_atr"] = np.nan
                continue
            target = b.iloc[j]
            expected = e.time + pd.Timedelta(minutes=h - 1)
            if target.time != expected:
                row[f"fwd_{h}m_atr"] = np.nan
            else:
                row[f"fwd_{h}m_atr"] = float((entry - float(target.close)) / atr)
        rows.append(row)
    return pd.DataFrame(rows)


def ev(summary: dict, p: str, h: int):
    return summary[p][str(h)]["ev"]


def n(summary: dict, p: str, h: int):
    return summary[p][str(h)]["n"]


def make_gates(r: dict, a: dict) -> dict:
    late_n = n(r, "LATE_CHECK", 15)
    late_ok = True
    if late_n >= 3:
        late_ok = (ev(r, "LATE_CHECK", 15) is not None and ev(r, "LATE_CHECK", 15) > 0 and
                   ev(r, "LATE_CHECK", 30) is not None and ev(r, "LATE_CHECK", 30) > 0)
    checks = {
        "rithmic_full_n15_ge25": n(r, "FULL", 15) >= 25,
        "rithmic_train_n15_ge12": n(r, "TRAIN", 15) >= 12,
        "rithmic_valid_n15_ge8": n(r, "VALID", 15) >= 8,
        "rithmic_train_ev15_pos": ev(r, "TRAIN", 15) is not None and ev(r, "TRAIN", 15) > 0,
        "rithmic_train_ev30_pos": ev(r, "TRAIN", 30) is not None and ev(r, "TRAIN", 30) > 0,
        "rithmic_valid_ev15_pos": ev(r, "VALID", 15) is not None and ev(r, "VALID", 15) > 0,
        "rithmic_valid_ev30_pos": ev(r, "VALID", 30) is not None and ev(r, "VALID", 30) > 0,
        "rithmic_full_ev15_pos": ev(r, "FULL", 15) is not None and ev(r, "FULL", 15) > 0,
        "rithmic_full_ev30_pos": ev(r, "FULL", 30) is not None and ev(r, "FULL", 30) > 0,
        "rithmic_late_conditional_positive": late_ok,
        "amp_valid_ev15_pos": ev(a, "VALID", 15) is not None and ev(a, "VALID", 15) > 0,
        "amp_valid_ev30_pos": ev(a, "VALID", 30) is not None and ev(a, "VALID", 30) > 0,
    }
    checks["pass"] = all(checks.values())
    return checks


def fmt(x):
    return "NA" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:+.5f}"


def main():
    m = load_base()
    work = ROOT / "_short_lab002_work"
    work.mkdir(parents=True, exist_ok=True)
    rz = work / "rithmic.zip"
    az = work / "amp.zip"
    if not rz.exists():
        download(RITH_URL, rz)
    if not az.exists():
        download(AMP_URL, az)
    if m.sha(rz) != RITH_SHA or m.sha(az) != AMP_SHA:
        raise SystemExit("source SHA mismatch")

    rb = m.load_rithmic(rz)
    ab = m.load_amp(az)
    re = build_events(rb)
    ae = build_events(ab)
    rs = summarize(re)
    aas = summarize(ae)
    gates = make_gates(rs, aas)
    status = "HISTORICAL_SHORT_ACCEPTANCE_CANDIDATE_PASS_NOT_OOS" if gates["pass"] else "HISTORICAL_SHORT_ACCEPTANCE_REJECT_NOT_OOS"

    all_events = pd.concat([re, ae], ignore_index=True)
    all_events.to_csv(OUT_EVENTS, index=False)

    payload = {
        "lab": "GC_SHORT_SELL_PRESSURE_ACCEPTANCE_CONTINUATION_LAB_002",
        "status": status,
        "mechanism": "extreme sell pressure -> break/close below prior20 low -> next M1 accepts below -> SHORT at following M1 open",
        "rithmic": rs,
        "amp": aas,
        "gates": gates,
        "event_counts": {"rithmic": int(len(re)), "amp": int(len(ae))},
        "notes": [
            "Historical bounded discovery only; not independent OOS.",
            "No XAU execution tuning in this lab.",
            "AMP is supportive/feed-parity evidence, not independent market OOS.",
        ],
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# GC SHORT SELL-PRESSURE ACCEPTANCE CONTINUATION LAB002",
        "",
        f"**Status:** `{status}`",
        "",
        "Mechanism: `EXTREME SELL -> BREAK/CLOSE BELOW PRIOR20 LOW -> NEXT M1 ACCEPTS BELOW -> SHORT`.",
        "Historical bounded discovery only; not independent OOS. No XAU execution tuning here.",
        "",
        "## Key periods",
        "",
        "| Feed | Period | N15 | EV15 ATR | N30 | EV30 ATR |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for feed, s in (("RITHMIC", rs), ("AMP", aas)):
        for p in ("TRAIN", "VALID", "LATE_CHECK", "POST_CHECK", "FULL"):
            lines.append(f"| {feed} | {p} | {n(s,p,15)} | {fmt(ev(s,p,15))} | {n(s,p,30)} | {fmt(ev(s,p,30))} |")
    lines += ["", "## Frozen gates", ""]
    for k, v in gates.items():
        if k == "pass":
            continue
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "",
        "## Decision",
        "",
        ("Advance this exact GC SHORT mechanism to a separate GC->XAU transfer lab. Do not retune it before transfer testing."
         if gates["pass"] else
         "Reject this exact acceptance definition. Do not tune its thresholds post hoc; preregister a different bearish mechanism if SHORT research continues."),
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(status)
    print(json.dumps(gates, indent=2))


if __name__ == "__main__":
    main()
