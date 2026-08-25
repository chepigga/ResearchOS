# STRUCT_BREAK_LOW_EXIT_REARM_REENTRY_LAB_009B

**Date:** 2026-08-25
**Verdict:** `REENTRY_SIGNAL_ENRICHES_WINNERS__OLD_TARGET_EXECUTION_FAILS_OOS`
**Preregistration:** `0e71e44ac88253e1a5a13f9427bcbbe9be2e86e6`

## Core result

The frozen LOW30 -> scratch -> re-arm -> renewed HIGH mechanism does identify part of the lost right tail, but re-entering the old trade with the old stop/2.3R destination does not improve OOS portfolio expectancy.

VAL recovered canonical outcomes after LOW/scratch:
- full TP: 31, re-entered 18 (58.1%)
- SL: 68, re-entered 27 (39.7%)
- BE: 35, re-entered 29 (82.9%)

So the renewed-HIGH trigger is not random, but it heavily re-enters trades that later only reach the BE class.

## Primary preregistered market re-entry

Full portfolio:
- DEV canonical +0.0155R/trade -> policy +0.0160R (+0.0005R)
- VAL canonical -0.0315R/trade -> policy -0.0457R (-0.0142R)

VAL 95% bootstrap CI for improvement approximately [-0.051R,+0.023R].

Primary policy fails.

## Risk-normalized diagnostic

Sizing the second order so the old structural stop equals one fresh unit of risk removes most of the damage:
- DEV +0.0155R -> +0.0221R (+0.0066R)
- VAL -0.0315R -> -0.0345R (-0.0030R)
- VAL DD 38.78R -> 39.91R

Still not an OOS edge.

## M1 replication

For the 60 triggered re-entries in 2024–2025, exact M1 execution reproduces the M5 second-leg average for both market/original-risk and risk-normalized variants. Failure is not a same-bar ordering artifact.

## Critical diagnostic

A fresh DEV-trained post-scratch response model predicts eventual renewed +1R progress OOS:
- 30m VAL AUC 0.638, 95% CI [0.545,0.728]
- 60m VAL AUC 0.691, 95% CI [0.600,0.779]

But it does not predict the old full TP 2.3R:
- 30m AUC 0.490
- 60m AUC 0.478

Interpretation: after scratch, the market reveals whether a new impulse is forming, but that impulse should be treated as a **new trade**, not forced to inherit the original 2.3R destination.

## Next step

`STRUCT_BREAK_REENTRY_FRESH_GEOMETRY_1P5R_HAZARD_LAB_010`

Test fresh post-scratch stop/target geometry under the frozen constraint TP >= 1.5 x SL, with +1.5R-before--1R as the primary hazard target and DEV/VAL + M1 replication.
