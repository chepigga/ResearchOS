# BTC_RETAIL_FLOW_ACCEPTANCE_POST_CONFIRM_MAE_SURVIVAL_AND_CAUSAL_FAILURE_EXIT_LAB_028

## Question
After frozen retail-flow ACCEPT_FIRST confirmation, which adverse excursions are survivable noise and which causal closed-bar event marks genuine failure before the original +12h exit?

## Frozen lineage
- Exact LAB026 `first_passage_2h.csv`.
- Exact ACCEPT_FIRST definition: first +0.5 ATR directional passage before -0.5 ATR adverse passage, within 2h; same-bar dual hit ambiguous and excluded.
- Exact 3209 frozen flow events; primary survival universe is ACCEPT_FIRST only.
- No change to flow thresholds, side, acceptance threshold, horizon, ATR clock, or costs.

## Entry/clock
- Entry price = original signal close + side * 0.5 * ATR14(M15), the frozen acceptance threshold.
- Entry time = frozen acceptance passage bar.
- Original time exit = signal_time + 12h.
- Price analysis uses completed M15 bars after acceptance; no intrabar ordering guesses.

## Part A — path survival map (descriptive, no trading-rule promotion)
For each ACCEPT trade before Aug-2026 compute from acceptance entry to original +12h exit:
- post-entry MAE and MFE in original-signal ATR units;
- time to maximum MAE/MFE;
- first passage after entry to +0.5, +1.0, +1.5 ATR favorable;
- whether MAE reached >=0.5, >=1.0, >=1.5, >=2.0 ATR;
- final residual 12h return from acceptance entry.

Report survivor rates among eventual residual winners (>0) and losers (<=0) for the fixed MAE bands. These bands are diagnostics only; no stop threshold may be selected from them.

## Part B — frozen causal failure candidates
Primary failure rule, fixed before run:
`ORIGIN_CLOSE1` = after acceptance, first completed M15 close at/beyond the original flow-signal price against the trade direction:
`side * (close - signal_close) <= 0`.
Exit at that M15 close. If it never occurs, exit at original signal +12h.

Audits only (cannot replace primary after results):
1. `ORIGIN_CLOSE2`: two consecutive completed M15 closes at/beyond original signal price; exit second close.
2. `ENTRY_CLOSE2`: two consecutive completed M15 closes back through acceptance-entry price; exit second close.
3. `TIME_ONLY`: no failure exit, original +12h close.
4. `HARD_SL15`: LAB027 fixed 1.5 ATR emergency stop benchmark.

All executable policies use 5 bps round-turn cost. No TP.

## Mechanism tests
For primary ORIGIN_CLOSE1 report:
- failure incidence;
- residual outcome of events that trigger failure vs events that do not;
- how often a mere intrabar wick through origin occurs without a close failure and what its later residual is;
- EV/trade, PF, DD and policy EV/signal versus TIME_ONLY and HARD_SL15;
- by year/window, side, 2022 SHORT, and pooled recent 2025H2 + 2026 Jan-Jul.

## Fixed windows
2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul; Aug-2026 reused audit only.

## Bootstrap
7-calendar-day cluster bootstrap, 5000 draws, seed 20260907. Primary comparison: ORIGIN_CLOSE1 net ATR minus HARD_SL15 net ATR on identical ACCEPT events. Cluster IDs must use explicit elapsed seconds from UTC epoch (not pandas raw datetime integer units).

## Primary gates
1. Exact LAB026 ACCEPT lineage/parity; >=1400 pre-Aug ACCEPT events.
2. Primary ORIGIN_CLOSE1 triggers on >=20% and <=85% of ACCEPT events.
3. Triggered failure events have lower frozen TIME_ONLY residual than non-triggered events by >=0.50 ATR.
4. Wick-through-origin-without-close-failure exists N>=100.
5. Wick-only group frozen TIME_ONLY residual mean > triggered-close-failure residual mean.
6. ORIGIN_CLOSE1 net EV/trade > 0.
7. ORIGIN_CLOSE1 PF > 1.20.
8. ORIGIN_CLOSE1 EV/trade > HARD_SL15 EV/trade.
9. ORIGIN_CLOSE1 DD <= HARD_SL15 DD.
10. 7d bootstrap CI lower bound for ORIGIN_CLOSE1 minus HARD_SL15 EV > 0.
11. 2022 SHORT ORIGIN_CLOSE1 N>=80 and cumulative net ATR > 0.
12. Pooled recent ORIGIN_CLOSE1 cumulative net ATR > 0.
13. LONG and SHORT ORIGIN_CLOSE1 EV/trade both > 0.
14. ORIGIN_CLOSE1 beats TIME_ONLY on DD while retaining >=70% of TIME_ONLY cumulative net ATR.

PASS requires >=11/14 including gates 3,6,8,10,12. WATCH if failure state is strongly discriminative but execution fails one or more critical economics gates. Otherwise FAIL.

## Guardrails
- No stop search or MAE-band promotion.
- No threshold/horizon optimization.
- No H4/price-pattern/calendar router.
- August 2026 cannot affect formal verdict.
- This is reused research lineage, not fresh prospective OOS.
- Live allocation remains 0.