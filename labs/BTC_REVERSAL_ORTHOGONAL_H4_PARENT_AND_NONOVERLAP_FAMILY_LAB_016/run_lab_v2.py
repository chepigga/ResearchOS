#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
SRC=HERE/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab016_base",SRC)
L16=importlib.util.module_from_spec(spec); spec.loader.exec_module(L16)


def remove_canonical_overlap_fixed(sel,canon):
    """Execution-only parity fix: force BOTH timestamp vectors to integer nanoseconds.
    No prereg threshold, family definition, router, maturity, or execution rule changes.
    """
    if len(sel)==0 or len(canon)==0:
        return sel.copy(),0
    ct=np.asarray([pd.Timestamp(t).value for t in canon.event_time],dtype=np.int64)
    keep=[]; removed=0; day=int(pd.Timedelta(hours=24).value)
    for idx,r in sel.iterrows():
        t=int(pd.Timestamp(r.event_time).value)
        if int(np.min(np.abs(ct-t)))<=day:
            removed+=1
        else:
            keep.append(idx)
    return sel.loc[keep].copy(),removed

L16.remove_canonical_overlap=remove_canonical_overlap_fixed

if __name__=="__main__":
    L16.main()
