# XAU_CONTEXT_SETUP_CONFIRMATION_OB_IMBALANCE_LIQUIDITY_PRICE_ACTION_LAB_016

**Verdict: SETUP_CONFIRMATION_PARTIAL**

- Population PULLBACK+G1+D14: **397**
- Exact resolved ±1 ATR: **220**
- Mean confirmation: **52.0%**; median **50%**

## Primary gates

| Gate | Effect | 95% CI | N | Pass |
|---|---:|---:|---:|---|
| H1 >=50 vs <50 direction accuracy premium | +0.074 | [-0.078, +0.232] | 176/44 | FAIL |
| H2 >=50 vs <50 signed24 premium | -0.197 ATR | [-0.694, +0.269] | 233/56 | FAIL |
| H3 >=75 absolute accuracy | 0.681 | [+0.585, +0.783] | 72 | PASS |
| H4 bucket monotonicity | — | — | eligible buckets=3 | PASS |

## Score buckets

|   score_pct |   n_all |   n_resolved |   accuracy |   mean_signed24_atr |
|------------:|--------:|-------------:|-----------:|--------------------:|
|           0 |       7 |            2 |   1        |            1.74906  |
|          25 |      72 |           42 |   0.52381  |            0.628845 |
|          50 |     212 |          104 |   0.576923 |            0.466515 |
|          75 |      94 |           64 |   0.65625  |            0.61795  |
|         100 |      12 |            8 |   0.875    |            0.992334 |

## Component diagnostics

| component            | present   |   n_all |   prevalence |   n_resolved |   accuracy |   mean_signed24_atr |
|:---------------------|:----------|--------:|-------------:|-------------:|-----------:|--------------------:|
| OB_CONFIRM           | True      |     118 |    0.297229  |           74 |   0.648649 |            0.644534 |
| OB_CONFIRM           | False     |     279 |    0.702771  |          146 |   0.582192 |            0.541041 |
| IMBALANCE_CONFIRM    | True      |     223 |    0.561713  |          124 |   0.620968 |            0.504993 |
| IMBALANCE_CONFIRM    | False     |     174 |    0.438287  |           96 |   0.583333 |            0.658687 |
| LIQUIDITY_CONFIRM    | True      |     126 |    0.31738   |           74 |   0.648649 |            0.641559 |
| LIQUIDITY_CONFIRM    | False     |     271 |    0.68262   |          146 |   0.582192 |            0.537177 |
| PRICE_ACTION_CONFIRM | True      |     359 |    0.904282  |          202 |   0.608911 |            0.549235 |
| PRICE_ACTION_CONFIRM | False     |      38 |    0.0957179 |           18 |   0.555556 |            0.804162 |

## Side symmetry at >=50%

| side   |   n |   accuracy |   mean_score_pct |
|:-------|----:|-----------:|-----------------:|
| BULL   | 114 |   0.587719 |          60.5263 |
| BEAR   |  62 |   0.677419 |          62.9032 |

## Constraints

- Equal 25% weights were frozen before outcomes.
- This percentage is setup evidence coverage, NOT probability of profit.
- Reused history => any positive result remains DISCOVERY_ONLY.
- No automated entry/risk claim.