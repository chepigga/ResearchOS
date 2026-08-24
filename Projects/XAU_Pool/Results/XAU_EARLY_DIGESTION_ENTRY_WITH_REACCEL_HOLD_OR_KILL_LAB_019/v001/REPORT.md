# XAU_EARLY_DIGESTION_ENTRY_WITH_REACCEL_HOLD_OR_KILL_LAB_019 — v001 REPORT

**Verdict:** `NO_HOLD_KILL_MANAGEMENT_EDGE`  
**Holdout opened:** `false`

## Primary Confirmation — HOLD_OR_KILL_5M / 1.5R / serial
- n: **2078**
- trades_per_week: **26.675054792374787**
- ev: **-0.18326542450542616**
- pf: **0.6602228704951432**
- tp_rate: **0.21703561116458134**
- kill_rate: **0.36236766121270453**
- hold_rate: **0.3325312800769971**
- gross_ev: **-0.14534712121999896**
- max_dd_R: **383.12872108722723**
- worst_day_R: **-8.135814837967107**
- max_consec_losses: **20**
- stress10_ev: **-0.2591020310762806**
- buy_ev: **-0.19287532822709108**
- sell_ev: **-0.17401850109430572**
- median_duration_min: **5.0**
- weekly EV CI: **[-0.21779018036121625, -0.14721190459595515]**

## Management lift vs frozen early-entry baseline
- baseline serial EV **-0.18058070652626182R**, PF **0.7301902968759422**
- paired independent management-minus-baseline **-0.012914898560788767R**, weekly CI **[-0.04255362673128272, 0.01598989425292398]**

## Future-MICRO conditional diagnostic (not entry-usable)
- FUTURE_MICRO: N **1160**, management EV **0.2473R**, baseline EV **0.3541R**, delta **-0.1068R**, kill **16.8%**, hold **66.4%**
- NO_FUTURE_MICRO: N **1194**, management EV **-0.6050R**, baseline EV **-0.6833R**, delta **+0.0783R**, kill **53.9%**, hold **0.0%**

## Transfer / 2R
- Discovery independent EV **-0.16995103615179924R**
- Confirmation independent EV **-0.18503585970389108R**
- Confirmation 2R serial EV **-0.15794294667984862R**, PF **0.7200306934545501**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_CONFIRMATION_EV: **FAIL**
- G3_WEEK_CLUSTER_CI: **FAIL**
- G4_MANAGEMENT_LIFT: **FAIL**
- G5_SPLIT_TRANSFER: **FAIL**
- G6_2R_SURVIVAL: **FAIL**
- G7_DIRECTION_BREADTH: **FAIL**
- G8_PROP_DD_PROXY: **FAIL**
- G9_COST_STRESS: **FAIL**
- G10_TOXIC_KILL_VALUE: **FAIL**
- G11_HEALTHY_RETENTION: **PASS**

No holdout opening, EA authorization or live allocation is authorized by LAB019.
