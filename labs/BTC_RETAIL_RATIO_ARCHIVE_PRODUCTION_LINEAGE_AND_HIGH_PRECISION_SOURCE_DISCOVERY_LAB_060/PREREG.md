# BTC_RETAIL_RATIO_ARCHIVE_PRODUCTION_LINEAGE_AND_HIGH_PRECISION_SOURCE_DISCOVERY_LAB_060

## Purpose
Determine whether a publicly reachable Binance source exists that reproduces the archive `count_long_short_ratio` with archive-grade precision and can extend beyond the latest complete daily archive. This is a transport/data-lineage lab only. Frozen SHORT v1 alpha, thresholds, 12h non-overlap clock, execution, management, costs, sizing and acceptance rules are unchanged.

## Frozen candidate universe (before probing)
1. Official USD-M big-data route `GET /futures/data/globalLongShortAccountRatio` on:
   - `https://www.binance.com`
   - `https://fapi.binance.com`
   - `https://fapi1.binance.com`
   - `https://fapi2.binance.com`
   - `https://fapi3.binance.com`
   - `https://fapi4.binance.com`
2. Binance web/BAPI public market-data route candidates:
   - `/bapi/futures/v1/public/future/marketData/longShortRatio`
   - `/bapi/futures/v1/public/future/marketData/globalLongShortAccountRatio`
   - `/bapi/futures/v1/public/future/marketData/longShortAccountRatio`
3. `data.binance.vision` daily USD-M metrics for BTCUSDT, including an explicit probe for the current UTC day and latest prior days.
4. Deterministic reconstructions from any successful official REST payload:
   - reported `longShortRatio`
   - `longAccount / shortAccount`
   - `(1-shortAccount)/shortAccount`
   - `longAccount/(1-longAccount)`
No other source/transformation may be added after results are seen.

## Canonical target
- `data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-YYYY-MM-DD.zip`
- field: `count_long_short_ratio`
- canonical timestamp: archive `create_time`

## Alignment
For the already-known official REST family, primary alignment is frozen at REST timestamp -5 minutes from LAB056-058.
For previously untested BAPI candidates only, diagnostic offsets `[-10,-5,0,+5,+10]` minutes are reported. A post-result best offset is diagnostic only and does not authorize live use.

## Measurements
For each successful candidate/reconstruction:
- HTTP/status/schema/row count
- newest timestamp and whether it extends beyond latest archive timestamp
- decimal-place distribution of raw ratio strings
- overlap N with canonical archive
- exact equality share
- mean / median / p95 / p99 / max absolute error
- correlation (diagnostic only)
- best fixed diagnostic timestamp offset where applicable
- whether values appear to be the same four-decimal family as official REST

For `data.binance.vision` current-day probe:
- HTTP status
- rows if available
- first/last timestamp
- whether file is a partial intraday high-precision feed

## Archive-equivalent high-precision source gate
A candidate is `ARCHIVE_EQUIVALENT_LIVE_SOURCE` only if all hold:
1. public and successful without credentials;
2. overlap >= 200 canonical 5m observations;
3. exact value share >= 99.9%;
4. max absolute error <= 1e-8;
5. candidate has >=95% ratio strings with >=6 decimal digits OR is byte/value exact to archive despite formatting;
6. candidate produces observations at least 5 minutes newer than the newest complete daily archive observation available at run time.

If exact archive reproduction is met but no live freshness exists: `ARCHIVE_EQUIVALENT_DELAYED_ONLY`.
If no candidate meets archive equivalence but official REST family is clearly lower-precision near-lineage: `NO_HIGH_PRECISION_PUBLIC_SOURCE_FOUND_OFFICIAL_REST_IS_LOSSY_NEAR_LINEAGE`.
If lineage cannot be established: `NO_ARCHIVE_EQUIVALENT_SOURCE_LINEAGE_UNRESOLVED`.

## Governance
- No PnL, trade outcomes, HIGH_RESPONSE, ACCEPT, TP/SL or September performance are used to select a source.
- No tolerance is tuned from observed errors.
- No candidate discovered after execution may be promoted in this LAB.
- Frozen SHORT v1 remains unchanged and live allocation remains 0 regardless of result; a separately preregistered lab is required before any new transport source can drive the clock.