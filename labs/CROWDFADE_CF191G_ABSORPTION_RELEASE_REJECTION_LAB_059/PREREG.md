# LAB059 — CF191G ABSORPTION RELEASE VS REJECTION — PREREGISTRATION

## Purpose

Test whether the LAB058 absorption/impact-decay state becomes informative only after observing its **causal resolution**: price acceptance through the absorption range (release) versus rejection through the opposite side.

This is an execution-timing diagnostic. CF191g signal core is unchanged.
No production veto or delayed-entry rule is promoted from this LAB.

## Frozen universe

Use the exact LAB058 `ADVERSE_DECAY_CORNER` universe:
- persistent aggression WITH the CF191g trade side in >=4 of the final 5 completed 1m bars
- causal sequence aggression percentile >= 0.80
- causal efficiency-drop percentile >= 0.80

Expected LAB058 universe:
- 2021–2025: N=122
- 2026 Mar–Aug: N=12

Frozen CF191g control parity remains:
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Absorption range

For each LAB058 adverse-decay candidate, define the anchor range from the same final five completed 1m bars ending at the original CF191g candidate-entry time:
- anchor_high = maximum 1m high of those five bars
- anchor_low = minimum 1m low of those five bars

Only future completed 1m closes after the candidate time may resolve the state.

## Resolution definitions

Mirror BUY/SELL symmetrically.

For BUY:
- RELEASE = first future completed 1m close > anchor_high
- REJECTION = first future completed 1m close < anchor_low

For SELL:
- RELEASE = first future completed 1m close < anchor_low
- REJECTION = first future completed 1m close > anchor_high

If neither boundary is closed beyond within the horizon, state = UNRESOLVED.

Primary horizon: **3 completed 1m bars** after candidate entry.
Secondary robustness horizons: 1m and 5m.

No ATR distance threshold, no wick-only trigger, no OI condition, no ret15/D condition.

## Primary hypothesis

Within LAB058 adverse-decay candidates:

`RELEASE_3M` should have better continuation geometry than `REJECTION_3M`:
- higher final CF191g EV / PF
- higher 60m MFE
- lower 60m MAE
- higher impulse60 success rate

The sign should repeat separately in 2021–2025 and 2026.

## Local delayed-entry diagnostic

For RELEASE events only, also calculate a non-stateful local hypothetical:
- delayed entry = the completed 1m close that first resolves RELEASE
- same trade side
- same frozen ATR snapshot from the original CF191g candidate
- same CF191g positive-skew management geometry (SL 1.5 ATR, BE/trailing logic, max hold 6h)

Report delayed-entry R versus the original candidate's frozen CF191g R.
This local delayed-entry diagnostic is descriptive only; it does NOT model portfolio occupancy/re-entry consequences.

## Outputs

For each event report:
- period / timestamp / side
- anchor_high / anchor_low / original entry price / ATR
- 1m / 3m / 5m resolution class
- resolution minute and resolution close
- original frozen CF191g final R
- 15/30/60/120m MFE/MAE and signed returns
- impulse60
- delayed-release R when release occurs

## Decision questions

Primary 3m:
1. Is RELEASE EV > REJECTION EV in both periods?
2. Is RELEASE PF > REJECTION PF in both periods?
3. Is RELEASE MFE60 > REJECTION MFE60 in both periods?
4. Is RELEASE MAE60 < REJECTION MAE60 in both periods?
5. Is RELEASE impulse60 rate > REJECTION in both periods?

Secondary:
- Do 1m and 5m classifications show the same direction?
- Does local delayed-release entry preserve or improve R without obvious right-tail destruction?

No threshold search or stateful gate is allowed inside LAB059.