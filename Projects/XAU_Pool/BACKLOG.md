# XAU_Pool Backlog

## XPL-001 — Complete evidence package for LAB_001

- **Priority:** P0
- **Status:** IN_PROGRESS
- **Dependencies:** raw dataset and original runtime outputs
- **Goal:** make LAB_001 independently reproducible
- **Done when:** raw-data hash, selected trade-level outputs, execution logs and environment lock complete the now-saved pool/baseline/permutation/model artifacts
- **Risks:** unavailable source bytes; changed external dataset; inability to prove preregistration freeze
- **Required files:** raw release asset SHA256; selected trade table; logs; dependency lock
- **Next action:** hash the `ak47` raw-data release asset and add the remaining outputs

## XPL-002 — Portable reproducibility repair

- **Priority:** P0
- **Status:** IN_PROGRESS
- **Dependencies:** imported Python scripts
- **Goal:** remove `/home/claude/` assumptions without changing research logic
- **Done when:** `$XAU_DATA` flow works in a clean environment; OOS-2/CONTROL print labels are corrected; dependency versions are locked; smoke test passes
- **Risks:** accidental logic drift while refactoring
- **Required files:** current scripts and a small non-sensitive fixture
- **Next action:** make a code-only label/dependency patch; do not change selection logic

## XPL-003 — Portfolio and FTMO execution validation

- **Priority:** P0
- **Status:** PLANNED
- **Dependencies:** XPL-001 and XPL-002
- **Goal:** convert overlapping candidate trades into account-level performance
- **Done when:** simultaneous-position policy, sizing, spread/commission/slippage, daily 3%, MaxLoss 10% EOD-trailing and BestDay 50% are tested on frozen trades
- **Risks:** candidate edge may collapse under overlap and prop constraints
- **Required files:** trade-level selected candidates and broker conditions
- **Next action:** create `XAU_POOL_PORTFOLIO_EXECUTION_LAB_002` spec

## XPL-004 — Simplified 9-feature selector

- **Priority:** P1
- **Status:** PLANNED
- **Dependencies:** sealed protocol and XPL-001
- **Goal:** test whether the 9 coincidence features preserve the effect of the 36-feature model
- **Done when:** same frozen splits, gates, permutation and execution model are applied without retuning
- **Risks:** post-hoc simplification overfits the known periods
- **Required files:** canonical pool and feature matrix
- **Next action:** reserve a new forward/OOS period before implementation

## XPL-005 — Forward validation

- **Priority:** P0
- **Status:** BLOCKED
- **Dependencies:** data strictly after 2026-07-23
- **Goal:** test the frozen candidate without re-fitting decisions on known history
- **Done when:** preregistered forward horizon and gates are completed
- **Risks:** insufficient sample; regime change; selection drift
- **Required files:** new XAUUSD bid/ask data
- **Next action:** accumulate untouched forward data
