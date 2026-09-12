# XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013 — PREREG

## Objective
Test whether the already-supported `PULLBACK + COMPRESSION` overlay can add a **causal directional-pressure label** for the first breakout resolution without becoming an automated trading signal.

LAB012 already supported the non-directional statement `PULLBACK + G1_VOL_COMPRESSION => breakout risk elevated`. LAB013 does **not** retest or optimize that risk overlay. It asks only whether the direction of resolution can be described as `BULL`, `BEAR`, or `UNRESOLVED` using information available at the H4 close where the overlay is shown.

No entries, TP/SL, EV, PF, sizing, commission, or prop-risk changes are tested.

## Frozen source and parity
- Base lineage: completed LAB012 output branch.
- Canonical XAUUSD M1 asset: release `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- Required SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Frozen H4 Context router, scores, smoothing, hysteresis, `PULLBACK` state, bias logic and G1 compression definition are unchanged.
- G1 is exactly `COMPRESSED_24 AND LOW_ATR`, with `range24_ratio < 0.85` and `atr_ratio < 0.95`.
- Primary population: frozen `PULLBACK` bars with G1 compression ON.
- Required Context parity: **6,216 valid H4 Context bars and 610 frozen episodes**.
- Expected primary compression count is approximately LAB012's 720 valid 8h observations; exact M1 path eligibility may differ only at the dataset tail or gaps.

All candidate definitions, targets and gates below are frozen **before LAB013 outcomes are computed**.

---

# Exact breakout-resolution target

At each eligible H4 bar, the information timestamp is frozen `available_time` (H4 close). Reference price is the closed H4 `close`; reference volatility is the closed H4 `ATR14`.

Using native M1 bars strictly from `available_time` forward for the next **8 hours**:
- upper barrier = `close + 1.0 * ATR14`;
- lower barrier = `close - 1.0 * ATR14`.

The first barrier touched defines the resolution:
- `BULL_FIRST` if +1 ATR is touched before -1 ATR;
- `BEAR_FIRST` if -1 ATR is touched before +1 ATR;
- `AMBIGUOUS` if both barriers are first touched in the same M1 bar because intrabar ordering is unknowable from M1 OHLC;
- `NO_BREAKOUT` if neither barrier is touched within 8h.

`AMBIGUOUS` and `NO_BREAKOUT` are excluded from the primary **direction-accuracy** metric but remain reported. There is no same-bar directional assumption.

This exact M1 first-passage outcome replaces H4 high/low approximation for LAB013.

---

# Frozen causal direction candidates

Every candidate emits `+1 = BULL`, `-1 = BEAR`, or `0 = UNRESOLVED` at the H4 close.

## D1_HTF_BIAS
Use the frozen Context bias directly:
- `BULL -> +1`
- `BEAR -> -1`
- `NEUTRAL -> 0`.

## D2_TREND_PRESSURE
Directional trend structure, with no optimized threshold:
- BULL if `close > EMA20 > EMA50` **and** `slope50_atr > 0`;
- BEAR if `close < EMA20 < EMA50` **and** `slope50_atr < 0`;
- otherwise UNRESOLVED.

## D3_PRE12H_MOMENTUM
Use the already frozen LAB008 pre-momentum direction:
- sign of `close[t] - close[t-3 H4 bars]`, requiring an exact contiguous 12h lookback;
- positive -> BULL, negative -> BEAR, zero/invalid -> UNRESOLVED.

## D4_CONSENSUS_2OF3
Vote D1, D2 and D3:
- BULL if at least 2 candidates vote BULL;
- BEAR if at least 2 candidates vote BEAR;
- otherwise UNRESOLVED.

No score weighting, confidence threshold, candidate subset, lookback search or tie-break optimization is allowed.

---

# D-H1 — first-passage direction accuracy

Primary metric for each D1–D4 candidate:

`accuracy = predicted direction == exact M1 BULL_FIRST/BEAR_FIRST`

only when:
- prediction is BULL or BEAR;
- exact 8h first-passage target is BULL_FIRST or BEAR_FIRST.

Report:
- directional prediction coverage among all eligible `PULLBACK + G1` bars;
- coverage among bars that actually resolve ±1 ATR within 8h;
- N predicted resolved breakouts;
- accuracy and edge over 50%: `accuracy - 0.50`;
- BULL and BEAR prediction counts and accuracies separately.

### Eligibility
A candidate is eligible for D-H1 if:
- >=100 predicted resolved-breakout observations overall;
- directional prediction coverage >=30% of eligible `PULLBACK + G1` bars;
- >=20 predicted resolved-breakout observations in both 2025 and 2026 YTD.

### Statistical pass
Weekly-cluster bootstrap with **5,000 draws** on binary correctness.

D-H1 passes when:
- observed accuracy >50%;
- 95% bootstrap CI lower bound for accuracy is >50%;
- yearly accuracy >50% in >=3/4 years 2023–2026, with each counted year having >=20 predicted resolved breakouts.

Secondary descriptive exact-M1 horizons: none. The primary 8h target is frozen; no horizon selection is permitted.

---

# D-H2 — directional resolution follow-through

A direction label that merely predicts which ±1 ATR barrier is touched first but has no residual directional information should not be promoted as `directional pressure`.

For every directional prediction with a contiguous future 24h H4 close, compute:

`pred_signed_close_atr_24h = prediction_sign * (close_24h - reference_close) / ATR14`.

This metric does **not** condition on which barrier was hit first.

D-H2 passes for a candidate when:
- N >=150 valid directional predictions overall;
- mean `pred_signed_close_atr_24h > 0`;
- weekly-cluster bootstrap 95% CI lower bound >0;
- positive yearly mean in >=3/4 years, each with >=20 valid predictions.

This is a semantic persistence/follow-through test, not PnL.

---

# D-H3 — direction must beat simple unconditional trend continuation

For each candidate report whether accuracy differs by frozen bias alignment:
- `WITH_BIAS`: prediction equals frozen non-neutral bias;
- `AGAINST_BIAS`: prediction opposes frozen non-neutral bias;
- `NO_BIAS`: frozen bias neutral.

This is diagnostic only and cannot rescue a failed D-H1/D-H2.

Also report unconditional target balance among exact 8h resolutions (`BULL_FIRST` vs `BEAR_FIRST`) so a candidate cannot appear accurate merely because one side dominates the sample.

---

# Predeclared candidate selection

A candidate is a **direction winner** only if both D-H1 and D-H2 pass.

Among qualifying candidates rank by:
1. higher D-H1 accuracy;
2. higher directional coverage;
3. higher D-H2 mean signed 24h ATR;
4. simpler preregistered order D1 -> D2 -> D3 -> D4 if still tied.

If no candidate passes both D-H1 and D-H2, there is no directional-pressure winner and the display must remain `DIRECTION UNRESOLVED`.

No post-result threshold or candidate invention is allowed.

---

# Additional resolution diagnostics

For the winning candidate, or for all candidates if none wins, report descriptively:
- median time to first ±1 ATR touch for correctly vs incorrectly predicted resolutions;
- `NO_BREAKOUT` and `AMBIGUOUS` rates;
- first-passage direction by year;
- prediction coverage by year;
- accuracy by BULL vs BEAR prediction;
- 24h signed close ATR by prediction side.

These diagnostics cannot override the frozen gates.

---

# Inference
- Weekly cluster bootstrap: **5,000 draws**.
- Fixed seed: `2026091213` plus deterministic offsets.
- Calendar weeks are resampled jointly.
- Year transfer: 2023, 2024, 2025, 2026 YTD.
- Same reused history as LAB007–012: all positive findings remain **DISCOVERY_ONLY** and require fresh post-freeze replication before production display changes.

# Verdict
- `COMPRESSION_DIRECTION_AND_RESOLUTION_SUPPORTED_DISCOVERY_ONLY` if at least one candidate passes both D-H1 and D-H2.
- `FIRST_BREAK_DIRECTION_ONLY_NOT_PERSISTENT` if at least one candidate passes D-H1 but none passes D-H2.
- `DIRECTION_UNRESOLVED_BREAKOUT_RISK_ONLY` if no candidate passes D-H1 and at least one candidate is eligible.
- `COMPRESSION_DIRECTION_UNDERPOWERED` only if all four candidates fail D-H1 minimum-N eligibility.

# Anti-overfit / product restriction
- No modification of Context state weights, smoothing, hysteresis, compression thresholds or Pullback definition.
- No optimization of EMA periods, momentum lookback, vote count, ATR barrier, horizon, coverage threshold, or confidence threshold.
- No post-result BUY-only/SELL-only filter can be promoted from this lab.
- LAB013 can support only the human-facing wording `directional pressure BULL/BEAR/UNRESOLVED`; it cannot authorize automated entries or risk changes.