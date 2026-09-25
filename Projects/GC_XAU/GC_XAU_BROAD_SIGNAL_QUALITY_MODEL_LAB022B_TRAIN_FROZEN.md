# GC_XAU LAB022B — LEG_SPECIFIC_SIGNAL_QUALITY_MODEL — TRAIN-FROZEN AMENDMENT

Frozen: 2026-09-25, BEFORE reading W6-W9 outcomes.

Reason:
LAB022A universal additive ridge/logistic score is rejected on TRAIN because the fixed prereg TRADE gate (pUP >= 0.55) produces zero TRADE observations. This is a TRAIN-only model-form failure, not an OOS result.

The TRAIN diagnostics also show different legs are driven by different contexts. Therefore the prereg instruction "if fail, study separate leg-specific confirmation models" is activated before VALID/POST is opened.

## Construction
For each leg select exactly three TRAIN-derived binary votes:
1. SIDE vote = the better TRAIN side.
2. TREND vote = strongest absolute TRAIN uplift among H1 aligned, H4 aligned, BOTH aligned. Direction of the vote follows the TRAIN uplift sign.
3. IMPULSE vote = strongest positive TRAIN uplift among IMP3 / IMP5 / IMP15 / IMP30; favorable state is aligned impulse > 0.

No magnitude threshold search.

## Frozen votes
- BASE1: BUY + BOTH aligned + IMP5 aligned.
- DOM2: BUY + BOTH aligned + IMP5 aligned.
- DOM_CONT: BUY + BOTH aligned + IMP15 aligned.
- MIX2: BUY + BOTH aligned + IMP5 aligned.
- MIXED: BUY + H1 aligned + IMP3 aligned.
- REV1: BUY + H4 NOT aligned + IMP5 aligned.
- REV2: BUY + BOTH aligned + IMP15 aligned.

## Quality class
Score = number of favorable votes, 0..3.
- TRADE = 3/3
- WATCH = 2/3
- REJECT = 0-1/3

## OOS pass
Useful only if, in both VALID and POST:
- TRADE EV5 > 0
- TRADE PF-like > 1
- TRADE hit-rate > 52%
- TRADE EV > WATCH EV > REJECT EV, or at minimum TRADE > both other buckets
- at least 3 legs contribute >=5% each to TRADE bucket
- positive TRADE result appears in at least 3 of W6-W9, not one window only

No rule changes after W6-W9 outcomes are read.
