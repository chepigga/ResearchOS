#!/usr/bin/env python3
import numpy as np
import pandas as pd
import run_lab as lab

def score_clock_fixed(e,clock):
    dev0=e[e.split=="DEV_2021_2024"].copy()
    thr=float(dev0.rev_24h.quantile(.75))
    e=e.copy()
    e["tail_rev"]=(e.rev_24h>=thr).astype(int)
    dev=e[e.split=="DEV_2021_2024"].copy()
    sets=lab.model_sets(); rows=[]; router=[]
    for name,fs in sets.items():
        m=lab.fit_pipe(dev,fs,"tail_rev")
        pdev=m.predict_proba(dev[fs])[:,1]
        q80=float(np.quantile(pdev,.80))
        for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
            d=e[e.split==sp].copy()
            p=m.predict_proba(d[fs])[:,1]
            auc,br,ll=lab.metrics(d.tail_rev.to_numpy(),p)
            top=p>=q80
            vals=d.rev_24h.to_numpy()[top]
            mean,lo,hi=lab.boot(vals)
            hit=float(d.tail_rev.to_numpy()[top].mean()) if top.sum() else np.nan
            rows.append(dict(clock=clock,split=sp,model=name,n=len(d),auc=auc,brier=br,logloss=ll))
            router.append(dict(clock=clock,split=sp,model=name,n_total=len(d),n_top=int(top.sum()),top_hit=hit,top_mean_rev=mean,top_ci_lo=lo,top_ci_hi=hi,threshold=thr,q80=q80))
    return pd.DataFrame(rows),pd.DataFrame(router),thr

lab.score_clock=score_clock_fixed
if __name__=="__main__":
    lab.main()
