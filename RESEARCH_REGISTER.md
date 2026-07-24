# Research Register

| Project | Laboratory | Version | Date | Status | Primary result | Verdict | Next step | Links |
|---|---|---|---|---|---|---|---|---|
| FXArena | Causal P4 exit and deploy court | P4c v001 | 2026-07-24 | COMPLETED / FAIL PC5 | TRAILING +2127.40R vs P0 +1889.61R; gross DD 10.618R vs 14.416R; PC1-PC4 PASS | PC5 FAIL; deploy exit remains P0; no P4c pin | Use GEO*-TRAILING P0 for August exam; new exit rules require new frozen evidence | [Report](Projects/FXArena/Releases/v1.2/P4c_Causal_v001/FXArena_P4c_Causal_v001_Report.md) |
| FXArena | Archived P4b lookahead price | P4c v001 audit | 2026-07-24 | PUBLISHED DEBT | 193 early TP2 trades; P4b +2256.51R -> causal P4c +2110.80R | Archived P4b advantage includes +145.71R retrospective benefit | Keep P4b numbers unchanged but research-only | [Audit](Projects/FXArena/Releases/v1.2/P4c_Causal_v001/LOOKAHEAD_COST_summary.json) |
| FXArena | P4c execution-cost inheritance | PC5 | 2026-07-24 | FALSIFIED FOR DEPLOY | Central stress +1903.21R / DD 10.820R; commission9-only +2002.19R | FAIL PC1 under costs; spread x1.5 alone passes | Do not tune cost gate or policy on same sample | [Costs](Projects/FXArena/Releases/v1.2/P4c_Causal_v001/PC5_cost_decomposition.csv) |
| FXArena | P4c-TRAILING candidate | Registry v4 candidate | 2026-07-24 | NOT_PROMOTED / RESEARCH ONLY | N=3515; +2127.402776R; gross DD 10.618161R; one negative month | Strong causal economics, insufficient cost headroom | Not valid for R2/live canonical reference | [Gates](Projects/FXArena/Releases/v1.2/P4c_Causal_v001/PC1_PC5_gates.csv) |
| FXArena | TB flag regeneration and trailing P4b transfer | Flag-Replay v001.2 | 2026-07-24 | COMPLETED / RESEARCH ONLY | Flag parity 3535/3535; archived P4b trailing +2277.31R | Retrospective flag use prevents deploy | Superseded for deploy by causal P4c court | [Report](Projects/FXArena/Releases/v1.2/FlagReplay_v001_2/FXArena_FlagReplay_v001_2_Report.md) |
| FXArena | Full-universe frozen TB flag fixture | Generator v001.2 | 2026-07-24 | VALIDATED | 291659 episodes; 57811 TB; 622 trailing-only resolved | Generator parity exact | Preserve generator and SHA | [Control](Projects/FXArena/Releases/v1.2/FlagReplay_v001_2/TB_FLAG_CONTROL_3535.json) |
| FXArena | Monthly vs trailing canonicalization | Closure v001.1 | 2026-07-24 | COMPLETED | MONTHLY 3535 / +1848.87R; TRAILING 3515 / +1889.61R | Two canonical baselines established | Preserve separation | [Report](Projects/FXArena/Releases/v1.2/Closure_v001_1/FXArena_Closure_v001_1_Report.md) |
| FXArena | GEO*-MONTHLY canonical reference | Registry v4 | 2026-07-24 | CANONICAL RESEARCH REFERENCE | N=3535; total +1848.874807R; gross DD 14.415969R | Research comparisons only | Preserve unchanged | [Rows](Projects/FXArena/Releases/v1.2/Closure_v001_1/REGISTRY_V4_CANONICAL_ROWS.csv) |
| FXArena | GEO*-TRAILING canonical reference | Registry v4 | 2026-07-24 | CANONICAL LIVE REFERENCE | N=3515; total +1889.613320R; gross DD 14.415969R | August E-exam, kill metrics and deploy exit P0 | Live comparisons only against this pin | [Rows](Projects/FXArena/Releases/v1.2/Closure_v001_1/REGISTRY_V4_CANONICAL_ROWS.csv) |
| FXArena | Entry Lab market/limit/hybrid | v001 | 2026-07-24 | COMPLETED / CLOSED | E0 retained; E1-E6 all failed | F10 — market@D3+60 optimal | Do not reopen without new causal information | [Report](Projects/FXArena/Releases/v1.2/EntryLab_v001/FXArena_EntryLab_v001_Report.md) |
| FXArena | Session & Time-of-Day Lab | v001 | 2026-07-24 | COMPLETED / CLOSED | No block passed T1-T3 | F9 — no session edge worth filtering | Keep all sessions | [Report](Projects/FXArena/Releases/v1.2/SessionTiming_v001/FXArena_SessionTiming_v001_Report.md) |
| FXArena | Selection & Sizing Lab | v001 | 2026-07-23 | COMPLETED | Fixed sizing failed; baseline distinction discovered | No promotion | Keep two-baseline law | [Report](Projects/FXArena/Releases/v1.2/SelectionSizing_v001/FXArena_SelectionSizing_v001_Report.md) |

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

- Exit deploy improvement under archived P4b and causal P4c: closed; deploy exit P0.
- F9: session/time veto closed.
- F10: entry method closed; market@D3+60 retained.
- Fixed 0.7/1.0/1.3 sizing closed on current sample.

## Promotion boundary

P4c passes causal, total, DD, calendar and bootstrap gates but fails the preregistered execution-cost gate. It is not a deploy candidate and cannot be rescued by adjusting costs, activation time or targets after observation. The official August/live exit remains P0 on GEO*-TRAILING.
