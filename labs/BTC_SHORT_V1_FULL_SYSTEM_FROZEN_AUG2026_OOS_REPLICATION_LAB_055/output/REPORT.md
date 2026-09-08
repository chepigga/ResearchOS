# BTC_SHORT_V1_FULL_SYSTEM_FROZEN_AUG2026_OOS_REPLICATION_LAB_055

**Verdict: WATCH_FULL_SYSTEM_PARITY_PASS_AUG_OOS_INSUFFICIENT_N — 20/21**

## Frozen end-to-end parity
- reconstructed pre-Aug HIGH_RESPONSE SHORT: **475** vs frozen **475**
- reconstructed ACCEPT trades: **327** vs frozen **327**
- reconstructed persistent exits: **59** vs frozen **59**
- router/trade/persistent flow-ID parity: **True / True / True**
- max abs 5bps net-R parity error: **8.127e-14**; M15 path coverage **100.0%**

## Full frozen system economics

| Scope | Orig N | Trades | Persistent exits | EV 5bps | PF | CumR | MaxDD R | DD @0.25% | EV/orig | EV 10bps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FULL_PREAUG | 475 | 327 | 59 | +0.101 | 1.228 | +33.170 | 9.79 | 2.45% | +0.070 | +0.040 |
| 2021 | 82 | 62 | 7 | +0.273 | 1.696 | +16.939 | 4.48 | 1.12% | +0.207 | +0.234 |
| 2022 | 79 | 49 | 12 | +0.023 | 1.049 | +1.145 | 9.23 | 2.31% | +0.014 | -0.029 |
| 2023 | 83 | 52 | 8 | -0.023 | 0.952 | -1.212 | 4.71 | 1.18% | -0.015 | -0.106 |
| 2024 | 94 | 64 | 16 | +0.085 | 1.193 | +5.439 | 6.44 | 1.61% | +0.058 | +0.030 |
| 2025_H1 | 46 | 32 | 4 | -0.054 | 0.891 | -1.730 | 7.76 | 1.94% | -0.038 | -0.126 |
| 2025_H2 | 44 | 33 | 4 | +0.201 | 1.519 | +6.632 | 3.12 | 0.78% | +0.151 | +0.117 |
| 2026_JAN_JUL | 47 | 35 | 8 | +0.170 | 1.384 | +5.957 | 4.84 | 1.21% | +0.127 | +0.102 |
| POOLED_RECENT | 91 | 68 | 12 | +0.185 | 1.445 | +12.589 | 4.84 | 1.21% | +0.138 | +0.110 |
| AUG2026 | 1 | 0 | 0 | — | — | +0.000 | — | — | +0.000 | — |

## August 2026 selection-untouched audit
- HIGH_RESPONSE SHORT events: **1**
- ACCEPT trades: **0**
- persistent exits: **0**
- evidence status: **INSUFFICIENT_N**
- August was not used for rule selection, but prior labs exposed it as audit-only; therefore this is not claimed as pristine unseen OOS.

## Gates
- PASS — `preaug_high_response_n_eq475`
- PASS — `preaug_accept_trades_n_eq327`
- PASS — `preaug_persistent_exit_n_eq59`
- PASS — `router_flow_id_parity_100pct`
- PASS — `traded_flow_id_parity_100pct`
- PASS — `persistent_exit_flow_id_parity_100pct`
- PASS — `netr_5bps_max_error_le1e9`
- PASS — `preaug_m15_path_coverage_ge99pct`
- PASS — `full_5bps_ev_positive`
- PASS — `full_pf_gt1_10`
- PASS — `full_cumr_positive`
- PASS — `full_dd_025_le4pct`
- PASS — `full_10bps_ev_positive`
- PASS — `2022_ev_per_original_nonnegative`
- PASS — `2025h2_ev_per_original_positive`
- PASS — `2026_ev_per_original_positive`
- PASS — `recent_pooled_ev_per_original_positive`
- PASS — `august_reported_without_tuning`
- PASS — `august_eligible_path_coverage_100pct`
- FAIL — `august_trades_ge20`
- PASS — `no_september_no_postaug_threshold_change`

## Freeze decision
No parameter is changed from SHORT v1. If August has <20 trades, no live-profitability conclusion is allowed. The next valid step is broker/native or genuinely new-time-period validation, not more reused-sample sequence mining.

## Frozen SHORT v1
`FLOW SHORT → HIGH_RESPONSE → ACCEPT → SL 2.5 ATR → TP 1.5R → max signal+12h → after ADVERSE_FIRST, EXIT NOW on 2 consecutive M15 closes above frozen level before recovery.`
