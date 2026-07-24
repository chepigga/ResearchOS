# FXArena Backlog

## FXA-CLOSURE-0011 — Monthly vs trailing canonicalization

- **Priority:** P0
- **Status:** COMPLETED / PARTIAL PASS / P4b TRANSFER STOP
- **Control A:** monthly exact, N=3535, +1848.874807R, gross DD 14.415969R
- **Control B:** trailing q0.96/90d exact, N=3515, +1889.613320R, gross DD 14.415969R
- **Official live pin:** `trades_GEOstar_TRAILING_PINNED.csv.gz`
- **Official research pin:** existing GEO*-MONTHLY fixture unchanged
- **Intersection:** 2893; monthly-only 642; trailing-only 622
- **Rule:** live comparisons only against TRAILING; research comparisons only against MONTHLY
- **P4b result:** C1-C4 NOT EXECUTED; 622 trailing-only episodes lack frozen causal `tb_flag`
- **P4b trailing pin:** NOT CREATED
- **Result:** `Releases/v1.2/Closure_v001_1/`

## FXA-TBFLAG-REPLAY-001 — Full-universe causal P4 flag replay

- **Priority:** P0 / BLOCKS LIVE P4b
- **Status:** NEW FROZEN SPEC REQUIRED
- **Goal:** reproduce the original P4 `EFFICIENCY_5 / BB_EXPANSION / RANGE_EXPANSION_15` 30-minute causal flag signal-by-signal on monthly 3535, then emit flags for the full selector universe including all 622 trailing-only episodes
- **Control:** monthly `tb_flag` must equal the archived P4 fixture exactly; any mismatch = STOP
- **Prohibited:** infer flags from MFE/outcomes, assign missing rows non-TB, fit a new classifier, or change the P4 rule
- **Done when:** exact full-universe flag fixture exists and Closure C1-C4 can be rerun without assumptions

## FXA-ENTRY-001 — Entry Lab v001

- **Priority:** P0
- **Status:** COMPLETED / CLOSED F10
- **Winner:** E0 `market @ D3+60s`
- **Finding:** every E1-E6 candidate failed EL1, EL2 and paired EL4
- **Result:** `Releases/v1.2/EntryLab_v001/`
- **Reopen only if:** genuinely new causal entry information appears

## FXA-SESSION-001 — Session & Time-of-Day Lab v001

- **Priority:** P0
- **Status:** COMPLETED / CLOSED F9
- **Verdict:** no session veto; hour-level filters prohibited
- **Result:** `Releases/v1.2/SessionTiming_v001/`

## FXA-SELECT-001 — Selection & Sizing Lab v001

- **Priority:** P0
- **Status:** COMPLETED
- **Part A:** FAIL SA2/SA5 despite monotonic p_win tercile EV
- **Part B:** historical control mismatch resolved by Closure v001.1 through two separate canonical baselines
- **Promotion:** none
- **Result:** `Releases/v1.2/SelectionSizing_v001/`

## FXA-SIZING-002 — Sizing risk-shape research

- **Priority:** P2 / NEW INFORMATION REQUIRED
- **Status:** CLOSED FOR CURRENT 0.7/1.0/1.3 POLICY

## FXA-EXIT-003L — Exit Tournament v003-lite core closure

- **Priority:** P0
- **Status:** MONTHLY CONFIRMED / LIVE TRANSFER BLOCKED
- **Primary:** `tb_flag=true -> P4`, `tb_flag=false -> P5`
- **Monthly result:** P4b +2256.51R, gross DD 12.436807R
- **Live blocker:** no frozen P4/TB flag for 622 trailing-only episodes
- **Prohibited:** promote P4b to EA before trailing C1-C4 and exact execution closure

## FXA-EXIT-P5 — P5 BE@60 secondary verdict

- **Priority:** P0
- **Status:** FALSIFIED BY RH7

## FXA-DEPLOY-EXIT — Deferred deploy tests

- **Priority:** P0 / PRE-EA
- **Status:** BLOCKED BY TB-FLAG REPLAY, THEN EXECUTION REPLAY
- **Tasks:** Closure C1-C4 on trailing, exact tick ExecutionReplay, RH7 spread replay, R1 Dukascopy, R2 forward A/B

## FXA-DATA-001 — Verify external release assets

- **Priority:** P0
- **Status:** ACTIVE
- **Immediate needs:** original full-universe P4/TB flag generator and deploy-replay inputs