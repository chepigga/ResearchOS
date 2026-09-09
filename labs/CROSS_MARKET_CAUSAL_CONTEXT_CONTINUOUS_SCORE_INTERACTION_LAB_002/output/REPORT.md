# CROSS_MARKET_CAUSAL_CONTEXT_CONTINUOUS_SCORE_INTERACTION_LAB_002

**Verdict: MIXED_CROSS_MARKET_CONTINUOUS_CONTEXT**

> Reused-history discovery only. No thresholds, router weights, alpha rules, or risk sizing were fit in this lab.

## Frozen continuous score

`C = (Expansion + Pullback - Reversal - Range) / 200`

| Market | N | Q1 mean | Q5 mean | Lift | Slope | Lift 95% CI | Slope 95% CI | Q5 monotone | Positive transfer | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BTC | 327 | +0.0856 | +0.2986 | +0.2130 | +0.1154 | [-0.1549, +0.5624] | [-0.3566, +0.5867] | 50% | 3/5 required | MIXED_CONTINUOUS_CONTEXT_EVIDENCE |
| XAU | 266,297 | -0.0235 | -0.0081 | +0.0154 | +0.0153 | [-0.0076, +0.0394] | [-0.0124, +0.0428] | 50% | 3/4 required | MIXED_CONTINUOUS_CONTEXT_EVIDENCE |

## Frozen gates

### BTC
- PASS — `top_gt_bottom`
- FAIL — `bootstrap_lift_ci_low_gt_zero`
- PASS — `continuous_slope_gt_zero`
- FAIL — `bootstrap_slope_ci_low_gt_zero`
- FAIL — `q5_adjacent_monotone_ge_075`
- FAIL — `time_transfer_positive_required`

### XAU
- PASS — `top_gt_bottom`
- FAIL — `bootstrap_lift_ci_low_gt_zero`
- PASS — `continuous_slope_gt_zero`
- FAIL — `bootstrap_slope_ci_low_gt_zero`
- FAIL — `q5_adjacent_monotone_ge_075`
- FAIL — `time_transfer_positive_required`

## Interpretation

- A pass only supports graded Context information on reused history; it does not authorize live risk modulation.
- Bias compatibility is reported separately in the Q5 × bias matrices and never folded into C.
- XAU primary outcome is drift-adjusted excess; raw R is secondary.
- If only one market passes, Context is market/alpha-specific rather than a general router.