# BTC_RETAIL_FLOW_ACCEPTANCE_TWO_CLOSE_FAILURE_PERSISTENCE_AND_SURVIVAL_EXECUTION_LAB_029

## Question
Does the LAB028 audit candidate `ORIGIN_CLOSE2` provide a stable causal invalidation rule after frozen retail-flow acceptance, preserving more right-tail than a hard 1.5 ATR stop while maintaining bounded drawdown?

## Frozen lineage
- Exact LAB026 flow stream, expected 3209 rows.
- Exact pre-Aug ACCEPT_FIRST population, expected 1496 trades.
- Entry = frozen +0.5 ATR directional acceptance threshold.
- Direction = frozen Binance retail-flow contrarian side.
- Original time exit = signal_time + 12h.
- Cost = 5 bps round-turn.
- No TP.
- No threshold/horizon/side/calendar optimization.

## Primary invalidation rule
`ORIGIN_CLOSE2`:
After acceptance entry, exit at the close of the **second consecutive completed M15 bar** whose close is back through the original flow-signal price.
- LONG: close <= original signal price for two consecutive M15 bars.
- SHORT: close >= original signal price for two consecutive M15 bars.
- Wick alone does nothing.
- One isolated bad close does nothing; counter resets when a close returns to the valid side.
- If no failure occurs, exit at original signal +12h.

This rule is frozen from the LAB028 audit before LAB029 execution. LAB029 cannot substitute another failure rule after seeing results.

## Benchmarks
1. `HARD_SL15`: exact LAB028/LAB027 1.5 ATR stop from acceptance entry + original 12h time exit.
2. `TIME_ONLY`: no soft/hard exit, original 12h time exit.
3. `ORIGIN_CLOSE1`: LAB028 primary, diagnostic only.

## M1 parity audit
Download frozen `btc_1m.zip` and independently aggregate M1 into M15 OHLC using UTC left-labelled 15-minute bars. On the exact ACCEPT population:
- M15 close parity median relative error <= 1e-8 for available matched bars.
- `ORIGIN_CLOSE2` trigger/no-trigger parity >=99% between native M15 archive and M1-derived M15 closes on matched events.
- trigger-time parity >=99% among events triggered in both streams.
This is an implementation parity audit only; M1 does not alter the trading rule.

## Required reporting
- All pre-Aug economics: EV/trade, policy EV/original flow signal, Cum ATR, PF, DD, trigger rate, median hold.
- Year/windows: 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul; Aug reused audit only.
- LONG/SHORT split.
- 2022 SHORT stress test.
- pooled recent 2025H2 + 2026 Jan-Jul.
- right-tail retention vs TIME_ONLY: cumulative ORIGIN_CLOSE2 / cumulative TIME_ONLY.
- loss avoided: compare losses of triggered vs untriggered states.
- 7-day cluster bootstrap of ORIGIN_CLOSE2 minus HARD_SL15 EV/trade and policy EV/original signal, 5000 draws, fixed seed 20260907.

## PASS gates
1. exact lineage: 3209 total and >=1490 pre-Aug ACCEPT trades.
2. M15/M1 close parity passes.
3. ORIGIN_CLOSE2 trigger parity >=99%.
4. pre-Aug ORIGIN_CLOSE2 EV/trade > 0.
5. pre-Aug ORIGIN_CLOSE2 PF > 1.20.
6. ORIGIN_CLOSE2 EV/trade > HARD_SL15 EV/trade.
7. ORIGIN_CLOSE2 policy EV/original signal > HARD_SL15.
8. ORIGIN_CLOSE2 DD <= 1.20 * HARD_SL15 DD.
9. right-tail retention vs TIME_ONLY >= 55%.
10. 7d bootstrap point difference EV/trade > 0.
11. 7d bootstrap CI lower bound for EV/trade >= -0.05 ATR (non-inferiority tolerance fixed before run).
12. 2022 SHORT: N>=80, cumulative >0, PF>1.25.
13. pooled recent 2025H2+2026 cumulative >0.
14. LONG and SHORT each EV/trade >0.
15. at least 5 of 6 completed pre-Aug subwindows (2021, 2022, 2023, 2024, 2025H1, 2025H2/2026 considered separately = 7 total windows; require >=5 positive) have positive cumulative PnL.

PASS requires >=12/15 plus critical gates 1,4,6,8,12,13. WATCH if >=9/15 with positive overall economics but critical recent or comparative execution fails. Otherwise FAIL.

## Guardrails
- No stop-distance search.
- No profit target search.
- No post-hoc side removal.
- No calendar router.
- August 2026 is reused audit only.
- This remains reused research lineage, not prospective OOS.
- No live allocation; prop/broker execution and full floating daily-DD simulation remain future requirements.