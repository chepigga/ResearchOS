# GC_XAU_RESEARCH_BACKLOG_RECOVERY_STATE_015

Updated: 2026-10-03

## PURPOSE

Canonical recovery checkpoint for the GC futures / COMEX aggressive order-flow -> XAUUSD research branch.

Do not restart discovery from scratch.
Do not mix this branch with CrowdFade / crypto / BTC AEIF / unrelated EAs.

---

## 1. CURRENT CORE HYPOTHESIS

The useful information is not simply:

`7/7 crowd = trade contrarian`.

The current structural interpretation is:

`GC 7/7 crowd saturation -> XAU important extreme contact -> observe what crowd does next`

Then branch:

- crowd support COLLAPSES -> reversal candidate;
- crowd support PERSISTS -> do NOT assume reversal; breakout becomes competitive and needs price acceptance;
- intermediate state -> usually no-trade / unresolved.

This is a structural signal problem first.
Execution must be researched separately and with correct clock parity.

---

## 2. FROZEN GC SIGNAL DEFINITION

GC aggressive order-flow horizons:

- 1m
- 3m
- 5m
- 10m
- 15m
- 30m
- 60m

At each horizon:

`LS = aggressive BUY volume / aggressive SELL volume`

- LS < 1 -> crowd SELL
- LS > 1 -> crowd BUY
- 7/7 -> all seven horizons aligned in the same crowd direction

The main structural event uses:

1. XAU active structural extreme;
2. GC crowd at/near full alignment;
3. contact with the extreme;
4. post-contact support behavior.

M15 is currently the preferred structural timeframe.
M30 repeatedly showed poorer OOS stability.

---

## 3. LAB001-003 — STILL VALID

### LAB001 — alignment decay

Main finding:
useful information is in how 7/7 alignment decays, not only the static 7/7 state.

Resolved reversal rates increased as support decayed:

- 7->6: ~53.9%
- 7->5: ~55.1%
- 7->4: ~55.5%
- 7->3: ~56.9%
- 7->2: ~58.3%
- 7->1: ~59.4%
- 7->0: ~62.4%

Pivot timing showed that 7->3 often occurred near the actual reversal area, while later decay states became increasingly delayed.

### LAB002 — extreme outcome

Key structural result:

`ACTIVE EXTREME CONTACT -> observe post-contact GC support collapse`

M30 early exploratory result:
drop >=3 votes within 5m showed substantially higher reversal frequency.

### LAB003 — frozen structural OOS

Frozen rule:

`M15 active extreme contact -> GC support drop >=3 votes within 5m`

M15:
- TRAIN: 71.7% reversal
- VALID: 69.6%
- POST: 72.8%

This structural signal result remains valid.

IMPORTANT:
This is a structural reversal classification, NOT a trade win-rate.

---

## 4. CRITICAL CLOCK BUG DISCOVERED IN LAB004-009

A 3-hour timezone mismatch was found between signal timestamps and XAU execution/context timestamps.

Signal timestamps were treated as UTC while XAU broker timestamps were effectively used as if already UTC.

Parity audit:
- 12 / 12 control trades confirmed a 3-hour mismatch.

Example pattern:
a signal recorded around 16:41 UTC was paired with an XAU execution bar around 16:42 broker time instead of the correct ~19:42 broker time.

### CONSEQUENCE

The following execution/regime conclusions are INVALIDATED:

- LAB004 execution edge
- LAB005 cost/equity edge
- LAB006 regime profitability conclusions
- LAB007 EMA execution interpretation insofar as it relied on bad execution clock
- LAB008 cluster profitability
- LAB009 frozen-cluster profitability

Specifically DO NOT promote:

- 50% retracement edge
- 75% retracement edge
- ALIGNED_BIAS_LOCAL_PULLBACK as a profitable execution regime
- any equity/DD numbers derived from LAB004-009

These must not be cited as validated trading edges.

The clock bug affects execution/context alignment, not the underlying GC signal existence.

---

## 5. CORRECTED EXECUTION REPLAY

After correcting clock parity, old retracement execution lost its edge.

Corrected per-signal expectancy:

### 25% retracement
- TRAIN: -0.371R
- VALID: -0.243R
- POST: -0.367R

### 50% retracement
- TRAIN: -0.497R
- VALID: -0.344R
- POST: -0.497R

### 75% retracement
- TRAIN: -0.546R
- VALID: -0.424R
- POST: -0.443R

Conclusion:

OLD RETRACEMENT EXECUTION MODEL = FAIL.

Do not optimize around those old 25/50/75% structures as if they were proven.

---

## 6. NEW PRISTINE FORWARD DATA AFTER 2026-07-28

Forward sources used:

- GC: AMP / GCEZ26 explicit aggressor history, approximately 2026-08-06 -> 2026-09-15
- XAU: post-cutoff 2026 M1 overlap

This period is outside the old W1-W9 research windows.

### Strict causal signal-only audit

Signal quality was recomputed from `signal_time`, not from execution entry.

No:
- limit price
- SL
- TP
- commission
- old cluster filter

Forward sample:
- 89 unique causal signals
- 44 BUY
- 45 SELL

Directional close in signal direction:

- 5m: 61.8%
- 10m: 58.4%
- 15m: 57.3%
- 30m: 50.6%
- 60m: 51.7%

Main interpretation:

The GC signal has useful information concentrated primarily in the first 5-15 minutes after confirmation.
The edge largely washes out by 30-60 minutes.

### BUY / SELL asymmetry

BUY branch was materially stronger in the forward sample.

BUY:
- 5m: ~65.9%
- 10m: ~68.2%
- 15m: ~65.9%

SELL was weaker and did not behave as a mirror image.

Do not assume BUY and SELL symmetry.

### Important nuance

First-touch +1 ATR vs -1 ATR was close to 50/50.

Therefore:
the signal can point in the correct eventual direction while price first makes adverse excursion.

This explains why a valid directional signal can still produce poor trade P/L with naive market entry or a tight stop.

---

## 7. LAB011 — EXTREME CONTACT x CROWD PERSISTENCE/COLLAPSE

Research question:

`EXTREME CONTACT x CROWD RESPONSE -> REVERSAL vs BREAKOUT`

No execution rules used.

Primary universe:
- XAU active structural extreme
- GC exactly 7/7 at contact
- M15 and M30 separately

Post-contact crowd state at +5m:

### COLLAPSE
support drops by >=3 votes

### PERSISTENCE
support drops by <=1 vote

### TRANSITION
support drops by exactly 2 votes

Binary structural outcome:
- REVERSAL = REVERSAL_HOLD or FALSE_BREAK_RECLAIM
- BREAKOUT = BREAKOUT_ACCEPT
- unresolved excluded from binary rate

### M15 result

COLLAPSE reversal rate:
- TRAIN: 71.0%
- VALID: 65.5%
- POST: 68.9%

PERSISTENCE:
- TRAIN: 56.0% reversal / 44.0% breakout
- VALID: 63.0% / 37.0%
- POST: 48.0% / 52.0%

TRANSITION:
approximately coin-flip / low-edge in OOS.

### Interpretation

Do NOT simplify this to:

`PERSISTENCE = breakout`

Correct interpretation:

- COLLAPSE = positive evidence for reversal
- PERSISTENCE = veto against automatic contrarian reversal
- PERSISTENCE still requires XAU breakout acceptance before continuation trade
- TRANSITION = mostly no-trade / unresolved

### M30

M30 was unstable:
COLLAPSE reversal rate fell to ~45% in VALID.

Therefore:
M15 remains the preferred branching timeframe.

---

## 8. CURRENT STRUCTURAL STATE MACHINE

Current best research architecture:

`7/7 crowd saturation`
-> `XAU active extreme contact`
-> observe GC crowd support for 5m

Then:

### Branch A — COLLAPSE
`drop >=3 votes`

Interpretation:
REVERSAL CANDIDATE.

Do not enter blindly.
Execution still needs to be built from post-signal price path.

### Branch B — PERSISTENCE
`drop <=1 vote`

Interpretation:
DO NOT FADE AUTOMATICALLY.

Wait for XAU breakout / acceptance confirmation.

### Branch C — TRANSITION
`drop ==2 votes`

Interpretation:
NO TRADE for now.

---

## 9. WHAT WE KNOW VS WHAT WE DO NOT KNOW

### We know

1. GC multi-horizon aggressive-flow state contains real structural information.
2. Extreme contact is essential context.
3. M15 is more robust than M30.
4. Fast post-contact crowd collapse is associated with reversal.
5. Persistence does not guarantee breakout, but it weakens the reversal case.
6. Forward signal information is strongest in the first 5-15 minutes.
7. BUY and SELL behavior is asymmetric.
8. Directional signal correctness is not the same as trade profitability.
9. Old retracement execution conclusions were invalid due to clock mismatch.

### We do NOT yet know

1. Best causal entry after a COLLAPSE signal.
2. Best stop geometry.
3. Best TP / exit geometry.
4. Whether BUY and SELL should use different execution logic.
5. Exact XAU price-acceptance rule for the PERSISTENCE / breakout branch.
6. Whether there is a profitable continuation branch after persistence.
7. Whether a single execution model can work across both reversal and breakout states.

---

## 10. NEXT PRIORITY — KEEP IT SMALL

Do not launch another broad discovery campaign.

### P1 — REVERSAL PATH AFTER COLLAPSE

Use the existing valid M15 COLLAPSE signal.

Measure only the first:
- 1m
- 2m
- 3m
- 5m
- 10m
- 15m

after `signal_time`.

For every event record:
- directional return
- MFE
- MAE
- first favorable excursion
- first adverse excursion
- stabilization / reclaim behavior
- whether price first moves wrong-way then reverses

Goal:
find the natural causal entry geometry instead of imposing arbitrary 25/50/75% retracement.

### P2 — PERSISTENCE / BREAKOUT ACCEPTANCE

Only after P1 is understood.

Need a simple XAU acceptance definition such as:
- sustained closes beyond extreme
- expansion after level break
- no rapid reclaim
- optional GC persistence confirmation

Do not optimize this together with reversal execution.

---

## 11. RESEARCH RULES GOING FORWARD

1. Every signal timestamp and XAU timestamp must be normalized explicitly to UTC before joins.
2. Add a mandatory `clock_parity_assert` to every new LAB.
3. For every replay, sample at least 10 signal-to-XAU-bar joins and verify visually/numerically.
4. Do not infer execution edge from structural hit-rate.
5. Do not reuse invalid LAB004-009 profitability numbers.
6. Keep signal logic frozen while researching execution.
7. Keep reversal and breakout branches separate.
8. Keep BUY/SELL statistics separate.
9. New execution claims require realistic Bid/Ask, costs and slippage only after path geometry is proven.
10. No production EA promotion until corrected execution survives OOS/forward.

---

## 12. CURRENT VERDICT

### SIGNAL
PASS.

Structural GC signal remains alive and transferred to new Aug-Sep 2026 data.

### REVERSAL BRANCH
PASS as a structural classifier.

M15 COLLAPSE after extreme contact is the strongest current branch.

### BREAKOUT BRANCH
UNPROVEN.

Persistence is only a veto against automatic reversal, not yet a standalone trade signal.

### EXECUTION
FAIL / RESET.

Old 25/50/75% retracement execution must be discarded.

### REGIME MODEL
RESET.

Old profitable cluster conclusions were contaminated by execution clock mismatch.

---

## 13. RECOVERY COMMAND

If this research is resumed later, start with:

> Continue GC_XAU from RECOVERY_STATE_015. Do not restart discovery. Treat LAB004-009 execution/regime profitability as invalid due to the 3-hour clock bug. Keep LAB001-003 structural signal findings and LAB011 M15 crowd-branch findings. Next task: causal post-signal price-path study for the M15 COLLAPSE reversal branch only.

