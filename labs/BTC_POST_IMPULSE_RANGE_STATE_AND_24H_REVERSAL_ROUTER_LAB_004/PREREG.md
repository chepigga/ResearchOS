# BTC_POST_IMPULSE_RANGE_STATE_AND_24H_REVERSAL_ROUTER_LAB_004

Frozen before results: 2026-09-03.

## Question
After a causal BTC 60m impulse, do price-only post-impulse states observed before entry improve prediction and routing of a large 24h reversal beyond the frozen BTC-only event-time CORE?

## Data / event parent
- Binance Spot BTCUSDT, completed 15m bars.
- Parent event unchanged: completed 60m absolute log-return >= prior 30-day 97.5th percentile, 4h cooldown.
- DEV 2021-2024, bridge 2025, OOS 2026.

## Clocks
- PRIMARY: observe exactly 2 completed M15 bars after the impulse (+30m), then enter at next M15 open.
- SECONDARY AUDIT ONLY: +15m and +60m clocks. They cannot rescue the primary result.
- 24h outcome starts from the delayed entry price.

## Target
- Trade direction is always opposite the parent impulse.
- Large reversal target = delayed-entry 24h reversal return >= DEV-only 75th percentile for that clock.
- Thresholds and top-20 probability cut are estimated on DEV only and transferred unchanged.

## Frozen models
CORE uses the event-time BTC-only features inherited from LAB003: impulse direction, 15m/60m/4h/24h z-returns, volume z, range z, 7d lag autocorrelation, hour sin/cos.

Candidate post-impulse families, all computed only through the decision bar:
1. RANGE_STATE: impulse range z, decision range z, post/pre range ratio, range persistence.
2. EXHAUSTION: impulse efficiency/close-location plus signed post move, retracement fraction, opposite-bar share.
3. ACCEPTANCE: break beyond pre-impulse 60m range, decision acceptance, failed acceptance, signed close-location/extension.
4. RECOVERY_SEQUENCE: signed path efficiency, terminal opposite streak, first post-bar response, cumulative signed recovery.
5. VOLUME_RESPONSE: impulse volume z, post/pre quote-volume ratio, decision volume z, post volume slope.
6. FULL_POST: union of the five frozen families; reported but cannot be interpreted as a single mechanism.

## Promotion rule
A family is transferable on PRIMARY +30m only if versus CORE it has: positive average AUC delta in bridge and OOS; positive top-20 mean reversal-return delta in bridge and OOS; and positive OOS Brier improvement. No 2026 tuning is authorized.

PASS requires: OOS N>=100, CORE OOS AUC>=0.55, CORE OOS top-20 mean reversal return >0, and >=1 transferable named family (FULL_POST alone is insufficient). Secondary clocks are audit/support only.
