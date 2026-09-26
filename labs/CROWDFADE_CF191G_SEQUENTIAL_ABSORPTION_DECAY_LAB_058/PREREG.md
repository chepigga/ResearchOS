# LAB058 — CF191G SEQUENTIAL ABSORPTION / MARGINAL PRICE-IMPACT DECAY — PREREGISTRATION

## Purpose

Test whether CF191g weakness is associated with **persistent aggressive flow whose minute-by-minute marginal price impact deteriorates inside the final 5 minutes before entry**.

Diagnostic only:
- no skip
- no risk change
- no exit change
- no combination with D

Control parity must match frozen CF191g:
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Data

Use the final five completed Binance USD-M BTCUSDT 1m bars ending at the actual CF191g entry time.
All features are causal and use only information available no later than entry.

## Per-minute aggression

For each of the five 1m bars i:
- delta_notional_i = taker_buy_quote_i - taker_sell_quote_i
- signed_delta_i = trade_side * delta_notional_i
- aggression_mag_i = abs(delta_notional_i)

Normalize magnitude causally:
- typical_1m_aggression_i = rolling median aggression_mag over prior 1440 completed 1m bars, excluding the current bar
- aggression_intensity_i = aggression_mag_i / typical_1m_aggression_i

NO delta_ratio is used.

## Per-minute price impact

For each minute i:
- impact_i = trade_side * (close_i - open_i) / entry_ATR
- marginal_efficiency_i = impact_i / (aggression_intensity_i + 1e-6)

Interpretation:
- positive efficiency = aggression is producing movement in the CF191g direction
- negative efficiency = price response is against the CF191g direction
- falling efficiency while aggression persists = candidate absorption / failed impact

## Sequence features

Across the five minutes:
- with_fraction = fraction of minutes where signed_delta_i > 0
- against_fraction = fraction where signed_delta_i < 0
- mean_aggression_intensity = mean(aggression_intensity_i)
- efficiency_slope = OLS slope of marginal_efficiency_i versus minute index 1..5
- impact_slope = OLS slope of impact_i versus minute index 1..5
- first2_efficiency = mean minutes 1–2
- last2_efficiency = mean minutes 4–5
- efficiency_drop = first2_efficiency - last2_efficiency

## Causal sequence percentiles

At each CF191g entry, compare the current 5m sequence to all prior completed rolling 5m sequences from the previous 24 hours:
- sequence_aggression_percentile from mean_aggression_intensity
- efficiency_drop_percentile from efficiency_drop

Current sequence is excluded from its own reference window.

## Diagnostic maps

Split events by persistence direction:
- WITH_PERSISTENT: with_fraction >= 0.80 (at least 4 of 5 minutes aggressive flow in CF191g direction)
- AGAINST_PERSISTENT: against_fraction >= 0.80
- MIXED otherwise

For WITH_PERSISTENT and AGAINST_PERSISTENT separately, map:
- sequence_aggression_percentile buckets P0_20 / P20_40 / P40_60 / P60_80 / P80_100
- efficiency_drop_percentile buckets D0_20 / D20_40 / D40_60 / D60_80 / D80_100

Primary candidate corners, diagnostic only:
- ADVERSE_DECAY_CORNER = WITH_PERSISTENT + aggression percentile >=0.80 + efficiency_drop percentile >=0.80
- SUPPORTIVE_DECAY_CORNER = AGAINST_PERSISTENT + aggression percentile >=0.80 + efficiency_drop percentile >=0.80

These are NOT production thresholds and no stateful skip is tested here.

## Outcomes

For each event report:
- frozen final R
- MFE / MAE at 15m, 30m, 60m, 120m
- signed return at 15m, 30m, 60m, 120m
- impulse60 = +1.0 ATR favorable before -0.5 ATR adverse, conservative same-bar failure

## Primary diagnostic questions

Separately for 2021–2025 and 2026 Mar–Aug:
1. Is ADVERSE_DECAY_CORNER EV/PF below control?
2. Does ADVERSE_DECAY_CORNER show MFE60 lower and MAE60 higher than control?
3. Is SUPPORTIVE_DECAY_CORNER EV greater than ADVERSE_DECAY_CORNER?
4. Does the sign repeat in both periods?
5. Are event counts large enough to justify a later preregistered veto test?

No hard gate may be promoted from LAB058.