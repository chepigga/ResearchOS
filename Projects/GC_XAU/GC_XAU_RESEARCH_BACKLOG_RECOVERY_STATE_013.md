# GC_XAU_RESEARCH_BACKLOG_RECOVERY_STATE_013

Updated: 2026-09-25  
Project scope: **GC futures / COMEX order flow -> XAUUSD execution only**  
Do not mix with BTC / CrowdFade / crypto branches.

---

# 1. FROZEN / DO NOT CHANGE

## Q65
Frozen and unchanged:
`DOMINANCE_REVERSAL -> REV2 -> +30s -> Q65`

- impulse >= 0.0521
- aligned volume >= 20.60
- SL = 2.25 ATR
- TP = 4.50 ATR
- timeout = 300s
- forward demo only / not production proven

Do not retune Q65 from Broad Demo findings.

## Broad Demo
Keep Broad Demo as a **data-acquisition / execution observation engine**.

Do not yet:
- delete MIX or REV;
- promote DOM as universal production winner;
- change all legs to one common new timeout;
- change signal semantics post-hoc from one forward day.

---

# 2. LAB018 — BROAD LEGS LONG-HISTORY CAUSAL REPLAY

Exact causal labels:
- BASE1
- DOM2
- DOM_CONT
- MIX2
- MIXED
- REV1
- REV2

Long-history conclusion:
- no raw leg is positive and production-robust across TRAIN / VALID / POST;
- leg alone is not enough;
- **label x side x regime/trend context matters**;
- Broad legs are better understood as market-state descriptors than standalone alphas.

Important 2026 clue:
- REV2, MIX2 and DOM legs improve relative to older history;
- therefore one strong forward day must not be turned into a permanent hierarchy.

---

# 3. LAB019 — LEG x SIDE x H1/H4 TREND

Primary replicated interaction:

## MIX2 BUY + H1&H4 BOTH aligned
Raw +5m edge survived:
- TRAIN
- VALID
- POST

Approx:
- TRAIN EV +0.0539 ATR
- VALID EV +0.0670 ATR
- POST EV +0.0396 ATR

Positive in 8/9 quality windows.

But:
- inherited market-entry / cost geometry remains net negative;
- this is a **signal/information edge**, not yet an executable production edge.

Decision:
- no production promotion;
- preserve as a future execution-transfer candidate.

---

# 4. 25-SEP-2026 FORWARD SAMPLE — 155 CLOSED BROAD TRADES

Source:
`ReportHistory-1514715065_ftmo(1).xlsx`

Closed Broad trades analyzed: **155**

Actual ranking:

| Method | N | Net EV | PF | WR |
|---|---:|---:|---:|---:|
| DOM | 41 | +0.133R | 1.54 | 63.4% |
| BASE | 54 | +0.002R | 1.01 | 55.6% |
| MIX | 49 | -0.209R | 0.49 | 40.8% |
| REV | 11 | -0.475R | 0.045 | 18.2% |

Combined:
- BASE + DOM = profitable
- MIX + REV = main source of losses on this forward day

This is strong forward evidence but **not enough to override long-history regime dependence**.

---

# 5. WHICH LEG WAS MOST ACCURATE?

Directional precision during first ~5 minutes:

| Leg | Approx directional hit | Favorable excursion | Adverse excursion |
|---|---:|---:|---:|
| DOM_CONT | ~69% | +0.664R | 0.350R |
| DOM2 | ~68% | +0.431R | 0.363R |
| BASE1 | ~56% | +0.357R | 0.338R |
| MIXED | ~46% | +0.343R | 0.571R |
| MIX2 | ~36% | +0.280R | 0.528R |
| REV2 | ~33% | small N | small N |
| REV1 | ~25% | +0.110R | 0.583R |

Current forward ranking:
**DOM_CONT > DOM2 > BASE1 >>> MIX > REV**

Important:
- DOM accuracy is not just higher P/L;
- favorable excursion is larger than adverse excursion;
- MIX/REV often fail already at entry/state interpretation.

---

# 6. SIDE ASYMMETRY — 25-SEP SAMPLE

Approx method EV by side:

| Method | BUY EV | SELL EV |
|---|---:|---:|
| BASE | +0.003R | ~0R |
| DOM | +0.214R | +0.019R |
| MIX | -0.270R | -0.128R |
| REV | -0.592R | -0.408R |

Important observations:
- **DOM BUY** was the strongest side/method combination;
- DOM_CONT BUY was especially strong;
- REV BUY was the weakest;
- do NOT create a blanket BUY-only rule from one day.

Need long-history side x regime confirmation before production changes.

---

# 7. EXIT STUDY — HOLD 5 / 10 / 15 / 30 MIN x TP 0.5 / 1 / 1.5 / 2R

Production-relevant interpretation respects:
**TP >= 1.5R**

## BASE1
Key result:
- 5m / TP1.5 -> ~+0.007R
- **10m / TP1.5 -> ~+0.169R, PF ~1.57**
- 10m / TP2 -> ~+0.148R
- 15m weaker
- 30m negative

Interpretation:
**BASE is primarily an exit-timing problem.**
5-minute timeout is probably too short.
Current best research candidate: ~10m hold with >=1.5R TP.

Not production-ready until replicated.

## DOM2
- 5m / TP1.5 -> ~+0.102R
- **10m / TP1.5 -> ~+0.118R**
- longer holds degrade

Interpretation:
DOM2 works around 5–10 minutes.
No evidence for long holding.

## DOM_CONT
- **5m / TP1.5 -> ~+0.212R**
- 10m weaker
- 15m can turn negative

Interpretation:
**current short timeout is already good for DOM_CONT.**
Do not lengthen it globally.

## MIX2
- negative at 5m;
- remains negative at 10/15m;
- 30m can reduce damage but still not produce robust positive edge.

Interpretation:
**MIX2 is mainly an ENTRY/STATE problem, not an EXIT problem.**

## MIXED
Same conclusion:
- changing timeout/TP does not reliably rescue it.

Interpretation:
**ENTRY/STATE problem.**

## REV1
- very negative at 5m;
- longer hold reduces loss substantially;
- still not convincingly positive.

Interpretation:
REV may identify a future reversal state, but the market-entry timing is too early.

## REV2
Some longer-hold cells looked positive, but:
- N=3 in this forward sample;
- no conclusion allowed.

---

# 8. TP / PROFIT REACH DIAGNOSTIC

TP0.5R was used **only as a diagnostic**, not as a proposed production TP.

Approx 5m TP0.5 hit rate:
- DOM ~49%
- MIX ~33%
- BASE ~28%
- REV 0%

Interpretation:
- DOM most often creates immediate meaningful favorable movement;
- MIX can briefly move in the signal direction, but adverse excursion is much larger;
- REV usually does not produce immediate reversal follow-through.

Production rule remains:
**TP must be >= 1.5 x stop.**

---

# 9. WHAT DRIVES PROFIT BY SIGNAL TYPE?

This is now the central research question.

## BASE
Strong clue:
**short-term price impulse confirmation matters.**

5m aligned impulse:
- BASE aligned -> approx +0.166R, PF ~1.77
- BASE counter/not aligned -> approx -0.040R, PF <1

30–60m broader direction also appears useful.

Working interpretation:
BASE is an **early warning / candidate signal**.
It should probably not always execute immediately.

Candidate architecture:
`BASE event -> wait for price-response / impulse confirmation -> entry`

Need causal historical validation.

---

## DOM
Strong clue:
**broader persistence/trend matters more than 3–5m impulse.**

DOM stays profitable even when immediate short impulse is not aligned.

Approx 30m direction:
- aligned DOM -> ~+0.260R, PF ~1.91
- counter DOM -> ~+0.096R, PF ~1.40

Working interpretation:
DOM already contains persistence/order-flow information.

Candidate architecture:
`DOM event + broader trend/regime context -> trade`

Do NOT require a strict 3–5m impulse filter yet; it may remove good pullback entries.

---

## MIX
Trend alignment reduces losses but does not reliably create positive edge.

Working interpretation:
MIX means the order-flow state is conflicted / unstable.
The bot probably changes its mind too easily.

Need to study:
- whether MIX should become observation-only;
- whether MIX needs persistence confirmation;
- whether first-side dominance should remain authoritative until stronger contrary evidence appears.

Do not disable yet without long-history validation.

---

## REV
Current forward evidence suggests:
**REV event != REV entry**

REV likely detects the beginning of a reversal process before price confirms it.

Candidate architecture:
`REV detected -> WAIT -> reversal confirmation -> entry`

Possible confirmation families to test:
- price reclaim / break;
- opposite impulse;
- failed continuation of previous dominance side;
- microstructure response;
- 30–120s delayed confirmation;
- M1 close confirmation.

Do NOT simply lengthen the timeout and call it fixed.

---

# 10. NEXT LABS — PRIORITY ORDER

## P0 — preserve forward logging
Broad Demo remains unchanged until research proves a production change.

Log for every signal:
- timestamp UTC
- leg
- side
- episode state
- XAU entry
- SL / TP
- +1m / +3m / +5m / +10m / +15m / +30m virtual outcome
- MFE / MAE
- timeout outcome
- H1/H4 trend state
- 3m / 5m / 15m / 30m price impulse
- spread / commission / slippage if available
- final actual execution result

## P1 — LAB022 `BROAD_SIGNAL_QUALITY_MODEL`
Goal:
determine **when each leg deserves an actual order**.

Frozen factors to test:
- LEG
- SIDE
- causal H1 trend
- causal H4 trend
- H1&H4 alignment
- 3m impulse
- 5m impulse
- 15m impulse
- 30m trend / directional persistence

Primary outputs:
- N
- directional hit-rate
- EV
- PF
- MFE
- MAE
- SL rate
- TP1.5 reach
- TP2 reach
- stability TRAIN / VALID / POST

Do not threshold-hunt on full sample.
Derive on TRAIN only, freeze, then test VALID/POST.

## P1 — LAB023 `BASE_CONFIRMATION_AND_EXIT`
Frozen BASE hypothesis:
- raw BASE weak;
- BASE + aligned price response may have edge;
- 5m timeout too short;
- ~10m appears better.

Test:
- immediate entry vs 1/3/5m confirmation;
- impulse confirmation;
- 5m vs 10m vs 15m hold;
- TP >=1.5R only for production candidates.

## P1 — LAB024 `DOM_PERSISTENCE_TREND_FILTER`
Test:
- DOM2 and DOM_CONT separately;
- BUY vs SELL;
- 15m / 30m / H1 / H4 trend alignment;
- pullback-vs-impulse entry state;
- preserve 5m DOM_CONT baseline.

Question:
Can broader trend identify high-quality DOM without destroying trade count?

## P1 — LAB025 `REV_CONFIRMATION_DELAY`
Do NOT change REV definition first.

Test:
- REV event at t0;
- entry only after causal confirmation;
- delays 30s / 60s / 120s / M1 close;
- reclaim / failed prior-side continuation;
- impulse reversal confirmation;
- exact execution with original SL/TP constraints.

Goal:
determine whether REV is a good **event detector** but bad immediate entry.

## P2 — LAB026 `MIX_STATE_VALIDITY`
Question:
Is MIX an actual tradable state, or should it be observation-only?

Test:
- persistence after conflict;
- return to original dominance;
- confirmation of new side;
- H1/H4 and 30m trend context;
- side asymmetry;
- execution delay.

Do not disable MIX until long-history causal result exists.

## P2 — leg-specific timeout router
Only after LAB022–026.

Candidate concept to validate:
- BASE -> ~10m
- DOM2 -> 5–10m
- DOM_CONT -> ~5m
- MIX -> no immediate production trade unless confirmed
- REV -> delayed/confirmed entry

Do not hardcode this yet.

---

# 11. BROKER / EXECUTION REQUIREMENT BEFORE EA CHANGES

Before modifying production/demo EA execution logic, confirm target environment:

- broker / prop firm
- account type
- average XAUUSD spread
- commission per lot round-turn
- STOPLEVEL
- freeze level
- EA allowed
- hedging rules
- news trading rules
- leverage
- min lot / lot step
- swaps
- VPS latency
- realistic slippage
- prop challenge rules/link if applicable

No final execution optimization should be promoted without these.

---

# 12. CURRENT WORKING MODEL OF THE FOUR SIGNALS

## BASE
**Early warning / setup candidate**
- moderate directional accuracy
- needs price confirmation
- probably needs longer hold than 5m

## DOM
**Best current actual trade signal**
- highest directional precision
- persistence survives pullbacks
- broader trend strengthens it
- DOM_CONT especially strong in current forward sample

## MIX
**Conflict / uncertainty state**
- weak accuracy
- adverse excursion too large
- timeout does not solve core problem
- needs state validation before entry

## REV
**Potential reversal event, not immediate trade**
- low immediate directional precision
- often too early
- needs delayed causal confirmation

---

# 13. DO NOT FORGET

1. Do not optimize all four signals with one exit rule.
2. Entry quality and exit quality must be studied separately.
3. DOM's strong 25-Sep result does not override long-history regime dependence.
4. BASE may become useful through confirmation + exit timing.
5. MIX and REV should not be “fixed” only by moving TP/timeout.
6. REV likely requires confirmation after the event.
7. Always preserve BUY/SELL separately.
8. Always preserve DOM2 vs DOM_CONT and REV1 vs REV2 separately.
9. TP >= SL * 1.5 for any production candidate.
10. Prefer confirmation / limit entry where possible.
11. Forward demo remains the arbiter after historical causal validation.
12. Avoid curve fitting: TRAIN -> freeze -> VALID -> POST.
13. Keep Q65 separate and frozen.
