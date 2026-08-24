# XAU_BIAS_X_ROOM_TO_RUN_AND_DESTINATION_CONTEXT_LAB_017 — v001 REPORT

**Verdict:** `NO_BIAS_X_ROOM_RESIDUAL_EDGE`  
**Holdout opened:** `false`

## OOS residual prediction — Confirmation
- N **2354**, TP1.5 base rate **0.333**
- BIAS_LOCATION AUC **0.5099**
- ROOM_DESTINATION_ONLY AUC **0.5168**
- BIAS_X_ROOM AUC **0.5160**
- BIAS_X_ROOM_PLUS_FIXED_RAW AUC **0.5250**
- BIAS_X_ROOM minus location **+0.0061**, weekly CI **[-0.029641452786814616, 0.034460071364525974]**

## Primary p>=0.55 selection
- coverage **7.26%**
- TP1.5 precision **37.43%**
- rejected TP1.5 **32.98%**
- gap **+4.44 pp**, weekly CI **[None, None]**

## Executable economics — Confirmation / 1.5R / serial
- N **160**, trades/week **2.07**
- EV **-0.0964R**, PF **0.850**, TP **36.88%**
- BUY **-0.2363R**, SELL **+0.0746R**
- max DD **27.15R**, worst day **-2.13R**, stress10 **-0.1692R**
- weekly EV CI **[-0.3391161465745369, 0.08201926094861316]**

## Baseline / transfer
- baseline serial EV **-0.1806R**, PF **0.730**
- routed-minus-baseline weekly **+0.0675R**, CI **[-0.1117772333724804, 0.24697041623655397]**
- Discovery-2023 routed independent EV **+0.0771R**
- Confirmation routed independent EV **-0.0840R**
- Confirmation 2R serial EV **-0.0655R**

## Transparent room diagnostic
- clear=0: N 2224, TP1.5 33.50%, EV -0.1672R, mean nearest room 0.171 ATR
- clear=1: N 130, TP1.5 30.00%, EV -0.2564R, mean nearest room 1.197 ATR

## Nearest destination types
- M15_SWING: N 1438, TP1.5 32.82%, EV -0.1761R, room 0.183 ATR
- H1_SWING: N 436, TP1.5 36.70%, EV -0.0911R, room 0.208 ATR
- CURRENT_SESSION: N 262, TP1.5 33.59%, EV -0.1929R, room 0.398 ATR
- VWAP: N 184, TP1.5 31.52%, EV -0.2254R, room 0.342 ATR
- PREV_SESSION: N 33, TP1.5 15.15%, EV -0.6563R, room 0.269 ATR
- OPEN_SPACE: N 1, TP1.5 100.00%, EV +1.4668R, room 5.000 ATR

## Group permutation importance
- BIAS_LOCATION: AUC drop +0.0141
- H1_ROOM: AUC drop +0.0077
- H1_STRUCTURE: AUC drop +0.0052
- SESSION_ROOM: AUC drop +0.0050
- M15_ROOM: AUC drop +0.0018
- M15_STRUCTURE: AUC drop +0.0005
- ROOM_AGGREGATE: AUC drop +0.0003
- VWAP_ROOM: AUC drop -0.0022

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **FAIL**
- G2_ROOM_RESIDUAL_AUC: **FAIL**
- G3_ROOM_ADDS_OVER_LOCATION: **FAIL**
- G4_SELECTION_QUALITY: **FAIL**
- G5_CONFIRMATION_EV: **FAIL**
- G6_WEEK_CLUSTER_CI: **FAIL**
- G7_DISCOVERY_TRANSFER: **FAIL**
- G8_2R_SURVIVAL: **FAIL**
- G9_DIRECTION_BREADTH: **FAIL**
- G10_PROP_DD_PROXY: **FAIL**
- G11_COST_STRESS: **FAIL**
- G12_ROUTER_LIFT: **FAIL**

No holdout opening, EA authorization or live allocation is authorized by LAB017.