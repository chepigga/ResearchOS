# XAU_POST_TOUCH_SEQUENCE_RETEST_ENTRY_CAUSAL_LAB_005 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-23  
**Parents:** LAB002 + LAB003 + LAB004

## Question

Does the transferable post-touch directional state become economically tradable if we **do not chase the T+3 confirmation at market**, but instead wait for the first causal role-flip retest toward the touched dynamic level and enter only after that retest bar confirms the original direction?

LAB005 isolates **entry location / lifecycle**. It intentionally keeps the LAB004 risk distance, targets, cost model, and maximum holding horizon unchanged.

## Canonical data / embargo

- canonical input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- canonical LAB002 event universe: `XAU_VWAP_TOUCH_RESPONSE_VS_ACCEPTANCE_CAUSAL_MAP_LAB_002/v001/events.csv.gz`
- Discovery: decision time `< 2024-01-01`
- Confirmation: `2024-01-01 <= decision_time < 2025-07-01`
- sealed holdout: `>= 2025-07-01`

Default execution must not read/use post-2025-07-01 events or price bars for a reported verdict.

## Frozen directional state

Primary clock: `T+3` after the original VWAP touch, exactly as LAB003/LAB004.

For event arrival side `a ∈ {+1,-1}`:

`s3 = a * (BidClose[T+3] - dynamic_level[T+3]) / ATR_touch`

- `BACK` signal if `s3 >= +0.10`; trade direction `d = a`
- `THROUGH` signal if `s3 <= -0.10`; trade direction `d = -a`
- otherwise no signal

No state threshold optimization is allowed in LAB005.

`T+1` is retained only as a secondary frontier diagnostic using the same ±0.10 threshold. `T+5` is not primary because LAB004 already showed that later market confirmation did not create executable economics.

## Retest lifecycle — primary

After the completed T+3 decision bar:

1. **Do not enter at market.**
2. Observe completed M1 bars from `T+4` through `T+18` inclusive: frozen **15-minute retest window**.
3. At each candidate bar `j`, use the contemporaneous dynamic VWAP level of the original level type (`MID`, `HIGH`, or `LOW`).
4. A **retest touch** occurs when the M1 bar range reaches the role-flip zone within `±0.05 * ATR_touch` of that dynamic level.
5. A **retest confirmation** occurs on the same completed bar only if:

   `d * (BidClose[j] - Level[j]) / ATR_touch >= +0.03`

   meaning the bar closes back on the intended trade side by at least 0.03 ATR after touching the level zone.
6. The first qualifying retest-confirmation bar only is used.
7. The trade is entered at the **next contiguous M1 open** (`j+1`):
   - BUY = `AskOpen[j+1]`
   - SELL = `BidOpen[j+1]`
8. If no qualifying retest-confirmation appears inside 15 minutes, the signal is **UNFILLED**.
9. No limit-fill assumption at an intra-bar price is used. Confirmation is known at close; entry is next-bar executable open.

This deliberately tests a conservative causal version of the podcast lifecycle: confirmation → pullback/retest → renewed respect → entry.

## Entry / stop / target

To isolate entry-location improvement versus LAB004:

- fixed risk distance: `1R = 0.50 * ATR_touch`
- hard stop: 1R from actual retest entry
- primary target: `1.5R`
- secondary target: `2.0R`
- max holding horizon: 60 minutes from actual entry
- BUY exits: future Bid OHLC
- SELL exits: future Ask OHLC
- if TP and SL are both touched in the same M1 bar, count conservatively as LOSS
- if neither barrier is hit, close at the final executable quote at 60 minutes and realize clipped R in `[-1,targetR]`

No BE/trailing/partial exit is allowed.

## Costs

Same research cost model as LAB004:

- spread embedded through canonical Bid/Ask entry and exits
- commission proxy: `$5 round-turn / lot`
- XAU contract proxy: 100 oz/lot
- price-equivalent commission: `$0.05`
- commission R cost = `0.05 / risk_price`

Stress diagnostics:
- BASE
- additional `$0.05` round-trip price-equivalent
- additional `$0.10` round-trip price-equivalent

No cost assumptions may be changed after outcomes are inspected.

## Primary serial executable lifecycle

Primary deployability view is one lifecycle at a time:

1. chronological T+3 directional signals;
2. same decision minute: keep strongest `abs(s3)` per direction; level tie-break `MID > HIGH > LOW`;
3. if both LONG and SHORT remain on the same decision minute, skip as conflict;
4. when flat, accept the next signal and enter **PENDING_RETEST** state;
5. while pending (maximum 15m), ignore all other signals;
6. if pending expires unfilled, become flat after expiry;
7. if filled, hold one position until TP/SL/time exit;
8. while position is active, ignore later signals;
9. no pyramiding, averaging, martingale, or hedging.

Independent-signal results are diagnostic only.

## Fill / missed-move / adverse-selection diagnostics

For every eligible signal report:

- retest fill rate;
- median wait from decision to retest confirmation and to entry;
- entry improvement versus LAB004 T+3 market entry in ATR units and price units;
- fill rate separately for BACK / THROUGH, BUY / SELL, MID/HIGH/LOW, Discovery/Confirmation/year;
- among filled signals, conditional LAB002 `label_0p5` correctness rate;
- among unfilled signals, conditional LAB002 `label_0p5` correctness rate;
- **adverse-selection gap** = correctness(filled) − correctness(unfilled);
- missed-directional-move rate: unfilled signal whose frozen `label_0p5` agrees with the signal direction;

These are explanatory diagnostics, not optimization targets.

## Matched market-entry comparison

For each **filled retest signal**, also simulate the frozen LAB004 market entry at its original T+3 decision close using the same 0.50 ATR risk, same target, same 60m horizon, same Bid/Ask rules and costs.

Report paired `Retest_R - Market_R` by signal and by week.

Bootstrap paired weekly mean differences:
- calendar-week clusters
- 4000 resamples
- seed `20260823`

This comparison asks whether the retest lifecycle improves entry quality on the **same signals that actually fill**.

## Primary statistics

Primary = VWAP_VOLUME / T+3 / retest / 1.5R / serial lifecycle / BASE cost.

Report:
- eligible signals
- serial accepted signals
- fills / fill rate
- trades/week
- EV R / PF / TP rate / positive rate / total R
- gross EV before commission
- max DD R
- worst calendar day R
- max consecutive losses
- BUY / SELL EV
- BACK / THROUGH EV
- yearly EV
- 2R survival
- +0.05 / +0.10 stress EV
- paired retest-vs-market weekly bootstrap CI

Risk translation for prop intuition: 1R = 0.25% equity risk; no compounding.

## Frozen gates

Primary = Confirmation / T+3 / 1.5R / serial retest.

- `G0_DATA_EXECUTION`: canonical SHA valid, AskOpen/AskHigh/AskLow/AskClose present, holdout false.
- `G1_FILL_POWER`: Confirmation serial fills >= 500 and fill rate >= 10%.
- `G2_CONFIRMATION_EV`: Confirmation serial EV > 0 and PF > 1.0.
- `G3_WEEK_CLUSTER_CI`: lower 95% weekly cluster CI of Confirmation serial mean R > 0.
- `G4_SPLIT_TRANSFER`: Discovery and Confirmation serial EV both > 0.
- `G5_2R_SURVIVAL`: Confirmation T+3 2R serial EV >= 0.
- `G6_DIRECTION_BREADTH`: Confirmation BUY EV > 0 and SELL EV > 0.
- `G7_BRANCH_BREADTH`: Confirmation BACK EV > 0 and THROUGH EV > 0.
- `G8_PROP_DD_PROXY`: Confirmation max DD <= 20R and worst calendar day > -16R.
- `G9_COST_STRESS`: Confirmation 1.5R EV remains > 0 under additional $0.10 price-equivalent stress.
- `G10_RETEST_UPLIFT`: lower 95% CI of paired weekly `(Retest_R - Market_R)` on filled Confirmation signals > 0.

## Verdicts

- `GO_TO_REPLICATION`: all G0..G10 pass.
- `RETEST_EDGE_NARROW`: G2/G3/G4/G10 pass but one breadth/stress/DD gate fails.
- `RETEST_IMPROVES_BUT_NOT_PROFITABLE`: G10 passes but G2 fails.
- `NO_RETEST_EXECUTABLE_EDGE`: G2 or G4 fails and G10 does not establish a robust positive executable edge.
- `INVALID_EXECUTION_DATA`: G0 fails.

No holdout opening and no EA/live allocation follow automatically.

## Anti-overfit

LAB005 does **not** optimize after outcomes:
- state clock or ±0.10 signal threshold;
- 15m retest window;
- ±0.05 ATR retest zone;
- +0.03 ATR confirmation close;
- next-bar-open entry rule;
- 0.50 ATR stop;
- 1.5R / 2R targets;
- 60m hold;
- MID/HIGH/LOW subset;
- BUY/SELL or BACK/THROUGH subset;
- session/time/news/volatility filters;
- iFVG requirement;
- collision policy;
- transaction-cost assumptions.

If this LAB fails, later work must change **one clearly stated dimension** in a new preregistered LAB rather than tuning this result.
