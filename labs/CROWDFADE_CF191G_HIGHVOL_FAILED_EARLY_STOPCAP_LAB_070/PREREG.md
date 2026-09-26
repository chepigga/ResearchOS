# LAB070 — CF191G HIGH-VOL FAILED-EARLY DEFENSIVE STOP CAP — PREREGISTRATION

## Purpose

Test one materially softer action after LAB069 full-exit failed historically but helped 2026.

Rule:
`if position is still open at +15m AND entry vol=P80_100 AND FAILED_EARLY -> tighten protective loss cap from -1.00R to -0.75R`

## Frozen state

Same as LAB069:
- entry volatility percentile over prior 2016 completed M5 bars
- HIGH = P80_100
- first 15 completed 1m bars after fill
- FAILED_EARLY = expansion15_atr <= 0 OR eff15 <= 0

No entry changes and no threshold search.

## Defensive action

At the completed +15m close, if the state is active:
- target defensive stop corresponds to -0.75R from entry
- since original SL distance is 1.5 ATR, defensive stop price = entry - side * (0.75 * 1.5 ATR)

Causal ordering:
- original CF191g stop/BE/trail management is applied normally through the +15m bar
- if position has already exited, no action
- after the +15m close the state becomes known
- if the +15m close is already beyond the new -0.75R stop, close at that actual +15m close (no retroactive fill at the better stop)
- otherwise install the -0.75R stop for subsequent bars
- later canonical BE/trailing may only tighten the stop further

## Stateful replay

Full replay required; any earlier defensive-stop exit changes occupancy and future reachability.

## PASS criteria

Same as LAB069:
- R/DD >= control
- SumR >=98% control
- PF >= control OR MaxDD lower
- max consecutive losses not worse
- positive years/months not worse
- action-state count >=100 historical / >=20 2026

Overall PASS requires both periods.

## Stop rule

If LAB070 fails overall, stop this high-vol FAILED_EARLY management branch. Do not tune the stop cap inside this branch.