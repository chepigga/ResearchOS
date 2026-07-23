# Research Register

Реєстр містить лише перевірені факти та посилання на збережені артефакти. Неперевірені числові результати не вносяться.

## Validated results

| Project | Laboratory | Version | Date | Status | Universe | Primary result | Verdict | Canonical configuration | Supersedes | Next step | Links |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FXArena | GeoSweep / canonical geometry | v009 / Release v.1.1 | 2026-07-23 | VALIDATED | Pinned GEO* trades | N=3535; EV=+0.523020R; Total=+1848.87R; MaxDD=14.416R | Canonical geometry retained | `MICRO30 + TP2.0 + TO120` | prior C2 execution geometry | Adaptive Exit research over fixed entries | [Status](Projects/FXArena/STATUS.md) |
| FXArena | TimeoutSweep near-miss | v009b | 2026-07-23 | COMPLETED / CANDIDATE | GEO** TP2/60 pinned trades | N=3698; EV=+0.528467R; Total=+1954.27R; MaxDD=14.998R | Promoted to additional validation, not canonical | `MICRO30 + TP2.0 + TO60` | — | GS5/GS6/GS7 + Pillar B validation | [Status](Projects/FXArena/STATUS.md) |
| FXArena | GEO** Validation A+B | v001 / Release v.1.1 | 2026-07-23 | REJECTED | Paired pinned GEO* and GEO** sets | GS5 PASS; GS6 PASS; GS7 FAIL; Pillar B PASS | GEO** rejected as canonical replacement | GEO* remains canonical | GEO** provisional status | Do not re-optimize TP2/60 on same data | [Status](Projects/FXArena/STATUS.md) |

## GS7 decision record

GEO** failed the preregistered block-bootstrap gates:

- `P(DD_GEO** > DD_GEO* + 0.5R) = 37.88%`, required `<5%`.
- `P(Total_GEO** > Total_GEO*) = 87.78%`, required `>=95%`.

The result is economically interesting but insufficiently stable to replace GEO*.

## Active research

| Project | Research line | Status | Locked baseline | Objective | Link |
|---|---|---|---|---|---|
| FXArena | Regression Heads / Adaptive Exit Layer | PLANNED | GEO* `MICRO30 + TP2.0 + TO120` | reduce drawdown through causal selective exits without changing entry selection | [Backlog](Projects/FXArena/BACKLOG.md) |

## Governance note

GitHub Release `v.1.1` is the current FXArena checkpoint. `Projects/FXArena/STATUS.md` is the operational source of truth; this register is the factual ledger. Older backlog snapshots do not override later completed validation reports.
