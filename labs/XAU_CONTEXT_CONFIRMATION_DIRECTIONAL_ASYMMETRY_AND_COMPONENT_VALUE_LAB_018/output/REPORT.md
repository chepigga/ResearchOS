# XAU_CONTEXT_CONFIRMATION_DIRECTIONAL_ASYMMETRY_AND_COMPONENT_VALUE_LAB_018

**Verdict: DIRECTIONAL_ASYMMETRY_CONFIRMED**

- Population: **397**; exact resolved: **220**; HIGH75: **72**
- H1 BULL-BEAR HIGH75 accuracy gap: **+0.195**, 95% CI **[+0.009, +0.359]** — PASS
- H2 BULL HIGH75: **0.762**, CI **[0.625, 0.886]**, N=42 — PASS
- H3 BEAR HIGH75: **0.567**, CI **[0.462, 0.684]**, N=30 — FAIL

## HIGH75 side metrics

| side   |   n_resolved |   accuracy |   ci_lo |   ci_hi |   n_follow24 |   mean_signed24_atr |
|:-------|-------------:|-----------:|--------:|--------:|-------------:|--------------------:|
| BULL   |           42 |      0.762 |   0.625 |   0.886 |           42 |               1.190 |
| BEAR   |           30 |      0.567 |   0.462 |   0.684 |           37 |               0.060 |

## Component value by direction

| side   | component            |   n_present |   n_absent |   accuracy_present |   accuracy_absent |   marginal_premium |   marginal_ci_lo |   marginal_ci_hi |   conditional_premium |   conditional_weight |   eligible_strata | directionally_supportive   |
|:-------|:---------------------|------------:|-----------:|-------------------:|------------------:|-------------------:|-----------------:|-----------------:|----------------------:|---------------------:|------------------:|:---------------------------|
| BULL   | OB_CONFIRM           |          46 |         97 |              0.652 |             0.546 |              0.106 |           -0.058 |            0.256 |                 0.168 |                   40 |                 4 | True                       |
| BULL   | IMBALANCE_CONFIRM    |          79 |         64 |              0.582 |             0.578 |              0.004 |           -0.173 |            0.186 |                 0.013 |                   51 |                 4 | True                       |
| BULL   | LIQUIDITY_CONFIRM    |          46 |         97 |              0.674 |             0.536 |              0.138 |           -0.041 |            0.296 |                 0.169 |                   42 |                 4 | True                       |
| BULL   | PRICE_ACTION_CONFIRM |         133 |         10 |              0.594 |             0.400 |              0.194 |           -0.152 |            0.535 |                -0.167 |                    4 |                 1 | False                      |
| BEAR   | OB_CONFIRM           |          28 |         49 |              0.643 |             0.653 |             -0.010 |           -0.232 |            0.196 |                -0.087 |                   17 |                 2 | False                      |
| BEAR   | IMBALANCE_CONFIRM    |          45 |         32 |              0.689 |             0.594 |              0.095 |           -0.076 |            0.302 |                 0.062 |                   22 |                 3 | True                       |
| BEAR   | LIQUIDITY_CONFIRM    |          28 |         49 |              0.607 |             0.673 |             -0.066 |           -0.232 |            0.114 |                -0.090 |                   21 |                 2 | False                      |
| BEAR   | PRICE_ACTION_CONFIRM |          69 |          8 |              0.638 |             0.750 |             -0.112 |           -0.375 |            0.222 |                 0.250 |                    4 |                 1 | False                      |

## Exact 3-of-4 / 4-of-4 compositions

| side   | combination     |   n_resolved |   accuracy | eligible   |
|:-------|:----------------|-------------:|-----------:|:-----------|
| BULL   | NO_OB           |           14 |      0.571 | True       |
| BULL   | NO_IMBALANCE    |            4 |      1.000 | False      |
| BULL   | NO_LIQUIDITY    |           18 |      0.833 | True       |
| BULL   | NO_PRICE_ACTION |            0 |    nan     | False      |
| BULL   | ALL4            |            6 |      0.833 | False      |
| BEAR   | NO_OB           |           12 |      0.500 | True       |
| BEAR   | NO_IMBALANCE    |            3 |      0.333 | False      |
| BEAR   | NO_LIQUIDITY    |           13 |      0.615 | True       |
| BEAR   | NO_PRICE_ACTION |            0 |    nan     | False      |
| BEAR   | ALL4            |            2 |      1.000 | False      |

## Predeclared candidate diagnostics

| candidate               | side   |   n_resolved |   accuracy |   ci_lo |   ci_hi | quality_capable   |
|:------------------------|:-------|-------------:|-----------:|--------:|--------:|:------------------|
| HIGH75                  | BULL   |           42 |      0.762 |   0.625 |   0.886 | True              |
| HIGH75                  | BEAR   |           30 |      0.567 |   0.462 |   0.680 | False             |
| HIGH75_AND_OB           | BULL   |           28 |      0.857 |   0.731 |   0.964 | True              |
| HIGH75_AND_OB           | BEAR   |           18 |      0.611 |   0.500 |   0.750 | False             |
| HIGH75_AND_LIQUIDITY    | BULL   |           24 |      0.708 |   0.500 |   0.900 | False             |
| HIGH75_AND_LIQUIDITY    | BEAR   |           17 |      0.529 |   0.353 |   0.750 | False             |
| HIGH75_AND_IMBALANCE    | BULL   |           38 |      0.737 |   0.568 |   0.878 | True              |
| HIGH75_AND_IMBALANCE    | BEAR   |           27 |      0.593 |   0.500 |   0.722 | False             |
| HIGH75_AND_PRICE_ACTION | BULL   |           42 |      0.762 |   0.619 |   0.889 | True              |
| HIGH75_AND_PRICE_ACTION | BEAR   |           30 |      0.567 |   0.467 |   0.682 | False             |
| COREPAIR_PLUS_AUX       | BULL   |           10 |      0.900 |   0.700 |   1.000 | False             |
| COREPAIR_PLUS_AUX       | BEAR   |            5 |      0.600 |   0.250 |   1.000 | False             |

## Constraints

- Frozen LAB016 definitions and equal 25% weights; no tuning in LAB018.
- Reused-history directional robustness audit, not fresh OOS validation.
- Confirmation % is evidence coverage, NOT probability of profit and NOT automatic-entry permission.