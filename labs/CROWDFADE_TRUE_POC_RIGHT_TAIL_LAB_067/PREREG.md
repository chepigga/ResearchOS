# LAB067 — TRUE POC RIGHT-TAIL DISTRIBUTION CHECK — PREREGISTRATION

## Status

Post-LAB066 robustness diagnostic on the SAME event sample. This is not independent OOS confirmation.

No new POC thresholds and no production action.

## Frozen classes

Use LAB066 classes unchanged:
- POC_ALIGNED
- POC_MIDDLE
- POC_OPPOSITE

## Time splits

Report separately:
- 2021–2023
- 2024–2025
- 2026 Mar–Aug

No reclassification or threshold changes.

## Primary distribution question

LAB066 showed a mean/MFE advantage but historical median did not pass. Test whether this is a positive-skew / right-tail effect.

For POC_ALIGNED vs POC_OPPOSITE report:
- N
- mean and median signed 4h return
- 25th / 75th / 90th percentile signed 4h return
- positive-return share
- 75th / 90th percentile 4h MFE
- median and 75th percentile 4h MAE

Primary robustness pattern:
- q90 signed 4h return ALIGNED > OPPOSITE
- q90 MFE4 ALIGNED > OPPOSITE

Evaluate separately in 2021–23, 2024–25, and 2026.

## Decision rule

If right-tail advantage does NOT repeat across the two historical subperiods and 2026, close the footprint/POC branch.

If it does repeat but samples are small, retain POC location only as shadow/context; no hard rule is promoted.
