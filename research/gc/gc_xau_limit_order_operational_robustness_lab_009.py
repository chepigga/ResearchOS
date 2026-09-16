#!/usr/bin/env python3
"""GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009

Operational robustness study on the four frozen LAB008 limit candidates.
No new signal/depth/expiry/exit parameter is searched.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
SRC = ROOT / "GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008_TRADES.csv"
OUT_JSON = ROOT / "GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009.json"
OUT_MD = ROOT / "GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009.md"
OUT_CSV = ROOT / "GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009_RESULTS.csv"
OUT_SEQ = ROOT / "GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009_SEQUENCES.csv"

CANDIDATES = {
    "D1.00_E3M": (1.00, 3),
    "D1.00_E5M": (1.00, 5),
    "D0.75_E3M": (0.75, 3),
    "D0.75_E5M": (0.75, 5),
}
COSTS_R = (0.00, 0.025, 0.05, 0.10)
MODES = ("ALL_SIGNALS", "ONE_ACTIVE_SETUP")
COHORTS = ("COMMON_CLOCK", "AMP_ALL")
CLOCK_OFFSET_MS = 180 * 60 * 1000
SPLIT = pd.Timestamp("2026-09-01T00:00:00Z")


def as_bool(s: pd.Series):
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def load_source():
    d = pd.read_csv(SRC, low_memory=False)
    d["signal_time_utc"] = pd.to_datetime(d.signal_time_utc, utc=True)
    d["filled"] = as_bool(d.filled)
    for c in ("depth_atr", "expiry_min", "fill_time_msc", "exit_time_msc", "r"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["candidate"] = ""
    for key, (depth, expiry) in CANDIDATES.items():
        m = np.isclose(d.depth_atr, depth) & d.expiry_min.eq(expiry)
        d.loc[m, "candidate"] = key
    d = d[d.candidate.ne("") & d.cohort.isin(COHORTS)].copy()
    return d.sort_values(["cohort", "candidate", "signal_time_utc"]).reset_index(drop=True)


def apply_mode(df: pd.DataFrame, mode: str):
    z = df.sort_values("signal_time_utc").copy()
    z["accepted"] = False
    z["busy_skip"] = False
    busy_until_utc_ms = -10**30
    for idx, row in z.iterrows():
        signal_utc_ms = int(row.signal_time_utc.value // 1_000_000)
        if mode == "ONE_ACTIVE_SETUP" and signal_utc_ms < busy_until_utc_ms:
            z.at[idx, "busy_skip"] = True
            continue
        z.at[idx, "accepted"] = True
        if mode == "ONE_ACTIVE_SETUP":
            if bool(row.filled) and np.isfinite(row.exit_time_msc):
                busy_until_utc_ms = int(row.exit_time_msc) - CLOCK_OFFSET_MS
            else:
                busy_until_utc_ms = signal_utc_ms + int(row.expiry_min) * 60_000
    return z


def pf(v: np.ndarray):
    p = float(v[v > 0].sum())
    n = float(-v[v < 0].sum())
    if n == 0:
        return float("inf") if p > 0 else np.nan
    return p / n


def max_dd(v: np.ndarray):
    if len(v) == 0:
        return np.nan
    eq = np.cumsum(np.nan_to_num(v, nan=0.0))
    peaks = np.maximum.accumulate(np.r_[0.0, eq])
    return float((peaks[1:] - eq).max()) if len(eq) else 0.0


def adjusted_sequence(z: pd.DataFrame, cost_r: float):
    r = np.zeros(len(z), dtype=float)
    valid = z.accepted & z.r.notna()
    r[valid.to_numpy()] = z.loc[valid, "r"].to_numpy(float)
    cost_mask = z.accepted & z.filled & z.r.notna()
    r[cost_mask.to_numpy()] -= cost_r
    return r


def summarize(z: pd.DataFrame, cost_r: float):
    rseq = adjusted_sequence(z, cost_r)
    accepted = z.accepted
    filled = z.accepted & z.filled & z.r.notna()
    fill_r = z.loc[filled, "r"].to_numpy(float) - cost_r

    tmp = z.copy()
    tmp["adj_r"] = rseq
    tmp["week"] = tmp.signal_time_utc.dt.to_period("W-SUN").astype(str)
    weekly = tmp.groupby("week", sort=True).adj_r.sum()

    closed = tmp[filled & tmp.exit_time_msc.notna()].copy()
    if len(closed):
        exit_utc_ms = closed.exit_time_msc.astype(np.int64) - CLOCK_OFFSET_MS
        closed["exit_day"] = pd.to_datetime(exit_utc_ms, unit="ms", utc=True).dt.date
        daily = closed.groupby("exit_day").adj_r.sum()
        worst_day = float(daily.min()) if len(daily) else 0.0
    else:
        worst_day = 0.0

    early = tmp[tmp.signal_time_utc < SPLIT].adj_r
    late = tmp[tmp.signal_time_utc >= SPLIT].adj_r
    return {
        "original_signals": int(len(tmp)),
        "accepted_signals": int(accepted.sum()),
        "accept_rate_pct": float(accepted.mean() * 100.0) if len(tmp) else None,
        "fills": int(filled.sum()),
        "fill_rate_original_pct": float(filled.sum() / len(tmp) * 100.0) if len(tmp) else None,
        "fill_rate_accepted_pct": float(filled.sum() / accepted.sum() * 100.0) if accepted.sum() else None,
        "ev_r_per_original_signal": float(rseq.mean()) if len(rseq) else None,
        "ev_r_per_accepted_signal": float(rseq.sum() / accepted.sum()) if accepted.sum() else None,
        "ev_r_per_fill": float(fill_r.mean()) if len(fill_r) else None,
        "pf": float(pf(rseq)) if len(rseq) else None,
        "max_dd_r": max_dd(rseq),
        "positive_weeks": int((weekly > 0).sum()),
        "weeks": int(len(weekly)),
        "positive_week_pct": float((weekly > 0).mean() * 100.0) if len(weekly) else None,
        "worst_closed_utc_day_r": worst_day,
        "early_ev_r_per_original_signal": float(early.mean()) if len(early) else None,
        "late_ev_r_per_original_signal": float(late.mean()) if len(late) else None,
        "dd_pct_at_025risk": max_dd(rseq) * 0.25,
        "dd_pct_at_050risk": max_dd(rseq) * 0.50,
        "worst_day_pct_at_025risk": worst_day * 0.25,
        "worst_day_pct_at_050risk": worst_day * 0.50,
    }, tmp


def main():
    src = load_source()
    rows = []
    seq_rows = []
    detail = {}
    for cohort in COHORTS:
        detail[cohort] = {}
        for cand in CANDIDATES:
            base = src[(src.cohort == cohort) & (src.candidate == cand)].copy()
            detail[cohort][cand] = {}
            for mode in MODES:
                mz = apply_mode(base, mode)
                detail[cohort][cand][mode] = {}
                for cost in COSTS_R:
                    s, seq = summarize(mz, cost)
                    ck = f"{cost:.3f}R"
                    detail[cohort][cand][mode][ck] = s
                    rows.append({"cohort": cohort, "candidate": cand, "mode": mode, "cost_r": cost, **s})
                    if mode == "ONE_ACTIVE_SETUP" and abs(cost - 0.05) < 1e-12:
                        q = seq[["signal_time_utc", "accepted", "busy_skip", "filled", "status", "r", "fill_time_msc", "exit_time_msc"]].copy()
                        q["cohort"] = cohort
                        q["candidate"] = cand
                        q["cost_r"] = cost
                        q["adj_r"] = adjusted_sequence(seq, cost)
                        seq_rows.append(q)

    res = pd.DataFrame(rows)
    res.to_csv(OUT_CSV, index=False)
    pd.concat(seq_rows, ignore_index=True).to_csv(OUT_SEQ, index=False)

    stable = []
    for cand in CANDIDATES:
        c = detail["COMMON_CLOCK"][cand]["ONE_ACTIVE_SETUP"]["0.050R"]
        a = detail["AMP_ALL"][cand]["ONE_ACTIVE_SETUP"]["0.050R"]
        gates = {
            "common_ev_pos": c["ev_r_per_original_signal"] > 0,
            "amp_ev_pos": a["ev_r_per_original_signal"] > 0,
            "common_late_ev_pos": c["late_ev_r_per_original_signal"] > 0,
            "common_pf_gt1": c["pf"] > 1.0,
            "common_fills_ge40": c["fills"] >= 40,
            "common_dd_050risk_lt5pct": c["dd_pct_at_050risk"] < 5.0,
            "common_worst_day_050risk_gt_minus4pct": c["worst_day_pct_at_050risk"] > -4.0,
        }
        if all(gates.values()):
            stable.append({"candidate": cand, "common": c, "amp": a, "gates": gates})
    stable.sort(key=lambda x: (x["common"]["ev_r_per_original_signal"], x["amp"]["ev_r_per_original_signal"]), reverse=True)
    selected = stable[0] if stable else None

    result = {
        "lab": "GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009",
        "status": "POST_DISCOVERY_OPERATIONAL_ROBUSTNESS_NOT_OOS",
        "candidates": CANDIDATES,
        "costs_r": COSTS_R,
        "modes": MODES,
        "primary_gate_cost_r": 0.05,
        "stable_candidates": stable,
        "selected_descriptive_candidate": selected,
        "detail": detail,
        "governance": {"new_limit_parameters_searched": False, "new_exit_parameters_searched": False, "independent_oos": False},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        "# GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009",
        "",
        "**Status: POST_DISCOVERY_OPERATIONAL_ROBUSTNESS_NOT_OOS**",
        "",
        "Primary operational mode: **ONE_ACTIVE_SETUP**. Primary cost stress: **+0.05R adverse cost per filled trade** on top of already embedded FTMO spread.",
        "",
        "| Candidate | Cohort | Accept | Fills | EV/orig | EV/fill | PF | MaxDD R | +weeks | LATE EV | DD @0.5% | Worst day @0.5% |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cand in CANDIDATES:
        for cohort in COHORTS:
            s = detail[cohort][cand]["ONE_ACTIVE_SETUP"]["0.050R"]
            lines.append(
                f"| {cand} | {cohort} | {s['accept_rate_pct']:.1f}% | {s['fills']} | {s['ev_r_per_original_signal']:+.3f} | {s['ev_r_per_fill']:+.3f} | {s['pf']:.2f} | {s['max_dd_r']:.2f} | {s['positive_weeks']}/{s['weeks']} | {s['late_ev_r_per_original_signal']:+.3f} | {s['dd_pct_at_050risk']:.2f}% | {s['worst_day_pct_at_050risk']:+.2f}% |"
            )
    lines += ["", "## Cost stress — COMMON_CLOCK / ONE_ACTIVE_SETUP", "", "| Candidate | 0R | 0.025R | 0.05R | 0.10R |", "|---|---:|---:|---:|---:|"]
    for cand in CANDIDATES:
        vals = []
        for cost in COSTS_R:
            s = detail["COMMON_CLOCK"][cand]["ONE_ACTIVE_SETUP"][f"{cost:.3f}R"]
            vals.append(s["ev_r_per_original_signal"])
        lines.append(f"| {cand} | {vals[0]:+.3f} | {vals[1]:+.3f} | {vals[2]:+.3f} | {vals[3]:+.3f} |")
    lines += ["", "## Robustness gate", ""]
    if stable:
        for x in stable:
            c = x["common"]
            lines.append(f"- **{x['candidate']} PASS** — COMMON EV {c['ev_r_per_original_signal']:+.3f}R/original signal, PF {c['pf']:.2f}, DD@0.5% {c['dd_pct_at_050risk']:.2f}%.")
        lines += ["", f"Descriptive operational leader: **{selected['candidate']}**."]
    else:
        lines.append("No candidate passed all preregistered operational robustness gates.")
    lines += ["", "## Governance", "", "This remains post-discovery. A passing operational candidate can be frozen for forward/OOS shadow testing, but LAB009 itself cannot certify production profitability."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "stable": [x["candidate"] for x in stable], "selected": None if selected is None else selected["candidate"]}, indent=2))


if __name__ == "__main__":
    main()
