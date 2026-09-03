# BTC_24H_RIGHT_TAIL_BTC_ONLY_CAUSAL_DECOMPOSITION_LAB_003 — preregistration

Frozen before result inspection: 2026-09-03.

## Question
Why did the BTC-only 24h top bucket in LAB002 outperform the BTC+PAXG router, and which BTC-only components transfer from 2025 bridge to untouched 2026 OOS?

## Data / clock
- Binance Spot BTCUSDT, completed 15m klines.
- 2021-01 through 2026-07 synchronized BTC clock only.
- No forward fill.
- Event decision at completed 15m bar. Entry/outcomes start at next 15m open.
- BTC impulse definition inherited unchanged from LAB002: completed 60m absolute return >= prior 30d 97.5th percentile; 4h cooldown.
- DEV: 2021-2024. Bridge: 2025. Untouched OOS: 2026.

## Frozen target
- Primary horizon: 24h.
- Continuation and reversal tail thresholds are the DEV-only 75th percentiles and are transferred unchanged to bridge/OOS.

## Frozen LAB002 core
`impulse_dir, btc_z15, btc_z60, btc_z4h, btc_z24h, btc_vol_z, btc_range_z, btc_corr7d_lag, hour_sin, hour_cos`

## Decomposition
1. Reproduce LAB002 BTC-only router.
2. DROP_ONE_FEATURE: refit the core after removing exactly one frozen core feature.
3. CORE_PLUS_FAMILY candidates, frozen before OOS inspection:
   - IMPULSE_PATH: 60m path efficiency, directional consistency, close-location within impulse range, 60m aggregated volume z.
   - PRE_STATE: pre-impulse 4h/24h returns, prior 7d range position, distances to prior 7d high/low.
   - VOL_REGIME: causal realized-vol 4h/24h z, 24h-vs-7d vol ratio, ATR-like 4h z.
   - BREAK_ACCEPTANCE: close beyond prior 4h/24h extremes, signed breakout distance, close-location value.
   - TREND_REGIME: 7d/30d returns z, 7d trend efficiency, 7d-vs-30d trend interaction.
   - CALENDAR: day-of-week sin/cos and weekend flag.

No feature may use bars after decision time.

## Models
Two regularized logistic classifiers trained on DEV only: P(24h continuation-tail) and P(24h reversal-tail). C=0.5, StandardScaler, median imputation. Router chooses the side with the higher probability. Top-20 threshold is frozen from each model's DEV confidence distribution.

## Transfer rule
For a core feature, contribution = CORE minus DROP(feature). For an added family, contribution = CORE_PLUS_FAMILY minus CORE.
A component is `ROBUST_TRANSFER` only if:
- bridge average AUC contribution > 0,
- OOS average AUC contribution > 0,
- bridge top-20 chosen-return contribution > 0,
- OOS top-20 chosen-return contribution > 0,
- OOS tail-hit contribution >= 0.

## No rescue
After OOS is viewed, do not tune impulse percentile, tail percentile, horizon, regularization C, top bucket size, or feature thresholds. Any new mechanism requires LAB004.