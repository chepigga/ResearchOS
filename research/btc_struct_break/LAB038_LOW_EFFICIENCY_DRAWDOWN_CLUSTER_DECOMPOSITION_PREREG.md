# BTC_LOW_EFFICIENCY_DRAWDOWN_CLUSTER_DECOMPOSITION_LAB_038

Date: 2026-08-27

## Objective
Decompose the worst rolling 3-month cluster observed after the LAB037 portfolio rule `EFFICIENCY_STATE=LOW -> 0.5x risk`.

## Frozen scope
No new entry filters and no threshold tuning. This LAB is attribution only.

## Frozen attribution dimensions
1. stream contribution
2. calendar concentration (year / quarter / month)
3. ATR_STATE
4. SIGNAL_CLUSTER
5. FAILED_BREAK_DENSITY
6. PERSISTENCE_STATE
7. RECENT_HITRATE
8. REALIZED_DD_STATE
9. LOW-efficiency vs non-LOW-efficiency contribution

## Primary questions
- Is the worst rolling-3M loss dominated by one stream?
- Is it concentrated in one calendar block?
- Is it concentrated in one causal market subregime?
- Does LOW-efficiency risk reduction already remove most of the broad bad regime, leaving an idiosyncratic residual cluster?

## Decision rule
This LAB does not promote a new router. A follow-up router is justified only if one pre-existing causal state captures >=40% of the residual worst-3M loss contribution while representing <=35% of all VAL trades and showing negative or materially sub-baseline EV in both DEV and VAL.
