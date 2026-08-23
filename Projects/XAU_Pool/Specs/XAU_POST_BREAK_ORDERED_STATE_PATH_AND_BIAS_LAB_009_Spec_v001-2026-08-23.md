# XAU_POST_BREAK_ORDERED_STATE_PATH_AND_BIAS_LAB_009 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-23  
**Parents:** LAB002 → LAB003 → LAB008

## Motivation

LAB008 showed that post-break behavior is not predictive of another symmetric +0.50 ATR extension from the already-current price, but it is highly informative for whether the market continues to accept the new side of the broken level. The remaining question is whether the **order of behavioral states** adds information beyond a snapshot or an unordered summary.

This LAB models the trader's storyline directly. It does not generate an entry.

## Canonical data / embargo

- canonical input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- canonical SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- frozen break universe: LAB008 `events.csv.gz`, family `VWAP_VOLUME`
- Discovery: break time `< 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>=2025-07-01`

No holdout bars/events may be used.

## Break lineage

Use LAB008 break events without redefining or optimizing break detection. Unique event key:
`family, level, break_i, break_time, dir`.

Primary family: `VWAP_VOLUME`.  
Anchored-mean family is a diagnostic control only.

## Decision clocks

Primary: **T+15 minutes** after break.  
Secondary: **T+30 minutes** after break.

The ordered state path is built from non-overlapping completed 5-minute blocks after the break:
- T+15 path = blocks 1–5, 6–10, 11–15 minutes
- T+30 path = six 5-minute blocks

All bars in every block must be contiguous M1 bars.

## Dynamic level

Recompute the same causal intraday anchored VWAP line family used by LAB008:
- anchor 01:00 platform clock
- typical price `(high+low+close)/3`
- causal tick-volume weighting
- MID and ±1.618 weighted-SD HIGH/LOW

For each minute define signed close distance:
`x_t = dir * (Close_t - Level_t) / ATR_touch`
where positive means the market is on the breakout side.

ATR_touch is the completed Wilder ATR14(M15) available at the break.

## Frozen 5-minute behavioral states

Each completed 5-minute block is assigned exactly one token using block-level signed distances. Priority order is fixed:

1. **RECLAIM**
   - ending signed distance `<= -0.05 ATR`, OR
   - fraction of closes on breakout side `< 0.40`.

2. **FAILED_RECOVERY**
   - at least one close reaches `<= -0.05 ATR`,
   - block ends `>= +0.05 ATR`,
   - at least 60% of closes finish on breakout side.

3. **EXPAND**
   - at least 80% of closes are on breakout side,
   - end minus start signed distance `>= +0.10 ATR`,
   - block maximum signed distance exceeds start by `>= +0.15 ATR`.

4. **TEST**
   - at least one close comes within `±0.05 ATR` of the dynamic level,
   - block ends on breakout side (`> 0`),
   - at least 60% of closes are on breakout side.

5. **HOLD**
   - at least 80% of closes are on breakout side,
   - minimum signed distance in block is `> -0.05 ATR`.

6. **CHOP**
   - all remaining blocks.

No state threshold may be changed after replay.

## Ordered storyline representations

At each clock create three nested representations from exactly the same block tokens:

### SNAPSHOT_STATE
Only the final 5-minute token is known.

### BAG_OF_STATES
Counts of the six tokens across the observed blocks; order discarded.

Example: `EXPAND → HOLD → TEST` and `TEST → HOLD → EXPAND` map to the same bag.

### ORDERED_PATH
Exact chronological token sequence.

Example: `EXPAND>HOLD>TEST` remains distinct from `TEST>HOLD>EXPAND`.

No continuous price features are allowed in the primary ordered-vs-unordered comparison. This prevents the test from silently becoming another aggregate feature model.

## Primary future bias target

After the decision clock, observe the next 30 contiguous completed M1 bars.

`ACCEPTANCE_PERSISTS = 1` if at least **20 of 30 closes (>=2/3)** are on the breakout side of the contemporaneous dynamic level:
`dir * (Close - Level) > 0`.

Otherwise `0`.

This target asks whether the new side remains accepted, not whether price extends another fixed ATR from the decision price.

Secondary targets:
1. `TERMINAL_SIDE`: the 30-minute terminal close remains on breakout side.
2. `NO_DEEP_RECLAIM`: no future close reaches `<= -0.05 ATR_touch` during the next 30 minutes.

Primary verdict is based only on `ACCEPTANCE_PERSISTS`.

## Probability estimator

Train on Discovery only. No Confirmation fitting.

For each representation estimate empirical probability using Beta(1,1) smoothing:
`p = (successes + 1) / (n + 2)`.

Frozen backoff for sparse cells:
- ORDERED_PATH exact sequence if Discovery N >= 50;
- otherwise last two ordered tokens if N >= 50;
- otherwise SNAPSHOT_STATE probability.

For T+15, BAG_OF_STATES uses the exact six-token count vector if N >= 50; otherwise SNAPSHOT_STATE probability.

SNAPSHOT_STATE always uses the final state token.

No threshold optimization. These probabilities are a bias score, not a trade rule.

## Evaluation

Primary OOS Confirmation metrics:
- ROC AUC
- Brier score
- log loss
- calibration by probability quintile

Primary incremental tests at T+15:
- ORDERED_PATH AUC − SNAPSHOT_STATE AUC
- ORDERED_PATH AUC − BAG_OF_STATES AUC
- ORDERED_PATH Brier improvement vs both

Calendar-week cluster bootstrap:
- 4000 resamples
- seed 20260823
- cluster by break week
- report 95% CI for both AUC differences

## Transfer / interpretability diagnostics

Report:
- Discovery and Confirmation state/path counts
- top 20 most frequent ordered paths with Discovery and Confirmation acceptance rates
- paths with strongest/weakest Confirmation acceptance, but do not use them to alter the primary model
- BUY/SELL mirror
- MID/HIGH/LOW breadth
- yearly 2022/2023/2024/2025-H1 AUC
- T+30 secondary ordered-path result
- anchored-mean control
- transition matrix between adjacent tokens

## Frozen gates

Primary = Confirmation / VWAP_VOLUME / T+15 / ACCEPTANCE_PERSISTS.

- `G0_DATA_CAUSALITY`: canonical SHA valid; holdout sealed; contiguous bars.
- `G1_POWER`: >= 8,000 resolved Confirmation events.
- `G2_BIAS_AUC`: ORDERED_PATH AUC >= 0.75.
- `G3_ORDER_BEATS_SNAPSHOT`: ORDERED − SNAPSHOT AUC >= +0.01 and lower week-bootstrap CI > 0.
- `G4_ORDER_BEATS_BAG`: ORDERED − BAG AUC >= +0.01 and lower week-bootstrap CI > 0.
- `G5_BRIER_INCREMENTAL`: ORDERED Brier lower than both SNAPSHOT and BAG.
- `G6_CALIBRATION`: top probability quintile acceptance rate exceeds bottom by >= 25 percentage points in Confirmation.
- `G7_DIRECTION_MIRROR`: BUY and SELL ORDERED AUC each >= 0.70.
- `G8_LEVEL_BREADTH`: MID/HIGH/LOW ORDERED AUC each >= 0.70.
- `G9_YEAR_TRANSFER`: 2024 and 2025-H1 ORDERED AUC each >= 0.70.
- `G10_T30_SURVIVAL`: T+30 ORDERED AUC >= 0.70.

## Verdicts

- `ORDERED_STORYLINE_ADDS_BIAS_INFORMATION`: all G0..G10 pass.
- `BIAS_STRONG_ORDER_NOT_INCREMENTAL`: G0,G1,G2,G6,G7,G8,G9 pass but G3/G4 fail.
- `ORDER_INCREMENTAL_BUT_NARROW`: G2/G3/G4 pass but breadth/transfer/power gate fails.
- `NO_ORDERED_STORYLINE_EDGE`: G2 fails or no transfer.
- `INVALID_DATA_CAUSALITY`: G0 fails.

No economics, entry, holdout opening, or live allocation is authorized by LAB009.

## Anti-overfit

Do not tune after outcomes:
- 5-minute state block size;
- 15/30-minute decision clocks;
- state definitions/priority;
- 30-minute future bias horizon;
- 2/3 acceptance target;
- Beta(1,1) smoothing;
- N=50 backoff threshold;
- gates.

If order does not beat snapshot/bag, conclude that the human-readable storyline is useful primarily as a descriptive bias narrative, not incremental predictive information.
