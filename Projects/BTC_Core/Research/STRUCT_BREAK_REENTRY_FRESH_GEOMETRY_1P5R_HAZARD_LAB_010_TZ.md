# STRUCT_BREAK_REENTRY_FRESH_GEOMETRY_1P5R_HAZARD_LAB_010 — PREREGISTRATION

Date: 2026-08-25
Branch: lab/btc-struct-break-regime-004

## Question
After the frozen LAB008 LOW30 -> LAB009A scratch/recovery -> LAB009B re-arm/new-IMPULSE sequence, does treating the re-entry as a **new trade with fresh stop/target geometry** produce a transferable OOS edge?

## Frozen upstream state
- Original STRUCT_BREAK v002 signal unchanged.
- LOW30 classifier unchanged from LAB008.
- Scratch/recovery logic unchanged from LAB009A.
- Re-arm/new IMPULSE trigger unchanged from LAB009B: first fresh rolling 30m HIGH state after scratch, within 12h.
- Maximum one re-entry per original setup.
- 2026 excluded from fit/selection/formal verdict.

## Causal re-entry execution
A new IMPULSE is known only after its 30m observation window fully closes. Re-entry occurs at the next M5 open. No bar used to confirm the impulse may be used as the entry bar.

## Fresh stop branches — fixed before outcomes
All pivots must already be confirmed before the re-entry timestamp.

### A. LOCAL_PIVOT_5M
- BUY: last confirmed M5 swing-low pivot 3-3 before re-entry.
- SELL: last confirmed M5 swing-high pivot 3-3 before re-entry.
- If the pivot lies on the wrong side of entry or no eligible pivot exists, no trade.

### B. ATR_1P0_5M
- Stop distance = 1.0 × ATR14(M5) measured on the last fully closed M5 bar before re-entry.
- BUY stop below entry; SELL stop above entry.

### C. HYBRID_MAX
- Stop distance = max(distance to eligible LOCAL_PIVOT_5M, 1.0 × ATR14(M5)).
- Requires an eligible local pivot.

No stop multiplier or pivot order will be optimized after outcomes are viewed.

## Targets
Primary: TP = **1.5R**.
Secondary: TP = **2.0R**.
User risk rule requires TP >= 1.5 × SL, therefore no target below 1.5R is tested.

## Management
- Fresh leg is independently risk-normalized: stop distance = 1 fresh R.
- Cost = 0.06R per fresh re-entry trade.
- Primary path: fixed stop/TP, no BE/trailing, to isolate geometry.
- Secondary diagnostic only: BE after +1R.
- Maximum holding horizon: 24h; if neither stop nor target is hit, exit at final observed close and normalize to R, capped only by realized price path (not by an optimized time stop).

## Intrabar ordering
Primary execution uses M1 where available (2024–2025). Full-history M5 uses conservative adverse-first ordering if stop and TP occur in the same bar. M1 replication is required for any promising result.

## Splits
- DEV: 2019-09 through 2022-12.
- VAL: 2023-01 through 2025-12.
- 2026 shadow only, excluded from verdict.

## Primary evidence
For each geometry branch and TP=1.5R report:
- N
- win rate
- EV after 0.06R cost
- PF
- max drawdown in fresh-R units
- year-by-year EV
- DEV vs VAL transfer
- bootstrap 95% CI for VAL EV
- probability TP before SL

Also report full-policy effect when the fresh leg is added after the scratch event.

## Gates
A geometry is **PROMOTABLE CANDIDATE** only if all hold:
1. DEV EV > 0.
2. VAL EV > +0.10R per fresh re-entry.
3. VAL bootstrap 95% CI lower bound > 0.
4. At least 2/3 VAL years positive.
5. VAL N >= 40 fresh re-entries.
6. Full adaptive policy improves canonical portfolio EV on VAL and does not increase max DD by >10%.
7. If M1 replication is available, direction/sign must agree.

If EV is positive but CI crosses zero, verdict is WATCH only.

## Hazard question
Separately from the fixed-target backtest, estimate on VAL:
P(+1.5R before -1R | new IMPULSE, geometry)
and compare it with fair break-even probability after costs.

## Anti-overfit rules
- No VAL threshold tuning.
- No choosing a stop geometry based on 2026.
- No extra feature filters after seeing results.
- No target below 1.5R.
- If all three fixed geometries fail, fresh-geometry hypothesis is rejected for this re-entry trigger rather than retuned in LAB010.
