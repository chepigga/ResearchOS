# BTC_RETAIL_FLOW_SIGNAL_TIME_LOCAL_EXTREME_PROXIMITY_AND_MAE_CONDITIONING_LAB_024

## Question
Does the frozen Binance retail-flow directional signal work better when BTC is already near, at, or just through a causal local extreme at the exact flow-signal close?

## Frozen lineage
- Exact LAB022 `flow_only_nonoverlap.csv` stream, asserted N=3209.
- `side=+1` = contrarian FLOW LONG; `side=-1` = contrarian FLOW SHORT.
- Exact frozen Binance BTCUSDT M15 price archive/checksum already used in LAB023.
- No H4 fields/context/direction may be read.
- No new entry trigger in the primary test: entry clock remains the flow-signal close.

## Causal price-state features at signal close
All local-extreme reference levels exclude the current M15 bar and use only bars already closed before the signal bar.
For each horizon H in {4,8,16} M15 bars = {1h,2h,4h}:
- FLOW LONG directional distance: `(signal_close - prior_H_low) / ATR14`.
- FLOW SHORT directional distance: `(prior_H_high - signal_close) / ATR14`.
Smaller/negative values mean price is nearer to or already beyond the directional local extreme.

Also freeze:
- `signal_bar_sweep`: LONG if current low < prior4 low and close > prior4 low; SHORT mirror.
- `recent_sweep_1to4`: at least one side-aligned causal sweep/reclaim on the current or preceding 3 M15 closes, each sweep compared only with its own prior4 bars.

## Outcomes
Primary outcome has no stop/TP and uses the same 12h direction target as LAB022:
- signed close-to-close return after 12h, normalized by ATR14 known at flow-signal close.
Path diagnostics over the next 12h:
- MAE in ATR in FLOW direction.
- MFE in ATR in FLOW direction.
- whether a hypothetical 1.5 ATR stop would have been touched before the 12h horizon.
These are outcomes only, never features.

## Threshold-free primary tests
For each H={1h,2h,4h}, compute Spearman:
- proximity distance vs signed 12h return; expected rho < 0.
- proximity distance vs 12h MAE; expected rho > 0.
Report pre-Aug pooled, 2022 SHORT, LONG/SHORT separately, and recent 2025H2+2026.

## Fixed economic bins
Predeclared before run for every horizon:
- `<=0.25 ATR`
- `(0.25,0.50]`
- `(0.50,1.00]`
- `(1.00,2.00]`
- `>2.00 ATR`
No best-bin promotion.

Fixed contrast on the 4h horizon:
- NEAR = distance <=0.50 ATR.
- FAR = distance >=1.50 ATR.
Compare N, EV, t, PF-like positive/negative payoff ratio, median MAE/MFE, 1.5ATR stop-touch rate.
Bootstrap 5000 event resamples with seed 20260907 for NEAR-minus-FAR EV and MAE differences.

## Windows
- 2021
- 2022 bearish stress
- 2023
- 2024
- 2025 H1
- 2025 H2
- 2026 Jan-Jul
- Aug 2026 reused audit only
- ALL_PRE_AUG
- POOLED_RECENT = 2025H2 + 2026 Jan-Jul

## Primary gates
1. Frozen flow lineage exactly 3209 and >=99% timestamp parity.
2. Valid signal-time feature rows pre-Aug >=3000.
3. 4h proximity-return Spearman rho < 0 pre-Aug.
4. 4h proximity-MAE Spearman rho > 0 pre-Aug.
5. NEAR4H N >=500 pre-Aug.
6. NEAR4H mean signed12 ATR exceeds ALL_PRE_AUG baseline by >=0.10 ATR.
7. NEAR4H mean signed12 ATR > FAR4H mean.
8. NEAR4H median MAE at least 0.25 ATR lower than FAR4H.
9. NEAR4H 1.5ATR stop-touch rate at least 10 percentage points lower than FAR4H.
10. Bootstrap 95% CI of NEAR-minus-FAR EV is entirely >0.
11. 2022 SHORT NEAR4H N>=40 and mean signed12 ATR >0.
12. LONG and SHORT NEAR4H pooled pre-Aug both have positive mean signed12 ATR.
13. POOLED_RECENT NEAR4H mean signed12 ATR >0.
14. `recent_sweep_1to4` mean signed12 ATR exceeds baseline by >=0.10 ATR pre-Aug.

PASS_MECHANISTIC_PROXIMITY requires >=11/14 and critical gates 1,3,4,6,7,13.
WATCH if >=7/14 with positive NEAR4H EV but robustness incomplete.
Otherwise FAIL_NO_SIGNAL_TIME_PROXIMITY_MECHANISM.

## Guardrails
- No threshold search.
- No entry delay or post-flow confirmation.
- No TP/stop/horizon optimization.
- No calendar/regime filter.
- August 2026 is reused audit only.
- This LAB can identify a conditioning mechanism but cannot promote a live filter without a separate preregistered replication.
- Live allocation = 0.