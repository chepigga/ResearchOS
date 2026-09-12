# XAU_CONTEXT_REVERSAL_TEMPORAL_SEQUENCE_AND_COMPRESSION_STATE_INTERACTION_LAB_012

**Verdict: COMPRESSION_INTERACTION_SUPPORTED_REVERSAL_SEQUENCE_NOT_CONFIRMED**

> Indicator temporal-sequence / state-interaction diagnostic only. No trading edge or execution claim.

- Valid Context H4 bars: **6,216**
- Frozen episodes: **610**
- RSEQ events: **330** (BULL 178, BEAR 152)
- RSEQ overlap with raw R3: **3**; suppressed R3 overlap: **3**

## Primary gates

| Gate | Eligible | Effect | 95% CI | Transfer | Pass |
|---|---|---:|---:|---|---|
| R_H1 | YES | +0.0098 | [-0.0602, +0.0782] | PASS | FAIL |
| R_H2 | YES | +0.0466 | [-0.1308, +0.2388] | FAIL | FAIL |
| C_H1 | YES | +0.0992 | [+0.0550, +0.1453] | PASS | PASS |
| C_H2 | YES | +0.2678 | [+0.0710, +0.4745] | PASS | PASS |
| C_H3 | YES | +0.0754 | [-0.3712, +0.2603] | NA | FAIL |

## Reversal sequence by main state

| State | N event | N control | 24h flip premium |
|---|---:|---:|---:|
| PULLBACK | 205 | 2543 | -0.0056 |
| EXPANSION | 8 | 1019 | -0.1373 |
| RANGE | 32 | 463 | +0.1455 |

## Compression interaction

- Pullback 8h breakout premium: **+0.0992**, CI [+0.0550, +0.1453].
- Pullback 24h range premium: **+0.2678 ATR**, CI [+0.0710, +0.4745].
- Pullback minus Expansion 8h breakout interaction: **+0.0754**, CI [-0.3712, +0.2603].
- G1 valid counts in interaction: Pullback **720**, Expansion **22**.

## Interpretation constraints

- One ordered reversal sequence and frozen G1 compression were preregistered before outcomes; no variant/threshold search is allowed.
- Positive reused-history findings remain DISCOVERY_ONLY until fresh post-freeze replication.
- This lab supports display semantics only; it cannot authorize automated entries or risk changes.
