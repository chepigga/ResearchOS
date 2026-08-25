# XAU_DOUBLE_NO_RETURN_CONFIRMED_STARTER_WINNER_MONETIZATION_LAB_027 — v001 REPORT

**Verdict:** `DOUBLE_NO_RETURN_CONFIRMED_BUT_MONETIZATION_NOT_POSITIVE`  
**Holdout opened:** `false`

## Primary Confirmation — starter only, TP2 after double-no-return confirmation
- N **2273**, EV **-0.0471R**, PF **0.562**, trades/week **29.18**
- BUY **-0.0503R**, SELL **-0.0439R**, stress10 **-0.0662R**
- MaxDD **108.42R**, worst day **-1.88R**
- weekly EV CI **[-0.053483776454954945, -0.03901252733534173]**

## Double-no-return confirmed alive
- N **118**
- incremental TP2-vs-keep-TP1.5 starter **+0.0186R**, week CI **[-0.021782035340842294, 0.05277730241905832]**

## Secondary
- TP2.5 EV **-0.0465R**, PF **0.568**
- structural trail proxy EV **-0.0454R**, PF **0.564**

## Controls / transfer
- Discovery TP2 EV **-0.0429R**
- Full immediate baseline EV **-0.1806R**, MaxDD **375.41R**

## Frozen gates
- G0_CAUSALITY: **PASS**
- G1_CONFIRMED_POWER: **PASS**
- G2_POSITIVE_ECONOMICS: **FAIL**
- G3_CONFIRMED_INCREMENTAL: **PASS**
- G4_WEEKLY_ROBUSTNESS: **FAIL**
- G5_TRANSFER: **FAIL**
- G6_DIRECTION_BREADTH: **FAIL**
- G7_STRESS: **FAIL**
- G8_PROP_DD: **PASS**
- G9_TP25_SURVIVAL: **FAIL**

No sensitivity rescue, no holdout opening, no EA/live authorization.
