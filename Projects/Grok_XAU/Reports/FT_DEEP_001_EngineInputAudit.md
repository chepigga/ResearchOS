# FT_DEEP_001 — Engine and input audit

**Date:** 2026-07-25  
**Status:** PREREGISTERED / BLOCKED_FULL_M5_AND_PARITY_FIXTURE

## Frozen contract

- Source: `AK47_FT_EA_156.mq5`
- Source SHA256: `838b3e180a139008c69792c0f122f3da66a590ef5e6ee98056056f0938311b65`
- Specification SHA256: `8438dd2b8affeedb882cfd18e1ae9a0e17077337dbacd90c8de9df24afa5bd8c`
- Modules: NYBUY + LONBUY only
- Parameters: v1.56 defaults, no tuning
- Portfolio gates: excluded
- Cost: -0.05R/trade

## Recovered exact implementation details

- M5 state machines: IDLE -> RAIDED -> RECLAIM -> ENTRY.
- `InpUseFTFilter=false`, therefore `HasFTImpulse()` is a no-op.
- `HTFAllowBuy = H4 bias BULL and D1 bias not BEAR`.
- Bias uses custom EMA50 with 200-bar seed warmup, 3-bar slope and 0.03 ATR threshold.
- Sell-side levels, touch clustering, per-level daily dedup and same-bar reclaim are present.
- NYBUY empirical quality corridor and London empirical H1/touches/reclaim gates are present.
- TP is 5R and source entry trigger is reclaim-high + one point.

## Available M5 input

- File: `XAUUSD_M5.csv`
- SHA256: `cd2e3285c0e4660786a019999fb3e746257c2cbd4d400fe48092cdbbc7760a80`
- Rows: `95,466`
- First bar: `2025-01-01 23:00:00`
- Last bar: `2026-04-21 23:45:00`
- Approximate depth: `15.61` months

This is below the frozen 24-month minimum and lacks the 200-D1 warmup before
2023-01-01. It cannot support GO/REGIME/NO-GO.

## Step 0 reference state

Historical `AK47_v154b_oracle_outcomes.csv` provides a candidate-level diagnostic
basket and the `NYSELL_OFF` reconstruction reports 25 accepted NYBUY+LONBUY
signals for the older 2026-H1 run. The frozen Step 0 target remains tester
156-1: NYBUY N=17, LONBUY small sample, N tolerance +/-2 per module and at
least 80% entry-time matching within one M5 bar.

The exact tester 156-1 entry list is not available in the active runtime.
Therefore trade-time parity is not claimed.

## Decision

Do not open the deep verdict. Export the complete same-feed M5 interval
2022-06-01..2026-07-23, then rerun Step 0 before the 42-month analysis.
