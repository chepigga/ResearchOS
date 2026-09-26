# LAB068 — CF191G VOLATILITY × POST-ENTRY EXPANSION GEOMETRY — PREREGISTRATION

## Purpose

Explain the LAB064 2026 high-volatility degradation without introducing a volatility filter.

Diagnostic only; canonical CF191g entry and management remain unchanged.

## Frozen volatility axis

Reuse LAB064 exactly:
- vol_metric = ATR14_M5 / close_M5
- causal percentile vs prior 7 days / 2016 completed M5 bars
- MID = P40_60
- HIGH = P80_100

No new volatility threshold.

## Fixed post-entry expansion diagnostics

Using already frozen LAB054 targets:
- MFE15 / MFE30 / MFE60 / MFE120
- MAE15 / MAE30 / MAE60 / MAE120
- impulse60 = +1 ATR favorable before -0.5 ATR adverse
- final R

Derived fixed diagnostics:
- FAST_0P5 = MFE15 >= 0.5 ATR
- EXPAND_1R_60 = MFE60 >= 1.0 ATR
- LATE_EXPAND = MFE15 < 0.5 ATR AND MFE60 >= 1.0 ATR
- FAILED_EXPAND = MFE60 < 1.0 ATR
- RIGHT_TAIL = final R >= +1.5R

## Time splits

Report MID vs HIGH separately:
- 2021–2023
- 2024–2025
- 2026 Mar–Aug

## Primary question

Is the 2026 high-vol penalty specifically an expansion/right-tail failure rather than excess adverse excursion?

For 2026 HIGH vs MID report:
- FAST_0P5 rate
- EXPAND_1R_60 rate
- FAILED_EXPAND rate
- impulse60 rate
- mean MFE15/30/60/120
- mean MAE15/30/60/120
- RIGHT_TAIL rate
- final EV/PF

Also compare the same signs in 2021–23 and 2024–25 to determine whether this is a recent regime change.

## Interpretation rule

If HIGH in 2026 has materially lower expansion/right-tail but MAE is not materially worse, classify the failure as 'lost directional expansion under high ATR', not 'volatility causes more stop pressure'.

No action/risk multiplier is promoted from LAB068.
