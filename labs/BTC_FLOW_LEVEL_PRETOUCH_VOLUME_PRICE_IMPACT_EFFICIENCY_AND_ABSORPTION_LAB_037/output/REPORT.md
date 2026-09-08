# BTC_FLOW_LEVEL_PRETOUCH_VOLUME_PRICE_IMPACT_EFFICIENCY_AND_ABSORPTION_LAB_037

**Verdict: WATCH_PRICE_IMPACT_DIRECTIONALLY_USEFUL_TRANSFER_INCOMPLETE — 11/17**

## Coverage
- frozen HIGH_VOLUME pre-Aug: **568**; IGNITION **365**, ABSORPTION **203**
- futures primary impact coverage: **100.0%**; spot primary impact coverage: **100.0%**

## HIGH_VOLUME ignition vs absorption impact

| Feature | Ign N | Abs N | Ign median | Abs median | RBC | p | BH q |
|---|---:|---:|---:|---:|---:|---:|---:|
| fut_impact_eff_15 | 365 | 203 | 0.155 | 0.147 | -0.041 | 0.420 | 0.761 |
| fut_impact_eff_30 | 365 | 203 | 0.266 | 0.247 | -0.013 | 0.801 | 0.801 |
| fut_impact_eff_60 | 365 | 203 | 0.487 | 0.470 | 0.054 | 0.287 | 0.761 |
| spot_impact_eff_15 | 365 | 203 | 0.186 | 0.183 | -0.056 | 0.270 | 0.761 |
| spot_impact_eff_30 | 365 | 203 | 0.306 | 0.280 | -0.031 | 0.544 | 0.761 |
| spot_impact_eff_60 | 365 | 203 | 0.605 | 0.561 | 0.039 | 0.445 | 0.761 |
| fut_minus_spot_impact_60 | 365 | 203 | -0.065 | -0.048 | -0.017 | 0.742 | 0.801 |

## ACCEPT impact → post-classification residual

| Feature | N | rho | p | BH q |
|---|---:|---:|---:|---:|
| fut_impact_eff_15 | 1363 | -0.030 | 0.264 | 0.586 |
| fut_impact_eff_30 | 1363 | -0.005 | 0.857 | 0.886 |
| fut_impact_eff_60 | 1363 | 0.022 | 0.418 | 0.586 |
| spot_impact_eff_15 | 1362 | -0.026 | 0.336 | 0.586 |
| spot_impact_eff_30 | 1363 | 0.004 | 0.886 | 0.886 |
| spot_impact_eff_60 | 1363 | 0.031 | 0.248 | 0.586 |
| fut_minus_spot_impact_60 | 1363 | -0.040 | 0.139 | 0.586 |

## Primary median-half cluster audit
- frozen pre-Aug HIGH_VOLUME median `fut_impact_eff_60` = **0.4822**
- HIGH impact N=284 residual **+0.650 ATR**; LOW impact N=284 residual **+0.031 ATR**
- difference **+0.619 ATR**, 7d bootstrap 95% CI **[-0.158, +1.399]**, clusters=239

## High-impact HIGH_VOLUME transfer

| Slice | N | Residual | Hit | Impact median | L/S |
|---|---:|---:|---:|---:|---:|
| 2021 | 62 | 0.663 | 0.581 | 0.931 | 28/34 |
| 2022 | 50 | 0.178 | 0.480 | 0.950 | 24/26 |
| 2023 | 44 | 2.296 | 0.523 | 0.749 | 26/18 |
| 2024 | 48 | 0.562 | 0.542 | 0.697 | 26/22 |
| 2025_H1 | 16 | -0.823 | 0.438 | 0.839 | 3/13 |
| 2025_H2 | 26 | 0.608 | 0.538 | 0.805 | 14/12 |
| 2026_JAN_JUL | 38 | 0.103 | 0.421 | 0.808 | 20/18 |
| POOLED_RECENT | 64 | 0.308 | 0.469 | 0.806 | 34/30 |
| AUG_REUSED | 1 | -3.173 | 0.000 | 1.504 | 0/1 |
| LONG | 141 | 0.549 | 0.496 | 0.859 | 141/0 |
| SHORT | 143 | 0.750 | 0.531 | 0.823 | 0/143 |
| 2022_SHORT | 26 | 0.649 | 0.500 | 0.971 | 0/26 |

## Gates
- PASS — `frozen_lab036_high_volume_ge_500`
- PASS — `futures_impact_coverage_ge_95pct`
- PASS — `spot_impact_coverage_ge_95pct`
- PASS — `ignition_ge_150_absorption_ge_100`
- PASS — `primary_ignition_gt_absorption`
- FAIL — `primary_rbc_ge_0_10`
- FAIL — `primary_state_bh_q_le_0_10`
- FAIL — `any_state_feature_bh_q_le_0_10`
- PASS — `primary_accept_residual_rho_positive`
- FAIL — `primary_accept_residual_absrho_ge_0_05`
- FAIL — `primary_residual_bh_q_le_0_10`
- PASS — `high_minus_low_residual_ge_0_15`
- FAIL — `cluster_boot_ci_lower_gt_zero`
- PASS — `stress_2022_short_highimpact_positive_n20`
- PASS — `pooled_recent_highimpact_positive_n40`
- PASS — `both_2025h2_2026_highimpact_positive`
- PASS — `august_not_used_for_selection`

## Guardrail
Frozen LAB035–036 FLOW/level/touch/acceptance/high-volume lineage. All impact features exclude the touch bar and use only strictly prior rolling normalization. Median split is diagnostic-only and cannot be promoted without independent replication. No entry/SL/TP optimization. August 2026 audit-only. Live allocation = **0**.
