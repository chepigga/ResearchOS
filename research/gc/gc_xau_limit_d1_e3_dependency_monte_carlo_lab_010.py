#!/usr/bin/env python3
"""GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("research/gc")
SRC = ROOT / "GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009_SEQUENCES.csv"
OUT_JSON = ROOT / "GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010.json"
OUT_MD = ROOT / "GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010.md"
OUT_DAY = ROOT / "GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010_DAYS.csv"
OUT_BOOT = ROOT / "GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010_BOOTSTRAP.csv"

CANDIDATE = "D1.00_E3M"
COST_R = 0.05
N_BOOT = 10000
SEED = 20260916
COHORTS = ("COMMON_CLOCK", "AMP_ALL")


def max_dd(v: np.ndarray) -> float:
    if len(v) == 0:
        return np.nan
    eq = np.cumsum(np.nan_to_num(v, nan=0.0))
    peaks = np.maximum.accumulate(np.r_[0.0, eq])
    return float((peaks[1:] - eq).max()) if len(eq) else 0.0


def load():
    d = pd.read_csv(SRC, low_memory=False)
    d["signal_time_utc"] = pd.to_datetime(d.signal_time_utc, utc=True)
    d["adj_r"] = pd.to_numeric(d.adj_r, errors="coerce").fillna(0.0)
    d = d[(d.candidate == CANDIDATE) & np.isclose(pd.to_numeric(d.cost_r, errors="coerce"), COST_R) & d.cohort.isin(COHORTS)].copy()
    d["day"] = d.signal_time_utc.dt.date.astype(str)
    d["week"] = d.signal_time_utc.dt.to_period("W-SUN").astype(str)
    return d.sort_values(["cohort", "signal_time_utc"]).reset_index(drop=True)


def bootstrap_days(z: pd.DataFrame, cohort: str):
    days = [g.sort_values("signal_time_utc").adj_r.to_numpy(float) for _, g in z.groupby("day", sort=True)]
    rng = np.random.default_rng(SEED + (0 if cohort == "COMMON_CLOCK" else 1))
    nday = len(days)
    out = np.empty((N_BOOT, 2), dtype=float)
    for i in range(N_BOOT):
        picks = rng.integers(0, nday, nday)
        path = np.concatenate([days[j] for j in picks])
        out[i, 0] = path.mean()
        out[i, 1] = max_dd(path)
    return out


def analyze(z: pd.DataFrame, cohort: str):
    vals = z.adj_r.to_numpy(float)
    day_sum = z.groupby("day", sort=True).adj_r.sum()
    day_n = z.groupby("day", sort=True).size()
    week_sum = z.groupby("week", sort=True).adj_r.sum()

    day_rows = []
    for d in day_sum.index:
        day_rows.append({"cohort": cohort, "day": d, "signals": int(day_n[d]), "sum_r": float(day_sum[d]), "ev_r": float(day_sum[d] / day_n[d])})

    loo_day = []
    for d in day_sum.index:
        x = z[z.day != d].adj_r.to_numpy(float)
        loo_day.append(float(x.mean()))
    loo_week = []
    for w in week_sum.index:
        x = z[z.week != w].adj_r.to_numpy(float)
        loo_week.append(float(x.mean()))

    pos_days = day_sum[day_sum > 0]
    pos_total = float(pos_days.sum())
    max_pos_share = float(pos_days.max() / pos_total) if len(pos_days) and pos_total > 0 else None

    boot = bootstrap_days(z, cohort)
    evb = boot[:, 0]
    ddb = boot[:, 1]
    summary = {
        "signals": int(len(z)),
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
    boot_df = pd.DataFrame({"cohort": cohort, "boot_id": np.arange(N_BOOT), "ev_r_per_signal": evb, "max_dd_r": ddb})
    return summary, day_rows, boot_df


def main():
    d = load()
    detail = {}
    all_days = []
    all_boot = []
    for cohort in COHORTS:
        s, dr, b = analyze(d[d.cohort == cohort].copy(), cohort)
        detail[cohort] = s
        all_days.extend(dr)
        all_boot.append(b)

    c = detail["COMMON_CLOCK"]
    a = detail["AMP_ALL"]
    gates = {
        "common_boot_p_ev_gt0_ge80pct": c["bootstrap_p_ev_gt_0"] >= 0.80,
        "amp_boot_p_ev_gt0_ge80pct": a["bootstrap_p_ev_gt_0"] >= 0.80,
        "common_loo_week_min_ev_pos": c["leave_one_week_out_min_ev"] > 0,
        "amp_loo_week_min_ev_pos": a["leave_one_week_out_min_ev"] > 0,
        "common_max_positive_day_share_lt50pct": c["max_positive_day_share"] is not None and c["max_positive_day_share"] < 0.50,
        "common_boot_p95_dd_050risk_lt5pct": c["bootstrap_dd_p95_pct_at_050risk"] < 5.0,
    }
    passed = all(gates.values())
    result = {
        "lab": "GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010",
        "status": "HISTORICAL_ROBUSTNESS_PASS_NOT_OOS" if passed else "HISTORICAL_ROBUSTNESS_FAIL_NOT_OOS",
        "frozen_candidate": {"candidate": CANDIDATE, "extra_cost_r_per_fill": COST_R},
        "detail": detail,
        "gates": gates,
        "governance": {"parameter_search": False, "independent_oos": False},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame(all_days).to_csv(OUT_DAY, index=False)
    pd.concat(all_boot, ignore_index=True).to_csv(OUT_BOOT, index=False)

    lines = [
        "# GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010",
        "",
        f"**Status: {result['status']}**",
        "",
        "Frozen candidate: **D1.00_E3M**, ONE_ACTIVE_SETUP, SL 1.5 ATR, TP 3R, timeout 30m, +0.05R adverse cost/fill.",
        "",
        "| Cohort | N | EV R/signal | Sum R | MaxDD R | P(EV>0) | Boot EV CI95 | LOO-week min EV | Max +day share | Boot DD p95 @0.5% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cohort in COHORTS:
        s = detail[cohort]
        lines.append(
            f"| {cohort} | {s['signals']} | {s['observed_ev_r_per_signal']:+.3f} | {s['observed_sum_r']:+.2f} | {s['observed_max_dd_r']:.2f} | {s['bootstrap_p_ev_gt_0']*100:.1f}% | [{s['bootstrap_ev_ci95'][0]:+.3f},{s['bootstrap_ev_ci95'][1]:+.3f}] | {s['leave_one_week_out_min_ev']:+.3f} | {s['max_positive_day_share']*100:.1f}% | {s['bootstrap_dd_p95_pct_at_050risk']:.2f}% |"
        )
    lines += ["", "## Gates", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", "## Governance", "", "This is a historical dependency/Monte-Carlo stress test on a post-discovery candidate. A PASS supports freezing for forward shadow; it does not convert the sample into independent OOS evidence."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "gates": gates}, indent=2))


if __name__ == "__main__":
    main()
