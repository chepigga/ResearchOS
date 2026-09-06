# BTC_BINANCE_RETAIL_FLOW_DIRECTION_X_H4_PIVOT_M15_PRICE_TIMING_LAB_022

**Verdict: WATCH_DIRECTIONAL_FLOW_EXECUTION_BRIDGE — 7/10**

## Data/parity
- Metrics rows M15: **205440**, range 2020-10-01 00:00:00+00:00 .. 2026-08-31 23:45:00+00:00
- 2022 coverage: **94.9%**
- Price label offset selected by close parity: **0 min**, median close error 0.000478

## Part A — clean 12h direction at frozen H4/M15 child clock

| Sample | N | Mean ATR | Cum ATR | t | Hit | PF |
|---|---:|---:|---:|---:|---:|---:|
| PRICE_ONLY | 209 | -0.168 | -35.115 | -0.432 | 0.545 | 0.915 |
| FLOW_EXTREME | 100 | 0.194 | 19.360 | 0.342 | 0.440 | 1.112 |
| FLOW_PRICE_AGREE | 27 | 0.189 | 5.090 | 0.242 | 0.519 | 1.136 |
| FLOW_PRICE_CONFLICT | 73 | 0.195 | 14.269 | 0.270 | 0.411 | 1.106 |

## Part B — FLOW agrees with price timing, local-extreme fill, SL1.5ATR, no TP, TIME12H

| Window | N | Mean net ATR | Cum net ATR | t | PF | DD | Stop rate | Long/Short |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 5 | -1.585 | -7.925 | -177.766 | 0.000 | 7.925 | 1.000 | 0/5 |
| 2022 | 1 | -1.563 | -1.563 | — | 0.000 | 1.563 | 1.000 | 1/0 |
| 2023 | 2 | 1.074 | 2.148 | 0.377 | 2.210 | 1.775 | 0.500 | 1/1 |
| 2024 | 1 | 1.419 | 1.419 | — | inf | 0.000 | 0.000 | 0/1 |
| 2025_H1 | 4 | 1.149 | 4.594 | 0.701 | 2.409 | 1.684 | 0.500 | 3/1 |
| 2025_H2 | 2 | 2.033 | 4.066 | 0.556 | 3.509 | 1.621 | 0.500 | 2/0 |
| 2026_JAN_JUL | 1 | -1.640 | -1.640 | — | 0.000 | 1.640 | 1.000 | 1/0 |
| AUG2026_REUSED_AUDIT | 1 | -1.666 | -1.666 | — | 0.000 | 1.666 | 1.000 | 0/1 |
| ALL_PRE_AUG | 16 | 0.069 | 1.099 | 0.101 | 1.062 | 11.263 | 0.688 | 8/8 |
| POOLED_RECENT | 3 | 0.809 | 2.426 | 0.332 | 1.744 | 3.261 | 0.667 | 3/0 |

## Execution audits

| Sample | N | Mean net ATR | Cum net ATR | PF | Stop rate |
|---|---:|---:|---:|---:|---:|
| PRIMARY_SL15_TIME12 | 17 | -0.033 | -0.567 | 0.971 | 0.706 |
| AUDIT_NOSTOP_TIME12 | 17 | -0.186 | -3.170 | 0.894 | 0.000 |
| AUDIT_VF1_SL15_TIME12 | 9 | 0.050 | 0.449 | 1.046 | 0.667 |

## Non-overlapping flow-only reference
N=3209, mean=0.323 ATR, t=3.079.

## Gates
- PASS — `metrics_2022_coverage_ge_90pct`
- PASS — `partA_flow_extreme_n_ge_30`
- PASS — `partA_flow_mean_positive`
- PASS — `partA_agreement_mean_gt_price_only`
- PASS — `partB_bounded_n_ge_12`
- PASS — `partB_bounded_mean_positive`
- FAIL — `partB_bounded_pf_gt_1_25`
- FAIL — `stress_2022_short_n_ge_3_and_cum_positive`
- PASS — `recent_2025h2_2026_cum_positive`
- FAIL — `nostop_time12_mean_positive`

## Guardrail
Retail-flow thresholds here are causal trailing-90d quintiles because the earlier standalone absolute thresholds were not persisted. No cutoff/horizon/stop/TP rescue is allowed. August 2026 is reused audit only. Live allocation remains **0**.
