# LAB062 — CF191G ACCEPTED REJECTION (NO-RECLAIM 3M) STATEFUL EARLY EXIT — PREREGISTRATION

## Purpose

Test exactly one management action supported by LAB061:

`post-fill rejection -> no reclaim for the next 3 completed 1m bars -> full exit at the close of the 3rd bar`

This is a full stateful replay.

## Frozen CF191g entry core

Unchanged from canonical OLD_v191g_POSITIVE_SKEW:
- same signal
- same confirmation
- same pause / max-day logic
- same positive-skew management when the new rule does not fire

No C/D entry skips.
No delayed-entry release.
No volume/OI filter.

## Frozen control parity

- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Anchor

At each actual CF191g fill:
- anchor_high = maximum high of the final five completed Binance BTCUSDT 1m bars ending at fill
- anchor_low = minimum low of those same five bars

Anchor is frozen at fill.

## Rejection

Search only during the first 15 minutes after fill.

For BUY:
- first completed 1m close < anchor_low

For SELL:
- first completed 1m close > anchor_high

No wick-only trigger.

## Reclaim

After the first rejection bar, inspect the next 3 completed 1m bars.

For BUY:
- reclaim if any completed close >= anchor_low

For SELL:
- reclaim if any completed close <= anchor_high

## Accepted rejection / action

If NONE of the next 3 completed 1m bars reclaims the broken anchor boundary:
- state = ACCEPTED_REJECTION
- close the position at the close of the 3rd completed 1m bar after rejection

If reclaim occurs within those 3 bars:
- no defensive action
- original frozen CF191g management continues

## Ordering / conservatism

If the frozen CF191g position would have exited before or at the accepted-rejection action timestamp, the frozen control exit wins and no early-exit override is applied.

## Stateful semantics

Early exit changes occupancy and future reachability.
Therefore primary results must be full stateful replay.

After accepted-rejection exit:
- position is free immediately after the exit close
- future canonical CF191g entries evolve naturally
- day count remains consumed
- anti-repeat state remains based on original fill

## Event audit

For every accepted-rejection exit report:
- entry timestamp / side
- rejection minute
- action minute from fill
- early-exit R
- original frozen trade R
- delta_R
- saved_R = max(delta_R,0)
- given_up_R = max(-delta_R,0)
- original exit reason
- MFE / MAE at 15m / 30m / 60m / 120m

## Primary metrics

Report separately for 2021–2025 and 2026:
- N
- WR
- EV
- PF
- SumR
- MaxDD_R
- R/DD
- max consecutive losses
- positive years/months
- number of accepted-rejection exits
- total / mean saved_R
- total / mean given_up_R
- net local delta_R
- original initial-stop share among acted events

## PASS criteria

Candidate PASSES a period only if:
- R/DD >= control
- SumR >= 98% of control
- PF >= control OR MaxDD_R < control
- max consecutive losses does not worsen
- positive years/months do not worsen
- accepted-rejection exits >= 50 historical / >= 10 forward 2026

Overall promotion requires PASS in BOTH periods.

## Stop rule

If LAB062 fails overall, do NOT continue tuning this accepted-rejection full-exit rule inside the same branch.
Any later management idea must be materially different (for example a softer stop action) and separately preregistered.