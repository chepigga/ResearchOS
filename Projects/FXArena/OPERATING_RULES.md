# FXArena Operating Rules

## Canonical-state lookup rule

Before answering any question about the current state of FXArena, the research assistant must first verify the repository in this order:

1. `Projects/FXArena/STATUS.md`
2. `RESEARCH_REGISTER.md`
3. Linked laboratory reports, specifications, decisions, and release manifest

Memory of prior chats is not a canonical source when repository evidence exists.

## Significant-laboratory update rule

After every significant FXArena laboratory or validation milestone, the research assistant must immediately update GitHub where applicable:

- `Projects/FXArena/STATUS.md`
- `Projects/FXArena/BACKLOG.md`
- `RESEARCH_REGISTER.md`
- laboratory `SPEC` / `REPORT`
- result lineage and manifest
- `CHANGELOG.md` or release checkpoint for major milestones

A significant laboratory includes a completed experiment, changed verdict, changed canonical configuration, discovered leakage or execution issue, new validated/rejected hypothesis, or any result that changes the research direction.

## Data-access and storage rule

Files that the research assistant must read directly must be stored as ordinary repository files under stable paths, not only as GitHub Release assets.

Recommended locations:

- specifications: `Projects/FXArena/Specs/`
- laboratory code: `Projects/FXArena/Labs/<LabName>/`
- reusable tooling: `Projects/FXArena/Tooling/`
- reports: `Projects/FXArena/Reports/`
- manifests and checksums: `Projects/FXArena/Manifests/`
- lightweight fixtures and small datasets: `Projects/FXArena/Fixtures/`
- external-data indexes and exact filenames: `Projects/FXArena/DataIndex/`

Large M1, CSV, Parquet, tick-history, or other binary datasets may remain outside the repository. For those files, use one of these access channels:

1. Google Drive with a stable linked file and a matching entry in `DataIndex/`;
2. direct upload into the active ChatGPT conversation;
3. another explicitly accessible storage connector.

GitHub Release assets are archival checkpoints, but must not be assumed directly readable by the assistant. Every release containing external or large assets must also include a repository manifest listing:

- exact filename;
- SHA256;
- row count or size where applicable;
- purpose;
- producing laboratory;
- consuming laboratory;
- storage location or Drive reference.

Do not start a laboratory until all required runtime inputs are confirmed accessible.

## Conflict rule

When documents disagree, do not silently reconcile them from memory. Identify the conflict, use the latest validated evidence and governance precedence, and update the canonical files so the contradiction is removed.

## Permanent instruction

> Відтепер перед відповідями щодо стану FXArena я спочатку звірятимуся з `STATUS.md` і `RESEARCH_REGISTER.md`, а після значущих лабораторій одразу оновлюватиму GitHub.

> Файли, які асистент має читати напряму, зберігаються у звичайних шляхах репозиторію. Великі M1/CSV/Parquet передаються через Google Drive або окремим завантаженням у чат, з обов'язковим записом у `DataIndex/` і маніфесті.