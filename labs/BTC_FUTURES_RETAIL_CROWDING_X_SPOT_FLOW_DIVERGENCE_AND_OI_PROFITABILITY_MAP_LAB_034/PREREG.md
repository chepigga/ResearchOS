# BTC_FUTURES_RETAIL_CROWDING_X_SPOT_FLOW_DIVERGENCE_AND_OI_PROFITABILITY_MAP_LAB_034

## Question
On the frozen Binance retail-flow signal stream, does profitability depend on whether leveraged futures crowding is supported or contradicted by spot aggressive flow and open-interest expansion?

## Frozen signal lineage
- Exact `flow_only_nonoverlap.csv` from LAB022 / same signal timestamps and side used by LAB023-LAB026.
- Direction is frozen contrarian retail-flow direction; no new direction rule.
- Primary outcome is frozen signed 12h ATR return (`signed12_atr`).
- No stop/TP/entry optimization in this LAB.

## Data
Binance BTCUSDT only, causally aligned on M15 clock.
1. USD-M futures daily `metrics` archive:
   - `count_long_short_ratio`
   - `sum_open_interest`
   - `count_toptrader_long_short_ratio`
   - `sum_toptrader_long_short_ratio`
   - `sum_taker_long_short_vol_ratio` when present.
2. Binance Spot BTCUSDT monthly 15m klines.
3. Binance USD-M Futures BTCUSDT monthly 15m klines.

Kline aggressive flow is built from quote volume and taker-buy quote volume over the trailing 12 M15 bars (3h):
`imbalance = (2*taker_buy_quote - total_quote) / total_quote`.

All features use observations at or before the frozen signal timestamp only.

## Ten frozen quality features
1. `retail_ratio_level` = absolute `count_long_short_ratio`.
2. `crowd_change_strength` = `-side * (ratio_t - ratio_t-12)`; larger = stronger crowd move opposite frozen trade side.
3. `oi_logchg_3h` = log OI_t - log OI_t-12.
4. `futures_taker_imb_3h`.
5. `spot_taker_imb_3h`.
6. `spot_trade_confirmation` = `side * spot_taker_imb_3h`.
7. `futures_trade_confirmation` = `side * futures_taker_imb_3h`.
8. `leveraged_vs_spot_divergence` = `-side * (futures_taker_imb_3h - spot_taker_imb_3h)`; positive means aggressive futures flow is more aligned with the crowded side than spot flow.
9. `top_count_vs_retail_logdiv` = log(top-trader account ratio) - log(retail ratio).
10. `top_position_vs_retail_logdiv` = log(top-trader position ratio) - log(retail ratio).

No feature can be replaced after results.

## Primary tests
For each feature on pre-Aug-2026 events:
- Spearman vs frozen signed 12h ATR return.
- BH-FDR across exactly 10 features.
- Fixed quintile profitability map Q1..Q5; no threshold promotion.

## Core hypothesis tests
A. `leveraged_vs_spot_divergence` should have positive association with contrarian-flow profitability.
B. OI expansion should strengthen that effect.
C. Fixed 2x2x2 sign map:
- OI up vs non-up;
- leveraged-vs-spot divergence positive vs non-positive;
- spot trade confirmation positive vs non-positive.
Report N, mean signed12 ATR, hit-rate for all eight cells.
No cell is promoted as a live rule.

## Stress / transfer
- 2022 SHORT.
- 2025H2.
- 2026 Jan-Jul.
- LONG and SHORT separately.
- August 2026 reused audit only.

## Bootstrap
For the primary divergence quality contrast only:
- top quintile vs bottom quintile of `leveraged_vs_spot_divergence` using fixed full pre-Aug ranks for descriptive research only;
- 7-day cluster bootstrap, 5000 resamples.
This contrast is not a deployable cutoff.

## Gates
1. Exact frozen flow lineage >=3200 rows.
2. Spot-kline feature coverage >=90% pre-Aug.
3. Futures-kline feature coverage >=90% pre-Aug.
4. Futures metrics/OI feature coverage >=90% pre-Aug.
5. At least one feature BH q <=0.10.
6. At least one feature |rho| >=0.05.
7. `leveraged_vs_spot_divergence` rho > 0.
8. Divergence Q5 mean > Q1 mean by >=0.20 ATR.
9. Divergence Q5-Q1 7d bootstrap lower CI > 0.
10. OI-up + positive-divergence cell mean > overall baseline mean by >=0.15 ATR.
11. 2022 SHORT high-divergence descriptive subset positive.
12. Both LONG and SHORT have same sign for divergence rho.
13. 2025H2 and 2026 divergence rho have same sign.
14. August is not used for feature selection or gates.

PASS requires >=11/14 including gates 1-4 and at least one of 7/8/9. WATCH if external-state effects are positive but not transfer-robust. Otherwise FAIL.

## Guardrails
- No entry/SL/TP/horizon search.
- No post-result threshold or cell promotion.
- This is reused-data quality mapping, not fresh prospective OOS.
- Live allocation remains 0.