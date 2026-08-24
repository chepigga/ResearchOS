# XAU_EVENT_ALIGNED_POST_BREAK_PHASE_PATH_RESIDUAL_LAB_016 — v001 REPORT

**Verdict:** `NO_EVENT_ALIGNED_RESIDUAL_EDGE`  
**Holdout opened:** `false`

## OOS residual prediction — Confirmation
- FIXED_CLOCK_RAW AUC **0.5277**, Brier **0.2326**, N **2354**
- EVENT_ALIGNED_PRICE AUC **0.4916**, Brier **0.2389**
- EVENT_ALIGNED_PLUS_COMPACT AUC **0.4960**, Brier **0.2372**
- EVENT_ALIGNED minus FIXED_CLOCK AUC **-0.0361**, weekly CI **[-0.07594224735602978, -0.012093237000524327]**
- phase+compact increment **+0.0044**

## Primary p>=0.55 selection
- coverage **5.56%**
- TP1.5 precision **29.01%**
- rejected TP1.5 **33.56%**
- gap **-4.55 pp**

## Executable economics — Confirmation / 1.5R / serial
- N **129**, trades/week **1.67**
- EV **-0.3263R**, PF **0.559**, TP **27.91%**
- BUY **-0.2704R**, SELL **-0.3814R**
- +$0.10 stress EV **-0.4016R**
- weekly EV CI **[-0.4912355762425079, -0.026962737953308773]**

## Baseline / transfer
- all-digestion serial EV **-0.1806R**, PF **0.730**
- routed-minus-baseline weekly diff **-0.0482R**, CI **[-0.22804750854201106, 0.13661401456374794]**
- Discovery-2023 routed independent EV **+0.0955R**
- Confirmation routed independent EV **-0.2992R**
- Confirmation 2R serial EV **-0.3155R**

## Phase construction diagnostics
- DISCOVERY: P1/P2/P3 fallback 14.4% / 20.8% / 45.9%; median durations expansion/pullback/recovery/post/digestion = 6.0/2.0/2.0/3.0/4.0 min
- CONFIRMATION: P1/P2/P3 fallback 12.4% / 19.7% / 46.5%; median durations expansion/pullback/recovery/post/digestion = 6.0/2.0/3.0/3.0/4.0 min

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **FAIL**
- G2_PHASE_RESIDUAL_AUC: **FAIL**
- G3_PHASE_BEATS_FIXED_CLOCK: **FAIL**
- G4_SELECTION_QUALITY: **FAIL**
- G5_CONFIRMATION_EV: **FAIL**
- G6_WEEK_CLUSTER_CI: **FAIL**
- G7_DISCOVERY_TRANSFER: **FAIL**
- G8_2R_SURVIVAL: **FAIL**
- G9_DIRECTION_BREADTH: **FAIL**
- G10_PROP_DD_PROXY: **FAIL**
- G11_COST_STRESS: **FAIL**
- G12_ROUTER_LIFT: **FAIL**

No holdout opening, EA authorization or live allocation is authorized.
