# GC_XAU_CROWDFade_STALL_EARLY_SIGNAL_TO_5MIN_UNWIND_LAB003_PREREG

**Status:** PREREGISTERED_BOUNDED_EXECUTION_AUDIT_NOT_OOS

## Frozen trigger
Exactly the LAB002 30s_FADE_STALL mechanism:
- 30-second non-overlapping GC buckets
- explicit aggressor AMP/CQG trades only
- causal prior 1-hour Q90 abs(delta_frac) and Q75 volume
- extreme effort = abs(delta_frac)>=Q90 AND volume>=Q75 AND nonzero delta
- signed crowd impact = sign(delta)*(close-open)/prior completed GC M1 ATR14
- STALL = signed crowd impact <= +0.05 GC ATR
- direction = opposite the GC crowd
- 60-second event cooldown
- no trigger retuning

## Question
Does the early 30s GC crowd-stall signal precede a larger XAU unwind over the next 1-5 minutes, and can a bounded entry geometry overcome XAU spread/friction?

## XAU clock/execution
- frozen FTMO clock = GC UTC +180 minutes
- raw FTMO Bid/Ask ticks
- LONG executable entry/exit uses Ask/Bid
- SHORT executable entry/exit uses Bid/Ask
- XAU ATR14 from prior completed broker M1

## Frozen path horizons
10s, 30s, 60s, 120s, 180s, 300s from trigger end.
For the first 5 minutes also record MFE, MAE, time to MFE, and first passage to +/-0.25 ATR and +/-0.50 ATR.

## Frozen entry variants
A. MARKET_NOW: enter first executable quote at trigger end.
B. LIMIT_RETRACE_010: LONG buy limit at initial Ask -0.10 ATR; SHORT sell limit at initial Bid +0.10 ATR; expiry 30s; no chase after expiry.
C. CONFIRM_005: wait for XAU mid to move +0.05 ATR in predicted fade direction within 30s, then enter first executable quote; otherwise no entry.
All variants use hard exit clock trigger+5m. No depth/expiry/confirmation sweep.

## Frozen R:R diagnostic
- G1: SL 0.25 ATR / TP 0.50 ATR (1:2)
- G2: SL 0.30 ATR / TP 0.45 ATR (1:1.5)
- first-passage on raw Bid/Ask
- hard timeout at trigger+5m

## Discovery split
- TRAIN: before 2026-08-20 00:00 UTC
- VALID: 2026-08-20 00:00 UTC through 2026-09-06 22:00 UTC
- POST_CHECK: after VALID; not used for promotion

## Promotion logic
No production promotion from LAB003 alone.
A variant is called a historical execution candidate only if TRAIN fills>=10, VALID fills>=10, TRAIN and VALID 300s fixed-hold EV>0, VALID PF>=1.10 on at least one frozen R:R geometry, and VALID R:R geometry EV>0.

Historical bounded audit only; not OOS certification and not EA authorization.
