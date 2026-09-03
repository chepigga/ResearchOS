# BTC_24H_REVERSAL_ENTRY_DECAY_AND_CAUSAL_LIMIT_RETEST_LAB_005

**Verdict:** **WATCH_LIMIT_RETEST_EXECUTION**

Role: frozen-selector execution decay / causal limit-retest study; not a production strategy.

## Frozen selector

- Parent impulse: completed BTC 60m |return| >= prior 30d 97.5th percentile; 4h cooldown.
- Selector: exact LAB003 BTC-only CORE, DEV-trained logistic CONT/REV router, DEV q80 top bucket.
- This LAB executes only events frozen as top-20% and routed REV.
- DEV CONT tail threshold: **+2.068%**; REV tail threshold: **+1.980%**.
- Frozen router q80: **0.324358**.

## Execution definitions

- MKT_0 = next M15 open after impulse.
- MKT_15 / MKT_30 / MKT_60 = delayed market entries; all use the same common LAB003 exit at parent +24h, isolating entry decay.
- Primary limit = opposite-direction reversal order at event close + impulse_dir × 0.50 × event M15 range; TTL 60m; no market fallback.
- Limit fill uses only subsequent M15 high/low touch; filled price is the preset limit. Secondary 0.25×/1.00× levels are audit only.

## Frozen reversal signal census

- DEV_2021_2024: **122** selected REV events
- BRIDGE_2025: **27** selected REV events
- OOS_2026: **21** selected REV events

## Entry decay / fill results

| Split | Method | Signals | Filled | Fill | Mean REV | 95% CI | Positive | MFE | MAE | Price improvement |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV_2021_2024 | MKT_0 | 122 | 122 | 100.0% | +0.503% | [-0.428%, +1.401%] | 53.3% | +4.591% | +4.434% | — |
| DEV_2021_2024 | MKT_15 | 122 | 122 | 100.0% | +0.530% | [-0.411%, +1.448%] | 57.4% | +4.574% | +4.331% | — |
| DEV_2021_2024 | MKT_30 | 122 | 122 | 100.0% | +0.424% | [-0.478%, +1.302%] | 53.3% | +4.438% | +4.370% | — |
| DEV_2021_2024 | MKT_60 | 122 | 122 | 100.0% | +0.481% | [-0.383%, +1.331%] | 58.2% | +4.416% | +4.217% | — |
| DEV_2021_2024 | LIMIT_R0.50_T60 | 122 | 77 | 63.1% | +0.680% | [-0.447%, +1.789%] | 63.6% | +4.750% | +4.498% | +0.594% |
| DEV_2021_2024 | LIMIT_R0.25_T60_AUDIT | 122 | 92 | 75.4% | +0.404% | [-0.591%, +1.408%] | 60.9% | +4.483% | +4.573% | +0.315% |
| DEV_2021_2024 | LIMIT_R1.00_T60_AUDIT | 122 | 46 | 37.7% | +1.255% | [-0.354%, +2.952%] | 63.0% | +5.483% | +4.807% | +1.103% |
| BRIDGE_2025 | MKT_0 | 27 | 27 | 100.0% | +0.392% | [-0.654%, +1.489%] | 55.6% | +2.622% | +2.329% | — |
| BRIDGE_2025 | MKT_15 | 27 | 27 | 100.0% | +0.334% | [-0.765%, +1.421%] | 55.6% | +2.561% | +2.290% | — |
| BRIDGE_2025 | MKT_30 | 27 | 27 | 100.0% | +0.329% | [-0.796%, +1.485%] | 55.6% | +2.544% | +2.278% | — |
| BRIDGE_2025 | MKT_60 | 27 | 27 | 100.0% | +0.317% | [-0.768%, +1.424%] | 55.6% | +2.489% | +2.277% | — |
| BRIDGE_2025 | LIMIT_R0.50_T60 | 27 | 18 | 66.7% | +0.519% | [-0.605%, +1.598%] | 55.6% | +2.669% | +2.073% | +0.317% |
| BRIDGE_2025 | LIMIT_R0.25_T60_AUDIT | 27 | 20 | 74.1% | +0.326% | [-0.637%, +1.305%] | 55.0% | +2.440% | +2.123% | +0.173% |
| BRIDGE_2025 | LIMIT_R1.00_T60_AUDIT | 27 | 9 | 33.3% | +0.967% | [-1.033%, +3.096%] | 55.6% | +3.076% | +2.140% | +0.714% |
| OOS_2026 | MKT_0 | 21 | 21 | 100.0% | +1.219% | [-0.580%, +3.088%] | 61.9% | +3.878% | +3.236% | — |
| OOS_2026 | MKT_15 | 21 | 21 | 100.0% | +1.494% | [-0.461%, +3.708%] | 57.1% | +4.155% | +2.907% | — |
| OOS_2026 | MKT_30 | 21 | 21 | 100.0% | +1.288% | [-0.701%, +3.391%] | 57.1% | +3.928% | +2.943% | — |
| OOS_2026 | MKT_60 | 21 | 21 | 100.0% | +0.892% | [-1.127%, +2.919%] | 61.9% | +3.527% | +3.117% | — |
| OOS_2026 | LIMIT_R0.50_T60 | 21 | 14 | 66.7% | +1.922% | [-0.791%, +4.688%] | 57.1% | +4.791% | +3.607% | +0.418% |
| OOS_2026 | LIMIT_R0.25_T60_AUDIT | 21 | 16 | 76.2% | +1.907% | [-0.469%, +4.320%] | 62.5% | +4.585% | +3.375% | +0.203% |
| OOS_2026 | LIMIT_R1.00_T60_AUDIT | 21 | 10 | 47.6% | +2.810% | [-0.796%, +6.510%] | 60.0% | +5.732% | +3.058% | +0.844% |

## Primary limit matched comparison

Matched comparison uses only events where the primary limit actually filled, versus MKT_0 on those same events.

| Split | N | Limit mean | MKT_0 matched | Delta | 95% CI |
|---|---:|---:|---:|---:|---:|
| BRIDGE_2025 | 18 | +0.519% | +0.200% | +0.319% | [+0.219%, +0.439%] |
| DEV_2021_2024 | 77 | +0.680% | +0.080% | +0.599% | [+0.515%, +0.694%] |
| OOS_2026 | 14 | +1.922% | +1.485% | +0.437% | [+0.317%, +0.553%] |

## Gates

- PASS — `oos_selected_rev_ge_15`
- PASS — `bridge_selected_rev_ge_15`
- PASS — `entry_decay_bridge`
- FAIL — `entry_decay_oos`
- PASS — `primary_limit_fill_bridge_ge_0.30`
- PASS — `primary_limit_fill_oos_ge_0.30`
- PASS — `primary_limit_matched_delta_bridge_positive`
- PASS — `primary_limit_matched_delta_oos_positive`

**Score 7/8 -> WATCH_LIMIT_RETEST_EXECUTION**

## Interpretation

A positive result means execution timing/price placement improves the already-frozen LAB003 reversal selector. It does not authorize live trading or optimize SL/TP. R:R mapping is a later LAB and must remain >=1:1.5.

No 2026 tuning of selector, limit distance, TTL, delay clocks, or fallback behavior is authorized after this run.