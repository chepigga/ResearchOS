# BTC_REVERSAL_SLOW_STATE_TRANSITION_AND_REGIME_ONSET_LAB_010

**Verdict:** **FAIL_NO_ROBUST_TRANSITION_ONSET**

Role: causal pre-impulse slow-state transition/onset gate over the frozen reversal branch; research only.

## Frozen base
- Exact frozen REV selector + `LIMIT_R0.50_T60` + SL 1R + TP 1.5R + 5 bps.
- Transition features are computed from slow-state series ending before the current 60m impulse window.
- No acceptance-history, router-score, current impulse-shape, or post-impulse path feature enters the primary gate.
- Ridge alpha = 10.0; ON threshold = median training score.

## Primary transition walk-forward

| Year | Signals | ON | Coverage | Base Cum R | Gated Cum R | Δ R | Base EV/op | Gate EV/op | EV/traded | Base PF | Gate PF | Base DD | Gate DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 33 | 19 | 57.6% | -2.79 | -0.89 | +1.90 | -0.085 | -0.027 | -0.047 | 0.781 | 0.863 | 5.87 | 3.93 |
| 2023 | 9 | 6 | 66.7% | +1.57 | -0.35 | -1.92 | +0.175 | -0.039 | -0.058 | 1.698 | 0.845 | 2.25 | 2.25 |
| 2024 | 33 | 16 | 48.5% | -5.66 | -1.74 | +3.92 | -0.172 | -0.053 | -0.109 | 0.671 | 0.770 | 9.48 | 3.84 |
| 2025 | 27 | 13 | 48.1% | +4.96 | -0.09 | -5.05 | +0.184 | -0.003 | -0.007 | 1.556 | 0.985 | 4.06 | 3.38 |
| 2026_JAN_JUL | 22 | 8 | 36.4% | +6.17 | +3.23 | -2.94 | +0.281 | +0.147 | +0.404 | 1.929 | 4.029 | 2.28 | 1.07 |
| FRESH_AUG2026 | 0 | 0 | — | +0.00 | +0.00 | +0.00 | — | — | — | — | — | — | — |

## Pooled primary
- 2022→2026 BASE **+4.25R** → GATED **+0.17R**; delta **-4.09R**.
- Pooled coverage **50.0%**; DD 12.59R → 8.84R.
- Recent 2025+2026 BASE **+11.13R** → GATED **+3.14R**; DD 4.06R → 3.38R.

## 2025 onset localization

| Period | Signals | ON | Coverage | Base Cum R | Gated Cum R | Δ R | Mean score | Frozen threshold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025_H1 | 11 | 9 | 81.8% | -1.68 | -0.56 | +1.12 | +0.3086 | +0.0575 |
| 2025_H2 | 16 | 4 | 25.0% | +6.64 | +0.48 | -6.17 | -0.1698 | +0.0575 |

## Audit transition families

| Family | Coverage | Base Cum R | Gated Cum R | Δ R | Base DD | Gate DD | Recent Δ R |
|---|---:|---:|---:|---:|---:|---:|---:|
| TREND_TRANSITION | 45.2% | +4.25 | +0.47 | -3.79 | 12.59 | 8.31 | -8.59 |
| EFFICIENCY_TRANSITION | 62.9% | +4.25 | +4.45 | +0.20 | 12.59 | 10.07 | -5.95 |
| VOL_TRANSITION | 29.8% | +4.25 | -6.02 | -10.27 | 12.59 | 10.33 | -8.43 |
| POSITION_TRANSITION | 45.2% | +4.25 | +0.65 | -3.60 | 12.59 | 7.28 | -6.47 |
| TRANSITION_COMBINED | 50.0% | +4.25 | +0.17 | -4.09 | 12.59 | 8.84 | -7.99 |

## Frozen 2025 transition coefficients
2025 threshold from 2021–2024 train = **+0.0575R-score**; intercept **+0.0182**.

| Feature | Std coefficient |
|---|---:|
| d7_aligned_ret60d | -0.2519 |
| d7_rv30_90_ratio | -0.2510 |
| d7_oriented_pos30d | +0.2068 |
| d30_rv30_90_ratio | +0.2066 |
| d30_eff60d | -0.1758 |
| d30_eff90d | +0.1700 |
| d7_aligned_ret30d | -0.1689 |
| d30_aligned_ret60d | +0.1376 |
| d30_eff30d | +0.1314 |
| d7_eff60d | -0.1257 |
| d30_rv60d | -0.1091 |
| curve_ret30_60 | +0.0986 |
| d7_eff90d | +0.0948 |
| d7_rv90d | +0.0780 |
| d30_rv90d | -0.0715 |
| d7_eff30d | -0.0712 |

## Gates
- FAIL — `pooled_gated_cum_gt_base`
- PASS — `pooled_gated_maxdd_lt_base`
- PASS — `year_2022_delta_positive`
- PASS — `year_2024_delta_positive`
- FAIL — `year_2025_gated_positive`
- PASS — `y2026_jan_jul_gated_positive`
- FAIL — `positive_years_ge_4_of_5`
- PASS — `pooled_coverage_25_to_75pct`
- FAIL — `recent_retains_ge_70pct_base`
- PASS — `recent_gated_maxdd_le_base`

**Score 6/10 → FAIL_NO_ROBUST_TRANSITION_ONSET**

## Causality/status
- 2022/2024 are mechanism-discovery years; inherited selector was fit on full DEV 2021–2024.
- 2025 is the key onset transfer check: its transition gate is trained only on 2021–2024 outcomes.
- 2026 is a reused forward-transfer audit; August has zero frozen REV opportunities.
- Audit families cannot rescue a failed primary combined transition gate.
- No live allocation is authorized by this LAB.
