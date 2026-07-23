# FXArena Backlog

## FXA-EXIT-002A — v002.1 DD Convention Audit Replay

- **Priority:** P0
- **Status:** READY / BLOCKING
- **Finding:** pinned GEO* MaxDD 14.416R is gross DD; archived v002 used net DD 15.827R
- **Gate 0:** reproduce P0 N, IDs, chronology, outcomes, exits, Total net and gross MaxDD 14.415969R
- **Required:** recompute RH2 and RH6(i) with gross DD using the original sampler and frozen seeds
- **Diagnostics:** always report both gross and net MaxDD
- **Done when:** exact corrected P0–P7 verdict table and hashes are committed

## FXA-EXIT-003 — P4b frozen confirmation tournament

- **Priority:** P0
- **Status:** DRAFT / BLOCKED BY FXA-EXIT-002A AND INCOMPLETE REVIEW ADDITIONS
- **Primary candidate:** `tb_flag=true -> P4`, `tb_flag=false -> P5`
- **Constraint:** one candidate; no threshold, session, direction, symbol or parameter tuning
- **Required:** dual DD reporting, original RH gates, dedup/cluster sanity, +0.025R/+0.05R/+0.10R cost shocks, untouched replication
- **Kill rule:** disable P5 fallback if realized incremental execution drag exceeds +0.10R per modified exit

## FXA-EXIT-002 — Exit Policy Tournament v002

- **Priority:** P0
- **Status:** COMPLETED OUTPUT / VERDICT INVALIDATED
- **P0 trade parity:** 3535/3535; exact exits and gross outcomes
- **Defect:** net DD compared with frozen gross-DD threshold
- **Provisional corrected winner:** P5, pending exact gross RH6
- **Full negative-result catalogue:** P1–P3 adaptive heads and P6/P7 simple alternatives retained

## FXA-EXIT-002B — P4 TB deep dive / P4b Research v001

- **Priority:** P0
- **Status:** COMPLETED / POST-HOC CANDIDATE
- **Finding:** P4 earns on TB continuation; non-TB branch creates the main DD; P5 protects that branch
- **Observed result:** +2256.51R; EV +0.6383R; gross MaxDD 12.436807R; net MaxDD 13.283629R
- **Verdict:** exploratory GO for v003 only; NO-GO for EA/production

## FXA-DATA-001 — Verify external release assets

- **Priority:** P0
- **Status:** READY
- **Goal:** match large tick/bar/result assets against manifest hashes and source lineage

## FXA-VALIDATE-002 — Validate TrendBirth and MarketGeometry

- **Priority:** P1
- **Status:** PLANNED

## FXA-ARCH-001 — Operationalize FXArena OS layers

- **Priority:** P1
- **Status:** PLANNED
