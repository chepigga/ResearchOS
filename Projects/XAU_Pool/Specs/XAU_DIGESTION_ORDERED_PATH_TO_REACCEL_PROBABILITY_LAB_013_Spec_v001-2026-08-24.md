# XAU_DIGESTION_ORDERED_PATH_TO_REACCEL_PROBABILITY_LAB_013 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-24  
**Parents:** LAB009 Bias Engine v001 → LAB011 → LAB012

## Motivation

LAB012 found a strong latent state: among accepted-side DIGESTION setups, those that later produced MICRO_REACCEL had an earlier digestion-close entry EV of about +0.35R, while those that did not re-accelerate were strongly negative. Waiting until MICRO_REACCEL became causally visible destroyed roughly 0.5R of entry value.

LAB013 therefore does **not** add more confirmation. It asks whether the **entire ordered story already known at the digestion close** can estimate the probability of near-future re-acceleration well enough to preserve the earlier next-M1-open entry.

Primary question:

`P(MICRO_REACCEL within 10m | all causal storyline information available at DIGESTION close)`

This is a probability/sequence problem, not a single-bar pattern test.

## Canonical data / embargo

- canonical input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- canonical SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- frozen break universe: LAB008 `break_census.csv`, `model_event=true`, family `VWAP_VOLUME`
- Discovery: break time `< 2024-01-01`
- Confirmation: `2024-01-01 <= break_time < 2025-07-01`
- sealed holdout: `>=2025-07-01`

No post-holdout bars/events may be read.

## Parent reconstruction — frozen

Reconstruct LAB012 exactly through the DIGESTION close:

1. LAB009 Bias Engine v001 at T+15 using Discovery-only Beta(1,1) probability and exact/last2/snapshot backoff.
2. `STRONG_ACCEPTANCE` iff `p_accept >= 0.75`.
3. After T+15, the old broken level is a failure boundary; acceptance is valid only while completed signed closes remain `> +0.05 ATR_touch`.
4. Scan LAB011 5-minute internal blocks T+16..20, 21..25, 26..30, 31..35.
5. First block in `DIGESTION = {SHALLOW_PULLBACK, DEEP_PULLBACK, BASE, HOLD}` before degradation is the frozen setup.
6. Entry location is frozen LAB012 `DIGESTION_BASELINE`: next contiguous M1 open after digestion close.
7. Future label is frozen LAB012 `MICRO_REACCEL`: first qualifying bar within the next 10 completed M1 bars, never after T+45, using the unchanged +0.05 ATR close-extreme break, +0.03 ATR directional body, +0.10 ATR accepted-side close, and no prior degradation.

LAB013 does not change the parent setup, target, risk geometry, or entry location.

## Target

Binary target:

`REACCEL_SOON = 1` iff the frozen LAB012 MICRO_REACCEL event occurs after this digestion close within the parent 10-minute causal window.

Else `0`.

The target is future information and is used **only for model training/evaluation**, never as an input feature.

## Causal feature clocks

Every primary input must be known by the completed digestion-close minute `j`. No bar after `j` may enter the model.

### A. SNAPSHOT model — comparator

Represents “where the market is now”, not the full story:

- `p_accept` from frozen LAB009 Bias Engine;
- digestion state;
- digestion block index after T+15 (A/B/C/D = 1..4);
- signed close distance to broken level at digestion close;
- directional drawdown from the pre-digestion high-water mark at digestion close;
- digestion block total directional change;
- digestion block range in ATR;
- ATR_touch.

### B. ORDERED_PRICE_STORY — primary model

Contains all SNAPSHOT inputs plus chronology already observed:

**LAB009 post-break bias sequence**
- position-specific state tokens for T+1..5, T+6..10, T+11..15 (`bias_s1`, `bias_s2`, `bias_s3`), preserving order.

**accepted-side block sequence before and including digestion**
- position-specific internal block tokens A/B/C/D up to the digestion block;
- unobserved later positions encoded as `NOT_OBSERVED`;
- number of completed EXPAND blocks before digestion;
- elapsed minutes break→digestion close.

**five-minute digestion micro-sequence**
For each of the five completed M1 bars inside the digestion block, position-specific values:
- signed distance to the broken level / ATR_touch;
- directional drawdown from the causal pre-/in-block high-water mark / ATR_touch;
- directional close-to-close return / ATR_touch.

The five positions remain separate. They are not sorted or averaged before modeling.

### C. ORDERED_PRICE_VOLUME_STORY — pre-registered secondary

Adds to B, for each of the same five digestion M1 bars:
- tick volume divided by the causal median tick volume of the completed T+1..T+15 post-break window;
- directional range (`high-low`) / ATR_touch.

This tests whether local activity adds information beyond ordered price behavior. It is not required for the primary verdict.

## Model class

Use a simple fixed regularized logistic probability model for each representation:

- sklearn LogisticRegression
- L2 penalty
- `C = 1.0`
- `solver = liblinear`
- `max_iter = 2000`
- numerical features standardized using Discovery mean/std only;
- categorical features one-hot encoded with Discovery vocabulary; unseen Confirmation categories ignored;
- no class weighting;
- no hyperparameter search;
- no probability recalibration on Confirmation.

Primary model = `ORDERED_PRICE_STORY`.

Rationale: the goal is a causal, inspectable probability model of an ordered trading story, not a black-box classifier.

## Discovery / Confirmation protocol

### Confirmation verdict model
Train once on all Discovery digestion setups and evaluate on untouched Confirmation.

### Discovery internal transfer diagnostic
Use a frozen temporal split:
- train on Discovery events with `break_time < 2023-01-01`;
- evaluate on Discovery-2023 events `2023-01-01 <= break_time < 2024-01-01`.

No 2023 fitting for that diagnostic.

## Primary routing rule

No threshold search.

`EARLY_ARMED = p_reaccel >= 0.70`

where `p_reaccel` is the primary ORDERED_PRICE_STORY probability at the digestion close.

This is a semantic probability threshold preregistered before Confirmation outcomes.

Entry for EARLY_ARMED remains the frozen LAB012 early digestion entry: next contiguous M1 open after the digestion close.

Rejected setups do not trade.

Pre-registered diagnostics only:
- probability deciles/quintiles;
- thresholds 0.60 and 0.80 for monotonicity/power diagnostics, never for primary verdict selection.

## Economics

Frozen from LAB012:

- `1R = 0.50 * ATR_touch` from actual executable entry;
- hard SL = 1R;
- primary TP = 1.5R;
- secondary TP = 2.0R;
- max hold = 60 minutes;
- BUY entry AskOpen, exits future Bid OHLC;
- SELL entry BidOpen, exits future Ask OHLC;
- same-M1 TP+SL = conservative LOSS;
- no hit = executable quote at horizon clipped to `[-1R,targetR]`;
- spread embedded in Bid/Ask;
- commission proxy `$5 RT/lot` = `$0.05` XAU price-equivalent;
- stress extra `$0.05` and `$0.10` price-equivalent.

No SL/TP optimization.

## Serial portfolio

Primary = `EARLY_ARMED / digestion-next-open / 1.5R / serial`.

- chronological break lifecycles;
- when flat, accept the next strong-bias lifecycle with a valid digestion setup;
- if its model probability is <0.70, skip immediately after digestion close;
- if >=0.70, enter at the next contiguous M1 open;
- one position max;
- later overlapping break lifecycles ignored while in a position;
- no hedging, pyramiding, averaging, martingale.

Baseline = same serial DIGESTION universe with no LAB013 probability gate.

## Frozen evaluation

### Predictive
Report Discovery-2023 and Confirmation:
- N and target base rate;
- ROC AUC for SNAPSHOT, ORDERED_PRICE_STORY, ORDERED_PRICE_VOLUME_STORY;
- Brier score;
- log loss;
- probability calibration by quintile;
- selected (`p>=0.70`) precision, recall, coverage;
- selected vs rejected target-rate gap;
- BUY/SELL, MID/HIGH/LOW and digestion-state precision/AUC diagnostics;
- top standardized positive/negative logistic coefficients.

### Economics
Report Discovery-2023 and Confirmation:
- selected independent and serial N;
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
- EARLY_ARMED minus all-digestion baseline weekly mean-R difference;
- ORDERED_PRICE_STORY AUC minus SNAPSHOT AUC;
- selected minus rejected REACCEL_SOON rate.

## Frozen gates

Primary = Confirmation / ORDERED_PRICE_STORY / p>=0.70 / digestion-next-open / 1.5R / serial.

- `G0_DATA_CAUSALITY`: canonical SHA valid, Bid/Ask present, holdout sealed, all features timestamp <= digestion close, entry next minute, zero causal violations.
- `G1_MODEL_POWER`: Confirmation resolved digestion setups >= 1500 and selected serial trades >= 300 and >= 3/week.
- `G2_REACCEL_AUC`: Confirmation ORDERED_PRICE_STORY AUC >= 0.65.
- `G3_SEQUENCE_INCREMENTAL`: ORDERED_PRICE_STORY AUC - SNAPSHOT AUC >= +0.02 and lower 95% week-bootstrap CI > 0.
- `G4_SELECTION_PRECISION`: Confirmation p>=0.70 target precision >= 0.70 and selected-minus-rejected REACCEL_SOON rate >= +20 percentage points with lower bootstrap CI > 0.
- `G5_CONFIRMATION_EV`: Confirmation serial EV > 0 and PF > 1.0.
- `G6_WEEK_CLUSTER_CI`: lower 95% weekly cluster CI of Confirmation primary mean R > 0.
- `G7_DISCOVERY_TRANSFER`: Discovery-2023 EARLY_ARMED independent EV > 0 and Confirmation independent EV > 0.
- `G8_2R_SURVIVAL`: Confirmation serial 2R EV >= 0.
- `G9_DIRECTION_BREADTH`: Confirmation serial BUY EV > 0 and SELL EV > 0.
- `G10_PROP_DD_PROXY`: max DD <= 20R and worst day > -16R.
- `G11_COST_STRESS`: Confirmation serial 1.5R EV remains > 0 under extra `$0.10` price-equivalent stress.
- `G12_ROUTER_LIFT`: EARLY_ARMED serial EV > all-DIGESTION serial EV and lower 95% weekly routed-minus-baseline CI > 0.

`ORDERED_PRICE_VOLUME_STORY` is secondary and cannot rescue a failed primary verdict in LAB013.

## Verdicts

- `EARLY_REACCEL_PROBABILITY_EXECUTABLE_EDGE`: all G0..G12 pass.
- `EARLY_REACCEL_EDGE_NOT_PROP_READY`: G2..G7 and G12 pass, but one or more 2R/breadth/DD/stress/power gates fail.
- `PROBABILITY_SELECTS_EDGE_BUT_NOT_ROBUST`: G2/G4/G5 pass, but CI/transfer/router-lift gate fails.
- `SEQUENCE_PREDICTS_REACCEL_BUT_ECONOMICS_FAIL`: G2/G3/G4 pass but G5 fails.
- `NO_EARLY_REACCEL_PROBABILITY_EDGE`: G2 or G4 fails and no positive transferable economics.
- `INVALID_DATA_CAUSALITY`: G0 fails.

No holdout opening, EA authorization, or live allocation is authorized by LAB013.

## Anti-overfit

No post-result tuning of:
- parent LAB009/012 definitions;
- p_accept 0.75;
- digestion state set/block alignment;
- future MICRO_REACCEL target/window/thresholds;
- feature families described above;
- LogisticRegression class/C/solver;
- p_reaccel primary threshold 0.70;
- 0.50 ATR risk;
- 1.5R/2R targets;
- 60m hold;
- cost assumptions;
- BUY/SELL, level, year, session, volatility, news, or digestion-state subsets.

Any change requires a new preregistered LAB.
