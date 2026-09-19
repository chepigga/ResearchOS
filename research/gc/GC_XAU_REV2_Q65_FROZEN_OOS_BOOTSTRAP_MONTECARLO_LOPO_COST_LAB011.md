# GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011

Status: FROZEN_VALIDATION_NOT_PRISTINE_OOS

Frozen: Q65 impulse + Q65 aligned volume; entry REV2+30s; SL 2.25 ATR; TP 4.50 ATR; timeout 300s.

POST_CHECK is not pristine OOS because it was inspected in prior discovery labs.

## Exact FTMO metals commission conversion

- Commission per side: 0.000700% of notional
- Commission R/trade: median 0.0112, mean 0.0121, range 0.0034–0.0286

| Split | N | EV R | PF | CumR | WR | MaxDD R | DD% @0.25 | Streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 8 | 0.379 | 4.000 | 3.035 | 75.0% | 1.010 | 0.253% | 1 |
| VALID | 15 | 0.366 | 3.912 | 5.488 | 80.0% | 1.885 | 0.471% | 3 |
| POST_CHECK | 8 | 0.070 | 1.170 | 0.556 | 50.0% | 2.025 | 0.506% | 2 |
| FULL | 31 | 0.293 | 2.474 | 9.080 | 71.0% | 2.025 | 0.506% | 3 |

## Bootstrap

- IID: P(EV>0) 0.979; 95% CI [0.009, 0.585] R/trade
- Block-3: P(EV>0) 0.983; 95% CI [0.027, 0.617] R/trade

## Monte Carlo path risk

- MaxDD median 2.045R; p95 3.590R; p99 4.260R
- p95 DD at 0.25% risk: 0.898%
- Losing streak median 2.0; p95 4.0; p99 5.0

## Leave-one-period-out

- ISO weeks tested: 7
- Minimum remaining EV after removing any week: 0.207R
- Minimum remaining PF after removing any week: 1.876
- Remaining EV positive for every removed week: True

- Leave TRAIN: N=23, EV=0.263R, PF=2.174, CumR=6.045
- Leave VALID: N=16, EV=0.224R, PF=1.840, CumR=3.592
- Leave POST_CHECK: N=23, EV=0.371R, PF=3.943, CumR=8.524

True independent OOS requires fresh future REV2 events collected after this freeze.
