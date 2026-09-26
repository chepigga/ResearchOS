# LAB061 — CF191G POST-ENTRY REJECTION RECLAIM FAILURE — PREREGISTRATION

## Purpose

Test whether post-fill rejection becomes genuinely toxic only when the rejection is NOT cancelled by a fast reclaim.

This is the final diagnostic test of the current exit/invalidation branch before stopping that branch if the preregistered hypothesis fails.

CF191g entry core remains frozen.
No C/D entry filter.
No delayed-entry release rule.
No immediate exit on first rejection.

## Frozen control

Exact OLD_v191g_POSITIVE_SKEW lineage:
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Frozen pre-entry anchor

At each actual CF191g fill, define:
- anchor_high = max high of final five completed 1m bars ending at fill
- anchor_low = min low of same five bars

Anchor is frozen at fill.

## First post-fill rejection

For BUY:
- rejection = first completed 1m close < anchor_low

For SELL:
- rejection = first completed 1m close > anchor_high

Search rejection only within the first 15 minutes after fill.

No wick trigger. No ATR-X trigger. No OI. No C/D.

## Reclaim after rejection

After the first rejection bar, test whether price reclaims the anchor boundary that was broken.

For BUY rejection below anchor_low:
- reclaim = completed 1m close >= anchor_low

For SELL rejection above anchor_high:
- reclaim = completed 1m close <= anchor_high

Reclaim windows are preregistered separately:
- 1 minute after rejection
- 3 minutes after rejection
- 5 minutes after rejection

Primary window = 3 minutes.
1m and 5m are robustness only.

## State classes

For each reclaim window N:
- RECLAIMED_N = rejection followed by reclaim within N completed 1m bars
- NO_RECLAIM_N = rejection not reclaimed within N completed 1m bars
- NO_REJECTION = no rejection in first 15m after fill

## Diagnostic-only first stage

LAB061 is a map/diagnostic only.
No stateful early exit is executed in this LAB.

Report separately for 2021–2025 and 2026:
- N
- final frozen CF191g EV / PF / SumR
- MFE / MAE at 15m / 30m / 60m / 120m
- initial-stop share
- positive-R share
- right-tail share: fraction of trades with final R >= +1.5R

## Primary hypothesis

For the 3m reclaim window, in BOTH 2021–2025 and 2026:
- NO_RECLAIM_3M EV < RECLAIMED_3M EV
- NO_RECLAIM_3M PF < RECLAIMED_3M PF
- NO_RECLAIM_3M MFE60 < RECLAIMED_3M MFE60
- NO_RECLAIM_3M MAE60 > RECLAIMED_3M MAE60
- NO_RECLAIM_3M initial-stop share > RECLAIMED_3M initial-stop share

Minimum sample for a viable next-step candidate:
- historical NO_RECLAIM_3M N >= 50
- 2026 NO_RECLAIM_3M N >= 10

## Stop rule

If the primary hypothesis fails to repeat in BOTH periods, or sample size is below the minimum, STOP this rejection/reclaim exit branch.
No threshold tuning, no alternate reclaim definitions, and no production exit rule may be pursued from this branch without a new independent rationale.

If the primary hypothesis passes, only then may a later LAB preregister exactly one stateful action for NO_RECLAIM.