# XAU_POST_TOUCH_SEQUENCE_EXECUTION_ECONOMICS_LAB_004 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-22  
**Parents:** LAB002 + LAB003

## Question

Does the transferable causal post-touch sequence (`BACK` vs `THROUGH`) remain economically positive when the trade is entered at the actual causal decision clock, using canonical Bid/Ask execution, a hard stop, and minimum R:R >= 1:1.5?

This LAB tests execution economics. It does not attempt to re-prove VWAP specificity; LAB003 already found the sequence mostly generic.

## Canonical data / embargo

- `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- source/platform clock; anchored session begins 01:00 platform time
- Discovery: `< 2024-01-01`
- Confirmation: `2024-01-01 <= decision_time < 2025-07-01`
- sealed holdout: `>= 2025-07-01`

Default run excludes the holdout before event generation. LAB004 is not authorized to open it.

## Level / touch universe

Primary level family: `VWAP_VOLUME` MID/HIGH/LOW exactly as LAB002/003:
- M1 typical price `(BidHigh + BidLow + BidClose)/3`
- broker tick_volume
- cumulative intraday VWAP from 01:00
- weighted SD bands at `±1.618 SD`

Execution-control family: `ANCHOR_MEAN` MID/HIGH/LOW:
- same 01:00 anchor
- unweighted cumulative mean and SD
- same `±1.618 SD`

Touch episodes are frozen from LAB002/003:
- touch tolerance `0.05 * completed M15 ATR14`
- episode re-arms after close-distance `>= 0.25 ATR`
- arrival side = first close in prior 5 completed M1 bars farther than `0.05 ATR` from the line
- consecutive M1 bars required through the selected decision clock

No lagged placebo is needed for the primary economics verdict because LAB003 already established lack of VWAP specificity.

## Decision clocks / signal

For `k in {1,3,5}`:

`s_k = arrival_side * (BidClose[t+k] - Level[t+k]) / ATR_touch`

- `BACK` if `s_k >= +0.10`
- `THROUGH` if `s_k <= -0.10`
- otherwise `NEUTRAL` => no trade

Trade direction:
- BACK => `direction = arrival_side` (trade rejection back toward arrival side)
- THROUGH => `direction = -arrival_side` (trade acceptance through the level)

`T+3` is the preregistered primary clock. T+1 and T+5 are frontier diagnostics only.

## Entry / stop / target

Decision is made only after the completed M1 close at `t+k`.

- BUY entry = `AskClose[t+k]`
- SELL entry = `BidClose[t+k]`
- fixed risk distance `1R = 0.50 * ATR_touch`
- hard stop = `1R`
- targets: `1.5R` primary and `2.0R` secondary
- max holding horizon = 60 minutes from decision time
- BUY exits are evaluated on future Bid OHLC
- SELL exits are evaluated on future Ask OHLC
- if TP and SL are both touched in the same M1 bar, count conservatively as **LOSS**
- if neither barrier is hit by 60 minutes, close at the last available executable quote and realize actual R, clipped to `[-1, targetR]`

The outcome begins immediately after the decision bar; there is no T+5 embargo in LAB004.

## Costs

Spread is already embedded through Bid/Ask entry and exit logic.

Base commission proxy:
- FTMO-style `$5 round-turn / lot`
- XAU standard contract proxy `100 oz / lot`
- equivalent price cost `$0.05` per round-turn per lot
- commission R-cost = `0.05 / risk_price`

This proxy is for research economics only; exact broker/prop contract specifications are required before final EA/live sizing.

Stress diagnostics (not alternative optimization targets):
- BASE: embedded spread + commission proxy
- STRESS_0p05: subtract an additional `$0.05` round-trip price-equivalent per trade
- STRESS_0p10: subtract an additional `$0.10` round-trip price-equivalent per trade

## Collision / portfolio rules

Two views are reported:

### A. Independent-event diagnostic
Every eligible signal is evaluated independently. This is NOT the primary deployability statistic.

### B. Serial executable portfolio — primary
For each family × clock × target:
1. collect all candidate decisions chronologically;
2. on a given decision minute, deduplicate same-direction candidates by keeping the largest `abs(s_k)`; ties: `MID > HIGH > LOW`;
3. if both LONG and SHORT remain on the same minute, skip that minute as a conflict;
4. permit at most one active position at a time;
5. while a position is active, ignore later signals until the position exits;
6. no pyramiding, hedging, martingale, or averaging.

Primary gates use this serial portfolio.

## Risk translation

Report P&L in R. For prop-risk intuition only, also translate serial results at fixed `0.25% equity risk per trade`:
- 1R = 0.25%
- 16R daily loss corresponds to 4% daily drawdown
- 20R overall drawdown corresponds to 5% equity

No compounding is used for the research summary.

## Primary statistics

For each split × family × clock × target:
- independent N / EV / PF / WR
- serial trades / trades per week
- serial EV R / PF / WR / total R
- max drawdown R
- worst calendar-day R
- max consecutive losses
- BUY and SELL EV separately
- yearly EV transfer
- base / +0.05 / +0.10 price-cost stress EV

Weekly bootstrap for serial T+3 1.5R:
- group serial trade R by calendar week
- bootstrap weekly mean-R-per-trade values, 4000 resamples, seed `20260822`
- report 95% CI of mean trade R using week clusters

## Frozen gates

Primary = `VWAP_VOLUME`, `T+3`, `1.5R`, serial portfolio, BASE costs.

- `G0_DATA_EXECUTION`: canonical SHA valid, Ask fields present, holdout false.
- `G1_CONFIRMATION_EV`: Confirmation serial EV > 0 and PF > 1.0.
- `G2_WEEK_CLUSTER_CI`: lower 95% week-cluster CI for Confirmation serial mean R > 0.
- `G3_SPLIT_TRANSFER`: Discovery and Confirmation serial EV are both > 0.
- `G4_2R_SURVIVAL`: Confirmation T+3 2R serial EV >= 0.
- `G5_T1_EXECUTABLE`: Confirmation T+1 1.5R serial EV > 0.
- `G6_DIRECTION_BREADTH`: Confirmation T+3 1.5R BUY EV > 0 and SELL EV > 0.
- `G7_PROP_DD_PROXY`: Confirmation T+3 1.5R max DD <= 20R and worst calendar day > -16R.
- `G8_COST_STRESS`: Confirmation T+3 1.5R EV remains > 0 under additional `$0.10` round-trip price-equivalent stress.

## Verdicts

- `GO_TO_REPLICATION`: all G0..G8 pass.
- `PROMISING_BUT_NOT_ROBUST`: G1 and G3 pass but one of G2/G4/G5/G6/G7/G8 fails.
- `NO_EXECUTABLE_EDGE`: G1 or G3 fails.
- `INVALID_EXECUTION_DATA`: G0 fails.

No holdout opening and no EA/live allocation follow automatically.

## Anti-overfit

LAB004 does not optimize:
- level anchor/bands;
- touch/re-arm thresholds;
- decision threshold ±0.10;
- T+1/T+3/T+5 clocks;
- risk distance 0.50 ATR;
- 1.5R/2R targets;
- 60-minute max hold;
- level subset;
- BUY/SELL subset;
- time-of-day/session/news filters;
- iFVG/trend/volatility filters;
- collision policy;
- cost assumptions after seeing outcomes.
