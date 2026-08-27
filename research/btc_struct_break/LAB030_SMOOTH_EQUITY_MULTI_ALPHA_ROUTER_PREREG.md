# BTC_SMOOTH_EQUITY_MULTI_ALPHA_ROUTER_LAB_030 — PREREG

Date: 2026-08-27

## Objective
Construct the smoothest causal multi-alpha portfolio from already discovered BTC M15 streams. Primary objective is minimum drawdown / monthly variance subject to positive expectancy and adequate trade frequency, not maximum EV.

## Frozen primary streams
1. OLD_PROTECTED_BREAK_RETEST — frozen old-protected-pivot BREAK_RETEST core.
2. COMPRESSION_SELL — frozen old-protected-pivot COMPRESSION SELL core.
3. LOW_RV_BREAK_RETEST — BREAK_RETEST with frozen LAB024 low 1h realized-volatility state (<20th trailing percentile); no threshold changes.
4. POC_OPPOSED_BREAK_RETEST — frozen LAB025 POC_MIGRATION == OPPOSED; no side selection and no threshold changes.

Rejection states from LAB027–029 are diagnostic only and cannot be included in the primary router.

## Time windows
Because POC and M1-derived profile data begin in 2024, primary apples-to-apples router comparison is 2024–2025, with 2026 shadow only. Older years are used for streams that have coverage only as descriptive background, never to advantage one combination.

## Router universe
Enumerate all non-empty subsets of the four frozen streams. Also test equal-risk one-position routing under deterministic stream priority fixed as:
OLD_PROTECTED_BREAK_RETEST > COMPRESSION_SELL > LOW_RV_BREAK_RETEST > POC_OPPOSED_BREAK_RETEST.
No post-result priority changes.

## Smoothness metrics
For each stream and subset:
- N, trades/year, EV, PF, total R, MaxDD
- profitable-month percentage
- monthly R standard deviation
- worst calendar month
- rolling 3-month R minimum and standard deviation
- rolling 6-month R minimum and standard deviation
- Ulcer Index on trade-level equity
- max consecutive losing trades
- Recovery Factor = total R / MaxDD
- contribution concentration: largest stream share of positive net contribution and largest month share
- pairwise monthly-return correlation between alpha streams

## Primary admission constraints
A candidate router must satisfy on 2024–2025 combined:
- EV > 0
- PF >= 1.20
- trades/year >= 35
- MaxDD <= 8R
- profitable months >= 55%
- Recovery Factor >= 2
- no single month contributes >40% of total positive net R
- 1.5x cost stress EV > 0

## Primary ranking
Among candidates satisfying all admission constraints, rank lexicographically by:
1. lowest MaxDD
2. lowest monthly R standard deviation
3. lowest Ulcer Index
4. highest worst rolling-3M R
5. highest trades/year

No optimization over numeric weights. Equal-risk only.

## 2026
2026 is shadow only and cannot promote a candidate. Material deterioration must be reported explicitly.

## Verdicts
- SMOOTH_EQUITY_ROUTER_FOUND__FREEZE_FOR_REPLICATION
- NO_MULTI_ALPHA_ROUTER_MEETS_SMOOTHNESS_GATE
