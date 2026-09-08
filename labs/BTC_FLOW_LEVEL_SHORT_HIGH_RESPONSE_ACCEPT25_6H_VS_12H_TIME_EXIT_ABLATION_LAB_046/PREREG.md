# BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_ACCEPT25_6H_VS_12H_TIME_EXIT_ABLATION_LAB_046

## Purpose
Test whether shortening the frozen LAB044 SHORT HIGH_RESPONSE -> ACCEPT execution horizon improves bounded economics without changing signal selection, entry, stop, target, or cost assumptions.

## Frozen lineage
- Source execution parent: LAB044 persisted branch/output.
- Formal universe: exact pre-Aug 2026 HIGH_RESPONSE SHORT events from LAB043, with ACCEPT-only entry eligibility exactly as LAB044.
- Entry: frozen LAB035 class_time close / class_price on ACCEPT.
- SL: 2.5 x frozen ATR14.
- TP: 1.5R.
- Costs: 5 bps RT primary; 0 and 10 bps sensitivity.
- Same Binance USD-M BTCUSDT M15 path lineage.
- August 2026 audit-only.

## Fixed time-exit policies
1. PRIMARY `ENTRY_PLUS_6H`: horizon = ACCEPT entry_time + 6h. This is the direct interpretation of max holding time 6h.
2. AUDIT `SIGNAL_PLUS_6H`: horizon = original FLOW signal_time + 6h. If ACCEPT occurs after this horizon, no trade.
3. PARITY `SIGNAL_PLUS_12H`: horizon = original FLOW signal_time + 12h, reproducing LAB044 primary ACCEPT2.5 policy.

No other horizon is tested. No threshold/entry/SL/TP optimization.

## Path ordering
Exactly LAB044 guardrail: ACCEPT enters at class_time close, so barrier testing begins on the next M15 bar. Any later bar that touches both SL and TP is counted SL-first. If neither barrier is hit by the fixed horizon, exit at that horizon close.

## Metrics
- eligible/traded count;
- TP/SL/time-exit shares;
- 0/5/10bps EV in R;
- PF, cumulative R, max DD R and DD at 0.25% risk;
- EV per original HIGH_RESPONSE signal;
- median holding hours;
- yearly/period transfer 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul, pooled recent, August audit.

## Primary gates for ENTRY_PLUS_6H
1. parent formal HIGH_RESPONSE N=475 and ACCEPT traded N=327;
2. regenerated SIGNAL_PLUS_12H matches LAB044 ACCEPT2.5 trade count and net EV within 1e-9;
3. M15 path coverage >=99%;
4. ENTRY_PLUS_6H net EV >0;
5. ENTRY_PLUS_6H PF >=1.10;
6. ENTRY_PLUS_6H EV/original >= +0.05R;
7. ENTRY_PLUS_6H 10bps EV >0;
8. DD at 0.25% <=4%;
9. 2025H2 EV/original >0;
10. 2026 EV/original >0;
11. pooled recent EV/original >0 with >=50 original signals;
12. ENTRY_PLUS_6H EV/original not worse than SIGNAL_PLUS_12H by >0.05R;
13. ENTRY_PLUS_6H PF not worse than SIGNAL_PLUS_12H by >0.10;
14. August not used for selection.

## Verdict
- PASS if >=12/14 and critical gates 1,2,3,4,5,6,7,8,9,10,11 pass.
- WATCH if ENTRY_PLUS_6H stays positive but loses meaningful edge versus 12h, or if SIGNAL_PLUS_6H differs materially from ENTRY_PLUS_6H.
- FAIL otherwise.

## Guardrail
This is reused historical execution research, not fresh OOS and not live authorization.
