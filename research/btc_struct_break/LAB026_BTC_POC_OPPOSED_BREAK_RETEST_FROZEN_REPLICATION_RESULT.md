# LAB026 — BTC_POC_OPPOSED_BREAK_RETEST_FROZEN_REPLICATION result

Date: 2026-08-27
Prereg: c3b03622f7a2d52d1304856c025aa0c635a7fa36
Verdict: POC_OPPOSED_BREAK_RETEST_REPLICATION_FAIL

## Seed 2025
- N37
- EV +0.094R
- PF 1.21
- MaxDD 6.42R
- 1.5x cost remains positive
- overlap with current two-engine core: 8.1%

## M1 execution parity
- expected 37
- M1 fill confirmed 34
- fill rate 91.9% (fails prereg >=95%)
- outcome agreement 88.2%
- M1 EV +0.158R, PF 1.43

The sign does not reverse, but exact execution parity gate fails because 3/37 M15 fills are not confirmed on retained M1.

## Portfolio 2025
Current two-engine core:
- N34
- EV +0.264R
- PF 1.67
- MaxDD 3.24R

Core + POC_OPPOSED seed:
- N64
- EV +0.156R
- PF 1.38
- MaxDD 6.60R

Frequency increases strongly, but MaxDD more than doubles and fails the prereg <=50% worsening gate.

## 2026 shadow
The seed deteriorates materially in 2026 and remains a regime-stability warning. 2026 is excluded from the formal promotion gate.

## Decision
Do not admit POC_OPPOSED as a third engine. Preserve it as a research clue that failed POC migration / value rejection may matter, but further work should target a causal mechanism or independent replication rather than side-selection or threshold tuning.
