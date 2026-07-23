# FXArena Backlog

## FXA-IMPORT-001 — Import Research v1.2

- **Priority:** P0
- **Status:** COMPLETED
- **Source:** `Archive_Arena.zip`
- **Result:** 26 artifacts indexed with SHA256 and classified by code/spec/report/result/model/archive role
- **Manifest:** `Archive/Imports/FXArena_v1_2/IMPORT_MANIFEST.csv`
- **Notes:** large CSV and binary assets remain referenced through checkpoint / GitHub Release `v1.0`; no numerical claims reconstructed from chat memory

## FXA-IMPORT-002 — Register named research lines

- **Priority:** P0
- **Status:** COMPLETED
- **Registered:** C2, GEO*, TrendBirth, MarketGeometry, OS Prototype, TimeoutSweep, BattleOutcome RiskFirst
- **Caution:** imported historical status does not automatically promote every result to production canonical

## FXA-DATA-001 — Verify Release v1.0 assets

- **Priority:** P0
- **Status:** READY
- **Goal:** match large tick/bar/result assets in Release `v1.0` against manifest hashes and source lineage
- **Done when:** every external asset has exact filename, hash, date range, broker/source, schema and consuming laboratory

## FXA-VALIDATE-001 — Reproduce GEO* control

- **Priority:** P0
- **Status:** PLANNED
- **Goal:** reproduce the frozen control using the imported C2 reference and exact release assets
- **Risk:** universe mismatch or execution drift

## FXA-VALIDATE-002 — Validate TrendBirth and MarketGeometry

- **Priority:** P1
- **Status:** PLANNED
- **Goal:** reproduce results on the full canonical GEO* universe with causal feature windows and explicit execution costs

## FXA-ARCH-001 — Operationalize FXArena OS layers

- **Priority:** P1
- **Status:** PLANNED
- **Goal:** connect Feature → Model → Entry → Execution → Risk without promoting research-only modules prematurely
