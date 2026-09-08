# BTC_FLOW_LEVEL_DIRECTIONAL_LIQUIDITY_ELASTICITY_AND_THIN_BOOK_CONTINUATION_LAB_040

**Verdict: WATCH_THIN_BOOK_CONTINUATION_POSITIVE_PROOF_INCOMPLETE — 16/25**

## Primary THIN vs WEAK
- frozen HIGH_VOLUME pre-Aug: **568**, resolved LAB039 cells: **414**
- THIN_LIQUIDITY N=**53**, residual **+0.713 ATR**, ACCEPT **0.660**
- WEAK N=**150**, residual **-0.195 ATR**, ACCEPT **0.687**
- residual gap **+0.908 ATR**, 7d bootstrap 95% CI **[-0.539, +2.548]**
- ACCEPT-rate gap **-0.026**, 95% CI **[-0.180, +0.126]**
- THIN frequency **0.82/month**

## Elasticity state discrimination

| Feature | Thin N | Weak N | Thin median | Weak median | RBC | p | BH q |
|---|---:|---:|---:|---:|---:|---:|---:|
| fut_elasticity_15 | 53 | 150 | 0.433 | 0.192 | 0.362 | 0.000 | 0.000 |
| fut_elasticity_30 | 53 | 150 | 0.534 | 0.199 | 0.430 | 0.000 | 0.000 |
| fut_elasticity_60 | 53 | 150 | 1.166 | 0.396 | 0.627 | 0.000 | 0.000 |
| spot_elasticity_15 | 53 | 150 | 0.254 | 0.201 | 0.130 | 0.160 | 0.160 |
| spot_elasticity_30 | 53 | 150 | 0.351 | 0.173 | 0.302 | 0.001 | 0.001 |
| spot_elasticity_60 | 53 | 150 | 0.767 | 0.330 | 0.465 | 0.000 | 0.000 |
| fut_minus_spot_elasticity_60 | 53 | 150 | 0.364 | 0.053 | 0.219 | 0.018 | 0.020 |
| fut_elasticity_accel_15_60 | 53 | 150 | 0.661 | 0.219 | 0.343 | 0.000 | 0.000 |

## LOW_PRESSURE elasticity → residual

| Feature | N | rho | p | BH q |
|---|---:|---:|---:|---:|
| fut_elasticity_15 | 203 | -0.157 | 0.026 | 0.205 |
| fut_elasticity_30 | 203 | -0.065 | 0.360 | 0.523 |
| fut_elasticity_60 | 203 | 0.015 | 0.832 | 0.832 |
| spot_elasticity_15 | 203 | -0.107 | 0.129 | 0.417 |
| spot_elasticity_30 | 203 | -0.060 | 0.392 | 0.523 |
| spot_elasticity_60 | 203 | 0.065 | 0.356 | 0.523 |
| fut_minus_spot_elasticity_60 | 203 | -0.050 | 0.481 | 0.549 |
| fut_elasticity_accel_15_60 | 203 | 0.100 | 0.156 | 0.417 |

## Causal rolling elasticity diagnostic

| State | N | ACCEPT | Residual | Hit | Elasticity | Prior N med |
|---|---:|---:|---:|---:|---:|---:|
| HIGH_ELASTICITY | 210 | 0.700 | 0.396 | 0.505 | 1.320 | 28.000 |
| LOW_ELASTICITY | 204 | 0.598 | 0.050 | 0.475 | 0.170 | 28.000 |
- HIGH−LOW residual bootstrap: **+0.346 ATR**, 95% CI **[-0.554, +1.242]**

## THIN transfer

| Slice | N | ACCEPT | Residual | Hit | L/S |
|---|---:|---:|---:|---:|---:|
| 2021 | 5 | 0.800 | -0.559 | 0.200 | 5/0 |
| 2022 | 4 | 0.750 | -0.835 | 0.250 | 1/3 |
| 2023 | 8 | 0.875 | 5.273 | 0.625 | 5/3 |
| 2024 | 17 | 0.471 | -0.299 | 0.647 | 11/6 |
| 2025_H1 | 6 | 0.500 | 0.539 | 0.500 | 4/2 |
| 2025_H2 | 4 | 1.000 | 1.461 | 0.500 | 3/1 |
| 2026_JAN_JUL | 9 | 0.667 | -0.248 | 0.333 | 3/6 |
| POOLED_RECENT | 13 | 0.769 | 0.278 | 0.385 | 6/7 |
| AUG_REUSED | 0 | — | — | — | 0/0 |
| LONG | 32 | 0.719 | 0.425 | 0.469 | 32/0 |
| SHORT | 21 | 0.571 | 1.153 | 0.524 | 0/21 |
| 2022_SHORT | 3 | 0.667 | -1.506 | 0.000 | 0/3 |

## Gates
- PASS — `frozen_high_volume_ge_500`
- PASS — `resolved_lab039_cells_ge_400`
- PASS — `thin_n_ge_50`
- PASS — `weak_n_ge_120`
- PASS — `thin_residual_positive`
- PASS — `thin_residual_gt_weak`
- PASS — `thin_weak_residual_gap_ge_0_50`
- FAIL — `thin_weak_resid_boot_ci_lower_gt_zero`
- FAIL — `thin_accept_rate_ge_weak`
- FAIL — `accept_rate_boot_ci_lower_gt_zero`
- PASS — `primary_elasticity_thin_gt_weak`
- PASS — `primary_elasticity_state_bh_q_le_0_10`
- PASS — `any_elasticity_state_bh_q_le_0_10`
- PASS — `primary_elasticity_residual_rho_positive`
- FAIL — `primary_elasticity_residual_absrho_ge_0_05`
- FAIL — `primary_elasticity_residual_bh_q_le_0_10`
- PASS — `rolling_high_elasticity_residual_gt_low`
- FAIL — `rolling_elasticity_boot_ci_lower_gt_zero`
- FAIL — `stress_2022_short_thin_positive_n8`
- FAIL — `pooled_recent_thin_positive_n15`
- FAIL — `both_2025h2_2026_thin_positive`
- PASS — `long_thin_positive`
- PASS — `short_thin_positive`
- PASS — `thin_frequency_ge_0_5_per_month`
- PASS — `august_not_used_for_selection`

## Guardrail
Frozen FLOW/LEVEL/HIGH_VOLUME and causal rolling pressure/response lineage from LAB039. Elasticity uses only pre-touch features already frozen in LAB038. No trading execution optimization. August audit-only. Live allocation = **0**.
