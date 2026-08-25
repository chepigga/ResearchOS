# XAU_POST_PROBATION_HEALTHY_STATE_RR_CONSTRAINED_ADD_LIMIT_LAB_026 — v001 REPORT

**Verdict:** `HEALTH_SIGNAL_PERSISTS_RR_LIMIT_NOT_ENOUGH`  
**Holdout opened:** `false`

## Primary Confirmation — 25% starter + healthy probation + RR>=1.5 add-limit
- N **2275**, trades/week **29.20**
- EV **-0.0636R**, PF **0.576**, TP **6.02%**
- add fill/promotion rate **8.31%**, mean risk budget **0.312R**
- risk-efficiency **-0.2035**
- BUY **-0.0743R**, SELL **-0.0532R**
- stress10 **-0.0873R**
- max DD **148.66R**, worst day **-3.03R**
- weekly EV CI **[-0.07576936922739967, -0.0476368145187786]**

## Comparison
- FULL_IMMEDIATE EV **-0.1772R**, PF **0.735**
- LAB025 market-promotion EV **-0.0715R**, PF **0.569**
- LAB026 minus FULL paired weekly **+0.1108R**, CI **[0.06787458704763745, 0.15303692515441786]**
- LAB026 minus LAB025 market-promotion paired weekly **+0.0070R**, CI **[-0.0007769464397251409, 0.014973478163771203]**

## Healthy add cohort
      cohort   n  baseline_ev  lab025_market_promote_ev  lab026_ev  tp_rate  mean_add_rr  median_add_rr  median_fill_latency
 HEALTHY_ALL 382     0.279799                 -0.064088  -0.019722 0.513089     1.528151            1.5                  1.0
  ADD_FILLED 191    -0.248818                 -0.380267  -0.241549 0.308901     1.528151            1.5                  1.0
ADD_UNFILLED 191     0.808415                  0.252091   0.202104 0.717277          NaN            NaN                  NaN

## Filled add economics
{
  "n": 191,
  "combined_ev": -0.24154857647181277,
  "starter_cf_ev": -0.062204486522154635,
  "incremental_add_ev": -0.1793440899496582,
  "mean_rr": 1.5281505936186002,
  "median_rr": 1.5,
  "rr_ge_1p5": 1.0
}

## Transfer / 2R
- Discovery EV **-0.0422R**
- Confirmation 2R EV **-0.0579R**, PF **0.641**

## Frozen gates
- G0_DATA_CAUSALITY: **PASS**
- G1_POWER: **PASS**
- G2_POSITIVE_ECONOMICS: **FAIL**
- G3_WEEKLY_ROBUSTNESS: **FAIL**
- G4_RISK_EFFICIENCY: **FAIL**
- G5_HEALTHY_SELECTIVITY: **PASS**
- G6_FILLED_ADD_ECONOMICS: **FAIL**
- G7_BEATS_LAB025_MARKET_PROMOTION: **FAIL**
- G8_DISCOVERY_TRANSFER: **FAIL**
- G9_DIRECTION_BREADTH: **FAIL**
- G10_2R_SURVIVAL: **FAIL**
- G11_COST_STRESS: **FAIL**
- G12_PROP_DD_PROXY: **PASS**

No sensitivity rescue, no holdout opening, no EA/live authorization.
