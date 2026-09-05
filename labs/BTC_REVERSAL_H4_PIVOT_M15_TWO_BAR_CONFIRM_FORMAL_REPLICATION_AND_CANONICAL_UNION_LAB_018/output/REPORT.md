# BTC_REVERSAL_H4_PIVOT_M15_TWO_BAR_CONFIRM_FORMAL_REPLICATION_AND_CANONICAL_UNION_LAB_018

**Verdict: PASS_FORMAL_TWO_BAR_REPLICATION_REUSED — 16/16**

Frozen primary: exact LAB017 audit `TWO_BAR_CONFIRM_12H` promoted before this run; exact LAB016 213-parent lineage; exact LAB015 canonical stream.

## H4 two-bar module

| Window | Parents | Real fills | Fills/mo | Mean R | Cum R | PF | DD R | LOEO worst | Max concurrent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025_H2 | 22 | 11 | 1.83 | +0.272 | +2.99 | 1.562 | 1.95 | -0.70 | 1 |
| 2026_JAN_JUL | 21 | 7 | 1.00 | +0.538 | +3.77 | 2.487 | 2.53 | +1.61 | 1 |
| POOLED_RECENT | 43 | 18 | 1.38 | +0.375 | +6.76 | 1.861 | 2.53 | +3.07 | 1 |
| AUG2026_REUSED_AUDIT | 6 | 2 | 2.00 | -1.461 | -2.92 | 0.000 | 2.92 | -2.92 | 1 |

## Canonical + H4 two-bar union

| Window | Fills | Fills/mo | Canon | H4 | Cum R | Mean R | PF | DD R | Max conc | Risk load @0.5% | Eq ret @0.25% | Eq DD @0.25% | Eq ret @0.5% | Eq DD @0.5% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025_H2 | 22 | 3.67 | 11 | 11 | +10.84 | +0.493 | 2.267 | 1.75 | 2 | 1.00% | +2.73% | 0.44% | +5.52% | 0.88% |
| 2026_JAN_JUL | 19 | 2.71 | 12 | 7 | +10.83 | +0.570 | 2.570 | 3.75 | 4 | 2.00% | +2.73% | 0.93% | +5.52% | 1.86% |
| POOLED_RECENT | 41 | 3.15 | 23 | 18 | +21.67 | +0.528 | 2.402 | 3.75 | 4 | 2.00% | +5.54% | 0.93% | +11.35% | 1.86% |

## Direction split

| Window | Side | N | Cum R | Mean R | PF | DD R |
|---|---|---:|---:|---:|---:|---:|
| 2025_H2 | BUY | 8 | +4.54 | +0.567 | 2.740 | 1.39 |
| 2025_H2 | SELL | 3 | -1.55 | -0.516 | 0.429 | 1.55 |
| 2026_JAN_JUL | BUY | 6 | +5.13 | +0.855 | 5.379 | 1.17 |
| 2026_JAN_JUL | SELL | 1 | -1.36 | -1.362 | 0.000 | 1.36 |
| POOLED_RECENT | BUY | 14 | +9.67 | +0.690 | 3.558 | 1.39 |
| POOLED_RECENT | SELL | 4 | -2.91 | -0.727 | 0.286 | 2.91 |

## Gates
- PASS — `lineage_exact`
- PASS — `h2_real_fills_ge_8`
- PASS — `y2026_real_fills_ge_5`
- PASS — `mean_R_positive_both`
- PASS — `pf_gt_1_30_both`
- PASS — `cumR_positive_both`
- PASS — `pooled_ev_ge_0_25R`
- PASS — `pooled_pf_ge_1_50`
- PASS — `pooled_loeo_positive`
- PASS — `pooled_maxdd_le_3R`
- PASS — `union_freq_ge_3_per_month`
- PASS — `union_incremental_cumR_ge_2R`
- PASS — `union_pf_ge_1_75`
- PASS — `union_maxdd_le_4R`
- PASS — `union_max_concurrent_risk_050_lt_4pct`
- PASS — `union_positive_both_recent_windows`

## Status
- This is formal replication on reused research windows, **not fresh OOS**.
- August 2026 remains consumed/reused audit only.
- No parameter or child-rule rescue is allowed after this run.
- Live allocation remains **0**; M1/raw execution parity, exact prop costs/slippage, future fresh replication, and full prop-rule implementation are still required.

## Risk-accounting note
- LAB015 canonical artifact did not persist actual `exit_time`; union concurrency uses conservative `canonical event_time + 24h`. This may overstate overlap. PnL, EV, PF and DD-R are unaffected.
