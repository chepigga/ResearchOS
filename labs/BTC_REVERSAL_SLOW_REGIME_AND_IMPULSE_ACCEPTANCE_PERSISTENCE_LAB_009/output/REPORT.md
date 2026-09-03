# BTC_REVERSAL_SLOW_REGIME_AND_IMPULSE_ACCEPTANCE_PERSISTENCE_LAB_009

**Verdict:** **FAIL_NO_ROBUST_SLOW_REGIME**

Role: slow pre-impulse regime + prior-impulse acceptance persistence gate over the frozen reversal branch; research only.

## Frozen base
- Exact frozen REV selector + `LIMIT_R0.50_T60` + SL 1R + TP 1.5R + 5 bps.
- Slow features end before the current 60m impulse window.
- Prior impulse outcomes enter only after +24h15m, strictly before the current signal.
- Ridge alpha = 10.0; ON threshold = median training score.

## Primary slow+acceptance walk-forward

| Year | Signals | ON | Coverage | Base Cum R | Gated Cum R | Δ R | Base EV/op | Gate EV/op | EV/traded | Base PF | Gate PF | Base DD | Gate DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 33 | 13 | 39.4% | -2.79 | +1.08 | +3.87 | -0.085 | +0.033 | +0.083 | 0.781 | 1.351 | 5.87 | 3.09 |
| 2023 | 9 | 3 | 33.3% | +1.57 | -1.14 | -2.71 | +0.175 | -0.127 | -0.381 | 1.698 | 0.000 | 2.25 | 1.14 |
| 2024 | 33 | 10 | 30.3% | -5.66 | +1.63 | +7.29 | -0.172 | +0.049 | +0.163 | 0.671 | 1.391 | 9.48 | 3.13 |
| 2025 | 27 | 5 | 18.5% | +4.96 | -4.45 | -9.42 | +0.184 | -0.165 | -0.891 | 1.556 | 0.000 | 4.06 | 4.45 |
| 2026_JAN_JUL | 22 | 12 | 54.5% | +6.17 | +3.56 | -2.61 | +0.281 | +0.162 | +0.296 | 1.929 | 2.643 | 2.28 | 1.10 |
| FRESH_AUG2026 | 0 | 0 | — | +0.00 | +0.00 | +0.00 | +nan | +nan | +nan | — | — | nan | nan |

## Pooled primary
- 2022→2026 BASE **+4.25R** → GATED **+0.68R**; delta **-3.58R**.
- Pooled coverage **34.7%**; DD 12.59R → 7.36R.
- Recent 2025+2026 BASE **+11.13R** → GATED **-0.90R**; DD 4.06R → 4.45R.

## Audit families

| Family | Coverage | Base Cum R | Gated Cum R | Δ R | Base DD | Gate DD | Recent Δ R |
|---|---:|---:|---:|---:|---:|---:|---:|
| SLOW_ONLY | 37.9% | +4.25 | +0.59 | -3.67 | 12.59 | 5.01 | -11.29 |
| ACCEPTANCE_ONLY | 39.5% | +4.25 | -4.70 | -8.95 | 12.59 | 8.15 | -15.96 |
| SLOW_PLUS_ACCEPTANCE | 34.7% | +4.25 | +0.68 | -3.58 | 12.59 | 7.36 | -12.03 |

## 2026 slow+acceptance model coefficients
Frozen 2026 threshold from 2021–2025 train = **+0.0152R-score**; intercept **+0.0482**.

| Feature | Std coefficient |
|---|---:|
| aligned_ret30d | -0.2049 |
| accept_streak_signed | -0.1704 |
| oriented_pos30d | +0.1690 |
| eff90d | +0.1488 |
| accept_ewm20 | +0.1325 |
| same_dir_accept_rate_10 | -0.1269 |
| accept_rate_10 | +0.1145 |
| eff60d | -0.1102 |
| rv90d | +0.1091 |
| known_impulses_30d | +0.0794 |
| aligned_ret90d | -0.0727 |
| aligned_ret60d | +0.0564 |
| same_dir_mean_cont_10 | -0.0551 |
| rv30d | -0.0452 |
| rv60d | -0.0372 |
| accept_rate_20 | -0.0306 |
| mean_cont_10 | +0.0283 |
| eff30d | -0.0245 |
| rv30_90_ratio | -0.0181 |
| oriented_pos90d | -0.0144 |
| mean_cont_20 | +0.0098 |

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
- FAIL — `recent_gated_maxdd_le_base`

**Score 5/10 → FAIL_NO_ROBUST_SLOW_REGIME**

## Causality/status
- 2022/2024 are mechanism-discovery years and the inherited DEV selector was fit on full 2021–2024; they are not pristine end-to-end forward tests.
- 2025/2026 are reused forward-transfer audits; August was already consumed in LAB007 and has zero frozen REV signals.
- Audit families cannot rescue a failed primary combined gate.
- No live allocation is authorized by this LAB.
