# RAW CHRIS XAU EXECUTABLE TRANSFER — IMMEDIATE VS LIMIT LAB011 PREREG

## Purpose

Transfer the two bounded LAB010 execution hypotheses to executable FTMO-Demo XAUUSD raw Bid/Ask ticks on the available Aug-Sep 2026 GC/XAU overlap.

This is a transfer test, not a new strategy discovery lab.

## Frozen source

Use only frozen LAB003 `AMP_CQG_RAW_EXCLUSIVE` Chris events.

Because the LAB010 long-history quality windows end on 2026-07-28 while certified FTMO raw XAU Bid/Ask begins on 2026-08-03, LAB011 uses the already-existing Aug-Sep GCEZ26/AMP overlap for executable XAU transfer.

This period is later in calendar time than the long-history LAB010 source window, but is **not clean independent OOS**, because Aug-Sep Chris/XAU behavior was previously inspected in older Chris transfer work.

## Frozen clock

- GC event timestamps are UTC.
- FTMO historical broker clock mapping is frozen at `UTC + 180 minutes`.
- Do not recalibrate the offset in LAB011.

## Frozen variant A — immediate

At frozen Chris `entry_time`:

- map to FTMO broker clock with +180m
- first valid XAU tick within 5s
- SHORT at executable Bid
- XAU ATR14 = completed prior broker-clock M1 midpoint ATR
- SL = 1.0 XAU ATR above fill
- TP = 2.0 XAU ATR below fill
- hard timeout = original GC entry clock +30m
- SHORT exit side = Ask
- stop execution = actual Ask at first crossing
- TP fill = target price

## Frozen variant B — limit

At the same initial decision clock:

- initial executable XAU Bid is reference
- SELL LIMIT = initial Bid +0.50 XAU ATR
- expiry = 5m
- no fill = no trade
- if filled, same SL=1.0 ATR / TP=2.0 ATR
- hard timeout remains original decision clock +30m, not fill+30m
- exits use Ask
- no fallback market order

## Costs

- Bid/Ask spread is embedded.
- Exact FTMO XAU commission is not assumed.
- Report flat extra cost stress of +0.00R, +0.05R and +0.10R per filled trade.
- No spread/session filter.

## Metrics

For each variant report:

- signals / fills / fill rate
- EV per fill
- EV per original signal
- PF
- WR
- SumR
- MaxDD in event sequence
- max consecutive negative trades
- TP / SL / timeout counts
- August and September metrics
- event bootstrap P(EV>0) and 95% CI

## Frozen gates

### Immediate A

ALL required:

1. signals >=20
2. filled >=20
3. gross EV/fill >0
4. EV/fill after +0.05R cost >0
5. gross PF >=1.10
6. max consecutive negative trades <=8

### Limit B

ALL required:

1. signals >=20
2. fills >=10
3. fill rate 40%–85%
4. gross EV/fill >0
5. gross EV/original signal >0
6. EV/fill after +0.05R cost >0
7. gross PF >=1.10
8. max consecutive negative trades <=8

## Governance

Do not modify:

- Chris signal
- clock offset
- ATR definition
- SL/TP
- 30m timeout
- +0.50 ATR limit depth
- 5m expiry
- execution side
- sample dates
- gates

If both fail, do not rescue by sweeping alternative stops, targets, limit depth, expiry, sessions, or spread filters on the same overlap.

A pass means historical executable-transfer support only. It does not authorize funded/live use.
