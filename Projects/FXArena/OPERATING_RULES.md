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

## Conflict rule

When documents disagree, do not silently reconcile them from memory. Identify the conflict, use the latest validated evidence and governance precedence, and update the canonical files so the contradiction is removed.

## Permanent instruction

> Відтепер перед відповідями щодо стану FXArena я спочатку звірятимуся з `STATUS.md` і `RESEARCH_REGISTER.md`, а після значущих лабораторій одразу оновлюватиму GitHub.
