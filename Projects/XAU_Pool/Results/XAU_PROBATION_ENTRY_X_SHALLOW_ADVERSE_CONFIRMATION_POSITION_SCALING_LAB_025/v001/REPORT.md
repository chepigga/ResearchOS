# XAU_PROBATION_ENTRY_X_SHALLOW_ADVERSE_CONFIRMATION_POSITION_SCALING_LAB_025 — v001 REPORT

**Verdict:** `PROBATION_SELECTS_HEALTH_BUT_EXECUTION_NOT_POSITIVE`  
**Holdout opened:** `false`

## LAB023 signal parity
- Confirmation same-side 0.10ATR event: **1839**
- no-event: **515**
- exact parity expected 1839 / 515: **True**

## Primary Confirmation — starter 25% -> promote to 100% after healthy 5m probation
- N **2276**, trades/week **29.22**
- EV **-0.0715R**, PF **0.569**, TP **14.32%**
- promotion rate **16.43%**, mean risk budget used **0.373R**
- risk-efficiency **-0.1917 R per risk-budget-R**
- BUY **-0.0893R**, SELL **-0.0544R**
- stress10 **-0.0970R**
- max DD **165.17R**, worst day **-3.39R**
- weekly EV CI **[-0.08391421675902286, -0.055548230088653706]**

## Baseline / lift
- FULL_IMMEDIATE serial EV **-0.1806R**, PF **0.730**, max DD **375.41R**
- staged-minus-full paired weekly mean **+0.1038R**, CI **[0.06111111200003096, 0.14622022638455556]**
- STARTER_ONLY_25 independent EV **-0.0430R**, risk-efficiency **-0.1721**

## Promotion selectivity
 promoted    n  baseline_ev  baseline_tp  staged_ev  mean_p_accept
    False 1972    -0.259663     0.299189  -0.071576       0.843087
     True  382     0.279799     0.507853  -0.064088       0.840473

## Actual promoted cohort
- N **382**, staged EV **-0.0641R**, baseline EV **+0.2798R**, TP **50.79%**

## Transfer / 2R
- Discovery EV **-0.0504R**
- Confirmation 2R EV **-0.0609R**, PF **0.662**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_POSITIVE_ECONOMICS: **FAIL**
- G3_WEEKLY_ROBUSTNESS: **FAIL**
- G4_RISK_EFFICIENCY: **FAIL**
- G5_PROMOTION_SELECTIVITY: **PASS**
- G6_PROMOTED_EXECUTION: **FAIL**
- G7_DISCOVERY_TRANSFER: **FAIL**
- G8_DIRECTION_BREADTH: **FAIL**
- G9_2R_SURVIVAL: **FAIL**
- G10_COST_STRESS: **FAIL**
- G11_PROP_DD_PROXY: **PASS**
- G12_BEATS_FULL_IMMEDIATE: **PASS**

No sensitivity rescue, no holdout opening, no EA/live authorization.
