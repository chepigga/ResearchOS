# XAU_VWAP_SEQUENCE_PLACEBO_AND_EXECUTION_FRONTIER_LAB_003 — v001 REPORT

**Verdict:** `GENERIC_SEQUENCE_NOT_VWAP_SPECIFIC`  
**Holdout opened:** `false`

## Canonical audit

- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- raw rows: 1,454,538
- pre-holdout rows: 1,080,929
- mapped events: 178,914
- VWAP / same-anchor mean / lagged-VWAP-placebo events: 71,561 / 67,847 / 39,506
- Discovery / Confirmation: 94,602 / 84,312
- sealed holdout `>=2025-07-01`: untouched

## Primary answer

LAB002's post-touch sequence is real and highly transferable, but **it is not specific to current-session tick-volume VWAP**.

At the preregistered primary clock T+3 in Confirmation:

| Family | Coverage | Accuracy | Separation |
|---|---:|---:|---:|
| VWAP_VOLUME | 77.2% | 79.0% | 57.9 pp |
| ANCHOR_MEAN | 77.1% | 78.8% | 57.5 pp |
| LAGGED_VWAP_SHAPE | 78.4% | 78.4% | 56.7 pp |

Paired weekly `week × arrival_side` differences:

- VWAP − ANCHOR_MEAN: **+0.26 pp**, 95% CI **[-1.15, +1.64] pp** → FAIL.
- VWAP − LAGGED_VWAP_SHAPE: **+1.39 pp**, 95% CI **[-0.49, +3.22] pp** → FAIL.

Thus most of the very strong 85/15-style map in LAB002 is best interpreted as **generic short-horizon response persistence after a level interaction**, not a unique VWAP-volume effect.

## Execution frontier

VWAP_VOLUME in Confirmation:

| Clock | Coverage | Accuracy | Separation |
|---|---:|---:|---:|
| T+1 | 70.1% | 72.5% | 44.7 pp |
| T+3 | 77.2% | 79.0% | 57.9 pp |
| T+5 | 80.2% | 85.1% | 70.1 pp |

T+1 retains **63.9%** of the T+5 separation, passing the frozen 60% retention gate. Therefore useful state information is already present one minute after touch, but T+5 is substantially cleaner.

Important: these are **state-prediction metrics**, not trade P&L. The common future label still begins only after T+5, so LAB003 deliberately does not pretend T+1 can already monetize the full measured accuracy.

## Breadth / transfer

Confirmation T+3 VWAP separation:

- HIGH: **56.2 pp**, accuracy 78.2%
- LOW: **59.6 pp**, accuracy 79.9%
- MID: **58.1 pp**, accuracy 79.1%
- arrival from BELOW: **57.8 pp**
- arrival from ABOVE: **58.0 pp**

Yearly VWAP T+3 separation:

- 2022: **56.3 pp**
- 2023: **57.3 pp**
- 2024: **57.9 pp**
- 2025 H1: **57.9 pp**

The sequence itself is extremely stable; what fails is the claim that current-session VWAP owns the effect.

## Placebo nuance

There is one weak hint of location specificity only at T+5 in Confirmation:

- VWAP − lagged placebo: **+1.96 pp**, CI **[+0.34, +3.55] pp**.

But:
- this was not the preregistered primary clock;
- VWAP still does not beat same-anchor mean;
- Discovery T+5 VWAP − lagged placebo is essentially zero/slightly negative.

So it is not promoted as a finding.

## Frozen gates

- G0_DATA_CLOCK: PASS
- G1_VWAP_MAP_TRANSFER: PASS
- G2_VWAP_OVER_MEAN_T3: **FAIL**
- G3_VWAP_OVER_LAGGED_T3: **FAIL**
- G4_T1_RETAINS_SIGNAL: PASS
- G5_DIRECTION_MIRROR: PASS
- G6_LEVEL_BREADTH: PASS

## Interpretation

The podcast's useful idea survives, but in a different form:

> **The information is in the sequence after touching a level — not primarily in VWAP volume weighting.**

`BACK / reclaim` versus `THROUGH / hold` is a transferable causal state variable. VWAP can still be a convenient objective level generator, but LAB003 does not justify calling it the source of edge.

## Next research step

Do **not** optimize VWAP further.

The next lab should test actual executable economics from T+1 / T+3 / T+5 using Bid/Ask and the user's minimum R:R >= 1:1.5, with the decision made at the corresponding clock and outcomes starting immediately after that clock.

Suggested:
`XAU_POST_TOUCH_SEQUENCE_EXECUTION_ECONOMICS_LAB_004`

Primary question: does the generic causal sequence remain profitable after the entry delay, spread, stop geometry and 1.5R/2R targets?

No holdout opening and no live allocation are authorized by LAB003.
