# FXArena Changelog

## 2026-07-24 — P4c Causal Exit v001

- Reproduced archived P4b exactly: 3535 trades, zero exit-time mismatches, +2256.511802R and gross DD 12.436807R.
- Reproduced the frozen TB generator 3535/3535 with zero mismatches.
- Implemented the preregistered causal P4c policy: TP2 from inception; TP3 activates only at entry+30m if the TB trade remains open; no re-entry after early TP2.
- Quantified the archived lookahead price: 193 trades diverged; causal P4c loses 145.708807R versus P4b on MONTHLY, with unchanged gross DD.
- Recorded P4c MONTHLY +2110.802995R and zero negative months.
- Recorded P4c TRAILING +2127.402776R versus P0 +1889.613320R; gross DD 10.618161R versus 14.415969R.
- Passed PC1, PC2, PC3 and PC4; paired moving-block probability P(total>P0)=100%, block20/5000/seed2026072406.
- Recalculated the raw-spread path because P4c exit structure differs from P4b.
- Failed PC5: spread x1.5 + commission 9 points + 0.05R slip on 1070 changed BE exits yields +1903.209668R, below PC1 threshold +2078.574652R.
- Diagnosed commission sensitivity as primary: commission 9 points alone yields +2002.190324R and fails PC1, while spread x1.5 alone still passes.
- Did not create `trades_P4c_TRAILING_PINNED`; deploy exit remains P0 GEO*-TRAILING.
- Kept ContPrimary, activation time, TP levels, BE time and F1-F10 unchanged.

## 2026-07-24 — Flag-Replay v001.2

- Reconstructed the frozen TB generator and resolved all 622 trailing-only flags.
- Recorded archived P4b trailing +2277.306670R / DD 10.618161R as research-only.
- Preserved the retrospective-flag causality warning later adjudicated by P4c v001.

## 2026-07-24 — Closure v001.1 monthly vs trailing

- Created separate MONTHLY research and TRAILING live canonical references.
- Created `trades_GEOstar_TRAILING_PINNED.csv.gz` as the official live P0 reference.

## 2026-07-24 — Entry Lab v001

- Retained `market @ D3+60s`; declared F10.

## 2026-07-24 — Session & Time-of-Day Lab v001

- No block passed T1-T3; declared F9.

## 2026-07-23 — Selection & Sizing Lab v001

- Confirmed monotonic p_win economics but falsified fixed sizing under DD gates.

## 2026-07-23 — Exit Tournament v003-lite

- Recorded monthly P4b +2256.51R before causal and execution closure.

## 2026-07-23 — DD convention audit

- Established gross-DD as the permanent gate convention.
