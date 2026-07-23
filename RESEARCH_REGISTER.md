# Research Register

| Project | Laboratory | Version | Date | Status | Primary result | Verdict | Next step | Links |
|---|---|---|---|---|---|---|---|---|
| FXArena | Exit Tournament core confirmation | v003-lite | 2026-07-23 | AVAILABLE-DATA RUN COMPLETE / HOLD | P4b +2256.51R; EV +0.6383R; gross DD 12.436807R; RH1-RH3, RH5 and RH8 PASS | STRONG CORE CONFIRMATION; formal PASS blocked by exact RH6 sampler and raw-spread RH7 replay | Close RH6 and RH7; no tuning | [Report](Projects/FXArena/Releases/v1.2/ExitTournament_v003_lite/FXArena_ExitTournament_v003_lite_Report.md) |
| FXArena | P5 BE@60 secondary | v003-lite | 2026-07-23 | FALSIFIED | Commission 9pt plus 0.05R slip gives +1792.89R before spread increase | FAIL RH7 | Keep only as frozen non-TB component inside P4b | [Verdict](Projects/FXArena/Releases/v1.2/ExitTournament_v003_lite/CORE_VERDICT.json) |
| FXArena | DD Convention Audit | v002.1 | 2026-07-23 | PARTIALLY COMPLETED | P0 gross DD 14.415969R; net DD 15.827253R | Original v002 DD verdict superseded | Historical exact P0-P7 RH6 replay | [Report](Projects/FXArena/Releases/v1.2/ExitTournament_v003_lite/FXArena_ExitTournament_v003_lite_Report.md) |
| FXArena | Exit Policy Tournament | v002 | 2026-07-23 | COMPLETED OUTPUT / INVALIDATED VERDICT | Corrected P0-P7 table preserved | No final winner claimed | Maintain negative-result catalogue | [Table](Projects/FXArena/Releases/v1.2/ExitTournament_v003_lite/P0_P7_corrected_tournament_table.csv) |
| FXArena | GeoSweep | v009 / Release v1.1 | 2026-07-23 | VALIDATED | N=3535; Total +1848.87R; EV +0.523020R; gross DD 14.416R | CANONICAL GEOMETRY RETAINED | Continue fixed-entry research | [Status](Projects/FXArena/STATUS.md) |

## Permanent DD convention

- Gate metric: gross equity MaxDD.
- Net equity MaxDD: mandatory labelled diagnostic.

## Deferred deploy tests

R1 Dukascopy and R2 forward are deferred until the pre-EA stage. P4b remains NO-GO for EA while the core verdict is HOLD.
