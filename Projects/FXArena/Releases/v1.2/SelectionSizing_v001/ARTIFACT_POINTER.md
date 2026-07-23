# Selection & Sizing Lab v001 — Complete Artifact Pointer

The repository stores the governed report, final verdict, frozen specification, threshold/tercile tables, canonical sampler source and SHA256 manifest.

The complete immutable execution artifact also contains:

- all candidate trade files (`.csv.gz`);
- `SA4_permutation200.csv`;
- `SA5_paired_moving_block_5000.csv`;
- total and gross-DD threshold plots;
- full run source and run log.

## GitHub Actions provenance

- Repository: `chepigga/ResearchOS`
- Execution branch: `agent/selection-sizing-v001`
- Draft PR: `#2`
- Workflow: `FXArena Selection Sizing v001`
- Successful run ID: `30043178348`
- Workflow artifact ID: `8578059385`
- Workflow artifact name: `FXArena-SelectionSizing-v001-output`
- Artifact digest: `sha256:ca6b678f144ff01f6ad910fb93a3fe67d48a0b19e3b3b4600655eaa1dd6906ec`
- Frozen sampler: paired non-circular moving-block, block 20, shared indices, 5000 iterations
- Seeds: SA4 `2026072304`; SA5 `2026072305`; reserved SB5 base `2026072310`

The output-level `MANIFEST_SHA256.csv` is the authoritative file inventory. Binary files are not reconstructed from summary statistics.
