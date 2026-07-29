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
- **Status:** VALIDATED / PASS
- **Control:** N=88, B52/S36, legacy EV=+0.275780R; 88/88 entry-time/direction matches; exit mismatches 0
- **OOS:** 2026-05-01..2026-07-23; N=14; EV_net=+0.235714R; Sum=+3.300R; May/June/July positive
- **Decision:** `InpBH_Enable=true` permitted on demo only; live prohibited
- **Canonical configuration:** AK47_FT v1.56 BH v1.55; EMA20; SL 0.25 ATR; TP2R; TO96; fixed cost -0.05R
- **Risks:** modest N=14; SELL leg EV=-0.05R; bar-level cost model; execution drift
- **Next action:** one complete controlled demo forward month at `InpBH_RiskPct=0.30` with full lifecycle logging
- **Links:** `Projects/Grok_XAU/STATUS.md`, `Projects/Grok_XAU/Reports/BH_OOS_002_v002_Report.md`

## XAU-BH-FWD-001 — Run BH_SWEEP demo forward

- **Project:** Grok XAU
- **Priority:** P0
- **Status:** READY
- **Dependencies:** validated OOS PASS
- **Goal:** verify frozen signal parity and real demo execution for one complete month
- **Configuration:** `InpBH_Enable=true`, `InpBH_RiskPct=0.30`, all v1.56 defaults unchanged
- **Required logging:** signal, fill, spread, slippage, rejects, SL, TP, time-stop and portfolio gates
- **Stop conditions:** missing/duplicate signals, material oracle drift, materially excessive costs, or unsafe drawdown behaviour
- **Done when:** forward report and explicit live/no-live ADR are committed
