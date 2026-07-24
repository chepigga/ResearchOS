# New-session bootstrap prompt

Continue the FXArena project from GitHub checkpoint `Projects/FXArena/Checkpoints/Continuation_v1.2_2026-07-24`.

Before doing research:

1. Read `README_CONTINUE_HERE.md` and `Docs/PROJECT_STATE_2026-07-24.md`.
2. Download and reconstruct the binary checkpoint using `BINARY_BACKUP.md`.
3. Run `python Tools/reconstruct_chunked_files.py`.
4. Verify every artifact with `python Tools/verify_manifest.py`.
5. Treat GEO*-TRAILING + P0 as the only live/deploy canonical baseline.
6. Preserve F9, F10, F11 and final PC5-r closure.
7. Do not use final-episode fields as causal D3 features.
8. Do not write EA code until a new frozen hypothesis passes causal, robustness and execution validation.

Current priority: August/live forward benchmark of ContPrimary using measured execution costs and exact provenance. Any new hypothesis requires genuinely new causal information and a frozen specification before looking at results.
