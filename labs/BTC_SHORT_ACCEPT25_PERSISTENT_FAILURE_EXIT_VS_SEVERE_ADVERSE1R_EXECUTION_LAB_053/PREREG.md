# BTC_SHORT_ACCEPT25_PERSISTENT_FAILURE_EXIT_VS_SEVERE_ADVERSE1R_EXECUTION_LAB_053

## Frozen parent
- Exact pre-August frozen system from LAB044/LAB051: `SHORT HIGH_RESPONSE -> ACCEPT -> SL 2.5 ATR -> TP 1.5R -> original max 12h`.
- Exact traded parent cohort: 327 trades, originating from 475 HIGH_RESPONSE SHORT signals.
- Exact LAB051 `ADVERSE_FIRST` cohort: 145.
- Exact LAB052 `PERSISTENT_FAILURE_FIRST` cohort: 59.
- Reused historical lineage only; not fresh OOS. August is not used for selection.

## Frozen state clocks
After `ADVERSE_FIRST` (+0.5R adverse first within 120m):
- `PERSISTENT_FAILURE_FIRST`: 2 consecutive closed M15 bars above the frozen level before recovery back to/below entry. Exit price is the close of the second confirming M15 bar.
- `SEVERE_ADVERSE_1R`: price reaches entry + 1.0R, where 1R = frozen 2.5 ATR risk distance. This is mechanically the existing parent SL and is therefore a control, not a newly optimized stop.
- If both are timestamped on the same M15 bar, the intrabar Severe +1R barrier takes precedence because it is observable before that bar's close.

## Frozen execution policies
1. `PARENT_HOLD`: exact parent exit.
2. `PERSISTENT_EXIT`: replace parent exit only for exact LAB052 PERSISTENT_FAILURE_FIRST events, at frozen state_time/state_price.
3. `SEVERE_1R_CONTROL`: exact parent logic; expected parity with PARENT_HOLD because Severe +1R equals parent SL.
4. `OCO_PERSISTENT_OR_SEVERE`: after ADVERSE_FIRST, exit at whichever occurs first: persistent-failure confirmation close or Severe +1R barrier. This is the preregistered primary policy.

No entry, response router, ACCEPT rule, stop distance, target, time exit, threshold, re-entry, trailing, breakeven, or sizing is searched.

## Costs and metrics
- Recompute short R from entry to actual policy exit using frozen risk distance.
- Report 0/5/10 bps round-trip cost screens; primary = 5 bps.
- Metrics: EV/trade, PF, CumR, max DD in R, DD at 0.25% risk, EV per original 475 signal, early-exit count, average saved/lost R vs parent.
- Transfer: 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul, BAD_POOLED=2022+2025H1, RECENT_POOLED=2025H2+2026.
- 7-day cluster bootstrap, 5000 draws, on paired trade-level delta `OCO - PARENT`.

## Primary hypothesis
`OCO_PERSISTENT_OR_SEVERE` improves the full parent system because confirmed persistent failure is an earlier causal exit than the existing -1R stop, while recovered/non-adverse trades remain untouched.

## PASS gates
1. exact parent N=327.
2. exact adverse-first N=145.
3. exact persistent-failure N=59.
4. parent 5bps parity to frozen LAB044/LAB051 within 1e-9 per trade.
5. Severe1R control parity to parent within 1e-12 aggregate.
6. OCO early-exit count >=40.
7. OCO full EV > parent EV.
8. OCO full PF > parent PF.
9. OCO CumR > parent CumR.
10. OCO max DD <= parent max DD.
11. OCO EV/original > parent EV/original.
12. OCO-parent paired delta > +0.03R/trade.
13. paired 7d bootstrap lower bound >0.
14. 2022 OCO EV/original >= parent.
15. 2025H1 OCO EV/original >= parent.
16. BAD_POOLED OCO EV/original > parent.
17. RECENT_POOLED OCO EV/original remains >0.
18. 2026 degradation in EV/original is no worse than -0.10R.
19. OCO 10bps EV/trade remains >0.
20. no August selection / no new threshold search.

Formal PASS requires >=17/20 plus gates 7, 9, 13, 16, 17, 19. Otherwise WATCH if full economics improve but proof/transfer is incomplete; FAIL if full economics do not improve.

Live allocation = 0.