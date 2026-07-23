# Master Backlog

## ROS-001 — Import FXArena Research v1.2

- **Project:** FXArena
- **Priority:** P0
- **Status:** BLOCKED
- **Dependencies:** source checkpoint and manifest
- **Goal:** import the existing FXArena research state without inventing or silently altering artifacts
- **Done when:** manifest, hashes, code, specs, reports, primary results, decisions, backlog, lessons, and register entries are verified and committed
- **Risks:** missing inputs; mixed universes; stale or conflicting versions; absent lineage
- **Required files:** FXArena Research v1.2 checkpoint or its complete constituent files
- **Next action:** obtain the checkpoint and run the import checklist

## ROS-002 — Establish research branch

- **Project:** ResearchOS
- **Priority:** P1
- **Status:** PLANNED
- **Dependencies:** initialized `main`
- **Goal:** isolate active research from stable governance
- **Done when:** `research` exists from the verified bootstrap commit
- **Risks:** branch divergence before the first import
- **Required files:** none
- **Next action:** create `research` after bootstrap verification
