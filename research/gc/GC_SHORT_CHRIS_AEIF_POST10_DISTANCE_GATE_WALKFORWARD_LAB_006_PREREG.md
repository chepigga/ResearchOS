# GC SHORT CHRIS/AEIF POST10 DISTANCE GATE WALKFORWARD LAB006 — PREREG

**Date:** 2026-09-17

## Scope

Historical walk-forward decision-gate test only. Frozen LAB003 Chris/AEIF event definition is unchanged. No XAU execution tuning. No threshold sweep.

## Frozen feature

Use only `cp10_dist_seed_high`, the only feature family that passed LAB005 residual-edge gates.

Interpretation for SHORT: larger positive value means price at the +10m checkpoint is farther below the original seed-bar high.

## Frozen checkpoint and targets

- Decision time: +10m checkpoint after LAB003 entry.
- Primary residual target: `resid_10_20_atr`.
- Secondary diagnostic target: `resid_10_30_atr`.
- No information after +10m may be used in the gate.

## Frozen walk-forward gate

For each feed independently and chronologically:

1. Require at least 8 prior eligible events.
2. Compute the median (`Q50`) of `cp10_dist_seed_high` using **all prior eligible events only**.
3. Current event is selected iff `cp10_dist_seed_high >= prior Q50`.
4. After evaluating the current event, it may enter history for future thresholds.
5. No target variable is used to set the threshold.
6. No alternate quantiles will be tested in LAB006.

This is an expanding-history causal walk-forward gate, not a fitted classifier.

## Frozen evidence outputs

For each feed and residual horizon report:
- OOF eligible N;
- selected N and selection share;
- baseline residual EV;
- selected residual EV;
- rejected residual EV;
- uplift = selected EV - baseline EV;
- selected win rate;
- chronological threshold history.

## Frozen primary gates

LAB006 passes only if all are true on the primary `10->20m` residual:

1. Rithmic OOF eligible N >= 12.
2. AMP OOF eligible N >= 12.
3. Selection share is between 25% and 75% on each feed.
4. Selected EV > 0 on each feed.
5. Selected EV > baseline EV on each feed.
6. Uplift >= +0.10 ATR on each feed.
7. Selected win rate >= 55% on each feed.
8. Secondary `10->30m` selected EV is non-negative on each feed.

If any primary gate fails, reject this exact gate. Do not change Q50 post hoc.

## Governance

A pass means only that a causal historical walk-forward decision rule exists on GC. It does not validate GC->XAU transfer, execution, SL/TP, or live/demo readiness.
