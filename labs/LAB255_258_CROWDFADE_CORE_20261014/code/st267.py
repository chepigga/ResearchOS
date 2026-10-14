"""LAB267: HTF filter for engine S — EMA150/250 (AlgoSignals v1.02) vs user's EMA9/20/200 on H1 and M15.
Same plateau cells (H1/H2 x sens 1.3/1.8), RIDE exit, compass skip |z24|>=1 against. Filter = last closed bar of filter TF."""
import numpy as np,pandas as pd
exec(open("st265.py").read().split("\nF={")[0])
def emas(tf):
    b=df.resample(tf).agg({"c":"last"}).dropna().c
    out={}
    for p in (9,20,150,200,250):
        e=b.ewm(span=p,adjust=False).mean(); e.index=e.index+pd.Timedelta(tf); out[p]=e.reindex(T,method="ffill").to_numpy()
    c=b.copy(); c.index=c.index+pd.Timedelta(tf); out["c"]=c.reindex(T,method="ffill").to_numpy()
    return out
EH=emas("1h"); EM=emas("15min")
def sgn(x): return np.where(np.isfinite(x),np.sign(x),0).astype(int)
FILT={"немає фільтра":np.zeros(N,int)+9,
 "EMA150/250 H1 (зараз)":sgn(EH[150]-EH[250]),
 "ціна vs EMA200 H1":sgn(EH["c"]-EH[200]),
 "EMA20 vs EMA200 H1":sgn(EH[20]-EH[200]),
 "EMA9 vs EMA20 H1":sgn(EH[9]-EH[20]),
 "9>20>200 H1 (стек)":np.where((EH[9]>EH[20])&(EH[20]>EH[200]),1,np.where((EH[9]<EH[20])&(EH[20]<EH[200]),-1,0)),
 "ціна vs EMA200 M15":sgn(EM["c"]-EM[200]),
 "EMA9 vs EMA20 M15":sgn(EM[9]-EM[20]),
 "9>20>200 M15 (стек)":np.where((EM[9]>EM[20])&(EM[20]>EM[200]),1,np.where((EM[9]<EM[20])&(EM[20]<EM[200]),-1,0))}
rows=[]
for tf,sens in [("1h",1.3),("1h",1.8),("2h",1.3),("2h",1.8)]:
    A=simX(signals(tf,sens),False,"RIDE"); A=A[~((A.cz==-A.side)&(A.az>=1))]
    for fn,Fa in FILT.items():
        x=A if fn=="немає фільтра" else A[Fa[A.si.to_numpy(int)]==A.side.to_numpy()]
        r=dict(cell=f"{tf} {sens}",filt=fn)
        for seg,m,mo in [("21",x.tr,48),("25",~x.tr,19.3)]:
            s=summ(x[m],mo); r.update({f"n{seg}":s["n"],f"ev{seg}":s["ev"],f"Rmo{seg}":s["Rmo"],f"rdd{seg}":s["rdd"]})
        rows.append(r)
R=pd.DataFrame(rows); R.to_csv("out_oos/LAB267_HTF_FILTERS.csv",index=False)
R["cellv"]=R.apply(lambda r:f"{r.ev21:+.2f}/{r.ev25:+.2f} ({r.n21:.0f})",axis=1)
pd.set_option("display.width",250)
print(R.pivot_table(index="filt",columns="cell",values="cellv",aggfunc="first",sort=False).to_string())
print("\nсереднє по 4 клітинках:"); print(R.groupby("filt",sort=False)[["n21","ev21","ev25","Rmo21","Rmo25","rdd21","rdd25"]].mean().round(2).to_string())
