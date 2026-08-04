# XAU_Pool Import Provenance — 2026-08-04

- **Source attachment:** `files.zip`
- **Source ZIP SHA256:** `1fca1ea35c23185350c44eac913b571be20cc45cdc9fba83b1cce142b2e82e4c`
- **Nested archive:** `ResearchOS_commit_2026-08-03.tar.gz`
- **Nested archive SHA256:** `7b6f32dbdcab400c330d63670e1ca90d5d6113625ce58d01fc8ad2cfbf6224e2`
- **Imported project:** `XAU_Pool`
- **Import date:** 2026-08-04

## Imported from package

- four XAU_POOL_SELECTION specification files;
- one XAU_POOL_SELECTION report;
- nine Python reproduction scripts;
- source-package README retained in Archive.

## Added during governed import

- project README, STATUS, BACKLOG and CHANGELOG;
- directory READMEs;
- results lineage README;
- ADR-001;
- checksums and this provenance record;
- root Research Register, Lessons Learned, Master Backlog, Decisions and Changelog updates.

## Explicitly excluded

The package also contained:

- `Projects/FXArena/Reports/ExitPolicyTournament_v002_Report.md`;
- `Projects/FXArena/Specs/FXArena_SPEC_ExitTP3_v003.md`;
- mixed FXArena/AK47 registry notes.

These were not placed inside XAU_Pool because the user requested an isolated new XAU_Pool project. No claim is made here about whether those FXArena files should be imported separately.

## Preservation rule

Supplied XAU specification, report and Python files were moved to the new project path without changing their contents. Known inconsistencies are documented in `STATUS.md` rather than silently repaired.

## Superseding source package received 2026-08-04

- **Attachment:** `files (2).zip`
- **ZIP SHA256:** `9ef9d9258d7b81044b15f90844076c1ad37bac8e20c1193cbe460f1f9e2e8a2f`
- **Nested TAR.GZ SHA256:** `cc02512836c8ea84715feb2d995751fc9ae9e46f0cc61079f7139a6b6e98abef`

This package added four result/model artifacts, updated all nine scripts and changed the main specification status to frozen. The supplied CSV manifest is retained in Archive. Its README row is stale: it declares 3,213 bytes and the old SHA, while the actual updated README is 4,747 bytes with SHA256 `e42767cb77ecc95c27e00596a862810cb4b57ceede0fffb7739943a206ea856d`. All other listed payload hashes match after normalizing CSV CRLF line endings.
