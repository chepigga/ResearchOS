# CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001 — PREREG

## Purpose
Test whether a ZynAlgo-Context-inspired but independently specified causal regime router adds incremental value to frozen BTC/XAU alphas by selecting market state, without changing any entry/exit threshold in the frozen alpha.

## Contamination rule
This is a discovery/ablation on reused historical data, NOT a new validation of BTC SHORT v1. No alpha threshold may be changed after results are seen. Router parameters below are fixed before execution.

## Information clock
- BTC frozen entries are treated as M15-class execution events.
- Router clock = H4.
- Only a fully closed H4 bar is available. H4 bar [t,t+4h) becomes usable at t+4h.
- No current/incomplete H4 values are allowed.

## Inputs (price-only, causal)
EMA20/50/200, normalized EMA slopes, ATR14 and trailing ATR ratio, RSI14, ADX14, 24-bar range compression, 20-bar prior high/low breakout/sweep, EMA spread in ATR units, distance to EMA20/50 in ATR units, relative volume, rejection wick.

## Raw regime scores (0..100, fixed weights)
### EXPANSION
- 25: ordered EMA stack with directional slope
- 20: close breaks prior 20-bar high/low
- 20: ATR ratio expansion
- 15: ADX trend strength
- 10: relative volume expansion
- 10: displacement away from EMA20

### PULLBACK
- 30: ordered EMA stack
- 25: price near EMA20 or EMA50
- 15: RSI in pullback/neutral band
- 15: ADX >= 18
- 15: no fresh 20-bar breakout and ATR ratio not extreme

### REVERSAL
- 30: failed 20-bar high/low sweep
- 25: RSI extreme then causal turn
- 15: close crosses EMA20
- 15: ADX decelerates
- 15: rejection wick >= 45% of candle range

### RANGE
- 25: ADX < 20
- 25: 24-bar range compressed vs its trailing median
- 20: EMA20/50/200 spread < 1 ATR
- 15: ATR ratio < 0.95
- 15: no ordered EMA stack

## State machine
- 3-bar rolling mean of each raw score.
- Current-state inertia bonus = +5 score points.
- Default minimum hold = 3 H4 bars.
- Low volatility ATR ratio < 0.80: min hold 4, switch gap 12.
- Normal volatility: min hold 3, switch gap 8.
- High volatility ATR ratio > 1.35: min hold 2, switch gap 5.
- State switches only if best challenger exceeds current state after inertia by required gap and minimum hold has elapsed.

## Directional bias
- BULL: EMA20 > EMA50 > EMA200 and EMA50 normalized slope > 0.
- BEAR: EMA20 < EMA50 < EMA200 and EMA50 normalized slope < 0.
- otherwise NEUTRAL.

## Frozen BTC variants
A. BASELINE = all frozen PERSISTENT_EXIT SHORT v1 trades at 5 bps costs.
B. PRIMARY = regime in {PULLBACK, EXPANSION}; no directional condition.
C. STRICT = PRIMARY plus BEAR bias.
D. NEGATIVE CONTROL = regime in {REVERSAL, RANGE}.

Primary interpretation is fixed to B. C is secondary diagnostic only; it cannot replace B after results are seen.

## Metrics
Trade count/retention, EV/trade, PF, CumR, CumR per baseline trade, maxDD R, DD at 0.25% and 0.50% risk, win rate, max loss streak, recovery factor, yearly/period transfer, 7-day cluster bootstrap.

## Evidence standard
Router is interesting only if PRIMARY improves EV, PF and recovery factor versus BASELINE, has lower absolute DD, and beats NEGATIVE CONTROL without collapsing to a tiny sample. Even if it passes, reused-history result remains discovery-only and must be frozen and tested on fresh/native broker data next.

## XAU rule
No surrogate GC/Yahoo data is permitted. XAU is executed only if the repository contains the native/clean XAU dataset required by the existing XAU research lineage. If absent, status must be `BLOCKED_NATIVE_XAU_DATA_NOT_IN_REPO`; BTC result must not be generalized to XAU.
