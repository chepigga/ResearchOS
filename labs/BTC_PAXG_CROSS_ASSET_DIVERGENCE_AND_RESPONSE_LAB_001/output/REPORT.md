# BTC_PAXG_CROSS_ASSET_DIVERGENCE_AND_RESPONSE_LAB_001

**Frozen:** 2026-09-03  
**Verdict:** **WATCH_WEAK_INCREMENTAL_CONTEXT**  
**Role:** causal cross-asset context study; not a production entry strategy.

## 1. Data / causality

- Binance Spot `BTCUSDT` + `PAXGUSDT`, 15m completed klines.
- Synchronized coverage: `2021-01-01 00:00:00+00:00` → `2026-07-31 23:45:00+00:00`.
- Synchronized bars: **195,578**.
- Impulse: completed BTC 60m |return| >= prior 30d 97.5th percentile.
- Cooldown: **4h**.
- Entry reference/outcomes begin at the next 15m open; PAXG is never forward-filled.
- Development 2021–2024; bridge 2025; untouched OOS 2026.

## 2. Event census

- BRIDGE_2025: **301** events
- DEV_2021_2024: **1,155** events
- OOS_2026: **176** events

## 3. Primary 4h conditional response

### DEV_2021_2024

| PAXG state | N | continuation WR | mean signed 4h | 95% CI |
|---|---:|---:|---:|---:|
| ALL | 1155 | 47.7% | -0.023% | [-0.147%, +0.088%] |
| INVERSE | 160 | 40.0% | -0.264% | [-0.617%, +0.122%] |
| NEUTRAL | 347 | 47.3% | -0.067% | [-0.282%, +0.169%] |
| ALIGNED | 648 | 49.8% | +0.060% | [-0.085%, +0.203%] |

### BRIDGE_2025

| PAXG state | N | continuation WR | mean signed 4h | 95% CI |
|---|---:|---:|---:|---:|
| ALL | 301 | 53.2% | +0.117% | [-0.059%, +0.290%] |
| INVERSE | 62 | 48.4% | +0.075% | [-0.332%, +0.484%] |
| NEUTRAL | 114 | 55.3% | +0.161% | [-0.079%, +0.395%] |
| ALIGNED | 125 | 53.6% | +0.098% | [-0.148%, +0.363%] |

### OOS_2026

| PAXG state | N | continuation WR | mean signed 4h | 95% CI |
|---|---:|---:|---:|---:|
| ALL | 176 | 44.3% | -0.087% | [-0.311%, +0.130%] |
| INVERSE | 21 | 47.6% | +0.018% | [-0.553%, +0.708%] |
| NEUTRAL | 51 | 47.1% | -0.091% | [-0.414%, +0.259%] |
| ALIGNED | 104 | 42.3% | -0.106% | [-0.390%, +0.207%] |

## 4. Incremental model — BTC-only vs BTC+PAXG

| Split | Model | N | AUC | Brier | LogLoss |
|---|---|---:|---:|---:|---:|
| DEV_2021_2024 | BTC_ONLY | 1155 | 0.5572 | 0.2470 | 0.6870 |
| DEV_2021_2024 | BTC_PLUS_PAXG | 1155 | 0.5878 | 0.2439 | 0.6807 |
| BRIDGE_2025 | BTC_ONLY | 301 | 0.4782 | 0.2577 | 0.7088 |
| BRIDGE_2025 | BTC_PLUS_PAXG | 301 | 0.5030 | 0.2596 | 0.7151 |
| OOS_2026 | BTC_ONLY | 176 | 0.4792 | 0.2519 | 0.6973 |
| OOS_2026 | BTC_PLUS_PAXG | 176 | 0.4945 | 0.2535 | 0.7005 |

- 2025 AUC delta from PAXG: **+0.0037**.
- 2026 AUC delta from PAXG: **+0.0085**.
- 2026 Brier improvement: **-0.00792**.
- 2026 baseline continuation WR: **44.3%**.
- Frozen augmented top-20%: N **33**, WR **51.5%**, lift **+7.2 pp**, mean signed 4h **+0.133%**.

## 5. Promotion gates

- PASS — `oos_events_ge_100`
- FAIL — `paxg_auc_delta_2026_ge_0.02`
- PASS — `paxg_auc_delta_bridge_positive`
- FAIL — `oos_brier_improves`
- PASS — `oos_top20_lift_ge_0.05`
- PASS — `oos_top20_mean_positive`
- FAIL — `mechanism_transfer_same_sign`

**Score: 4/7 → WATCH_WEAK_INCREMENTAL_CONTEXT**

## 6. Interpretation

PAXG can only be promoted as a **router/context feature**, never as a standalone BTC signal. A positive result means BTC impulse outcomes become more separable when PAXG state is known; it does not authorize a trade, stop, or target.

If WATCH/FAIL, do not rescue the result by tuning EMA periods, PAXG thresholds, impulse percentile, or horizon on 2026. A new mechanism requires a separately preregistered LAB.