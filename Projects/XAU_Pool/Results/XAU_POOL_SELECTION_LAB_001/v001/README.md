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

## Saved artifacts

| File | Role | SHA256 |
|---|---|---|
| `Artifacts/pool_excess.parquet` | candidate pool with R/excess labels | `107180b046476e627dcd9a304a5eff027d063fe29b9458cbfa2c14f983b6410e` |
| `Artifacts/baseline.parquet` | matched drift baseline | `6b6c8bc62fa0c109ea3a34fe13bcb6fc7fe81596bef05da7386fbab098c50b51` |
| `Artifacts/permutation_37_shuffles.jsonl` | raw GATE-4 records | `10dc21c667782bd3a87439df5348c31add462a8d353fcf8887cd2f8c5c26a5ce` |
| `Artifacts/weights_schedule_XAU_POOL_v001.pkl` | 48-window WF model schedule | `fc5cacc24b2c3d344cf85405506cb99d965ede1e6c7a7e8ed4cf40d7ebf25ae2` |

## Still missing

- raw input bytes/hash in this checkpoint (data remains an external release asset);
- selected trade-level result tables and full execution logs;
- runtime/dependency lock.

The artifacts materially improve reproducibility, but the numerical result was not independently rerun during this GitHub update.
