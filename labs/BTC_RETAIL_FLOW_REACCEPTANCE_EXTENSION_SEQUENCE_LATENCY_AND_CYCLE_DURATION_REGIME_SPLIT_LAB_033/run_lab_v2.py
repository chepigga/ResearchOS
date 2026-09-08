#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab033_base',HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

def reconstruct_cycles_exact(price,row):
    at=row['accept_time']; xt=row['extension_time']; side=int(row['side']); origin=float(row['origin']); entry=float(row['entry'])
    if pd.isna(at) or pd.isna(xt) or at not in price.index or xt not in price.index or xt<at:
        return dict(recon_failure_time=pd.NaT,recon_reaccept_time=pd.NaT,cycle_count=np.nan,bad_closes=np.nan)
    # Exact LAB028/LAB029 semantics: acceptance passage bar itself is included in the close-failure path.
    path=price.loc[(price.index>=at)&(price.index<=xt)]
    consec=0; failed=False; cycles=0; bad_count=0; first_fail=pd.NaT; first_reaccept=pd.NaT
    for t,z in path.iterrows():
        close=float(z.close)
        bad=side*(close-origin)<=0
        if bad: bad_count+=1
        if not failed:
            consec=consec+1 if bad else 0
            if consec>=2:
                failed=True
                if pd.isna(first_fail): first_fail=t
        else:
            reaccepted=side*(close-entry)>0  # exact LAB030 first_close uses strict > 0
            if reaccepted:
                cycles+=1; failed=False; consec=0
                if pd.isna(first_reaccept): first_reaccept=t
    return dict(recon_failure_time=first_fail,recon_reaccept_time=first_reaccept,cycle_count=float(cycles),bad_closes=float(bad_count))

L.reconstruct_cycles=reconstruct_cycles_exact
L.main()
