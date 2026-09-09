# BTC_FLOW_EVENT_CLOCK_PHASE_DRIFT_AND_CANONICAL_ANCHOR_RECOVERABILITY_LAB_059

## Status
Pre-registered before any LAB059 computation. No PnL/trade outcomes are used.

## Frozen upstream objects
- Frozen SHORT v1 alpha/rules are unchanged.
- 12h non-overlap rule is unchanged: a nonzero FLOW state may emit only when `t - last_event_time >= 12h`; emitted event resets `last_event_time=t`.
- LAB058 fixed REST shift = -5 minutes and LAB058 causal ratio residual envelope are frozen.
- LAB058 evaluation decision file is the sole input for this audit.

## Question
Can the frozen 12h event clock be represented causally as a **set of possible clock states** when REST transport is ambiguous, such that:
1. the true archive clock is never excluded,
2. ambiguity is explicit rather than guessed,
3. the state set naturally collapses back to a single canonical anchor without altering the frozen rule?

## Possible-side construction
For each M15 row, use LAB058 `delta_lo`, `delta_hi`, `q20`, `q80`.
- SHORT (-1) is possible iff `delta_hi >= q80`.
- BUY (+1) is possible iff `delta_lo <= q20`.
- NEUTRAL (0) is possible iff interval `[delta_lo, delta_hi]` intersects `(q20,q80)`.
- If `transport_fresh == false`, conservatively allow all three sides {-1,0,+1}.
No observed archive side is used to build the possible-side set.

## Set-valued clock transition
State = possible `last_event_time` only; side of the prior event does not affect the frozen cooldown.
For every current state and every possible side:
- if side != 0 and cooldown is free, emit `(time, side)` and set `last_event_time=time`;
- otherwise emit no event and retain the prior clock state.
Deduplicate identical `last_event_time` states after every row.

## Initialization / evaluation
- Process LAB058 evaluation from its first M15 row.
- Use the first 24h as causal clock preroll only.
- Formal LAB059 metrics begin 24h after evaluation start, matching LAB058 clock-audit hygiene.
- Archive clock used only as ground truth for scoring, never for set transitions.

## Metrics
1. `archive_path_containment`: share of formal rows where the true archive `last_event_time` is contained in the causal state set.
2. `side_set_contains_archive`: share of rows where archive pointwise side is in the causal possible-side set.
3. `clock_state_singleton_share`: share of rows with exactly one possible clock state.
4. `max_clock_state_count` and p50/p95 state count.
5. Divergence episodes: start when state count goes 1 -> >1; end on first return to 1. Report duration and number of M15 rows.
6. `anchor_recovery_rate_48h`: fraction of divergence episodes that return to singleton within 48h.
7. median/p95/max resynchronization time.
8. Event certainty: at each row, compare event outputs across all possible transitions:
   - `CERTAIN_EVENT(side)` only if every possible transition emits the same side at this timestamp;
   - `CERTAIN_NO_EVENT` only if every possible transition emits no event;
   - otherwise `AMBIGUOUS_EVENT_CLOCK`.
9. `certain_event_precision`: among CERTAIN_EVENT rows, exact match to archive event timestamp+side.
10. `archive_event_certain_recall`: fraction of archive events recovered as CERTAIN_EVENT.
11. SHORT-specific certain-event precision/recall.
12. `false_certain_event_n`.
13. Naive LAB058 abstention clock is reproduced for comparison only; it cannot determine the verdict.

## Pre-registered gates
PASS_SET_CLOCK_RECOVERABLE only if all are true:
- formal rows >= 1000
- side_set_contains_archive == 100%
- archive_path_containment == 100%
- certain_event_precision == 100%
- false_certain_event_n == 0
- SHORT certain-event precision == 100% (if any certain SHORT events)
- anchor_recovery_rate_48h >= 90%
- median resynchronization time <= 24h

WATCH_SET_CLOCK_SAFE_BUT_LOW_RECOVERY if containment/precision gates pass but one or more recovery gates fail.
FAIL_SET_CLOCK_EXCLUDES_CANONICAL if archive path containment <100% or any false-certain event occurs.

## Governance
- No threshold/envelope/cooldown changes after seeing results.
- No use of PnL or downstream trade outcomes.
- No live allocation is authorized by this lab.
- Any new clock rule (calendar reset, grace period, phase snapping, alternative cooldown) is explicitly out of scope and would require a new preregistered lab + fresh OOS.
