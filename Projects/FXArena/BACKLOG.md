# FXArena Backlog

## P0 — Preserve Release v.1.1 as canonical checkpoint

- **Status:** COMPLETED
- **Result:** release asset uploaded; manifest and validation artifacts preserved
- **Canonical geometry:** GEO* = `MICRO30 + TP2.0 + TO120`
- **Rejected candidate:** GEO** = `MICRO30 + TP2.0 + TO60` after GS7 FAIL
- **Rule:** no re-optimization of TP2/60 on the same data

## P1 — Regression Targets Builder v001

- **Status:** PLANNED
- **Goal:** build causal targets for adaptive exit research without changing GEO* entry selection
- **Targets:** MFE, MAE, time-to-TP, time-to-MFE, giveback, outcomes at 30/45/60/90/120 minutes
- **Universe:** pinned GEO* entries only
- **Control:** canonical TP2/TO120 execution
- **Required output:** versioned dataset, lineage, hashes, target sanity report

## P2 — Exit Regression Lab v001

- **Status:** PLANNED
- **Dependencies:** P1
- **Goal:** estimate TP2 probability, expected MFE/MAE, stagnation and giveback risk
- **Method:** causal walk-forward; no entry reselection; no lookahead
- **Pre-registered controls:** EFFICIENCY_5, BB_EXPANSION, RANGE_EXPANSION_15
- **Required gates:** reverse chronology, permutation, split-half stability, economic comparison with GEO*

## P3 — Adaptive Exit Simulator v001

- **Status:** PLANNED
- **Dependencies:** P2
- **Policies:** canonical TP2/120; selective early timeout; partial + runner; selective break-even; stagnation exit
- **Execution:** spread, commission and slippage included
- **Primary gate:** EV not below GEO* while MaxDD improves by at least 15%
- **Robustness gate:** P(DD_new < DD_GEO*) >=95%; both historical halves positive; worst month not degraded

## P4 — Execution Entry Lab

- **Status:** PLANNED
- **Goal:** market vs limit vs confirmation vs retracement on the fixed GEO* universe
- **Metric:** realized EV delta versus D3+60s market entry including fill probability

## P5 — Forward / Exam Governance

- **Status:** IN_PROGRESS
- **Scope:** ContPrimary C2 forward monitoring
- **Rules:** no changes to model, weights or threshold before the declared exam; preserve execution drag and trade logs

## Frozen / Rejected

- GEO** TP2/60 as canonical replacement — REJECTED after GS7
- Flat TP8/TP12 on GEO* — REJECTED
- H1 stop — REJECTED
- timeout >=360 or no-timeout variants — REJECTED
- repeated global timeout search on the same sample — PROHIBITED
