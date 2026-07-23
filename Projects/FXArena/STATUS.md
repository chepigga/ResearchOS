# FXArena Status

- **Project:** FXArena
- **Updated:** 2026-07-23
- **Lifecycle status:** ACTIVE_RESEARCH / SELECTION-SIZING v001 COMPLETED WITH B CONTROL STOP
- **Canonical live baseline:** C2 / ContPrimary unchanged
- **Frozen research control:** GEO* `MICRO30 / TP 2.0R / timeout 120 min`
- **Canonical GEO* metrics:** N=3535; Total net=+1848.87R; EV net=+0.523020R; gross MaxDD=14.415969R
- **DD convention:** gross equity MaxDD is the gate metric; net MaxDD is diagnostic and must be labelled

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
- **Important verdict boundary:** “1 bit sufficient” is not claimed because Part B was not validly adjudicated
- **Result checkpoint:** `Releases/v1.2/SelectionSizing_v001/`

## Exit research

- **v003-lite Gate 0:** PASS; exact P0 gross DD 14.415969R and 3535/3535 parity
- **P4b observed:** +2256.51R; EV +0.6383R; gross MaxDD 12.436807R; net MaxDD 13.283629R; 0 negative months
- **P4b computable gates:** RH1 PASS; RH2 PASS; RH3 PASS; RH4 diagnostic PASS; RH5 PASS; RH8 PASS
- **P4b unresolved gates:** RH6 formal paired replay and RH7 exact spread-path replay
- **P4b status:** STRONG CORE CONFIRMATION / FORMAL HOLD; still NO-GO for EA
- **P5 v003-lite verdict:** FAIL RH7
- **Deploy tests:** R1 Dukascopy and R2 forward are deferred until pre-EA

## Next action

Decide and preregister the selection-threshold convention before another threshold lab: either reproduce the historical monthly top-4% selector or explicitly re-pin the system to trailing q0.96/90d. No post-hoc rescue of v001 is allowed.
