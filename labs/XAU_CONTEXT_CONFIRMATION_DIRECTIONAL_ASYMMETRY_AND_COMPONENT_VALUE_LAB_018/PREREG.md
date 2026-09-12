# XAU_CONTEXT_CONFIRMATION_DIRECTIONAL_ASYMMETRY_AND_COMPONENT_VALUE_LAB_018 — PREREG

## Status
Preregistered before LAB018 runner/outcomes. This is a **reused-history directional robustness audit**, not fresh OOS validation and not a trading-edge test.

## Frozen lineage
- Base: LAB017 output commit `f451ae1317a7137138b0ba8e80190fe2c3c2fa4c`.
- Canonical XAU: release `ak47`, `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`, SHA256 `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`.
- Frozen Context/router, G1 compression, D14 concordance, M15 aggregation, exact ±1 ATR / 8h first-passage target, and LAB016 confirmation definitions are unchanged.
- Components remain exactly: `OB_CONFIRM`, `IMBALANCE_CONFIRM`, `LIQUIDITY_CONFIRM`, `PRICE_ACTION_CONFIRM`.
- Equal 25% weights remain frozen. `HIGH75 = SETUP_CONFIRMATION_PCT >= 75` remains unchanged.
- No component definition, threshold, horizon, weighting, or score boundary may be tuned in LAB018.

## Population and outcome
Exactly the LAB016/LAB017 population:
`PULLBACK & G1_VOL_COMPRESSION & D14_CONCORDANCE != 0`.
Primary outcome is exact `BULL_FIRST` / `BEAR_FIRST` ±1 ATR resolution in the next 8h. Accuracy is whether D14 direction equals the exact first-passage direction.

## Purpose
LAB017 found a descriptive HIGH75 asymmetry: BULL 76.2% vs BEAR 56.7%. LAB018 tests whether that asymmetry is statistically supported and maps component value separately inside BULL and BEAR so the future indicator can avoid presenting identical `QUALITY` semantics when the evidence behaves differently by direction.

## Bootstrap
- 5,000 weekly-cluster bootstrap draws.
- Seed `2026091218`.
- Cluster key: calendar week ending Sunday from `available_time`.

## H1 — HIGH75 directional asymmetry
Within exact resolved HIGH75 observations:
- require BULL N >= 25 and BEAR N >= 25;
- effect = accuracy(BULL) - accuracy(BEAR);
- PASS only if effect > 0 and weekly-cluster bootstrap 95% CI lower bound > 0.

If H1 passes, a single direction-agnostic `STRONG` semantic is considered structurally unsupported on reused history.

## H2 — BULL HIGH75 absolute quality
Within exact resolved BULL HIGH75 observations:
- N >= 30;
- accuracy > 60%;
- weekly-cluster bootstrap 95% CI lower bound > 55%.
PASS only if all hold.

## H3 — BEAR HIGH75 absolute quality
Within exact resolved BEAR HIGH75 observations:
- N >= 25;
- accuracy > 55%;
- weekly-cluster bootstrap 95% CI lower bound > 50%.
PASS only if all hold.

H2/H3 thresholds are frozen before outcomes and are intentionally different because LAB017 already established a large descriptive side gap; this LAB is testing whether each side supports a defensible human-facing quality label, not forcing symmetry.

## Component value by direction
For each side separately and each frozen component:
1. **Marginal premium** = accuracy(component present) - accuracy(component absent), with weekly-cluster bootstrap CI.
2. **Conditional premium**: hold the exact 3-bit pattern of the other three components fixed; retain strata where both present and absent have >=4 exact resolved observations on that side; aggregate stratum accuracy differences with weight `min(n_present,n_absent)`.
3. Report prevalence and N.

A component is tagged `DIRECTIONALLY_SUPPORTIVE` for a side only if:
- marginal premium > 0,
- conditional premium > 0,
- at least one of those two effects has a bootstrap/stratified support N >= 20.
This tag is descriptive/structural and cannot change the frozen 25% weight in LAB018.

## Exact composition map
Report exact confirmation combinations separately for BULL and BEAR:
- four exact 3-of-4 combinations (`NO_OB`, `NO_IMBALANCE`, `NO_LIQUIDITY`, `NO_PRICE_ACTION`),
- exact 4-of-4.
A side×combination cell is `ELIGIBLE` at N_resolved >= 10. No winner may be selected from ineligible cells.

## Predeclared side-specific candidate diagnostics
These are diagnostics motivated by LAB017 and are **not** allowed to replace the frozen score in LAB018:
- `HIGH75`
- `HIGH75_AND_OB`
- `HIGH75_AND_LIQUIDITY`
- `HIGH75_AND_IMBALANCE`
- `HIGH75_AND_PRICE_ACTION`
- `COREPAIR_PLUS_AUX = OB & LIQUIDITY & (IMBALANCE | PRICE_ACTION)`

For each candidate and each side report N, accuracy and weekly-cluster 95% CI. A candidate is `QUALITY_CAPABLE` only if N >= 25, accuracy > 60%, and CI lower bound > 50%. Because multiple candidates are inspected on reused history, no candidate other than frozen HIGH75 can be promoted to production semantics from this LAB alone.

## 24h diagnostic
For each side×HIGH75 report mean D14-signed 24h ATR follow-through. This is diagnostic only and cannot rescue or fail H1–H3; setup confirmation is primarily an entry/first-resolution quality layer, not a 24h trend forecast.

## Verdict
- `DIRECTIONAL_ASYMMETRY_CONFIRMED`: H1 passes. Report H2/H3 separately to determine which side supports `STRONG` under frozen HIGH75.
- `DIRECTIONAL_ASYMMETRY_NOT_CONFIRMED`: H1 fails, regardless of descriptive gap. H2/H3 and component maps remain useful diagnostics.

## Interpretation constraints
- `SETUP CONFIRMATION %` remains evidence coverage, **not probability of profit**.
- Reused history means all positive findings remain robustness/discovery evidence only.
- No automated entry, risk increase, component reweighting, or new threshold is authorized by LAB018.
