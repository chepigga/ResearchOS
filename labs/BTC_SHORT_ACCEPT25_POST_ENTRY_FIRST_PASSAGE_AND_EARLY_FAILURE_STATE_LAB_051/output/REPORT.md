# BTC_SHORT_ACCEPT25_POST_ENTRY_FIRST_PASSAGE_AND_EARLY_FAILURE_STATE_LAB_051

**Verdict: WATCH_EARLY_PATH_DISCRIMINATIVE_PROOF_INCOMPLETE — 10/15**

## Frozen parity
- Parent ACCEPT2.5 trades: **327**; M15 path coverage: **100.0%**; entry/class parity: **100.0%**

## Primary first-passage within 120m

| State | N | Share | Residual EV | Frozen parent EV | Median min | MFE60 | MAE60 | MFE120 | MAE120 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FAVORABLE_FIRST | 159 | 48.6% | +0.151 | +0.589 | 30 | +0.848 | +0.267 | +1.181 | +0.305 |
| ADVERSE_FIRST | 145 | 44.3% | +0.086 | -0.477 | 30 | +0.234 | +0.723 | +0.299 | +0.869 |
| NONE_120 | 23 | 7.0% | — | +0.161 | — | +0.282 | +0.314 | +0.290 | +0.353 |

FAVORABLE−ADVERSE residual gap: **+0.065R**, 7d bootstrap 95% CI **[-0.184, +0.306]**, clusters=189
FAVORABLE residual **+0.151R**; ADVERSE residual **+0.086R**

## Frozen transfer

| Slice | N | Resolved | Fav N | Adv N | Adv share | Fav residual | Adv residual | Gap | Boot 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2021 | 62 | 56 | 34 | 22 | 39.3% | +0.136 | +0.126 | +0.010 | [-0.542, +0.522 ] |
| 2022 | 49 | 45 | 21 | 24 | 53.3% | +0.290 | -0.135 | +0.425 | [-0.151, +0.934 ] |
| 2023 | 52 | 49 | 28 | 21 | 42.9% | -0.154 | +0.145 | -0.299 | [-0.917, +0.328 ] |
| 2024 | 64 | 60 | 27 | 33 | 55.0% | +0.318 | +0.055 | +0.263 | [-0.287, +0.719 ] |
| 2025_H1 | 32 | 30 | 15 | 15 | 50.0% | +0.153 | -0.195 | +0.348 | [-0.287, +0.958 ] |
| 2025_H2 | 33 | 29 | 18 | 11 | 37.9% | +0.235 | -0.045 | +0.280 | [-0.534, +0.976 ] |
| 2026_JAN_JUL | 35 | 35 | 16 | 19 | 54.3% | +0.156 | +0.607 | -0.452 | [-1.319, +0.417 ] |
| BAD_POOLED | 81 | 75 | 36 | 39 | 52.0% | +0.233 | -0.158 | +0.391 | [-0.045, +0.795 ] |
| RECENT_POOLED | 68 | 64 | 34 | 30 | 46.9% | +0.198 | +0.368 | -0.170 | [-0.784, +0.415 ] |

## Early reclaim diagnostics
- RECLAIM1 N=170, residual **+0.068R**
- RECLAIM2 N=115, residual **+0.110R**
- Frozen parent EV: RECLAIM2 **-0.332R** vs NO_RECLAIM2 **+0.313R**

## Gates
- PASS — `exact_frozen_parent_n327`
- PASS — `parent_path_coverage_ge99pct`
- PASS — `first_passage_resolved_n_ge100`
- PASS — `favorable_first_n_ge40`
- PASS — `adverse_first_n_ge40`
- PASS — `favorable_residual_positive`
- FAIL — `adverse_residual_negative`
- FAIL — `residual_gap_ge0_30r`
- FAIL — `residual_gap_boot_lower_gt0`
- PASS — `bad_pooled_residual_gap_positive`
- FAIL — `recent_pooled_residual_gap_positive`
- PASS — `reclaim2_n_ge20`
- FAIL — `reclaim2_residual_negative`
- PASS — `reclaim2_parent_ev_lt_no_reclaim2`
- PASS — `august_not_used_for_selection`

## Guardrail
Mechanism/state audit only. No early exit, breakeven, trailing, stop tightening, re-entry, or allocation rule was searched or promoted. Reused historical lineage; not fresh OOS. Live allocation = **0**.
