# BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023

**Verdict: FAIL_LOCAL_EXTREME_TIMING_NO_TRANSFER — 3/12**

## Frozen lineage
- LAB022 flow events: **3209** (asserted exact).
- H4 fields read: **0**.
- Primary trigger coverage pre-Aug: **95.4%** (3050/3196).

## Overall execution comparison

| Sample | N | Mean net ATR | Cum ATR | t | PF | Stop | Median MAE | Long/Short |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| IMMEDIATE_FLOW_SL15_TIME12 | 3196 | 0.099 | 316.512 | 1.521 | 1.085 | 0.693 | 1.660 | 1563/1633 |
| PRIMARY_SWEEP_RECLAIM4_SL15_TIME12 | 3050 | -0.134 | -408.042 | -2.199 | 0.889 | 0.713 | 1.683 | 1491/1559 |
| AUDIT_PRIMARY_NOSTOP_TIME12 | 3050 | -0.062 | -189.094 | -0.606 | 0.968 | 0.000 | 2.793 | 1491/1559 |
| AUDIT_PRIMARY_SL15_TIME24 | 3050 | -0.038 | -117.011 | -0.464 | 0.971 | 0.800 | 1.748 | 1491/1559 |
| AUDIT_EXTREME4_COLOR_SL15_TIME12 | 3050 | -0.134 | -408.042 | -2.199 | 0.889 | 0.713 | 1.683 | 1491/1559 |
| AUDIT_PIVOT2X2_CONFIRMED_SL15_TIME12 | 3178 | 0.086 | 273.059 | 1.310 | 1.074 | 0.684 | 1.655 | 1554/1624 |

## Primary by window

| Window | N | Mean net ATR | Cum ATR | PF | Stop | DD | Long/Short |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 596 | 0.044 | 26.025 | 1.039 | 0.690 | 85.598 | 301/295 |
| 2022 | 507 | -0.287 | -145.602 | 0.761 | 0.728 | 145.602 | 269/238 |
| 2023 | 546 | -0.135 | -73.792 | 0.895 | 0.729 | 137.666 | 257/289 |
| 2024 | 558 | -0.194 | -108.035 | 0.838 | 0.713 | 140.707 | 259/299 |
| 2025_H1 | 246 | -0.058 | -14.347 | 0.952 | 0.720 | 65.588 | 122/124 |
| 2025_H2 | 297 | -0.300 | -88.965 | 0.767 | 0.737 | 126.042 | 141/156 |
| 2026_JAN_JUL | 300 | -0.011 | -3.325 | 0.990 | 0.673 | 43.922 | 142/158 |
| AUG2026_REUSED_AUDIT | 11 | -1.835 | -20.185 | 0.000 | 1.000 | 20.185 | 7/4 |
| ALL_PRE_AUG | 3050 | -0.134 | -408.042 | 0.889 | 0.713 | 545.684 | 1491/1559 |
| POOLED_RECENT | 597 | -0.155 | -92.291 | 0.873 | 0.705 | 129.522 | 283/314 |

## Primary side/year

| Year | Side | N | Mean | Cum | PF | Stop |
|---:|---|---:|---:|---:|---:|---:|
| 2021 | LONG | 301 | 0.039 | 11.771 | 1.034 | 0.711 |
| 2021 | SHORT | 295 | 0.048 | 14.254 | 1.045 | 0.668 |
| 2022 | LONG | 269 | -0.490 | -131.795 | 0.613 | 0.766 |
| 2022 | SHORT | 238 | -0.058 | -13.807 | 0.949 | 0.685 |
| 2023 | LONG | 257 | 0.221 | 56.884 | 1.168 | 0.747 |
| 2023 | SHORT | 289 | -0.452 | -130.677 | 0.639 | 0.713 |
| 2024 | LONG | 259 | 0.006 | 1.492 | 1.005 | 0.714 |
| 2024 | SHORT | 299 | -0.366 | -109.527 | 0.692 | 0.712 |
| 2025 | LONG | 263 | -0.307 | -80.864 | 0.756 | 0.738 |
| 2025 | SHORT | 280 | -0.080 | -22.449 | 0.936 | 0.721 |
| 2026 | LONG | 142 | -0.419 | -59.462 | 0.666 | 0.732 |
| 2026 | SHORT | 158 | 0.355 | 56.137 | 1.336 | 0.620 |

## Gates
- PASS — `frozen_flow_lineage_exact_3209`
- PASS — `primary_trigger_coverage_ge_30pct`
- PASS — `primary_pre_aug_n_ge_700`
- FAIL — `primary_mean_net_atr_positive`
- FAIL — `primary_pf_gt_1_20`
- FAIL — `primary_improves_immediate_by_ge_0_10atr`
- FAIL — `primary_stop_rate_reduced_ge_10pp`
- FAIL — `stress_2022_short_n_ge_40_and_cum_positive`
- FAIL — `short_pooled_positive_and_ge4_of5_years_positive`
- FAIL — `long_pooled_mean_positive`
- FAIL — `recent_cum_positive`
- FAIL — `primary_nostop_time12_mean_positive`

## Guardrail
Primary uses frozen LAB022 flow direction only. No H4 direction/context is read. Audits are diagnostics and cannot rescue the primary. August 2026 remains reused audit; live allocation = **0**.
