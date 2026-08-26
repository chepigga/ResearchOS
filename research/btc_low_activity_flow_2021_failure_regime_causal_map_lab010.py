import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

import btc_low_activity_flow_alignment_flip_lab008 as lab8

LAB = "BTC_LOW_ACTIVITY_FLOW_2021_FAILURE_REGIME_CAUSAL_MAP_LAB_010"
FAIL_YEAR = 2021
# Primary comparator is deliberately broad: every non-sparse, non-exposed year
# around the failure year. This avoids defining the reference only from winners.
REFERENCE_YEARS = [2020, 2022, 2023, 2024, 2025]
# Secondary outcome-informed comparator is diagnostic only, inherited from LAB009.
HEALTHY_DIAGNOSTIC_YEARS = [2020, 2023, 2024, 2025]
SPARSE_DIAGNOSTIC_YEAR = 2019
EXPOSED_DIAGNOSTIC_YEAR = 2026

BARS_1D = 96
BARS_7D = 7 * BARS_1D
BARS_30D = 30 * BARS_1D
BARS_PREV23D = BARS_30D - BARS_7D

FEATURES = [
    "rv_7d_daily_pct",
    "rv_prev23d_daily_pct",
    "rv_7d_vs_prev23d",
    "range_7d_vs_prev23d",
    "trades_7d_vs_prev23d",
    "volume_7d_vs_prev23d",
    "avg_trade_7d_vs_prev23d",
    "trend_eff_7d",
    "trend_eff_30d",
    "trend_signed_7d_atr",
    "trend_signed_30d_atr",
    "directional_position_30d",
    "direction_bar_share_7d",
    "direction_bar_share_30d",
    "flow_delta_7d",
    "flow_delta_prev23d",
    "flow_shift_7d_minus_prev23d",
]

PAIR_FAMILIES = [
    ("rv_7d_vs_prev23d", "trend_eff_7d"),
    ("rv_7d_daily_pct", "trend_signed_7d_atr"),
    ("range_7d_vs_prev23d", "trend_eff_7d"),
    ("trades_7d_vs_prev23d", "volume_7d_vs_prev23d"),
    ("flow_delta_7d", "trend_signed_7d_atr"),
    ("flow_shift_7d_minus_prev23d", "directional_position_30d"),
]


def safe_ratio(a, b):
    return float(a / b) if np.isfinite(a) and np.isfinite(b) and abs(b) > 1e-12 else np.nan


def dailyized_rv_pct(close):
    c = np.asarray(close, float)
    if len(c) < 3 or np.any(c <= 0):
        return np.nan
    r = np.diff(np.log(c))
    if len(r) == 0:
        return np.nan
    return float(np.sqrt(np.mean(r * r) * BARS_1D) * 100.0)


def trend_eff(close):
    c = np.asarray(close, float)
    if len(c) < 2:
        return np.nan
    path = float(np.abs(np.diff(c)).sum())
    return float(abs(c[-1] - c[0]) / path) if path > 1e-12 else 0.0


def directional_flow_delta(volume, taker_ratio, direction):
    v = np.asarray(volume, float)
    q = np.clip(np.asarray(taker_ratio, float), 0.0, 1.0)
    buy = v * q
    sell = v - buy
    future = buy if direction > 0 else sell
    counter = sell if direction > 0 else buy
    den = float(v.sum())
    return float((future.sum() - counter.sum()) / den) if den > 1e-12 else np.nan


def add_slow_regime_features(m, events):
    x = events.copy()
    C = m.close.to_numpy(float)
    H = m.high.to_numpy(float)
    L = m.low.to_numpy(float)
    V = m.volume.to_numpy(float)
    TRD = m.trades.to_numpy(float)
    TKR = m.taker_ratio.to_numpy(float)
    AVG = m.avg_trade.to_numpy(float)

    out = {f: [] for f in FEATURES}

    for r in x.itertuples():
        i = int(r.bar_index)
        d = int(r.direction)
        atr = float(r.atr)

        if i < BARS_30D + 1 or not np.isfinite(atr) or atr <= 0:
            for f in FEATURES:
                out[f].append(np.nan)
            continue

        s7 = slice(i - BARS_7D, i)          # all windows end at i-1
        sp = slice(i - BARS_30D, i - BARS_7D)
        s30 = slice(i - BARS_30D, i)

        c7, cp, c30 = C[s7], C[sp], C[s30]
        h7, hp = H[s7], H[sp]
        l7, lp = L[s7], L[sp]
        v7, vp = V[s7], V[sp]
        t7, tp = TRD[s7], TRD[sp]
        a7, ap = AVG[s7], AVG[sp]

        rv7 = dailyized_rv_pct(c7)
        rvp = dailyized_rv_pct(cp)
        range7 = np.mean((h7 - l7) / np.maximum(c7, 1e-12))
        rangep = np.mean((hp - lp) / np.maximum(cp, 1e-12))

        tr7 = d * (c7[-1] - c7[0]) / atr
        tr30 = d * (c30[-1] - c30[0]) / atr

        hi30 = float(np.max(H[s30]))
        lo30 = float(np.min(L[s30]))
        span30 = hi30 - lo30
        if span30 > 1e-12:
            pos30 = (c30[-1] - lo30) / span30 if d > 0 else (hi30 - c30[-1]) / span30
        else:
            pos30 = 0.5

        r7 = np.diff(c7)
        r30 = np.diff(c30)
        share7 = float(np.mean(d * r7 > 0)) if len(r7) else np.nan
        share30 = float(np.mean(d * r30 > 0)) if len(r30) else np.nan

        fd7 = directional_flow_delta(v7, TKR[s7], d)
        fdp = directional_flow_delta(vp, TKR[sp], d)

        vals = {
            "rv_7d_daily_pct": rv7,
            "rv_prev23d_daily_pct": rvp,
            "rv_7d_vs_prev23d": safe_ratio(rv7, rvp),
            "range_7d_vs_prev23d": safe_ratio(float(range7), float(rangep)),
            "trades_7d_vs_prev23d": safe_ratio(float(np.mean(t7)), float(np.mean(tp))),
            "volume_7d_vs_prev23d": safe_ratio(float(np.mean(v7)), float(np.mean(vp))),
            "avg_trade_7d_vs_prev23d": safe_ratio(float(np.mean(a7)), float(np.mean(ap))),
            "trend_eff_7d": trend_eff(c7),
            "trend_eff_30d": trend_eff(c30),
            "trend_signed_7d_atr": float(tr7),
            "trend_signed_30d_atr": float(tr30),
            "directional_position_30d": float(pos30),
            "direction_bar_share_7d": share7,
            "direction_bar_share_30d": share30,
            "flow_delta_7d": fd7,
            "flow_delta_prev23d": fdp,
            "flow_shift_7d_minus_prev23d": float(fd7 - fdp) if np.isfinite(fd7) and np.isfinite(fdp) else np.nan,
        }
        for f in FEATURES:
            out[f].append(vals[f])

    for f, vals in out.items():
        x[f] = vals
    return x


def base_mask(d):
    return (d.low_activity_score >= 2) & (d.flow_align_12 == 1)


def wilson(k, n, z=1.959963984540054):
    if n <= 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    cen = (p + z * z / (2 * n)) / den
    half = z * np.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return float(cen - half), float(cen + half)


def sample_metric(g):
    n = int(len(g))
    large = int(g.is_large.sum()) if n else 0
    fail = int(g.is_fail.sum()) if n else 0
    lo, hi = wilson(large, n)
    return dict(
        n=n,
        large=large,
        large_rate=float(large / n) if n else np.nan,
        large_ci_lo=lo,
        large_ci_hi=hi,
        fail=fail,
        fail_rate=float(fail / n) if n else np.nan,
    )


def freeze_bins(reference):
    cuts = {}
    for f in FEATURES:
        z = pd.to_numeric(reference[f], errors="coerce").dropna()
        cuts[f] = [float(z.quantile(1 / 3)), float(z.quantile(2 / 3))]
    return cuts


def bin_one(v, cuts):
    if not np.isfinite(v):
        return "NA"
    lo, hi = cuts
    if v <= lo:
        return "LOW"
    if v <= hi:
        return "MID"
    return "HIGH"


def apply_bins(d, cuts):
    x = d.copy()
    for f in FEATURES:
        x[f + "_BIN"] = [bin_one(float(v), cuts[f]) if pd.notna(v) else "NA" for v in x[f]]
    return x


def standardized_differences(failure, reference):
    rows = []
    for f in FEATURES:
        a = pd.to_numeric(failure[f], errors="coerce").dropna().to_numpy(float)
        b = pd.to_numeric(reference[f], errors="coerce").dropna().to_numpy(float)
        if len(a) < 3 or len(b) < 3:
            continue
        va = np.var(a, ddof=1) if len(a) > 1 else 0.0
        vb = np.var(b, ddof=1) if len(b) > 1 else 0.0
        pooled = np.sqrt((va + vb) / 2.0)
        smd = (np.mean(a) - np.mean(b)) / pooled if pooled > 1e-12 else np.nan
        rows.append(dict(
            feature=f,
            fail_n=len(a), ref_n=len(b),
            fail_mean=float(np.mean(a)), ref_mean=float(np.mean(b)),
            fail_median=float(np.median(a)), ref_median=float(np.median(b)),
            smd=float(smd) if np.isfinite(smd) else np.nan,
            abs_smd=float(abs(smd)) if np.isfinite(smd) else np.nan,
        ))
    return pd.DataFrame(rows).sort_values("abs_smd", ascending=False)


def feature_bin_map(failure, reference, cuts):
    rows = []
    for f in FEATURES:
        bf = f + "_BIN"
        for cell in ["LOW", "MID", "HIGH"]:
            fg = failure[failure[bf] == cell]
            rg = reference[reference[bf] == cell]
            fm = sample_metric(fg)
            rm = sample_metric(rg)
            rows.append(dict(
                feature=f, cell=cell,
                fail_n=fm["n"], fail_large=fm["large"], fail_large_rate=fm["large_rate"],
                ref_n=rm["n"], ref_large=rm["large"], ref_large_rate=rm["large_rate"],
                fail_occupancy=float(len(fg) / len(failure)) if len(failure) else np.nan,
                ref_occupancy=float(len(rg) / len(reference)) if len(reference) else np.nan,
                occupancy_diff_pp=100.0 * ((len(fg) / len(failure)) - (len(rg) / len(reference))) if len(failure) and len(reference) else np.nan,
                conditional_gap_pp=100.0 * (fm["large_rate"] - rm["large_rate"]) if np.isfinite(fm["large_rate"]) and np.isfinite(rm["large_rate"]) else np.nan,
                cut_lo=cuts[f][0], cut_hi=cuts[f][1],
            ))
    return pd.DataFrame(rows)


def decomposition_from_map(failure, reference, fmap):
    actual = float(failure.is_large.mean())
    ref_rate = float(reference.is_large.mean())
    rows = []
    for f in FEATURES:
        z = fmap[fmap.feature == f].copy()
        usable = z[(z.fail_n > 0) & (z.ref_n > 0) & z.ref_large_rate.notna()]
        covered = int(usable.fail_n.sum())
        if covered == 0:
            continue
        weights = usable.fail_n.to_numpy(float) / covered
        expected = float(np.sum(weights * usable.ref_large_rate.to_numpy(float)))
        gap = ref_rate - actual
        explained = (ref_rate - expected) / gap if abs(gap) > 1e-12 else np.nan
        rows.append(dict(
            family=f,
            dimensions=1,
            fail_rate=actual,
            ref_rate=ref_rate,
            expected_fail_rate_if_ref_cell_rates=expected,
            occupancy_effect_pp=100.0 * (expected - ref_rate),
            residual_failure_pp=100.0 * (actual - expected),
            total_failure_gap_pp=100.0 * (actual - ref_rate),
            occupancy_explained_fraction=float(explained) if np.isfinite(explained) else np.nan,
            fail_coverage=covered / len(failure),
        ))
    return pd.DataFrame(rows).sort_values("occupancy_explained_fraction", ascending=False)


def pair_maps(failure, reference):
    rows = []
    dec = []
    actual = float(failure.is_large.mean())
    ref_rate = float(reference.is_large.mean())

    for f1, f2 in PAIR_FAMILIES:
        b1, b2 = f1 + "_BIN", f2 + "_BIN"
        fam = f1 + "__X__" + f2
        local = []
        for c1 in ["LOW", "MID", "HIGH"]:
            for c2 in ["LOW", "MID", "HIGH"]:
                fg = failure[(failure[b1] == c1) & (failure[b2] == c2)]
                rg = reference[(reference[b1] == c1) & (reference[b2] == c2)]
                fm, rm = sample_metric(fg), sample_metric(rg)
                rec = dict(
                    family=fam, cell=c1 + "|" + c2,
                    fail_n=fm["n"], fail_large=fm["large"], fail_large_rate=fm["large_rate"],
                    ref_n=rm["n"], ref_large=rm["large"], ref_large_rate=rm["large_rate"],
                    fail_occupancy=float(len(fg) / len(failure)) if len(failure) else np.nan,
                    ref_occupancy=float(len(rg) / len(reference)) if len(reference) else np.nan,
                    conditional_gap_pp=100.0 * (fm["large_rate"] - rm["large_rate"]) if np.isfinite(fm["large_rate"]) and np.isfinite(rm["large_rate"]) else np.nan,
                )
                rows.append(rec)
                local.append(rec)

        z = pd.DataFrame(local)
        usable = z[(z.fail_n > 0) & (z.ref_n >= 5) & z.ref_large_rate.notna()]
        covered = int(usable.fail_n.sum())
        if covered:
            w = usable.fail_n.to_numpy(float) / covered
            expected = float(np.sum(w * usable.ref_large_rate.to_numpy(float)))
            gap = ref_rate - actual
            explained = (ref_rate - expected) / gap if abs(gap) > 1e-12 else np.nan
            dec.append(dict(
                family=fam, dimensions=2,
                fail_rate=actual, ref_rate=ref_rate,
                expected_fail_rate_if_ref_cell_rates=expected,
                occupancy_effect_pp=100.0 * (expected - ref_rate),
                residual_failure_pp=100.0 * (actual - expected),
                total_failure_gap_pp=100.0 * (actual - ref_rate),
                occupancy_explained_fraction=float(explained) if np.isfinite(explained) else np.nan,
                fail_coverage=covered / len(failure),
            ))

    return pd.DataFrame(rows), pd.DataFrame(dec).sort_values("occupancy_explained_fraction", ascending=False)


def fisher_compare(a, b, label):
    am, bm = sample_metric(a), sample_metric(b)
    table = [[am["large"], am["n"] - am["large"]], [bm["large"], bm["n"] - bm["large"]]]
    odds, p = fisher_exact(table, alternative="two-sided") if am["n"] and bm["n"] else (np.nan, np.nan)
    return dict(
        comparison=label,
        fail_n=am["n"], fail_large=am["large"], fail_rate=am["large_rate"],
        ref_n=bm["n"], ref_large=bm["large"], ref_rate=bm["large_rate"],
        gap_pp=100.0 * (am["large_rate"] - bm["large_rate"]),
        fisher_odds_ratio=float(odds) if np.isfinite(odds) else None,
        fisher_p=float(p) if np.isfinite(p) else None,
    )


def main():
    m, sig, events = lab8.build_all_events()

    discovery = events[events.year.isin([2023, 2024, 2025])].copy()
    thr = lab8.freeze_thresholds(discovery)
    allx = lab8.apply_frozen_state(events, thr)
    allx = add_slow_regime_features(m, allx)
    allx["base_selector"] = base_mask(allx).astype(int)

    base = allx[base_mask(allx)].copy()
    failure = base[base.year == FAIL_YEAR].dropna(subset=FEATURES).copy()
    reference = base[base.year.isin(REFERENCE_YEARS)].dropna(subset=FEATURES).copy()
    healthy = base[base.year.isin(HEALTHY_DIAGNOSTIC_YEARS)].dropna(subset=FEATURES).copy()
    year2022 = base[base.year == 2022].dropna(subset=FEATURES).copy()

    cuts = freeze_bins(reference)
    allx = apply_bins(allx, cuts)
    base = allx[base_mask(allx)].copy()
    failure = base[base.year == FAIL_YEAR].dropna(subset=FEATURES).copy()
    reference = base[base.year.isin(REFERENCE_YEARS)].dropna(subset=FEATURES).copy()
    healthy = base[base.year.isin(HEALTHY_DIAGNOSTIC_YEARS)].dropna(subset=FEATURES).copy()
    year2022 = base[base.year == 2022].dropna(subset=FEATURES).copy()

    yearly_rows = []
    for y, g in base.groupby("year"):
        r = sample_metric(g)
        r["year"] = int(y)
        yearly_rows.append(r)
    yearly = pd.DataFrame(yearly_rows).sort_values("year")

    comparisons = pd.DataFrame([
        fisher_compare(failure, reference, "2021_vs_broad_reference_2020_2022_2025"),
        fisher_compare(failure, healthy, "2021_vs_healthy_diagnostic_2020_2023_2025"),
        fisher_compare(failure, year2022, "2021_vs_2022_shadow"),
    ])

    smd = standardized_differences(failure, reference)
    fmap = feature_bin_map(failure, reference, cuts)
    dec1 = decomposition_from_map(failure, reference, fmap)
    pmap, dec2 = pair_maps(failure, reference)

    print("=" * 84)
    print(LAB)
    print("EVENTS", len(allx), "BASE LOW2_X_ALIGN", len(base))
    print("FAIL YEAR", FAIL_YEAR, sample_metric(failure))
    print("REFERENCE YEARS", REFERENCE_YEARS, sample_metric(reference))
    print("HEALTHY DIAGNOSTIC YEARS", HEALTHY_DIAGNOSTIC_YEARS, sample_metric(healthy))
    print("\nIMPORTANT: all slow-regime windows end at signal bar i-1; BOS bar is excluded.")
    print("Funding/OI were not used because they are not present in the frozen btc_15m input bundle.")

    print("\nBASE SELECTOR YEARLY")
    print(yearly.to_string(index=False))
    print("\n2021 SIGNIFICANCE CHECKS")
    print(comparisons.to_string(index=False))
    print("\nTOP STRUCTURAL DIFFERENCES 2021 VS BROAD REFERENCE")
    print(smd.head(12).to_string(index=False))
    print("\nSINGLE-FEATURE OCCUPANCY / CONDITIONAL DECOMPOSITION")
    print(dec1.head(12).to_string(index=False))
    print("\nPAIR OCCUPANCY / CONDITIONAL DECOMPOSITION")
    print(dec2.to_string(index=False))

    # Strongest cells by 2021 over-occupancy, regardless of outcome, then show
    # their conditional LARGE gap. This is the causal map, not a selector search.
    fmap2 = fmap.copy()
    fmap2["abs_occupancy_diff_pp"] = fmap2.occupancy_diff_pp.abs()
    print("\nMOST DIFFERENT 2021 REGIME CELLS")
    print(fmap2.sort_values("abs_occupancy_diff_pp", ascending=False).head(20).to_string(index=False))

    best1 = dec1.iloc[0].to_dict() if len(dec1) else None
    best2 = dec2.iloc[0].to_dict() if len(dec2) else None
    top_smd = smd.iloc[0].to_dict() if len(smd) else None

    max_explained = max(
        [v for v in [best1.get("occupancy_explained_fraction") if best1 else np.nan,
                     best2.get("occupancy_explained_fraction") if best2 else np.nan]
         if np.isfinite(v)] or [np.nan]
    )

    if np.isfinite(max_explained) and max_explained >= 0.60:
        verdict_class = "SLOW_REGIME_OCCUPANCY_PLAUSIBLY_EXPLAINS_MAJORITY_OF_2021_GAP"
    elif np.isfinite(max_explained) and max_explained >= 0.25:
        verdict_class = "PARTIAL_SLOW_REGIME_EXPLANATION__LARGE_RESIDUAL_REMAINS"
    else:
        verdict_class = "2021_FAILURE_NOT_EXPLAINED_BY_TESTED_SLOW_REGIME_OCCUPANCY"

    verdict = {
        "lab": LAB,
        "question": "Why did frozen LOW_ACTIVITY>=2 + FLOW_ALIGN_12 collapse in 2021?",
        "base_selector": "LOW_ACTIVITY_SCORE>=2 AND FLOW_DELTA_12>0",
        "target": "clean MFE >= 2.5R within 32 M15 bars before structural SL",
        "failure_year": FAIL_YEAR,
        "reference_years_primary": REFERENCE_YEARS,
        "healthy_reference_diagnostic_only": HEALTHY_DIAGNOSTIC_YEARS,
        "causality": "all regime features use only bars ending at i-1; BOS candle excluded; no post-BOS variables",
        "regime_bins": "unsupervised terciles frozen on broad reference base-selector events; LARGE labels not used to set cuts",
        "funding_open_interest_used": False,
        "funding_open_interest_note": "not present in frozen btc_15m input bundle / repository search",
        "comparisons": comparisons.to_dict(orient="records"),
        "strongest_structural_difference": top_smd,
        "best_single_feature_decomposition": best1,
        "best_pair_decomposition": best2,
        "verdict_class": verdict_class,
        "interpretation_rule": "occupancy effect asks whether 2021 visited different slow regimes; residual failure asks whether 2021 still failed inside comparable regimes",
        "warning": "This lab diagnoses a historical regime break. It does not authorize a production router or EA rule by itself.",
    }

    out = Path("lab010")
    out.mkdir(exist_ok=True)
    allx.to_csv(out / f"{LAB}_EVENTS.csv", index=False)
    yearly.to_csv(out / f"{LAB}_YEARLY.csv", index=False)
    comparisons.to_csv(out / f"{LAB}_COMPARISONS.csv", index=False)
    smd.to_csv(out / f"{LAB}_STRUCTURAL_DIFFERENCES.csv", index=False)
    fmap.to_csv(out / f"{LAB}_FEATURE_BIN_MAP.csv", index=False)
    dec1.to_csv(out / f"{LAB}_SINGLE_FEATURE_DECOMPOSITION.csv", index=False)
    pmap.to_csv(out / f"{LAB}_PAIR_CELL_MAP.csv", index=False)
    dec2.to_csv(out / f"{LAB}_PAIR_DECOMPOSITION.csv", index=False)
    with open(out / "verdict.json", "w") as f:
        json.dump(verdict, f, indent=2, default=float)

    print("\nVERDICT")
    print(json.dumps(verdict, indent=2, default=float))


if __name__ == "__main__":
    main()
