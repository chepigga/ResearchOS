# FXArena PC5-r Resolution v001 — paired cost stress P4c/P0

## Verdict

**P4C_CLOSED_FINAL__DEPLOY_EXIT_P0**

This was the final permitted PC5 adjudication. No third retrial is allowed on these data.

## Gate 0

- Exact paired order: **PASS**, N=3515.
- P0 replay at 6pt/x1.0: exit mismatches **0**, total +1889.613324R.
- P4c replay at 6pt/x1.0: exit mismatches **0**, total +2127.402776R.
- Frozen changed BE exits receiving slip when enabled: **1070**.

## Full 4×2×2 survivability map

| Commission RT pt | Spread | BE slip R | P0 total | P4c total | Delta | Ratio | P0 gross DD | P4c gross DD | 10% advantage | DD gate |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 5 | x1 | 0.00 | +1931.35 | +2169.14 | +237.79 | 1.123x | 14.416 | 10.618 | PASS | PASS |
| 5 | x1 | 0.05 | +1931.35 | +2115.64 | +184.29 | 1.095x | 14.416 | 10.768 | FAIL | PASS |
| 5 | x1.5 | 0.00 | +1884.14 | +2123.66 | +239.52 | 1.127x | 14.436 | 10.670 | PASS | PASS |
| 5 | x1.5 | 0.05 | +1884.14 | +2070.16 | +186.02 | 1.099x | 14.436 | 10.820 | FAIL | PASS |
| 6 | x1 | 0.00 | +1889.61 | +2127.40 | +237.79 | 1.126x | 14.416 | 10.618 | PASS | PASS |
| 6 | x1 | 0.05 | +1889.61 | +2073.90 | +184.29 | 1.098x | 14.416 | 10.768 | FAIL | PASS |
| 6 | x1.5 | 0.00 | +1842.40 | +2081.92 | +239.52 | 1.130x | 14.436 | 10.670 | PASS | PASS |
| 6 | x1.5 | 0.05 | +1842.40 | +2028.42 | +186.02 | 1.101x | 14.436 | 10.820 | PASS | PASS |
| 7.5 | x1 | 0.00 | +1827.01 | +2064.80 | +237.79 | 1.130x | 14.416 | 10.618 | PASS | PASS |
| 7.5 | x1 | 0.05 | +1827.01 | +2011.30 | +184.29 | 1.101x | 14.416 | 10.768 | PASS | PASS |
| 7.5 | x1.5 | 0.00 | +1779.79 | +2019.32 | +239.52 | 1.135x | 14.436 | 10.670 | PASS | PASS |
| 7.5 | x1.5 | 0.05 | +1779.79 | +1965.82 | +186.02 | 1.105x | 14.436 | 10.820 | PASS | PASS |
| 10 | x1 | 0.00 | +1722.66 | +1960.45 | +237.79 | 1.138x | 14.416 | 10.618 | PASS | PASS |
| 10 | x1 | 0.05 | +1722.66 | +1906.95 | +184.29 | 1.107x | 14.416 | 10.768 | PASS | PASS |
| 10 | x1.5 | 0.00 | +1675.45 | +1914.97 | +239.52 | 1.143x | 14.436 | 10.670 | PASS | PASS |
| 10 | x1.5 | 0.05 | +1675.45 | +1861.47 | +186.02 | 1.111x | 14.436 | 10.820 | PASS | PASS |

## Central cell — commission 7.5pt, spread x1.5, BE slip 0.05R

- P0 total: **+1779.792484R**.
- P4c total: **+1965.815894R**.
- P4c/P0 ratio: **1.1045x**.
- P0 gross DD: **14.436103R**.
- P4c gross DD: **10.819815R**.
- PR1: **PASS**.
- PR2: **PASS**.
- PR4: **PASS**, P(total P4c>P0)=99.98%; diagnostic P(DD P4c>P0+0.5)=1.50%.

## Fact cell — commission 5pt, spread x1.0, BE slip 0.05R

- P0 total: **+1931.350808R**.
- P4c total: **+2115.640260R**.
- Ratio: **1.0954x**.
- Gross DD: P0 14.415969R; P4c 10.768161R.
- PR5: **FAIL**.

## Extreme diagnostic — commission 10pt, spread x1.5, BE slip 0.05R

- P0 total: **+1675.448775R**.
- P4c total: **+1861.472184R**.
- Ratio: **1.1110x**.
- PR1 diagnostic: **PASS**; PR2 diagnostic: **PASS**.

## Gate table

| Gate | Result |
|---|---|
| PR1 | PASS |
| PR2 | PASS |
| PR3 diagnostic | PR1=PASS, PR2=PASS |
| PR4 | PASS |
| PR5 | FAIL |

## Governance

- P4c policy unchanged.
- P0 policy unchanged.
- Commission grid, spread cells and central cell unchanged after results.
- Slip is applied only to the frozen set of 1070 P4c BE exits; P0 has no BE branch.
- ContPrimary untouched; F1-F10 remain active.
- Third PC5 retrial is permanently prohibited.

## Promotion boundary

P4c is closed permanently on these data and remains a research fixture. Deployment exit is P0.
