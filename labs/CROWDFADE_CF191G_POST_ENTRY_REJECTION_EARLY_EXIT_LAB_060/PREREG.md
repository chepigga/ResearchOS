# LAB060 — CF191G POST-ENTRY ABSORPTION REJECTION EARLY INVALIDATION — PREREGISTRATION

## Purpose

Test whether CF191g often enters correctly but should exit early when post-fill price action rejects the pre-entry absorption range.

This is a MANAGEMENT LAB.
CF191g entry signal, confirmation, pause, max/day, and positive-skew core are frozen and unchanged.
No C/D entry skip is used.

## Frozen control parity

Exact OLD_v191g_POSITIVE_SKEW lineage:
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Pre-entry anchor

At each actual CF191g fill, define the absorption/signal range from the final five completed Binance BTCUSDT 1m bars ending at the fill time:
- anchor_high = max 1m high across those 5 bars
- anchor_low = min 1m low across those 5 bars

The anchor is frozen at fill and never updated.

## Post-fill REJECTION — causal

REJECTION is defined only after the position is open.

For BUY:
- first completed 1m close < anchor_low

For SELL:
- first completed 1m close > anchor_high

No wick-only trigger.
No future MFE knowledge.
No OI condition.
No ret15/C/D condition.
No arbitrary ATR threshold.

## Management horizons — preregistered

Test separately:
- 5 minutes after fill
- 10 minutes after fill
- 15 minutes after fill

For each horizon H:
- if REJECTION occurs on a completed 1m bar within H minutes after fill, close the position at that completed 1m close
- otherwise keep the original frozen CF191g management unchanged

Each horizon is a separate stateful replay from the same canonical entry logic.
No selecting/tuning H after results inside this LAB.

## Stateful semantics

An early exit changes occupancy and therefore future signal reachability.
Therefore the primary comparison MUST be a full stateful replay, not trade deletion or local substitution.

After an early exit:
- position becomes free immediately after the rejection close
- future CF191g signals/re-entries evolve naturally
- day count remains consumed because the trade was actually opened
- anti-repeat last-entry state remains based on the original fill, exactly as in the frozen core

## Event-level diagnostic

For every early-rejection event also report a local, non-stateful audit:
- original frozen trade R
- early-exit R at rejection close
- delta_R = early_exit_R - original_R
- saved_R = max(delta_R, 0)
- given_up_R = max(-delta_R, 0)
- whether original trade eventually hit initial/profit stop/time exit
- original MFE/MAE at 15m/30m/60m/120m

This local audit explains the mechanism but does not replace stateful results.

## Primary metrics

Report separately for 2021–2025 and 2026, for CONTROL and each H=5/10/15:
- N
- WR
- EV
- PF
- SumR
- MaxDD_R
- R/DD
- max consecutive losses
- positive years/months
- number of rejection exits
- mean / total saved_R
- mean / total given_up_R
- net local delta_R

## Success criteria

A horizon is a candidate only if, in BOTH 2021–2025 and 2026:
- R/DD >= control
- SumR is not materially lower: >= 98% of control SumR
- PF >= control OR MaxDD_R < control
- max consecutive losses does not worsen
- positive years/months do not worsen
- rejection-event count is meaningful: >= 20 historical and >= 5 in 2026

Secondary mechanism checks:
- initial-stop frequency among rejected trades is high
- median saved_R on rescued losers is economically meaningful
- right-tail damage (given_up_R from eventual winners) does not dominate saved_R

## Guardrails

No entry filter changes.
No delayed-entry release logic.
No BE-ish stop modification in this LAB.
No mixing 5/10/15 rules.
No threshold search.
No production promotion unless one preregistered horizon passes both periods.