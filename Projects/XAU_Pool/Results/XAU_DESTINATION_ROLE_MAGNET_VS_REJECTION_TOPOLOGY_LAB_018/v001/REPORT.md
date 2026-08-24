# XAU_DESTINATION_ROLE_MAGNET_VS_REJECTION_TOPOLOGY_LAB_018 — v001 REPORT

**Verdict:** `NO_DESTINATION_ROLE_RESIDUAL_EDGE`  
**Holdout opened:** `false`

## OOS residual prediction — Confirmation
- N **2354**, TP1.5 base rate **0.333**
- BIAS_X_ROOM_BASELINE AUC **0.5160**
- DESTINATION_TOPOLOGY_ONLY AUC **0.4951**
- BIAS_X_DESTINATION_TOPOLOGY AUC **0.5224**
- TOPOLOGY_PLUS_FIXED_RAW AUC **0.5248**
- topology minus LAB017 baseline **+0.0064**, weekly CI **[-0.01067290490606472, 0.033227925948666796]**

## Primary p>=0.55 selection
- coverage **5.14%**
- TP1.5 precision **29.75%**
- rejected TP1.5 **33.50%**
- gap **-3.75 pp**, weekly CI **[None, None]**

## Executable economics — Confirmation / 1.5R / serial
- N **116**, trades/week **1.56**
- EV **-0.2591R**, PF **0.632**, TP **28.45%**
- BUY **-0.2550R**, SELL **-0.2637R**
- max DD **41.69R**, worst day **-2.13R**, stress10 **-0.3282R**
- weekly EV CI **[-0.4755326187930762, 0.005992501959273956]**

## Baseline / transfer
- baseline serial EV **-0.1806R**, PF **0.730**
- routed-minus-baseline weekly **+0.0010R**, CI **[-0.19006099625382997, 0.1939698754353805]**
- Discovery-2023 routed independent EV **-0.1431R**
- Confirmation routed independent EV **-0.2292R**
- Confirmation 2R serial EV **-0.1890R**

## Destination roles
- MIXED: N 835, TP1.5 31.62%, EV -0.2163R, mean p 0.353
- REJECTION_DOMINANT: N 719, TP1.5 32.96%, EV -0.1604R, mean p 0.317
- FRESH: N 630, TP1.5 35.40%, EV -0.1370R, mean p 0.344
- ACCEPTANCE_DOMINANT: N 120, TP1.5 33.33%, EV -0.1890R, mean p 0.316
- REPEATED_MAGNET: N 50, TP1.5 40.00%, EV -0.0043R, mean p 0.347

## TP placement
- TP_BEYOND_DEST: N 2148, TP1.5 33.05%, EV -0.1792R
- TP_NEAR_DEST: N 123, TP1.5 38.21%, EV -0.0365R
- TP_BEFORE_DEST: N 82, TP1.5 31.71%, EV -0.2105R
- OPEN_SPACE: N 1, TP1.5 100.00%, EV +1.4668R

## Destination types
- M15_SWING: N 1438, TP1.5 32.82%, EV -0.1761R
- H1_SWING: N 436, TP1.5 36.70%, EV -0.0911R
- CURRENT_SESSION: N 262, TP1.5 33.59%, EV -0.1929R
- VWAP: N 184, TP1.5 31.52%, EV -0.2254R
- PREV_SESSION: N 33, TP1.5 15.15%, EV -0.6563R
- OPEN_SPACE: N 1, TP1.5 100.00%, EV +1.4668R

## Group permutation importance
- LAB017_BASELINE: AUC drop +0.0358
- CURRENT_APPROACH: AUC drop +0.0097
- LIFECYCLE_INTERACTION: AUC drop +0.0014
- DEST_ID_PLACEMENT: AUC drop -0.0015
- HISTORICAL_ROLE: AUC drop -0.0033

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **FAIL**
- G2_TOPOLOGY_RESIDUAL_AUC: **FAIL**
- G3_TOPOLOGY_ADDS_OVER_ROOM: **FAIL**
- G4_SELECTION_QUALITY: **FAIL**
- G5_CONFIRMATION_EV: **FAIL**
- G6_WEEK_CLUSTER_CI: **FAIL**
- G7_DISCOVERY_TRANSFER: **FAIL**
- G8_2R_SURVIVAL: **FAIL**
- G9_DIRECTION_BREADTH: **FAIL**
- G10_PROP_DD_PROXY: **FAIL**
- G11_COST_STRESS: **FAIL**
- G12_ROUTER_LIFT: **FAIL**

No holdout opening, EA authorization or live allocation is authorized by LAB018.