#!/usr/bin/env python3
"""
BTC_BUY_P12_FLOW_SPONSORSHIP_BROAD_SHELL_REPLICATION_LAB_014

Question
--------
Does the frozen BUY P12 aggressive-flow sponsorship effect from LAB013 replicate
across progressively broader pre-BOS shells?

Frozen target
-------------
clean MFE >= 2.5R within 32 M15 bars before structural SL.

Frozen predictor
----------------
P12 persistence only. P12 is computed causally from bars ending at i-1; BOS and
post-BOS bars are excluded from the predictor.

Frozen shells
-------------
A) ALL_BUY_BOS
B) LOW_ACTIVITY_BUY_BOS
C) LOW_ACTIVITY_PLUS_FLOW_ALIGN_BUY_BOS

The purpose is replication/interaction localization, not threshold mining.
2021 remains discovery-only and is excluded from independent threshold training.
2026 is pseudo-forward diagnostic.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

LAB = "BTC_BUY_P12_FLOW_SPONSORSHIP_BROAD_SHELL_REPLICATION_LAB_014"
DISCOVERY_YEAR = 2021
INDEPENDENT_YEARS = [2020, 2022, 2023, 2024, 2025]
PSEUDO_FORWARD_YEAR = 2026
LOW_Q = 0.33
OUTDIR = Path("lab014")
OUTDIR.mkdir(parents=True, exist_ok=True)

# We deliberately import the frozen causal event/feature builder from LAB013.
# This ensures identical BOS, target, LOW_ACTIVITY_SCORE, FLOW_DELTA_12 and P12 definitions.
try:
    import btc_flow_sponsorship_persistence_directional_ablation_lab013 as lab013
except Exception as e:
    print("ERROR: LAB014 requires research/btc_flow_sponsorship_persistence_directional_ablation_lab013.py")
    raise


def safe_rate(s: pd.Series) -> float:
    return float(s.mean()) if len(s) else float("nan")


def odds_fisher(veto: pd.DataFrame, keep: pd.DataFrame, col: str, alternative: str) -> Tuple[float, float]:
    va = int(veto[col].sum())
    vb = int(len(veto) - va)
    ka = int(keep[col].sum())
    kb = int(len(keep) - ka)
    if min(len(veto), len(keep)) == 0:
        return float("nan"), float("nan")
    odds, p = fisher_exact([[va, vb], [ka, kb]], alternative=alternative)
    return float(odds), float(p)


def discover_event_builder():
    # LAB013 versions may expose a different public helper name; resolve conservatively.
    candidates = [
        "build_events",
        "build_dataset",
        "prepare_events",
        "make_events",
        "load_and_build_events",
    ]
    for name in candidates:
        fn = getattr(lab013, name, None)
        if callable(fn):
            return fn
    return None


def load_lab013_artifact_if_available() -> pd.DataFrame | None:
    # Useful if a future workflow copies prior event outputs into cwd.
    candidates = [
        Path("lab013/events.csv"),
        Path("lab013/LAB013_EVENTS.csv"),
        Path("lab013/btc_flow_sponsorship_persistence_directional_ablation_lab013_events.csv"),
    ]
    for p in candidates:
        if p.exists():
            df = pd.read_csv(p)
            return df
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    # Canonical aliases observed/expected from lineage. Only exact or unambiguous aliases are used.
    aliases = {
        "direction": ["direction", "dir"],
        "year": ["year"],
        "large": ["large", "is_large", "target_large", "label_large"],
        "fail": ["fail", "is_fail", "target_fail", "label_fail"],
        "p12": ["p12", "P12", "persistence_12", "flow_p12", "flow_persistence_12"],
        "low_activity_score": ["low_activity_score", "LOW_ACTIVITY_SCORE"],
        "flow_delta_12": ["flow_delta_12", "FLOW_DELTA_12"],
    }
    rename = {}
    cols = {c.lower(): c for c in x.columns}
    for canon, cand in aliases.items():
        if canon in x.columns:
            continue
        found = None
        for c in cand:
            if c in x.columns:
                found = c
                break
            if c.lower() in cols:
                found = cols[c.lower()]
                break
        if found:
            rename[found] = canon
    x = x.rename(columns=rename)
    missing = [c for c in aliases if c not in x.columns]
    if missing:
        raise RuntimeError(f"LAB014 missing frozen LAB013 columns: {missing}. Available: {list(x.columns)}")
    x["direction"] = pd.to_numeric(x["direction"], errors="coerce")
    x["year"] = pd.to_numeric(x["year"], errors="coerce").astype("Int64")
    for c in ["large", "fail"]:
        x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0).astype(int)
    for c in ["p12", "low_activity_score", "flow_delta_12"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["direction", "year", "p12", "low_activity_score", "flow_delta_12"])
    return x


def build_events() -> pd.DataFrame:
    # Prefer LAB013 internal builder, which preserves exact lineage.
    fn = discover_event_builder()
    if fn is not None:
        try:
            out = fn()
            if isinstance(out, tuple):
                dfs = [z for z in out if isinstance(z, pd.DataFrame)]
                if dfs:
                    out = max(dfs, key=len)
            if isinstance(out, pd.DataFrame):
                return normalize_columns(out)
        except TypeError:
            pass

    prior = load_lab013_artifact_if_available()
    if prior is not None:
        return normalize_columns(prior)

    # Last-resort: execute LAB013 in-process and inspect common globals. This remains
    # deterministic and uses the same downloaded frozen data in the workflow.
    import runpy
    ns = runpy.run_path(str(Path(lab013.__file__)), run_name="lab013_embedded")
    for name in ["events", "df_events", "all_events", "event_df", "ev"]:
        obj = ns.get(name)
        if isinstance(obj, pd.DataFrame) and len(obj):
            try:
                return normalize_columns(obj)
            except Exception:
                continue
    # Search any DataFrame with the canonical feature columns.
    for obj in ns.values():
        if isinstance(obj, pd.DataFrame) and len(obj):
            try:
                return normalize_columns(obj)
            except Exception:
                continue
    raise RuntimeError("Could not obtain LAB013 causal event table. Expose build_events() or an events DataFrame in LAB013.")


def shell_mask(df: pd.DataFrame, shell: str) -> pd.Series:
    buy = df["direction"].astype(int).eq(1)
    if shell == "ALL_BUY_BOS":
        return buy
    if shell == "LOW_ACTIVITY_BUY_BOS":
        return buy & df["low_activity_score"].ge(2)
    if shell == "LOW_ACTIVITY_PLUS_FLOW_ALIGN_BUY_BOS":
        return buy & df["low_activity_score"].ge(2) & df["flow_delta_12"].gt(0)
    raise KeyError(shell)


SHELLS = [
    "ALL_BUY_BOS",
    "LOW_ACTIVITY_BUY_BOS",
    "LOW_ACTIVITY_PLUS_FLOW_ALIGN_BUY_BOS",
]


def train_cutoff(train_shell: pd.DataFrame) -> float:
    if len(train_shell) < 20:
        return float("nan")
    return float(train_shell["p12"].quantile(LOW_Q))


def evaluate(test: pd.DataFrame, cutoff: float, shell: str, year: int, fold_type: str) -> Dict:
    d = test[shell_mask(test, shell)].copy()
    supported = d[np.isfinite(d["p12"])].copy()
    if not math.isfinite(cutoff):
        veto = supported.iloc[0:0]
        keep = supported.iloc[0:0]
    else:
        veto = supported[supported["p12"] <= cutoff]
        keep = supported[supported["p12"] > cutoff]

    baseline_large = safe_rate(supported["large"])
    baseline_fail = safe_rate(supported["fail"])
    veto_large = safe_rate(veto["large"])
    keep_large = safe_rate(keep["large"])
    veto_fail = safe_rate(veto["fail"])
    keep_fail = safe_rate(keep["fail"])
    total_large = int(supported["large"].sum())
    keep_large_n = int(keep["large"].sum())
    large_retention = keep_large_n / total_large if total_large else float("nan")
    freq_ret = len(keep) / len(supported) if len(supported) else float("nan")
    large_gap = (veto_large - keep_large) * 100 if np.isfinite(veto_large) and np.isfinite(keep_large) else float("nan")
    fail_gap = (veto_fail - keep_fail) * 100 if np.isfinite(veto_fail) and np.isfinite(keep_fail) else float("nan")
    valid = len(veto) >= 4 and len(keep) >= 8
    # Same conceptual gate as LAB013, but broad-shell replication prioritizes effect direction.
    pass_year = bool(valid and large_gap <= -7.0 and fail_gap >= 5.0)
    return {
        "shell": shell,
        "year": year,
        "fold_type": fold_type,
        "cutoff_q33": cutoff,
        "test_n": int(len(d)),
        "supported_n": int(len(supported)),
        "baseline_large_rate": baseline_large,
        "baseline_fail_rate": baseline_fail,
        "veto_n": int(len(veto)),
        "veto_large_rate": veto_large,
        "veto_fail_rate": veto_fail,
        "keep_n": int(len(keep)),
        "keep_large_rate": keep_large,
        "keep_fail_rate": keep_fail,
        "veto_minus_keep_large_pp": large_gap,
        "veto_minus_keep_fail_pp": fail_gap,
        "large_retention": large_retention,
        "frequency_retention": freq_ret,
        "valid_year": valid,
        "pass_year": pass_year,
    }


def pooled_eval(df: pd.DataFrame, shell: str) -> Dict:
    ind = df[df["year"].astype(int).isin(INDEPENDENT_YEARS)].copy()
    d = ind[shell_mask(ind, shell)].copy()
    cutoff = train_cutoff(d)
    r = evaluate(ind, cutoff, shell, -1, "POOLED_INDEPENDENT")
    supported = d[np.isfinite(d["p12"])].copy()
    veto = supported[supported["p12"] <= cutoff]
    keep = supported[supported["p12"] > cutoff]
    ol, pl = odds_fisher(veto, keep, "large", "less")
    of, pf = odds_fisher(veto, keep, "fail", "greater")
    r.update({
        "fisher_large_odds": ol,
        "fisher_large_less_p": pl,
        "fisher_fail_odds": of,
        "fisher_fail_greater_p": pf,
    })
    return r


def main() -> None:
    print("=" * 100)
    print(LAB)
    events = build_events()
    print(f"ALL_EVENTS {len(events)}")
    print("IMPORTANT: P12 is frozen from LAB013; no threshold mining. 2021 excluded from independent training.")

    # Required lineage parity reference from LAB013 logs.
    lab013_base = events[(events["direction"].astype(int) == 1) & (events["low_activity_score"] >= 2) & (events["flow_delta_12"] > 0)]
    print(f"LAB013_BASE_BUY_ALL_YEARS {len(lab013_base)}")

    yearly: List[Dict] = []
    for y in INDEPENDENT_YEARS:
        train = events[(events["year"].astype(int).isin([z for z in INDEPENDENT_YEARS if z != y]))].copy()
        test = events[events["year"].astype(int).eq(y)].copy()
        for shell in SHELLS:
            cutoff = train_cutoff(train[shell_mask(train, shell)])
            yearly.append(evaluate(test, cutoff, shell, y, "INDEPENDENT_LOYO"))

    diagnostic: List[Dict] = []
    train_all_ind = events[events["year"].astype(int).isin(INDEPENDENT_YEARS)].copy()
    for y, fold in [(DISCOVERY_YEAR, "DISCOVERY_2021_DIAGNOSTIC"), (PSEUDO_FORWARD_YEAR, "PSEUDO_FORWARD_2026")]:
        test = events[events["year"].astype(int).eq(y)].copy()
        for shell in SHELLS:
            cutoff = train_cutoff(train_all_ind[shell_mask(train_all_ind, shell)])
            diagnostic.append(evaluate(test, cutoff, shell, y, fold))

    yearly_df = pd.DataFrame(yearly)
    diag_df = pd.DataFrame(diagnostic)
    pooled_df = pd.DataFrame([pooled_eval(events, s) for s in SHELLS])

    # Classify where the interaction localizes.
    summaries = []
    for shell in SHELLS:
        p = pooled_df[pooled_df.shell == shell].iloc[0]
        y = yearly_df[(yearly_df.shell == shell) & yearly_df.valid_year]
        pass_years = int(y.pass_year.sum())
        valid_years = int(len(y))
        pooled_pass = bool(
            p.veto_n >= 20
            and p.veto_minus_keep_large_pp <= -7.0
            and p.veto_minus_keep_fail_pp >= 5.0
        )
        robust = bool(pooled_pass and valid_years >= 3 and pass_years >= max(3, math.ceil(0.6 * valid_years)))
        summaries.append({
            "shell": shell,
            "supported_n": int(p.supported_n),
            "veto_n": int(p.veto_n),
            "keep_n": int(p.keep_n),
            "veto_large_rate": float(p.veto_large_rate),
            "keep_large_rate": float(p.keep_large_rate),
            "large_gap_pp": float(p.veto_minus_keep_large_pp),
            "veto_fail_rate": float(p.veto_fail_rate),
            "keep_fail_rate": float(p.keep_fail_rate),
            "fail_gap_pp": float(p.veto_minus_keep_fail_pp),
            "large_retention": float(p.large_retention),
            "frequency_retention": float(p.frequency_retention),
            "fisher_large_less_p": float(p.fisher_large_less_p),
            "fisher_fail_greater_p": float(p.fisher_fail_greater_p),
            "valid_years": valid_years,
            "passing_years": pass_years,
            "pooled_pass": pooled_pass,
            "robust_replication": robust,
        })
    summary_df = pd.DataFrame(summaries)

    def get(shell):
        return summary_df[summary_df.shell == shell].iloc[0]

    a, b, c = map(get, SHELLS)
    if a.robust_replication:
        verdict = "P12_IS_GENERAL_BUY_PRE_BOS_SPONSORSHIP_SIGNAL"
    elif b.robust_replication and not a.robust_replication:
        verdict = "P12_REQUIRES_LOW_ACTIVITY_CONTEXT"
    elif c.robust_replication and not b.robust_replication:
        verdict = "P12_REQUIRES_LOW_ACTIVITY_AND_FLOW_ALIGNMENT_INTERACTION"
    elif c.pooled_pass or b.pooled_pass or a.pooled_pass:
        verdict = "P12_EFFECT_PRESENT_BUT_NOT_YEARLY_ROBUST"
    else:
        verdict = "P12_BROAD_SHELL_REPLICATION_FAILS"

    print("\nPOOLED INDEPENDENT")
    print(summary_df.to_string(index=False))
    print("\nYEARLY INDEPENDENT")
    print(yearly_df.to_string(index=False))
    print("\n2021 + 2026 DIAGNOSTIC")
    print(diag_df.to_string(index=False))

    verdict_json = {
        "lab": LAB,
        "question": "Does frozen BUY P12 sponsorship replicate in ALL BUY BOS, LOW_ACTIVITY BUY BOS, or only LOW_ACTIVITY+FLOW_ALIGN BUY BOS?",
        "target": "clean MFE >= 2.5R within 32 M15 bars before structural SL",
        "predictor": "frozen P12 aggressive-flow persistence ending at i-1",
        "causality": "BOS candle and post-BOS excluded from P12/features",
        "shells": SHELLS,
        "threshold_policy": "P12 LOW = training-fold Q33 within each shell; no threshold search; BUY only",
        "independent_years": INDEPENDENT_YEARS,
        "discovery_year_excluded": DISCOVERY_YEAR,
        "pseudo_forward_year": PSEUDO_FORWARD_YEAR,
        "summary": summaries,
        "verdict_class": verdict,
        "warning": "Replication/interaction study only. Production admission still requires untouched forward and execution-cost validation.",
    }
    print("\nVERDICT")
    print(json.dumps(verdict_json, indent=2))

    yearly_df.to_csv(OUTDIR / "lab014_yearly_independent.csv", index=False)
    diag_df.to_csv(OUTDIR / "lab014_diagnostics_2021_2026.csv", index=False)
    pooled_df.to_csv(OUTDIR / "lab014_pooled_independent.csv", index=False)
    summary_df.to_csv(OUTDIR / "lab014_shell_summary.csv", index=False)
    events.to_csv(OUTDIR / "lab014_events_frozen_lineage.csv", index=False)
    with open(OUTDIR / "lab014_verdict.json", "w", encoding="utf-8") as f:
        json.dump(verdict_json, f, indent=2)


if __name__ == "__main__":
    main()
