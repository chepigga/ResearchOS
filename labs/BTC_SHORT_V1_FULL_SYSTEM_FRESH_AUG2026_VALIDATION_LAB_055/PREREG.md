# BTC_SHORT_V1_FULL_SYSTEM_FRESH_AUG2026_VALIDATION_LAB_055

## Frozen system
No parameter, threshold, feature, entry, stop, target, time-exit, or management change is allowed.

Pipeline:
1. Binance retail FLOW direction = SHORT.
2. Frozen LAB041 causal book state, collapsed exactly as LAB043:
   - HIGH_RESPONSE = DRIVEN_MOVE or THIN_BOOK.
   - LOW_RESPONSE = ABSORPTION or WEAK.
3. Trade only SHORT HIGH_RESPONSE.
4. Require frozen level state = ACCEPT.
5. Entry = ACCEPT class close.
6. SL = 2.5 ATR14.
7. TP = 1.5R.
8. Horizon = signal_time + 12h.
9. Conservative same-M15-bar ordering: SL before TP.
10. Post-entry management:
   - ADVERSE_FIRST = +0.5R adverse first within 120m.
   - after ADVERSE_FIRST, recovery = first M15 close <= entry price;
   - PERSISTENT_FAILURE = 2 consecutive closed M15 bars > frozen level before recovery;
   - EXIT NOW at the second persistent-failure close.
   - otherwise retain frozen parent SL/TP/time exit.
11. Costs: report 0/5/10 bps; primary 5 bps.
12. Risk diagnostic: 0.25% equity risk/trade.

## Validation design
- Reused lineage: signal_time < 2026-08-01. Must reproduce LAB053 EXIT_NOW economics within numerical tolerance.
- Fresh OOS: 2026-08-01 <= signal_time < 2026-09-01. August has not been used for selection in LAB043-054.
- Use only causal rolling states already frozen by LAB041. August observations may use strictly-prior rolling history but may not alter any frozen rule.
- No minimum August sample is invented post hoc. Report exact N and label inference weak if N<20 signals or N<10 trades.

## Primary full-system gates
1. pre-Aug original HIGH_RESPONSE SHORT N = 475.
2. pre-Aug ACCEPT trades N = 327.
3. pre-Aug EXIT_NOW early exits N = 59.
4. pre-Aug 5bps EV parity vs LAB053 <= 1e-9 R/trade.
5. pre-Aug CumR parity vs LAB053 <= 1e-6 R.
6. pre-Aug PF parity vs LAB053 <= 1e-6.
7. pre-Aug DD parity vs LAB053 <= 1e-6 R.
8. fresh August pipeline coverage >=99% for eligible trades.
9. fresh August HIGH_RESPONSE signal count reported exactly.
10. fresh August ACCEPT trade count reported exactly.
11. fresh August 5bps EV/trade > 0.
12. fresh August PF > 1.0.
13. fresh August CumR > 0.
14. fresh August EV/original signal > 0.
15. fresh August 10bps EV/trade > 0.
16. fresh August DD at 0.25% risk <= 4%.
17. full through-Aug 5bps EV/trade > 0.
18. full through-Aug PF >= 1.15.
19. full through-Aug DD at 0.25% <= 4%.
20. no August selection / no threshold changes.

## Verdict
- PASS_FRESH_OOS: all parity/coverage gates plus August gates 11-16 pass.
- WATCH_FRESH_OOS_SMALL_N: August N is small but economics positive; no strong proof claim.
- FAIL_FRESH_OOS: August economics negative or parity/causality fails.

This is the frozen SHORT v1 validation. No further post-failure sequence refinement is permitted from this reused lineage.