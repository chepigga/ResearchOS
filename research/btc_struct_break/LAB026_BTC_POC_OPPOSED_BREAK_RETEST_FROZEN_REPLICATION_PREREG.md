# LAB026 — BTC_POC_OPPOSED_BREAK_RETEST_FROZEN_REPLICATION

Date: 2026-08-27
Status: FROZEN BEFORE RESULT CALCULATION

## Candidate
Exactly one regime from LAB025:

`BREAK_RETEST + POC_MIGRATION == OPPOSED`

Definition frozen from LAB025:
- build Binance BTCUSDT M1 volume-at-price approximation using the prior 24h only;
- 48 price bins;
- assign each M1 bar volume to its HLC3 bin;
- contiguous 70% value area around POC;
- compare current prior-24h POC to a lagged prior-24h POC ending 6h earlier;
- normalize POC delta by M15 ATR14 at fill;
- OPPOSED iff POC migration is at least 0.5 ATR against trade direction;
- no side selection;
- no threshold changes;
- no additional profile conditions.

## Data windows
Retained M1 coverage begins 2024-01-01.
- 2024: discovery lineage / parity check only
- 2025: primary temporal replication
- 2026: shadow only, excluded from promotion verdict

## Required replication checks
1. Exact LAB025 lineage reproduction for 2024 and 2025.
2. 2025 EV >= +0.08R.
3. 2025 PF >= 1.15.
4. 2025 N >= 30.
5. Both 2025 half-years non-negative OR one positive and the other no worse than -0.05R.
6. 1.5x cost 2025 EV > 0.
7. No BUY/SELL post-hoc selector; pooled direction result only.
8. M1 execution parity for all 2025 trades where source minutes are available: fill confirmation >=95%, outcome sign not reversed.
9. Overlap with current two-engine old-pivot core <=20% within +/-8 M15 bars.

## Portfolio admission
Compare current frozen two-engine core:
- OLD PROTECTED PIVOT + BREAK_RETEST
- OLD PROTECTED PIVOT + COMPRESSION_RELEASE SELL

against adding this POC_OPPOSED BREAK_RETEST regime under one global active position.

Admission gates on 2025 primary replication window:
- portfolio trade count increases by >=20%;
- portfolio EV remains >= +0.15R;
- portfolio PF >= 1.30;
- MaxDD worsens by no more than 50%;
- 1.5x cost portfolio EV > 0.

2026 shadow is reported but cannot promote or tune the rule.
