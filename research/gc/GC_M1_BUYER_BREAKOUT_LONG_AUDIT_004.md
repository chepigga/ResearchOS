# GC_M1_BUYER_BREAKOUT_LONG_AUDIT_004

Frozen after bounded discovery 003. **Historical candidate audit, not OOS.**

Candidate: extreme buyer aggression (prior240 delta Q90 + buy-volume Q75), high reaches prior20 high, bullish body, top-quartile close, next M1 open LONG.

| Feed/period | N | 5m EV | 15m EV | 15m day-CI95 | Price-no-OF 15m | Mirror SHORT 15m |
|---|---:|---:|---:|---:|---:|---:|
| Rithmic TRAIN | 146 | +0.200 | +0.339 | [-0.142,+0.779] | +0.404 | -0.078 |
| Rithmic VALID | 115 | +0.039 | +0.278 | [-0.625,+1.069] | -0.210 | -0.113 |
| Rithmic LATE | 40 | +0.028 | +0.561 | [+0.179,+0.935] | +0.238 | -0.206 |
| Rithmic POST | 1 | +1.279 | +0.691 | NA | -0.793 | +0.215 |
| Rithmic PRE_DISCOVERY | 261 | +0.129 | +0.312 | [-0.152,+0.752] | +0.100 | -0.095 |
| Rithmic FULL | 302 | +0.120 | +0.346 | [-0.067,+0.718] | +0.115 | -0.111 |
| AMP TRAIN | 108 | +0.239 | +0.532 | [-0.071,+1.071] | +0.074 | +0.047 |
| AMP VALID | 120 | +0.063 | +0.320 | [-0.510,+1.059] | -0.208 | +0.021 |
| AMP LATE | 37 | -0.127 | +0.319 | [-0.111,+0.686] | +0.231 | +0.088 |
| AMP POST | 14 | +0.236 | +0.303 | [-0.229,+0.911] | -0.244 | +1.452 |
| AMP PRE_DISCOVERY | 228 | +0.147 | +0.420 | [-0.085,+0.891] | -0.089 | +0.032 |
| AMP FULL | 279 | +0.116 | +0.401 | [-0.020,+0.795] | -0.045 | +0.144 |

## Feed event parity

Candidate common-clock event Jaccard: **0.858** (247 exact matches; R 269, AMP 266).

## Interpretation

The key question is whether buyer order flow adds information beyond the same bullish local-high price pattern. A positive candidate with a near-zero/negative PRICE_BREAKOUT_NO_OF complement is stronger evidence for a genuine order-flow selector. Mirror SHORT is reported to expose directional asymmetry rather than hiding it.
