# XAU_VWAP_SEQUENCE_PLACEBO_AND_EXECUTION_FRONTIER_LAB_003 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-22  
**Parent:** XAU_VWAP_TOUCH_RESPONSE_VS_ACCEPTANCE_CAUSAL_MAP_LAB_002

## Question

Does the transferable post-touch sequence from LAB002 contain information that is specific to the current-session tick-volume VWAP location, or is it generic short-horizon path persistence that also appears around similarly constructed placebo levels?

Secondarily, how much of the T+5 information is already available at executable causal clocks T+1 and T+3?

## Data / embargo

Canonical input only:

- `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- source/platform clock; intraday anchor 01:00 platform time
- Discovery: `< 2024-01-01`
- Internal confirmation: `2024-01-01 <= t < 2025-07-01`
- sealed holdout: `>= 2025-07-01`

The holdout is not read by the default run and is not authorized in LAB003.

## Frozen level families

All lines are causal at each minute.

### A. `VWAP_VOLUME` — primary
Same as LAB002:
- typical price `(BidHigh + BidLow + BidClose)/3`
- broker `tick_volume`
- intraday cumulative VWAP from 01:00
- weighted SD
- `MID = VWAP`
- `HIGH/LOW = VWAP ± 1.618 * weighted_SD`

### B. `ANCHOR_MEAN` — same-clock volume ablation
- cumulative unweighted mean of M1 typical price from 01:00
- cumulative unweighted SD
- `MID/HIGH/LOW = mean ± 1.618 * SD`

This tests whether tick-volume weighting matters.

### C. `LAGGED_VWAP_SHAPE` — location placebo
For each current session and minute-offset from 01:00:
- take the **previous completed trading session's** VWAP MID/HIGH/LOW trajectory at the same minute-offset;
- translate the previous trajectory by the difference between current-session first M1 open and previous-session first M1 open;
- no current-session volume or future prices are used in the placebo line.

This preserves a realistic VWAP-like moving shape and band spacing while deliberately putting yesterday's intraday VWAP geometry into today's price path.

No placebo offset or multiplier is optimized.

## Touch universe — frozen from LAB002

For every family and each of MID/HIGH/LOW:
- touch tolerance: `0.05 * completed M15 ATR14`
- a new episode is armed only after close-distance reaches `>= 0.25 ATR`
- arrival side is the first close in the previous 5 completed M1 bars more than `0.05 ATR` from the line
- event requires consecutive M1 bars through T+5
- events with insufficient forward horizon are excluded
- same line may generate repeated episodes only after re-arm

## Causal decision clocks

For `k in {1,3,5}` minutes after touch:
- signed side `s_k = arrival_side * (Close[t+k] - Level[t+k]) / ATR_touch`
- `BACK`: `s_k >= +0.10`
- `THROUGH`: `s_k <= -0.10`
- `NEUTRAL`: otherwise

`BACK` predicts later REJECTION.  
`THROUGH` predicts later ACCEPTANCE.  
`NEUTRAL` is no-decision.

This three-state classifier is fixed across all level families and clocks.

## Future label

Primary label is the LAB002 `0.50 ATR` response label, unchanged:
- the label window begins only **after T+5**, regardless of decision clock;
- REJECTION barrier = `+0.50 ATR` back toward arrival side from the touched level at T0;
- ACCEPTANCE barrier = `-0.50 ATR` through the touched level;
- first barrier reached within 60 minutes wins;
- same-M1 dual hit = AMBIGUOUS;
- neither hit = UNRESOLVED.

Thus T+1/T+3/T+5 are compared against exactly the same future label; there is no hidden shortening of the target horizon.

## Primary statistics

For each split × family × clock:
- N touches
- decision coverage = fraction BACK or THROUGH
- resolved decision N
- directional accuracy:
  - BACK correct if future label REJECTION
  - THROUGH correct if future label ACCEPTANCE
- rejection rate among BACK
- rejection rate among THROUGH
- separation = `P(REJECTION|BACK) - P(REJECTION|THROUGH)`

### Paired weekly incremental tests

Within each `week × arrival_side` cell:
- compute separation for each family if both BACK and THROUGH each have >=5 resolved events;
- compare:
  1. `VWAP_VOLUME - ANCHOR_MEAN`
  2. `VWAP_VOLUME - LAGGED_VWAP_SHAPE`

Bootstrap paired week-side differences, 4000 resamples, seed `20260822`.

Primary specificity is evaluated at T+3. T+1 and T+5 are transfer/frontier diagnostics, not alternative optimization targets.

## Frozen gates

- `G0_DATA_CLOCK`: canonical SHA matches; tick_volume present; holdout false.
- `G1_VWAP_MAP_TRANSFER`: VWAP_VOLUME separation is positive in both Discovery and Confirmation at T+1, T+3 and T+5.
- `G2_VWAP_OVER_MEAN_T3`: lower 95% paired week-side bootstrap CI of `(VWAP_VOLUME - ANCHOR_MEAN)` separation at T+3 is `> 0`.
- `G3_VWAP_OVER_LAGGED_T3`: lower 95% paired week-side bootstrap CI of `(VWAP_VOLUME - LAGGED_VWAP_SHAPE)` separation at T+3 is `> 0`.
- `G4_T1_RETAINS_SIGNAL`: in Confirmation, VWAP_VOLUME T+1 separation is at least 60% of VWAP_VOLUME T+5 separation.
- `G5_DIRECTION_MIRROR`: in Confirmation T+3, VWAP_VOLUME separation is positive for arrival from ABOVE and BELOW separately.
- `G6_LEVEL_BREADTH`: in Confirmation T+3, VWAP_VOLUME separation is positive for MID, HIGH and LOW separately.

## Verdicts

- `VWAP_SPECIFIC_SEQUENCE_EDGE`: all G0..G6 pass.
- `GENERIC_SEQUENCE_NOT_VWAP_SPECIFIC`: G1/G4/G5/G6 pass but either G2 or G3 fails.
- `SEQUENCE_NOT_STABLE`: G1/G5/G6 fail.
- `INVALID_DATA_CLOCK`: G0 fails.

No holdout opening and no EA/live allocation follow automatically.

## Explicit anti-overfit rules

LAB003 does **not** optimize:
- anchor hour;
- band multiplier;
- touch/re-arm distance;
- +/−0.10 decision threshold;
- T+1/T+3/T+5 clocks;
- 0.50 ATR future barriers;
- 60-minute horizon;
- session subsets;
- BUY/SELL filters;
- trend/news/iFVG filters;
- placebo translation.

No 1.5R/2R or next-VWAP-level economics are tested unless LAB003 first shows VWAP-specific incremental information.
