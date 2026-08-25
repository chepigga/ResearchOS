# STRUCT_BREAK_SECOND_BREAK_QUALITY_DECOMPOSITION_LAB_014

**Date:** 2026-08-25  
**Preregistration:** `7f31abe9fcfdb48d39b6535d0a8ed4b1dfb5ae1d`  
**Verdict:** `QUALITY_BLOCK_TRANSFER_SIGNAL__RECOVERY_ONLY_WEAK`

## Population
LAB013 M5 BREAK2 entries: DEV 93, VAL 82. Target: fresh BREAK2 TP1.5R vs SL. 2026 excluded.

## Block transfer
| Block | DEV AUC | VAL AUC |
|---|---:|---:|
| LOW severity | 0.621 | 0.538 |
| **Recovery quality** | **0.623** | **0.595** |
| New-structure maturity | 0.692 | 0.524 |
| BREAK2 acceptance | 0.674 | 0.478 |
| Retest quality | 0.711 | 0.467 |
| All 39 features | 0.861 | 0.480 |

Only recovery quality clears the preregistered 0.58 VAL-AUC diagnostic gate. Its VAL bootstrap CI is approximately [0.465, 0.719], so this is a weak transfer seed, not a trading selector.

## Recovery-quality interpretation
The useful information is in the path from LOW toward RESET: recovery efficiency, favorable-close persistence, timing and two-way travel. No single feature is independently strong; no univariate feature survives BH multiple-comparison correction.

A DEV-frozen recovery-score tertile diagnostic gives on VAL:
- LOW: N34, TP 35.3%, EV -0.178R
- MID: N25, TP 40.0%, EV -0.060R
- HIGH: N23, TP 56.5%, EV +0.353R

This is descriptive only. Yearly AUC weakens from 0.817 in 2023 to 0.563 in 2024 and 0.490 in 2025.

## The LAB013 “80% TP” subgroup
We separately tested whether the five causal blocks can distinguish, before ENTRY2, cases whose original canonical path will later be TP2.3R versus SL. They cannot robustly do so. Best block VAL AUC is only ~0.567 and the combined model is ~0.517.

Thus the striking 80% vs 22% second-break split by future FIRST-trade fate is not causally identifiable from these blocks.

Recovery quality still has some information about BREAK2's own outcome even inside canonical-SL cases (VAL AUC ~0.603), so it is not merely a disguised future FIRST-fate label.

## Falsified visual hypotheses
No transferable block-level edge was found in:
- more mature post-reset structure;
- more pivots;
- stronger BREAK2 penetration;
- clearing the full post-reset range;
- stronger break candle;
- retest timing/excursion.

## Conclusion
The only stage worth independent replication is `LOW -> recovery/reset quality`. Do not optimize a trading threshold on LAB014 VAL. A future replication should freeze the recovery-quality score from DEV and test it on an independent population.