import pandas as pd,numpy as np
out=pd.read_pickle("twoside.pkl")
Lt=pd.concat([out["лонг EMA50 (як раніше)"],out["шорт повний тренд D1, вихід 1R"]]).sort_values("t").reset_index(drop=True)
d1=pd.read_pickle("d1.pkl"); m15=pd.read_pickle("m15.pkl"); c=d1.close
tr=pd.concat([d1.high-d1.low,(d1.high-c.shift()).abs(),(d1.low-c.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(14).mean().shift(1)
c15=m15.close; tr15=pd.concat([m15.high-m15.low,(m15.high-c15.shift()).abs(),(m15.low-c15.shift()).abs()],axis=1).max(axis=1); a15=tr15.rolling(96).mean().shift(1)
P=pd.period_range("2022-10","2026-10",freq="M"); M=pd.read_pickle("/home/claude/duo/M300.pkl"); dd=lambda s:(s.cumsum().cummax()-s.cumsum()).max()
Ld=pd.read_pickle("/home/claude/duo/legs300.pkl"); Ld["m"]=pd.PeriodIndex(Ld.xt,freq="M")
def shock_times(kind,k):
    s=(d1.index[((tr/atr)>k).values]+pd.Timedelta(days=1)) if kind=="D1" else (m15.index[((tr15/a15)>k).values]+pd.Timedelta(minutes=15))
    return np.sort(np.asarray(s,dtype="datetime64[ns]"))
def blocked(times,sh,H):
    t=np.asarray(times,dtype="datetime64[ns]")
    if len(sh)==0: return np.zeros(len(t),bool)
    idx=np.searchsorted(sh,t,side="right")-1
    ok=idx>=0; res=np.zeros(len(t),bool)
    res[ok]=(t[ok]-sh[idx[ok]])<np.timedelta64(int(H*3600),"s")
    return res
def evals(nm,shk,H,all_legs):
    x=Lt[~blocked(Lt.t,shk,H)]
    m=x[x.t>="2022-10-01"].groupby(x.t.dt.to_period("M")).R.sum().reindex(P,fill_value=0)
    if all_legs: z=Ld[~blocked(Ld.et,shk,H)]; base=z.groupby("m").net.sum().reindex(P,fill_value=0)
    else: base=M.ALL
    duo=base+m*250; j=duo[pd.Period("2025-06","M")]; h=x.t<"2024-10-01"
    print(f"{nm:44s} L угод {len(x):4d} R/уг {x.R.mean():+.3f} [{x.R[h].mean():+.3f}|{x.R[~h].mean():+.3f}] | Duo+L ${duo.sum():.0f} DD ${dd(duo):.0f} мінус {(duo<0).sum()} гірший {duo.min():.0f} черв25 {j:.0f}")
evals("без кулдауну",np.array([],dtype="datetime64[ns]"),0,False)
for kind,k in (("D1",1.5),("D1",2.0),("M15",4.0),("M15",6.0)):
    sh=shock_times(kind,k); print(f"-- шоків {kind}>{k}×ATR: {len(sh)}")
    for H in ((24,48,72) if kind=="D1" else (8,24,48)):
        for al in (False,True):
            evals(f"{kind}>{k}×ATR пауза {H}г {'всі ноги' if al else 'лише L'}",sh,H,al)
