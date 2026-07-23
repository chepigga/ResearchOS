# FXArena Research v1.2 — Source Import

- Import date: 2026-07-23
- Source archive: `Archive_Arena.zip`
- Source archive role: verified user-supplied checkpoint
- Source market-data location: GitHub Release `v1.0`
- Import policy: preserve original filenames and hashes; do not reconstruct missing artifacts from chat memory.

## Import treatment

- Small source code, specifications, reports, and compact result tables are copied into the governed ResearchOS structure.
- Large CSV outputs and binary model files remain referenced as release/checkpoint assets and are indexed by SHA256 in `IMPORT_MANIFEST.csv`.
- The two `ResearchOS-1.0` archives are treated as legacy snapshots, not canonical project content.
- `FXArena_TrendBirthExecution_v001_report.md` is an empty source file (0 bytes) and is preserved as supplied.
- `weights_schedule_C2.pkl` and `weights_schedule_C2.1.pkl` are byte-identical and share SHA256 `d81c3c670074763509db9da9dcdf44913e7e951710b69a3a8d72f482d2ee483b`; neither is silently deleted or selected as canonical.

## Canonicality

This import establishes provenance and availability. It does not automatically promote every historical result to canonical status. Canonical decisions must be made from the imported reports/specifications and recorded separately.
