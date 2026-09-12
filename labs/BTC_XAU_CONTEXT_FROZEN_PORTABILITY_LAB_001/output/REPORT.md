# BTC_XAU_CONTEXT_FROZEN_PORTABILITY_LAB_001
**Verdict: BTC_PORTABILITY_NOT_SUPPORTED**

- Data: 2025-10-01 00:00:00 → 2025-10-31 23:45:00; M15 rows **2,976**.
- Frozen BTC population: **0**; resolved: **0**; HIGH75 resolved: **0**.

- H1 HIGH75 all: **nan**, CI **[nan, nan]**, N=0 — FAIL.
- H2 BULL HIGH75: **nan**, CI **[nan, nan]**, N=0 — FAIL.
- H3 BEAR HIGH75: **nan**, CI **[nan, nan]**, N=0 — FAIL.
- H4 BULL-BEAR asymmetry: **+nan**, CI **[+nan, +nan]** — FAIL.

## Score buckets
|   score_pct |   n_all |   n_resolved |   accuracy |   mean_signed24_atr |
|------------:|--------:|-------------:|-----------:|--------------------:|
|           0 |       0 |            0 |        nan |                 nan |
|          25 |       0 |            0 |        nan |                 nan |
|          50 |       0 |            0 |        nan |                 nan |
|          75 |       0 |            0 |        nan |                 nan |
|         100 |       0 |            0 |        nan |                 nan |

## Direction
| side   |   n_resolved |   accuracy |   ci_lo |   ci_hi |   n_follow24 |   mean_signed24_atr |
|:-------|-------------:|-----------:|--------:|--------:|-------------:|--------------------:|
| BULL   |            0 |        nan |     nan |     nan |            0 |                 nan |
| BEAR   |            0 |        nan |     nan |     nan |            0 |                 nan |

## Components by side
| side   | component            |   n_present |   n_absent |   accuracy_present |   accuracy_absent |   premium |
|:-------|:---------------------|------------:|-----------:|-------------------:|------------------:|----------:|
| BULL   | OB_CONFIRM           |           0 |          0 |                nan |               nan |       nan |
| BULL   | IMBALANCE_CONFIRM    |           0 |          0 |                nan |               nan |       nan |
| BULL   | LIQUIDITY_CONFIRM    |           0 |          0 |                nan |               nan |       nan |
| BULL   | PRICE_ACTION_CONFIRM |           0 |          0 |                nan |               nan |       nan |
| BEAR   | OB_CONFIRM           |           0 |          0 |                nan |               nan |       nan |
| BEAR   | IMBALANCE_CONFIRM    |           0 |          0 |                nan |               nan |       nan |
| BEAR   | LIQUIDITY_CONFIRM    |           0 |          0 |                nan |               nan |       nan |
| BEAR   | PRICE_ACTION_CONFIRM |           0 |          0 |                nan |               nan |       nan |

## Annual HIGH75


## Boundary
This is a no-retune Binance BTCUSDT portability test. It does not establish FTMO BTCUSD execution parity or profit probability.