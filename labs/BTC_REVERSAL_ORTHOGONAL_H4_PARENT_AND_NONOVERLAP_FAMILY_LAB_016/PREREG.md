# BTC_REVERSAL_ORTHOGONAL_H4_PARENT_AND_NONOVERLAP_FAMILY_LAB_016 — PREREG

## Question
Can a genuinely orthogonal H4 parent-event family add positive reversal fills outside ±24h of the frozen canonical `P975_T25` selected-event clock, while preserving the exact frozen `VF1_MATURE` execution architecture?

## Frozen canonical reference
- Canonical reference = LAB015 `P975_T25` selected REV events.
- Frozen canonical router = LAB014/015 DEV-trained BTC-only CONT/REV logistic models; T25 cutoff from canonical P97.5 DEV confidence distribution.
- Frozen maturity/execution for all candidate families: first event(s) shadow only; real trade only after >=1 prior virtual fill in the same 7d episode (`VF1_MATURE`); `LIMIT_R0.50_T60`; no market fallback; SL = 1.0 × parent M15/H4 event bar range used by first-hit engine; TP = 1.5R; same-bar ambiguity = SL-first; primary cost = 5 bps round trip.
- No family-specific router refit, entry retune, stop retune, target retune, TTL retune, or maturity retune.

## H4 clock
A completed H4 bar is recognized only on UTC-aligned closes at 03:45, 07:45, 11:45, 15:45, 19:45, 23:45 in the Binance 15m panel. All features and thresholds must be known at that completed H4 close.

## Orthogonality rule — mandatory
1. Build each H4 family causally.
2. Score with frozen T25 router and retain routed REV only.
3. REMOVE every retained H4 candidate whose event time is within ±24h of ANY frozen canonical `P975_T25` selected REV event.
4. Only the remaining non-overlap population may enter virtual-fill episode construction and PnL.

A family with insufficient non-overlap after this filter is rejected as a second engine regardless of pre-filter quality.

## Frozen discovery families
### 1. H4_DISPLACEMENT_EXTREME
- completed H4 close-to-close absolute log return over 16 M15 bars;
- >= prior 30d causal 97.5th percentile of completed-H4 absolute returns;
- direction = sign(H4 return).

### 2. H4_FAILED_EXTENSION
- completed H4 absolute return >= prior 30d causal 95th percentile;
- last completed 60m return has opposite sign to the H4 return;
- last 60m magnitude >= 25% of absolute H4 return;
- direction = sign(H4 return), because frozen branch trades reversal against the parent displacement.

### 3. H4_7D_PIVOT_SWEEP_RECLAIM
- prior 7d high/low uses bars strictly before the current completed H4 block;
- bearish parent: H4 high sweeps above prior7d high and H4 close finishes back below prior7d high;
- bullish parent: H4 low sweeps below prior7d low and H4 close finishes back above prior7d low;
- minimum sweep excursion = 0.10 × current H4 high-low range;
- parent direction = +1 for high sweep (reversal SELL), -1 for low sweep (reversal BUY).

## Event de-duplication
Within each family apply a 4h cooldown after a chosen H4 event. No cross-family suppression is allowed before reporting; families are evaluated independently.

## Evaluation windows
- 2025_H2 = 2025-07-01 through 2025-12-31 UTC.
- 2026_JAN_JUL = 2026-01-01 through 2026-07-31 UTC.
- POOLED_RECENT = union of the two windows.
- AUG2026 = reused/consumed audit only; cannot promote.
- Historical 2021–2025H1 is descriptive only.

## Primary family status
This LAB is discovery-only for the H4 families. No family can become canonical from LAB016. The best admissible family by prereg gates may be labeled `PROMISING_ORTHOGONAL_H4_DISCOVERY` and must receive its own replication LAB.

## Discovery gates per family
1. Non-overlap selected REV >= 10 in 2025_H2.
2. Non-overlap selected REV >= 10 in 2026_JAN_JUL.
3. Real fills >= 5 in 2025_H2.
4. Real fills >= 5 in 2026_JAN_JUL.
5. Mean R/fill > 0 in both recent windows.
6. PF > 1.2 in both recent windows.
7. CumR > 0 in both recent windows.
8. Pooled frequency >= 0.75 real fills/month.
9. Pooled worst leave-one-episode-out remaining R > 0.
10. Pooled max DD <= 4R.

`PROMISING_ORTHOGONAL_H4_DISCOVERY` requires >=8/10 and gates 5,6,7 all pass. Otherwise reject.

## Portfolio descriptive audit
For each H4 family report frozen canonical `P975_T25` + H4 family union:
- incremental real fills/month;
- cumulative R;
- mean R/fill;
- PF;
- max DD;
- fraction of union fills originating from H4 family.
This union is descriptive and cannot promote a family.

## Causality / anti-leakage
- H4 thresholds are rolling and shifted by one completed H4 observation.
- Prior 7d levels exclude the current H4 block.
- Orthogonality uses only event timestamps from the already-frozen canonical selector, not their future outcomes.
- VF1 activation uses actual virtual fill_time strictly earlier than the current event.
- No future outcome, year label, MFE/MAE, TP/SL result, or post-event bar may determine parent selection or orthogonality.

## Status constraints
- 2025H2/2026 are reused research windows, not fresh holdouts.
- August 2026 is consumed/reused.
- A positive LAB016 result is mechanism discovery only.
- No live allocation is authorized.
