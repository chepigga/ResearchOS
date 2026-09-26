# LAB054 — CF191G CAUSAL REGIME IMPULSE MODEL — PREREGISTRATION

## Purpose

Test whether a causal market-regime / impulse layer can score **existing CF191g entries** without changing the frozen CrowdFade direction signal.

This LAB is diagnostic / shadow-only. It does not change entry reachability, risk, stops, trailing, or exits.

## Frozen CF191g control

Use the same OLD_v191g_POSITIVE_SKEW state machine as LAB053:
- CrowdFade Z threshold = 1.00
- completed M5 confirmation = +0.30 ATR in trade direction
- confirmation TTL = 45m / 9 completed M5 bars
- max adverse before confirmation = 0.75 ATR
- confirm |Z| >= 0.75
- same-side crowd consistency at confirmation
- response ratio >= 0.50
- SL = 1.50 ATR
- positive-skew management: BE arm 3.0 ATR, lock 2.25 ATR; trailing arm 3.5 ATR, gap 0.5 ATR
- max hold = 6h
- anti-repeat = 1 ATR
- max 3 trades/day
- cost proxy = 0.5 bps

Parity must match LAB053 OLD_v191g_POSITIVE_SKEW:
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Primary prediction target

At the actual CF191g entry time, using only future prices after entry:

IMPULSE60 = 1 if price reaches **+1.00 ATR favorable excursion before -0.50 ATR adverse excursion within 60 minutes**.
Otherwise IMPULSE60 = 0.

If favorable and adverse thresholds occur in the same 1-minute bar, score the observation conservatively as failure (0).

Secondary diagnostics only:
- signed return at 15m / 30m / 60m / 120m
- MFE and MAE at 15m / 30m / 60m / 120m
- corresponding +1.0 ATR / -0.5 ATR first-passage labels for 30m and 120m

Only IMPULSE60 drives model-selection conclusions.

## Causal features frozen before results

All features are known by the completed M5 confirmation / entry time.

### Trend regime
- H1 trend: UP / DOWN / NEUTRAL from completed H1 close vs EMA50 and EMA50 slope vs 4 completed H1 bars ago.
- H4 trend: same.
- H1/H4 aligned flag.
- trade-with-H1, trade-with-H4, trade-with-aligned-trend encodings.

### Price impulse / structure
- signed return in trade direction over 15m, 30m, 60m, normalized by entry ATR
- directional path efficiency over 30m and 60m
- 15m and 60m high-low range / ATR
- close location in recent 15m and 60m range, signed for trade direction
- pullback depth from recent 60m directional extreme / ATR
- ATR% = ATR / price

### Confirmation response
- confirmation age in minutes
- maximum favorable excursion before confirmation / ATR
- maximum adverse excursion before confirmation / ATR
- response ratio = pre-confirm favorable / adverse
- signal Z
- confirm Z
- delta |Z| from signal to confirm

### Flow
Using only Binance data timestamped no later than entry:
- open interest percent change over 30m and 60m
- taker delta ratio over 15m, 30m and 60m, where delta = 2*taker_buy_volume - total_volume
- volume expansion = recent 15m volume / prior 60m average 15m-equivalent volume

No future OI, volume, taker delta or bar close may enter features.

## Model families

No parameter search.

1. TREND_ONLY
2. PRICE_ONLY
3. FLOW_ONLY
4. FULL = trend + price + confirmation + flow

Model: sklearn LogisticRegression, L2, C=1.0, max_iter=2000.
Preprocessing: median imputation from training fold only, StandardScaler fit on training fold only.
No class weighting.
No probability calibration fitted on test data.

## Walk-forward protocol

- Test 2024: train all eligible entries from 2021–2023.
- Test 2025: train 2021–2024.
- Test 2026 Mar–Aug: train 2021–2025.

No random train/test split is decision-bearing.

Primary ranking metrics:
- ROC AUC for IMPULSE60
- Brier score
- monotonicity of actual impulse rate across predicted probability quintiles

Trading diagnostics (not model-fitting target):
- CF191g trade EV, PF, SumR, MaxDD by predicted probability quintile
- 15/30/60/120m signed return/MFE/MAE by quintile
- regime buckets crossed with probability quintiles

## Success criteria

The FULL model is considered useful as a shadow quality score if:
1. pooled walk-forward AUC >= 0.58,
2. 2024, 2025 and 2026 each have AUC > 0.52,
3. top probability quintile has higher IMPULSE60 rate than bottom quintile in all three test periods,
4. top quintile CF191g EV is greater than bottom quintile EV in at least 2/3 test periods,
5. FULL is not materially worse than the best simpler family by >0.02 AUC pooled.

No hard entry veto or production risk multiplier is promoted by this LAB alone.

## Explicit anti-overfit rules

- no threshold optimization after results
- no EMA-period search
- no horizon search for the primary decision target
- no feature deletion based on observed coefficients in this LAB
- no hard-veto backtest promoted from diagnostic quintiles
- 2026 Mar–Aug is reused forward-shadow/stress, not pristine OOS
- BTCUSDT only; ETH/SOL transfer is not established here
