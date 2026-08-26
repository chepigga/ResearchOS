# XAU_PRE_ENTRY_TICK_ACTIVITY_SURVIVAL_TRANSFER_LAB_029 — Spec v001
Date: 2026-08-26

## Hypothesis
The narrow PRICE + TICK_ACTIVITY family from LAB028 transfers better than the broad FULL stack and provides a stable pre-entry ranking of first-5m probation survival.

## Frozen parent/universe
- Canonical XAU M1 input SHA-256: db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b
- Frozen parent runner LAB012 SHA-256: 09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a
- Same strong-accept + digestion + early-entry universe and first-5m survival label as LAB028.
- Holdout >= 2025-07-01 remains sealed.

## Target
Binary survive5 = survives the first five completed M1 bars beginning with entry bar without:
1. baseline SL;
2. same-side 0.10 ATR adverse excursion;
3. acceptance degradation to <= +0.05 ATR from frozen level;
4. early TP1.5 is treated as early resolution, not survival.

## Decision clock
All features end at entry_i - 1. No feature may inspect entry bar or later.

## Feature families
### PRICE_ONLY control
p_accept, direction, level rank, ATR, move-spent/break age, 3/5/15/30m price displacement/path/efficiency/range/close-location.

### PRICE_PLUS_ACTIVITY primary
PRICE_ONLY plus tick_volume sum/mean/max over 3/5/15/30m and short/long tick-volume ratios.
No effort/result ratios. No spread features. No real_volume.

## Model
Fixed HistGradientBoostingClassifier:
- max_iter=200
- learning_rate=0.05
- max_leaf_nodes=15
- min_samples_leaf=40
- l2_regularization=1.0
- random_state=20260826

## Training
Discovery only (<2024-01-01). Confirmation 2024-01-01..2025-06-30 untouched.

## Operational threshold
Frozen from Discovery only: 70th percentile of primary model train scores (top 30%). No Confirmation threshold tuning.

## Primary diagnostics
- AUC PRICE_ONLY vs PRICE_PLUS_ACTIVITY on full Confirmation
- yearly: 2024, 2025H1
- BUY/SELL precision vs respective base rate
- score deciles on Confirmation
- coverage, precision lift, survivor retention, failure rejection
- selected vs rejected starter-control economics = 0.25 * frozen baseline net R

## Transfer gates
G0 causality / sealed holdout
G1 power >=300 Confirmation and >=50 survivors
G2 activity AUC > price-only AUC
G3 activity AUC >=0.62
G4 yearly transfer: AUC >0.58 in both 2024 and 2025H1
G5 yearly precision lift >1.15 in both periods
G6 direction breadth: selected precision > base for BUY and SELL
G7 useful operations: coverage 0.15..0.40 and survivor retention >=0.40
G8 failure rejection >=0.65
G9 selected starter-control EV > rejected starter-control EV
G10 score-decile spread: top decile survival > bottom decile survival and top decile >=1.5x overall base

## Verdicts
- TICK_ACTIVITY_SURVIVAL_ROUTER_TRANSFERABLE if all gates pass.
- TICK_ACTIVITY_SIGNAL_TRANSFERABLE_NOT_ECONOMIC if G0-G8 and G10 pass but G9 fails.
- TICK_ACTIVITY_SIGNAL_WEAK_OR_UNSTABLE otherwise.

No holdout opening, EA authorization, live allocation, or threshold rescue.
