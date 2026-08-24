# XAU_BIAS_X_ROOM_TO_RUN_AND_DESTINATION_CONTEXT_LAB_017 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-24  
**Parents:** LAB009 Bias Engine v001 → LAB012 digestion next-open execution → LAB014 residual target → LAB015/LAB016 representation failures

## Motivation

LAB009 established a transferable post-break acceptance Bias Engine. LAB012 showed a strong latent split between healthy and toxic digestion setups, but delayed reacceleration confirmation destroyed entry quality. LAB014–016 then tested compressed, raw-clock and hand phase-aligned post-break paths against the economically correct residual target. None produced transferable residual TP1.5 ranking.

The remaining human-trader hypothesis is spatial rather than purely sequential:

> Knowing the directional bias is not enough. A trader also asks whether enough **room to run** remains from the current location before the next already-known structural destination/obstacle, and how much of the move has already been spent.

LAB017 changes only the causal context representation. Break detection, LAB009 bias, digestion decision, next-open entry, risk geometry, target, costs, partitions and sealed holdout remain frozen.

## Canonical lineage / embargo

- canonical market input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- canonical SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- LAB008 break census SHA-256: `c9cba1459a60ef9c3bb308e751ebae95840f48a24f94754808862a180832ccdb`
- frozen LAB012 runner SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`
- reconstructed LAB012 event table is produced by that exact runner without changes.
- Discovery: `break_time < 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>=2025-07-01`

No market bar at or after `2025-07-01` may be read.

## Eligible universe / execution — frozen

Same causal digestion universe as LAB014–016:
- LAB009 `strong_accept == true` (`p_accept >= 0.75`);
- `digestion_found == true`;
- valid frozen `baseline_entry_i >= 0`;
- no parent causality violation;
- `baseline_outcome_1p5` available;
- break before sealed holdout.

Decision clock = completed digestion close.  
Executable entry = frozen next contiguous M1 open after digestion close.

Primary target:

`RESIDUAL_TP15 = 1` iff frozen LAB012 `baseline_outcome_1p5 == "TP"`; else `0`.

Frozen geometry:
- `1R = 0.50 * ATR_touch`
- TP = `1.5R` = `0.75 ATR_touch` from entry before execution costs
- SL = `1R`
- max hold = 60 minutes
- spread / Bid-Ask path and `$0.05` XAU RT commission proxy frozen from LAB012
- secondary 2R and +$0.10 stress frozen.

No trade is resimulated with a different entry, stop, target or horizon.

## Causal spatial context

All LAB017 features are computed from information available no later than the digestion-close decision minute. Next-open price is **not** used as a feature.

### 1. Bias / current location

- `p_accept` — frozen LAB009 Bias Engine probability;
- `level` — MID/HIGH/LOW broken line;
- `digestion_state`;
- `elapsed_min` from break to digestion close;
- `x_decision = dir*(Close_decision - DynamicBrokenLevel_decision)/ATR_touch`;
- `peak_x_since_break` — maximum directional signed distance from break+1 through decision;
- `spent_from_break_atr = dir*(Close_decision - Close_break)/ATR_touch`;
- `peak_spent_atr = dir*(max directional price since break - Close_break)/ATR_touch`;
- `drawdown_from_peak_atr = peak_x_since_break - x_decision`;
- `path_efficiency = abs(net directional displacement) / sum(abs(M1 close-to-close movement))` over break+1..decision;
- `elapsed_per_atr = elapsed_min / max(abs(peak_spent_atr),0.25)`.

### 2. Known destination levels ahead of current decision close

For BUY, a candidate is ahead iff level price > decision close. For SELL, ahead iff level price < decision close. Distance is always directional and normalized by `ATR_touch`.

Frozen candidate families:

#### A. Same-session VWAP destinations
Using the exact LAB009/LAB012 anchored VWAP family. All currently known same-session MID/HIGH/LOW prices may enter the candidate set except the broken line itself.

#### B. Previous completed anchored-session high/low (`PDH/PDL` analogue)
Session anchor remains 01:00 platform time. The immediately prior completed anchored session supplies its high and low.

#### C. Current-session high/low known so far
High/low from current anchored-session start through the digestion-close minute only.

#### D. Confirmed M15 swings
A causal 5-bar fractal pivot (`2 left + pivot + 2 right`) on completed M15 bars. A pivot becomes available only after the two right bars are completed. Candidate pivots must be confirmed before the digestion decision and within the previous 5 calendar days.

#### E. Confirmed H1 swings
Same causal 5-bar fractal definition on completed H1 bars, confirmed before decision and within the previous 20 calendar days.

For M15/H1 swings, select the nearest known pivot price ahead in the break direction; if none exists, distance is missing and an explicit `*_exists=0` flag is supplied.

### 3. Room-to-run features

For each family above:
- `room_<family>_atr` = directional distance from decision close to nearest candidate ahead / ATR_touch;
- `room_<family>_R = 2 * room_<family>_atr` because frozen `1R=0.50 ATR`;
- `exists_<family>`.

Cross-family spatial features:
- `nearest_room_atr` = minimum positive known destination distance;
- `nearest_room_R`;
- `nearest_type` categorical;
- `clearance_vs_tp15_atr = nearest_room_atr - 0.75`; if no known candidate, use capped open-space value plus flag;
- `known_levels_inside_tp15` = count of candidate levels at directional distance `<=0.75 ATR`;
- `known_levels_inside_1p5atr` = count within `<=1.50 ATR`;
- `open_space_0p75 = 1` iff no known candidate within `0.75 ATR`;
- `open_space_1p5 = 1` iff no known candidate within `1.50 ATR`.

No assumption is made that a known level is necessarily resistance/support. Individual family distances are retained so the learner can distinguish obstacle vs magnet behavior.

### 4. Range / destination position

Using only completed information at decision:
- previous-session range position `(Close-PDL)/(PDH-PDL)`;
- current-session range position `(Close-session_low_so_far)/(session_high_so_far-session_low_so_far)`;
- completed M15 rolling 4h range position using previous 16 completed M15 bars;
- completed H1 rolling 24h range position using previous 24 completed H1 bars;
- directional distance beyond/inside those rolling extremes, normalized by ATR_touch.

### 5. M15/H1 structural context

Using completed bars only:
- M15 EMA20 directional distance and 4-bar EMA slope / ATR_touch;
- H1 EMA20 directional distance and 4-bar EMA slope / ATR_touch;
- M15 confirmed-swing structure score in break direction: `+1` if last two confirmed highs and lows form directional HH/HL for BUY (LL/LH for SELL), `-1` for opposite, else `0`;
- H1 analogous score.

## Comparison representations

All use the same frozen learner.

### A. BIAS_LOCATION_BASELINE
Only:
- `p_accept`, `level`, `digestion_state`, `elapsed_min`;
- `x_decision`, `peak_x_since_break`, `spent_from_break_atr`, `peak_spent_atr`, `drawdown_from_peak_atr`, `path_efficiency`, `elapsed_per_atr`.

### B. ROOM_DESTINATION_ONLY
All frozen spatial/destination/range/structure features, excluding `p_accept` and excluding raw chronological path.

### C. BIAS_X_ROOM — **primary**
Union of A and B.

### D. BIAS_X_ROOM_PLUS_FIXED_RAW — secondary
Adds the LAB015 frozen 35-slot raw price path (`x`, directional return, drawdown, body, mask) to C. Diagnostic only; cannot rescue a failed primary BIAS_X_ROOM verdict.

## Transparent room diagnostic

`CLEAR_TP15_ROOM = open_space_0p75 == 1`

Report TP1.5 rate and EV for CLEAR vs BLOCKED. This is descriptive and cannot replace the primary probability router.

## Learner — frozen

Same fixed nonlinear learner for all representations:

`sklearn.ensemble.HistGradientBoostingClassifier`
- learning_rate `0.05`
- max_iter `200`
- max_leaf_nodes `15`
- min_samples_leaf `30`
- l2_regularization `1.0`
- max_bins `64`
- early_stopping `False`
- random_state `20260824`.

Categorical variables are Discovery-fitted one-hot variables with unknown Confirmation categories ignored.

No hyperparameter search, feature selection, calibration fitting or Confirmation tuning.

## Train / evaluation

Primary: fit on all Discovery eligible events and evaluate untouched Confirmation.  
Temporal transfer: fit on Discovery before 2023 and evaluate 2023 only.

## Routing rule

No threshold search:

`ROOM_ARMED = p_bias_x_room >= 0.55`.

Entry remains frozen digestion next-open. Diagnostic thresholds `0.45,0.50,0.60,0.65` cannot replace `0.55`.

## Serial portfolio

Reuse frozen LAB012 serial policy. Baseline = identical serial all-digestion universe without LAB017 gate.

## Evaluation

Report predictive metrics, weekly AUC increment bootstrap, calibration, routed precision/coverage, CLEAR vs BLOCKED, serial/independent 1.5R and 2R economics, cost stress, direction/level breadth, DD, routed-minus-baseline bootstrap, grouped permutation importance and nearest-destination diagnostics.

Bootstrap: 4000 calendar-week resamples, seed `20260824`.

## Frozen gates

Primary = Confirmation / BIAS_X_ROOM / `p>=0.55` / frozen digestion next-open / 1.5R / serial.

- `G0_DATA_CAUSALITY`: canonical hashes valid; holdout sealed; all features available by digestion close; entry strictly after decision; no parent causal violations.
- `G1_POWER`: Confirmation eligible >=1500; routed serial >=250; routed frequency >=2/week.
- `G2_ROOM_RESIDUAL_AUC`: primary OOS AUC >=0.60.
- `G3_ROOM_ADDS_OVER_LOCATION`: primary AUC - BIAS_LOCATION AUC >=+0.03 and lower weekly-bootstrap CI >0.
- `G4_SELECTION_QUALITY`: routed TP1.5 rate >=0.48 and routed-minus-rejected TP rate >=+12 pp with lower bootstrap CI >0.
- `G5_CONFIRMATION_EV`: routed serial EV >0 and PF>1.
- `G6_WEEK_CLUSTER_CI`: lower 95% weekly CI of routed serial mean R >0.
- `G7_DISCOVERY_TRANSFER`: 2023 routed independent EV >0 and Confirmation routed independent EV >0.
- `G8_2R_SURVIVAL`: Confirmation routed serial 2R EV >=0.
- `G9_DIRECTION_BREADTH`: Confirmation routed BUY EV >0 and SELL EV >0.
- `G10_PROP_DD_PROXY`: max DD <=20R and worst day >-16R.
- `G11_COST_STRESS`: Confirmation routed serial +$0.10 stress EV >0.
- `G12_ROUTER_LIFT`: routed serial EV > baseline serial EV and lower routed-minus-baseline weekly CI >0.

## Verdicts

- `BIAS_X_ROOM_RESIDUAL_EXECUTABLE_EDGE`: all G0..G12 pass.
- `BIAS_X_ROOM_EDGE_NOT_PROP_READY`: G2..G7 and G12 pass but one or more power/2R/breadth/DD/stress gates fail.
- `ROOM_CONTEXT_PREDICTS_RESIDUAL_BUT_EXECUTION_FAILS`: G2/G3/G4 pass but G5 fails.
- `ROOM_CONTEXT_SELECTS_EDGE_WITHOUT_FULL_ROBUSTNESS`: G2/G3/G4/G5 pass but CI/transfer/lift fails.
- `ROOM_CONTEXT_ADDS_INFORMATION_BUT_NO_ECONOMIC_SELECTION`: G2/G3 pass but G4/G5 fail.
- `NO_BIAS_X_ROOM_RESIDUAL_EDGE`: G2 or G3 fails and no positive transferable routed economics.
- `INVALID_DATA_CAUSALITY`: G0 fails.

No holdout opening, EA authorization or live allocation is authorized by LAB017.

## Anti-overfit

Do not tune after outcomes: target, entry, risk geometry, universe, destination families, swing definitions, lookbacks, EMA lengths, session anchor, spatial thresholds, learner, routing threshold, direction/level/year/state/session subsets or gates.
