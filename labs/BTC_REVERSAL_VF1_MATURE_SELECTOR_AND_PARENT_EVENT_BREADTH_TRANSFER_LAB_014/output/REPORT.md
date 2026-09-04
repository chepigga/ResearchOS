# BTC_REVERSAL_VF1_MATURE_SELECTOR_AND_PARENT_EVENT_BREADTH_TRANSFER_LAB_014

**Verdict:** **FAIL_VF1_BREADTH_DESTROYS_EDGE**

Role: upstream parent-event/router breadth transfer over frozen `VF1_MATURE`; no execution or maturity retuning.

## Frozen router cutoffs
- T20: **0.324358** (canonical P97.5 DEV score distribution)
- T25: **0.313090** (canonical P97.5 DEV score distribution)
- T30: **0.305260** (canonical P97.5 DEV score distribution)
- T40: **0.289096** (canonical P97.5 DEV score distribution)

Primary cell: **P960_T30**. Baseline: **P975_T20**.

## Primary vs baseline

| Cell | Window | Selected REV | Mature | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | Episodes | Worst ep | Boot CI low |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P975_T20 | 2025_H2 | 16 | 10 | 7 | 1.17 | +1.058 | +7.40 | 7.841 | 1.08 | 5 | +0.00 | +0.000 |
| P975_T20 | 2026_JAN_JUL | 22 | 10 | 8 | 1.14 | +0.813 | +6.50 | 4.096 | 1.07 | 8 | -0.66 | -0.068 |
| P975_T20 | POOLED_RECENT | 38 | 20 | 15 | 1.15 | +0.927 | +13.91 | 5.369 | 1.08 | 13 | -0.66 | -0.033 |
| P975_T20 | AUG2026_REUSED_AUDIT | 0 | 0 | 0 | 0.00 | — | +0.00 | — | 0.00 | 0 | — | — |
| P960_T30 | 2025_H2 | 53 | 43 | 24 | 4.00 | -0.190 | -4.56 | 0.729 | 7.09 | 8 | -3.19 | -0.316 |
| P960_T30 | 2026_JAN_JUL | 65 | 50 | 29 | 4.14 | +0.196 | +5.70 | 1.374 | 4.21 | 12 | -1.22 | -0.029 |
| P960_T30 | POOLED_RECENT | 118 | 93 | 53 | 4.08 | +0.021 | +1.14 | 1.036 | 7.09 | 20 | -3.19 | -0.112 |
| P960_T30 | AUG2026_REUSED_AUDIT | 4 | 1 | 1 | 1.00 | -1.243 | -1.24 | 0.000 | 1.24 | 2 | -1.24 | -0.621 |

## Full breadth grid — pooled recent

| Cell | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | Boot CI low |
|---|---:|---:|---:|---:|---:|---:|---:|
| P975_T20 | 15 | 1.15 | +0.927 | +13.91 | 5.369 | 1.08 | -0.033 |
| P975_T25 | 23 | 1.77 | +0.648 | +14.91 | 2.962 | 2.08 | -0.045 |
| P975_T30 | 30 | 2.31 | +0.481 | +14.43 | 2.192 | 4.50 | -0.010 |
| P975_T40 | 49 | 3.77 | +0.169 | +8.28 | 1.310 | 5.74 | -0.060 |
| P970_T20 | 20 | 1.54 | +0.415 | +8.31 | 1.949 | 4.19 | -0.116 |
| P970_T25 | 29 | 2.23 | +0.292 | +8.46 | 1.593 | 4.36 | -0.138 |
| P970_T30 | 39 | 3.00 | +0.189 | +7.37 | 1.353 | 4.45 | -0.098 |
| P970_T40 | 60 | 4.62 | +0.107 | +6.41 | 1.186 | 7.43 | -0.059 |
| P960_T20 | 29 | 2.23 | +0.087 | +2.52 | 1.151 | 3.55 | -0.086 |
| P960_T25 | 41 | 3.15 | -0.021 | -0.86 | 0.966 | 9.57 | -0.160 |
| P960_T30 | 53 | 4.08 | +0.021 | +1.14 | 1.036 | 7.09 | -0.112 |
| P960_T40 | 79 | 6.08 | +0.123 | +9.76 | 1.220 | 7.11 | -0.042 |
| P950_T20 | 44 | 3.38 | -0.110 | -4.82 | 0.834 | 10.78 | -0.163 |
| P950_T25 | 58 | 4.46 | -0.095 | -5.54 | 0.854 | 10.16 | -0.131 |
| P950_T30 | 75 | 5.77 | -0.122 | -9.13 | 0.818 | 15.14 | -0.131 |
| P950_T40 | 111 | 8.54 | -0.086 | -9.50 | 0.870 | 15.78 | -0.094 |

## Plateau neighbors
- PASS — `P970_T30`
- FAIL — `P960_T25`
- FAIL — `P960_T40`
- FAIL — `P950_T30`

## Gates
- PASS — `h2_2025_fills_ge_18`
- PASS — `y2026_fills_ge_21`
- PASS — `pooled_fills_ge_39`
- FAIL — `h2_2025_mean_fill_R_ge_0.30`
- FAIL — `y2026_mean_fill_R_ge_0.30`
- FAIL — `recent_pf_ge_1.5_both`
- FAIL — `recent_maxdd_le_2.5R_both`
- FAIL — `recent_cum_R_positive_both`
- FAIL — `pooled_retains_ge_90pct_baseline_R`
- FAIL — `pooled_cluster_bootstrap_ci_low_gt_0`
- FAIL — `pooled_all_loeo_positive`
- FAIL — `plateau_neighbors_ge_2`

**Score 3/12 → FAIL_VF1_BREADTH_DESTROYS_EDGE**

## Interpretation
- Baseline pooled VF1 frequency: **1.15 fills/month**; primary breadth: **4.08/month**.
- Baseline pooled CumR **+13.91R** → primary **+1.14R**; retention **8.2%**.
- August 2026 is reused/consumed audit only and cannot promote.
- Broader parent universes are scored by the canonical frozen router; no breadth-specific refit occurred.
- No live allocation is authorized by this LAB.
