# Research Register

Реєстр містить лише перевірені факти та посилання на збережені артефакти. Неперевірені числові результати не вносяться.

| Project | Laboratory | Version | Date | Status | Universe | Primary result | Verdict | Canonical configuration | Supersedes | Next step | Links |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FXArena | DD Convention Audit | v002.1 | 2026-07-23 | CRITICAL AUDIT / READY | 3535 pinned GEO* episodes | P0 gross MaxDD=14.415969R; net MaxDD=15.827253R | V002 RH2/RH6-DD VERDICT INVALIDATED | Gross DD for legacy gates; net DD mandatory diagnostic | Archived net-DD gate interpretation | Exact original-seed gross-DD RH6 replay | [Erratum](Projects/FXArena/Releases/v1.2/ExitPolicyTournament_v002/ERRATUM_DD_CONVENTION.md) |
| FXArena | Exit Policy Tournament | v002 | 2026-07-23 | COMPLETED OUTPUT / AUDIT REQUIRED | 3535 pinned GEO* episodes | P1–P7 all below gross RH2 ceiling; archived DD gates used wrong convention | ORIGINAL “NO WINNER” VERDICT WITHDRAWN | Frozen P0–P7 specification | — | Close v002.1 corrected verdict | [Catalogue](Projects/FXArena/Releases/v1.2/ExitPolicyTournament_v002/P0_P7_FALSIFICATION_CATALOG.md) |
| FXArena | P5 BE@60 | v002 policy P5 | 2026-07-23 | PROVISIONAL CORRECTED WINNER | Same 3535 episodes | +1984.15R; EV +0.5613R; gross MaxDD 13.571548R; PF 4.310; 0 negative months | PROVISIONAL PASS PENDING EXACT GROSS RH6 | BE at minute 60; otherwise P0 | None until audit closes | Original sampler/seed replay | [Erratum](Projects/FXArena/Releases/v1.2/ExitPolicyTournament_v002/ERRATUM_DD_CONVENTION.md) |
| FXArena | P4 TB Deep Dive / P4b Research | v001 | 2026-07-23 | POST-HOC RESEARCH CANDIDATE | TB 1274; non-TB 2261 | +2256.51R; EV +0.6383R; gross MaxDD 12.436807R; net MaxDD 13.283629R | EXPLORATORY GO FOR CONFIRMATION; NO-GO FOR EA | TB -> frozen P4; non-TB -> frozen P5 | No canonical policy | Finalize and freeze v003 after v002.1 | [Report](Projects/FXArena/Releases/v1.2/ExitPolicyTournament_v002/FXArena_P4b_Research_v001_Report.md) |
| FXArena | GeoSweep / canonical geometry | v009 / Release v1.1 | 2026-07-23 | VALIDATED | Pinned GEO* trades | N=3535; EV=+0.523020R; Total=+1848.87R; gross MaxDD=14.416R | CANONICAL GEOMETRY RETAINED | `MICRO30 + TP2.0 + TO120` | prior geometry | Exit research over fixed entries | [Status](Projects/FXArena/STATUS.md) |
| FXArena | GEO** Validation A+B | v001 / Release v1.1 | 2026-07-23 | REJECTED | Paired pinned GEO* and GEO** sets | GS5 PASS; GS6 PASS; GS7 FAIL; Pillar B PASS | GEO** REJECTED AS CANONICAL REPLACEMENT | GEO* remains canonical | GEO** provisional | Do not re-optimize TP2/60 on same data | [Status](Projects/FXArena/STATUS.md) |

## Integrity notes

- The exact DD discrepancy is gross versus net, not chronological sorting.
- Archived v002 trade outputs remain immutable evidence; corrected interpretations are append-only audit artifacts.
- Adaptive P1–P3 and simple P6/P7 failures remain registered in the falsification catalogue.
- P4b is post-selection research and cannot retroactively win v002.
