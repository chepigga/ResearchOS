# GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007

**Status: POST_DISCOVERY_GEOMETRY_MAP_COMPLETED_NOT_OOS**

Primary exact common-clock executable cohort: **N=245** (raw common signal times before executable/ATR gate: 247). Secondary AMP cohort: **N=279**.

No GC threshold/session/regime parameter was changed. All entries use FTMO Ask; exits/path use Bid. Quoted spread is included. Commission/slippage are not included.

## Retest depth from market-reference Ask

| Cohort | Window | Mean ATR | Q25 | Median | Q75 |
|---|---:|---:|---:|---:|---:|
| COMMON_CLOCK | 5m | -1.279 | -1.603 | -1.044 | -0.430 |
| COMMON_CLOCK | 10m | -1.756 | -2.299 | -1.360 | -0.658 |
| AMP_ALL | 5m | -1.270 | -1.665 | -1.063 | -0.434 |
| AMP_ALL | 10m | -1.731 | -2.291 | -1.372 | -0.671 |

## Entry geometry

| Cohort | Geometry | Fill | Fill rate | Median delay | Median MFE30 | Median MAE30 |
|---|---|---:|---:|---:|---:|---:|
| COMMON_CLOCK | MARKET | 245 | 100.0% | 0.0s | +2.421 ATR | -2.463 ATR |
| COMMON_CLOCK | LIM_025ATR_5M | 202 | 82.4% | 21.5s | +2.289 ATR | -2.514 ATR |
| COMMON_CLOCK | LIM_050ATR_5M | 175 | 71.4% | 47.7s | +2.258 ATR | -2.583 ATR |
| COMMON_CLOCK | LIM_050ATR_10M | 192 | 78.4% | 52.2s | +2.244 ATR | -2.590 ATR |
| COMMON_CLOCK | LIM_075ATR_10M | 180 | 73.5% | 88.0s | +2.325 ATR | -2.531 ATR |
| COMMON_CLOCK | LIM_100ATR_10M | 157 | 64.1% | 112.8s | +2.343 ATR | -2.407 ATR |
| AMP_ALL | MARKET | 279 | 100.0% | 0.0s | +2.244 ATR | -2.522 ATR |
| AMP_ALL | LIM_025ATR_5M | 233 | 83.5% | 20.0s | +2.287 ATR | -2.507 ATR |
| AMP_ALL | LIM_050ATR_5M | 202 | 72.4% | 45.8s | +2.244 ATR | -2.411 ATR |
| AMP_ALL | LIM_050ATR_10M | 220 | 78.9% | 50.1s | +2.224 ATR | -2.562 ATR |
| AMP_ALL | LIM_075ATR_10M | 204 | 73.1% | 82.7s | +2.325 ATR | -2.460 ATR |
| AMP_ALL | LIM_100ATR_10M | 179 | 64.2% | 108.9s | +2.286 ATR | -2.368 ATR |

## First passage from MARKET entry

Primary/common-clock only. Percentages are path order, not optimized trade results.

| Window | Stop | RR | TP first | SL first | Neither |
|---|---:|---:|---:|---:|---:|
| 15m | 1.0 ATR | 1.5 | 31.8% | 67.3% | 2 |
| 15m | 1.0 ATR | 2.0 | 25.7% | 71.4% | 7 |
| 15m | 1.0 ATR | 3.0 | 18.8% | 73.9% | 18 |
| 15m | 1.5 ATR | 1.5 | 30.6% | 59.6% | 24 |
| 15m | 1.5 ATR | 2.0 | 24.9% | 60.0% | 37 |
| 15m | 1.5 ATR | 3.0 | 11.0% | 61.2% | 68 |
| 30m | 1.0 ATR | 1.5 | 32.2% | 67.8% | 0 |
| 30m | 1.0 ATR | 2.0 | 26.5% | 73.5% | 0 |
| 30m | 1.0 ATR | 3.0 | 21.2% | 78.0% | 2 |
| 30m | 1.5 ATR | 1.5 | 32.7% | 65.7% | 4 |
| 30m | 1.5 ATR | 2.0 | 31.0% | 66.5% | 6 |
| 30m | 1.5 ATR | 3.0 | 20.0% | 70.2% | 24 |

## Observed leaders — descriptive only, NOT validated

| Cohort | Geometry | Stop | RR | Fill | EV R/signal | EV R/filled | PF | MaxDD R | Day CI95 R/signal |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| COMMON_CLOCK | LIM_100ATR_10M | 1.5 ATR | 3.0 | 64.1% | +0.054 | +0.084 | 1.13 | 12.00 | [-0.098,+0.221] |
| AMP_ALL | LIM_100ATR_10M | 1.5 ATR | 3.0 | 64.2% | +0.051 | +0.080 | 1.13 | 14.14 | [-0.096,+0.207] |

Full configuration grid is in `GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007_CONFIGS.csv`. A favorable observed configuration is only a candidate to freeze for a later untouched forward/OOS test.
