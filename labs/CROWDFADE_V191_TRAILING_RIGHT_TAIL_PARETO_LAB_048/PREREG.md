# LAB048 — V191_TRAILING_RIGHT_TAIL_PARETO

Status: PRE-REGISTERED BEFORE EXECUTION

## Frozen strategy state

Use the exact LAB046-supported / LAB047-control V191 lane.

Entry / signal / gating:
- BTCUSDT only
- v191 contrarian crowd signal: |Z| >= 1.00
- confirmation move = 0.30 ATR against crowd
- confirmation freshness <= 45m
- original v191d confirmation-side consistency
- cancel if max pre-confirm adverse excursion > 0.75 ATR
- skip RAPID_REPEAT<=30m
- skip causal HIGH_VOL
- pause = 1.0 ATR
- max trades/day = 3
- flat research cost proxy = 0.5 bps

Frozen management except trailing:
- SL = 1.50 ATR
- fixed TP = OFF
- BE arm = +0.50 ATR
- BE lock = +0.15 ATR
- ExitZ = 0.75
- max hold = 6h

No entry threshold, gate, SL, BE, ExitZ, hold, cost or day-cap change is allowed in LAB048.

Every variant MUST be replayed chronologically/statefully from raw data.
A trailing change may alter exit time, occupancy and later signal reachability.

## Mechanistic trailing grid

The grid is fixed before execution and is not derived from individual LAB047 winner paths.

Anchors:
1. CONTROL_A2P5_G0P5
   - trail arm = +2.5 ATR
   - trail gap = 0.5 ATR
2. TRAIL_OFF
   - trailing disabled

Delayed-arm family, original gap:
3. A3P5_G0P5
   - arm = +3.5 ATR
   - gap = 0.5 ATR
4. A5P0_G0P5
   - arm = +5.0 ATR
   - gap = 0.5 ATR

Wider-gap family, original arm:
5. A2P5_G1P0
   - arm = +2.5 ATR
   - gap = 1.0 ATR

Delayed + wider:
6. A3P5_G1P0
   - arm = +3.5 ATR
   - gap = 1.0 ATR
7. A5P0_G1P0
   - arm = +5.0 ATR
   - gap = 1.0 ATR

No extra arm or gap values may be added after results are observed.

## Immutable reference
V192_CANONICAL_CONTROL is replayed unchanged on the common research frame.

## Samples

Historical:
- 2021-01-01 through 2025-12-31
- BTCUSDT 1-minute OHLC execution frame

Forward shadow/stress:
- 2026-03-01 through 2026-08-31
- BTCUSDT second OHLC execution frame

2026 is reused shadow/stress, not pristine OOS.

## Required metrics

For every trailing variant and v192:
- N
- WR
- EV
- PF
- SumR
- MaxDD_R
- R/DD
- max consecutive losses
- median / p90 hold minutes
- exit-reason counts
- historical yearly metrics
- 2026 monthly metrics
- full chronological trade ledger
- matched stateful reachability delta vs control

Right-tail diagnostics:
- max trade R
- top-1, top-5 and top-10 positive trade SumR
- gross positive SumR
- top-1 / gross-positive share
- top-5 / gross-positive share
- top-10 / gross-positive share
- total SumR with largest 1 trade removed
- total SumR with largest 5 trades removed
- total SumR with largest 10 trades removed
- period sign after removing each period's single best trade
- count of positive historical years after per-year top-1 removal
- count of positive 2026 months after per-month top-1 removal

## Pre-registered interpretation

Base robustness:
- aggregate EV > 0 and PF > 1 in BOTH historical and 2026;
- >=4/5 positive historical years;
- >=4/6 positive 2026 months;
- frequency >= 90% of CONTROL in both samples.

A variant is PARETO_ELIGIBLE only if it satisfies base robustness AND:
- historical MaxDD <= TRAIL_OFF historical MaxDD from the same replay;
- 2026 MaxDD <= TRAIL_OFF 2026 MaxDD from the same replay;
- forward top-1/gross-positive concentration <= TRAIL_OFF;
- forward top-5/gross-positive concentration <= TRAIL_OFF;
- it improves at least one of SumR or R/DD versus CONTROL in at least one sample without being worse than CONTROL on BOTH SumR and R/DD in the other sample.

ROBUST_PARETO is a stricter label:
- PARETO_ELIGIBLE;
- >=3/5 historical years remain positive after removing each year's best trade;
- >=3/6 forward months remain positive after removing each month's best trade;
- aggregate SumR remains >0 after removing the top 5 trades in BOTH samples.

TRAIL_OFF remains a diagnostic anchor and is not production-promoted even if it meets metrics.

No single "winner" may be selected only by maximum EV.
Report the Pareto trade-off across:
- SumR
- R/DD
- MaxDD
- frequency
- right-tail concentration
- trimmed robustness

## Guardrail

LAB048 may establish whether delayed/wider trailing preserves more right-tail edge than the current 2.5/0.5 trail at tolerable risk.

It does NOT authorize production promotion.
Any new dynamic/adaptive trail or any combination with other exit changes requires a separate preregistered LAB.
