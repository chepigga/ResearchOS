# XAU_POST_TOUCH_RETEST_REACCELERATION_IFVG_CAUSAL_LAB_006 — Spec v001

**Status:** PREREGISTERED / HOLDOUT_SEALED  
**Date:** 2026-08-23  
**Parents:** LAB002 → LAB003 → LAB004 → LAB005

## Source-derived execution hypothesis

The podcast does not present VWAP as a standalone entry. Its concrete entry examples combine location/context with an inverse fair-value-gap model: **“get an inversion → come back → wick into this gap → close below/above → entry.”** It also explicitly says VWAP alone should not be traded without other confluences.

LAB006 therefore changes exactly one dimension from LAB005: after a causal VWAP retest has formed, require evidence that the original post-touch direction has **re-accelerated**, and measure whether a causal direction-aligned iFVG adds incremental selection value.

## Question

Can the adverse-selection problem discovered in LAB005 be reduced by distinguishing a healthy pullback from a broken impulse using only information available after the retest and before entry?

Primary hypothesis:

`T+3 sequence signal → VWAP role-flip retest → renewed displacement → aligned iFVG evidence → next-M1-open entry`

If this cannot produce positive executable economics with transfer, the podcast-style iFVG confirmation does not rescue the frozen post-touch sequence under this causal formulation.

## Canonical data / embargo

- canonical input: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- frozen LAB005 candidate universe: `XAU_POST_TOUCH_SEQUENCE_RETEST_ENTRY_CAUSAL_LAB_005/v001/candidates_T3.csv.gz`
- Discovery: decision time `< 2024-01-01`
- Confirmation: `2024-01-01 <= decision_time < 2025-07-01`
- sealed holdout: `>= 2025-07-01`

No post-holdout price bars or events may be read for the reported verdict.

## Frozen parent signal / retest

LAB006 does not change LAB005's parent lifecycle:

- primary decision clock: `T+3`
- directional threshold: `|s3| >= 0.10 ATR_touch`
- BACK direction = arrival side; THROUGH direction = opposite arrival side
- retest window: T+4 through T+18 (15 minutes)
- retest zone: dynamic original VWAP level ± `0.05 ATR_touch`
- retest confirmation close: at least `+0.03 ATR_touch` on intended side
- first qualifying retest only

The frozen LAB005 candidate file supplies `decision_i`, `dir`, `atr0`, `retest_confirm_i`, branch, split, and LAB002 label lineage. LAB006 independently validates canonical timestamps/index lineage before use.

## New dimension A — causal re-acceleration

After LAB005 retest-confirmation bar `j`, observe at most the next **5 completed M1 bars**, `j+1 ... j+5`.

The first bar `k` is a **REACCEL** confirmation if all are true using only completed-bar information:

1. directional progress from the retest-confirmation close:
   `d * (Close[k] - Close[j]) / ATR_touch >= +0.10`
2. directional real body:
   `d * (Close[k] - Open[k]) / ATR_touch >= +0.05`
3. close remains beyond the contemporaneous touched dynamic level on intended side:
   `d * (Close[k] - Level[k]) / ATR_touch >= +0.05`

If no such bar appears within five minutes, REACCEL is absent.

No optimization of 5m, 0.10, 0.05, or level-hold threshold is allowed in LAB006.

## New dimension B — causal aligned iFVG evidence

Use the same frozen standard M1 iFVG construction used earlier in the XAU research line:

- bullish FVG completed at bar `i` if `Low[i] > High[i-2]`, zone `[High[i-2], Low[i]]`
- bearish FVG completed at bar `i` if `High[i] < Low[i-2]`, zone `[High[i], Low[i-2]]`
- source FVG lifetime for inversion: maximum 240 M1 bars
- bullish FVG becomes bearish iFVG on first completed close below its lower edge
- bearish FVG becomes bullish iFVG on first completed close above its upper edge
- after inversion, first zone revisit within 30 M1 bars that closes back in the inverted direction is the causal iFVG confirmation event
- same minute/direction duplicates: narrowest gap, then oldest source

An iFVG is **ALIGNED** for a LAB006 setup if its confirmed event direction equals trade direction `d` and its confirmation time lies inside the local setup window:

`max(decision_i, retest_confirm_i - 5) <= ifvg_confirm_i <= reaccel_i`

This is deliberately local; stale iFVGs from far earlier in the session do not count.

## Frozen branches

All branch definitions are fixed before canonical outcomes:

1. **PRIMARY_BOTH** — retest exists, REACCEL exists, and local ALIGNED iFVG exists by the REACCEL close.
2. **REACCEL_ONLY** — retest + REACCEL, irrespective of iFVG. Pre-registered ablation.
3. **IFVG_ONLY** — retest + local aligned iFVG within 5 minutes after retest confirmation, irrespective of REACCEL. Pre-registered ablation.
4. **RETEST_BASELINE** — frozen LAB005 retest entry. Diagnostic parent comparator only.

Primary entry is at the **next contiguous M1 open after the REACCEL confirmation bar**:
- BUY = AskOpen
- SELL = BidOpen

For IFVG_ONLY ablation, entry is next contiguous M1 open after aligned iFVG confirmation.

No intra-bar fill assumptions.

## Economics

Unchanged from LAB005 to isolate the health filter:

- `1R = 0.50 * ATR_touch` from actual entry
- hard stop = 1R
- primary TP = 1.5R
- secondary TP = 2.0R
- max hold = 60 minutes from entry
- BUY exits use future Bid OHLC
- SELL exits use future Ask OHLC
- same-M1 TP+SL = conservative LOSS
- no hit = executable quote at horizon, clipped to `[-1,targetR]`

Costs unchanged:
- spread embedded through Bid/Ask
- commission proxy = `$5 round-turn/lot` = `$0.05` XAU price equivalent
- stress: additional `$0.05` and `$0.10` price-equivalent round trip

## Primary serial lifecycle

Primary deployability = `PRIMARY_BOTH / T+3 / 1.5R / BASE` with one lifecycle at a time.

1. chronological parent T+3 signals;
2. same decision minute: strongest `abs(s3)` per direction, tie `MID > HIGH > LOW`;
3. if simultaneous LONG and SHORT remain, skip conflict;
4. when flat, accept next signal and enter PENDING_RETEST;
5. ignore all other signals during 15m retest window;
6. if retest occurs, continue into PENDING_HEALTH for max 5m;
7. if PRIMARY_BOTH health does not qualify, become flat after health-window expiry;
8. if qualifies, enter next contiguous M1 open after REACCEL;
9. hold one position until TP/SL/time exit; ignore later signals;
10. no hedging, pyramiding, averaging, martingale.

REACCEL_ONLY and IFVG_ONLY serial portfolios are pre-registered diagnostics, not primary selection rules.

## Diagnostics

Report for Discovery and Confirmation:

- parent eligible / retest-filled / health-pass counts and rates;
- PRIMARY_BOTH, REACCEL_ONLY, IFVG_ONLY signal correctness versus frozen LAB002 `label_0p5`;
- correctness of rejected-by-health parent retests;
- health-selection uplift in percentage points;
- median wait from decision → retest → health → entry;
- entry deterioration/improvement versus LAB005 retest entry in ATR;
- 1.5R and 2R EV, PF, TP rate, total R;
- BUY/SELL and BACK/THROUGH EV;
- yearly transfer;
- max DD, worst day, max consecutive losses;
- cost stress;
- serial frequency;
- paired same-signal `LAB006_R - LAB005_retest_R` and `LAB006_R - LAB004_market_R`.

## Frozen bootstrap

Calendar-week cluster bootstrap:
- 4000 resamples
- seed `20260823`

Primary intervals:
- Confirmation serial mean R
- same-signal PRIMARY_BOTH minus LAB005 retest-entry R
- correctness uplift of PRIMARY_BOTH pass versus health-fail parent retests

## Frozen gates

Primary = Confirmation / PRIMARY_BOTH / T+3 / 1.5R / serial / BASE.

- `G0_DATA_EXECUTION`: canonical SHA valid, AskOpen/AskHigh/AskLow/AskClose present, holdout false.
- `G1_PRIMARY_POWER`: Confirmation serial PRIMARY_BOTH trades >= 300 and >= 15 trades/week.
- `G2_CONFIRMATION_EV`: Confirmation EV > 0 and PF > 1.0.
- `G3_WEEK_CLUSTER_CI`: lower 95% weekly cluster CI of Confirmation mean R > 0.
- `G4_SPLIT_TRANSFER`: Discovery and Confirmation primary EV both > 0.
- `G5_2R_SURVIVAL`: Confirmation primary 2R EV >= 0.
- `G6_DIRECTION_BREADTH`: Confirmation BUY EV > 0 and SELL EV > 0.
- `G7_BRANCH_BREADTH`: Confirmation BACK EV > 0 and THROUGH EV > 0.
- `G8_PROP_DD_PROXY`: max DD <= 20R and worst day > -16R.
- `G9_COST_STRESS`: 1.5R EV remains > 0 under additional $0.10 price-equivalent stress.
- `G10_HEALTH_SELECTION`: PRIMARY_BOTH correctness exceeds rejected-by-health retest correctness by >= +5 percentage points in both Discovery and Confirmation.
- `G11_IFVG_INCREMENTAL`: Confirmation PRIMARY_BOTH EV >= REACCEL_ONLY EV and PRIMARY_BOTH correctness >= REACCEL_ONLY correctness, with PRIMARY_BOTH N >= 300.

## Verdicts

- `GO_TO_REPLICATION`: all G0..G11 pass.
- `REACCEL_EDGE_IFVG_NOT_INCREMENTAL`: G0..G10 pass except G11.
- `NARROW_HEALTH_SUBSET`: G2/G3/G4/G10 pass but power/breadth/stress/DD gate fails.
- `HEALTH_FILTER_IMPROVES_BUT_NOT_PROFITABLE`: G10 passes but G2 fails.
- `NO_REACCEL_IFVG_EXECUTABLE_EDGE`: G2 and G10 fail or no robust transfer.
- `INVALID_EXECUTION_DATA`: G0 fails.

No automatic holdout opening or live/EA allocation.

## Anti-overfit

LAB006 does not optimize after outcomes:
- parent T+3 ±0.10 state rule;
- LAB005 15m retest lifecycle;
- 5m post-retest health window;
- reacceleration thresholds 0.10 / 0.05 / 0.05 ATR;
- iFVG lifetime 240m / retest 30m / local setup window;
- 0.50 ATR stop;
- 1.5R / 2R targets;
- 60m hold;
- costs;
- MID/HIGH/LOW, BUY/SELL, BACK/THROUGH subsets;
- session/news/volatility filters.

If LAB006 fails, later work must change one explicit causal dimension in a new preregistered LAB.
