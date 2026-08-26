# XAU_PRE_ENTRY_EFFORT_RESULT_VOLUME_AND_FLOW_SURVIVAL_SCREEN_LAB_028 — v001 REPORT

**Verdict:** `NO_PRE_ENTRY_SURVIVAL_SIGNAL`  
**Holdout opened:** `false`

## Data reality
- canonical real_volume nonzero rows: **0** / 1080929; therefore v001 uses tick activity, not exchange volume.
- Confirmation N **2354**, survivors **382**, base survival **16.23%**

## Confirmation model family
|    n |   survivors |   base_rate |      auc |    brier |   threshold |   coverage |   precision |   precision_lift |   survivor_retention |   failure_rejection |   buy_base |   buy_precision |   sell_base |   sell_precision | family        |   n_features |
|-----:|------------:|------------:|---------:|---------:|------------:|-----------:|------------:|-----------------:|---------------------:|--------------------:|-----------:|----------------:|------------:|-----------------:|:--------------|-------------:|
| 2354 |         382 |    0.162277 | 0.628036 | 0.137732 |    0.161855 |   0.324979 |    0.214379 |          1.32107 |             0.429319 |            0.695233 |   0.181424 |        0.219048 |    0.143927 |         0.208696 | PRICE_ONLY    |           34 |
| 2354 |         382 |    0.162277 | 0.643652 | 0.134890 |    0.149150 |   0.306712 |    0.240997 |          1.48510 |             0.455497 |            0.722110 |   0.181424 |        0.241730 |    0.143927 |         0.240122 | PLUS_ACTIVITY |           48 |
| 2354 |         382 |    0.162277 | 0.634134 | 0.137258 |    0.145042 |   0.334325 |    0.223634 |          1.37810 |             0.460733 |            0.690162 |   0.181424 |        0.241627 |    0.143927 |         0.203252 | PLUS_EFFORT   |           64 |
| 2354 |         382 |    0.162277 | 0.624665 | 0.135168 |    0.136597 |   0.450722 |    0.212064 |          1.30680 |             0.589005 |            0.576065 |   0.181424 |        0.207080 |    0.143927 |         0.217742 | PLUS_SPREAD   |           82 |
| 2354 |         382 |    0.162277 | 0.624665 | 0.135168 |    0.136597 |   0.450722 |    0.212064 |          1.30680 |             0.589005 |            0.576065 |   0.181424 |        0.207080 |    0.143927 |         0.217742 | FULL          |           82 |

## Primary FULL router
- AUC **0.6247** vs PRICE_ONLY **0.6280**; delta **-0.0034**, weekly CI **[-0.0288217525490251, 0.02485386820078757]**
- fixed Discovery top-30% threshold -> Confirmation coverage **45.07%**
- selected survival precision **21.21%** vs base **16.23%**, lift **1.31x**
- survivor retention **58.90%**, failure rejection **57.61%**
- BUY precision/base **20.71%/18.14%**; SELL **21.77%/14.39%**

## Starter economics diagnostic
- selected 0.25x frozen baseline EV **-0.0460R**
- unselected **-0.0406R**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_RANK_INFORMATION: **PASS**
- G3_ACTIVITY_ADDS: **FAIL**
- G4_OPERATIONAL_PRECISION: **FAIL**
- G5_USEFUL_RETENTION: **FAIL**
- G6_FAILURE_REJECTION: **FAIL**
- G7_BREADTH: **PASS**
- G8_STARTER_ECONOMICS: **FAIL**

No Confirmation threshold tuning, no external GC data, no holdout opening, no EA/live authorization.
