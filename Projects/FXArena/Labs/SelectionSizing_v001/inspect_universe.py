from __future__ import annotations

import json
import pickle
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
RELEASE = ROOT / "_release_assets"
WORK = ROOT / "_selection_universe_work"
OUT = ROOT / "selection_sizing_universe_artifact"
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)


def extract(zip_name: str, subdir: str) -> Path:
    src = RELEASE / zip_name
    dst = WORK / subdir
    dst.mkdir(exist_ok=True)
    with zipfile.ZipFile(src) as zf:
        zf.extractall(dst)
    return dst


def describe_obj(obj):
    rec = {"type": type(obj).__name__}
    if isinstance(obj, pd.DataFrame):
        rec.update({
            "shape": list(obj.shape),
            "columns": obj.columns.tolist(),
            "dtypes": {c: str(t) for c, t in obj.dtypes.items()},
            "head": obj.head(5).to_dict(orient="records"),
            "tail": obj.tail(3).to_dict(orient="records"),
        })
    elif isinstance(obj, dict):
        rec["keys"] = [str(k) for k in obj.keys()]
        rec["values"] = {
            str(k): {
                "type": type(v).__name__,
                "shape": list(v.shape) if hasattr(v, "shape") else None,
                "keys": [str(x) for x in v.keys()] if isinstance(v, dict) else None,
            }
            for k, v in obj.items()
        }
    elif isinstance(obj, (list, tuple)):
        rec["length"] = len(obj)
        rec["item_types"] = sorted({type(x).__name__ for x in obj[:100]})
    return rec


timeout = extract("FXArena_TimeoutSweep_v009b_FINAL_results.zip", "timeout")
geo = extract("FXArena_GeoSweep_v009_results.zip", "geo")

inventory = {}

with (timeout / "meta.pkl").open("rb") as fh:
    meta = pickle.load(fh)
inventory["meta.pkl"] = describe_obj(meta)

with np.load(timeout / "outcomes.npz", allow_pickle=True) as z:
    inventory["outcomes.npz"] = {
        k: {
            "shape": list(z[k].shape),
            "dtype": str(z[k].dtype),
            "head": z[k].reshape(-1)[:5].tolist(),
        }
        for k in z.files
    }

x48 = np.load(timeout / "X48.npy", mmap_mode="r")
inventory["X48.npy"] = {
    "shape": list(x48.shape),
    "dtype": str(x48.dtype),
    "first_row": x48[0, : min(10, x48.shape[1])].tolist(),
}

for name in [
    "weights_schedule_C2.pkl",
    "weights_schedule_GEOstar_MICRO30_TP2_TO120.pkl",
]:
    with (RELEASE / name).open("rb") as fh:
        obj = pickle.load(fh)
    inventory[name] = describe_obj(obj)

for name in [
    "c2_trades_loop_PINNED.pkl",
]:
    with (RELEASE / name).open("rb") as fh:
        obj = pickle.load(fh)
    inventory[name] = describe_obj(obj)

for name in [
    "C2_p_by_episode.csv",
    "C2_frozen_livewindow.csv",
    "trades_GEOstar_MICRO30_TP2_TO120_PINNED.csv.gz",
    "c2_trades_loop_PINNED.csv.gz",
]:
    p = RELEASE / name
    df = pd.read_csv(p, sep=None, engine="python")
    inventory[name] = describe_obj(df)

for src in [
    timeout / "FXArena_TimeoutSweepLab_v009b.py",
    geo / "FXArena_GeoSweepLab_v009.py",
    geo / "FXArena_GeoSweep_v009_validate.py",
    RELEASE / "wf_toolkit.py",
    RELEASE / "fitlog_GEOstar_MICRO30_TP2_TO120.json",
    timeout / "prep_audit.json",
    timeout / "TimeoutSweep_v009b_control_audit.json",
    geo / "prep_audit.json",
    geo / "control_audit.json",
]:
    if src.exists():
        shutil.copy2(src, OUT / src.name)

(OUT / "universe_inventory.json").write_text(json.dumps(inventory, indent=2, default=str))

lines = ["# Full universe inventory", ""]
for name, rec in inventory.items():
    lines += [f"## `{name}`", "", "```json", json.dumps(rec, indent=2, default=str), "```", ""]
(OUT / "universe_inventory.md").write_text("\n".join(lines))
print(json.dumps(inventory, indent=2, default=str))
