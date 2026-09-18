# GC_XAU_CROWDFade_DIRECTIONAL_BIAS_TRANSFER_LAB005_PREREG

**Status:** PREREGISTERED_DIRECTIONAL_BIAS_AUDIT_NOT_OOS

## Purpose
Test whether frozen GC crowd-fade information is useful as a directional bias for XAUUSD, independent of entry timing, spread, stop, target, or trade management.

## Frozen parent trigger
Exactly LAB002/LAB004 30s_FADE_STALL:
- 30-second non-overlapping GC buckets
- explicit aggressor AMP/CQG trades only
- causal prior 1-hour Q90 abs(delta_frac) and Q75 volume
- extreme effort = abs(delta_frac)>=Q90 AND volume>=Q75 AND nonzero delta
- signed crowd impact = sign(delta)*(close-open)/prior completed GC M1 ATR14
- STALL = signed crowd impact <= +0.05 GC ATR
- directional bias = opposite GC crowd
- 60-second event cooldown
- no trigger retuning

## Frozen XAU state labels
Using XAU mid from trigger end:
- R5 = predicted-direction mid return at +5s
- R10 = at +10s
- R30 = at +30s
- DIVERGE_EARLY: R5>0 AND R10>0
- CROWD_PERSISTS: R5<0 AND R10<0
- REVERSAL_CONFIRM: R5<=0 AND R30>0
- ALL: every frozen stall event

These labels are diagnostic partitions, not optimized filters.

## Directional bias measurement
Use XAU mid-price only; no Bid/Ask execution and no costs.
Bias return = predicted-direction change in XAU mid from trigger end.
Horizons: 1m, 3m, 5m, 10m, 15m.

Primary metrics:
- directional accuracy = share of events with bias return >0
- mean bias return in XAU ATR
- median bias return in XAU ATR
- mean absolute XAU move
- signed efficiency = mean signed return / mean absolute return

## Additional directional diagnostics
For each event and horizon:
- whether predicted direction was correct
- maximum excursion in predicted direction
- maximum excursion against predicted direction
- first side to hit +/-0.25 ATR within 15m

## Split
- TRAIN: before 2026-08-20 00:00 UTC
- VALID: 2026-08-20 through 2026-09-06 22:00 UTC
- POST_CHECK: after VALID; not used for candidate nomination

## Candidate gate
A state may be called a historical directional-bias candidate only if:
- TRAIN N>=10 and VALID N>=10
- TRAIN and VALID accuracy >50% at 3m and 5m
- TRAIN and VALID mean signed return >0 at 3m and 5m
- VALID signed efficiency >0 at 3m and 5m
- POST_CHECK reported but not used for selection

No production or EA promotion from LAB005 alone. Historical directional-bias audit only.
