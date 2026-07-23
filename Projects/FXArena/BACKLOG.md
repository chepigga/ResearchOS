# FXArena Backlog

## FXA-SELECT-001 — Selection & Sizing Lab v001

- **Priority:** P0
- **Status:** COMPLETED / PART B CONTROL STOP
- **Frozen input:** GEO* PINNED N=3535; P0 exits; full v1.1 universe and p_win
- **Control:** PASS; total +1848.874807R; gross MaxDD 14.415969R
- **Part A:** FAIL SA2 and SA5 despite +75.86R total improvement and monotonic p_win tercile EV
- **Part B:** STOP; trailing q0.96/90d did not reproduce PINNED
- **Composition:** NOT RUN
- **Promotion:** none
- **Artifacts:** report, sampler code, seeds, 200 permutation rows, 5000 paired-bootstrap rows, candidate trades and SHA256 manifest
- **Result:** `Releases/v1.2/SelectionSizing_v001/`

## FXA-SELECT-002 — Resolve threshold convention

- **Priority:** P0
- **Status:** DECISION REQUIRED BEFORE NEW LAB
- **Conflict:** historical PINNED is reproduced by monthly top-4%; frozen v001 requested trailing q0.96/90d
- **Allowed paths:** preregister monthly top-{3,4,5,6}% grid with 4% exact control; or explicitly create a new trailing-90d baseline and comparison universe
- **Prohibited:** treating the v001 top-5% diagnostic cell as a winner; changing the v001 control after seeing results
- **Done when:** a new frozen spec names one convention, reproduces its control signal-by-signal, and defines paired gates before execution

## FXA-SIZING-002 — Sizing risk-shape research

- **Priority:** P2 / NEW INFORMATION REQUIRED
- **Status:** CLOSED FOR CURRENT 0.7/1.0/1.3 POLICY
- **Finding:** p_win terciles are economically monotonic, but fixed weights increase gross-DD tail
- **Reopen only if:** a genuinely new preregistered risk-shape mechanism targets correlation/cluster risk rather than tuning the three weights on the same sample

## FXA-EXIT-003L — Exit Tournament v003-lite core closure

- **Priority:** P0
- **Status:** HOLD / TWO EXECUTION INPUTS MISSING
- **Primary:** `tb_flag=true -> P4`, `tb_flag=false -> P5`
- **Completed:** Gate0; RH1-RH3; RH4 economics diagnostic; RH5 permutation-200; RH8 dedup; commission and BE-slip components of RH7
- **Result:** P4b +2256.51R, gross DD 12.436807R; RH5 p=0.00498
- **Blocker RH6:** exact formal paired replay under Registry v3 sampler law
- **Blocker RH7:** raw M1 spread path for x1.25/x1.5/x2.0 replay
- **Prohibited:** tuning P4b or promoting it to EA before closure
- **Done when:** RH6 and exact RH7 are committed with a final PASS/FAIL/F8 verdict

## FXA-EXIT-P5 — P5 BE@60 secondary verdict

- **Priority:** P0
- **Status:** FALSIFIED BY RH7
- **Finding:** at commission 9 points + 0.05R slip on 1324 changed exits, total falls to +1792.89R before any spread increase
- **Verdict:** cannot become v003-lite winner
- **Note:** remains a frozen component inside P4b on the non-TB branch, where 1077 exits change

## FXA-EXIT-002A — v002.1 DD Convention Audit Replay

- **Priority:** P0
- **Status:** PARTIALLY COMPLETED / HISTORICAL RH6 SOURCE DEBT
- **Gate 0:** PASS; P0 gross MaxDD 14.415969R and net MaxDD 15.827253R
- **Corrected P0-P7 table:** committed

## FXA-EXIT-002 — Exit Policy Tournament v002

- **Priority:** P0
- **Status:** COMPLETED OUTPUT / ORIGINAL VERDICT SUPERSEDED
- **Defect:** net DD was compared with the frozen gross-DD threshold

## FXA-EXIT-002B — P4 TB deep dive / P4b Research v001

- **Priority:** P0
- **Status:** COMPLETED / POST-HOC CANDIDATE
- **Finding:** P4 earns on TB continuation; P5 protects the non-TB branch
- **Observed result:** +2256.51R; EV +0.6383R; gross MaxDD 12.436807R

## FXA-DEPLOY-EXIT — Deferred deploy tests

- **Priority:** P1 / PRE-EA
- **Status:** DEFERRED
- **R1:** independent Dukascopy feed
- **R2:** forward offline replay on live ContPrimary entries

## FXA-DATA-001 — Verify external release assets

- **Priority:** P0
- **Status:** ACTIVE
- **Immediate needs:** raw M1 spread path and deploy-replay inputs
