# BTC_FLOW_LEVEL_PREBREAK_VOLUME_IGNITION_VS_ABSORPTION_AND_OI_CONTINUATION_LAB_036

## Frozen lineage
- Source events: exact `activation_stream.csv` persisted by `BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035`.
- Preserve LAB035 `flow_id`, `signal_time`, `side`, `level`, `touch_time`, `class_time`, `state`, `atr14`, and original +12h horizon.
- Primary universe: pre-August-2026 events with LAB035 `state` in `{ACCEPT,REJECT}` and valid `touch_time`; August 2026 is audit-only.
- No level/lookback/acceptance/entry/SL/TP threshold may be changed in this LAB.

## Data
- Binance BTCUSDT USD-M futures M15 klines: quote volume + taker-buy quote volume.
- Binance BTCUSDT spot M15 klines: quote volume + taker-buy quote volume.
- Binance USD-M daily metrics resampled to M15 for `sum_open_interest`.
- All pre-break features use only M15 bars with timestamp strictly `< touch_time`; touch-bar volume is excluded.

## Frozen pre-break volume features
For each touch event, using only fully closed bars before `touch_time`:
- futures quote-volume sums over 15m / 30m / 60m;
- spot quote-volume sums over 15m / 30m / 60m;
- futures and spot 60m taker imbalance: `(2*taker_buy_quote - quote_volume)/quote_volume`;
- flow-aligned taker pressure = `side * imbalance`;
- futures-vs-spot 60m volume log-ratio.

### Causal HIGH_VOLUME definition
- Primary ignition clock uses futures 60m quote-volume.
- `HIGH_VOLUME` iff the pre-touch 60m futures quote-volume exceeds the rolling 80th percentile of analogous 60m sums over the prior 90 days.
- The percentile history is shifted so the current pre-touch 60m observation is not included in its own threshold.
- Minimum history: 30 days; otherwise event is unresolved for HIGH_VOLUME.
- 15m and 30m volume are diagnostics only and cannot replace the primary 60m definition after results are seen.

## Frozen states
- `IGNITION = HIGH_VOLUME & LAB035 ACCEPT`.
- `ABSORPTION = HIGH_VOLUME & LAB035 REJECT`.
- `LOWVOL_ACCEPT` and `LOWVOL_REJECT` are fixed comparison groups.
- LAB035 residual from `class_time/class_price` to original signal+12h is the primary post-classification payoff for ignition-vs-absorption. The price move used to define ACCEPT/REJECT is excluded from this residual.

## OI continuation state
Applied only after LAB035 ACCEPT:
- wait exactly 1 hour after `class_time`;
- `OI_PERSIST` iff `log(OI[class_time+1h] / OI[class_time]) >= 0`;
- `OI_FLUSH` iff the log change is `< 0`;
- OI state is not known before +1h and therefore cannot be used earlier;
- payoff is recomputed from the futures close at `class_time+1h` to original signal+12h, signed by frozen flow direction and normalized by frozen ATR14.

## Primary hypotheses
H1. High pre-break futures volume increases probability of LAB035 ACCEPT versus low-volume touches.
H2. `IGNITION` has higher post-classification residual than `ABSORPTION`.
H3. Within ACCEPT, `OI_PERSIST` retains positive post-1h residual and beats `OI_FLUSH`.
H4. Pre-break flow-aligned futures taker pressure and spot confirmation provide mechanism diagnostics, but no cutoff is optimized.

## Statistics
- 7-day episode cluster bootstrap, 5000 draws, fixed seed `20260908`.
- Primary comparisons: `IGNITION-ABSORPTION` residual and `OI_PERSIST-OI_FLUSH` post-1h residual.
- Report 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul, pooled recent, LONG/SHORT, 2022 SHORT, August reused audit.

## Gates
1. frozen LAB035 lineage recovered exactly enough to retain >=1900 classified touch events pre-Aug;
2. futures-volume coverage >=95%;
3. spot-volume coverage >=95%;
4. HIGH_VOLUME classified N>=250;
5. IGNITION N>=150;
6. high-volume ACCEPT rate exceeds low-volume ACCEPT rate by >=0.05;
7. IGNITION residual >0;
8. IGNITION residual - ABSORPTION residual >= +0.20 ATR;
9. cluster-bootstrap lower 95% bound for IGNITION-ABSORPTION >0;
10. IGNITION residual exceeds LOWVOL_ACCEPT residual by >= +0.10 ATR;
11. OI_PERSIST post-1h residual >0;
12. OI_PERSIST - OI_FLUSH post-1h residual >= +0.30 ATR;
13. cluster-bootstrap lower 95% bound for OI_PERSIST-OI_FLUSH >0;
14. 2022 SHORT IGNITION residual positive with N>=20;
15. pooled recent IGNITION residual positive with N>=40;
16. both 2025H2 and 2026 Jan-Jul IGNITION residual are positive;
17. August 2026 not used for selection.

## Verdict
- `PASS_VOLUME_IGNITION_AND_OI_CONTINUATION_MECHANISM` if >=14/17 gates pass including gates 6-9 and 11-13.
- `WATCH_VOLUME_OR_OI_MECHANISM_PARTIAL` if >=10/17 pass but PASS criteria fail.
- otherwise `FAIL_NO_VOLUME_IGNITION_MECHANISM`.

## Guardrail
Research only. No live allocation, no EA rule promotion, no stop widening, no TP optimization in this LAB.