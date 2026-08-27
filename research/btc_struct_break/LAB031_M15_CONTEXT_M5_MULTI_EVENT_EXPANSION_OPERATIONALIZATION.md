# LAB031 — M15 context operationalization addendum

Date: 2026-08-27

This addendum is frozen before any LAB031 PnL calculation.

## M15 context episode construction
The primary M15 context pool is built from the three LAB030 streams, but M5 events are not allowed to know the original M15 trade outcome.

### OLD_PROTECTED_BREAK context
For every frozen old-protected BREAK_RETEST trade:
- context direction = trade side;
- context starts at canonical BREAK confirmation proxy `fill_idx - delay` (delay is frozen in run_v002);
- context ends at the canonical trade exit bar `fill_idx + bars`.

### LOW_RV_BREAK context
For every frozen LOW_RV BREAK_RETEST event:
- direction = canonical BREAK side;
- start = `fill_idx - delay`;
- end = `fill_idx + bars`.

### COMPRESSION_SELL context
For every frozen Compression SELL trade:
- direction = SELL;
- start = frozen `release_idx`;
- end = frozen `exit_idx`.

## Episode union / de-duplication
Context intervals of the same direction that overlap in time are merged into one context episode. BUY and SELL contexts are not merged with each other.
If BUY and SELL context episodes overlap, the overlap is marked CONFLICT and no new M5 event may be opened during that overlapping interval.

## M5 event eligibility
- M5 event must be fully known after context start and before context end.
- Event direction must equal context direction.
- Entry must occur before context end.
- One accepted event per M5 family per merged context episode.
- Event result is simulated independently for family diagnostics; portfolio router later enforces one global position.

## Stop and execution
Most recent confirmed M5 pivot-3 on the risk side at fill. TP 2.3R, BE +1R, cost 0.06R, adverse same-bar ordering. Maximum hold is capped at the earlier of 288 M5 bars (24h) or the context episode end; if neither TP nor SL is hit, exit at context-end close normalized to R.

No thresholds may be changed after this addendum.
