# XAU_POST_BREAK_BEHAVIORAL_SEQUENCE_AND_ACCEPTANCE_LAB_008 — implementation freeze

Frozen before canonical outcome replay.

- local runner: `run_lab008.py`
- SHA-256: `e966be07c26944554cb33f79c15ab17d3612f246426d317a0c8708045b304c98`
- preregistered spec commit precedes this freeze
- canonical outcome replay must use this exact script hash
- holdout remains sealed

Implementation-only performance patch before any outcomes existed:
- cached dynamic level arrays;
- replaced repeated DataFrame filtering for M5/M15 with searchsorted array slices;
- replaced repeated future-label DataFrame/array reconstruction with a Numba barrier function.

No break rule, feature definition, clock, target, model, gate, or holdout boundary changed.