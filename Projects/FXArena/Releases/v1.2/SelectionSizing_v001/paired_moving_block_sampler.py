#!/usr/bin/env python3
"""Canonical FXArena paired moving-block sampler (Registry v3).

- shared resample for baseline and candidate
- non-circular moving blocks of 20 chronological paired events
- blocks sampled with replacement until N observations are filled
- gross equity MaxDD is the DD metric
- absolute-DD-to-fixed-constant formulation is intentionally not implemented
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def max_drawdown(values: np.ndarray) -> float:
    x = np.asarray(values, dtype=np.float64)
    if x.size == 0:
        return 0.0
    equity = np.cumsum(x)
    peak = np.maximum.accumulate(np.r_[0.0, equity])
    return float(np.max(peak[1:] - equity))


def sampled_indices(n: int, block_size: int, rng: np.random.Generator) -> np.ndarray:
    if n <= 0:
        return np.empty(0, dtype=np.int64)
    b = min(int(block_size), n)
    starts_max = n - b
    n_blocks = int(np.ceil(n / b))
    starts = rng.integers(0, starts_max + 1, size=n_blocks)
    idx = np.concatenate([np.arange(s, s + b, dtype=np.int64) for s in starts])
    return idx[:n]


def paired_bootstrap(
    baseline_net: np.ndarray,
    baseline_gross: np.ndarray,
    candidate_net: np.ndarray,
    candidate_gross: np.ndarray,
    *,
    n_iter: int = 5000,
    block_size: int = 20,
    seed: int = 2026072305,
) -> tuple[pd.DataFrame, dict]:
    arrays = [
        np.asarray(baseline_net, dtype=np.float64),
        np.asarray(baseline_gross, dtype=np.float64),
        np.asarray(candidate_net, dtype=np.float64),
        np.asarray(candidate_gross, dtype=np.float64),
    ]
    n = len(arrays[0])
    if any(len(x) != n for x in arrays):
        raise ValueError("Paired arrays must have identical length")
    rng = np.random.default_rng(seed)
    rows = []
    for iteration in range(int(n_iter)):
        idx = sampled_indices(n, block_size, rng)
        bn, bg, cn, cg = (x[idx] for x in arrays)
        bdd = max_drawdown(bg)
        cdd = max_drawdown(cg)
        rows.append((iteration, float(bn.sum()), float(cn.sum()), bdd, cdd, cdd - bdd))
    frame = pd.DataFrame(
        rows,
        columns=[
            "iteration",
            "total_baseline",
            "total_candidate",
            "gross_DD_baseline",
            "gross_DD_candidate",
            "delta_gross_DD",
        ],
    )
    summary = {
        "n_iter": int(n_iter),
        "block_size": int(block_size),
        "seed": int(seed),
        "n_paired_events": int(n),
        "p_total_candidate_gt_baseline": float((frame.total_candidate > frame.total_baseline).mean()),
        "p_gross_DD_candidate_gt_baseline_plus_0_5": float((frame.delta_gross_DD > 0.5).mean()),
        "mean_total_delta": float((frame.total_candidate - frame.total_baseline).mean()),
        "mean_gross_DD_delta": float(frame.delta_gross_DD.mean()),
        "total_delta_p025": float((frame.total_candidate - frame.total_baseline).quantile(0.025)),
        "total_delta_p975": float((frame.total_candidate - frame.total_baseline).quantile(0.975)),
        "pass_total": bool((frame.total_candidate > frame.total_baseline).mean() >= 0.95),
        "pass_DD": bool((frame.delta_gross_DD > 0.5).mean() < 0.05),
    }
    summary["PASS"] = bool(summary["pass_total"] and summary["pass_DD"])
    return frame, summary
