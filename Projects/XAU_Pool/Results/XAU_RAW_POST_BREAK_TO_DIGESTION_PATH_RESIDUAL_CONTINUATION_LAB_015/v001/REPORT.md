# XAU_RAW_POST_BREAK_TO_DIGESTION_PATH_RESIDUAL_CONTINUATION_LAB_015 — v001 REPORT

**Verdict:** `NO_RAW_PATH_RESIDUAL_EDGE`  
**Holdout opened:** `false`

## OOS residual prediction — Confirmation
- COMPACT_BASELINE: AUC **0.5050**, Brier **0.2365**, N **2354**
- RAW_PRICE_PATH: AUC **0.5277**, Brier **0.2326**, N **2354**
- RAW_PRICE_PLUS_COMPACT: AUC **0.5196**, Brier **0.2342**, N **2354**
- RAW_PRICE_ACTIVITY_PLUS_COMPACT: AUC **0.5224**, Brier **0.2334**, N **2354**
- RAW+COMPACT minus COMPACT AUC: **+0.0146**, weekly CI **[-0.003908225984164171, 0.05572192575084755]**
- activity increment: **+0.0028**

## Primary p>=0.55 selection
- coverage: **6.03%**
- TP1.5 precision: **35.21%**
- rejected TP1.5 rate: **33.18%**
- gap: **+2.03%**, weekly CI **[None, None]**

## Executable economics — Confirmation / 1.5R / serial
- n: **141**
- trades_per_week: **1.8161**
- ev: **-0.1709R**
- pf: **0.7477**
- tp_rate: **34.75%**
- total_R: **-24.10R**
- max_dd_R: **30.23R**
- worst_day_R: **-3.19R**
- max_consec_losses: **10**
- stress10_ev: **-0.2503R**
- buy_ev: **-0.0812R**
- sell_ev: **-0.2820R**
- weekly EV CI: **[-0.3783, 0.0685]R**

## Baseline / transfer
- all-digestion serial EV: **-0.1806R**, PF **0.7302**
- routed-minus-baseline weekly diff: **+0.0330R**, CI **[-0.1785, 0.2403]**
- Discovery-2023 routed independent EV: **-0.0570R**
- Confirmation routed independent EV: **-0.1593R**
- Confirmation routed 2R EV: **-0.1118R**, PF **0.8435**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **FAIL**
- G2_RAW_RESIDUAL_AUC: **FAIL**
- G3_RAW_ADDS_OVER_COMPACT: **FAIL**
- G4_SELECTION_QUALITY: **FAIL**
- G5_CONFIRMATION_EV: **FAIL**
- G6_WEEK_CLUSTER_CI: **FAIL**
- G7_DISCOVERY_TRANSFER: **FAIL**
- G8_2R_SURVIVAL: **FAIL**
- G9_DIRECTION_BREADTH: **FAIL**
- G10_PROP_DD_PROXY: **FAIL**
- G11_COST_STRESS: **FAIL**
- G12_ROUTER_LIFT: **FAIL**

No holdout opening, EA authorization or live allocation is authorized by LAB015.

## Post-hoc raw-only diagnostic — does not change verdict

The raw-price-only representation was slightly stronger than the preregistered RAW+COMPACT integration (AUC **0.5277** vs **0.5196**), while the old compact story remained near chance (**0.5050**). Raw-only quintiles show a weak monotonic TP1.5 gradient from **30.8%** in Q1 to **36.9%** in Q5, but Q5 mean EV is still **-0.100R** and raw-only `p>=0.55` serial EV remains about **-0.155R**.

Grouped permutation importance places most of the weak information in signed distance, directional candle body, and drawdown from the running directional high-water mark. The strongest individual clock positions are early/intermediate (especially T2, T7, T17), not only the digestion end.

This suggests raw chronology is not completely empty, but fixed clock-time slots may still be the wrong representation for a human-like storyline: equivalent phases can occur at different minutes. Event-time/phase alignment is a distinct future hypothesis; it is not tested or authorized by LAB015.
