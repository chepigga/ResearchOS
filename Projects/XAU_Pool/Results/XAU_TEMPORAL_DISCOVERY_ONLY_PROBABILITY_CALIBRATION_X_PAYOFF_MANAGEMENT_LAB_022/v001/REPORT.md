# XAU_TEMPORAL_DISCOVERY_ONLY_PROBABILITY_CALIBRATION_X_PAYOFF_MANAGEMENT_LAB_022 — v001 REPORT

**Verdict:** `CALIBRATION_FIXES_PROBABILITIES_NOT_ECONOMICS`  
**Holdout opened:** `false`

## Discovery-only temporal calibration
- 1.5R temperature T **2.2518**
- 1.5R OOT raw logloss **0.9989** -> calibrated **0.8544**
- 1.5R OOT raw Brier **0.5504** -> calibrated **0.5167**
- 2R temperature T **2.0958**

## Confirmation probability quality — 1.5R
- RAW FULL macro AUC **0.7581**, logloss **0.9066**, Brier **0.5311**
- TEMP-CAL macro AUC **0.7596**, logloss **0.8397**, Brier **0.5108**
- relative logloss improvement **7.38%**
- relative Brier improvement **3.82%**

## Primary Confirmation — TEMP_CAL_PAYOFF / 1.5R / serial
- N **2096**, trades/week **26.91**
- EV **-0.1537R**, PF **0.619**
- TP rate **2.00%**, model-exit rate **60.97%**
- BUY **-0.1313R**, SELL **-0.1755R**
- stress10 EV **-0.2296R**
- median duration **2.0 min**
- weekly EV CI **[-0.18339211823876841, -0.12659238672274242]**

## Baseline / raw-manager comparison
- baseline serial EV **-0.1806R**, PF **0.730**
- LAB021-style RAW payoff manager serial EV **-0.1702R**, PF **0.464**
- calibrated minus baseline paired trade mean **+0.0130R**, week CI **[-0.02584144301906628, 0.04947866077067842]**
- calibrated minus raw manager paired trade mean **+0.0203R**, week CI **[-0.0060356072203701025, 0.043962098254847946]**

## Transfer / 2R
- 2024 calibrated independent EV **-0.1686R**
- 2025H1 calibrated independent EV **-0.1378R**
- 2R calibrated serial EV **-0.1454R**, PF **0.661**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_RANK_INFORMATION: **PASS**
- G3_CALIBRATION_IMPROVES: **PASS**
- G4_CALIBRATION_MATERIAL: **PASS**
- G5_CONFIRMATION_EV: **FAIL**
- G6_WEEK_CLUSTER_CI: **FAIL**
- G7_MANAGEMENT_LIFT: **FAIL**
- G8_BEATS_RAW_MANAGER: **FAIL**
- G9_TEMPORAL_TRANSFER: **FAIL**
- G10_2R_SURVIVAL: **FAIL**
- G11_DIRECTION_BREADTH: **FAIL**
- G12_PROP_DD_PROXY: **FAIL**
- G13_COST_STRESS: **FAIL**

No Confirmation calibration, no threshold rescue, no holdout opening, no EA/live authorization.
