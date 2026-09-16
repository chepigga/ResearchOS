# GC_XAU_D1_E3_CORRECTED_ONEACTIVE_DEPENDENCY_LAB_014H

**Status: CORRECTED_HISTORICAL_ROBUSTNESS_PASS_NOT_OOS**

Uses the already-collected LAB009 sequence only. The sole change is the corrected unfilled one-active clock: `order_start + 3m` instead of `signal-bar left edge + 3m`.

| Cohort | N | Accepted | Fills | EV R/signal | Sum R | MaxDD R | P(EV>0) | EV CI95 | LOO-week min EV | +day share | DD p95 @0.25% | DD p95 @0.50% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| COMMON_CLOCK | 245 | 208 | 88 | +0.08376 | +20.52 | 8.40 | 96.04% | [-0.0099,+0.1843] | +0.07170 | 20.5% | 3.512% | 7.025% |
| AMP_ALL | 279 | 237 | 103 | +0.08634 | +24.09 | 8.40 | 96.31% | [-0.0086,+0.1852] | +0.07497 | 16.9% | 3.894% | 7.788% |

## Gates @ 0.25% research risk

- PASS — `common_boot_p_ev_gt0_ge80pct`
- PASS — `amp_boot_p_ev_gt0_ge80pct`
- PASS — `common_loo_week_min_ev_pos`
- PASS — `amp_loo_week_min_ev_pos`
- PASS — `common_max_positive_day_share_lt50pct`
- PASS — `common_boot_p95_dd_025risk_lt5pct`
- PASS — `amp_boot_p95_dd_025risk_lt5pct`

## 0.50% diagnostic

- FAIL — `common_boot_p95_dd_050risk_lt5pct`
- FAIL — `amp_boot_p95_dd_050risk_lt5pct`

## Delta vs frozen LAB010

- **COMMON_CLOCK**: ΔEV +0.008571R/signal; ΔSum +2.100R; ΔMaxDD +0.000R; Δboot p95 DD@0.25% -0.173 pp.
- **AMP_ALL**: ΔEV +0.007527R/signal; ΔSum +2.100R; ΔMaxDD +0.000R; Δboot p95 DD@0.25% -0.181 pp.

This is a corrected historical robustness audit, not independent OOS certification.
