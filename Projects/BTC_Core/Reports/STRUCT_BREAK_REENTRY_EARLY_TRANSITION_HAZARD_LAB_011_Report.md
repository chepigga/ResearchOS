# STRUCT_BREAK_REENTRY_EARLY_TRANSITION_HAZARD_LAB_011

**Date:** 2026-08-25  
**Status:** COMPLETED  
**Preregistration commit:** `14625682a444927e30ac87a050bf4b295fa33f46`  
**Formal verdict:** `EARLY_TRANSITION_REENTRY_REJECTED`

## Question
Can the `LOW -> recovery/scratch -> renewed movement` transition be detected on a 5m/15m event clock early enough to support a fresh `TP=1.5R / SL=1R` trade?

## Frozen design
- DEV 2019–2022; VAL 2023–2025; 2026 excluded.
- Frozen LAB008 LOW30 and LAB009A scratch/re-arm population.
- Scratch bar excluded; fully closed M5 only.
- Decision every 5m from 15m through 60m post-scratch.
- Features limited to `NET_R`, `MAE_R`, `CLOSEBACK_FRAC`, `DIR_CLOSE_FRAC` on 5m/15m windows.
- DEV-only standardized logistic regression, C=0.3, setup-equal weights.
- Trigger = first crossing of DEV q67 score threshold.
- Fresh stop = 1.0× ATR14(M5); TP=1.5R; cost=0.06R; no BE/trailing.

## Result
Candidate discrimination fails to transfer:
- DEV AUC **0.551**
- VAL AUC **0.467**

Fresh re-entry:
- DEV N=145, EV **-0.112R**, TP 37.9%
- VAL N=139, EV **-0.161R**, 95% CI **[-0.359,+0.037]**, PF 0.76, TP 36.0%

Fair resolved TP probability after cost is ~42.4%; VAL actual is **36.0%**.

VAL yearly EV:
- 2023: -0.171R
- 2024: -0.276R
- 2025: -0.013R
- positive years: 0/3

## Timing test
The early trigger genuinely entered sooner:
- 80 VAL setups triggered by both methods;
- median **45 min earlier** than LAB009B 30m-HIGH;
- earlier in 92.5% of common cases.

Thus LAB010 did not fail merely because confirmation was too late.

## Full portfolio
VAL canonical:
- EV -0.031R/trade
- Max DD 38.78R

LAB011 adaptive:
- EV **-0.071R/trade**
- improvement **-0.040R/trade**
- Max DD **69.87R** (+80.2%)

## Fixed-horizon diagnostic
- 15m VAL AUC 0.534; selected EV -0.028R, TP 41.3%
- 30m VAL AUC 0.382
- 45m VAL AUC 0.386
- 60m VAL AUC 0.474

DEV becomes apparently strong at 30–45m, but the relation reverses OOS.

## M1 replication
Exact M1 replay 2024–2025 gives 100% outcome agreement with M5.

# Verdict
`EARLY_TRANSITION_REENTRY_REJECTED`

LAB008 remains valid: path state after the original entry is informative. What fails is monetizing LOW/recovery as a second independent full-risk 1.5R trade.

Next clean direction: `STRUCT_BREAK_LOW_PARTIAL_DERISK_X_READD_LAB_012` — adaptive exposure reduction/restoration rather than flat exit and fresh re-entry.