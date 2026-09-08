# BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041

**Verdict: WATCH_ALL_TOUCH_THIN_BOOK_POSITIVE_PROOF_INCOMPLETE — 15/25**

## All-touch universe
- classified pre-Aug: **1966**; rolling resolved: **1926 (98.0%)**
- THIN_BOOK N=**264**, residual **+0.382 ATR**, ACCEPT **0.720**
- WEAK N=**690**, residual **+0.154 ATR**, ACCEPT **0.716**
- THIN-WEAK residual gap **+0.228 ATR**, 7d bootstrap 95% CI **[-0.527, +1.007]**
- THIN frequency **4.00/month**

## Rolling book states

| State | N | ACCEPT | Residual | Hit | Pressure | Response | Elasticity |
|---|---:|---:|---:|---:|---:|---:|---:|
| THIN_BOOK | 264 | 0.720 | +0.382 | 0.458 | 0.682 | 1.495 | 2.999 |
| DRIVEN_MOVE | 700 | 0.689 | +0.567 | 0.517 | 4.362 | 2.368 | 0.683 |
| ABSORPTION | 272 | 0.632 | -0.092 | 0.430 | 2.715 | 0.217 | 0.093 |
| WEAK | 690 | 0.716 | +0.154 | 0.475 | 0.587 | 0.337 | 0.778 |

## Rolling elasticity

- HIGH_ELASTICITY: N=978, residual **+0.416 ATR**, ACCEPT 0.708, mean elasticity 1.745
- LOW_ELASTICITY: N=948, residual **+0.181 ATR**, ACCEPT 0.681, mean elasticity 0.133
- HIGH−LOW elasticity residual gap **+0.234 ATR**, 95% CI **[-0.263, +0.728]**

## LOW_PRESSURE elasticity → residual

| Feature | N | rho | p | BH q |
|---|---:|---:|---:|---:|
| fut_elasticity_15 | 954 | -0.058 | 0.074 | 0.588 |
| fut_elasticity_30 | 954 | -0.010 | 0.755 | 0.811 |
| fut_elasticity_60 | 954 | -0.011 | 0.729 | 0.811 |
| spot_elasticity_15 | 954 | -0.033 | 0.314 | 0.811 |
| spot_elasticity_30 | 954 | -0.008 | 0.811 | 0.811 |
| spot_elasticity_60 | 954 | 0.016 | 0.627 | 0.811 |
| fut_minus_spot_elasticity_60 | 954 | -0.010 | 0.755 | 0.811 |
| fut_elasticity_accel_15_60 | 954 | 0.013 | 0.688 | 0.811 |

## THIN transfer

| Slice | N | ACCEPT | Residual | Hit | L/S |
|---|---:|---:|---:|---:|---:|
| 2021 | 43 | 0.628 | -0.917 | 0.442 | 29/14 |
| 2022 | 31 | 0.710 | +1.619 | 0.484 | 14/17 |
| 2023 | 41 | 0.780 | +0.567 | 0.463 | 20/21 |
| 2024 | 53 | 0.717 | +0.259 | 0.453 | 35/18 |
| 2025_H1 | 27 | 0.741 | +1.013 | 0.444 | 16/11 |
| 2025_H2 | 36 | 0.833 | +0.245 | 0.472 | 20/16 |
| 2026_JAN_JUL | 33 | 0.636 | +0.510 | 0.455 | 22/11 |
| POOLED_RECENT | 69 | 0.739 | +0.372 | 0.464 | 42/27 |
| AUG_REUSED | 3 | 0.333 | -6.033 | 0.333 | 3/0 |
| LONG | 156 | 0.712 | -0.256 | 0.410 | 156/0 |
| SHORT | 108 | 0.731 | +1.303 | 0.528 | 0/108 |
| 2022_SHORT | 17 | 0.529 | +2.081 | 0.529 | 0/17 |

## Gates
- PASS — `all_classified_preaug_ge_1900`
- PASS — `feature_coverage_ge_95pct`
- PASS — `rolling_resolved_ge_85pct`
- PASS — `thin_n_ge_250`
- PASS — `weak_n_ge_250`
- PASS — `thin_residual_positive`
- PASS — `thin_residual_gt_weak`
- FAIL — `thin_weak_gap_ge_0_30`
- FAIL — `thin_weak_boot_ci_lower_gt_zero`
- PASS — `thin_accept_ge_weak`
- PASS — `thin_frequency_ge_3_month`
- PASS — `rolling_high_elasticity_gt_low`
- PASS — `rolling_elasticity_gap_ge_0_20`
- FAIL — `rolling_elasticity_boot_ci_lower_gt_zero`
- FAIL — `primary_elasticity_rho_positive`
- FAIL — `primary_elasticity_absrho_ge_0_05`
- FAIL — `primary_elasticity_bh_q_le_0_10`
- FAIL — `any_elasticity_feature_bh_q_le_0_10`
- FAIL — `long_thin_positive_n100`
- PASS — `short_thin_positive_n100`
- FAIL — `stress_2022_short_positive_n20`
- FAIL — `pooled_recent_positive_n80`
- PASS — `2025h2_positive`
- PASS — `2026_positive`
- PASS — `august_not_used`

## Guardrail
No HIGH_VOLUME gate. Rolling thresholds use only strictly prior 90d all-touch history, minimum 40 prior touches, no global fallback. Touch bar excluded in source features. No execution optimization. August audit-only. Live allocation = **0**.
