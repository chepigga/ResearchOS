# PREREG — BTC_SHORT_V1_FULL_SYSTEM_FROZEN_AUG2026_OOS_REPLICATION_LAB_055

## Purpose
Freeze and evaluate the complete BTC SHORT v1 system assembled from LAB043–LAB054 without changing any selector, threshold, entry, stop, target, horizon, failure-state, cost, sizing, or management rule.

This is an end-to-end implementation/parity test plus a selection-untouched August 2026 audit. August was not used to select/tune the frozen rules, but some prior labs exposed August as audit-only, so it is **not claimed as pristine unseen OOS**.

## Frozen system
1. Direction: retail-flow SHORT lineage already frozen upstream.
2. Quality router: SHORT only and `HIGH_RESPONSE`, where frozen causal book state is `DRIVEN_MOVE` or `THIN_BOOK` from the LAB041 rolling 90-calendar-day classifier.
3. Classifier thresholds: strictly prior 90 calendar days, current event excluded, minimum 40 prior eligible events; pressure split uses median `abs(fut_netdelta_norm_60)` and response split uses median `fut_disp_atr_60`.
4. Entry: only frozen `ACCEPT` events; enter at `class_time` / `class_price`.
5. Initial stop: `2.5 * ATR14` above SHORT entry.
6. Target: `1.5R` below SHORT entry.
7. Maximum horizon: original `signal_time + 12h`.
8. Parent intrabar ordering: conservative SL-first on an ambiguous M15 bar.
9. Cost screens: 5 bps primary; 0 and 10 bps audit.
10. Post-entry management:
   - identify `ADVERSE_FIRST` only if +0.5R adverse barrier occurs before -0.5R favorable barrier within first 120 minutes after entry; same-bar ambiguity is adverse-first;
   - after ADVERSE_FIRST, `PERSISTENT_FAILURE_FIRST` occurs when 2 consecutive **closed M15 bars** close above frozen level before any closed M15 recovery at/below entry price;
   - intrabar SL/TP exit-bar close is not observable and cannot form persistence;
   - if persistent failure occurs before parent exit, **EXIT NOW at the second confirming M15 close**;
   - otherwise keep frozen parent exit.
11. No re-entry, trailing, break-even, ATR regime filter, extension filter, or WAIT/reacceptance management.
12. Risk screen: 0.25% equity risk per trade only for DD translation; no compounding.

## Reconstruction inputs
The runner must independently reconstruct the LAB041 rolling response state from persisted pre-touch net-flow features, then join frozen LAB035 activation/acceptance data and simulate execution from M15 futures price paths. It must not use LAB043, LAB044, LAB052 or LAB053 state labels to generate the new decisions. Those outputs may only be used for parity comparison.

## Formal pre-Aug parity window
`2021-01-01 <= signal_time < 2026-08-01 UTC`.
Expected frozen lineage:
- HIGH_RESPONSE SHORT original events = 475
- ACCEPT trades = 327
- persistent-failure EXIT NOW trades = 59

Parity target versus frozen LAB053 `PERSISTENT_EXIT` execution:
- same traded flow IDs
- max absolute 5bps net-R error <= 1e-9
- same persistent-exit flow IDs

## Selection-untouched August audit
`2026-08-01 <= signal_time < 2026-09-01 UTC`.
No threshold or policy may be changed after seeing August.
Report:
- HIGH_RESPONSE SHORT events
- ACCEPT trades
- persistent exits
- EV/PF/CumR/DD when defined
- 10bps EV

Fresh-evidence status:
- `ADEQUATE_N` requires >=20 August trades.
- `<20` trades => `INSUFFICIENT_N`; no statistical PASS/FAIL about live profitability.

## Formal gates
Parity / implementation:
1. pre-Aug HIGH_RESPONSE SHORT N == 475
2. pre-Aug ACCEPT trades == 327
3. pre-Aug persistent exits == 59
4. traded flow-ID parity 100%
5. persistent-exit flow-ID parity 100%
6. max abs 5bps net-R parity error <= 1e-9
7. M15 price-path coverage >=99%

Frozen economics:
8. full 5bps EV > 0
9. full PF > 1.10
10. full CumR > 0
11. max DD at 0.25% risk <=4%
12. full 10bps EV > 0
13. 2022 EV/original >= 0
14. 2025H2 EV/original > 0
15. 2026 Jan-Jul EV/original > 0
16. recent pooled EV/original > 0

August evidence:
17. August router events are reported with no selection/tuning
18. August path coverage =100% for eligible trades when any exist
19. August trade count >=20 (`ADEQUATE_N` only; expected may fail)
20. no September / no post-Aug threshold change

## Verdict logic
- `PASS_FULL_SYSTEM_FROZEN_REPLICATION` only if all parity/economic gates pass and August has >=20 trades with positive 5bps EV.
- `WATCH_FULL_SYSTEM_PARITY_PASS_AUG_OOS_INSUFFICIENT_N` if parity and frozen economics pass but August has <20 trades.
- `FAIL_FULL_SYSTEM_PARITY_OR_ECONOMICS` if core parity fails or frozen full-system economics are non-positive.

## Guardrail
This LAB freezes the reused-history SHORT v1 specification. No further post-failure sequence mining is allowed from this lineage. Any next research step must be fresh/native validation, implementation parity, or broker/prop execution validation—not another threshold search on the same sample.
