import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
df=pd.DataFrame({"c":L.BC,"a":L.BA},index=L.BT)
h1=df.resample("1h").agg({"c":"last","a":"last"}).dropna()
C=h1.c.to_numpy(); A=h1.a.to_numpy(); T=h1.index
def zigzag(thr_fn):
    piv=[0]; d=0; ei=0
    for i in range(1,len(C)):
        if d>=0:
            if C[i]>C[ei]: ei=i
            elif C[ei]-C[i]>=thr_fn(ei): piv.append(ei); d=-1; ei=i; continue
        if d<=0:
            if C[i]<C[ei]: ei=i
            elif C[i]-C[ei]>=thr_fn(ei): piv.append(ei); d=1; ei=i
    piv.append(ei)
    w=[(T[a],T[b],C[a],C[b],abs(C[b]-C[a])/A[a],abs(C[b]/C[a]-1)*100,(b-a)) for a,b in zip(piv[:-1],piv[1:]) if b>a]
    return pd.DataFrame(w,columns=["t0","t1","p0","p1","atr","pct","hours"])
days=(T[-1]-T[0]).days; yrs=days/365.25
rows=[]
for kind,vals in [("ATR",[3,6,10,15,25]),("%",[2,5,10,20])]:
    for v in vals:
        W=zigzag((lambda i,v=v:v*A[i]) if kind=="ATR" else (lambda i,v=v:C[i]*v/100))
        W=W[(W.atr>=v) if kind=="ATR" else (W.pct>=v)]
        n=len(W)
        rows.append(dict(threshold=f"{v} {kind}",per_day=n/days,per_week=n/days*7,per_month=n/days*30.44,per_year=n/yrs,
            med_size_atr=W.atr.median(),med_size_pct=W.pct.median(),med_hours=W.hours.median(),
            y2025_26=len(W[W.t0>="2025-01-01"])/((T[-1]-pd.Timestamp("2025-01-01",tz="UTC")).days/30.44)))
R=pd.DataFrame(rows); pd.set_option("display.width",250)
print(R.round(2).to_string(index=False))
# by year for 6 ATR and 5%
for kind,v in [("ATR",6),("%",5)]:
    W=zigzag((lambda i:v*A[i]) if kind=="ATR" else (lambda i:C[i]*v/100)); W=W[(W.atr>=v) if kind=="ATR" else (W.pct>=v)]
    print(f"\n{v}{kind} by year:",W.groupby(W.t0.dt.year).agg(n=("atr","size"),med_atr=("atr","median"),med_pct=("pct","median"),med_h=("hours","median")).round(1).to_dict("index"))
print("\nmedian H1 ATR % of price by year:",(h1.a/h1.c*100).groupby(h1.index.year).median().round(2).to_dict())
