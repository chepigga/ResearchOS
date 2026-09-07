# BTC_RETAIL_FLOW_ACCEPTANCE_ORIGIN_CLOSE2_FAILURE_RECOVERY_AND_REACCEPTANCE_LAB_030

**Verdict: WATCH_REACCEPTANCE_DISCRIMINATIVE_BUT_TRANSFER_INCOMPLETE — 10/12**

## Frozen lineage
- LAB029 rows: **1501**; triggered failures pre-Aug: **1097**

## Failure recovery by window

| Window | N fail | Origin reclaim | Full reaccept | Rate | Reaccept residual | No-reaccept residual | Gap | Reaccept PF | Median reaccept h | Reentry net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 234 | 186 | 154 | 0.658 | -0.036 | -2.676 | 2.640 | 0.970 | 1.500 | -0.122 |
| 2022 | 189 | 145 | 109 | 0.577 | 0.435 | -2.807 | 3.241 | 1.464 | 1.750 | 0.298 |
| 2023 | 193 | 153 | 125 | 0.648 | 0.554 | -2.143 | 2.697 | 1.334 | 1.750 | 0.343 |
| 2024 | 188 | 142 | 122 | 0.649 | 0.248 | -3.146 | 3.394 | 1.175 | 1.500 | 0.095 |
| 2025_H1 | 94 | 70 | 59 | 0.628 | 0.322 | -3.603 | 3.925 | 1.262 | 1.750 | 0.141 |
| 2025_H2 | 103 | 77 | 66 | 0.641 | -0.276 | -2.738 | 2.462 | 0.835 | 1.625 | -0.499 |
| 2026_JAN_JUL | 96 | 77 | 66 | 0.688 | 0.692 | -2.163 | 2.855 | 1.475 | 1.750 | 0.516 |
| AUG2026_REUSED_AUDIT | 4 | 3 | 2 | 0.500 | -8.008 | -2.117 | -5.891 | 0.000 | 3.375 | -8.508 |
| HIST | 898 | 696 | 569 | 0.634 | 0.282 | -2.791 | 3.072 | 1.216 | 1.750 | 0.134 |
| RECENT | 199 | 154 | 132 | 0.663 | 0.208 | -2.481 | 2.688 | 1.133 | 1.750 | 0.008 |
| ALL_PRE_AUG | 1097 | 850 | 701 | 0.639 | 0.268 | -2.738 | 3.006 | 1.198 | 1.750 | 0.110 |

## By side pre-Aug

| Side | N fail | Full reaccept | Rate | Reaccept residual | No-reaccept residual | Gap | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | 530 | 325 | 0.613 | 0.020 | -2.751 | 2.771 | 1.014 |
| SHORT | 567 | 376 | 0.663 | 0.482 | -2.724 | 3.206 | 1.380 |

## 7d cluster bootstrap
- clusters: **286**, draws: **5000**
- FULL_REACCEPT residual minus NO_REACCEPT residual: **3.006 ATR**, 95% CI **[2.525, 3.511]**

## Recovery anatomy
- pre-Aug median failure→origin reclaim: **0.750 h**
- pre-Aug median failure→full reaccept: **1.750 h**
- median extra bad closes before reaccept: **4.000**

## Gates
- FAIL — `exact_lab029_lineage_and_failure_n_ge_900`
- PASS — `full_reaccept_n_ge_200`
- PASS — `full_reaccept_residual_positive`
- PASS — `residual_gap_ge_0_50atr`
- PASS — `bootstrap_ci_lower_gt_zero`
- PASS — `no_reaccept_nonpositive_or_gap_ge_0_50`
- PASS — `recent_full_reaccept_n_ge_40`
- PASS — `recent_full_reaccept_residual_positive`
- PASS — `recent_reaccept_gt_no_reaccept`
- FAIL — `recent_recovery_shift_support`
- PASS — `stress_2022_short_reaccept_n20_residual_positive`
- PASS — `long_and_short_reaccept_residual_positive`

## Guardrail
FULL_REACCEPT is a state audit, not a promoted re-entry rule. Recovery levels are frozen from the original signal price and +0.5 ATR acceptance entry. No threshold/horizon/side rescue. August 2026 reused audit only. Live allocation = **0**.
