# GC_XAU_LONG_DEMO_READINESS_LAB_018

**Status: READY_FOR_FTMO_DEMO_SHADOW**

Chosen: **D1.00_E3M_BARE_CORRECTED**
LAB017 overlay adopted: **False**

## Frozen baseline
- Signals / accepted / fills: **279 / 237 / 103**
- EV/signal: **+0.08634R**
- SumR: **+24.09R**
- LOO-week minimum EV: **+0.07497R**
- Bootstrap P(EV>0): **96.31%**
- p95 DD @0.25% risk: **3.894%**
- Corrected late-half EV: **+0.06814R/signal**

## Cost stress
- total 0.10R/fill: **EV +0.06788R/signal**
- total 0.15R/fill: **EV +0.04942R/signal**
- total 0.20R/fill diagnostic: **EV +0.03096R/signal**
- total 0.25R/fill diagnostic: **EV +0.01250R/signal**
- historical break-even total execution cost: **0.284R/fill**

## Readiness gates
- PASS — `historical_replay_exact`
- PASS — `historical_ev_positive`
- PASS — `loo_week_min_positive`
- PASS — `bootstrap_p_positive_ge95`
- PASS — `risk_p95_dd_025_le4pct`
- PASS — `stress_cost_010_positive`
- PASS — `stress_cost_015_nonnegative`
- PASS — `late_half_positive`
- PASS — `execution_no_lookahead`
- PASS — `implementation_spec_frozen`

## Decision
The frozen LONG system is ready to be transferred to **FTMO Demo / shadow execution at 0.25% risk per trade**.
This is not live/funded promotion. The demo phase is the independent forward/OOS and implementation/slippage test.
