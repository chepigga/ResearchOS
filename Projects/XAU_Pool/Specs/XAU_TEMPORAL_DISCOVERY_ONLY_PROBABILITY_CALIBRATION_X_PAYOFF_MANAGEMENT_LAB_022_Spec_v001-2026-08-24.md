# XAU_TEMPORAL_DISCOVERY_ONLY_PROBABILITY_CALIBRATION_X_PAYOFF_MANAGEMENT_LAB_022 — Spec v001
Date: 2026-08-24
Status: PREREGISTERED / PRE-OUTCOME / HOLDOUT SEALED

## Research question
LAB021 showed strong OOS rankability for live TP/SL/TIME outcomes but poor probability calibration and no management edge.
Test whether a calibration layer learned exclusively from temporally out-of-time Discovery predictions can convert the frozen LAB021 outcome ranking into usable money probabilities for the unchanged EV(HOLD) vs EXIT decision.

## Frozen lineage
- Same XAU canonical M1 lineage and same pre-holdout caches as LAB021.
- Same strong-bias / digestion early-entry universe.
- Same live-state snapshot construction as frozen LAB020.
- Same LAB021 multiclass outcome labels:
  - TP
  - SL (including SAME_BAR_LOSS)
  - TIME
- Same entry, hard SL, TP, commissions, stress assumptions, time horizon, serial-deduplication.
- Holdout: break_time >= 2025-07-01 remains sealed.

## Splits
Discovery: break_time < 2024-01-01
Confirmation: 2024-01-01 <= break_time < 2025-07-01
Sealed holdout: break_time >= 2025-07-01

### Temporal calibration folds inside Discovery
Primary FULL-state calibration uses expanding-window out-of-time Discovery predictions:
- Fold A train: break_time < 2023-01-01
  calibration-prediction window: 2023-01-01 <= break_time < 2023-07-01
- Fold B train: break_time < 2023-07-01
  calibration-prediction window: 2023-07-01 <= break_time < 2024-01-01

The two OOT probability blocks are concatenated and used ONLY to estimate the calibration parameter.
No Confirmation labels may influence model fit, temperature, TIME payoff, threshold, or decision rule.

## Frozen base learner
Exactly the LAB021 FULL-state multiclass HistGradientBoostingClassifier architecture and FULL feature set.
Sample weights preserve equal total weight per trade, as in LAB021.
Final base model is fitted on all Discovery snapshots after calibration temperature is frozen.

## Primary calibration method
Single-parameter multiclass temperature scaling.

Given raw probabilities p_c:
  logit-like score z_c = log(max(p_c, 1e-12))
  calibrated p_c(T) = softmax(z_c / T)

T is selected on concatenated temporal OOT Discovery predictions to minimize multiclass log loss.
Frozen search domain: T in [0.50, 5.00].
Scalar bounded optimizer; no class-specific temperatures.
No isotonic, Platt-per-class, vector scaling, Dirichlet calibration, or Confirmation refit in primary LAB.

Interpretation:
- T > 1 softens overconfident probabilities.
- T < 1 sharpens underconfident probabilities.

A separate T is estimated for 1.5R and 2R outcome models because terminal outcome distributions differ.
Primary verdict is based on 1.5R.

## Discovery-only TIME payoff
Unchanged from LAB021:
E_DISCOVERY[TIME terminal gross R] is estimated from Discovery trades only, separately for 1.5R and 2R.

## Management decision
At every completed live M1 snapshot:
EV_HOLD_terminal =
  pTP_cal * target_R
+ pSL_cal * (-1.0R)
+ pTIME_cal * E_DISCOVERY[TIME terminal gross R]

EV_REMAINING = EV_HOLD_terminal - current_R

Decision:
- HOLD if EV_REMAINING > 0
- EXIT if EV_REMAINING <= 0
Exit executes at next contiguous M1 open, using the same bid/ask convention and causal precedence as LAB021.
No margin, hysteresis, timer, or probability threshold is optimized.

## Primary comparisons
1. LAB021 RAW_FULL probabilities vs TEMP_CAL_FULL on untouched Confirmation:
   - macro OVR AUC (should be unchanged within numerical tolerance)
   - log loss
   - multiclass Brier
   - class calibration quintiles
2. RAW_FULL payoff manager vs TEMP_CAL payoff manager vs frozen baseline:
   - serial EV / PF
   - paired trade-level management-minus-baseline
   - week-cluster bootstrap CI
   - BUY / SELL EV
   - 2024 / 2025H1 transfer
   - 2R secondary survival
   - stress and DD proxies

## Frozen gates — primary 1.5R
G0_DATA_CAUSALITY:
- all hashes match
- no feature/decision lookahead
- no holdout rows read

G1_POWER:
- calibrated serial N >= 500
- >= 5 trades/week

G2_RANK_INFORMATION:
- raw FULL macro AUC >= 0.60

G3_CALIBRATION_IMPROVES:
- calibrated Confirmation logloss < raw FULL logloss
- calibrated Confirmation multiclass Brier < raw FULL Brier

G4_CALIBRATION_MATERIAL:
- relative logloss improvement >= 2%
- relative Brier improvement >= 2%

G5_CONFIRMATION_EV:
- calibrated serial EV > 0
- PF > 1

G6_WEEK_CLUSTER_CI:
- calibrated serial weekly EV bootstrap lower 95% CI > 0

G7_MANAGEMENT_LIFT:
- paired calibrated-manager minus frozen-baseline trade mean > 0
- week-cluster lower 95% CI > 0

G8_BEATS_RAW_MANAGER:
- paired calibrated-manager minus LAB021-style raw manager mean > 0
- week-cluster lower 95% CI > 0

G9_TEMPORAL_TRANSFER:
- calibrated independent EV > 0 in both 2024 and 2025H1

G10_2R_SURVIVAL:
- calibrated 2R serial EV >= 0

G11_DIRECTION_BREADTH:
- BUY EV > 0
- SELL EV > 0

G12_PROP_DD_PROXY:
- max DD <= 20R
- worst day > -16R

G13_COST_STRESS:
- +$0.10 stress EV > 0

## Verdicts
- CALIBRATED_OUTCOME_X_PAYOFF_MANAGEMENT_EXECUTABLE_EDGE
- CALIBRATION_FIXES_PROBABILITIES_NOT_ECONOMICS
- CALIBRATION_IMPROVES_BUT_NOT_TRANSFERABLE
- NO_TEMPORAL_CALIBRATION_MANAGEMENT_EDGE
- INVALID_DATA_CAUSALITY

## Prohibited post-hoc actions
- no Confirmation calibration
- no threshold or exit-margin tuning
- no class-specific rescue temperatures
- no switching to isotonic/Platt after result
- no BUY-only / SELL-only promotion from this LAB
- no holdout opening
- no EA/live authorization
