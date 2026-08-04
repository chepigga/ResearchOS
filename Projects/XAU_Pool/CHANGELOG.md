# XAU_Pool Changelog

## 2026-08-04 — LAB_001 evidence and reproducibility update

- Added `pool_excess.parquet`, `baseline.parquet`, 37 permutation records and the 48-window weight schedule.
- Updated all nine Python scripts to use `$XAU_DATA`.
- Added deterministic per-iteration seeds for resumed permutation runs.
- Updated the main specification status to `FROZEN 2026-08-03` exactly as supplied.
- Preserved the supplied manifest and documented its stale README row; generated a fresh project manifest from actual bytes.
- Remaining code-quality issue: OOS-2/CONTROL scripts still print several OOS-1 labels.

## 2026-08-04 — Project initialization

- Created standalone `XAU_Pool` project under ResearchOS.
- Imported `XAU_POOL_SELECTION_LAB_001 v001` specification, appendices, report and nine Python scripts from the supplied package.
- Preserved original research artifacts without rewriting their numerical claims.
- Recorded the result as `CANDIDATE`, not canonical.
- Added evidence gaps, lineage, backlog and ADR for separation from AK47.
