# GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002_PREREG

**Status:** PREREGISTERED_BOUNDED_DISCOVERY_NOT_OOS

## Purpose
Test whether sub-minute COMEX GC trade-flow bursts contain causal information that predicts XAUUSD CFD direction before the CFD has already expressed the move.

## Data
- GC: canonical AMP/CQG GCEZ26 explicit-aggressor raw ticks, Aug-Sep 2026 overlap.
- XAU: frozen FTMO-Demo raw Bid/Ask ticks over the same overlap.
- Frozen clock: FTMO broker time = GC UTC +180 minutes.

## Micro windows
Non-overlapping GC buckets: 1s, 2s, 5s, 10s, 30s.

Each bucket uses only trades timestamped before its bucket end.

## Features
For each bucket:
- buy_vol, sell_vol, total volume
- delta, delta_frac
- first/last/high/low trade price
- signed crowd impact = sign(delta) * (last-first) / prior completed GC M1 ATR14

Causal 1-hour lookback, excluding current bucket:
- Q90 of abs(delta_frac)
- Q75 of volume
- among prior extreme-effort buckets only, Q20/Q80 of signed crowd impact

Extreme effort:
- abs(delta_frac) >= prior 1h Q90
- volume >= prior 1h Q75
- nonzero delta

Mechanisms:
1. FADE_Q20: extreme effort + impact <= causal prior-extreme Q20; trade opposite crowd.
2. FADE_STALL: extreme effort + signed impact <= 0.05 GC ATR; trade opposite crowd.
3. CHASE_Q80: extreme effort + impact >= causal prior-extreme Q80; trade with crowd.

No threshold sweep beyond the frozen mechanism set and window set above.

## Event de-clustering
Within each window/mechanism, accept the first eligible event then impose 60 seconds cooldown. This avoids counting one burst many times.

## XAU measurement
At GC bucket end:
- LONG entry = first executable XAU Ask
- SHORT entry = first executable XAU Bid
- exits at first executable quote after +1s,+3s,+5s,+10s,+30s,+60s
- LONG exit Bid; SHORT exit Ask
- quoted spread therefore embedded
- normalize by prior completed XAU M1 ATR14

## Lead diagnostic
For each event, measure predicted-direction XAU mid move from GC bucket start to GC bucket end/action time.

- STRICT_LEAD: pre_move_atr <= 0.00
- LOOSE_LEAD: pre_move_atr <= +0.10

These are diagnostics/subsets, not optimized filters.

## Discovery split
- TRAIN: before 2026-08-20 00:00 UTC
- VALID: 2026-08-20 00:00 UTC through 2026-09-06 22:00 UTC
- POST_CHECK: after VALID; not used for nomination.

## Nomination gate
For a window/mechanism candidate:
- TRAIN N >=20
- VALID N >=20
- TRAIN EV5s >0
- VALID EV5s >0
- TRAIN EV30s >0
- VALID EV30s >0
- VALID STRICT_LEAD N >=5
- VALID STRICT_LEAD EV5s >0
- VALID STRICT_LEAD EV30s >0
- VALID median pre_move_atr <= +0.10

Winner, if several pass, maximizes the minimum of TRAIN/VALID all-event and VALID strict-lead EV at 5s and 30s. POST_CHECK is never used for selection.

Historical bounded discovery only. Not OOS certification, not production authorization.
