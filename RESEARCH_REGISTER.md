# Research Register

| Project | Laboratory | Version | Date | Status | Primary result | Verdict | Next step | Links |
|---|---|---|---|---|---|---|---|---|
| FXArena | Monthly vs trailing canonicalization | Closure v001.1 | 2026-07-24 | PARTIAL PASS / P4b TRANSFER STOP | MONTHLY exact: 3535 / +1848.874807R / DD 14.415969R; TRAILING exact: 3515 / +1889.613320R / DD 14.415969R | Two canonical baselines established; live P0 pin created; P4b C1-C4 not executed | Exact full-universe causal P4/TB flag replay for 622 trailing-only episodes | [Report](Projects/FXArena/Releases/v1.2/Closure_v001_1/FXArena_Closure_v001_1_Report.md) |
| FXArena | GEO*-MONTHLY canonical reference | Registry v4 | 2026-07-24 | CANONICAL RESEARCH REFERENCE | N=3535; total +1848.874807R; gross DD 14.415969R | Use only for research laboratory comparisons | Preserve unchanged | [Rows](Projects/FXArena/Releases/v1.2/Closure_v001_1/REGISTRY_V4_CANONICAL_ROWS.csv) |
| FXArena | GEO*-TRAILING canonical reference | Registry v4 | 2026-07-24 | CANONICAL LIVE REFERENCE | q0.96/90d; N=3515; total +1889.613320R; gross DD 14.415969R | Official August E-exam and kill-metric baseline | Compare live results only against this pin | [Rows](Projects/FXArena/Releases/v1.2/Closure_v001_1/REGISTRY_V4_CANONICAL_ROWS.csv) |
| FXArena | P4b transfer to trailing selection | Closure v001.1 | 2026-07-24 | STOPPED BEFORE ECONOMIC GATES | Frozen P4b flags cover 2893/3515; 622 trailing-only flags absent | STOP-ALARM; no P4b trailing pin; deployment blocked | Reproduce original P4 flag signal-by-signal on full universe, then run C1-C4 | [Coverage](Projects/FXArena/Releases/v1.2/Closure_v001_1/P4b_TRAILING_COVERAGE_AUDIT.json) |
| FXArena | Entry Lab market/limit/hybrid tournament | v001 | 2026-07-24 | COMPLETED / CLOSED | E0 +2256.51R, gross DD 12.436807R; E1-E6 all failed | F10 — market@D3+60 optimal | Do not reopen without new causal information | [Report](Projects/FXArena/Releases/v1.2/EntryLab_v001/FXArena_EntryLab_v001_Report.md) |
| FXArena | Session & Time-of-Day Lab | v001 | 2026-07-24 | COMPLETED / STAGE 1 CLOSED | No pre-registered block passed T1-T3 | F9 — no session edge worth filtering | Keep all sessions | [Report](Projects/FXArena/Releases/v1.2/SessionTiming_v001/FXArena_SessionTiming_v001_Report.md) |
| FXArena | Selection & Sizing Lab | v001 | 2026-07-23 | COMPLETED / HISTORICAL CONTROL DIAGNOSED | Sizing FAIL; monthly/trailing mismatch identified | No promotion; mismatch resolved by separate Closure v001.1 pins | Keep two-baseline law | [Report](Projects/FXArena/Releases/v1.2/SelectionSizing_v001/FXArena_SelectionSizing_v001_Report.md) |
| FXArena | Exit Tournament core confirmation | v003-lite | 2026-07-23 | MONTHLY RESEARCH CONFIRMATION | P4b +2256.51R; gross DD 12.436807R | Not a live/deploy verdict | Complete trailing transfer and execution replay | [Report](Projects/FXArena/Releases/v1.2/ExitTournament_v003_lite/FXArena_ExitTournament_v003_lite_Report.md) |

## Permanent metric conventions

- Gate DD metric: gross equity MaxDD.
- Net equity MaxDD: mandatory labelled diagnostic.
- Bootstrap: paired moving-block, shared indices, block 20, at least 5000 iterations, seed and sampler source published.
- Absolute bootstrap formulation is rejected.

## Permanent baseline separation

- `GEO*-MONTHLY`: research comparisons only.
- `GEO*-TRAILING`: live/E-exam/kill metrics only.
- Mixing monthly and trailing references is a registry defect.

## Closed research fronts

- F9: session/time veto closed.
- F10: entry method closed; market@D3+60 retained.
- Fixed 0.7/1.0/1.3 sizing closed on current sample.

## Deploy boundary

P4b remains NO-GO for EA until a frozen full-universe causal TB flag fixture exists, trailing C1-C4 pass, and exact execution/deploy replay closes.