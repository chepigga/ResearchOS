# BTC_SHORT_V1_FROZEN_FULL_SYSTEM_END_TO_END_VALIDATION_LAB_055

**Verdict: FAIL_FROZEN_SYSTEM_VALIDATION — 14/16 gates**

## Frozen end-to-end lineage
- HIGH_RESPONSE SHORT signals: **475**
- ACCEPT trades: **327**
- ADVERSE_FIRST: **145**
- PERSISTENT_FAILURE: **59**
- final trades: **327**, EXIT_NOW early exits **59**

## Full frozen economics
- EV 5bps **+0.101R**, PF **1.228**, CumR **+33.17R**, WR **44.0%**
- MaxDD **9.79R** = **2.45%** at 0.25% risk; **4.90%** at 0.50% risk
- 10bps EV **+0.040R**, PF **1.082**
- max consecutive losses **8**

## 7-day cluster bootstrap
- EV 95% CI **[-0.014, +0.214]R**
- total-R 95% interval **[-4.7, +70.1]R**
- resampled maxDD p50 **12.13R**, p95 **22.68R**, p99 **29.47R**
- p95 DD at 0.25% risk **5.67%**; at 0.50% risk **11.34%**

## Transfer

| Period | Orig N | Trades | EV | PF | CumR | DD R | EV/orig | Loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 82 | 62 | +0.273 | 1.696 | +16.94 | 4.48 | +0.207 | 4 |
| 2022 | 79 | 49 | +0.023 | 1.049 | +1.15 | 9.23 | +0.014 | 6 |
| 2023 | 83 | 52 | -0.023 | 0.952 | -1.21 | 4.71 | -0.015 | 4 |
| 2024 | 94 | 64 | +0.085 | 1.193 | +5.44 | 6.44 | +0.058 | 8 |
| 2025_H1 | 46 | 32 | -0.054 | 0.891 | -1.73 | 7.76 | -0.038 | 4 |
| 2025_H2 | 44 | 33 | +0.201 | 1.519 | +6.63 | 3.12 | +0.151 | 2 |
| 2026_JAN_JUL | 47 | 35 | +0.170 | 1.384 | +5.96 | 4.84 | +0.127 | 3 |

Active profitable-month share **58.5%**; worst quarter **2022Q3** CumR **-4.90R**.
Pooled 2025H2+2026 EV/original **+0.138R**.

## Untouched August 2026 audit
- HIGH_RESPONSE SHORT signals **1**; ACCEPT/executable **0**; router residual **-3.173 ATR**.
- This is **insufficient fresh OOS sample** and cannot validate or invalidate the system. No August result was used to alter the specification.

## Gates
- PASS — `exact_original_high_response_475`
- PASS — `exact_accept_trades_327`
- PASS — `exact_adverse_first_145`
- PASS — `exact_persistent_failure_59`
- PASS — `exact_final_trades_327`
- PASS — `exact_early_exits_59`
- PASS — `ev_5bps_positive`
- PASS — `pf_5bps_gt_1_10`
- PASS — `cumr_positive`
- PASS — `ev_10bps_positive`
- PASS — `historical_dd_025_lt4pct`
- FAIL — `bootstrap_ev_lower_gt0`
- FAIL — `cluster_p95_dd_025_lt5pct`
- PASS — `recent_ev_per_original_positive`
- PASS — `max_loss_streak_le10`
- PASS — `august_not_used_for_selection`

## Decision
SHORT v1 is frozen after this audit. No further reused-history tuning is authorized. Next evidence must come from fresh/native broker execution or a genuinely untouched future sample. Live allocation remains **0** until that replication.
