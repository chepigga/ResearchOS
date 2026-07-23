# FXArena Release v1.1 — Frozen Fixtures

Prepared: 2026-07-23
Status: **BLOCKED / INCOMPLETE**

This release must freeze the exact fixtures used for C2, GEO*, GEO**-PROV and TB v002 validation. No aggregate-only substitute is acceptable.

## Verified available from Archive_Arena.zip

- C2_SPEC_FROZEN.md
- C2_Control_Reference_2026-07-22.md
- C2_frozen_livewindow.csv
- C2_p_by_episode.csv
- weights_schedule_C2.pkl
- FXArena_GeoSweep_v009_report.md
- FXArena_TimeoutSweep_TZ_v009b_2026-07-22.md
- FXArena_TimeoutSweep_v009b_FINAL_report.md
- FXArena_TrendBirthExecution_v002_report.md
- FXArena_MarketGeometry_v001_report.md
- FXArena_OS_Prototype_v001_report.md
- wf_toolkit.py

## Blocking missing assets

- ContPrimary_Model_C2.mqh
- c2_trades_loop.pkl
- v009 24-cell table
- GEO* model weights
- trades_MICRO30_TP2_TO120.csv.gz
- trades_MICRO30_TP2_TO60.csv.gz
- v009b cell table
- seven TB v002 output files referenced by its report

## Publication gate

Release v1.1 is publishable only when every blocking asset is present and SHA256-indexed. Until then it must not be cited as satisfying the GEO** validation prerequisite.
