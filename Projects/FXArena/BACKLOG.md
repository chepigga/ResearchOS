# FXArena Backlog

## P0 — Preserve Release v.1.1 as canonical checkpoint

- **Status:** COMPLETED
- **Result:** release asset uploaded; manifest and validation artifacts preserved
- **Canonical geometry:** GEO* = `MICRO30 + TP2.0 + TO120`
- **Rejected candidate:** GEO** = `MICRO30 + TP2.0 + TO60` after GS7 FAIL
- **Rule:** no re-optimization of TP2/60 on the same data

## P1 — Exit Policy Tournament v002

- **Status:** PREREGISTERED / FROZEN BEFORE RUN
- **Priority:** P0
- **Supersedes:** Exit Policy Tournament v001, which was never run and must be ignored or removed if found
- **Spec:** [ExitPolicyTournament_TZ_v002.md](Specs/ExitPolicyTournament_TZ_v002.md)
- **Locked baseline:** Release `v.1.1`; GEO* `MICRO30 + TP2.0 + TO120`; N=3535; Total=+1848.87R; MaxDD=14.416R
- **Question:** compare adaptive regression-head exits, TB rule-based exits and simple global BE/partial exits on identical pinned entries
- **Policies:** P0–P7 exactly as frozen in the spec
- **Primary gates:** RH1–RH6 plus the preregistered Occam rule
- **Run discipline:** P0 control first; one tournament run; no tuning or overrides
- **Required inputs:** `v.1.1 COMPLETE.zip`, `wf_toolkit`, M1 tradingticks data, full universe count 291659, pinned GEO* fixture
- **Required outputs:** target cache, head weights, P1–P7 trades, GS5, GS6, >=5000 paired block bootstrap rows, report, manifest, Release v1.2
- **Runtime state:** SPEC COMMITTED; execution pending verified access to the release asset and M1 inputs in the active runtime

## P2 — Forward / Exam Governance

- **Status:** IN_PROGRESS
- **Scope:** ContPrimary v1.20 / C2 demo-forward monitoring
- **Isolation rule:** Exit Policy Tournament v002 must not change forward model, weights, thresholds, execution or logs
- **Rules:** no changes before the declared exam; preserve execution drag and trade logs

## Deferred until tournament verdict

### Execution Entry Lab

- **Status:** PLANNED
- **Goal:** market vs limit vs confirmation vs retracement on the fixed GEO* universe
- **Metric:** realized EV delta versus D3+60s market entry including fill probability

## Frozen / Rejected

- GEO** TP2/60 as canonical replacement — REJECTED after GS7
- Flat TP8/TP12 on GEO* — REJECTED
- H1 stop — REJECTED
- timeout >=360 or no-timeout variants — REJECTED
- repeated global timeout search on the same sample — PROHIBITED
- Exit Policy Tournament v001 — SUPERSEDED / NEVER RUN
- TP >3.0 or TO >120 inside v002 — OUT OF SCOPE / PROHIBITED
