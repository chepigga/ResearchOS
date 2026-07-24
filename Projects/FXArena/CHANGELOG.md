# FXArena Changelog

## 2026-07-24 — Closure v001.1 monthly vs trailing

- Reproduced the historical monthly top-4% selector signal-by-signal: N=3535, total +1848.874807R, gross MaxDD 14.415969R.
- Reproduced the EA-style trailing q0.96/90d selector signal-by-signal: N=3515, total +1889.613320R, gross MaxDD 14.415969R.
- Created `trades_GEOstar_TRAILING_PINNED.csv.gz` as the official live/August E-exam P0 reference.
- Retained GEO*-MONTHLY as the research-only reference.
- Recorded intersection 2893, monthly-only 642, trailing-only 622, symmetric difference 1264 and Jaccard overlap 69.59%.
- Established the permanent rule that live results compare only to TRAILING and research laboratories compare only to MONTHLY.
- Stopped P4b transfer before C1-C4: the frozen P4b fixture contains causal `tb_flag` only for the monthly set and leaves all 622 trailing-only episodes unlabelled.
- Refused post-hoc non-TB assignment, outcome/MFE inference, or a new flag model.
- Did not create `trades_P4b_TRAILING_PINNED`; P4b live deployment remains blocked pending exact full-universe P4 flag replay.
- Reserved Registry v3 bootstrap law for the future complete pair: block 20, 5000 iterations, seed 2026072405.
- Kept ContPrimary, q0.96/90d, P4b rules and F1-F10 unchanged.

## 2026-07-24 — Entry Lab v001

- Executed the frozen E0-E6 market/limit/hybrid tournament on 3535 exact GEO* signals with P4b exits.
- Reproduced E0 signal-by-signal and retained `market @ D3+60s`.
- Found E1-E6 all failed EL1, EL2 and paired EL4.
- Declared F10: Entry layer closed.

## 2026-07-24 — Session & Time-of-Day Lab v001

- Executed the frozen four-block diagnostic.
- No block passed T1-T3; Stage 2 was not run.
- Declared F9: no session edge worth filtering.

## 2026-07-23 — Selection & Sizing Lab v001

- Reproduced P0 control and confirmed monotonic p_win tercile economics.
- Falsified fixed 0.7/1.0/1.3 sizing under DD gates.
- Identified that trailing q0.96/90d and historical monthly top-4% are different selector mechanisms.

## 2026-07-23 — Exit Tournament v003-lite

- Recorded monthly P4b +2256.51R and gross MaxDD 12.436807R.
- Kept P4b as research confirmation rather than live/deploy validation.

## 2026-07-23 — DD convention audit

- Identified the permanent gross-DD versus net-DD convention.

## 2026-07-23 — Exit Policy Tournament v002 / P4b v001

- Recorded frozen P0-P7 outputs and the P4b post-tournament candidate.
- Kept C2 / ContPrimary unchanged.