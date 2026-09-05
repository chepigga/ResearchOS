# BTC_REVERSAL_H4_TWO_BAR_DIRECTIONAL_ASYMMETRY_AND_BUY_ONLY_CAUSAL_REPLICATION_LAB_019

**Verdict: PASS_RECENT_BUY_DOMINANCE_REUSED — 15/19**

Frozen primary candidate: H4 `TWO_BAR_CONFIRM_12H + VF1`, real orders BUY-only (`impulse_dir < 0`); all directions remain active as shadow/virtual state.

## Directional windows

| Window | Side | Fills | Fills/mo | Cum R | Mean R | PF | DD R | LOEO worst |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | BUY | 1 | 0.08 | +1.48 | +1.477 | inf | 0.00 | +0.00 |
| 2021 | SELL | 10 | 0.83 | -1.26 | -0.126 | 0.815 | 4.17 | -2.65 |
| 2022 | BUY | 6 | 0.50 | +0.51 | +0.085 | 1.147 | 3.47 | -0.83 |
| 2022 | SELL | 7 | 0.58 | -0.80 | -0.115 | 0.834 | 3.59 | -2.21 |
| 2023 | BUY | 7 | 0.58 | -6.40 | -0.914 | 0.169 | 6.40 | -6.51 |
| 2023 | SELL | 1 | 0.08 | -1.30 | -1.305 | 0.000 | 1.30 | +0.00 |
| 2024 | BUY | 2 | 0.17 | -2.39 | -1.197 | 0.000 | 2.39 | +0.00 |
| 2024 | SELL | 1 | 0.08 | +1.42 | +1.423 | inf | 0.00 | +0.00 |
| 2025_H1 | BUY | 7 | 1.17 | -1.03 | -0.147 | 0.774 | 3.39 | -1.86 |
| 2025_H1 | SELL | 3 | 0.50 | +1.11 | +0.369 | 1.947 | 1.17 | -0.15 |
| 2025_H2 | BUY | 8 | 1.33 | +4.54 | +0.567 | 2.740 | 1.39 | +0.85 |
| 2025_H2 | SELL | 3 | 0.50 | -1.55 | -0.516 | 0.429 | 1.55 | -1.34 |
| 2026_JAN_JUL | BUY | 6 | 0.86 | +5.13 | +0.855 | 5.379 | 1.17 | +2.97 |
| 2026_JAN_JUL | SELL | 1 | 0.14 | -1.36 | -1.362 | 0.000 | 1.36 | +0.00 |
| POOLED_RECENT | BUY | 14 | 1.08 | +9.67 | +0.690 | 3.558 | 1.39 | +5.98 |
| POOLED_RECENT | SELL | 4 | 0.31 | -2.91 | -0.727 | 0.286 | 2.91 | -2.70 |
| HIST_PRE_RECENT | BUY | 23 | 0.43 | -7.84 | -0.341 | 0.568 | 12.88 | -9.31 |
| HIST_PRE_RECENT | SELL | 22 | 0.41 | -0.84 | -0.038 | 0.941 | 6.24 | -2.26 |
| ALL_PRE_AUG | BUY | 37 | 0.55 | +1.83 | +0.049 | 1.083 | 12.88 | -1.86 |
| ALL_PRE_AUG | SELL | 26 | 0.39 | -3.75 | -0.144 | 0.794 | 6.24 | -5.17 |
| AUG2026_REUSED_AUDIT | BUY | 2 | 2.00 | -2.92 | -1.461 | 0.000 | 2.92 | +0.00 |
| AUG2026_REUSED_AUDIT | SELL | 0 | 0.00 | +0.00 | — | — | 0.00 | — |

## Recent BUY robustness
- 7d episode bootstrap, 5000 draws: **[+0.124, +0.699, +1.236] R/fill**, episodes=9.
- Positive BUY months: **6/13**.
- Worst leave-one-month-out remaining R: **+5.98R**.
- Historical positive BUY windows: **2/5**; worst leave-one-window-out remaining R: **-9.31R**.

## Canonical + H4 BUY-only union

| Window | Fills | Fills/mo | Canon | H4 BUY | Cum R | Mean R | PF | DD R | Max conc | Risk load @0.5% | Eq ret @0.25% | Eq DD @0.25% | Eq ret @0.5% | Eq DD @0.5% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025_H2 | 19 | 3.17 | 11 | 8 | +12.38 | +0.652 | 3.119 | 1.39 | 2 | 1.00% | +3.13% | 0.35% | +6.35% | 0.69% |
| 2026_JAN_JUL | 18 | 2.57 | 12 | 6 | +12.19 | +0.677 | 3.203 | 2.39 | 4 | 2.00% | +3.09% | 0.60% | +6.24% | 1.19% |
| POOLED_RECENT | 37 | 2.85 | 23 | 14 | +24.58 | +0.664 | 3.160 | 2.39 | 4 | 2.00% | +6.32% | 0.60% | +12.99% | 1.19% |

LAB018 all-direction pooled benchmark: **41 fills, 3.15/month, +21.67R, PF 2.402, DD 3.75R**.

## Gates
- PASS — `lineage_exact`
- PASS — `buy_h2_fills_ge_6`
- PASS — `buy_2026_fills_ge_5`
- PASS — `buy_cumR_positive_both_recent`
- PASS — `buy_meanR_ge_0_30_both_recent`
- PASS — `buy_pf_gt_1_50_both_recent`
- PASS — `buy_sell_mean_delta_positive_both_recent`
- PASS — `sell_cumR_negative_both_recent`
- PASS — `buy_recent_loeo_positive`
- PASS — `buy_recent_cluster_bootstrap_low_gt_0`
- FAIL — `hist_buy_cumR_positive`
- FAIL — `hist_buy_pf_gt_1_20`
- FAIL — `hist_buy_positive_windows_ge_3_of_5`
- FAIL — `hist_buy_leave_one_window_out_positive`
- PASS — `union_freq_ge_2_75_per_month`
- PASS — `union_cumR_gt_all_direction_union_21_67R`
- PASS — `union_pf_ge_2_50`
- PASS — `union_maxdd_le_3_75R`
- PASS — `union_riskload_050_lt_4pct`

## Status
- This is a formal promotion/replication on **reused research windows**, not fresh OOS.
- August 2026 is consumed/reused audit only and cannot rescue the verdict.
- No SELL rescue, time filter, RR change, child-rule change or threshold change is allowed after this run.
- Canonical concurrency is conservatively bounded with `event_time + 24h` because its persisted artifact lacks actual exit timestamps; PnL/PF/DD-R are unaffected.
- Live allocation remains **0** pending fresh replication and execution/cost parity.
