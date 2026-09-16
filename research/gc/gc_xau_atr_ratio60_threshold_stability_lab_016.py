#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
LAB015 = ROOT / "gc_xau_e3_preentry_failure_discriminator_lab_015.py"
OUT_JSON = ROOT / "GC_XAU_ATR_RATIO60_THRESHOLD_STABILITY_LAB_016.json"
OUT_MD = ROOT / "GC_XAU_ATR_RATIO60_THRESHOLD_STABILITY_LAB_016.md"
OUT_WEEK = ROOT / "GC_XAU_ATR_RATIO60_THRESHOLD_STABILITY_LAB_016_WEEKLY.csv"
OUT_GRID = ROOT / "GC_XAU_ATR_RATIO60_THRESHOLD_STABILITY_LAB_016_GRID.csv"

THRESHOLDS = (1.10, 1.13, 1.1657688284518744, 1.20, 1.23)
INCUMBENT = 1.1657688284518744
BASE_FULL_PF = 1.3799527829165632
BASE_FULL_EV_FILL = 0.23387120985174975
BASE_VALID_PF = 1.2595996954108832
BASE_VALID_EV_FILL = 0.17345979647909035
BASE_FULL_FILLS = 103
MIN_RETAINED_FILLS = 67


def load_lab015():
    spec = importlib.util.spec_from_file_location("lab015_mod", LAB015)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def weekly_stats(z: pd.DataFrame, thr: float) -> tuple[list[dict], float]:
    x = z.copy()
    x["week"] = x.signal_time_utc.dt.to_period("W-SUN").astype(str)
    rows = []
    weeks = sorted(x.week.unique())
    for w in weeks:
        q = x[x.week == w]
        rows.append({
            "threshold": thr,
            "week": w,
            "signals": int(len(q)),
            "accepted": int(q.accepted_corrected.sum()),
            "fills": int(q.active_fill.sum()),
            "sum_r": float(q.active_r.sum()),
            "ev_r_per_signal": float(q.active_r.mean()) if len(q) else None,
        })
    loo = []
    for w in weeks:
        q = x[x.week != w]
        loo.append(float(q.active_r.mean()) if len(q) else np.nan)
    return rows, float(np.nanmin(loo))


def main():
    m = load_lab015()
    d = m.attach_features(m.load_exec(), m.load_gc_features())
    baseline = m.simulate(d)
    bm = m.split_metrics(baseline)
    if bm["full"]["fills"] != 103 or abs(bm["full"]["ev_r_per_signal"] - 0.08633955059043093) > 1e-12:
        raise SystemExit(f"Baseline mismatch: {bm['full']}")

    grid_rows = []
    weekly_rows = []
    details = {}
    for thr in THRESHOLDS:
        veto = d["atr_ratio_60"].to_numpy(float) >= thr
        sim = m.simulate(d, veto)
        sm = m.split_metrics(sim)
        wr, loo_min = weekly_stats(sim, thr)
        weekly_rows.extend(wr)
        rec = {
            "threshold": thr,
            "full": sm["full"],
            "train": sm["train"],
            "valid": sm["valid"],
            "retained_fill_frac": sm["full"]["fills"] / BASE_FULL_FILLS,
            "loo_week_min_ev_signal": loo_min,
        }
        details[str(thr)] = rec
        grid_rows.append({
            "threshold": thr,
            "full_fills": sm["full"]["fills"],
            "retained_fill_frac": rec["retained_fill_frac"],
            "full_sum_r": sm["full"]["sum_r"],
            "full_ev_signal": sm["full"]["ev_r_per_signal"],
            "full_ev_fill": sm["full"]["ev_r_per_fill"],
            "full_pf": sm["full"]["pf"],
            "full_maxdd_r": sm["full"]["max_dd_r"],
            "train_fills": sm["train"]["fills"],
            "train_sum_r": sm["train"]["sum_r"],
            "train_ev_fill": sm["train"]["ev_r_per_fill"],
            "train_pf": sm["train"]["pf"],
            "valid_fills": sm["valid"]["fills"],
            "valid_sum_r": sm["valid"]["sum_r"],
            "valid_ev_fill": sm["valid"]["ev_r_per_fill"],
            "valid_pf": sm["valid"]["pf"],
            "loo_week_min_ev_signal": loo_min,
        })

    inc = details[str(INCUMBENT)]["full"]
    incumbent_reproduced = (
        inc["fills"] == 76
        and abs(inc["sum_r"] - 42.455943823874804) < 1e-12
        and abs(inc["ev_r_per_fill"] - 0.5586308397878266) < 1e-12
        and abs(inc["pf"] - 2.0267636851587336) < 1e-12
        and abs(inc["max_dd_r"] - 5.25) < 1e-12
    )

    count_full_pf = sum(details[str(t)]["full"]["pf"] > BASE_FULL_PF for t in THRESHOLDS)
    count_full_ev = sum(details[str(t)]["full"]["ev_r_per_fill"] > BASE_FULL_EV_FILL for t in THRESHOLDS)
    count_valid_pf = sum(details[str(t)]["valid"]["pf"] > BASE_VALID_PF for t in THRESHOLDS)
    count_valid_ev = sum(details[str(t)]["valid"]["ev_r_per_fill"] > BASE_VALID_EV_FILL for t in THRESHOLDS)
    count_retention = sum(details[str(t)]["full"]["fills"] >= MIN_RETAINED_FILLS for t in THRESHOLDS)
    inc_loo = details[str(INCUMBENT)]["loo_week_min_ev_signal"]

    gates = {
        "incumbent_exact_reproduction": incumbent_reproduced,
        "four_of_five_full_pf_above_baseline": count_full_pf >= 4,
        "four_of_five_full_evfill_above_baseline": count_full_ev >= 4,
        "four_of_five_valid_pf_above_baseline": count_valid_pf >= 4,
        "four_of_five_valid_evfill_above_baseline": count_valid_ev >= 4,
        "four_of_five_retain_ge65pct_fills": count_retention >= 4,
        "incumbent_loo_week_min_ev_positive": inc_loo > 0,
        "no_new_optimum_selected": True,
    }
    passed = all(gates.values())
    result = {
        "lab": "GC_XAU_ATR_RATIO60_THRESHOLD_STABILITY_LAB_016",
        "status": "THRESHOLD_NEIGHBORHOOD_STABLE_PASS_NOT_OOS" if passed else "THRESHOLD_FRAGILITY_FAIL_NOT_OOS",
        "baseline": bm,
        "frozen_thresholds": list(THRESHOLDS),
        "incumbent_threshold": INCUMBENT,
        "details": details,
        "counts": {
            "full_pf_above_baseline": count_full_pf,
            "full_evfill_above_baseline": count_full_ev,
            "valid_pf_above_baseline": count_valid_pf,
            "valid_evfill_above_baseline": count_valid_ev,
            "retain_ge65pct_fills": count_retention,
        },
        "gates": gates,
        "governance": {"new_market_data": False, "threshold_optimization": False, "independent_oos": False},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame(grid_rows).to_csv(OUT_GRID, index=False)
    pd.DataFrame(weekly_rows).to_csv(OUT_WEEK, index=False)

    lines = [
        "# GC_XAU_ATR_RATIO60_THRESHOLD_STABILITY_LAB_016",
        "",
        f"**Status: {result['status']}**",
        "",
        "Frozen grid only; no threshold optimization.",
        "",
        "| Thr | Fills | Retain | SumR | EV/fill | PF | MaxDD R | VALID fills | VALID SumR | VALID EV/fill | VALID PF | LOO-week min EV/signal |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in grid_rows:
        lines.append(
            f"| {r['threshold']:.5f} | {r['full_fills']} | {r['retained_fill_frac']*100:.1f}% | {r['full_sum_r']:+.3f} | {r['full_ev_fill']:+.3f} | {r['full_pf']:.3f} | {r['full_maxdd_r']:.3f} | {r['valid_fills']} | {r['valid_sum_r']:+.3f} | {r['valid_ev_fill']:+.3f} | {r['valid_pf']:.3f} | {r['loo_week_min_ev_signal']:+.4f} |"
        )
    lines += ["", "## Gates", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "",
        "## Governance",
        "",
        "LAB016 does not select a new best threshold. If the neighborhood passes, the LAB015 threshold 1.1657688284518744 remains frozen for subsequent research because it was selected before this stability audit.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "gates": gates, "counts": result["counts"]}, indent=2))


if __name__ == "__main__":
    main()
