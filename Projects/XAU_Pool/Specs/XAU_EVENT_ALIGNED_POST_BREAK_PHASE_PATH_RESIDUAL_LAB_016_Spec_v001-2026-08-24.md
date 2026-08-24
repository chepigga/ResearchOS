# XAU_EVENT_ALIGNED_POST_BREAK_PHASE_PATH_RESIDUAL_LAB_016 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-24  
**Parents:** LAB009 Bias Engine v001 → LAB011 → LAB012 → LAB014 → LAB015

## Motivation

LAB015 showed that raw chronological M1 path carries a small amount of incremental information over compressed story features, but fixed clock-time alignment remained weak and non-transferable. A human trader usually aligns a story by **events/phases**, not by minute number: initial expansion, first meaningful pullback, recovery attempt, subsequent push/failure, digestion.

LAB016 tests only this representation hypothesis. It keeps the LAB014/015 eligible universe, decision clock, executable entry, residual TP1.5 target, SL/TP, costs, hold horizon and embargo unchanged.

Primary question:

> Does an event/phase-aligned representation of the already-observed post-break path predict residual TP1.5 from the frozen digestion next-open better OOS than the same information aligned by fixed clock time?

## Canonical lineage / embargo

- canonical market input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- canonical SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- LAB008 break census SHA-256: `c9cba1459a60ef9c3bb308e751ebae95840f48a24f94754808862a180832ccdb`
- frozen LAB012 runner SHA-256: `09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a`
- reconstructed frozen LAB012 event table SHA-256: `a6ab0ece5ad2cdfff0b306a4de8d0a8932f6787dfad485441e57f6fe50b68c89`
- Discovery: `break_time < 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>=2025-07-01`

No bar at or after the holdout boundary may be read.

## Eligible universe / economics — frozen

Same causal digestion baseline universe as LAB014/015:
- LAB009 `p_accept >= 0.75`;
- frozen LAB012 `digestion_found == true`;
- valid next-open baseline entry after digestion close;
- no parent causality violation;
- frozen `baseline_outcome_1p5` exists.

Primary target:

`RESIDUAL_TP15 = 1` iff frozen LAB012 `baseline_outcome_1p5 == "TP"`; else `0`.

Frozen economics:
- `1R = 0.50 * ATR_touch`
- TP `1.5R`; SL `1R`
- max hold `60m`
- BUY Ask / SELL Bid
- spread embedded in canonical Bid/Ask lineage
- commission proxy `$0.05` XAU price-equivalent RT
- secondary 2R and +$0.10 stress unchanged.

No trade is resimulated with a different entry or risk geometry.

## Base causal path

For each eligible event, use completed M1 closes from break close through the frozen digestion close.

`x_t = dir * (Close_t - DynamicLevel_t) / ATR_touch`

Also retain at each observed minute:
- directional return `ret_t` / ATR_touch;
- running drawdown `dd_t = running_max(x) - x_t`;
- directional candle body `body_t = dir*(Close-Open)/ATR_touch`.

All phase landmarks must be `<= digestion_end_i`.

## Frozen event/phase landmark algorithm

The event-time segmentation is close-based and uses one fixed reversal size:

`PIVOT_REVERSAL = 0.15 ATR_touch`.

It is computed only on the path available by digestion close.

### P0 — BREAK
Break close (`break_i`).

### P1 — INITIAL_EXPANSION_PEAK
Starting after the break, track the running maximum of `x`. The first directional peak is confirmed when a later completed close is at least `0.15 ATR` below that running maximum **and** that peak was at least `+0.15 ATR` above the break-close `x`.

P1 is the argmax minute that established that confirmed running maximum.

If no such confirmed peak exists before frozen digestion start, P1 is the maximum `x` observed between break+1 and digestion_start-1. This fallback is flagged.

### P2 — FIRST_PULLBACK_TROUGH
After P1, track the running minimum. The first pullback trough is confirmed when a later completed close rebounds at least `0.15 ATR` above that running minimum.

P2 is the argmin minute that established that trough.

If no rebound confirms a trough before digestion start, P2 is the minimum `x` from P1 through digestion_start-1. This fallback is flagged.

### P3 — RECOVERY_PEAK
After P2, track a new running maximum. The recovery peak is confirmed when a later completed close draws down at least `0.15 ATR` from that maximum.

P3 is the argmax minute that established that maximum.

If no second drawdown confirms it before digestion start, P3 is the maximum `x` from P2 through digestion_start-1. This fallback is flagged.

### P4 — DIGESTION_START
Frozen LAB012 `digestion_start_i`.

### P5 — DIGESTION_END
Frozen LAB012 `digestion_end_i`; this is the decision close.

Landmarks are forced monotonic:
`P0 <= P1 <= P2 <= P3 <= P4 <= P5`.
If a phase collapses to zero/one bar, it remains valid and is represented by repeated observed values plus its duration flag; no future interpolation is introduced.

## Event-aligned raw representation

Five phases:
1. `INITIAL_EXPANSION`: P0 → P1
2. `FIRST_PULLBACK`: P1 → P2
3. `RECOVERY`: P2 → P3
4. `POST_RECOVERY`: P3 → P4
5. `DIGESTION`: P4 → P5

For every phase, sample exactly **5 relative-time slots** at nearest observed bar positions corresponding to 0%, 25%, 50%, 75%, 100% of that phase. This is nearest-index event-time sampling, not price interpolation.

For every relative slot preserve:
- `x`
- `ret`
- `dd`
- `body`

For every phase also include:
- phase duration in minutes;
- phase existence/fallback indicator;
- directional amplitude `x_end - x_start`.

These phase features may use only bars at or before P5.

## Comparison representations

All representations use the exact same frozen learner.

### A. FIXED_CLOCK_RAW — benchmark
Reproduce LAB015 `RAW_PRICE_PATH`: minimal static context plus 35 fixed M1 slots of `x/ret/dd/body/mask`.

### B. EVENT_ALIGNED_PRICE — primary
Minimal static context (`p_accept`, level, elapsed minutes, digestion_state) plus the 5 event-aligned phases described above.

### C. EVENT_ALIGNED_PLUS_COMPACT — secondary
EVENT_ALIGNED_PRICE plus LAB014 compact story. Diagnostic only; cannot rescue failed primary B.

Primary incremental hypothesis is B versus A, not B versus the weak compact model.

## Frozen learner

Use identical `sklearn.ensemble.HistGradientBoostingClassifier` for every representation:
- `learning_rate=0.05`
- `max_iter=200`
- `max_leaf_nodes=15`
- `min_samples_leaf=30`
- `l2_regularization=1.0`
- `max_bins=64`
- `early_stopping=False`
- `random_state=20260824`

Discovery-only fitting. No hyperparameter search, Confirmation calibration or feature selection.

Categorical context is Discovery one-hot; unknown Confirmation categories map to all-zero for that family.

## Train / evaluation

Primary:
- train all Discovery `<2024-01-01`
- untouched Confirmation `2024-01-01 ... 2025-06-30`.

Temporal transfer diagnostic:
- train pre-2023 Discovery
- test 2023 only.

## Routing rule — frozen

No threshold search:

`PHASE_RESIDUAL_ARMED = p_phase_residual >= 0.55`.

Entry remains frozen next M1 open after digestion close.

Diagnostic thresholds `0.45/0.50/0.60/0.65`, quintiles and top-20% may be reported but cannot replace `0.55`.

## Serial portfolio

Reuse frozen LAB012 deterministic serial policy and dedupe. Baseline = same entire digestion universe without LAB016 gate.

## Required diagnostics

Report:
- N/base rate;
- AUC/Brier/log loss for FIXED_CLOCK_RAW, EVENT_ALIGNED_PRICE, EVENT_ALIGNED_PLUS_COMPACT;
- EVENT_ALIGNED minus FIXED_CLOCK AUC with 4000 calendar-week bootstrap, seed 20260824;
- phase-fallback frequencies and phase-duration distributions;
- probability quintiles and frozen threshold selection quality;
- Discovery-2023 transfer;
- independent/serial 1.5R and secondary 2R economics;
- BUY/SELL and MID/HIGH/LOW breadth;
- DD/worst-day/consecutive-loss/+0.10 stress;
- routed-minus-baseline weekly bootstrap;
- permutation importance grouped by phase/channel as diagnostic only.

## Frozen gates

Primary = Confirmation / EVENT_ALIGNED_PRICE / `p>=0.55` / frozen next-open / 1.5R / serial.

- `G0_DATA_CAUSALITY`: canonical/parent hashes valid; holdout sealed; every landmark/feature <= digestion close; entry strictly after decision; no parent violation.
- `G1_POWER`: Confirmation eligible >=1500; routed serial >=250; routed >=2/week.
- `G2_PHASE_RESIDUAL_AUC`: event-aligned OOS AUC >=0.60.
- `G3_PHASE_BEATS_FIXED_CLOCK`: event-aligned AUC - fixed-clock raw AUC >= +0.03 and lower week-bootstrap CI >0.
- `G4_SELECTION_QUALITY`: routed TP1.5 >=0.48 and routed-minus-rejected >=+12pp with lower week-bootstrap CI >0.
- `G5_CONFIRMATION_EV`: routed serial EV >0 and PF>1.
- `G6_WEEK_CLUSTER_CI`: lower 95% weekly routed mean-R CI >0.
- `G7_DISCOVERY_TRANSFER`: 2023 routed independent EV >0 and Confirmation routed independent EV >0.
- `G8_2R_SURVIVAL`: routed serial 2R EV >=0.
- `G9_DIRECTION_BREADTH`: routed BUY EV >0 and SELL EV >0.
- `G10_PROP_DD_PROXY`: max DD <=20R and worst day >-16R.
- `G11_COST_STRESS`: routed +$0.10 stress EV >0.
- `G12_ROUTER_LIFT`: routed serial EV > baseline serial EV and lower routed-minus-baseline weekly CI >0.

## Verdicts

- `EVENT_ALIGNED_RESIDUAL_EXECUTABLE_EDGE`: all G0..G12 pass.
- `EVENT_ALIGNMENT_ADDS_RESIDUAL_INFORMATION_BUT_NOT_PROP_READY`: G2/G3/G4/G5/G7/G12 pass but one or more power/CI/2R/breadth/DD/stress gates fail.
- `EVENT_ALIGNMENT_PREDICTS_BUT_EXECUTION_FAILS`: G2/G3/G4 pass but G5 fails.
- `EVENT_ALIGNMENT_ADDS_INFORMATION_BUT_NO_SELECTION_EDGE`: G2/G3 pass but G4/G5 fail.
- `NO_EVENT_ALIGNED_RESIDUAL_EDGE`: G2 or G3 fails and no positive transferable routed economics.
- `INVALID_DATA_CAUSALITY`: G0 fails.

No holdout opening, EA authorization or live allocation is authorized by LAB016.
