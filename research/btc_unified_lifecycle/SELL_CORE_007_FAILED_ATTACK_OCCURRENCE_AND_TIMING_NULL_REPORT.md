# SELL_CORE_007 — FAILED_ATTACK_OCCURRENCE_AND_TIMING_NULL — CANONICAL REPORT

## Frozen design

Primary treated population = every first causal FAILED_ATTACK emitted by lifecycle-safe SELL_CORE_006B. No future STRUCTURE_BREAK requirement. SELL next M1 open, SL 1.5× completed H1 ATR14, no TP, 48h primary / 72h sensitivity, frozen cost proxy.

Timing null conditions on failure-containing correction episodes and compares the failed-attack timestamp to earlier READY-state M15 decisions in the same correction episode and exact H4 ST age.

Occurrence null uses a causal risk set: other correction episodes at the same elapsed correction age, same year, exact H4 ST age, H4 still bearish, lifecycle state READY, and no failed attack known yet. Controls may fail later. Nearest ATR% is K1 primary matching; K5 is sensitivity.

## Unconditional causal result

42 first failed attacks across 33 H4 episodes over 136 weeks (~0.309/week). Only 13/42 later reached the structure-break sequence used in SELL_CORE_006.

- 48h: EV **-0.2365R**, PF **0.723**, price EV **-0.3000%**.
- 72h: EV **-0.1863R**, PF **0.786**, price EV **-0.2997%**.
- Cluster bootstrap P(EV>0): 23.9% at 48h and 28.9% at 72h.

Yearly 48h:
- 2024 N14: **-0.7659R**
- 2025 N17: **-0.2471R**
- 2026 N11: **+0.4535R**

Therefore first failed attack is **not a standalone SELL rule**.

## Timing null

Exact same-correction / exact-H4-age timing comparison matched 27/42 events (64.3%). The other 15 events had correction delay = 0, so no earlier same-correction control exists by construction.

Matched delayed failures:
- 48h treated -0.2861R vs control -0.4230R; delta **+0.1370R**, CI [+0.0146,+0.3220], P(delta>0)=99.57%.
- 72h treated -0.5357R vs control -0.6825R; delta **+0.1467R**, CI [+0.0003,+0.4162], P(delta>0)=99.0%.

But yearly delta is not stable:
- 2024: +0.107R (48h)
- 2025: approximately 0R
- 2026: +0.316R

Interpretation: for delayed failures, the failed-attack timestamp contains **relative timing information** versus being short earlier in the same correction state, but both treated and controls are negative in aggregate. This is not standalone execution edge.

## Occurrence risk-set

Exact risk-set matching covered only 21/42 events (50%). K1 produced an attractive aggregate delta:
- 48h: treated +0.2017R vs control -0.5591R; delta +0.7608R; P=95.45% but CI still crosses zero [-0.0807,+1.8650].
- 72h: treated +0.3026R vs control -0.8162R; delta +1.1188R; CI [+0.0010,+2.4651], P=97.53%.

K5 weakened materially and did not clear a 95% criterion.

### Mandatory coverage audit

The matched half is structurally different from the unmatched half:

- Matched N21: mean H4 ST age **20.5**, correction delay 0.76h, EV48 **+0.2017R**.
- Unmatched N21: mean H4 ST age **48.2**, correction delay 1.31h, EV48 **-0.6748R**.
- Market-clock composition: B4 has **1 matched vs 9 unmatched** events.

Occurrence delta by year (K1, 48h):
- 2024 N7: **-0.256R**
- 2025 N9: **+0.627R**
- 2026 N5: **+2.425R**

Thus the attractive matched occurrence result is not representative of all failures and is strongly associated with matchability / earlier H4 age plus modern regime performance. It is **not promoted**.

## Canonical verdict

1. **FAILED_ATTACK standalone SELL: REJECT.** Unconditional 42-event population is negative in R and price space.
2. **Exact failed-attack timing: RELATIVE TIMING CANDIDATE, not tradable edge.** It beats earlier same-correction timestamps for delayed events, but both sides remain negative and the effect is not clean 3/3 by year.
3. **Occurrence selector: NOT PASSED.** Exact-age risk-set coverage is only 50%, matched events are a much earlier-H4 and much more profitable subset, and 2024 occurrence delta is negative.
4. SELL_CORE_006's +0.82R completed-sequence result is confirmed to be future-conditioned selection: only 13/42 failures later broke structure.

The next research question should not add a new indicator. It should explain why the 13/42 failures that later produce seller acceptance differ *causally before that acceptance*, without conditioning on the future structure break.
