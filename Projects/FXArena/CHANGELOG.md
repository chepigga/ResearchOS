# FXArena Changelog

## 2026-07-23 — Selection & Sizing Lab v001

- Executed the frozen lab against the full Release v1.1 universe and exact PINNED GEO* fixture.
- Reproduced P0 control: N=3535, total +1848.874807R, gross MaxDD 14.415969R and exact p/outcome parity.
- Confirmed monotonic p_win tercile economics: LOW EV +0.43369R, MID +0.47725R, HIGH +0.65763R.
- Falsified fixed sizing weights 0.7/1.0/1.3 under the frozen DD gates: total rose to +1924.73R, but gross MaxDD rose to 15.185R.
- SA4 permutation-200 passed at p=0.004975.
- SA5 paired moving-block failed the DD condition: P(total improvement)=99.58%, P(DD candidate > P0+0.5R)=56.18%.
- Stopped Part B at control: trailing q0.96/90d produced 3515 trades rather than PINNED 3535.
- Verified that the historical monthly top-4% selector reproduces PINNED signal-by-signal.
- Preserved the top-{3,4,5,6}% trailing curve as diagnostic only; no threshold winner was declared.
- Did not run composition and did not touch P0 exits or ContPrimary.
- Published the canonical paired moving-block sampler, seeds, manifest and complete workflow-artifact pointer.

## 2026-07-23 — Exit Tournament v003-lite

- Reproduced canonical Gate 0: P0 gross MaxDD 14.415969R with 3535/3535 parity.
- Confirmed P4b RH1-RH3, RH5 permutation-200 and RH8 dedup robustness.
- Recorded P4b: +2256.51R, EV +0.6383R, gross MaxDD 12.436807R.
- RH5: observed advantage over P4 +122.16R; monthly permutation p=0.00498.
- Falsified P5 as standalone secondary under RH7.
- Set core verdict to HOLD pending exact RH6 and spread-path RH7 replay.
- Deferred R1 Dukascopy and R2 forward to pre-EA deployment testing.

## 2026-07-23 — DD convention audit

- Identified exact P0 mismatch: pinned 14.416R is gross DD; tournament 15.827R is net DD.
- Invalidated archived RH2 and RH6-DD interpretations that mixed conventions.
- Added the corrected P0-P7 gross/net table.

## 2026-07-23 — Exit Policy Tournament v002 / P4b v001

- Recorded exact P0 replay parity and frozen P1-P7 outputs.
- Added P4 TB deep-dive and P4b post-tournament candidate.
- Kept C2 / ContPrimary unchanged.
