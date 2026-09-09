# CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001

**Verdict: MIXED_DISCOVERY_EDGE_BUT_PROP_UTILITY_NOT_CLEAN**

> Reused-history discovery/ablation only. Frozen BTC SHORT v1 alpha thresholds were not changed. Router was preregistered before execution.

## Data / clock
- Frozen BTC PERSISTENT_EXIT trades: **327** (parity exact).
- Context source: **Binance USD-M futures public monthly archive**, 2020-01-01 00:00:00+00:00 → 2026-07-31 23:00:00+00:00.
- Router timeframe: **H4**, using only the last fully closed H4 bar (`available_time = H4 open + 4h`).

## Main ablation

| Variant | N | Retain | EV | PF | CumR | DD R | DD @0.25% | Recovery | WR | Loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASELINE | 327 | 100.0% | +0.101R | 1.228 | +33.17R | 9.79R | 2.45% | 3.39 | 44.0% | 8 |
| PRIMARY_PULLBACK_EXPANSION | 291 | 89.0% | +0.104R | 1.232 | +30.24R | 10.21R | 2.55% | 2.96 | 44.0% | 10 |
| STRICT_PRIMARY_PLUS_BEAR | 92 | 28.1% | +0.167R | 1.396 | +15.33R | 6.70R | 1.68% | 2.29 | 45.7% | 9 |
| NEG_CONTROL_REVERSAL_RANGE | 36 | 11.0% | +0.082R | 1.196 | +2.93R | 3.93R | 0.98% | 0.75 | 44.4% | 4 |

## Gates
- PASS — `primary_retention_ge_35pct`
- PASS — `primary_ev_gt_baseline`
- PASS — `primary_pf_gt_baseline`
- FAIL — `primary_recovery_gt_baseline`
- FAIL — `primary_dd_lt_baseline`
- PASS — `primary_ev_gt_negative_control`

## Regime decomposition

| Regime | N | EV | PF | CumR | DD R |
|---|---:|---:|---:|---:|---:|
| EXPANSION | 49 | +0.114R | 1.249 | +5.60R | 4.76R |
| PULLBACK | 242 | +0.102R | 1.229 | +24.64R | 12.04R |
| RANGE | 36 | +0.082R | 1.196 | +2.93R | 3.93R |

## Transfer by period

| Variant | Period | N | EV | PF | CumR | DD R |
|---|---|---:|---:|---:|---:|---:|
| BASELINE | 2021 | 62 | +0.273R | 1.696 | +16.94R | 4.48R |
| BASELINE | 2022 | 49 | +0.023R | 1.049 | +1.15R | 9.23R |
| BASELINE | 2023 | 52 | -0.023R | 0.952 | -1.21R | 4.71R |
| BASELINE | 2024 | 64 | +0.085R | 1.193 | +5.44R | 6.44R |
| BASELINE | 2025_H1 | 32 | -0.054R | 0.891 | -1.73R | 7.76R |
| BASELINE | 2025_H2 | 33 | +0.201R | 1.519 | +6.63R | 3.12R |
| BASELINE | 2026_JAN_JUL | 35 | +0.170R | 1.384 | +5.96R | 4.84R |
| PRIMARY_PULLBACK_EXPANSION | 2021 | 58 | +0.244R | 1.607 | +14.14R | 4.48R |
| PRIMARY_PULLBACK_EXPANSION | 2022 | 45 | -0.014R | 0.972 | -0.63R | 10.21R |
| PRIMARY_PULLBACK_EXPANSION | 2023 | 43 | +0.018R | 1.036 | +0.77R | 3.94R |
| PRIMARY_PULLBACK_EXPANSION | 2024 | 60 | +0.069R | 1.154 | +4.12R | 7.86R |
| PRIMARY_PULLBACK_EXPANSION | 2025_H1 | 25 | +0.008R | 1.016 | +0.19R | 6.19R |
| PRIMARY_PULLBACK_EXPANSION | 2025_H2 | 30 | +0.109R | 1.256 | +3.27R | 3.12R |
| PRIMARY_PULLBACK_EXPANSION | 2026_JAN_JUL | 30 | +0.279R | 1.717 | +8.37R | 3.47R |
| STRICT_PRIMARY_PLUS_BEAR | 2021 | 12 | +0.488R | 2.533 | +5.86R | 1.73R |
| STRICT_PRIMARY_PLUS_BEAR | 2022 | 21 | -0.093R | 0.807 | -1.95R | 6.70R |
| STRICT_PRIMARY_PLUS_BEAR | 2023 | 10 | +0.429R | 2.025 | +4.29R | 1.82R |
| STRICT_PRIMARY_PLUS_BEAR | 2024 | 11 | +0.317R | 1.862 | +3.48R | 1.76R |
| STRICT_PRIMARY_PLUS_BEAR | 2025_H1 | 10 | -0.069R | 0.867 | -0.69R | 2.56R |
| STRICT_PRIMARY_PLUS_BEAR | 2025_H2 | 15 | +0.051R | 1.114 | +0.77R | 1.78R |
| STRICT_PRIMARY_PLUS_BEAR | 2026_JAN_JUL | 13 | +0.275R | 1.766 | +3.57R | 2.33R |
| NEG_CONTROL_REVERSAL_RANGE | 2021 | 4 | +0.699R | 3.722 | +2.80R | 1.03R |
| NEG_CONTROL_REVERSAL_RANGE | 2022 | 4 | +0.444R | 2.577 | +1.78R | 0.67R |
| NEG_CONTROL_REVERSAL_RANGE | 2023 | 9 | -0.220R | 0.473 | -1.98R | 2.06R |
| NEG_CONTROL_REVERSAL_RANGE | 2024 | 4 | +0.330R | 1.865 | +1.32R | 1.53R |
| NEG_CONTROL_REVERSAL_RANGE | 2025_H1 | 7 | -0.275R | 0.472 | -1.92R | 2.78R |
| NEG_CONTROL_REVERSAL_RANGE | 2025_H2 | 3 | +1.121R | inf | +3.36R | 0.00R |
| NEG_CONTROL_REVERSAL_RANGE | 2026_JAN_JUL | 5 | -0.483R | 0.372 | -2.42R | 3.85R |

## XAU status
- **BLOCKED_NATIVE_XAU_DATA_NOT_IN_REPO**
- No GC/Yahoo surrogate was substituted.

## Decision
If PRIMARY passes all preregistered gates, freeze the router specification and test it only on fresh/native broker data. If it fails, do not tune weights on this same history; inspect decomposition only to form a new separately preregistered hypothesis.
