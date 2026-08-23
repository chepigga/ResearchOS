# XAU_ORDERED_STORYLINE_BIAS_ROUTER_TO_ENTRY_LAB_010 — v001 REPORT

**Verdict:** `NO_BIAS_ROUTER_ENTRY_LIFT`  
**Holdout opened:** `false`

## Primary Confirmation — routed serial / 1.5R

- N: **990**
- trades/week: **12.74**
- EV: **-0.1562R**
- PF: **0.765**
- TP rate: **34.24%**
- gross EV: **-0.1163R**
- stress +$0.10 EV: **-0.2362R**
- max DD: **157.90R**
- worst day: **-5.41R**
- BUY EV: **-0.1735R**
- SELL EV: **-0.1390R**

## Baseline versus Bias Router

Baseline serial EV: **-0.1744R**, PF **0.737**.  
Routed serial EV: **-0.1562R**, PF **0.765**.

Independent candidate route rate: **14.78%** (1,016/6,876).

Weekly routed CI: **[-0.2323, -0.0748]R**.  
Weekly routed-minus-baseline independent EV CI: **[-0.0611, +0.0854]R**.

## 2R

Routed serial EV: **-0.1458R**, PF **0.795**.

## Discovery transfer

Routed serial EV: **-0.1197R**, PF **0.816**.

## Level breadth

- MID: **-0.2398R**
- HIGH: **-0.1348R**
- LOW: **-0.0623R**

## Gates

- G0_DATA_CAUSALITY: PASS
- G1_POWER: PASS
- G2_ROUTED_EV: FAIL
- G3_WEEK_CI: FAIL
- G4_INCREMENTAL_LIFT: FAIL
- G5_SPLIT_TRANSFER: FAIL
- G6_2R_SURVIVAL: FAIL
- G7_DIRECTION_BREADTH: FAIL
- G8_LEVEL_BREADTH: FAIL
- G9_PROP_DD_PROXY: FAIL
- G10_COST_STRESS: FAIL
- G11_ROUTER_MONOTONICITY: PASS

No holdout opening or live allocation is authorized.

## Post-verdict adverse-selection diagnostic

The Bias Engine itself remains valid on the full break universe. In Confirmation, breaks with `p_accept >= 0.75` have about **83.0%** realized acceptance persistence. However, conditioning on a later qualifying retest changes the cohort sharply:

- strong-bias breaks with a qualifying retest: **65.1%** acceptance;
- strong-bias breaks with no qualifying retest: **94.3%** acceptance;
- retest rate among strong-bias breaks: **38.6%**.

Among routed retest candidates, actual acceptance-persist trades have about **+0.168R** EV, while failed-acceptance trades have about **-0.761R** EV. Break-even therefore requires roughly **81.9%** true acceptance precision inside the retest cohort, far above the observed 65.1%.

Interpretation: a return to the broken level after a strong acceptance storyline is itself adverse-selection information. The Bias Engine is useful context, but this simple post-T+15 retest entry is the wrong downstream setup.
