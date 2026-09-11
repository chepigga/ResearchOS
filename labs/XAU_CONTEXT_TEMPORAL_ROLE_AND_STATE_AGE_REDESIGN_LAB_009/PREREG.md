# XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009 — PREREG

## Objective
Test a **causal display-layer redesign** of the frozen H4 XAU Context indicator suggested by LAB008: the four labels should not all be treated as equal persistent regimes.

This is a state-description / human-decision-support lab, **not** a trading-alpha lab. No entries, TP/SL, EV, PF, sizing, commissions, or live-risk claims.

## Frozen source
- Base branch lineage includes completed LAB008 outputs.
- Canonical XAUUSD M1 release asset: `ak47/XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`.
- Required SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Frozen H4 Context router from `CROSS_MARKET_CAUSAL_CONTEXT_ROUTER_LAB_001` with only previously audited runtime/parity fixes.
- Frozen regimes, scores, weights, smoothing, hysteresis, bias, and available-time logic are unchanged.
- Exact LAB008 parity target: **6,216 valid Context H4 bars and 610 state episodes**.

## Why this lab exists
LAB008 was discovery on reused history and suggested:
- `REVERSAL` behaves more like an onset event than a persistent regime;
- `RANGE` looks short-lived;
- `PULLBACK` and `EXPANSION` may become more semantically useful after persistence is established.

LAB009 preregisters that interpretation **before** recomputing the outcomes. Because the history is reused, even a pass is `DISCOVERY_ONLY`; true validation still requires fresh post-freeze data.

## Frozen episode age
For each contiguous H4 regime episode:
- `ONSET`: episode age = 1 H4 bar.
- `EARLY`: age = 2–3 H4 bars.
- `MATURE`: age >= 4 H4 bars.

Age uses only already observed bars and is causal.

## Frozen redesigned display roles
Every eligible H4 bar is mapped causally to one role:

1. `REVERSAL_EVENT`
   - regime = `REVERSAL`
   - age = 1 only.
   - Reversal ages >=2 are **not** treated as continuing reversal evidence; they are labeled `REVERSAL_AFTERGLOW` for diagnostics only.

2. `RANGE_SHORT`
   - regime = `RANGE`
   - age <=2.
   - Range age >=3 becomes `RANGE_STALE`.

3. `PULLBACK_FORMING`
   - regime = `PULLBACK`
   - age <=3.

4. `PULLBACK_MATURE`
   - regime = `PULLBACK`
   - age >=4.

5. `EXPANSION_FORMING`
   - regime = `EXPANSION`
   - age <=3.

6. `EXPANSION_MATURE`
   - regime = `EXPANSION`
   - age >=4.

No score-gap/purity threshold is part of the redesigned role. LAB008 did not support score-gap purity as a useful purifier.

## Frozen semantic metrics
Reference price = close of the H4 bar that produced the state; ATR = ATR14(H4) known at that close. Future path begins only after `available_time`.

- `range_atr_H = (future max high - future min low)/ATR14`.
- `contained_1atr_H = 1` iff neither +1ATR nor -1ATR is touched within H.
- `bias_follow_H = 1` iff H close return is in frozen Context bias direction; neutral bias excluded.
- `momentum_flip_H = 1` iff H close return is opposite the already-known pre-state 12h momentum direction; zero/invalid pre-momentum excluded.

## Primary preregistered role hypotheses
All directions below are frozen before LAB009 outcome computation.

### H1 — REVERSAL is an onset event, not a persistent state
At **24h**:
`P(momentum_flip | REVERSAL_EVENT) - P(momentum_flip | REVERSAL_AFTERGLOW) > 0`.

Secondary comparator, descriptive only:
`REVERSAL_EVENT` vs `EXPANSION_FORMING` on 24h momentum flip.

### H2 — RANGE is a short-lived containment condition
At **8h**:
`P(contained_1atr | RANGE_SHORT) - P(contained_1atr | RANGE_STALE) > 0`.

Secondary comparator, descriptive only:
`RANGE_SHORT` vs `EXPANSION_FORMING` on 8h containment.

### H3 — PULLBACK gains continuation meaning with maturity
At **24h**:
`P(bias_follow | PULLBACK_MATURE) - P(bias_follow | PULLBACK_FORMING) > 0`.

### H4 — EXPANSION gains movement meaning with maturity
At **24h**:
`mean(range_atr | EXPANSION_MATURE) - mean(range_atr | EXPANSION_FORMING) > 0`.

### H5 — Mature PULLBACK is directionally informative in absolute terms
At **24h**:
`P(bias_follow | PULLBACK_MATURE) - 0.50 > 0`.

### H6 — Mature EXPANSION separates from short RANGE
At **24h**:
`mean(range_atr | EXPANSION_MATURE) - mean(range_atr | RANGE_SHORT) > 0`.

## Secondary time-shape audit
Without changing the primary verdict, report the same role metrics on 4h, 8h, 12h, 24h, and 48h to show decay / persistence shape.

The chosen primary horizons above cannot be changed after results.

## Inference
- Weekly cluster bootstrap, **5,000 draws**.
- Fixed seed: `2026091109` plus deterministic hypothesis offsets.
- Calendar weeks are resampled jointly for pairwise comparisons.
- A primary gate passes iff observed effect >0 **and** the 95% weekly-cluster bootstrap lower bound >0.
- For H5 one-sample bias-follow test, weekly clusters are bootstrapped against null 0.50.

## Minimum sample safeguards
A hypothesis is `ELIGIBLE` only if:
- pairwise role test: each side has >=20 valid observations;
- one-sample H5: >=50 valid observations.

If a role is too rare (expected especially for REVERSAL), the hypothesis is `UNDERPOWERED`, not failed. Underpowered hypotheses do not count as semantic passes or failures.

## Year transfer
For 2023, 2024, 2025, 2026 YTD, report the sign of H2–H6. Per-year eligibility is frozen **before outcomes** as:
- pairwise hypothesis: each side must have >=5 valid observations in that year;
- one-sample H5: >=10 valid observations in that year.

H1 is expected to be too sparse and is reported only.

A transferable redesigned role must have the preregistered positive sign in >=3/4 calendar years when all four years are eligible. If fewer than four years are eligible, transfer is reported as underpowered and cannot pass.

## Verdict
Count only eligible H1–H6.

- `TEMPORAL_ROLE_REDESIGN_SUPPORTED_DISCOVERY_ONLY` if:
  - >=4 primary hypotheses are eligible,
  - >=75% of eligible hypotheses pass bootstrap CI gate,
  - and at least **2 of H2–H6** pass 3/4-year transfer.
- `PARTIAL_TEMPORAL_ROLE_SUPPORT` if >=2 eligible primary hypotheses pass but full verdict fails.
- `TEMPORAL_ROLE_REDESIGN_NOT_SUPPORTED` if <=1 eligible primary hypothesis passes.
- If fewer than 3 primary hypotheses are eligible: `TEMPORAL_ROLE_REDESIGN_UNDERPOWERED`.

## Anti-overfit rules
- No changes to router weights, state names, hysteresis, score thresholds, or bias logic.
- No post-result age-boundary search.
- No post-result horizon selection.
- No score-gap filtering.
- `REVERSAL_AFTERGLOW` and `RANGE_STALE` remain in diagnostics; they cannot be silently dropped.
- Secondary horizons cannot override a failed primary horizon.
- Any useful new interaction discovered here requires a later preregistered lab or fresh data.

## Production restriction
Even a full pass only supports a better **human-readable Context display layer on reused history**. It does not authorize automated entries, position sizing, or prop-challenge risk changes.

> Pre-outcome clarification note: the per-year minimum sample thresholds above were specified after the runner skeleton was written but **before any LAB009 outcome computation or workflow run**. No hypothesis direction, age boundary, primary horizon, or verdict threshold changed.