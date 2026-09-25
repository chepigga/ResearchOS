# GC_XAU LAB023A — MIX2_BUY_BOTH_IMP5_EXECUTION_TRANSFER — PREREG

Date frozen: 2026-09-25

## Parent lineage
- LAB022 final commit: dc612d762770d17a156a362059e303d2b5a892c0
- Recovery STATE_014: 5e5c242c70b7a934fa8d1e81890b76e315b2a22e
- Parent signal object: MIX2_BUY_BOTH_HTF_IMP5_001

## Signal — FROZEN / MUST NOT CHANGE
An event is eligible iff all are true:
- Broad causal label = MIX2
- side = BUY
- causal H1 trend = UP/aligned
- causal H4 trend = UP/aligned
- causal pre-entry XAU 5m impulse > 0

No leg, side, EMA length, slope horizon, trend state, impulse horizon, threshold, cooldown, or GC signal semantic may be retuned in LAB023A.

Chronological split remains:
- TRAIN = W1-W5
- VALID = W6-W7
- POST = W8-W9

## Price source / clock
- Massive C:XAUUSD M1 quote aggregates
- UTC only
- reference market minute = ceil(signal t0 to next exact minute, with exact-minute t0 kept exact
- ATR14 = SMA(True Range) over 14 completed XAU M1 bars immediately preceding the reference minute
- H1/H4 are UTC aggregates of completed M1 bars only
- EMA20 trend convention is inherited from LAB019/022

## Execution families

### MKT
Immediate market entry at reference minute open.

### CONF_CLOSE
Within the next 5 completed M1 bars after the reference minute, wait for the first bar whose close is above the frozen reference market open. Enter at the next M1 open. If none, no trade.

### CONF_PREHIGH
Within the next 5 completed M1 bars after the reference minute, wait for the first bar whose close is above the high of the last completed pre-entry M1 bar. Enter at the next M1 open. If none, no trade.

### LIMIT_A025 / LIMIT_A050 / LIMIT_A075
BUY limit below the frozen reference market open by:
- 0.25 ATR
- 0.50 ATR
- 0.75 ATR

Pending lifetime = 5 minutes from the reference minute.
Because Massive M1 quote aggregates do not provide a historical Bid/Ask pair for every bar, use conservative trade-through fill:
M1 low <= limit_price - 0.10 XAU, where 0.10 is half the frozen 0.20 XAU spread.
No fill => no trade.

## Risk / targets / holds
Signal ATR is frozen at t0 and is not recomputed to favor delayed entries.

For every filled execution:
- 1R stop distance = 2.25 * frozen ATR14
- SL is 1R below actual transaction entry
- TP grid = 1.5R and 2.0R only
- max hold after fill = 5m / 10m / 15m
- exact M1 first-passage path
- if SL and TP are both touched in the same M1 bar, SL wins
- for a limit fill bar, same-bar SL is allowed; same-bar TP is NOT credited because fill-vs-high ordering is unknowable

No BE, trailing, partial TP, averaging, martingale, grid, or re-entry is introduced.

## Costs — FTMO XAU operational model
Observed Broad forward history implies commission = $6 per 1.00 lot round-turn.
With XAU contract size 100 oz, this is 0.06 XAU price-distance equivalent per round trip.

Base:
- spread = 0.20 XAU round trip
- commission = 0.06 XAU round trip
- slippage = 0.02 XAU per market side
- market/confirmation entry: 0.02 adverse entry slippage + 0.02 adverse exit slippage
- limit entry: no adverse entry slippage beyond the limit cap; 0.02 adverse exit slippage

Stress:
- same spread/commission
- slippage = 0.05 XAU per market side

Costs are embedded in transaction prices / net PnL, not used to alter the frozen signal.

## TRAIN selection rule
OOS execution outcomes stay sealed until the execution candidate is frozen.

A candidate cell is eligible for OOS only if on TRAIN:
- entered/fill N >= 300
- execution rate >= 50% of frozen eligible parent events
- aggregate base-cost net EV > 0
- base-cost PF > 1.05
- at least 3 of 5 TRAIN windows have positive net EV

Among eligible cells:
1. maximize median TRAIN-window net EV;
2. tie-break by lower sequential MaxDD;
3. then higher aggregate net EV.

The exact winning execution family + parameter cell is frozen before VALID/POST is opened.

If no candidate passes, LAB023A is an execution-transfer FAIL and OOS is reported only for the already-exposed MKT baseline, not mined for a rescue.

## Required report
For every TRAIN cell:
- eligible N
- entered N / execution rate
- net EVR / PF / SumR / MaxDD
- WR / SL rate / TP rate / timeout rate
- W1-W5 EV
- base and slippage-stress economics

For the frozen winner only:
- VALID and POST N / execution rate
- net EVR / PF / SumR / MaxDD
- W6/W7/W8/W9 EV
- base + stress costs
- comparison vs inherited immediate-market baseline

Passing is research evidence only. It does not authorize EA/Broad Demo/Q65 changes.
