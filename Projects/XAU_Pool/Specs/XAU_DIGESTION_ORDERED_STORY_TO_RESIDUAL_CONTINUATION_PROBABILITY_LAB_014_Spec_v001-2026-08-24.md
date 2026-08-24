# XAU_DIGESTION_ORDERED_STORY_TO_RESIDUAL_CONTINUATION_PROBABILITY_LAB_014 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-24  
**Parents:** LAB009 Bias Engine v001 → LAB011 → LAB012 → LAB013

## Motivation

LAB012 showed that the earlier digestion-close location contains a strong latent economic split: setups that later re-accelerate are profitable from the digestion next-open, while non-reaccelerating setups are strongly negative. LAB013 then showed that predicting `MICRO_REACCEL_SOON` itself is the wrong objective: high `P(reaccel)` often identifies cases where the rebound has already progressed far enough that residual 1.5R economics are exhausted.

LAB014 changes the target from a future event to the trader's actual economic question:

> Given the **entire ordered story already known at the digestion close**, is there still enough residual continuation from the executable next-M1-open entry to take TP1.5R before SL1R?

Primary target:

`RESIDUAL_TP15 = 1` iff the frozen LAB012/LAB013 digestion-next-open trade reaches the full 1.5R TP before the 1R SL within the frozen 60-minute horizon. All SL, same-bar-loss, and time-exit outcomes are `0`.

The model estimates:

`p_residual = P(RESIDUAL_TP15 = 1 | causal ordered story at digestion close)`

This is intentionally different from `P(MICRO_REACCEL_SOON)`.

## Canonical lineage / embargo

- canonical market input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- canonical SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- frozen parent event table: LAB013 `events.csv.gz`
- parent event SHA-256: `6a1ab06285b84003e284fb683058806629e0760089c681f6327d29d6348b7fd8`
- frozen LAB012 runner SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`
- frozen LAB013 runner SHA-256: `c23835cad2260f22cbc79df1b08b88688534b3f151ff886f0eabeca43fd9dd1b`
- Discovery: `break_time < 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>=2025-07-01`

No holdout bars or post-holdout events may be read.

LAB014 does **not** redefine break, bias, digestion, execution, SL/TP, spread, commission, or the 60-minute horizon. It consumes the frozen causal digestion events and frozen baseline execution outcomes from LAB013.

## Eligible universe

Only parent rows satisfying all of:
- `strong_accept == true` from frozen LAB009 Bias Engine (`p_accept >= 0.75`);
- `digestion_found == true`;
- valid `baseline_entry_i >= 0` and `baseline_entry_time`;
- `feature_causality_violation == false`;
- `causality_violation == false`;
- `baseline_outcome_1p5` present;
- `break_time < 2025-07-01`.

Entry timing remains frozen:
- decision = completed digestion close;
- executable entry = next contiguous M1 open;
- BUY AskOpen / SELL BidOpen from parent LAB012 simulation.

## Primary economic target

`RESIDUAL_TP15 = 1` iff `baseline_outcome_1p5 == "TP"`.

Otherwise `0`, including:
- `SL`;
- `SAME_BAR_LOSS`;
- `TIME`.

The target is defined from the frozen 1.5R execution geometry:
- `1R = 0.50 * ATR_touch`;
- TP = 1.5R;
- SL = 1R;
- max hold = 60m;
- spread embedded through Bid/Ask;
- commission proxy `$0.05` XAU price-equivalent round-turn.

Secondary diagnostic target only:
- `RESIDUAL_TP20 = 1` iff frozen `baseline_outcome_2p0 == "TP"`.

## Story representations

All features must be timestamped at or before the digestion close. No future `micro_found`, `micro_wait`, future outcome, future maximum excursion, or future label may enter the model.

### A. LOCATION_SNAPSHOT — baseline

Causal context available at digestion close:
- categorical: `digestion_state`, `level`, `bias_s3`, final observed internal state;
- numeric: `p_accept`, `elapsed_min`, `digestion_block_index`, `pre_expand_count`, `x_end`, `drawdown_end`, `digestion_change`, `digestion_range_atr`.

This model intentionally answers: “where are we now?” without the full ordered story.

### B. ORDERED_STORY — primary

Adds the chronological path already known at digestion close:
- `bias_s1`, `bias_s2`, `bias_s3` as separate categorical positions;
- `internal_A`, `internal_B`, `internal_C`, `internal_D` as separate ordered categorical positions (unobserved positions remain explicit `NOT_OBSERVED`);
- five ordered digestion-bar price positions, each kept separate:
  - signed close distance `x_1..x_5`;
  - drawdown from prior directional high-water mark `dd_1..dd_5`;
  - directional close-to-close return `ret_1..ret_5`.

No sorting or averaging of the five-bar sequence is allowed.

### C. ORDERED_STORY_PLUS_ACTIVITY — secondary

Adds the same five-bar causal activity sequence:
- `volr_1..volr_5`;
- `range_1..range_5`.

This secondary model cannot rescue a failed primary verdict.

### D. REACCEL_PROBABILITY diagnostic only

LAB013 `p_ordered` / `p_reaccel` is **not** part of the primary model because Discovery values are fitted in-sample to the LAB013 target. It may only be reported as a diagnostic relation to `p_residual`, never used as a primary predictive feature or routing gate in LAB014.

## Model class

For each representation use a fixed, inspectable probability model:
- `sklearn.linear_model.LogisticRegression`
- L2 penalty
- `C=1.0`
- solver `liblinear`
- `max_iter=2000`
- numeric features standardized using Discovery mean/std only;
- categorical features one-hot encoded with Discovery vocabulary, unknown Confirmation categories ignored;
- no class weights;
- no hyperparameter search;
- no Confirmation recalibration.

Primary model = `ORDERED_STORY`.

## Train / evaluation protocol

### Primary Confirmation verdict
Train once on all Discovery eligible digestion setups (`break_time < 2024-01-01`) and evaluate untouched Confirmation (`2024-01-01 <= break_time < 2025-07-01`).

### Discovery temporal transfer diagnostic
Train only on Discovery events with `break_time < 2023-01-01`; evaluate on Discovery-2023 (`2023-01-01 <= break_time < 2024-01-01`).

No 2023 fitting for that diagnostic.

## Primary routing rule

No threshold search.

`RESIDUAL_ARMED = p_residual >= 0.55`

Rationale: 0.55 is a preregistered semantic “more likely than not with margin” residual-continuation threshold, not fitted to Confirmation P&L. It is intentionally stricter than the theoretical approximately 40% win probability needed for a frictionless 1.5R/-1R binary payoff because real trades include costs and time exits.

Entry for `RESIDUAL_ARMED` remains the same frozen digestion next-M1-open entry. Rejected setups do not trade.

Pre-registered diagnostics only:
- thresholds `0.45`, `0.50`, `0.60`, `0.65` for monotonicity/power tables;
- probability quintiles/deciles.

These cannot replace the primary 0.55 rule in LAB014.

## Economics / portfolio

Reuse the frozen parent baseline execution columns exactly:
- primary economics: `baseline_net_R_1p5`;
- secondary: `baseline_net_R_2p0`;
- stress: `baseline_stress10_R_1p5`;
- TP/SL/time outcomes from parent.

No trade is resimulated with a different stop, target, entry, or hold.

### Independent
All eligible routed events are evaluated independently.

### Serial primary
Use the frozen LAB012 serial policy on the same digestion lifecycles:
- deterministic dedupe by `break_time`, direction, highest `p_accept`, tie `MID > HIGH > LOW`;
- simultaneous opposite-direction conflict at same break time skipped;
- one position max;
- when flat, inspect next lifecycle;
- if `p_residual < 0.55`, skip at the digestion decision and move on;
- if armed, enter at frozen next-M1-open;
- later overlapping lifecycles ignored until exit;
- no hedging, pyramiding, averaging, martingale.

Baseline = identical serial DIGESTION universe with no LAB014 probability gate.

## Evaluation

### Predictive
Report Discovery-2023 and Confirmation:
- N / target base rate;
- AUC, Brier, log loss for LOCATION_SNAPSHOT, ORDERED_STORY, ORDERED_STORY_PLUS_ACTIVITY;
- ordered-minus-snapshot AUC;
- calibration by quintile;
- `p>=0.55` precision, recall, coverage;
- routed vs rejected TP1.5 rate;
- BUY/SELL, MID/HIGH/LOW, digestion-state diagnostics;
- top standardized logistic coefficients;
- relationship between LAB013 `p_reaccel` and LAB014 `p_residual` as diagnostic only.

### Economics
Report Discovery-2023 and Confirmation:
- routed independent and serial N;
- trades/week;
- EV, PF, TP rate, total R;
- 2R survival;
- BUY/SELL EV;
- max DD, worst day, max consecutive losses;
- +$0.10 stress;
- serial baseline comparison.

### Bootstraps
Calendar-week cluster bootstrap, 4000 resamples, seed `20260824`:
- Confirmation primary serial mean R;
- routed-minus-baseline weekly mean-R difference;
- ORDERED_STORY AUC minus LOCATION_SNAPSHOT AUC;
- routed-minus-rejected TP1.5 rate.

## Frozen gates

Primary = Confirmation / ORDERED_STORY / `p_residual>=0.55` / frozen digestion next-open / 1.5R / serial.

- `G0_DATA_CAUSALITY`: canonical and parent hashes valid; holdout sealed; all feature timestamps <= digestion close; entry after decision; zero parent/feature causal violations.
- `G1_POWER`: Confirmation eligible setups >= 1500; routed serial trades >= 250; routed frequency >= 2/week.
- `G2_RESIDUAL_AUC`: Confirmation ORDERED_STORY AUC >= 0.65.
- `G3_SEQUENCE_INCREMENTAL`: ORDERED_STORY AUC - LOCATION_SNAPSHOT AUC >= +0.01 and lower 95% weekly bootstrap CI > 0.
- `G4_SELECTION_QUALITY`: routed TP1.5 rate >= 0.50 and routed-minus-rejected TP1.5 rate >= +15 percentage points with lower bootstrap CI > 0.
- `G5_CONFIRMATION_EV`: Confirmation routed serial EV > 0 and PF > 1.0.
- `G6_WEEK_CLUSTER_CI`: lower 95% weekly cluster CI of Confirmation routed serial mean R > 0.
- `G7_DISCOVERY_TRANSFER`: Discovery-2023 routed independent EV > 0 and Confirmation routed independent EV > 0.
- `G8_2R_SURVIVAL`: Confirmation routed serial 2R EV >= 0.
- `G9_DIRECTION_BREADTH`: Confirmation routed serial BUY EV > 0 and SELL EV > 0.
- `G10_PROP_DD_PROXY`: max DD <= 20R and worst day > -16R.
- `G11_COST_STRESS`: Confirmation routed serial 1.5R EV remains > 0 under extra `$0.10` price-equivalent stress.
- `G12_ROUTER_LIFT`: routed serial EV > all-DIGESTION serial EV and lower 95% weekly routed-minus-baseline CI > 0.

`ORDERED_STORY_PLUS_ACTIVITY` is secondary and cannot rescue a failed primary verdict.

## Verdicts

- `RESIDUAL_CONTINUATION_EXECUTABLE_EDGE`: all G0..G12 pass.
- `RESIDUAL_EDGE_NOT_PROP_READY`: G2..G7 and G12 pass but one or more 2R/breadth/DD/stress/power gates fail.
- `RESIDUAL_PROBABILITY_SELECTS_EDGE_BUT_NOT_ROBUST`: G2/G4/G5 pass but CI/transfer/router-lift gate fails.
- `SEQUENCE_PREDICTS_RESIDUAL_BUT_ECONOMICS_FAIL`: G2/G3/G4 pass but G5 fails.
- `RESIDUAL_EDGE_WITHOUT_SEQUENCE_INCREMENT`: G2/G4/G5 pass but G3 fails; economic selection exists but ordered path is not incremental over current location.
- `NO_RESIDUAL_CONTINUATION_EDGE`: G2 or G4 fails and no positive transferable economics.
- `INVALID_DATA_CAUSALITY`: G0 fails.

No holdout opening, EA authorization, or live allocation is authorized by LAB014.

## Anti-overfit

No post-result tuning of:
- parent LAB009/011/012/013 event definitions;
- `p_accept=0.75`;
- digestion blocks/states;
- feature families above;
- LogisticRegression class/C/solver;
- primary `p_residual=0.55`;
- `0.50 ATR` risk;
- `1.5R/2R` targets;
- 60m hold;
- cost assumptions;
- BUY/SELL, level, year, session, volatility, news, digestion-state subsets.
