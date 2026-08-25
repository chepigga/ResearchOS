# STRUCT_BREAK_POST_ENTRY_RESPONSE_STATE_MACHINE_LAB_008 — Preregistration

Date: 2026-08-25
Status: PREREGISTERED

## Objective
Test whether post-entry price response contains causal information that improves trade management even when pre-entry direction is weak.

## Canonical population
STRUCT_BREAK v002, BTCUSDT, 2019-09-08..2025-12-31 for formal DEV/VAL. 2026 shadow only.

DEV: 2019-09..2022-12
VAL: 2023-01..2025-12

## Exact reconstruction
Entry = broken M15 pivot-3 level (`lvl`).
Stop = last confirmed opposing M15 pivot-5.
Risk unit R = abs(lvl-stop).
Canonical cost = 0.06R round-turn.

Reconstruction must reproduce stored `riskATR` and `gap` to numerical tolerance before analysis.

## Data clocks
Primary: canonical Binance BTCUSDT 5m archive over full DEV/VAL.
Replication: canonical BTCUSDT 1m archive where available (2024+), used only as higher-resolution confirmation.

## Causal observation rule
The fill bar itself is not used for post-entry features because the exact within-bar order before/after the limit touch is unknown. Observation begins from the next fully closed lower-timeframe bar after the first bar that touches `lvl`.

## Fixed observation horizons
5m, 15m, 30m, 60m, 120m after the first usable post-fill bar.

## Fixed response features
At each horizon:
- NET_R: mark-to-market directional return from entry
- MFE_R
- MAE_R
- path efficiency
- directional close fraction
- velocity = NET_R / elapsed time
- MFE velocity
- fraction of closes back through broken level
- observed range expansion vs pre-entry 30m
- aligned taker imbalance where present

## Primary question
For trades still alive at each horizon, compare:

HOLD value = canonical final R
EXIT-NOW value = NET_R - 0.06R
HOLD_ADVANTAGE = final_R - EXIT_NOW_R

A state supports early exit if HOLD_ADVANTAGE is negative on both DEV and VAL with useful N.

## Fixed diagnostic state grid
No optimized threshold search.

At each horizon evaluate economic MFE bands:
- < 0.10R
- 0.10..0.25R
- 0.25..0.50R
- >= 0.50R

And fixed candidate rules:
A) MFE < 0.25R
B) MFE < 0.25R AND NET_R <= 0
C) MFE < 0.50R AND NET_R <= 0
D) MFE < 0.25R AND MAE >= 0.25R

All horizon/rule combinations are diagnostics. Candidate selection is DEV-only. The selected candidate is then frozen and reported on VAL separately.

## Primary promotion gate
A candidate adaptive exit is promoted only if:
- improves EV versus canonical on DEV and VAL;
- VAL improvement >= +0.05R/trade;
- does not worsen VAL max drawdown;
- improves or preserves at least 2 of 3 VAL calendar years;
- affected VAL N >= 50;
- no 2026 information used for selection.

## State-machine interpretation
IMPULSE: positive progress / high efficiency; default HOLD.
STALL: insufficient progress without hard structural failure; candidate EXIT + RE-ARM.
FAILURE: strong adverse response; EXIT, setup may be cancelled in later work.

LAB008 does NOT optimize re-entry. Re-entry is a separate follow-up after an early-exit rule survives VAL.
