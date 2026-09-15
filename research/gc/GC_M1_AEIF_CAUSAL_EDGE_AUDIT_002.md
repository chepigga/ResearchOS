# GC_M1_AEIF_CAUSAL_EDGE_AUDIT_002

Fixed LAB001 M1 selector. No threshold search. This audit removes close-fill/confirmation lookahead from the information-entry clock.

## Rithmic raw — B next-open

| Window | N | 5m EV | 5m CI95 | 15m EV | 15m CI95 |
|---|---:|---:|---:|---:|---:|
| PRE_DISCOVERY | 383 | +0.042 | [-0.142,+0.216] | +0.139 | [-0.212,+0.484] |
| DISCOVERY_CLOCK | 54 | +0.163 | [-0.117,+0.476] | +0.271 | [-0.305,+0.863] |
| POST_DISCOVERY | 1 | -0.655 | NA | -2.473 | NA |
| NON_DISCOVERY | 384 | +0.041 | [-0.138,+0.214] | +0.132 | [-0.224,+0.469] |
| FULL | 438 | +0.056 | [-0.110,+0.211] | +0.149 | [-0.156,+0.463] |

## Rithmic raw — D next-open after confirmation

| Window | N | 5m EV | 5m CI95 | 15m EV | 15m CI95 |
|---|---:|---:|---:|---:|---:|
| PRE_DISCOVERY | 207 | +0.066 | [-0.172,+0.312] | +0.122 | [-0.329,+0.550] |
| DISCOVERY_CLOCK | 31 | +0.237 | [-0.081,+0.887] | +0.633 | [+0.199,+1.233] |
| POST_DISCOVERY | 0 | NA | NA | NA | NA |
| NON_DISCOVERY | 207 | +0.066 | [-0.172,+0.312] | +0.122 | [-0.329,+0.550] |
| FULL | 238 | +0.088 | [-0.120,+0.305] | +0.189 | [-0.194,+0.569] |

## AMP/CQG raw — B next-open

| Window | N | 5m EV | 5m CI95 | 15m EV | 15m CI95 |
|---|---:|---:|---:|---:|---:|
| PRE_DISCOVERY | 341 | -0.024 | [-0.221,+0.166] | +0.115 | [-0.241,+0.462] |
| DISCOVERY_CLOCK | 55 | +0.368 | [+0.063,+0.672] | +0.341 | [-0.210,+0.768] |
| POST_DISCOVERY | 45 | -0.089 | [-0.972,+0.173] | -0.357 | [-2.837,+0.015] |
| NON_DISCOVERY | 386 | -0.031 | [-0.207,+0.138] | +0.059 | [-0.261,+0.366] |
| FULL | 441 | +0.018 | [-0.145,+0.184] | +0.095 | [-0.195,+0.390] |

## AMP/CQG raw — D next-open after confirmation

| Window | N | 5m EV | 5m CI95 | 15m EV | 15m CI95 |
|---|---:|---:|---:|---:|---:|
| PRE_DISCOVERY | 186 | +0.023 | [-0.226,+0.282] | +0.110 | [-0.372,+0.573] |
| DISCOVERY_CLOCK | 34 | +0.465 | [+0.238,+0.827] | +0.813 | [+0.161,+1.597] |
| POST_DISCOVERY | 23 | -0.578 | [-0.676,-0.471] | -0.746 | [-1.108,-0.352] |
| NON_DISCOVERY | 209 | -0.043 | [-0.274,+0.208] | +0.015 | [-0.440,+0.470] |
| FULL | 243 | +0.028 | [-0.185,+0.260] | +0.128 | [-0.293,+0.545] |

## Interpretation

PRE_DISCOVERY is the most important historical falsification slice because it predates the original 6–11 Sep ATAS discovery. The two feeds are representations of largely the same GC market and therefore are feed-parity evidence, not two independent market samples. Day-cluster bootstrap CIs are diagnostic, not a substitute for new forward history.
