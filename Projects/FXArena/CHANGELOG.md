# FXArena Changelog

## 2026-07-24 — PC5-r Resolution v001

- Executed the final permitted PC5 adjudication as a symmetric paired stress of P0 and P4c on the exact 3515 GEO*-TRAILING entries.
- Reproduced P0 and P4c at 6pt/x1.0 with zero exit-time mismatches.
- Evaluated the frozen 4x2x2 grid: commission 5/6/7.5/10pt, spread x1/x1.5 and P4c BE slip 0/0.05R.
- Preserved the frozen 1070 actual P4c BE exits as the slip population; P0 has no BE branch.
- Central cell 7.5pt/x1.5/0.05R: P0 +1779.792484R, P4c +1965.815894R, ratio 1.1045x, gross DD 14.436R versus 10.820R.
- Passed PR1, PR2 and PR4; paired moving-block block20/5000/seed2026072407 gave P(total P4c>P0)=99.98% and DD-bad diagnostic 1.50%.
- Extreme diagnostic 10pt/x1.5/0.05R retained a 1.1110x advantage and passed the DD condition.
- Failed PR5 in the measured fact cell 5pt/x1.0/0.05R: P4c +2115.640260R versus P0 +1931.350808R, ratio 1.0954x.
- Recorded the final shortfall as 0.46 percentage points versus the preregistered +10% advantage gate.
- Declared `P4C_CLOSED_FINAL__DEPLOY_EXIT_P0`; P4c is not admitted to forward A/B.
- Permanently prohibited a third PC5 retrial on these data.
- Preserved the complete paired grid, central/fact/extreme trade pairs, bootstrap output, runner/sampler source and SHA256 manifests.

## 2026-07-24 — P4c Causal Exit v001

- Reproduced archived P4b exactly and quantified its +145.708807R retrospective lookahead benefit.
- Implemented causal P4c and recorded base TRAILING +2127.402776R / gross DD 10.618161R.
- Passed PC1-PC4 before the final paired-cost adjudication.
- Original absolute PC5 verdict is superseded only by PC5-r methodology; the final deploy decision remains P0 because PR5 failed.

## 2026-07-24 — Flag-Replay v001.2

- Reconstructed the frozen TB generator and resolved all 622 trailing-only flags.
- Preserved archived P4b as research-only because retrospective flag use is non-causal.

## 2026-07-24 — Closure v001.1 monthly vs trailing

- Created separate MONTHLY research and TRAILING live canonical references.
- Created `trades_GEOstar_TRAILING_PINNED.csv.gz` as the official live P0 reference.

## 2026-07-24 — Entry Lab v001

- Retained `market @ D3+60s`; declared F10.

## 2026-07-24 — Session & Time-of-Day Lab v001

- No block passed T1-T3; declared F9.

## 2026-07-23 — Selection & Sizing Lab v001

- Confirmed monotonic p_win economics but falsified fixed sizing under DD gates.

## 2026-07-23 — DD convention audit

- Established gross-DD as the permanent gate convention.
