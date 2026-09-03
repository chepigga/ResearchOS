# BTC_REVERSAL_EDGE_ON_OFF_REGIME_AND_ROUTER_ABSTENTION_LAB_008

**Verdict:** **FAIL_NO_ROBUST_ON_OFF_ROUTER**

Role: causal event-time ON/OFF abstention layer over the frozen LAB006 reversal setup; research only.

## Frozen base
- Exact frozen REV selector + `LIMIT_R0.50_T60` + SL 1R + TP 1.5R + 5 bps.
- Gate can only TRADE or ABSTAIN; it cannot change entry, stop, target, TTL, direction, or size.
- Ridge alpha = 5.0; ON threshold = median training score for each expanding yearly fit.

## Causality boundary
- Gate features are known at impulse close and each yearly gate fit uses only prior completed signal outcomes.
- The inherited LAB003 selector was fit on full DEV 2021–2024, so 2022–2024 are conditional mechanism diagnostics, not end-to-end deployment-causal tests.
- 2025/2026 are stronger forward-transfer audits; August 2026 has zero frozen REV signals and cannot evaluate the gate.

## Primary combined walk-forward

| Year | Signals | ON | Coverage | Base Cum R | Gated Cum R | Δ R | Base EV/op | Gate EV/op | EV/traded | Base PF | Gate PF | Base DD R | Gate DD R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 33 | 7 | 21.2% | -2.79 | -0.55 | +2.24 | -0.085 | -0.017 | -0.079 | 0.781 | 0.834 | 5.87 | 3.33 |
| 2023 | 9 | 4 | 44.4% | +1.57 | -0.87 | -2.44 | +0.175 | -0.097 | -0.218 | 1.698 | 0.612 | 2.25 | 2.25 |
| 2024 | 33 | 20 | 60.6% | -5.66 | -5.99 | -0.32 | -0.172 | -0.181 | -0.299 | 0.671 | 0.490 | 9.48 | 8.12 |
| 2025 | 27 | 15 | 55.6% | +4.96 | -0.96 | -5.93 | +0.184 | -0.036 | -0.064 | 1.556 | 0.857 | 4.06 | 3.42 |
| 2026_JAN_JUL | 22 | 11 | 50.0% | +6.17 | +2.59 | -3.59 | +0.281 | +0.118 | +0.235 | 1.929 | 1.822 | 2.28 | 2.08 |
| FRESH_AUG2026 | 0 | 0 | — | 0 | 0 | 0 | — | — | — | — | — | — | — |

## Pooled primary

- 2022→2026 opportunities: **124**; gate coverage **46.0%**.
- BASE cum: **+4.25R** → GATED: **-5.79R**; delta **-10.04R**.
- BASE max DD: **12.59R** → GATED **11.32R**.
- Recent 2025+2026 BASE **+11.13R** → GATED **+1.62R**; DD 4.06R → 3.42R.

## Audit feature families

| Family | Coverage | Base Cum R | Gated Cum R | Δ R | Base DD | Gate DD | Recent Δ R |
|---|---:|---:|---:|---:|---:|---:|---:|
| ROUTER_ONLY | 52.4% | +4.25 | -0.89 | -5.15 | 12.59 | 12.59 | -6.86 |
| TREND_ONLY | 50.8% | +4.25 | -1.89 | -6.15 | 12.59 | 8.77 | -9.26 |
| VOL_ONLY | 49.2% | +4.25 | +2.21 | -2.05 | 12.59 | 9.59 | -2.47 |
| IMPULSE_ONLY | 47.6% | +4.25 | +2.93 | -1.33 | 12.59 | 7.84 | -8.34 |
| PRIMARY_COMBINED | 46.0% | +4.25 | -5.79 | -10.04 | 12.59 | 11.32 | -9.51 |

## 2026 gate model standardized coefficients

Frozen 2026 ON threshold from 2021–2025 training scores: **+0.0690R-score**; intercept **+0.0482**.

| Feature | Std coefficient |
|---|---:|
| signed_ret24h | +0.2150 |
| impulse_strength | -0.1623 |
| signed_ret30d | -0.1494 |
| router_conf | -0.1477 |
| extreme_pos7d | -0.1372 |
| btc_vol_z | +0.1186 |
| eff24h | +0.0899 |
| signed_ret7d | -0.0811 |
| router_margin | +0.0674 |
| btc_range_z | -0.0668 |
| eff7d | +0.0663 |
| rv_ratio_4h24h | +0.0360 |

## Gates
- FAIL — `pooled_gated_cum_gt_base`
- PASS — `pooled_gated_maxdd_lt_base`
- PASS — `year_2022_delta_positive`
- FAIL — `year_2024_delta_positive`
- FAIL — `year_2025_gated_positive`
- PASS — `y2026_jan_jul_gated_positive`
- FAIL — `positive_years_ge_4_of_5`
- PASS — `pooled_coverage_25_to_75pct`
- PASS — `recent_gated_cum_positive`
- PASS — `recent_gated_maxdd_le_base`

**Score 6/10 → FAIL_NO_ROBUST_ON_OFF_ROUTER**

## Interpretation
- Audit-family results cannot rescue the primary combined gate.
- 2022/2024 improvement is mechanism evidence only because the inherited DEV selector was not historically walk-forward in those years.
- A later end-to-end causal selector replication is mandatory before production or live risk.
