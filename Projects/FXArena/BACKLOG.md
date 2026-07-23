# FXArena Backlog

## FXA-ENTRY-001 — Entry Lab v001

- **Priority:** P0
- **Status:** COMPLETED / CLOSED F10
- **Frozen input:** GEO* PINNED 3535 signals, P4b exits, exact M1 spread, Levels/Rounds
- **Gate 0:** PASS; entry/risk exact, 0 exit-time differences, total difference -0.00000192R
- **Winner:** E0 `market @ D3+60s`
- **Finding:** every E1–E6 candidate failed EL1, EL2 and paired EL4
- **Pure limits:** E1/E2 fill only 34.23%/31.63% and miss 64.05%/66.95% of TB
- **Best failed arm:** E3 +1847.72R versus E0 +2256.51R; gross DD 16.699R
- **Hybrids:** E4 +1551.17R; E5 +1829.93R; E6 +1648.59R
- **Bootstrap:** block 20, 5000, seed 2026072404; P(total>E0)=0 for all candidates
- **Verdict:** Entry layer CLOSED; no v1.30 entry composition
- **Artifacts:** report, E0 parity audit, arm/gate tables, all trades, missed analysis, bootstrap CSV, sampler code, source/output manifests
- **Result:** `Releases/v1.2/EntryLab_v001/`
- **Reopen only if:** genuinely new causal entry information appears; do not create another TTL/offset/hour grid

## FXA-SESSION-001 — Session & Time-of-Day Lab v001

- **Priority:** P0
- **Status:** COMPLETED / CLOSED F9
- **Control:** PASS; full S1–S4 diagnostics on P0/P4b
- **Closest signal:** S3 NY overlap = 42.48% top-5 DD negative-loss share at 25.205% trade share
- **Transition:** FAIL frozen T1 and T2; Stage 2 NOT RUN
- **Verdict:** no session veto; hour-level filters prohibited
- **Result:** `Releases/v1.2/SessionTiming_v001/`

## FXA-SELECT-001 — Selection & Sizing Lab v001

- **Priority:** P0
- **Status:** COMPLETED / PART B CONTROL STOP
- **Part A:** FAIL SA2/SA5 despite monotonic p_win tercile EV
- **Part B:** STOP; trailing q0.96/90d did not reproduce PINNED
- **Promotion:** none
- **Result:** `Releases/v1.2/SelectionSizing_v001/`

## FXA-SELECT-002 — Resolve threshold convention

- **Priority:** P0
- **Status:** DECISION REQUIRED BEFORE NEW LAB
- **Conflict:** historical PINNED is reproduced by monthly top-4%; frozen v001 requested trailing q0.96/90d
- **Allowed paths:** preregister monthly top-{3,4,5,6}% with 4% exact control, or explicitly pin a new trailing-90d baseline
- **Prohibited:** treating the diagnostic top-5% cell as a winner

## FXA-SIZING-002 — Sizing risk-shape research

- **Priority:** P2 / NEW INFORMATION REQUIRED
- **Status:** CLOSED FOR CURRENT 0.7/1.0/1.3 POLICY
- **Finding:** p_win terciles are monotonic, but fixed weights increase gross-DD tail

## FXA-EXIT-003L — Exit Tournament v003-lite core closure

- **Priority:** P0
- **Status:** HOLD / DEPLOY INPUTS MISSING
- **Primary:** `tb_flag=true -> P4`, `tb_flag=false -> P5`
- **Result:** P4b +2256.51R, gross DD 12.436807R; RH5 p=0.00498
- **Completed:** Gate0, RH1-RH3, RH4 diagnostic, RH5, RH8, commission/BE-slip RH7 legs
- **Blocker RH6:** formal paired replay under Registry v3 sampler law
- **Blocker RH7:** exact raw-spread execution replay
- **Prohibited:** promote P4b to EA before closure

## FXA-EXIT-P5 — P5 BE@60 secondary verdict

- **Priority:** P0
- **Status:** FALSIFIED BY RH7
- **Finding:** commission 9pt + 0.05R slip reduces total to +1792.89R before spread increase

## FXA-EXIT-002A — Historical DD convention debt

- **Priority:** P1
- **Status:** PARTIALLY COMPLETED
- **Gate 0:** P0 gross DD 14.415969R; net DD 15.827253R

## FXA-DEPLOY-EXIT — Deferred deploy tests

- **Priority:** P0 / PRE-EA
- **Status:** DEFERRED
- **Tasks:** exact tick ExecutionReplay, RH6 formal, RH7 spread replay, R1 Dukascopy, R2 forward A/B

## FXA-DATA-001 — Verify external release assets

- **Priority:** P0
- **Status:** ACTIVE
- **Immediate needs:** deploy-replay inputs and exact P4b spread-path execution convention
