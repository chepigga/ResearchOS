# FXArena Exit Policy Tournament v002 — DD Convention Erratum

**Date:** 2026-07-23  
**Status:** CRITICAL AUDIT FINDING  
**Effect:** original RH2 verdicts and RH6(i) probabilities are not comparable with the pinned GEO* gate until recomputed.

## Exact cause

The discrepancy is not caused by entry-time versus exit-time sorting.

On the same 3,535 P0 trades:

- cumulative **gross R** MaxDD = **14.415969R**, matching the pinned GEO* value **14.416R**;
- cumulative **net R** MaxDD = **15.827253R**, the value used by the v002 tournament output.

Total R and EV were calculated from `net`, while the preregistered pinned MaxDD and RH2 ceiling were inherited from the `gross` equity curve. The v002 engine silently compared a net-DD statistic with a gross-DD threshold.

## Consequence for RH2

Using the canonical gross-DD convention, every P1–P7 policy is below the frozen 14.916R ceiling:

| Policy | Total net R | Canonical gross MaxDD | Net MaxDD diagnostic | Corrected RH2 |
|---|---:|---:|---:|---|
| P0 | +1848.87 | 14.416 | 15.827 | BASELINE |
| P1 | +1996.79 | 14.416 | 15.827 | PASS |
| P2 | +1829.52 | 14.790 | 16.201 | PASS |
| P3 | +1988.10 | 14.790 | 16.201 | PASS |
| P4 | +2134.36 | 14.416 | 15.827 | PASS |
| P5 | +1984.15 | 13.572 | 15.812 | PASS |
| P6 | +1500.27 | 12.746 | 14.085 | PASS |
| P7 | +1643.97 | 13.853 | 15.961 | PASS |

Therefore the archived statements “P4 fails RH2” and “P5 fails RH2” are false under the frozen canonical convention.

## Consequence for RH6

The archived block-bootstrap `delta_dd` values were also produced from net-DD and cannot serve as formal RH6(i) evidence against the pinned gross-DD baseline.

A separate forensic estimate was run with:

- paired moving blocks;
- 20-trade block length;
- 5,000 iterations;
- shared resamples;
- net Total R and gross MaxDD;
- audit seed `20260723`.

Estimated `P(DD_candidate > DD_P0 + 0.5R)`:

| Policy | p(total improvement) | p(gross DD bad) | Estimated RH6 |
|---|---:|---:|---|
| P1 | 1.0000 | 0.1086 | FAIL |
| P2 | 0.1634 | 0.1624 | FAIL |
| P3 | 0.9994 | 0.1712 | FAIL |
| P4 | 1.0000 | 0.0862 | FAIL |
| **P5** | **0.9996** | **0.0250** | **PASS estimate** |
| P6 | 0.0000 | 0.0626 | FAIL |
| P7 | 0.0000 | 0.0094 | FAIL because Total condition fails |

This estimate is not a replacement for the original sampler and seeds. It identifies the likely corrected outcome and defines what must be reproduced exactly.

## Corrected provisional tournament interpretation

P5 already satisfies the archived non-DD gates:

- RH1 PASS;
- RH3 PASS;
- RH4 PASS;
- RH5 N/A by specification;
- corrected RH2 PASS;
- gross-DD RH6 estimate PASS.

Therefore **P5 is the provisional corrected v002 winner**, pending one exact rerun of RH6 using the original block-bootstrap implementation and frozen seeds with gross DD.

P1–P3 do not justify their adaptive complexity:

- P1 improves Total but estimated gross RH6 fails;
- P2 fails RH1, RH5 and RH6;
- P3 improves Total but estimated gross RH6 fails;
- none beats a confirmed simple P5 under the frozen Occam rule.

P4 remains the strongest frozen Total-R policy but estimated gross RH6 still fails.

P6 and P7 reduce or reshape drawdown but fail RH1 and the Total component of RH6.

## P4b implication

P4b remains a valid post-tournament confirmation candidate, but its drawdown must be reported in both conventions:

- gross MaxDD: **12.436807R**;
- net MaxDD: **13.283629R**.

Its mechanism and post-selection status are unchanged. It must not retroactively replace the v002 winner.

## Required process correction

Before v003:

1. Run `v002.1 DD Convention Audit Replay`.
2. Gate 0: P0 must match N, Total, exits and **gross MaxDD = 14.415969R**.
3. Recompute RH2 and RH6(i) using gross DD with the original sampler and seeds.
4. Preserve net DD as a mandatory execution/prop-risk diagnostic.
5. Register the complete P0–P7 table, including negative results for P1–P3 and P6–P7.
6. Only after v002.1 is closed may P4b enter v003 confirmation.
