#!/usr/bin/env python3
"""LAB016 — causal D0.75 prefill warning gate before frozen XAU D1 touch.

Historical bounded discovery on the same frozen AMP GC + FTMO XAU ticks.
No baseline retune. No post-fill feature is used by the classifier.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path("research/gc")
LAB15_SCRIPT = ROOT / "gc_xau_d1_e3_trade_failure_discriminator_lab_015.py"
LAB15_FEATURES = ROOT / "GC_XAU_D1_E3_TRADE_FAILURE_DISCRIMINATOR_LAB_015_FEATURES.csv"
OUT_JSON = ROOT / "GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016.json"
OUT_MD = ROOT / "GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016.md"
OUT_FEATURES = ROOT / "GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016_FEATURES.csv"
OUT_OOF = ROOT / "GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016_OOF.csv"
OUT_COEF = ROOT / "GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016_COEFFICIENTS.csv"
OUT_UNIV = ROOT / "GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016_UNIVARIATE.csv"

BROKER_OFFSET_MS = 180 * 60_000
WARNING_DEPTH_ATR = 0.75
D1_DEPTH_ATR = 1.00
MIN_LEAD_MS = 250
INITIAL_TRAIN = 45
TEST_BLOCK = 12
VETO_Q = 0.75

BASE_FEATURES = [
    "gc_delta_excess", "gc_buy_strength", "gc_body_atr", "gc_range_atr",
    "gc_close_pos", "gc_breakout_atr", "gc_buy_loc_excess", "xau_spread_start_atr",
]
DYNAMIC_FEATURES = [
    "warning_delay_sec", "xau_spread_warning_atr", "xau_prefill_range_warning_atr",
    "xau_mom_10s_warning_atr", "xau_mom_30s_warning_atr",
    "xau_approach_velocity_atr_per_sec", "xau_remaining_to_d1_atr",
    "gc_post_delta_to_warning",
]
MODEL_FEATURES = BASE_FEATURES + DYNAMIC_FEATURES


def load_lab15():
    spec = importlib.util.spec_from_file_location("lab15mod", LAB15_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def max_dd(v: np.ndarray) -> float:
    if len(v) == 0:
        return np.nan
    eq = np.cumsum(np.nan_to_num(v, nan=0.0))
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    return float((peak[1:] - eq).max()) if len(eq) else 0.0


def build_warning_features(l15, pop, amp_seq, lab15f, gc_raw, xau):
    gt, gbuy, gsell = gc_raw
    xt, xb, xa = xau
    lab15f = lab15f.copy()
    lab15f["signal_time_utc"] = pd.to_datetime(lab15f.signal_time_utc, utc=True)
    base = lab15f.set_index("signal_time_utc")
    rows = []

    for r in pop.sort_values("signal_time_utc").itertuples(index=False):
        sig = pd.Timestamp(r.signal_time_utc)
        if sig not in base.index:
            raise SystemExit(f"Missing LAB015 feature row {sig}")
        b = base.loc[sig]
        if isinstance(b, pd.DataFrame):
            b = b.iloc[0]
        atr = float(r.xau_atr14_m1)
        start_ts = int(r.entry_tick_msc)
        fill_ts = int(r.fill_time_msc)
        start_ask = float(r.entry_ask)
        limit_px = start_ask - D1_DEPTH_ATR * atr
        warn_px = start_ask - WARNING_DEPTH_ATR * atr

        si = int(np.searchsorted(xt, start_ts, side="left"))
        fi = int(np.searchsorted(xt, fill_ts, side="right")) - 1
        if si >= len(xt) or fi < si:
            raise SystemExit(f"Bad XAU indices for {sig}")

        # first quote tick crossing D0.75 while still strictly above D1
        idx = np.arange(si, fi + 1)
        m = (xa[idx] <= warn_px + 1e-12) & (xa[idx] > limit_px + 1e-12)
        cand = idx[m]
        wi = int(cand[0]) if len(cand) else -1
        causal = wi >= 0 and int(xt[wi]) <= fill_ts - MIN_LEAD_MS

        row = {
            "signal_time_utc": sig.isoformat(),
            "status": str(r.status),
            "net_r": float(r.adj_r_corrected),
            "sl_label": int(str(r.status) == "SL"),
            "warning_available": bool(causal),
            "fill_time_msc": fill_ts,
            "warning_time_msc": int(xt[wi]) if wi >= 0 else np.nan,
            "warning_lead_to_fill_sec": float((fill_ts - int(xt[wi])) / 1000.0) if wi >= 0 else np.nan,
        }
        for f in BASE_FEATURES:
            row[f] = float(b[f]) if pd.notna(b[f]) else np.nan

        if causal:
            warn_ts = int(xt[wi])
            start_mid = (float(xb[si]) + float(xa[si])) / 2.0
            warn_mid = (float(xb[wi]) + float(xa[wi])) / 2.0
            delay_sec = max((warn_ts - start_ts) / 1000.0, 0.001)
            m10 = l15.mid_at_or_before(xt, xb, xa, warn_ts - 10_000, si)
            m30 = l15.mid_at_or_before(xt, xb, xa, warn_ts - 30_000, si)
            mids = (xb[si:wi + 1] + xa[si:wi + 1]) / 2.0
            order_start_utc_ms = int(sig.value // 1_000_000) + 60_000
            warn_utc_ms = warn_ts - BROKER_OFFSET_MS
            row.update({
                "warning_delay_sec": delay_sec,
                "xau_spread_warning_atr": float((xa[wi] - xb[wi]) / atr),
                "xau_prefill_range_warning_atr": float((np.max(mids) - np.min(mids)) / atr),
                "xau_mom_10s_warning_atr": float((warn_mid - m10) / atr),
                "xau_mom_30s_warning_atr": float((warn_mid - m30) / atr),
                "xau_approach_velocity_atr_per_sec": float(((start_mid - warn_mid) / atr) / delay_sec),
                "xau_remaining_to_d1_atr": float((xa[wi] - limit_px) / atr),
                "gc_post_delta_to_warning": l15.gc_window_delta_frac(gt, gbuy, gsell, order_start_utc_ms, warn_utc_ms),
            })
        else:
            for f in DYNAMIC_FEATURES:
                row[f] = np.nan
        rows.append(row)

    return pd.DataFrame(rows).sort_values("signal_time_utc").reset_index(drop=True)


def make_pipe():
    return Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc", StandardScaler()),
        ("lr", LogisticRegression(C=1.0, class_weight="balanced", solver="liblinear", random_state=20260917)),
    ])


def walk_forward(df: pd.DataFrame):
    d = df[df.warning_available].copy().reset_index(drop=True)
    rows, coef_rows = [], []
    fold = 0
    start = INITIAL_TRAIN
    while start < len(d):
        end = min(start + TEST_BLOCK, len(d))
        tr = d.iloc[:start].copy()
        te = d.iloc[start:end].copy()
        if tr.sl_label.nunique() < 2:
            raise SystemExit("Training window has one class")
        pipe = make_pipe()
        pipe.fit(tr[MODEL_FEATURES], tr.sl_label)
        p_train = pipe.predict_proba(tr[MODEL_FEATURES])[:, 1]
        threshold = float(np.quantile(p_train, VETO_Q))
        p_test = pipe.predict_proba(te[MODEL_FEATURES])[:, 1]
        for j, (_, rr) in enumerate(te.iterrows()):
            rows.append({
                "signal_time_utc": rr.signal_time_utc,
                "status": rr.status,
                "net_r": float(rr.net_r),
                "sl_label": int(rr.sl_label),
                "fold": fold,
                "p_sl": float(p_test[j]),
                "threshold": threshold,
                "veto": bool(p_test[j] >= threshold),
            })
        lr = pipe.named_steps["lr"]
        for f, c in zip(MODEL_FEATURES, lr.coef_[0]):
            coef_rows.append({"fold": fold, "feature": f, "coef": float(c)})
        fold += 1
        start = end
    return pd.DataFrame(rows), pd.DataFrame(coef_rows)


def univariate(df: pd.DataFrame):
    d = df[df.warning_available].copy()
    y = d.sl_label.to_numpy(int)
    rows = []
    for f in MODEL_FEATURES:
        x = pd.to_numeric(d[f], errors="coerce").to_numpy(float)
        m = np.isfinite(x)
        yy, xx = y[m], x[m]
        auc = float(roc_auc_score(yy, xx)) if len(np.unique(yy)) == 2 else np.nan
        rows.append({
            "feature": f,
            "n": int(m.sum()),
            "auc_raw": auc,
            "auc_directionless": max(auc, 1 - auc) if np.isfinite(auc) else np.nan,
            "failure_direction": "HIGH" if np.isfinite(auc) and auc >= 0.5 else "LOW",
            "sl_median": float(np.median(xx[yy == 1])) if np.any(yy == 1) else np.nan,
            "non_sl_median": float(np.median(xx[yy == 0])) if np.any(yy == 0) else np.nan,
        })
    return pd.DataFrame(rows).sort_values("auc_directionless", ascending=False)


def summarize_coefficients(cdf: pd.DataFrame):
    rows = []
    for f, g in cdf.groupby("feature", sort=False):
        v = g.coef.to_numpy(float)
        med = float(np.median(v))
        sign = np.sign(med)
        same = float((np.sign(v) == sign).mean() * 100) if sign != 0 else np.nan
        rows.append({"feature": f, "folds": len(v), "coef_median": med, "coef_mean": float(v.mean()), "coef_abs_median": float(np.median(np.abs(v))), "same_sign_as_median_pct": same})
    return pd.DataFrame(rows).sort_values("coef_abs_median", ascending=False)


def overlay_metrics(oof: pd.DataFrame, amp_seq: pd.DataFrame):
    if oof.empty:
        return {}
    o = oof.copy()
    o["signal_time_utc"] = pd.to_datetime(o.signal_time_utc, utc=True)
    t0, t1 = o.signal_time_utc.min(), o.signal_time_utc.max()
    s = amp_seq[(amp_seq.signal_time_utc >= t0) & (amp_seq.signal_time_utc <= t1)].copy().sort_values("signal_time_utc")
    s["base_r"] = pd.to_numeric(s.adj_r_corrected, errors="coerce").fillna(0.0)
    veto_times = set(o.loc[o.veto, "signal_time_utc"])
    s["overlay_r"] = [0.0 if t in veto_times else r for t, r in zip(s.signal_time_utc, s.base_r)]
    n = len(s)
    split = n // 2
    late = s.iloc[split:]
    return {
        "original_signals_oof_period": int(n),
        "baseline_sum_r": float(s.base_r.sum()),
        "overlay_sum_r": float(s.overlay_r.sum()),
        "baseline_ev_r_per_signal": float(s.base_r.mean()),
        "overlay_ev_r_per_signal": float(s.overlay_r.mean()),
        "baseline_maxdd_r": max_dd(s.base_r.to_numpy(float)),
        "overlay_maxdd_r": max_dd(s.overlay_r.to_numpy(float)),
        "late_half_signals": int(len(late)),
        "late_half_baseline_ev_r": float(late.base_r.mean()) if len(late) else np.nan,
        "late_half_overlay_ev_r": float(late.overlay_r.mean()) if len(late) else np.nan,
    }


def main():
    l15 = load_lab15()
    pop, amp_seq = l15.load_population()
    if len(pop) != 103:
        raise SystemExit(f"Expected 103 corrected AMP fills, got {len(pop)}")
    lab15f = pd.read_csv(LAB15_FEATURES, low_memory=False)
    gc_raw = l15.load_gc_raw_prefix()
    xau = l15.load_xau_ticks()
    feat = build_warning_features(l15, pop, amp_seq, lab15f, gc_raw, xau)
    feat.to_csv(OUT_FEATURES, index=False)

    eligible = feat[feat.warning_available].copy()
    oof, coef = walk_forward(feat)
    oof.to_csv(OUT_OOF, index=False)
    coef_summary = summarize_coefficients(coef)
    coef_summary.to_csv(OUT_COEF, index=False)
    uni = univariate(feat)
    uni.to_csv(OUT_UNIV, index=False)

    y = oof.sl_label.to_numpy(int) if len(oof) else np.array([], int)
    auc = float(roc_auc_score(y, oof.p_sl)) if len(np.unique(y)) == 2 else np.nan
    ap = float(average_precision_score(y, oof.p_sl)) if len(np.unique(y)) == 2 else np.nan
    veto = oof.veto.astype(bool) if len(oof) else pd.Series(dtype=bool)
    base_sl = float(oof.sl_label.mean()) if len(oof) else np.nan
    veto_sl = float(oof.loc[veto, "sl_label"].mean()) if veto.any() else np.nan
    enrich = float(veto_sl / base_sl) if np.isfinite(veto_sl) and base_sl > 0 else np.nan
    om = overlay_metrics(oof, amp_seq)
    coverage = float(feat.warning_available.mean())

    gates = {
        "warning_coverage_ge70pct": coverage >= 0.70,
        "oof_ge40_and_both_classes": len(oof) >= 40 and len(np.unique(y)) == 2,
        "oof_sl_auc_ge0_60": np.isfinite(auc) and auc >= 0.60,
        "veto_share_10_to_40pct": len(oof) > 0 and 0.10 <= float(veto.mean()) <= 0.40,
        "veto_sl_enrichment_ge1_25x": np.isfinite(enrich) and enrich >= 1.25,
        "overlay_sum_gt_baseline": bool(om) and om["overlay_sum_r"] > om["baseline_sum_r"],
        "overlay_ev_signal_gt_baseline": bool(om) and om["overlay_ev_r_per_signal"] > om["baseline_ev_r_per_signal"],
        "overlay_maxdd_le_baseline": bool(om) and om["overlay_maxdd_r"] <= om["baseline_maxdd_r"] + 1e-12,
        "late_half_overlay_ev_pos": bool(om) and om["late_half_overlay_ev_r"] > 0,
    }
    passed = all(gates.values())
    status = "HISTORICAL_CAUSAL_PREFILL_GATE_CANDIDATE_PASS_NOT_OOS" if passed else "HISTORICAL_CAUSAL_PREFILL_GATE_FAIL_NOT_OOS"

    result = {
        "lab": "GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016",
        "status": status,
        "population": {
            "corrected_accepted_fills": int(len(feat)),
            "warning_eligible_fills": int(feat.warning_available.sum()),
            "warning_coverage": coverage,
            "warning_sl": int(eligible.sl_label.sum()),
            "warning_non_sl": int(len(eligible) - eligible.sl_label.sum()),
            "median_warning_delay_sec": float(eligible.warning_delay_sec.median()) if len(eligible) else None,
            "median_warning_lead_to_fill_sec": float(eligible.warning_lead_to_fill_sec.median()) if len(eligible) else None,
            "p10_warning_lead_to_fill_sec": float(eligible.warning_lead_to_fill_sec.quantile(0.10)) if len(eligible) else None,
        },
        "oof": {
            "fills": int(len(oof)),
            "sl": int(oof.sl_label.sum()) if len(oof) else 0,
            "sl_rate": base_sl,
            "auc_sl": auc,
            "average_precision_sl": ap,
            "vetoed": int(veto.sum()) if len(oof) else 0,
            "veto_share": float(veto.mean()) if len(oof) else np.nan,
            "veto_sl_rate": veto_sl,
            "veto_sl_enrichment_x": enrich,
        },
        "overlay": om,
        "gates": gates,
        "top_univariate": uni.head(10).to_dict("records"),
        "top_coefficients": coef_summary.head(10).to_dict("records"),
        "governance": {
            "new_market_data": False,
            "independent_oos": False,
            "baseline_retuned": False,
            "threshold_search": False,
            "feature_subset_search": False,
            "reclaimed_signals_simulated": False,
            "warning_min_lead_ms": MIN_LEAD_MS,
        },
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# GC_XAU_D075_PREFILL_WARNING_GATE_LAB_016", "", f"**Status: {status}**", "",
        "Causal historical discovery at D0.75, strictly before frozen D1 touch.", "",
        "## Population", "",
        f"- Corrected accepted fills: **{len(feat)}**",
        f"- Executable D0.75 warnings: **{int(feat.warning_available.sum())} ({coverage*100:.1f}%)**",
        f"- Median warning lead to D1 fill: **{result['population']['median_warning_lead_to_fill_sec']:.3f}s**" if len(eligible) else "- No eligible warnings",
        f"- P10 warning lead: **{result['population']['p10_warning_lead_to_fill_sec']:.3f}s**" if len(eligible) else "",
        "", "## Walk-forward", "",
        f"- OOF warning-eligible fills: **{len(oof)}**",
        f"- SL AUC: **{auc:.3f}**" if np.isfinite(auc) else "- SL AUC: NA",
        f"- Veto: **{int(veto.sum())}/{len(oof)} ({float(veto.mean())*100:.1f}%)**" if len(oof) else "- Veto: NA",
        f"- Veto SL rate: **{veto_sl*100:.1f}%**, enrichment **{enrich:.2f}x**" if np.isfinite(enrich) else "- Veto SL enrichment: NA",
        "", "## Conservative overlay", "",
    ]
    if om:
        lines += [
            f"- Baseline -> overlay SumR: **{om['baseline_sum_r']:+.2f}R -> {om['overlay_sum_r']:+.2f}R**",
            f"- EV/original signal: **{om['baseline_ev_r_per_signal']:+.5f}R -> {om['overlay_ev_r_per_signal']:+.5f}R**",
            f"- MaxDD: **{om['baseline_maxdd_r']:.2f}R -> {om['overlay_maxdd_r']:.2f}R**",
            f"- Late-half overlay EV/signal: **{om['late_half_overlay_ev_r']:+.5f}R**",
        ]
    lines += ["", "## Gates", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", "## Strongest descriptive features", "", "| Feature | AUC* | Failure side |", "|---|---:|---|"]
    for _, r in uni.head(8).iterrows():
        lines.append(f"| {r.feature} | {r.auc_directionless:.3f} | {r.failure_direction} |")
    lines += ["", "`AUC*` is full-history descriptive only, not OOF evidence.", "", "A PASS is still not production promotion; reclaimed-signal state transitions are not simulated in LAB016."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "population": result["population"], "oof": result["oof"], "overlay": om, "gates": gates}, indent=2))


if __name__ == "__main__":
    main()
