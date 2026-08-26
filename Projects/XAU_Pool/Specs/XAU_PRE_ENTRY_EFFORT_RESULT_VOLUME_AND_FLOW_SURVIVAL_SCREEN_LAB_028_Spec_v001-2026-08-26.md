# XAU_PRE_ENTRY_EFFORT_RESULT_VOLUME_AND_FLOW_SURVIVAL_SCREEN_LAB_028 — Spec v001

Date: 2026-08-26
Status: PREREGISTERED BEFORE OUTCOME RUN
Holdout cutoff: 2025-07-01 (sealed; never opened)

## Question
Can information available strictly before the frozen LAB025 starter entry identify which candidates will survive the first 5 completed M1 probation bars without shallow adverse/degradation?

## Frozen parent universe
Rebuild exactly from frozen LAB012 parent runner and canonical break census, then apply the LAB025 baseline-universe filters: strong_accept, digestion_found, baseline entry exists, no causality violation, break_time < holdout.

## Target
SURVIVE_FIRST_5M = 1 iff the LAB025 starter remains alive through all first 5 M1 probation bars and therefore would be eligible for promotion at t+5.
Failure occurs causally on any earlier event: frozen SL; same-side 0.10 ATR adverse return (BUY AskLow <= entry-0.10ATR; SELL BidHigh >= entry+0.10ATR); acceptance degradation x<=0.05 at completed bar close; TP during first 5m resolves the starter and is not counted as promotion-survival.

## Decision clock
Immediately before frozen early market entry. All rolling features end at entry_i-1. No entry-bar OHLC/volume/spread may be used.

## Data reality
Canonical XAU contains tick_volume and spread fields. real_volume is audited; if structurally zero it is not used or described as exchange volume. No external GC futures data are introduced in v001.

## Feature families
PRICE_ONLY:
- frozen p_accept, direction, level encoding, ATR
- signed pre-entry displacement / ATR over 3/5/15/30m
- directional efficiency = signed net path / total absolute close-to-close path
- range / ATR and close-location / range
- move-spent from break to entry / ATR where causal parent fields permit

TICK_ACTIVITY incremental:
- sum/mean/max tick_volume over 3/5/15/30m
- short/long activity ratios (3/15, 5/30)
- activity z-like ratio to 30m local mean

EFFORT_RESULT incremental:
- tick_volume sum divided by absolute displacement+epsilon
- tick_volume sum divided by directional efficiency+epsilon
- displacement per tick-volume unit
- range expansion per activity

SPREAD incremental:
- mean/max spread_mean, spread_max, spread_close over 3/5/15/30m
- short/long spread ratios
- tick_activity x spread interaction

FULL = all above.

## Model
HistGradientBoostingClassifier, fixed hyperparameters before outcome run: max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0, random_state=20260826. Median imputation learned on Discovery only. No hyperparameter tuning.

## Split
Use frozen parent split labels. Discovery only for fit and threshold construction. Confirmation untouched for verdict. Holdout >=2025-07-01 sealed.

## Operational threshold
For each model family, choose the 70th percentile of Discovery predicted score (top 30% Discovery score) as a fixed threshold. Apply unchanged to Confirmation.

## Primary comparison
FULL vs PRICE_ONLY on Confirmation.

## Metrics
- ROC AUC and Brier
- fixed-threshold Confirmation coverage
- survival precision among selected
- survival lift vs unconditional Confirmation base rate
- survivor retention = selected survivors / all Confirmation survivors
- failure rejection = rejected failures / all Confirmation failures
- selected starter-control EV proxy = 0.25 * frozen baseline net R1.5, diagnostic only
- winner retention diagnostics for baseline TP and later no-return cohorts where causally derivable, not target labels

## Frozen gates
G0 data/causality PASS.
G1 power: >=300 Confirmation events and >=50 survivors.
G2 rank information: FULL AUC >=0.60.
G3 activity adds: FULL minus PRICE_ONLY AUC >0 with week-cluster CI lower bound >0.
G4 operational precision: selected survival precision >=1.5x unconditional base rate.
G5 useful retention: survivor retention >=0.50 at Confirmation coverage <=0.40.
G6 failure rejection >=0.65.
G7 breadth: BUY and SELL selected precision each > their unconditional base rates.
G8 starter economics diagnostic: selected 0.25x baseline EV > unselected and >0.

Verdict taxonomy:
- PRE_ENTRY_SURVIVAL_ROUTER_EDGE if all gates pass.
- PRE_ENTRY_SURVIVAL_SIGNAL_BUT_NOT_ECONOMIC if G2/G4 pass but economics/retention gates fail.
- NO_PRE_ENTRY_SURVIVAL_SIGNAL otherwise.

No Confirmation threshold tuning, no sensitivity rescue, no holdout opening, no EA/live authorization.
