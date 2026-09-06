# BTC_REVERSAL_H4_BUY_PARENT_RANGE_COMPRESSION_AND_M15_RESPONSE_SCALE_LAB_021

**Verdict: FAIL_NO_ROBUST_PARENT_COMPRESSION_MECHANISM — 4/10**

## Parent compression — compact vs large

| Window | Class | Opps | Fills | CumR | MeanR | PF | DD |
|---|---|---:|---:|---:|---:|---:|---:|
| HIST_PRE_RECENT | COMPACT | 23 | 7 | -2.00 | -0.285 | 0.634 | 4.15 |
| HIST_PRE_RECENT | LARGE | 66 | 16 | -5.84 | -0.365 | 0.539 | 10.06 |
| 2025_H1 | COMPACT | 2 | 1 | +0.83 | 0.826 | inf | 0.00 |
| 2025_H1 | LARGE | 12 | 6 | -1.86 | -0.310 | 0.593 | 3.39 |
| 2025_H2 | COMPACT | 11 | 6 | +2.06 | 0.343 | 1.789 | 1.39 |
| 2025_H2 | LARGE | 2 | 2 | +2.48 | 1.240 | inf | 0.00 |
| 2026_JAN_JUL | COMPACT | 8 | 4 | +4.87 | 1.216 | inf | 0.00 |
| 2026_JAN_JUL | LARGE | 9 | 2 | +0.26 | 0.131 | 1.223 | 1.17 |
| POOLED_RECENT | COMPACT | 19 | 10 | +6.92 | 0.692 | 3.655 | 1.39 |
| POOLED_RECENT | LARGE | 11 | 4 | +2.74 | 0.685 | 3.342 | 1.17 |
| AUG2026_REUSED_AUDIT | COMPACT | 4 | 2 | -2.92 | -1.461 | 0.000 | 2.92 |
| AUG2026_REUSED_AUDIT | LARGE | 0 | 0 | +0.00 | — | — | 0.00 |

## Fixed parent-range bins — pooled recent

| Bin | Opps | Fills | CumR | MeanR | PF | DD |
|---|---:|---:|---:|---:|---:|---:|
| LT1 | 9 | 4 | +2.06 | 0.514 | 2.482 | 1.39 |
| 1_1P5 | 10 | 6 | +4.87 | 0.811 | 4.985 | 1.22 |
| 1P5_2 | 6 | 2 | +2.48 | 1.240 | inf | 0.00 |
| 2_3 | 4 | 2 | +0.26 | 0.131 | 1.223 | 1.17 |
| GE3 | 1 | 0 | +0.00 | — | — | 0.00 |

## Threshold-free monotonicity

- HIST_PRE_RECENT: N=23, Spearman rho=0.291
- 2025_H2: N=8, Spearman rho=0.667
- 2026_JAN_JUL: N=6, Spearman rho=0.029
- POOLED_RECENT: N=14, Spearman rho=0.446
- ALL_PRE_AUG: N=37, Spearman rho=0.056
- AUG2026_REUSED_AUDIT: N=2, Spearman rho=—
- Recent episode-bootstrap rho 95% CI: [-0.176, +0.866], median +0.452
- Recent compact-minus-large meanR bootstrap 95% CI: [-1.171, +1.638], median -0.124R

## M15 response-scale interaction — pooled recent

| Parent | Response | Fills | CumR | MeanR | PF |
|---|---|---:|---:|---:|---:|
| COMPACT | LOW | 3 | +3.15 | 1.051 | inf |
| COMPACT | MID | 6 | +2.37 | 0.395 | 1.909 |
| COMPACT | HIGH | 1 | +1.40 | 1.403 | inf |
| LARGE | LOW | 2 | -0.07 | -0.034 | 0.942 |
| LARGE | MID | 1 | +1.38 | 1.377 | inf |
| LARGE | HIGH | 1 | +1.43 | 1.432 | inf |

## VF maturity interaction — pooled recent

| Parent | VF | Fills | CumR | MeanR | PF |
|---|---|---:|---:|---:|---:|
| COMPACT | VF1 | 5 | +3.83 | 0.767 | 4.139 |
| COMPACT | VF2PLUS | 5 | +3.09 | 0.618 | 3.228 |
| LARGE | VF1 | 3 | +1.64 | 0.546 | 2.399 |
| LARGE | VF2PLUS | 1 | +1.10 | 1.103 | inf |

## Gates
- PASS — `recent_compact_cumR_positive`
- PASS — `recent_compact_mean_gt_large`
- FAIL — `recent_spearman_negative`
- FAIL — `bootstrap_compact_minus_large_low_gt_0`
- FAIL — `bootstrap_spearman_high_lt_0`
- PASS — `both_recent_windows_compact_positive`
- FAIL — `response_scale_supportive`
- FAIL — `large_not_rescued_by_high_response`
- FAIL — `vf_maturity_supportive`
- PASS — `historical_compact_improves_baseline`

## Guardrail
Reused-data mechanism test only. No cutoff or router is promoted. Live allocation remains **0** pending separately preregistered replication and execution/cost parity.