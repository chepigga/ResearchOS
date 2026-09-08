# BTC_SHORT_HIGH_RESPONSE_ACCEPT25_CAUSAL_ATR90_REGIME_REPLICATION_LAB_047

**Verdict: WATCH_ATR90_REGIME_POSITIVE_PROOF_INCOMPLETE — 15/20**

## Frozen parity
- ACCEPT2.5 pre-Aug trades: **327**; original HIGH_RESPONSE SHORT signals: **475**
- ATR-rank coverage: **100.0%**; August original audit signals: **1**

## Fixed ATR90 split

| State | N | Trade EV | PF | CumR | MaxDD R | DD@0.25% | EV/original | Freq/mo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 327 | +0.086 | 1.176 | +28.22 | 11.44 | 2.86% | +0.059 | 4.98 |
| HIGH_ATR | 187 | +0.098 | 1.209 | +18.26 | 14.61 | 3.65% | +0.038 | 2.85 |
| LOW_ATR | 140 | +0.071 | 1.136 | +9.96 | 8.83 | 2.21% | +0.021 | 2.13 |

## Primary separation
- HIGH_ATR − LOW_ATR trade EV gap: **+0.027R**
- 7d cluster bootstrap 95% CI: **[-0.226, +0.274]**, clusters=197, draws=5000

## Fixed transfer (EV per original HIGH_RESPONSE signal)

| Slice | ALL | HIGH_ATR | LOW_ATR | High N | Low N |
|---|---:|---:|---:|---:|---:|
| 2021 | +0.180 | +0.187 | -0.007 | 33 | 29 |
| 2022 | -0.025 | -0.049 | +0.024 | 17 | 32 |
| 2023 | -0.004 | -0.039 | +0.035 | 35 | 17 |
| 2024 | +0.057 | -0.005 | +0.063 | 48 | 16 |
| 2025_H1 | -0.080 | -0.073 | -0.007 | 15 | 17 |
| 2025_H2 | +0.088 | +0.147 | -0.059 | 22 | 11 |
| 2026_JAN_JUL | +0.216 | +0.159 | +0.058 | 17 | 18 |
| POOLED_RECENT | +0.154 | +0.153 | +0.001 | 39 | 29 |
| AUG_REUSED | — | — | — | 0 | 0 |

## Gates
- PASS — `exact_frozen_accept25_preaug_n327`
- PASS — `atr_rank_coverage_ge99pct`
- PASS — `exact_high_response_original_preaug_n475`
- PASS — `high_atr_n_ge120`
- PASS — `low_atr_n_ge100`
- PASS — `high_atr_trade_ev_positive`
- PASS — `high_atr_pf_ge1_15`
- PASS — `high_atr_ev_gt_low_atr`
- FAIL — `high_low_gap_ge0_15r`
- FAIL — `bootstrap_lower_gt0`
- FAIL — `high_atr_ev_per_original_ge0_055`
- PASS — `high_atr_dd025_le4pct`
- FAIL — `high_atr_2022_not_worse_parent`
- FAIL — `high_atr_2023_not_worse_parent`
- PASS — `high_atr_2025h1_not_worse_parent`
- PASS — `high_atr_2025h2_positive`
- PASS — `high_atr_2026_positive`
- PASS — `high_atr_recent_positive_n30`
- PASS — `low_atr_ev_le_high_atr`
- PASS — `august_not_used_for_selection`

## Guardrail
Fixed 0.50 ATR-rank split only. No alternative percentile, stop, target, entry, or time-exit searched. Reused historical lineage; not fresh OOS. Live allocation = **0**.