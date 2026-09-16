# GC_XAU_LIMIT_ORDER_DEPTH_EXPIRY_STABILITY_LAB_008 — PREREG

Status: PREREGISTERED BEFORE LAB008 OUTCOME

## Purpose

Continue from LAB007 by testing only XAU limit-entry geometry. The GC BUYER_BREAKOUT_LONG_001 selector is frozen and is not changed. This is a post-discovery execution study, not independent OOS validation.

## Frozen cohorts

Primary: exact common-clock executable AMP∩Rithmic GC signals from LAB006/LAB007.
Secondary: all executable AMP-native signals.

## Frozen exit/risk geometry

To isolate the limit-order effect, LAB008 does NOT sweep stop/target/time-stop.

- LONG only.
- Entry: Buy Limit below the LAB006 market-reference Ask.
- Stop: 1.5 XAU ATR14(M1) below filled limit price.
- Take profit: 3R = 4.5 XAU ATR above filled limit price.
- Hard timeout: 30 minutes from the original GC signal execution timestamp, not from fill.
- Unfilled limit order: 0R for EV-per-signal.
- FTMO Ask is used for limit fill eligibility; Bid is used for SL/TP/timeout exit path.
- Quoted spread is therefore embedded in the executable path. No discretionary slippage or commission is added.

## Bounded limit grid

Depth below market-reference Ask, in frozen XAU ATR14(M1):

- 0.50 ATR
- 0.75 ATR
- 1.00 ATR
- 1.25 ATR
- 1.50 ATR

Expiry after original executable signal timestamp:

- 3 minutes
- 5 minutes
- 10 minutes
- 15 minutes

Total: 20 limit geometries. No other depth/expiry is tested in LAB008.

## Stability diagnostics

For each geometry and cohort report:

- signals, fills, fill rate;
- TP / SL / timeout counts;
- EV R per signal (unfilled = 0R);
- EV R per filled trade;
- PF;
- max drawdown in R-per-signal sequence;
- win rate on filled trades;
- day-cluster bootstrap 95% CI of EV R/signal;
- median fill delay;
- early vs late time-split EV and PF.

Time split is descriptive only because the parent signal and some geometry were already observed in LAB007:

- EARLY: signal time < 2026-09-01 00:00 UTC
- LATE: signal time >= 2026-09-01 00:00 UTC

## Robustness interpretation

Do not promote a single isolated maximum. A useful limit candidate should preferably show:

1. EV R/signal > 0 on COMMON_CLOCK and AMP_ALL;
2. EV R/signal > 0 in both EARLY and LATE on COMMON_CLOCK;
3. fill rate >= 40%;
4. PF > 1.0;
5. at least one adjacent depth/expiry geometry also has positive EV R/signal on COMMON_CLOCK.

These are descriptive stability gates, not proof of OOS edge. Any selected geometry from LAB008 must be frozen before a later untouched forward/OOS test.
