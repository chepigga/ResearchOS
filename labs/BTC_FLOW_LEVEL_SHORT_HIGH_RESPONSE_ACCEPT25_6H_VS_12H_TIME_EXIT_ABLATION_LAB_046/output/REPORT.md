# BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ACCEPT25_6H_VS_12H_TIME_EXIT_ABLATION_LAB_046

**Verdict: WATCH_ACCEPT25_ENTRY6H_POSITIVE_BUT_DEGRADES — 11/14**

## Fixed ACCEPT2.5 time-exit ablation

| Policy | Trades | TP | SL | Time | Late | EV 0bps | EV 5bps | EV 10bps | PF | EV/original | CumR | MaxDD R | DD@0.25% | Median hold h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ENTRY_PLUS_6H | 331 | 0.341 | 0.408 | 0.251 | 0 | +0.116 | +0.054 | -0.008 | 1.110 | +0.037 | +17.79 | 15.03 | 3.76% | 3.00 |
| SIGNAL_PLUS_6H | 257 | 0.268 | 0.296 | 0.436 | 74 | +0.110 | +0.051 | -0.008 | 1.123 | +0.028 | +13.10 | 8.78 | 2.19% | 2.25 |
| SIGNAL_PLUS_12H | 327 | 0.367 | 0.419 | 0.214 | 4 | +0.148 | +0.086 | +0.024 | 1.176 | +0.059 | +28.22 | 11.44 | 2.86% | 2.75 |

## Paired diagnostic
- ENTRY_PLUS_6H minus SIGNAL_PLUS_12H EV/original: **-0.022R**, 7d cluster bootstrap 95% CI **[-0.056, +0.012]**, clusters=236

## Transfer (EV/original)

| Slice | ENTRY+6h | SIGNAL+6h | SIGNAL+12h |
|---|---:|---:|---:|
| 2021 | +0.124 | +0.163 | +0.180 |
| 2022 | -0.068 | -0.022 | -0.025 |
| 2023 | -0.030 | -0.003 | -0.004 |
| 2024 | +0.077 | +0.036 | +0.057 |
| 2025_H1 | -0.092 | -0.035 | -0.080 |
| 2025_H2 | +0.128 | +0.082 | +0.088 |
| 2026_JAN_JUL | +0.146 | -0.077 | +0.216 |
| POOLED_RECENT | +0.137 | -0.000 | +0.154 |
| AUG_REUSED | +0.000 | +0.000 | +0.000 |

## Gates
- FAIL — `parent_formal_n475_accept327`
- PASS — `signal12_parent_trade_ev_parity`
- PASS — `m15_path_coverage_ge_99pct`
- PASS — `entry6_net_ev_positive`
- PASS — `entry6_pf_ge_1_10`
- FAIL — `entry6_ev_per_original_ge_0_05`
- FAIL — `entry6_10bps_ev_positive`
- PASS — `entry6_dd_025_le_4pct`
- PASS — `entry6_2025h2_positive`
- PASS — `entry6_2026_positive`
- PASS — `entry6_pooled_recent_positive_n50`
- PASS — `entry6_not_worse_12h_by_0_05`
- PASS — `entry6_pf_not_worse_12h_by_0_10`
- PASS — `august_not_used_for_selection`

## Guardrail
Only time exit changed. Frozen HIGH_RESPONSE -> ACCEPT, SL 2.5 ATR, TP 1.5R, M15 path ordering and costs retained. Reused historical lineage; not fresh OOS. Live allocation = **0**.
