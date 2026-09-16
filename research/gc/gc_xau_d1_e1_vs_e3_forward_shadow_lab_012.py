#!/usr/bin/env python3
"""GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012

Forward-only evaluator for the frozen GC BUYER_BREAKOUT_LONG_001 sensor.
It does not discover or retune parameters. It consumes the append-only LAB012
shadow ledger and compares the declared E1 and E3 candidates on the same fresh
post-freeze GC signal set.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("research/gc")
LEDGER = ROOT / "GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012_LEDGER.csv"
OUT_JSON = ROOT / "GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012.json"
OUT_MD = ROOT / "GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012.md"
OUT_PAIRED = ROOT / "GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012_PAIRED.csv"

LAB = "GC_XAU_D1_E1_VS_E3_FORWARD_SHADOW_LAB_012"
SENSOR = "BUYER_BREAKOUT_LONG_001"
FREEZE_COMMIT = "a8c74b568b85d6a4d195f6558860256a72a7319b"
FREEZE_TS = pd.Timestamp("2026-09-16T19:29:45Z")
FREEZE_MS = FREEZE_TS.value // 1_000_000
SEED = 20260916
BOOT_N = 10_000
RISK_PCT = 0.25

E1 = "GCXAU_D1.00_E1M_SL1.5_TP3_ONEACTIVE_CHALLENGER_001"
E3 = "GCXAU_D1.00_E3M_SL1.5_TP3_ONEACTIVE_001"
CANDIDATES = (E1, E3)

TERMINAL_OUTCOMES = {
    "TP", "SL", "TIMEOUT", "UNFILLED", "OVERLAP_REJECT", "REJECTED_ONEACTIVE"
}

REQUIRED = {
    "record_version", "signal_id", "candidate", "sensor_label", "freeze_commit",
    "signal_time_utc_ms", "signal_bool", "xau_atr14_m1", "market_reference_ask",
    "limit_price", "order_start_utc_ms", "expiry_utc_ms", "timeout_utc_ms",
    "oneactive_accept", "fill_time_utc_ms", "fill_delay_ms", "shadow_fill_price",
    "sl_price", "tp_price", "outcome", "r_quote_only", "commission_r",
    "slippage_r", "r_actual_cost", "r_stress005", "data_gap", "stale_quote",
}


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin({"1", "true", "t", "yes", "y"})


def num(df: pd.DataFrame, cols: list[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


def latest_append_only(df: pd.DataFrame) -> pd.DataFrame:
    """Resolve corrections without deleting the old audit trail from source CSV."""
    x = df.copy()
    x["record_version"] = pd.to_numeric(x["record_version"], errors="coerce").fillna(1).astype(int)
    x["void_record"] = as_bool(x.get("void_record", pd.Series(False, index=x.index)))
    x = x.sort_values(["signal_id", "candidate", "record_version"], kind="stable")
    x = x.drop_duplicates(["signal_id", "candidate"], keep="last")
    return x.loc[~x["void_record"]].copy()


def max_dd_r(v: np.ndarray) -> float:
    if len(v) == 0:
        return 0.0
    eq = np.cumsum(v)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return float(np.max(dd)) if len(dd) else 0.0


def pf(v: np.ndarray) -> float | None:
    if len(v) == 0:
        return None
    gp = float(v[v > 0].sum())
    gl = float(-v[v < 0].sum())
    if gl == 0:
        return float("inf") if gp > 0 else None
    return gp / gl


def candidate_metrics(df: pd.DataFrame) -> dict:
    z = df.sort_values("signal_time_utc_ms", kind="stable").copy()
    r = z["r_stress005"].to_numpy(float)
    filled = z["fill_time_utc_ms"].notna()
    rf = z.loc[filled, "r_stress005"].to_numpy(float)
    n = len(z)
    half = n // 2
    late = r[half:] if n else np.array([], dtype=float)

    ts = pd.to_datetime(z["signal_time_utc_ms"], unit="ms", utc=True)
    z["utc_day"] = ts.dt.date
    daily = z.groupby("utc_day", sort=True)["r_stress005"].sum()
    pos_daily = daily[daily > 0]
    pos_total = float(pos_daily.sum())
    max_pos_day_share = float(pos_daily.max() / pos_total) if pos_total > 0 else None

    actual_complete = z["r_actual_cost"].notna().all() and n > 0
    actual_ev = float(z["r_actual_cost"].mean()) if actual_complete else None

    return {
        "signals": int(n),
        "fills": int(filled.sum()),
        "fill_rate_pct": float(filled.mean() * 100.0) if n else None,
        "ev_r_signal_stress005": float(r.mean()) if n else None,
        "ev_r_fill_stress005": float(rf.mean()) if len(rf) else None,
        "pf_stress005_filled": pf(rf),
        "wr_pct_stress005_filled": float((rf > 0).mean() * 100.0) if len(rf) else None,
        "sum_r_stress005": float(r.sum()) if n else 0.0,
        "maxdd_r_stress005": max_dd_r(r),
        "maxdd_pct_at_025risk": max_dd_r(r) * RISK_PCT,
        "late_half_ev_r_signal_stress005": float(late.mean()) if len(late) else None,
        "utc_days": int(len(daily)),
        "positive_days": int((daily > 0).sum()),
        "max_positive_day_share": max_pos_day_share,
        "actual_cost_complete": bool(actual_complete),
        "ev_r_signal_actual_cost": actual_ev,
    }


def paired_bootstrap(day_groups: list[np.ndarray]) -> tuple[float | None, float | None, float | None]:
    if not day_groups:
        return None, None, None
    allv = np.concatenate(day_groups)
    mean = float(allv.mean()) if len(allv) else None
    if len(day_groups) < 2:
        return mean, None, None
    rng = np.random.default_rng(SEED)
    k = len(day_groups)
    vals = np.empty(BOOT_N)
    for j in range(BOOT_N):
        pick = rng.integers(0, k, k)
        vals[j] = np.concatenate([day_groups[i] for i in pick]).mean()
    return mean, float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def f(x, digits=4):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    if isinstance(x, float) and np.isinf(x):
        return "∞"
    return f"{x:+.{digits}f}"


def empty_result(reason: str, extra: dict | None = None) -> dict:
    d = {
        "lab": LAB,
        "status": "INSUFFICIENT_FRESH_FORWARD_SAMPLE",
        "reason": reason,
        "freeze_commit": FREEZE_COMMIT,
        "freeze_utc": FREEZE_TS.isoformat(),
        "governance": "forward-only; no historical retuning; shadow only",
    }
    if extra:
        d.update(extra)
    return d


def write_report(res: dict) -> None:
    OUT_JSON.write_text(json.dumps(res, indent=2, default=str, allow_nan=False), encoding="utf-8")
    lines = [
        f"# {LAB}", "",
        f"Status: **{res['status']}**", "",
        f"Forward cutoff: `{res['freeze_utc']}` from LAB011 commit `{FREEZE_COMMIT}`.", "",
    ]
    if "reason" in res:
        lines += [res["reason"], ""]
    if "metrics" in res:
        lines += [
            "## Forward metrics", "",
            "| Candidate | Signals | Fills | Fill % | EV/signal | EV/fill | PF | MaxDD R | DD @0.25% | Late-half EV | Max +day share |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for c, label in ((E1, "E1 challenger"), (E3, "E3 incumbent")):
            m = res["metrics"][c]
            share = "NA" if m["max_positive_day_share"] is None else f"{100*m['max_positive_day_share']:.1f}%"
            lines.append(
                f"| {label} | {m['signals']} | {m['fills']} | "
                f"{('NA' if m['fill_rate_pct'] is None else f'{m['fill_rate_pct']:.1f}%')} | "
                f"{f(m['ev_r_signal_stress005'])} | {f(m['ev_r_fill_stress005'])} | "
                f"{f(m['pf_stress005_filled'],2)} | {m['maxdd_r_stress005']:.2f} | "
                f"{m['maxdd_pct_at_025risk']:.2f}% | {f(m['late_half_ev_r_signal_stress005'])} | {share} |"
            )
        p = res["paired"]
        ci = "NA" if p["ci95_low"] is None else f"[{p['ci95_low']:+.4f}, {p['ci95_high']:+.4f}]"
        lines += ["", "## Paired E1 − E3", "", f"Mean paired difference: **{f(p['mean_diff_r_signal'])}R/signal**; UTC-day bootstrap CI95: **{ci}**.", ""]
        lines += ["## Maturity", "", f"Mature: **{res['maturity']['mature']}**", ""]
        for k, v in res["maturity"]["checks"].items():
            lines.append(f"- {k}: `{v}`")
        if "health_gates" in res:
            lines += ["", "## Frozen health gates", ""]
            for c, label in ((E1, "E1"), (E3, "E3")):
                g = res["health_gates"][c]
                lines.append(f"- {label}: **{'PASS' if g['all_pass'] else 'FAIL'}** — {g['checks']}")
    lines += ["", "No live/production claim is made by this report. E1 is not promoted before the frozen maturity and paired-promotion gates are satisfied.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not LEDGER.exists():
        res = empty_result("Canonical forward ledger does not exist yet.")
        write_report(res)
        print(OUT_MD.read_text())
        return

    df = pd.read_csv(LEDGER)
    missing = sorted(REQUIRED - set(df.columns))
    if missing:
        raise SystemExit(f"LAB012 ledger missing required columns: {missing}")
    if df.empty:
        res = empty_result("Ledger schema is frozen, but no post-freeze shadow observations have been appended yet.")
        write_report(res)
        print(OUT_MD.read_text())
        return

    df = latest_append_only(df)
    num(df, [
        "signal_time_utc_ms", "xau_atr14_m1", "market_reference_ask", "limit_price",
        "order_start_utc_ms", "expiry_utc_ms", "timeout_utc_ms", "fill_time_utc_ms",
        "fill_delay_ms", "shadow_fill_price", "sl_price", "tp_price", "r_quote_only",
        "commission_r", "slippage_r", "r_actual_cost", "r_stress005",
    ])
    df["signal_bool"] = as_bool(df["signal_bool"])
    df["oneactive_accept"] = as_bool(df["oneactive_accept"])
    df["data_gap"] = as_bool(df["data_gap"])
    df["stale_quote"] = as_bool(df["stale_quote"])
    df["candidate"] = df["candidate"].astype(str).str.strip()
    df["sensor_label"] = df["sensor_label"].astype(str).str.strip()
    df["freeze_commit"] = df["freeze_commit"].astype(str).str.strip()
    df["outcome"] = df["outcome"].astype(str).str.strip().str.upper()

    exposed = df["signal_time_utc_ms"].le(FREEZE_MS).fillna(True)
    wrong_sensor = ~df["sensor_label"].eq(SENSOR)
    wrong_candidate = ~df["candidate"].isin(CANDIDATES)
    wrong_freeze = ~df["freeze_commit"].eq(FREEZE_COMMIT)
    nonsignal = ~df["signal_bool"]

    rejected_rows = int((exposed | wrong_sensor | wrong_candidate | wrong_freeze | nonsignal).sum())
    x = df.loc[~(exposed | wrong_sensor | wrong_candidate | wrong_freeze | nonsignal)].copy()

    if x.empty:
        res = empty_result(
            "No valid post-freeze BUYER_BREAKOUT_LONG_001 observations are available.",
            {"source_rows": int(len(df)), "rejected_rows": rejected_rows},
        )
        write_report(res)
        print(OUT_MD.read_text())
        return

    # Candidate semantics that can be audited directly from the ledger.
    expiry_expected = x["order_start_utc_ms"] + np.where(x["candidate"].eq(E1), 60_000, 180_000)
    expiry_error = np.abs(x["expiry_utc_ms"] - expiry_expected) > 1
    timeout_error = np.abs(x["timeout_utc_ms"] - (x["signal_time_utc_ms"] + 30 * 60_000)) > 1
    limit_error = np.abs(x["limit_price"] - (x["market_reference_ask"] - x["xau_atr14_m1"])) > 1e-7
    sl_error = x["fill_time_utc_ms"].notna() & (np.abs(x["sl_price"] - (x["shadow_fill_price"] - 1.5 * x["xau_atr14_m1"])) > 1e-7)
    tp_error = x["fill_time_utc_ms"].notna() & (np.abs(x["tp_price"] - (x["shadow_fill_price"] + 4.5 * x["xau_atr14_m1"])) > 1e-7)
    semantic_errors = int((expiry_error | timeout_error | limit_error | sl_error | tp_error).sum())
    if semantic_errors:
        raise SystemExit(f"LAB012 frozen execution semantic mismatch in {semantic_errors} rows")

    # A pair becomes scoreable only after both candidate rows have terminal outcomes.
    counts = x.groupby("signal_id")["candidate"].nunique()
    complete_ids = counts[counts.eq(2)].index
    x = x[x["signal_id"].isin(complete_ids)].copy()
    terminal = x["outcome"].isin(TERMINAL_OUTCOMES) & x["r_stress005"].notna()
    terminal_by_signal = terminal.groupby(x["signal_id"]).sum()
    settled_ids = terminal_by_signal[terminal_by_signal.eq(2)].index
    settled = x[x["signal_id"].isin(settled_ids)].copy()

    # Data-gap/stale rows are preserved but not silently scored as valid observations.
    bad_data_ids = settled.loc[settled["data_gap"] | settled["stale_quote"], "signal_id"].unique()
    score = settled[~settled["signal_id"].isin(bad_data_ids)].copy()

    if score.empty:
        res = empty_result(
            "Fresh observations exist, but no complete clean E1/E3 pair has matured yet.",
            {
                "source_rows": int(len(df)), "postfreeze_valid_rows": int(len(x)),
                "settled_pairs": int(len(settled_ids)), "data_bad_pairs": int(len(bad_data_ids)),
                "rejected_rows": rejected_rows,
            },
        )
        write_report(res)
        print(OUT_MD.read_text())
        return

    # Force all blocked/unfilled records to have zero signal R.
    nofill = score["fill_time_utc_ms"].isna()
    nonzero_nofill = nofill & score["r_stress005"].abs().gt(1e-12)
    if nonzero_nofill.any():
        raise SystemExit("LAB012 unfilled/blocked row has non-zero r_stress005")

    metrics = {c: candidate_metrics(score[score["candidate"].eq(c)]) for c in CANDIDATES}

    wide = score.pivot(index="signal_id", columns="candidate", values="r_stress005")
    times = score.groupby("signal_id")["signal_time_utc_ms"].first()
    wide = wide.join(times.rename("signal_time_utc_ms")).dropna(subset=[E1, E3]).reset_index()
    wide["diff_e1_minus_e3"] = wide[E1] - wide[E3]
    wide["utc_day"] = pd.to_datetime(wide["signal_time_utc_ms"], unit="ms", utc=True).dt.date
    wide.to_csv(OUT_PAIRED, index=False)

    groups = [g["diff_e1_minus_e3"].to_numpy(float) for _, g in wide.groupby("utc_day", sort=True)]
    dmean, dlo, dhi = paired_bootstrap(groups)

    signals = int(len(wide))
    days = int(wide["utc_day"].nunique())
    fills_e1 = metrics[E1]["fills"]
    fills_e3 = metrics[E3]["fills"]
    maturity_checks = {
        "signals_ge_100": signals >= 100,
        "utc_days_ge_15": days >= 15,
        "e1_fills_ge_30": fills_e1 >= 30,
        "e3_fills_ge_30": fills_e3 >= 30,
        "no_bad_data_pairs_in_scored_set": True,
    }
    mature = all(maturity_checks.values())

    res = {
        "lab": LAB,
        "status": "INSUFFICIENT_FRESH_FORWARD_SAMPLE",
        "freeze_commit": FREEZE_COMMIT,
        "freeze_utc": FREEZE_TS.isoformat(),
        "source_rows": int(len(df)),
        "rejected_rows": rejected_rows,
        "settled_pairs_before_data_quality": int(len(settled_ids)),
        "data_bad_pairs_excluded": int(len(bad_data_ids)),
        "scoreable_paired_signals": signals,
        "scoreable_utc_days": days,
        "metrics": metrics,
        "paired": {"mean_diff_r_signal": dmean, "ci95_low": dlo, "ci95_high": dhi, "bootstrap_unit": "UTC day", "n_boot": BOOT_N},
        "maturity": {"mature": mature, "checks": maturity_checks},
        "risk_pct_per_fill": RISK_PCT,
        "governance": "forward-only; shadow only; no historical retuning",
    }

    if mature:
        gates = {}
        for c in CANDIDATES:
            m = metrics[c]
            checks = {
                "ev_signal_stress005_gt_0": m["ev_r_signal_stress005"] is not None and m["ev_r_signal_stress005"] > 0,
                "pf_filled_stress005_gt_1p20": m["pf_stress005_filled"] is not None and m["pf_stress005_filled"] > 1.20,
                "late_half_ev_ge_0": m["late_half_ev_r_signal_stress005"] is not None and m["late_half_ev_r_signal_stress005"] >= 0,
                "max_positive_day_share_lt_0p50": m["max_positive_day_share"] is not None and m["max_positive_day_share"] < 0.50,
                "maxdd_025risk_lt_4pct": m["maxdd_pct_at_025risk"] < 4.0,
            }
            gates[c] = {"checks": checks, "all_pass": all(checks.values())}
        res["health_gates"] = gates

        e1_pass = gates[E1]["all_pass"]
        e3_pass = gates[E3]["all_pass"]
        paired_promote = dlo is not None and dlo > 0

        if e1_pass and paired_promote:
            res["status"] = "E1_FORWARD_CHALLENGER_PROMOTION_GATE_PASS_RESEARCH_ONLY"
        elif e3_pass and not e1_pass:
            res["status"] = "E3_SURVIVES_FORWARD_CHALLENGE_RESEARCH_ONLY"
        elif e1_pass and e3_pass:
            res["status"] = "E1_VS_E3_INCONCLUSIVE"
        else:
            res["status"] = "FORWARD_HEALTH_GATE_FAIL_NO_PROMOTION"

        # Actual-cost production gate remains explicitly separate.
        res["actual_cost_production_gate"] = {
            c: bool(metrics[c]["actual_cost_complete"] and metrics[c]["ev_r_signal_actual_cost"] is not None and metrics[c]["ev_r_signal_actual_cost"] > 0)
            for c in CANDIDATES
        }

    write_report(res)
    print(OUT_MD.read_text())


if __name__ == "__main__":
    main()
