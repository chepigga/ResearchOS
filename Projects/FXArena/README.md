# FXArena

Дослідницький та інженерний проєкт торгової системи FXArena.

## Current state

FXArena має валідований checkpoint у GitHub Release `v.1.1`.

- Канонічна модель: **C2**
- Канонічна геометрія: **GEO*** = `MICRO30 + TP2.0 + TO120`
- GEO** (`TP2/60`) не замінив канон через GS7 block-bootstrap FAIL
- Поточний research-напрямок: **Regression Heads / Adaptive Exit Layer** поверх незмінних GEO* входів

Актуальний оперативний стан завжди читати в [STATUS.md](STATUS.md). Чергу робіт — у [BACKLOG.md](BACKLOG.md). Підтверджені результати — у глобальному [RESEARCH_REGISTER.md](../../RESEARCH_REGISTER.md).

## Architecture

`Feature -> Statistical Model -> Decision/Entry -> Execution -> Risk -> Trade`

FXArena розглядається як Market State / Decision Engine, а не як окремий індикаторний ансамбль.

## Directories

- `Specs/` — preregistered technical specifications.
- `Reports/` — completed laboratory reports.
- `Results/` — versioned outputs with per-result README.
- `Code/` — versioned MQL5, Python, notebooks and tools.
- `Decisions/` — ADRs.
- `Experiments/` — active experimental material.
- `Releases/` — FXArena checkpoints.
- `Archive/` — superseded material retained for traceability.

## Governance

- GitHub is the single source of truth.
- Chat conclusions are non-canonical until committed or included in a release.
- A later validated report supersedes an older backlog snapshot.
- Rejected candidates cannot be silently re-tuned on the same data.
