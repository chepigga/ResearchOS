# BTC_FLOW_LEVEL_PRETOUCH_NET_TAKER_DELTA_PRICE_RESPONSE_AND_CVD_ABSORPTION_LAB_038

**Verdict: WATCH_NET_TAKER_DELTA_ABSORPTION_PARTIAL — 13/21**

## Coverage
- frozen HIGH_VOLUME pre-Aug: **568**; IGNITION **365**, ABSORPTION **203**
- futures/spot primary coverage: **100.0% / 100.0%**
- 2x2 frozen medians: net pressure **3.442**, directional response **1.713 ATR**

## HIGH_VOLUME state discrimination

| Feature | Ign N | Abs N | Ign med | Abs med | RBC | p | BH q |
|---|---:|---:|---:|---:|---:|---:|---:|
| fut_netdelta_norm_15 | 365 | 203 | 1.822 | 1.960 | -0.048 | 0.338 | 0.507 |
| fut_netdelta_norm_30 | 365 | 203 | 2.482 | 3.179 | -0.086 | 0.088 | 0.263 |
| fut_netdelta_norm_60 | 365 | 203 | 3.251 | 3.822 | -0.067 | 0.188 | 0.361 |
| spot_netdelta_norm_15 | 365 | 203 | 1.923 | 2.469 | -0.099 | 0.051 | 0.263 |
| spot_netdelta_norm_30 | 365 | 203 | 2.155 | 2.949 | -0.098 | 0.053 | 0.263 |
| spot_netdelta_norm_60 | 365 | 203 | 2.451 | 2.486 | -0.023 | 0.644 | 0.734 |
| fut_response_eff_60 | 365 | 203 | 0.470 | 0.399 | 0.089 | 0.078 | 0.263 |
| spot_response_eff_60 | 365 | 203 | 0.569 | 0.507 | 0.063 | 0.211 | 0.361 |
| fut_absorption_gap_60 | 365 | 203 | 1.323 | 1.635 | -0.069 | 0.173 | 0.361 |
| spot_absorption_gap_60 | 365 | 203 | 0.686 | 0.745 | -0.006 | 0.902 | 0.902 |
| fut_minus_spot_netdelta_60 | 365 | 203 | 0.621 | 0.846 | -0.021 | 0.673 | 0.734 |
| fut_minus_spot_absorption_gap_60 | 365 | 203 | 0.617 | 0.845 | -0.022 | 0.661 | 0.734 |

## ACCEPT feature → residual

| Feature | N | rho | p | BH q |
|---|---:|---:|---:|---:|
| fut_netdelta_norm_15 | 1363 | 0.028 | 0.306 | 0.911 |
| fut_netdelta_norm_30 | 1363 | 0.021 | 0.439 | 0.911 |
| fut_netdelta_norm_60 | 1363 | 0.028 | 0.302 | 0.911 |
| spot_netdelta_norm_15 | 1363 | -0.010 | 0.724 | 0.911 |
| spot_netdelta_norm_30 | 1363 | -0.022 | 0.412 | 0.911 |
| spot_netdelta_norm_60 | 1363 | 0.016 | 0.556 | 0.911 |
| fut_response_eff_60 | 1363 | 0.002 | 0.935 | 0.935 |
| spot_response_eff_60 | 1363 | 0.008 | 0.759 | 0.911 |
| fut_absorption_gap_60 | 1363 | 0.009 | 0.735 | 0.911 |
| spot_absorption_gap_60 | 1363 | -0.003 | 0.919 | 0.935 |
| fut_minus_spot_netdelta_60 | 1363 | 0.016 | 0.545 | 0.911 |
| fut_minus_spot_absorption_gap_60 | 1363 | 0.016 | 0.563 | 0.911 |

## Fixed 2x2 pressure × response map

| Cell | N | Accept rate | Residual | Hit | Net Δ norm | Response ATR | Abs gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| EFFICIENT_IGNITION | 212 | 0.618 | 0.965 | 0.533 | 7.445 | 3.277 | 4.168 |
| ABSORPTION | 72 | 0.583 | -0.379 | 0.486 | 5.471 | 1.100 | 4.371 |
| THIN_LIQUIDITY | 72 | 0.694 | -0.023 | 0.500 | 1.738 | 2.589 | -0.851 |
| WEAK | 212 | 0.670 | 0.083 | 0.467 | 0.286 | 0.558 | -0.272 |

## 7d cluster bootstrap
- EFFICIENT_IGNITION − ABSORPTION ACCEPT-rate: **+0.035**, 95% CI **[-0.104, +0.174]**
- residual difference: **+1.344 ATR**, 95% CI **[+0.149, +2.728]**, clusters=182

## Efficient-ignition transfer

| Slice | N | Accept | Residual | Hit | L/S |
|---|---:|---:|---:|---:|---:|
| 2021 | 32 | 0.594 | 1.777 | 0.625 | 10/22 |
| 2022 | 39 | 0.615 | 0.639 | 0.564 | 19/20 |
| 2023 | 42 | 0.524 | 1.718 | 0.524 | 21/21 |
| 2024 | 41 | 0.610 | 0.487 | 0.512 | 16/25 |
| 2025_H1 | 14 | 0.643 | -0.016 | 0.500 | 2/12 |
| 2025_H2 | 15 | 0.800 | 2.000 | 0.533 | 8/7 |
| 2026_JAN_JUL | 29 | 0.690 | 0.033 | 0.448 | 15/14 |
| POOLED_RECENT | 44 | 0.727 | 0.703 | 0.477 | 23/21 |
| AUG_REUSED | 1 | 0.000 | -3.173 | 0.000 | 0/1 |
| LONG | 91 | 0.615 | 0.931 | 0.527 | 91/0 |
| SHORT | 121 | 0.620 | 0.991 | 0.537 | 0/121 |
| 2022_SHORT | 20 | 0.650 | 1.651 | 0.600 | 0/20 |

## Gates
- PASS — `frozen_high_volume_ge_500`
- PASS — `futures_netdelta_coverage_ge_95pct`
- PASS — `spot_netdelta_coverage_ge_95pct`
- PASS — `ignition_ge_150_absorption_ge_100`
- PASS — `response_eff_ignition_gt_absorption`
- FAIL — `response_eff_rbc_ge_0_10`
- FAIL — `response_eff_bh_q_le_0_10`
- PASS — `absorption_gap_absorption_gt_ignition`
- FAIL — `absorption_gap_state_bh_q_le_0_10`
- FAIL — `any_state_feature_bh_q_le_0_10`
- PASS — `accept_residual_rho_response_positive`
- FAIL — `accept_residual_rho_gap_negative`
- FAIL — `any_residual_feature_bh_q_le_0_10`
- FAIL — `efficient_accept_rate_beats_absorption_0_05`
- PASS — `efficient_residual_beats_absorption_0_20`
- FAIL — `cluster_accept_rate_ci_lower_gt_zero`
- PASS — `cluster_residual_ci_lower_gt_zero`
- PASS — `stress_2022_short_efficient_positive_n20`
- PASS — `pooled_recent_efficient_positive_n40`
- PASS — `both_2025h2_2026_efficient_positive`
- PASS — `august_not_used_for_selection`

## Guardrail
Frozen FLOW/LEVEL/TOUCH/HIGH_VOLUME lineage from LAB035–037. Touch bar excluded. Net-delta normalization uses strictly prior 90d history. 2x2 median map is diagnostic-only. No entry/SL/TP optimization. August audit-only. Live allocation = **0**.
