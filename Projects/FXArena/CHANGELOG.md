# FXArena Changelog

## 2026-07-23 — Exit Tournament v003-lite

- Reproduced canonical Gate 0: P0 gross MaxDD 14.415969R with 3535/3535 parity.
- Confirmed P4b RH1-RH3, RH5 permutation-200 and RH8 dedup robustness.
- Recorded P4b: +2256.51R, EV +0.6383R, gross MaxDD 12.436807R.
- RH5: observed advantage over P4 +122.16R; monthly permutation p=0.00498.
- Falsified P5 as standalone secondary under RH7: +1792.89R after commission 9pt and 0.05R slip, before spread increase.
- Preserved the full corrected P0-P7 table and SHA256 manifest.
- Set core verdict to HOLD because the original bootstrap sampler/seeds and raw M1 spread path are absent.
- Deferred R1 Dukascopy and R2 forward to pre-EA deployment testing.
- Kept P4b NO-GO for EA; Entry Lab and Exit v004 remain unfrozen.

## 2026-07-23 — DD convention audit

- Identified exact P0 mismatch: pinned 14.416R is gross DD; tournament 15.827R is net DD.
- Invalidated archived RH2 and RH6-DD interpretations that mixed conventions.
- Added the corrected P0-P7 gross/net table.

## 2026-07-23 — Exit Policy Tournament v002 / P4b v001

- Recorded exact P0 replay parity and frozen P1-P7 outputs.
- Added P4 TB deep-dive and P4b post-tournament candidate.
- Kept C2 / ContPrimary unchanged.
