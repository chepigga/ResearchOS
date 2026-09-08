# BTC_SHORT_PERSISTENT_FAILURE_EXIT_NOW_VS_REACCEPTANCE_OCO_LAB_054

## Objective
Final post-failure decision test on the frozen SHORT core. Compare immediate exit at the already-proven `PERSISTENT_FAILURE_FIRST` clock versus waiting for one fixed causal OCO resolution. No signal, entry, SL, TP, time-exit, regime filter, sizing, or threshold search is allowed.

## Frozen parent
- Universe: exact 327 `SHORT HIGH_RESPONSE -> ACCEPT` trades from LAB044/LAB053, pre-2026-08-01 only.
- Parent execution: SL 2.5 ATR, TP 1.5R, frozen original max-12h horizon, 5 bps primary costs; 10 bps stress.
- Exact LAB052 `ADVERSE_FIRST` cohort: 145.
- Exact LAB052 `PERSISTENT_FAILURE_FIRST` cohort: 59.
- `EXIT_NOW` is exactly LAB053 `PERSISTENT_EXIT`.

## Frozen WAIT_REACCEPT_OCO policy
Only after the causal `PERSISTENT_FAILURE_FIRST` close is known:
1. Start observing from the **next M15 bar**; the confirmation bar's intrabar high/low may not be reused.
2. `REACCEPT`: first subsequent closed M15 bar with `close <= frozen entry_price`. If this occurs first, cancel the failure-exit logic and revert to the frozen parent hold/exit.
3. `FAILURE_EXTENSION_025`: adverse price reaches `persistent_state_price + 0.25R`, where `1R = frozen risk_dist = 2.5 ATR`. If this occurs first and before the frozen parent exit, exit at that barrier.
4. Same subsequent bar ambiguity: intrabar `FAILURE_EXTENSION_025` has priority over close-based REACCEPT because the barrier is observable before the close.
5. The frozen parent SL/TP/TIME remains active at all times. If the +0.25R extension level is beyond the frozen parent SL, the parent SL necessarily wins.
6. If neither OCO branch resolves before parent exit, use the frozen parent exit.

No alternative reaccept definition, extension size, number of closes, or clock is tested.

## Policies
- `PARENT_HOLD`
- `EXIT_NOW` = immediate exit at persistent confirmation (LAB053)
- `WAIT_REACCEPT_OCO` = frozen OCO above

## Primary comparisons
1. Full-sample economics: EV/trade, PF, CumR, max DD, EV/original signal, 10bps EV.
2. Paired `WAIT_REACCEPT_OCO - EXIT_NOW` delta in R/trade with 7-day cluster bootstrap, 5000 draws.
3. Secondary paired `WAIT_REACCEPT_OCO - PARENT_HOLD` delta.
4. Transfer: 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul, BAD_POOLED=(2022+2025H1), RECENT_POOLED=(2025H2+2026).
5. OCO attribution counts: REACCEPT, EXTENSION_EXIT, UNRESOLVED/PARENT.

## PASS gates
- exact parent N=327, adverse N=145, persistent N=59; path coverage >=99%.
- EXIT_NOW parity with LAB053 <=1e-9 R.
- OCO resolves at least 30 of 59 persistent events and both REACCEPT and EXTENSION branches have N>=10.
- WAIT full EV > EXIT_NOW; PF > EXIT_NOW; CumR > EXIT_NOW; max DD <= EXIT_NOW.
- paired WAIT-EXIT delta >0 and 7d bootstrap lower bound >0.
- 2026 WAIT EV/original > EXIT_NOW EV/original.
- BAD_POOLED WAIT EV/original >= EXIT_NOW - 0.02R/original.
- RECENT_POOLED WAIT EV/original positive.
- WAIT 10bps EV positive.
- no August 2026 selection and no new threshold search.

Formal PASS requires all critical parity/causality gates, positive full economics, positive paired bootstrap proof, and transfer guardrails. Otherwise WATCH if economics improve but proof/transfer is incomplete; FAIL if WAIT does not improve EXIT_NOW.

## Guardrail
Reused historical lineage, not fresh OOS. This LAB ends recursive post-failure management research: no further sequence refinement is promoted from this sample unless LAB054 clearly fails due to a pre-specified mechanical ambiguity. Live allocation = 0.