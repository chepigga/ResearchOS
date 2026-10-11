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
- **Status:** COMPLETED
- **Dependencies:** initialized `main`
- **Goal:** isolate active research from stable governance
- **Done when:** `research` exists from the verified bootstrap commit
- **Risks:** branch divergence before the first import
- **Required files:** none
- **Next action:** use feature/research branches for large new laboratories

## ROS-003 — Complete XAU_Pool candidate evidence

- **Project:** XAU_Pool
- **Priority:** P0
- **Status:** IN_PROGRESS
- **Dependencies:** raw data and original runtime outputs
- **Goal:** turn LAB_001 from a report-backed candidate into an independently reproducible checkpoint
- **Done when:** raw-release hash, selected trade-level outputs, logs and environment lock complete the now-saved pool/baseline/permutation/model artifacts and portable path update
- **Risks:** missing source artifacts; post-hoc reconstruction; data drift
- **Required files:** raw-data SHA256, selected trades, logs and dependency lock
- **Next action:** complete remaining evidence, then create LAB_002 spec

## ROS-004 — CrowdFade BTC aggressive flow ignition vs exhaustion

- **Project:** CrowdFade BTCUSDT Futures
- **Priority:** P0
- **Status:** BLOCKED — acquire >=3 months native Binance aggTrades (target 6 months)
- **Dependencies:** auditable Binance archive manifests, warmup, LAB204 detector parity, causal features
- **Goal:** distinguish genuine flow ignition continuation from exhaustion/stall at event close, then test realizable net EV and residual R:R >=1.5
- **Done when:** clean chronological train/holdout, independent event-level labels, detailed trade replay with costs, coverage and risk metrics; L/S/OI ablation separate
- **Risks:** seven-day overfitting, overlapping events, lookahead, 15m-close TP/SL misinterpretation, simulated liquidity and mismatched broker costs
- **Recovery & full plan:** [CrowdFade LAB205 backlog](Projects/CrowdFade/BACKLOG_LAB205_IGNITION_EXHAUSTION_20261011.md)
- **Next action:** download/verify 2026-05-01..08-07 with 7d warmup, then Feb–Aug, reproduce 79 LAB204 events before labeling
