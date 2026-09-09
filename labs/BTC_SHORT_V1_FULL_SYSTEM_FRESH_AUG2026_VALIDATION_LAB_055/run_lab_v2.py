#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab055_base',HERE/'run_lab.py')
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
_orig=base.parent_sim

def _fixed_parent_sim(r,fut):
    z=_orig(r,fut)
    if bool(z.get('eligible',False)) and pd.notna(z.get('entry_time')) and pd.Timestamp(z['entry_time'])==pd.Timestamp(z['horizon']):
        z.update(traded=False,parent_exit_time=pd.NaT,parent_exit_price=float('nan'),parent_exit_reason='NO_TRADE',
                 final_exit_time=pd.NaT,final_exit_price=float('nan'),final_exit_reason='NO_TRADE',
                 adverse_first=False,adverse_time=pd.NaT,persistent_failure=False,persistent_time=pd.NaT,early_exit=False,
                 net_r_0bps=0.0,net_r_5bps=0.0,net_r_10bps=0.0)
    return z
base.parent_sim=_fixed_parent_sim
base.main()
