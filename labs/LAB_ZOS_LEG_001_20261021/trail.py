import pandas as pd,numpy as np
exec(open("octs.py").read().split("exits=")[0])
d=d1.close; er=((d-d.shift(20)).abs()/d.diff().abs().rolling(20).sum()).shift(1)
S={(tf,nm):sig for tf,nm,sig in strats}; b=B["M15"]
o,h,l,c,a,cost,ma=[b[x].values for x in ("open","high","low","close","atr","cost","ma20")]; idx=b.index; n=len(b)
def run3(sig,sa,be,act,dist,tgt,hold):
    res=[];i=0
    while i<n-1:
        s=sig[i]
        if s==0 or np.isnan(a[i]): i+=1; continue
        e=o[i+1]; R=sa*a[i]; st=e-s*R; best=0.0; j=i+1; out=None
        tp=None if tgt is None else e+s*tgt*R
        while j<n and j<=i+hold:
            if (s>0 and l[j]<=st) or (s<0 and h[j]>=st): out=s*(st-e); break
            if tp is not None and ((s>0 and h[j]>=tp) or (s<0 and l[j]<=tp)): out=s*(tp-e); break
            fav=(h[j]-e) if s>0 else (e-l[j]); best=max(best,fav/R)
            if be is not None and best>=be: st=(max(st,e) if s>0 else min(st,e))
            if act is not None and best>=act:
                ns=e+s*(best-dist)*R; st=(max(st,ns) if s>0 else min(st,ns))
            j+=1
        if out is None: j=min(j,n-1); out=s*(c[j]-e)
        res.append((idx[i+1],(out-cost[i])/R)); i=j+1
    return res
rows=[]
cfg=[("без трейлу, ціль 2R",None,None,None,2.0),("беззбиток після +0.5R, ціль 2R",0.5,None,None,2.0),("беззбиток після +1R, ціль 2R",1.0,None,None,2.0),
     ("трейл після +0.5R, дист 0.5R",None,0.5,0.5,None),("трейл після +1R, дист 0.5R",None,1.0,0.5,None),("трейл після +1R, дист 1R",None,1.0,1.0,None),
     ("трейл після +0.3R, дист 0.3R",None,0.3,0.3,None),("б/з 0.5R + трейл після 1R дист 0.5R",0.5,1.0,0.5,None)]
for nm in ("PDH/PDL фейд","RSI2 10/90 фейд"):
    for sa in (1.0,2.0):
        for cn,be,act,dist,tg in cfg:
            for hold in (8,24):
                r=pd.DataFrame(run3(S[("M15",nm)],sa,be,act,dist,tg,hold),columns=["t","R"])
                r["m"]=r.t.dt.to_period("M"); reg=er.reindex(r.t.dt.normalize()).values<0.2
                oc=r[r.t>="2026-10-01"]; k=r[reg&(r.t<"2026-10-01")]; mm=k.groupby("m").R.sum(); am=r.groupby("m").R.sum()
                rows.append((nm,sa,cn,hold,len(oc),oc.R.sum(),k.R.mean(),(mm>0).mean(),r.R.mean(),r[r.t<"2024-07-01"].R.mean(),r[r.t>="2024-07-01"].R.mean(),(am>0).mean()))
O=pd.DataFrame(rows,columns=["стратегія","стоп ATR","вихід","год*4","жовт n","жовт ΣR","кор R/уг","кор міс+%","всі R/уг","22-24","24-26","всі міс+%"])
O.to_pickle("trailO.pkl"); pd.set_option("display.width",260); print(O.round(3).to_string(index=False))
