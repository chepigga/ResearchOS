# Research Register

| Project | Laboratory | Version | Date | Status | Primary result | Verdict | Next step | Links |
|---|---|---|---|---|---|---|---|---|
| FXArena | TB flag regeneration and trailing P4b transfer | Flag-Replay v001.2 | 2026-07-24 | COMPLETED / STOP-ALARM | Flag parity 3535/3535; trailing P4b +2277.31R vs P0 +1889.61R; gross DD 10.618R vs 14.416R | C1 PASS, C2 PASS, C3 FAIL, C4 PASS; NOT_PROMOTED | New preregistered causal P4c or symmetric C3 adjudication; no post-hoc override | [Report](Projects/FXArena/Releases/v1.2/FlagReplay_v001_2/FXArena_FlagReplay_v001_2_Report.md) |
| FXArena | Full-universe frozen TB flag fixture | Generator v001.2 | 2026-07-24 | VALIDATED | 291659 episodes; 57811 TB; 622 trailing-only resolved, 196 TB | Generator law reproduced archived 1274 flags with zero mismatches | Preserve generator and SHA; use only under its archived observation convention | [Control](Projects/FXArena/Releases/v1.2/FlagReplay_v001_2/TB_FLAG_CONTROL_3535.json) |
| FXArena | P4b-TRAILING candidate | Registry v4 candidate | 2026-07-24 | NOT_PROMOTED | N=3515; +2277.306670R; gross DD 10.618161R; one negative month | Strong economics, frozen C3 FAIL; no official pin | Do not use as R2/live canonical reference | [Verdict](Projects/FXArena/Releases/v1.2/FlagReplay_v001_2/FINAL_VERDICT.json) |
| FXArena | Monthly vs trailing canonicalization | Closure v001.1 | 2026-07-24 | PARTIAL PASS / LIVE P0 PIN CREATED | MONTHLY 3535 / +1848.87R; TRAILING 3515 / +1889.61R | Two canonical baselines established | Preserve baseline separation | [Report](Projects/FXArena/Releases/v1.2/Closure_v001_1/FXArena_Closure_v001_1_Report.md) |
| FXArena | GEO*-MONTHLY canonical reference | Registry v4 | 2026-07-24 | CANONICAL RESEARCH REFERENCE | N=3535; total +1848.874807R; gross DD 14.415969R | Research comparisons only | Preserve unchanged | [Rows](Projects/FXArena/Releases/v1.2/Closure_v001_1/REGISTRY_V4_CANONICAL_ROWS.csv) |
| FXArena | GEO*-TRAILING canonical reference | Registry v4 | 2026-07-24 | CANONICAL LIVE REFERENCE | N=3515; total +1889.613320R; gross DD 14.415969R | August E-exam and kill-metric baseline | Live comparisons only against this pin | [Rows](Projects/FXArena/Releases/v1.2/Closure_v001_1/REGISTRY_V4_CANONICAL_ROWS.csv) |
| FXArena | Entry Lab market/limit/hybrid | v001 | 2026-07-24 | COMPLETED / CLOSED | E0 retained; E1-E6 all failed | F10 — market@D3+60 optimal | Do not reopen without new causal information | [Report](Projects/FXArena/Releases/v1.2/EntryLab_v001/FXArena_EntryLab_v001_Report.md) |
| FXArena | Session & Time-of-Day Lab | v001 | 2026-07-24 | COMPLETED / CLOSED | No block passed T1-T3 | F9 — no session edge worth filtering | Keep all sessions | [Report](Projects/FXArena/Releases/v1.2/SessionTiming_v001/FXArena_SessionTiming_v001_Report.md) |
| FXArena | Selection & Sizing Lab | v001 | 2026-07-23 | COMPLETED | Fixed sizing failed; baseline distinction discovered | No promotion | Keep two-baseline law | [Report](Projects/FXArena/Releases/v1.2/SelectionSizing_v001/FXArena_SelectionSizing_v001_Report.md) |
| FXArena | Exit Tournament core confirmation | v003-lite | 2026-07-23 | MONTHLY RESEARCH CONFIRMATION | P4b +2256.51R; gross DD 12.436807R | Not a live/deploy verdict | Causal-policy and execution closure required | [Report](Projects/FXArena/Releases/v1.2/ExitTournament_v003_lite/FXArena_ExitTournament_v003_lite_Report.md) |

## Permanent metric conventions

- Gate DD metric: gross equity MaxDD.
- Net equity MaxDD: mandatory labelled diagnostic.
- Bootstrap: paired moving-block, shared indices, block 20, at least 5000 iterations, seed and sampler source published.
- Absolute bootstrap formulation is rejected.

## Permanent baseline separation

- `GEO*-MONTHLY`: research comparisons only.
- `GEO*-TRAILING`: live/E-exam/kill metrics only.
- Mixing monthly and trailing references is a registry defect.

## Promotion boundary

P4b-TRAILING is not canonical because Flag-Replay v001.2 failed frozen C3. The current result cannot be rescued by relaxing C3 after observation. Archived P4b also has a separate retrospective-flag causality issue; live deployment requires a new frozen causal-policy decision and exact execution replay.
