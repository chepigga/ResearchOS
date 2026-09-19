# GC_XAU_ANCHORED_5MIN_EPISODE_AND_RESOLUTION_STATE_LAB007B_PREREG

Status: PREREGISTERED_ANCHORED_EPISODE_DISCOVERY_NOT_OOS

Purpose: replace LAB007 connected-chain episodes with strictly anchored 5-minute episodes and test whether a causal resolution state improves directional XAU setup quality.

## Frozen source
- exact LAB005 causal repeated_failed_attack signals, one unique signal per gc_t0_ms
- no future XAU information in signal generation

## Anchored episode construction
- first unassigned signal opens episode at anchor t0
- episode contains all subsequent signals with gc_t0_ms <= anchor+300s
- episode closes strictly at anchor+300s
- next unassigned signal after anchor+300s starts next episode
- no chain extension beyond anchor+300s

## Causal state at each signal inside episode
- signal_index
- elapsed_s from anchor
- cumulative LONG count / SHORT count
- directional_balance = abs(LONG-SHORT)/total
- dominant_direction = sign(LONG-SHORT)
- same-direction run length
- direction flips so far
- current signal equals dominant direction
- current quiet_start
- current impact deterioration
- cumulative mean impact deterioration

## Frozen resolution rules
Each emits at most one setup per episode at first causal clock satisfying condition:
R1_EARLY_DOMINANCE_3: total>=3, elapsed<=180s, balance>=0.67, current==dominant.
R2_EARLY_QUIET_DOMINANCE_3: R1 plus current quiet_start.
R3_RUN3_BEFORE240: run_length>=3 and elapsed<=240s.
R4_DOMINANCE_THEN_OPPOSITE_FLIP: total>=4, previous signal==dominant, current signal==-dominant_before_current; predicted direction=current signal direction.
R5_DOMINANCE_REASSERT_AFTER_FLIP: total>=4, at least one flip, current==current dominant, previous signal==-current dominant, elapsed<=300s.

Important: R4 is a resolution hypothesis distinct from old crowd-fade direction. It tests whether the first opposite flip after dominance is the actual XAU direction. No other flip rule is searched.

## Outcomes from emission t0
- +1 ATR, +2 ATR, +3 ATR first passage in predicted direction within 5m
- MFE/MAE to 5m
- executable fixed 5m return using Ask/Bid

## Split
- TRAIN <2026-08-20
- VALID 2026-08-20 through 2026-09-06 22:00 UTC
- POST_CHECK descriptive only

## Survival gate
- TRAIN N>=100
- VALID N>=100
- TRAIN +2>=25%
- VALID +2>=25%
- TRAIN +3>=9%
- VALID +3>=9%
- TRAIN executable fixed5m EV>0
- VALID executable fixed5m EV>0
- VALID PF>=1.10

No limit/SL/TP optimization. Any survivor advances to LAB008 execution geometry.