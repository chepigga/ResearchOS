# SELL_CORE_008 — POST_FAILED_ATTACK_EARLY_RESPONSE — RESULT

## Verdict

**FAIL as a tradable 3/5 EARLY SELL rule; PASS as an information-localization result.**

Frozen population: all first causal failed attacks from lifecycle-safe SELL_CORE_006B. No future structure-break requirement. Post-failure M5 response was measured at 15/30/60 minutes using five preregistered features: bearish displacement, bearish efficiency, repeated reclaim, acceptance below failure close, and causal lower-high. Natural composite = 3 of 5 bearish votes. No threshold optimization.

## Coverage

| Horizon | Eligible | 3/5 pass | Future break winners eligible | Pass winner rate |
|---:|---:|---:|---:|---:|
| 15m | 42 | 23 | 13 | 39.1% |
| 30m | 42 | 24 | 13 | 50.0% |
| 60m | 40 | 22 | 12 | 54.5% |

At 30m the gate captured 12/13 eligible winners. At 60m it captured 12/12 eligible winners, but admitted 10 false positives.

## Winner/non-winner response separation

The response sequence clearly separates future first-failure structure-break winners from other failed attacks:

### 15m
- bearish displacement: +0.195 ATR vs -0.030 ATR
- bearish efficiency: +0.440 vs -0.063
- acceptance below: 71.8% vs 50.6%
- repeated reclaim: 15.4% vs 34.5%
- mean bearish votes: 3.31 vs 2.24

### 30m
- bearish displacement: +0.296 ATR vs -0.171 ATR
- bearish efficiency: +0.327 vs -0.107
- acceptance below: 79.5% vs 48.9%
- repeated reclaim: 15.4% vs 55.2%
- mean bearish votes: 3.85 vs 2.31

### 60m
- bearish displacement: +0.560 ATR vs -0.215 ATR
- bearish efficiency: +0.306 vs -0.063
- acceptance below: 81.3% vs 44.6%
- repeated reclaim: 16.7% vs 67.9%
- mean bearish votes: 4.33 vs 2.14

`lower_high` was weak at 15/30m and only became directionally useful by 60m. The strongest information is displacement + directional efficiency + acceptance below + absence of reclaim.

## Trading result of frozen 3/5 gate

| Horizon | N | EV48 | PF48 | EV price 48h | EV72 | PF72 |
|---:|---:|---:|---:|---:|---:|---:|
| 15m | 23 | -0.601R | 0.355 | -0.610% | -0.647R | 0.319 |
| 30m | 24 | -0.027R | 0.970 | -0.238% | -0.321R | 0.649 |
| 60m | 22 | +0.080R | 1.092 | -0.237% | -0.261R | 0.710 |

60m slight positive R is not accepted because price-space EV remains negative and bootstrap is weak.

## Paired timing versus immediate failed-attack entry

Waiting 15/30/60m did **not** improve paired outcome on the same selected events. In price space it consistently worsened entry. Therefore fixed waiting itself is not the alpha.

## Why the gate fails despite strong response separation

At 30m, selected future winners averaged approximately +0.961R over 48h, while selected non-winners averaged approximately -1.015R. At 60m, winners averaged approximately +0.967R and non-winners approximately -0.984R. The 3/5 gate therefore found the correct winner population with high recall, but precision remained only about 50–55%, so false positives erased the edge.

## Year transfer

2024 remains strongly negative at every horizon. 2026 is strongly positive at 30/60m; 2025 is near flat to weak positive by 60m. Therefore the frozen gate is not stable across years and cannot be promoted.

## Canonical interpretation

SELL information is indeed concentrated in the **post-failed-attack response sequence**, not in Funding/FVG/fixed B3 timing or full structure-break confirmation. The next research problem is no longer `when to enter after failure`; it is **how to causally reject the false-positive failed attacks where buyers regain control** without post-hoc threshold mining.

Do not promote a stricter score threshold from this LAB. Any next false-positive rejection rule must be separately preregistered and validated.
