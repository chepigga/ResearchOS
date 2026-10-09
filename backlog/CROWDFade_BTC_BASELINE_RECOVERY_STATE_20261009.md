# CrowdFade BTC — Canonical Baseline Recovery State 2026-10-09

**Frozen:** 2026-10-09  
**Branch:** `baseline/crowdfade-btc-20261009`  
**Canonical research/demo portfolio:** `ENGINE_A + B3_HIGH + R48_HIGH + EARLY_EPISODE`  
**Portfolio architecture:** one primary position + conditional same-side add-on  
**Risk baseline:** 0.25% per position  
**Status:** frozen BTC research/demo baseline; NOT pristine production-validated

---

## 1. Executive baseline

The current best BTC CrowdFade architecture is:

`ENGINE_A + B3_HIGH + R48_HIGH + EARLY_EPISODE`

with selective pyramiding:

- maximum 2 simultaneous positions
- second position only if:
  - first position mark-to-market `>= 0R`
  - second signal is in the **same direction**
- total nominal stop risk at baseline size: max **0.50%**
- exact same-time priority:
  `ENGINE_A > B3_HIGH > R48_HIGH > EARLY_EPISODE`

This should be interpreted as **conditional pyramiding / add-on**, not as independent portfolio concurrency.

Canonical execution remains:

- SL = 1.0 H1 ATR
- TP = 3R
- max hold = 48h
- stop-first if SL and TP are both touched within the same bar
- research costs: 2.81 bps normal / 7.5 bps stress

---

## 2. ENGINE_A — Capitulation Fade

### Frozen mechanism

`established H4 trend -> extension -> OI build -> fresh crowd extreme -> M5 SWING3 break -> reversal entry`

Context:

- ratio field used in research: `count_long_short_ratio`
- Z window: 72 x M5 = 6h
- fresh event: crossing into `|Z| >= 1`
- side = inverse crowd direction
- side must be opposite existing H4 trend
- H4 preferred phases:
  - `CONTINUATION_4_12`
  - `REACCEL_IMPULSE`
- price extension >= **1.53 H1 ATR**
- OI 4h growth >= **+0.867%**
- entry trigger = first M5 `SWING3_BREAK`
- entry = next M5 open

### LAB145 — stronger/later confirmation

Tested:
- baseline first SWING3
- minimum 30m / 60m wait
- 2/3 and 3/3 acceptance
- two-step break-pullback-second-break

Result:
- all stronger/later confirmation variants were worse
- baseline SWING3 remained best
- artificial waiting increased stop rate and reduced EV

Conclusion:
**do not strengthen or delay A trigger.**

### LAB146 — earlier/weaker confirmation

Tested:
- entry at SWING3 close
- first favorable response
- extreme reclaim
- failed continuation
- rejection wick

Stress 7.5 bps:
- BASE_NEXT_OPEN: EV +0.296R, PF 1.42
- SWING3_CLOSE: EV +0.274R, PF 1.39
- FIRST_RESPONSE: ~0 edge
- REJECTION_WICK: negative
- FAILED_CONT: negative
- EXTREME_RECLAIM: negative

Conclusion:
**do not weaken or anticipate A trigger.**
The first SWING3 is near the local timing optimum in the tested family.

---

## 3. LAB147 — ENGINE A missed-trade funnel

Question:
where does A lose potentially profitable reversals before entry?

Stress 7.5 bps:

- CANONICAL: N=123, 2.56/mo, EV +0.306R, PF 1.44, +0.79R/mo
- ACTIVE_Z_RESCUE: N=173, 3.60/mo, EV +0.175R, PF 1.24, +0.63R/mo
- FAIL_ONLY_PHASE: EV +0.127R, PF 1.17
- FAIL_ONLY_EXTENSION: EV -0.038R, PF 0.95
- FAIL_ONLY_OI: EV -0.164R, PF 0.80
- multi-fail: essentially no edge after stress costs

BUY OI diagnostic @7.5 bps:
- negative OI: EV -0.330R, PF 0.61
- positive OI below canonical gate: EV +0.187R, PF 1.25
- canonical OI pass: EV +0.661R, PF 2.21

Conclusion:
- the main useful leak is **fresh-Z timing**
- OI growth is a strong quality filter, including for BUY
- do not replace A BUY OI logic with falling-OI logic

---

## 4. EARLY_EPISODE — conditional rescue leg

Origin:
LAB147 showed that valid A-like context can appear shortly after the fresh Z crossing while Z remains extreme.

LAB148 anatomy isolated the best rescue family.

### Frozen rescue rule

`ACTIVE_Z_RESCUE` where the full A context becomes valid within **<=5 minutes** of the fresh-Z episode start.

The rescue signal still requires:
- established opposite H4 trend
- valid A phase
- extension gate
- OI gate
- SWING3 trigger

What differs from A:
- the full context does not have to be valid exactly on the first fresh-Z crossing
- it may become valid immediately afterward while the same Z extreme episode is still active

### LAB148 standalone anatomy

Stress 7.5 bps:

`EARLY_EPISODE`
- N=110
- 2.29/mo standalone
- EV +0.357R
- PF 1.52
- R/mo +0.82R
- DD 9.1R
- BUY/SELL 35/75

`EARLY_STRONG_Z`
- N=47
- 0.98/mo
- EV +0.744R
- PF 2.30
- R/mo +0.73R
- DD 4.3R

Decision:
use **EARLY_EPISODE** as the frozen broad rescue candidate; EARLY_STRONG_Z remains a quality sub-class, not a replacement baseline.

### LAB149 portfolio composition

At 7.5 bps:

A only:
- N=124
- 2.58/mo
- EV +0.296R
- PF 1.42
- R/mo +0.76R

A + EARLY_EPISODE:
- N=136
- 2.83/mo
- EV +0.321R
- PF 1.46
- R/mo +0.91R

Full old canonical:
`A+B3_HIGH+R48_HIGH`
- N=282
- 5.88/mo
- EV +0.472R
- PF 1.71
- R/mo +2.77R
- DD 3.54% at 0.25%

Full + EARLY_EPISODE:
- N=292
- 6.08/mo
- EV +0.487R
- PF 1.74
- R/mo +2.96R
- DD 3.80% at 0.25%

Important:
raw EARLY_EPISODE signals are temporally unique, but one-position occupancy blocks most of them.
Therefore the standalone 2.29/mo does NOT translate into +2.29 accepted portfolio trades/month.

---

## 5. LAB150 — blocked signal / selective concurrency audit

Universe:
`A + B3_HIGH + R48_HIGH + EARLY_EPISODE`

At stress 7.5 bps, currently blocked by one-position logic:

- all blocked: N=214, EV +0.248R, PF 1.35
- blocked EARLY_EPISODE: N=131, EV +0.297R, PF 1.43
- blocked A: N=75, EV +0.199R, PF 1.28
- blocked B3_HIGH: N=6, EV +0.257R, PF 1.36
- blocked R48_HIGH: N=2, negative small sample

The crucial split:

### Same-side blocked signals
- N=169
- EV **+0.535R**
- PF **1.87**
- WR 42.0%

### Opposite-side blocked signals
- N=45
- EV **-0.827R**
- PF **0.19**
- WR 6.7%

Strong source-pair findings @7.5 bps:

- open A -> blocked A, same side:
  - N=44
  - EV +0.748R
  - PF 2.39

- open A -> blocked EARLY_EPISODE, same side:
  - N=114
  - EV +0.469R
  - PF 1.74

- open R48_HIGH -> blocked A, opposite side:
  - N=22
  - EV -0.920R
  - PF 0.12

- open R48_HIGH -> blocked EARLY_EPISODE, opposite side:
  - N=14
  - EV -1.089R
  - PF 0.00

Interpretation:
**second same-side entries behave like confirmation/add-on into an already working move.**
Opposite-side second entries are strongly harmful.

---

## 6. LAB151 — concurrent MTM prop-DD replay

This is the current architecture-defining LAB.

M5 bar-by-bar mark-to-market equity replay.
Risk scale = **0.25% per position**.

### Normal cost 2.81 bps

`SECOND_MTM_GE0_SAME_SIDE`
- N=344
- **7.17 trades/month**
- EV **+0.618R**
- PF **2.04**
- R/month **+4.43R**
- max MTM DD **3.97%**
- max daily-start loss proxy **1.11%**
- max intraday peak DD **1.55%**
- worst simultaneous floating **-0.54%**
- max nominal open risk **0.50%**
- days >4%: 0
- days >5%: 0

### Stress cost 7.5 bps

`SECOND_MTM_GE0_SAME_SIDE`
- N=341
- **7.10 trades/month**
- EV **+0.571R**
- PF **1.91**
- R/month **+4.06R**
- max MTM DD **4.52%**
- max daily-start loss proxy **1.15%**
- max intraday peak DD **1.55%**
- worst simultaneous floating **-0.60%**
- max nominal open risk **0.50%**
- days >4%: 0
- days >5%: 0

### Comparison @7.5 bps

ONE_POSITION:
- 6.08/mo
- PF 1.74
- EV +0.487R
- R/mo +2.97R
- MTM DD 3.98%

SECOND_OPEN_MTM_GE0:
- 7.31/mo
- PF 1.84
- EV +0.536R
- R/mo +3.92R
- MTM DD 4.52%

SECOND_SAME_SIDE:
- 8.08/mo
- PF 1.71
- EV +0.468R
- R/mo +3.78R
- MTM DD 5.24%

SECOND_ANY:
- 8.40/mo
- PF 1.64
- EV +0.429R
- R/mo +3.60R
- MTM DD 4.87%

Winner:
**SECOND_MTM_GE0_SAME_SIDE**

Frozen pyramiding rule:
- max 2 positions
- second allowed only if first position MTM >= 0R
- second signal must be same side
- baseline 0.25% risk per position

Important:
the second trade is not treated as independent diversification.
It is a **same-direction add-on / pyramid**.

---

## 7. LAB152 — EARLY_EPISODE robustness + placebo

Frozen `EARLY_EPISODE <=5m`.

Stress 7.5 bps:
- N=110
- EV +0.357R
- PF 1.52
- total +39.2R
- DD 9.1R

### Threshold sensitivity @7.5 bps

- <=5m: EV +0.357R, PF 1.52
- <=10m: EV +0.293R, PF 1.42
- <=15m: EV +0.292R, PF 1.42
- <=30m: EV +0.258R, PF 1.36

Edge decays gradually as episode age widens.
This is better than a cliff-like overfit pattern.

### Year robustness @7.5 bps

- 2021: N44, EV +0.252R, PF 1.36
- 2022: N22, EV +0.380R, PF 1.56
- 2023: N18, EV +0.020R, PF 1.03
- 2024: N26, EV +0.747R, PF 2.28

Chronological halves:
- H1: EV +0.253R, PF 1.36
- H2: EV +0.464R, PF 1.70

Interpretation:
EARLY_EPISODE is positive overall but clearly **regime-sensitive**.
2023 is nearly flat.

### Placebo controls @7.5 bps

Observed:
- EV +0.357R
- PF 1.52

2000 uniform random matched-count/side runs:
- median EV -0.146R
- p95 EV +0.083R
- median PF 0.83
- p95 PF 1.11
- empirical p(EV >= observed) = **0.0005**

2000 same-side time-shift runs +/-1..14 days:
- median EV -0.196R
- p95 EV +0.035R
- median PF 0.77
- p95 PF 1.05
- empirical p(EV >= observed) = **0.0005**

Decision:
EARLY_EPISODE timing is clearly non-random in TRAIN, but because of regime sensitivity it remains a **conditional add-on**, not a core standalone engine.

---

## 8. R48_HIGH — frozen core breakout leg

Mechanism:

`48h boundary break -> 4/6 M5 acceptance outside range -> no retest -> strong mean acceptance margin -> OI build -> continuation`

Frozen R48_HIGH = `CLEAN_ACCEPT_OI`.

Thresholds:
- mean acceptance margin >= 0.689 H1ATR
- OI breakout->entry >= +0.350%
- no retest through old boundary
- continuation entry after acceptance window

Stress 7.5 bps:
- N=133
- 2.77/mo
- EV +0.474R
- PF 1.70

Strong BUY bias in TRAIN:
- raw signals roughly BUY 124 / SELL 10

---

## 9. LAB153 — R48_HIGH random-long / bull-drift controls

Purpose:
test whether R48_HIGH is merely BTC bull drift / random long timing.

Stress 7.5 bps:

Observed:
- N=133
- EV **+0.474R**
- PF **1.70**
- WR 39.8%
- total +63.0R

Same timestamps, force all LONG:
- EV +0.323R
- PF 1.45
- total +43.0R

Same timestamps, force all SHORT:
- EV -0.240R
- PF 0.72

Same timestamps, flip original side:
- EV -0.389R
- PF 0.57

### Time robustness

- 2021: EV +0.633R, PF 2.02
- 2022: EV +0.502R, PF 1.76
- 2023: EV +0.341R, PF 1.46
- 2024: EV +0.403R, PF 1.58

Chronological halves:
- H1: EV +0.627R, PF 2.00
- H2: EV +0.318R, PF 1.44

### Random long controls — 2000 runs

Uniform random long:
- median EV -0.098R
- p95 EV +0.146R
- median PF 0.88
- p95 PF 1.20
- p(EV>=observed)=0.0005

Year-matched random long:
- median EV -0.103R
- p95 EV +0.149R
- median PF 0.87
- p95 PF 1.20
- p(EV>=observed)=0.0005

Year-matched observed side-mix:
- median EV -0.106R
- p95 EV +0.145R
- median PF 0.87
- p95 PF 1.19
- p(EV>=observed)=0.0005

Conclusion:
R48_HIGH is **not explained by generic BTC bull drift**.
Some of its strength comes from choosing good long-biased timing, but the actual R48 direction logic materially improves over all-long-at-same-times.

R48_HIGH remains a **core leg**.

---

## 10. B3_HIGH — frozen rare quality leg

Mechanism:

`H4 trend -> crowd attacks countertrend -> 0.50 H1ATR attack -> Z strengthens + OI rises -> terminal velocity decay -> reclaim -> continuation with H4 trend`

Frozen morphology:
`d04 > d03 AND d05 > d04`

Reference TRAIN:
- N ~42
- ~0.88/mo
- EV ~+0.705R
- PF ~2.25

B3_HIGH remains unchanged.

---

## 11. Exit research status

Canonical execution remains:
- SL = 1 H1ATR
- TP = 3R
- max hold 48h

LAB141 fixed-cohort exploratory exit study suggested:
- TP4 may outperform TP3
- no-TP H48 had even larger tail gain but higher DD and violates current production philosophy

However:
LAB141 used a fixed accepted cohort and did NOT recompute raw-signal chronology under changed holding periods.

Therefore:
**TP4 is NOT canonical. TP3 remains frozen until a full raw-signal chronology replay proves otherwise.**

LAB142 simple reentry was rejected.
LAB143 entry delay/retracement did not improve R/month.
LAB144 generic concurrency did not help before the later selective-pyramiding discovery.

---

## 12. Current canonical baseline

### Signal engines

Core:
1. ENGINE_A
2. B3_HIGH
3. R48_HIGH

Conditional add-on:
4. EARLY_EPISODE

### Position architecture

- max 2 simultaneous BTC positions
- first position may come from any canonical leg
- second position allowed only if:
  - existing position MTM >= 0R
  - new signal side == existing position side
- same-time engine priority:
  `A > B3_HIGH > R48_HIGH > EARLY_EPISODE`

### Risk

Research/demo baseline:
- **0.25% risk per position**
- maximum nominal stop risk with 2 open positions = **0.50%**

Do NOT move to 0.35–0.40% yet without exact prop-rule replay.

---

## 13. Current performance reference

### Normal cost 2.81 bps

Canonical selective-pyramiding portfolio:
- N=344
- **7.17 trades/month**
- EV **+0.618R**
- PF **2.04**
- R/month **+4.43R**
- MTM DD **3.97%**
- worst daily-start loss proxy **1.11%**

At $100k / 0.25% risk:
- average research expectation ~= **$1,108/month**

### Stress cost 7.5 bps

- N=341
- **7.10 trades/month**
- EV **+0.571R**
- PF **1.91**
- R/month **+4.06R**
- MTM DD **4.52%**
- worst daily-start loss proxy **1.15%**
- worst simultaneous floating ~= -0.60%
- max nominal open risk = 0.50%

At $100k / 0.25% risk:
- average research expectation ~= **$1,015/month**

These are historical TRAIN averages, not guaranteed returns.

---

## 14. Scientific / validation caveats

This baseline is NOT pristine production validated.

Critical caveats:

1. BTC OOS has been repeatedly inspected in prior work; it is development OOS, not pristine.
2. LAB145–153 are TRAIN/development research.
3. Placebo significance does not replace future unseen validation.
4. R48_HIGH is BTC-specific until independent future BTC evidence confirms persistence.
5. EARLY_EPISODE is regime-sensitive; 2023 was nearly flat.
6. Same-side second entries are correlated pyramids, not independent diversification.
7. LAB151 daily loss reset used UTC proxy, not exact FTMO CET/CEST reset.
8. Live broker costs must replace 2.81/7.5bps proxies.
9. Exact feeder ratio field parity remains mandatory.
10. MTM replay is on M5 close path except frozen exit bars; live intrabar excursions may be worse.
11. Any increase above 0.25% risk requires a separate exact prop-risk replay.

---

## 15. Critical live parity requirement

Before final EA:

- verify live feeder `g_ratio`
- ensure it equals research `count_long_short_ratio`
- remove/fix any fuzzy field selector ambiguity
- verify exact event parity:
  `research -> indicator -> EA`
- verify timestamps / server offset / UTC handling
- verify OI synchronization
- verify H1/H4 causal bar usage
- verify no future leakage around SWING3 / R48 acceptance / B3 milestone timing

Any parity mismatch invalidates the baseline.

---

## 16. Broker / prop specs still required before final code

Before generating/finalizing live or prop EA code, record:

- prop/broker name
- account type
- BTC symbol
- average spread
- commission round-turn
- STOPLEVEL
- freeze level
- leverage
- min lot / lot step
- swap long/short
- EA rules
- hedging rules
- news rules
- max positions/orders/exposure
- VPS latency
- expected slippage
- exact daily-loss reset timezone and formula
- rules/challenge URL

---

## 17. NEXT BACKLOG — highest priority

### P0 — exact prop-risk replay

Run exact FTMO-style daily drawdown with:
- CET/CEST reset
- floating + closed P/L according to actual firm rule
- 0.25% baseline
- then 0.30 / 0.35 / 0.40% only as research scenarios
- report safety margin to 5% daily and 10% overall
- use selective pyramiding rule exactly

Do not increase risk before this.

### P0 — feeder/research parity audit

Resolve:
- feeder `g_ratio` exact source
- must match `count_long_short_ratio`
- verify Z calculation and fresh episode parity
- verify OI field/time alignment
- verify R48 and B3 event parity

### P0 — demo forward

Deploy only after broker specs are supplied.
Start at **0.25% risk**.

Log per signal:
- engine
- side
- signal time
- entry time
- all gate values
- first-position MTM at second-entry decision
- whether add-on was allowed/rejected
- SL/TP
- spread/slippage
- exit reason
- realized R

### P1 — EARLY_EPISODE regime monitor

Because 2023 was flat:
- classify live regime for rescue trades
- compare performance by trend/range/volatility state
- do NOT optimize a new filter on existing TRAIN without preregistration
- forward evidence should decide whether rescue remains enabled continuously

### P1 — full chronology exit replay

Revisit TP4 only with:
- full raw signal regeneration
- changed holding periods allowed to alter future signal occupancy
- exact same portfolio/pyramiding architecture
- MTM DD included

Until then TP3 remains canonical.

### P1 — future unseen BTC validation

The strongest next scientific evidence is future data.
Do not repeatedly mine the already-inspected 2025-2026 segment and call it validation.

---

## 18. Rejected / do-not-reintroduce list

Do not reintroduce without a new preregistered test:

- blind Z fade
- simple Z-turn trigger
- generic funding/OI magic filter
- generic M5 microstructure trigger
- generic second-level trigger
- stronger/later A confirmation from LAB145
- weaker/earlier A trigger from LAB146
- BUY negative-OI rescue hypothesis
- generic loosening of extension
- generic loosening of OI
- B4 fast-scale A
- B1 generic false-break
- B2 deleveraging reversal
- TREND_SQUEEZE
- crowd-follow standalone
- raw R48_ACCEPT
- simple reentry from LAB142
- generic second position
- opposite-side second position
- same-side second position without MTM filter
- TP4 as canonical before full chronology replay
- no-TP production logic

---

## 19. Recovery procedure

If research drifts or later code becomes confused:

1. checkout branch:
   `baseline/crowdfade-btc-20261009`

2. restore canonical engines:
   - A from frozen A lineage
   - B3_HIGH from LAB133
   - R48_HIGH from LAB137
   - EARLY_EPISODE from LAB147/LAB148

3. restore execution:
   - SL1 H1ATR
   - TP3R
   - 48h
   - stop-first

4. restore portfolio:
   - priority A > B3_HIGH > R48_HIGH > EARLY_EPISODE
   - max two positions
   - second only if first MTM >=0R AND same side
   - 0.25% risk per position

5. reference LAB151 for canonical MTM portfolio metrics.

6. reference LAB152 for EARLY_EPISODE QA.

7. reference LAB153 for R48 bull-drift QA.

8. do not alter thresholds while debugging parity.

---

## 20. Final frozen statement

**Canonical CrowdFade BTC research/demo baseline as of 2026-10-09:**

`A + B3_HIGH + R48_HIGH + EARLY_EPISODE`

with:

`SECOND_MTM_GE0_SAME_SIDE`

and:

`risk = 0.25% per position, max 2 positions`

Stress reference:
- ~7.10 trades/month
- PF ~1.91
- EV ~+0.571R
- ~+4.06R/month
- MTM DD ~4.52%
- daily-start loss proxy ~1.15%

R48_HIGH = core.
EARLY_EPISODE = conditional/regime-sensitive add-on.
Selective second entry = pyramiding, not diversification.

**This is the recovery baseline. Do not call it production-validated until forward BTC data, broker parity, and exact prop-rule replay are complete.**
