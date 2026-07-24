# FXArena Changelog

## 2026-07-24 — Flag-Replay v001.2

- Reconstructed the frozen TB generator `EFFICIENCY_5 OR BB_EXPANSION OR RANGE_EXPANSION_15` without threshold changes or outcome inference.
- Reproduced archived `tb_flag` exactly on 3535/3535 monthly episodes with 1274 true flags and zero mismatches.
- Reproduced the archived P4b trade fixture with zero exit-time mismatches and total +2256.511802R.
- Generated flags for all 291659 universe episodes and resolved all 622 trailing-only episodes; 196 of those are TB.
- Ran P4b on the exact GEO*-TRAILING 3515 set: total +2277.306670R versus P0 +1889.613320R; gross MaxDD 10.618161R versus 14.415969R.
- Recorded C1 PASS, C2 PASS and C4 PASS with paired moving-block probability 100%, block 20, 5000 iterations, seed 2026072405.
- Recorded C3 FAIL because P4b has one negative month, February 2023 at -2.040203R, while P0 has zero negative months.
- Declared STOP-ALARM / NOT_PROMOTED under the frozen all-gates rule; did not create `trades_P4b_TRAILING_PINNED`.
- Preserved the exact candidate, universe flags, generator source, controls, bootstrap output and SHA256 manifest in the complete artifact.
- Kept ContPrimary, q0.96/90d, flag thresholds, P4b rules and F1-F10 unchanged.
- Preserved the separate forensic warning that archived P4b applies the 30-minute flag retrospectively; a causal P4c requires a new frozen session.

## 2026-07-24 — Closure v001.1 monthly vs trailing

- Reproduced monthly N=3535 / +1848.874807R and trailing N=3515 / +1889.613320R signal-by-signal.
- Created `trades_GEOstar_TRAILING_PINNED.csv.gz` as the official live P0 reference.
- Established separate MONTHLY research and TRAILING live baselines.
- Initially stopped P4b transfer because 622 trailing-only flags were missing; Flag-Replay v001.2 later resolved that input debt.

## 2026-07-24 — Entry Lab v001

- Executed E0-E6 and retained `market @ D3+60s`.
- Declared F10: Entry layer closed.

## 2026-07-24 — Session & Time-of-Day Lab v001

- No block passed T1-T3; declared F9.

## 2026-07-23 — Selection & Sizing Lab v001

- Confirmed monotonic p_win economics but falsified fixed sizing under DD gates.
- Identified the monthly/trailing selector distinction.

## 2026-07-23 — Exit Tournament v003-lite

- Recorded monthly P4b +2256.51R and gross MaxDD 12.436807R.

## 2026-07-23 — DD convention audit

- Established gross-DD as the permanent gate convention.

## 2026-07-23 — Exit Policy Tournament v002 / P4b v001

- Recorded frozen P0-P7 outputs and kept ContPrimary unchanged.
