# LAB056 — CF191G CAUSAL ABSORPTION MAP — DIAGNOSTIC PREREGISTRATION

## Purpose

Test whether CF191g weakness is better explained by **absorption / failed price impact** than by generic exhaustion.

This LAB is diagnostic only:
- no signal change
- no skip
- no risk multiplier
- no exit change
- no threshold promotion

Exact CF191g control lineage must match LAB053/LAB054:
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Causal windows

At each actual CF191g entry, using only completed Binance futures 1m bars ending no later than entry:
- 5 minutes
- 15 minutes
- 30 minutes

For each window calculate:
- total volume
- taker buy volume
- taker sell volume = total - taker buy
- taker delta = taker buy - taker sell = 2*taker_buy - total
- taker_delta_ratio = taker_delta / total_volume
- signed_flow = trade_side * taker_delta_ratio
- signed_price_response_atr = trade_side * (entry_close - close_window_start) / entry ATR
- absolute price response / ATR
- flow_to_price_impact = signed_price_response_atr / (abs(taker_delta_ratio)+1e-6)

Interpretation relative to CF191g trade side:

### Adverse absorption candidate
Strong aggressive flow **in the CF191g direction** but weak / opposite price response.

### Supportive absorption candidate
Strong aggressive flow **against the CF191g direction** but price refuses to move materially against the trade.

## No arbitrary production threshold

Primary diagnostic is a 5x5 map for each horizon:
- signed_flow quintile Q1..Q5
- signed_price_response_atr quintile Q1..Q5

Quintiles are computed separately inside each evaluation period (2021–2025 and 2026) for descriptive mapping only. They are NOT causal production thresholds and cannot be promoted directly.

Additionally report corner buckets descriptively:
- FLOW_WITH / PRICE_WEAK: signed_flow Q5 and price-response Q1/Q2
- FLOW_AGAINST / PRICE_RESISTS: signed_flow Q1 and price-response Q4/Q5
- FLOW_WITH / PRICE_WITH: signed_flow Q5 and price-response Q4/Q5
- FLOW_AGAINST / PRICE_AGAINST: signed_flow Q1 and price-response Q1/Q2

These labels are descriptive, not entry rules.

## OI context

Add causal open-interest change over 15m and 30m from the frozen Binance positioning/OI archive:
- oi_ch15
- oi_ch30

OI is context only. No OI threshold is used to define absorption in this LAB.

## Outcomes

For every entry report:
- frozen CF191g final R
- MFE / MAE at 15m, 30m, 60m, 120m
- signed return at 15m, 30m, 60m, 120m
- +1.0 ATR favorable before -0.5 ATR adverse first-passage at 60m (same-bar ambiguity = failure)

## Decision questions

1. Do FLOW_WITH / PRICE_WEAK buckets have lower final EV/PF than control?
2. Do they have worse 60m MFE/MAE geometry?
3. Do FLOW_AGAINST / PRICE_RESISTS buckets have higher EV/PF than control?
4. Is the pattern present in both 2021–2025 and 2026?
5. Which window (5/15/30m) gives the cleanest and most stable separation?

No hard gate is promoted from LAB056. Any gate must be preregistered in a later LAB.