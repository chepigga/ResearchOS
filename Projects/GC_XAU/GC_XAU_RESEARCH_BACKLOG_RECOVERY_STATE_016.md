# GC_XAU_RESEARCH_BACKLOG_RECOVERY_STATE_016

Updated: 2026-10-03

## PURPOSE

Canonical freeze / backlog checkpoint immediately before EA implementation.

This state supersedes STATE_015 for active development, but does NOT delete or rewrite prior history.

Do not restart discovery.
Do not reuse invalid LAB004-LAB009 execution conclusions.
Do not mix this branch with CrowdFade / crypto / BTC AEIF.

---

## 1. CORE RESEARCH STATUS

### Structural signal
PASS.

GC multi-horizon aggressive order flow around active XAU M15 structural extremes contains robust information.

### Clock parity
Mandatory UTC normalization remains required.

Historical XAU raw broker timestamps were UTC+3.
Correct conversion:
`broker time - 3h = UTC`.

Old LAB004-LAB009 execution/regime profitability remains INVALID.

### Preferred structural timeframe
M15.

M30 remained materially less stable OOS.

---

## 2. FINAL SIGNAL UNIVERSE FOR EA

### REVERSAL UNIVERSE

Frozen expansion:

`M15 active structural extreme + crowd support >= 6/7 at contact + support drop >=3 votes within 5m`

This replaces the older exact 7/7-only reversal requirement.

Rationale:
6/7 + collapse retained strong reversal quality and materially increased signal frequency.

Measured structural reversal rates for COLLAPSE:

- 7/7:
  - TRAIN ~70.1%
  - VALID ~61.7%
  - POST ~65.5%

- 6/7:
  - TRAIN ~70.0%
  - VALID ~83.3%
  - POST ~85.0%

Combined 5-7/7 collapse:
- TRAIN ~70.6%
- VALID ~69.1%
- POST ~70.3%

EA freeze uses **6/7+**, not 5/7, to avoid unnecessary dilution before demo.

### CONTINUATION UNIVERSE

Persistence branch remains strict.

Use:
`7/7 persistence + XAU breakout acceptance`

Do NOT weaken persistence to 6/7 before demo.

Important:
Persistence alone is NOT a SELL signal.
It only enables the continuation branch.
XAU acceptance is still required.

---

## 3. ASYMMETRIC EXECUTION ARCHITECTURE

The system is intentionally NOT mirror-symmetric.

BUY and SELL have different path behavior.

### BUY reversal behavior

BUY signals often show:
- valid structural reversal
- possible initial adverse movement
- delayed confirmation
- different winner/loser path geometry from SELL

Three BUY execution states are preserved.

---

## 4. BUY_A_RESILIENT

Structural source:
`6/7+ COLLAPSE reversal candidate`

Execution pattern:
- pre-confirmation adverse excursion must remain limited
- XAU must respond positively quickly

Frozen execution:
- pre-confirmation MAE <= 0.25 ATR
- +0.4 ATR response within <=3 minutes
- entry at next M1 open
- SL = 2 ATR
- TP = 3R
- max hold = 30 minutes

Own qualification context:
`prior 15m return >= -0.102%`

Interpretation:
Do not buy resilient reversal when XAU is already in a strong short-term sell impulse.

Historical qualified-state sample:
- total ~50 trades in final 6/7+ pipeline

---

## 5. BUY_B_RECLAIM

Structural source:
`6/7+ COLLAPSE reversal candidate`

Execution pattern:
- initial adverse excursion allowed
- price must reclaim instead of continuing lower

Frozen execution concept:
- adverse excursion >=0.25 ATR but <=1.25 ATR
- reclaim to >= +0.10 ATR from signal reference within 10m
- SL = 2 ATR
- TP = 2R
- max hold = 45m

Own qualification context:
`M1 ATR14 / price >= 0.0662%`

Interpretation:
Reclaim branch needs sufficient short-horizon volatility.

Historical qualified-state sample:
- total ~46 trades in final 6/7+ pipeline

---

## 6. BUY_C_LATE

Structural source:
`6/7+ COLLAPSE reversal candidate`

Execution pattern:
- neither A nor B triggered
- later stabilization / delayed reversal

Frozen execution concept:
- after minute 4
- two consecutive higher M1 closes
- price back above signal reference
- trigger allowed within 15m
- SL = 2 ATR
- TP = 1.5R
- max hold = 60m

Own qualification context:
`prior 30m range / price >= 0.2843%`

Interpretation:
Late reversal works only when there is enough prior local expansion.

Historical qualified-state sample:
- total ~37 trades in final 6/7+ pipeline

---

## 7. SELL_PERSISTENCE_ACCEPT

Structural source:
`strict 7/7 persistence`

Execution pattern:
Continuation only after XAU proves acceptance through the lower extreme.

Frozen acceptance:
- crowd remains persistent
- XAU closes at least 0.25 ATR below the lower extreme
- acceptance within next 2 M1 bars
- entry at next M1 open
- structural SL = 0.75 ATR above extreme
- TP = 1.5R
- max hold = 60m

Own qualification context:
`prior 30m range / price >= 0.4285%`

Interpretation:
Continuation SELL requires stronger expansion than BUY reversal branches.

Historical qualified-state sample:
- total ~102 trades in final 6/7+ pipeline

---

## 8. TRANSITION STATE

`support drop == 2`

Current handling:
SHADOW ONLY / NO LIVE ENTRY.

Reason:
insufficient evidence of consistent edge.

Do not assign reduced risk.
Do not trade until a future separate study proves an advantage.

---

## 9. EQUAL-RISK PRINCIPLE

Final design decision:

Do NOT use different risk multipliers for A/B/C/SELL.

Correct principle:
- each branch trades ONLY when its own causal qualification context is satisfied
- every qualified trade receives the SAME risk %

Reason:
weak states should be filtered by context, not masked by smaller position size.

Suggested baseline for 100k monetization:
~0.7-0.75% risk per qualified trade.

A more conservative demo/live-forward start can use 0.25-0.5%, but the model itself is equal-risk.

---

## 10. FINAL 6/7+ PIPELINE CHECK

No new parameter search in this check.

Rules:
- reversal = support >=6/7 + collapse >=3 votes / 5m
- route to BUY_A/B/C
- continuation SELL remains strict 7/7 persistence + acceptance
- own qualification context for each state
- equal risk
- max 4 trades/day

Measured W1-W9 result:

- Trades: **235**
- Active days: **108**
- Avg trades per active day: **2.18**
- Annualized from nine sampled monthly windows: **~313 trades/year**

Split P/L:
- TRAIN: **+39.71R**
- VALID: **+9.04R**
- POST: **+12.78R**
- Total: **+61.53R**

Risk:
- Max DD: **8.19R**
- Worst day: **-4.00R**
- Positive active days: **55.6%**
- Positive sampled months: **78.6%**

State counts:
- BUY_A_RESILIENT: **50**
- BUY_B_RECLAIM: **46**
- BUY_C_LATE: **37**
- SELL_PERSISTENCE_ACCEPT: **102**

Verdict:
**PASS FOR DEMO-EA FREEZE.**

Do not broaden signal universe further before demo forward observation.

---

## 11. MONETIZATION REFERENCE

Earlier equal-risk qualified-state pipeline with exact 7/7 reversal produced:

- Total: +57.86R
- Max DD: 7.93R
- Avg active month: +4.13R
- Median active month: +3.56R
- Positive sampled months: 85.7%

Approximate sizing to target ~$3,000 average active month:
- risk per R ~ $726
- on 100k ~ 0.73% per trade
- historical max DD ~ $5,756
- historical worst day ~ -$2,202

Final 6/7+ expansion increases frequency and total R but also slightly increases DD.

Do NOT assume exact dollar monetization until demo execution confirms:
- spreads
- slippage
- real fills
- execution parity
- duplicate suppression
- live signal timing

---

## 12. EA IMPLEMENTATION REQUIREMENTS

The EA must be built as a state machine, not as one symmetric strategy.

### Signal layer
- M15 structural extremes
- crowd support count across 1/3/5/10/15/30/60m GC horizons
- reversal eligibility at support >=6/7
- continuation persistence strict at 7/7
- post-contact vote drop tracking for 5m

### BUY state router
- A_RESILIENT
- B_RECLAIM
- C_LATE
- each state mutually exclusive in execution
- each state logs why it triggered

### SELL state router
- PERSISTENCE_ACCEPT
- no blind persistence SELL
- explicit XAU acceptance required

### Position/risk layer
- equal RiskPercent for every qualified trade
- max 4 trades/day
- one-position-at-a-time is preferred initially unless demo proves safe to relax
- normalize volume using SYMBOL_VOLUME_MIN/MAX/STEP
- use actual tick value / tick size
- validate STOPLEVEL / FREEZELEVEL
- reject trade if spread > MaxSpread
- full order error handling
- unique MagicNumber

### Exit layer
BUY_A:
- 2 ATR SL
- 3R TP
- 30m max hold

BUY_B:
- 2 ATR SL
- 2R TP
- 45m max hold

BUY_C:
- 2 ATR SL
- 1.5R TP
- 60m max hold

SELL:
- structural SL = extreme +0.75 ATR
- 1.5R TP
- 60m max hold

### Logging
Every signal/order must record:
- timestamp UTC
- crowd support at contact
- crowd support after 5m
- branch
- state
- extreme level
- ATR
- qualification metric
- qualification pass/fail
- confirmation timestamp
- entry price
- SL
- TP
- lot
- spread
- broker time
- UTC time
- exit reason
- realized P/L
- realized R

Order comments:
- GCX_BUY_A
- GCX_BUY_B
- GCX_BUY_C
- GCX_SELL_PA

### Shadow logging
Also log:
- rejected 5/7 reversal candidates
- TRANSITION drop==2
- persistence without acceptance
- qualified signal blocked by max-trades/day
- qualified signal blocked by spread / DD / stop-level

This allows live learning without taking those trades.

---

## 13. MANDATORY SAFETY / PROP GUARDS

Inputs:
- RiskPercent
- MaxTradesPerDay = 4
- MaxDailyLossPercent
- MaxOverallLossPercent
- MaxSpreadPoints
- MaxSlippagePoints
- MaxOpenPositions
- TradingStart / TradingEnd if needed
- optional NewsFilter switch
- EmergencyStop switch

Account/equity guards:
- block new entries after daily DD threshold
- block new entries after overall DD threshold
- optional close-all emergency threshold
- preserve broker/server restart state where possible

No:
- martingale
- grid averaging
- revenge sizing
- dynamic risk increase after loss

---

## 14. CLOCK PARITY REQUIREMENT IN EA

Critical.

The EA must explicitly log:
- broker/server timestamp
- derived UTC timestamp

No hidden timezone assumptions.

If GC feed and XAU broker server are on different clocks, normalize before:
- signal joins
- contact detection
- state timing
- response timing
- hold timeout

Add a runtime clock diagnostic line at startup.

---

## 15. BROKER SPECS REQUIRED BEFORE FINAL MQ5 BUILD

Before producing final broker-adapted EA code, confirm:

- broker / prop firm
- account type
- account size
- exact XAU symbol
- leverage
- average spread
- commission per lot / round-turn
- STOPLEVEL
- FREEZELEVEL
- min lot
- max lot
- lot step
- hedging allowed?
- news trading allowed?
- EA allowed?
- max orders / positions if any
- VPS / expected latency
- expected slippage
- rules/spec link if prop

Known old reference:
FTMO Demo 100k, leverage 1:10, EA allowed, hedging/news allowed, commission around $5 RT, VPS ~40ms.

Do not assume these are still current without confirmation.

---

## 16. WHAT NOT TO CHANGE BEFORE DEMO

Freeze the following:

1. M15 as structural timeframe
2. reversal threshold = support >=6/7
3. collapse = vote drop >=3 within 5m
4. continuation persistence remains strict 7/7
5. SELL requires XAU acceptance
6. A/B/C/SELL branch definitions
7. each branch qualification context
8. equal risk
9. max 4 trades/day
10. no 5/7 live reversal yet
11. no TRANSITION live entry
12. no new HTF filter
13. no old retracement execution
14. no LAB004-LAB009 regime reuse

---

## 17. DEMO OBSERVATION GOALS

Primary goal of demo is not to retune quickly.

Observe:
- actual trades/day
- state distribution
- branch-specific P/L
- branch-specific MAE/MFE
- real spread/slippage
- signal-to-entry delay
- duplicate signal behavior
- missed confirmations
- false acceptance
- real holding-time distribution
- daily DD
- rolling overall DD

Preferred minimum forward sample before major changes:
- >=50 total trades for basic execution audit
- >=100 total trades for state comparison
- ideally >=30 trades in a state before judging it independently

---

## 18. RECOVERY COMMAND

If work is resumed later, use:

> Continue GC_XAU from RECOVERY_STATE_016. The signal/execution architecture is frozen for demo-EA implementation: reversal uses M15 extreme + support >=6/7 + drop >=3/5m routed into BUY_A/B/C; SELL uses strict 7/7 persistence + XAU acceptance; branch-specific causal qualification contexts are frozen; all qualified trades use equal risk; max 4 trades/day. Do not restart discovery and do not reuse invalid LAB004-LAB009 execution conclusions. Next task: implement broker-adapted MQL5 EA after confirming broker specs.
