# LAB027 post-hoc diagnostic — does not change frozen verdict

Frozen verdict remains `DOUBLE_NO_RETURN_CONFIRMED_BUT_MONETIZATION_NOT_POSITIVE`.

## What is positive
The causally confirmed double-no-return starter is a real positive cohort. On the independent Confirmation diagnostic, the confirmed-alive cohort has starter TP2 EV about +0.130R versus +0.112R if the same 25% starter simply kept TP1.5. The increment is +0.0186R, but its week-cluster CI crosses zero.

The 77 trades that hit TP1.5 before the second confirmation clock are also strongly positive (+0.366R on the 25% starter). These cannot be retrospectively extended and are correctly left at TP1.5.

## Why the full strategy remains negative
The first-probation-fail cohort is enormous (1,972 independent Confirmation events) and has about -0.072R starter EV. This cost of buying information dominates the much smaller winner cohorts. A second-return cohort (191) is also negative at about -0.062R starter EV.

Therefore the current bottleneck is no longer winner monetization. It is the **cost of entering a starter on the broad pre-confirmation universe**.

## Implication
Do not add more TP/trailing complexity to LAB027. The next clean question is whether we can shrink or pre-route the starter universe using information already known *before* entry, while preserving the early/no-return winner cohort. Any such router must be preregistered and must not use the post-entry no-return state itself.
