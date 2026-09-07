# BTC_RETAIL_FLOW_EARLY_DIRECTIONAL_ACCEPTANCE_VS_ADVERSE_FAILURE_FIRST_PASSAGE_LAB_026

## Question
Does early price acceptance in the direction of the frozen Binance retail-flow signal distinguish durable 12h directional edge from failed-flow cases, while early adverse first-passage identifies signal failure?

## Frozen lineage
- Exact LAB022 non-overlapping flow-only stream: `flow_only_nonoverlap.csv`.
- Assert exactly 3209 flow events.
- Flow side is unchanged and is the only direction source.
- Frozen BTCUSDT M15 price archive / SHA from LAB023-025.
- No H4 direction, local-extreme filter, passive limit, TP, or new flow threshold.

## Signal clock / ATR
At the frozen M15 flow-signal close t0:
- entry reference = close(t0)
- ATR = causal ATR14(M15) known at t0
- favorable threshold = +0.5 ATR in FLOW direction
- adverse threshold = -0.5 ATR against FLOW direction
Thresholds are frozen and symmetric.

## First-passage states
Within each fixed observation horizon:
- 1h = next 4 completed M15 bars
- PRIMARY 2h = next 8 completed M15 bars
- 4h = next 16 completed M15 bars
classify:
- `ACCEPT_FIRST`: favorable +0.5 ATR is reached before adverse -0.5 ATR.
- `ADVERSE_FIRST`: adverse -0.5 ATR is reached before favorable +0.5 ATR.
- `AMBIGUOUS_SAME_BAR`: both thresholds are touched for the first time within the same M15 bar; excluded from primary directional comparison because OHLC cannot resolve intrabar ordering.
- `NONE`: neither threshold is reached inside the horizon.

No same-bar ordering assumption is permitted.

## Anti-tautology primary outcome
The key test is NOT total return from t0, because ACCEPT_FIRST mechanically contains +0.5 ATR.
For `ACCEPT_FIRST`, residual return = FLOW-signed move from the favorable threshold price (+0.5 ATR) to close(t0+12h), normalized by signal ATR.
For `ADVERSE_FIRST`, residual return = FLOW-signed move from the adverse threshold price (-0.5 ATR) to close(t0+12h), normalized by signal ATR.
This asks whether the first-passage state predicts what happens AFTER classification.

Also report total signed 12h return from signal close, MAE/MFE from signal, passage delay, and conditional stop-touch rates for diagnostics.

## Primary 2h hypotheses
H1: ACCEPT_FIRST residual mean > 0.
H2: ACCEPT_FIRST residual mean > ADVERSE_FIRST residual mean by >=0.25 ATR.
H3: ADVERSE_FIRST residual mean <= 0.
H4: ACCEPT_FIRST total 12h mean > baseline frozen flow mean.
H5: classification is not sparse: ACCEPT_FIRST and ADVERSE_FIRST each N>=400 pre-Aug.

## Robustness
- 1h and 4h fixed horizons must preserve the ordering `ACCEPT residual > ADVERSE residual`.
- LONG and SHORT are reported separately.
- 2022 SHORT is a mandatory bearish stress-test.
- Windows: 2021, 2022, 2023, 2024, 2025H1, 2025H2, 2026 Jan-Jul; Aug2026 reused audit only.
- 7-day cluster bootstrap, seed 20260907, 5000 resamples, for primary 2h difference in residual mean. Primary robust support requires lower 95% CI > 0.

## Gates (14)
1. Exact 3209 flow lineage + >=99% timestamp parity.
2. >=3000 eligible pre-Aug events.
3. Primary 2h ambiguous fraction <=20%.
4. Primary ACCEPT N>=400.
5. Primary ADVERSE N>=400.
6. Primary ACCEPT residual mean >0.
7. Primary ADVERSE residual mean <=0.
8. Primary residual mean difference ACCEPT-ADVERSE >=0.25 ATR.
9. Bootstrap 95% lower CI of residual difference >0.
10. Primary ACCEPT total 12h mean > all-flow baseline mean.
11. 1h ACCEPT residual > ADVERSE residual.
12. 4h ACCEPT residual > ADVERSE residual.
13. 2022 SHORT: ACCEPT residual > ADVERSE residual with each N>=30.
14. Recent 2025H2+2026: ACCEPT residual > ADVERSE residual.

PASS: >=11/14 and critical gates 1,4,5,6,8,9,13,14.
WATCH: >=8/14 with positive primary residual separation but one robustness/coverage failure.
Otherwise FAIL.

## Guardrails
- No threshold search around 0.5 ATR.
- No horizon search: 2h is primary; 1h/4h are fixed sensitivity only.
- No entry optimization in this LAB.
- No outcome-based rescue by side/year.
- August 2026 remains reused/consumed audit only.
- Live allocation remains 0.