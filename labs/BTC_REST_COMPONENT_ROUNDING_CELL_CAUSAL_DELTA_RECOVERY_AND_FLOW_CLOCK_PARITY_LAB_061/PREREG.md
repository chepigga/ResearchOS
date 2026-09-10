# BTC_REST_COMPONENT_ROUNDING_CELL_CAUSAL_DELTA_RECOVERY_AND_FLOW_CLOCK_PARITY_LAB_061 — PREREG

## Purpose
Transport/data-parity audit only. Frozen SHORT v1 alpha, thresholds, 12h non-overlap, execution, management, costs and risk are unchanged.

LAB060 established a 100% historical consistency on 407 overlap rows between archive-implied account fractions and REST longAccount/shortAccount rounded to 4 decimals. LAB061 tests whether the mathematically implied component rounding cell is tight enough to recover the archive directional decisions and the frozen 12h FLOW event clock causally.

## Frozen inputs
- Canonical source: Binance USD-M BTCUSDT daily metrics `count_long_short_ratio` from data.binance.vision.
- Live-like source: `https://www.binance.com/futures/data/globalLongShortAccountRatio`, BTCUSDT, 5m.
- REST timestamp alignment: fixed -5 minutes, inherited from LAB056 before this LAB.
- M15 aggregation: last 5m observation in each left-closed M15 bucket.
- `delta_ls_12 = ratio_t - ratio_{t-12}`.
- q20/q80: canonical archive delta, strictly prior rolling 90 calendar days, min 1000 prior M15 observations.
- Direction: delta<=q20 => BUY(+1); delta>=q80 => SHORT(-1); else NEUTRAL(0).
- FLOW events: first non-neutral directional state, then exact 12h non-overlap from previous FLOW event regardless side.
- No PnL, trade outcome, HIGH_RESPONSE, ACCEPT, management or cost metric may be used to choose any parameter in this LAB.

## Component rounding-cell construction
For a REST component reported to 4 decimal places, use half-unit rounding interval ±0.00005. No empirical error envelope and no fitted tolerance is allowed.

For observed REST `longAccount=L` and `shortAccount=S`, underlying long fraction p must satisfy the intersection:
- p in [L-0.00005, L+0.00005]
- p in [1-(S+0.00005), 1-(S-0.00005)]
- clipped to (0,1).

Map the p-cell monotonically to ratio r=p/(1-p), producing [r_lo, r_hi].

For M15, use the rounding cell attached to the same last 5m observation selected by the frozen M15 aggregation.

Causal delta interval:
- `delta_lo = r_lo_t - r_hi_{t-12}`
- `delta_hi = r_hi_t - r_lo_{t-12}`.

Recovered pointwise state:
- CERTAIN_SHORT iff delta_lo >= q80.
- CERTAIN_BUY iff delta_hi <= q20.
- CERTAIN_NEUTRAL iff delta_lo > q20 and delta_hi < q80.
- otherwise UNCERTAIN.

For event-clock recovery, UNCERTAIN emits no directional event in the direct recovered stream. This is deliberately conservative and is not a new trading rule; it is only a parity diagnostic.

## Evaluation window
Use all historical overlap available from REST within its public retention, requiring >=1500 comparable M15 rows if available. The archive may be seeded earlier than overlap solely for strictly-prior 90d thresholds.

## Metrics
1. Component-cell validity and archive-ratio coverage.
2. Cell width distribution at raw and M15 level.
3. Pointwise certainty coverage and accuracy.
4. SHORT precision and recall; BUY precision and recall.
5. Number and timestamps of false-certain and uncertain decisions.
6. Direct recovered FLOW event parity vs canonical archive event stream, all-side and SHORT-only, after 24h overlap preroll.
7. Event timestamp drift distribution for nearest same-side recovered events.

## Gates fixed before run
Pointwise transport PASS gates:
- comparable M15 N >= 1500.
- archive ratio inside component-implied cell >= 99.9%.
- certain decision coverage >= 99.0%.
- certain decision accuracy = 100%.
- false-certain N = 0.
- CERTAIN SHORT precision = 100%.
- canonical SHORT recall >= 99.0%.
- CERTAIN BUY precision = 100%.
- canonical BUY recall >= 99.0%.

Clock PASS gates:
- all-side FLOW event union match >= 95.0%.
- SHORT FLOW event union match >= 95.0%.
- no tuning.

Verdict:
- PASS_COMPONENT_CELL_FLOW_CLOCK_PARITY only if every pointwise and clock gate passes.
- WATCH_COMPONENT_CELL_SAFE_BUT_CLOCK_OR_RECALL_LOW if safety is perfect (certain accuracy=100%, false-certain=0, short precision=100%) but one or more recall/clock gates fail.
- FAIL_COMPONENT_CELL_UNSAFE if any false-certain decision exists, canonical ratio coverage <99.9%, or certain SHORT precision <100%.
- INSUFFICIENT_DATA if comparable M15 N <1500.

## Governance
- Do not widen/narrow the rounding cell after results.
- Do not add empirical residuals from LAB058.
- Do not change timestamp shift, thresholds, cooldown or event rules.
- A PASS only validates transport parity candidate; it does not authorize live capital. Frozen SHORT v1 live allocation remains 0 pending full broker-native parity and fresh OOS evidence.
