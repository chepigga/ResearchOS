# XAU_CONTEXT_BROAD_PARENT_PERMISSION_AND_M15_OR_EXECUTION_LAB_002 — PREREG

## Goal
Test whether the frequency bottleneck found in LAB001 is primarily the H4 parent permission rather than the frozen M15 execution layer.

This is a discovery lab on reused XAU history. It does **not** constitute production validation.

## Data
Canonical release asset only:
- release/tag: `ak47`
- file: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`

Evaluation window frozen before outcomes:
- start: `2023-01-01 00:00:00`
- end exclusive: `2026-07-01 00:00:00`

## Frozen H4 Context lineage
Use the exact causal H4 Context lineage used by LAB001/LAB016/LAB018:
- state/router from LAB008/009/010
- D14 concordance = D1 HTF Bias == D2 Trend Pressure != 0
- G1 compression unchanged
- LAB016 evidence unchanged where it is defined

No future bars may be used to create parent permission.

## Frozen M15 execution layer
The execution layer is imported from `XAU_CONTEXT_HIGH_FREQUENCY_EXECUTION_LAYER_DISCOVERY_LAB_001` unchanged:
- LONG only
- four entry families: Sweep→Reclaim, OB Retest, FVG Retest, BOS→Retest
- OR-router across all four families
- family priority unchanged: Sweep, OB, FVG, BOS
- limit expiry: 3h or parent expiry, whichever is earlier
- stop: M15 structure - 0.10 ATR with minimum 1.0 ATR distance and rejection if >2.5 ATR
- TP: 1.5R
- max hold: 8h
- one open position at a time
- 60m cooldown after exit
- max 2 trades/day
- ambiguous same-M1 SL/TP bar is scored as SL
- risk for DD conversion: 0.25% per 1R
- commission model unchanged from LAB001
- spread stress checkpoints unchanged: $0.20/oz and $0.40/oz round-trip equivalent deducted in R

No entry/exit/cost parameter may be tuned in this lab.

## Parent permission construction
Each qualifying H4 bar creates a 24h LONG permission window beginning at its causal `available_time`. Overlapping windows are merged exactly as in LAB001. M15 trigger bars must close while permission is active.

### P0 — BASELINE_E75
Exact LAB001 parent gate:
`PULLBACK AND G1_VOL_COMPRESSION AND D14_BULL AND SETUP_CONFIRMATION_PCT >= 75`

### P1 — PULLBACK_D14
`PULLBACK AND D14_BULL`

### P2 — G1_D14
`G1_VOL_COMPRESSION AND D14_BULL`
regardless of state.

### P3 — EXPANSION_D14
`EXPANSION AND D14_BULL`

### P4 — PULLBACK_OR_EXPANSION_D14
`(PULLBACK OR EXPANSION) AND D14_BULL`

### P5 — NONRANGE_D14
`regime != RANGE AND D14_BULL`

### P6 — D14_ALL
`D14_BULL`
regardless of state.

No other parent formula will be added after outcomes are visible.

## Frozen metrics
For each parent variant, report:
- qualifying H4 bars
- merged permission episodes
- permission-hours and % of evaluation time
- raw M15 triggers and valid fills by family
- OR-router selected trades
- mean and median trades/month
- fraction of months with >=10 trades
- gross expectancy R
- commission-only expectancy R
- expectancy after $0.20 spread stress
- expectancy after $0.40 spread stress (`EV40`)
- PF after $0.40 stress (`PF40`)
- cumulative R after $0.40 stress
- max DD R and DD% at 0.25% risk
- max consecutive losses
- median and p90 holding time
- 2023 / 2024 / 2025 / 2026H1 block results
- source composition of OR-router

## Baseline parity lock
P0 must reproduce LAB001 E75_OR_ROUTER within numerical tolerance:
- trades = 98
- EV40 = 0.0752983797 R ± 1e-6
- PF40 = 1.1407351575 ± 1e-6
- max DD% = 1.9209036869 ± 1e-6
If parity fails, verdict = `TECHNICAL_PARITY_BLOCKED` and no parent comparison is interpreted.

## Hypotheses / decision gates
### H1 — frequency lift
A broadened parent passes H1 if:
- mean trades/month >= 10
- median trades/month >= 8
- >=60% of months have >=10 trades

### H2 — edge preservation
A broadened parent passes H2 if all are true under $0.40 spread stress:
- trades >= 300
- EV40 >= +0.05R
- PF40 >= 1.10
- max DD at 0.25% risk <= 4.0%
- max consecutive losses <= 8
- median hold <= 8h
- positive expectancy in >=3 of 4 calendar blocks
- worst calendar block cumulative R >= -5R
- largest absolute single trade <=5% of total absolute R

### H3 — useful broad parent
Pass iff the same broadened parent passes both H1 and H2.

### Target-frequency classification
A parent is `TARGET_FREQUENCY` only if it passes H2 and additionally:
- mean trades/month >=20
- median trades/month >=15
- >=75% of months have >=10 trades

A parent that passes H1+H2 but not target-frequency is `VIABLE_MEDIUM_FREQUENCY`.
A parent that passes H2 but not H1 is `EDGE_ONLY`.
A parent that passes H1 but not H2 is `FREQUENCY_ONLY`.
Otherwise `NOT_VIABLE`.

## Deterministic discovery ranking
Among parents passing H2, rank by:
1. higher mean monthly net40 R
2. higher EV40
3. higher PF40
4. lower max DD%
Frequency classification is reported separately and cannot rescue a negative/weak edge.

## Verdicts
- any `TARGET_FREQUENCY` -> `BROAD_PARENT_TARGET_FREQUENCY_CANDIDATE_FOUND`
- else any `VIABLE_MEDIUM_FREQUENCY` -> `BROAD_PARENT_MEDIUM_FREQUENCY_CANDIDATE_FOUND`
- else any `EDGE_ONLY` -> `BROAD_PARENT_EDGE_FOUND_FREQUENCY_STILL_LOW`
- else if any `FREQUENCY_ONLY` -> `FREQUENCY_LIFT_FOUND_BUT_EDGE_NOT_PRESERVED`
- else -> `BROAD_PARENT_PERMISSION_NOT_SUPPORTED`

## Research boundary
Because all variants are evaluated on reused XAU history, any selected parent must be frozen and tested in a separate temporal/fresh-OOS replication before EA/production use.