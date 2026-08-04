# ADR-001 — Separate XAU_Pool from AK47

- **Status:** ACCEPTED
- **Date:** 2026-08-04
- **Project:** XAU_Pool

## Context

The supplied package stored `XAU_POOL_SELECTION_LAB_001` under `Projects/AK47/`, while the user explicitly requested a new project named `XAU_Pool`.

## Decision

Import the XAU pool-selection specification, report and reproduction code into `Projects/XAU_Pool/`. Do not duplicate or mix the two unrelated FXArena documents from the same package into this project.

## Evidence

The laboratory has its own hypothesis, candidate universe, model, validation protocol, status and next steps. Its report identifies the result as a research candidate rather than an AK47 EA version.

## Alternatives

- Keep all files under AK47.
- Duplicate files under both projects.
- Import the entire mixed archive unchanged.

## Consequences

- XAU_Pool receives an independent status, backlog, lineage and release path.
- Original file contents and names are retained.
- Cross-project transfer from FXArena remains cited as precedent, not inherited canonical state.

## Validation required

Confirm independent reproduction and portfolio/execution validation before any canonical promotion.

## Supersedes

The directory placement proposed by the package README for these XAU_POOL files only.
