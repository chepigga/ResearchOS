# UNIVERSAL_CONTEXT_NORMALIZED_CROSS_MARKET_STATE_ENGINE_LAB_001 — PREREG

Status: **FROZEN BEFORE OUTCOMES**

## Question
Can one causal H4 market-state engine, using only rolling normalized price/volatility/structure features and **no asset-specific thresholds**, preserve the same forward semantics on XAUUSD, BTCUSDT and EURUSD?

This LAB tests the **state layer only**. It does not test OB/FVG/liquidity confirmation weights, entry/SL/TP, profit probability, broker costs, or FTMO execution parity.

## Markets / data fixed before outcomes
1. **XAUUSD** — canonical native M1 release `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`, SHA256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
2. **BTCUSDT** — Binance USD-M futures public monthly 1h archive, fixed calendar `2021-01` through `2026-07`, resampled to H4.
3. **EURUSD** — ResearchOS release `v1.0/EURUSD_M1_202301020005_202607172354.csv`, SHA256 `09b872ae42af24ca67c525754da3266e21d96833fc9d66fe8bbdb1dac39836f5`, resampled to H4.

Each source uses its native timestamp clock. All features use closed H4 bars only and become available at H4 close (`available_time = H4 open + 4h`).

## Universal feature set
No volume feature is allowed in LAB001 because BTC volume is traded volume while MT5 FX/XAU sources are not guaranteed to have the same volume semantics.

Base indicators:
- EMA20, EMA50, EMA200 (`adjust=False`)
- Wilder ATR14
- Wilder RSI14
- Wilder ADX14
- prior 20-bar high/low breakout and sweep
- 24-bar high-low range
- EMA spread / ATR
- |close-EMA20| / ATR
- EMA50 3-bar slope / ATR
- 12-bar efficiency ratio: `abs(close-close[-12]) / sum(abs(delta close),12)`
- rejection wick fraction of candle range
- EMA20 cross event

Directional stack:
- `trend_dir=+1` if EMA20>EMA50>EMA200 and EMA50 slope/ATR > 0
- `trend_dir=-1` if EMA20<EMA50<EMA200 and EMA50 slope/ATR < 0
- else 0

## Causal normalization
For each continuous feature below, compute the current bar's percentile rank within the trailing **252 H4 bars including the current closed bar**, `min_periods=126`. No future values are used.

Normalized percentiles:
- `p_atr`: percentile of ATR14/close
- `p_adx`: percentile of ADX14
- `p_range`: percentile of `(rolling24 high-low)/ATR14`
- `p_spread`: percentile of EMA spread/ATR
- `p_dist20`: percentile of |close-EMA20|/ATR
- `p_er`: percentile of ER12
- `p_slope`: percentile of abs(EMA50 slope/ATR)
- `p_wick`: percentile of rejection wick fraction
- `p_rsi`: percentile of RSI14

Derived normalized terms:
- `rsi_central = 1 - 2*abs(p_rsi-0.5)`, clipped [0,1]
- RSI reversal turn = previous `p_rsi<0.20` and current RSI rises, or previous `p_rsi>0.80` and current RSI falls.

## Frozen state scores — same formula for every market
All scores are on 0–100 scale and then smoothed by trailing 3-bar mean (`min_periods=3`).

### EXPANSION
- 25 × stack
- 15 × breakout
- 15 × p_atr
- 15 × p_adx
- 10 × p_range
- 10 × p_er
- 10 × p_dist20

### PULLBACK
- 25 × stack
- 25 × (1-p_dist20)
- 15 × p_adx
- 15 × p_slope
- 10 × rsi_central
- 10 × not_breakout

### RANGE
- 25 × (1-p_adx)
- 20 × (1-p_spread)
- 20 × (1-p_range)
- 15 × (1-p_er)
- 10 × (1-p_atr)
- 10 × not_stack

### REVERSAL
- 25 × sweep
- 15 × EMA20 cross
- 20 × p_wick
- 20 × RSI reversal turn
- 10 × ADX falling vs previous bar
- 10 × prior/current directional stack exists

## TRANSITION / CHOP rule
After score smoothing:
- if top score < **50**, label `TRANSITION`;
- OR if top-minus-second score < **8**, label `TRANSITION`;
- otherwise label the top-scoring core state.

No asset-specific state threshold, weight, lookback, or override is allowed.

## Forward outcomes
All outcomes begin only after the signal H4 bar is closed.

- `range8_atr`: high-low range of the next 2 H4 bars / current ATR14.
- `absclose8_atr`: absolute close change after next 2 H4 bars / current ATR14.
- `signed8_atr`: trend_dir × close change after next 2 H4 bars / current ATR14.
- `signed24_atr`: trend_dir × close change after next 6 H4 bars / current ATR14.
- Reversal secondary: `reverse12_atr = -prior_trend_dir × close change after next 3 H4 bars / ATR14` when prior_trend_dir != 0.

## Primary preregistered hypotheses
All per-market effects require at least **100 eligible bars**. Pooled confidence intervals use deterministic 5,000-draw cluster bootstrap resampling by market×calendar-week, seed `2026091201`.

### H1 — EXPANSION semantics
For each of XAU/BTC/EUR:
`mean(range8_atr | EXPANSION) - mean(range8_atr | not EXPANSION) > 0`.
Pooled bootstrap 95% CI lower bound must also be >0.

### H2 — RANGE semantics
For each market:
`mean(range8_atr | RANGE) - mean(range8_atr | not RANGE) < 0`.
Pooled bootstrap 95% CI upper bound must also be <0.

### H3 — PULLBACK continuation semantics
Among PULLBACK bars with non-zero trend_dir:
`mean(signed24_atr) > 0` in at least **2 of 3 markets**, and pooled bootstrap 95% CI lower bound >0.

### H4 — EXPANSION directional continuation
Among EXPANSION bars with non-zero trend_dir:
`mean(signed8_atr) > 0` in at least **2 of 3 markets**, and pooled bootstrap 95% CI lower bound >0.

### H5 — non-degenerate universal state breadth
For every market:
- at least 3 of the 4 core states each occupy >=3% of ready bars;
- no core state occupies >75%;
- TRANSITION occupies <=50%.

## Secondary diagnostics — cannot rescue a failed primary verdict
- REVERSAL `reverse12_atr` by market and pooled, only when N>=50.
- state occupancy by market/year;
- episode duration / state switching rate;
- score-gap distributions;
- common-window robustness: 2023-06-01 through 2026-07-17.

## Verdict frozen
- `UNIVERSAL_STATE_ENGINE_SUPPORTED`: H1,H2,H3,H4,H5 all PASS.
- `UNIVERSAL_STATE_ENGINE_PARTIAL_SUPPORT`: H5 PASS and at least 3 of H1–H4 PASS.
- `UNIVERSAL_STATE_ENGINE_NOT_SUPPORTED`: otherwise.
- `UNIVERSAL_STATE_ENGINE_DATA_BLOCKED`: any required market cannot be loaded/verified or has <500 ready H4 bars.

## Anti-curve-fit boundary
After this prereg commit, no score weight, percentile lookback, transition threshold, market universe, or primary pass/fail criterion may be changed in LAB001. Technical parser/runtime fixes are allowed only if they do not change the frozen formulas and must be disclosed. Any hypothesis formed from LAB001 outcomes requires a new LAB.