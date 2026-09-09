# BTC_FLOW_EVENT_CLOCK_PHASE_DRIFT_AND_CANONICAL_ANCHOR_RECOVERABILITY_LAB_059 — REPORT

## Verdict
**WATCH_SET_CLOCK_SAFE_BUT_LOW_RECOVERY**

## Canonical containment
- formal rows: 1344
- side-set contains archive side: 100.000000%
- archive clock path containment: 100.000000%
- singleton clock-state share: 68.377976%
- state count p50 / p95 / max: 1.0 / 4.0 / 5

## Divergence / resynchronization
- formal divergence episodes: 3
- recovered episodes: 3
- recover <=48h: 66.666667%
- resync hours p50 / p95 / max: 25.5 / 54.974999999999994 / 58.25

## Event certainty
- archive events: 15
- CERTAIN_EVENT: 10
- precision: 100.000000%
- archive event certain recall: 66.666667%
- false certain events: 0

## SHORT event certainty
- archive SHORT events: 9
- certain SHORT events: 7
- precision: 100.000000%
- recall: 77.777778%

## Naive abstention clock (comparison only)
- all-event union parity: 61.111111%
- SHORT-event union parity: 70.000000%

No alpha, threshold, cooldown, execution, management, cost, sizing, or live-allocation change was made.
