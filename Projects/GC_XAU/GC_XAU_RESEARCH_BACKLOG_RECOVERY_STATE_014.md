# GC_XAU_RESEARCH_BACKLOG_RECOVERY_STATE_014

Updated: 2026-09-25

## New completed result — LAB022 SIGNAL_QUALITY_MODEL

Universal Broad quality router: FAIL.

Main causal factor ranking on TRAIN:
1. 5m aligned impulse +0.105 ATR uplift
2. 3m aligned impulse +0.090
3. 15m aligned impulse +0.074
4. 30m aligned impulse +0.070
5. H1&H4 BOTH alignment +0.046
6. H1 +0.043
7. H4 +0.024

Therefore impulse is generally more informative than trend, but factor importance is leg-specific.

### Frozen leg-specific OOS winner
`MIX2_BUY_BOTH_HTF_IMP5_001`

Rule:
- MIX2
- BUY
- H1 aligned
- H4 aligned
- causal 5m XAU impulse aligned

Raw:
- TRAIN N976 EV +0.0756 ATR
- VALID N387 EV +0.1466, PF 1.256
- POST N222 EV +0.0930, PF 1.159
- W6/W7/W8/W9 all positive

Execution proxy:
- VALID net +0.0035R
- POST net -0.0334R
Therefore signal-quality PASS, execution FAIL.

### Other leg-specific OOS results
- BASE quality rule FAIL
- DOM2 quality rule FAIL
- DOM_CONT +VALID / -POST -> regime unstable
- MIXED FAIL
- REV1 near-flat / unstable
- REV2 unstable and too small

## Updated priority
P1: LAB023A `MIX2_BUY_BOTH_IMP5_EXECUTION_TRANSFER`
- freeze signal
- optimize execution only
- market vs confirmation vs retracement/limit
- TP >=1.5R
- realistic costs
- 5/10/15m hold

P1 retained:
- BASE_CONFIRMATION_AND_EXIT
- DOM_PERSISTENCE_TREND_FILTER
- REV_CONFIRMATION_DELAY

Do not change Broad Demo or Q65 yet.
