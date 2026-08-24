# XAU_LIVE_STATE_OUTCOME_PROBABILITY_X_REMAINING_PAYOFF_MANAGEMENT_LAB_021 — v001 REPORT

**Verdict:** `NO_OUTCOME_X_PAYOFF_MANAGEMENT_EDGE`  
**Holdout opened:** `false`

## Outcome-probability prediction — Confirmation
- MINIMAL macro OVR AUC **0.7513**, logloss **0.9063**, Brier **0.5203**
- FULL macro OVR AUC **0.7581**, logloss **0.9066**, Brier **0.5311**
- TP/SL/TIME AUC **0.7236 / 0.7223 / 0.8283**
- FULL minus MINIMAL macro AUC **+0.0068**, weekly CI **[-0.006546658663022789, 0.01592354399635357]**
- Discovery TIME terminal mean payoff: 1.5R **+0.1346R**, 2R **+0.3879R**

## Primary Confirmation — OUTCOME_X_PAYOFF / 1.5R / serial
- n: **2109**
- trades_per_week: **27.072998343175374**
- ev: **-0.17018485312486084**
- pf: **0.4637410755833894**
- gross_ev: **-0.13221389808594064**
- tp_rate: **0.06780464675201517**
- model_exit_rate: **0.8601232811759127**
- max_dd_R: **363.5276832633667**
- worst_day_R: **-4.652138421997627**
- max_consec_losses: **25**
- stress10_ev: **-0.24612676320270127**
- buy_ev: **-0.1633074558835131**
- sell_ev: **-0.1768125124775563**
- median_duration_min: **1.0**
- weekly EV CI: **[-0.1939599086828366, -0.14411388897864458]**

## Management lift vs baseline
- baseline serial EV **-0.18058070652626182R**, PF **0.7301902968759422**
- MINIMAL-payoff serial EV **-0.16974020549348684R**, PF **0.4510611367971835**
- paired FULL manager-minus-baseline mean **-0.007250595730015946R**, weekly CI **[-0.05255517185337038, 0.0347950195149419]**

## Transfer / 2R
- 2024 independent EV **-0.17388160112674902R**
- 2025H1 independent EV **-0.1916091125491814R**
- Confirmation 2R serial EV **-0.1648487415761332R**, PF **0.4421864605284005**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_PROBABILITY_INFORMATION: **PASS**
- G3_FULL_ADDS_OVER_MINIMAL: **FAIL**
- G4_CALIBRATION: **FAIL**
- G5_CONFIRMATION_EV: **FAIL**
- G6_WEEK_CLUSTER_CI: **FAIL**
- G7_MANAGEMENT_LIFT: **FAIL**
- G8_TIME_TRANSFER: **FAIL**
- G9_2R_SURVIVAL: **FAIL**
- G10_DIRECTION_BREADTH: **FAIL**
- G11_PROP_DD_PROXY: **FAIL**
- G12_COST_STRESS: **FAIL**

No holdout opening, EA authorization or live allocation is authorized by LAB021.
