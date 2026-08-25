# STRUCT_BREAK_LOW_PARTIAL_DERISK_LAB_012

**Date:** 2026-08-25  
**Status:** COMPLETED  
**Preregistration:** `b5816a3c8279145a6832cc474d084646022f5010`  
**Verdict:** `LOW_PARTIAL_DERISK_REJECTED_AS_EDGE__25PCT_RISK_CONTROL_ONLY`

## Frozen test
LAB008 LOW30 state only. DEV 2019–2022, VAL 2023–2025, 2026 excluded. On LOW, close 25%, 50%, or 75% at the observed 30m state; residual follows the original canonical SL/BE/TP. No re-entry and no new turnover.

## Whole portfolio
Canonical VAL: EV -0.0315R, MaxDD 38.78R.

- Reduce 25%: VAL EV **-0.0347R**, MaxDD **37.64R** (~2.9% better DD).
- Reduce 50%: VAL EV **-0.0379R**, MaxDD **41.40R**.
- Reduce 75%: VAL EV **-0.0411R**, MaxDD **46.38R**.

No branch passes the preregistered promotion gate.

## Why 25% almost balances
VAL has 200 LOW trades: 125 SL, 39 BE, 36 TP +2.3R.

At 25% reduction:
- future SLs save about **+22.51R** total;
- future TP winners lose about **-22.62R** total;
- future BE trades lose another **-2.13R**.

Net damage is about -2.24R across the 200 LOW trades.

## Prop-risk effect
At LOW30, average remaining distance to the original stop is ~0.744R. A 25% reduction removes ~0.186R of future open downside immediately on the affected trade. This is useful mechanically, but does not translate into enough portfolio DD reduction.

## Key mathematical implication
With no re-entry and unchanged residual management:

`partial_result = f * EXIT_NOW + (1-f) * HOLD`

Because full EXIT at LOW has lower VAL expectancy than HOLD, every positive fixed fraction f necessarily lowers expectancy linearly. Optimizing 17%, 33%, etc. cannot create edge.

## Verdict
`LOW_PARTIAL_DERISK_REJECTED_AS_EDGE__25PCT_RISK_CONTROL_ONLY`

25% may be used only as a discretionary risk-control idea; it is not validated as a strategy improvement.

Next clean branch: `STRUCT_BREAK_LOW_FAILURE_PERSISTENCE_OPTIMAL_STOP_LAB_013` — wait after LOW for an additional causal failure-confirmation before reducing/exiting.
