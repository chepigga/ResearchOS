# GC_M1_BUYER_BREAKOUT_INCREMENTAL_ORDERFLOW_AUDIT_005

Historical incremental-information audit; no threshold search.

| Feed/period | Price N | OF N | OF 15m | No-OF 15m | Incremental | Delta CI95 | Placebo mean inc | Placebo max inc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Rithmic TRAIN | 920 | 147 | +0.339 | +0.404 | -0.065 | [-0.440,+0.342] | +0.396 | +1.558 |
| Rithmic VALID | 877 | 115 | +0.278 | -0.210 | +0.487 | [-0.310,+1.250] | +0.698 | +2.522 |
| Rithmic LATE | 326 | 40 | +0.561 | +0.238 | +0.323 | [-0.063,+1.066] | +0.498 | +2.446 |
| Rithmic POST | 15 | 1 | +0.691 | -0.793 | +1.485 | NA | -0.906 | -0.906 |
| Rithmic PRE_DISCOVERY | 1797 | 262 | +0.312 | +0.100 | +0.212 | [-0.181,+0.641] | +0.535 | +1.987 |
| Rithmic FULL | 2138 | 303 | +0.346 | +0.115 | +0.231 | [-0.106,+0.602] | +0.535 | +1.900 |
| AMP TRAIN | 659 | 108 | +0.532 | +0.074 | +0.458 | [+0.069,+0.883] | +0.473 | +1.868 |
| AMP VALID | 880 | 120 | +0.320 | -0.208 | +0.527 | [-0.236,+1.252] | +0.731 | +2.453 |
| AMP LATE | 326 | 37 | +0.319 | +0.231 | +0.088 | [-0.485,+0.845] | +0.498 | +1.602 |
| AMP POST | 129 | 16 | +0.303 | -0.244 | +0.547 | [-0.020,+1.319] | -0.205 | +2.368 |
| AMP PRE_DISCOVERY | 1539 | 228 | +0.420 | -0.089 | +0.509 | [+0.089,+0.944] | +0.600 | +2.213 |
| AMP FULL | 1994 | 281 | +0.401 | -0.045 | +0.446 | [+0.083,+0.825] | +0.548 | +1.839 |

## Interpretation

A useful order-flow edge should show positive synchronous incremental return versus the same price-breakout complement, preferably larger than typical shifted-flow placebo alignment. Because the candidate was discovered historically, even a strong result here creates a **frozen historical candidate**, not a validated OOS strategy.
