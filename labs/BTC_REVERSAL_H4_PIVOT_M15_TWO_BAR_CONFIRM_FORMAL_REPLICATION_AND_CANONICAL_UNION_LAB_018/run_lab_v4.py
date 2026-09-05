#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
SRC=HERE/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab018_base",SRC)
L18=importlib.util.module_from_spec(spec); spec.loader.exec_module(L18)


def module_extra_fixed(s,a,b,months):
    d=s[(s.parent_time>=a)&(s.parent_time<b)].copy().sort_values("signal_time")
    rf=d[d.real_fill].copy().sort_values("fill_time")
    r=rf.real_R.to_numpy(float)
    _,_,_,_,loeo=L18.L17.episode_stats(d)
    return dict(
        fills_per_month=len(rf)/months,
        mean_R=float(r.mean()) if len(r) else np.nan,
        cum_R=float(r.sum()) if len(r) else 0.0,
        pf=L18.pf(r), dd=L18.maxdd(r), loeo=loeo,
        max_concurrent=L18.max_concurrent(rf),
    )


def build_union_fixed(canon,child,a,b,months):
    c=canon[(canon.event_time>=a)&(canon.event_time<b)&(canon.real_fill)].copy()
    c["src"]="CANON"; c["window_time"]=c.event_time
    c["exit_time"]=pd.to_datetime(c.event_time,utc=True)+pd.Timedelta(hours=24)
    h=child[(child.parent_time>=a)&(child.parent_time<b)&(child.real_fill)].copy()
    h["src"]="H4_TWO_BAR"; h["window_time"]=h.parent_time
    cols=["src","window_time","fill_time","exit_time","real_R","impulse_dir"]
    z=pd.concat([c[cols],h[cols]],ignore_index=True).sort_values("fill_time")
    r=z.real_R.to_numpy(float) if len(z) else np.array([])
    er25,ed25=L18.equity_stats(r,.0025); er50,ed50=L18.equity_stats(r,.005)
    mc=L18.max_concurrent(z)
    return dict(
        real_fills=len(z), fills_per_month=len(z)/months,
        canonical_fills=int((z.src=="CANON").sum()) if len(z) else 0,
        h4_fills=int((z.src=="H4_TWO_BAR").sum()) if len(z) else 0,
        cum_R=float(r.sum()) if len(r) else 0.0,
        mean_R=float(r.mean()) if len(r) else np.nan,
        profit_factor=L18.pf(r), max_dd_R=L18.maxdd(r), max_concurrent=mc,
        risk_load_025_pct=mc*.25, risk_load_050_pct=mc*.50,
        equity_return_025_pct=er25, equity_dd_025_pct=ed25,
        equity_return_050_pct=er50, equity_dd_050_pct=ed50,
    ),z

L18.module_extra=module_extra_fixed
L18.build_union=build_union_fixed

if __name__=="__main__":
    L18.main()
    p=L18.OUT/"REPORT.md"
    if p.exists():
        txt=p.read_text(encoding="utf-8")
        txt += "\n## Risk-accounting note\n- LAB015 canonical artifact did not persist actual `exit_time`; union concurrency uses conservative `canonical event_time + 24h`. This may overstate overlap. PnL, EV, PF and DD-R are unaffected.\n"
        p.write_text(txt,encoding="utf-8")
