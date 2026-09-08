# BTC_SHORT_ACCEPT25_ADVERSE_FIRST_RECOVERY_VS_PERSISTENT_FAILURE_SEQUENCE_LAB_052

## Frozen parent
- Exact LAB051 `ADVERSE_FIRST` cohort only from frozen `SHORT HIGH_RESPONSE -> ACCEPT -> SL 2.5 ATR -> TP 1.5R -> original max 12h` execution.
- Expected formal pre-August cohort: **145 ADVERSE_FIRST trades**.
- Parent entry, ATR, level, frozen parent exit, costs and payoff are unchanged.
- Reused historical lineage only; not fresh OOS. August is not used for selection.

## Causal sequence clock
State clock starts at the frozen LAB051 `fp_time` when +0.5R adverse first-passage becomes knowable.
Only information strictly after that clock is used.

### RECOVERED_FIRST
First closed M15 bar after `fp_time` with `close <= frozen entry_price`.
This is a causal return through the entry/original short-acceptance price after the adverse excursion.

### PERSISTENT_FAILURE_FIRST
Before RECOVERED_FIRST, two consecutive closed M15 bars after `fp_time` with `close > frozen level`.
The second close is the persistent-failure confirmation clock.

The two states are OCO. If neither state occurs before the frozen parent exit, classify `UNRESOLVED`.
For intrabar parent SL/TP, the close of the exit bar is not observable and is excluded. For TIME exit, the exit close is observable.

## Primary payoff
For each resolved sequence state, compute residual R from the causal state close to the already frozen parent exit:
`residual_r = (state_close - frozen_exit_price) / frozen_risk_dist` for SHORT.
No hypothetical early exit is simulated in LAB052.

Primary comparison:
`RECOVERED_FIRST residual EV - PERSISTENT_FAILURE_FIRST residual EV`.
7-day cluster bootstrap, 5000 draws, frozen seed.

## Secondary diagnostics
- Frozen parent EV by sequence state.
- Sequence resolution latency from ADVERSE_FIRST.
- Severe-adverse diagnostic: whether price reaches +1.0R adverse after ADVERSE_FIRST before recovery. This is audit-only and cannot define the primary state.
- Transfer by 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul.
- `BAD_POOLED = 2022 + 2025H1`.
- `RECENT_POOLED = 2025H2 + 2026 Jan-Jul`.

## Preregistered gates
1. exact LAB051 ADVERSE_FIRST N = 145.
2. path coverage >=99%.
3. sequence resolved N >=60.
4. RECOVERED_FIRST N >=20.
5. PERSISTENT_FAILURE_FIRST N >=20.
6. RECOVERED residual EV >0.
7. PERSISTENT_FAILURE residual EV <0.
8. residual gap >= +0.30R.
9. 7d bootstrap lower 95% bound >0.
10. PERSISTENT_FAILURE frozen parent EV < RECOVERED frozen parent EV.
11. BAD_POOLED persistent residual <0.
12. BAD_POOLED residual gap >0.
13. RECENT_POOLED recovered residual >0.
14. RECENT_POOLED persistent residual <=0.
15. August not used for selection.

## Verdict
- PASS: gates 1-10 all pass and at least 3/4 transfer gates 11-14 pass.
- WATCH: residual ordering is correct (`recovered > persistent`) but PASS conditions incomplete.
- FAIL: no causal residual separation or persistent state is not worse.

## Guardrail
Mechanism/state audit only. No early-exit, stop-tightening, breakeven, trailing, re-entry, allocation, or new threshold is promoted here. Live allocation = 0.
