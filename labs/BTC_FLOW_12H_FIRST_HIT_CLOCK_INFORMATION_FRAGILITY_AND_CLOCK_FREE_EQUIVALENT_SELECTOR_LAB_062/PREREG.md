# BTC_FLOW_12H_FIRST_HIT_CLOCK_INFORMATION_FRAGILITY_AND_CLOCK_FREE_EQUIVALENT_SELECTOR_LAB_062

## Purpose
Determine whether the frozen BTC SHORT v1 edge materially depends on the path-dependent 12h first-hit FLOW clock, or whether a clock-free local SHORT selector preserves the same economic edge with better transport robustness.

This is an architecture audit, not a post-hoc repair of LAB056-061 and not a live authorization.

## Frozen components
- BTCUSDT Binance USD-M retail `count_long_short_ratio`, M15 last observation.
- `delta_ls_12 = ratio_t - ratio_{t-12}`.
- Strictly-prior rolling 90 calendar day q20/q80, minimum 1000 prior M15 observations.
- Contrarian SHORT state iff `delta_ls_12 >= q80`.
- Activation level = prior 12h futures low (48 closed M15 bars).
- TOUCH within signal+12h.
- ACCEPT = first of the first 4 M15 closes from TOUCH with `close <= level`.
- HIGH_RESPONSE logic = directional futures 60m response above strictly-prior 90d median among valid all-touch events, min 40 prior events.
- Trade only SHORT + HIGH_RESPONSE + ACCEPT.
- Frozen execution/management: SL=2.5 ATR14(signal), TP=1.5R, horizon=signal+12h; accept bar excluded from intrabar SL/TP; later ambiguous bar SL-first; ADVERSE_FIRST -0.5R within first 120m does not exit; before recovery, 2 consecutive closes > level => PERSISTENT_FAILURE exit now.
- Costs 5bps primary, 10bps stress; risk reporting 0.25% per trade.

## Selector families fixed before PnL
A. `FROZEN_FIRST_HIT_12H`
- Original all-side FLOW: any BUY/SHORT threshold state can emit if >=12h since prior emitted FLOW event.
- Then retain SHORT events only for downstream logic.

B. `SHORT_RUN_ONSET_FROZEN_ROUTER`
- Clock-free local selector.
- Emit SHORT only when current M15 is SHORT and immediately previous M15 is not SHORT.
- No 12h timer; BUY states do not move a global clock.
- HIGH_RESPONSE threshold is taken from the canonical/frozen all-touch event history strictly before the candidate timestamp. This isolates whether the 12h clock itself is necessary.

C. `SHORT_RUN_ONSET_NATIVE_ROUTER`
- Same local SHORT run-onset selector.
- HIGH_RESPONSE threshold is recomputed causally from this selector's own prior valid all-touch events over 90 calendar days, min 40.
- This tests a fully clock-free lineage rather than inheriting canonical clock history.

D. `ALL_SHORT_STATE_DIAGNOSTIC`
- Every M15 SHORT state is a candidate.
- Diagnostic only: quantify duplication/clustering and whether raw state carries edge before deduplication. It cannot be selected as a deployable winner in this LAB.

No other cooldown, refractory period, score, threshold margin, session filter, ATR filter, or outcome-derived deduplication may be introduced after results.

## Historical window
Use official Binance archive data over the maximal overlap supported by the frozen historical router lineage, with at least 2021-2026 coverage when available. Data download/transport fallbacks may change only retrieval, not research logic.

Report separately:
- FULL overlap.
- `2021-2024` lineage/history slice.
- `2025+` confirmatory/reused slice. This is not claimed as fresh OOS because prior project research has already examined this era.

## Canonical parity gate
Before interpreting selector economics, the rebuilt `FROZEN_FIRST_HIT_12H` stream must match persisted frozen FLOW timestamps+sides >=99.5% over common overlap, and frozen router state must match where persisted overlap exists. Otherwise verdict is `FAIL_BASELINE_REPLICATION`.

## Information-fragility test fixed before outcomes
For each canonical FLOW event, suppress only the exact M15 threshold state that created that event and rebuild the frozen first-hit event stream for the next 72h, with all other states unchanged.
Report:
- fraction of single-state deletions that alter >=1 later FLOW event;
- fraction altering >=2 later FLOW events;
- number of changed timestamps/sides within 72h;
- resynchronization latency where measurable.
This is structural sensitivity only; no PnL is used to choose deletions.

## Primary economic metrics
For A/B/C and diagnostic D report:
- candidate SHORT signals;
- TOUCH, HIGH_RESPONSE, ACCEPT/trades;
- trades/week;
- EV/trade 5bps and 10bps;
- PF 5bps/10bps;
- CumR;
- MaxDD R and DD at 0.25%;
- win rate;
- exit distribution;
- year-by-year N/EV/PF;
- share positive years;
- overlap/concurrency and share trades occurring <12h after prior trade.

## Clock-free equivalence gates
`SHORT_RUN_ONSET_FROZEN_ROUTER` is economically equivalent enough to justify a separate future freeze only if, on 2025+ reused-confirmatory slice:
1. >=30 completed trades;
2. EV5 > 0;
3. PF5 >= 1.20;
4. EV10 > 0;
5. DD at 0.25% <=4%;
6. EV5 >= 70% of frozen baseline EV5 when both are defined;
7. positive-year share over FULL >=60%;
8. max concurrent 0.25%-risk trades <=4.

`SHORT_RUN_ONSET_NATIVE_ROUTER` passes architecture-independence only if it independently satisfies the same absolute gates 1-5 and 7-8, and EV5 >=60% of frozen baseline EV5 on 2025+.

## Verdicts
- `CLOCK_FREE_EQUIVALENT_SUPPORTED`: baseline parity passes and B passes equivalence gates; C may be PASS or WATCH but must not show catastrophic degradation.
- `CLOCK_FREE_NATIVE_SUPPORTED`: B and C both pass their preregistered gates.
- `CLOCK_IS_ECONOMICALLY_MATERIAL`: baseline parity passes but B has EV5<=0 or PF5<1 on >=30 2025+ trades, or severe DD >4%.
- `WATCH_CLOCK_FREE_PROMISING_NOT_EQUIVALENT`: positive but one or more equivalence gates fail without catastrophic failure.
- `INSUFFICIENT_DATA`: required sample sizes unavailable.
- `FAIL_BASELINE_REPLICATION`: canonical parity fails.

## Guardrails
- No live allocation change; remains 0.
- Frozen SHORT v1 remains unchanged.
- No selector from LAB062 becomes production without a new frozen specification and future OOS/forward validation.
- No outcome-driven parameter changes inside LAB062.