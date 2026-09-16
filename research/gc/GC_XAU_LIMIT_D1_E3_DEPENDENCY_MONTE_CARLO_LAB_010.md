# GC_XAU_LIMIT_D1_E3_DEPENDENCY_MONTE_CARLO_LAB_010

**Status: HISTORICAL_ROBUSTNESS_FAIL_NOT_OOS**

Frozen candidate: **D1.00_E3M**, ONE_ACTIVE_SETUP, SL 1.5 ATR, TP 3R, timeout 30m, +0.05R adverse cost/fill.

| Cohort | N | EV R/signal | Sum R | MaxDD R | P(EV>0) | Boot EV CI95 | LOO-week min EV | Max +day share | Boot DD p95 @0.5% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| COMMON_CLOCK | 245 | +0.075 | +18.42 | 8.40 | 94.2% | [-0.019,+0.177] | +0.061 | 21.5% | 7.37% |
| AMP_ALL | 279 | +0.079 | +21.99 | 8.40 | 94.8% | [-0.016,+0.178] | +0.067 | 17.6% | 8.15% |

## Gates

- PASS — `common_boot_p_ev_gt0_ge80pct`
- PASS — `amp_boot_p_ev_gt0_ge80pct`
- PASS — `common_loo_week_min_ev_pos`
- PASS — `amp_loo_week_min_ev_pos`
- PASS — `common_max_positive_day_share_lt50pct`
- FAIL — `common_boot_p95_dd_050risk_lt5pct`

## Governance

This is a historical dependency/Monte-Carlo stress test on a post-discovery candidate. A PASS supports freezing for forward shadow; it does not convert the sample into independent OOS evidence.
