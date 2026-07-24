# FXArena Closure v001.1 — Monthly vs Trailing Canonicalization

## Verdict

**PARTIAL PASS / P4b TRANSFER STOP-ALARM**

- Control A monthly: **PASS** — 3535 ordered signals, +1848.874807R, gross MaxDD 14.415969R.
- Control B trailing q0.96/90d: **PASS** — 3515 ordered signals, +1889.613320R, gross MaxDD 14.415969R.
- `trades_GEOstar_TRAILING_PINNED` is now the official live P0 reference.
- P4b transfer gates C1–C4 were **not executed** because the frozen P4b archive supplies causal `tb_flag` for only 2893/3515 trailing episodes. The missing 622 episodes are all trailing-only.
- `trades_P4b_TRAILING_PINNED` was not created. P4b deployment remains blocked pending a new frozen flag-replay session using the original P4 generator.

## Controls

| Control | N | Total R | Gross MaxDD | Ordered parity | Result |
|---|---:|---:|---:|---|---|
| A: monthly | 3535 | +1848.874807 | 14.415969 | True | PASS |
| B: trailing | 3515 | +1889.613320 | 14.415969 | True | PASS |

## Set relationship

- Intersection: **2893**
- Monthly-only: **642**
- Trailing-only: **622**
- Symmetric difference: **1264**
- Jaccard overlap: **69.59%**

This confirms that monthly and trailing are two different causal selection mechanisms, not two labels for the same fixture.

## Canonical registry rows

| Key | N | Total R | Gross MaxDD | Use |
|---|---:|---:|---:|---|
| GEO*-MONTHLY | 3535 | +1848.874807 | 14.415969 | research comparisons only |
| GEO*-TRAILING | 3515 | +1889.613320 | 14.415969 | live/E-exam/kill metrics only |

Mixing the two baselines is a registry defect.

## P4b transfer blocker

The P4b monthly fixture contains 3535 `tb_flag` values. On the trailing set:

- covered by the frozen P4b fixture: **2893**;
- missing frozen flag: **622**;
- coverage: **82.30%**.

The missing rows cannot be assigned `tb_flag=False`, inferred from outcome/MFE, or refitted from this sample. Any such action would change the frozen P4b policy. Therefore C1–C4 and the P4b trailing pin are stopped before economics.

A diagnostic intersection-only table is included, but it is explicitly non-promotable.

## Bootstrap reservation

Registry v3 law is preserved: paired moving-block, shared indices, block 20, 5000 iterations, seed `2026072405`. It was not executed because the candidate pair is incomplete.

## Governance

- ContPrimary untouched.
- q0.96 and 90-day window unchanged.
- P4b rules unchanged.
- No threshold, window, flag, or exit tuning.
- F1–F10 remain active.
