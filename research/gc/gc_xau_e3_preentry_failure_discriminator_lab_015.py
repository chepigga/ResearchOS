#!/usr/bin/env python3
"""GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015

Bounded causal pre-entry failure-discriminator research on frozen existing data.
No new market data, no retuning of the baseline signal/execution geometry.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
AMP_ZIP = ROOT / "_lab015" / "amp_gc.zip"
BASE = ROOT / "gc_m1_orderflow_edge_discovery_003.py"
EXEC = ROOT / "GC_XAU_EXISTING_DATA_FULL_REPLAY_AUDIT_LAB_013H_E1_E3.csv"
OUT_JSON = ROOT / "GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015.json"
OUT_MD = ROOT / "GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015.md"
OUT_FEATURES = ROOT / "GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015_FEATURES.csv"
OUT_VETOES = ROOT / "GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015_VETOES.csv"
OUT_TRADES = ROOT / "GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015_SELECTED_TRADES.csv"

CLOCK_OFFSET_MS = 180 * 60_000
EXPIRY_MIN = 3
SPLIT = pd.Timestamp("2026-09-01T00:00:00Z")
QLEVELS = (0.20, 0.25, 0.33, 0.67, 0.75, 0.80)
FEATURES = (
    "delta_excess",
    "buy_q75_ratio",
    "close_pos",
    "body_atr",
    "breakout_atr",
    "range_atr",
    "atr_ratio_60",
)


def load_base():
    spec = importlib.util.spec_from_file_location("edge003_lab015", BASE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def load_gc_features() -> pd.DataFrame:
    m = load_base()
    b = m.load_amp(AMP_ZIP).copy().sort_values("time").reset_index(drop=True)
    prior_atr_med60 = b.atr14.shift(1).rolling(60, min_periods=30).median()
    b["delta_excess"] = b.delta_frac - b.q90_delta
    b["buy_q75_ratio"] = b.buy_vol / b.q75_buy.replace(0, np.nan)
    b["breakout_atr"] = (b.high - b.prior20_high) / b.atr14
    b["range_atr"] = (b.high - b.low) / b.atr14
    b["atr_ratio_60"] = b.atr14 / prior_atr_med60
    hour = b.time.dt.hour + b.time.dt.minute / 60.0
    b["utc_hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    b["utc_hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    return b[["time", *FEATURES, "utc_hour_sin", "utc_hour_cos"]].rename(columns={"time": "signal_time_utc"})


def load_exec() -> pd.DataFrame:
    d = pd.read_csv(EXEC, low_memory=False)
    d = d[d.candidate.eq("D1.00_E3M")].copy()
    d["signal_time_utc"] = pd.to_datetime(d.signal_time_utc, utc=True)
    for c in ("fill_time_msc", "exit_time_msc", "raw_r", "stress_r"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["filled"] = d.filled.astype(str).str.lower().isin(["true", "1", "yes"])
    return d.sort_values("signal_time_utc").reset_index(drop=True)


def attach_features(d: pd.DataFrame, f: pd.DataFrame) -> pd.DataFrame:
    z = d.merge(f, on="signal_time_utc", how="left", validate="one_to_one")
    missing = z[list(FEATURES)].isna().any(axis=1)
    if int(missing.sum()):
        raise SystemExit(f"Missing causal features for {int(missing.sum())} E3 signal rows")
    return z


def pf(v: np.ndarray) -> float:
    pos = float(v[v > 0].sum()); neg = float(-v[v < 0].sum())
    if neg == 0:
        return float("inf") if pos > 0 else np.nan
    return pos / neg


def max_dd(v: np.ndarray) -> float:
    if len(v) == 0:
        return np.nan
    eq = np.cumsum(np.nan_to_num(v, nan=0.0))
    peaks = np.maximum.accumulate(np.r_[0.0, eq])
    return float((peaks[1:] - eq).max()) if len(eq) else 0.0


def simulate(d: pd.DataFrame, veto_mask: np.ndarray | None = None) -> pd.DataFrame:
    z = d.sort_values("signal_time_utc").copy().reset_index(drop=True)
    veto_mask = np.zeros(len(z), dtype=bool) if veto_mask is None else np.asarray(veto_mask, dtype=bool)
    if len(veto_mask) != len(z): raise ValueError("veto mask length mismatch")
    z["veto"] = veto_mask; z["accepted_corrected"] = False; z["busy_skip_corrected"] = False
    busy_until_utc_ms = -10**30
    for i, row in z.iterrows():
        sig_ms = int(pd.Timestamp(row.signal_time_utc).value // 1_000_000)
        if bool(z.at[i, "veto"]): continue
        if sig_ms < busy_until_utc_ms:
            z.at[i, "busy_skip_corrected"] = True; continue
        z.at[i, "accepted_corrected"] = True
        if bool(row.filled) and np.isfinite(row.exit_time_msc):
            busy_until_utc_ms = int(row.exit_time_msc) - CLOCK_OFFSET_MS
        else:
            busy_until_utc_ms = sig_ms + 60_000 + EXPIRY_MIN * 60_000
    z["active_fill"] = z.accepted_corrected & z.filled & z.stress_r.notna()
    z["active_r"] = np.where(z.active_fill, z.stress_r, 0.0)
    return z


def metrics(z: pd.DataFrame) -> dict:
    vals = z.active_r.to_numpy(float); fills = z[z.active_fill].copy(); fv = fills.stress_r.to_numpy(float)
    return {
        "signals": int(len(z)), "accepted": int(z.accepted_corrected.sum()), "fills": int(len(fills)),
        "sum_r": float(vals.sum()), "ev_r_per_signal": float(vals.mean()) if len(vals) else None,
        "ev_r_per_fill": float(fv.mean()) if len(fv) else None, "pf": float(pf(fv)) if len(fv) else None,
        "max_dd_r": max_dd(vals), "fail_fills": int((fv < 0).sum()), "good_fills": int((fv > 0).sum()),
    }


def split_metrics(z: pd.DataFrame) -> dict:
    return {"full": metrics(z), "train": metrics(z[z.signal_time_utc < SPLIT].copy()), "valid": metrics(z[z.signal_time_utc >= SPLIT].copy())}


def rank_auc(y: np.ndarray, score: np.ndarray) -> float | None:
    mask = np.isfinite(score); y = y[mask].astype(int); score = score[mask]
    n1 = int((y == 1).sum()); n0 = int((y == 0).sum())
    if n1 == 0 or n0 == 0: return None
    ranks = pd.Series(score).rank(method="average").to_numpy(float)
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def fill_feature_diag(base: pd.DataFrame, feature: str) -> dict:
    out = {}
    for name, mask in (("train", base.signal_time_utc < SPLIT), ("valid", base.signal_time_utc >= SPLIT)):
        q = base[mask & base.active_fill].copy(); q = q[np.isfinite(q[feature]) & q.stress_r.ne(0)].copy()
        y = q.stress_r.lt(0).astype(int).to_numpy(); s = q[feature].to_numpy(float); auc = rank_auc(y, s)
        fail = q[q.stress_r < 0][feature]; good = q[q.stress_r > 0][feature]
        out[name] = {"n": int(len(q)), "fail_n": int(len(fail)), "good_n": int(len(good)),
                     "fail_median": float(fail.median()) if len(fail) else None, "good_median": float(good.median()) if len(good) else None,
                     "auc_fail_high": auc, "auc_direction_free": None if auc is None else float(max(auc, 1 - auc))}
    return out


def choose_single_feature(d: pd.DataFrame, baseline: pd.DataFrame, feature: str):
    train_fills = baseline[(baseline.signal_time_utc < SPLIT) & baseline.active_fill].copy(); vals = train_fills[feature].dropna(); rows = []
    if len(vals) < 20: return None, rows
    base_train = metrics(baseline[baseline.signal_time_utc < SPLIT].copy()); base_valid = metrics(baseline[baseline.signal_time_utc >= SPLIT].copy())
    thresholds = sorted(set(float(vals.quantile(q)) for q in QLEVELS))
    for thr in thresholds:
        for side in ("LOW", "HIGH"):
            veto = (d[feature].to_numpy(float) <= thr) if side == "LOW" else (d[feature].to_numpy(float) >= thr)
            sm = split_metrics(simulate(d, veto)); tr = sm["train"]; va = sm["valid"]
            removed_frac = 1.0 - (tr["fills"] / base_train["fills"] if base_train["fills"] else 0.0)
            eligible = (0.10 <= removed_frac <= 0.40 and tr["fills"] >= 30 and tr["ev_r_per_fill"] > base_train["ev_r_per_fill"] and tr["pf"] > base_train["pf"])
            rows.append({"feature": feature, "side": side, "threshold": thr, "eligible_train": bool(eligible),
                         "train_removed_fill_frac": float(removed_frac), "train_sum_r_delta": float(tr["sum_r"] - base_train["sum_r"]),
                         "train_ev_fill_delta": float(tr["ev_r_per_fill"] - base_train["ev_r_per_fill"]), "train_pf_delta": float(tr["pf"] - base_train["pf"]),
                         "valid_sum_r_delta": float(va["sum_r"] - base_valid["sum_r"]), "valid_ev_fill_delta": float(va["ev_r_per_fill"] - base_valid["ev_r_per_fill"]),
                         "valid_pf_delta": float(va["pf"] - base_valid["pf"]), "metrics": sm})
    eligible_rows = [r for r in rows if r["eligible_train"]]
    if not eligible_rows: return None, rows
    eligible_rows.sort(key=lambda r: (r["train_sum_r_delta"], r["train_ev_fill_delta"], r["train_pf_delta"]), reverse=True)
    return eligible_rows[0], rows


def veto_from_rule(d: pd.DataFrame, rule: dict) -> np.ndarray:
    x = d[rule["feature"]].to_numpy(float)
    return x <= rule["threshold"] if rule["side"] == "LOW" else x >= rule["threshold"]


def trade_composition(z: pd.DataFrame) -> dict:
    q = z[z.veto & z.filled].copy()
    return {"vetoed_raw_fill_rows": int(len(q)), "sl": int(q.status.eq("SL").sum()), "tp": int(q.status.eq("TP").sum()),
            "negative_timeout": int((q.status.eq("TIMEOUT") & q.stress_r.lt(0)).sum()), "positive_timeout": int((q.status.eq("TIMEOUT") & q.stress_r.gt(0)).sum())}


def promotion_gates(cm: dict, bm: dict) -> dict:
    return {
        "train_retained_fills_ge30": cm["train"]["fills"] >= 30,
        "valid_retained_fills_ge15": cm["valid"]["fills"] >= 15,
        "train_ev_fill_improves": cm["train"]["ev_r_per_fill"] > bm["train"]["ev_r_per_fill"],
        "train_pf_improves": cm["train"]["pf"] > bm["train"]["pf"],
        "valid_ev_fill_improves": cm["valid"]["ev_r_per_fill"] > bm["valid"]["ev_r_per_fill"],
        "valid_pf_improves": cm["valid"]["pf"] > bm["valid"]["pf"],
        "valid_sum_r_ge80pct_baseline": cm["valid"]["sum_r"] >= 0.80 * bm["valid"]["sum_r"],
        "full_dd_improve10pct_or_pf_plus015": (cm["full"]["max_dd_r"] <= 0.90 * bm["full"]["max_dd_r"]) or (cm["full"]["pf"] >= bm["full"]["pf"] + 0.15),
        "full_retained_fills_ge65pct": cm["full"]["fills"] >= math.ceil(0.65 * bm["full"]["fills"]),
        "causal_features_only": True,
    }


def summarize_challenger(kind: str, rules: list[dict], sim: pd.DataFrame, bm: dict) -> dict:
    cm = split_metrics(sim); gates = promotion_gates(cm, bm)
    return {"kind": kind, "rules": [{k: r[k] for k in ("feature", "side", "threshold", "train_removed_fill_frac")} for r in rules],
            "metrics": cm, "composition": trade_composition(sim), "gates": gates, "passed": all(gates.values())}


def main():
    d = attach_features(load_exec(), load_gc_features()); baseline = simulate(d); bm = split_metrics(baseline)
    if bm["full"]["accepted"] != 237 or bm["full"]["fills"] != 103: raise SystemExit(f"Corrected baseline mismatch: {bm['full']}")
    if abs(bm["full"]["ev_r_per_signal"] - 0.08633955059043093) > 1e-12: raise SystemExit("Corrected baseline EV mismatch")

    feature_diag = {f: fill_feature_diag(baseline, f) for f in FEATURES}; selected_singles = {}; all_veto_rows = []
    for f in FEATURES:
        best, rows = choose_single_feature(d, baseline, f); selected_singles[f] = best
        for r in rows:
            flat = {k: v for k, v in r.items() if k != "metrics"}; flat.update({f"{p}_{k}": v for p, md in r["metrics"].items() for k, v in md.items()}); all_veto_rows.append(flat)

    candidates = [x for x in selected_singles.values() if x is not None]
    candidates.sort(key=lambda r: (r["train_sum_r_delta"], r["train_ev_fill_delta"], r["train_pf_delta"]), reverse=True)
    top = candidates[:2]

    primary_single = None
    if top:
        ssim = simulate(d, veto_from_rule(d, top[0])); primary_single = summarize_challenger("TOP_SINGLE", [top[0]], ssim, bm)

    composite_pool = []
    if len(top) == 2:
        va = veto_from_rule(d, top[0]); vb = veto_from_rule(d, top[1])
        for kind, v in (("OR", va | vb), ("2OF2", va & vb)):
            sim = simulate(d, v); sm = split_metrics(sim)
            composite_pool.append({"kind": kind, "rules": top, "sim": sim, "metrics": sm})
    composite_summary = None
    if composite_pool:
        composite_pool.sort(key=lambda c: (c["metrics"]["train"]["sum_r"], c["metrics"]["train"]["pf"], c["metrics"]["train"]["ev_r_per_fill"]), reverse=True)
        c = composite_pool[0]; composite_summary = summarize_challenger(c["kind"], c["rules"], c["sim"], bm)

    # Governance: the top single is frozen by TRAIN ranking independently of the composite screen.
    # Composite failure cannot erase a passing top-single challenger.
    passing = [x for x in (primary_single, composite_summary) if x is not None and x["passed"]]
    passed = bool(passing)
    selected_for_research = primary_single if primary_single and primary_single["passed"] else (passing[0] if passing else None)
    if selected_for_research:
        v = np.zeros(len(d), dtype=bool)
        if selected_for_research["kind"] == "TOP_SINGLE":
            v = veto_from_rule(d, top[0])
        elif selected_for_research["kind"] == "OR":
            v = veto_from_rule(d, top[0]) | veto_from_rule(d, top[1])
        else:
            v = veto_from_rule(d, top[0]) & veto_from_rule(d, top[1])
        simulate(d, v).to_csv(OUT_TRADES, index=False)
    else:
        baseline.to_csv(OUT_TRADES, index=False)

    result = {
        "lab": "GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015",
        "status": "CAUSAL_PREENTRY_VETO_CHALLENGER_PASS_NOT_OOS" if passed else "NO_CAUSAL_PREENTRY_VETO_PROMOTED",
        "baseline": bm, "feature_diagnostics": feature_diag, "selected_single_feature_rules": selected_singles,
        "train_selected_top_two": [{k: r[k] for k in ("feature", "side", "threshold", "train_sum_r_delta", "train_ev_fill_delta", "train_pf_delta")} for r in top],
        "primary_train_selected_single": primary_single, "train_selected_composite": composite_summary,
        "selected_for_research": selected_for_research,
        "governance": {"new_market_data": False, "baseline_retuned": False, "independent_oos": False, "post_entry_features_used": False,
                       "selection_fix": "Top TRAIN-ranked single and TRAIN-ranked composite are independent preregistered challenger classes; composite failure does not erase a passing top single."},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    feat_rows = []
    for f, dg in feature_diag.items():
        for p, x in dg.items(): feat_rows.append({"feature": f, "period": p, **x})
    pd.DataFrame(feat_rows).to_csv(OUT_FEATURES, index=False); pd.DataFrame(all_veto_rows).to_csv(OUT_VETOES, index=False)

    lines = ["# GC_XAU_E3_PREENTRY_FAILURE_DISCRIMINATOR_LAB_015", "", f"**Status: {result['status']}**", "",
             "Existing frozen AMP GC + LAB013H E3 outcomes only. Baseline geometry unchanged; every veto is replayed through corrected one-active state.", "",
             "## Corrected E3 baseline", "", "| Period | Fills | Sum R | EV/fill | PF | MaxDD R |", "|---|---:|---:|---:|---:|---:|"]
    for p in ("train", "valid", "full"):
        x = bm[p]; lines.append(f"| {p.upper()} | {x['fills']} | {x['sum_r']:+.3f} | {x['ev_r_per_fill']:+.3f} | {x['pf']:.3f} | {x['max_dd_r']:.3f} |")
    lines += ["", "## Pre-entry feature separation", "", "| Feature | TRAIN fail/good median | TRAIN AUC* | VALID fail/good median | VALID AUC* |", "|---|---:|---:|---:|---:|"]
    for f in FEATURES:
        tr = feature_diag[f]["train"]; va = feature_diag[f]["valid"]
        lines.append(f"| {f} | {tr['fail_median']:+.4f} / {tr['good_median']:+.4f} | {tr['auc_direction_free']:.3f} | {va['fail_median']:+.4f} / {va['good_median']:+.4f} | {va['auc_direction_free']:.3f} |")
    lines += ["", "`AUC* = max(AUC, 1-AUC)`: 0.5 means no separation.", "", "## TRAIN-selected top single", ""]
    if primary_single:
        r = primary_single["rules"][0]; lines.append(f"Frozen from TRAIN: **{r['feature']} {r['side']} {r['threshold']:.6g}**.")
        lines += ["", "| Period | Fills | Sum R | EV/fill | PF | MaxDD R |", "|---|---:|---:|---:|---:|---:|"]
        for p in ("train", "valid", "full"):
            x = primary_single["metrics"][p]; lines.append(f"| {p.upper()} | {x['fills']} | {x['sum_r']:+.3f} | {x['ev_r_per_fill']:+.3f} | {x['pf']:.3f} | {x['max_dd_r']:.3f} |")
        lines += ["", "### Top-single promotion gates", ""]
        for k, v in primary_single["gates"].items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", "## TRAIN-selected composite diagnostic", ""]
    if composite_summary:
        lines.append(f"Composite: **{composite_summary['kind']}** — " + "; ".join(f"{r['feature']} {r['side']} {r['threshold']:.6g}" for r in composite_summary['rules']) + ".")
        lines += ["", "| Period | Fills | Sum R | EV/fill | PF | MaxDD R |", "|---|---:|---:|---:|---:|---:|"]
        for p in ("train", "valid", "full"):
            x = composite_summary["metrics"][p]; lines.append(f"| {p.upper()} | {x['fills']} | {x['sum_r']:+.3f} | {x['ev_r_per_fill']:+.3f} | {x['pf']:.3f} | {x['max_dd_r']:.3f} |")
        lines += ["", "Composite promotion: **" + ("PASS" if composite_summary["passed"] else "FAIL") + "**."]
    lines += ["", "## Research selection", ""]
    if selected_for_research:
        lines.append("Historical challenger selected for further robustness work: **" + selected_for_research["kind"] + "** — " + "; ".join(f"{r['feature']} {r['side']} {r['threshold']:.6g}" for r in selected_for_research['rules']) + ".")
    else:
        lines.append("No causal pre-entry veto passed all frozen promotion gates.")
    lines += ["", "## Governance", "", "This is still historical/post-discovery evidence, not independent OOS certification. No production logic is changed by LAB015 alone."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "selected": selected_for_research}, indent=2, default=str))


if __name__ == "__main__":
    main()
