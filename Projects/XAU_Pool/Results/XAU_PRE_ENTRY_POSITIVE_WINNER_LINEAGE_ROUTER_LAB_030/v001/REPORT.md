# XAU_PRE_ENTRY_POSITIVE_WINNER_LINEAGE_ROUTER_LAB_030 — v001 REPORT

**Verdict:** `NO_PRE_ENTRY_POSITIVE_LINEAGE_SIGNAL`  
**Holdout opened:** `false`

## Target parity — Confirmation
- EARLY_TP15 **77**
- DOUBLE_NO_RETURN_CONFIRMED **118**
- positive total **195** / 2354 = **8.28%**

## Confirmation router
- PRICE_ONLY AUC **0.6175**
- PRICE+TICK_ACTIVITY AUC **0.6091**, delta **-0.0084**
- coverage **21.03%**, precision **12.32%**, lift **1.49x**
- positive retention **31.28%**, negative rejection **79.90%**
- BUY precision/base **10.98%/8.51%**, SELL **13.75%/8.07%**

## Yearly transfer
|    n |   positives |   base_rate |      auc |     brier |   threshold |   coverage |   precision |   retention |   negative_rejection |   precision_lift |   buy_base |   buy_precision |   sell_base |   sell_precision | period   |
|-----:|------------:|------------:|---------:|----------:|------------:|-----------:|------------:|------------:|---------------------:|-----------------:|-----------:|----------------:|------------:|-----------------:|:---------|
| 1625 |         139 |   0.0855385 | 0.641537 | 0.0791152 |   0.0801133 |   0.198154 |   0.142857  |    0.330935 |             0.814266 |          1.67009 |  0.0876747 |       0.11976   |   0.0835322 |        0.167742  | 2024     |
|  729 |          56 |   0.0768176 | 0.531363 | 0.0742721 |   0.0801133 |   0.237311 |   0.0867052 |    0.267857 |             0.76523  |          1.12872 |  0.0794521 |       0.0909091 |   0.0741758 |        0.0823529 | 2025H1   |

## Subtype retention
| subtype                    |   n |   selected_n |   retention |   baseline_ev |
|:---------------------------|----:|-------------:|------------:|--------------:|
| DOUBLE_NO_RETURN_CONFIRMED | 118 |           47 |    0.398305 |      0.446367 |
| EARLY_TP15                 |  77 |           14 |    0.181818 |      1.46272  |

## Economic selection
- selected full baseline EV **-0.1858R**, rejected **-0.1685R**
- selected 0.25x starter EV **-0.0464R**, rejected **-0.0421R**
- top decile positive-lineage rate **11.02%**, bottom **2.54%**

## Frozen gates
- G0_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_RANK_INFORMATION: **PASS**
- G3_ACTIVITY_ADDS: **FAIL**
- G4_OPERATIONAL_PRECISION: **FAIL**
- G5_USEFUL_RETENTION: **FAIL**
- G6_YEARLY_TRANSFER: **FAIL**
- G7_BREADTH: **PASS**
- G8_SUBTYPE_RETENTION: **FAIL**
- G9_ECONOMIC_SELECTION: **FAIL**
- G10_DECILE_SPREAD: **FAIL**

No threshold rescue, no feature-family rescue, no holdout opening, no EA/live authorization.
