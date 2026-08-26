# XAU_PRE_ENTRY_TICK_ACTIVITY_SURVIVAL_TRANSFER_LAB_029 — v001 REPORT

**Verdict:** `TICK_ACTIVITY_SIGNAL_TRANSFERABLE_NOT_ECONOMIC`  
**Holdout opened:** `false`

## Confirmation
- Base survival **16.23%**; N **2354**, survivors **382**
- PRICE_ONLY AUC **0.6395**
- PRICE+TICK_ACTIVITY AUC **0.6402**; delta **+0.0006**
- coverage **30.29%**, precision **23.42%**, lift **1.44x**
- survivor retention **43.72%**, failure rejection **72.31%**
- BUY precision/base **22.01%/18.14%**; SELL **25.42%/14.39%**

## Yearly transfer
|    n |   survivors |   base_rate |      auc |    brier |   threshold |   coverage |   precision |   survivor_retention |   failure_rejection |   precision_lift |   buy_base |   buy_precision |   sell_base |   sell_precision | period   |
|-----:|------------:|------------:|---------:|---------:|------------:|-----------:|------------:|---------------------:|--------------------:|-----------------:|-----------:|----------------:|------------:|-----------------:|:---------|
| 1625 |         254 |    0.156308 | 0.666805 | 0.128952 |    0.154875 |   0.289846 |    0.248408 |             0.46063  |            0.741794 |          1.58922 |   0.17662  |        0.234432 |    0.137232 |         0.267677 | 2024     |
|  729 |         128 |    0.175583 | 0.580231 | 0.152178 |    0.154875 |   0.331962 |    0.206612 |             0.390625 |            0.680532 |          1.17672 |   0.191781 |        0.193103 |    0.159341 |         0.226804 | 2025H1   |

## Score-decile diagnostic
- bottom decile survival **2.54%**
- top decile survival **27.12%**

## Starter-control economics
- selected 0.25x baseline EV **-0.0529R**
- rejected **-0.0387R**

## Frozen gates
- G0_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_ACTIVITY_ADDS: **PASS**
- G3_ACTIVITY_AUC: **PASS**
- G4_YEARLY_TRANSFER: **PASS**
- G5_YEARLY_PRECISION_LIFT: **PASS**
- G6_DIRECTION_BREADTH: **PASS**
- G7_USEFUL_OPERATIONS: **PASS**
- G8_FAILURE_REJECTION: **PASS**
- G9_STARTER_ECONOMICS: **FAIL**
- G10_DECILE_SPREAD: **PASS**

No threshold rescue, no holdout opening, no EA/live authorization.
