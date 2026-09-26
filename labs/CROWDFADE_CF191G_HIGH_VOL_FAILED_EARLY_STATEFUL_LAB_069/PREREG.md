# LAB069 — CF191G HIGH-VOL + FAILED-EARLY STATEFUL EXIT — PREREGISTRATION

## Purpose

Test exactly one management action supported by LAB068:
`HIGH entry volatility (P80–100) + FAILED_EARLY at t+15m + position still open -> full exit at the completed 15m close`.

This is a full stateful management replay.
CF191g entry signal, confirmation, pause, max/day, and positive-skew management are frozen unless the new rule fires.

## Frozen control parity
- 2021–2025: N=5297, SumR=+700.3704107793633
- 2026 Mar–Aug: N=544, SumR=+35.49784078156513

## Entry volatility — frozen from LAB064/LAB068
`vol_metric = ATR14_M5 / close_M5` at canonical fill.
`vol_percentile_7d` = causal percentile versus prior 2016 completed M5 bars, current bar excluded.
`HIGH = vol_percentile_7d >= 0.80`.

## Early state — frozen from LAB068
Use exactly the first 15 completed 1m bars after fill.

`expansion15_atr = side * (close_15m - entry_price) / entry_ATR`
`eff15 = side * (close_15m - entry_price) / sum(abs(1m close changes from entry through t+15m))`

`FAILED_EARLY = expansion15_atr <= 0 OR eff15 <= 0`.

No persistence threshold is required for FAILED_EARLY.
No threshold search.

## Action

If at the completed t+15m bar:
- the canonical position is still open,
- HIGH is true,
- FAILED_EARLY is true,

then:
- close the position at the completed 1m close at t+15m.

Otherwise retain frozen CF191g management.

## Ordering / conservatism

If the frozen CF191g control position exits before or at the t+15m timestamp, control exit wins and LAB069 does not override it.

## Stateful semantics

An early exit changes occupancy and future signal reachability.
Primary metrics MUST come from a full stateful replay.

After LAB069 exit:
- position is free immediately after the t+15m close,
- future canonical entries evolve naturally,
- day count remains consumed,
- anti-repeat last-entry state remains based on the original fill.

## Event audit

For every LAB069 defensive exit report:
- entry timestamp / side / vol percentile,
- expansion15 / eff15 / persist15,
- early-exit R,
- frozen-control R and exit reason,
- delta_R,
- saved_R = max(delta_R,0),
- given_up_R = max(-delta_R,0),
- post15 MFE/MAE to 60m,
- whether frozen control eventually reached R >= +1.5.

## Primary metrics

Report separately for 2021–2025 and 2026:
- N / WR / EV / PF / SumR / MaxDD_R / R/DD,
- max consecutive losses,
- positive years/months,
- number of defensive exits,
- total/mean saved_R,
- total/mean given_up_R,
- net local delta_R.

## PASS criteria

A period passes only if:
- R/DD >= control,
- SumR >= 98% of control,
- PF >= control OR MaxDD_R < control,
- max consecutive losses does not worsen,
- positive years/months do not worsen,
- defensive exits >= 100 historical / >= 20 forward-2026.

Overall promotion requires PASS in BOTH periods.

## Stop rule

If LAB069 fails overall, do NOT tune the 15m threshold, HIGH-vol percentile, or FAILED_EARLY definition inside this branch.
Any later action must be materially different and separately preregistered.