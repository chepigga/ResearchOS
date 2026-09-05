# BTC_REVERSAL_H4_PIVOT_PARENT_TO_M15_CHILD_VIRTUAL_FILL_AND_EXECUTION_BRIDGE_LAB_017

**Verdict:** **WATCH_H4_TO_M15_BRIDGE**

Frozen orthogonal parent: `H4_7D_PIVOT_SWEEP_RECLAIM`; frozen T25 cutoff **0.313090**.

Primary child: `BREAK_CONFIRM_12H`; H4 supplies context only, M15 child supplies entry/SL geometry.

## Parent / child census and economics

| Rule | Window | H4 parents | Children | Found | Virtual fills | Mature | Real fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | LOEO worst |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BREAK_CONFIRM_12H | 2025_H2 | 22 | 22 | 100.0% | 17 | 15 | 11 | 1.83 | +0.234 | +2.58 | 1.477 | 1.95 | -1.11 |
| BREAK_CONFIRM_12H | 2026_JAN_JUL | 21 | 21 | 100.0% | 13 | 10 | 6 | 0.86 | +0.018 | +0.11 | 1.028 | 2.73 | -1.33 |
| BREAK_CONFIRM_12H | POOLED_RECENT | 43 | 43 | 100.0% | 30 | 25 | 17 | 1.31 | +0.158 | +2.69 | 1.292 | 2.73 | -1.00 |
| BREAK_CONFIRM_12H | AUG2026_REUSED_AUDIT | 6 | 6 | 100.0% | 3 | 3 | 1 | 1.00 | -1.201 | -1.20 | 0.000 | 1.20 | -1.20 |
| COLOR_ONLY_12H | 2025_H2 | 22 | 22 | 100.0% | 17 | 16 | 11 | 1.83 | +0.457 | +5.03 | 2.207 | 1.75 | +0.04 |
| COLOR_ONLY_12H | 2026_JAN_JUL | 21 | 21 | 100.0% | 14 | 11 | 7 | 1.00 | -0.735 | -5.15 | 0.355 | 7.98 | -6.58 |
| COLOR_ONLY_12H | POOLED_RECENT | 43 | 43 | 100.0% | 31 | 27 | 18 | 1.38 | -0.007 | -0.12 | 0.990 | 7.98 | -5.10 |
| COLOR_ONLY_12H | AUG2026_REUSED_AUDIT | 6 | 6 | 100.0% | 1 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | +0.00 |
| TWO_BAR_CONFIRM_12H | 2025_H2 | 22 | 22 | 100.0% | 16 | 14 | 11 | 1.83 | +0.272 | +2.99 | 1.562 | 1.95 | -0.70 |
| TWO_BAR_CONFIRM_12H | 2026_JAN_JUL | 21 | 21 | 100.0% | 15 | 10 | 7 | 1.00 | +0.538 | +3.77 | 2.487 | 2.53 | +1.61 |
| TWO_BAR_CONFIRM_12H | POOLED_RECENT | 43 | 43 | 100.0% | 31 | 24 | 18 | 1.38 | +0.375 | +6.76 | 1.861 | 2.53 | +3.07 |
| TWO_BAR_CONFIRM_12H | AUG2026_REUSED_AUDIT | 6 | 6 | 100.0% | 4 | 3 | 2 | 2.00 | -1.461 | -2.92 | 0.000 | 2.92 | -2.92 |

## Canonical + primary child union

| Window | Fills | Fills/mo | Canonical | Incremental child | Cum R | Mean R/fill | PF | DD R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025_H2 | 22 | 3.67 | 11 | 11 | +10.42 | +0.474 | 2.207 | 1.75 |
| 2026_JAN_JUL | 18 | 2.57 | 12 | 6 | +7.17 | +0.398 | 1.878 | 3.75 |
| POOLED_RECENT | 40 | 3.08 | 23 | 17 | +17.60 | +0.440 | 2.047 | 3.75 |

## Primary gates
- PASS — `h2_parents_ge_15`
- PASS — `y2026_parents_ge_15`
- PASS — `child_found_ge_50pct_both`
- PASS — `h2_real_fills_ge_4`
- PASS — `y2026_real_fills_ge_4`
- PASS — `mean_R_positive_both`
- FAIL — `pf_gt_12_both`
- PASS — `cumR_positive_both`
- PASS — `pooled_freq_ge_050pm`
- FAIL — `pooled_loeo_positive`
- PASS — `pooled_maxdd_le_4R`
- PASS — `union_freq_ge_220pm_and_cumR_gt_12`

**Score 10/12 → WATCH_H4_TO_M15_BRIDGE**

## Historical descriptive audit — primary

| Window | Parents | Children | Real fills | Cum R | Mean R/fill | PF | DD R |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 40 | 40 | 15 | +0.67 | +0.045 | 1.075 | 4.63 |
| 2022 | 34 | 34 | 11 | +2.56 | +0.233 | 1.454 | 3.34 |
| 2023 | 32 | 32 | 5 | -6.25 | -1.250 | 0.000 | 6.25 |
| 2024 | 29 | 29 | 5 | +1.59 | +0.318 | 1.715 | 1.17 |
| 2025_H1 | 29 | 29 | 11 | -0.40 | -0.036 | 0.945 | 3.72 |

## Frozen mechanics / caveats
- Strict ±24h canonical non-overlap is applied to the H4 parent before M15 child search.
- `NO_CHILD` and unfilled shadow limits carry 0R; only VF1-mature child opportunities can contribute real PnL.
- VF1 uses only whether a prior child virtual limit filled before the current child signal; prior outcome is not used.
- `COLOR_ONLY_12H` and `TWO_BAR_CONFIRM_12H` are audit-only and cannot rescue the primary verdict.
- 2025H2/2026 are reused research windows; August 2026 is consumed/reused audit only.
- 5 bps is a frozen stress assumption, not a claim of exact current FTMO BTC all-in cost.
- No live allocation is authorized.
