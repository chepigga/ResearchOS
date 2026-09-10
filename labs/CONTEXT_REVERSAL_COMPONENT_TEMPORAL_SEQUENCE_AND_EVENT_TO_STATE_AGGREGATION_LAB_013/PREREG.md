# CONTEXT_REVERSAL_COMPONENT_TEMPORAL_SEQUENCE_AND_EVENT_TO_STATE_AGGREGATION_LAB_013 — PREREG

## Objective
Determine whether frozen LAB010/LAB012 Reversal components behave as a causal temporal event sequence rather than a same-bar persistent state. This lab is diagnostic only: no trading edge, no score-weight changes, no frequency target, no threshold tuning after outcomes.

## Frozen parent
Use LAB010 Context engine exactly as-is. Preserve all four score formulas, 3-bar smoothing, inertia, min-hold, switch-gap, volatility-dependent hysteresis and closed-HTF causality. Reversal components are frozen as:
- swing_sweep 30
- rsi_turn 20
- rsi_rhythm_turn 15
- ema20_cross 15
- adx_decay 10
- rejection_wick 10

## Data
BTCUSDT Binance USD-M futures H1, 2020-01 through 2026-07, resampled causally to H4 exactly as parent.

## Primary sequence windows
Evaluate component activity known at bar close over trailing windows W={1,2,3} H4 bars, where W=1 is same-bar baseline and W=2/3 allow recent causal event memory only. A component is sequence-active at bar t iff it fired on any closed bar in [t-W+1,t]. No future bars.

## Sequence diagnostics
For each W and each bar:
1. active component count;
2. weighted sequence coverage score = sum of frozen component weights whose event occurred in trailing W bars, clipped 0..100;
3. raw same-bar Reversal score from parent;
4. whether sequence score is rank1/rank2 against frozen contemporaneous non-Reversal scores (diagnostic only; no state replacement in primary audit).

## Transition-conditioned tests
Using actual frozen LAB010 Current Context transitions:
- for destination REVERSAL and each other destination, measure at lags 1/2/3 bars before transition: sequence score, active-component count, rank1 share, rank1-or-2 share;
- compare Reversal transition bars with matched non-transition bars by year and volatility state descriptively;
- compute how often a Reversal candidate episode (sequence rank<=2) converts to a frozen Reversal transition within next 1/2/3 bars. This conversion metric is diagnostic and does not introduce lookahead into the sequence construction.

## Event ordering
Within Reversal-transition episodes, record the first occurrence offsets (0,-1,-2 bars relative to evaluation bar) for each component and common pair/triple temporal orderings. No ordering rule will be selected or promoted in this lab.

## Causality gate
Perturb all H1 OHLCV strictly after a cutoff. Recompute H4/Context/sequence diagnostics. All sequence columns for H4 bars with available_time <= cutoff must be identical. Any change => CAUSALITY_FAIL.

## Parent parity gates
- LAB010 regime counts must remain exactly PULLBACK 7641 / EXPANSION 4568 / RANGE 2184 / REVERSAL 29.
- Frozen Reversal score reconstruction must match parent exactly.

## Diagnostic classification fixed before outcomes
Let REV W3 median active-component count in the bar immediately preceding actual Reversal transitions be A3_rev; same-bar baseline A1_rev. Let top2_W3 and top2_W1 be corresponding rank<=2 shares. Let nontransition_W3 be median active count on eligible non-transition bars.

Classify:
- `TEMPORAL_SEQUENCE_SUPPORTED` if A3_rev >= A1_rev+1 AND top2_W3 >= top2_W1+0.15 AND A3_rev >= nontransition_W3+1.
- `WEAK_TEMPORAL_SEQUENCE_SIGNAL` if any two of those three conditions pass.
- `SAME_BAR_MODEL_NOT_REJECTED` otherwise.
- Any parity/causality failure overrides classification.

## Prohibitions
No modifying component weights; no changing Context state machine; no optimizing window beyond preregistered W=1/2/3; no using PnL; no post-outcome threshold choice; no promotion to production from this reused-history diagnostic.
