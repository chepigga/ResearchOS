# LAB069 — CF191G HIGH-VOL FAILED-EARLY STATEFUL MANAGEMENT — PREREGISTRATION

## Purpose

Test one management action directly implied by LAB068.

Rule:
`if position is still open at +15m AND entry volatility bucket == P80_100 AND early_state == FAILED_EARLY -> full exit at the completed 15m close`

No entry filter. No threshold tuning. No alternative action in this LAB.

## Frozen CF191g control parity
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Frozen entry volatility
`vol_metric = ATR14_M5 / close_M5`
`vol_percentile_7d` = causal percentile versus prior 2016 completed M5 bars, current bar excluded.
`HIGH = P80_100`.

## Frozen early state at +15m
Use exactly the first 15 completed 1m bars AFTER fill.

`expansion15_atr = side * (close_15m - entry_price) / entry_ATR`
`eff15 = side * (close_15m - entry_price) / sum(abs(close_t-close_t-1))`

`FAILED_EARLY = expansion15_atr <= 0 OR eff15 <= 0`

Persistence is not required for FAILED_EARLY and is not used in the action.

## Action

If:
- frozen control position is still open strictly after the +15m completed 1m close
- entry vol bucket = P80_100
- FAILED_EARLY = true

then close the position at the +15m completed 1m close.

If the frozen control would have exited before or at +15m, control exit wins and no action is applied.

## Stateful semantics

Full stateful replay required.
After early exit:
- occupancy is freed immediately after the +15m close
- future canonical CF191g signals evolve naturally
- day count remains consumed
- anti-repeat state remains based on original fill

## Event audit

For every action event report:
- entry_ts / side / vol percentile
- expansion15 / eff15
- early_exit_R
- original frozen R
- delta_R / saved_R / given_up_R
- original exit reason
- original right-tail flag R>=+1.5
- post15 MFE/MAE to 60m

## Primary metrics

Report CONTROL vs LAB069 separately for 2021–2025 and 2026:
- N / WR / EV / PF / SumR
- MaxDD_R / R-DD
- max consecutive losses
- positive years/months
- action count
- total saved_R / total given_up_R / net local delta_R
- original initial-stop share among action events
- original right-tail share among action events

## PASS criteria

A period passes only if:
- R/DD >= control
- SumR >= 98% of control
- PF >= control OR MaxDD_R < control
- max consecutive losses does not worsen
- positive years/months do not worsen
- action count >= 100 historical / >= 20 forward_2026

Overall promotion requires PASS in BOTH periods.

## Stop rule

If LAB069 fails overall, do not tune 15m, P80 threshold, expansion threshold, or efficiency threshold inside this branch.
A materially different softer action would require a new preregistered rationale.