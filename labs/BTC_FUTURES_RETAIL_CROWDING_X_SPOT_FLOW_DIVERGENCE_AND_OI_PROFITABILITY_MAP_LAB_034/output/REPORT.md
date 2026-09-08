# BTC_FUTURES_RETAIL_CROWDING_X_SPOT_FLOW_DIVERGENCE_AND_OI_PROFITABILITY_MAP_LAB_034

**Verdict: FAIL_NO_FUTURES_SPOT_DIVERGENCE_QUALITY_EDGE — 7/14**

## Coverage
- frozen flow rows: **3209**; joined: **3207**
- pre-Aug spot/futures/metrics coverage: **99.9% / 100.0% / 100.0%**

## Threshold-free feature tests

| Feature | N | rho→12h | p | BH q | Missing |
|---|---:|---:|---:|---:|---:|
| retail_ratio_level | 3194 | -0.007 | 0.675 | 0.750 | 0.000 |
| crowd_change_strength | 3191 | 0.012 | 0.513 | 0.642 | 0.001 |
| oi_logchg_3h | 3185 | 0.017 | 0.340 | 0.567 | 0.003 |
| futures_taker_imb_3h | 3194 | -0.019 | 0.271 | 0.542 | 0.000 |
| spot_taker_imb_3h | 3194 | -0.029 | 0.101 | 0.475 | 0.000 |
| spot_trade_confirmation | 3194 | -0.026 | 0.146 | 0.475 | 0.000 |
| futures_trade_confirmation | 3194 | -0.024 | 0.168 | 0.475 | 0.000 |
| leveraged_vs_spot_divergence | 3194 | -0.005 | 0.776 | 0.776 | 0.000 |
| top_count_vs_retail_logdiv | 2738 | -0.025 | 0.190 | 0.475 | 0.143 |
| top_position_vs_retail_logdiv | 2738 | -0.016 | 0.410 | 0.586 | 0.143 |

## leveraged_vs_spot_divergence quintiles

| Q | N | Mean ATR | Hit |
|---|---:|---:|---:|
| Q1 | 639 | 0.101 | 0.487 |
| Q2 | 639 | 0.687 | 0.543 |
| Q3 | 638 | 0.237 | 0.492 |
| Q4 | 639 | 0.606 | 0.534 |
| Q5 | 639 | 0.097 | 0.487 |

Q5-Q1 = **-0.005 ATR**, 7d bootstrap 95% CI **[-0.740, 0.760]**

## Fixed OI × divergence × spot confirmation map

| OI up | Div+ | Spot confirms trade | N | Mean ATR | Hit |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 414 | 0.515 | 0.553 |
| 0 | 0 | 1 | 254 | 0.163 | 0.484 |
| 0 | 1 | 0 | 202 | 0.117 | 0.530 |
| 0 | 1 | 1 | 633 | 0.131 | 0.491 |
| 1 | 0 | 0 | 491 | 0.304 | 0.505 |
| 1 | 0 | 1 | 314 | 0.337 | 0.478 |
| 1 | 1 | 0 | 157 | 0.693 | 0.490 |
| 1 | 1 | 1 | 720 | 0.517 | 0.521 |

## Transfer / side divergence rho

| Slice | N | rho | p | Mean ATR |
|---|---:|---:|---:|---:|
| ALL_PRE_AUG | 3194 | -0.005 | 0.776 | 0.345 |
| LONG | 1562 | -0.026 | 0.313 | 0.378 |
| SHORT | 1632 | 0.016 | 0.518 | 0.314 |
| 2022_SHORT | 253 | 0.122 | 0.052 | 0.948 |
| 2025_H2 | 309 | -0.042 | 0.458 | 0.011 |
| 2026_JAN_JUL | 316 | 0.037 | 0.508 | 0.202 |
| AUG_REUSED | 13 | 0.324 | 0.280 | -5.530 |

## Gates
- PASS — `exact_frozen_flow_lineage_ge_3200`
- PASS — `spot_kline_coverage_ge_90pct`
- PASS — `futures_kline_coverage_ge_90pct`
- PASS — `metrics_oi_coverage_ge_90pct`
- FAIL — `at_least_one_feature_bh_q_le_0_10`
- FAIL — `at_least_one_feature_abs_rho_ge_0_05`
- FAIL — `divergence_rho_positive`
- FAIL — `divergence_q5_minus_q1_ge_0_20`
- FAIL — `divergence_boot_ci_lower_gt_zero`
- PASS — `oi_up_positive_div_cell_beats_baseline_0_15`
- PASS — `stress_2022_short_high_div_positive`
- FAIL — `long_short_divergence_rho_same_sign`
- FAIL — `2025h2_2026_divergence_rho_same_sign`
- PASS — `august_not_used_for_selection`

## Guardrail
This LAB maps quality on reused frozen signals only. No quintile/cell/feature cutoff is promoted. No entry/stop/TP optimization. August 2026 is audit-only. Live allocation = **0**.
