# LAB051 — V200 FIXED-ENTRY TRAILING COUNTERFACTUAL

## Question
How would current frozen V200 (Z2.05) performance change if a trailing stop were ADDED without changing its entry sequence?

## Frozen entry sequence
Use the exact Z2.05 current V200 research lineage:
- LONG: Z <= -2.05
- SHORT: Z >= +2.05
- completed M15 confirmation = 0.25 ATR
- confirmation TTL = 60m
- passive retrace = 0.60 ATR
- pending TTL = 20m
- anti-repeat = 1 ATR
- max 3/day
- cost proxy = 0.5 bps
- initial SL = 4.5 ATR
- fixed TP = 10 ATR
- max hold = 24h
- flat risk

The baseline trade sequence must first reproduce LAB032:
- historical N=1642, SumR=122.39971058019937
- 2026 Mar-Aug N=176, SumR=17.115236780278384

## Critical fixed-entry rule
1. Generate the baseline V200 trade sequence using the original no-trail exits and occupancy.
2. Freeze every baseline entry timestamp, side, entry price and signal ATR.
3. For all counterfactual variants, replay exits only.
4. Do NOT allow an earlier/later trailing exit to create or delete later entries.

Thus this lab answers pure exit-management impact, not a new stateful system.

## Exit variants
All retain hard SL4.5, TP10 and H24. Trail only adds an earlier dynamic stop.

- CONTROL: no trailing
- T25_G05: arm 2.5 ATR, gap 0.5 ATR  (V191f-style)
- T35_G05: arm 3.5 ATR, gap 0.5 ATR  (V191 strict balanced style)
- T50_G05: arm 5.0 ATR, gap 0.5 ATR
- T80_G10: arm 8.0 ATR, gap 1.0 ATR
- T80_G20: arm 8.0 ATR, gap 2.0 ATR

## Causality
Trailing stop calculated from completed path bar/tick. New stop becomes active only on the NEXT observation to avoid same-bar lookahead.

Historical path: Binance BTCUSDT 1m.
2026 Mar-Aug path: frozen BTCUSDT 1-second archive.

## Metrics
For historical 2021-2025 and 2026 Mar-Aug:
- N
- WR
- EV
- SumR
- PF
- MaxDD_R
- R/DD
- max consecutive losses
- exit mix
- delta vs CONTROL
- positive years/months

## Decision
No parameter promotion from this LAB alone.
Primary question is whether adding trailing improves EV and/or DD without destroying right-tail expectancy.
