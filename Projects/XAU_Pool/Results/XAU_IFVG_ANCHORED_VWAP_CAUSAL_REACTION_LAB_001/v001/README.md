# XAU_IFVG_ANCHORED_VWAP_CAUSAL_REACTION_LAB_001 — v001

**Status:** `PREREGISTERED / BLOCKED_CANONICAL_RUNTIME`  
**Date:** 2026-08-22

## What is complete

- Frozen causal specification is committed before any canonical outcome replay.
- Frozen Python implementation is committed.
- Local synthetic smoke test passed compilation and event/state/outcome execution.
- Primary inference is restricted to `VWAP_VOLUME + CENTER + FAILED_RECOVERY`.
- Outer VWAP bands are diagnostic proxies only; they are not claimed to reproduce the protected podcast indicator.
- A same-anchor unweighted-mean placebo is included to test whether volume weighting adds anything.
- Historical holdout `>= 2025-07-01` is not authorized for internal tuning and has not been used for a reported verdict.

## Why there is no numeric verdict yet

The canonical XAU source is an external GitHub release asset rather than a repository file. The current connected runtime can read/write the ResearchOS repository but has not exposed the release asset bytes to the analysis runtime. A GitHub Actions workflow was added to download the `ak47` release asset, verify the canonical decompressed CSV SHA-256, and run the internal lab. Connector-authored `push` and traceable PR attempts did not surface an Actions run/result in the current session.

No alternate XAU feed was substituted, because doing so would change the broker clock, Bid/Ask lineage, volume proxy and therefore the preregistered hypothesis.

## Canonical input expected

- `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`

## Next executable action

Expose/download the canonical release asset to a runtime that can execute the committed script, then run **without** `--open-holdout`. Only if all frozen internal gates pass may the sealed holdout be opened once.

No EA or live allocation is authorized from this preregistration alone.
