# GC_XAU_LIMIT_ORDER_OPERATIONAL_ROBUSTNESS_LAB_009 — PREREG

Status: PREREGISTERED BEFORE LAB009 OPERATIONAL OUTCOME

## Purpose

Evaluate whether the four stable blind-limit candidates identified by LAB008 remain usable under prop-oriented operational constraints. No new depth, expiry, GC signal, stop, target, or timeout parameter is introduced.

## Frozen candidates from LAB008

- D1.00_E3M: depth 1.00 ATR, expiry 3m
- D1.00_E5M: depth 1.00 ATR, expiry 5m
- D0.75_E3M: depth 0.75 ATR, expiry 3m
- D0.75_E5M: depth 0.75 ATR, expiry 5m

All retain:
- SL = 1.5 XAU ATR14(M1)
- TP = 3R
- hard timeout = 30m from original GC signal
- FTMO Ask entry eligibility / Bid exit path
- LONG only

## Cohorts

Primary: COMMON_CLOCK.
Secondary: AMP_ALL.

## Operational modes

1. ALL_SIGNALS — LAB008 baseline.
2. ONE_ACTIVE_SETUP — process signals chronologically; after accepting a signal, ignore every later signal until either:
   - the pending limit expires if unfilled; or
   - the filled trade exits (TP/SL/timeout).

ONE_ACTIVE_SETUP is the primary prop-safety mode because it prevents overlapping pending setups and overlapping open positions.

## Cost stress

LAB008 already embeds quoted spread. Apply additional adverse round-turn cost to every filled trade after the observed R outcome:

- 0.00R
- 0.025R
- 0.05R
- 0.10R

Unfilled/skipped signals remain 0R.

## Risk translation

Translate sequence max drawdown and worst closed-PnL UTC day to account-percent approximations for:

- 0.25% risk per filled trade
- 0.50% risk per filled trade

This is not a full FTMO equity-DD simulator because intratrade floating PnL is not reconstructed here.

## Stability diagnostics

For every candidate/cohort/mode/cost:
- accepted signals;
- fills and fill rate;
- EV R per original signal and per accepted signal;
- EV R per fill;
- PF;
- max sequence DD R;
- positive weeks / total weeks;
- worst UTC closed-PnL day R;
- EARLY (<2026-09-01) vs LATE EV.

Primary descriptive robustness gate for ONE_ACTIVE_SETUP at +0.05R cost per fill:

1. COMMON_CLOCK EV/original-signal > 0;
2. AMP_ALL EV/original-signal > 0;
3. COMMON_CLOCK LATE EV/original-signal > 0;
4. COMMON_CLOCK PF > 1.0;
5. COMMON_CLOCK fill count >= 40;
6. COMMON_CLOCK max DD at 0.50% risk < 5%;
7. COMMON_CLOCK worst closed-PnL UTC day at 0.50% risk > -4%.

LAB009 is post-discovery and NOT independent OOS. It may identify an operational candidate to freeze for forward/OOS, but it cannot certify production edge.
