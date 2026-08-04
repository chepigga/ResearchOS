# XAU_POOL_SELECTION_LAB_001 v001 — Results

- **Created by:** supplied research package; original runtime not available here
- **Imported:** 2026-08-04
- **Code:** `Code/Python/XAU_POOL_SELECTION_LAB_001/`
- **Input:** `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- **Input rows:** 1,454,538 M1 bars (per supplied report)
- **Input period:** 2022-06-01 — 2026-07-23
- **Symbol:** XAUUSD
- **Primary report:** `Reports/XAU_POOL_SELECTION_LAB_001_Report.md`
- **Canonical:** no; status CANDIDATE
- **Candidate rows:** 266,297; AMBIGUOUS excluded: 145
- **Primary selected counts:** IS 3,436; OOS-1 2,260; OOS-2 2,437; CONTROL 1,506
- **Causal cutoff:** features calculated at bar close before entry, according to the specification

## Missing from package

- raw input bytes and hash;
- `pool.parquet`, `pool_excess.parquet`, `baseline.parquet`;
- OOS/CONTROL scored tables;
- selected trade-level result tables;
- fitted models/scalers;
- execution logs and runtime environment lock.

Therefore the numerical result is preserved as reported but has not been independently reproduced during import.
