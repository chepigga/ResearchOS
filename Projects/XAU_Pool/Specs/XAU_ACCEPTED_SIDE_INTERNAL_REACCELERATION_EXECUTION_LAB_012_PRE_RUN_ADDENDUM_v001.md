# LAB012 pre-run addendum — deterministic simultaneous-event handling

**Status:** frozen before implementation commit and before canonical outcomes.

For serial portfolio construction only, simultaneous strong-bias break lifecycles are deduplicated deterministically:

1. At the same `break_time` and same direction, retain the event with the highest frozen LAB009 `p_accept`.
2. Exact `p_accept` ties use level priority `MID > HIGH > LOW`.
3. If both BUY and SELL directions remain at the same `break_time`, skip that timestamp as a conflict.
4. Independent-event diagnostics may retain all unique level events; this addendum affects only serial lifecycle admission.

No price/outcome information is used in this deduplication.