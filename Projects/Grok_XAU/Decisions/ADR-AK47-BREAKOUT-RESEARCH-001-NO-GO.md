# ADR-AK47-BREAKOUT-RESEARCH-001-NO-GO

**Decision:** Reject the non-tight AK47 breakout geometry family as a canonical research or deployment baseline.

## Evidence

- Aggregate walk-forward EV is positive but weak.
- Two of six unseen test splits are negative.
- Aggregate selected OOS MaxDD exceeds 10%.
- WF2 fails family-wise permutation: real best Calmar 4.93 versus permutation p95 41.86.
- Six train windows select six different configurations.
- The sealed tail is negative.

## Consequences

1. Stop base breakout grid research under this specification.
2. Do not run the ML addendum; the base entry class returned NO-GO.
3. Do not tune BUY-only, sessions, SL/TP, or filters on the inspected sample.
4. Keep V15 tight trailing as a separate tick-native execution question.
5. No live deployment or risk increase is authorized.
