# XAU_DIGESTION_ORDERED_PATH_TO_REACCEL_PROBABILITY_LAB_013 — v001 REPORT

**Verdict:** `NO_EARLY_REACCEL_PROBABILITY_EDGE`  
**Holdout opened:** `false`

## OOS reacceleration probability — Confirmation
- N: **2354**, target base rate: **0.493**
- SNAPSHOT AUC: **0.6865**
- ORDERED_PRICE_STORY AUC: **0.6957**
- ORDERED_PRICE_VOLUME_STORY AUC: **0.6954**
- ordered - snapshot AUC: **+0.0092**, weekly CI **[-0.00246, +0.01833]**
- p>=0.70 coverage: **7.65%**, precision: **76.11%**, rejected rate: **47.06%**, gap: **+29.05 pp**
- selection-gap weekly CI: **[+13.62 pp, +44.05 pp]**

## Early executable economics — Confirmation / 1.5R / serial
- N: **173**, trades/week: **2.24**
- EV: **-0.2957R**, PF: **0.595**, TP: **30.06%**
- BUY EV: **-0.2990R**, SELL EV: **-0.2926R**
- max DD: **55.35R**, worst day: **-3.10R**
- +$0.10 stress EV: **-0.3899R**
- weekly mean-R CI: **[-0.5944, -0.2084]R**

## Baseline / transfer
- all-digestion serial EV: **-0.1806R**, PF **0.730**
- routed-minus-baseline weekly diff: **-0.1888R**, CI **[-0.3530, -0.0214]**
- Discovery-2023 selected independent EV: **-0.1771R**
- Confirmation selected independent EV: **-0.2414R**
- Confirmation 2R serial EV: **-0.2822R**, PF **0.635**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_MODEL_POWER: **FAIL**
- G2_REACCEL_AUC: **PASS**
- G3_SEQUENCE_INCREMENTAL: **FAIL**
- G4_SELECTION_PRECISION: **PASS**
- G5_CONFIRMATION_EV: **FAIL**
- G6_WEEK_CLUSTER_CI: **FAIL**
- G7_DISCOVERY_TRANSFER: **FAIL**
- G8_2R_SURVIVAL: **FAIL**
- G9_DIRECTION_BREADTH: **FAIL**
- G10_PROP_DD_PROXY: **FAIL**
- G11_COST_STRESS: **FAIL**
- G12_ROUTER_LIFT: **FAIL**

No holdout opening, EA authorization, or live allocation is authorized by LAB013.

## Post-hoc target/timing diagnostic — does not change verdict

The probability model predicts the frozen MICRO_REACCEL event, but high predicted probability is not equivalent to good residual entry economics.

- all true MICRO_REACCEL cases: earlier digestion entry EV **+0.3541R**;
- true MICRO_REACCEL cases with `p_reaccel>=0.70`: earlier entry EV **-0.0251R**;
- true MICRO_REACCEL cases rejected by the model: earlier entry EV **+0.4049R**;
- false positives inside `p_reaccel>=0.70`: earlier entry EV **-0.9306R**.

The selected true-positive cohort is already much farther through its rebound at the decision clock: median signed close distance is about **1.71 ATR** beyond the broken level and the digestion block itself has already gained about **+0.42 ATR** directionally, versus about **0.96 ATR** and near-zero block change for rejected true-reaccel cases.

Therefore LAB013 identifies a target mismatch: predicting that a micro re-acceleration event will occur is not the same as predicting that sufficient **residual continuation from the current entry location** remains. The next research target should be joint/economic, not merely `REACCEL_SOON`.
