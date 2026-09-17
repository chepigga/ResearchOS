# CROWDFADE_V190_HISTORICAL_REPLAY_001

## Scope

Frozen audit of `CrowdFadeMulti_v190.mq5` against the BTC datasets published in the `btc` GitHub release. No strategy retuning was performed.

Primary question: does the execution/state-machine implemented by v1.90 reproduce the historical edge attributed to the research simulator?

## Frozen v1.90 execution semantics audited

- decision clock: M5
- contrarian state: `|z| >= 1`
- entry offset: `1.50 ATR`
- initial stop: `1.00 ATR`
- pending TTL: 3h
- pause: 3h
- hold: 6h
- break-even: arm `+0.50 ATR`, lock `+0.15 ATR`
- trailing: arm `+2.50 ATR`, distance `0.50 ATR`
- opposite-z exit enabled
- chase disabled
- one active order/position per broker symbol (`HasAnyFor`)
- cooldown timestamp begins when the pending order is successfully SENT (`lastTrade=TimeCurrent()`)

Score weighting was not applied to raw-R expectancy because it changes position size rather than the underlying trade-event set.

## Data

- `BTCUSDT_flow_2021-01-2026-08.csv.zip`
- `btc_5m.zip`
- `BTCUSDT_sec.csv.zip` (2026-03-01 through 2026-08-31)

Release assets were downloaded by GitHub Actions and SHA-256 checked before use.

## Result A — long M5 bar-level replay, 2021-01 through 2026-08

Strict causal flow lookup, v1.90 order-send cooldown semantics:

- N: 6,380
- WR: 72.93%
- EV: +0.0988R after half-spread proxy
- t: 7.56
- PF: 1.37
- Sum: +630.4R
- MaxDD: 23.70R
- R/DD: 4.74
- fill rate: 45.2%

All calendar-year slices were positive, including partial 2026.

This result is secondary because M5 OHLC cannot resolve the exact intrabar ordering of fill, stop, BE and trailing events.

## Result B — 1-second live-semantics replay, 2026-03-01 through 2026-08-31

The seconds data remove most of the M5 intrabar ambiguity and reproduce the v1.90 state-machine constraint that a real pending order blocks new orders on that symbol.

- N: 629 fills
- orders sent: 1,284
- fill rate: 48.99%
- WR: 64.23%
- EV: -0.0179R after half-spread proxy
- t: -0.44
- PF: 0.949
- Sum: -11.26R
- MaxDD: 30.21R
- toxic-fill rate (`MFE < 0.5 ATR`): 37.20%
- median fill lag: 59.8 minutes

With zero spread proxy the result is only +0.0091R/trade (t=0.22, PF=1.027), i.e. statistically indistinguishable from zero.

## Critical parity finding

The released research `sim.py` does not model pending-order occupancy the same way as the live EA.

Research simulator behavior:

1. Evaluate signal at time `t`.
2. Search forward through the entire pending-validity window to determine whether that hypothetical limit will eventually fill.
3. If it never fills, `continue` immediately and allow the next signal time to be tested.
4. Only after a future fill is found does the simulator set `last=t` and apply pause.

Live v1.90 behavior:

1. Send the first eligible pending order.
2. Immediately set `lastTrade=TimeCurrent()`.
3. `HasAnyFor(symbol)` blocks every later signal while that pending order exists.
4. An unfilled order therefore consumes its real 3h lifetime and prevents fresh M5 quotes during that period.

Thus the research scheduler conditions future order availability on knowledge of whether an earlier hypothetical order will eventually fill. This is not reproducible by the live EA.

## Seconds semantics matrix

Same seconds dataset and same v1.90 entry/exit mechanics; only pending/cooldown scheduling changed:

| Semantics | N | WR | EV | PF | t | Toxic rate |
|---|---:|---:|---:|---:|---:|---:|
| live v1.90: order-send anchor + single pending | 629 | 64.23% | -0.0179R | 0.949 | -0.44 | 37.20% |
| research: pause only after future fill, anchored to signal | 991 | 74.67% | +0.2493R | 2.016 | 6.98 | 27.04% |
| research: pause only after future fill, anchored to fill | 745 | 75.17% | +0.2667R | 2.120 | 6.37 | 25.91% |

The first research-like mode almost reproduces the scale of the old v1.90 comment (`N≈1005`, `EV≈+0.206R`). This isolates execution-state semantics as the dominant source of the historical/live discrepancy.

## Interpretation

The CrowdFade directional/limit-entry idea is not disproved: the long bar-level replay remains positive. However, the exact v1.90 live state-machine is NOT validated by the old `+0.206R` research statistic.

The old research result is materially dependent on a fill-conditioned scheduling rule that the live EA cannot know causally. The current live implementation commits to the first quote for up to 3h and consequently receives a substantially more toxic fill set.

This also explains why adverse selection became much more severe in live-parity replay: toxic fills rise from ~27% under the research scheduler to ~37% under actual v1.90 scheduling.

## Decision

`CrowdFadeMulti_v190.mq5` should be treated as SHADOW / RESEARCH until execution parity is resolved. Do not use the old `EV +0.206R` as a validation statistic for the current live implementation.

Do not silently change the frozen live bot. Any alternative causal quote-management rule must be tested as a separate research branch against the same seconds dataset before promotion.
