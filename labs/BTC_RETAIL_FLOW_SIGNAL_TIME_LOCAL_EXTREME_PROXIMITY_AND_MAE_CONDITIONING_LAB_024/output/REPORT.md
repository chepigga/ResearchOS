# BTC_RETAIL_FLOW_SIGNAL_TIME_LOCAL_EXTREME_PROXIMITY_AND_MAE_CONDITIONING_LAB_024

**Verdict: FAIL_NO_SIGNAL_TIME_PROXIMITY_MECHANISM — 6/14**

## Frozen parity
- flow lineage: **3209**
- feature rows: **3209**, pre-Aug **3196**
- timestamp parity: **100.00%**
- recomputed-vs-frozen 12h payoff median absolute error: **0.000000 ATR**

## Threshold-free proximity correlations

| Slice | H | N | rho(distance, return) | rho(distance, MAE) |
|---|---|---:|---:|---:|
| ALL_PRE_AUG | 1H | 3196 | -0.003 | -0.016 |
| ALL_PRE_AUG | 2H | 3196 | -0.003 | -0.025 |
| ALL_PRE_AUG | 4H | 3196 | -0.009 | -0.031 |
| POOLED_RECENT | 1H | 625 | 0.026 | -0.050 |
| POOLED_RECENT | 2H | 625 | 0.024 | -0.063 |
| POOLED_RECENT | 4H | 625 | 0.020 | -0.058 |
| LONG_PRE_AUG | 1H | 1563 | 0.003 | -0.020 |
| LONG_PRE_AUG | 2H | 1563 | 0.003 | -0.023 |
| LONG_PRE_AUG | 4H | 1563 | -0.023 | -0.016 |
| SHORT_PRE_AUG | 1H | 1633 | -0.008 | -0.012 |
| SHORT_PRE_AUG | 2H | 1633 | -0.007 | -0.028 |
| SHORT_PRE_AUG | 4H | 1633 | 0.005 | -0.049 |
| 2022_SHORT | 1H | 253 | -0.037 | 0.033 |
| 2022_SHORT | 2H | 253 | -0.070 | 0.019 |
| 2022_SHORT | 4H | 253 | -0.064 | 0.039 |

## 4H fixed near/far by window

| Window | Group | N | EV ATR | t | Payoff ratio | Median MAE | Stop1.5 touch | L/S |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | ALL | 631 | 0.630 | 3.098 | 1.421 | 2.338 | 0.656 | 318/313 |
| 2021 | NEAR4H | 76 | 0.624 | 1.321 | 1.495 | 2.130 | 0.605 | 43/33 |
| 2021 | FAR4H | 446 | 0.518 | 2.045 | 1.314 | 2.349 | 0.652 | 220/226 |
| 2021 | SWEEP1TO4 | 231 | 0.365 | 1.162 | 1.240 | 2.620 | 0.710 | 115/116 |
| 2022 | ALL | 529 | 0.451 | 1.759 | 1.259 | 2.542 | 0.675 | 276/253 |
| 2022 | NEAR4H | 48 | 1.740 | 2.681 | 2.856 | 2.546 | 0.583 | 26/22 |
| 2022 | FAR4H | 403 | 0.372 | 1.246 | 1.208 | 2.522 | 0.663 | 212/191 |
| 2022 | SWEEP1TO4 | 201 | 0.100 | 0.273 | 1.056 | 2.694 | 0.721 | 107/94 |
| 2023 | ALL | 572 | 0.452 | 1.607 | 1.248 | 2.694 | 0.698 | 268/304 |
| 2023 | NEAR4H | 67 | -0.009 | -0.010 | 0.996 | 2.985 | 0.716 | 21/46 |
| 2023 | FAR4H | 406 | 0.449 | 1.316 | 1.249 | 2.639 | 0.685 | 202/204 |
| 2023 | SWEEP1TO4 | 216 | 0.848 | 2.210 | 1.542 | 2.528 | 0.690 | 94/122 |
| 2024 | ALL | 583 | 0.177 | 0.725 | 1.092 | 2.608 | 0.705 | 279/304 |
| 2024 | NEAR4H | 55 | -0.721 | -1.065 | 0.662 | 2.964 | 0.636 | 22/33 |
| 2024 | FAR4H | 453 | 0.269 | 0.930 | 1.139 | 2.522 | 0.711 | 220/233 |
| 2024 | SWEEP1TO4 | 179 | -0.153 | -0.376 | 0.921 | 2.608 | 0.743 | 76/103 |
| 2025_H1 | ALL | 256 | 0.175 | 0.397 | 1.081 | 2.807 | 0.691 | 128/128 |
| 2025_H1 | NEAR4H | 17 | 1.114 | 0.510 | 1.627 | 4.371 | 0.882 | 9/8 |
| 2025_H1 | FAR4H | 206 | -0.107 | -0.214 | 0.955 | 2.847 | 0.689 | 107/99 |
| 2025_H1 | SWEEP1TO4 | 81 | -0.249 | -0.267 | 0.902 | 2.856 | 0.753 | 41/40 |
| 2025_H2 | ALL | 309 | 0.011 | 0.034 | 1.005 | 2.999 | 0.735 | 147/162 |
| 2025_H2 | NEAR4H | 49 | -0.437 | -0.571 | 0.794 | 2.814 | 0.714 | 21/28 |
| 2025_H2 | FAR4H | 200 | 0.249 | 0.580 | 1.121 | 2.892 | 0.710 | 104/96 |
| 2025_H2 | SWEEP1TO4 | 123 | -0.435 | -0.828 | 0.808 | 2.898 | 0.675 | 51/72 |
| 2026_JAN_JUL | ALL | 316 | 0.202 | 0.674 | 1.111 | 2.834 | 0.728 | 147/169 |
| 2026_JAN_JUL | NEAR4H | 37 | 1.635 | 2.909 | 4.039 | 2.678 | 0.703 | 12/25 |
| 2026_JAN_JUL | FAR4H | 242 | 0.137 | 0.388 | 1.072 | 2.705 | 0.731 | 116/126 |
| 2026_JAN_JUL | SWEEP1TO4 | 102 | -0.769 | -1.428 | 0.662 | 2.928 | 0.706 | 44/58 |
| AUG2026_REUSED_AUDIT | ALL | 13 | -5.530 | -4.454 | 0.014 | 8.657 | 0.923 | 9/4 |
| AUG2026_REUSED_AUDIT | NEAR4H | 1 | -5.097 | — | 0.000 | 7.559 | 1.000 | 1/0 |
| AUG2026_REUSED_AUDIT | FAR4H | 10 | -5.577 | -4.253 | 0.000 | 8.733 | 1.000 | 6/4 |
| AUG2026_REUSED_AUDIT | SWEEP1TO4 | 4 | -5.399 | -3.368 | 0.000 | 8.184 | 1.000 | 2/2 |
| ALL_PRE_AUG | ALL | 3196 | 0.347 | 3.302 | 1.192 | 2.648 | 0.693 | 1563/1633 |
| ALL_PRE_AUG | NEAR4H | 349 | 0.426 | 1.472 | 1.260 | 2.678 | 0.668 | 154/195 |
| ALL_PRE_AUG | FAR4H | 2356 | 0.316 | 2.505 | 1.169 | 2.587 | 0.687 | 1181/1175 |
| ALL_PRE_AUG | SWEEP1TO4 | 1133 | 0.095 | 0.572 | 1.051 | 2.683 | 0.712 | 528/605 |
| POOLED_RECENT | ALL | 625 | 0.108 | 0.483 | 1.056 | 2.913 | 0.731 | 294/331 |
| POOLED_RECENT | NEAR4H | 86 | 0.455 | 0.895 | 1.317 | 2.746 | 0.709 | 33/53 |
| POOLED_RECENT | FAR4H | 442 | 0.187 | 0.686 | 1.095 | 2.789 | 0.722 | 220/222 |
| POOLED_RECENT | SWEEP1TO4 | 225 | -0.586 | -1.559 | 0.741 | 2.907 | 0.689 | 95/130 |

## Pre-Aug NEAR4H by side

| Side | N | EV ATR | t | Payoff ratio | Median MAE | Stop1.5 touch |
|---|---:|---:|---:|---:|---:|---:|
| LONG | 154 | 0.386 | 0.768 | 1.201 | 2.726 | 0.656 |
| SHORT | 195 | 0.458 | 1.370 | 1.324 | 2.655 | 0.677 |

## Bootstrap NEAR4H - FAR4H
- N near/far: **349 / 2356**
- EV diff: **0.110 ATR**, 95% CI **[-0.513, 0.713]**
- mean MAE diff: **0.091 ATR**, 95% CI **[-0.366, 0.605]**

## Gates
- PASS — `frozen_lineage_3209_and_timestamp_parity`
- PASS — `feature_rows_pre_aug_ge_3000`
- PASS — `rho4h_return_negative`
- FAIL — `rho4h_mae_positive`
- FAIL — `near4h_n_ge_500`
- FAIL — `near4h_ev_baseline_plus_010`
- PASS — `near4h_ev_gt_far4h`
- FAIL — `near4h_median_mae_lower_by_025`
- FAIL — `near4h_stop_touch_lower_by_10pp`
- FAIL — `bootstrap_ev_diff_ci_gt_zero`
- FAIL — `stress_2022_short_near_n40_ev_positive`
- PASS — `near4h_long_short_both_positive`
- PASS — `recent_near4h_ev_positive`
- FAIL — `recent_sweep_ev_baseline_plus_010`

## Guardrail
This LAB conditions the frozen flow signal at the same signal-time close. It does not delay entry, optimize a threshold, or use H4 direction. August 2026 is reused audit. Live allocation = **0**.
