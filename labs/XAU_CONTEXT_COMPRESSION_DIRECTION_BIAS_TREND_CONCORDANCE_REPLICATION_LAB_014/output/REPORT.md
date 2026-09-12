# XAU_CONTEXT_COMPRESSION_DIRECTION_BIAS_TREND_CONCORDANCE_REPLICATION_LAB_014

**Verdict: BIAS_TREND_CONCORDANCE_SEMANTICS_SUPPORTED_INCREMENT_NOT_CONFIRMED**

> Concordance replication for human-facing compression direction only. No trading edge or execution claim.

- Valid Context H4 bars: **6,216**
- Frozen episodes: **610**
- Pullback + G1 bars: **767**
- D14 directional coverage: **51.8%** (397/767)
- Exact resolved D14 predictions: **220**
- Exact target balance: BULL **211**, BEAR **205**, bull share **0.507**

## Primary gates

| Gate | Eligible | Effect | 95% CI | Transfer | Pass |
|---|---|---:|---:|---|---|
| H1 first-passage accuracy | YES | 0.605 | [+0.528, +0.682] | PASS | PASS |
| H2 signed 24h ATR | YES | +0.570 | [+0.218, +0.929] | PASS | PASS |
| H3 BULL/BEAR symmetry | YES | 0.580 / 0.649 | — | — | PASS |
| H4 concordance uplift vs D2 no-bias | YES | +0.148 | [-0.046, +0.343] | — | FAIL |

## Side symmetry

| side   |   n_resolved |   accuracy |   mean_signed24_atr |
|:-------|-------------:|-----------:|--------------------:|
| BULL   |          143 |   0.58042  |            0.795669 |
| BEAR   |           77 |   0.649351 |            0.422377 |

## Incremental concordance diagnostic

- Concordant accuracy: **0.605** (N=220).
- D2 with neutral HTF bias accuracy: **0.457** (N=46).
- Difference: **+0.148**, CI [-0.046, +0.343].

## Interpretation constraints

- D14 agreement rule, exact M1 ±1 ATR target, gates and bootstrap were frozen before outcomes.
- No disagreement or neutral-bias cases may be reclassified after results.
- Reused history: positive findings remain DISCOVERY_ONLY pending genuinely fresh post-freeze data.
- This lab cannot authorize automated entries, BUY/SELL signals, sizing or prop-risk changes.