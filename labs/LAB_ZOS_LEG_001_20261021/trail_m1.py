import pandas as pd,numpy as np
exec(open("octs.py").read().split("exits=")[0])
d=d1.close; er=((d-d.shift(20)).abs()/d.diff().abs().rolling(20).sum()).shift(1)
S={(tf,nm):sig for tf,nm,sig in strats}; b=B["M15"]
m1=pd.read_pickle("m1b.pkl"); M=m1[["open","high","low","close"]].values; mt=m1.index
pos=np.searchsorted(mt.values,b.index.values)   # first M1 at/after M15 start
a=b.atr.values; cost=b.cost.values; idx=b.index; n=len(b)
def run(sig,sa,be,act,dist,tgt,hold):
    res=[];i=0
    while i<n-1:
        s=sig[i]
        if s==0 or np.isnan(a[i]): i+=1; continue
        k0=pos[i+1]
        if k0>=len(M) or abs((mt[k0]-idx[i+1]).total_seconds())>3600: i+=1; continue
        e=M[k0,0]; R=sa*a[i]; st=e-s*R; best=0.0; tp=None if tgt is None else e+s*tgt*R
        kend=np.searchsorted(mt.values,(idx[i+1]+pd.Timedelta(minutes=15*hold)).to_datetime64())
        out=None; k=k0
        while k<min(kend,len(M)):
            op,hh,ll,cl=M[k]
            if (s>0 and ll<=st) or (s<0 and hh>=st):
                fill=min(op,st) if s>0 else max(op,st); out=s*(fill-e); break
            if tp is not None and ((s>0 and hh>=tp) or (s<0 and ll<=tp)): out=s*(tp-e); break
            fav=(hh-e) if s>0 else (e-ll); best=max(best,fav/R)
            if be is not None and best>=be: st=(max(st,e) if s>0 else min(st,e))
            if act is not None and best>=act:
                ns=e+s*(best-dist)*R; st=(max(st,ns) if s>0 else min(st,ns))
            k+=1
        if out is None: k=min(k,len(M)-1); out=s*(M[k-1,3]-e)
        res.append((idx[i+1],(out-cost[i])/R))
        i=max(i+1,np.searchsorted(idx.values,mt[min(k,len(M)-1)].to_datetime64()))
    return res
rows=[]
cfg=[("без трейлу, ціль 2R",None,None,None,2.0),("трейл після +0.5R, дист 0.5R",None,0.5,0.5,None),("трейл після +0.3R, дист 0.3R",None,0.3,0.3,None),("трейл після +0.3R, дист 0.5R",None,0.3,0.5,None),("трейл після +0.2R, дист 0.2R",None,0.2,0.2,None)]
for nm in ("PDH/PDL фейд","RSI2 10/90 фейд"):
    for sa in (1.0,):
        for cn,be,act,dist,tg in cfg:
            hold=8
            r=pd.DataFrame(run(S[("M15",nm)],sa,be,act,dist,tg,hold),columns=["t","R"])
            r["m"]=r.t.dt.to_period("M"); reg=er.reindex(r.t.dt.normalize()).values<0.2
            oc=r[r.t>="2026-10-01"]; kk=r[reg&(r.t<"2026-10-01")]; mm=kk.groupby("m").R.sum(); am=r.groupby("m").R.sum()
            rows.append((nm,cn,len(oc),oc.R.sum(),kk.R.mean(),(mm>0).mean(),len(r),r.R.mean(),r[r.t<"2024-07-01"].R.mean(),r[r.t>="2024-07-01"].R.mean(),(am>0).mean()))
            r.to_pickle(f"tr_{nm[:3]}_{cn[:22].replace(' ','_')}.pkl")
O=pd.DataFrame(rows,columns=["стратегія","вихід","жовт n","жовт ΣR","кор R/уг","кор міс+%","n","всі R/уг","22-24","24-26","всі міс+%"])
pd.set_option("display.width",260); print(O.round(3).to_string(index=False))
