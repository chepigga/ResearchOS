# UNIVERSAL_CONTEXT_DIRECTIONAL_ASYMMETRY_AND_SEPARATE_BULL_BEAR_HEADS_LAB_004 — PREREG

Status: **FROZEN BEFORE OUTCOMES**

## Question
Does the frozen universal geometry layer from LAB002/LAB003 contain stable **directional asymmetry** such that separate causal BULL and BEAR predictive heads outperform a mirrored universal direction rule across XAUUSD, BTCUSDT and EURUSD?

LAB004 is an outcome-driven redesign after LAB003 and is therefore **discovery/confirmation on reused markets, not final fresh OOS proof**. No asset-specific parameter is allowed. A later LAB must replicate any accepted head on unseen markets.

## Frozen market universe / data
Identical to LAB001–003:
- XAUUSD — canonical `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`, SHA256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- BTCUSDT — Binance USD-M futures monthly 1h archive, `2021-01` through `2026-07`, resampled to H4.
- EURUSD — `v1.0/EURUSD_M1_202301020005_202607172354.csv`, SHA256 `09b872ae42af24ca67c525754da3266e21d96833fc9d66fe8bbdb1dac39836f5`, resampled to H4.

Closed H4 bars only; all predictions become available at H4 close.

## Frozen geometry
Import LAB002 `add_engine()` unchanged. States remain:
- EXPANSION
- RETRACEMENT
- COMPRESSION
- TRANSITION

No geometry weight, percentile lookback, threshold, or state definition may change.

## Additional causal features
From current closed H4 bar and known history only:
- `clv = (close-low)/(high-low)`, clipped [0,1].
- `bull_close_strength = clv`; `bear_close_strength = 1-clv`.
- upper/lower wick fractions.
- `bull_pressure = max(pressure,0)/100`; `bear_pressure=max(-pressure,0)/100`.
- `bull_range_pos=(range_pos24+1)/2`; `bear_range_pos=(1-range_pos24)/2`.
- boolean direction-specific EMA/order/slope/breakout terms.

No volume feature.

# A. EXPANSION — separate continuation heads
Eligible when `regime == EXPANSION`.

### EXPANSION_BULL score 0–100
- 30 × bull_pressure
- 20 × breakout_up
- 15 × trend_dir==+1
- 15 × bull_close_strength
- 10 × p_er
- 10 × p_adx

BULL signal if score >= **55**.
Outcome: `bull_signed8 = +1 * close_ret_8h_atr`.

### EXPANSION_BEAR score 0–100
- 25 × bear_pressure
- 25 × breakout_down
- 20 × trend_dir==-1
- 10 × bear_close_strength
- 10 × p_er
- 10 × p_adx

BEAR signal if score >= **65**.
Outcome: `bear_signed8 = -1 * close_ret_8h_atr`.

The different score weights/thresholds are frozen hypotheses motivated by LAB003 asymmetry and are universal across assets.

# B. RETRACEMENT — separate directional continuation heads
Eligible when `regime == RETRACEMENT`.

### RETRACEMENT_BULL score
- 25 × ordered_up
- 20 × close>=EMA50
- 20 × lower_wick > upper_wick
- 15 × positive slope50 × p_slope
- 10 × p_adx
- 10 × (1-p_dist20)

BULL if score >= **60**.
Outcome: `bull_signed24 = close_ret_24h_atr`.

### RETRACEMENT_BEAR score
- 25 × ordered_down
- 20 × close<=EMA50
- 20 × upper_wick > lower_wick
- 15 × negative slope50 × p_slope
- 10 × p_adx
- 10 × (1-p_dist20)

BEAR if score >= **65**.
Outcome: `bear_signed24 = -close_ret_24h_atr`.

If both heads fire on the same bar, classify `CONFLICT` and exclude from primary directional evaluation. If neither fires, abstain.

# C. COMPRESSION — separate first-passage heads
Eligible when `regime == COMPRESSION`.

### COMPRESSION_BULL score
- 30 × bull_pressure
- 20 × bull_range_pos
- 20 × 1[EMA20>EMA50] × p_spread
- 15 × 1[slope50>0] × p_slope
- 15 × 1[close>EMA20]

BULL if score >= **55**.

### COMPRESSION_BEAR score
- 30 × bear_pressure
- 25 × bear_range_pos
- 20 × 1[EMA20<EMA50] × p_spread
- 15 × 1[slope50<0] × p_slope
- 10 × 1[close<EMA20]

BEAR if score >= **60**.

If both heads fire: CONFLICT/exclude. Outcome is frozen LAB003 first unique ±1.0 ATR first passage within next 6 H4 bars (24h); same-bar double hit = AMBIGUOUS; no hit = NONE.

# Statistics
Deterministic cluster bootstrap: **5,000 draws by market × calendar-week**, seed `2026091304`.

Minimum primary cell size: N>=100 per market unless specifically stated. Pooled side comparisons require N>=300 per side.

## Primary hypotheses

### H1 — EXPANSION_BULL portability
Expansion BULL signal has mean `bull_signed8 > 0` in all 3 markets and pooled 95% CI lower bound >0.

### H2 — EXPANSION_BEAR portability
Expansion BEAR signal has mean `bear_signed8 > 0` in at least 2 of 3 markets, no eligible market mean < -0.03 ATR, and pooled 95% CI lower bound >0.

### H3 — EXPANSION directional asymmetry
Among eligible Expansion BULL vs BEAR signals, pooled `mean(BULL signed8)-mean(BEAR signed8) > 0` with bootstrap CI lower bound >0. Diagnostic market-level differences are reported but not required to share sign.

### H4 — RETRACEMENT_BULL portability
Retracement BULL signal has mean `bull_signed24 >0` in at least 2 of 3 markets, no market with N>=100 below -0.05 ATR, and pooled CI lower bound >0.

### H5 — RETRACEMENT_BEAR portability
Retracement BEAR signal has mean `bear_signed24 >0` in at least 2 of 3 markets, no market with N>=100 below -0.05 ATR, and pooled CI lower bound >0.

### H6 — COMPRESSION_BULL direction
For unique resolved first passages after Compression BULL signal: accuracy >50% in all 3 markets and pooled CI lower bound >50%.

### H7 — COMPRESSION_BEAR direction
For unique resolved first passages after Compression BEAR signal: accuracy >50% in at least 2 of 3 markets, no eligible market <47%, and pooled CI lower bound >50%.

### H8 — coverage / conflict sanity
For each market:
- Expansion BULL coverage 5–70% of Expansion; BEAR 3–60%.
- Retracement BULL and BEAR each 5–70% of Retracement.
- Compression BULL and BEAR each 5–70% of Compression.
- conflict rate within Retracement <=10%; Compression <=10%.

## Secondary diagnostics — cannot rescue primaries
- BULL/BEAR yearly stability.
- score deciles and monotonicity within each side.
- common-window `2023-06-01` through `2026-07-17`.
- side-specific 8h/24h distributions.
- state transition context before signals.

## Frozen verdicts
- `SEPARATE_BULL_BEAR_HEADS_SUPPORTED`: H1,H2,H4,H5,H6,H7,H8 PASS (H3 may pass or fail).
- `DIRECTIONAL_ASYMMETRY_CONFIRMED_BULL_HEADS_SUPPORTED_BEAR_NOT_SUPPORTED`: H1 PASS, at least one of H4/H6 PASS, H8 PASS, and at least two corresponding BEAR gates among H2/H5/H7 FAIL.
- `DIRECTIONAL_ASYMMETRY_PARTIAL_SUPPORT`: H8 PASS and at least 4 of H1–H7 PASS.
- `SEPARATE_BULL_BEAR_HEADS_NOT_SUPPORTED`: otherwise.
- `DATA_BLOCKED`: required data unavailable or <500 ready H4 bars per market.

## Anti-curve-fit boundary
After this prereg commit, no weights, side thresholds, geometry definitions, horizons, first-passage target, market universe, or pass/fail criteria may change in LAB004. Technical runtime/parser fixes that do not alter the frozen formulas are allowed and must be disclosed.
