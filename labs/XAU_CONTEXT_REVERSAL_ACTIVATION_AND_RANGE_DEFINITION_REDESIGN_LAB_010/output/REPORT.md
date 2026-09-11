# XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010

**Verdict: REVERSAL_RANGE_REDESIGN_NOT_SUPPORTED**

> Indicator-state / human-decision-support redesign only. No trading edge or execution claim.

- Canonical XAU SHA: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Valid Context H4 bars: **6,216**
- Frozen episodes: **610**
- Reversal winner: **NONE**
- Range winner: **NONE**

## Reversal candidate summary

| Candidate | Eligible | N24 | N2025 | N2026 | 24h flip premium | 95% CI | Bootstrap | Years + | Transfer |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| R1_LOCATION_TRANSITION | YES | 823 | 201 | 112 | +0.0006 | [-0.0341, +0.0363] | FAIL | 2/4 | FAIL |
| R2_TWO_OF_FIVE | YES | 906 | 223 | 127 | +0.0090 | [-0.0242, +0.0431] | FAIL | 2/4 | FAIL |
| R3_RAW_REVERSAL_WINNER | YES | 147 | 33 | 24 | +0.0324 | [-0.0561, +0.1202] | FAIL | 4/4 | PASS |

## Range candidate summary

| Candidate | Eligible | Prevalence | N8 | 8h containment premium | 95% CI | Bootstrap | Expansion-candidate 24h range | Movement CI | Years + |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| G1_VOL_COMPRESSION | YES | 18.1% | 1055 | -0.0601 | [-0.1004, -0.0203] | FAIL | +0.0522 | [-0.2036, +0.3241] | 1/4 |
| G2_STRUCTURAL_COIL | YES | 4.3% | 246 | +0.0531 | [-0.0182, +0.1045] | FAIL | +0.3313 | [+0.0549, +0.6227] | 2/4 |
| G3_MAJORITY_3OF5 | YES | 21.3% | 1251 | -0.0001 | [-0.0403, +0.0383] | FAIL | +0.2160 | [-0.0186, +0.4741] | 2/4 |
| G4_STRICT_COIL | YES | 2.3% | 137 | +0.0050 | [-0.0914, +0.0613] | FAIL | +0.1093 | [-0.2988, +0.4230] | 2/4 |

## Reversal scarcity diagnostic — annual

| Year | Sweep | RSI turn | EMA20 cross | ADX falling | Rejection | Raw rev #1 | Raw rev top2 | Frozen events | R1 | R2 | R3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 11.0% | 15.4% | 10.8% | 49.5% | 40.7% | 4.1% | 13.0% | 3 | 292 | 316 | 53 |
| 2024 | 9.9% | 11.9% | 15.0% | 51.6% | 40.9% | 3.1% | 9.9% | 3 | 304 | 338 | 42 |
| 2025 | 11.5% | 13.8% | 12.6% | 49.9% | 41.3% | 3.5% | 9.8% | 1 | 293 | 328 | 49 |
| 2026 | 11.0% | 11.4% | 13.4% | 51.8% | 40.8% | 4.2% | 11.0% | 1 | 154 | 186 | 32 |

## Interpretation constraints

- R1–R3 and G1–G4 were frozen in PREREG before outcomes; no thresholds were optimized after seeing results.
- Reversal candidates are activation-event onsets, not repeated bars.
- Range candidates are persistent bar-level conditions because a human display must remain on while compression persists.
- A candidate that increases frequency without semantic separation is rejected.
- Reused history: any winner is discovery-only and requires fresh post-freeze replication before changing the production indicator.