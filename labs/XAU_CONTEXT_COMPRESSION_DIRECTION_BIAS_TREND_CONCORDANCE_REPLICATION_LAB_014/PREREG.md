# XAU_CONTEXT_COMPRESSION_DIRECTION_BIAS_TREND_CONCORDANCE_REPLICATION_LAB_014 — PREREG

## Objective
Replicate the post-hoc LAB013 finding that `D1_HTF_BIAS` and `D2_TREND_PRESSURE` agreement may improve human-facing breakout-resolution direction inside the already-supported `PULLBACK + G1_VOL_COMPRESSION` overlay.

This is a **replication / indicator-semantics** lab. It does not test trading entries, TP/SL, EV, PF, sizing, commission or prop-firm risk.

## Frozen source and parity
- Base lineage: completed LAB013 output branch.
- Canonical XAUUSD M1 asset: release `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- Required SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Frozen H4 Context router, scores, smoothing, hysteresis, `PULLBACK` state, bias logic and G1 definition remain unchanged.
- G1 remains exactly `range24_ratio < 0.85 AND atr_ratio < 0.95`.
- Required Context parity: **6,216 valid H4 bars and 610 frozen episodes**.
- Primary population: frozen `PULLBACK` bars with G1 compression ON.

All definitions and gates below are frozen before LAB014 outcomes are computed.

## Frozen direction inputs
### D1_HTF_BIAS
- `BULL -> +1`
- `BEAR -> -1`
- `NEUTRAL -> 0`

### D2_TREND_PRESSURE
- BULL if `close > EMA20 > EMA50` and `slope50_atr > 0`;
- BEAR if `close < EMA20 < EMA50` and `slope50_atr < 0`;
- otherwise `0 = UNRESOLVED`.

## Replication rule — D14_CONCORDANCE
- `+1 BULL` only when D1=+1 and D2=+1;
- `-1 BEAR` only when D1=-1 and D2=-1;
- otherwise `0 = UNRESOLVED`.

No score weighting, confidence threshold, EMA change, slope threshold, state-age filter, session filter, or post-result subset is allowed.

## Exact breakout target
Use exactly LAB013's native-M1 first-passage target from frozen H4 `available_time` over the next **8h**:
- upper barrier = H4 close + 1.0 ATR14;
- lower barrier = H4 close - 1.0 ATR14;
- `BULL_FIRST`, `BEAR_FIRST`, `AMBIGUOUS` (same first M1 bar), or `NO_BREAKOUT`.

`AMBIGUOUS` and `NO_BREAKOUT` are excluded from direction accuracy but remain reported.

# H1 — Concordance first-passage accuracy replication
Metric: exact first-passage direction accuracy among D14 directional predictions that resolve ±1 ATR within 8h.

Eligibility:
- >=150 resolved D14 predictions overall;
- D14 directional coverage >=40% of all eligible Pullback+G1 bars;
- >=30 resolved D14 predictions in both 2025 and 2026 YTD.

Pass:
- accuracy >50%;
- weekly-cluster bootstrap 95% CI lower bound >50%;
- yearly accuracy >50% in >=3/4 years 2023–2026, each counted year N>=25.

# H2 — 24h directional follow-through replication
For every D14 directional prediction with exact contiguous +24h H4 close:
`pred_signed_close_atr_24h = sign * (close_24h - reference_close) / ATR14`.

Eligibility: >=200 valid D14 directional predictions overall.

Pass:
- mean >0;
- weekly-cluster bootstrap 95% CI lower bound >0;
- positive yearly mean in >=3/4 years, each counted year N>=25.

# H3 — BULL / BEAR symmetry
This is a required robustness gate.

Eligibility:
- >=60 resolved BULL predictions;
- >=60 resolved BEAR predictions.

Pass:
- BULL accuracy >50%;
- BEAR accuracy >50%;
- neither side is below 47.5%;
- absolute difference between BULL and BEAR accuracy <=10 percentage points.

No side may be removed after seeing outcomes.

# H4 — Incremental value of concordance over D2 when HTF bias is neutral
Diagnostic discovered in LAB013: D2 WITH_BIAS accuracy was ~60.45% while D2 with neutral bias was ~45.65%.

Define:
- `CONCORDANT`: D14 directional predictions;
- `D2_NO_BIAS`: D2 directional prediction while D1=0.

Primary contrast: exact 8h first-passage accuracy(CONCORDANT) - accuracy(D2_NO_BIAS).

Eligibility:
- >=150 resolved CONCORDANT;
- >=30 resolved D2_NO_BIAS.

Pass:
- observed difference >0;
- weekly-cluster bootstrap 95% CI lower bound >0.

H4 is evidence that requiring concordance adds information rather than merely reducing coverage. H4 is required for the strongest verdict but failure does not invalidate H1/H2/H3 semantic usefulness.

# Coverage / abstention diagnostics
Report:
- total Pullback+G1 bars;
- D14 directional coverage;
- share `UNRESOLVED`;
- target BULL/BEAR balance;
- NO_BREAKOUT and AMBIGUOUS rates;
- D14 coverage and accuracy by year;
- BULL and BEAR N / accuracy / 24h signed ATR separately;
- median exact M1 time to first ±1ATR for correct vs incorrect predictions.

# Inference
- Weekly cluster bootstrap: **5,000 draws**.
- Fixed seed: `2026091214` plus deterministic offsets.
- Year transfer: 2023, 2024, 2025, 2026 YTD.
- Reused history: all positive findings remain **DISCOVERY_ONLY** until fresh post-freeze replication.

# Verdict
- `BIAS_TREND_CONCORDANCE_REPLICATED_DISCOVERY_ONLY` if H1, H2, H3 and H4 all pass.
- `BIAS_TREND_CONCORDANCE_SEMANTICS_SUPPORTED_INCREMENT_NOT_CONFIRMED` if H1, H2 and H3 pass but H4 fails or is underpowered.
- `BIAS_TREND_CONCORDANCE_DIRECTION_ONLY_NOT_PERSISTENT` if H1 and H3 pass but H2 fails.
- `BIAS_TREND_CONCORDANCE_NOT_REPLICATED` if H1 fails while eligible.
- `BIAS_TREND_CONCORDANCE_UNDERPOWERED` if H1 is ineligible.

## Anti-overfit / product restriction
- No threshold, horizon, EMA, bias, ATR barrier, coverage or state filter changes after outcomes.
- No BUY-only or SELL-only promotion.
- This lab can support only a human-facing `directional pressure BULL/BEAR/UNRESOLVED` display; it cannot authorize automated entries or risk changes.
