import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import zthr as Z
from run_exec import sim
rows=[]
for T in [1.5,2.0,2.5,3.0]:
    ev=Z.events(T,"FRESH")
    for k,H,tp,hl,name in [(1.0,72,3.0,True,"SL1 half3R 72h"),(2.0,48,None,False,"SL2 time48h"),(3.0,48,None,False,"SL3 time48h"),(3.0,24,None,False,"SL3 time24h"),(3.0,72,None,False,"SL3 time72h")]:
        for sg in ["TRAIN","OOS"]:
            e=ev[(ev.entry_time<Z.TE) if sg=="TRAIN" else (ev.entry_time>=Z.TE)].reset_index(drop=True)
            t,eq=sim(e,k,H,tp,half_lock=hl)
            dd=float(np.max(np.maximum.accumulate(eq)-eq)); m=Z.MO[sg]
            rows.append(dict(T=T,exit=name,seg=sg,trades_mo=len(t)/m,ev=t.net_r.mean(),r_mo=t.net_r.sum()/m,dd=dd,r_dd=t.net_r.sum()/dd))
R=pd.DataFrame(rows); pd.set_option("display.width",250)
print(R.pivot_table(index=["T","exit"],columns="seg",values=["trades_mo","ev","r_mo","dd","r_dd"]).round(2).to_string())
R.to_csv("out_oos/ZTHRESH_EXITS.csv",index=False)
