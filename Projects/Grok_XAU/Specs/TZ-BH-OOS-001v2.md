# TZ-BH-OOS-001v2

**Date:** 2026-07-24  
**Project:** Grok XAU  
**Laboratory:** BH_OOS_001  
**Status:** PREREGISTERED / FROZEN BEFORE RUN  
**Causality:** causal bar-close oracle; no future features in signal formation

## 1. Objective

Out-of-sample validation of `BH_SWEEP` on 2026-05..07 using the exact same oracle engine that produced the in-sample verdict.

## 2. Frozen engine

MorrisCandle V2 + EMA20, using the 2026-07-05 backlog configuration without changes:

- timeframe: XAUUSD M15;
- fractal depth: 5;
- maximum swing age: 96 bars;
- sweep: breach of an unconsumed swing followed by reclaim-close beyond the level on the same bar;
- a swing is consumed by its first breach;
- BeltHold must occur within no more than 3 bars;
- BeltHold body: at least `0.60 × candle range`;
- opposite wick: no more than `0.05 × candle range`;
- signal candle must reclaim-close beyond the swept level;
- EMA20 reversal context: BUY only below EMA20; SELL mirrored above EMA20;
- entry: market entry under the original frozen oracle convention;
- stop: extreme over `[sweep..signal] ∓ 0.25 × ATR14(M15)`;
- target: 2R;
- time stop: 96 M15 bars, closed at the actual price and expressed in R.

No tuning, reinterpretation or post-hoc parameter change is allowed.

## 3. Data

- symbol/timeframe: XAUUSD M15;
- required export with warmup: 2024-12-01 through 2026-07-23;
- OOS test window: 2026-05-01 through 2026-07-23;
- source: the same broker feed used for the in-sample result;
- prior M5/M15 slice ended on 2026-04-21 and is insufficient;
- changing feed between in-sample and OOS invalidates this experiment.

## 4. Costs

Apply a net correction of `-0.05R per trade`, representing the conservative edge of the SMC backlog convention for approximately 30–35 points spread plus $4 round-turn commission.

## 5. Step 0 — mandatory reproduction control

Before opening the OOS window, run the frozen engine on the original in-sample fixture.

Expected control:

- trades: `N=88`;
- BUY: `52`;
- SELL: `36`;
- EV: `+0.276R` exactly.

Permitted drift:

- `|ΔN| <= 2`;
- `|ΔEV| <= 0.02R`;
- drift must be documented with a concrete cause.

If either tolerance is exceeded:

- verdict: `CONTROL_FAIL`;
- stop the laboratory;
- localise pipeline/data/engine drift before any OOS calculation.

## 6. Step 1 — OOS run

- window: 2026-05-01 00:00 through 2026-07-23 end-of-day;
- frozen parameters only;
- no tuning or sample-aware exclusions;
- net result uses `R_net = R_gross - 0.05` for every trade.

## 7. Pre-registered verdict

### PASS

`N >= 8` and `EV_net >= 0`.

Consequence: `InpBH_Enable=true` is permitted on demo only, followed by one forward month. Live remains prohibited.

### FAIL

`N >= 8` and `EV_net < 0`.

Consequence: BH is permanently disabled in this form and entered into the falsified catalogue.

### INCONCLUSIVE

`N < 8`.

Consequence: blocker remains; repeat after two additional months of data accumulation without changing parameters.

### Near miss

Near-miss treatment is forbidden unless a separate NM1–NM4 protocol is preregistered and approved.

## 8. Required artifacts

1. Control run summary: N, EV, BUY/SELL split and drift diagnosis if any.
2. OOS trades CSV with columns:
   - `time`
   - `dir`
   - `entry`
   - `SL`
   - `exit_time`
   - `exit_reason` (`TP`, `SL`, `TIMESTOP`)
   - `R`
3. Monthly breakdown for May, June and July 2026.
4. Final report with formal verdict and data/code hashes.

## 9. Current execution blockers recorded at preregistration

- exact frozen oracle code/config package unavailable;
- original in-sample fixture unavailable;
- fresh same-feed XAUUSD M15 export unavailable;
- supplied `Grok_Core_XAU.mq5` is unrelated to the frozen BH engine and cannot be substituted.
