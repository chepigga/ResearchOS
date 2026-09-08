# BTC_FLOW_LEVEL_PREBREAK_VOLUME_IGNITION_VS_ABSORPTION_AND_OI_CONTINUATION_LAB_036

**Verdict: WATCH_VOLUME_OR_OI_MECHANISM_PARTIAL — 10/17**

## Coverage
- LAB035 classified pre-Aug: **1969**
- volume resolved pre-Aug: **1966** (99.8%)
- HIGH_VOLUME: **568**, ignition: **365**, absorption: **203**
- ACCEPT rate HIGH vs LOW: **0.643 vs 0.714** (gap -0.071)

## Activation states

| State | N | Residual ATR | Hit | Fut vol60 exp | Fut taker aligned | Spot taker aligned |
|---|---:|---:|---:|---:|---:|---:|
| IGNITION | 365 | 0.382 | 0.488 | 1.150 | 0.060 | 0.069 |
| ABSORPTION | 203 | 0.266 | 0.517 | 1.220 | 0.060 | 0.063 |
| LOWVOL_ACCEPT | 998 | 0.339 | 0.466 | -0.062 | 0.046 | 0.048 |
| LOWVOL_REJECT | 400 | 0.164 | 0.500 | -0.053 | 0.049 | 0.058 |

## OI continuation after ACCEPT (+1h classification)

| OI state | N | Post-1h residual | Hit | Mean OI logchg |
|---|---:|---:|---:|---:|
| OI_PERSIST | 762 | 0.246 | 0.475 | 0.009 |
| OI_FLUSH | 569 | 0.249 | 0.438 | -0.010 |
| UNRESOLVED | 32 | — | — | — |

## Bootstrap

- IGNITION-ABSORPTION: **+0.116 ATR**, 7d bootstrap 95% CI **[-0.760, +0.975]**, clusters=239
- OI_PERSIST-OI_FLUSH: **-0.003 ATR**, 7d bootstrap 95% CI **[-0.548, +0.547]**, clusters=286

## IGNITION transfer

| Window | N | Residual | Hit | L/S |
|---|---:|---:|---:|---:|
| 2021 | 54 | 1.172 | 0.630 | 24/30 |
| 2022 | 58 | 0.207 | 0.466 | 28/30 |
| 2023 | 64 | 0.975 | 0.453 | 34/30 |
| 2024 | 78 | 0.222 | 0.474 | 31/47 |
| 2025_H1 | 26 | -0.961 | 0.385 | 9/17 |
| 2025_H2 | 35 | 0.692 | 0.571 | 19/16 |
| 2026_JAN_JUL | 50 | -0.296 | 0.420 | 23/27 |
| POOLED_RECENT | 85 | 0.111 | 0.482 | 42/43 |
| AUG_REUSED | 0 | — | — | 0/0 |
| 2022_SHORT | 30 | 1.084 | 0.467 | 0/30 |

## Volume diagnostics

| LAB035 state | High vol | N | Fut15 | Fut30 | Fut60 | Spot60 | Fut taker aligned | Spot taker aligned |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ACCEPT | 1 | 365 | 1.290 | 1.239 | 1.150 | 0.938 | 0.060 | 0.069 |
| ACCEPT | 0 | 998 | 0.126 | 0.027 | -0.062 | -0.091 | 0.046 | 0.048 |
| REJECT | 1 | 203 | 1.369 | 1.336 | 1.220 | 1.003 | 0.060 | 0.063 |
| REJECT | 0 | 400 | 0.140 | 0.056 | -0.053 | -0.115 | 0.049 | 0.058 |

## Gates
- PASS — `frozen_lab035_classified_ge_1900`
- PASS — `futures_volume_coverage_ge_95pct`
- PASS — `spot_volume_coverage_ge_95pct`
- PASS — `high_volume_n_ge_250`
- PASS — `ignition_n_ge_150`
- FAIL — `high_volume_accept_rate_gap_ge_0_05`
- PASS — `ignition_residual_positive`
- FAIL — `ignition_minus_absorption_ge_0_20`
- FAIL — `ignition_absorption_boot_ci_lower_gt_zero`
- FAIL — `ignition_beats_lowvol_accept_ge_0_10`
- PASS — `oi_persist_post1h_residual_positive`
- FAIL — `oi_persist_minus_flush_ge_0_30`
- FAIL — `oi_boot_ci_lower_gt_zero`
- PASS — `stress_2022_short_ignition_positive_n20`
- PASS — `pooled_recent_ignition_positive_n40`
- FAIL — `both_2025h2_2026_ignition_positive`
- PASS — `august_not_used_for_selection`

## Guardrail
Frozen LAB035 flow/level/acceptance lineage. Pre-touch volume excludes touch bar. OI state is known only +1h after ACCEPT and its payoff starts after that classification. No entry/SL/TP optimization. August reused audit only. Live allocation = **0**.
