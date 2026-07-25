# AK47_BREAKOUT_RESEARCH_001 — ML selection execution lock

**Date locked:** 2026-07-25  
**Status:** PRE-DATA LOCKED  
**Authority:** `SPEC-AK47-BREAKOUT-RESEARCH-001 — ADDENDUM: ML-селекція`  
**Eligible M1/tick data inspected before lock:** NONE

## 1. Sequencing

The ML stage does not run in parallel with the base geometry study.

1. Complete the 1,512-candidate base grid, walk-forward and family-wise price permutation.
2. If the base verdict is `NO-GO`, stop. ML is not allowed to rescue the entry class.
3. If the base verdict is `GO` or `REGIME`, freeze the selected base geometry from the base stage.
4. Generate causal directional candidate features and economic labels using that geometry.
5. Run monthly walk-forward ML selection.
6. Compare ML against:
   - the unfiltered frozen base geometry;
   - the preregistered manual-regime comparator.
7. ONNX implementation is considered only after `ML-GO`.

The original execution lock's manual regime filters remain only as a benchmark. This ML lock supersedes them as the primary post-geometry research stage.

## 2. Candidate unit and labels

At each eligible strategy-timeframe setup bar, generate two directional candidate records:

- `BUY_STOP = previous_high + padding`;
- `SELL_STOP = previous_low - padding`.

Each direction receives a separate causal feature vector known at setup time.

Economic labels are produced using the frozen base geometry and the eligible M1/tick execution model:

- a directional candidate is label-eligible only if its own stop entry fills before the next setup refresh/session cancellation;
- after fill, simulate its SL/TP/BE independently of the opposite candidate;
- `net_R` includes actual spread and `$5` round-turn commission;
- classification label: `y = 1(net_R > 0)`;
- continuous economic target retained for evaluation: `net_R`;
- `UNFILLED` candidates are retained in the candidate audit but excluded from supervised fitting.

During OOS execution:

- score BUY and SELL independently;
- if neither passes, skip the setup;
- if one passes, place only that stop order;
- if both pass, place the normal OCO pair;
- if both selected orders touch in one M1 bar, apply the parent conservative dual-touch rule.

## 3. Feature schema

All features use only information available before the pending order is placed.

### Time/session
- `hour_sin`, `hour_cos`;
- `dow_sin`, `dow_cos`;
- categorical session bucket: `00-07`, `08-09`, `10-14`, `15-18`, `19-23`.

### Volatility
- signal-TF `ATR(14)`;
- signal-TF `ATR(14) / ATR(100)`;
- previous setup candle range divided by `ATR(14)`.

### Geometry
- candidate direction (`BUY=+1`, `SELL=-1`);
- distance from candidate entry to prior 20-bar swing high, normalized by `ATR(14)`;
- distance from candidate entry to prior 20-bar swing low, normalized by `ATR(14)`;
- padding divided by `ATR(14)`.

### Spread regime
- spread points at setup;
- spread divided by trailing 20-trading-day median spread for the same minute-of-day;
- trailing 20-day spread percentile rank for the same minute-of-day.

### Higher timeframe context
Using only last fully closed bars:
- `(H4 close - H4 EMA50) / H4 ATR14`;
- `(D1 close - D1 EMA50) / D1 ATR14`;
- H4 ADX(14);
- D1 ADX(14).

### Prior-result state
A shadow baseline stream is maintained for every frozen base-geometry candidate, including candidates ML would skip:
- previous shadow baseline `net_R`;
- shadow baseline consecutive-loss streak capped at `5`;
- trailing 10 shadow-trade mean `net_R`.

Rows with incomplete warm-up are excluded. No future-value imputation is allowed.

## 4. Model

Exactly one model is allowed:

`sklearn.ensemble.RandomForestClassifier`

Frozen parameters:

```text
n_estimators = 500
max_depth = 6
min_samples_leaf = 50
max_features = "sqrt"
bootstrap = true
class_weight = "balanced_subsample"
criterion = "gini"
random_state = 47015
n_jobs = -1
```

No hyperparameter search, feature elimination, calibration model or alternative algorithm is allowed. AUC, accuracy and F1 are diagnostics only.

## 5. Monthly walk-forward

Primary test months: `2023-06` through `2026-05` inclusive — 36 monthly OOS windows.

For each test month:

1. train on immediately preceding 12 calendar months;
2. fit the frozen RandomForest;
3. predict `p_win` for all directional candidates in the next month;
4. calculate the threshold as the `q0.96` quantile of model scores on the final 90 calendar days of the training window;
5. execute only OOS candidates with `p_win >= threshold`.

`2026-06-01..2026-07-23` remains the sealed tail audit and cannot alter the ML verdict.

## 6. Baselines

### Baseline A — simple geometry
The frozen unfiltered base geometry selected by the main SPEC.

### Baseline B — manual regime comparator
On each 12-month train window choose exactly one of:

- `NONE`;
- H1 ADX(14) ≥ `20`, `25`, or `30`;
- M15 ATR(14)/ATR(100) ≥ `0.8`, `1.0`, or `1.2`;
- place only direction agreeing with H4 close vs EMA50;
- place only direction agreeing with D1 close vs EMA50;
- place only direction agreeing with both H4 and D1 EMA50 bias.

Selection uses the same train Calmar-like score and tie-breaks as the base SPEC. Only the selected comparator is evaluated next month.

## 7. Economic metrics and gates

Primary metric: OOS mean `net_R` of realized selected trades.

`ML-GO` requires all of:

1. aggregate realized OOS N ≥ `90`;
2. aggregate ML EV exceeds Baseline A by at least `+0.10R`;
3. aggregate ML EV exceeds Baseline B by at least `+0.10R`;
4. no more than one OOS month with realized N > 0 has ML EV ≤ 0;
5. MaxDD ≤ `10%`;
6. label-permutation control passes.

The `+0.10R` requirement is aggregate paired OOS uplift. The monthly clause is a separate stability gate.

`ML-NEUTRAL`:
- positive uplift but below `+0.10R` against either baseline; or
- uplift passes but monthly stability or permutation fails without underperforming both baselines.

`ML-NO-GO`:
- aggregate ML EV is below either canonical baseline; or
- aggregate ML EV ≤ 0.

## 8. Label-permutation control

- `250` complete ML permutations;
- shuffle `y` labels inside each training calendar month, preserving monthly class balance and all features;
- refit the frozen RandomForest for every rolling test month;
- use the same `q0.96 / trailing 90-day` selection rule;
- evaluate selected candidates against unchanged true OOS `net_R`;
- aggregate all 36 OOS months per permutation.

Permutation statistic:

`max(ML_EV - Baseline_A_EV, ML_EV - Baseline_B_EV)`

Observed statistic must exceed the 95th percentile of the 250 permuted statistics.

No best-of-model or best-of-quantile search is permitted.

## 9. Outputs

1. Candidate-level feature/label table with provenance.
2. Monthly predictions and selected candidates.
3. Realized ML trades.
4. Monthly/yearly/BUY/SELL metrics.
5. Baseline A and B comparisons.
6. 250-permutation distribution and histogram.
7. Diagnostic AUC/accuracy and feature importances.
8. Explicit `ML-GO`, `ML-NEUTRAL`, or `ML-NO-GO`.
9. ONNX export only in a later task after `ML-GO`.
