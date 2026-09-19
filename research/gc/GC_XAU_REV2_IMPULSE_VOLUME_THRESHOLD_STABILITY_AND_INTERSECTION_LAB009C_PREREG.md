# GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C_PREREG

Status: PREREGISTERED_THRESHOLD_STABILITY_INTERSECTION_NOT_OOS

Purpose: test whether the LAB009B REV2 quality effect persists across adjacent TRAIN-frozen percentile thresholds and whether impulse+volume intersections improve quality without collapsing sample size.

## Frozen parent
- exact LAB009 event ledger
- frozen REV2 structure
- no new signal families

## Frozen features
- 5s post_signed_impulse_atr
- 30s post_volume
- 30s post_aligned_volume

## Threshold grid
- TRAIN-only percentiles Q60, Q65, Q70, Q75, Q80
- thresholds frozen separately for each feature
- apply unchanged to VALID and POST_CHECK

## Single-feature tests
- IMPULSE_Qx: 5s post_signed_impulse_atr >= TRAIN Qx
- VOLUME_Qx: 30s post_volume >= TRAIN Qx
- ALIGNED_VOLUME_Qx: 30s post_aligned_volume >= TRAIN Qx

## Intersection tests
Intersection requires the same frozen REV2 event to satisfy the 5s impulse threshold and the 30s volume threshold; entry/outcome clock = REV2+30s so all information is causal.
- IMPULSE_Qx_AND_VOLUME_Qx
- IMPULSE_Qx_AND_ALIGNED_VOLUME_Qx

## Outcomes from each test's causal clock
- +2ATR hit rate within 5m
- +3ATR hit rate within 5m
- executable fixed5m EV ATR
- PF on fixed5m ATR outcomes
- N and relative retention vs base clock

## Stability diagnostics
- adjacent-threshold plateau = at least 3 consecutive Q levels with TRAIN EV>0 and VALID EV>0
- robust plateau additionally requires TRAIN and VALID +2ATR rate both above their respective unfiltered base rates at each plateau level
- POST is descriptive only
- report threshold sensitivity, do not choose a single winner from this LAB

## Sample warning
- intersections with VALID N<12 are reported but cannot be considered stable evidence

No SL/TP optimization. No production promotion from LAB009C.