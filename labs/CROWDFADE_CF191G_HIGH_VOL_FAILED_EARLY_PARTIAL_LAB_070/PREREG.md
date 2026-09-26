# LAB070 — CF191G HIGH-VOL FAILED-EARLY 50% REDUCTION + RUNNER — PREREGISTRATION

## Purpose

Test a materially different defensive action after LAB069 full-exit failed historically:
`HIGH entry volatility + FAILED_EARLY at t+15m + position still open -> close 50% at t+15m and leave 50% under frozen CF191g management`.

Entry logic and all state definitions remain frozen.

## Frozen condition

Exactly LAB069/LAB068:
- `vol_percentile_7d >= 0.80` using prior 2016 completed M5 bars;
- first 15 completed 1m bars after fill;
- `expansion15_atr = side * (close15-entry)/entry_ATR`;
- `eff15 = side * (close15-entry) / sum(abs(1m close changes))`;
- `FAILED_EARLY = expansion15_atr <= 0 OR eff15 <= 0`;
- frozen position must still be open after t+15m.

No threshold changes.

## Action

At the completed t+15m close:
- close exactly 50% of the original position;
- retain exactly 50% as a runner;
- runner keeps the original frozen CF191g stop/BE/trailing/6h exit path.

Because the runner remains open, occupancy/re-entry timing remains identical to the frozen control trade.

## Costs

Costs are linear in notional.
Modified trade R for acted events:
`R_partial = 0.5 * R_at_15m_close + 0.5 * R_frozen_control`.

This preserves one full-position equivalent cost because each half contributes half of its notional-weighted cost.

## Primary outputs

Separately 2021–2025 and 2026:
- N / WR / EV / PF / SumR / MaxDD_R / R/DD;
- max consecutive losses;
- positive years/months;
- number of partial reductions;
- total saved_R versus control;
- total given_up_R versus control;
- net local delta_R;
- right-tail retention: fraction of acted frozen winners >= +1.5R and their modified mean R.

## PASS criteria

A period passes only if:
- R/DD >= control;
- SumR >= 98% of control;
- PF >= control OR MaxDD_R < control;
- max consecutive losses does not worsen;
- positive years/months do not worsen;
- actions >= 100 historical / >= 20 forward-2026.

Overall promotion requires PASS in BOTH periods.

## Stop rule

If LAB070 fails overall, do not tune the 50% fraction, 15m timing, P80 threshold, or FAILED_EARLY definition in this branch.
Any further management action needs a new independent mechanism.