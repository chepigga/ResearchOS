# BTC_SHORT_HIGH_RESPONSE_ACCEPT25_BAD_REGIME_AND_YEARLY_FAILURE_STATE_LAB_045

**Verdict: WATCH_FAILURE_STATE_PARTIAL_REUSED — 11/22**

## Frozen lineage
- ACCEPT2.5 trades: **327**; BAD **133**, GOOD **194**
- futures/metrics feature coverage: **100.0% / 99.7%**
- regime clock: **entry_time - 15m**

## BAD vs GOOD causal regime features

| Feature | Bad N | Good N | Bad mean | Good mean | RBC | p | BH q |
|---|---:|---:|---:|---:|---:|---:|---:|
| downside_extension_72h_atr | 133 | 194 | 12.563 | 10.902 | 0.129 | 0.048 | 0.159 |
| bear_trend_eff_24h | 133 | 194 | 0.069 | 0.070 | -0.018 | 0.782 | 0.869 |
| flow_persist_12h | 133 | 194 | 0.646 | 0.630 | 0.026 | 0.688 | 0.860 |
| bear_trend_24h_atr | 133 | 194 | 2.885 | 3.105 | -0.002 | 0.981 | 0.981 |
| bear_trend_72h_atr | 133 | 194 | 3.127 | 0.521 | 0.146 | 0.025 | 0.146 |
| downside_extension_24h_atr | 133 | 194 | 7.889 | 7.564 | 0.058 | 0.373 | 0.533 |
| atr_rank_90d | 133 | 194 | 0.503 | 0.570 | -0.142 | 0.029 | 0.146 |
| flow_persist_3h | 133 | 194 | 0.676 | 0.738 | -0.110 | 0.080 | 0.159 |
| oi_logchg_3h | 133 | 193 | -0.002 | 0.003 | -0.093 | 0.156 | 0.260 |
| oi_logchg_12h | 133 | 194 | -0.001 | 0.006 | -0.118 | 0.069 | 0.159 |

## Feature → frozen trade payoff

| Feature | N | rho→netR | p | BH q |
|---|---:|---:|---:|---:|
| downside_extension_72h_atr | 327 | -0.060 | 0.278 | 0.599 |
| bear_trend_eff_24h | 327 | 0.026 | 0.645 | 0.843 |
| flow_persist_12h | 327 | -0.051 | 0.360 | 0.599 |
| bear_trend_24h_atr | 327 | -0.018 | 0.748 | 0.843 |
| bear_trend_72h_atr | 327 | 0.001 | 0.979 | 0.979 |
| downside_extension_24h_atr | 327 | -0.082 | 0.140 | 0.599 |
| atr_rank_90d | 327 | 0.232 | 0.000 | 0.000 |
| flow_persist_3h | 327 | -0.017 | 0.759 | 0.843 |
| oi_logchg_3h | 326 | 0.062 | 0.267 | 0.599 |
| oi_logchg_12h | 327 | 0.055 | 0.319 | 0.599 |

## Primary 7d cluster bootstrap (BAD − GOOD)
- `downside_extension_72h_atr`: **+1.661**, 95% CI **[-0.053, +3.408]**, clusters=197
- `bear_trend_eff_24h`: **-0.001**, 95% CI **[-0.022, +0.019]**, clusters=197
- `flow_persist_12h`: **+0.016**, 95% CI **[-0.031, +0.065]**, clusters=197

## Fixed yearly/period map

| Period | State | N | Trade EV | EV/original | PF | Ext72 | BearEff24 | FlowPersist12 | ATRrank | OI3h |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | GOOD | 62 | 0.238 | 0.180 | 1.556 | 9.371 | 0.055 | 0.646 | 0.509 | 0.008 |
| 2022 | BAD | 49 | -0.040 | -0.025 | 0.930 | 14.477 | 0.104 | 0.652 | 0.422 | -0.003 |
| 2023 | BAD | 52 | -0.006 | -0.004 | 0.988 | 10.734 | 0.052 | 0.663 | 0.606 | -0.000 |
| 2024 | GOOD | 64 | 0.084 | 0.057 | 1.177 | 10.238 | 0.075 | 0.585 | 0.657 | 0.000 |
| 2025_H1 | BAD | 32 | -0.114 | -0.080 | 0.795 | 12.607 | 0.045 | 0.608 | 0.459 | -0.002 |
| 2025_H2 | GOOD | 33 | 0.117 | 0.088 | 1.248 | 13.985 | 0.059 | 0.609 | 0.596 | -0.000 |
| 2026_JAN_JUL | GOOD | 35 | 0.290 | 0.216 | 1.631 | 11.922 | 0.100 | 0.704 | 0.494 | 0.001 |

## Period-level descriptive correlations (N=7)

| Feature | rho vs EV/original | p |
|---|---:|---:|
| downside_extension_72h_atr | -0.429 | 0.337 |
| bear_trend_eff_24h | 0.321 | 0.482 |
| flow_persist_12h | 0.357 | 0.432 |
| bear_trend_24h_atr | 0.500 | 0.253 |
| bear_trend_72h_atr | -0.679 | 0.094 |
| downside_extension_24h_atr | -0.107 | 0.819 |
| atr_rank_90d | 0.286 | 0.535 |
| flow_persist_3h | 0.643 | 0.119 |
| oi_logchg_3h | 0.893 | 0.007 |
| oi_logchg_12h | 0.571 | 0.180 |

## Gates
- PASS — `exact_frozen_accept25_preaug_trades_327`
- PASS — `frozen_execution_payoff_timestamp_coverage_100pct`
- PASS — `futures_regime_feature_coverage_ge_99pct`
- PASS — `metrics_regime_feature_coverage_ge_95pct`
- PASS — `h1_bad_extension72_gt_good`
- FAIL — `h1_abs_rbc_ge_0_15`
- FAIL — `h1_bh_q_le_0_10`
- PASS — `h1_trade_rho_negative`
- PASS — `h2_bad_bear_eff24_lt_good`
- FAIL — `h2_abs_rbc_ge_0_15`
- FAIL — `h2_bh_q_le_0_10`
- PASS — `h2_trade_rho_positive`
- FAIL — `h3_bad_flowpersist12_lt_good`
- FAIL — `h3_abs_rbc_ge_0_15`
- FAIL — `h3_bh_q_le_0_10`
- FAIL — `h3_trade_rho_positive`
- FAIL — `at_least_2_primary_discrimination_q_le_0_10`
- FAIL — `at_least_1_primary_boot_ci_expected_excludes_zero`
- FAIL — `any_feature_discrimination_bh_q_le_0_10`
- PASS — `any_feature_trade_payoff_bh_q_le_0_10`
- PASS — `recent_periods_not_used_for_threshold_weight_tuning`
- PASS — `august_not_used_for_selection`

## Guardrail
BAD/GOOD labels come from reused LAB044 yearly execution and are descriptive. No cutoff/router/weight was searched. Any apparent failure-state must be independently converted into a preregistered causal router and replicated before use. Live allocation = **0**.
