# XAU_CONTEXT_EXPANSION_PARENT_FAILURE_STATE_AND_DUAL_PERMISSION_LAB_003 — PREREG

## Goal
Determine whether the weak `EXPANSION + D14_BULL` parent found in LAB002 is degraded by a causal failure/staleness state, and whether a filtered Expansion branch can be combined with the frozen E75 core to materially increase trade frequency while preserving a prop-usable edge.

This is a discovery lab on reused XAU history. It is **not** production/OOS validation.

## Data
Canonical release asset only:
- tag: `ak47`
- file: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`

Evaluation window:
- start `2023-01-01 00:00:00`
- end exclusive `2026-07-01 00:00:00`

## Frozen lineage
H4 Context, D14, G1, state age/display roles, and M15 execution are imported unchanged from LAB001/LAB002.

Frozen M15 execution:
- LONG only
- Sweep→Reclaim / OB Retest / FVG Retest / BOS→Retest
- OR-router priority unchanged
- pending expiry 3h or permission expiry
- M15 structure stop - 0.10 ATR, minimum 1.0 ATR, reject >2.5 ATR
- TP 1.5R
- max hold 8h
- one open position
- 60m post-exit cooldown
- max 2 trades/day
- ambiguous same-M1 SL/TP = SL
- commission model unchanged
- spread stress checkpoints $0.20 and $0.40/oz
- DD conversion 0.25% risk per 1R

No execution/exit/cost parameter may be tuned.

## Frozen controls / parity locks
### C0 — E75_CORE
Exact LAB001/LAB002 baseline parent:
`PULLBACK & G1 & D14_BULL & evidence>=75`, 24h permission.
Expected:
- trades 98
- EV40 0.0752983797R ±1e-6
- PF40 1.1407351575 ±1e-6
- DD% 1.9209036869 ±1e-6

### C1 — EXPANSION_RAW_24H
Exact LAB002 P3 parent:
`EXPANSION & D14_BULL`, 24h permission.
Expected:
- trades 444
- mean trades/month 10.5714285714
- EV40 0.0311536R ±1e-5
- cumulative EV40 13.8322R ±0.02
- DD% 5.3882 ±0.02

If C0 or C1 parity fails, verdict = `TECHNICAL_PARITY_BLOCKED` and no discovery outcome is interpreted.

## Causal Expansion variants
Every variant uses only information known at the qualifying H4 close (`available_time`).

### X1 — EXP_LIVE4H
`EXPANSION & D14_BULL`.
Each qualifying H4 bar grants permission for **4h only**, i.e. until the next H4 decision point. Consecutive qualifying bars merge continuously. This is the primary stale-permission test.

### X2 — EXP_FORMING_LIVE4H
X1 plus existing LAB009 role `EXPANSION_FORMING` (`episode_age <= 3`).

### X3 — EXP_MATURE_LIVE4H
X1 plus existing LAB009 role `EXPANSION_MATURE` (`episode_age >= 4`).

### X4 — EXP_ADX_HIGH_LIVE4H
X1 plus `ADX14 >= causal median of the previous 100 ready H4 ADX14 values`. Current H4 is excluded from the median reference.

### X5 — EXP_BREAKOUT_ACCEPT_LIVE4H
X1 plus H4 close above the maximum H4 high of the previous 6 completed H4 bars. Current bar is excluded from the reference.

### X6 — EXP_NO_G1_LIVE4H
X1 plus `G1_VOL_COMPRESSION == False`.

No additional Expansion selector will be added after outcomes are visible.

## Failure-state diagnostics
For C1 raw Expansion trades, report performance by causal staleness bucket measured from the most recent qualifying `EXPANSION & D14_BULL` H4 available_time at M15 activation:
- `0-4h`
- `4-8h`
- `8-12h`
- `12-24h`

Also report parent-bar counts for forming/mature, ADX-high/low, breakout-accept yes/no, G1 yes/no. Diagnostics cannot create a post-hoc winner.

## Dual-permission variants
For each Xi, construct:
`E75_CORE_24H UNION Xi`

The E75 branch retains its exact 24h permission. Expansion branch retains its specified 4h permission. Overlapping permission intervals are merged; the same frozen M15 OR-router selects executable trades. No risk stacking or simultaneous positions.

Also report D0 = `E75_CORE UNION EXPANSION_RAW_24H` as a non-selectable diagnostic control.

## Metrics
For each standalone Xi and each dual Di report:
- qualifying H4 bars and merged episodes
- permission hours / % time
- trades; mean/median trades per month; % months >=8 and >=10 trades
- gross / commission / spread20 / spread40 expectancy R
- PF40 and cumulative R40
- max DD R and DD% at 0.25%
- max consecutive losses
- median/p90 hold
- 2023 / 2024 / 2025 / 2026H1 performance
- M15 family composition
- largest single-trade absolute-R concentration

## Primary hypotheses
### H1 — stale-tail failure exists
X1 improves on C1 under $0.40 stress by all of:
- EV40(X1) > EV40(C1)
- PF40(X1) > PF40(C1)
- DD%(X1) < DD%(C1)
And at least one stale bucket (`4-24h`) has EV40 below the `0-4h` bucket.

### H2 — filtered Expansion edge
An Xi (X2..X6) passes if:
- trades >= 180
- mean trades/month >=4
- EV40 >= +0.08R
- PF40 >=1.20
- DD at 0.25% <=4.0%
- max consecutive losses <=8
- positive expectancy in >=3/4 calendar blocks
- worst calendar block cumulative R >= -5R
- median hold <=8h
- top absolute trade share <=5%

### H3 — dual permission is useful
A dual Di passes if:
- trades >= 300
- mean trades/month >=8
- median trades/month >=6
- >=50% months have >=8 trades
- EV40 >= +0.08R
- PF40 >=1.20
- DD at 0.25% <=4.0%
- max consecutive losses <=8
- positive expectancy in >=3/4 calendar blocks
- worst calendar block cumulative R >= -5R
- median hold <=8h
- top absolute trade share <=5%

### Target dual
`TARGET_DUAL` requires H3 plus:
- mean trades/month >=10
- median >=8
- >=60% months >=8 trades

## Deterministic selection
Among Xi passing H2, rank by:
1. mean monthly R40
2. EV40
3. PF40
4. lower DD%

Among Di passing H3, same ranking. A dual winner takes precedence for EA architecture because frequency is the project objective.

## Verdicts
- any target dual -> `TARGET_DUAL_PERMISSION_CANDIDATE_FOUND`
- else any H3 dual -> `DUAL_PERMISSION_CANDIDATE_FOUND`
- else any H2 standalone Expansion -> `EXPANSION_FILTER_EDGE_FOUND_DUAL_NOT_READY`
- else H1 only -> `STALE_EXPANSION_FAILURE_CONFIRMED_BUT_NO_TRADABLE_FILTER`
- else -> `EXPANSION_FAILURE_STATE_NOT_SUPPORTED`

## Research boundary
All outcomes use reused XAU history and are discovery-only. Any winner must be frozen and taken to a separate temporal/fresh-OOS replication before EA production use.