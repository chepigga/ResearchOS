# FXArena Changelog

## 2026-07-24 — Entry Lab v001

- Executed the frozen E0–E6 market/limit/hybrid tournament on 3535 exact GEO* signals with P4b exits.
- Reproduced E0 signal-by-signal: entry/risk exact, zero exit-time differences, total difference -0.00000192R and gross DD difference +0.00000002R.
- Retained E0 `market @ D3+60s`: +2256.51R, EV +0.63833R, gross MaxDD 12.436807R and zero negative months.
- Found E1/E2 pure limits filled only 34.23%/31.63% and missed 64.05%/66.95% of the TB branch.
- Found the TB branch contributed +1599.24R, or 70.9% of E0 total.
- Recorded E3 +1847.72R, E4 +1551.17R, E5 +1829.93R and E6 +1648.59R; all were below E0 and had worse gross DD.
- Ran paired moving-block bootstrap with shared indices, block 20, 5000 iterations and seed 2026072404; P(total candidate > E0)=0 for every candidate.
- Closed EL1/EL2/EL4 as FAIL for every E1–E6 arm; E1/E2 also failed EL5.
- Declared F10: market@D3+60 remains optimal, Entry layer closed, no v1.30 entry composition or tick-validation candidate.
- Preserved all candidate trades, missed/TB analysis, bootstrap CSV, sampler source, replay runner and SHA256 manifests in the complete output artifact.

## 2026-07-24 — Session & Time-of-Day Lab v001

- Executed the frozen four-block session diagnostic on exact P0/P4b 3535-trade fixtures.
- Reproduced P0 total +1848.874811R and gross MaxDD 14.415969R.
- Produced overall/yearly S1–S4 metrics, top-5 DD attribution, October-2023 named trade cluster and diagnostic-only hourly EV intervals.
- Found all four P4b blocks profitable overall; only Late NY 2025 was slightly negative.
- Identified NY overlap as the closest DD concentration: 42.48% of top-5 negative losses at 25.205% trade share.
- Rejected transition because the frozen trade-share ceiling was <=25% and the annual DD overrepresentation sign was not stable in 4/4 years.
- Did not execute Stage 2, permutation or paired bootstrap; no session veto was created.
- Closed the branch as F9: session edge worth filtering not found.
- Kept ContPrimary, selection, risk layer and P4b exits unchanged.

## 2026-07-23 — Selection & Sizing Lab v001

- Executed the frozen lab against the full Release v1.1 universe and exact PINNED GEO* fixture.
- Reproduced P0 control: N=3535, total +1848.874807R, gross MaxDD 14.415969R and exact p/outcome parity.
- Confirmed monotonic p_win tercile economics: LOW EV +0.43369R, MID +0.47725R, HIGH +0.65763R.
- Falsified fixed sizing weights 0.7/1.0/1.3 under the frozen DD gates: total rose to +1924.73R, but gross MaxDD rose to 15.185R.
- SA4 permutation-200 passed at p=0.004975.
- SA5 paired moving-block failed the DD condition: P(total improvement)=99.58%, P(DD candidate > P0+0.5R)=56.18%.
- Stopped Part B at control: trailing q0.96/90d produced 3515 trades rather than PINNED 3535.
- Verified that the historical monthly top-4% selector reproduces PINNED signal-by-signal.

## 2026-07-23 — Exit Tournament v003-lite

- Reproduced canonical Gate 0: P0 gross DD 14.415969R with 3535/3535 parity.
- Confirmed P4b RH1-RH3, RH5 permutation-200 and RH8 dedup robustness.
- Recorded P4b: +2256.51R, EV +0.6383R, gross MaxDD 12.436807R.
- Falsified P5 as standalone secondary under RH7.
- Set core verdict to HOLD pending exact RH6 and spread-path RH7 replay.

## 2026-07-23 — DD convention audit

- Identified exact P0 mismatch: pinned 14.416R is gross DD; tournament 15.827R is net DD.
- Invalidated archived RH2 and RH6-DD interpretations that mixed conventions.

## 2026-07-23 — Exit Policy Tournament v002 / P4b v001

- Recorded exact P0 replay parity and frozen P1-P7 outputs.
- Added P4 TB deep-dive and P4b post-tournament candidate.
- Kept C2 / ContPrimary unchanged.
