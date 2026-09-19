# GC_XAU_BIG_MOVE_DISCRIMINATOR_INSIDE_REPEATED_FAILED_ATTACK_LAB006_PREREG

Status: PREREGISTERED_CAUSAL_DISCRIMINATOR_DISCOVERY_NOT_OOS

Purpose: within the fully causal LAB005 repeated_failed_attack signals, identify causal-at-t0 features that discriminate future +2 ATR / +3 ATR XAU moves from non-winners.

## Frozen parent signal
- exact LAB005 causal repeated_failed_attack definition
- two contiguous 30s GC attacks with same nonzero crowd direction
- second crowd impact <= first crowd impact
- predicted XAU direction = opposite crowd
- 60s cooldown
- no future XAU label enters the signal

## Primary subset and labels
- Primary: QUIET_START, prior 30s absolute XAU move <=0.25 prior-completed XAU M1 ATR
- Secondary: ALL signals
- BIG2 label: predicted XAU direction reaches +2.0 ATR within 5m from t0
- BIG3 label: predicted XAU direction reaches +3.0 ATR within 5m from t0

## Frozen causal feature family at t0
Attack geometry:
- attack1_impact, attack2_impact, impact_deterioration = attack1-impact2
- attack1_delta_frac, attack2_delta_frac, abs_delta_frac_1, abs_delta_frac_2
- attack1_volume, attack2_volume, volume_ratio_2_to_1
- persistence_abs_delta = min(abs_delta_frac_1, abs_delta_frac_2)
- efficiency1 = attack1_impact / max(abs_delta_frac_1, eps)
- efficiency2 = attack2_impact / max(abs_delta_frac_2, eps)
- efficiency_deterioration = efficiency1-efficiency2

Pre-XAU context:
- prior30_abs_move_atr
- prior30_signed_pred_move_atr
- prior60_signed_pred_move_atr
- prior60_range_atr

Cross-market context:
- GC signed predicted-direction 60s return / GC ATR
- XAU signed predicted-direction prior60 move / XAU ATR
- GC_minus_XAU_signed_context = GC_pred_60_atr - XAU_pred_60_atr

Time context (descriptive only, not eligible for nomination): UTC hour.

## Discovery procedure
- TRAIN <2026-08-20, VALID 2026-08-20..2026-09-06 22:00, POST_CHECK descriptive only.
- For each eligible numeric feature, derive TRAIN-only quintile boundaries on QUIET_START.
- Evaluate BIG2 and BIG3 hit rates in each TRAIN quintile.
- Nominate at most one tail bin per feature: whichever edge quintile (Q1 or Q5) has the higher TRAIN BIG2 lift over base.
- Freeze that bin and apply unchanged to VALID and POST_CHECK.
- No internal threshold sweep beyond TRAIN quintile edges.

## Survival gate for a feature/bin
- TRAIN selected-bin N>=100
- VALID selected-bin N>=100
- TRAIN BIG2 lift >=1.25x
- VALID BIG2 lift >=1.20x
- TRAIN BIG3 lift >=1.20x
- VALID BIG3 lift >=1.15x
- same direction of enrichment in TRAIN and VALID
- POST_CHECK reported but not required.

## Pair test
- If at least two single-feature bins survive, test only the intersection of the top two survivors ranked by min(TRAIN BIG2 lift, VALID BIG2 lift).
- No other pairwise search.

No execution optimization in LAB006. Any surviving discriminator belongs in a separately preregistered LAB007 execution audit.
