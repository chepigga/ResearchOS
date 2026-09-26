# LAB064 — CF191G CAUSAL ENTRY VOLATILITY REGIME MAP — PREREGISTRATION

## Purpose

Test whether CF191g outcome quality depends on the volatility regime at the canonical fill.

Diagnostic only. No entry filter, no risk multiplier, no stop/target change.

## Frozen control parity
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Single volatility axis

At each completed M5 bar:
`vol_metric = ATR14_M5 / close_M5`

Normalize causally using the previous 7 days of completed M5 bars:
- lookback = 2016 M5 bars
- current bar excluded
- `vol_percentile = percentile rank of current vol_metric within prior 2016 bars`

No future distribution and no evaluation-period qcut.

## Fixed buckets
- P0_20
- P20_40
- P40_60
- P60_80
- P80_100

First 2016 bars without full history are NA and excluded from regime comparisons.

## Outcomes

For each canonical CF191g fill report:
- final frozen R / PF contribution
- MFE / MAE 15/30/60/120m
- signed returns 15/30/60/120m
- initial-stop share
- right-tail >= +1.5R share

## Primary questions

Separately for 2021–2025 and 2026:
1. Is P80_100 EV/PF lower than the middle regime P40_60?
2. Does P80_100 have higher MAE60 or initial-stop share?
3. Is any observed high-volatility penalty repeated in both periods?

No production action is promoted from LAB064.
If high volatility is not consistently harmful in both periods, the simple 'bot dislikes volatility' hypothesis is rejected.