# BTC_RETAIL_FLOW_REACCEPTANCE_POST_RECOVERY_PERSISTENCE_AND_SECOND_FAILURE_LAB_031

## Question
After a frozen FULL_REACCEPT state from LAB030, does post-reaccept persistence distinguish genuine renewed directional acceptance from a dead bounce that soon fails again?

## Frozen lineage
- Exact LAB030 `failure_recovery_stream.csv`.
- Use only rows with `full_reaccept == true`.
- Pre-Aug lineage target: 701 FULL_REACCEPT states.
- Levels are frozen from the original signal:
  - origin = `signal_close`
  - acceptance level = `entry = signal_close + side * 0.5 * ATR14`
- Original terminal horizon remains `signal_time + 12h`.

## Primary post-reaccept state
The reaccept bar itself does NOT count as persistence.
Starting from the next completed M15 bar after `full_reaccept_time`:

### PERSIST2
The next two completed M15 closes are both strictly on the flow side of the frozen acceptance level:
`side * (close - entry) > 0` for two consecutive bars.
Classification time = close time of the second qualifying bar.

### SECOND_FAIL
Before PERSIST2 is achieved, two consecutive completed M15 closes occur back through the original signal price:
`side * (close - signal_close) <= 0` for two consecutive bars.
Classification time = close time of the second bad bar.

### UNRESOLVED
Neither PERSIST2 nor SECOND_FAIL occurs before original `signal_time + 12h`.

If PERSIST2 and SECOND_FAIL could only be inferred at the same timestamp, classify as UNRESOLVED; do not impose optimistic intrabar/within-close ordering.

## Anti-tautology outcomes
Primary outcome is residual return from the classification close to original +12h, normalized by frozen ATR14:
`side * (close_12h - classification_close) / ATR14`.
Thus the price movement used to define PERSIST2/SECOND_FAIL is excluded from the residual.

Report:
- PERSIST2 residual
- SECOND_FAIL residual
- UNRESOLVED residual from first post-reaccept close to horizon (descriptive only)
- PERSIST2 minus SECOND_FAIL residual gap
- time from reaccept to classification
- post-classification MAE/MFE

## Secondary fixed audit
Without promoting a new rule, also measure first-passage from reacceptance:
- +0.5 ATR further in flow direction from the frozen acceptance level
- versus two-close SECOND_FAIL through origin
within the remaining original 12h horizon.
This audit cannot replace the PERSIST2 primary state.

## Windows
- 2021
- 2022
- 2023
- 2024
- 2025 H1
- 2025 H2
- 2026 Jan-Jul
- Aug 2026 reused audit only
- HIST = 2021 through 2025 H1
- RECENT = 2025 H2 through 2026 Jul
- ALL_PRE_AUG

Report LONG / SHORT separately and 2022 SHORT stress test.

## Bootstrap
7-day cluster bootstrap, 5000 draws, fixed seed 20260908, on PERSIST2 residual minus SECOND_FAIL residual.

## PASS gates
1. exact LAB030 pre-Aug FULL_REACCEPT lineage >= 690.
2. PERSIST2 N >= 150 pre-Aug.
3. SECOND_FAIL N >= 80 pre-Aug.
4. PERSIST2 residual > 0 pre-Aug.
5. SECOND_FAIL residual < PERSIST2 residual.
6. residual gap >= 0.50 ATR.
7. 7d bootstrap lower 95% CI > 0.
8. RECENT PERSIST2 N >= 30.
9. RECENT PERSIST2 residual > 0.
10. RECENT PERSIST2 residual > RECENT SECOND_FAIL residual.
11. 2025H2 and 2026 PERSIST2 residuals have the same positive sign.
12. 2022 SHORT PERSIST2 N >= 15 and residual > 0.
13. LONG and SHORT PERSIST2 residuals both > 0.
14. PERSIST2 win rate > 55% pre-Aug.

PASS requires >=11/14 and critical gates 1,4,7,8,9,10. WATCH if state separation is strong but recent transfer is incomplete. Otherwise FAIL.

## Guardrails
- No new threshold search.
- No stop/TP/horizon optimization.
- No side-specific rescue.
- No regime filter.
- PERSIST2 is a state audit, not a promoted live/re-entry rule.
- August 2026 is reused audit only.
- Live allocation remains 0.