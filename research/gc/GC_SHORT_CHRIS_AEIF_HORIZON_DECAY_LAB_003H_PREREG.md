# GC_SHORT_CHRIS_AEIF_HORIZON_DECAY_LAB_003H — PREREG

## Purpose
Pure horizon-decay audit of the already-frozen LAB003 Chris/AEIF SHORT event set. No signal thresholds, confirmation rules, event membership, feed semantics, or XAU execution are changed.

## Frozen event definition
Use exactly the LAB003 mechanism and event timestamps:
`EXTREME BUY -> UPPER LOCATION -> WEAK UPWARD RESULT -> BEARISH CONFIRMATION <=2 M1 -> SHORT`.

Event entry is the exact LAB003 `entry_time` / `entry` on GC.

## Horizons
Measure SHORT forward return in seed ATR units at fixed horizons:
- 1m
- 3m
- 5m
- 10m
- 15m
- 30m

For each event and horizon h:
`fwd_h_atr = (entry_price - close_at_horizon) / seed_atr14`.

No best-horizon optimization is permitted. This lab is descriptive/diagnostic. It may identify the temporal shape of the already-frozen signal but cannot promote the rejected LAB003 definition by itself.

## Periods
Same LAB003 clocks:
- TRAIN: < 2026-08-20 00:00 UTC
- VALID: 2026-08-20 00:00 to 2026-09-06 22:00 UTC
- LATE_CHECK: 2026-09-06 22:00 to 2026-09-11 12:46 UTC
- POST_CHECK: > 2026-09-11 12:46 UTC
- FULL

## Outputs
Report by feed and period for every horizon:
- N
- mean EV ATR
- median ATR
- win rate
- sum ATR

Also report horizon of maximum FULL mean EV separately for Rithmic and AMP as descriptive only.

## Interpretation rule
- If 1–5m is stronger than 15–30m across VALID and FULL on both feeds, interpret as evidence of a fast rejection edge.
- If 10–15m dominates and 30m decays, interpret as medium-speed mean reversion / rejection.
- If no consistent shape across feeds/periods, horizon structure is unstable.

No parameter retuning follows automatically. Any new signal/execution design requires separate preregistration.
