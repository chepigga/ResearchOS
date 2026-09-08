# BTC_RETAIL_FLOW_REACCEPTANCE_EXTENSION_SEQUENCE_LATENCY_AND_CYCLE_DURATION_REGIME_SPLIT_LAB_033

## Question
Can fixed causal sequence/latency variables known by the time of frozen `EXTENSION050_FIRST` explain the sharp 2025H2 vs 2026 post-extension residual split without introducing a new price threshold or tuned router?

## Frozen lineage
Primary universe is exact LAB032 `EXTENSION050_FIRST` events only.
- `FULL_REACCEPT` and +0.5 ATR extension definitions remain exactly frozen from LAB030/LAB032.
- Outcome remains LAB032 post-extension residual to the original signal +12h horizon.
- August 2026 remains reused audit only.

## Exact causal clocks
Join by `flow_id` to:
- LAB026 primary 2h first-passage stream for initial acceptance time;
- LAB030 failure/recovery stream for first frozen two-close failure, origin reclaim, full reaccept and bad-close count;
- LAB032 extension stream for extension classification time and residual.

No feature may use information after the LAB032 extension classification time.

## Ten preregistered sequence features
1. `signal_to_accept_h` = initial flow signal -> first +0.5 ATR ACCEPT passage.
2. `accept_to_failure_h` = initial ACCEPT -> first frozen ORIGIN_CLOSE2 failure.
3. `failure_to_origin_reclaim_h`.
4. `failure_to_full_reaccept_h`.
5. `reaccept_to_extension_h`.
6. `signal_to_extension_h`.
7. `accept_to_extension_h`.
8. `extra_bad_closes_before_reaccept` from frozen LAB030.
9. `cycle_count_accept_to_extension`: count complete frozen failure->reaccept cycles after initial ACCEPT and up to extension.
10. `origin_bad_close_count_accept_to_extension`: count completed M15 closes on the wrong side of original signal price between initial ACCEPT and extension.

Features 9-10 are reconstructed from the same frozen M15 price archive. Cycle definition is fixed: two consecutive M15 closes through origin create a failure state; after failure, first completed M15 close back through the frozen acceptance level creates a full reaccept and increments cycle count. No alternative cycle threshold is allowed.

## Primary regime comparison
Compare only:
- 2025H2: 2025-07-01 <= signal_time < 2026-01-01
- 2026 Jan-Jul: 2026-01-01 <= signal_time < 2026-08-01

For each of the 10 features:
- Mann-Whitney U, reported as rank-biserial effect `rbc = 2*AUC-1`, where positive means feature tends larger in 2026 than 2025H2.
- Two-sided p-value.
- Benjamini-Hochberg FDR across exactly 10 features; q<=0.10 is preregistered significance.
- Medians in 2025H2 and 2026.

## Independent economic alignment test
Across all pre-Aug EXTENSION050_FIRST events, compute Spearman rho between each feature and frozen post-extension residual.
A candidate sequence feature is `aligned` only when:
- 2025H2-vs-2026 |rbc| >= 0.30;
- BH q <= 0.10;
- pre-Aug |Spearman rho| >= 0.10 and p <= 0.05;
- direction is economically aligned: if the feature is larger in 2026 (rbc>0), rho must be positive because 2026 residual is better; if smaller in 2026 (rbc<0), rho must be negative.

This is a mechanism discovery criterion only; it does NOT promote a cutoff/router.

## Side composition and robustness audits
- Report LONG/SHORT composition in 2025H2 and 2026.
- Repeat 2025H2-vs-2026 feature effects within LONG and SHORT where each side has >=15 events per period; no FDR gate on side audits.
- Report yearly medians for any aligned feature.
- 7-day cluster bootstrap the 2026-minus-2025H2 median difference for each aligned feature, 5000 draws, fixed seed 20260908. This is support only.

## Path parity guardrail
For events with complete LAB026/LAB030/LAB032 clocks:
- initial acceptance must precede first failure;
- first failure must precede/full-reaccept;
- full reaccept must precede extension;
- reconstructed first failure and full reaccept from M15 should match frozen LAB030 timestamps in >=99% of eligible events.
If parity fails, scientific verdict is invalid/FAIL regardless of feature statistics.

## PASS gates
1. Exact LAB032 EXTENSION050 pre-Aug lineage >=590.
2. 2025H2 N>=45 and 2026 N>=45.
3. Clock ordering valid >=99%.
4. Reconstructed failure timestamp parity >=99%.
5. Reconstructed full-reaccept timestamp parity >=99%.
6. At least one of 10 features has BH q<=0.10.
7. At least one feature has |rbc|>=0.30.
8. At least one feature satisfies full aligned economic criterion.
9. At least one aligned feature has bootstrap 95% CI for 2026-minus-2025H2 median difference excluding zero in the same direction.
10. The aligned feature is not merely side composition: same directional 2025H2-vs-2026 effect exists within at least one side with >=15/period.
11. No more than 2/10 features have >10% missingness.
12. August reused audit is not used to select or rescue any feature.

PASS = >=9/12 and gates 1-5, 8 critical. WATCH if regime separation exists after FDR but economic alignment/robustness is incomplete. FAIL if no FDR-supported causal sequence feature or parity fails.

## Guardrails
- No new price level, stop, TP, entry, horizon, side filter or cutoff search.
- No model/classifier tuning.
- No feature additions after seeing results.
- This lab explains regime structure; it does not create a live rule.
- Live allocation remains 0.