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

## XAU-BH-OOS-001v2 — Validate frozen BH_SWEEP OOS

- **Project:** Grok XAU
- **Priority:** P0
- **Status:** PREREGISTERED / BLOCKED_DATA_AND_ENGINE
- **Dependencies:** exact frozen MorrisCandle V2 oracle/config; original in-sample fixture; same-feed XAUUSD M15 through 2026-07-23
- **Goal:** reproduce the N=88, B52/S36, EV=+0.276R control and then validate BH_SWEEP on 2026-05-01..2026-07-23 without tuning
- **Done when:** Step 0 passes the preregistered drift gate, OOS trades and monthly artifacts are stored, and PASS/FAIL/INCONCLUSIVE is recorded
- **Risks:** pipeline drift; feed substitution; unavailable frozen engine; insufficient OOS trades; post-hoc near-miss reinterpretation
- **Required files:** MorrisCandle V2 package, control fixture, `XAUUSD_M15_2024-12-01_2026-07-23.csv`
- **Next action:** revoke the exposed xAI key, run the same-feed M15 exporter, and recover the exact frozen oracle package before Step 0
