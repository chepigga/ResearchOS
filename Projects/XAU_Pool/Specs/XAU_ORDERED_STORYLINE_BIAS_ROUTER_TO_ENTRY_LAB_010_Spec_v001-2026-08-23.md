# XAU_ORDERED_STORYLINE_BIAS_ROUTER_TO_ENTRY_LAB_010 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-23  
**Parents:** LAB008 → LAB009 / `XAU_ORDERED_STORYLINE_BIAS_ENGINE_v001`

## Question

Does the frozen LAB009 ordered-storyline Bias Engine improve an entry engine that is defined independently of the bias probability?

LAB010 explicitly separates:

1. **Bias formation** at T+15 after a break; and
2. **Entry timing** after T+15 on a later role-flip retest.

No trade may be entered before the Bias Engine decision exists.

## Canonical data / embargo

- canonical input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- break universe: LAB008 frozen `break_census.csv`, `model_event=true`, `family=VWAP_VOLUME`
- Discovery: break time `< 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>=2025-07-01`

No post-holdout bars/events may be read for verdicts.

## Frozen Bias Engine

Use `XAU_ORDERED_STORYLINE_BIAS_ENGINE_v001` unchanged.

At T+15:
- construct three ordered 5-minute states using the LAB009 alphabet and priority;
- estimate `p_accept = P(ACCEPTANCE_PERSISTS)` from Discovery only;
- exact 3-state path if Discovery N>=50, else last-two-state backoff if N>=50, else snapshot-state probability;
- Beta(1,1) smoothing.

No LAB009 state definition, probability map, backoff rule, or training partition may change.

### Primary router

`STRONG_ACCEPTANCE = p_accept >= 0.75`

This threshold is frozen before LAB010 economics and is not selected from LAB009 Confirmation P&L.

Pre-registered diagnostics only:
- `p_accept < 0.25` = STRONG_REJECTION / veto cohort;
- probability quartile monotonicity of entry EV.

No reverse trade is authorized by low `p_accept` in LAB010.

## Independent post-bias entry engine

Entry engine knows the break direction and dynamic broken VWAP level, but not the Bias Engine probability.

After the T+15 Bias Engine decision, observe at most the next **30 completed M1 bars** (minutes T+16 through T+45).

The first bar `j` is a causal role-flip retest confirmation if:

1. price range touches the contemporaneous broken dynamic level within `±0.05 ATR_touch`:
   - `Low[j] <= Level[j] + 0.05*ATR_touch`
   - `High[j] >= Level[j] - 0.05*ATR_touch`
2. the completed bar closes back on the breakout side by at least `+0.03 ATR_touch`:
   - `break_dir * (Close[j] - Level[j]) / ATR_touch >= +0.03`
3. only the first qualifying retest is used.

Entry is the **next contiguous M1 open** after confirmation:
- upward break / BUY = AskOpen
- downward break / SELL = BidOpen

If no qualifying retest occurs, there is no entry candidate.

No intra-bar confirmation fill and no entry before T+15.

## Candidate comparison

Two systems use the exact same causal candidate generator:

### BASELINE_ENTRY
Trade every valid post-T+15 retest candidate.

### BIAS_ROUTED_ENTRY
Trade the same candidate only when the frozen T+15 `p_accept >= 0.75`.

Thus the only difference is the Bias Engine gate.

## Economics

Frozen from LAB004–LAB006 lineage:

- `1R = 0.50 * ATR_touch` from actual entry
- hard stop = 1R
- primary target = 1.5R
- secondary target = 2.0R
- max hold = 60 minutes from entry
- BUY exits evaluated on future Bid OHLC
- SELL exits evaluated on future Ask OHLC
- same-M1 TP+SL = conservative LOSS
- no hit = executable closing quote at horizon, clipped to `[-1,targetR]`

Costs:
- spread embedded through Bid/Ask
- commission proxy = `$5 round-turn/lot` = `$0.05` XAU price-equivalent
- additional cost stress = `$0.10` price-equivalent round trip

## Serial portfolios

Build separate chronological serial portfolios for BASELINE_ENTRY and BIAS_ROUTED_ENTRY:

- one position at a time;
- no hedging, pyramiding, averaging, grid, martingale;
- simultaneous opposite-direction entry candidates at the same minute are skipped as conflicts;
- while in position, later candidates are ignored;
- risk metrics are expressed in R.

Independent candidate metrics are also reported so serial overlap cannot hide selection quality.

## Evaluation

For Discovery and Confirmation report:

- break count;
- valid post-T+15 retest candidate count and fill rate;
- routed count/rate;
- median wait from T+15 to retest and entry;
- baseline vs routed independent EV, PF, TP rate;
- baseline vs routed serial EV, PF, frequency, total R;
- BUY/SELL and MID/HIGH/LOW routed EV;
- BACKOFF source (`EXACT_3/LAST_2/SNAPSHOT`) diagnostics;
- 1.5R / 2R;
- max DD, worst day, max consecutive losses;
- cost stress;
- `p_accept` quartile vs EV monotonicity;
- low-probability (`p<0.25`) veto cohort economics.

Calendar-week cluster bootstrap, 4000 resamples, seed `20260823`:

1. Confirmation routed serial weekly mean R;
2. Confirmation **independent** weekly mean EV difference: STRONG_ACCEPTANCE candidates minus all baseline candidates in the same calendar week.

## Frozen gates

Primary = Confirmation / BIAS_ROUTED_ENTRY / serial / 1.5R.

- `G0_DATA_CAUSALITY`: canonical SHA valid, required Bid/Ask fields present, no entry before T+15, holdout sealed.
- `G1_POWER`: routed Confirmation serial N >= 300 and >= 5 trades/week.
- `G2_ROUTED_EV`: routed Confirmation EV > 0 and PF > 1.0.
- `G3_WEEK_CI`: lower 95% weekly cluster CI of routed mean R > 0.
- `G4_INCREMENTAL_LIFT`: routed independent EV > baseline independent EV and lower 95% week-cluster CI of routed-minus-baseline EV > 0.
- `G5_SPLIT_TRANSFER`: routed Discovery and Confirmation serial EV both > 0.
- `G6_2R_SURVIVAL`: routed Confirmation 2R serial EV >= 0.
- `G7_DIRECTION_BREADTH`: routed Confirmation BUY EV > 0 and SELL EV > 0.
- `G8_LEVEL_BREADTH`: routed Confirmation MID/HIGH/LOW independent EV each >= 0.
- `G9_PROP_DD_PROXY`: routed serial max DD <= 20R and worst calendar day > -16R.
- `G10_COST_STRESS`: routed 1.5R EV remains > 0 under additional $0.10 price-equivalent stress.
- `G11_ROUTER_MONOTONICITY`: highest `p_accept` quartile independent EV > lowest quartile independent EV in Confirmation.

## Verdicts

- `BIAS_ROUTER_EXECUTABLE_EDGE`: all G0..G11 pass.
- `BIAS_ROUTER_POSITIVE_BUT_NARROW`: G2/G3/G4/G5 pass but one or more breadth/power/stress/DD gates fail.
- `BIAS_IMPROVES_BUT_NOT_PROFITABLE`: G4 passes but G2 fails.
- `NO_BIAS_ROUTER_ENTRY_LIFT`: G4 fails or no robust transfer.
- `INVALID_DATA_CAUSALITY`: G0 fails.

No automatic holdout opening, EA deployment, or live allocation.

## Anti-overfit

LAB010 does not optimize after outcomes:
- T+15 Bias Engine clock;
- LAB009 states/probability estimator;
- `p_accept >= 0.75` primary router;
- 30-minute retest window;
- ±0.05 ATR touch zone;
- +0.03 ATR confirmation close;
- first retest only;
- next-M1-open entry;
- 0.50 ATR stop;
- 1.5R / 2R targets;
- 60-minute hold;
- cost assumptions;
- serial lifecycle;
- gates.
