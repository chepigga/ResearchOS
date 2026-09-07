# BTC_RETAIL_FLOW_ADVERSE_EXCURSION_FIRST_PASSAGE_LIMIT_ENTRY_AND_TIME_EXIT_LAB_025

**Verdict: WATCH_ENTRY_PRICE_IMPROVES_BUT_POLICY_NOT_ROBUST — 7/15**

## Frozen parity
- flow lineage: **3209**
- eligible pre-Aug signals: **3196**
- timestamp parity: **100.00%**

## Policy economics by adverse depth

| Sample | Signals | Fills | Fill% | EV/fill | Policy EV/signal | Cum ATR | PF fill | Delay h | Post-fill MAE | Stop rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| IMMEDIATE_NOSTOP_ALL_SIGNALS | 3196 | 3196 | 1.000 | 0.193 | 0.193 | 616.268 | 1.102 | 0.000 | — | — |
| LIMIT_0.5ATR_NOSTOP | 3196 | 2855 | 0.893 | 0.086 | 0.077 | 245.675 | 1.047 | 0.500 | 1.660 | 0.671 |
| LIMIT_0.5ATR_STOP15 | 3196 | 2855 | 0.893 | 0.059 | 0.053 | 168.185 | 1.052 | 0.500 | 1.660 | 0.671 |
| LIMIT_1.0ATR_NOSTOP | 3196 | 2525 | 0.790 | 0.018 | 0.014 | 45.617 | 1.010 | 1.250 | 1.659 | 0.660 |
| LIMIT_1.0ATR_STOP15 | 3196 | 2525 | 0.790 | -0.027 | -0.021 | -67.953 | 0.976 | 1.250 | 1.659 | 0.660 |
| LIMIT_1.5ATR_NOSTOP | 3196 | 2215 | 0.693 | -0.027 | -0.019 | -60.674 | 0.985 | 2.250 | 1.652 | 0.638 |
| LIMIT_1.5ATR_STOP15 | 3196 | 2215 | 0.693 | -0.012 | -0.008 | -25.729 | 0.989 | 2.250 | 1.652 | 0.638 |
| LIMIT_2.0ATR_NOSTOP | 3196 | 1917 | 0.600 | -0.126 | -0.075 | -241.192 | 0.932 | 3.250 | 1.676 | 0.636 |
| LIMIT_2.0ATR_STOP15 | 3196 | 1917 | 0.600 | -0.071 | -0.043 | -137.008 | 0.934 | 3.250 | 1.676 | 0.636 |

## Matched immediate comparison

| Depth | N filled | Limit EV | Immediate EV same signals | Increment |
|---:|---:|---:|---:|---:|
| 0.500 | 2855 | 0.086 | -0.414 | 0.500 |
| 1.000 | 2525 | 0.018 | -0.982 | 1.000 |
| 1.500 | 2215 | -0.027 | -1.527 | 1.500 |
| 2.000 | 1917 | -0.126 | -2.126 | 2.000 |

## Primary 1.0 ATR by window

| Window | Signals | Fills | Fill% | EV/fill | Policy EV/signal | Cum ATR | PF fill | Stop | L/S fills |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 631 | 475 | 0.753 | 0.318 | 0.239 | 151.068 | 1.210 | 0.634 | 231/244 |
| 2022 | 529 | 403 | 0.762 | -0.075 | -0.057 | -30.245 | 0.958 | 0.667 | 214/189 |
| 2023 | 572 | 458 | 0.801 | 0.024 | 0.019 | 10.794 | 1.013 | 0.666 | 213/245 |
| 2024 | 583 | 471 | 0.808 | 0.002 | 0.001 | 0.733 | 1.001 | 0.639 | 218/253 |
| 2025_H1 | 256 | 199 | 0.777 | -0.289 | -0.224 | -57.471 | 0.873 | 0.704 | 98/101 |
| 2025_H2 | 309 | 256 | 0.828 | -0.400 | -0.332 | -102.463 | 0.801 | 0.703 | 124/132 |
| 2026_JAN_JUL | 316 | 263 | 0.832 | 0.278 | 0.232 | 73.200 | 1.161 | 0.650 | 128/135 |
| AUG2026_REUSED_AUDIT | 13 | 12 | 0.923 | -5.444 | -5.025 | -65.330 | 0.000 | 1.000 | 8/4 |
| ALL_PRE_AUG | 3196 | 2525 | 0.790 | 0.018 | 0.014 | 45.617 | 1.010 | 0.660 | 1226/1299 |
| POOLED_RECENT | 625 | 519 | 0.830 | -0.056 | -0.047 | -29.263 | 0.970 | 0.676 | 252/267 |

## Primary 1.0 ATR pre-Aug by side

| Side | Signals | Fills | Fill% | EV/fill | Policy EV/signal | Cum ATR | PF fill |
|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | 1563 | 1226 | 0.784 | -0.143 | -0.112 | -174.711 | 0.927 |
| SHORT | 1633 | 1299 | 0.795 | 0.170 | 0.135 | 220.328 | 1.100 |

## Gates
- PASS — `frozen_flow_lineage_3209_and_timestamp_parity`
- PASS — `pre_aug_eligible_signals_ge_3000`
- PASS — `primary_fill_rate_ge_35pct`
- FAIL — `primary_policy_ev_gt_immediate`
- FAIL — `primary_policy_ev_ge_0_10atr`
- PASS — `matched_limit_improves_by_ge_0_50atr`
- PASS — `primary_nostop_cum_positive`
- FAIL — `primary_bounded_policy_ev_positive`
- FAIL — `primary_bounded_pf_gt_1_20`
- FAIL — `primary_bounded_stop_rate_le_60pct`
- PASS — `stress_2022_short_nfill_ge60_and_nostop_cum_positive`
- PASS — `stress_2022_short_bounded_cum_positive`
- FAIL — `long_and_short_nostop_policy_ev_positive`
- FAIL — `recent_primary_nostop_policy_ev_positive`
- FAIL — `sensitivity_at_least_two_positive`

## Guardrail
Primary depth is frozen at 1.0 ATR. Unfilled orders contribute zero to policy EV. No H4 direction, price-pattern filter, TP, depth optimization, or market fallback is used. August 2026 is reused audit only. Live allocation = **0**.
