# XAU_RAW_POST_BREAK_TO_DIGESTION_PATH_RESIDUAL_CONTINUATION_LAB_015 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-24  
**Parents:** LAB009 Bias Engine v001 → LAB011 → LAB012 → LAB013 → LAB014

## Motivation

LAB014 used the correct economic target — whether TP1.5R remains available from the executable digestion next-open — but the compact hand-engineered storyline representation was approximately non-predictive OOS. Post-hoc nonlinear learners on the same compressed representation were also near chance (~0.52 AUC).

LAB015 tests the remaining hypothesis directly:

> A human trader may read the **raw chronological path** from break to digestion close — tempo, repeated attempts, expansion/recovery shape, distance evolution and drawdown from the running directional extreme — in a way that compact state labels and summary features erase.

LAB015 changes **representation only**. It does not change break detection, bias, digestion, entry, stop, target, costs, hold horizon, target definition, train/Confirmation split, or holdout embargo.

## Canonical lineage / embargo

- canonical market input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- canonical SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- LAB008 break census SHA-256: `c9cba1459a60ef9c3bb308e751ebae95840f48a24f94754808862a180832ccdb`
- frozen LAB012 runner SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`
- Discovery: `break_time < 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>=2025-07-01`

The frozen LAB012 runner is rerun only to reconstruct the canonical causal digestion-event table and frozen baseline execution outcomes. LAB015 must not modify LAB012 event construction or execution logic.

No market bar at or after `2025-07-01` may be read.

## Eligible universe

Same frozen digestion baseline universe used by LAB014:
- LAB009 `strong_accept == true` (`p_accept >= 0.75`);
- `digestion_found == true`;
- valid `baseline_entry_i >= 0` and next-open entry;
- `causality_violation == false`;
- `baseline_outcome_1p5` / `baseline_net_R_1p5` available;
- `break_time < 2025-07-01`.

Primary decision = completed digestion close.  
Executable entry = frozen next contiguous M1 open after digestion close.

## Target / economics — frozen from LAB014

Primary target:

`RESIDUAL_TP15 = 1` iff frozen LAB012 `baseline_outcome_1p5 == "TP"`; else `0`.

Thus SL, same-bar loss and time exits are all `0`.

Frozen geometry:
- `1R = 0.50 * ATR_touch`
- TP = `1.5R`
- SL = `1R`
- max hold = 60 minutes
- BUY Ask execution / SELL Bid execution
- spread embedded in Bid/Ask
- commission proxy `$0.05` XAU price-equivalent RT
- secondary 2R and +$0.10 stress unchanged.

No trade is resimulated with a different entry, stop, target or holding period.

## Raw chronological path

For each eligible event, observe each completed M1 minute from **break+1 through the digestion-close minute**, maximum 35 post-break minutes under the frozen LAB012 digestion scan.

Let:

`x_t = dir * (Close_t - DynamicLevel_t) / ATR_touch`

where positive means the price remains on the accepted breakout side.

At each chronological minute `t = 1..35`, preserve its position explicitly. For minutes after the actual digestion decision, set all path values to `0` and `observed_mask_t = 0`; observed minutes have `observed_mask_t = 1`. No interpolation, sorting, averaging or time warping is allowed.

### Raw price channels — primary

For each observed minute:
- `x_t`: signed close distance to contemporaneous broken level / ATR_touch;
- `ret_t`: directional close-to-close return / ATR_touch, with t=1 measured from break close;
- `dd_t`: running directional high-water mark of `x` minus current `x_t`;
- `body_t`: directional `(Close-Open) / ATR_touch`;
- `observed_mask_t`.

These are kept as **35 ordered slots per channel**. The model receives the path itself, not counts or summary statistics.

### Raw activity channels — secondary

Adds, position by position:
- `range_t = (High-Low)/ATR_touch`;
- `volr_t = TickVolume_t / median(TickVolume[t-60:t-1])` using only prior completed minutes; clipped to `[0,5]`.

Activity cannot rescue a failed primary raw-price verdict.

## Comparison representations

To avoid model-class confounding, all representations use the same frozen learner.

### A. COMPACT_BASELINE
Frozen compact causal story equivalent to LAB014:
- static current-location context: `p_accept`, elapsed minutes, digestion block index/state, level;
- LAB009 ordered bias tokens s1/s2/s3;
- frozen internal-state positions known by digestion close;
- frozen digestion 5-bar `x`, drawdown and directional-return positions.

No future variables.

### B. RAW_PRICE_PATH — primary
Minimal static context (`p_accept`, level, elapsed minutes, digestion state) plus the full ordered 35-slot raw price channels above.

### C. RAW_PRICE_PLUS_COMPACT — primary integration representation
Union of RAW_PRICE_PATH and COMPACT_BASELINE. This is the **primary LAB015 model**, because the central question is whether the raw path adds information beyond the existing compact story.

### D. RAW_PRICE_ACTIVITY_PLUS_COMPACT — secondary
Adds the raw activity channels. Diagnostic only; cannot rescue a failed primary verdict.

## Learner — frozen and identical across representations

Use `sklearn.ensemble.HistGradientBoostingClassifier` with:
- `learning_rate = 0.05`
- `max_iter = 200`
- `max_leaf_nodes = 15`
- `min_samples_leaf = 30`
- `l2_regularization = 1.0`
- `max_bins = 64`
- `early_stopping = False`
- `random_state = 20260824`

Categorical variables are frozen one-hot indicators built from Discovery vocabulary; unknown Confirmation categories map to all-zero for that categorical family.

No hyperparameter search, feature selection, calibration fitting or Confirmation tuning.

## Train / evaluation protocol

### Primary
Train on all Discovery eligible events (`break_time < 2024-01-01`) and evaluate untouched Confirmation (`2024-01-01 <= break_time < 2025-07-01`).

### Discovery temporal-transfer diagnostic
Train on pre-2023 Discovery only and evaluate 2023. No 2023 fitting.

## Routing rule

For parity with LAB014, no threshold search:

`RAW_RESIDUAL_ARMED = p_raw_residual >= 0.55`

where `p_raw_residual` is the probability from `RAW_PRICE_PLUS_COMPACT`.

Entry remains the frozen digestion next-M1-open. Rejected events do not trade.

Diagnostics only: `0.45, 0.50, 0.60, 0.65`, quintiles/deciles and top 20% score. None may replace `0.55` as the LAB015 primary rule.

## Serial portfolio

Reuse the frozen LAB012 serial policy:
- deterministic dedupe at the lifecycle level by break time/direction, highest `p_accept`, tie `MID > HIGH > LOW`;
- simultaneous opposite-direction conflict at the same break time skipped;
- one open position maximum;
- when flat, inspect next lifecycle;
- if raw router rejects at digestion decision, skip and move on;
- if armed, enter at frozen next-open;
- later overlapping lifecycles ignored until exit;
- no hedging, pyramiding, averaging or martingale.

Baseline = identical serial DIGESTION universe without LAB015 gate.

## Evaluation

Report for Discovery-2023 and Confirmation:
- N / TP1.5 base rate;
- AUC, Brier, log loss for COMPACT_BASELINE, RAW_PRICE_PATH, RAW_PRICE_PLUS_COMPACT, RAW_PRICE_ACTIVITY_PLUS_COMPACT;
- RAW_PRICE_PLUS_COMPACT minus COMPACT_BASELINE AUC;
- weekly cluster bootstrap 95% CI of AUC increment;
- probability calibration/quintiles;
- primary `p>=0.55` precision, recall, coverage;
- routed-minus-rejected TP1.5 rate and weekly bootstrap CI;
- independent and serial economics: N, trades/week, EV, PF, TP rate, total R, 2R, BUY/SELL, MID/HIGH/LOW, DD, worst day, consecutive losses, +$0.10 stress;
- routed-minus-baseline weekly mean-R bootstrap;
- elapsed-time / digestion-state diagnostics;
- secondary activity increment;
- raw-path permutation importance grouped by chronological minute/channel as diagnostic only.

Calendar-week bootstrap:
- 4000 resamples
- seed `20260824`.

## Frozen gates

Primary = Confirmation / RAW_PRICE_PLUS_COMPACT / `p>=0.55` / frozen digestion next-open / 1.5R / serial.

- `G0_DATA_CAUSALITY`: canonical/break/runner hashes valid; holdout sealed; all raw slots are <= digestion close; no parent causal violations; entry strictly after decision.
- `G1_POWER`: Confirmation eligible >=1500; routed serial >=250; routed frequency >=2/week.
- `G2_RAW_RESIDUAL_AUC`: primary OOS AUC >=0.60.
- `G3_RAW_ADDS_OVER_COMPACT`: primary AUC - COMPACT_BASELINE AUC >= +0.03 and lower weekly-bootstrap CI >0.
- `G4_SELECTION_QUALITY`: routed TP1.5 rate >=0.48 and routed-minus-rejected TP rate >= +12 pp with lower bootstrap CI >0.
- `G5_CONFIRMATION_EV`: routed serial EV >0 and PF>1.0.
- `G6_WEEK_CLUSTER_CI`: lower 95% weekly CI of routed serial mean R >0.
- `G7_DISCOVERY_TRANSFER`: Discovery-2023 routed independent EV >0 and Confirmation routed independent EV >0.
- `G8_2R_SURVIVAL`: Confirmation routed serial 2R EV >=0.
- `G9_DIRECTION_BREADTH`: Confirmation routed BUY EV >0 and SELL EV >0.
- `G10_PROP_DD_PROXY`: max DD <=20R and worst day >-16R.
- `G11_COST_STRESS`: Confirmation routed serial +$0.10 stress EV >0.
- `G12_ROUTER_LIFT`: routed serial EV > baseline serial EV and lower routed-minus-baseline weekly CI >0.

Secondary activity increment is reported but is not a required gate.

## Verdicts

- `RAW_PATH_RESIDUAL_EXECUTABLE_EDGE`: all G0..G12 pass.
- `RAW_PATH_RESIDUAL_EDGE_NOT_PROP_READY`: G2..G7 and G12 pass but one or more power/2R/breadth/DD/stress gates fail.
- `RAW_PATH_PREDICTS_RESIDUAL_BUT_EXECUTION_FAILS`: G2/G3/G4 pass but G5 fails.
- `RAW_PATH_SELECTS_EDGE_WITHOUT_FULL_ROBUSTNESS`: G2/G3/G4/G5 pass but CI/transfer/lift fails.
- `RAW_PATH_ADDS_INFORMATION_BUT_NO_ECONOMIC_SELECTION`: G2/G3 pass but G4/G5 fail.
- `NO_RAW_PATH_RESIDUAL_EDGE`: G2 or G3 fails and no positive transferable routed economics.
- `INVALID_DATA_CAUSALITY`: G0 fails.

No holdout opening, EA authorization or live allocation is authorized by LAB015.

## Anti-overfit

Do not tune after outcomes:
- break/bias/digestion/entry definitions;
- 35-minute raw horizon or raw channels;
- mask/padding method;
- activity normalization;
- learner/hyperparameters;
- target/SL/TP/hold/costs;
- `p>=0.55` router;
- subsets by direction, level, state, year, session, volatility or news;
- gates.
