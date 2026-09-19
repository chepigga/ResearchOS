# GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009_PREREG

Status: PREREGISTERED_REV2_QUALITY_DISCOVERY_NOT_OOS

Purpose: test whether executed GC volume, aggressor delta, short-horizon impulse, and GC->XAU lead-lag discriminate high-quality frozen LAB007D REV2 transitions.

## Frozen parent signal
- exact LAB007D DOMINANCE_REVERSAL REV2 clocks
- no change to REV2 structural definition

## Layer A: features available exactly at REV2 t0
- REV2 attack1_volume
- REV2 attack2_volume
- REV2 attack2/attack1 volume ratio
- REV2 attack1_delta_frac
- REV2 attack2_delta_frac
- abs REV2 attack2_delta_frac
- REV2 attack2 signed impact
- REV2 impact deterioration
- REV2 reversal-direction aggressive-volume share

## Layer B: delayed causal confirmation windows
Separate confirmation clocks at REV2+5s, +15s, +30s.
For each window [REV2, REV2+W]:
- GC total executed volume
- GC reversal-direction aggressive volume
- GC opposite aggressive volume
- GC aligned delta fraction
- GC signed impulse in reversal direction / prior completed GC M1 ATR
- GC impulse efficiency = signed impulse ATR / total volume
- volume acceleration = post-window volume / equal-length pre-REV2 volume
- aligned delta acceleration = post aligned delta_frac - pre aligned delta_frac
- XAU signed move in reversal direction / prior completed XAU M1 ATR
- GC-XAU lead gap = GC signed impulse ATR - XAU signed move ATR

Outcome clock for Layer B is confirmation end, never REV2 t0.

## Labels/outcomes
- +2 ATR and +3 ATR XAU first passage in reversal direction within 5m after the relevant clock
- executable fixed5m XAU return from the relevant clock
- time to +0.50 ATR among +2ATR winners

## Discovery procedure
- TRAIN <2026-08-20; VALID through 2026-09-06 22:00; POST descriptive only.
- For each feature and each clock, derive TRAIN-only Q20/Q80 on available observations.
- Compare Q1 and Q5 tails on TRAIN BIG2 lift; freeze the better tail.
- Apply unchanged threshold to VALID and POST.
- No threshold sweep beyond TRAIN quintile edges.

## Survival gate
- TRAIN selected N>=30
- VALID selected N>=30
- TRAIN +2ATR lift>=1.25x
- VALID +2ATR lift>=1.20x
- TRAIN fixed5m EV>0
- VALID fixed5m EV>0
- POST reported, not required.

No SL/TP optimization. No production promotion from LAB009.