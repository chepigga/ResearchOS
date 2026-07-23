# FXArena Exit Tournament v003-lite — Core Confirmation Report

**Date:** 2026-07-23  
**Status:** **CORE HOLD / FORMAL PASS NOT CLAIMED**  
**PRIMARY:** `P4b_PRIMARY`  
**SECONDARY:** `P5_SOLO`  
**Deploy tests:** `R1 Dukascopy` and `R2 forward` — **DEPLOY-TESTS DEFERRED** until the pre-EA stage.

## Executive verdict

The available-data session confirms the **economic mechanism** of P4b, but cannot issue a formal PASS because two frozen inputs needed for exact gate execution are absent from the active runtime:

1. the original release bootstrap sampler/seed implementation;
2. raw M1 spread-path data required to replay spread multipliers x1.25/x1.5/x2.0.

This is a **technical HOLD**, not a failed market hypothesis and not permission to tune the candidate.

What is already decided:

- **Gate 0 PASS:** P0 gross MaxDD = **14.415969R**, matching canonical 14.416 ±0.001; net MaxDD is separately 15.827253R.
- **P4b passes RH1–RH3.**
- **P4b passes RH5 permutation-200 strongly.**
- **P4b passes RH8 dedup on every registered subset.**
- **P5_SOLO fails RH7:** commission 9 points + 0.05R slip on its changed exits already reduces total below RH1 before any spread increase.
- P4b exceeds P5 by **+272.36R / +13.73%**, so the v002 Occam tie rule is not triggered.
- The literal absolute-DD RH6 formulation and the legacy paired-DD formulation give different answers under the deterministic audit sampler. This must be resolved with the exact frozen sampler rather than silently choosing the favorable interpretation.

## 1. Gate 0 — canonical DD convention

Gate metric: **gross equity MaxDD**. Net equity MaxDD is diagnostic only.

| Check | Result |
|---|---:|
| N | 3535 |
| Signal-by-signal gross parity | 100% at 1e-6 |
| Exit-label parity | 100% |
| Net total | +1848.874811R |
| Gross MaxDD | **14.415969R** |
| Net MaxDD | 15.827253R |
| Gate 0 | **PASS** |

All following RH2 and RH6 DD calculations use gross outcomes only.

## 2. Core economics

| Policy | N | Net total | EV | Gross DD | Net DD | PF | Negative months | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | 3535 | +1848.87R | 0.5230 | 14.416R | 15.827R | 2.861 | 1 | -0.22R |
| P4 | 3535 | +2134.36R | 0.6038 | 14.416R | 15.827R | 3.121 | 0 | +2.08R |
| P5_SOLO | 3535 | +1984.15R | 0.5613 | 13.572R | 15.812R | 4.310 | 0 | +4.54R |
| **P4b_PRIMARY** | **3535** | **+2256.51R** | **0.6383** | **12.437R** | **13.284R** | **4.297** | **0** | **+4.59R** |

| Candidate | RH1 total ≥1904.3361 | RH2 gross DD ≤14.916 | RH3 calendar |
|---|---|---|---|
| P5_SOLO | PASS | PASS | PASS |
| P4b_PRIMARY | PASS | PASS | PASS |

## 3. RH5 — permutation-200

Frozen test: shuffle `tb_flag` inside each month, preserve each month's flagged count, route shuffled-flag episodes to the frozen P4/P5 outcomes and compare with the best global branch P4.

| Metric | Result |
|---|---:|
| Observed P4b total | +2256.51R |
| Best global branch P4 | +2134.36R |
| Observed router advantage | **+122.16R** |
| Null mean advantage | -88.60R |
| Null p95 advantage | -60.24R |
| Empirical one-sided p | 0.00498 |
| RH5 | **PASS** |

The null moves below the best global branch. The edge is tied to the correct TB/non-TB assignment rather than the 36% allocation rate alone.

## 4. RH6 — bootstrap audit

The frozen test requires the **original release sampler and seeds**. They are not present in the supplied v002 output or P4b research archives.

A deterministic forensic audit was run only to expose sensitivity: moving blocks 20 trades, 5000 iterations, seed 20260723, paired P0/candidate indices.

| Candidate | P(total>P0) | P(gross DD>14.916), literal absolute | P(gross DD>P0-resample+0.5), legacy paired |
|---|---:|---:|---:|
| P5_SOLO | 0.9996 | **0.0504** | 0.0250 |
| P4b_PRIMARY | 1.0000 | **0.0732** | 0.0234 |

Under the literal absolute-DD wording both estimates exceed 0.05; under the historical paired-delta convention both pass. These definitions are not interchangeable.

**RH6 formal status: BLOCKED / NOT SCORED.**

## 5. RH7 — universal execution-cost stress

The frozen trade streams permit exact recalculation of round-turn commission 6/9/12 points and BE execution slip on changed P5 exits.

Changed exits:

- P5_SOLO: **1324**;
- P4b non-TB P5 branch: **1077**.

At commission 9 points + 0.05R slip, before adding any spread multiplier:

| Candidate | Net total | Gross DD after slip | RH1 | RH2 |
|---|---:|---:|---|---|
| P5_SOLO | **1792.89R** | 14.222R | **FAIL** | PASS |
| P4b_PRIMARY | **2077.60R** | 12.487R | **PASS** | PASS |

P5 fails the central RH7 gate **even before spread x1.5 is applied**. This is a genuine secondary-candidate falsification.

Spread participates in M1 entry/exit path and trigger logic. Exact multipliers cannot be reconstructed from final trade rows without the raw per-minute spread series.

An explicitly labelled additive-cost proxy gives this central x1.5 / commission 9 / slip 0.05 headroom:

- P5: no spread headroom because RH1 already fails.
- P4b: RH1 and RH2 survive while baseline average spread is **≤8.312 points** in the proxy.
- 5-point proxy: P4b +1973.37R, gross DD 12.840R.
- 8-point proxy: P4b +1910.84R, gross DD 13.051R.
- 10 points: RH1 fails.

**RH7 PRIMARY formal status: BLOCKED pending raw M1 spread replay.**  
**RH7 SECONDARY status: FAIL.**

## 6. RH8 — dedup robustness

| Subset | Candidate | N | Net total | EV | Gross DD |
|---|---|---:|---:|---:|---:|
| ALL | P0 | 3535 | +1848.87R | 0.5230 | 14.416R |
| ALL | P5_SOLO | 3535 | +1984.15R | 0.5613 | 13.572R |
| ALL | P4b_PRIMARY | 3535 | +2256.51R | 0.6383 | 12.437R |
| FIRST_EPISODE_PER_LEVEL | P0 | 2342 | +1243.54R | 0.5310 | 11.024R |
| FIRST_EPISODE_PER_LEVEL | P5_SOLO | 2342 | +1333.11R | 0.5692 | 10.572R |
| FIRST_EPISODE_PER_LEVEL | P4b_PRIMARY | 2342 | +1522.81R | 0.6502 | 8.543R |
| UNIQUE_ENTRY_CLUSTER | P0 | 2783 | +1441.28R | 0.5179 | 11.486R |
| UNIQUE_ENTRY_CLUSTER | P5_SOLO | 2783 | +1540.68R | 0.5536 | 8.437R |
| UNIQUE_ENTRY_CLUSTER | P4b_PRIMARY | 2783 | +1755.56R | 0.6308 | 8.437R |
| UNIQUE_DECISION_TIME_DIR | P0 | 2109 | +1157.36R | 0.5488 | 8.106R |
| UNIQUE_DECISION_TIME_DIR | P5_SOLO | 2109 | +1216.62R | 0.5769 | 5.543R |
| UNIQUE_DECISION_TIME_DIR | P4b_PRIMARY | 2109 | +1391.29R | 0.6597 | 6.543R |

**RH8: PASS.**

## 7. RH4 reverse chronology

| Candidate | Forward gross DD | Reverse gross DD | Degradation |
|---|---:|---:|---:|
| P5_SOLO | 13.572R | 13.572R | 0.000000% |
| P4b_PRIMARY | 12.437R | 12.437R | 0.000000% |

**RH4 economics diagnostic: PASS.**

## 8. Full P0–P7 registry debt

| Policy | Net total | EV | Gross DD | Net DD | RH1 | RH2 | RH3 |
|---|---:|---:|---:|---:|---|---|---|
| P0 | +1848.87R | 0.5230 | 14.416R | 15.827R | BASELINE | BASELINE | BASELINE |
| P1 | +1996.79R | 0.5649 | 14.416R | 15.827R | PASS | PASS | PASS |
| P2 | +1829.52R | 0.5175 | 14.790R | 16.201R | FAIL | PASS | PASS |
| P3 | +1988.10R | 0.5624 | 14.790R | 16.201R | PASS | PASS | PASS |
| P4 | +2134.36R | 0.6038 | 14.416R | 15.827R | PASS | PASS | PASS |
| P5 | +1984.15R | 0.5613 | 13.572R | 15.812R | PASS | PASS | PASS |
| P6 | +1500.27R | 0.4244 | 12.746R | 14.085R | FAIL | PASS | PASS |
| P7 | +1643.97R | 0.4651 | 13.853R | 15.961R | FAIL | PASS | PASS |

## 9. Core verdict

### PRIMARY — P4b

- Gate 0: PASS
- RH1: PASS
- RH2: PASS
- RH3: PASS
- RH4 diagnostic: PASS
- RH5: PASS
- RH6: **NOT FORMALLY SCORED — frozen sampler/definition unavailable**
- RH7: **NOT FORMALLY SCORED — raw spread-path replay unavailable**
- RH8: PASS

**Verdict: CORE HOLD / STRONG CONFIRMATION, NOT FORMAL PASS.**

### SECONDARY — P5_SOLO

**Verdict: FAIL RH7.**

### F8

F8 is **not activated** because P4b has not failed a fully executable gate. Declaring F8 would confuse an input blocker with market falsification.

## 10. Required closure

1. replay RH6 with the exact frozen release sampler/seeds and explicitly resolve the absolute-versus-paired DD definition;
2. replay RH7 spread multipliers on raw M1 spread paths.

R1 Dukascopy and R2 forward remain **DEPLOY-TESTS DEFERRED**. No parameter tuning is authorized, and Entry Lab / Exit v004 must not be frozen before core closure.
