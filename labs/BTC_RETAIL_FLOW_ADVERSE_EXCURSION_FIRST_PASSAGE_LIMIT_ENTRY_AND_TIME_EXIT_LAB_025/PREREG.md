# BTC_RETAIL_FLOW_ADVERSE_EXCURSION_FIRST_PASSAGE_LIMIT_ENTRY_AND_TIME_EXIT_LAB_025

## Question
Can the known contrarian Binance retail-flow direction be monetized more efficiently by using a passive adverse-excursion limit instead of entering immediately, while keeping the original 12h forecast horizon and avoiding price-pattern filters?

## Frozen lineage
- Exact persisted LAB022 non-overlapping flow stream: `flow_only_nonoverlap.csv`.
- Expected event count: **3209**.
- Side is frozen from LAB022 (`+1 LONG`, `-1 SHORT`).
- No H4 direction/context and no LAB023/LAB024 price-pattern filters are used.
- Frozen Binance BTCUSDT M15 price archive and ATR14 convention from LAB023/024.

## Signal and passive order mechanics
At each flow signal close `t0`:
- `P0` = M15 close at `t0`.
- `ATR0` = ATR14(M15) known at `t0`.
- For adverse depth `d`, limit price is `P0 - side * d * ATR0`.
  - LONG => buy limit below P0.
  - SHORT => sell limit above P0.
- Order becomes active only after the signal close; first eligible bar is `t0 + 15m`.
- Search until the original forecast horizon `t0 + 12h` inclusive.
- First bar whose low/high reaches the limit is the first-passage fill.
- Fill price is exactly the frozen limit price; no market fallback.
- If never touched by `t0+12h`, the order expires and contributes **0** to policy PnL.

## Frozen depths
- **PRIMARY: 1.0 ATR**.
- Sensitivity only: 0.5 ATR, 1.5 ATR, 2.0 ATR.
- No depth may be selected or retuned after results.

## Primary exit
- No TP.
- No stop in the primary mechanism-isolation test.
- Exit at the M15 close exactly `t0 + 12h` (the original flow forecast horizon), regardless of fill time.
- Cost: fixed 5 bps round-turn in price terms.
- If fill occurs on the final horizon bar, exit uses that bar close.

## Bounded audit
For each depth, also run an emergency stop at **1.5 ATR0 from the fill price**, still with no TP and same `t0+12h` time exit.
Conservative same-bar rule: if the fill bar touches both the limit and the emergency stop after the limit would be reachable, count STOP; M15 cannot resolve intrabar sequencing.

## Required comparisons
For each depth report:
1. fill rate per original signal;
2. median/mean fill delay;
3. EV per filled trade;
4. **policy EV per original signal** = total net PnL / all eligible original flow signals, with unfilled = 0;
5. matched immediate-entry PnL on the exact subset that later filled;
6. incremental execution benefit vs matched immediate;
7. post-fill MAE/MFE to the original 12h horizon;
8. bounded stop-touch rate and bounded EV;
9. LONG/SHORT split;
10. yearly 2021..2026 and 2022 SHORT stress test.

## Key scientific distinction
A passive limit can show a high EV per fill simply because it selects signals with large adverse excursions. The primary policy metric is therefore **EV per original signal**, not EV per fill. Matched-immediate comparison is required to separate better entry price from selection effects.

## Windows
- 2021
- 2022 bearish stress
- 2023
- 2024
- 2025 H1
- 2025 H2
- 2026 Jan-Jul
- Aug 2026 reused audit only
- ALL_PRE_AUG and POOLED_RECENT.

## Primary gates (1.0 ATR depth)
1. exact frozen flow lineage = 3209 and timestamp parity >=99%.
2. pre-Aug eligible signals >=3000.
3. pre-Aug 1.0ATR fill rate >=35%.
4. primary no-stop policy EV per original signal > immediate no-stop policy EV per original signal.
5. primary no-stop policy EV per original signal >= +0.10 ATR.
6. matched-filled limit EV exceeds matched-immediate EV by >= +0.50 ATR/fill.
7. primary no-stop total pre-Aug cumulative ATR > 0.
8. primary bounded 1.5ATR-stop policy EV per original signal > 0.
9. primary bounded PF on filled trades >1.20.
10. primary bounded stop-touch rate <=60%.
11. 2022 SHORT primary no-stop Nfill>=60 and policy cumulative ATR >0.
12. 2022 SHORT primary bounded cumulative ATR >0.
13. LONG and SHORT primary no-stop policy EV per original signal are both >0 pre-Aug.
14. recent 2025H2+2026 primary no-stop policy EV per original signal >0.
15. sensitivity is not a single-point spike: at least two of 0.5/1.5/2.0 ATR have positive pre-Aug no-stop policy EV per original signal.
16. August 2026 reused audit is reported but cannot rescue or fail the primary verdict.

PASS requires >=12/15 evaluative gates (1-15) and critical gates 1,3,4,5,7,8,11,14. WATCH if primary improves matched entry but misses policy-level robustness/fill-rate gates. Otherwise FAIL.

## Guardrails
- No optimized depth, TTL, stop, TP, or side-specific threshold.
- No price-pattern trigger.
- No calendar/regime filter.
- Original flow 12h horizon is preserved.
- Reused research lineage, not fresh prospective OOS.
- Live allocation remains **0**.