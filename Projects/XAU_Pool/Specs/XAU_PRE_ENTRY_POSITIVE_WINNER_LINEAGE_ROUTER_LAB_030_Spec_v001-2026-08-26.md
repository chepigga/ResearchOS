# XAU_PRE_ENTRY_POSITIVE_WINNER_LINEAGE_ROUTER_LAB_030 — Spec v001

Date: 2026-08-26
Status: PRE-OUTCOME PREREGISTRATION
Holdout: SEALED, >= 2025-07-01 never opened.

## Purpose
Test whether information available strictly before the frozen early starter entry can identify the already-positive winner lineage discovered in LAB027, rather than merely first-5m survival.

## Frozen universe
Rebuild the exact LAB012/LAB025 pre-holdout strong-accept + digestion + early-entry serial universe using canonical XAU M1 data and frozen LAB012 parent runner. Expected split: Discovery 2423, Confirmation 2354.

## Positive lineage target
Binary target POSITIVE_LINEAGE=1 iff, starting from the frozen early market entry:
1. The candidate survives the exact LAB025 first 5 completed M1 probation bars with no frozen SL, no same-side shallow adverse excursion of 0.10 ATR, no acceptance degradation (directional close distance to frozen level <= +0.05 ATR), and no TP1.5; AND then
2. During the next 5 completed M1 bars either:
   A. TP1.5 is hit before SL and before a return to the RR=1.5 add-limit (= original early entry price), labelled EARLY_TP15; OR
   B. No SL, no TP1.5, and no return to original early entry price occurs for the full second 5m window, labelled DOUBLE_NO_RETURN_CONFIRMED.
All other candidates are negative.

This target intentionally matches the two positive cohorts emphasized by LAB027 (approximately 77 early TP1.5 + 118 double-no-return confirmed on Confirmation). It is a positive-state lineage target, not generic TP/SL and not survive5.

## Decision clock / causality
All router features must end at entry_i-1. No bar at or after the entry bar is allowed in features.

## Feature families
### PRICE_ONLY
Frozen narrow pre-entry price/context family used in LAB029:
- p_accept, dir, level_rank, atr0
- 3/5/15/30m directional displacement, path length, directional efficiency, range, close-location
- move_spent_break_entry
- break_to_entry_min

### PRICE_PLUS_TICK_ACTIVITY (PRIMARY)
PRICE_ONLY plus:
- tick_volume sum / mean / max over 3/5/15/30m
- tick activity ratios mean_3/mean_15 and mean_5/mean_30
No spread, handcrafted effort/result ratios, or real_volume. Canonical real_volume is unavailable/non-informative.

## Model
HistGradientBoostingClassifier fixed:
- max_iter=200
- learning_rate=0.05
- max_leaf_nodes=15
- min_samples_leaf=40
- l2_regularization=1.0
- random_state=20260826
Median imputation fitted on Discovery only.

## Operational threshold
Frozen from Discovery training predictions only: 80th percentile (top-20% score). No Confirmation tuning.

## Primary evaluation
Untouched Confirmation 2024-01-01 through 2025-06-30:
- AUC / Brier
- coverage
- positive-lineage precision and lift over base
- positive-lineage retention
- negative rejection
- BUY/SELL breadth
- subtype retention: EARLY_TP15 and DOUBLE_NO_RETURN_CONFIRMED
- selected vs rejected frozen baseline 1.5R EV and 0.25x starter-control EV
- score deciles
- yearly transfer: 2024 and 2025H1

## Frozen gates
G0 causality: 0 violations.
G1 power: Confirmation >=300 and >=100 positive-lineage events.
G2 rank information: PRIMARY AUC >=0.60.
G3 tick activity adds: PRIMARY AUC > PRICE_ONLY AUC.
G4 operational precision: selected precision >=1.5x base.
G5 useful retention: positive-lineage retention >=40% with coverage <=30%.
G6 yearly transfer: both 2024 and 2025H1 AUC >0.55 and precision lift >1.20.
G7 breadth: BUY and SELL selected precision > their base rates.
G8 subtype retention: >=30% of EARLY_TP15 and >=30% of DOUBLE_NO_RETURN_CONFIRMED retained.
G9 economic selection: selected frozen baseline EV >0 and selected 0.25x starter-control EV >0, and both exceed rejected cohort.
G10 decile spread: top decile positive-lineage rate >=2x bottom decile and >=1.5x overall base.

## Verdicts
- PRE_ENTRY_POSITIVE_LINEAGE_ROUTER_EDGE: all gates PASS.
- POSITIVE_LINEAGE_SIGNAL_NOT_ECONOMIC: G0/G1/G2/G4/G5/G6/G7/G8/G10 pass but G9 fails.
- NO_PRE_ENTRY_POSITIVE_LINEAGE_SIGNAL: otherwise.

No threshold rescue, no feature-family rescue, no holdout opening, no EA/live authorization.
