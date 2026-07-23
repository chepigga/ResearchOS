# FXArena Research v1.2 — Exit Policy Tournament v002 / P4b Research v001

**Date:** 2026-07-23  
**Branch:** `research`  
**Status:** `RESEARCH / FROZEN CONFIRMATION REQUIRED`  
**Live baseline:** unchanged  
**EA / production status:** `NO-GO`

## Scope

This checkpoint records the completed frozen `Exit Policy Tournament v002` and the post-tournament `P4 TB Deep Dive / P4b Research v001`.

The tournament was executed once against the pinned GEO* fixture. No tournament policy passed every frozen gate. P4 produced the strongest economics but failed RH2 and RH6. The follow-up analysis isolated the structural source of P4 drawdown and registered one simple composite candidate for confirmation.

## P0 canonical replay

- Episodes replayed: **3535 / 3535**.
- Gross parity at `1e-6`: **100%**.
- Exit-label parity: **100%**.
- Median absolute net difference: **1.54e-08R**.
- Fixture total: **+1848.8748066R**.
- Recalculated total: **+1848.8748114R**.

## Frozen tournament result

| Policy | Total R | EV | MaxDD | PF | Negative months | Formal verdict |
|---|---:|---:|---:|---:|---:|---|
| P0 | +1848.87 | +0.5230 | 15.827R | 2.861 | 1 | BASELINE |
| P1 | +1996.79 | +0.5649 | 15.827R | 3.033 | 1 | FAIL |
| P2 | +1829.52 | +0.5175 | 16.201R | 2.958 | 1 | FAIL |
| P3 | +1988.10 | +0.5624 | 16.201R | 3.143 | 1 | FAIL |
| **P4** | **+2134.36** | **+0.6038** | **15.827R** | **3.121** | **0** | **FAIL: RH2, RH6** |
| P5 | +1984.15 | +0.5613 | 15.812R | 4.310 | 0 | FAIL: RH2 |
| P6 | +1500.27 | +0.4244 | 14.085R | 2.772 | 1 | FAIL |
| P7 | +1643.97 | +0.4651 | 15.961R | 4.082 | 0 | FAIL |

**Tournament verdict:** no P1-P7 policy is promoted.

## P4b frozen confirmation candidate

```text
P4b_PRIMARY:
    tb_flag == true  -> frozen P4
    tb_flag == false -> frozen P5
```

Observed full-sample result:

- N: **3535**.
- Total: **+2256.51R**.
- EV: **+0.6383R/trade**.
- MaxDD: **13.284R**.
- PF: **4.297**.
- Negative months: **0 / 42**.
- Worst month: **+4.59R**.
- Improvement versus P4: **+122.16R** and **-16.1% MaxDD**.
- Improvement versus P0: **+407.64R**.

## Structural finding

P4 changes only `tb_flag=True` trades. The main P4 drawdown cluster was driven predominantly by `tb_flag=False` trades, so further TB target tuning cannot directly repair RH2. P5 is the pre-existing frozen policy that improves the non-TB branch across all years, both chronological halves, all available six-month blocks and deduplicated subsets.

## Robustness and execution sensitivity

- Estimated paired moving-block bootstrap, 5000 iterations: `p_total_good = 100%`, `p_dd_bad = 3.66%` versus P0.
- Exact tournament RH6 is **not claimed**, because the original sampler/indices were not present in the supplied output archive.
- P4b remains better than P4 under additional cost shocks up to approximately **+0.113R per modified P5 exit**.
- Frozen forward kill threshold: disable the P5 fallback if realized incremental execution drag exceeds **0.10R per modified exit**.

## Governance verdict

- `Exit Policy Tournament v002`: **COMPLETED / FORMAL FAIL — NO WINNER**.
- `P4b Research v001`: **EXPLORATORY GO FOR FROZEN CONFIRMATION**.
- No EA implementation, production promotion or modification of the live ContPrimary baseline is authorized.
- Next required lab: `Exit Policy Tournament v003 — P4b Confirmation`, one primary candidate, no post-registration tuning.

## Supplied source archives

The exact supplied archives are identified by SHA256 in `SOURCE_ARTIFACTS_SHA256.csv`. Extracted text reports and summary tables are committed in this directory. Large binary matrices, trade streams, model weights and bootstrap samples remain inside the source archives and must be preserved byte-for-byte for formal reproduction.
