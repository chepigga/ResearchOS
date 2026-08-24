# XAU_LIVE_POST_ENTRY_MFE_MAE_AND_ACCEPTANCE_STATE_MANAGEMENT_LAB_020 — v001 REPORT

**Verdict:** `NO_LIVE_STATE_MANAGEMENT_EDGE`  
**Holdout opened:** `false`

## Snapshot hold-value prediction — Confirmation
- MINIMAL AUC **0.6064**, MAE **0.8964R**
- FULL LIVE STATE AUC **0.5938**, MAE **0.8982R**
- full-minus-minimal AUC **-0.0126**, weekly CI **[-0.02995862174871889, 0.017270029335372052]**

## Primary Confirmation — LIVE_STATE / 1.5R / serial
- n: **2114**
- trades_per_week: **27.137182786852886**
- ev: **-0.16157353956530837**
- pf: **0.4800036773340633**
- positive_rate: **0.25023651844843897**
- gross_ev: **-0.12358348022073257**
- total_R: **-341.5664626410619**
- tp_rate: **0.07852412488174078**
- model_exit_rate: **0.8500473036896878**
- max_dd_R: **343.62932848129316**
- worst_day_R: **-4.905647142043903**
- max_consec_losses: **25**
- stress10_ev: **-0.23755365825445998**
- buy_ev: **-0.16541183620305422**
- sell_ev: **-0.15787079615454608**
- median_duration_min: **1.0**
- weekly EV CI: **[-0.18564454674449743, -0.13400699392779716]**

## Management lift vs frozen early-entry baseline
- baseline serial EV **-0.18058070652626182R**, PF **0.7301902968759422**
- paired independent manager-minus-baseline trade mean **-0.0030442004147961266R**, weekly CI **[-0.0466387403914007, 0.04211760914782018]**

## Transfer / 2R
- Discovery-2023 independent EV **-0.16901679647053894R**
- Confirmation independent EV **-0.17516516155789844R**
- Confirmation 2R serial EV **-0.16014271320366646R**, PF **0.44347454194049685**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_MODEL_INFORMATION: **FAIL**
- G3_FULL_STATE_ADDS_OVER_MINIMAL: **FAIL**
- G4_CONFIRMATION_EV: **FAIL**
- G5_WEEK_CLUSTER_CI: **FAIL**
- G6_MANAGEMENT_LIFT: **FAIL**
- G7_DISCOVERY_TRANSFER: **FAIL**
- G8_2R_SURVIVAL: **FAIL**
- G9_DIRECTION_BREADTH: **FAIL**
- G10_PROP_DD_PROXY: **FAIL**
- G11_COST_STRESS: **FAIL**

No holdout opening, EA authorization or live allocation is authorized by LAB020.
