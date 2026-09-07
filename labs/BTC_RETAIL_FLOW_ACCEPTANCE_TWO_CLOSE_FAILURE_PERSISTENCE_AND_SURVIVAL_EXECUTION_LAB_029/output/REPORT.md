# BTC_RETAIL_FLOW_ACCEPTANCE_TWO_CLOSE_FAILURE_PERSISTENCE_AND_SURVIVAL_EXECUTION_LAB_029

**Verdict: WATCH_TWO_CLOSE_EXECUTION_POSITIVE_BUT_NOT_TRANSFERABLE — 12/15**

## Frozen lineage
- flow rows: **3209**, pre-Aug ACCEPT: **1496**

## M1 -> M15 parity
- matched ACCEPT events: **646**
- median close relative error: **0.0000000000**
- trigger parity: **100.000%**
- trigger-time parity: **100.000%**

## Pre-Aug policies

| Policy | Trades | EV/trade | Policy EV/orig | Cum ATR | PF | DD | Trigger | Hold h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ORIGIN_CLOSE2 | 1496 | 0.229 | 0.107 | 342.657 | 1.228 | 72.967 | 0.735 | 2.500 |
| HARD_SL15 | 1496 | 0.196 | 0.092 | 293.697 | 1.172 | 67.496 | 0.680 | — |
| TIME_ONLY | 1496 | 0.379 | 0.178 | 567.625 | 1.222 | 139.590 | — | — |
| ORIGIN_CLOSE1 | 1496 | 0.168 | 0.079 | 251.714 | 1.202 | 74.850 | 0.803 | — |

## ORIGIN_CLOSE2 by window

| Window | Trades | EV | Cum | PF | DD | Trigger | L/S |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 322 | 0.350 | 112.629 | 1.372 | 55.557 | 0.727 | 162/160 |
| 2022 | 268 | 0.460 | 123.226 | 1.525 | 43.723 | 0.705 | 136/132 |
| 2023 | 265 | 0.368 | 97.401 | 1.362 | 38.103 | 0.728 | 133/132 |
| 2024 | 253 | 0.096 | 24.330 | 1.095 | 35.159 | 0.747 | 122/131 |
| 2025_H1 | 128 | 0.211 | 27.056 | 1.196 | 33.351 | 0.734 | 68/60 |
| 2025_H2 | 132 | -0.130 | -17.162 | 0.887 | 61.799 | 0.780 | 57/75 |
| 2026_JAN_JUL | 128 | -0.194 | -24.824 | 0.834 | 49.857 | 0.758 | 58/70 |
| AUG2026_REUSED_AUDIT | 5 | -1.057 | -5.285 | 0.068 | 5.285 | 0.800 | 5/0 |
| ALL_PRE_AUG | 1496 | 0.229 | 342.657 | 1.228 | 72.967 | 0.735 | 736/760 |
| POOLED_RECENT | 260 | -0.161 | -41.985 | 0.860 | 67.538 | 0.769 | 115/145 |

## By side

| Side | Trades | EV | Cum | PF | DD |
|---|---:|---:|---:|---:|---:|
| LONG | 736 | 0.378 | 278.382 | 1.363 | 56.619 |
| SHORT | 760 | 0.085 | 64.275 | 1.088 | 103.203 |

## Failure persistence states

| State | N | Time-only EV | Primary EV | MAE | MFE | Win rate |
|---|---:|---:|---:|---:|---:|---:|
| TRIGGER | 1099 | -1.153 | -1.358 | 3.360 | 2.355 | 0.343 |
| NO_TRIGGER | 397 | 4.621 | 4.621 | 0.714 | 5.979 | 0.952 |

## 7d cluster bootstrap vs HARD_SL15
- clusters: **289**, draws **5000**
- EV/trade diff: **0.033 ATR**, 95% CI **[-0.052, 0.117]**
- policy EV/original-signal diff: **0.015 ATR**, 95% CI **[-0.024, 0.055]**

## Gates
- PASS — `exact_lineage_and_accept_n`
- FAIL — `m1_m15_close_parity`
- PASS — `origin_close2_trigger_parity_ge_99pct`
- PASS — `origin_close2_ev_positive`
- PASS — `origin_close2_pf_gt_1_20`
- PASS — `origin_close2_ev_gt_hardsl15`
- PASS — `origin_close2_policy_ev_gt_hardsl15`
- PASS — `origin_close2_dd_le_1_20x_hardsl`
- PASS — `right_tail_retention_ge_55pct`
- PASS — `bootstrap_point_ev_diff_positive`
- FAIL — `bootstrap_noninferiority_ci_lo_ge_minus_0_05`
- PASS — `stress_2022_short_n80_cum_positive_pf_gt_1_25`
- FAIL — `pooled_recent_cum_positive`
- PASS — `long_and_short_ev_positive`
- PASS — `positive_subwindows_ge_5_of_7`

## Guardrail
ORIGIN_CLOSE2 is frozen from LAB028 audit: two consecutive completed M15 closes through original signal price. No rule/threshold/horizon/side rescue. M1 is parity-only. August 2026 reused audit. Live allocation = **0**.
