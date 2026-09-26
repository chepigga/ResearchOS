# LAB067 — TRUE H4 VOLUME-MASS LOCATION + POC REJECTION — PREREGISTRATION

## Purpose

Test the second structural element from the reviewed video: not only where the POC sits, but whether the traded quote-notional mass itself is concentrated on the swept/rejected side of the H4 range.

Use the exact LAB066 event universe and already reconstructed true aggTrade volume profiles. Diagnostic only.

## Frozen universe
- historical composite H4 events: N=221
- forward_2026 composite H4 events: N=21

## Rejected-side volume mass

For LONG-rejection event (swept low, close upper third):
- rejected_side_share = lower_third_share
- opposite_side_share = upper_third_share

For SHORT-rejection event (swept high, close lower third):
- rejected_side_share = upper_third_share
- opposite_side_share = lower_third_share

Natural mass-location states, no tuned threshold:
- MASS_ALIGNED if rejected_side_share > opposite_side_share
- MASS_OPPOSITE if rejected_side_share < opposite_side_share
- MASS_BALANCED only on exact equality

## Combined true-profile states

- PROFILE_CONFIRMED = POC_ALIGNED AND MASS_ALIGNED
- PROFILE_PARTIAL = exactly one of {POC_ALIGNED, MASS_ALIGNED}
- PROFILE_CONTRADICTED = POC_OPPOSITE AND MASS_OPPOSITE
- PROFILE_OTHER = everything else

No percentile or share threshold is introduced.

## Primary event-level hypothesis

Primary horizon = 4h after H4 event close.
In BOTH 2021–2025 and 2026:
- PROFILE_CONFIRMED mean signed 4h return > PROFILE_CONTRADICTED
- PROFILE_CONFIRMED median signed 4h return > PROFILE_CONTRADICTED
- PROFILE_CONFIRMED MFE4 > PROFILE_CONTRADICTED
- PROFILE_CONFIRMED MAE4 < PROFILE_CONTRADICTED

Report N. If PROFILE_CONFIRMED or PROFILE_CONTRADICTED has N < 20 historical or N < 5 forward, result is shadow-only even if signs agree.

## CF191g overlap

Reuse LAB066 overlap mapping and classify by the H4 event's combined profile state.
Report CF191g EV/PF/MFE/MAE by SUPPORTIVE vs ADVERSE relation and combined profile state.

No production rule from LAB067.