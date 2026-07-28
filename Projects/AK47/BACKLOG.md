# AK47 Research Backlog

**Updated:** 2026-07-29

## P1 — AK47_H1_M3_EXIT_CAUSAL_LAB_001

Evaluate M3 on identical baseline entries.

Compare:

- original SL/TP;
- full M3 exit;
- 50% M3 exit + runner;
- 70% M3 exit + runner;
- no new exposure while runner exists;
- eventual TP/SL after M3;
- post-M3 MFE and MAE.

Primary question: does M3 create exit edge or merely rearrange the path?

## P2 — AK47_ENTRY_PROFILE_UNIVERSE_LAB_001

Classify all entries, not only post-M3 entries.

Target taxonomy:

- strong continuation;
- failed breakout reversal;
- two-sided chop;
- exhaustion.

Use H1/M15/M5 state, OCO geometry, approach speed, breakout order, spread, MAE-first/MFE-first and higher-timeframe context.

## P3 — RS001_PERDIR_LOOKBACK_001

Frozen grid:

- ON_LOOKBACK: 50, 75, 100, 150, 200;
- ON_CONFIRM: 5, 7, 10;
- OFF_LOOKBACK: 50, 75, 100;
- BUY and SELL tested independently.

Goal: reduce regime-detection lag without introducing 2022–2023 flip-flops.

## P4 — AK47_XAU_REGIME_BREAK_LAB_001

Explain why performance differs across early and late history.

Features:

- ATR percentile;
- trend persistence;
- H1/H4 directional efficiency;
- range overlap;
- daily range;
- false-break frequency;
- mean-reversion speed;
- BUY/SELL asymmetry.

## P5 — Execution Survival

After a candidate survives OOS:

- spread sweep;
- commission;
- slippage Monte Carlo;
- rollover widening;
- delayed OCO cancellation;
- broker-feed variation;
- VPS latency.

## Closed branches

- fixed post-M3 cooldown;
- same-direction lock;
- opposite structural reset;
- fresh-H1-bar rearm;
- D1-bias cooldown;
- pre-exit 5-bar momentum cooldown;
- auction-rhythm rule `0.50 < pre30_alternation <= 4/7`.
