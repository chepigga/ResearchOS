# GC_XAU_POST_SIGNAL_PATH_GEOMETRY_LAB_007 — PREREGISTRATION

Status: **FROZEN BEFORE LAB007 PATH RESULTS**

Purpose: characterize executable FTMO XAUUSD path geometry after the frozen GC `BUYER_BREAKOUT_LONG_001` signal. This is post-discovery execution research on the same historical window, **not independent OOS certification**.

## Signal governance

GC signal is unchanged from LAB003/004/006:
- M1 completed GC bar
- `delta_frac >= prior240 Q90`
- aggressive BUY volume `>= prior240 Q75`
- current High reaches/exceeds prior 20 completed M1 highs
- bullish body / positive impact
- close in top 25% of current bar
- signal known only after completed M1 bar

No GC threshold/session/regime filter may be changed in LAB007.

## Primary cohort

Primary = exact common-clock candidate events present in both AMP/CQG and reconstructed Rithmic ledgers from LAB006, executable on FTMO XAUUSD. Expected N from LAB006 = 246.

Secondary = all executable AMP candidate events, reported separately. It cannot replace the primary cohort based on outcome.

## XAU execution source

Same FTMO-Demo raw `COPY_TICKS_ALL` Bid/Ask files as LAB006, 2026-08-03 through 2026-09-15. Frozen clock mapping from LAB006: `FTMO clock = UTC + 180 min`.

LONG execution conventions:
- market/retest fills use Ask;
- exits and path marking use Bid;
- spread is therefore naturally included;
- no commission and no discretionary slippage are added in LAB007.

Reference volatility = causal XAU M1 ATR14 already attached to each LAB006 candidate event.

## Frozen time budget

All geometry uses a hard horizon of **30 minutes from the original GC-derived XAU entry target**, not 30 minutes from a delayed limit fill. Waiting for a retest consumes the same 30-minute budget.

## Entry geometries

No entry geometry is selected ex ante as the winner; all are mapped:

1. `MARKET` — first executable Ask after target time (LAB006 convention).
2. `LIM_025ATR_5M` — Buy Limit at market-reference Ask minus `0.25 * ATR`, expires after 5 minutes.
3. `LIM_050ATR_5M` — Buy Limit at market-reference Ask minus `0.50 * ATR`, expires after 5 minutes.
4. `LIM_050ATR_10M` — Buy Limit at market-reference Ask minus `0.50 * ATR`, expires after 10 minutes.
5. `LIM_075ATR_10M` — Buy Limit at market-reference Ask minus `0.75 * ATR`, expires after 10 minutes.
6. `LIM_100ATR_10M` — Buy Limit at market-reference Ask minus `1.00 * ATR`, expires after 10 minutes.

A limit is filled only when observed FTMO Ask is `<= limit_price`. Fill price is conservatively recorded at the limit price even if Ask trades through it. Unfilled limit = no trade and contributes **0R per original signal**.

## Frozen stop/target map

This LAB maps, but does not optimize/select, the following brackets:

- Stop distance `1.0 ATR`, targets `1.5R`, `2.0R`, `3.0R`.
- Stop distance `1.5 ATR`, targets `1.5R`, `2.0R`, `3.0R`.

All target ratios satisfy the user's minimum `TP >= 1.5 * SL` rule.

After fill:
- stop hit when Bid `<= stop_price`;
- target hit when Bid `>= target_price`;
- first passage wins;
- if neither is hit by the original +30m horizon, exit at first Bid tick at/after the horizon within 5 seconds and record realized R;
- if required timeout data are unavailable because of a session/data gap, mark `DATA_GAP` and exclude from per-trade outcome while reporting its count.

## Path diagnostics

Without choosing a strategy, report:
- adverse retracement distribution in the first 5m and 10m from market reference;
- MFE/MAE from each filled entry geometry to +30m;
- market-entry first-passage order for `SL1.0ATR` vs `TP1.5/2/3R` and `SL1.5ATR` vs `TP1.5/2/3R` at 15m and 30m;
- fill rate and median fill delay for every limit geometry;
- per-filled-trade EV(R), per-original-signal EV(R), PF, win rate, max DD(R), day-cluster CI95 of per-signal R, and TP/SL/timeout shares.

## Interpretation rule

LAB007 is descriptive/post-discovery. A favorable geometry becomes a **candidate for a separately frozen forward/OOS test**, not a validated live rule. No configuration may be relabeled as OOS or production-ready based on LAB007 alone.
