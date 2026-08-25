# STRUCT_BREAK_SECOND_BREAK_QUALITY_DECOMPOSITION_LAB_014

## Status
PREREGISTERED before outcome analysis.

## Purpose
Decompose the already frozen LAB013 BREAK2 population to determine *where* causal separation between successful and failed second breaks first appears. This LAB is diagnostic only: no trading selector is promoted from it.

## Frozen population
- Canonical STRUCT_BREAK v002 lineage.
- LAB008 LOW30 state unchanged.
- LAB013 reset/BREAK2/retest/ENTRY2 construction unchanged.
- DEV: 2019–2022.
- VAL: 2023–2025.
- 2026 excluded.
- Primary outcome: LAB013 fresh second-leg TP1.5R vs SL/TIME, with cost already embedded in PnL but classification based on path outcome.

## Five preregistered feature blocks
All values must be known no later than ENTRY2. No future bars after ENTRY2 may enter features.

### A. LOW severity
- LOW30 NET_R, MFE_R, MAE_R, closeback fraction, directional-close fraction.
- Distance from LOW30 current price to old entry in old-R units.

### B. Recovery quality
- time LOW30 -> reset/reclaim;
- recovery distance in old-R units;
- directional efficiency of the recovery path;
- fraction of post-LOW closes on the favorable side of old entry before reset when causally observable;
- whether reset was true recovery versus already-at/above-entry.

### C. New-structure maturity
- reset -> H2/L2 durations;
- H2/L2 separation and pullback depth;
- new structure width in ATR;
- number of confirmed post-reset pivots before BREAK2;
- BREAK2 relation to full post-LOW/post-reset range extreme.

### D. BREAK2 acceptance
- close penetration beyond BREAK2 level in ATR;
- break-bar body/range and close-location in side-aligned terms;
- immediate acceptance using only bars closed before ENTRY2 when retest is delayed;
- whether BREAK2 also clears the full post-reset range extreme.

### E. Retest quality
- BREAK2 -> ENTRY2 delay;
- maximum retest penetration through level before fill, normalized by fresh risk and ATR where causal;
- fill-bar close location cannot be used because entry occurs intrabar; only pre-fill completed bars plus static geometry are allowed;
- pullback depth relative to fresh structure width.

## Analysis
1. Report univariate oriented AUC separately on DEV and VAL for every feature.
2. Report block-level fixed L2 logistic models trained on DEV only and evaluated on VAL.
3. Report combined model only as a diagnostic; no threshold/selector promotion.
4. Report direction consistency DEV -> VAL and bootstrap CIs for VAL AUC where practical.
5. Apply Benjamini-Hochberg FDR to univariate feature tests as a caution against multiple comparisons.
6. Explicitly test whether any separation remains after conditioning on canonical FIRST trade fate using only for diagnostic interpretation; future FIRST fate itself is never a permissible predictor.

## Interpretation gates
A block is called `TRANSFER_SIGNAL` only if:
- VAL AUC >= 0.58;
- DEV and VAL orientation agree;
- no obvious leakage;
- signal is not solely explained by a future/outcome-derived variable.

A feature is called `STRONG_SEED` only if oriented VAL AUC >= 0.60 and direction agrees DEV -> VAL. This still does not authorize a trading rule.

Formal outputs are limited to:
- `NO_PRE_ENTRY_SEPARATION`
- `WEAK_TRANSFER_SEED`
- `QUALITY_BLOCK_TRANSFER_SIGNAL`

No LAB015 rule may be proposed by optimizing VAL thresholds from this decomposition.