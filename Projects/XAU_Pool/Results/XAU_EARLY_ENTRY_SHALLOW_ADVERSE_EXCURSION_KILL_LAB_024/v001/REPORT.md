# XAU_EARLY_ENTRY_SHALLOW_ADVERSE_EXCURSION_KILL_LAB_024 — v001 REPORT

**Verdict:** `NO_SHALLOW_ADVERSE_EXCURSION_KILL_EDGE`  
**Holdout opened:** `false`

## Primary Confirmation — 0.10 ATR adverse-excursion kill / 1.5R / serial
- N **2130**, trades/week **27.34**
- EV **-0.1830R**, PF **0.213**, TP **0.33%**
- kill rate **74.41%**
- BUY **-0.1827R**, SELL **-0.1833R**
- max DD **390.63R**, worst day **-3.79R**
- stress10 **-0.2590R**
- weekly EV CI **[-0.19800900161124987, -0.16701014232662054]**

## Baseline / paired lift
- frozen baseline serial EV **-0.1806R**, PF **0.730**
- paired manager-minus-baseline **-0.0162R**, weekly CI **[-0.061411747281970346, 0.030947895593379182]**
- Discovery independent EV **-0.1924R**
- Confirmation independent EV **-0.1883R**
- Confirmation 2R serial EV **-0.1816R**, PF **0.219**

## Trigger cohort
- TRIGGERED: N **1770**, baseline EV **-0.2325R**, baseline TP **31.24%**, managed EV **-0.2549R**, delta **-0.0225R**
- NOT_TRIGGERED: N **584**, baseline EV **+0.0108R**, baseline TP **39.55%**, managed EV **+0.0135R**, delta **+0.0027R**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_CONFIRMATION_EV: **FAIL**
- G3_WEEK_CLUSTER_CI: **FAIL**
- G4_MANAGEMENT_LIFT: **FAIL**
- G5_SPLIT_TRANSFER: **FAIL**
- G6_DIRECTION_BREADTH: **FAIL**
- G7_2R_SURVIVAL: **FAIL**
- G8_COST_STRESS: **FAIL**
- G9_PROP_DD_PROXY: **FAIL**
- G10_TRIGGERED_COHORT_SAVING: **FAIL**
- G11_NON_TRIGGERED_RETENTION: **PASS**

No threshold rescue, holdout opening, EA authorization or live allocation is authorized by LAB024.
