# LAB073 — CF191g MARKET vs CONFIRM CAUSAL STATEFUL

## Why this LAB exists
LAB072 found an apparent large advantage for MARKET_SIGNAL, but that comparison used the frozen universe of signals that later passed canonical confirmation. Therefore MARKET_SIGNAL was conditioned on future confirmation and cannot be promoted.

LAB073 removes that hindsight.

## Frozen inputs
- BTCUSDT CrowdFade Z source and price history identical to canonical CF191g.
- Z threshold 1.00.
- Same M5 signal clock.
- Same max 3 trades/day.
- Same ATR pause distance 1.0 ATR after prior filled trade.
- Same signal ATR snapshot.
- Historical: 2021-2025.
- Forward shadow/stress: Mar-Aug 2026.

## Two causal state machines

### MARKET_RAW
When a fresh eligible |Z|>=1 signal appears while flat and passes the frozen pause/day rules, enter immediately after that M5 bar closes.
No future confirmation information is used.

### CONFIRM_CANONICAL
Use the frozen CF191g confirmation logic:
- +0.30 ATR favorable confirmation
- max 45m
- max adverse 0.75 ATR before confirm
- crowd sign still on original side
- |Z| at confirmation >=0.75
- response ratio >=0.50
Then enter immediately after the confirmation M5 bar closes.

Each method runs its OWN causal occupancy / next-signal reachability. No shared post-hoc event universe.

## Standardized management
Execution comparator only:
- SL = 1.5 ATR
- TP = 3.0 ATR = 2R
- max hold = 6h
- conservative SL-first if both touched in same 1m bar.

This does not replace CF191g positive-skew production management.

## Costs
Same frozen broker models as LAB072:
- IC: 0.597376 bps median spread, 0 commission, 0.684253 bps median BTC stop slippage.
- GetLeveraged: 2.643809 bps median spread, 0 commission, 0.291636 bps median BTC stop slippage.
- Gross diagnostic also reported.

## Promotion
MARKET_RAW is a valid execution candidate only if versus CONFIRM_CANONICAL it has:
1. higher or equal EV, PF, and R/DD in 2021-25 and 2026 under both IC and GetLeveraged costs;
2. positive SumR in every historical year under both broker cost models;
3. no MaxDD_R > 1.5x confirmation in either period;
4. at least 200 trades in 2026 shadow/stress.

No parameter tuning after result.
