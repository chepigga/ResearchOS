# XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013

**Verdict: COMPRESSION_DIRECTION_AND_RESOLUTION_SUPPORTED_DISCOVERY_ONLY**

> Human-facing compression direction/resolution diagnostic only. No trading edge or execution claim.

- Valid Context H4 bars: **6,216**
- Frozen episodes: **610**
- Pullback + G1 compression bars: **767**
- Exact 8h resolved first passages: **416**
- Exact target balance: BULL **211**, BEAR **205**, bull share **0.507**
- NO_BREAKOUT: **350**; AMBIGUOUS: **1**
- Direction winner: **D2_TREND_PRESSURE**

## Candidate gates

| Candidate | Coverage | N resolved predicted | Accuracy | 95% CI | H1 | Signed24 ATR | 95% CI | H2 | Both |
|---|---:|---:|---:|---:|---|---:|---:|---|---|
| D1_HTF_BIAS | 74.2% | 306 | 0.572 | [0.502, 0.642] | PASS | +0.487 | [+0.174, +0.786] | PASS | PASS |
| D2_TREND_PRESSURE | 62.3% | 266 | 0.579 | [0.508, 0.648] | PASS | +0.518 | [+0.181, +0.853] | PASS | PASS |
| D3_PRE12H_MOMENTUM | 89.6% | 369 | 0.504 | [0.446, 0.562] | FAIL | +0.123 | [-0.080, +0.349] | FAIL | FAIL |
| D4_CONSENSUS_2OF3 | 62.1% | 263 | 0.567 | [0.492, 0.636] | FAIL | +0.562 | [+0.228, +0.881] | PASS | FAIL |

## Interpretation constraints

- D1–D4, exact M1 ±1 ATR first-passage target, 8h horizon, 24h follow-through metric and gates were preregistered before outcomes.
- `NO_BREAKOUT` and same-M1 `AMBIGUOUS` outcomes are never forced into a direction.
- Reused history: any positive result remains DISCOVERY_ONLY pending fresh post-freeze replication.
- This lab cannot authorize automated entries, BUY/SELL signals, sizing or prop-risk changes.
