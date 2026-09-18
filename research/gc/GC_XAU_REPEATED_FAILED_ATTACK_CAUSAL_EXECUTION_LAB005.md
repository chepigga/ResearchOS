# GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005

Status: CAUSAL_EXECUTION_AUDIT_NOT_OOS

## Causal timing — no future XAU information in signal

| Subset | Period | N | +2ATR<=5m | +3ATR<=5m | med t0.25 | med t0.50 | med t1.0 | med t0.50 on +2 winners |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | TRAIN | 5017 | 19.6% | 7.8% | 21.1s | 50.1s | 105.0s | 38.0s |
| ALL | VALID | 6433 | 20.0% | 7.4% | 22.1s | 52.6s | 104.8s | 38.2s |
| ALL | POST_CHECK | 3756 | 19.7% | 7.4% | 22.9s | 51.9s | 106.2s | 37.7s |
| QUIET | TRAIN | 2729 | 18.8% | 6.8% | 22.8s | 54.6s | 111.3s | 40.4s |
| QUIET | VALID | 3473 | 19.7% | 6.9% | 23.3s | 53.5s | 105.8s | 39.8s |
| QUIET | POST_CHECK | 2059 | 19.3% | 7.3% | 24.9s | 54.6s | 111.1s | 40.7s |

## QUIET_START execution

| Variant | Period | Fills | Fill% | Hold300 EV ATR | G15 EV/PF | G20 EV/PF | Missed +2 winners |
|---|---|---:|---:|---:|---:|---:|---:|
| MARKET_NOW | TRAIN | 2729 | 100.0% | -0.254 | -0.421/+0.449 | -0.416/+0.476 | 0.0% |
| MARKET_NOW | VALID | 3473 | 100.0% | -0.170 | -0.370/+0.502 | -0.349/+0.548 | 0.0% |
| MARKET_NOW | POST_CHECK | 2059 | 100.0% | -0.199 | -0.456/+0.415 | -0.440/+0.452 | 0.0% |
| LIMIT_005_15S | TRAIN | 1984 | 72.7% | -0.285 | -0.519/+0.355 | -0.506/+0.388 | 31.8% |
| LIMIT_005_15S | VALID | 2553 | 73.5% | -0.227 | -0.440/+0.431 | -0.429/+0.464 | 33.9% |
| LIMIT_005_15S | POST_CHECK | 1476 | 71.7% | -0.237 | -0.568/+0.311 | -0.567/+0.330 | 34.7% |
| LIMIT_005_30S | TRAIN | 2184 | 80.0% | -0.311 | -0.532/+0.343 | -0.518/+0.376 | 27.1% |
| LIMIT_005_30S | VALID | 2843 | 81.9% | -0.230 | -0.437/+0.434 | -0.424/+0.469 | 26.8% |
| LIMIT_005_30S | POST_CHECK | 1639 | 79.6% | -0.246 | -0.571/+0.308 | -0.565/+0.332 | 27.9% |
| LIMIT_010_15S | TRAIN | 1643 | 60.2% | -0.298 | -0.522/+0.353 | -0.500/+0.394 | 45.7% |
| LIMIT_010_15S | VALID | 2082 | 59.9% | -0.208 | -0.461/+0.410 | -0.442/+0.452 | 47.1% |
| LIMIT_010_15S | POST_CHECK | 1215 | 59.0% | -0.250 | -0.597/+0.285 | -0.587/+0.313 | 48.7% |
| LIMIT_010_30S | TRAIN | 1942 | 71.2% | -0.312 | -0.525/+0.349 | -0.504/+0.389 | 37.9% |
| LIMIT_010_30S | VALID | 2511 | 72.3% | -0.207 | -0.447/+0.423 | -0.428/+0.465 | 37.7% |
| LIMIT_010_30S | POST_CHECK | 1456 | 70.7% | -0.249 | -0.608/+0.276 | -0.599/+0.301 | 38.2% |

Historical viable candidates: NONE

No signal threshold, session filter, entry depth, expiry, SL, TP, or timeout was optimized after seeing outcomes.
