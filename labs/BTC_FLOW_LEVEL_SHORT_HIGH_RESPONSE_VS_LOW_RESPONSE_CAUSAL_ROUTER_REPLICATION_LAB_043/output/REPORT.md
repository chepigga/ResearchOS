# BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043

**Verdict: PASS_SHORT_HIGH_RESPONSE_CAUSAL_ROUTER_REPLICATION — 25/25**

## Primary SHORT response router
- frozen resolved SHORT pre-Aug: **963**; HIGH_RESPONSE **475**, LOW_RESPONSE **488**
- HIGH_RESPONSE residual **+0.799 ATR**, hit **0.524**, ACCEPT **0.697**
- LOW_RESPONSE residual **-0.195 ATR**, hit **0.455**, ACCEPT **0.662**
- gap **+0.994 ATR**, 7d bootstrap 95% CI **[+0.283, +1.710]**, clusters=275
- HIGH_RESPONSE frequency **7.20/month**

## Frozen component decomposition

| Component | N | ACCEPT | Residual | Hit |
|---|---:|---:|---:|---:|
| DRIVEN_MOVE | 367 | 0.687 | +0.650 | 0.523 |
| THIN_BOOK | 108 | 0.731 | +1.303 | 0.528 |
| ABSORPTION | 153 | 0.595 | -0.302 | 0.425 |
| WEAK | 335 | 0.693 | -0.147 | 0.469 |

## Transfer

| Slice | HIGH N | HIGH residual | LOW N | LOW residual | Gap |
|---|---:|---:|---:|---:|---:|
| 2021 | 82 | +1.123 | 81 | -0.136 | +1.260 |
| 2022 | 79 | +0.784 | 83 | +0.397 | +0.388 |
| 2023 | 83 | +0.476 | 85 | -0.044 | +0.520 |
| 2024 | 94 | +0.670 | 86 | -0.972 | +1.642 |
| 2025_H1 | 46 | +1.107 | 41 | -0.185 | +1.292 |
| 2025_H2 | 44 | +0.063 | 50 | -0.258 | +0.321 |
| 2026_JAN_JUL | 47 | +1.471 | 62 | -0.152 | +1.622 |
| POOLED_RECENT | 91 | +0.790 | 112 | -0.199 | +0.989 |
| AUG_REUSED | 1 | -3.173 | 0 | +nan | +nan |

## Gates
- PASS — `short_resolved_preaug_ge_900`
- PASS — `high_response_n_ge_450`
- PASS — `low_response_n_ge_450`
- PASS — `high_response_residual_positive`
- PASS — `low_response_residual_le_zero`
- PASS — `residual_gap_ge_0_50`
- PASS — `cluster_boot_ci_lower_gt_zero`
- PASS — `high_response_hit_ge_0_50`
- PASS — `high_response_frequency_ge_6_month`
- PASS — `2021_high_positive`
- PASS — `2022_high_positive`
- PASS — `2023_high_positive`
- PASS — `2024_high_positive`
- PASS — `2025h1_high_positive`
- PASS — `2025h2_high_positive`
- PASS — `2026_high_positive`
- PASS — `pooled_recent_high_positive_n60`
- PASS — `pooled_recent_low_le_zero_n60`
- PASS — `pooled_recent_gap_ge_0_50`
- PASS — `2022_stress_high_positive_n50`
- PASS — `thin_book_short_positive`
- PASS — `driven_move_short_positive`
- PASS — `absorption_short_le_zero`
- PASS — `weak_short_le_zero`
- PASS — `august_not_used_for_selection`

## Guardrail
Frozen LAB041 causal states collapsed to SHORT HIGH_RESPONSE vs LOW_RESPONSE only. No new thresholds/features/execution optimization. Reused historical lineage, not fresh OOS. August audit-only. Live allocation = **0**.
