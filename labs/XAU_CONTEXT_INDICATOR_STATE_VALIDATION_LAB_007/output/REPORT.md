# XAU_CONTEXT_INDICATOR_STATE_VALIDATION_LAB_007

**Verdict: CONTEXT_STATE_SEMANTICS_NOT_SUPPORTED**

> This lab validates state semantics, not trading edge. No TP/SL, no PF/EV gate, no live-risk authorization.

- Canonical XAU SHA: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Valid H4 Context bars: **6,216**
- Primary state episodes: **610**

## Primary 24h state map — episode onsets

| State | Episodes | Range / ATR | |Close| / ATR | Contained ±1ATR | Momentum flip | Bias follow | Median episode H4 bars |
|---|---:|---:|---:|---:|---:|---:|---:|
| EXPANSION | 201 | 2.668 | 1.272 | 13.0% | 53.5% | 53.5% | 5.0 |
| PULLBACK | 318 | 2.533 | 1.236 | 14.1% | 57.5% | 47.0% | 10.0 |
| REVERSAL | 10 | 1.960 | 0.848 | 11.1% | 80.0% | nan% | 3.0 |
| RANGE | 81 | 2.463 | 1.132 | 12.7% | 52.2% | 33.3% | 7.0 |

## Preregistered semantic gates

| Hypothesis | Effect | 95% weekly-cluster CI | P(effect>0) | Gate | Year sign transfer |
|---|---:|---:|---:|---|---|
| H1_EXPANSION_RANGE_MOVEMENT | +0.2049 | [-0.0872, +0.5007] | 0.909 | FAIL | 2/4 |
| H2_EXPANSION_RANGE_DISPLACEMENT | +0.1397 | [-0.1428, +0.4169] | 0.833 | FAIL | 3/4 |
| H3_RANGE_CONTAINMENT | -0.0029 | [-0.0929, +0.0914] | 0.476 | FAIL | 2/4 |
| H4_REVERSAL_MOMENTUM_FLIP | +0.2646 | [-0.2139, +0.5204] | 0.895 | FAIL | 1/2 |
| H5_PULLBACK_BIAS_RESUME | +0.1363 | [-0.3482, +0.5057] | 0.738 | FAIL | 3/3 |

**Semantic gates:** 0/5  
**Stable 3-of-4-year hypotheses:** 1/5  
**Transfer gate:** FAIL

## Interpretation rules

- `EXPANSION` is useful if it identifies more future movement/displacement than `RANGE`; it does not need to make money by itself.
- `RANGE` is useful if it genuinely contains price more often.
- `REVERSAL` is useful if it increases the probability that already-known pre-state momentum flips.
- `PULLBACK` is useful if it more often resumes the already-known structural bias than `RANGE`.
- 4h/12h/48h and all-H4-bar tables are diagnostics only; the preregistered verdict is driven by 24h episode onsets.