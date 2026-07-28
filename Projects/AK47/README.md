# AK47 — XAUUSD Algorithmic Research Project

AK47 is the canonical ResearchOS project for XAUUSD strategy research, EA development, causal trade-lifecycle analysis, regime classification, execution survival and prop-challenge validation.

## Current state

The project has a viable but regime-dependent entry/management architecture. The main unresolved questions are:

- whether M3 adaptive giveback creates causal exit edge;
- whether full M3 close should be replaced by partial exit + runner;
- which entry profiles are stable across 2022–2026;
- how to separate strong continuation, failed breakout, two-sided chop and exhaustion;
- how RS001 per-direction gating should react without excessive lag.

The 2026 auction-rhythm WATCH profile `0.50 < pre30_alternation <= 4/7` failed sealed replay on 2022–2025 and is permanently marked NO-GO.

## Architecture

`Market State -> Entry Profile -> Execution -> M3 Lifecycle -> Risk Governor -> Trade`

## Canonical files

- [STATUS.md](STATUS.md) — current operational state.
- [BACKLOG.md](BACKLOG.md) — ordered research queue.
- [FALSIFICATION_LOG.md](FALSIFICATION_LOG.md) — rejected hypotheses and anti-curve-fitting record.
- `Research/` — reports, preregistrations and Python labs.
- `Code/` — MQL5 and Python sources.
- `Data/` — manifests and dataset references, not uncontrolled raw dumps.
- `Releases/` — frozen project checkpoints.
- `Archive/` — superseded material retained for traceability.

## Governance

- GitHub is the single source of truth.
- Chat conclusions are non-canonical until committed.
- Every hypothesis must have a frozen rule before OOS validation.
- Failed OOS profiles cannot be silently retuned on the same data.
- MT5 is used for final replication; Python is the main research environment.
