#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab031_core', HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
_orig_sim=L.simulate
_orig_dumps=L.json.dumps

def _default(o):
    if isinstance(o,np.bool_): return bool(o)
    if isinstance(o,np.integer): return int(o)
    if isinstance(o,np.floating): return float(o)
    raise TypeError(f'Object of type {o.__class__.__name__} is not JSON serializable')

def _dumps(obj,*args,**kwargs):
    kwargs.setdefault('default',_default)
    return _orig_dumps(obj,*args,**kwargs)

L.json.dumps=_dumps

def simulate_with_terminal(price,d):
    out=_orig_sim(price,d)
    seen=set(out.flow_id.astype(int).tolist()) if len(out) else set()
    rows=[]
    for r in d.itertuples():
        fid=int(r.flow_id)
        if fid in seen or not bool(r.full_reaccept) or pd.isna(r.full_reaccept_time):
            continue
        sig_t=pd.Timestamp(r.signal_time); rt=pd.Timestamp(r.full_reaccept_time)
        end=sig_t+pd.Timedelta(hours=12)
        if end not in price.index:
            continue
        side=int(r.side); origin=float(r.signal_close); entry=float(r.entry); atr=float(r.atr14)
        end_close=float(price.loc[end,'close'])
        # These are terminal/near-terminal reaccepts with insufficient post-reaccept bars.
        # By PREREG they are UNRESOLVED, never PERSIST2/SECOND_FAIL.
        rows.append(dict(flow_id=fid,signal_time=sig_t,side=side,origin=origin,entry=entry,atr14=atr,
          reaccept_time=rt,state='UNRESOLVED',class_time=end,class_close=end_close,residual_atr=0.0,
          class_delay_h=max(0.0,float((end-rt).total_seconds()/3600)),post_class_mae_atr=0.0,post_class_mfe_atr=0.0,
          audit_first_passage='NONE',plus05_time=pd.NaT,second_fail_time=pd.NaT))
    if rows:
        out=pd.concat([out,pd.DataFrame(rows)],ignore_index=True).sort_values('signal_time').reset_index(drop=True)
    return out

L.simulate=simulate_with_terminal
L.main()
