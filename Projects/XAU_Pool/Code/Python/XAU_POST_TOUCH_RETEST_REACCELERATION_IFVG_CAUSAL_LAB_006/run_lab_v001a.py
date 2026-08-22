#!/usr/bin/env python3
"""Implementation-only null-handling patch for LAB006 v001.

Research logic is unchanged. Parent health_map leaves entry fields NaN on signals with
no causal entry; this wrapper makes simulate_branch interpret NaN exactly as NO_ENTRY.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).with_name('run_lab.py')
spec = importlib.util.spec_from_file_location('lab006_base', BASE)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def safe_simulate_branch(x:pd.DataFrame, df:pd.DataFrame, branch:str, target:float)->pd.DataFrame:
    y=x.copy(); key=lab.tkey(target)
    times_m=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    bh=df.high.to_numpy(float); bl=df.low.to_numpy(float); bc=df.close.to_numpy(float)
    ah=df.ask_high.to_numpy(float); al=df.ask_low.to_numpy(float); ac=df.ask_close.to_numpy(float)
    vals=[]; gross=[]; stress05=[]; stress10=[]; out=[]; exi=[]; ext=[]
    entry_i_col=f'{branch}_entry_i'; entry_col=f'{branch}_entry'
    for r in y.itertuples(index=False):
        raw=getattr(r,entry_i_col)
        ei=-1 if pd.isna(raw) else int(raw)
        if ei<0:
            vals.append(np.nan); gross.append(np.nan); stress05.append(np.nan); stress10.append(np.nan); out.append('NO_ENTRY'); exi.append(-1); ext.append(pd.NaT); continue
        d=int(r.dir); atr=float(r.atr0); risk=lab.RISK_ATR*atr; entry=float(getattr(r,entry_col))
        gr,xi,oc=lab.sim_trade(ei,d,entry,risk,target,times_m,bh,bl,bc,ah,al,ac)
        comm=lab.COMMISSION_PRICE/risk; nr=gr-comm
        gross.append(float(gr)); vals.append(float(nr)); stress05.append(float(nr-0.05/risk)); stress10.append(float(nr-0.10/risk)); exi.append(int(xi)); ext.append(df.at[xi,'time']); out.append(['SL','TP','SAME_BAR_LOSS','TIME'][oc])
    y[f'{branch}_gross_R_{key}']=gross; y[f'{branch}_net_R_{key}']=vals; y[f'{branch}_stress05_R_{key}']=stress05; y[f'{branch}_stress10_R_{key}']=stress10
    y[f'{branch}_outcome_{key}']=out; y[f'{branch}_exit_i_{key}']=exi; y[f'{branch}_exit_time_{key}']=ext
    return y

lab.simulate_branch = safe_simulate_branch

if __name__ == '__main__':
    lab.main()
