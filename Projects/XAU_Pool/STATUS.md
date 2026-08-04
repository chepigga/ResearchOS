# XAU_Pool Status

- **Project:** XAU_Pool
- **Updated:** 2026-08-04
- **Lifecycle status:** CANDIDATE
- **Laboratory:** XAU_POOL_SELECTION_LAB_001
- **Version:** v001
- **Instrument:** XAUUSD
- **Period:** 2022-06-01 — 2026-07-23
- **Formal verdict:** PASS according to supplied report
- **Practical verdict:** selection layer works on the studied pool; not yet a deployable trading system
- **Canonical impact:** none; no canonical XAU_Pool baseline exists yet

## Primary evidence

| Split | Lift | Excess level | Raw EV selected | N | Positive months |
|---|---:|---:|---:|---:|---:|
| IS | +0.3591R | +0.3294R | +0.2527R | 3,436 | 16/16 |
| OOS-1 | +0.3466R | +0.3240R | +0.2535R | 2,260 | 10/10 |
| OOS-2 | +0.3959R | +0.3643R | +0.3276R | 2,437 | 11/11 |
| CONTROL | +0.3539R | +0.3363R | +0.2261R | 1,506 | 7/7 |

Permutation: `z=23.4`; 0 of 37 completed shuffles reached the real result. The planned run was 40 shuffles and stopped at 37 due to runtime limits.

## Evidence gaps

- Raw input `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv` is external in GitHub release `ak47`; its SHA256 is not supplied in this package.
- Selected trade-level tables and complete execution logs are not included.
- A dependency/environment lockfile is still absent.
- `step8_oos2.py` and `step9_control.py` retain copied OOS-1 labels in several print statements; selection date ranges in code are distinct, but labels require a code-only repair.

## Evidence added 2026-08-04

- Specification status changed from `DRAFT` to `FROZEN 2026-08-03` in the supplied source.
- `pool_excess.parquet` — 266,297 candidates with R/excess labels.
- `baseline.parquet` — month × direction × timeframe drift baseline.
- `permutation_37_shuffles.jsonl` — 37 raw permutation records.
- `weights_schedule_XAU_POOL_v001.pkl` — 48 WF windows, 36 features, coefficients/intercept/mean/scale per window, according to the supplied package description.
- All nine scripts now use `$XAU_DATA` rather than `/home/claude/`.
- Permutation resume now uses deterministic seed `2026 + iteration`.

## Next action

Add the raw-data SHA256 and dependency lock, repair OOS labels without logic changes, then create `XAU_POOL_PORTFOLIO_EXECUTION_LAB_002` with portfolio constraints, FTMO rules and forward data after 2026-07-23.
