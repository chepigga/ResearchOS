# FXArena Changelog

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

- Reproduced canonical Gate 0: P0 gross MaxDD 14.415969R with 3535/3535 parity.
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
