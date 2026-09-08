#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab046_base',HERE/'run_lab.py')
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
_orig=base.simulate

def _fixed_simulate(r,fut,policy):
    if policy=='ENTRY_PLUS_6H' and r.state=='ACCEPT' and pd.notna(r.class_time):
        parent_horizon=pd.Timestamp(r.signal_time)+pd.Timedelta(hours=12)
        if pd.Timestamp(r.class_time)>=parent_horizon:
            z=_orig(r,fut,'SIGNAL_PLUS_12H')
            z['policy']='ENTRY_PLUS_6H'
            z['eligible']=False
            z['covered']=False
            z['horizon']=pd.Timestamp(r.class_time)+pd.Timedelta(hours=6)
            z['exit_reason']='PARENT_LATE_ACCEPT'
            return z
    return _orig(r,fut,policy)

base.simulate=_fixed_simulate
base.main()
