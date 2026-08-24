# XAU_LIVE_STATE_OUTCOME_PROBABILITY_X_REMAINING_PAYOFF_MANAGEMENT_LAB_021 — Spec v001

Date: 2026-08-24
Status: PREREGISTRATION / PRE-OUTCOME / HOLDOUT SEALED

## Question
Can a live position-management engine improve the frozen early-digestion entry by decomposing HOLD value into terminal-outcome probabilities and remaining payoff, instead of directly regressing one noisy HOLD-advantage value?

## Frozen lineage
- Canonical XAU M1 cache SHA-256: `ec05163508f6f69c9688e5e50e1f418f6ca64aba42f17cf8d6504775df147ef8`
- Frozen setup cache SHA-256: `83526be03cb66ff596c3949138e7e8935cd12b9f8783a41adaf5f2c04d4ccfda`
- Frozen LAB012 parent runner SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`
- LAB020 runner reference SHA-256: `8e0cd8dc09d5a9d48fab7b951091e836e8d4f276943cd1663192314f8f0ae78d`
- Early entry universe, actual entry price, 1R risk, TP/SL, commission proxy, 60-minute maximum hold, strong-bias/digestion definitions remain frozen from LAB012/LAB019/LAB020.

## Data split
- Discovery: break_time < 2024-01-01.
- Confirmation: 2024-01-01 <= break_time < 2025-07-01.
- Holdout: break_time >= 2025-07-01 — MUST NOT be read.

## Live snapshots
Reuse the LAB020 causal snapshot clock:
- only completed contiguous M1 bars after the frozen early entry;
- snapshot feature_max_i == decision_i;
- snapshot is generated only while the frozen baseline position is still alive and before its terminal exit;
- TP/SL within an M1 bar have priority over any management decision made at that bar close;
- management exit executes at next contiguous M1 open.

## Outcome classes
For each live snapshot, terminal baseline outcome is frozen from the original TP/SL/TIME path:
- `TP`: baseline outcome is TP.
- `SL`: baseline outcome is SL or SAME_BAR_LOSS.
- `TIME`: baseline outcome is TIME.

No future path information other than the training label may enter features.

## Frozen feature representations
### MINIMAL
Categorical:
- level

Numeric:
- current_R
- time_in_trade_min
- dir
- p_accept

### FULL LIVE STATE
Categorical:
- level
- digestion_state

Numeric = MINIMAL plus:
- mfe_R, mae_R, pullback_from_mfe_R
- distance_to_tp_R, distance_to_sl_R, range_since_entry_R
- progress_1/3/5/10
- eff_3/5/10
- favfrac_3/5/10
- level_x_now, level_x_min3, level_x_min5
- level_side_frac3, level_side_frac5
- old_level_degraded_now
- micro_seen_now, degrade_seen_now, minutes_since_micro

No new destination/topology features are admitted.

## Model
Fixed learner for MINIMAL and FULL:
- `HistGradientBoostingClassifier`
- learning_rate = 0.05
- max_iter = 200
- max_leaf_nodes = 15
- min_samples_leaf = 50
- l2_regularization = 1.0
- max_bins = 64
- early_stopping = false
- random_state = 20260824
- multiclass log-loss objective via predict_proba.

Training uses Discovery only.
Each snapshot receives `1 / number_of_snapshots_for_trade` sample weight so each trade contributes total weight 1.
No class balancing, probability threshold tuning, calibration tuning, or Confirmation fitting.

## Remaining payoff decomposition
For target T in {1.5R primary, 2.0R secondary}:
- terminal TP gross payoff = +T R.
- terminal SL gross payoff = -1.0 R.
- terminal TIME gross payoff = the trade-weighted mean baseline gross TIME payoff estimated using Discovery-only TIME trades for that same target.

At each live snapshot:
`EV_HOLD_terminal = pTP*T + pSL*(-1) + pTIME*TIME_MEAN_DISCOVERY`

`EV_HOLD_remaining = EV_HOLD_terminal - current_R`

Decision:
- HOLD if `EV_HOLD_remaining > 0`.
- EXIT_NOW if `EV_HOLD_remaining <= 0`.

There is no optimized safety margin, minimum holding time, timer or probability gate.
Execution of EXIT_NOW is next contiguous M1 open using bid/ask conventions already frozen in the parent execution model.

## Primary comparison
Primary strategy: FULL OUTCOME_X_PAYOFF manager, target 1.5R, serial one-position-at-a-time portfolio.
Compare against the exact frozen early-entry baseline on the same universe.

Secondary diagnostics:
- MINIMAL manager economics.
- 2R target.
- BUY/SELL breadth.
- 2024 vs 2025H1 transfer.
- class probability calibration / multiclass log-loss / multiclass Brier.
- outcome-conditioned management delta.
- group permutation importance.

## Metrics
Prediction:
- macro one-vs-rest AUC
- TP-vs-rest AUC
- SL-vs-rest AUC
- TIME-vs-rest AUC when class count permits
- multiclass log-loss
- multiclass Brier score

Economics:
- N, trades/week, EV, PF, TP rate, model-exit rate
- gross EV, cost-stress EV
- max DD R, worst day R, max consecutive losses
- BUY EV, SELL EV
- paired manager-minus-baseline weekly bootstrap CI
- weekly strategy EV CI

## Frozen gates
- G0_DATA_CAUSALITY: zero snapshot causality violations; holdout sealed.
- G1_POWER: serial N >= 500 and trades/week >= 5.
- G2_PROBABILITY_INFORMATION: FULL macro OVR AUC >= 0.60.
- G3_FULL_ADDS_OVER_MINIMAL: FULL - MINIMAL macro AUC >= +0.02 and weekly bootstrap lower CI > 0.
- G4_CALIBRATION: FULL multiclass log-loss < MINIMAL and FULL multiclass Brier < MINIMAL.
- G5_CONFIRMATION_EV: primary serial EV > 0 and PF > 1.
- G6_WEEK_CLUSTER_CI: primary weekly EV lower 95% CI > 0.
- G7_MANAGEMENT_LIFT: paired manager-minus-baseline trade mean > 0 and weekly bootstrap lower CI > 0.
- G8_TIME_TRANSFER: 2024 and 2025H1 independent managed EV each > 0.
- G9_2R_SURVIVAL: 2R serial EV >= 0.
- G10_DIRECTION_BREADTH: BUY EV > 0 and SELL EV > 0.
- G11_PROP_DD_PROXY: max DD <= 20R and worst day > -16R.
- G12_COST_STRESS: +$0.10 stress EV > 0.

## Verdict labels
- INVALID_DATA_CAUSALITY
- OUTCOME_X_PAYOFF_MANAGEMENT_EXECUTABLE_EDGE
- OUTCOME_X_PAYOFF_POSITIVE_BUT_NOT_PROP_READY
- OUTCOME_PROBABILITIES_INFORMATIVE_BUT_MANAGEMENT_NEGATIVE
- OUTCOME_X_PAYOFF_MANAGEMENT_IMPROVES_BUT_REMAINS_NEGATIVE
- NO_OUTCOME_X_PAYOFF_MANAGEMENT_EDGE

## Prohibitions
- No holdout opening.
- No exit-margin tuning after outcomes.
- No class reweighting after outcomes.
- No post-hoc probability calibration on Confirmation.
- No rescue subset may change the frozen verdict.
- No EA/live authorization from this LAB alone.
