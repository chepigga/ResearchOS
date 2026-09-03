# BTC_24H_RIGHT_TAIL_BTC_ONLY_CAUSAL_DECOMPOSITION_LAB_003

**Verdict:** **PASS_TRANSFERABLE_BTC_COMPONENT_FOUND**

Role: leakage-safe predictive decomposition of the frozen BTC-only 24h right-tail router; not a live strategy and not proof of structural causality.

## Data / clock

- Binance Spot BTCUSDT, completed 15m bars: `2021-01-01 00:00:00+00:00` -> `2026-07-31 23:45:00+00:00`.
- Bars: **195,578**.
- Events: DEV **1,155**, bridge **301**, OOS **174**.
- Frozen 24h tail thresholds from DEV only: continuation **+2.068%**, reversal **+1.980%**, absolute **+3.758%**.
- Entry/outcome starts at next 15m open. No post-decision feature is used.

## CORE reproduction

| Split | N top | Tail hit | Mean chosen 24h | 95% CI | CONT share |
|---|---:|---:|---:|---:|---:|
| DEV_2021_2024 | 231 | 37.7% | +0.693% | [+0.083%, +1.293%] | 47.2% |
| BRIDGE_2025 | 55 | 20.0% | -0.098% | [-0.777%, +0.578%] | 50.9% |
| OOS_2026 | 24 | 37.5% | +0.966% | [-0.652%, +2.754%] | 12.5% |

## Core feature DROP decomposition

| Feature | Bridge AUC Δ | OOS AUC Δ | Bridge return Δ | OOS return Δ | OOS hit Δ | Transfer |
|---|---:|---:|---:|---:|---:|---|
| btc_corr7d_lag | +0.0078 | -0.0263 | -0.046% | +0.947% | +9.4 pp | NO |
| btc_z4h | -0.0057 | +0.0008 | -0.128% | +0.487% | -6.0 pp | NO |
| btc_vol_z | -0.0016 | -0.0049 | -0.249% | +0.339% | +12.5 pp | NO |
| hour_cos | -0.0003 | -0.0068 | +0.197% | +0.328% | +5.5 pp | NO |
| btc_z24h | +0.0066 | +0.0148 | +0.256% | +0.288% | -0.6 pp | NO |
| btc_range_z | +0.0013 | +0.0010 | +0.036% | +0.234% | +5.4 pp | ROBUST |
| impulse_dir | -0.0005 | +0.0004 | +0.045% | +0.000% | +0.0 pp | NO |
| hour_sin | -0.0011 | +0.0090 | +0.170% | -0.023% | +10.2 pp | NO |
| btc_z60 | +0.0034 | -0.0023 | +0.167% | -0.034% | -1.6 pp | NO |
| btc_z15 | +0.0071 | -0.0261 | -0.113% | -0.183% | -2.5 pp | NO |

Positive DROP contribution means the CORE got worse when that feature was removed.

## Frozen CORE_PLUS family tests

| Family | Bridge AUC Δ | OOS AUC Δ | Bridge return Δ | OOS return Δ | OOS hit Δ | Transfer |
|---|---:|---:|---:|---:|---:|---|
| CALENDAR | +0.0264 | +0.0300 | +0.218% | +0.275% | -3.0 pp | NO |
| IMPULSE_PATH | +0.0037 | -0.0114 | +0.323% | -0.119% | -8.3 pp | NO |
| BREAK_ACCEPTANCE | +0.0103 | -0.0027 | +0.275% | -0.234% | -2.9 pp | NO |
| TREND_REGIME | -0.0238 | -0.0280 | -0.108% | -1.052% | -10.8 pp | NO |
| PRE_STATE | -0.0077 | -0.0306 | -0.405% | -1.186% | -13.5 pp | NO |
| VOL_REGIME | +0.0032 | -0.0093 | -0.018% | -1.311% | -11.7 pp | NO |

## Stable components

- **btc_range_z** (CORE_FEATURE)

## Gates

- PASS — `oos_events_ge_100`
- PASS — `core_oos_top_return_positive`
- PASS — `core_oos_tail_hit_ge_0.30`
- PASS — `core_bridge_not_catastrophic`
- PASS — `robust_core_feature_found`
- FAIL — `robust_add_family_found`

## Interpretation

This LAB does not tune 2026. A robust component must improve bridge and OOS with the same sign. If the CORE reproduces but no component transfers, the correct conclusion is that the top-bucket effect is distributed/interaction-driven or unstable, not permission to optimize thresholds on OOS.