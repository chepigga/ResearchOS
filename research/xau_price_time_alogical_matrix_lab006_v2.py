#!/usr/bin/env python3
"""Compatibility wrapper for XAU_PRICE_TIME_ALOGICAL_MATRIX_LAB006.

LAB001 stores atr14_causal in causal_labels_m1.parquet rather than
m1_bidask_bars.parquet. This wrapper causally joins ATR by minute, writes a
patched temporary bars parquet, then runs the frozen LAB006 logic unchanged.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

import xau_price_time_alogical_matrix_lab006 as lab


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bars", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--outdir", type=Path, required=True)
    a = p.parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)

    bars = pd.read_parquet(a.bars)
    if "atr14_causal" not in bars.columns:
        atr = pd.read_parquet(a.labels, columns=["minute", "atr14_causal"])
        bars = bars.merge(atr, on="minute", how="left", validate="one_to_one")

    patched = a.outdir / "_bars_with_causal_atr.parquet"
    bars.to_parquet(patched, index=False)

    sys.argv = [
        "xau_price_time_alogical_matrix_lab006.py",
        "--bars", str(patched),
        "--labels", str(a.labels),
        "--outdir", str(a.outdir),
    ]
    lab.main()

    try:
        patched.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    main()
