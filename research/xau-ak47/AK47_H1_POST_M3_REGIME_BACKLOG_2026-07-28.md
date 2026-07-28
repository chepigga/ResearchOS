# AK47 H1 — Post-M3 Regime Awareness Backlog

**Date:** 2026-07-28

## Problem

After `M3_GIVEBACK_EXIT`, the EA immediately becomes eligible to place a new OCO because there is no open position. It does not determine whether the market is continuing, reversing, balancing, exhausting, or failing to accept the breakout.

Root cause:

> The EA sees execution availability, not market-state validity.

## Evidence

Rejected branches:

- one-hour lock;
- directional episode lock;
- structural reset;
- fresh-bar re-arm.

Fresh-bar candidate result:

- 326 trades;
- Net -$964.84;
- PF 0.983;
- Expected Payoff -$2.96;
- Max Equity DD 7.21%;
- Win Rate 45.71%.

Baseline M3:

- 364 trades;
- Net +$4,664.50;
- PF 1.091;
- Max Equity DD 6.54%.

Conclusion: timing contamination was real descriptively, but waiting for a fresh bar did not create edge.

## Correct architecture

Current:

```text
H1 range completed
→ place BUY STOP and SELL STOP
```

Required:

```text
H1 state completed
→ classify local market state
→ decide whether breakout trading is permitted
→ determine allowed direction
→ place one-sided order or skip
```

## Updated target states

The first classification should not immediately be BUY/SELL. It should determine whether the local auction is suitable for breakout trading:

- TREND_EXPANSION;
- BALANCED_VOLATILITY;
- COMPRESSION;
- EXHAUSTION;
- TWO_SIDED_INSTABILITY.

Only after an expansion-ready state is identified should the system classify continuation or reversal direction.

## Primary next lab

`AK47_H1_POST_M3_VOLATILITY_STATE_LAB_001`

The first version must be a non-invasive Python/export research lab. It must not alter the original trading path.

### Required identifiers

- episode_id;
- source position_id;
- M3 exit time/direction/price;
- source EpisodeHigh/EpisodeLow;
- peak MFE_R;
- M3 close_R.

### Required features

- H1 OHLC;
- ATR14 and ATR change;
- range/ATR;
- body/range;
- wick ratios;
- close location;
- overlap with prior bars and source episode;
- displacement from M3 exit;
- penetration/reclaim of source range;
- midpoint cross;
- 2–4 bar directional efficiency;
- direction changes;
- side switches;
- high/low break counts;
- compression and expansion counts;
- climax-range flag;
- previous expansion duration.

### Outcomes

Calculate independently for BUY and SELL:

- trigger;
- trigger time;
- MFE_R;
- MAE_R;
- final outcome_R;
- holding time;
- execution-cost estimate.

### Causal control

For every post-M3 state, find matched non-M3 observations with similar volatility/auction features. This prevents another hindsight-association trap.

## Hypotheses

### H1 — Trend expansion

Breakout may work when overlap is low, efficiency is high, close is near the edge, ATR/range is expanding, and penetration back into the prior range is limited.

### H2 — Failed expansion

Reversal may work only after failed acceptance, reclaim, opposite displacement and loss of source midpoint.

### H3 — Balance skip

Both directions may be negative when overlap is high, side switches are frequent, efficiency is low, and both sides of recent ranges are broken.

## GO criteria

Proceed to EA implementation only if a pre-registered state/direction rule has:

- EV > +0.10R after costs;
- PF > 1.30;
- at least 100 directional trades overall;
- stable chronological folds;
- no single month contributing over 30% of profit;
- explicit BUY/SELL asymmetry;
- skip state removing a demonstrably negative cluster;
- no worsening of max drawdown.

## NO-GO criteria

Reject if:

- fewer than 50 events drive the result;
- one year dominates;
- thresholds are unstable;
- future bars are required;
- edge disappears after costs;
- trade count becomes unusable;
- improvement depends on outliers.

## Immediate action

Build the Python-first volatility-state lab. Do not create another cooldown or directional lock before this analysis is complete.
