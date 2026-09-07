# BTC_RETAIL_FLOW_ACCEPTANCE_CONFIRM_ENTRY_AND_ADVERSE_VETO_EXECUTION_LAB_027

## Question
Does the frozen LAB026 early-acceptance discriminator survive a bounded executable policy with costs, while adverse-first events are vetoed?

## Frozen lineage
- Exact persisted LAB026 `first_passage_2h.csv`.
- Flow lineage: exact 3209 frozen retail-flow events from LAB022/LAB023.
- Primary first-passage state is frozen: within 2h after flow signal, +0.5 ATR in flow direction before -0.5 ATR => ACCEPT_FIRST; reverse ordering => ADVERSE_FIRST; same M15 bar hit of both => AMBIGUOUS and no trade; neither => NONE and no trade.
- No threshold/horizon/side optimization.

## Primary executable policy
- Trade only `ACCEPT_FIRST`.
- Entry side = frozen flow side.
- Market entry price = exact +0.5 ATR acceptance threshold from the original signal close.
- Entry timestamp = frozen LAB026 passage timestamp.
- Emergency SL = 1.5 ATR14(M15) below/above the acceptance entry, using the ATR frozen at original flow signal.
- No TP.
- Time exit = original flow signal time + 12h, not entry time +12h.
- Cost = 5 bps round-turn expressed in ATR units and charged once per executed trade.
- Conservative bar resolution: after entry, if stop is touched in a bar before the time exit, stop wins. The acceptance bar itself is eligible for stop only after acceptance; because intrabar ordering after the threshold is unknowable from M15 OHLC, if the acceptance bar also touches the post-entry SL, mark `ENTRY_BAR_AMBIGUOUS` and exclude from the primary executable PnL; report it separately. No optimistic ordering.

## Diagnostic audits
1. Same ACCEPT_FIRST entries with no emergency stop, same original +12h time exit and 5 bps cost.
2. Immediate flow entry at signal close, same 1.5 ATR emergency stop, same +12h exit and 5 bps cost.
3. Immediate flow entry with no stop, same +12h exit and 5 bps cost.
4. ADVERSE_FIRST remains veto/zero-risk; no reverse trading.

## Economic accounting
Report both:
- EV per executed trade/fill.
- Policy EV per original eligible flow signal, with veto/ambiguous/no-trade = 0.
Also report cumulative ATR, PF, max DD in ATR, stop rate, median holding time, and signal utilization.

## Windows
- 2021
- 2022 bearish stress test
- 2023
- 2024
- 2025 H1
- 2025 H2
- 2026 Jan-Jul
- Aug 2026 reused audit only
- ALL_PRE_AUG
- POOLED_RECENT = 2025H2 + 2026 Jan-Jul

## Side audits
- LONG and SHORT separately pre-Aug.
- 2022 SHORT separately.

## Cluster robustness
- Fixed 7-calendar-day clusters.
- 5000 bootstrap draws, seed 20260907.
- Bootstrap primary bounded ACCEPT policy EV per original signal and compare against bounded immediate-flow policy EV on the same eligible signal lineage.

## Primary gates
1. Exact LAB026 lineage/parity: 3209 total events, >=3000 pre-Aug, timestamp/threshold parity.
2. ACCEPT executable count >=1000 pre-Aug after excluding entry-bar ambiguity.
3. Signal utilization >=35% pre-Aug.
4. Primary bounded ACCEPT EV/trade > 0.
5. Primary bounded ACCEPT PF > 1.20.
6. Primary bounded ACCEPT policy EV/signal > 0.
7. Primary bounded ACCEPT policy EV/signal > bounded immediate-flow policy EV/signal.
8. Primary bounded ACCEPT max DD <= bounded immediate-flow max DD.
9. No-stop ACCEPT EV/trade > 0.
10. 2022 SHORT bounded ACCEPT N>=80 and cumulative net ATR >0.
11. POOLED_RECENT bounded ACCEPT cumulative net ATR >0.
12. LONG bounded ACCEPT EV/trade >0.
13. SHORT bounded ACCEPT EV/trade >0.
14. 7d cluster bootstrap lower 95% bound for (ACCEPT bounded policy EV/signal - immediate bounded policy EV/signal) >0.
15. Aug2026 reused audit reported but cannot rescue/fail the scientific verdict.

PASS_EXECUTION if gates 1-14 score >=11 and critical gates 1,2,4,6,10,11 pass.
WATCH if the no-stop acceptance edge survives but bounded execution fails one or more critical economics gates.
FAIL otherwise.

## Guardrails
- No TP search.
- No stop-distance search.
- No first-passage threshold search.
- No market fallback for vetoed events.
- No H4 direction or price-pattern filter.
- No calendar regime rescue.
- August 2026 is consumed/reused audit only.
- This is reused research lineage, not fresh prospective OOS.
- Live allocation remains 0.