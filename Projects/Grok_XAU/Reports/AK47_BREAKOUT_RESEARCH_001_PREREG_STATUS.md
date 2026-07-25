# AK47_BREAKOUT_RESEARCH_001 — preregistration status

**Date:** 2026-07-25  
**Status:** `BLOCKED_WAITING_FOR_ELIGIBLE_M1_DATA`  
**Formal verdict:** NOT OPENED

## Base stage

- M5 reconstruction is prohibited for verdicts.
- Eligible input: XAUUSD M1/ticks with actual spread.
- Search family: `1,512` candidates (`756` each for M15 and H1).
- Base grid, 6 rolling walk-forward splits and 250 family-wise price permutations remain unchanged.
- Base stage must return `GO`, `REGIME`, or `NO-GO` before any ML stage.

## ML addendum

- ML replaces the manual regime stage as the primary post-geometry research path.
- Manual ADX/ATR/bias filters remain only as Baseline B.
- ML is forbidden after base `NO-GO`.
- One frozen RandomForest only; no hyperparameter search.
- Rolling train: 12 months; test: next month.
- Selection: trailing `q0.96` over final 90 training days.
- Primary OOS months: `2023-06..2026-05`.
- Label permutations: `250`.
- `ML-GO` requires aggregate OOS uplift of at least `+0.10R` versus both simple geometry and manual comparator, N≥90, MaxDD≤10%, ≤1 negative OOS month with trades, and permutation pass.
- ONNX work is forbidden unless `ML-GO` is opened.

## Data blocker

Required files:

```text
XAUUSD_M1_20220601_20260723_TESTER_FULL.csv
XAUUSD_M1_20220601_20260723_TESTER_META.csv
```

Generate with `Every tick based on real ticks`. The formal run starts only after the M1 audit passes with no duplicate timestamps, invalid OHLC or non-positive spread rows.
