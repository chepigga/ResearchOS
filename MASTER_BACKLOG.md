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

## XAU-BH-OOS-002 — Validate frozen BH_SWEEP OOS

- **Project:** Grok XAU
- **Priority:** P0
- **Status:** VALIDATED / PASS — DEMO ONLY
- **Result:** Step 0 N=88 B52/S36; OOS N=14, EV_net=+0.235714R, sum +3.300R
- **Next action:** one controlled demo forward month at frozen 0.30% risk; live prohibited

## XAU-FT-DEEP-001 — Validate FT core over 42 months

- **Project:** Grok XAU
- **Priority:** P0
- **Status:** INCONCLUSIVE / PARTIAL REGIME SIGNAL / FULL DATA REQUIRED
- **Dependencies:** full same-feed M5 2022-06..2026-07; tester 156-1 entry-time fixture
- **Partial input:** exactly 100,000 rows, actual coverage 2025-02-19..2026-07-23; truncated despite filename
- **Partial diagnostic:** warmup-safe N=27, EV_net=+2.160244R; top-three months 93.31%; zero-entry months 4/8
- **Step 0:** NYBUY/LONBUY count gate PASS; required >=80% time-overlap BLOCKED
- **Verdict:** formal GO/REGIME/NO-GO not open because depth<24 months and N<90
- **Next action:** rerun chunked exporter v002 and supply `AK47_ea_dryrun_signals.csv`
