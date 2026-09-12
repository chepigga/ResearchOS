# XAU_CONTEXT_REVERSAL_TEMPORAL_SEQUENCE_AND_COMPRESSION_STATE_INTERACTION_LAB_012 — PREREG

## Objective
Test two architecture claims suggested by LAB010–011 without changing the frozen Context router:

1. `REVERSAL` should be represented as a **causal temporal sequence event**, not a raw competing score/state.
2. frozen `G1_VOL_COMPRESSION` should be interpreted as a **breakout-risk overlay whose usefulness depends on the persistent main state**, with Pullback as the preregistered primary state from LAB011.

This is indicator / human-decision-support research only. No entries, TP/SL, EV, PF, position sizing or prop-firm risk are tested.

## Frozen source and parity
- Base lineage: completed LAB011 output commit `f8184e5d9d9327fcebc560bceda6a619b0e67977`.
- Canonical XAUUSD M1: release `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- Required SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Frozen H4 router, scores, smoothing, hysteresis, bias and availability logic remain unchanged.
- Required parity: **6,216 valid Context H4 bars and 610 frozen episodes**.
- Previously audited runtime/parity fixes are allowed only to execute frozen code.

All definitions below are frozen before LAB012 outcomes are computed.

---

# Part A — REVERSAL temporal sequence

## Frozen components
Use only already-frozen causal fields:
- `LOCATION = SWEEP OR REJECTION`.
- `TRANSITION = RSI_TURN OR ADX_FALLING`.
- `EMA20 directional cross` derived from frozen EMA20 and closes.
- pre-anchor 12h momentum = `close(anchor) - close(anchor-3 H4 bars)`; zero/invalid momentum is ineligible.

`EMA20_CROSS` is intentionally excluded from the transition stage because it is reserved as the structural-response stage.

## Ordered sequence definition — RSEQ_PRIMARY
A sequence is emitted only at the **response bar** `C` and must satisfy all of the following using contiguous H4 bars:

1. **A — location/rejection anchor:** `LOCATION=True` at an earlier bar A.
2. **B — transition clue:** on a later bar B, `TRANSITION=True`.
3. **C — structural response:** on bar C, price closes across EMA20 in the direction opposite the pre-anchor 12h momentum:
   - if anchor momentum < 0, C must be a bullish EMA20 cross (`close > EMA20` and previous close <= previous EMA20);
   - if anchor momentum > 0, C must be a bearish EMA20 cross (`close < EMA20` and previous close >= previous EMA20).
4. Timing is fixed: `A < B <= C`; B must occur within **2 H4 bars (8h)** after A; C must occur within **3 H4 bars (12h)** after A.
5. If multiple anchors/Bs map to one response bar, emit **one event at C** using the earliest qualifying anchor; no duplicate event on the same response bar.
6. No cooldown or threshold search is allowed.

The event is fully causal because it becomes visible only at close of C.

## R-H1 — state-stratified 24h reversal semantics
Primary states: frozen `PULLBACK`, `EXPANSION`, `RANGE`.

Primary metric: frozen `momentum_flip_24h` from LAB008–011, evaluated from the response/event bar C.

Control: non-sequence H4 bars with the **same frozen main state**.

Primary effect: event-minus-control momentum-flip premium within each state, aggregated with sequence-event-count weights.

Eligibility:
- >=30 valid sequence events overall;
- >=5 valid events in both 2025 and 2026 YTD;
- >=2 state strata with >=5 valid sequence events.

Pass:
- observed 24h state-stratified flip premium >0;
- weekly-cluster bootstrap 95% CI lower bound >0;
- positive annual premium in >=3/4 years where each year has >=5 valid sequence events.

## R-H2 — directional follow-through after confirmed sequence
The sequence direction is fixed at C:
- bullish sequence = +1;
- bearish sequence = -1.

Metric: `SEQ_SIGNED_CLOSE_ATR_24H = sequence_direction * (close_24h - close_C) / ATR14_C`.

Eligibility: same event-count gate as R-H1.

Pass:
- mean signed 24h follow-through >0;
- weekly-cluster bootstrap 95% CI lower bound >0;
- positive mean in >=3/4 eligible years.

This tests whether the event remains useful **after** confirmation rather than merely describing a reversal that has already completed.

## Secondary reversal diagnostics
Cannot override primary gates:
- event count and direction by year/main state;
- 8h and 12h state-stratified `momentum_flip` premiums;
- overlap with LAB011 `R3_RAW_REVERSAL_WINNER` and its suppressed subset;
- stage latency distributions A→B and A→C;
- bullish vs bearish sequence semantics;
- descriptive comparison with raw R3 suppressed events.

No alternate windows or sequence variants can replace RSEQ_PRIMARY after results.

---

# Part B — COMPRESSION × main-state interaction

## Frozen overlay
Use exactly LAB010–011 `G1_VOL_COMPRESSION`:
`range24_ratio < 0.85 AND atr_ratio < 0.95`.

No threshold changes.

## C-H1 — Pullback 8h breakout risk (primary replication)
Scope: frozen `PULLBACK` bars only.

Metric: `breakout_1atr_8h = 1 - contained_1atr_8h`.

Compare G1 vs non-G1 Pullback bars.

Eligibility:
- >=300 valid G1 Pullback bars overall;
- >=50 valid G1 Pullback bars in both 2025 and 2026 YTD.

Pass:
- breakout premium >0;
- weekly-cluster bootstrap 95% CI lower bound >0;
- positive premium in >=3/4 years.

## C-H2 — Pullback 24h movement follow-through
Scope: frozen `PULLBACK` only.

Metric: `range_atr_24h`.

Compare G1 vs non-G1 Pullback bars.

Eligibility: same as C-H1.

Pass:
- 24h range premium >0;
- weekly-cluster bootstrap 95% CI lower bound >0;
- positive premium in >=3/4 years.

## C-H3 — Pullback vs Expansion interaction
Primary interaction metric:
`[breakout premium of G1 within PULLBACK] - [breakout premium of G1 within EXPANSION]` at 8h.

Eligibility:
- >=300 valid G1 Pullback bars;
- >=20 valid G1 Expansion bars;
- both states have non-G1 controls.

Pass:
- interaction >0;
- weekly-cluster bootstrap 95% CI lower bound >0.

This is the preregistered test of the LAB011 discovery that compression appears structurally associated with Pullback and is scarce inside Expansion.

## Secondary compression diagnostics
Cannot override C-H1/C-H2/C-H3:
- G1 prevalence by year and frozen state;
- 4h and 12h breakout premiums inside Pullback;
- Expansion-only 8h/24h premiums;
- descriptive `RANGE`-state G1 premiums;
- 12h transition probability into frozen `EXPANSION`, G1 vs non-G1 within Pullback.

---

# Inference
- Weekly cluster bootstrap: **5,000 draws**.
- Fixed seed: `2026091212` plus deterministic offsets.
- Calendar weeks resampled jointly.
- Year transfer: 2023, 2024, 2025, 2026 YTD.
- No post-result threshold, window, direction or main-state subset search.
- Reused history: all positive findings remain **DISCOVERY_ONLY** and require fresh post-freeze replication before production display changes.

# Verdict
Five primary gates: `R-H1`, `R-H2`, `C-H1`, `C-H2`, `C-H3`.

- `TEMPORAL_SEQUENCE_AND_COMPRESSION_INTERACTION_SUPPORTED_DISCOVERY_ONLY` if all 5 pass.
- `PARTIAL_TEMPORAL_SEQUENCE_COMPRESSION_SUPPORT` if 2–4 gates pass and at least one gate passes on each side (Reversal and Compression).
- `COMPRESSION_INTERACTION_SUPPORTED_REVERSAL_SEQUENCE_NOT_CONFIRMED` if C-H1 and C-H2 pass but both R-H1 and R-H2 fail/underpower.
- `REVERSAL_SEQUENCE_SUPPORTED_COMPRESSION_INTERACTION_NOT_CONFIRMED` if R-H1 and R-H2 pass but C-H1 and C-H2 fail.
- `TEMPORAL_SEQUENCE_AND_COMPRESSION_INTERACTION_NOT_SUPPORTED` if <=1 gate passes.
- `LAB012_UNDERPOWERED` only if both R-H1 and C-H1 fail eligibility.

# Anti-overfit / production restrictions
- Frozen router remains untouched.
- One primary reversal sequence only; no winner selection among variants.
- Frozen G1 compression only.
- Secondary tables cannot rescue failed primaries.
- This lab validates display semantics only; it cannot authorize automated entries, lot changes or prop-challenge risk changes.
