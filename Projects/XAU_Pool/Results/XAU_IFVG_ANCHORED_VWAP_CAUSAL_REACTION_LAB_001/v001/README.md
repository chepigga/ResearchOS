# XAU_IFVG_ANCHORED_VWAP_CAUSAL_REACTION_LAB_001 — v001

**Status:** `NO_INCREMENTAL_VWAP_EDGE`  
**Date:** 2026-08-22  
**Holdout opened:** `false`

## Canonical source

- Release: `https://github.com/chepigga/ResearchOS/releases/tag/ak47`
- Member: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- SHA-256 verified: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Internal rows retained: `1,080,929`
- Internal period: `2022-06-01 01:05` -> `2025-06-30 23:49`
- Historical holdout `>=2025-07-01` remains sealed.

## Frozen primary hypothesis

Primary inference was fixed before the canonical replay:

`VWAP_VOLUME + CENTER + FAILED_RECOVERY -> aligned confirmed iFVG -> forward response`

The control is ordinary `VWAP_VOLUME + FAR` iFVG. A same-anchor unweighted cumulative-mean centre is the placebo for the volume-weighting ablation.

## Canonical internal result

- Confirmed iFVG events: `188,859`
- Primary Confirmation N: `711`
- Confirmation primary EV, 1.5R probe: `+0.03785R`
- Confirmation primary EV, 2.0R probe: `+0.06932R`
- 1.5R selected-minus-FAR weekly lift: `+0.10627R`; 95% bootstrap CI `[-0.00457, +0.21965]`
- 2.0R selected-minus-FAR weekly lift: `+0.14255R`; 95% bootstrap CI `[+0.00920, +0.28512]`

The 1.5R incremental lift narrowly fails the preregistered positive-CI gate. More importantly, the same primary subset is negative in Discovery (`-0.04723R` at 1.5R), so the split-sign stability gate also fails.

## Directional detail

### Discovery

- BUY: N `403`, EV 1.5R `-0.04395R`, EV 2R `-0.05263R`
- SELL: N `381`, EV 1.5R `-0.05071R`, EV 2R `-0.04081R`
- Combined: N `784`, EV 1.5R `-0.04723R`

### Confirmation

- BUY: N `349`, EV 1.5R `-0.00076R`, EV 2R `+0.01213R`
- SELL: N `362`, EV 1.5R `+0.07508R`, EV 2R `+0.12446R`
- Combined: N `711`, EV 1.5R `+0.03785R`

The positive Confirmation result is therefore driven mainly by SELL. It is not temporally stable: 2024 SELL was strong, while 2025 H1 SELL reversed negative. This prevents promotion as a standalone edge.

## Frozen gates

- G0 volume proxy present: **PASS**
- G1 Confirmation power: **PASS**
- G2 Confirmation 1.5R EV positive: **PASS**
- G3 1.5R weekly clustered lift CI > 0: **FAIL**
- G4 Discovery and Confirmation primary 1.5R signs both positive: **FAIL**
- G5 Confirmation 2R EV non-negative: **PASS**
- G6 volume-weighted centre >= unweighted-anchor placebo: **PASS**

Frozen verdict rule therefore resolves to **`NO_INCREMENTAL_VWAP_EDGE`**. The holdout is not authorized to open.

## Implementation audit

The canonical CSV is semicolon-delimited. The committed v001 loader expected the default comma delimiter, so the canonical execution required implementation patch `v001a`: `pd.read_csv(..., sep=';')`. This changes parsing only; no event definition, clock, state threshold, ATR risk, target, split, bootstrap seed or gate was changed.

The local runtime lacked `pyarrow`, so the full event table was serialized as `events.csv.gz` rather than `events.parquet`. This is output-only and does not change any calculated result. Small frozen outputs (`audit.json`, `verdict.json`, `summary.csv`) are persisted here.

## Interpretation

This is not evidence that anchored VWAP is useless. It says the preregistered claim that `CENTER + FAILED_RECOVERY` provides a stable incremental 1.5R edge over ordinary iFVG did not survive the full internal split test.

The non-random clue worth preserving is the 2R lift and the Confirmation SELL asymmetry. Those may justify a separate diagnostic/regime LAB, but they must not be used to retroactively redefine LAB001 or open its sealed holdout.

No EA or live allocation is authorized from LAB001.
