# GC_XAU_ANCHORED_EPISODE_STRUCTURAL_CLASSES_LAB007C_PREREG

Status: PREREGISTERED_STRUCTURAL_TAXONOMY_NOT_OOS

Purpose: partition frozen LAB007B anchored 5-minute repeated_failed_attack episodes into deterministic structural classes using GC signal sequence only, then measure post-episode XAU outcomes.

## Frozen episode source
- exact LAB005 causal repeated_failed_attack signals, unique gc_t0_ms
- anchored episodes from LAB007B: first unassigned signal opens episode; all signals through anchor+300s belong to it; no chain extension

## Structural features from the completed episode
- n_signals
- LONG count / SHORT count
- directional_balance = abs(LONG-SHORT)/n
- number of direction flips
- first direction
- last direction
- first two same-direction flag
- last two same-direction flag
- longest same-direction run
- final same-direction run length
- dominant direction
- first-half dominant direction
- second-half dominant direction
- mean impact deterioration
- first-half vs second-half impact deterioration
- share quiet_start signals

## Deterministic mutually exclusive classes
Class order is frozen and first matching class wins:
1. SPARSE: n_signals<=2.
2. ONE_SIDED_BUILDUP: n>=3, directional_balance>=0.67, flips<=1.
3. DOMINANCE_REVERSAL: n>=4, first two signals same direction, last two signals same opposite direction.
4. ALTERNATING_CONFLICT: n>=4, flips>=2, directional_balance<=0.33.
5. REASSERTION: n>=4, flips>=1, final_run>=2, final direction equals full-episode dominant direction.
6. MIXED_TRANSITION: all remaining episodes.

## Outcome clock
- taxonomy uses complete episode only, therefore outcome clock = last signal t0 of episode
- predicted direction for descriptive directional tests:
  ONE_SIDED_BUILDUP -> final/dominant signal direction
  DOMINANCE_REVERSAL -> final signal direction
  ALTERNATING_CONFLICT -> no directional prediction
  REASSERTION -> final signal direction
  SPARSE/MIXED -> no primary directional prediction

## Outcomes from episode end
- +1/+2/+3 ATR first passage within next 5m for predicted direction when defined
- absolute 2ATR/3ATR expansion in either direction within next 5m for all classes
- executable fixed 5m XAU return in predicted direction where defined
- class frequency per TRAIN/VALID/POST

## Split
- TRAIN <2026-08-20
- VALID 2026-08-20 through 2026-09-06 22:00 UTC
- POST_CHECK descriptive only

## Discovery goal
- identify classes that are stable in frequency and materially enriched for 2ATR/3ATR expansion in TRAIN and VALID
- directional class is interesting only if TRAIN and VALID predicted-direction fixed5m EV are both >0 and +2ATR directional hit rate is >=25% in both

No execution geometry, limits, SL/TP, or class-threshold optimization in LAB007C.