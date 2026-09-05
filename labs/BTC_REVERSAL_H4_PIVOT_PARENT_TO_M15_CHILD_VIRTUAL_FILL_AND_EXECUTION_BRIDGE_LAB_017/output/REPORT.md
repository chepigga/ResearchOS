# BTC_REVERSAL_H4_PIVOT_PARENT_TO_M15_CHILD_VIRTUAL_FILL_AND_EXECUTION_BRIDGE_LAB_017

**Verdict:** **FAIL_H4_TO_M15_EXECUTION_BRIDGE**

Frozen orthogonal parent: `H4_7D_PIVOT_SWEEP_RECLAIM`; frozen T25 cutoff **0.313090**.

Primary child: `BREAK_CONFIRM_12H`; H4 supplies context only, M15 child supplies entry/SL geometry.

## Parent / child census and economics

| Rule | Window | H4 parents | Children | Found | Virtual fills | Mature | Real fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | LOEO worst |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BREAK_CONFIRM_12H | 2025_H2 | 34 | 34 | 100.0% | 22 | 27 | 17 | 2.83 | +0.168 | +2.86 | 1.317 | 2.81 | +0.59 |
| BREAK_CONFIRM_12H | 2026_JAN_JUL | 32 | 32 | 100.0% | 21 | 21 | 14 | 2.00 | -0.262 | -3.66 | 0.649 | 7.26 | -5.83 |
| BREAK_CONFIRM_12H | POOLED_RECENT | 66 | 66 | 100.0% | 43 | 48 | 31 | 2.38 | -0.026 | -0.80 | 0.959 | 7.26 | -3.07 |
| BREAK_CONFIRM_12H | AUG2026_REUSED_AUDIT | 0 | 0 | — | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| COLOR_ONLY_12H | 2025_H2 | 34 | 34 | 100.0% | 25 | 27 | 20 | 3.33 | +0.088 | +1.76 | 1.155 | 4.12 | -0.60 |
| COLOR_ONLY_12H | 2026_JAN_JUL | 32 | 32 | 100.0% | 23 | 22 | 16 | 2.29 | -0.473 | -7.56 | 0.482 | 8.96 | -8.99 |
| COLOR_ONLY_12H | POOLED_RECENT | 66 | 66 | 100.0% | 48 | 49 | 36 | 2.77 | -0.161 | -5.80 | 0.776 | 11.32 | -8.16 |
| COLOR_ONLY_12H | AUG2026_REUSED_AUDIT | 0 | 0 | — | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |
| TWO_BAR_CONFIRM_12H | 2025_H2 | 34 | 34 | 100.0% | 21 | 25 | 16 | 2.67 | +0.093 | +1.48 | 1.156 | 4.28 | -0.97 |
| TWO_BAR_CONFIRM_12H | 2026_JAN_JUL | 32 | 32 | 100.0% | 24 | 21 | 16 | 2.29 | +0.232 | +3.71 | 1.447 | 5.82 | -0.93 |
| TWO_BAR_CONFIRM_12H | POOLED_RECENT | 66 | 66 | 100.0% | 45 | 46 | 32 | 2.46 | +0.162 | +5.19 | 1.292 | 5.82 | +0.56 |
| TWO_BAR_CONFIRM_12H | AUG2026_REUSED_AUDIT | 0 | 0 | — | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | — |

## Canonical + primary child union

| Window | Fills | Fills/mo | Canonical | Incremental child | Cum R | Mean R/fill | PF | DD R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025_H2 | 28 | 4.67 | 11 | 17 | +10.71 | +0.383 | 1.873 | 2.81 |
| 2026_JAN_JUL | 25 | 3.57 | 11 | 14 | +4.62 | +0.185 | 1.340 | 4.73 |
| POOLED_RECENT | 53 | 4.08 | 22 | 31 | +15.33 | +0.289 | 1.593 | 4.73 |

## Primary gates
- PASS — `h2_parents_ge_15`
- PASS — `y2026_parents_ge_15`
- PASS — `child_found_ge_50pct_both`
- PASS — `h2_real_fills_ge_4`
- PASS — `y2026_real_fills_ge_4`
- FAIL — `mean_R_positive_both`
- FAIL — `pf_gt_12_both`
- FAIL — `cumR_positive_both`
- PASS — `pooled_freq_ge_050pm`
- FAIL — `pooled_loeo_positive`
- FAIL — `pooled_maxdd_le_4R`
- PASS — `union_freq_ge_220pm_and_cumR_gt_12`

**Score 7/12 → FAIL_H4_TO_M15_EXECUTION_BRIDGE**

## Historical descriptive audit — primary

| Window | Parents | Children | Real fills | Cum R | Mean R/fill | PF | DD R |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 58 | 58 | 29 | +2.91 | +0.100 | 1.179 | 4.95 |
| 2022 | 51 | 51 | 15 | -1.82 | -0.121 | 0.818 | 7.72 |
| 2023 | 34 | 34 | 5 | -6.25 | -1.250 | 0.000 | 6.25 |
| 2024 | 47 | 47 | 11 | +0.03 | +0.003 | 1.005 | 4.43 |
| 2025_H1 | 32 | 32 | 11 | -0.40 | -0.036 | 0.945 | 3.72 |

## Frozen mechanics / caveats
- Strict ±24h canonical non-overlap is applied to the H4 parent before M15 child search.
- `NO_CHILD` and unfilled shadow limits carry 0R; only VF1-mature child opportunities can contribute real PnL.
- VF1 uses only whether a prior child virtual limit filled before the current child signal; prior outcome is not used.
- `COLOR_ONLY_12H` and `TWO_BAR_CONFIRM_12H` are audit-only and cannot rescue the primary verdict.
- 2025H2/2026 are reused research windows; August 2026 is consumed/reused audit only.
- 5 bps is a frozen stress assumption, not a claim of exact current FTMO BTC all-in cost.
- No live allocation is authorized.
