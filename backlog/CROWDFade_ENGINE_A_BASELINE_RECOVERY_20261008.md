# CrowdFade — Engine A Baseline Recovery Backlog

**Frozen:** 2026-10-08  
**Baseline branch:** `baseline/crowdfade-engine-a-20261008`  
**Project:** CrowdFade / BTC anti-crowd research  
**Purpose:** permanent recovery point for the strongest currently-supported CrowdFade construction.

---

## 1. Baseline thesis

CrowdFade is no longer defined as:

> extreme crowd -> blindly fade crowd.

The frozen Engine A thesis is:

> **A mature / reaccelerating H4 trend becomes stretched while OI expands and crowd positioning becomes extreme in the old trend direction. We do not fade immediately. We wait for the first causal M5 structural failure, then enter against the late crowd.**

Mechanism:

`established H4 trend -> price stretch -> OI build -> fresh crowd extreme -> M5 SWING3 break -> reversal entry`

This is a **confirmed anti-crowd capitulation reversal**, not a generic contrarian system.

---

## 2. Frozen signal definition

### Crowd / Z
- Research field used downstream: `count_long_short_ratio`.
- Rolling Z window: 72 x 5m = 6h.
- Fresh event: `|Z| >= 1` crossing from below.
- Crowd direction = sign(Z).
- Trade side = inverse crowd direction.

### Trend
- Causal H4 trend from EMA50 direction / slope logic used in LAB118-LAB125.
- Trade side must be **opposite the existing H4 trend**.
- Preferred phases:
  - `CONTINUATION_4_12`
  - `REACCEL_IMPULSE`

### Capitulation context
Frozen LAB118 thresholds:
- Price extension: `>= 1.53 H1 ATR` away from H1 EMA20 in the old-trend direction.
- OI growth: `OI 4h >= +0.867%`.
- These thresholds came from TRAIN and were frozen before later execution work.

### Entry confirmation
Frozen execution trigger:
- `SWING3_BREAK` on M5.
- First M5 close through the prior 3-bar swing in the reversal direction.
- Entry = **next M5 open**.

Do **not** enter immediately at the Z extreme.

---

## 3. Frozen execution shell

Primary baseline:
- Stop: `1.0 H1 ATR`
- Take-profit: `3R`
- Maximum hold: `48h`
- Same-bar SL/TP ambiguity: conservative **stop-first**
- One-position chronology in research replay
- Costs:
  - normal proxy: `2.81 bps RT`
  - stress proxy: `7.5 bps RT`

Structural 3-bar / 6-bar stops were tested and transferred worse than ATR1. Do not substitute them into the baseline without a new LAB.

---

## 4. Baseline portfolio form

### Core baseline
`CORE_CONT + REACCEL`

LAB122 @ 2.81bps:
- N = 143
- ~2.17 trades/month
- EV ~= +0.349R
- PF ~= 1.53
- R/month ~= +0.76R
- development OOS N = 19
- OOS EV ~= +0.361R
- OOS PF ~= 1.60

LAB122 @ 7.5bps:
- EV ~= +0.294R
- PF ~= 1.43
- OOS EV ~= +0.285R
- OOS PF ~= 1.44

At 0.25% fixed risk the LAB122 benchmark showed roughly:
- MTM DD ~= 2.75% at 2.81bps
- max daily DD ~= 0.89%

These are research estimates, not broker-certified prop results.

---

## 5. Quality-score findings

LAB124/LAB125 showed that quality is **not monotonic** with the hand-built score.

Important:
- Tier A was **not** the strongest.
- Tier B was the strongest standalone band.
- Extremely “perfect-looking” capitulation setups can be too late.

LAB124 Tier B @ 2.81bps:
- N = 73
- EV ~= +0.777R
- PF ~= 2.49
- development OOS N = 11
- OOS EV ~= +0.656R
- OOS PF ~= 2.39

LAB125 useful fixed mid-band:
### `MID_50_A`
- ~1.86 trades/month
- EV ~= +0.463R
- PF ~= 1.75
- OOS EV ~= +0.572R
- OOS PF ~= 2.05

### `MID_45_A`
- ~2.17 trades/month
- EV ~= +0.367R
- PF ~= 1.57
- OOS EV ~= +0.491R
- OOS PF ~= 1.86

Interpretation:
> the sweet spot is mid/high quality, not maximum severity.

Do not blindly size risk upward with raw score.

---

## 6. What has been rejected / downgraded

Do not reintroduce these into Engine A without a separate preregistered LAB:

- Blind Z fade.
- Z-turn as a standalone trigger.
- Funding/OI as a magic standalone filter.
- Generic M5 aggregate microstructure trigger.
- Generic second-level flow burst trigger.
- Early-harvest exits that clip long-tail winners.
- Structural SL3 / SL6 as replacement for ATR1.
- Crowd-following as a standalone leg.
- Generic anti-crowd trend continuation.
- TREND_SQUEEZE.
- Broad D-tier score expansion.
- Simple FAST30 / FAST60 reclaim as proof of a trap.

---

## 7. Engine B status

Engine B is **not part of the baseline**.

Current exploratory hypothesis:
`trapped countertrend crowd continuation`

LAB126 generic trend continuation failed transfer.
LAB127 showed a possible narrower pattern:
- countertrend attack depth ~0.5-1.0 H1 ATR,
- Z strengthens in the countertrend crowd direction,
- OI builds,
- then price reclaims.

Best LAB127 transfer was still too weak for production:
- 0.50 ATR + TRAP_STRONG_IMP:
  - ~3.28 trades/month
  - OOS PF ~= 1.21 at 2.81bps
  - OOS PF ~= 1.12 at 7.5bps

LAB128 tested second-level `effort x result`.
Absolute crowd effort did **not** produce a stable standalone edge.
Potential lead: **price-progress stall / declining flow efficiency** after a ~0.5 ATR countertrend attack.
This remains research only.

---

## 8. Scientific caveats — DO NOT REMOVE

1. The historical OOS segment has been inspected repeatedly across many LABs.
   It is therefore **development OOS**, not pristine validation.

2. Final validation requires:
   - future unseen data, or
   - an independent asset / market replication.

3. Exact feeder field parity is still a pre-production requirement:
   - downstream LABs explicitly use `count_long_short_ratio`.
   - verify that live feeder `g_ratio` is exactly the intended equivalent.
   - do not assume fuzzy selector parity.

4. Long holds require real:
   - broker spread,
   - commissions,
   - slippage,
   - swap / funding,
   not only the 2.81bps / 7.5bps research proxies.

5. Before a final EA / prop deployment, re-check prop/broker rules and execution specs.

---

## 9. Recovery procedure

If future experiments damage or confuse CrowdFade:

1. Return to branch:
   `baseline/crowdfade-engine-a-20261008`

2. Recover the logical chain:
   - LAB118 — Capitulation Reversal Anatomy
   - LAB119 — Capitulation x Trend Phase
   - LAB120 — Entry Timing
   - LAB121 — Execution Transfer
   - LAB122 — Portfolio Expansion
   - LAB124 — Anti-Crowd Quality Score
   - LAB125 — Mid-Band Expansion

3. Restore the frozen Engine A definition:
   `fresh |Z|>=1 inverse crowd + H4 old trend + >=1.53 H1ATR extension + OI4h >= +0.867% + CONT/REACCEL + M5 SWING3_BREAK -> next M5 open -> SL1 H1ATR -> TP3R -> max48h`

4. Use `CORE_CONT + REACCEL` as the canonical benchmark.

5. Treat all Engine B work as optional add-on research. Never mutate Engine A merely to raise frequency.

---

## 10. Next required work before production EA

- Verify live feeder ratio semantics exactly.
- Run full historical signal parity audit: research event -> indicator event -> EA event.
- Freeze one chosen quality policy:
  - canonical simple baseline: `CORE_CONT + REACCEL`, or
  - selected mid-band variant after parity review.
- Re-run with broker-specific spreads, commission, swap/funding, slippage.
- Monte Carlo / order randomization.
- Walk-forward / leave-one-year-out.
- Future forward/demo validation.
- Only after that build/freeze production EA.

---

## 11. Baseline status

**Status: FROZEN RESEARCH / DEMO BASELINE**

Engine A is currently the strongest CrowdFade baseline found in this research chain.

It is not declared a pristine, fully validated production edge yet.

Do not overwrite this baseline with new experiments. Fork new LAB branches from it or compare new engines against it.


---

## 12. Portfolio add-on freeze — B3 after LAB134

**Engine A logic itself remains unchanged.**

Two B3 definitions were frozen before portfolio testing:

### B3_BALANCED
`0.50 H1ATR countertrend attack + positive slope of five 0.1ATR milestone durations`

### B3_HIGH
`0.50 H1ATR countertrend attack + TERMINAL_TWO_STEP`

where:
- `d04 > d03`
- `d05 > d04`

Shared B3 context:
- established causal H4 trend, age >=4 H4 bars
- fresh `|Z| >= 1` with crowd direction opposite H4 trend
- attack reaches 0.50 H1 ATR within 6h
- by depth hit, |Z| strengthens >= +0.25 and keeps attack sign
- OI rises from signal to depth hit
- reclaim of start of final 0.1ATR wave
- next M5 entry in H4 trend direction
- SL 1 H1ATR / TP 3R / max48h / stop-first

### LAB134 portfolio result — BTC TRAIN only

At 2.81bps and fixed 0.25% risk per accepted trade:

- A only:
  - 2.58 trades/month
  - EV +0.348R
  - PF 1.52
  - +0.90R/month
  - realized DD 2.61%

- A + B3_BALANCED:
  - 6.77 trades/month
  - EV +0.321R
  - PF 1.47
  - +2.17R/month
  - realized DD 4.66%

- A + B3_HIGH:
  - 3.35 trades/month
  - EV +0.459R
  - PF 1.72
  - +1.54R/month
  - realized DD 2.08%

At 7.5bps stress:

- A only PF 1.42, DD 2.80%
- A + B3_BALANCED PF 1.35, DD 5.70%
- A + B3_HIGH PF 1.60, DD 2.21%

B3 overlap with Engine A on TRAIN:
- B3_BALANCED: 0% within +/-12h of A
- B3_HIGH: 0% within +/-12h of A

### Baseline portfolio decision

**Promote `A + B3_HIGH` as the preferred CrowdFade portfolio baseline candidate.**

Reason:
- adds genuinely unique trades;
- increases frequency from ~2.58 to ~3.35 trades/month;
- improves PF from 1.52 to 1.72 at normal cost;
- improves PF from 1.42 to 1.60 at stress cost;
- increases R/month from +0.90R to +1.54R;
- does not worsen realized DD in the TRAIN replay.

**Do not promote B3_BALANCED into the canonical baseline.**
It remains frozen as a research/expansion candidate because it raises frequency strongly but weakens PF and materially raises DD, especially under stress costs.

Scientific caveat:
LAB134 is still BTC TRAIN composition evidence only. B3_HIGH is not yet externally validated and must not be called a production-validated edge.
