#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

LAB = "BTC_RETAIL_RATIO_REST_QUANTIZATION_ORIGIN_AND_CAUSAL_DECISION_RECOVERABILITY_LAB_058"
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(parents=True, exist_ok=True)
LABS = HERE.parent
L57 = LABS / "BTC_RETAIL_RATIO_ARCHIVE_VS_REST_DECISION_PARITY_AND_THRESHOLD_MARGIN_LAB_057" / "output"
QUANTUM = 0.0001
COOLDOWN = pd.Timedelta(hours=12)
PREROLL = pd.Timedelta(hours=24)


def safe_rate(num: int, den: int) -> float:
    return float(num / den) if den else float("nan")


def exact_share(a: pd.Series, b: pd.Series, atol: float = 5e-9) -> float:
    if len(a) == 0:
        return float("nan")
    return float(np.isclose(a.to_numpy(float), b.to_numpy(float), rtol=0.0, atol=atol).mean())


def quantization_origin(raw: pd.DataFrame) -> dict:
    arc = raw["ratio_arc"].astype(float)
    rest = raw["ratio_rest"].astype(float)
    scale = 10000.0
    candidates = {
        "round4": np.round(arc * scale) / scale,
        "floor4": np.floor(arc * scale) / scale,
        "ceil4": np.ceil(arc * scale) / scale,
    }
    out = {}
    for name, pred in candidates.items():
        diff = np.abs(pred.to_numpy(float) - rest.to_numpy(float))
        out[name] = {
            "exact_share": float(np.isclose(pred, rest, rtol=0.0, atol=5e-9).mean()),
            "mean_abs": float(np.mean(diff)),
            "p95_abs": float(np.quantile(diff, 0.95)),
            "max_abs": float(np.max(diff)),
        }
    best_name = max(out, key=lambda k: out[k]["exact_share"])
    best_share = out[best_name]["exact_share"]
    return {
        "candidates": out,
        "best": best_name,
        "best_exact_share": best_share,
        "verdict": "PURE_QUANTIZATION_CONFIRMED" if best_share >= 0.99 else "PURE_QUANTIZATION_REJECTED",
    }


def make_events(df: pd.DataFrame, side_col: str) -> pd.DataFrame:
    rows = []
    next_allowed = None
    for r in df[["time", side_col]].sort_values("time").itertuples(index=False):
        side = getattr(r, side_col)
        if pd.isna(side) or int(side) == 0:
            continue
        t = r.time
        if next_allowed is None or t >= next_allowed:
            rows.append({"signal_time": t, "side": int(side)})
            next_allowed = t + COOLDOWN
    return pd.DataFrame(rows, columns=["signal_time", "side"])


def event_union_match(a: pd.DataFrame, b: pd.DataFrame, start: pd.Timestamp, side: int | None = None) -> dict:
    aa = a[a.signal_time >= start].copy()
    bb = b[b.signal_time >= start].copy()
    if side is not None:
        aa = aa[aa.side == side]
        bb = bb[bb.side == side]
    A = set(zip(aa.signal_time.astype(str), aa.side.astype(int)))
    B = set(zip(bb.signal_time.astype(str), bb.side.astype(int)))
    union = A | B
    inter = A & B
    return {
        "archive_n": len(A),
        "recovered_n": len(B),
        "intersection_n": len(inter),
        "union_n": len(union),
        "union_match": float(len(inter) / len(union)) if union else 1.0,
        "archive_only_n": len(A - B),
        "recovered_only_n": len(B - A),
    }


def qstats(x: pd.Series) -> dict:
    x = pd.to_numeric(x, errors="coerce").dropna().astype(float)
    if len(x) == 0:
        return {"n": 0}
    return {
        "n": int(len(x)),
        "min": float(x.min()),
        "p01": float(x.quantile(0.01)),
        "p05": float(x.quantile(0.05)),
        "p50": float(x.quantile(0.50)),
        "p95": float(x.quantile(0.95)),
        "p99": float(x.quantile(0.99)),
        "max": float(x.max()),
        "mean": float(x.mean()),
    }


def main():
    raw = pd.read_csv(L57 / "raw_ratio_overlap.csv")
    raw["time"] = pd.to_datetime(raw["time"], utc=True)
    raw = raw.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)

    comp = pd.read_csv(L57 / "m15_decision_comparison.csv")
    comp["time"] = pd.to_datetime(comp["time"], utc=True)
    comp = comp.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)

    origin = quantization_origin(raw)

    split_i = len(raw) // 2
    cal_raw = raw.iloc[:split_i].copy()
    eval_raw = raw.iloc[split_i:].copy()
    cal_end = cal_raw.time.max()
    residual = cal_raw.ratio_arc.astype(float) - cal_raw.ratio_rest.astype(float)
    e_lo = float(residual.min() - QUANTUM)
    e_hi = float(residual.max() + QUANTUM)

    eval_resid = eval_raw.ratio_arc.astype(float) - eval_raw.ratio_rest.astype(float)
    env_ok = (eval_resid >= e_lo) & (eval_resid <= e_hi)
    residual_coverage = float(env_ok.mean()) if len(eval_raw) else float("nan")

    # Evaluation begins strictly after calibration. Historical lag values remain causal/past.
    eval_comp = comp[comp.time > cal_end].copy()
    full = comp.copy()
    full["ratio_rest_lag12"] = full.ratio_rest.shift(12)
    full["ratio_lo"] = full.ratio_rest.astype(float) + e_lo
    full["ratio_hi"] = full.ratio_rest.astype(float) + e_hi
    full["ratio_lo_lag12"] = full.ratio_lo.shift(12)
    full["ratio_hi_lag12"] = full.ratio_hi.shift(12)
    full["delta_lo"] = full.ratio_lo - full.ratio_hi_lag12
    full["delta_hi"] = full.ratio_hi - full.ratio_lo_lag12

    aligned_raw_times = set(raw.time.tolist())
    full["expected_current_raw"] = full.time + pd.Timedelta(minutes=10)
    full["expected_lag_raw"] = full.time - pd.Timedelta(hours=3) + pd.Timedelta(minutes=10)
    full["fresh_current"] = full.expected_current_raw.isin(aligned_raw_times)
    full["fresh_lag"] = full.expected_lag_raw.isin(aligned_raw_times)
    full["transport_fresh"] = full.fresh_current & full.fresh_lag

    recovered = []
    labels = []
    for r in full.itertuples(index=False):
        side = np.nan
        label = "UNCERTAIN"
        if bool(r.transport_fresh) and pd.notna(r.delta_lo) and pd.notna(r.delta_hi) and pd.notna(r.q20) and pd.notna(r.q80):
            if r.delta_lo >= r.q80:
                side, label = -1, "CERTAIN_SHORT"
            elif r.delta_hi <= r.q20:
                side, label = 1, "CERTAIN_BUY"
            elif r.delta_lo > r.q20 and r.delta_hi < r.q80:
                side, label = 0, "CERTAIN_NEUTRAL"
        recovered.append(side)
        labels.append(label)
    full["recovered_side"] = recovered
    full["recovered_label"] = labels

    ev = full[full.time > cal_end].copy()
    certain = ev.recovered_side.notna()
    exact = certain & (ev.recovered_side.astype("Float64") == ev.side_arc.astype("Float64"))
    certainty_coverage = float(certain.mean()) if len(ev) else float("nan")
    certain_accuracy = float(exact.sum() / certain.sum()) if certain.sum() else float("nan")

    short_pred = certain & (ev.recovered_side == -1)
    short_true = ev.side_arc == -1
    buy_pred = certain & (ev.recovered_side == 1)
    buy_true = ev.side_arc == 1

    short_precision = safe_rate(int((short_pred & short_true).sum()), int(short_pred.sum()))
    short_recall = safe_rate(int((short_pred & short_true).sum()), int(short_true.sum()))
    buy_precision = safe_rate(int((buy_pred & buy_true).sum()), int(buy_pred.sum()))
    buy_recall = safe_rate(int((buy_pred & buy_true).sum()), int(buy_true.sum()))

    false_certain = ev[certain & (ev.recovered_side.astype("Float64") != ev.side_arc.astype("Float64"))].copy()
    uncertain = ev[~certain].copy()
    certain_rows = ev[certain].copy()

    # Stateful clock diagnostic. Generate from evaluation start onward; score only after 24h preroll.
    eval_start = ev.time.min()
    clock_input = full[full.time >= eval_start].copy()
    archive_events = make_events(clock_input, "side_arc")
    recovered_events = make_events(clock_input, "recovered_side")
    event_start = eval_start + PREROLL
    clock_all = event_union_match(archive_events, recovered_events, event_start, None)
    clock_short = event_union_match(archive_events, recovered_events, event_start, -1)

    pointwise_gates = {
        "evaluation_m15_n_ge1000": len(ev) >= 1000,
        "eval_ratio_envelope_coverage_ge99_5pct": residual_coverage >= 0.995,
        "certainty_coverage_ge95pct": certainty_coverage >= 0.95,
        "certain_accuracy_ge99_9pct": certain_accuracy >= 0.999,
        "certain_short_precision_ge99_5pct": short_precision >= 0.995,
        "canonical_short_recall_ge98pct": short_recall >= 0.98,
        "certain_buy_precision_ge99_5pct": buy_precision >= 0.995,
        "canonical_buy_recall_ge98pct": buy_recall >= 0.98,
        "no_tuning": True,
    }
    pointwise_verdict = (
        "PASS_CAUSAL_DECISION_RECOVERABILITY_WITH_ABSTENTION"
        if all(pointwise_gates.values())
        else "FAIL_CAUSAL_DECISION_RECOVERABILITY"
    )
    clock_verdict = "CLOCK_PARITY_PASS" if clock_all["union_match"] >= 0.95 else "CLOCK_PARITY_FAIL"
    short_clock_verdict = "SHORT_CLOCK_PARITY_PASS" if clock_short["union_match"] >= 0.95 else "SHORT_CLOCK_PARITY_FAIL"

    # Nearest threshold distance already persisted by LAB057; if absent, reconstruct.
    if "nearest_threshold_dist" not in ev.columns:
        ev["nearest_threshold_dist"] = np.minimum(
            np.abs(ev.delta_ls_12_arc - ev.q20),
            np.abs(ev.delta_ls_12_arc - ev.q80),
        )
        uncertain = ev[ev.recovered_side.isna()].copy()
        certain_rows = ev[ev.recovered_side.notna()].copy()

    metrics = {
        "lab": LAB,
        "source_lab": "LAB057",
        "fixed_rest_shift_minutes": -5,
        "quantum": QUANTUM,
        "raw_n": int(len(raw)),
        "calibration_raw_n": int(len(cal_raw)),
        "evaluation_raw_n": int(len(eval_raw)),
        "calibration_start": str(cal_raw.time.min()),
        "calibration_end": str(cal_end),
        "evaluation_raw_start": str(eval_raw.time.min()),
        "evaluation_raw_end": str(eval_raw.time.max()),
        "quantization_origin": origin,
        "calibration_residual": qstats(residual),
        "causal_residual_envelope": {"e_lo": e_lo, "e_hi": e_hi, "guard_quantum": QUANTUM},
        "evaluation_residual_coverage": residual_coverage,
        "evaluation_m15_n": int(len(ev)),
        "evaluation_m15_start": str(ev.time.min()),
        "evaluation_m15_end": str(ev.time.max()),
        "transport_fresh_share": float(ev.transport_fresh.mean()) if len(ev) else float("nan"),
        "certainty_coverage": certainty_coverage,
        "uncertain_n": int((~certain).sum()),
        "certain_n": int(certain.sum()),
        "certain_accuracy": certain_accuracy,
        "false_certain_n": int(len(false_certain)),
        "canonical_short_n": int(short_true.sum()),
        "certain_short_pred_n": int(short_pred.sum()),
        "certain_short_precision": short_precision,
        "canonical_short_recall": short_recall,
        "canonical_buy_n": int(buy_true.sum()),
        "certain_buy_pred_n": int(buy_pred.sum()),
        "certain_buy_precision": buy_precision,
        "canonical_buy_recall": buy_recall,
        "uncertain_threshold_distance": qstats(uncertain.nearest_threshold_dist),
        "certain_threshold_distance": qstats(certain_rows.nearest_threshold_dist),
        "pointwise_verdict": pointwise_verdict,
        "pointwise_gates": pointwise_gates,
        "clock_event_eval_start": str(event_start),
        "clock_all": clock_all,
        "clock_short": clock_short,
        "clock_verdict": clock_verdict,
        "short_clock_verdict": short_clock_verdict,
        "frozen_short_v1_changed": False,
        "live_allocation": 0,
    }

    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    ev.to_csv(OUT / "evaluation_decision_recovery.csv", index=False)
    false_certain.to_csv(OUT / "false_certain_decisions.csv", index=False)
    uncertain.to_csv(OUT / "uncertain_decisions.csv", index=False)
    archive_events.to_csv(OUT / "archive_clock_events.csv", index=False)
    recovered_events.to_csv(OUT / "recovered_clock_events.csv", index=False)

    lines = [
        f"# {LAB}",
        "",
        f"**Quantization origin: {origin['verdict']}**",
        f"**Pointwise recoverability: {pointwise_verdict}**",
        f"**All-side clock: {clock_verdict}**",
        f"**SHORT clock: {short_clock_verdict}**",
        "",
        "## Pure quantization origin",
        f"- best deterministic transform: **{origin['best']}**",
        f"- best exact share: **{origin['best_exact_share']:.3%}**",
        "",
        "## Causal calibration",
        f"- calibration raw N: **{len(cal_raw)}**",
        f"- evaluation raw N: **{len(eval_raw)}**",
        f"- frozen residual envelope: **[{e_lo:+.8f}, {e_hi:+.8f}]**",
        f"- evaluation envelope coverage: **{residual_coverage:.3%}**",
        "",
        "## Pointwise causal recovery",
        f"- evaluation M15 N: **{len(ev)}**",
        f"- transport fresh: **{metrics['transport_fresh_share']:.3%}**",
        f"- certainty coverage: **{certainty_coverage:.3%}**",
        f"- accuracy among CERTAIN: **{certain_accuracy:.3%}**",
        f"- false-certain decisions: **{len(false_certain)}**",
        f"- SHORT precision: **{short_precision:.3%}**",
        f"- SHORT recall: **{short_recall:.3%}**",
        f"- BUY precision: **{buy_precision:.3%}**",
        f"- BUY recall: **{buy_recall:.3%}**",
        "",
        "## Threshold-margin concentration",
        f"- UNCERTAIN median distance to nearest threshold: **{metrics['uncertain_threshold_distance'].get('p50', float('nan')):.8f}**",
        f"- CERTAIN median distance to nearest threshold: **{metrics['certain_threshold_distance'].get('p50', float('nan')):.8f}**",
        "",
        "## Stateful 12h clock diagnostic",
        f"- all-side union match: **{clock_all['union_match']:.3%}** ({clock_all['intersection_n']}/{clock_all['union_n']})",
        f"- SHORT union match: **{clock_short['union_match']:.3%}** ({clock_short['intersection_n']}/{clock_short['union_n']})",
        "",
        "## Decision",
        "LAB058 is transport-only. Frozen SHORT v1 is unchanged. No PnL was used and live/prop allocation remains 0.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
