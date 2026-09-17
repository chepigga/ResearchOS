# GC_SHORT_CHRIS_LONG_HISTORY_REPLICATION_LAB_008H — STATUS

**Status:** `PREREGISTERED_DATA_ACCESS_BLOCKED_NOT_A_STRATEGY_FAIL`

The long-history replication definition is frozen in `GC_SHORT_CHRIS_LONG_HISTORY_REPLICATION_LAB_008H_PREREG.md`.

## What is available now
- Certified explicit-aggressor Rithmic GC: ~2026-08-03 through 2026-09-11.
- Certified explicit-aggressor AMP/CQG GC: ~2026-08-06 through 2026-09-15.
- Long FTMO XAU tick-native M1 Bid/Ask: 2022-06-01 through 2026-07-23, 1,454,538 M1 rows.
- Massive Futures API access was previously demonstrated by the user for GC contract metadata. Massive exposes historical futures trades and BBO quotes, which are suitable for a parity-first long-history reconstruction.

## Blocker
No long Massive GC trade+quote archive is currently present in ResearchOS / accessible Library / Drive, and the authenticated Massive market-data connection/API credential is not available to this GitHub Actions runtime from the current research environment.

Therefore Stage A (Massive inferred aggressor vs explicit Rithmic parity) cannot yet be computed honestly. Stage B long-history Chris replication is intentionally prohibited until Stage A passes.

This is a **data-access blocker**, not a failed trading result.

## Exact continuation after authenticated Massive access
1. Download overlapping GC trades + BBO quotes.
2. Infer aggressor causally using frozen trade-at-prevailing-BBO rule; inside-spread prints excluded.
3. Run Stage A parity gates from prereg.
4. If PASS, construct causal prior-session-volume front-contract chain for 2022-06-01→2026-07-23, reset 240-bar state at each roll.
5. Run unchanged LAB003 Chris events + unchanged LAB006 POST10 Q50 walk-forward gate.
6. Report yearly and aggregate event count, selected N, EV, WR, rejected EV, concentration and all preregistered gates.

No parameter may be changed in response to the long-history outcome.
