# BTC_RETAIL_RATIO_ARCHIVE_VS_REST_DECISION_PARITY_AND_THRESHOLD_MARGIN_LAB_057

## Purpose
Determine whether the known numerical mismatch between Binance daily-metrics `count_long_short_ratio` and live REST `globalLongShortAccountRatio` materially changes the frozen BTC SHORT v1 FLOW decisions.

This is a transport/decision-parity audit only. It does not evaluate PnL and cannot tune the frozen strategy.

## Frozen reference decision
- M15 retail ratio = last 5m observation in each M15 bucket.
- `delta_ls_12 = ratio_t - ratio_{t-12}`.
- Frozen thresholds are strictly-prior archive-derived rolling 90-calendar-day q20/q80 with minimum 1000 prior M15 observations.
- Decision classes using the same archive thresholds for both transports:
  - BUY if `delta_ls_12 <= q20`
  - SHORT if `delta_ls_12 >= q80`
  - NEUTRAL otherwise.
- Frozen FLOW event construction = 12h non-overlapping across both BUY and SHORT extremes exactly as LAB022/LAB055.

## REST alignment
LAB056 established that the closest raw timestamp alignment is REST timestamp minus 5 minutes. LAB057 freezes this `-5m` alignment before evaluating any decision parity.

## Why shared archive thresholds
The goal is to isolate transport/value differences, not threshold-estimation differences. Therefore REST `delta_ls_12` is classified against the exact q20/q80 threshold computed from archive history at the same timestamp.

## Evaluation window
- Use as much historical overlap as Binance REST provides, targeting approximately the latest 30 calendar days ending at the latest complete archive day.
- Archive history is downloaded sufficiently far back to compute the frozen 90d q20/q80 causally.
- Require >=1500 comparable M15 decision rows for a formal verdict.
- Discard the first 24h of overlap from event-stream parity so cooldown phase can settle causally.

## Primary metrics
1. All-class pointwise decision parity: BUY/SHORT/NEUTRAL exact match share.
2. SHORT binary parity: `(SHORT vs not SHORT)` exact match share.
3. BUY binary parity as a symmetry diagnostic.
4. SHORT false-positive and false-negative rates versus archive reference.
5. Frozen 12h non-overlap FLOW event exact union-match share on `signal_time + side`.
6. SHORT-only FLOW event exact union-match share.
7. Numeric transport error:
   - raw ratio absolute difference after fixed -5m alignment;
   - `abs(delta_rest-delta_archive)` distribution;
   - normalized delta error divided by `(q80-q20)`.
8. Threshold margin:
   - distance of archive delta to q80 for all points and SHORT points;
   - margin/error ratio = nearest archive threshold distance / delta transport error;
   - every decision flip is listed with archive delta, REST delta, q20, q80, threshold distance, delta error and normalized error.

## Preregistered verdict
`PASS_REST_DECISION_PARITY_FOR_SHADOW_MONITORING` only if all are true:
- comparable M15 N >=1500;
- all-class pointwise parity >=99.0%;
- SHORT binary parity >=99.5%;
- SHORT false-positive rate <=0.5%;
- SHORT false-negative rate <=0.5%;
- all-side frozen FLOW event union-match >=95.0%;
- SHORT-only frozen FLOW event union-match >=95.0%.

`FAIL_REST_DECISION_PARITY` if any formal parity gate above fails.

## Interpretation guardrail
A PASS authorizes only a separately preregistered LIVE_SHADOW transport for signal monitoring. It does not alter the strategy, does not convert live REST observations into fresh OOS evidence, and does not authorize live/prop allocation.

A FAIL means archive daily metrics remain the canonical decision source until a new transport is independently validated.

## No-tuning law
No tolerance-based substitution, threshold adjustment, q-level change, cooldown change, timestamp shift change, or outcome-conditioned exception may be introduced after seeing LAB057 results.