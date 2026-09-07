# BTC_RETAIL_FLOW_DIRECTION_TO_PRICE_LOCAL_EXTREME_ENTRY_INDEPENDENT_OF_H4_DIRECTION_LAB_023

## Question
Does the frozen Binance retail-flow directional signal become economically stronger when price is used only for causal local-extreme timing, with no H4 directional agreement requirement?

## Frozen direction lineage
- Exact persisted LAB022 `flow_only_nonoverlap.csv`.
- Assert exact row count = 3209.
- `side=+1` LONG and `side=-1` SHORT are frozen by LAB022's causal trailing-90d q20/q80 contrarian `count_long_short_ratio` rule.
- Flow observations are already non-overlapping by >=12h. No flow threshold is re-estimated or tuned in LAB023.
- H4 direction/context is not read anywhere in LAB023.

## Price data / clock
- Exact frozen Binance BTCUSDT M15 price archive used in LAB022, SHA256 `19acf95a3bb7a868fa1e6c8da8dbc73d4a2f7004b771e394bbee8e6c5b6e58b9`.
- ATR14 = causal SMA true range on completed M15 bars.
- Entry/timing decisions use completed bars only.

## Primary local-extreme trigger — SWEEP_RECLAIM_4
For each frozen flow event at time `t0`, search bars `t0+1 ... t0+48` (12h) and take only the first trigger.

FLOW SHORT (`side=-1`):
1. `level = max(high[k-4:k])` from the four completed M15 bars before candidate bar k.
2. Current `high[k] > level` (upward liquidity sweep / local high).
3. Current `close[k] < level` (reclaim back below swept level).
4. Current `close[k] < open[k]` (bearish confirmation).

FLOW LONG (`side=+1`) is exact mirror:
1. `level = min(low[k-4:k])`.
2. `low[k] < level`.
3. `close[k] > level`.
4. `close[k] > open[k]`.

Entry = candidate M15 close. No limit offset and no H4 gate.

## Primary execution
- Emergency SL = 1.5 × ATR14(M15) from entry.
- No take-profit.
- TIME EXIT = close exactly 12h (48 M15 bars) after entry.
- Stop is scanned starting on the first bar after entry close.
- Cost = 5 bps round-turn, converted to ATR units at entry.
- One trade maximum per frozen flow event.

## Baseline — immediate flow entry
Same frozen flow events, same side, same SL1.5ATR/no-TP/TIME12h/cost, but entry at flow-event M15 close. This is the direct test of whether price timing improves the same directional signal.

## Preregistered audits (cannot rescue primary)
1. `EXTREME4_COLOR`: new 4-bar high/low plus candle closing in FLOW direction, without requiring reclaim through the swept level.
2. `PIVOT2X2_CONFIRMED`: causal 2-left/2-right local pivot; entry only when the second right bar has closed, in FLOW direction. No future-known pivot at entry.
3. Primary SWEEP_RECLAIM_4 with no stop, TIME12h only.
4. Primary SWEEP_RECLAIM_4 with TIME24h instead of TIME12h, diagnostic only.

## Windows
- 2021
- 2022 bearish stress test
- 2023
- 2024
- 2025 H1
- 2025 H2
- 2026 Jan-Jul
- Aug 2026 reused audit
- ALL_PRE_AUG = 2021 through 2026-07-31
- POOLED_RECENT = 2025-07-01 through 2026-07-31

## Primary hypothesis
`FLOW direction + causal local-extreme timing` should improve the same frozen FLOW stream by reducing adverse excursion / stop-outs while preserving positive directional drift.

## Primary gates
1. Frozen flow lineage parity: exactly 3209 events.
2. SWEEP_RECLAIM_4 trigger coverage >=30% pre-Aug.
3. Primary pre-Aug trades N >= 700.
4. Primary mean net ATR > 0.
5. Primary PF > 1.20.
6. Primary mean net ATR >= immediate-flow mean net ATR + 0.10 ATR.
7. Primary stop rate <= immediate stop rate - 10 percentage points.
8. 2022 SHORT branch N >= 40 and cumulative net ATR > 0.
9. SHORT pooled pre-Aug mean > 0 and positive cumulative net ATR in >=4 of 5 full years 2021-2025.
10. LONG pooled pre-Aug mean > 0.
11. POOLED_RECENT primary cumulative net ATR > 0.
12. Primary no-stop TIME12 audit mean net ATR > 0.

PASS requires >=9/12 and critical gates 1,2,3,4,5,6,8. WATCH if direction remains positive but local-extreme trigger only partially improves execution. Otherwise FAIL.

## Guardrails
- No H4 direction, H4 score, H4 regime or calendar regime filter.
- No flow cutoff search.
- No local-extreme lookback search.
- No stop, horizon, target, side-specific threshold or time-window optimization.
- Audits cannot be promoted inside LAB023.
- August 2026 is reused/consumed audit only.
- Live allocation remains 0.