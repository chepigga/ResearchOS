# XAU_VWAP_TOUCH_RESPONSE_VS_ACCEPTANCE_CAUSAL_MAP_LAB_002 — v001 REPORT

**Verdict:** `CAUSAL_MAP_TRANSFERABLE`  
**Secondary caution:** `NOT_YET_VWAP_SPECIFIC` — the map proves that the first 1–5 minute path after a VWAP touch strongly separates later rejection from acceptance, but this LAB does not yet prove that the same sequence would fail around placebo/non-VWAP levels.  
**Holdout opened:** `false`

## Canonical audit

- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Raw M1 rows: 1,454,538
- Rows used pre-holdout: 1,080,929
- Period used: 2022-06-01 01:05:00 -> 2025-06-30 23:49:00
- VWAP touch candidates: 71,641
- Mapped causal events: 71,561
- Discovery events: 37,834
- Confirmation events: 33,727
- MID/HIGH/LOW: 26,667 / 23,155 / 21,739

## Core transferable map

Primary future label begins only after T+5m. REJECTION means the +0.50 ATR barrier back toward the arrival side is reached before the -0.50 ATR acceptance barrier through the level.

| T+5 state | Discovery rejection | Confirmation rejection | Interpretation |
|---|---:|---:|---|
| NO_PENETRATION | 84.6% (N=13,372) | 85.8% (N=11,940) | strong rejection |
| EARLY_REJECTION | 72.8% (N=6,299) | 72.5% (N=5,524) | rejection |
| RECLAIM_CHOP | 41.1% (N=2,832) | 42.1% (N=2,620) | slight acceptance / noisy |
| OTHER | 33.7% (N=4,020) | 35.4% (N=3,490) | acceptance-leaning |
| EARLY_ACCEPTANCE | 15.0% (N=10,543) | 14.0% (N=9,469) | strong acceptance |

The ranking and magnitude transfer almost unchanged. This is much stronger than LAB001's handcrafted CENTER+FAILED_RECOVERY branch.

## Earliest causal recognition

A simple signed distance at the decision clock already rank-orders the later path:

| Clock | State | Discovery rejection | Confirmation rejection |
|---|---|---:|---:|
| T+1m | THROUGH_>0.10 | 29.1% | 28.4% |
| T+1m | BACK_>0.10 | 72.4% | 73.1% |
| T+3m | THROUGH_>0.10 | 22.0% | 21.3% |
| T+3m | BACK_>0.10 | 78.9% | 79.2% |
| T+5m | THROUGH_>0.10 | 15.8% | 15.2% |
| T+5m | BACK_>0.10 | 84.6% | 85.3% |

Thus recognition begins by T+1m and strengthens through T+3/T+5. That motivates a separate executable-entry frontier LAB rather than waiting automatically for a 5m confirmation.

## Feature maps

### Penetration depth

Confirmation rejection rate falls monotonically from **89.6%** when there is no penetration to **38.4%** when 5m penetration exceeds 0.10 ATR. Discovery shows the same 88.7% -> 38.7% structure.

### Fraction of closes beyond level

Confirmation rejection falls from **85.8%** with zero closes beyond to **13.1%** when 80–100% of the first five closes are beyond. Discovery: 84.6% -> 14.4%. This is the cleanest direct measurement of acceptance.

### Arrival speed

As signed 5m approach speed increases, rejection probability declines monotonically. Confirmation: about **67.3%** in the weakest/away bucket to **41.3%** at >1 ATR approach speed. Discovery: 64.9% -> 41.5%. Strong attack into the level is materially more likely to break/accept than reject.

## Level and direction transfer

The T+5 state map is nearly identical across MID, HIGH and LOW. In Confirmation:

- EARLY_ACCEPTANCE rejection: HIGH 14.9%, LOW 12.9%, MID 14.0%.
- EARLY_REJECTION rejection: HIGH 71.3%, LOW 71.9%, MID 74.4%.
- NO_PENETRATION rejection: HIGH 85.0%, LOW 86.4%, MID 85.9%.

Arrival from ABOVE and BELOW also mirrors closely, so the mechanism is not a one-sided BUY/SELL artifact.

## Yearly transfer

- 2022: EARLY_ACCEPTANCE rejection 15.9%; EARLY_REJECTION 74.6%; NO_PENETRATION 84.8%.
- 2023: EARLY_ACCEPTANCE rejection 14.5%; EARLY_REJECTION 71.8%; NO_PENETRATION 84.5%.
- 2024: EARLY_ACCEPTANCE rejection 14.3%; EARLY_REJECTION 73.2%; NO_PENETRATION 85.5%.
- 2025: EARLY_ACCEPTANCE rejection 13.3%; EARLY_REJECTION 71.1%; NO_PENETRATION 86.3%.

No year reverses the core ordering.

## iFVG incremental value

The podcast's iFVG is **secondary**, not the main information source. Once the 5m response state is known:

- In EARLY_REJECTION, a rejection-aligned confirmed iFVG improves rejection probability versus no iFVG by about **+6.4 pp** in Discovery and **+9.2 pp** in Confirmation.
- In EARLY_ACCEPTANCE, an acceptance-aligned iFVG does **not** improve acceptance versus no iFVG; the incremental value is weak/negative.
- A rejection-aligned iFVG inside EARLY_ACCEPTANCE acts as a modest counter-signal (~+5.4 pp rejection in both periods), but does not overturn the dominant acceptance path.
- In RECLAIM_CHOP the iFVG categories do not transfer cleanly.

Interpretation: **penetration / closes-beyond / current side of VWAP contain most of the signal; iFVG can refine some rejection states but is not the engine.**

## Sensitivity of future label

The unconditional rejection base rate is stable across 0.25 / 0.50 / 0.75 ATR barriers and across splits (~53–55%). The strong state separation is therefore not being created by a severely imbalanced primary label.

## What this LAB proves

It supports the podcast's central behavioural idea:

> Do not trade the VWAP touch. Read what price does immediately after the touch.

The market distinguishes two paths very clearly: hold/reclaim back to the arrival side versus sustained closes through the level. The information is visible causally by T+1m and becomes very strong by T+3–5m.

## What this LAB does NOT prove

It does not yet prove a VWAP-specific economic edge. Because the future label is defined around the touched level, some of the strong separation may be generic short-horizon path persistence that would also occur around arbitrary/placebo levels. No live/EA allocation is authorized.

## Next required LAB

`XAU_VWAP_SEQUENCE_PLACEBO_AND_EXECUTION_FRONTIER_LAB_003`

Freeze the LAB002 touch/state logic, then:
1. compare real tick-volume VWAP levels against same-clock unweighted anchored mean and matched placebo levels;
2. test executable decision clocks T+1 / T+3 / T+5 without changing the outcome definition;
3. only if VWAP beats placebo, move to 1.5R/2R and next-VWAP-level economics.
