# LAB020 — OLD_PROTECTED_PIVOT_FREQUENCY_SURFACE

Date: 2026-08-26
Status: PREREGISTERED BEFORE RESULT CALCULATION

## Goal
Determine whether the currently positive old-protected-pivot core is a narrow threshold cliff or sits on a broader neighboring plateau that can increase trade frequency without destroying edge.

This is a coarse mechanism surface, not threshold optimization.

## Frozen event families
1. BREAK_RETEST canonical M15 event family.
2. COMPRESSION_RELEASE SELL using LAB018 operational definition.

No new event logic, side switching, ML, or PnL-driven threshold changes.

## Surface axes
Pivot-age bins (M15 bars):
- <10
- 10–15
- 16–21
- 22–31
- 32+

riskATR bins:
- <2.5
- 2.5–3.0
- 3.0–3.72
- 3.72–5.0
- >5.0

The historical positive core `pivot age >=22 AND riskATR >3.72` is the reference region, not a tunable target.

## Data splits
- DEV: 2019–2022
- VAL: 2023–2025
- 2026 excluded from verdict.

## Required outputs
For every cell and each event family separately:
- N, trades/year
- EV (R)
- PF
- sumR
- yearly EV/count
- cost stress 1.25x and 1.5x where sample allows

Also calculate cumulative neighboring regions, especially:
- age >=16 & riskATR >=3.0
- age >=16 & riskATR >=3.72
- age >=22 & riskATR >=3.0
- frozen core age >=22 & riskATR >3.72
- age >=32 & riskATR >3.72

These cumulative regions are descriptive and fixed before results; no additional cuts may be introduced based on PnL.

## Plateau criteria
A broader region may be called a `PLATEAU_CANDIDATE` only if on VAL:
- N >= 1.5x frozen-core N for that family;
- EV >= +0.10R;
- PF >= 1.20;
- >=2/3 positive VAL years;
- EV remains >0 under 1.5x costs;
- the adjacent included cells do not show a single isolated winner surrounded by negative cells.

For the two-engine combined portfolio, a broader surface admission is only descriptive in LAB020; no new portfolio rule is promoted without a later frozen replication.

## Interpretation guardrails
- Do not choose a new threshold because it is the best cell.
- Do not merge bins after seeing results.
- A smooth monotone/plateau-like neighborhood is stronger evidence than one high-EV cell.
- If the positive region is confined to the frozen 22/3.72 corner, conclude that the core is structurally narrow and frequency must come from independent event families rather than loosening context.
