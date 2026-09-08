# BTC_SHORT_ACCEPT25_ATR_RANK_MONOTONICITY_AND_WITHIN_PERIOD_CONFOUND_AUDIT_LAB_048

**Verdict: WATCH_ATR_RANK_NONLINEAR_OR_PARTIAL_WITHIN_PERIOD — 15/17**

## Frozen parity
- ACCEPT2.5 trades: **327**; ATR-rank coverage: **100.0%**
- Global Spearman ATR-rank -> netR: **rho +0.232, p=0.0000**

## Fixed absolute ATR-rank quintiles

| Bin | Range | N | EV | PF | CumR |
|---:|---|---:|---:|---:|---:|
| Q1 | 0.0-0.2 | 45 | -0.110 | 0.809 | -4.94 |
| Q2 | 0.2-0.4 | 66 | -0.076 | 0.871 | -5.03 |
| Q3 | 0.4-0.6 | 67 | +0.244 | 1.557 | +16.35 |
| Q4 | 0.6-0.8 | 79 | +0.002 | 1.003 | +0.12 |
| Q5 | 0.8-1.0 | 70 | +0.310 | 1.765 | +21.71 |

Q5-Q1 EV gap: **+0.420R**, 7d bootstrap 95% CI **[+0.011, +0.853]**
Quintile midpoint-vs-EV Spearman: **+0.900**

## Fixed absolute ATR-rank deciles

| Bin | N | EV | PF |
|---:|---:|---:|---:|
| D1 | 21 | +0.140 | 1.310 |
| D2 | 24 | -0.328 | 0.521 |
| D3 | 24 | -0.047 | 0.920 |
| D4 | 42 | -0.093 | 0.844 |
| D5 | 29 | +0.687 | 3.414 |
| D6 | 38 | -0.094 | 0.830 |
| D7 | 39 | -0.087 | 0.849 |
| D8 | 40 | +0.088 | 1.232 |
| D9 | 32 | +0.274 | 1.656 |
| D10 | 38 | +0.341 | 1.863 |

D10-D1 EV gap: **+0.201R**; decile midpoint-vs-EV Spearman: **+0.406**

## Within-period fixed-effects audit
- Fixed-effects ATR beta: **+0.367 R per full 0->1 ATR-rank move**
- 7d cluster bootstrap 95% CI: **[-0.113, +0.816]**, clusters=197

| Period | N | rho ATR->netR | p | EV | ATR mean |
|---|---:|---:|---:|---:|---:|
| 2021 | 62 | +0.284 | 0.026 | +0.238 | 0.509 |
| 2022 | 49 | +0.332 | 0.020 | -0.040 | 0.422 |
| 2023 | 52 | +0.202 | 0.151 | -0.006 | 0.606 |
| 2024 | 64 | +0.174 | 0.168 | +0.084 | 0.657 |
| 2025_H1 | 32 | +0.257 | 0.155 | -0.114 | 0.459 |
| 2025_H2 | 33 | +0.436 | 0.011 | +0.117 | 0.596 |
| 2026_JAN_JUL | 35 | +0.270 | 0.117 | +0.290 | 0.494 |

Positive within-period rho signs (N>=20): **7/7**

## LAB047 half-split parity

| State | N | Trade EV | PF | CumR | EV/original |
|---|---:|---:|---:|---:|---:|
| ALL | 327 | +0.086 | 1.176 | +28.22 | +0.059 |
| HIGH_ATR | 187 | +0.098 | 1.209 | +18.26 | +0.038 |
| LOW_ATR | 140 | +0.071 | 1.136 | +9.96 | +0.021 |

## Gates
- PASS — `exact_frozen_accept25_n327`
- PASS — `atr_rank_coverage_ge99pct`
- PASS — `fixed_absolute_bins_only`
- PASS — `global_atr_rho_positive`
- PASS — `global_rho_p_le_005`
- PASS — `q5_q1_ev_gap_positive`
- PASS — `q5_q1_boot_lower_gt0`
- PASS — `quintile_mid_ev_rho_ge_070`
- PASS — `d10_d1_ev_gap_positive`
- FAIL — `decile_mid_ev_rho_ge_050`
- PASS — `fixed_effect_atr_beta_positive`
- FAIL — `fixed_effect_boot_lower_gt0`
- PASS — `at_least_5_of_7_period_rhos_positive`
- PASS — `2025h2_within_rho_nonnegative`
- PASS — `2026_within_rho_nonnegative`
- PASS — `lab047_half_split_parity`
- PASS — `august_not_used_for_selection`

## Guardrail
Audit only. No ATR cutoff/router is promoted here. Fixed absolute bins and frozen execution/payoff only; reused historical lineage, not fresh OOS. Live allocation = **0**.
