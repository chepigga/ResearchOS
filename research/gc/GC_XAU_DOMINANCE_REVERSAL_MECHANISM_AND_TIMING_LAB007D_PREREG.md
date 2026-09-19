# GC_XAU_DOMINANCE_REVERSAL_MECHANISM_AND_TIMING_LAB007D_PREREG

Status: PREREGISTERED_MECHANISM_TIMING_AUDIT_NOT_OOS

Purpose: study only frozen LAB007C DOMINANCE_REVERSAL anchored episodes and identify the causal reversal mechanics and execution window.

## Frozen source
- exact LAB007C anchored 5-minute episodes
- class = DOMINANCE_REVERSAL only
- class definition remains unchanged: first two episode signals same direction; last two episode signals same opposite direction
- no class retuning

## Reversal clocks
- dominance_dir = first signal direction
- reversal_dir = opposite dominance_dir
- REV1 = first signal in reversal_dir after at least two initial dominance_dir signals
- REV2 = next signal in reversal_dir after REV1, if present
- episode_end = last signal in episode

## Mechanism diagnostics at REV1 and REV2
- elapsed from episode anchor
- elapsed from last dominance signal
- XAU quiet_start flag
- current impact deterioration
- current attack1/attack2 impact
- current attack1/attack2 delta fraction
- change in impact deterioration versus prior dominance signal
- count of dominance-side signals before reversal
- count of reversal-side signals so far

## Timing outcomes from REV1 and REV2
- first passage in reversal direction to +0.25,+0.50,+1.00,+2.00,+3.00 XAU ATR within 5m
- adverse first passage to -0.25,-0.50,-1.00 ATR
- MFE/MAE 5m
- executable fixed5m return using Ask/Bid

## Frozen entry benchmarks
- MARKET_REV1
- MARKET_REV2
- LIMIT_REV2_005_30S: 0.05 ATR retrace from REV2 executable quote, expiry30s, no chase
- LIMIT_REV2_010_30S: 0.10 ATR retrace, expiry30s, no chase

## Split
- TRAIN <2026-08-20
- VALID 2026-08-20 through 2026-09-06 22:00 UTC
- POST_CHECK descriptive only

## Candidate timing gate
A reversal clock is timing-interesting if:
- TRAIN N>=40
- VALID N>=40
- TRAIN fixed5m EV>0
- VALID fixed5m EV>=0
- TRAIN +2ATR hit>=20%
- VALID +2ATR hit>=20%
- median time to +0.50 ATR among +2ATR winners >=15s in VALID

No SL/TP optimization in LAB007D. If a reversal clock survives, execution geometry belongs in LAB008.