# FXArena Backlog

## FXA-EXIT-003 — P4b frozen confirmation tournament

- **Priority:** P0
- **Status:** READY
- **Primary candidate:** `tb_flag=true -> P4`, `tb_flag=false -> P5`
- **Constraint:** one registered candidate; no threshold, session, direction, symbol or parameter tuning
- **Required gates:** exact P0 parity; original RH1-RH6 sampler/seeds; dedup/cluster sanity; +0.025R/+0.05R/+0.10R cost shocks; untouched replication period or broker feed
- **Kill rule:** disable P5 fallback if realized incremental execution drag exceeds +0.10R per modified exit
- **Done when:** formal frozen verdict is produced and all artifacts are SHA256-indexed

## FXA-EXIT-002 — Exit Policy Tournament v002

- **Priority:** P0
- **Status:** COMPLETED / FORMAL FAIL — NO WINNER
- **P0 parity:** 3535/3535; exact exit parity; gross parity at 1e-6
- **Best economics:** P4 +2134.36R, EV +0.6038R, zero negative months
- **Failure:** P4 failed RH2 and RH6; all P1-P7 policies failed at least one frozen gate
- **Result checkpoint:** `Releases/v1.2/ExitPolicyTournament_v002/`

## FXA-EXIT-002B — P4 TB deep dive / P4b Research v001

- **Priority:** P0
- **Status:** COMPLETED / CANDIDATE REGISTERED
- **Finding:** P4's main drawdown is predominantly non-TB; TB target tuning cannot directly repair RH2
- **Candidate result:** +2256.51R, EV +0.6383R, MaxDD 13.284R, PF 4.297, zero negative months
- **Verdict:** exploratory GO for v003 confirmation only; NO-GO for EA/production

## FXA-DATA-001 — Verify external release assets

- **Priority:** P0
- **Status:** READY
- **Goal:** match large tick/bar/result assets against manifest hashes and source lineage
- **Done when:** every external asset has exact filename, hash, date range, broker/source, schema and consuming laboratory

## FXA-VALIDATE-001 — Reproduce GEO* control

- **Priority:** P0
- **Status:** PARTIALLY COMPLETED
- **Result:** Exit Policy Tournament v002 reproduced the pinned P0 fixture for 3535/3535 episodes
- **Remaining:** independent reproduction from the complete external release assets and untouched feed

## FXA-VALIDATE-002 — Validate TrendBirth and MarketGeometry

- **Priority:** P1
- **Status:** PLANNED
- **Goal:** reproduce results on the full canonical GEO* universe with causal feature windows and explicit execution costs

## FXA-ARCH-001 — Operationalize FXArena OS layers

- **Priority:** P1
- **Status:** PLANNED
- **Goal:** connect Feature → Model → Entry → Execution → Risk without promoting research-only modules prematurely

## FXA-IMPORT-001 — Import Research v1.2

- **Priority:** P0
- **Status:** COMPLETED
- **Source:** `Archive_Arena.zip`
- **Result:** 26 artifacts indexed with SHA256 and classified by code/spec/report/result/model/archive role
- **Manifest:** `Archive/Imports/FXArena_v1_2/IMPORT_MANIFEST.csv`

## FXA-IMPORT-002 — Register named research lines

- **Priority:** P0
- **Status:** COMPLETED
- **Registered:** C2, GEO*, TrendBirth, MarketGeometry, OS Prototype, TimeoutSweep, BattleOutcome RiskFirst, Exit Policy Tournament v002, P4b Research v001
