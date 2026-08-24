# LAB018 post-hoc diagnostic — does not change frozen verdict

Frozen verdict remains `NO_DESTINATION_ROLE_RESIDUAL_EDGE`.

## What transferred weakly
- `REPEATED_MAGNET`: Discovery-2023 N=27, EV +0.0886R; Confirmation N=50, EV -0.0043R.
- Narrow `M15_SWING × REPEATED_MAGNET`: Discovery-2023 N=21, EV +0.1847R; Confirmation N=40, EV +0.0664R.

This narrow subset is not authorized for promotion because it is post-hoc and small in both splits.

## What did not transfer
- `TP_BEFORE_DEST`: Discovery-2023 EV +0.1119R but Confirmation EV -0.2105R.
- `TP_NEAR_DEST`: Discovery-2023 EV -0.0891R and Confirmation EV -0.0365R; better than baseline but still negative.
- Highest approach-speed quintile: Discovery-2023 EV -0.1130R; Confirmation EV -0.1106R. Current approach contains some predictive information but does not cross zero economics.

## Representation diagnosis
Group permutation importance on Confirmation:
- frozen LAB017 baseline: +0.0358 AUC drop;
- current approach topology: +0.0097;
- lifecycle destination interaction: +0.0014;
- destination identity/TP placement: -0.0015;
- historical destination role: -0.0033.

Thus the broad historical magnet/rejection-role encoding did not transfer as a useful residual predictor. The only incremental signal sits mostly in **current approach geometry**, not in the prior touch-history role label.

A separate preregistered replication of the narrow `M15_SWING × REPEATED_MAGNET` idea would be required before treating it as evidence.
