# BTC_FLOW_LEVEL_CVD_PRESSURE_X_PRICE_RESPONSE_CAUSAL_ROLLING_INTERACTION_REPLICATION_LAB_039

**Verdict: WATCH_ROLLING_INTERACTION_POSITIVE_PROOF_INCOMPLETE — 10/20**

## Causal rolling replication
- frozen HIGH_VOLUME pre-Aug: **568**
- resolved prior-90d thresholds: **414 (72.9%)**
- EFFICIENT_IGNITION: **156**, ABSORPTION: **55**
- ACCEPT rate: **0.609 vs 0.655** (gap -0.046)
- residual: **+0.435 vs +0.306 ATR** (gap +0.129)
- efficient hit: **0.494**; frequency **2.40/month**

## 7d cluster bootstrap
- ACCEPT-rate gap 95% CI **[-0.190, +0.104]**
- residual gap 95% CI **[-1.328, +1.703]**

## Rolling cells

| Cell | N | ACCEPT | Residual | Hit | Pressure | Response | Prior N med |
|---|---:|---:|---:|---:|---:|---:|---:|
| EFFICIENT_IGNITION | 156 | 0.609 | +0.435 | 0.494 | 7.596 | 3.212 | 28.0 |
| ABSORPTION | 55 | 0.655 | +0.306 | 0.491 | 5.027 | 1.121 | 28.0 |
| THIN_LIQUIDITY | 53 | 0.660 | +0.713 | 0.491 | 1.797 | 2.483 | 29.0 |
| WEAK | 150 | 0.687 | -0.195 | 0.487 | 0.101 | 0.528 | 28.0 |
| UNRESOLVED | 154 | 0.623 | +0.650 | 0.519 | 3.806 | 1.980 | 17.0 |

## Efficient-ignition transfer

| Slice | N | ACCEPT | Residual | Hit | L/S |
|---|---:|---:|---:|---:|---:|
| 2021 | 14 | 0.643 | +2.170 | 0.643 | 3/11 |
| 2022 | 20 | 0.550 | -0.245 | 0.550 | 11/9 |
| 2023 | 35 | 0.457 | +1.072 | 0.543 | 16/19 |
| 2024 | 41 | 0.659 | +0.262 | 0.463 | 14/27 |
| 2025_H1 | 15 | 0.667 | -0.749 | 0.400 | 1/14 |
| 2025_H2 | 9 | 0.889 | +1.231 | 0.444 | 3/6 |
| 2026_JAN_JUL | 22 | 0.636 | -0.262 | 0.409 | 12/10 |
| POOLED_RECENT | 31 | 0.710 | +0.172 | 0.419 | 15/16 |
| AUG_REUSED | 1 | 0.000 | -3.173 | 0.000 | 0/1 |
| LONG | 60 | 0.600 | +0.327 | 0.500 | 60/0 |
| SHORT | 96 | 0.615 | +0.503 | 0.490 | 0/96 |
| 2022_SHORT | 9 | 0.444 | +1.114 | 0.556 | 0/9 |

## Gates
- PASS — `frozen_high_volume_ge_500`
- FAIL — `resolved_rolling_thresholds_ge_80pct`
- PASS — `efficient_n_ge_120`
- FAIL — `absorption_n_ge_80`
- FAIL — `efficient_accept_rate_gt_absorption`
- FAIL — `accept_rate_gap_ge_0_03`
- FAIL — `accept_rate_boot_ci_lower_gt_zero`
- PASS — `efficient_residual_gt_absorption`
- FAIL — `residual_gap_ge_0_50`
- FAIL — `residual_boot_ci_lower_gt_zero`
- PASS — `efficient_residual_positive`
- FAIL — `efficient_residual_hit_ge_0_50`
- FAIL — `stress_2022_short_positive_n15`
- PASS — `pooled_recent_positive_n30`
- PASS — `2025h2_positive`
- FAIL — `2026_positive`
- PASS — `long_positive`
- PASS — `short_positive`
- PASS — `efficient_frequency_ge_1_per_month`
- PASS — `august_not_used_for_selection`

## Guardrail
Every interaction threshold is computed from frozen HIGH_VOLUME events in the strictly prior 90 calendar days only; current/future events are excluded and no global fallback is used. No trading execution optimization. August audit-only. Live allocation = **0**.
