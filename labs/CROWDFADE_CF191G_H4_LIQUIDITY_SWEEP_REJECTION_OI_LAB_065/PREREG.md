# LAB065 — CF191G H4 LIQUIDITY-SWEEP / REJECTION + OI-FLUSH MAP — PREREGISTRATION

## Purpose

Translate the reviewed Lunar Trading video into one causal, footprint-free proxy and test it only as a shadow diagnostic.

This LAB does NOT claim to reconstruct true footprint POC or volume-at-price.
No hard filter, no risk change, no exit change.

## Frozen CF191g control parity
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Timeframe / availability

Use only the most recent COMPLETED H4 candle available before each canonical CF191g fill.
The H4 candle close timestamp must be <= entry timestamp.

## H4 volume

Aggregate Binance BTCUSDT USD-M 1m quote asset volume into H4 candles.
`high_volume = current H4 quote volume >= causal 80th percentile of prior 180 completed H4 candles`
(~30 days, current H4 excluded).

## Sweep + rejection geometry

Define prior-24h extreme from the SIX completed H4 candles immediately preceding the event candle.

LONG-rejection event:
- event low < minimum low of prior 6 H4 candles
- event close location within event range >= 2/3 (upper third)

SHORT-rejection event:
- event high > maximum high of prior 6 H4 candles
- event close location <= 1/3 (lower third)

This is a proxy for 'price traded into an extreme but closed away from the volume/sweep zone'.
No wick-ratio threshold is added.

## OI flush

Using the causal Binance open-interest series:
`oi_change_h4 = OI_at_or_before_H4_close / OI_at_or_before_H4_open - 1`

`oi_flush = oi_change_h4 < 0`

No magnitude threshold is tuned in this LAB.

## Composite detector

`H4_REJECTION_LONG = high_volume AND long_rejection AND oi_flush`
`H4_REJECTION_SHORT = high_volume AND short_rejection AND oi_flush`

Event direction is +1 for LONG rejection and -1 for SHORT rejection.

For each CF191g fill classify the latest completed H4 event as:
- SUPPORTIVE = event direction == CF191g trade side
- ADVERSE = event direction == -CF191g trade side
- NONE = no composite event in latest completed H4 candle

## Outcomes

Report separately for 2021–2025 and 2026:
- N
- EV / PF / SumR / WR / MaxDD_R
- MFE / MAE 15m, 30m, 60m, 120m
- signed returns 15m, 30m, 60m, 120m
- initial-stop share
- right-tail share R >= +1.5R

Also report component attrition counts:
- high_volume
- local sweep + rejected close
- OI down
- full composite

## Primary questions

1. Is SUPPORTIVE composite EV/PF > NONE in BOTH periods?
2. Is SUPPORTIVE MFE60 > NONE and/or initial-stop share lower in BOTH periods?
3. Is ADVERSE worse than SUPPORTIVE where sample is meaningful?

## Guardrails

Diagnostic only.
No POC claim: quote-volume + OHLC rejection is only a proxy.
No threshold search inside LAB065.
If sample is small, retain only as shadow/context and do not promote.