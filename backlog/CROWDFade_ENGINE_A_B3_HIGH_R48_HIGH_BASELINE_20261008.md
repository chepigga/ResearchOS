# CrowdFade BTC — Canonical Baseline Backlog

**Frozen:** 2026-10-08  
**Canonical portfolio:** `ENGINE_A + B3_HIGH + R48_HIGH`  
**Status:** frozen BTC research/demo baseline; NOT yet pristine production-validated

---

## 1. Canonical portfolio

The current CrowdFade BTC baseline is a three-leg portfolio:

`ENGINE_A + B3_HIGH + R48_HIGH`

The three legs are intentionally different mechanisms:

1. **ENGINE_A — Capitulation Fade**
2. **B3_HIGH — Countertrend Attack Exhaustion**
3. **R48_HIGH — Accepted 48h Breakout Continuation**

The purpose of this backlog is to preserve the exact current construction so it can always be restored if later research drifts.

---

## 2. ENGINE_A — Capitulation Fade

### Mechanism

`established H4 trend -> price stretch -> OI build -> fresh crowd extreme -> M5 SWING3 break -> reversal entry`

This is not a blind crowd fade.

### Frozen context

- Research ratio field: `count_long_short_ratio`
- Z window: 72 x M5 = 6h
- fresh event: `|Z| >= 1` crossing from below
- trade side = inverse crowd direction
- trade side must be opposite existing H4 trend

### Trend / phase

Causal H4 trend:
- EMA50 direction / slope family used in LAB118-LAB125
- preferred phases:
  - `CONTINUATION_4_12`
  - `REACCEL_IMPULSE`

Canonical portfolio benchmark uses:

`CORE_CONT + REACCEL`

### Capitulation context

Frozen thresholds:
- price extension >= **1.53 H1 ATR** from H1 EMA20 in old-trend direction
- OI 4h growth >= **+0.867%**

### Entry

- wait for `M5 SWING3_BREAK` in reversal direction
- entry = next M5 open
- never enter immediately on Z extreme

### Execution

- SL = **1.0 H1 ATR**
- TP = **3R**
- max hold = **48h**
- same-bar ambiguity = **stop-first**
- one-position chronology in research replay

---

## 3. B3_HIGH — Countertrend Attack Exhaustion

### Mechanism

`established H4 trend -> crowd attacks countertrend -> Z strengthens + OI rises -> attack speed decays -> reclaim -> continuation with H4 trend`

This is not generic trend continuation.

### Frozen context

- causal H4 trend established
- trend age >= 4 H4 bars
- fresh `|Z| >= 1`
- crowd direction opposite H4 trend
- countertrend attack reaches **0.50 H1 ATR** within 6h
- by depth hit:
  - crowd Z retains attack sign
  - `|Z|` strengthens by at least **+0.25**
  - OI rises from signal to depth hit

### Exhaustion shape

Attack divided into five causal 0.10 H1ATR milestones:

- d01
- d02
- d03
- d04
- d05

Frozen B3_HIGH condition:

`d04 > d03 AND d05 > d04`

This is the `TERMINAL_TWO_STEP` morphology.

Interpretation:
- final two 0.1 ATR pieces of the countertrend attack take progressively longer
- attack is still pushing, but price efficiency is deteriorating

### Reclaim / entry

- reclaim = first M5 close back through the previous 0.10 ATR milestone
- entry = next M5 open
- direction = H4 trend direction

### Execution

- SL = **1 H1 ATR**
- TP = **3R**
- max hold = **48h**
- stop-first

### LAB133 BTC TRAIN reference

At 2.81bps:
- N = **42**
- ~0.88 trades/month
- EV ~= **+0.705R**
- PF ~= **2.25**
- WR ~= **45.2%**
- R/month ~= **+0.62R**

This is a rare quality leg.

---

## 4. R48_HIGH — Accepted 48h Breakout Continuation

### Mechanism

`48h boundary breakout -> market accepts outside old range -> no retest -> OI builds -> continuation`

This is a breakout-continuation mechanism and is structurally different from Engine A / B3.

### Frozen event

- boundary = prior 48h high/low
- current M5 close breaks outside the frozen boundary
- next six M5 bars are observed
- at least 4 of 6 closes remain outside the old range
- no retest through the broken boundary during the acceptance window

### Strong acceptance

Frozen BTC TRAIN threshold:

- mean acceptance margin >= **0.689 H1 ATR**

### OI condition

- OI change from breakout to entry >= **+0.350%**

### Entry

- entry after the 6-bar acceptance observation
- continuation direction

### Execution

- SL = **1 H1 ATR**
- TP = **3R**
- max hold = **48h**
- stop-first

### LAB137 BTC TRAIN reference

`CLEAN_ACCEPT_OI`:

At 2.81bps:
- N = **133**
- ~2.77 trades/month
- EV ~= **+0.549R**
- PF ~= **1.87**
- WR ~= **39.8%**
- R/month ~= **+1.52R**

At 7.5bps:
- EV ~= **+0.474R**
- PF ~= **1.70**

Important caveat:
- strong BUY bias in BTC TRAIN
- LAB137 count approximately BUY 123 / SELL 10

Do not assume side symmetry.

---

## 5. Canonical portfolio result — LAB138

Portfolio:

`ENGINE_A + B3_HIGH + R48_HIGH`

One-position chronology.

Priority on exact collision:
`ENGINE_A > B3_HIGH > R48_HIGH`

Risk scale for comparison:
- **0.25% per accepted trade**

### Normal cost — 2.81bps

- N = **282**
- **5.88 trades/month**
- EV = **+0.537R**
- PF = **1.86**
- R/month = **+3.15R**
- realized DD = **12.2R**
- realized DD at 0.25% risk ~= **3.05%**

Compared with `ENGINE_A + B3_HIGH`:
- +121 accepted trades
- +2.52 trades/month
- PF improvement: **+0.14**
- EV improvement: **+0.078R**
- R/month improvement: **+1.62R**
- DD increase: about **+0.97%**

### Stress cost — 7.5bps

- N = **282**
- **5.88 trades/month**
- EV = **+0.472R**
- PF = **1.71**
- R/month = **+2.77R**
- realized DD ~= **14.2R**
- realized DD at 0.25% risk ~= **3.54%**

### Overlap

R48_HIGH vs frozen A+B3_HIGH:
- within +/-6h: **0%**
- within +/-12h: **0%**
- unique >12h: **100%**

This is important: R48_HIGH adds genuinely new trades rather than relabeling A/B3 events.

---

## 6. Why this is the canonical baseline

The portfolio currently solves the main frequency problem better than prior CrowdFade baselines:

- old A-only / A+B3 variants were too sparse
- B3_HIGH adds quality but only ~0.8 trades/month
- R48_HIGH adds ~2.5 genuinely unique accepted trades/month
- PF improves rather than degrades
- stress-cost PF remains >1.7
- realized DD remains within a prop-compatible research range at 0.25% risk

The three legs cover different market states:

### ENGINE_A
late-crowd capitulation reversal

### B3_HIGH
countertrend attack exhaustion then primary-trend continuation

### R48_HIGH
accepted range expansion / breakout continuation

Do not merge these concepts into one generic signal.

---

## 7. Rejected / downgraded paths

Do not reintroduce these into canonical baseline without a new preregistered LAB:

- blind Z fade
- Z-turn standalone trigger
- generic OI/funding filter
- generic M5 microstructure trigger
- generic second-level flow burst
- early-harvest exits
- structural SL3 / SL6 replacing ATR1
- crowd-following standalone leg
- generic trend continuation
- TREND_SQUEEZE
- broad D-tier quality expansion
- simple FAST30 / FAST60 trap reclaim
- B4 fast-scale Engine A
- B2 deleveraging fade
- raw B1 false range break
- raw unfiltered R48_ACCEPT

---

## 8. Validation status

This baseline is **not pristine production-validated**.

Reasons:

1. BTC OOS was repeatedly inspected in prior LABs and is no longer pristine.
2. LAB138 is a BTC TRAIN composition test.
3. LAB139 cross-symbol ETH/SOL transfer failed as a generic cross-asset portfolio.
4. That failure does not invalidate BTC specifically, but it means the BTC construction should be treated as BTC-specific until future evidence says otherwise.
5. True BTC production validation now requires:
   - future unseen BTC data
   - live/demo forward execution
   - exact signal parity
   - broker-specific execution costs

---

## 9. Critical parity requirement

Before final production EA:

- verify live feeder `g_ratio`
- ensure it is exactly equivalent to research `count_long_short_ratio`
- do not rely on fuzzy selector behavior
- signal parity must be checked:
  `research event -> indicator event -> EA event`

Any mismatch invalidates production parity.

---

## 10. Broker / prop requirements before final EA

Before final live/prop code freeze, record:

- broker / prop name
- account type
- BTC symbol name in MT5
- average spread
- commission round-turn
- STOPLEVEL / freeze level
- leverage
- minimum lot
- lot step
- swap long / short
- EA rules
- hedging rules
- news rules
- max order / exposure limits
- VPS latency
- expected slippage
- prop challenge rules URL if relevant

Production implementation must use real broker costs, not only 2.81bps / 7.5bps proxies.

---

## 11. Recovery procedure

If future research becomes confused:

1. Return to canonical portfolio:
   `ENGINE_A + B3_HIGH + R48_HIGH`

2. Restore:
   - Engine A from LAB118–125 / baseline recovery doc
   - B3_HIGH from LAB133
   - R48_HIGH from LAB137

3. Confirm portfolio behavior from LAB138.

4. Do not alter thresholds while debugging parity.

5. New experiments must be separate legs or separate branches.

---

## 12. Current decision

**Canonical CrowdFade BTC research/demo baseline:**

`ENGINE_A + B3_HIGH + R48_HIGH`

**Expected research frequency:** ~5.88 trades/month  
**Normal-cost PF:** ~1.86  
**Stress-cost PF:** ~1.71  
**Research DD @0.25% risk:** ~3.05% normal / ~3.54% stress

**Status:** frozen for DEMO / forward implementation.

Do not call it production-validated until future BTC forward data and live execution parity confirm it.
