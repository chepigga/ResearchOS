# GC_XAU_LIMIT_SIGNAL_DECAY_CURVE_LAB_011 — PREREG

Purpose: measure how long the frozen GC BUYER_BREAKOUT_LONG_001 information remains useful for an XAUUSD limit entry. This is a post-discovery decay study, not OOS validation and not a search over GC signal thresholds.

## Frozen signal / execution scale

- GC selector: unchanged BUYER_BREAKOUT_LONG_001 from LAB006–010.
- Primary cohort: exact common-clock AMP ∩ Rithmic executable events from LAB006.
- Secondary cohort: AMP_ALL executable events.
- XAU source: FTMO-Demo raw Bid/Ask ticks, same 2026-08-03..2026-09-15 files used by LAB006–010.
- Limit depth: `market-reference Ask - 1.00 * XAU ATR14(M1)`.
- ATR: frozen LAB006 XAU ATR14(M1) value at the signal; no re-scaling after the signal.
- SL: 1.50 ATR.
- TP: 3R = 4.50 ATR above fill.
- Cost stress: subtract 0.05R from every filled trade in addition to the quoted spread already embedded by Ask-entry/Bid-exit.

## What varies

Only maximum wait for the same 1.00-ATR limit:

`1 / 3 / 5 / 10 / 15 / 30 / 60 minutes`.

For signal-age analysis, the bracket gets a fixed **30 minutes after the actual fill**. This differs deliberately from LAB009's 30m-from-original-signal operational timeout; otherwise a fill after 30m could not be evaluated. LAB011 therefore measures decay, not a deployable order policy.

A fill is the first FTMO Ask at or below the frozen limit. No carry across a >5-minute quote gap before fill. A trade path containing a >5-minute quote gap before its 30-minute post-fill evaluation end is marked data-gap and excluded from filled-trade outcome statistics.

## Pre-specified outputs

1. Cumulative expiry curve for each cohort: fill rate, EV R/original signal (unfilled = 0R), EV R/filled trade, PF, WR, MaxDD.
2. First-fill-delay buckets: `0-1, 1-3, 3-5, 5-10, 10-15, 15-30, 30-60m`, with N, mean R, PF, WR, and day-cluster CI95.
3. Raw XAU response from the actual fill at +5m/+15m/+30m in ATR units, for diagnostic separation from bracket geometry.
4. Early vs late sample EV per delay bucket where sample size permits.

## Interpretation rule

The goal is to estimate signal decay, not select the best expiry retrospectively. A monotone or clearly degrading age profile supports a short-lived GC→XAU edge. A flat profile supports longer-lived information. A late re-improvement is treated as a separate hypothesis unless independently replicated.

No new session, regime, news, spread, trend, or GC order-flow filters may be added in LAB011.