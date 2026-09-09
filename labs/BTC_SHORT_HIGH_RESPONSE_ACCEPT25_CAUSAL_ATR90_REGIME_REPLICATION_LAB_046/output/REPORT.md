# BTC_SHORT_HIGH_RESPONSE_ACCEPT25_CAUSAL_ATR90_REGIME_REPLICATION_LAB_046

**Verdict: WATCH_ATR90_REGIME_POSITIVE_PROOF_INCOMPLETE — 14/24**

## Frozen router summary

| State | N | Share | EV0 | EV5 | EV10 | PF5 | Win | CumR5 | MaxDD R | DD@0.25% | Contribution | EV/orig475 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 327 | 1.000 | +0.148 | +0.086 | +0.024 | 1.176 | 0.471 | +28.22 | 11.44 | 2.86% | 1.000 | +0.059 |
| HIGH_ATR90 | 187 | 0.572 | +0.148 | +0.098 | +0.047 | 1.209 | 0.481 | +18.26 | 14.61 | 3.65% | 0.647 | +0.038 |
| LOW_ATR90 | 140 | 0.428 | +0.148 | +0.071 | -0.006 | 1.136 | 0.457 | +9.96 | 8.83 | 2.21% | 0.353 | +0.021 |

## 7d cluster bootstrap
- HIGH_ATR90 − LOW_ATR90 EV5: **+0.027 R**, 95% CI **[-0.210, +0.264]**, clusters=197

## Fixed transfer

| Slice | State | N | EV5 | PF5 | CumR5 | Win |
|---|---|---:|---:|---:|---:|---:|
| 2021 | HIGH_ATR90 | 33 | +0.464 | 2.374 | +15.31 | 0.606 |
| 2021 | LOW_ATR90 | 29 | -0.019 | 0.963 | -0.56 | 0.414 |
| 2022 | HIGH_ATR90 | 17 | -0.228 | 0.637 | -3.88 | 0.353 |
| 2022 | LOW_ATR90 | 32 | +0.060 | 1.111 | +1.91 | 0.438 |
| 2023 | HIGH_ATR90 | 35 | -0.092 | 0.820 | -3.23 | 0.400 |
| 2023 | LOW_ATR90 | 17 | +0.172 | 1.353 | +2.92 | 0.471 |
| 2024 | HIGH_ATR90 | 48 | -0.011 | 0.978 | -0.51 | 0.417 |
| 2024 | LOW_ATR90 | 16 | +0.369 | 1.872 | +5.90 | 0.562 |
| 2025_H1 | HIGH_ATR90 | 15 | -0.224 | 0.613 | -3.36 | 0.400 |
| 2025_H1 | LOW_ATR90 | 17 | -0.018 | 0.967 | -0.31 | 0.471 |
| 2025_H2 | HIGH_ATR90 | 22 | +0.294 | 1.738 | +6.46 | 0.591 |
| 2025_H2 | LOW_ATR90 | 11 | -0.237 | 0.617 | -2.61 | 0.364 |
| 2026_JAN_JUL | HIGH_ATR90 | 17 | +0.439 | 2.160 | +7.46 | 0.647 |
| 2026_JAN_JUL | LOW_ATR90 | 18 | +0.150 | 1.280 | +2.70 | 0.500 |
| POOLED_RECENT | HIGH_ATR90 | 39 | +0.357 | 1.917 | +13.92 | 0.615 |
| POOLED_RECENT | LOW_ATR90 | 29 | +0.003 | 1.006 | +0.10 | 0.448 |
| BAD_COMPOSITE | HIGH_ATR90 | 67 | -0.156 | 0.719 | -10.46 | 0.388 |
| BAD_COMPOSITE | LOW_ATR90 | 66 | +0.069 | 1.130 | +4.52 | 0.455 |

## Gates
- PASS — `exact_formal_accept25_n_327`
- PASS — `atr_rank_90d_coverage_100pct`
- PASS — `frozen_lab044_payoff_entry_parity_100pct`
- PASS — `high_atr_n_ge_130`
- PASS — `low_atr_n_ge_130`
- PASS — `high_atr_ev5_positive`
- PASS — `high_atr_pf5_ge_1_20`
- FAIL — `low_atr_ev5_le_zero`
- FAIL — `high_minus_low_gap_ge_0_20r`
- FAIL — `cluster_boot_ci_lower_gt_zero`
- PASS — `high_atr_ev10_positive`
- PASS — `high_atr_dd_025_le_4pct`
- FAIL — `high_atr_ev_per_original475_ge_0_05`
- FAIL — `high_atr_captures_ge_75pct_full_cumr`
- PASS — `2021_high_ev_positive`
- FAIL — `2022_high_ev_positive`
- FAIL — `2023_high_ev_positive`
- FAIL — `2024_high_ev_positive`
- FAIL — `2025h1_high_ev_positive`
- PASS — `2025h2_high_ev_positive`
- PASS — `2026_high_ev_positive`
- PASS — `pooled_recent_high_positive_n30`
- FAIL — `bad_composite_high_ev_gt_low`
- PASS — `august_not_used_for_selection`

## Guardrail
Single fixed ATR90 rank boundary = 0.50, reused exactly from LAB045 causal pre-entry regime clock. No alternate threshold/feature/execution search. Reused historical replication, not fresh OOS. Live allocation = **0**.
