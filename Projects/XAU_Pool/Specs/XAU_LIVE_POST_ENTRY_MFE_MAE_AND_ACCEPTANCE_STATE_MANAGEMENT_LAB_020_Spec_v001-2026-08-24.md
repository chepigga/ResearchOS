# XAU_LIVE_POST_ENTRY_MFE_MAE_AND_ACCEPTANCE_STATE_MANAGEMENT_LAB_020 — Spec v001

Date: 2026-08-24
Status: PREREGISTERED / PRE-OUTCOME

## 1. Research question

LAB019 showed that `no MICRO_REACCEL yet -> KILL` is not a valid management rule: it saves some eventual SL trades but destroys too many late/trigger-free winners. LAB020 tests a different causal question:

> Once the frozen early digestion entry is already live, can the *current live state of the position* estimate whether continuing to hold has positive incremental expectancy versus exiting now?

This is a management study. It does not create a new entry universe and does not change the frozen LAB009 Bias Engine.

## 2. Frozen lineage

Canonical XAU M1 source SHA-256:
`db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`

Frozen LAB012 runner SHA-256:
`09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`

Performance caches allowed only if hashes match:
- processed M1 dataframe: `ec05163508f6f69c9688e5e50e1f418f6ca64aba42f17cf8d6504775df147ef8`
- LAB012 setup table with frozen baseline 1.5R/2R outcomes: `83526be03cb66ff596c3949138e7e8935cd12b9f8783a41adaf5f2c04d4ccfda`

The cached tables are a speed shortcut only. Their event census and baseline economics must match the LAB019 lineage.

## 3. Splits / holdout

- Discovery: break_time < 2024-01-01.
- Confirmation: 2024-01-01 <= break_time < 2025-07-01.
- Sealed holdout: break_time >= 2025-07-01; MUST NOT be opened.

Secondary temporal transfer diagnostic:
- train on Discovery before 2023-01-01;
- evaluate management on 2023-01-01 <= break_time < 2024-01-01.

## 4. Frozen entry / trade geometry

Universe is exactly the LAB012/LAB019 causal digestion-entry universe:
- strong LAB009 bias;
- frozen digestion found;
- entry = next contiguous M1 open after digestion close;
- BUY entry uses ask open; SELL entry uses bid open;
- initial risk distance = 0.50 ATR_touch;
- primary TP = 1.5R;
- SL = 1.0R;
- maximum original hold = 60 minutes;
- commission-price proxy = 0.05;
- stress diagnostic adds 0.10 price units.

No entry filtering is allowed in LAB020.

## 5. Live decision clock

For an open trade, TP/SL intrabar barrier checks have priority.

If neither barrier is hit, after each completed M1 bar beginning with the first fully completed bar after entry, a management state is formed using information available through that bar close only.

If the manager chooses EXIT, execution is at the next contiguous M1 open:
- long exits at bid open;
- short exits at ask open.

No same-close fill is allowed.

## 6. Frozen live-state representation

All price movement features are normalized by frozen initial risk `0.50 * ATR_touch` unless noted.

### Position-state
- `current_R`: mark-to-market R at current close (long uses bid close; short uses ask close).
- `mfe_R`: maximum favorable excursion since entry.
- `mae_R`: maximum adverse excursion magnitude since entry.
- `pullback_from_mfe_R = mfe_R - current_R`.
- `distance_to_tp_R = 1.5 - current_R`.
- `distance_to_sl_R = current_R + 1.0`.
- `time_in_trade_min`.
- `range_since_entry_R`.

### Live path / tempo
For 1, 3, 5 and 10 completed-bar windows where available:
- signed progress per bar;
- path efficiency = net progress / sum(abs signed close changes);
- favorable-close fraction.

### Acceptance state around the original broken level
Using bid close and the contemporaneous frozen level series, normalized by ATR_touch:
- current signed distance to broken level;
- minimum signed distance over last 3 and 5 closes;
- fraction of last 3 and 5 closes on breakout side (>0);
- `old_level_degraded_now = current signed distance <= 0.05 ATR`.

### Frozen context already known at entry
- `p_accept` from LAB009 Bias Engine;
- direction;
- level (MID/HIGH/LOW);
- digestion_state.

### Causal event flags
- `micro_seen_now = 1` only if frozen LAB012 MICRO_REACCEL has already completed by this decision bar;
- `degrade_seen_now = 1` only if frozen LAB012 degrade event has already completed by this decision bar;
- minutes since micro if observed, else sentinel.

No future `micro_found`, future degrade time, baseline outcome, future MFE/MAE, or future path value may enter features.

## 7. Training target: incremental HOLD advantage

For each Discovery live snapshot that occurs strictly before the frozen baseline exit, define:

`hold_advantage_R = frozen_baseline_gross_R_1p5 - current_R_close`

Interpretation:
- positive target: holding to the original frozen exit would outperform exiting at the current mark;
- negative target: exiting now would outperform continuing the original hold.

Snapshots from the same trade receive total training weight 1.0 (`weight = 1 / number_of_snapshots_for_trade`) so long-duration trades do not dominate training.

## 8. Frozen learner

Primary model: `HistGradientBoostingRegressor` with fixed parameters:
- learning_rate = 0.05
- max_iter = 200
- max_leaf_nodes = 15
- min_samples_leaf = 50
- l2_regularization = 1.0
- max_bins = 64
- early_stopping = false
- random_state = 20260824

Categoricals are one-hot encoded with unknown-category ignore. No hyperparameter search.

Baseline predictor for model diagnostics: same learner with only `current_R`, `time_in_trade_min`, direction, level and `p_accept`.

## 9. Primary causal management rule

At each live decision close:

- model predicts `E[hold_advantage_R | live state]`;
- if prediction > 0: `HOLD`;
- if prediction <= 0: `EXIT_NOW` at next contiguous M1 open.

The zero threshold is frozen by the economic definition of the target. It is NOT optimized.

Once EXIT is scheduled, no later feature can cancel it.

## 10. Primary comparison

Confirmation, 1.5R:
1. frozen BASELINE early-entry hold;
2. LIVE_STATE_MANAGER.

Both independent and serial non-overlap portfolios are reported. Primary verdict uses serial economics plus paired independent management-minus-baseline lift.

## 11. Secondary diagnostics (cannot rescue primary verdict)

- 2R version trained on the analogous 2R hold-advantage target.
- Discovery-2023 temporal transfer.
- conditional results by BUY/SELL, digestion_state, p_accept quartile.
- exit-state bins by current_R, MFE, MAE and pullback-from-MFE.
- manager action confusion against hindsight sign of hold_advantage (diagnostic only).
- feature permutation importance.

No threshold search and no post-hoc subgroup promotion.

## 12. Frozen gates

G0 DATA_CAUSALITY:
- no holdout access;
- every snapshot feature_max_i <= decision_i;
- scheduled exits are next-open only;
- TP/SL barrier priority preserved.

G1 POWER:
- Confirmation serial N >= 500;
- >= 5 trades/week.

G2 MODEL_INFORMATION:
- Confirmation snapshot-level AUC for `hold_advantage_R > 0` using predicted hold advantage >= 0.60.

G3 FULL_STATE_ADDS_OVER_MINIMAL:
- full-state AUC - minimal-state AUC >= +0.02;
- week-cluster bootstrap lower 95% CI > 0.

G4 CONFIRMATION_EV:
- serial net EV > 0;
- PF > 1.0.

G5 WEEK_CLUSTER_CI:
- lower 95% CI of weekly serial mean R > 0.

G6 MANAGEMENT_LIFT:
- paired independent manager-minus-baseline mean > 0;
- week-cluster bootstrap lower CI > 0.

G7 DISCOVERY_TRANSFER:
- 2023 management independent EV > 0;
- Confirmation independent EV > 0.

G8 2R_SURVIVAL:
- Confirmation serial 2R EV >= 0.

G9 DIRECTION_BREADTH:
- BUY EV > 0 and SELL EV > 0.

G10 PROP_DD_PROXY:
- max serial DD <= 20R;
- worst day > -16R.

G11 COST_STRESS:
- +0.10 price stress EV > 0.

## 13. Verdict labels

- `LIVE_STATE_MANAGEMENT_EXECUTABLE_EDGE`
- `LIVE_STATE_MANAGEMENT_POSITIVE_BUT_NOT_PROP_READY`
- `LIVE_STATE_PREDICTS_HOLD_VALUE_BUT_ECONOMICS_NEGATIVE`
- `LIVE_STATE_MANAGEMENT_IMPROVES_BUT_REMAINS_NEGATIVE`
- `NO_LIVE_STATE_MANAGEMENT_EDGE`
- `INVALID_DATA_CAUSALITY`

## 14. Holdout policy

LAB020 may not open the >=2025-07-01 holdout under any verdict. No EA/live allocation is authorized by this LAB alone.
