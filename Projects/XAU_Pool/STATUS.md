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

- Raw input `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv` is not included; no SHA256 supplied.
- Intermediate and primary parquet outputs are not included.
- Fitted models/scalers and selected trade tables are not included.
- The specification header remains `DRAFT`; an independently timestamped preregistration freeze is not evidenced in this package.
- Scripts use absolute `/home/claude/` paths and lack a dependency lockfile.
- `step8_oos2.py` and `step9_control.py` retain copied OOS-1 labels/date text in headers/output; selection ranges in code are distinct but labels require repair before rerun.

## Next action

Create `XAU_POOL_PORTFOLIO_EXECUTION_LAB_002` with frozen inputs, portable paths, saved trade-level outputs, portfolio constraints, FTMO rules, and forward data after 2026-07-23.
