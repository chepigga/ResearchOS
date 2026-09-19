# GC_XAU_DOMINANCE_REVERSAL_MECHANISM_AND_TIMING_LAB007D

Status: MECHANISM_TIMING_AUDIT_NOT_OOS

| Clock | Period | N | +2ATR | +3ATR | Fixed5m EV | PF | Med t+0.5 on +2 winners | Quiet | Med from last dominance | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| REV1 | TRAIN | 54 | 16.7% | 7.4% | -0.263 | 0.722 | 32.5s | 44.4% | 90.0s | FAIL |
| REV1 | VALID | 74 | 14.9% | 4.1% | -0.690 | 0.388 | 84.9s | 37.8% | 90.0s | FAIL |
| REV1 | POST_CHECK | 45 | 15.6% | 8.9% | -0.305 | 0.605 | 55.0s | 46.7% | 60.0s | FAIL |
| REV2 | TRAIN | 54 | 20.4% | 7.4% | 0.195 | 1.333 | 34.0s | 50.0% | 150.0s | FAIL |
| REV2 | VALID | 74 | 23.0% | 9.5% | -0.035 | 0.955 | 44.3s | 56.8% | 180.0s | FAIL |
| REV2 | POST_CHECK | 45 | 24.4% | 20.0% | 0.113 | 1.170 | 33.5s | 55.6% | 180.0s | FAIL |

## Mechanism medians

| Clock | Period | Impact deterioration | Change vs last dominance | Dom signals before | Rev signals so far |
|---|---|---:|---:|---:|---:|
| REV1 | TRAIN | 0.385 | 0.025 | 2.0 | 1.0 |
| REV1 | VALID | 0.344 | -0.035 | 2.0 | 1.0 |
| REV1 | POST_CHECK | 0.425 | 0.001 | 2.0 | 1.0 |
| REV2 | TRAIN | 0.443 | 0.019 | 2.0 | 2.0 |
| REV2 | VALID | 0.376 | -0.000 | 2.0 | 2.0 |
| REV2 | POST_CHECK | 0.439 | 0.073 | 2.0 | 2.0 |

Timing survivors: NONE

LIMIT_REV2 benchmarks were intentionally not approximated from the LAB005 ledger because exact post-REV2 executable tick path is required. No SL/TP optimization performed.
