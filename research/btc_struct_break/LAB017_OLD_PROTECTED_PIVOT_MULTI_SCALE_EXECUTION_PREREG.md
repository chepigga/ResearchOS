# OLD_PROTECTED_PIVOT_MULTI_SCALE_EXECUTION_LAB_017 — PREREGISTRATION

Date: 2026-08-25

## Goal
Test whether the positive old-protected-pivot lineage from LAB016 is real but under-sampled because M15 execution is too coarse.

Frozen positive context from LAB016:
- riskATR > 3.72
- protected pivot age >= 22 M15 bars (~5.5h)
- pivot must be causally confirmed and unviolated before entry
- 2026 excluded from all verdicts

## Branches

### A. M15->M15 CONTROL
Exact canonical STRUCT_BREAK v002 trades only. Keep trades satisfying the frozen LAB016 rule above. No recomputation/retuning. Canonical management: TP 2.3R, BE after +1R, cost 0.06R.

### B. M15 protected pivot -> M5 break/retest (PRIMARY)
Context/stop anchor is the latest causally confirmed M15 pivot-5 on the trade side:
- BUY anchor = last confirmed M15 pivot low
- SELL anchor = last confirmed M15 pivot high
- age >=22 M15 bars at M5 entry
- anchor unviolated since confirmation
- structural stop distance from M5 entry to M15 anchor, normalized by last closed M15 ATR14, must be >3.72

M5 execution is fixed and symmetric:
- pivot-3 microstructure
- BUY: confirmed pivot high followed by confirmed pivot low, then close >= pivot-high + 0.10*ATR14(M5)
- SELL: symmetric
- retest of broken pivot within next 12 M5 bars, no same-break-bar fill
- entry = broken M5 pivot level
- stop = M15 protected pivot anchor (not a new M5 stop)
- one entry maximum per M15 anchor per direction
- TP = 2.3R, BE after +1R, adverse same-bar ordering, 0.06R cost
- max hold = 6000 M5 bars (=2000 M15 bars)

### C. M5 protected pivot -> M5 break/retest (SCALE-PRESERVING)
Same M5 execution as Branch B.
Anchor/stop = latest causally confirmed M5 pivot-5.
Primary age threshold = 66 M5 bars (~5.5h, same wall-clock age as 22 M15 bars).
- anchor unviolated since confirmation
- riskATR = entry-to-anchor distance / ATR14(M5) >3.72
- one entry maximum per M5 anchor per direction
- same TP/BE/cost/hold logic as Branch B.

### C2. M5 age>=22 bars diagnostic only
Same as C but age >=22 M5 bars (~110m). This is explicitly secondary and cannot promote the mechanism on its own.

## Portfolio treatment
First evaluate event-level outcomes for every valid candidate. Then construct chronological one-position portfolios separately per branch: if a candidate fills while a prior branch trade is still open, skip it. No pyramiding.

## Metrics
For each branch and split/year:
- N, trades/year
- EV R/trade and bootstrap 95% CI
- PF
- TP/BE/SL rates
- total R
- MaxDD in R
- BUY/SELL diagnostics
- cost stress at 1.0x / 1.25x / 1.5x of 0.06R by subtracting incremental cost from fixed outcomes

## Promotion logic
Primary Branch B is interesting only if:
1. VAL 2023-2025 N >= 40
2. VAL EV > 0 and at least 2/3 VAL years positive
3. VAL PF > 1.20
4. EV remains >0 at 1.5x cost
5. frequency is materially higher than M15 control (>=2x trades/year)
6. no single VAL year contributes >60% of total positive R

Branch C additionally requires the same sign DEV->VAL and at least 2/3 VAL years positive.

No threshold optimization is permitted in this LAB.