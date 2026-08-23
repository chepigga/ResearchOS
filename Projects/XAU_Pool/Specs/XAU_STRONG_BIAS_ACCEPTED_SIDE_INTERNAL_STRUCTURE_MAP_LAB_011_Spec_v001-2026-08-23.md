# XAU_STRONG_BIAS_ACCEPTED_SIDE_INTERNAL_STRUCTURE_MAP_LAB_011 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-23  
**Parents:** LAB008 → LAB009 / `XAU_ORDERED_STORYLINE_BIAS_ENGINE_v001` → LAB010

## Motivation

LAB009 validated ordered post-break behavior as a Bias Engine. LAB010 showed that, after a strong T+15 acceptance bias, waiting for price to return all the way to the original broken level creates adverse selection: strong-bias breaks that retest the old level retain acceptance much less often than strong-bias breaks that never return.

LAB011 therefore stops treating the old broken level as the desired entry location. It asks what price builds **inside the already accepted side** after T+15: local expansion, base/hold, shallow pullback, deep pullback, and eventual degradation back to the old level.

This is a map/probability LAB. It does not authorize an entry.

## Canonical data / embargo

- canonical input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- break universe: LAB008 frozen `break_census.csv`, `model_event=true`, `family=VWAP_VOLUME`
- Discovery: break time `< 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>=2025-07-01`

No post-holdout bars/events may be read.

## Frozen Bias Engine

Use `XAU_ORDERED_STORYLINE_BIAS_ENGINE_v001` unchanged at T+15.

Primary universe:

`STRONG_ACCEPTANCE = p_accept >= 0.75`

The threshold is inherited from preregistered LAB010. It is not re-optimized here.

## Observation clock and separation

- Bias decision exists at T+15.
- Internal-structure observation window: **T+16 through T+30**.
- Split into three non-overlapping completed 5-minute blocks:
  - block A: T+16…T+20
  - block B: T+21…T+25
  - block C: T+26…T+30
- Outcome window begins strictly after observation: **T+31 through T+60**.

All required M1 bars must be contiguous.

## Geometry

Use signed close distance from the contemporaneous original broken VWAP level:

`x_t = break_dir * (Close_t - Level_t) / ATR_touch`

Positive = still on the accepted breakout side.

For each internal block define `prior_peak` as the maximum `x_t` observed from T+1 through the minute immediately before that block. Thus the internal states measure behavior relative to the already-built directional high-water mark, not just the original level.

## Frozen internal state alphabet

Each 5-minute block receives exactly one token in this priority order.

1. **LEVEL_RETEST**
   - any completed close in the block reaches `x_t <= +0.05 ATR`.
   - This is degradation toward the old broken level, not a desired setup.

2. **EXPAND**
   - block maximum exceeds `prior_peak` by at least `+0.15 ATR`, and
   - block ends at least `+0.05 ATR` above `prior_peak`.

3. **SHALLOW_PULLBACK**
   - drawdown from `prior_peak` to block minimum is `>=0.10 ATR` and `<0.25 ATR`,
   - block minimum remains `> +0.10 ATR` beyond the old level,
   - block recovers at least `+0.05 ATR` from its minimum by the block close,
   - block close is no worse than `0.10 ATR` below `prior_peak`.

4. **DEEP_PULLBACK**
   - drawdown from `prior_peak` to block minimum is `>=0.25 ATR`,
   - but block minimum remains `> +0.05 ATR` beyond the old level.

5. **BASE**
   - block signed-close range is `<=0.20 ATR`, and
   - all closes remain `> +0.10 ATR` beyond the old level.

6. **HOLD**
   - all remaining blocks whose minimum remains `> +0.05 ATR`.

No threshold may change after replay.

## Ordered internal structure

For each strong-bias break create:

`INTERNAL_PATH = state_A > state_B > state_C`

Also create:
- final internal state only (`SNAPSHOT_INTERNAL`);
- unordered bag of the three internal states (`BAG_INTERNAL`);
- whether any `LEVEL_RETEST` appeared;
- number of expansion blocks;
- number of shallow/deep pullback blocks.

The exact order is preserved for the primary path analysis.

## Primary future outcome: new leg vs level failure

At T+30 record the maximum signed close distance achieved from T+1 through T+30:

`peak_T30`.

During T+31…T+60:

- **NEW_LEG** occurs on the first close reaching `x_t >= peak_T30 + 0.30 ATR`.
- **LEVEL_FAILURE** occurs on the first close reaching `x_t <= +0.05 ATR`.
- if both thresholds are never reached, outcome = `UNRESOLVED`.

If both thresholds would appear in different minutes, the earlier close wins. Because closes are used, there is no same-bar ambiguity.

Primary resolved target:

`NEW_LEG_BEFORE_LEVEL_FAILURE = 1` for NEW_LEG, `0` for LEVEL_FAILURE. UNRESOLVED is excluded only from the binary AUC, but its frequency is reported.

Secondary outcomes:
- next-30m acceptance persistence: at least 20/30 closes remain `x_t>0`;
- terminal side after 30m;
- maximum additional directional extension beyond `peak_T30`.

## Probability estimator

Train on Discovery only, resolved events only.

Beta(1,1) smoothed empirical probability of NEW_LEG.

Frozen backoff:
1. exact 3-state INTERNAL_PATH if Discovery resolved N>=50;
2. else last two ordered internal states if N>=50;
3. else final internal state probability.

Also estimate snapshot-only and unordered-bag probabilities for the same events.

No threshold optimization and no P&L optimization.

## Primary evaluation

Confirmation, strong-bias universe:
- census and resolved/unresolved rates;
- NEW_LEG rate by each token and top internal paths;
- `LEVEL_RETEST` path vs no-level-retest path outcome gap;
- ordered-path ROC AUC / Brier on resolved NEW_LEG target;
- snapshot and bag AUC / Brier;
- ordered-minus-snapshot and ordered-minus-bag;
- calendar-week cluster bootstrap of AUC differences, 4000 resamples, seed 20260823;
- probability quintile calibration;
- BUY/SELL mirror;
- MID/HIGH/LOW breadth;
- 2024 / 2025-H1 transfer;
- matched bags with different order where both paths have enough observations.

## Frozen gates

Primary = Confirmation / STRONG_ACCEPTANCE / T+30 internal path / resolved NEW_LEG target.

- `G0_DATA_CAUSALITY`: canonical SHA valid, T+16…T+30 strictly after Bias decision, future outcome starts T+31, holdout sealed.
- `G1_POWER`: >=2,000 strong-bias Confirmation events and >=1,200 resolved outcomes.
- `G2_LEVEL_RETEST_ADVERSE`: no-LEVEL_RETEST NEW_LEG rate exceeds any-LEVEL_RETEST rate by >=15 percentage points in both Discovery and Confirmation.
- `G3_INTERNAL_PATH_PREDICTIVE`: Confirmation ORDERED_PATH AUC >=0.65.
- `G4_ORDER_INCREMENTAL`: ORDERED AUC exceeds SNAPSHOT by >=0.01 and lower weekly bootstrap CI >0.
- `G5_ORDER_BEATS_BAG`: ORDERED AUC exceeds BAG by >=0.01 and lower weekly bootstrap CI >0.
- `G6_CONSTRUCTIVE_PATH_EXISTS`: at least one exact no-LEVEL_RETEST path has Discovery N>=100, Confirmation N>=100, and NEW_LEG rate >=70% in both splits.
- `G7_DIRECTION_MIRROR`: BUY and SELL ordered AUC each >=0.60.
- `G8_LEVEL_BREADTH`: MID/HIGH/LOW ordered AUC each >=0.60.
- `G9_YEAR_TRANSFER`: 2024 and 2025-H1 ordered AUC each >=0.60.
- `G10_CALIBRATION`: top ordered-probability quintile NEW_LEG rate exceeds bottom by >=25 percentage points.

## Verdicts

- `INTERNAL_STRUCTURE_MAP_CONFIRMED`: all G0..G10 pass.
- `INTERNAL_STRUCTURE_USEFUL_ORDER_NOT_INCREMENTAL`: G0,G1,G2,G3,G6,G7,G8,G9,G10 pass but G4/G5 fail.
- `DEEP_RETEST_ADVERSE_BUT_NO_INTERNAL_EDGE`: G2 passes but G3/G6 fail.
- `NO_ACCEPTED_SIDE_INTERNAL_STRUCTURE_EDGE`: G2 and/or G3 fail with no robust constructive path.
- `INVALID_DATA_CAUSALITY`: G0 fails.

No entry, economics, holdout opening, EA deployment, or live allocation is authorized by LAB011.
