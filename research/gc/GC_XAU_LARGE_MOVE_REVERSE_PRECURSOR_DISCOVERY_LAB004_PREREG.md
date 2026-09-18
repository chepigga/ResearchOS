# GC_XAU_LARGE_MOVE_REVERSE_PRECURSOR_DISCOVERY_LAB004_PREREG

Status: PREREGISTERED_EVENT_FIRST_DISCOVERY_NOT_OOS

Purpose: start from large XAUUSD CFD moves and inspect GC futures microstructure BEFORE the XAU move starts.

XAU large-move event:
- every eligible XAU second uses prior completed XAU M1 ATR14
- event if either +1.00 ATR or -1.00 ATR is first reached within the next 300 seconds
- direction = side first reaching 1.00 ATR
- event clock = earliest eligible second in a cluster
- de-cluster 300 seconds after an accepted event
- report QUIET_START subset where absolute XAU mid move over prior 30 seconds <=0.25 ATR

GC precursor windows ending exactly at XAU event clock: 1s,2s,5s,10s,30s,60s.

Features per window:
- delta_frac and direction-aligned delta = future_XAU_direction * delta_frac
- volume and causal prior-hour volume percentile / Q75 state
- abs(delta_frac) and causal prior-hour Q90 state
- GC price impact normalized by prior completed GC M1 ATR
- crowd impact = sign(delta) * price impact
- EXTREME_EFFORT = abs(delta_frac)>=prior1h Q90 AND volume>=prior1h Q75
- STALL = EXTREME_EFFORT AND crowd_impact<=0.05 ATR
- TRAPPED_OPPOSITE = STALL AND crowd direction opposite future XAU move
- CHASE_ALIGNED = EXTREME_EFFORT AND crowd direction aligned with future XAU move AND crowd_impact>0.05 ATR
- DELTA_FLIP = 30s crowd direction opposite future XAU direction followed by 5s delta aligned with future direction
- REPEATED_FAILED_ATTACK = prior 60s split into two 30s windows with same crowd direction opposite future move and second crowd-impact <= first crowd-impact

Controls: deterministic same-day offsets -30m,-20m,+20m,+30m,+40m from each accepted XAU event; exclude controls within +/-5m of any accepted large-move event. Same precursor features are measured at controls.

Discovery split: TRAIN <2026-08-20; VALID 2026-08-20 to 2026-09-06 22:00 UTC; POST_CHECK after that. POST_CHECK is descriptive only.

Primary outputs:
- number/location/timing of large XAU moves
- precursor frequency in events vs controls
- enrichment ratio by GC window and precursor family
- direction agreement
- stability across TRAIN/VALID/POST_CHECK
- lead time: which precursor window is most enriched before event start

No trading entry, SL, TP, limit, or risk optimization in LAB004. This LAB identifies candidate precursors only.
