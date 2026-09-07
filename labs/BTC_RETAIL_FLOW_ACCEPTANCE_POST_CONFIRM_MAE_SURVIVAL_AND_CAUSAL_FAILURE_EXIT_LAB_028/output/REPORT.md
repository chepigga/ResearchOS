# BTC_RETAIL_FLOW_ACCEPTANCE_POST_CONFIRM_MAE_SURVIVAL_AND_CAUSAL_FAILURE_EXIT_LAB_028

**Verdict: WATCH_FAILURE_STATE_DISCRIMINATIVE_EXECUTION_NOT_ROBUST — 9/14**

## Frozen parity
- flow lineage: **3209**, pre-Aug ACCEPT: **1496**
- timestamp parity: **100.00%**

## Post-acceptance survival map

| Group | N | Frozen residual | Median MAE | MAE>=.5 | >=1 | >=1.5 | >=2 | Fav+.5 | +1 | +1.5 | tMAE h | tMFE h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 1496 | 0.527 | 2.490 | 0.970 | 0.773 | 0.680 | 0.585 | 0.922 | 0.818 | 0.741 | 4.500 | 5.000 |
| WINNER | 772 | 4.199 | 1.246 | 0.943 | 0.571 | 0.433 | 0.312 | 1.000 | 0.990 | 0.965 | 1.250 | 8.250 |
| LOSER | 724 | -3.388 | 4.219 | 0.999 | 0.988 | 0.945 | 0.876 | 0.838 | 0.635 | 0.501 | 8.750 | 1.500 |

## Failure-state discrimination

| Group | N | Frozen residual | Time-only net | MAE | Win rate |
|---|---:|---:|---:|---:|---:|
| ORIGIN_CLOSE1_TRIGGER | 1201 | -0.625 | -0.774 | 3.128 | 0.403 |
| NO_ORIGIN_CLOSE1 | 295 | 5.215 | 5.075 | 0.623 | 0.976 |
| WICK_ONLY_NO_CLOSE | 253 | 5.370 | 5.228 | 0.662 | 0.976 |
| NO_WICK_NO_CLOSE | 42 | 4.279 | 4.157 | 0.390 | 0.976 |

## Execution policies pre-Aug

| Policy | Accept trades | EV/trade | Policy EV/orig signal | Cum ATR | PF | DD | Trigger |
|---|---:|---:|---:|---:|---:|---:|---:|
| ORIGIN_CLOSE1 | 1496 | 0.168 | 0.079 | 251.714 | 1.202 | 74.850 | 0.803 |
| AUDIT_ORIGIN_CLOSE2 | 1496 | 0.229 | 0.107 | 342.657 | 1.228 | 72.967 | 0.735 |
| AUDIT_ENTRY_CLOSE2 | 1496 | 0.184 | 0.086 | 275.004 | 1.260 | 71.438 | 0.838 |
| TIME_ONLY | 1496 | 0.379 | 0.178 | 567.625 | 1.222 | 139.590 | — |
| HARD_SL15 | 1496 | 0.196 | 0.092 | 293.697 | 1.172 | 67.496 | 0.680 |

## Primary ORIGIN_CLOSE1 by window

| Window | Trades | EV | Cum | PF | DD | Trigger | L/S |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 322 | 0.259 | 83.470 | 1.338 | 42.991 | 0.798 | 162/160 |
| 2022 | 268 | 0.388 | 104.072 | 1.518 | 32.553 | 0.780 | 136/132 |
| 2023 | 265 | 0.266 | 70.458 | 1.306 | 37.747 | 0.796 | 133/132 |
| 2024 | 253 | 0.021 | 5.389 | 1.025 | 37.202 | 0.814 | 122/131 |
| 2025_H1 | 128 | 0.027 | 3.507 | 1.028 | 37.648 | 0.820 | 68/60 |
| 2025_H2 | 132 | 0.026 | 3.480 | 1.029 | 43.172 | 0.818 | 57/75 |
| 2026_JAN_JUL | 128 | -0.146 | -18.661 | 0.835 | 38.125 | 0.820 | 58/70 |
| AUG2026_REUSED_AUDIT | 5 | -0.952 | -4.761 | 0.075 | 4.761 | 0.800 | 5/0 |
| ALL_PRE_AUG | 1496 | 0.168 | 251.714 | 1.202 | 74.850 | 0.803 | 736/760 |
| POOLED_RECENT | 260 | -0.058 | -15.181 | 0.935 | 51.352 | 0.819 | 115/145 |

## Primary by side

| Side | Trades | EV | Cum | PF | DD |
|---|---:|---:|---:|---:|---:|
| LONG | 736 | 0.307 | 225.833 | 1.360 | 39.240 |
| SHORT | 760 | 0.034 | 25.881 | 1.042 | 76.881 |

## 7d cluster bootstrap
- clusters: **289**, draws: **5000**
- ORIGIN_CLOSE1 minus HARD_SL15 EV/trade: **-0.028 ATR**, 95% CI **[-0.120, 0.063]**

## Gates
- PASS — `exact_lab026_lineage_and_accept_n_ge_1400`
- PASS — `origin_close1_trigger_rate_20_to_85pct`
- PASS — `triggered_failure_residual_gap_ge_0_50atr`
- PASS — `wick_only_no_close_n_ge_100`
- PASS — `wick_only_residual_gt_close_failure`
- PASS — `origin_close1_ev_positive`
- PASS — `origin_close1_pf_gt_1_20`
- FAIL — `origin_close1_ev_gt_hard_sl15`
- FAIL — `origin_close1_dd_le_hard_sl15`
- FAIL — `bootstrap_origin_minus_hard_ci_lower_gt_zero`
- PASS — `stress_2022_short_n80_and_cum_positive`
- FAIL — `pooled_recent_cum_positive`
- PASS — `long_and_short_ev_positive`
- FAIL — `beats_time_dd_and_retains_70pct_cum`

## Guardrail
MAE bands are descriptive only and cannot become stops. Primary failure rule is frozen ORIGIN_CLOSE1: first completed M15 close back through original signal price. No threshold/stop/horizon optimization. August 2026 reused audit only. Live allocation = **0**.
