#!/usr/bin/env python3
"""Implementation-only wrapper for LAB001 canonical semicolon CSV.

Research logic remains in frozen run_lab.py v001. This wrapper only patches
pandas.read_csv to use the delimiter of the canonical ResearchOS release asset.
"""
from pathlib import Path
import run_lab as lab

_original_read_csv = lab.pd.read_csv


def _canonical_read_csv(path, *args, **kwargs):
    suffix = Path(path).suffix.lower() if isinstance(path, (str, Path)) else ""
    if suffix in {".csv", ".zip"} and "sep" not in kwargs:
        kwargs["sep"] = ";"
    return _original_read_csv(path, *args, **kwargs)


lab.pd.read_csv = _canonical_read_csv

if __name__ == "__main__":
    lab.main()
