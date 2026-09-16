# GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008

**Status: POST_DISCOVERY_LIMIT_STABILITY_MAP_NOT_OOS**

Frozen exit for every test: **SL 1.5 ATR / TP 3.0R / hard timeout 30m from original signal**.

Primary common-clock executable cohort: **N=245**. AMP-native secondary cohort: **N=279**.

Only limit depth and expiry were varied. Unfilled limits count as 0R in EV per signal.

## Primary COMMON_CLOCK grid

| Depth | Expiry | Fill | EV R/signal | EV R/fill | PF | MaxDD R | EARLY EV | LATE EV | CI95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 ATR | 3m | 64.5% | -0.058 | -0.090 | 0.87 | 33.92 | -0.004 | -0.199 | [-0.251,+0.148] |
| 0.50 ATR | 5m | 71.4% | -0.101 | -0.142 | 0.80 | 40.23 | -0.041 | -0.258 | [-0.301,+0.111] |
| 0.50 ATR | 10m | 78.4% | -0.119 | -0.151 | 0.79 | 42.23 | -0.059 | -0.272 | [-0.328,+0.104] |
| 0.50 ATR | 15m | 80.8% | -0.125 | -0.155 | 0.79 | 44.23 | -0.063 | -0.287 | [-0.341,+0.100] |
| 0.75 ATR | 3m | 50.6% | +0.050 | +0.098 | 1.15 | 9.76 | +0.056 | +0.033 | [-0.063,+0.166] |
| 0.75 ATR | 5m | 60.0% | +0.062 | +0.103 | 1.16 | 10.07 | +0.082 | +0.009 | [-0.067,+0.194] |
| 0.75 ATR | 10m | 73.5% | +0.047 | +0.065 | 1.10 | 12.47 | +0.072 | -0.018 | [-0.117,+0.214] |
| 0.75 ATR | 15m | 76.3% | +0.031 | +0.040 | 1.06 | 13.54 | +0.060 | -0.047 | [-0.141,+0.206] |
| 1.00 ATR | 3m | 41.2% | +0.072 | +0.175 | 1.28 | 8.00 | +0.061 | +0.101 | [-0.025,+0.179] |
| 1.00 ATR | 5m | 51.4% | +0.082 | +0.160 | 1.26 | 9.24 | +0.104 | +0.025 | [-0.045,+0.223] |
| 1.00 ATR | 10m | 64.1% | +0.054 | +0.084 | 1.13 | 12.00 | +0.077 | -0.007 | [-0.098,+0.221] |
| 1.00 ATR | 15m | 69.4% | +0.038 | +0.055 | 1.09 | 12.21 | +0.060 | -0.018 | [-0.116,+0.204] |
| 1.25 ATR | 3m | 30.6% | +0.019 | +0.061 | 1.09 | 11.38 | -0.008 | +0.088 | [-0.068,+0.112] |
| 1.25 ATR | 5m | 41.6% | +0.016 | +0.037 | 1.06 | 11.07 | +0.022 | -0.001 | [-0.080,+0.118] |
| 1.25 ATR | 10m | 54.7% | +0.019 | +0.034 | 1.05 | 14.79 | +0.012 | +0.036 | [-0.123,+0.172] |
| 1.25 ATR | 15m | 61.6% | -0.014 | -0.022 | 0.97 | 15.91 | -0.016 | -0.009 | [-0.158,+0.141] |
| 1.50 ATR | 3m | 22.0% | +0.018 | +0.080 | 1.12 | 12.16 | -0.043 | +0.176 | [-0.076,+0.117] |
| 1.50 ATR | 5m | 30.6% | -0.016 | -0.052 | 0.93 | 15.13 | -0.062 | +0.104 | [-0.113,+0.097] |
| 1.50 ATR | 10m | 44.5% | -0.022 | -0.050 | 0.93 | 17.58 | -0.030 | -0.003 | [-0.144,+0.107] |
| 1.50 ATR | 15m | 54.3% | -0.004 | -0.007 | 0.99 | 13.04 | -0.018 | +0.031 | [-0.134,+0.131] |

## Stable-gate candidates

| Geometry | COMMON EV | AMP EV | PF | Fill | EARLY | LATE | Positive neighbors |
|---|---:|---:|---:|---:|---:|---:|---:|
| D1.00_E5M | +0.082 | +0.080 | 1.26 | 51.4% | +0.104 | +0.025 | 4 |
| D1.00_E3M | +0.072 | +0.080 | 1.28 | 41.2% | +0.061 | +0.101 | 3 |
| D0.75_E5M | +0.062 | +0.066 | 1.16 | 60.0% | +0.082 | +0.009 | 3 |
| D0.75_E3M | +0.050 | +0.062 | 1.15 | 50.6% | +0.056 | +0.033 | 2 |

## Descriptive candidate

Observed stable-surface leader: **D1.00_E5M** — depth 1.00 ATR, expiry 5m, COMMON EV +0.082R/signal, AMP EV +0.080R/signal.

## Governance

This is not independent OOS. LAB007 already exposed part of this historical execution surface. The purpose of LAB008 is to determine whether a broad, mechanically stable limit-entry plateau exists rather than a single lucky parameter point. Any candidate must be frozen before untouched forward/OOS evaluation.
