# Research Register

| Project | Laboratory | Version | Date | Status | Primary result | Verdict | Next step | Links |
|---|---|---|---|---|---|---|---|---|
| FXArena | Session & Time-of-Day Lab | v001 | 2026-07-24 | COMPLETED / STAGE 1 CLOSED | All P4b blocks positive overall; S3 DD loss share 42.48% at 25.205% trade share; sign unstable across years | F9 — no session edge worth filtering; Stage 2 not run | Keep all sessions; do not tune boundaries | [Report](Projects/FXArena/Releases/v1.2/SessionTiming_v001/FXArena_SessionTiming_v001_Report.md) |
| FXArena | Selection & Sizing Lab | v001 | 2026-07-23 | PARTIAL COMPLETION / B CONTROL STOP | Control exact; sizing +1924.73R but gross DD 15.185R; trailing q0.96 N=3515 vs PINNED N=3535 | A FAIL SA2/SA5; B NOT ADJUDICATED; no composition or promotion | Resolve monthly-top versus trailing-90d threshold convention in a new frozen spec | [Report](Projects/FXArena/Releases/v1.2/SelectionSizing_v001/FXArena_SelectionSizing_v001_Report.md) |
| FXArena | Sizing tiers 0.7/1.0/1.3 | v001 Part A | 2026-07-23 | FALSIFIED UNDER FROZEN GATES | Tercile EV monotonic; +75.86R total; SA4 p=0.004975; P(total improvement)=99.58% | FAIL: gross DD 15.185R and paired P(DD>P0+0.5)=56.18% | Do not tune weights on same sample | [Verdict](Projects/FXArena/Releases/v1.2/SelectionSizing_v001/FINAL_VERDICT.json) |
| FXArena | Selection threshold grid | v001 Part B | 2026-07-23 | STOPPED AT CONTROL | Trailing top-{3,4,5,6}% curve recorded; historical monthly top-4% reproduces PINNED exactly | NO VERDICT | Preregister one threshold convention before rerun | [Curve](Projects/FXArena/Releases/v1.2/SelectionSizing_v001/B_threshold_curve.csv) |
| FXArena | Exit Tournament core confirmation | v003-lite | 2026-07-23 | AVAILABLE-DATA RUN COMPLETE / HOLD | P4b +2256.51R; EV +0.6383R; gross DD 12.436807R | STRONG CORE CONFIRMATION; formal PASS blocked by exact RH6 and spread RH7 replay | Close RH6 and RH7; no tuning | [Report](Projects/FXArena/Releases/v1.2/ExitTournament_v003_lite/FXArena_ExitTournament_v003_lite_Report.md) |
| FXArena | P5 BE@60 secondary | v003-lite | 2026-07-23 | FALSIFIED | Commission 9pt plus 0.05R slip gives +1792.89R before spread increase | FAIL RH7 | Keep only as frozen non-TB component inside P4b | [Verdict](Projects/FXArena/Releases/v1.2/ExitTournament_v003_lite/CORE_VERDICT.json) |
| FXArena | GeoSweep | v009 / Release v1.1 | 2026-07-23 | VALIDATED | N=3535; Total +1848.87R; EV +0.523020R; gross DD 14.416R | CANONICAL GEOMETRY RETAINED | Continue fixed-entry research | [Status](Projects/FXArena/STATUS.md) |

## Permanent metric conventions

- Gate DD metric: gross equity MaxDD.
- Net equity MaxDD: mandatory labelled diagnostic.
- Bootstrap: paired moving-block, shared indices, block 20, at least 5000 iterations, seed and sampler source published.
- Absolute bootstrap formulation is rejected.

## Closed time-filter result

SessionTiming v001 found no pre-registered session block eligible for a veto. Hour-level diagnostics are non-decisional, and changing session boundaries requires a new frozen hypothesis rather than reuse of this sample.

## Deferred deploy tests

R1 Dukascopy and R2 forward remain deferred until the pre-EA stage. P4b remains NO-GO for EA while its exit core verdict is HOLD.
