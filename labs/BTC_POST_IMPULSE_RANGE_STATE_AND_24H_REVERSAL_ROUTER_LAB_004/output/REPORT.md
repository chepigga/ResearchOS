# BTC_POST_IMPULSE_RANGE_STATE_AND_24H_REVERSAL_ROUTER_LAB_004

**Verdict:** **FAIL_NO_TRANSFERABLE_POST_IMPULSE_MECHANISM**

Role: leakage-safe post-impulse BTC reversal-router study; not a production strategy.

## Primary causal clock

- Parent impulse: frozen 60m |return| >= prior 30d 97.5th percentile, 4h cooldown.
- Observe exactly **+30m** (2 completed M15 bars) after impulse, then enter at next M15 open.
- Direction: opposite parent impulse. Outcome: 24h from delayed entry.
- DEV-only REV-tail threshold: **+1.938%**.

## Event census

- BRIDGE_2025: **301** events
- DEV_2021_2024: **1,155** events
- OOS_2026: **174** events

## CORE reproduction at delayed clock

| Split | AUC | Brier | N top | Tail hit | Mean reversal 24h | 95% CI |
|---|---:|---:|---:|---:|---:|---:|
| DEV_2021_2024 | 0.6070 | 0.1826 | 231 | 33.8% | +0.459% | [-0.224%, +1.148%] |
| BRIDGE_2025 | 0.4827 | 0.1687 | 78 | 19.2% | +0.442% | [-0.134%, +1.040%] |
| OOS_2026 | 0.5626 | 0.1623 | 56 | 23.2% | -0.264% | [-1.194%, +0.768%] |

## Post-impulse family transfer (+30m primary)

| Family | Bridge AUC Δ | OOS AUC Δ | Bridge return Δ | OOS return Δ | OOS Brier imp | OOS hit Δ | Transfer |
|---|---:|---:|---:|---:|---:|---:|---|
| RANGE_STATE | +0.0041 | -0.0122 | +0.021% | -0.308% | -0.00324 | +1.3 pp | NO |
| EXHAUSTION | +0.0003 | -0.0187 | +0.192% | -0.162% | -0.00117 | -0.3 pp | NO |
| ACCEPTANCE | -0.0057 | +0.0269 | +0.188% | +0.472% | +0.00497 | +6.0 pp | NO |
| RECOVERY_SEQUENCE | +0.0016 | -0.0084 | +0.119% | +0.062% | -0.00030 | +0.9 pp | NO |
| VOLUME_RESPONSE | -0.0138 | -0.0147 | -0.123% | -0.411% | -0.00109 | +1.3 pp | NO |

## Secondary clock audit (CORE only)

| Clock | Split | AUC | N top | Tail hit | Mean reversal |
|---|---|---:|---:|---:|---:|
| D15 | BRIDGE_2025 | 0.5004 | 71 | 23.9% | +0.611% |
| D15 | OOS_2026 | 0.5550 | 48 | 22.9% | +0.147% |
| D30 | BRIDGE_2025 | 0.4827 | 78 | 19.2% | +0.442% |
| D30 | OOS_2026 | 0.5626 | 56 | 23.2% | -0.264% |
| D60 | BRIDGE_2025 | 0.4943 | 79 | 21.5% | +0.174% |
| D60 | OOS_2026 | 0.5313 | 61 | 21.3% | -0.600% |

## Gates

- PASS — `oos_events_ge_100`
- PASS — `core_oos_auc_ge_0.55`
- FAIL — `core_oos_top_return_positive`
- FAIL — `named_transferable_family_found`

**Score 2/4 -> FAIL_NO_TRANSFERABLE_POST_IMPULSE_MECHANISM**

Transferable named families: **none**.

## Interpretation

A family is promoted only when its incremental contribution over the frozen event-time CORE has the same positive sign in bridge 2025 and OOS 2026 and improves OOS Brier. +15m/+60m are audit clocks only and cannot rescue a failed +30m primary result. No 2026 threshold or family tuning is authorized after this run.