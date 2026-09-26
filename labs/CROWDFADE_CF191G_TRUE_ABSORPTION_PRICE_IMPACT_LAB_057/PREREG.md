# LAB057 — CF191G TRUE ABSORPTION: AGGRESSION MAGNITUDE × PRICE IMPACT — PREREGISTRATION

## Purpose

Test a microstructure-correct absorption proxy using **absolute aggressive quote-notional magnitude**, not delta ratio.

Diagnostic only. No skip, no risk change, no exit change, no combination with D.

## Frozen CF191g control

Exact OLD_v191g_POSITIVE_SKEW lineage from LAB053/LAB054/LAB056.
Parity must match:
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Window

Only **5 minutes**. No 15m/30m absorption detector in this LAB.

All data are completed Binance USD-M BTCUSDT 1m klines ending no later than the CF191g entry.

## Aggression magnitude

For the 5 completed 1m bars ending at entry:
- quote_volume_5m = sum(quote asset volume)
- taker_buy_quote_5m = sum(taker buy quote asset volume)
- taker_sell_quote_5m = quote_volume_5m - taker_buy_quote_5m
- delta_notional_5m = taker_buy_quote_5m - taker_sell_quote_5m
- aggression_mag_5m = abs(delta_notional_5m)

NO delta_ratio is used in the absorption hypothesis.

## Typical aggression — causal

At each completed M5 timestamp, compute the distribution of `aggression_mag_5m` over the previous **24 hours = 288 completed M5 blocks**, excluding the current block.

Report:
- rolling_median_aggression
- aggression_to_median = aggression_mag / rolling_median_aggression
- causal aggression percentile rank within the prior 288 blocks

High aggression preregistered condition:
- `aggression_percentile >= 0.90`

Minimum history: 288 prior completed M5 blocks. If unavailable, event is diagnostic-NA.

## Price impact

- raw_price_change_5m = close_entry - close_5m_ago
- impact_atr_abs = abs(raw_price_change_5m) / entry_ATR
- impact_cf_dir = trade_side * raw_price_change_5m / entry_ATR

Low-impact preregistered condition:
- `impact_atr_abs < 0.15`

## Relative sign to CF191g side

- signed_aggression = trade_side * delta_notional_5m

Shadow flags:

### adverse_absorp
`aggression_percentile >= 0.90 AND impact_atr_abs < 0.15 AND signed_aggression > 0`

Meaning: huge aggressive notional in the CF191g trade direction, but almost no price movement.

### supportive_absorp
`aggression_percentile >= 0.90 AND impact_atr_abs < 0.15 AND signed_aggression < 0`

Meaning: huge aggressive notional against the CF191g trade direction, but almost no price movement.

These are shadow labels only.

## Diagnostic map

Use causal fixed buckets, not evaluation-period qcut:

Aggression percentile buckets:
- P0_20
- P20_40
- P40_60
- P60_90
- P90_100

Absolute impact buckets:
- I0_05: <0.05 ATR
- I05_15: 0.05–<0.15 ATR
- I15_30: 0.15–<0.30 ATR
- I30_60: 0.30–<0.60 ATR
- I60_PLUS: >=0.60 ATR

Produce maps separately for signed_aggression WITH trade direction and AGAINST trade direction.

## OI context

Report causal OI change over 5m / 15m / 30m as context only. No OI threshold enters the detector.

## Outcomes

For each CF191g event:
- frozen final R
- MFE/MAE at 15m / 30m / 60m / 120m
- signed return at 15m / 30m / 60m / 120m
- impulse60 = +1.0 ATR favorable before -0.5 ATR adverse, conservative same-bar failure

## Primary diagnostic questions

Report separately for 2021–2025 and 2026 Mar–Aug:

1. Is adverse_absorp EV below control EV in both periods?
2. Is adverse_absorp PF below control PF in both periods?
3. Is adverse_absorp 60m MFE/MAE geometry worse than control in both periods?
4. Is supportive_absorp EV greater than adverse_absorp EV in both periods?
5. Does supportive_absorp show better MFE/MAE geometry than adverse_absorp in both periods?
6. How many events are in each shadow flag?

## Interpretation

LAB057 can validate or reject the **mechanism** only.
No hard veto, half-risk, full-risk, or production rule may be promoted from this LAB.
If adverse absorption is consistently toxic in both periods, the next LAB must preregister exactly one stateful veto hypothesis.