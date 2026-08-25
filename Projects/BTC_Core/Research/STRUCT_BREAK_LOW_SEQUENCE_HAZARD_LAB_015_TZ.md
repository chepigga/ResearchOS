# STRUCT_BREAK_LOW_SEQUENCE_HAZARD_LAB_015 — PREREGISTRATION

Date: 2026-08-25
Branch: lab/btc-struct-break-regime-004

## Question
Can the sequence observed after a frozen LOW30 state identify, causally and OOS, that the current trade is progressing toward `SL before reclaim`, and can that information improve exit timing versus both HOLD and immediate LOW exit?

## Frozen population
- Canonical STRUCT_BREAK v002 only.
- LOW30 state = exact frozen LAB008 classifier and DEV tertile threshold.
- Primary population is LOW30 trades that are still alive, have not reached +1R, and are below the original entry at the 30m LOW decision (`NET_R < 0`).
- DEV = 2019–2022.
- VAL = 2023–2025.
- 2026 excluded.

## Competing outcomes after LOW
Starting immediately after the LOW30 decision:
1. `RECLAIM`: price touches the original entry before the original stop.
2. `SL_BEFORE_RECLAIM`: original stop is touched before any reclaim of original entry.
Trades that hit neither within 120m remain censored for checkpoint hazard evaluation; their canonical final outcome is retained for policy PnL.

Adverse same-bar ordering: if both stop and reclaim are possible in the same M5 bar, count STOP first.

## Observation clock
Checkpoints every 5 minutes after LOW30 through 120 minutes: 5,10,...,120.
Only fully closed M5 bars after the LOW decision are used.
A setup leaves the risk set immediately after reclaim or stop.

## Frozen sequence features
No new external indicators. Sequence features are built only from price path relative to original entry and original R:
- current NET_R;
- change in NET_R from LOW;
- NET_R slope over last 15m and 30m;
- cumulative MFE since LOW;
- cumulative MAE since LOW;
- change in MAE from LOW;
- directional-close fraction since LOW and over last 15m;
- path efficiency since LOW and over last 15m;
- sign-change / reversal count in aligned 5m close-to-close returns;
- fraction of bars making new adverse excursion;
- fraction of bars making new favorable excursion;
- elapsed minutes since LOW.

Snapshot comparator uses only current NET_R, cumulative MFE and cumulative MAE, and elapsed time.

## Primary model
- Standardized L2 logistic regression, C=0.3.
- Candidate rows are time-varying checkpoints in the active risk set.
- Target for each active checkpoint = whether the setup ultimately reaches `SL_BEFORE_RECLAIM` before reclaim.
- Each setup receives equal total sample weight so long-lived trades do not dominate.
- Fit scaler/model on DEV only.
- VAL never used for feature choice, model fitting, sign flipping, or threshold choice.

## Frozen action threshold
Primary high-hazard threshold = DEV predicted-risk 75th percentile over active DEV checkpoints.
Policy trigger = first checkpoint where score >= frozen threshold.

## Primary diagnostics / gates
1. Sequence model VAL AUC >= 0.62 for `SL_BEFORE_RECLAIM`.
2. Sequence model VAL AUC must exceed snapshot comparator by >= 0.03.
3. High-hazard triggered VAL setups must have `SL_BEFORE_RECLAIM` rate >= 75%.
4. At least 30 VAL setups must trigger.

## Frozen policy test
For each LOW trade:
- if first high-hazard trigger occurs before reclaim/stop, exit the entire current position at the next M5 open;
- otherwise keep canonical HOLD management.
- no re-entry, no partial close, no new target.
- existing 0.06R round-turn cost is retained; no extra volume is added.

Compare on full canonical portfolio:
- canonical HOLD;
- immediate EXIT at LOW30;
- sequence-hazard exit policy.

Promotion requires on VAL:
- paired EV improvement vs canonical HOLD > 0;
- bootstrap 95% CI lower bound > 0;
- MaxDD not worse than canonical and preferably >=10% lower;
- improvement positive in at least 2 of 3 years 2023/2024/2025.

## Secondary diagnostics (non-promotional)
- Fixed checkpoint AUC at 15/30/60/120m.
- Hazard calibration by score quartile.
- Median lead time from high-hazard trigger to eventual stop.
- M1 replay for 2024–2025 using frozen M5 trigger times/levels to rule out M5 ordering artifacts.

No threshold or feature optimization is permitted after VAL results are visible.
