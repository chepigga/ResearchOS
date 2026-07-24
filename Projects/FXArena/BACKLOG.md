# FXArena Backlog

## FXA-P4C-CAUSAL — P4c Causal Exit v001

- **Priority:** P0
- **Status:** COMPLETED / FAIL PC5 / NOT PROMOTED
- **Gate 0a:** P4b replay PASS, zero exit mismatches
- **Gate 0b:** TB flag parity PASS 3535/3535
- **Lookahead debt:** 193 early TP2 trades; archived P4b advantage over P4c = +145.708807R on MONTHLY
- **P4c MONTHLY:** +2110.802995R, gross DD 12.436807R
- **P4c TRAILING:** +2127.402776R, gross DD 10.618161R versus P0 +1889.613320R / 14.415969R
- **Gates:** PC1 PASS; PC2 PASS; PC3 PASS; PC4 PASS; PC5 FAIL
- **PC5 central stress:** spread x1.5 + commission 9pt + 0.05R slip -> +1903.209668R, gross DD 10.819815R
- **Primary diagnosis:** commission 9pt alone produces +2002.190324R and fails PC1; spread x1.5 alone passes
- **Pin:** `trades_P4c_TRAILING_PINNED` NOT CREATED
- **Deploy verdict:** P0 GEO*-TRAILING
- **Result:** `Releases/v1.2/P4c_Causal_v001/`
- **Prohibited:** tune 30m activation, TP2/TP3, BE60, cost gate or re-enter after TP2 on this sample

## FXA-TBFLAG-REPLAY-001 — Flag-Replay v001.2

- **Status:** COMPLETED
- **Generator:** PASS 3535/3535, zero mismatches
- **Universe:** 291659 episode flags, 57811 TB
- **Trailing:** all 3515 flags resolved; 1244 TB
- **Archived P4b:** research-only because retrospective flag use is non-causal
- **Result:** `Releases/v1.2/FlagReplay_v001_2/`

## FXA-CLOSURE-0011 — Monthly vs trailing canonicalization

- **Status:** COMPLETED / LIVE P0 PIN CREATED
- **MONTHLY:** N=3535, +1848.874807R, gross DD 14.415969R
- **TRAILING:** N=3515, +1889.613320R, gross DD 14.415969R
- **Rule:** live comparisons only against TRAILING; research comparisons only against MONTHLY

## FXA-EXIT-LINE — Exit improvement closure

- **Status:** CLOSED UNDER CURRENT FROZEN POLICIES
- **Deploy exit:** P0 TP2/TO120 on GEO*-TRAILING
- **P4b:** stronger but retrospective/lookahead; research-only
- **P4c:** causal and strong before costs, but fails PC5
- **Reopen only if:** genuinely new causal exit information or materially different verified execution economics; new frozen specification required

## FXA-ENTRY-001 — Entry Lab v001

- **Status:** COMPLETED / CLOSED F10
- **Winner:** E0 `market @ D3+60s`

## FXA-SESSION-001 — Session & Time-of-Day Lab v001

- **Status:** COMPLETED / CLOSED F9
- **Verdict:** no session veto

## FXA-SELECT-001 — Selection & Sizing Lab v001

- **Status:** COMPLETED
- **Part A:** FAIL SA2/SA5
- **Baseline distinction:** resolved through separate MONTHLY/TRAILING canonical pins

## FXA-SIZING-002 — Sizing risk-shape research

- **Status:** CLOSED FOR CURRENT 0.7/1.0/1.3 POLICY

## FXA-AUGUST-EXAM — Live benchmark execution

- **Priority:** P0
- **Status:** READY WITH P0 BASELINE
- **Reference:** `trades_GEOstar_TRAILING_PINNED.csv.gz`
- **Exit policy:** P0, not P4b/P4c
- **Rules:** live/E-exam/kill metrics compare only against GEO*-TRAILING

## FXA-DATA-001 — Verify external release assets

- **Status:** ACTIVE
- **Immediate need:** preserve exact M1/tick execution provenance for the August exam and future independent replication
