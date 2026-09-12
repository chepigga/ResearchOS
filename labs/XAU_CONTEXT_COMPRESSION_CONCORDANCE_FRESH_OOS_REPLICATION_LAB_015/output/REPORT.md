# XAU_CONTEXT_COMPRESSION_CONCORDANCE_FRESH_OOS_REPLICATION_LAB_015

**Verdict: FRESH_OOS_NO_TESTABLE_EVENTS**

> Genuine post-freeze OOS semantic replication on FTMO-Demo raw ticks. No trading edge or execution claim.

- Fresh OOS available_time: **2026-07-24 00:00:00 -> 2026-08-27 16:00:00**
- Fresh Pullback + G1 bars: **6**
- D14 directional coverage: **100.0%** (6/6)
- Exact resolved D14 predictions: **3**
- 24h D14 follow-through observations: **6**

## Primary fresh gates

| Gate | Eligible | Effect | 95% CI | Pass |
|---|---|---:|---:|---|
| H1 first-passage accuracy | NO | 0.667 | [0.667, 0.667] | FAIL |
| H2 signed 24h ATR | NO | -1.636 | [-1.636, -1.636] | FAIL |
| H3 BULL/BEAR symmetry | NO | NA / 0.667 | — | FAIL |
| H4 parent compression continuity | NO | breakout 0.040; range24 1.593 | breakout [-0.026, 0.141] | FAIL |

## Side symmetry

| side   |   n_resolved |   accuracy |   mean_signed24_atr |
|:-------|-------------:|-----------:|--------------------:|
| BULL   |            0 | nan        |           nan       |
| BEAR   |            3 |   0.666667 |            -1.92464 |

## Fresh-week breakdown

| week                  |   population |   resolved_d14_n |   accuracy |   follow24_n |   mean_signed24_atr |
|:----------------------|-------------:|-----------------:|-----------:|-------------:|--------------------:|
| 2026-07-27/2026-08-02 |            6 |                3 |   0.666667 |            6 |            -1.63608 |

## Source / leakage audit

- Archive SHA256: `31f9548204fa99c29ce7d09e5b64e01ff75f5e8e3efab6f747cbd410cf34fd2e`
- Source: **FTMO-Demo / XAUUSD**
- Processed raw members: **604** (CAUSAL_XAU_RAW_XAUUSD_20250101.csv -> CAUSAL_XAU_RAW_XAUUSD_20260827.csv)
- Reconstructed M1 rows: **579,773**, H4 rows: **2,557**
- M1 range: **2025-01-02 01:05:00 -> 2026-08-27 13:42:00**

## Interpretation constraints

- No pre-2026-07-24 Context observation enters H1/H2/H3.
- D1, D2, D14, G1, ±1 ATR barrier and 8h/24h horizons were frozen before outcomes.
- BID is the only price used; ask/spread cannot affect this semantic test.
- A positive verdict validates human-facing Context semantics only; it does not authorize automated entries or risk changes.
