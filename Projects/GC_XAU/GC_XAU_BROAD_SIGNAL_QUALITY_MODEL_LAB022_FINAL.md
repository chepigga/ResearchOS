# GC_XAU LAB022 — BROAD_SIGNAL_QUALITY_MODEL — FINAL

Date: 2026-09-25
Status: COMPLETED

## Executive result

### Universal quality router: FAIL
A single additive model across BASE / DOM / MIX / REV does not generalize.

The preregistered universal ridge/logistic model failed already on TRAIN as a routing model:
- fixed TRADE requirement pUP >= 0.55 produced zero TRADE observations;
- therefore no threshold was loosened post-hoc.

A TRAIN-frozen leg-specific model was then created BEFORE W6-W9 outcomes were opened.

### Leg-specific quality router: FAIL as a universal production router
OOS aggregate TRADE bucket:
- VALID N=2,097, EV -0.00865 ATR, PF 0.986, hit 50.0%
- POST N=1,524, EV -0.03324 ATR, PF 0.949, hit 46.7%

REJECT actually outperformed TRADE in both OOS blocks.

Conclusion:
There is no single TRADE/WATCH/REJECT rule that can be shared across all Broad legs.

---

# 1. What drives signal quality?

TRAIN univariate uplift in signed +5m XAU ATR:

| Factor | EV uplift |
|---|---:|
| 5m aligned impulse | **+0.1051 ATR** |
| 3m aligned impulse | **+0.0902 ATR** |
| 15m aligned impulse | +0.0740 ATR |
| 30m aligned impulse | +0.0702 ATR |
| H1&H4 BOTH aligned | +0.0464 ATR |
| H1 aligned | +0.0431 ATR |
| H4 aligned | +0.0240 ATR |

Primary answer:
**short-term impulse is the strongest general pre-entry quality variable.**
Trend matters, but as a secondary/context variable.

The ridge model agrees directionally:
- BUY coefficient strongest categorical effect;
- IMP3 strongest standardized continuous effect;
- BOTH alignment positive;
- H4 alone not reliably positive after controlling for the other variables.

---

# 2. Different legs need different context

TRAIN-only strongest contextual effects:

## BASE1
- BUY side better than SELL by ~+0.117 ATR
- IMP5 aligned uplift +0.0756
- BOTH HTF aligned uplift +0.0566

Interpretation:
BASE behaves like an early candidate signal that benefits from price-response confirmation.

## DOM2
- BUY better than SELL by ~+0.0953
- IMP5 aligned uplift **+0.1694**
- BOTH aligned +0.0650

Interpretation:
DOM2 still benefits strongly from immediate price confirmation on long history, even though the 25-Sep forward day showed it could also survive short pullbacks.

## DOM_CONT
- BUY better than SELL by ~+0.0848
- IMP15 aligned uplift **+0.1999**
- IMP3 +0.1350
- BOTH aligned +0.0453

Interpretation:
DOM_CONT quality is more related to persistent impulse than to only a 3–5m move.

## MIX2
- BUY better than SELL by ~+0.0674
- IMP5 aligned +0.0979
- BOTH aligned +0.0795

Interpretation:
raw MIX2 is not a good trade state, but MIX2 can become informative when BUY + HTF trend + immediate XAU response agree.

## MIXED
- BUY better than SELL by ~+0.0671
- IMP3 aligned +0.0843
- H1 aligned +0.0581

Still not robust OOS as a tradable state.

## REV1
- BUY better than SELL by ~+0.1072
- IMP5 aligned +0.1113
- H4 aligned is actually harmful on TRAIN: ~-0.0659 uplift vs NOT aligned

Interpretation:
REV is not a normal trend-continuation signal and should not reuse DOM-style HTF rules.

## REV2
Small TRAIN sample relative to other legs.
- IMP15 aligned +0.2564
- IMP30 aligned +0.2146
- BOTH aligned +0.0616

Interpretation:
REV2 appears to need a slower reversal/persistence confirmation, but sample size and instability remain important.

---

# 3. TRAIN-frozen leg-specific quality votes

Frozen before W6-W9:
- BASE1: BUY + BOTH + IMP5
- DOM2: BUY + BOTH + IMP5
- DOM_CONT: BUY + BOTH + IMP15
- MIX2: BUY + BOTH + IMP5
- MIXED: BUY + H1 + IMP3
- REV1: BUY + NOT-H4-aligned + IMP5
- REV2: BUY + BOTH + IMP15

TRADE = all 3 votes.
WATCH = 2 votes.
REJECT = 0-1 votes.

This complete router FAILED OOS.

---

# 4. OOS performance by TRADE leg

| Leg | VALID EV | VALID PF | POST EV | POST PF | Verdict |
|---|---:|---:|---:|---:|---|
| BASE1 | -0.073 | 0.894 | -0.006 | 0.990 | FAIL |
| DOM2 | -0.084 | 0.870 | -0.092 | 0.871 | FAIL |
| DOM_CONT | **+0.188** | 1.401 | **-0.181** | 0.753 | regime-unstable |
| MIX2 | **+0.147** | **1.256** | **+0.093** | **1.159** | **SURVIVES RAW OOS** |
| MIXED | -0.059 | 0.914 | -0.144 | 0.773 | FAIL |
| REV1 | +0.045 | 1.076 | -0.017 | 0.975 | unstable |
| REV2 | -0.471 | 0.483 | +0.650 | 2.078 | tiny / unstable |

The only frozen leg-specific quality state that remained positive in BOTH VALID and POST is:

# MIX2 BUY + H1&H4 BOTH aligned + 5m impulse aligned

---

# 5. MIX2 quality state — exact replication

Rule:
- leg = MIX2
- side = BUY
- H1 trend = UP and aligned
- H4 trend = UP and aligned
- pre-signal 5m XAU impulse > 0 in BUY direction

This rule was frozen before W6-W9 outcomes.

## TRAIN
Combined:
- N = 976
- EV = **+0.0756 ATR**

Window EV:
- W1 +0.2066
- W2 -0.0031
- W3 -0.1767
- W4 +0.2331
- W5 +0.0126

Positive 3/5 TRAIN windows.

## VALID
- N = 387
- EV = **+0.1466 ATR**
- PF = **1.256**
- hit = 53.0%

Window:
- W6 N282 EV **+0.1279**, PF 1.226
- W7 N105 EV **+0.1967**, PF 1.333

## POST
- N = 222
- EV = **+0.0930 ATR**
- PF = **1.159**
- hit = 50.9%

Window:
- W8 N88 EV **+0.1203**, PF 1.174
- W9 N134 EV **+0.0752**, PF 1.146

Critical fact:
**all 4 untouched OOS windows W6-W9 are positive.**

This strengthens LAB019, where MIX2 BUY + H1&H4 BOTH was already the only replicated HTF interaction.

Adding 5m aligned impulse materially improves selectivity.

---

# 6. TP / path behavior of MIX2 quality state

VALID:
- TP1.5-before-SL1 diagnostic reach ≈ 40.9%
- TP2-before-SL1 ≈ 33.3%
- MFE30 ≈ 3.17 ATR
- MAE30 ≈ 3.17 ATR

POST:
- TP1.5 reach ≈ 40.8%
- TP2 reach ≈ 34.3%
- MFE30 ≈ 3.23 ATR
- MAE30 ≈ 2.96 ATR

The signal contains directional information, but path is still volatile and two-sided.

---

# 7. Does it survive execution costs?

Inherited LAB018/019 execution proxy:
- market entry
- SL = 2.25 ATR
- TP = 4.5 ATR = 2R
- max hold = 5m
- same-M1 collision = SL first
- commission proxy = 0.0007% notional per side
- fixed spread stress = 0.2 XAU

## VALID
- N 387
- gross EV **+0.0636R**
- net EV **+0.0035R**
- net Sum ≈ +1.37R

## POST
- N 222
- gross EV **+0.0405R**
- net EV **-0.0334R**
- net Sum ≈ -7.42R

Window net:
- W6 +0.0019R
- W7 +0.0079R
- W8 -0.0250R
- W9 -0.0389R

Conclusion:
**quality edge is real, but the current market-entry 5m execution geometry still does not survive costs in POST.**

This is a signal-quality PASS / execution FAIL.

---

# 8. Answer to the research question

## What influences profit more: trend or impulse?
Across the Broad universe:
**IMPULSE > TREND.**

But the correct hierarchy depends on leg:
- BASE: short impulse confirmation
- DOM2: 5m impulse + regime
- DOM_CONT: slower 15m persistence
- MIX2: 5m impulse + BOTH H1/H4 trend is the strongest replicated combination
- REV: requires separate reversal confirmation logic; trend rules are not symmetric with DOM

## Which signal is more accurate?
Two different answers must be kept separate:

### 25-Sep forward execution sample
DOM_CONT / DOM2 were the most directionally accurate actual live-demo legs.

### Long-history causal quality model
The most robust conditional signal discovered is:
**MIX2 BUY + H1/H4 BOTH aligned + 5m aligned impulse.**

This does NOT mean raw MIX2 is better than raw DOM.
It means:
**MIX2 becomes high-quality only in a very specific regime.**

---

# 9. Decision

Do NOT replace the Broad Demo router yet.

Do NOT globally promote DOM or globally delete MIX.

Freeze new research fact:

`MIX2_BUY_BOTH_HTF_IMP5_001`

Definition:
- MIX2
- BUY
- H1 aligned UP
- H4 aligned UP
- causal pre-entry XAU 5m impulse > 0

Status:
- raw signal edge: REPLICATED across VALID + POST
- 4/4 OOS windows positive
- execution under current 5m market-entry cost model: NOT robust
- production: NOT AUTHORIZED

---

# 10. Next priority

## LAB023A — MIX2_BUY_BOTH_IMP5_EXECUTION_TRANSFER
Keep signal completely frozen.

Test execution only:
- market vs confirmation vs limit/retrace entry
- no signal retuning
- TP >= 1.5R
- realistic spread / commission / slippage
- 5 / 10 / 15m hold
- exact first-passage path
- TRAIN derive if needed, VALID/POST untouched only for execution choices not previously exposed

Separate ongoing branches remain:
- BASE confirmation + 10m exit study
- DOM persistence/regime study
- REV delayed confirmation study

Q65 remains frozen and separate.
