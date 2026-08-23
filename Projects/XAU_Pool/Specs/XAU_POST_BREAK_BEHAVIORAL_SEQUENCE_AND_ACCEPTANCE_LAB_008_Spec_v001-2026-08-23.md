# XAU_POST_BREAK_BEHAVIORAL_SEQUENCE_AND_ACCEPTANCE_LAB_008 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-23  
**Parents:** LAB002 → LAB003 → LAB004 → LAB005 → LAB006 → LAB007

## Why this LAB exists

LAB005–007 over-compressed trader judgment into local entry patterns: one retest, one confirmation bar, one iFVG flag. The podcast examples are broader. The trader watches a level break, then watches whether price starts to **respect the broken level from the other side**, whether repeated recovery attempts fail, whether the market holds the new side of the level, and whether the day has changed character.

LAB008 therefore tests the user's correction directly:

> the information may be in the **sequence after the break**, not in one bar or one wick.

This is a behavioral/state-path study, not an entry-strategy optimization.

## Source-derived storyline

The podcast explicitly describes a sequence like:

`drop below point of control → start respecting it as resistance → tries to return and goes lower → tries again and goes lower → earlier buy idea is abandoned → hold the bottom portion of VWAP → sell setups become acceptable.`

The research hypothesis is therefore not “does candle X predict candle Y?” but:

> after a causal break of an objective level, does the evolving acceptance/rejection storyline add future-path information beyond the current price snapshot?

## Canonical data / embargo

- canonical input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Discovery: break time `< 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>= 2025-07-01`
- no holdout read is authorized.

## Objective level families

Primary level family remains the causal 18:00 New York / 01:00 platform anchored tick-volume VWAP structure used in LAB002–007:

- MID = cumulative anchored VWAP
- HIGH / LOW = VWAP ± 1.618 × causal weighted SD

Secondary control family:

- same 01:00 anchor but unweighted cumulative anchored mean with ±1.618 × causal SD.

LAB008 is not required to prove VWAP-specificity; LAB003 already showed the sequence mechanism is largely generic. The anchored-mean control is retained to quantify that point.

## Break event — frozen

For each dynamic level independently, a causal **BREAK** occurs on the first completed M1 close `b` satisfying:

1. the close is at least `0.05 × ATR14(M15)` beyond the contemporaneous level;
2. break direction `d` is the sign of `Close[b] - Level[b]`;
3. among the previous eight completed M1 closes, at least five are on the opposite side of the level;
4. at least one of those prior eight closes is at least `0.10 ATR` on the opposite side, so tiny oscillations around the line do not count as structural breaks;
5. a level is re-armed only after price later reaches at least `0.25 ATR` back on the opposite side or 60 minutes have elapsed from the prior break, whichever occurs first.

Same-minute same-direction duplicates across HIGH/MID/LOW are retained as separate level interactions for the behavioral map but are deduplicated to strongest absolute break displacement for event-level model evaluation. Simultaneous opposite-direction conflicts are excluded from event-level model evaluation.

No break threshold is optimized in LAB008.

## Observation clocks — frozen

For each break event create three causal information clocks:

- `T+5m`
- `T+15m`
- `T+30m`

All features at a clock use only bars completed by that clock. Events with missing/non-contiguous M1 bars inside the observation window are excluded at that clock.

The purpose is to test **scale**: whether the market story becomes clearer when it is allowed to develop beyond a single M1 bar.

## Future label — frozen and starts AFTER each clock

The future label begins on the first M1 bar after the information clock.

From the **decision close** at the information clock, over the next 60 minutes:

- CONTINUATION = price reaches `+0.50 ATR_touch` in break direction before `-0.50 ATR_touch` against break direction;
- FAILURE = price reaches `-0.50 ATR_touch` first;
- same-M1 hit of both barriers = AMBIGUOUS;
- no barrier in 60 minutes = UNRESOLVED.

This target is intentionally measured from the current decision price, not from the original level, so a move already consumed before T+5/T+15/T+30 is not counted as future predictive success.

Secondary diagnostics:

- future `+0.75/-0.75 ATR` symmetric barrier label;
- signed 60-minute terminal return in ATR from the decision close.

No P&L, commission, SL/TP optimization, or live allocation is authorized in LAB008.

## Snapshot feature set — frozen baseline

At each clock, the SNAPSHOT model only knows the current state:

1. signed distance of current close from level / ATR in break direction;
2. current M1 signed body / ATR;
3. current M1 range / ATR;
4. current close-location-value inside the current M1 range, direction-normalized;
5. current tick volume divided by the median tick volume of the prior 30 completed M1 bars;
6. current causal level slope over five minutes / ATR;
7. original break displacement / ATR.

This is the formal version of “where is price now?”

## Sequence feature set — frozen storyline

SEQUENCE contains SNAPSHOT plus the evolving story known by that clock.

### Acceptance / time-on-side

- fraction of post-break closes on break side;
- fraction of last five closes on break side;
- longest consecutive run of closes on break side;
- number of closes on wrong side;
- mean signed distance from level;
- median signed distance from level;
- end signed distance from level.

### Expansion / loss of momentum

- max favorable excursion from level in ATR;
- max adverse excursion from level in ATR;
- first-half versus second-half favorable excursion;
- directional progress from break close to decision close;
- path efficiency = absolute net progress / sum absolute close-to-close movement;
- last-five directional progress;
- last-five path efficiency.

### Recovery attempts / role flip behavior

A recovery attempt begins when price has first been at least `+0.10 ATR` on the break side and then re-enters the near-level band `[-0.05,+0.05] ATR` or crosses to the wrong side.

Report:

- count of recovery attempts;
- minutes to first recovery attempt;
- deepest recovery against the break;
- duration of longest recovery episode;
- signed recovery depth of first attempt;
- signed recovery depth of last attempt;
- recovery-strength trend = last attempt depth minus first attempt depth (positive means later recovery is weaker / remains farther on break side);
- whether price re-expanded by at least `+0.10 ATR` after the most recent recovery attempt.

### Cross / chop structure

- number of side changes across the level;
- number of near-level closes `abs(distance)<=0.05 ATR`;
- proportion of observation time spent inside `±0.05 ATR`;
- proportion spent at least `+0.10 ATR` on break side;
- proportion spent at least `-0.10 ATR` on wrong side.

### Activity / intensity

- cumulative post-break tick volume divided by equal-length pre-break tick volume;
- median post-break M1 tick volume / median pre-break M1 volume;
- directional-volume proxy = tick volume weighted by sign of close-to-close move, normalized by total volume.

## Multiscale feature set — frozen

MULTISCALE contains SEQUENCE plus completed higher-scale summaries available by the clock.

### M5

- fraction of completed post-break M5 closes on break side;
- last completed M5 close signed distance / ATR;
- M5 path efficiency;
- whether the most recent completed M5 bar made a new favorable extreme versus the previous completed M5 bar.

### M15

At T+15 and T+30 only:

- fraction of completed post-break M15 closes on break side;
- last completed M15 close signed distance / ATR;
- whether the first completed M15 bar after break closed on break side;
- M15 favorable versus adverse range asymmetry.

No H1/D1 trend, session tuning, RSI/ADX, news labels, COT, or future features.

## Human-readable storyline states — frozen

Each clock is also assigned one descriptive state using only sequence information:

1. `CLEAN_ACCEPTANCE`
   - close-beyond fraction >= 0.80
   - end distance >= +0.10 ATR
   - no close deeper than -0.05 ATR

2. `TESTED_AND_RECLAIMED`
   - at least one wrong-side or near-level recovery attempt
   - final distance >= +0.10 ATR
   - last-five close-beyond fraction >= 0.80

3. `ACCEPTED_BUT_WEAKENING`
   - total close-beyond fraction >= 0.60
   - final distance > 0
   - current distance is at least 0.15 ATR below the post-break maximum favorable distance

4. `FAILED_BREAK`
   - final distance <= -0.05 ATR
   - close-beyond fraction <= 0.50

5. `CHOP_UNRESOLVED`
   - all other paths.

These are descriptive maps, not optimized trade rules.

## Models — frozen

For each clock independently fit on Discovery only and evaluate on Confirmation only:

1. `SNAPSHOT_LOGIT`
2. `SEQUENCE_LOGIT`
3. `MULTISCALE_LOGIT`

Implementation:

- median imputation learned on Discovery only;
- StandardScaler learned on Discovery only;
- LogisticRegression, L2, `C=1.0`, max_iter=2000, fixed random_state=20260823;
- no hyperparameter optimization;
- no class weighting;
- the same target definition across models.

Primary output is probability of future CONTINUATION.

## Primary question and gates

Primary clock for the scale test = `T+15m`.

Primary evidence that “sequence, not moment” is real requires:

- `G0_DATA_CAUSALITY`: canonical SHA valid; holdout false; all clock features causal.
- `G1_POWER`: Confirmation resolved events >= 3,000 at T+15.
- `G2_SEQUENCE_AUC`: T+15 SEQUENCE AUC >= 0.58.
- `G3_SEQUENCE_BEATS_SNAPSHOT`: T+15 SEQUENCE AUC - SNAPSHOT AUC >= +0.03 and lower 95% week-cluster bootstrap CI of AUC difference > 0.
- `G4_MULTISCALE_INCREMENTAL`: T+15 MULTISCALE AUC >= SEQUENCE AUC and T+30 MULTISCALE AUC >= T+30 SEQUENCE AUC; at least one clock improves by >= +0.01 AUC.
- `G5_SCALE_BUILD`: SEQUENCE AUC does not deteriorate from T+5 to T+15 by more than 0.01, and T+15 >= T+5 is preferred; T+30 is diagnostic because waiting longer may consume opportunity.
- `G6_CALIBRATION`: Confirmation Brier score of T+15 SEQUENCE < 0.25 and observed continuation rate rises monotonically across score quintiles except for at most one adjacent inversion <= 3 percentage points.
- `G7_STATE_ORDERING`: in Confirmation T+15, CLEAN_ACCEPTANCE and TESTED_AND_RECLAIMED continuation rates both exceed FAILED_BREAK by >= 15 percentage points.
- `G8_DIRECTION_MIRROR`: T+15 SEQUENCE AUC >= 0.55 separately for up-breaks and down-breaks.
- `G9_LEVEL_BREADTH`: T+15 SEQUENCE AUC >= 0.55 on at least two of MID/HIGH/LOW.
- `G10_DISCOVERY_CONFIRMATION_TRANSFER`: T+15 SEQUENCE AUC is >=0.58 in both Discovery cross-fit diagnostic and Confirmation OOS.

## Bootstrap — frozen

Primary paired AUC-difference bootstrap uses calendar-week clusters in Confirmation:

- 2000 bootstrap resamples
- seed 20260823
- resample weeks with replacement
- compute AUC(SEQUENCE)-AUC(SNAPSHOT) on each resample.

## Verdicts

- `SEQUENCE_ACCEPTANCE_EDGE_TRANSFERABLE`: G0..G10 all pass.
- `SEQUENCE_EDGE_NOT_MULTISCALE`: G0,G1,G2,G3,G5,G6,G7,G8,G9,G10 pass but G4 fails.
- `SEQUENCE_BEATS_SNAPSHOT_BUT_WEAK`: G3 passes but G2 or transfer/calibration breadth gates fail.
- `SNAPSHOT_EXPLAINS_MOST`: sequence does not beat snapshot robustly.
- `NO_POST_BREAK_PREDICTIVE_MAP`: neither snapshot nor sequence provides useful OOS discrimination.
- `INVALID_DATA_CLOCK`: G0 fails.

No automatic holdout opening. No EA/live allocation from LAB008 alone.

## Next step only if sequence survives

If the sequence hypothesis transfers, LAB009 may ask how to convert the evolving probability/storyline into an **early decision policy** (WAIT / CONTINUATION / ABORT) while preserving R:R. LAB008 must not optimize an entry trigger.
