# CROSS_MARKET_CAUSAL_CONTEXT_DIRECTION_COMPATIBILITY_INTERACTION_LAB_003 — PREREG

Status: reused-history interaction audit. This lab is **not** fresh OOS and cannot authorize live sizing by itself.

## Frozen lineage

- Base branch/result lineage: `CROSS_MARKET_CAUSAL_CONTEXT_CONTINUOUS_SCORE_INTERACTION_LAB_002`.
- Frozen Context score: `C = (EXPANSION + PULLBACK - REVERSAL - RANGE) / 200`.
- No router weights, alpha rules, exits, risk sizing, or broker assumptions may be fit in LAB003.
- BTC frozen universe must remain exactly `N=327`.
- XAU causal context universe must remain exactly `N=263405` after restoring the LAB001 warm-up and regime-availability boundary.
- BTC outcome: `net_r_5bps`.
- XAU primary outcome: drift-adjusted `excess`; raw `R` is secondary.

## Frozen HIGH Context definitions

Thresholds are inherited from the LAB002 global Q5 edges and are not re-fit:

- BTC HIGH: `C > 0.525`.
- XAU HIGH: `C > 0.55`.
- NON_HIGH: complement within valid Context observations.

Direction compatibility is frozen:

- `ALIGNED`: BUY with BULL H4 bias or SELL with BEAR H4 bias.
- `OPPOSED`: BUY with BEAR H4 bias or SELL with BULL H4 bias.
- `NEUTRAL`: all other bias states. Neutral is descriptive/secondary and is excluded from the primary interaction estimator.

## Primary estimands

For each market, using ALIGNED and OPPOSED only:

1. `HIGH_PREMIUM = mean(HIGH, ALIGNED) - mean(HIGH, OPPOSED)`.
2. `NONHIGH_PREMIUM = mean(NON_HIGH, ALIGNED) - mean(NON_HIGH, OPPOSED)`.
3. **Primary interaction:**
   `INTERACTION = HIGH_PREMIUM - NONHIGH_PREMIUM`.

This definition prevents a generic direction-alignment effect from being mislabeled as Context interaction.

## Inference

- Weekly cluster bootstrap, 5000 draws, fixed seed `2026090903`.
- Bootstrap both `HIGH_PREMIUM` and `INTERACTION`.
- Report 95% percentile CI and probability > 0.
- No event-level IID confidence intervals are accepted as primary evidence.

## Transfer / stability audits

### Time

- BTC periods: `2021`, `2022`, `2023`, `2024`, `2025_H1`, `2025_H2`, `2026_JAN_JUL`.
  Eligible period requires at least 5 HIGH ALIGNED and 5 HIGH OPPOSED observations.
- XAU periods: calendar years `2022..2026`.
  Eligible year requires at least 200 HIGH ALIGNED and 200 HIGH OPPOSED observations.
- A period is positive when `HIGH_PREMIUM > 0`.

### Leave-one-period-out

For every eligible period, remove that period and recompute the pooled primary `INTERACTION` and `HIGH_PREMIUM`.

### XAU TF / direction / mechanics

- TF: `M5`, `M15`, `H1`; eligible cell requires at least 200 HIGH ALIGNED and 200 HIGH OPPOSED.
- Direction: BUY and SELL; same minimum 200/200.
- Mechanic: every frozen `f_*` flag in the XAU pool. For a mechanic, use rows where that flag equals 1; eligible mechanic requires at least 200 HIGH ALIGNED and 200 HIGH OPPOSED.
- Mechanics are audited individually; no best-mechanic selection is allowed.

BTC has no equivalent frozen mechanic flags in the 327-trade file, so mechanic transfer is XAU-only.

## Frozen gates

### Per-market CORE

- G1: `HIGH_PREMIUM > 0`.
- G2: bootstrap 95% CI lower bound for `HIGH_PREMIUM` > 0.
- G3: `INTERACTION > 0`.
- G4: bootstrap 95% CI lower bound for `INTERACTION` > 0.
- G5: at least 75% of eligible time periods have positive `HIGH_PREMIUM`, with at least 4 eligible periods.
- G6: at least 80% of leave-one-eligible-period-out runs keep both `HIGH_PREMIUM > 0` and `INTERACTION > 0`.

### XAU additional transfer gates

- G7: at least 2/3 eligible TFs have positive `HIGH_PREMIUM`.
- G8: BUY and SELL both have positive `HIGH_PREMIUM` when both are eligible.
- G9: among eligible mechanics, at least 70% have positive `HIGH_PREMIUM`, and the median mechanic premium is > 0.

## Verdicts

- `DIRECTION_CONTEXT_INTERACTION_SUPPORTED_DISCOVERY_ONLY`: all CORE gates pass for that market (plus G7-G9 for XAU).
- `MIXED_DIRECTION_CONTEXT_INTERACTION`: G1 and G3 pass but one or more robustness gates fail.
- `DIRECTION_CONTEXT_INTERACTION_NOT_SUPPORTED`: either G1 or G3 fails.
- Cross-market promotion requires both markets to achieve `...SUPPORTED_DISCOVERY_ONLY`; even then `promotion_authorized=false` because history is reused.

No threshold, subgroup, mechanic, direction, or period may be changed after outcomes are seen inside LAB003.