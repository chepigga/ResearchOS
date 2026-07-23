# FXArena Research v1.2 — Exit Policy Tournament v002 / DD Audit / P4b Research v001

**Date:** 2026-07-23  
**Branch:** `research`  
**Status:** `V002 VERDICT INVALIDATED — DD CONVENTION AUDIT REQUIRED`  
**Live baseline:** unchanged  
**EA / production status:** `NO-GO`

## Critical erratum

The v002 output calculated Total/EV from net R and MaxDD from net R, while the frozen pinned GEO* MaxDD `14.416R` and RH2 ceiling `14.916R` were defined by the gross-R equity curve.

Exact P0 replay on the same 3,535 trades:

- gross MaxDD: **14.415969R** — canonical parity;
- net MaxDD: **15.827253R** — diagnostic used by the archived tournament report.

Therefore the archived RH2 verdicts and RH6(i) DD probabilities are not formally comparable with the frozen specification. The previous statement “no P1–P7 winner” is withdrawn pending v002.1 audit replay.

## Corrected deterministic RH2

Using canonical gross DD, all P1–P7 policies pass RH2. Most importantly:

- P4 gross DD: **14.415969R** — RH2 PASS, not FAIL;
- P5 gross DD: **13.571548R** — RH2 PASS, not FAIL;
- P4b gross DD: **12.436807R**; net DD remains **13.283629R**.

## Provisional corrected tournament result

P5 already has:

- Total: **+1984.15R**;
- EV: **+0.5613R**;
- PF: **4.310**;
- 0 negative months;
- worst month: **+4.54R**;
- RH1 PASS;
- corrected RH2 PASS;
- RH3 PASS;
- RH4 PASS;
- RH5 N/A.

A 5,000-iteration forensic gross-DD block-bootstrap estimate gives:

- `p_total_good = 0.9996`;
- `p_dd_bad = 0.0250`;
- estimated RH6 PASS.

Thus **P5 is the provisional corrected v002 winner**, subject to exact RH6 replay using the original sampler and frozen seeds.

P1–P3 remain negative complexity results; P4 remains the strongest Total-R frozen policy but its estimated gross RH6 still fails. Full details are in `P0_P7_FALSIFICATION_CATALOG.md`.

## P4b status

P4b remains a strong post-tournament candidate:

```text
P4b_PRIMARY:
    tb_flag == true  -> frozen P4
    tb_flag == false -> frozen P5
```

Observed metrics:

- Total net: **+2256.51R**;
- EV net: **+0.6383R/trade**;
- gross MaxDD: **12.436807R**;
- net MaxDD: **13.283629R**;
- PF: **4.297**;
- negative months: **0 / 42**.

It cannot retroactively replace the v002 winner because it was selected post hoc. It remains `EXPLORATORY GO FOR FROZEN CONFIRMATION` only.

## Required order of work

1. `Exit Policy Tournament v002.1 — DD Convention Audit Replay`.
2. Gate 0: P0 exact parity including gross MaxDD `14.415969R`.
3. Exact RH2/RH6 recomputation with original sampler and seeds.
4. Register complete P0–P7 falsification catalogue.
5. Finalize the remaining reviewer amendments to v003.
6. Freeze and run one-candidate P4b v003 confirmation.

The v003 document currently committed is a **draft**, not a preregistration, because the review message announced three additions but only two concrete amendments were included in the received text.
