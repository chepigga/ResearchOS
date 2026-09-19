# GC_XAU_TRAPPED_CROWD_EPISODE_STATE_AND_FINAL_DIRECTION_LAB007_PREREG

Status: PREREGISTERED_EPISODE_STATE_DISCOVERY_NOT_OOS

Purpose: treat the frozen LAB005 repeated_failed_attack signals as 5-minute trapped-crowd market episodes rather than independent trades, and test whether episode state identifies a final directional XAU setup.

## Frozen episode construction
- Source: exact LAB005 causal repeated_failed_attack signals, one unique signal per gc_t0_ms.
- TIME_ONLY connected clustering with adjacent signal gap <=5 minutes.
- No same-direction requirement.
- Episode start = first signal t0; episode end = last signal t0.
- No future XAU outcome enters clustering.

## Causal episode-state features available at each signal inside episode
- signal_index_in_episode
- elapsed seconds since episode start
- cumulative LONG count and SHORT count
- directional_balance = abs(LONG-SHORT)/total_signals
- dominant_direction = sign(LONG-SHORT), 0 if tied
- run_length_same_direction for current signal
- number of direction flips so far
- current signal direction relative to dominant direction
- attack1/attack2 impact and impact deterioration of current signal
- cumulative mean impact deterioration
- current XAU quiet_start flag
- prior30 signed XAU move in current signal direction when available from LAB005 ledger

## Frozen candidate finalization rules
Each rule emits at most one setup per episode, at the first causal clock when its condition is met:
R1 DOMINANCE_3: total signals>=3, directional_balance>=0.67, current signal equals dominant direction.
R2 DOMINANCE_5: total signals>=5, directional_balance>=0.60, current signal equals dominant direction.
R3 RUN3: current same-direction run length>=3.
R4 FINAL_FLIP_TO_DOMINANT: total signals>=4, at least one prior flip, current signal equals current dominant direction, previous signal was opposite current dominant direction.
R5 QUIET_DOMINANCE_3: R1 plus current signal quiet_start=True.

No threshold sweep beyond these five frozen rules.

## Outcome
- predicted XAU direction = emitted signal direction.
- from rule emission t0, measure +2 ATR and +3 ATR first passage within 5 minutes, +1 ATR hit, MFE/MAE, and fixed 5m directional return.
- executable benchmark MARKET_NOW only in LAB007; no limit/SL/TP tuning.
- LONG Ask->Bid, SHORT Bid->Ask, spread embedded.

## Split
- TRAIN <2026-08-20
- VALID 2026-08-20 to 2026-09-06 22:00 UTC
- POST_CHECK descriptive only.

## Candidate survival gate
- TRAIN setups>=100
- VALID setups>=100
- TRAIN +2ATR hit rate >=25%
- VALID +2ATR hit rate >=25%
- TRAIN +3ATR hit rate >=9%
- VALID +3ATR hit rate >=9%
- TRAIN fixed5m executable EV >0
- VALID fixed5m executable EV >0
- same directional rule frozen into POST without retuning.

No production promotion. If a rule survives, execution geometry belongs in LAB008.