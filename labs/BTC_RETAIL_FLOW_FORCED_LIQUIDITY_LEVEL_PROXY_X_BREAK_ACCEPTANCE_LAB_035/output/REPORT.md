# BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035

**Verdict: WATCH_LEVEL_ACCEPTANCE_DIRECTIONALLY_USEFUL_TRANSFER_INCOMPLETE — 11/13**

## Core
- frozen flow: **3209**, classified pre-Aug: **3196**
- baseline full 12h mean: **0.347 ATR**
- TOUCH: **1980**, ACCEPT: **1365**, REJECT: **604**
- ACCEPT full mean: **2.698 ATR**
- ACCEPT residual after break: **0.353 ATR**
- REJECT residual after classification: **0.189 ATR**
- ACCEPT-REJECT residual gap: **0.164 ATR**, 7d bootstrap 95% CI **[-0.317, 0.654]**

## Distance map

| Distance | N | Touch | Accept | Full mean | Accept N | Accept residual |
|---|---:|---:|---:|---:|---:|---:|
| <=0.5 | 399 | 0.985 | 0.777 | 0.162 | 310 | 0.241 |
| 0.5-1 | 356 | 0.857 | 0.517 | 0.230 | 184 | 0.164 |
| 1-2 | 822 | 0.730 | 0.490 | 0.374 | 403 | 0.335 |
| >2 | 1619 | 0.421 | 0.289 | 0.405 | 468 | 0.516 |

## ACCEPT by window

| Window | N | Full mean | Residual | Hit residual | L/S |
|---|---:|---:|---:|---:|---:|
| 2021 | 258 | 3.201 | 0.730 | 0.488 | 134/124 |
| 2022 | 232 | 2.966 | 0.382 | 0.474 | 119/113 |
| 2023 | 206 | 3.176 | 0.467 | 0.427 | 107/99 |
| 2024 | 265 | 2.168 | 0.131 | 0.479 | 142/123 |
| 2025_H1 | 125 | 2.527 | 0.412 | 0.504 | 66/59 |
| 2025_H2 | 132 | 2.470 | 0.245 | 0.492 | 66/66 |
| 2026_JAN_JUL | 147 | 2.032 | -0.068 | 0.442 | 66/81 |
| AUG_REUSED | 2 | -2.150 | -3.066 | 0.000 | 2/0 |
| ALL_PRE_AUG | 1365 | 2.698 | 0.353 | 0.472 | 700/665 |
| POOLED_RECENT | 279 | 2.239 | 0.080 | 0.466 | 132/147 |

## OI interaction

| Slice | N | Full mean | Residual |
|---|---:|---:|---:|
| OI_BACKED | 747 | 2.775 | 0.463 |
| NO_OI_BACKING | 618 | 2.606 | 0.220 |
| OI_FLUSH | 658 | 2.367 | -0.122 |
| NO_OI_FLUSH | 702 | 3.019 | 0.805 |

## Direct liquidation archive audit
- files attempted: **120**, available: **0**, event windows parsed: **0**
- matched forced-side share: **—**
This audit is validation-only because Binance USD-M liquidationSnapshot coverage was discontinued/removed.

## Gates
- PASS — `frozen_flow_lineage_n_ge_3200`
- PASS — `futures_coverage_ge_99pct`
- PASS — `oi_metrics_coverage_ge_90pct`
- PASS — `touch_n_ge_500`
- PASS — `accept_n_ge_200`
- PASS — `accept_residual_positive`
- FAIL — `accept_minus_reject_residual_ge_0_20`
- FAIL — `cluster_boot_ci_lower_gt_zero`
- PASS — `accept_full_mean_beats_baseline_0_15`
- PASS — `oi_backed_accept_beats_no_oi_0_15`
- PASS — `stress_2022_short_accept_resid_positive_n30`
- PASS — `recent_accept_resid_positive_n50`
- PASS — `near_touch_rate_gt_far`

## Guardrail
The level is a frozen 12h directional extreme with OI backing only as an interaction label. It is not claimed to be the true liquidation price. No level/lookback/acceptance/stop/TP optimization was performed. August 2026 is reused audit only. Live allocation = **0**.
