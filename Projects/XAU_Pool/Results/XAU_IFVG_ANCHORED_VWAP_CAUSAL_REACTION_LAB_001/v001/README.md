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

## Canonical source — confirmed

The user explicitly confirmed the canonical release location on 2026-08-22:

- Release: `https://github.com/chepigga/ResearchOS/releases/tag/ak47`
- Expected member: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- Expected SHA-256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`

This removes ambiguity about which source dataset is canonical.

## Why there is still no numeric verdict

The canonical XAU source is a GitHub release asset rather than a repository file. The current connected GitHub tool can read/write repository contents, commits, PRs and workflow artifacts, but its fetch action does not expose release-tag assets. Direct release fetch attempts returned unsupported-endpoint errors.

A frozen GitHub Actions runner was added that uses `gh release download ak47`, checks the decompressed CSV SHA-256 and runs the LAB without `--open-holdout`. Connector-authored push, PR and issue-comment trigger attempts did not surface an Actions run/result in this session.

No alternate XAU feed was substituted, because doing so would change broker clock, Bid/Ask lineage and tick-volume proxy and therefore change the preregistered hypothesis.

## Next executable action

Run the committed script against the confirmed release asset without `--open-holdout`. Only if all frozen internal gates pass may the sealed holdout be opened once.

No EA or live allocation is authorized from this preregistration alone.
