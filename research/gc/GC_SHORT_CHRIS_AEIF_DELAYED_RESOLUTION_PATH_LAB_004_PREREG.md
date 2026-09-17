# GC SHORT CHRIS/AEIF DELAYED RESOLUTION PATH LAB004 — PREREG

Date: 2026-09-17
Branch: gc-amp-feed-audit-001

## Purpose

Audit the causal path after the already-frozen LAB003 Chris/AEIF SHORT entry. This is **not** a new signal discovery and does not retune the LAB003 seed.

Frozen LAB003 mechanism:
`EXTREME BUY -> UPPER LOCATION -> WEAK UPWARD RESULT -> BEARISH CONFIRMATION <=2 M1 -> SHORT`

LAB003H showed mixed short-horizon behavior and a more delayed 10–30m realization. LAB004 asks whether the first 1/3/5/10 minutes after entry contain causal state information that separates later 15m/30m winners from losers.

## Frozen event population

Use the exact LAB003 event definition and regenerate it with the same source SHAs / code lineage. No threshold changes.

## Path features measured from entry forward

At 1m, 3m, 5m, 10m after entry, compute using only information available by that checkpoint:
- signed SHORT return in ATR units: `(entry - close_checkpoint)/seed_ATR`
- MFE to checkpoint in ATR: `(entry - min_low)/seed_ATR`
- MAE to checkpoint in ATR: `(max_high - entry)/seed_ATR`
- close position within the checkpoint path range
- fraction of checkpoint M1 bars that close bearish
- cumulative body direction in ATR units
- distance from seed high and seed close in ATR

Targets are descriptive future outcomes from original frozen entry:
- `winner15 = fwd_15m_atr > 0`
- `winner30 = fwd_30m_atr > 0`
- continuous `fwd_15m_atr` and `fwd_30m_atr`

## Analysis

For each checkpoint (1/3/5/10m), separately by feed and period:
1. compute univariate directionless AUC for winner15/winner30 where class counts permit;
2. compare medians for winners vs losers;
3. compute Spearman correlation with fwd15/fwd30;
4. no multivariate model, no threshold sweep, no trading overlay.

Primary question:
Does any **same causal path feature family** show consistent directional separation across Rithmic VALID and AMP VALID and remain directionally coherent on FULL?

## Evidence gate

Call `HISTORICAL_DELAYED_RESOLUTION_PATH_SIGNAL_NOT_OOS` only if at least one feature/checkpoint combination satisfies all:
- valid sample >= 8 events/feed;
- Rithmic VALID directionless AUC >= 0.65 for winner15 or winner30;
- AMP VALID directionless AUC >= 0.65 for the same target;
- same oriented direction on both feeds;
- FULL oriented direction does not flip on either feed;
- descriptive median separation has the same direction on both VALID feeds.

Otherwise status:
`HISTORICAL_DELAYED_RESOLUTION_PATH_INCONCLUSIVE_NOT_OOS`.

This gate does **not** create a production filter. A passing feature would require a separately preregistered walk-forward decision-gate LAB005 before any execution use.

## Prohibitions

- no LAB003 seed changes;
- no post-hoc checkpoint selection for trading;
- no threshold optimization;
- no XAU transfer/execution tuning;
- no promotion of LAB003 based solely on descriptive path results.
