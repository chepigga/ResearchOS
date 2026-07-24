# FXArena Backlog

## FXA-REV-CONF-001 — REV_Confirmation v001

- **Priority:** P0
- **Status:** COMPLETED / F11 / CLOSED
- **Scenario 2023:** (a), out-of-dataset control under documented artifact chronology
- **Engine:** `FXArena LevelBattleEngine v003 EVENT_STREAM`; 1,196,467 events; 106,079 acceptance confirmations
- **Production causal funnel:** `ACCEPTANCE_CONFIRMED` plus M1-reconstructed `max_penetration_seen@D3 <= 1.0 ATR`
- **RC1 2023:** N=2109; EV -0.287213R; PF 0.6570; total -605.733R; gross DD 184R; net DD 611.473R
- **Stability:** 12/12 negative months; both half-years negative
- **Gates:** only N passed; EV, PF, negative-month and half-year gates failed
- **Verdict:** `F11_SHALLOW_ACCEPTANCE_REV_FALSIFIED`
- **Frozen stop:** RC2-RC6 not executed; REV EA/module work prohibited
- **Forensic diagnosis:** historical strong candidate used final-episode `max_penetration_atr`; 23,467 episodes shallow at D3 later deepened beyond 1 ATR, so the selector consumed post-D3 information
- **Original reference-period causal diagnostic:** N=5830; EV -0.271R; PF 0.677; 29/30 negative months
- **Result:** `Releases/v1.2/REV_Confirmation_v001/`
- **Reopen:** prohibited for this funnel; any future REV hypothesis must use genuinely new causal information and a new frozen specification

## FXA-PC5R-001 — Final paired cost adjudication

- **Priority:** P0
- **Status:** COMPLETED / FINAL CLOSED / P4c NOT RE-QUALIFIED
- **Pair control:** PASS; 3515/3515, zero P0/P4c exit mismatches at 6pt/x1.0
- **Grid:** commission 5/6/7.5/10pt × spread x1/x1.5 × BE slip 0/0.05R
- **Central 7.5/x1.5/0.05:** P0 +1779.79R; P4c +1965.82R; ratio 1.1045x; DD 14.436R vs 10.820R
- **Gates:** PR1 PASS; PR2 PASS; PR4 PASS at 99.98%; PR5 FAIL
- **Fact 5/x1/0.05:** P0 +1931.35R; P4c +2115.64R; ratio 1.0954x; DD PASS
- **Failure margin:** 9.54% advantage versus frozen 10% requirement; shortfall 0.46 percentage points
- **Extreme diagnostic 10/x1.5/0.05:** ratio 1.1110x; DD PASS
- **Verdict:** `P4C_CLOSED_FINAL__DEPLOY_EXIT_P0`
- **Third retrial:** permanently prohibited
- **Result:** `Releases/v1.2/PC5r_Resolution_v001/`

## FXA-P4C-CAUSAL — P4c Causal Exit v001

- **Status:** COMPLETED / RESEARCH FIXTURE ONLY
- **Base TRAILING:** +2127.402776R; gross DD 10.618161R
- **Causal correction:** archived P4b lookahead cost = 145.708807R on MONTHLY
- **Deploy status:** superseded by final PC5-r FAIL; no forward A/B admission
- **Prohibited:** tune activation, TP, BE, cost law or reopen PC5 on these data

## FXA-TBFLAG-REPLAY-001 — Flag-Replay v001.2

- **Status:** COMPLETED
- **Generator:** PASS 3535/3535, zero mismatches
- **Universe:** 291659 episode flags; all 622 trailing-only episodes resolved
- **Role:** preserved research generator; archived P4b remains non-causal for deploy

## FXA-CLOSURE-0011 — Monthly vs trailing canonicalization

- **Status:** COMPLETED / LIVE P0 PIN CREATED
- **MONTHLY:** N=3535, +1848.874807R, gross DD 14.415969R
- **TRAILING:** N=3515, +1889.613320R on archived 6pt basis, gross DD 14.415969R
- **Rule:** live comparisons only against TRAILING; research comparisons only against MONTHLY

## FXA-EXIT-LINE — Exit improvement closure

- **Status:** CLOSED PERMANENTLY ON CURRENT DATA
- **Deploy exit:** P0 TP2/TO120 on GEO*-TRAILING
- **P4b:** stronger but retrospective/lookahead; research-only
- **P4c:** causal and economically strong, but final paired fact-cost gate PR5 failed
- **Reopen:** prohibited through PC5; any genuinely new exit family requires new data and a new research program, not a third PC5 trial

## FXA-REV-LINE — REV leg research closure

- **Status:** CLOSED F11 FOR SHALLOW-ACCEPTANCE FUNNEL
- **Deploy:** no REV leg and no magic 777003 module
- **Cause:** causal D3 penetration selector is negative in 2023 and 2024-2026H1; old positive result used future episode penetration
- **Reopen:** only a genuinely different causal REV mechanism under a new preregistered program

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

## FXA-AUGUST-EXAM — Live benchmark execution

- **Priority:** P0
- **Status:** READY WITH P0 BASELINE / CONT ONLY
- **Reference:** `trades_GEOstar_TRAILING_PINNED.csv.gz`
- **Exit policy:** P0 final; P4b/P4c excluded
- **REV:** excluded under F11
- **Measured cost basis:** 5pt RT; compare paired live results against P0 only

## FXA-DATA-001 — Execution provenance

- **Status:** ACTIVE
- **Immediate need:** preserve exact M1/tick provenance, commission records and spread maps for August exam replication
