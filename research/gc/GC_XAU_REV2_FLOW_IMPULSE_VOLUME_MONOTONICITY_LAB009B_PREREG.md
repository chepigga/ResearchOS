# GC_XAU_REV2_FLOW_IMPULSE_VOLUME_MONOTONICITY_LAB009B_PREREG

Status: PREREGISTERED_MONOTONICITY_AUDIT_NOT_OOS

Purpose: test whether the most promising LAB009 REV2 quality features show stable ordered behavior across broad TRAIN-derived tercile bins rather than only in a small extreme tail.

## Frozen parent
- exact LAB009 event ledger
- no REV2 definition changes
- no new feature family

## Frozen feature set
1. 5s post_signed_impulse_atr
2. 30s volume_acceleration
3. 30s post_volume
4. 30s post_aligned_volume
5. 0s attack2_volume

## Binning
- derive q33 and q67 from TRAIN only for each feature at its own confirmation clock
- freeze LOW <=q33, MID (q33,q67), HIGH >=q67
- apply same thresholds unchanged to VALID and POST_CHECK

## Outcomes
- +2ATR hit rate
- +3ATR hit rate
- executable fixed5m EV ATR
- sample count per bin

## Monotonicity tests
For positively-oriented features, primary pattern is LOW <= MID <= HIGH.
Report independently for +2ATR rate and fixed5m EV.
Strong monotonic candidate requires:
- TRAIN: HIGH > MID > LOW for both +2ATR and EV
- VALID: HIGH > LOW for both +2ATR and EV
- HIGH-bin TRAIN N>=15 and VALID N>=15
- HIGH-bin EV >0 in TRAIN and VALID
- POST reported descriptively only

No threshold search, no SL/TP optimization, no feature combinations in LAB009B.