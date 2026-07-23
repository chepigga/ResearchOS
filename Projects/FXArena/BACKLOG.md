# FXArena Backlog

## FXA-EXIT-003L — Exit Tournament v003-lite core closure

- **Priority:** P0
- **Status:** HOLD / TWO EXECUTION INPUTS MISSING
- **Primary:** `tb_flag=true -> P4`, `tb_flag=false -> P5`
- **Completed:** Gate0; RH1-RH3; RH4 economics diagnostic; RH5 permutation-200; RH8 dedup; commission and BE-slip components of RH7
- **Result:** P4b +2256.51R, gross DD 12.436807R; RH5 p=0.00498
- **Blocker RH6:** exact original release sampler/seeds and frozen absolute-versus-paired DD interpretation
- **Blocker RH7:** raw M1 spread path for x1.25/x1.5/x2.0 replay
- **Prohibited:** tuning P4b, freezing Entry Lab, or freezing Exit v004 before closure
- **Done when:** RH6 and exact RH7 are committed with a final PASS/FAIL/F8 verdict

## FXA-EXIT-P5 — P5 BE@60 secondary verdict

- **Priority:** P0
- **Status:** FALSIFIED BY RH7
- **Finding:** at commission 9 points + 0.05R slip on 1324 changed exits, total falls to +1792.89R before any spread increase
- **Verdict:** cannot become v003-lite winner
- **Note:** remains a frozen component inside P4b on the non-TB branch, where 1077 exits change

## FXA-EXIT-002A — v002.1 DD Convention Audit Replay

- **Priority:** P0
- **Status:** PARTIALLY COMPLETED / RH6 SOURCE DEBT
- **Gate 0:** PASS; P0 gross MaxDD 14.415969R and net MaxDD 15.827253R
- **Corrected P0-P7 table:** committed
- **Remaining:** exact original-sampler gross RH6 for the historical P0-P7 verdict catalogue

## FXA-EXIT-002 — Exit Policy Tournament v002

- **Priority:** P0
- **Status:** COMPLETED OUTPUT / ORIGINAL VERDICT SUPERSEDED
- **Defect:** net DD was compared with the frozen gross-DD threshold
- **Registry debt:** full corrected P0-P7 economic table is preserved in v003-lite artifacts

## FXA-EXIT-002B — P4 TB deep dive / P4b Research v001

- **Priority:** P0
- **Status:** COMPLETED / POST-HOC CANDIDATE
- **Finding:** P4 earns on TB continuation; P5 protects the non-TB branch
- **Observed result:** +2256.51R; EV +0.6383R; gross MaxDD 12.436807R
- **Verdict:** strong confirmation, but NO-GO for EA until RH6/RH7 closure

## FXA-DEPLOY-EXIT — Deferred deploy tests

- **Priority:** P1 / PRE-EA
- **Status:** DEFERRED
- **R1:** independent Dukascopy feed
- **R2:** forward offline replay on live ContPrimary entries
- **Activation:** only after v003-lite core PASS

## FXA-DATA-001 — Verify external release assets

- **Priority:** P0
- **Status:** ACTIVE
- **Immediate need:** locate exact bootstrap implementation/seeds and raw M1 spread path used by Release v1.1
