#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
SRC=HERE/"run_lab_v2.py"
spec=importlib.util.spec_from_file_location("lab018_v2",SRC)
V2=importlib.util.module_from_spec(spec); spec.loader.exec_module(V2)
L18=V2.L18


def module_extra_fixed(s,a,b,months):
    d=s[(s.parent_time>=a)&(s.parent_time<b)].copy().sort_values("signal_time")
    rf=d[d.real_fill].copy().sort_values("fill_time")
    r=rf.real_R.to_numpy(float)
    _,_,_,_,loeo=L18.L17.episode_stats(d)
    return dict(
        fills_per_month=len(rf)/months,
        mean_R=float(r.mean()) if len(r) else np.nan,
        cum_R=float(r.sum()) if len(r) else 0.0,
        pf=L18.pf(r),
        dd=L18.maxdd(r),
        loeo=loeo,
        max_concurrent=L18.max_concurrent(rf),
    )

L18.module_extra=module_extra_fixed

if __name__=="__main__":
    L18.main()
    p=L18.OUT/"REPORT.md"
    if p.exists():
        txt=p.read_text(encoding="utf-8")
        txt += "\n## Risk-accounting note\n- LAB015 canonical artifact did not persist actual `exit_time`; union concurrency uses conservative `canonical event_time + 24h`. This may overstate overlap. PnL, EV, PF and DD-R are unaffected.\n"
        p.write_text(txt,encoding="utf-8")
