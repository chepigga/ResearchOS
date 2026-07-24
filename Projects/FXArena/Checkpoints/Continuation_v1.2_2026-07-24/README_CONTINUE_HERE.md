# FXArena Continuation Checkpoint v1.2

This directory is the recovery point for continuing FXArena without access to the original chat runtime.

## Start here

1. Read `Docs/PROJECT_STATE_2026-07-24.md`.
2. Read `Docs/ARTIFACT_DEPENDENCY_MAP.md`.
3. Download the three binary checkpoint parts listed in `BINARY_BACKUP.md`.
4. Concatenate them in order:

```bash
cat FXArena_ContinuationCheckpoint_v1.2.zip.part00 \
    FXArena_ContinuationCheckpoint_v1.2.zip.part01 \
    FXArena_ContinuationCheckpoint_v1.2.zip.part02 \
  > FXArena_ContinuationCheckpoint_v1.2.zip
```

5. Verify the archive SHA256:

```text
12e143be4e88a1f936311b2981e98567ccdbc9069c896bf8b6589c6a3137565a
```

6. Extract the ZIP, run `python Tools/reconstruct_chunked_files.py`, then `python Tools/verify_manifest.py`.
7. Use the canonical live reference inside `Releases/FXArena_Closure_v001_1_output.zip`: `trades_GEOstar_TRAILING_PINNED.csv.gz`.

## Canonical deployment state

- Selector: GEO*-TRAILING q0.96 / 90d.
- Entry: market at D3+60s.
- Exit: P0 TP2 / TO120.
- REV leg: excluded under F11.
- ContPrimary: unchanged.
- Measured platform commission basis: 5pt RT; archived canonical reference also preserves the historical 6pt basis.

## Critical governance

- Gross equity MaxDD is the gate metric; net MaxDD is diagnostic and must be labelled.
- Paired moving-block bootstrap uses shared indices, block 20, at least 5000 iterations, with seed and sampler source published.
- MONTHLY is research-only; TRAILING is live/E-exam/kill-metric only.
- Final-episode values are not causal D3 features.
- No EA implementation before a strategy passes its frozen confirmation and execution court.
- Do not reopen F9, F10, F11, P4b/P4c/PC5-r on the same data.

## Existing immutable releases

The detailed laboratory releases remain under `Projects/FXArena/Releases/v1.2/`. The binary backup additionally contains all result ZIPs, frozen specs, replay inputs, manifests and recovery tools.
