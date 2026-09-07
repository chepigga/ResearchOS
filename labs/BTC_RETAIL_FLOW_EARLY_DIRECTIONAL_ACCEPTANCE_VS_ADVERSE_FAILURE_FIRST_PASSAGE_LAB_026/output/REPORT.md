# BTC_RETAIL_FLOW_EARLY_DIRECTIONAL_ACCEPTANCE_VS_ADVERSE_FAILURE_FIRST_PASSAGE_LAB_026

**Verdict: PASS_EARLY_ACCEPTANCE_RESIDUAL_DISCRIMINATOR — 13/14**

## Frozen parity
- flow lineage: **3209**
- pre-Aug eligible: **3196**
- timestamp parity: **100.00%**
- payoff parity median abs error: **0.000000 ATR**

## First-passage by fixed horizon (pre-Aug)

| Horizon | State | N | Residual EV | t(resid) | Total12 EV | MAE | Stop1.5 | Delay h |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1H | ACCEPT_FIRST | 1466 | 0.534 | 3.640 | 1.034 | 2.004 | 0.585 | 0.250 |
| 1H | ADVERSE_FIRST | 1378 | 0.095 | 0.570 | -0.405 | 3.172 | 0.803 | 0.250 |
| 1H | AMBIGUOUS_SAME_BAR | 292 | — | — | 0.382 | 3.183 | 0.740 | — |
| 1H | NONE | 60 | — | — | 0.679 | 1.857 | 0.567 | — |
| 2H | ACCEPT_FIRST | 1496 | 0.527 | 3.660 | 1.027 | 1.990 | 0.585 | 0.250 |
| 2H | ADVERSE_FIRST | 1403 | 0.114 | 0.690 | -0.386 | 3.139 | 0.800 | 0.250 |
| 2H | AMBIGUOUS_SAME_BAR | 293 | — | — | 0.375 | 3.205 | 0.741 | — |
| 2H | NONE | 4 | — | — | 1.459 | 0.936 | 0.000 | — |
| 4H | ACCEPT_FIRST | 1498 | 0.529 | 3.683 | 1.029 | 1.989 | 0.584 | 0.250 |
| 4H | ADVERSE_FIRST | 1404 | 0.114 | 0.693 | -0.386 | 3.139 | 0.800 | 0.250 |
| 4H | AMBIGUOUS_SAME_BAR | 293 | — | — | 0.375 | 3.205 | 0.741 | — |
| 4H | NONE | 1 | — | — | -0.287 | 1.213 | 0.000 | — |

## Primary 2h by window

| Window | State | N | Residual EV | Total12 EV | t(resid) | MAE | L/S |
|---|---|---:|---:|---:|---:|---:|---:|
| 2021 | ACCEPT_FIRST | 322 | 0.491 | 0.991 | 1.775 | 1.937 | 162/160 |
| 2021 | ADVERSE_FIRST | 244 | 0.616 | 0.116 | 1.844 | 3.033 | 129/115 |
| 2022 | ACCEPT_FIRST | 268 | 0.576 | 1.076 | 1.807 | 1.892 | 136/132 |
| 2022 | ADVERSE_FIRST | 220 | 0.260 | -0.240 | 0.602 | 3.071 | 119/101 |
| 2023 | ACCEPT_FIRST | 265 | 0.990 | 1.490 | 2.492 | 1.799 | 133/132 |
| 2023 | ADVERSE_FIRST | 254 | -0.108 | -0.608 | -0.255 | 3.386 | 113/141 |
| 2024 | ACCEPT_FIRST | 253 | 0.299 | 0.799 | 0.824 | 1.979 | 122/131 |
| 2024 | ADVERSE_FIRST | 280 | 0.051 | -0.449 | 0.144 | 2.909 | 133/147 |
| 2025_H1 | ACCEPT_FIRST | 128 | 0.304 | 0.804 | 0.596 | 2.235 | 68/60 |
| 2025_H1 | ADVERSE_FIRST | 112 | -0.327 | -0.827 | -0.437 | 3.310 | 49/63 |
| 2025_H2 | ACCEPT_FIRST | 132 | -0.054 | 0.446 | -0.119 | 2.603 | 57/75 |
| 2025_H2 | ADVERSE_FIRST | 143 | -0.015 | -0.515 | -0.030 | 3.441 | 74/69 |
| 2026_JAN_JUL | ACCEPT_FIRST | 128 | 0.828 | 1.328 | 1.719 | 2.091 | 58/70 |
| 2026_JAN_JUL | ADVERSE_FIRST | 150 | 0.025 | -0.475 | 0.059 | 3.215 | 70/80 |
| AUG2026_REUSED_AUDIT | ACCEPT_FIRST | 5 | -4.383 | -3.883 | -1.924 | 6.650 | 5/0 |
| AUG2026_REUSED_AUDIT | ADVERSE_FIRST | 7 | -5.625 | -6.125 | -3.574 | 8.808 | 4/3 |
| ALL_PRE_AUG | ACCEPT_FIRST | 1496 | 0.527 | 1.027 | 3.660 | 1.990 | 736/760 |
| ALL_PRE_AUG | ADVERSE_FIRST | 1403 | 0.114 | -0.386 | 0.690 | 3.139 | 687/716 |
| POOLED_RECENT | ACCEPT_FIRST | 260 | 0.380 | 0.880 | 1.147 | 2.425 | 115/145 |
| POOLED_RECENT | ADVERSE_FIRST | 293 | 0.006 | -0.494 | 0.017 | 3.301 | 144/149 |

## Primary 2h pre-Aug by side

| Side | State | N | Residual EV | Total12 EV | t(resid) |
|---|---|---:|---:|---:|---:|
| LONG | ACCEPT_FIRST | 736 | 0.498 | 0.998 | 2.312 |
| LONG | ADVERSE_FIRST | 687 | 0.224 | -0.276 | 0.926 |
| SHORT | ACCEPT_FIRST | 760 | 0.555 | 1.055 | 2.891 |
| SHORT | ADVERSE_FIRST | 716 | 0.007 | -0.493 | 0.032 |

## 7d cluster bootstrap
- clusters: **1**, valid draws: **5000**
- ACCEPT minus ADVERSE residual: **0.413 ATR**, 95% CI **[0.413, 0.413]**

## Gates
- PASS — `lineage_3209_and_timestamp_parity`
- PASS — `eligible_pre_aug_ge_3000`
- PASS — `primary_ambiguous_fraction_le_20pct`
- PASS — `primary_accept_n_ge_400`
- PASS — `primary_adverse_n_ge_400`
- PASS — `primary_accept_residual_positive`
- FAIL — `primary_adverse_residual_nonpositive`
- PASS — `primary_residual_diff_ge_0_25atr`
- PASS — `bootstrap_residual_diff_ci_lower_gt_zero`
- PASS — `primary_accept_total_gt_baseline`
- PASS — `sensitivity_1h_accept_resid_gt_adverse`
- PASS — `sensitivity_4h_accept_resid_gt_adverse`
- PASS — `stress_2022_short_each_n30_accept_gt_adverse`
- PASS — `recent_accept_resid_gt_adverse`

## Guardrail
Primary comparison uses residual return after the first-passage threshold, preventing the +0.5/-0.5 classification move from mechanically creating the result. Same-bar double hits are ambiguous and excluded. No threshold/horizon optimization. August 2026 is reused audit. Live allocation = **0**.
