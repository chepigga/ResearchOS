# LAB022 — DISJOINT_COMPRESSION_ISLAND_FROZEN_REPLICATION

Date: 2026-08-26
Status: FROZEN BEFORE RESULT CALCULATION

## Candidate
Exactly one frozen candidate from LAB020:
- family: COMPRESSION_RELEASE
- direction: SELL
- latest confirmed opposite-side M15 pivot-5 at actual fill
- pivot age: 16–21 M15 bars inclusive
- pivot unviolated from confirmation to fill
- riskATR: 2.5 <= riskATR < 3.0
- compression/release/retest operationalization exactly as LAB018 operational freeze
- preserve the pooled BUY+SELL family event queue / virtual opposite-side blocker state exactly as the historical discovery implementation
- TP 2.3R
- BE after +1R
- base cost 0.06R

No threshold changes, no side changes, no ML, no added filters.

## Primary replication checks
1. DEV 2019–2022 and VAL 2023–2025 sign and magnitude.
2. VAL yearly and half-year concentration; reject promotion if >70% of VAL net sumR comes from one year or one half-year.
3. Cost stress 1.0x / 1.25x / 1.5x.
4. Exact M1 execution replay for 2024–2025 where release asset coverage exists; require no sign reversal and high fill/outcome parity.
5. 2026 shadow only; excluded from formal verdict.
6. Overlap with the frozen BREAK_RETEST core and frozen OLD-PIVOT COMPRESSION SELL core.
7. Global one-position portfolio admission when added to the current two-engine portfolio.

## Promotion gates for the island
- DEV EV > 0
- VAL EV >= +0.10R
- VAL PF >= 1.30
- at least 2/3 positive VAL years
- 1.5x cost EV > 0
- M1 2024–2025 EV >= 0 and no material execution mismatch
- no single VAL year contributes >70% of VAL net sumR
- no single VAL half-year contributes >70% of VAL net sumR
- portfolio addition does not worsen MaxDD by >50% versus current two-engine core portfolio while maintaining EV >= +0.15R

## Decision
This LAB may only: PASS, WATCH, or REJECT the frozen island. It may not tune age/risk thresholds or replace the pooled blocker implementation after seeing results.