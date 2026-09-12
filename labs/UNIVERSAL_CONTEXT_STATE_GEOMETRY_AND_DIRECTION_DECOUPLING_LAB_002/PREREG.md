# UNIVERSAL_CONTEXT_STATE_GEOMETRY_AND_DIRECTION_DECOUPLING_LAB_002 — PREREG

Status: **FROZEN BEFORE OUTCOMES**

## Question
Can a causal H4 universal context engine improve cross-market portability by separating **market-state geometry** from **directional pressure**, using one fixed normalized feature space and no asset-specific thresholds on XAUUSD, BTCUSDT, and EURUSD?

This LAB is a redesign prompted by LAB001. It tests state semantics + directional pressure only. It does not test OB/FVG/liquidity confirmation weights, entry timing, SL/TP, profitability, broker costs, or FTMO execution.

## Markets / data fixed before outcomes
Same frozen market universe and sources as LAB001:
1. **XAUUSD** — `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`, SHA256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
2. **BTCUSDT** — Binance USD-M futures monthly 1h archive, fixed calendar `2021-01` through `2026-07`, resampled to H4.
3. **EURUSD** — `v1.0/EURUSD_M1_202301020005_202607172354.csv`, SHA256 `09b872ae42af24ca67c525754da3266e21d96833fc9d66fe8bbdb1dac39836f5`, resampled to H4.

All features use closed H4 bars only and become available at H4 close (`available_time = H4 open + 4h`).

## Frozen normalized feature space
Use the same indicator and causal normalization family as LAB001:
- EMA20, EMA50, EMA200
- Wilder ATR14
- Wilder RSI14
- Wilder ADX14
- prior 20-bar high/low breakout / sweep
- rolling 24-bar range / ATR
- EMA spread / ATR
- |close-EMA20| / ATR
- EMA50 3-bar slope / ATR
- ER12
- rejection wick fraction
- EMA20 cross

Rolling causal percentile normalization: trailing **252 H4 bars including current closed bar**, `min_periods=126`.

Percentiles: `p_atr, p_adx, p_range, p_spread, p_dist20, p_er, p_slope, p_wick, p_rsi`.

Derived:
- `rsi_central = 1 - 2*abs(p_rsi-0.5)`, clipped [0,1].
- `ordered_stack = (EMA20>EMA50>EMA200) OR (EMA20<EMA50<EMA200)`.
- `stack_dir=+1` only if EMA20>EMA50>EMA200 and slope50/ATR>0; `-1` only if inverse and slope<0; otherwise 0.
- `breakout_dir=+1` if close > prior20 high; `-1` if close < prior20 low; otherwise 0.

No volume feature is allowed.

---
# A. MARKET-STATE GEOMETRY — direction agnostic

Core states are **EXPANSION / RETRACEMENT / COMPRESSION**. There is no REVERSAL competitor state.

All scores are 0–100 and smoothed by trailing 3-bar mean (`min_periods=3`). Same formulas for every market.

## EXPANSION_GEOMETRY
- 25 × breakout_any
- 20 × p_atr
- 20 × p_range
- 15 × p_er
- 10 × p_dist20
- 10 × p_adx

## RETRACEMENT_GEOMETRY
- 25 × ordered_stack
- 20 × p_slope
- 20 × (1-p_dist20)
- 15 × p_adx
- 10 × rsi_central
- 10 × not_breakout

## COMPRESSION_GEOMETRY
- 25 × (1-p_adx)
- 20 × (1-p_spread)
- 20 × (1-p_range)
- 15 × (1-p_er)
- 10 × (1-p_atr)
- 10 × not_ordered_stack

## TRANSITION rule
After smoothing:
- if top score < **50**, state=`TRANSITION`;
- OR top-minus-second score < **8**, state=`TRANSITION`;
- otherwise state=top geometry score.

The thresholds 50/8 are carried from LAB001 and are not retuned.

---
# B. DIRECTIONAL PRESSURE — independent of geometry state

Define one signed pressure score on `[-100,+100]` before 3-bar smoothing:

`pressure_raw =`
- 30 × `stack_dir`
- 20 × `sign(EMA20-EMA50) × p_spread`
- 20 × `sign(slope50_atr) × p_slope`
- 15 × `sign(close-EMA20) × p_dist20`
- 15 × `breakout_dir`

Then use trailing 3-bar mean, clipped to [-100,+100].

Frozen direction classes:
- `BULL` if pressure >= +20
- `BEAR` if pressure <= -20
- `NEUTRAL` otherwise
- `HIGH_PRESSURE` if abs(pressure) >= 50
- `MODERATE_PRESSURE` if 20 <= abs(pressure) < 50

No state is allowed to alter these direction thresholds.

---
# C. REVERSAL as event overlay, not state

REVERSAL is secondary diagnostic only.

Raw event score:
- 25 × sweep
- 15 × EMA20 cross
- 20 × p_wick
- 20 × RSI reversal turn
- 10 × ADX falling
- 10 × prior/current ordered directional stack exists

`REVERSAL_EVENT = score >= 50 AND (sweep OR EMA20_cross OR RSI_turn)`.

No smoothing is applied to the event score because it is an event overlay, not a persistent state.

---
# Forward outcomes
All outcomes begin after the signal H4 bar closes.

- `range8_atr`: high-low of next 2 H4 bars / current ATR14.
- `absclose8_atr`: abs(close[t+2]-close[t]) / ATR14.
- `direction_signed8_atr`: sign(pressure) × close change after next 2 H4 bars / ATR14, only if |pressure|>=20.
- `direction_signed24_atr`: sign(pressure) × close change after next 6 H4 bars / ATR14, only if |pressure|>=20.
- `reverse12_atr`: -prior stack direction × close change after next 3 H4 bars / ATR14 for REVERSAL_EVENT when prior direction !=0.

## Statistical protocol
All per-market primary cells require >=100 eligible bars unless stated otherwise.
Pooled 95% confidence intervals: deterministic **5,000-draw cluster bootstrap by market × calendar-week**, seed `2026091202`.

---
# Primary hypotheses / frozen pass-fail gates

## H1 — EXPANSION geometry has universal future-range meaning
For **each market**:
`mean(range8_atr | EXPANSION) - mean(range8_atr | not EXPANSION) > 0`.

Pooled bootstrap 95% CI lower bound must be >0.

## H2 — COMPRESSION geometry has universal future-range meaning
For **each market**:
`mean(range8_atr | COMPRESSION) - mean(range8_atr | not COMPRESSION) < 0`.

Pooled bootstrap 95% CI upper bound must be <0.

## H3 — Directional Pressure predicts direction cross-market
Among resolved BULL/BEAR bars (`|pressure|>=20`), `mean(direction_signed8_atr) > 0` in **all 3 markets**, and pooled bootstrap 95% CI lower bound >0.

## H4 — Pressure magnitude is informative
Compare HIGH vs MODERATE pressure among resolved bars:
`mean(direction_signed8_atr | HIGH) - mean(... | MODERATE) > 0` in at least **2 of 3 markets**, and pooled bootstrap 95% CI lower bound >0.

Secondary same comparison at 24h is diagnostic only.

## H5 — Direction is not merely a proxy for one geometry state
For each core geometry state, pool all markets and calculate resolved-direction `direction_signed8_atr` with >=200 eligible bars.

PASS if:
- at least **2 of 3** core geometry states have bootstrap 95% CI lower bound >0;
- the remaining eligible core state has observed mean >=0.

This is the key decoupling gate.

## H6 — Non-degenerate geometry breadth
For every market:
- at least 2 of the 3 core geometry states each occupy >=5% of ready bars;
- no core geometry state occupies >80%;
- TRANSITION <=50%.

---
# Secondary diagnostics — cannot rescue primary verdict
- RETRACEMENT future range and abs-close distributions.
- Direction accuracy by BULL vs BEAR separately.
- Direction performance by market × geometry state.
- Pressure deciles / monotonicity.
- REVERSAL_EVENT count and `reverse12_atr` if N>=50.
- state occupancy by market/year.
- common-window robustness: `2023-06-01` through `2026-07-17`.

# Verdict frozen
- `GEOMETRY_DIRECTION_DECOUPLING_SUPPORTED`: H1–H6 all PASS.
- `GEOMETRY_DIRECTION_DECOUPLING_PARTIAL_SUPPORT`: H3 and H6 PASS, and at least 4 of H1–H6 PASS total.
- `GEOMETRY_DIRECTION_DECOUPLING_NOT_SUPPORTED`: otherwise.
- `GEOMETRY_DIRECTION_DECOUPLING_DATA_BLOCKED`: any required market cannot be loaded/verified or has <500 ready H4 bars.

# Anti-curve-fit boundary
After this prereg commit, no score weights, percentile lookback, direction threshold, geometry threshold, market universe, event threshold, or primary pass/fail criterion may change in LAB002. Technical parser/runtime fixes are allowed only when they do not alter frozen formulas and must be disclosed. Any outcome-driven redesign requires LAB003.