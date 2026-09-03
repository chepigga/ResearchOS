# BTC_REVERSAL_2025H2_PROFIT_CONCENTRATION_AND_EPISODE_INDEPENDENCE_LAB_011

**Verdict:** **WATCH_POSITIVE_BUT_CONCENTRATED**

Role: structural concentration/episode-independence diagnosis of the exact frozen reversal branch; no new gate.

## Frozen-window reconciliation

| Window | Signals | Fills | Cum R | EV/op | PF |
|---|---:|---:|---:|---:|---:|
| 2025_H2 | 16 | 12 | +6.64 | +0.415 | 2.458 |
| 2026_JAN_JUL | 22 | 15 | +6.17 | +0.281 | 1.929 |

## 2025 H2 monthly breadth

| Month | Signals | Fills | Cum R | EV | PF |
|---|---:|---:|---:|---:|---:|
| 2025-07 | 1 | 1 | -1.18 | -1.182 | 0.000 |
| 2025-08 | 1 | 1 | -1.20 | -1.201 | 0.000 |
| 2025-09 | 0 | 0 | +0.00 | +nan | — |
| 2025-10 | 8 | 6 | +5.94 | +0.743 | 6.455 |
| 2025-11 | 6 | 4 | +3.08 | +0.514 | 3.848 |
| 2025-12 | 0 | 0 | +0.00 | +nan | — |

## Direction split

| Window | Reversal side | Signals | Fills | Cum R | EV | PF |
|---|---|---:|---:|---:|---:|---:|
| 2025_H2 | BUY | 13 | 10 | +3.76 | +0.289 | 1.825 |
| 2025_H2 | SELL | 3 | 2 | +2.88 | +0.961 | inf |
| 2026_JAN_JUL | BUY | 16 | 12 | +6.97 | +0.436 | 2.585 |
| 2026_JAN_JUL | SELL | 6 | 3 | -0.80 | -0.133 | 0.644 |

## Primary 7d episodes

| Window | Episode | Start | End | Signals | Fills | Cum R | EV |
|---|---:|---|---|---:|---:|---:|---:|
| 2025_H2 | 46 | 2025-07-24 | 2025-07-24 | 1 | 1 | -1.18 | -1.182 |
| 2025_H2 | 47 | 2025-08-29 | 2025-08-29 | 1 | 1 | -1.20 | -1.201 |
| 2025_H2 | 48 | 2025-10-11 | 2025-10-21 | 7 | 5 | +7.03 | +1.005 |
| 2025_H2 | 49 | 2025-10-30 | 2025-10-30 | 1 | 1 | -1.09 | -1.089 |
| 2025_H2 | 50 | 2025-11-14 | 2025-11-21 | 6 | 4 | +3.08 | +0.514 |
| 2026_JAN_JUL | 51 | 2026-01-30 | 2026-02-06 | 8 | 4 | -1.70 | -0.212 |
| 2026_JAN_JUL | 52 | 2026-02-28 | 2026-02-28 | 1 | 1 | +1.47 | +1.468 |
| 2026_JAN_JUL | 53 | 2026-03-23 | 2026-03-23 | 1 | 1 | +1.36 | +1.364 |
| 2026_JAN_JUL | 54 | 2026-04-07 | 2026-04-07 | 1 | 1 | +1.38 | +1.380 |
| 2026_JAN_JUL | 55 | 2026-05-11 | 2026-05-11 | 1 | 0 | +0.00 | +0.000 |
| 2026_JAN_JUL | 56 | 2026-05-24 | 2026-05-24 | 1 | 1 | -1.18 | -1.180 |
| 2026_JAN_JUL | 57 | 2026-06-02 | 2026-06-06 | 8 | 6 | +6.06 | +0.757 |
| 2026_JAN_JUL | 58 | 2026-07-31 | 2026-07-31 | 1 | 1 | -1.22 | -1.219 |

## Concentration
- **2025_H2**: gross positive +11.20R; top-1 winner **13.0%**; top-3 **38.4%**; top 7d episode **62.8%** of gross positive R.
- **2026_JAN_JUL**: gross positive +12.82R; top-1 winner **11.5%**; top-3 **34.3%**; top 7d episode **55.9%** of gross positive R.

## Leave-one-out robustness
- **2025_H2**: worst leave-one-month-out remaining R = **+0.70R**; worst leave-one-episode-out remaining R = **-0.39R**.
- **2026_JAN_JUL**: worst leave-one-month-out remaining R = **+0.11R**; worst leave-one-episode-out remaining R = **+0.11R**.

## Episode-cluster bootstrap
- **2025_H2**: mean **+0.415R/op**, 95% cluster CI **[-1.171, +0.821]**, episodes=5.
- **2026_JAN_JUL**: mean **+0.281R/op**, 95% cluster CI **[-0.257, +0.875]**, episodes=8.

## Episode-gap audit (descriptive only)

| Window | Gap | Episodes | Positive | Negative | Top episode share | Worst LOEO R |
|---|---:|---:|---:|---:|---:|---:|
| 2025_H2 | 3d | 7 | 4 | 3 | 50.5% | +0.98 |
| 2025_H2 | 7d | 5 | 2 | 3 | 62.8% | -0.39 |
| 2025_H2 | 14d | 4 | 2 | 2 | 62.8% | +0.70 |
| 2026_JAN_JUL | 3d | 8 | 4 | 3 | 55.9% | +0.11 |
| 2026_JAN_JUL | 7d | 8 | 4 | 3 | 55.9% | +0.11 |
| 2026_JAN_JUL | 14d | 6 | 4 | 2 | 55.9% | +1.29 |

## Gates
- PASS — `h2_2025_cum_positive`
- FAIL — `h2_2025_positive_months_ge_4_of_6`
- PASS — `h2_2025_all_lomo_positive`
- PASS — `h2_2025_episodes_ge_4`
- FAIL — `h2_2025_positive_episodes_ge_3`
- FAIL — `h2_2025_all_loeo_positive`
- PASS — `h2_2025_top1_share_le_35pct`
- PASS — `h2_2025_top3_share_le_70pct`
- FAIL — `h2_2025_top_episode_share_le_50pct`
- FAIL — `h2_2025_cluster_bootstrap_ci_low_gt_0`
- PASS — `y2026_jan_jul_cum_positive`
- PASS — `y2026_episode_breadth`

**Score 7/12 → WATCH_POSITIVE_BUT_CONCENTRATED**

## Status
- 2025 H2/2026 were seen in earlier LABs; this is not a fresh holdout.
- 3d/14d episode definitions are audit-only and cannot rescue the primary 7d verdict.
- No live allocation is authorized by this LAB alone.
