from __future__ import annotations

import json
import pickle
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path("selection_sizing_artifact")
OUT.mkdir(exist_ok=True)

patterns = [
    "*C2_p_by_episode*",
    "*c2_trades_loop_PINNED*",
    "*trades_GEOstar*",
    "*GeoSweep*v009*",
    "*weights_schedule_GEOstar*",
    "*wf_toolkit*",
]

files: list[Path] = []
for pattern in patterns:
    files.extend(ROOT.rglob(pattern))
files = sorted(set(p for p in files if p.is_file()))

inventory: dict[str, object] = {"root": str(ROOT), "matches": []}
md = ["# Selection & Sizing v001 — input inventory", ""]

for path in files:
    rel = path.relative_to(ROOT)
    rec: dict[str, object] = {"path": str(rel), "bytes": path.stat().st_size}
    try:
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as zf:
                rec["zip_members"] = [
                    {"name": z.filename, "bytes": z.file_size}
                    for z in zf.infolist()
                ]
        elif path.name.endswith(".csv.gz") or path.suffix == ".csv":
            df = pd.read_csv(path, nrows=5, sep=None, engine="python")
            rec["columns"] = df.columns.tolist()
            rec["sample"] = df.to_dict(orient="records")
        elif path.suffix == ".pkl":
            with path.open("rb") as fh:
                obj = pickle.load(fh)
            rec["pickle_type"] = type(obj).__name__
            if isinstance(obj, dict):
                rec["pickle_keys"] = [str(k) for k in obj.keys()]
            elif hasattr(obj, "columns"):
                rec["columns"] = list(obj.columns)
                rec["shape"] = list(obj.shape)
        elif path.suffix in {".py", ".md", ".json"}:
            rec["head"] = path.read_text(errors="replace")[:3000]
    except Exception as exc:  # inspection must continue
        rec["error"] = repr(exc)
    inventory["matches"].append(rec)

for rec in inventory["matches"]:
    md.append(f"## `{rec['path']}`")
    md.append("")
    md.append(f"- bytes: {rec['bytes']}")
    if "columns" in rec:
        md.append(f"- columns: `{rec['columns']}`")
    if "shape" in rec:
        md.append(f"- shape: `{rec['shape']}`")
    if "pickle_keys" in rec:
        md.append(f"- pickle keys: `{rec['pickle_keys']}`")
    if "zip_members" in rec:
        md.append("- ZIP members:")
        for member in rec["zip_members"]:
            md.append(f"  - `{member['name']}` — {member['bytes']} bytes")
    if "error" in rec:
        md.append(f"- ERROR: `{rec['error']}`")
    md.append("")

(OUT / "input_inventory.json").write_text(json.dumps(inventory, indent=2, default=str))
(OUT / "input_inventory.md").write_text("\n".join(md))
print(json.dumps(inventory, indent=2, default=str))
