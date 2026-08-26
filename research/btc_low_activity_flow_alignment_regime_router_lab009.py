import json
from pathlib import Path

import numpy as np
import pandas as pd

import btc_low_activity_flow_alignment_flip_lab008 as lab8

LAB = "BTC_LOW_ACTIVITY_FLOW_ALIGNMENT_REGIME_ROUTER_LAB_009"
DISCOVERY_YEARS = [2023, 2024, 2025]
INDEPENDENT_YEARS = [2019, 2020, 2021, 2022]
EXPOSED_YEAR = 2026
MIN_CELL_N = 30
MIN_YEAR_N = 8

# Frozen base selector carried forward from LAB008.
BASE_SELECTOR = "LOW2_X_ALIGN"

# Regime dimensions are broad, causal, pre-BOS, and intentionally distinct from
# the LOW2 activity features themselves. Quantile cuts are UNSUPERVISED and are
# frozen on 2023-2025 only.
REGIME_FEATURES = [
    "atr_regime_ratio",
    "trend_1d_signed_atr",
    "trend_7d_signed_atr",
    "eff_1d_abs",
    "range_regime_1d_vs_7d",
    "trades_regime_1d_vs_7d",
    "volume_regime_1d_vs_7d",
]

PAIR_FAMILIES = [
    ("atr_regime_ratio", "trend_7d_signed_atr"),
    ("atr_regime_ratio", "trend_1d_signed_atr"),
    ("range_regime_1d_vs_7d", "trend_7d_signed_atr"),
    ("trades_regime_1d_vs_7d", "trend_7d_signed_atr"),
    ("volume_regime_1d_vs_7d", "trend_7d_signed_atr"),
    ("eff_1d_abs", "trend_7d_signed_atr"),
    ("atr_regime_ratio", "range_regime_1d_vs_7d"),
]


def safe_ratio(a, b):
    return float(a / b) if np.isfinite(a) and np.isfinite(b) and abs(b) > 1e-12 else np.nan


def add_regime_features(m, events):
    x = events.copy()
    C = m.close.to_numpy(float)
    H = m.high.to_numpy(float)
    L = m.low.to_numpy(float)
    V = m.volume.to_numpy(float)
    TRD = m.trades.to_numpy(float)

    out = {k: [] for k in [
        "trend_1d_signed_atr", "trend_7d_signed_atr", "eff_1d_abs",
        "range_regime_1d_vs_7d", "trades_regime_1d_vs_7d", "volume_regime_1d_vs_7d"
    ]}

    for r in x.itertuples():
        i = int(r.bar_index)
        d = int(r.direction)
        a = float(r.atr)
        # 96 M15 bars = 1 day; 672 bars = 7 days. All windows end at i-1.
        if i < 768 or not np.isfinite(a) or a <= 0:
            for k in out:
                out[k].append(np.nan)
            continue

        s1 = slice(i-96, i)
        s7 = slice(i-672, i)
        prior7 = slice(i-768, i-96)

        p1 = d * (C[i-1] - C[i-96]) / a
        p7 = d * (C[i-1] - C[i-672]) / a
        path1 = np.abs(np.diff(C[s1])).sum() / a
        eff1 = abs(p1) / path1 if path1 > 1e-12 else 0.0

        r1 = np.mean(H[s1] - L[s1])
        r7 = np.mean(H[prior7] - L[prior7])
        t1 = np.mean(TRD[s1])
        t7 = np.mean(TRD[prior7])
        v1 = np.mean(V[s1])
        v7 = np.mean(V[prior7])

        out["trend_1d_signed_atr"].append(float(p1))
        out["trend_7d_signed_atr"].append(float(p7))
        out["eff_1d_abs"].append(float(eff1))
        out["range_regime_1d_vs_7d"].append(safe_ratio(r1, r7))
        out["trades_regime_1d_vs_7d"].append(safe_ratio(t1, t7))
        out["volume_regime_1d_vs_7d"].append(safe_ratio(v1, v7))

    for k, vals in out.items():
        x[k] = vals
    return x


def freeze_bins(discovery):
    cuts = {}
    for f in REGIME_FEATURES:
        z = pd.to_numeric(discovery[f], errors="coerce").dropna()
        q33 = float(z.quantile(1/3))
        q67 = float(z.quantile(2/3))
        cuts[f] = [q33, q67]
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
    for f in REGIME_FEATURES:
        x[f + "_BIN"] = [bin_one(float(v), cuts[f]) if pd.notna(v) else "NA" for v in x[f]]
    return x


def base_mask(d):
    # LAB008's more promising frozen branch: LOW2 + 12-bar aligned taker flow.
    return (d.low_activity_score >= 2) & (d.flow_align_12 == 1)


def metric(sample, mask):
    g = sample.loc[mask]
    if len(g) == 0:
        return dict(n=0, large=0, rate=np.nan, fail_rate=np.nan)
    return dict(n=int(len(g)), large=int(g.is_large.sum()), rate=float(g.is_large.mean()), fail_rate=float(g.is_fail.mean()))


def discovery_cells(discovery):
    base = discovery.loc[base_mask(discovery)].copy()
    base_rate = float(base.is_large.mean())
    rows = []

    # Single-dimension cells.
    for f in REGIME_FEATURES:
        bf = f + "_BIN"
        for b, g in base.groupby(bf):
            if b == "NA" or len(g) < MIN_CELL_N:
                continue
            year_stats = []
            for y in DISCOVERY_YEARS:
                gy = g[g.year == y]
                by = base[base.year == y]
                if len(gy) >= MIN_YEAR_N and len(by) > 0:
                    year_stats.append((y, len(gy), float(gy.is_large.mean()), float(by.is_large.mean())))
            if len(year_stats) < 2:
                continue
            lifts = [100*(a-b0) for _,_,a,b0 in year_stats]
            rows.append(dict(
                family=f,
                cell=str(b),
                dimensions=1,
                n=len(g),
                large=int(g.is_large.sum()),
                rate=float(g.is_large.mean()),
                base_rate=base_rate,
                lift_pp=100*(float(g.is_large.mean())-base_rate),
                years=len(year_stats),
                positive_years=sum(v>0 for v in lifts),
                min_year_lift_pp=min(lifts),
                mean_year_lift_pp=float(np.mean(lifts)),
                std_year_lift_pp=float(np.std(lifts)),
                robustness_score=float(100*(g.is_large.mean()-base_rate) + 0.50*min(lifts) - 0.25*np.std(lifts)),
            ))

    # Pre-specified two-dimensional families only; no exhaustive interaction mining.
    for f1, f2 in PAIR_FAMILIES:
        b1, b2 = f1 + "_BIN", f2 + "_BIN"
        for (v1, v2), g in base.groupby([b1, b2]):
            if "NA" in (v1, v2) or len(g) < MIN_CELL_N:
                continue
            year_stats = []
            for y in DISCOVERY_YEARS:
                gy = g[g.year == y]
                by = base[base.year == y]
                if len(gy) >= MIN_YEAR_N and len(by) > 0:
                    year_stats.append((y, len(gy), float(gy.is_large.mean()), float(by.is_large.mean())))
            if len(year_stats) < 2:
                continue
            lifts = [100*(a-b0) for _,_,a,b0 in year_stats]
            rows.append(dict(
                family=f1 + "__X__" + f2,
                cell=str(v1) + "|" + str(v2),
                dimensions=2,
                n=len(g),
                large=int(g.is_large.sum()),
                rate=float(g.is_large.mean()),
                base_rate=base_rate,
                lift_pp=100*(float(g.is_large.mean())-base_rate),
                years=len(year_stats),
                positive_years=sum(v>0 for v in lifts),
                min_year_lift_pp=min(lifts),
                mean_year_lift_pp=float(np.mean(lifts)),
                std_year_lift_pp=float(np.std(lifts)),
                robustness_score=float(100*(g.is_large.mean()-base_rate) + 0.50*min(lifts) - 0.25*np.std(lifts)),
            ))

    cells = pd.DataFrame(rows)
    if len(cells) == 0:
        return cells, None

    # Frozen selection criterion: prefer all-3-year transfer, then 2/3; reject
    # cells whose worst discovery year is catastrophically negative.
    eligible = cells[(cells.positive_years >= 2) & (cells.min_year_lift_pp >= -5.0)].copy()
    if len(eligible) == 0:
        eligible = cells[(cells.positive_years >= 2)].copy()
    if len(eligible) == 0:
        eligible = cells.copy()
    eligible = eligible.sort_values(["positive_years", "robustness_score", "n"], ascending=[False, False, False])
    winner = eligible.iloc[0].to_dict()
    return cells.sort_values("robustness_score", ascending=False), winner


def router_mask(d, winner):
    if winner is None:
        return pd.Series(False, index=d.index)
    fam = winner["family"]
    cell = winner["cell"]
    if "__X__" in fam:
        f1, f2 = fam.split("__X__")
        v1, v2 = cell.split("|")
        return (d[f1 + "_BIN"] == v1) & (d[f2 + "_BIN"] == v2)
    return d[fam + "_BIN"] == cell


def evaluate_sample(d, name, winner):
    bm = base_mask(d)
    rm = router_mask(d, winner)
    routed = bm & rm
    rejected = bm & (~rm)
    baseline = metric(d, pd.Series(True, index=d.index))
    base = metric(d, bm)
    r = metric(d, routed)
    q = metric(d, rejected)
    return [
        dict(sample=name, layer="ALL_EVENTS", **baseline),
        dict(sample=name, layer="LOW2_X_ALIGN_BASE", **base),
        dict(sample=name, layer="ROUTED", **r),
        dict(sample=name, layer="REJECTED", **q),
    ]


def yearly_eval(d, winner):
    rows = []
    for y, g in d.groupby("year"):
        bm = base_mask(g)
        rm = router_mask(g, winner)
        routed = bm & rm
        base = metric(g, bm)
        rr = metric(g, routed)
        allm = metric(g, pd.Series(True, index=g.index))
        rows.append(dict(
            year=int(y), all_n=allm["n"], all_rate=allm["rate"],
            base_n=base["n"], base_rate=base["rate"],
            routed_n=rr["n"], routed_rate=rr["rate"],
            routed_vs_base_pp=100*((rr["rate"] if np.isfinite(rr["rate"]) else np.nan) - (base["rate"] if np.isfinite(base["rate"]) else np.nan)),
            routed_vs_all_pp=100*((rr["rate"] if np.isfinite(rr["rate"]) else np.nan) - allm["rate"]),
        ))
    return pd.DataFrame(rows)


def main():
    m, sig, events = lab8.build_all_events()
    discovery = events[events.year.isin(DISCOVERY_YEARS)].copy()
    thr = lab8.freeze_thresholds(discovery)
    allx = lab8.apply_frozen_state(events, thr)
    allx = add_regime_features(m, allx)

    discovery = allx[allx.year.isin(DISCOVERY_YEARS)].copy()
    independent = allx[allx.year.isin(INDEPENDENT_YEARS)].copy()
    exposed = allx[allx.year == EXPOSED_YEAR].copy()

    cuts = freeze_bins(discovery)
    allx = apply_bins(allx, cuts)
    discovery = allx[allx.year.isin(DISCOVERY_YEARS)].copy()
    independent = allx[allx.year.isin(INDEPENDENT_YEARS)].copy()
    exposed = allx[allx.year == EXPOSED_YEAR].copy()

    cells, winner = discovery_cells(discovery)

    print("="*72)
    print(LAB)
    print("EVENTS", len(allx), "LARGE", int(allx.is_large.sum()), "RATE", round(100*allx.is_large.mean(), 3))
    print("DISCOVERY", len(discovery), "INDEPENDENT", len(independent), "EXPOSED2026", len(exposed))
    print("BASE SELECTOR = LOW_ACTIVITY_SCORE>=2 AND FLOW_DELTA_12>0")
    print("\nFROZEN UNSUPERVISED REGIME CUTS")
    print(json.dumps(cuts, indent=2))
    print("\nDISCOVERY TOP REGIME CELLS")
    print(cells.head(20).to_string(index=False) if len(cells) else "NO CELLS")
    print("\nFROZEN WINNER")
    print(json.dumps(winner, indent=2, default=float) if winner else "NONE")

    rows = []
    rows += evaluate_sample(discovery, "DISCOVERY_2023_2025", winner)
    rows += evaluate_sample(independent, "INDEPENDENT_2019_2022", winner)
    rows += evaluate_sample(exposed, "EXPOSED_2026", winner)
    evaldf = pd.DataFrame(rows)
    print("\nROUTER EVALUATION")
    print(evaldf.to_string(index=False))

    yearly = yearly_eval(allx, winner)
    print("\nYEARLY TRANSFER")
    print(yearly.to_string(index=False))

    # Critical independent verdict.
    ii = evaldf[(evaldf.sample == "INDEPENDENT_2019_2022") & (evaldf.layer == "LOW2_X_ALIGN_BASE")].iloc[0]
    ir = evaldf[(evaldf.sample == "INDEPENDENT_2019_2022") & (evaldf.layer == "ROUTED")].iloc[0]
    ind_increment = 100*(ir.rate - ii.rate) if np.isfinite(ir.rate) and np.isfinite(ii.rate) else np.nan
    positive_ind_years = int((yearly[yearly.year.isin(INDEPENDENT_YEARS)].routed_vs_base_pp > 0).sum())

    verdict = {
        "lab": LAB,
        "base_selector": "LOW_ACTIVITY_SCORE>=2 AND FLOW_DELTA_12>0",
        "router_selection": "2023-2025 only; broad pre-specified causal regime families; unsupervised tercile cuts",
        "winner": winner,
        "regime_cuts": cuts,
        "independent_base_n": int(ii.n),
        "independent_base_rate": float(ii.rate),
        "independent_routed_n": int(ir.n),
        "independent_routed_rate": float(ir.rate) if np.isfinite(ir.rate) else None,
        "independent_increment_pp": float(ind_increment) if np.isfinite(ind_increment) else None,
        "independent_positive_years": positive_ind_years,
        "exposed_2026_diagnostic_only": True,
    }
    print("\nVERDICT")
    print(json.dumps(verdict, indent=2, default=float))

    out = Path("lab009")
    out.mkdir(exist_ok=True)
    allx.to_csv(out / f"{LAB}_EVENTS.csv", index=False)
    cells.to_csv(out / f"{LAB}_DISCOVERY_CELLS.csv", index=False)
    evaldf.to_csv(out / f"{LAB}_EVALUATION.csv", index=False)
    yearly.to_csv(out / f"{LAB}_YEARLY.csv", index=False)
    with open(out / "verdict.json", "w") as f:
        json.dump(verdict, f, indent=2, default=float)

    report = [
        f"# {LAB}", "",
        "Purpose: determine whether a broad pre-BOS regime can explain when the frozen LAB008 LOW ACTIVITY + FLOW ALIGNMENT selector works and when it fails.", "",
        "Base selector is frozen: LOW_ACTIVITY_SCORE >= 2 AND FLOW_DELTA_12 > 0.",
        "Router is discovered only on 2023-2025. 2019-2022 remains the independent replication set. 2026 is diagnostic only because it was already exposed in LAB007/008.", "",
        "## Frozen winner", "", "```json", json.dumps(winner, indent=2, default=float) if winner else "null", "```", "",
        "## Regime cuts", "", "```json", json.dumps(cuts, indent=2), "```", "",
        "## Evaluation", "", evaldf.to_markdown(index=False), "",
        "## Yearly transfer", "", yearly.to_markdown(index=False), "",
        "## Top discovery cells", "", cells.head(20).to_markdown(index=False) if len(cells) else "No eligible cells", "",
        "## Verdict", "", "```json", json.dumps(verdict, indent=2, default=float), "```",
    ]
    (out / f"{LAB}_REPORT.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
