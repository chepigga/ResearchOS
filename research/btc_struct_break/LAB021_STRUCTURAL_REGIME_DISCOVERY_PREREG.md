# LAB021 — OLD_PROTECTED_PIVOT_STRUCTURAL_REGIME_DISCOVERY

Date: 2026-08-26
Status: PREREGISTERED BEFORE CALCULATION

## Objective
Search for additional rare M15 structural regimes of the same class as the surviving old-protected-pivot core, without weakening the frozen core and without introducing ML/threshold optimization.

## Base event families
1. BREAK_RETEST canonical M15 entries.
2. COMPRESSION_RELEASE SELL M15 events, using the exact LAB018 operational definition and preserving pooled-family causal queue/state where relevant.

## Frozen structural regime hypotheses

### R0 — OLD_PROTECTED_CORE control
Latest opposite-side confirmed pivot-5 at fill:
- age >=22 M15 bars;
- unviolated after confirmation;
- riskATR >3.72.

### R1 — DISJOINT_MODERATE_MATURITY
The LAB020 watch island, frozen exactly:
- latest pivot-5 age 16–21 bars;
- unviolated;
- riskATR 2.5–3.0.
This is a known discovery seed, not a new discovery.

### R2 — NESTED_ANCESTOR_PROTECTED
The latest pivot-5 itself does NOT satisfy R0, but an earlier same-side confirmed pivot-5 exists that:
- age >=22 bars at fill;
- has never been violated after its confirmation and before fill;
- lies on the valid stop side of entry;
- entry-to-ancestor distance >3.72 ATR14(fill);
- is the nearest qualifying older pivot to current price (no outcome-based selection).
Purpose: test whether young local pivots can hide a still-valid higher-order protected anchor.

### R3 — TESTED_AND_HELD
Latest valid opposite-side pivot-5:
- age >=16 bars;
- unviolated;
- riskATR >=2.5;
- after pivot confirmation and before fill, price returns within 0.75 ATR14(fill) of pivot at least once but does not violate it;
- subsequently closes at least 2.0 ATR away from the pivot before the entry event.
Purpose: test a causally demonstrated defense/rejection state rather than age alone.

### R4 — PERSISTENT_DISPLACEMENT
Latest valid opposite-side pivot-5:
- age >=16 bars;
- unviolated;
- riskATR >=2.5;
- for the final 8 completed M15 bars before the release/break event, every close remains at least 2.0 ATR14(fill) away from the pivot in the favorable direction.
Purpose: test sustained acceptance away from the structural anchor.

### R5 — ACCEPTED_BALANCE_AWAY
Latest valid opposite-side pivot-5:
- age >=16 bars;
- unviolated;
- riskATR >=2.5;
- final 8 completed M15 bars before event form a range whose near edge remains at least 1.5 ATR14(fill) away from the pivot;
- 8-bar range <=2.5 ATR14(fill).
Purpose: test mature balance/acceptance away from the anchor before a new M15 event.

## Evaluation
For each regime x event family:
- N, trades/year, EV, PF, sumR, MaxDD;
- yearly EV 2019–2025;
- DEV 2019–2022 vs VAL 2023–2025 descriptive transfer;
- 1.0x / 1.25x / 1.5x modeled cost;
- overlap with R0 core and overlap among candidate regimes;
- bootstrap CI for EV;
- contribution concentration by year.

## Discovery seed gate
A regime/event combination is promoted only to REPLICATION SEED if:
- DEV EV >0;
- VAL EV >= +0.08R;
- VAL PF >=1.15;
- at least 2/3 VAL years positive;
- 1.5x-cost VAL EV >0;
- VAL N >=25;
- bootstrap lower CI need not be >0 at discovery, but must not show clear negative center;
- overlap with R0 <=50% unless the regime materially improves R0 outcomes.

No candidate can be called confirmed from LAB021. Any survivor requires a separate frozen LAB022 replication.

2026 is shadow only and excluded from formal discovery verdict.
