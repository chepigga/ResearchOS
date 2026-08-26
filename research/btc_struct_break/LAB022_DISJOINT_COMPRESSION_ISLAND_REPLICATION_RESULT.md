# LAB022 — DISJOINT_COMPRESSION_ISLAND_FROZEN_REPLICATION result

Date: 2026-08-26
Prereg: d078414c30a26fa09ba0d86fa8d9dd0bea7b16ee
Verdict: REPLICATION_BLOCKED_BY_TRADE_PROVENANCE_MISMATCH__ISLAND_NOT_PROMOTED

Frozen candidate: COMPRESSION SELL / pivot age 16–21 / riskATR 2.5–3.0 with LAB018 compression operationalization and pooled BUY+SELL virtual blocker.

Critical audit result:
- LAB020 published DEV: N42, EV +0.380476R.
- reconstructed DEV: N42, EV +0.380476R (exact match).
- LAB020 published VAL: N26, EV +0.328462R.
- reconstructed VAL: N31, EV +0.201290R (mismatch).

The exact trade-level dataset / queue provenance used for the LAB020 25-cell surface was not retained, so the 26-trade VAL lineage cannot be independently reconstructed from persisted artifacts.

Diagnostic only for the reconstructable causal implementation:
- 2024–2025 M1 replay: N15, 100% fills, 100% outcome agreement, EV +0.133R, PF 1.42.
- 2026 shadow: N8, EV -0.810R, PF 0.00.
- two-engine core VAL: N87, EV +0.214R, MaxDD 4.30R.
- adding reconstructable island: N111, EV +0.255R, MaxDD 5.36R.

The positive portfolio diagnostic does not override the provenance failure. The island is not promoted.

Next clean choices:
1. recover the original LAB020 trade-level surface dataset / compute script if it exists elsewhere, or
2. rerun the entire compression surface from a newly frozen implementation and treat resulting cells as fresh discovery, not validation of the old island.