# Research Register

| Project | Laboratory | Version | Date | Status | Primary result | Verdict | Next step | Links |
|---|---|---|---|---|---|---|---|---|
| FXArena | Causal shallow-acceptance REV confirmation | REV_Confirmation v001 | 2026-07-24 | COMPLETED / F11 / CLOSED | 2023 N=2109; EV -0.287R; PF 0.657; total -605.73R; gross DD 184R; 12/12 negative months | `F11_SHALLOW_ACCEPTANCE_REV_FALSIFIED`; RC2-RC6 stopped; no REV EA module | Continue August exam with ContPrimary/P0 only; any future REV idea requires genuinely new causal information | [Report](Projects/FXArena/Releases/v1.2/REV_Confirmation_v001/FXArena_REV_Confirmation_v001_Report.md) |
| FXArena | REV penetration provenance audit | REV_Confirmation v001 forensic | 2026-07-24 | PUBLISHED CAUSAL DEFECT | 23,467 episodes were shallow at D3 but deepened beyond 1 ATR later; old candidate aligned with episode-final penetration | Final-episode `max_penetration_atr` is post-D3 information and prohibited as a live D3 selector | Preserve audit and source SHA; do not quote the +1171.6R reference as causal | [Audit](Projects/FXArena/Releases/v1.2/REV_Confirmation_v001/REFERENCE_LEAKAGE_AUDIT.json) |
| FXArena | Causal REV diagnostic on original reference period | REV_Confirmation v001 diagnostic | 2026-07-24 | FALSIFIED | 2024-2026H1 N=5830; EV -0.271R; PF 0.677; total -1579.95R; 29/30 negative months | Failure is not isolated to the 2023 control | Close shallow-acceptance REV research line | [Monthly](Projects/FXArena/Releases/v1.2/REV_Confirmation_v001/CAUSAL_2024_2026H1_monthly_diagnostic.csv) |
| FXArena | Final paired P4c/P0 cost adjudication | PC5-r v001 | 2026-07-24 | COMPLETED / FINAL CLOSED | Central 7.5pt/x1.5/0.05: P4c/P0=1.1045x, DD 10.820R vs 14.436R; fact 5pt/x1/0.05=1.0954x | PR1 PASS, PR2 PASS, PR4 PASS, PR5 FAIL; P4c closed permanently; deploy exit P0 | Run August exam against GEO*-TRAILING P0; no third PC5 trial | [Report](Projects/FXArena/Releases/v1.2/PC5r_Resolution_v001/FXArena_PC5r_Resolution_v001_Report.md) |
| FXArena | PC5-r full survivability map | 4x2x2 | 2026-07-24 | PUBLISHED | 16 paired cells across commission, spread and BE-slip; extreme 10pt/x1.5/0.05 still 1.1110x | Edge remains, but fact-cell +10% gate missed by 0.46 pp | Preserve as closed evidence | [Grid](Projects/FXArena/Releases/v1.2/PC5r_Resolution_v001/PC5r_cost_grid_4x2x2.csv) |
| FXArena | P4c causal exit | P4c v001 | 2026-07-24 | RESEARCH FIXTURE ONLY | Base TRAILING +2127.40R vs P0 +1889.61R; gross DD 10.618R vs 14.416R | Causal/statistical edge confirmed, but final PC5-r PR5 failed | Excluded from forward A/B and deploy | [Report](Projects/FXArena/Releases/v1.2/P4c_Causal_v001/FXArena_P4c_Causal_v001_Report.md) |
| FXArena | Archived P4b lookahead price | P4c audit | 2026-07-24 | PUBLISHED DEBT | 193 early TP2 trades; retrospective benefit +145.708807R | P4b remains non-causal research reference | Preserve numbers unchanged | [Audit](Projects/FXArena/Releases/v1.2/P4c_Causal_v001/LOOKAHEAD_COST_summary.json) |
| FXArena | TB flag regeneration | Flag-Replay v001.2 | 2026-07-24 | COMPLETED | Flag parity 3535/3535; all 622 trailing-only flags resolved | Generator validated; archived P4b not deployable | Preserve generator and SHA | [Report](Projects/FXArena/Releases/v1.2/FlagReplay_v001_2/FXArena_FlagReplay_v001_2_Report.md) |
| FXArena | Monthly vs trailing canonicalization | Closure v001.1 | 2026-07-24 | COMPLETED | MONTHLY 3535 / +1848.87R; TRAILING 3515 / +1889.61R | Separate canonical baselines established | Preserve separation | [Report](Projects/FXArena/Releases/v1.2/Closure_v001_1/FXArena_Closure_v001_1_Report.md) |
| FXArena | GEO*-MONTHLY canonical reference | Registry v4 | 2026-07-24 | CANONICAL RESEARCH REFERENCE | N=3535; total +1848.874807R; gross DD 14.415969R | Research comparisons only | Preserve unchanged | [Rows](Projects/FXArena/Releases/v1.2/Closure_v001_1/REGISTRY_V4_CANONICAL_ROWS.csv) |
| FXArena | GEO*-TRAILING canonical reference | Registry v4 | 2026-07-24 | CANONICAL LIVE REFERENCE | N=3515; archived 6pt total +1889.613320R; measured 5pt P0 +1931.350808R | August E-exam, kill metrics and deploy exit P0 | Live comparisons only against P0 | [Rows](Projects/FXArena/Releases/v1.2/Closure_v001_1/REGISTRY_V4_CANONICAL_ROWS.csv) |
| FXArena | Entry Lab market/limit/hybrid | v001 | 2026-07-24 | COMPLETED / CLOSED | E0 retained; E1-E6 all failed | F10 — market@D3+60 optimal | Do not reopen without new causal information | [Report](Projects/FXArena/Releases/v1.2/EntryLab_v001/FXArena_EntryLab_v001_Report.md) |
| FXArena | Session & Time-of-Day Lab | v001 | 2026-07-24 | COMPLETED / CLOSED | No pre-registered block passed T1-T3 | F9 — no session edge worth filtering | Keep all sessions | [Report](Projects/FXArena/Releases/v1.2/SessionTiming_v001/FXArena_SessionTiming_v001_Report.md) |
| FXArena | Selection & Sizing Lab | v001 | 2026-07-23 | COMPLETED | Fixed sizing failed; baseline distinction discovered | No promotion | Keep two-baseline law | [Report](Projects/FXArena/Releases/v1.2/SelectionSizing_v001/FXArena_SelectionSizing_v001_Report.md) |

## Permanent metric conventions

- Gate DD metric: gross equity MaxDD.
- Net equity MaxDD: mandatory labelled diagnostic.
- Bootstrap: paired moving-block, shared indices, block 20, at least 5000 iterations, seed and sampler source published.
- Absolute bootstrap formulation is rejected.

## Permanent baseline separation

- `GEO*-MONTHLY`: research comparisons only.
- `GEO*-TRAILING`: live/E-exam/kill metrics only.
- Mixing MONTHLY and TRAILING references is a registry defect.

## Closed research fronts

- F11: shallow-acceptance REV funnel falsified after causal D3 reconstruction; final-episode penetration proxy prohibited.
- Exit improvement under P4b/P4c/PC5-r: permanently closed on current data; deploy exit P0.
- Third PC5 retrial: prohibited.
- F9: session/time veto closed.
- F10: entry method closed; market@D3+60 retained.
- Fixed 0.7/1.0/1.3 sizing closed on current sample.

## Promotion boundary

The shallow-acceptance REV reference cannot be promoted because its positive economics depend on an episode-final penetration field unavailable at D3. The true causal funnel fails the clean 2023 control and the original 2024-2026H1 period. The official August/live system remains ContPrimary with P0 exits on GEO*-TRAILING; no REV module is admitted.
