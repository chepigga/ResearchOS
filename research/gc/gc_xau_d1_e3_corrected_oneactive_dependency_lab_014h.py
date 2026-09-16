#!/usr/bin/env python3
"""LAB014H — corrected D1/E3 one-active dependency/Monte-Carlo audit.

Historical defect-correction audit only. No signal/execution parameter search.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
SRC = ROOT / "GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009_SEQUENCES.csv"
LAB010 = ROOT / "GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010.json"
OUT_JSON = ROOT / "GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H.json"
OUT_MD = ROOT / "GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H.md"
OUT_SEQ = ROOT / "GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H_SEQUENCES.csv"
OUT_BOOT = ROOT / "GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H_BOOTSTRAP.csv"

CANDIDATE = "D1.00_E3M"
COST_R = 0.05
BROKER_OFFSET_MS = 180 * 60_000
ORDER_START_DELAY_MS = 60_000
EXPIRY_MS = 3 * 60_000
N_BOOT = 10_000
SEED = 20260916
COHORTS = ("COMMON_CLOCK", "AMP_ALL")


def max_dd(v: np.ndarray) -> float:
    if len(v) == 0:
        return np.nan
    eq = np.cumsum(np.nan_to_num(v, nan=0.0))
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    return float((peak[1:] - eq).max()) if len(eq) else 0.0


def load_source() -> pd.DataFrame:
    d = pd.read_csv(SRC, low_memory=False)
    d = d[(d.candidate == CANDIDATE) & d.cohort.isin(COHORTS) & np.isclose(pd.to_numeric(d.cost_r, errors="coerce"), COST_R)].copy()
    d["signal_time_utc"] = pd.to_datetime(d.signal_time_utc, utc=True)
    d["r"] = pd.to_numeric(d.r, errors="coerce").fillna(0.0)
    d["fill_time_msc"] = pd.to_numeric(d.fill_time_msc, errors="coerce")
    d["exit_time_msc"] = pd.to_numeric(d.exit_time_msc, errors="coerce")
    d["filled"] = d.filled.astype(str).str.lower().eq("true") if d.filled.dtype == object else d.filled.astype(bool)
    return d.sort_values(["cohort", "signal_time_utc"], kind="mergesort").reset_index(drop=True)


def corrected_one_active(z: pd.DataFrame) -> pd.DataFrame:
    q = z.sort_values("signal_time_utc", kind="mergesort").copy().reset_index(drop=True)
    q["accepted_corrected"] = False
    q["busy_skip_corrected"] = False
    q["adj_r_corrected"] = 0.0
    q["busy_until_utc_ms"] = np.nan
    busy_until = -10**30
    for i, r in q.iterrows():
        signal_ms = int(pd.Timestamp(r.signal_time_utc).value // 1_000_000)
        if signal_ms < busy_until:
            q.at[i, "busy_skip_corrected"] = True
            q.at[i, "busy_until_utc_ms"] = busy_until
            continue
        q.at[i, "accepted_corrected"] = True
        if bool(r.filled) and np.isfinite(r.exit_time_msc):
            busy_until = int(r.exit_time_msc) - BROKER_OFFSET_MS
            q.at[i, "adj_r_corrected"] = float(r.r) - COST_R
        else:
            busy_until = signal_ms + ORDER_START_DELAY_MS + EXPIRY_MS
            q.at[i, "adj_r_corrected"] = 0.0
        q.at[i, "busy_until_utc_ms"] = busy_until
    q["day"] = q.signal_time_utc.dt.date.astype(str)
    q["week"] = q.signal_time_utc.dt.to_period("W-SUN").astype(str)
    return q


def bootstrap_days(z: pd.DataFrame, cohort: str):
    days = [g.sort_values("signal_time_utc").adj_r_corrected.to_numpy(float) for _, g in z.groupby("day", sort=True)]
    rng = np.random.default_rng(SEED + (0 if cohort == "COMMON_CLOCK" else 1))
    nday = len(days)
    out = np.empty((N_BOOT, 2), float)
    for i in range(N_BOOT):
        picks = rng.integers(0, nday, nday)
        path = np.concatenate([days[j] for j in picks])
        out[i, 0] = float(path.mean())
        out[i, 1] = max_dd(path)
    return out


def analyze(z: pd.DataFrame, cohort: str):
    vals = z.adj_r_corrected.to_numpy(float)
    day_sum = z.groupby("day", sort=True).adj_r_corrected.sum()
    week_sum = z.groupby("week", sort=True).adj_r_corrected.sum()

    loo_day = [float(z[z.day != d].adj_r_corrected.mean()) for d in day_sum.index]
    loo_week = [float(z[z.week != w].adj_r_corrected.mean()) for w in week_sum.index]
    pos_days = day_sum[day_sum > 0]
    pos_total = float(pos_days.sum())
    max_pos_share = float(pos_days.max() / pos_total) if len(pos_days) and pos_total > 0 else None

    boot = bootstrap_days(z, cohort)
    evb, ddb = boot[:, 0], boot[:, 1]
    summary = {
        "signals": int(len(z)),
        "accepted_signals": int(z.accepted_corrected.sum()),
        "busy_skips": int(z.busy_skip_corrected.sum()),
        "accepted_fills": int((z.accepted_corrected & z.filled).sum()),
        "observed_ev_r_per_signal": float(vals.mean()),
        "observed_sum_r": float(vals.sum()),
        "observed_max_dd_r": max_dd(vals),
        "days": int(len(day_sum)),
        "weeks": int(len(week_sum)),
        "positive_days": int((day_sum > 0).sum()),
        "positive_weeks": int((week_sum > 0).sum()),
        "max_positive_day_share": max_pos_share,
        "leave_one_day_out_min_ev": float(min(loo_day)),
        "leave_one_day_out_max_ev": float(max(loo_day)),
        "leave_one_week_out_min_ev": float(min(loo_week)),
        "leave_one_week_out_max_ev": float(max(loo_week)),
        "bootstrap_p_ev_gt_0": float((evb > 0).mean()),
        "bootstrap_ev_median": float(np.median(evb)),
        "bootstrap_ev_ci95": [float(np.quantile(evb, 0.025)), float(np.quantile(evb, 0.975))],
        "bootstrap_dd_median_r": float(np.median(ddb)),
        "bootstrap_dd_p95_r": float(np.quantile(ddb, 0.95)),
        "bootstrap_dd_p99_r": float(np.quantile(ddb, 0.99)),
        "bootstrap_dd_p95_pct_at_025risk": float(np.quantile(ddb, 0.95) * 0.25),
        "bootstrap_dd_p95_pct_at_050risk": float(np.quantile(ddb, 0.95) * 0.50),
    }
    bdf = pd.DataFrame({"cohort": cohort, "boot_id": np.arange(N_BOOT), "ev_r_per_signal": evb, "max_dd_r": ddb})
    return summary, bdf


def main():
    d = load_source()
    corrected = []
    detail = {}
    boots = []
    for cohort in COHORTS:
        z = corrected_one_active(d[d.cohort == cohort].copy())
        corrected.append(z)
        s, b = analyze(z, cohort)
        detail[cohort] = s
        boots.append(b)

    allseq = pd.concat(corrected, ignore_index=True)
    allseq.to_csv(OUT_SEQ, index=False)
    pd.concat(boots, ignore_index=True).to_csv(OUT_BOOT, index=False)

    old = json.loads(LAB010.read_text(encoding="utf-8"))["detail"]
    delta_vs_lab010 = {}
    for cohort in COHORTS:
        delta_vs_lab010[cohort] = {}
        for k in ("observed_ev_r_per_signal", "observed_sum_r", "observed_max_dd_r", "bootstrap_p_ev_gt_0", "leave_one_week_out_min_ev", "max_positive_day_share", "bootstrap_dd_p95_r", "bootstrap_dd_p95_pct_at_025risk", "bootstrap_dd_p95_pct_at_050risk"):
            delta_vs_lab010[cohort][k] = float(detail[cohort][k] - old[cohort][k])

    c, a = detail["COMMON_CLOCK"], detail["AMP_ALL"]
    gates = {
        "common_boot_p_ev_gt0_ge80pct": c["bootstrap_p_ev_gt_0"] >= 0.80,
        "amp_boot_p_ev_gt0_ge80pct": a["bootstrap_p_ev_gt_0"] >= 0.80,
        "common_loo_week_min_ev_pos": c["leave_one_week_out_min_ev"] > 0,
        "amp_loo_week_min_ev_pos": a["leave_one_week_out_min_ev"] > 0,
        "common_max_positive_day_share_lt50pct": c["max_positive_day_share"] is not None and c["max_positive_day_share"] < 0.50,
        "common_boot_p95_dd_025risk_lt5pct": c["bootstrap_dd_p95_pct_at_025risk"] < 5.0,
        "amp_boot_p95_dd_025risk_lt5pct": a["bootstrap_dd_p95_pct_at_025risk"] < 5.0,
    }
    diagnostic_050 = {
        "common_boot_p95_dd_050risk_lt5pct": c["bootstrap_dd_p95_pct_at_050risk"] < 5.0,
        "amp_boot_p95_dd_050risk_lt5pct": a["bootstrap_dd_p95_pct_at_050risk"] < 5.0,
    }
    passed = all(gates.values())
    result = {
        "lab": "GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H",
        "status": "CORRECTED_HISTORICAL_ROBUSTNESS_PASS_NOT_OOS" if passed else "CORRECTED_HISTORICAL_ROBUSTNESS_FAIL_NOT_OOS",
        "candidate": {"sensor": "BUYER_BREAKOUT_LONG_001", "execution": "D1.00_E3M", "cost_r_per_fill": COST_R, "one_active_clock": "order_start_plus_expiry_for_unfilled"},
        "detail": detail,
        "delta_vs_frozen_lab010": delta_vs_lab010,
        "gates": gates,
        "diagnostic_050risk": diagnostic_050,
        "governance": {"parameter_search": False, "new_market_data": False, "independent_oos": False, "defect_correction_only": True},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H",
        "",
        f"**Status: {result['status']}**",
        "",
        "Uses the already-collected LAB009 sequence only. The sole change is the corrected unfilled one-active clock: `order_start + 3m` instead of `signal-bar left edge + 3m`.",
        "",
        "| Cohort | N | Accepted | Fills | EV R/signal | Sum R | MaxDD R | P(EV>0) | EV CI95 | LOO-week min EV | +day share | DD p95 @0.25% | DD p95 @0.50% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cohort in COHORTS:
        s = detail[cohort]
        lines.append(
            f"| {cohort} | {s['signals']} | {s['accepted_signals']} | {s['accepted_fills']} | {s['observed_ev_r_per_signal']:+.5f} | {s['observed_sum_r']:+.2f} | {s['observed_max_dd_r']:.2f} | {s['bootstrap_p_ev_gt_0']*100:.2f}% | [{s['bootstrap_ev_ci95'][0]:+.4f},{s['bootstrap_ev_ci95'][1]:+.4f}] | {s['leave_one_week_out_min_ev']:+.5f} | {s['max_positive_day_share']*100:.1f}% | {s['bootstrap_dd_p95_pct_at_025risk']:.3f}% | {s['bootstrap_dd_p95_pct_at_050risk']:.3f}% |"
        )
    lines += ["", "## Gates @ 0.25% research risk", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", "## 0.50% diagnostic", ""]
    for k, v in diagnostic_050.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", "## Delta vs frozen LAB010", ""]
    for cohort in COHORTS:
        x = delta_vs_lab010[cohort]
        lines.append(f"- **{cohort}**: ΔEV {x['observed_ev_r_per_signal']:+.6f}R/signal; ΔSum {x['observed_sum_r']:+.3f}R; ΔMaxDD {x['observed_max_dd_r']:+.3f}R; Δboot p95 DD@0.25% {x['bootstrap_dd_p95_pct_at_025risk']:+.3f} pp.")
    lines += ["", "This is a corrected historical robustness audit, not independent OOS certification."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "detail": detail, "gates": gates, "diagnostic_050risk": diagnostic_050}, indent=2))


if __name__ == "__main__":
    main()
