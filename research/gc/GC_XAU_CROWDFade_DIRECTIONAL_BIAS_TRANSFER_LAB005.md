# GC_XAU_CROWDFade_DIRECTIONAL_BIAS_TRANSFER_LAB005

Bias-only audit. XAU mid-price; no entry/spread/SL/TP optimization.

| State | Gate | TrN | TrAcc3 | TrEV3 | TrAcc5 | TrEV5 | VaN | VaAcc3 | VaEV3 | VaAcc5 | VaEV5 | PostAcc5 | PostEV5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | FAIL | 25 | 44.0% | -0.043 | 56.0% | +0.048 | 41 | 39.0% | -0.245 | 45.0% | -0.416 | 35.3% | -0.525 |
| DIVERGE_EARLY | FAIL | 12 | 66.7% | +0.186 | 50.0% | +0.216 | 14 | 64.3% | +0.625 | 57.1% | +0.170 | 41.7% | -0.484 |
| CROWD_PERSISTS | FAIL | 10 | 20.0% | -0.661 | 50.0% | -0.613 | 16 | 18.8% | -0.788 | 33.3% | -0.859 | 33.3% | -0.385 |
| REVERSAL_CONFIRM | FAIL | 2 | 50.0% | +0.808 | 100.0% | +1.181 | 6 | 50.0% | -0.266 | 66.7% | -0.166 | 0.0% | -0.530 |

## Full horizon profile

| State | 1m | 3m | 5m | 10m | 15m | First +0.25 side (FULL) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | +0.026 | -0.178 | -0.297 | -0.328 | -0.135 | 60.2% |
| DIVERGE_EARLY | +0.341 | +0.248 | -0.022 | -0.015 | -0.107 | 92.1% |
| CROWD_PERSISTS | -0.359 | -0.683 | -0.720 | -0.636 | +0.040 | 13.8% |
| REVERSAL_CONFIRM | +0.271 | -0.053 | +0.030 | -0.164 | -0.364 | 60.0% |

Candidates: NONE

POST_CHECK was not used for candidate selection. This LAB tests directional information only, not an executable strategy.
