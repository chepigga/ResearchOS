# BTC_XAU_CONTEXT_FROZEN_PORTABILITY_LONG_HISTORY_LAB_002
**Verdict: BTC_PORTABILITY_NOT_SUPPORTED**

- Fixed Binance USD-M BTCUSDT M15 history: **2021-01-01 00:00:00 → 2026-07-31 23:45:00**; rows **195,648**; missing months **0**.
- H4 ready bars: **12,027**; episodes **705**; frozen population **1,314**; resolved **660**; HIGH75 resolved **223**.

- H1 HIGH75 overall: **0.516**, 95% CI **[0.443, 0.586]**, N=223 — FAIL.
- H2 BULL HIGH75: **0.475**, CI **[0.364, 0.579]**, N=99 — FAIL.
- H3 BEAR HIGH75: **0.548**, CI **[0.452, 0.640]**, N=124 — FAIL.
- H4 BULL-BEAR gap: **-0.074**, CI **[-0.212, +0.066]** — FAIL.

## Frozen gate counts
|   h4_ready |   episodes |   pullback |   g1 |   d14 |   pullback_g1 |   pullback_d14 |   g1_d14 |   population |
|-----------:|-----------:|-----------:|-----:|------:|--------------:|---------------:|---------:|-------------:|
|      12027 |        705 |       8367 | 3105 |  6084 |          2335 |           4335 |     1452 |         1314 |

## Evidence buckets
|   score_pct |   n_all |   n_resolved |   accuracy |   mean_signed24_atr |
|------------:|--------:|-------------:|-----------:|--------------------:|
|           0 |      24 |           12 |   0.75     |          0.156987   |
|          25 |     231 |          108 |   0.537037 |         -0.155894   |
|          50 |     625 |          317 |   0.457413 |         -0.0703965  |
|          75 |     390 |          200 |   0.525    |          0.00012065 |
|         100 |      44 |           23 |   0.434783 |         -0.114048   |

## Side metrics
| side   |   n_resolved |   accuracy |    ci_lo |    ci_hi |   n_follow24 |   mean_signed24_atr |
|:-------|-------------:|-----------:|---------:|---------:|-------------:|--------------------:|
| BULL   |           99 |   0.474747 | 0.363614 | 0.578983 |          188 |           -0.163719 |
| BEAR   |          124 |   0.548387 | 0.451593 | 0.640016 |          246 |            0.104911 |

## Component value by side
| side   | component            |   n_present |   n_absent |   accuracy_present |   accuracy_absent |    premium |
|:-------|:---------------------|------------:|-----------:|-------------------:|------------------:|-----------:|
| BULL   | OB_CONFIRM           |          95 |        187 |           0.431579 |          0.491979 | -0.0603997 |
| BULL   | IMBALANCE_CONFIRM    |         157 |        125 |           0.484076 |          0.456    |  0.0280764 |
| BULL   | LIQUIDITY_CONFIRM    |         102 |        180 |           0.421569 |          0.5      | -0.0784314 |
| BULL   | PRICE_ACTION_CONFIRM |         263 |         19 |           0.467681 |          0.526316 | -0.0586352 |
| BEAR   | OB_CONFIRM           |         135 |        243 |           0.555556 |          0.489712 |  0.0658436 |
| BEAR   | IMBALANCE_CONFIRM    |         211 |        167 |           0.530806 |          0.491018 |  0.0397877 |
| BEAR   | LIQUIDITY_CONFIRM    |         125 |        253 |           0.472    |          0.533597 | -0.0615968 |
| BEAR   | PRICE_ACTION_CONFIRM |         346 |         32 |           0.50289  |          0.625    | -0.12211   |

## HIGH75 exact compositions
| side   | composition   |   n_resolved |   accuracy |
|:-------|:--------------|-------------:|-----------:|
| ALL    | ALL4          |           23 |   0.434783 |
| ALL    | NO_IMBALANCE  |           30 |   0.433333 |
| ALL    | NO_LIQUIDITY  |          109 |   0.541284 |
| ALL    | NO_OB         |           61 |   0.540984 |
| BULL   | ALL4          |            9 |   0.333333 |
| BULL   | NO_IMBALANCE  |           12 |   0.5      |
| BULL   | NO_LIQUIDITY  |           50 |   0.48     |
| BULL   | NO_OB         |           28 |   0.5      |
| BEAR   | ALL4          |           14 |   0.5      |
| BEAR   | NO_IMBALANCE  |           18 |   0.388889 |
| BEAR   | NO_LIQUIDITY  |           59 |   0.59322  |
| BEAR   | NO_OB         |           33 |   0.575758 |

## Calendar-year HIGH75
|   year |   n_high75 |   accuracy |   bull_n |   bear_n |
|-------:|-----------:|-----------:|---------:|---------:|
|   2021 |         33 |   0.484848 |       18 |       15 |
|   2022 |         47 |   0.574468 |        9 |       38 |
|   2023 |         40 |   0.55     |       19 |       21 |
|   2024 |         39 |   0.589744 |       24 |       15 |
|   2025 |         36 |   0.361111 |       23 |       13 |
|   2026 |         28 |   0.5      |        6 |       22 |

## Missing months
None.

## Boundary
No retuning. This is direction/confirmation portability only, not P(profitable trade), RR economics, fees, funding, slippage, or FTMO BTCUSD parity.