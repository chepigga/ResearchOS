# XAU_CAUSAL_CONTEXT_ROUTER_ABLATION_LAB_001 — PREREG

## Purpose
Test whether the already-frozen ZynAlgo-Context-inspired causal H4 router enriches the existing XAU causal candidate pool. This is an event-level ablation, not an executable portfolio backtest and not a new optimization of the XAU alpha.

## Data
- Canonical native XAU M1 release asset: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv` from release `ak47`.
- Required SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Candidate universe: `Projects/XAU_Pool/Results/XAU_POOL_SELECTION_LAB_001/v001/Artifacts/pool_excess.parquet`.
- Primary outcome is `excess = R - month×direction×TF drift baseline`, already frozen by LAB001. Raw `R` is secondary.

## Event clock
LAB001 stores each candidate at the opening timestamp of its signal bar, while execution begins only after that bar is complete. Therefore the causal candidate availability time is fixed as:
- M5: `time + 5 minutes`
- M15: `time + 15 minutes`
- H1: `time + 60 minutes`
The router uses H4 bars. An H4 bar labeled `[t,t+4h)` becomes available only at `t+4h`. Context is attached by backward as-of merge on these availability timestamps. No incomplete H4 bar is permitted.

## Router
Copied unchanged from `CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001` preregistration. No XAU-specific threshold or weight is allowed.

Inputs: EMA20/50/200, normalized EMA slope, ATR14/trailing ATR ratio, RSI14, ADX14, 24-bar range compression, prior-20-bar breakout/sweep, EMA spread in ATR, distance to EMA20/50 in ATR, relative tick volume, rejection wick.

Raw scores (0..100):
### EXPANSION
- 25 ordered EMA stack with directional slope
- 20 prior-20-bar close breakout
- 20 ATR expansion
- 15 ADX trend strength
- 10 relative tick-volume expansion
- 10 displacement from EMA20

### PULLBACK
- 30 ordered EMA stack
- 25 near EMA20/EMA50
- 15 RSI pullback/neutral band
- 15 ADX >= 18
- 15 no fresh breakout and ATR ratio not extreme

### REVERSAL
- 30 failed prior-20-bar high/low sweep
- 25 RSI extreme then causal turn
- 15 close crosses EMA20
- 15 ADX decelerates
- 15 rejection wick >=45% of candle range

### RANGE
- 25 ADX <20
- 25 24-bar range compressed versus trailing median
- 20 EMA20/50/200 spread <1 ATR
- 15 ATR ratio <0.95
- 15 no ordered EMA stack

State machine:
- 3-H4-bar rolling mean per score.
- Current-state inertia +5.
- Low vol ATR ratio <0.80: min hold 4 H4 bars, switch gap 12.
- Normal: min hold 3, switch gap 8.
- High vol ATR ratio >1.35: min hold 2, switch gap 5.

Directional bias:
- BULL = EMA20>EMA50>EMA200 and normalized EMA50 slope >0.
- BEAR = EMA20<EMA50<EMA200 and normalized EMA50 slope <0.
- else NEUTRAL.

## Frozen variants
A. `BASELINE`: all causal candidates with finite R and excess.
B. `PRIMARY_PULLBACK_EXPANSION`: regime in {PULLBACK, EXPANSION}; no direction condition.
C. `STRICT_DIRECTION_MATCH`: B plus BUY only in BULL and SELL only in BEAR. Secondary diagnostic only; it cannot replace B post-hoc.
D. `NEG_CONTROL_REVERSAL_RANGE`: regime in {REVERSAL, RANGE}.

## Primary metrics
- N / retention
- mean excess R
- median excess R
- P(excess > 0)
- raw mean R / P(R > 0)
- week-cluster bootstrap 95% CI for mean excess
- transfer by calendar year, TF, direction, and year×direction

Because LAB001 candidates overlap by design, CumR, portfolio PF and max DD are explicitly NOT interpreted here.

## Preregistered enrichment gates for PRIMARY
1. retention >=35%
2. mean excess > BASELINE
3. mean excess > NEGATIVE CONTROL
4. P(excess>0) > BASELINE
5. raw mean R > BASELINE
6. cluster-bootstrap lower 95% bound of PRIMARY mean excess > 0
7. mean excess is positive in at least 3 distinct calendar years represented by >=100 PRIMARY events each

Passing these gates means `PROMISING_EVENT_ENRICHMENT`; it does not authorize EA/live use. Failure means the hard Context gate is rejected for this XAU candidate universe. `STRICT_DIRECTION_MATCH` remains diagnostic regardless of result.
