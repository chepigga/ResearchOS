# UNIVERSAL_CONTEXT_STATE_SPECIFIC_PREDICTIVE_HEADS_LAB_003 — PREREG

Status: **FROZEN BEFORE OUTCOMES**

## Question
Can the frozen universal geometry layer from LAB002 support **different causal predictive heads for different market geometries**, instead of forcing one directional model across EXPANSION / RETRACEMENT / COMPRESSION?

LAB003 does **not** change the LAB002 geometry engine. It tests three state-specific prediction heads only:
1. `EXPANSION_HEAD` → continuation direction.
2. `RETRACEMENT_HEAD` → parent-trend continuation vs reversal.
3. `COMPRESSION_HEAD` → first breakout direction.

No asset-specific threshold, weight, feature definition, or override is allowed.

## Frozen market universe / data
Identical to LAB001–002:
- **XAUUSD** — `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`, SHA256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- **BTCUSDT** — Binance USD-M futures monthly 1h archive, `2021-01` through `2026-07`, resampled to H4.
- **EURUSD** — `v1.0/EURUSD_M1_202301020005_202607172354.csv`, SHA256 `09b872ae42af24ca67c525754da3266e21d96833fc9d66fe8bbdb1dac39836f5`, resampled to H4.

Closed H4 bars only. Prediction becomes available at H4 close.

## Frozen geometry layer
Import and use LAB002 `add_engine()` unchanged.

States:
- `EXPANSION`
- `RETRACEMENT`
- `COMPRESSION`
- `TRANSITION`

LAB002 Directional Pressure is available as an input feature but is **not** itself the universal decision rule.

## Additional causal bar/context features
All computed from the current closed H4 bar and already-known history:
- `bar_dir = sign(close-open)`
- current upper/lower wick fractions of bar range
- prior-24-bar high/low excluding current bar
- `range_pos24 = 2*(close-prior24_low)/(prior24_high-prior24_low)-1`, clipped [-1,+1]
- `ema20_side = sign(close-EMA20)`
- `ema50_side = sign(close-EMA50)`
- `cross_against_parent` defined below
- `against_parent_sweep` defined below

No volume feature.

---
# A. EXPANSION_HEAD — continuation
Eligible only when `regime == EXPANSION` and LAB002 `pressure_dir != 0`.

Prediction direction:
`exp_dir = pressure_dir`.

Confidence score on 0–100:
- 30 × `abs(pressure)/100`
- 25 × `breakout_dir == exp_dir AND breakout_dir != 0`
- 20 × `trend_dir == exp_dir AND trend_dir != 0`
- 15 × `p_er`
- 10 × `p_adx`

Classes:
- `HIGH` if score >=60
- `MODERATE` if 40<=score<60
- `LOW` otherwise

Outcome:
`exp_signed8 = exp_dir * close_ret_8h_atr`.

---
# B. RETRACEMENT_HEAD — continuation vs reversal
Eligible only when `regime == RETRACEMENT` and `parent_dir = trend_dir != 0`.

### Continuation score 0–100
- 25 × `parent_dir*(close-EMA20) >= 0`
- 20 × `parent_dir*(close-EMA50) >= 0`
- 20 × directional rejection dominance:
  - bullish parent: lower wick > upper wick
  - bearish parent: upper wick > lower wick
- 15 × `p_slope`
- 10 × `p_adx`
- 10 × `(1-p_dist20)`

### Reversal score 0–100
- 30 × `parent_dir*(close-EMA50) < 0`
- 25 × `cross_against_parent`
- 20 × `against_parent_sweep`
- 15 × opposite-parent rejection dominance
- 10 × `rsi_turn`

Where:
- bullish-parent `cross_against_parent`: previous close>=previous EMA20 AND current close<EMA20;
- bearish-parent inverse;
- bullish-parent `against_parent_sweep`: high>prior20_high AND close<prior20_high;
- bearish-parent inverse: low<prior20_low AND close>prior20_low.

Classification:
- `CONTINUATION` if continuation score >=60 AND reversal score <50.
- `REVERSAL` if reversal score >=50 AND continuation score <60.
- otherwise `ABSTAIN`.

Outcomes:
- continuation: `parent_signed24 = parent_dir * close_ret_24h_atr`.
- reversal: `reverse_parent_signed24 = -parent_dir * close_ret_24h_atr`.

---
# C. COMPRESSION_HEAD — breakout direction
Eligible only when `regime == COMPRESSION`.

Signed head score before smoothing:
`compression_raw =`
- 35 × `(pressure/100)`
- 25 × `range_pos24`
- 20 × `sign(EMA20-EMA50) * p_spread`
- 20 × `sign(slope50_atr) * p_slope`

Use trailing 3-bar mean and clip to [-100,+100].

Prediction:
- BULL if score>=+20
- BEAR if score<=-20
- NEUTRAL otherwise
- HIGH if abs(score)>=50
- MODERATE if 20<=abs(score)<50

### Compression first-passage outcome
Starting after the signal H4 close, inspect the next 6 H4 bars (24h):
- upper target = signal close + 1.0*ATR14
- lower target = signal close - 1.0*ATR14
- first unique target hit determines `fp_dir` (+1/-1)
- if both targets are hit in the same first-hit bar, outcome=`AMBIGUOUS` and is excluded from directional accuracy
- if neither target is hit within 24h, outcome=`NONE`

Primary compression accuracy uses only unique resolved first passages.

---
# Statistics
Cluster bootstrap: deterministic **5,000 draws by market × calendar-week**, seed `2026091303`.

Minimum cell sizes:
- market-level EXPANSION / RETRACEMENT continuation primary cells: N>=100.
- RETRACEMENT reversal: at least 2 markets N>=50 and pooled N>=200.
- COMPRESSION first-passage: each market N>=100 resolved predictions.

## Primary hypotheses

### H1 — EXPANSION_HEAD universal continuation
For HIGH EXPANSION_HEAD:
- `mean(exp_signed8)>0` in all 3 markets;
- pooled bootstrap 95% CI lower bound >0.

### H2 — EXPANSION confidence adds value
Within EXPANSION, HIGH minus non-HIGH resolved `exp_signed8` >0 in at least 2 of 3 markets and pooled bootstrap CI lower bound >0.

### H3 — RETRACEMENT continuation head
For RETRACEMENT classified CONTINUATION:
- `mean(parent_signed24)>0` in at least 2 of 3 markets;
- no market with N>=100 may have mean < -0.05 ATR;
- pooled bootstrap CI lower bound >0.

### H4 — RETRACEMENT reversal head
For RETRACEMENT classified REVERSAL:
- at least 2 markets have N>=50 and positive `reverse_parent_signed24`;
- pooled N>=200;
- pooled bootstrap CI lower bound >0.

### H5 — COMPRESSION breakout-direction head
Among COMPRESSION bars with non-neutral head and unique ±1 ATR first passage:
- accuracy >50% in all 3 markets;
- each market N>=100;
- pooled bootstrap 95% CI lower bound >50%.

### H6 — head coverage / abstention sanity
For every market:
- EXPANSION HIGH coverage among eligible EXPANSION >=10% and <=80%;
- RETRACEMENT non-ABSTAIN coverage >=10% and <=80%;
- COMPRESSION non-neutral coverage >=20% and <=90%.

## Secondary diagnostics — cannot rescue primary verdict
- BULL vs BEAR asymmetry for each head.
- HIGH vs MODERATE compression accuracy.
- 8h/24h signed-return distributions.
- yearly stability.
- common-window robustness `2023-06-01` through `2026-07-17`.
- transition matrices between geometry states.

## Verdict
- `STATE_SPECIFIC_HEADS_SUPPORTED`: H1,H3,H5,H6 PASS and at least 5/6 hypotheses PASS.
- `STATE_SPECIFIC_HEADS_PARTIAL_SUPPORT`: H6 PASS, at least 2 of H1/H3/H5 PASS, and at least 4/6 total PASS.
- `STATE_SPECIFIC_HEADS_NOT_SUPPORTED`: otherwise.
- `STATE_SPECIFIC_HEADS_DATA_BLOCKED`: required market/data unavailable or <500 ready H4 bars.

## Boundary
This LAB tests predictive semantics only. It does **not** establish entry timing, SL/TP, profit probability, spread/commission/slippage economics, or FTMO execution parity.

After this prereg commit, no weights, thresholds, target horizons, state definitions, market universe, or pass/fail criteria may change inside LAB003. Technical runtime/parser fixes that do not alter formulas are allowed and must be disclosed.