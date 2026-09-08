# BTC_SHORT_ACCEPT25_POST_ENTRY_FIRST_PASSAGE_AND_EARLY_FAILURE_STATE_LAB_051 — PREREG

## Frozen parent
- Exact frozen parent: LAB044 `SHORT HIGH_RESPONSE -> ACCEPT -> SL 2.5 ATR -> TP 1.5R -> signal_time+12h`, 5 bps execution accounting.
- Formal universe: exact **327** traded ACCEPT2.5 rows with `signal_time < 2026-08-01 UTC`.
- No entry, stop, target, time-exit, ATR, flow, response, level, or pre-entry filter is changed.
- Same Binance USD-M BTCUSDT M15 lineage used by LAB035/LAB044.

## Causal post-entry clock
- Entry bar is excluded. Only M15 bars with timestamp `> entry_time` are observable.
- Early observation window: first **120 minutes after entry**, censored at the already-frozen parent exit if it occurs earlier.
- Parent risk distance `D = 2.5 * ATR14` frozen at the original entry.

## Primary first-passage state
For SHORT:
- `FAVORABLE_FIRST`: price first reaches `entry_price - 0.5D`.
- `ADVERSE_FIRST`: price first reaches `entry_price + 0.5D`.
- `NONE_120`: neither barrier is reached within 120 minutes before parent exit.
- If both +/-0.5R barriers are touched in the same M15 bar, classify **ADVERSE_FIRST** (conservative ordering).
- State time is the first M15 bar where the corresponding barrier is reached.

## Primary outcome: post-state residual
To avoid mechanical/tail leakage from using the already-realized +/-0.5R move itself:
- `residual_r = (state_price - frozen_parent_exit_price) / D` for SHORT.
- This measures continuation/recovery **after** the causal state is known, to the unchanged frozen parent exit.
- No new transaction cost is charged to this diagnostic residual because no new trade is opened at the state clock.
- Frozen parent final `net_r_5bps` remains an audit metric only.

## Early reclaim diagnostics
Using the frozen LAB035 activation `level`:
- `RECLAIM1`: first post-entry M15 close strictly above `level` within 120m before frozen exit.
- `RECLAIM2`: two consecutive post-entry M15 closes strictly above `level` within 120m before frozen exit. State clock is the second close.
- Reclaim residual is measured from the causal reclaim close to frozen parent exit, normalized by `D`.
- No reclaim exit rule is promoted in this LAB.

## Early path diagnostics
For each frozen trade, before frozen exit:
- MFE and MAE in R units over first 60m.
- MFE and MAE in R units over first 120m.
- minutes to +/-0.5R first passage when resolved.

## Frozen transfer slices
- 2021, 2022, 2023, 2024, 2025_H1, 2025_H2, 2026_JAN_JUL.
- `BAD_POOLED = 2022 + 2025_H1`.
- `RECENT_POOLED = 2025_H2 + 2026_JAN_JUL`.
- August 2026 may be audited only and is not used for selection.

## Statistics
- 7-day time-cluster bootstrap, 5000 draws, cluster clock = entry_time.
- Primary contrast: mean residual `FAVORABLE_FIRST - ADVERSE_FIRST`.
- Secondary: adverse-first share by frozen period; RECLAIM2 residual; full frozen parent outcome by state.

## Gates
1. Exact frozen parent N=327.
2. Parent path coverage >=99%.
3. First-passage resolved N>=100.
4. FAVORABLE_FIRST N>=40.
5. ADVERSE_FIRST N>=40.
6. FAVORABLE residual mean >0.
7. ADVERSE residual mean <0.
8. FAVORABLE-ADVERSE residual gap >=+0.30R.
9. 7d bootstrap lower bound of residual gap >0.
10. BAD_POOLED residual gap >0.
11. RECENT_POOLED residual gap >0.
12. RECLAIM2 N>=20.
13. RECLAIM2 residual mean <0.
14. RECLAIM2 frozen-parent final EV < non-RECLAIM2 final EV.
15. August not used for selection.

## Verdict
- `PASS_POST_ENTRY_EARLY_FAILURE_STATE` if gates 1-11 and 15 pass, plus at least 2 of reclaim gates 12-14.
- `WATCH_EARLY_PATH_DISCRIMINATIVE_PROOF_INCOMPLETE` if primary residual gap >0 but PASS is not met.
- `FAIL_NO_POST_ENTRY_EARLY_FAILURE_STATE` if primary residual gap <=0 or ADVERSE residual is not below FAVORABLE residual.

## Guardrail
Mechanism/state audit only. No early exit, breakeven, trailing, stop tightening, re-entry, or allocation rule is searched or promoted here. Reused historical lineage; not fresh OOS. Live allocation = 0.
