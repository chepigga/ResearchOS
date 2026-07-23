# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-24
- **Lifecycle status:** ACTIVE_RESEARCH / SESSION-TIMING v001 CLOSED F9
- **Canonical live baseline:** C2 / ContPrimary unchanged
- **Frozen research control:** GEO* `MICRO30 / TP 2.0R / timeout 120 min`
- **Canonical GEO* metrics:** N=3535; Total net=+1848.87R; EV net=+0.523020R; gross MaxDD=14.415969R
- **DD convention:** gross equity MaxDD is the gate metric; net MaxDD is diagnostic and must be labelled

## Session & Time-of-Day Lab v001

- **Control:** PASS; P0 N=3535, total +1848.874811R, gross MaxDD 14.415969R; P4b ordered episode parity exact
- **Frozen blocks:** S1 Asia 00:00–08:59; S2 London 09:00–13:59; S3 NY overlap 14:00–17:59; S4 Late NY 18:00–23:59
- **Stage 1:** completed on P0 and P4b, including yearly tables, top-5 DD attribution, October-2023 named cluster and diagnostic-only hourly curve
- **Closest candidate:** S3 NY overlap contributed 42.48% of negative loss in P4b top-5 DD episodes, but trade share was 25.205% (> frozen 25% ceiling)
- **Stability:** S3 DD overrepresentation sign was not stable in 4/4 years
- **Stage 2:** NOT RUN; no block passed T1–T3
- **Verdict:** F9 — session edge worth filtering not found
- **Promotion:** no session veto; keep all four blocks; hour-level filters prohibited
- **Result checkpoint:** `Releases/v1.2/SessionTiming_v001/`

## Selection & Sizing Lab v001

- **Control:** PASS; exact N=3535, total +1848.874807R, gross MaxDD 14.415969R and p/outcome parity
- **Part A sizing tiers:** economic signal confirmed but frozen candidate FAIL
- **Part A result:** +1924.73R, EV +0.54448R, gross MaxDD 15.185R, 0 negative months
- **Tercile diagnostic:** EV rises monotonically LOW +0.43369R -> MID +0.47725R -> HIGH +0.65763R
- **SA4:** PASS; permutation-200 p=0.004975
- **SA5:** FAIL; P(total improvement)=99.58%, but P(gross DD worse than P0 by >0.5R)=56.18%
- **Part B:** STOP before candidate gates; frozen trailing q0.96/90d produced N=3515, not the PINNED N=3535
- **Source audit:** original monthly top-4% selector reproduces PINNED exactly
- **Threshold curve:** diagnostic only; top-5% produced +1911.84R / gross DD 14.700R but cannot be promoted under the failed control
- **Composition:** not run
- **Selection/sizing promotion:** none

## Exit research

- **v003-lite Gate 0:** PASS; exact P0 gross DD 14.415969R and 3535/3535 parity
- **P4b observed:** +2256.51R; EV +0.6383R; gross MaxDD 12.436807R; net MaxDD 13.283629R; 0 negative months
- **P4b computable gates:** RH1 PASS; RH2 PASS; RH3 PASS; RH4 diagnostic PASS; RH5 PASS; RH8 PASS
- **P4b unresolved gates:** RH6 formal paired replay and RH7 exact spread-path replay
- **P4b status:** STRONG CORE CONFIRMATION / FORMAL HOLD; still NO-GO for EA
- **P5 v003-lite verdict:** FAIL RH7
- **Deploy tests:** R1 Dukascopy and R2 forward are deferred until pre-EA

## Next action

Do not add session/time filters. Continue with a genuinely new information layer: Entry Lab or exact execution replay, while separately resolving the selection-threshold convention and P4b RH6/RH7 deploy debt.
