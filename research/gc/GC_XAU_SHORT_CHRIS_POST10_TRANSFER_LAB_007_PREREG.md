# GC_XAU_SHORT_CHRIS_POST10_TRANSFER_LAB_007 — PREREG

## Purpose
Test whether the already-frozen GC SHORT Chris/AEIF post-10m walk-forward state transfers directionally to executable FTMO-Demo XAUUSD Bid/Ask ticks.

## Frozen GC state
Use `GC_SHORT_CHRIS_AEIF_POST10_DISTANCE_GATE_WALKFORWARD_LAB_006_OOF.csv` exactly as produced by LAB006.

A transfer event exists only when:
- `selected == True`
- the LAB006 walk-forward threshold was based only on prior GC events
- checkpoint is the completed +10m state from the LAB003 entry.

No GC signal threshold or gate parameter may be changed in LAB007.

## Causal XAU event time
`checkpoint_time_utc = entry_time + 10 minutes`.
The XAU SHORT may begin only at the first executable FTMO tick at/after checkpoint_time. No XAU information before that timestamp is used to select an event.

## FTMO clock and prices
- Use the same frozen FTMO-Demo raw XAUUSD tick files as LONG transfer LAB006.
- Recalibrate broker-clock offset only by GC/XAU M1 return correlation, never by trade PnL.
- Expected historical mapping: FTMO clock = UTC + 180 minutes.
- SHORT entry = executable XAU Bid.
- SHORT exit = executable XAU Ask.
- Quoted spread is therefore embedded.
- No commission/slippage overlay in this transfer-only LAB.

## Frozen horizons after checkpoint
- 5m diagnostic
- 10m PRIMARY (maps to GC residual 10→20)
- 20m SECONDARY (maps to GC residual 10→30)
- 30m diagnostic

Return for SHORT is `(entry_bid - exit_ask) / entry_bid` in bps and / XAU ATR14(M1).

## Comparators
For each feed separately:
1. selected LAB006 events (primary candidate),
2. all LAB006 OOF events (baseline),
3. rejected LAB006 events.

Also report the exact common selected seed-times between Rithmic and AMP once, deduplicated.

## Frozen PASS gates
All must pass:
- clock offset == +180m;
- selected executable N >= 6 on Rithmic and >= 6 on AMP;
- selected XAU 10m EV > 0 bps on both feeds;
- selected XAU 10m EV > all-OOF baseline XAU 10m EV on both feeds;
- selected XAU 10m EV > rejected XAU 10m EV on both feeds;
- selected XAU 10m WR >= 50% on both feeds;
- selected XAU 20m EV >= 0 on both feeds;
- exact-common selected subset XAU 10m EV > 0.

## Governance
Historical transfer only, not independent OOS. No XAU entry-depth, stop, target, timeout, session, spread filter, or cost threshold tuning is allowed. PASS only authorizes a separate execution-geometry study.
