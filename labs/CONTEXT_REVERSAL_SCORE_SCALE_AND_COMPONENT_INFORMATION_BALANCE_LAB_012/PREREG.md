# CONTEXT_REVERSAL_SCORE_SCALE_AND_COMPONENT_INFORMATION_BALANCE_LAB_012

## Purpose
Audit whether LAB010 Reversal rarity is caused by structural score-scale / attainable-budget imbalance versus low component co-activation / information density. This is an indicator architecture diagnostic only; no PnL/edge objective.

## Frozen parent
`CONTEXT_INDICATOR_PUBLIC_SPEC_GAP_CLOSURE_AND_NEXT_CONTEXT_LAB_010` exactly as implemented on branch `lab/context-reversal-score-scale-component-balance-012`.

## No-tuning rule
Do not change any LAB010 score weights, thresholds, smoothing, hysteresis, state-machine constants, feature definitions, or frequency targets in this LAB. Reversal frequency is descriptive only.

## Dataset
Frozen LAB010 BTCUSDT H1 monthly public Binance archive, 2020-01 through 2026-07, aggregated to H4 using the same causal clock.

## Diagnostics
For each regime (Expansion/Pullback/Reversal/Range):
1. theoretical maximum score from frozen component weights;
2. empirical raw score distribution: nonzero share, mean, median, p75, p90, p95, p99, max;
3. smoothed score distribution using frozen 3-bar mean;
4. empirical attainment ratio = empirical p95 / theoretical max and max / theoretical max;
5. component activation rates and mean contribution in score points;
6. contribution concentration: largest component share of total contributed points;
7. co-activation count distribution: number of simultaneously active components per bar;
8. raw winner and smoothed winner shares;
9. conditional score behavior 1/2/3 bars before actual state transitions.

## Primary diagnosis
Define:
- `SCALE_BUDGET_IMBALANCE` if Reversal theoretical max is lower than at least two other regimes OR Reversal p95/theoretical-max is materially lower (>10 percentage points) than the median of other regimes while component-count coactivation is not materially lower.
- `COACTIVATION_INFORMATION_SPARSE` if theoretical max is comparable but Reversal median/p90 active-component count is at least 1 component below the median of other regimes and Reversal p95 attainment is materially lower.
- `BOTH_SCALE_AND_COACTIVATION` if both conditions hold.
- `NO_CLEAR_STRUCTURAL_IMBALANCE` otherwise.

The diagnostic is descriptive and does not authorize changing weights.

## Integrity gates
- exact LAB010 output parity: regime counts and raw score columns must reproduce;
- no score/state changes relative to LAB010;
- all four regime component decompositions must exactly sum to the frozen raw scores (tolerance 1e-10);
- no future data / no outcome labels / no trading performance used.
