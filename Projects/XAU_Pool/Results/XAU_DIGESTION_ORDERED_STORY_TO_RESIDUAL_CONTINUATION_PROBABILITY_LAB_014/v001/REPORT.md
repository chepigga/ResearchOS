# XAU_DIGESTION_ORDERED_STORY_TO_RESIDUAL_CONTINUATION_PROBABILITY_LAB_014 — v001 REPORT

**Verdict:** `NO_RESIDUAL_CONTINUATION_EDGE`  
**Holdout opened:** `false`

## Residual probability — Confirmation
- N: **2354**, TP1.5 base rate: **0.333**
- LOCATION_SNAPSHOT AUC: **0.5026**
- ORDERED_STORY AUC: **0.4976**
- ORDERED_STORY_PLUS_ACTIVITY AUC: **0.4847**
- ordered - snapshot: **-0.0050**, weekly CI **[-0.024395950591319236, 0.020308452894148395]**
- p>=0.55 coverage: **0.64%**, TP precision: **40.00%**, rejected TP rate: **33.26%**, gap **+6.74 pp**

## Executable economics — Confirmation / 1.5R / serial
- N: **15**, trades/week **0.21**
- EV **-0.0433R**, PF **0.931**, TP **40.00%**
- BUY **0.4659R**, SELL **-0.2979R**
- max DD **5.15R**, worst day **-1.06R**
- +$0.10 stress EV **-0.1299R**
- weekly mean-R CI **[-0.6521697099939839, 0.6802907133510255]**

## Baseline / lift
- all-digestion serial EV **-0.1806R**, PF **0.730**
- routed-minus-baseline weekly diff **0.1807R**, CI **[0.07169338326908152, 0.29391139307351855]**
- Discovery-2023 routed independent EV **-0.1946R**
- Confirmation routed independent EV **-0.0433R**
- Confirmation routed 2R EV **0.1567R**, PF **1.251**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **FAIL**
- G2_RESIDUAL_AUC: **FAIL**
- G3_SEQUENCE_INCREMENTAL: **FAIL**
- G4_SELECTION_QUALITY: **FAIL**
- G5_CONFIRMATION_EV: **FAIL**
- G6_WEEK_CLUSTER_CI: **FAIL**
- G7_DISCOVERY_TRANSFER: **FAIL**
- G8_2R_SURVIVAL: **PASS**
- G9_DIRECTION_BREADTH: **FAIL**
- G10_PROP_DD_PROXY: **PASS**
- G11_COST_STRESS: **FAIL**
- G12_ROUTER_LIFT: **PASS**

No holdout opening, EA authorization, or live allocation is authorized by LAB014.

## Post-hoc representation diagnostic — does not change verdict

The primary linear ORDERED_STORY model is near chance, but this is not merely a linear-model failure. Using the same frozen causal feature representation, post-hoc nonlinear diagnostics produce only:

- Random Forest OOS AUC: **0.5223**
- Gradient Boosting OOS AUC: **0.5227**

Thus the current hand-engineered storyline representation contains little transferable information about residual TP1.5 from the digestion entry.

LAB013 `p_reaccel` is also non-monotonic with residual economics. In the highest reacceleration-probability decile, TP1.5 rate is only about **29.7%** and mean EV about **-0.30R**, while the setup is already much farther through its directional rebound.

Interpretation: LAB014 validates the economic target but rejects the current compact representation as sufficient. A rational next test, if pursued, is the **raw chronological path representation** from break through digestion close (signed-distance trajectory / tempo / pullback attempts), compared OOS against these handcrafted summaries, while keeping the same frozen residual TP1.5 target and entry.
