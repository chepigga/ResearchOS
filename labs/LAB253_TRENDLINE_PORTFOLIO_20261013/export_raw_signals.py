#!/usr/bin/env python3
"""Export the frozen LAB150 pre-portfolio candidate stream. Run from repository root."""
import importlib.util
from pathlib import Path

root=Path(__file__).resolve().parents[2]
p=root/"labs/LAB150_SELECTIVE_CONCURRENCY_OVERLAP_RISK_20261009/run_lab150.py"
spec=importlib.util.spec_from_file_location("lab150_raw253",p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
rows=mod.raw_events(7.5)
needed=["entry_time","side","atr","source"]
missing=set(needed)-set(rows.columns)
if missing: raise ValueError(f"Missing fields {sorted(missing)}")
out=Path("lab253_raw_signals.csv")
rows[needed].drop_duplicates().sort_values("entry_time").to_csv(out,index=False)
print(f"Wrote {out} with {len(rows)} rows")
