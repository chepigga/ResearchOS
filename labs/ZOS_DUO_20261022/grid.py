import pandas as pd,numpy as np,sys
sys.path.insert(0,"/home/claude/zr"); from z102 import run
P=pd.period_range("2022-10","2026-10",freq="M"); dd=lambda s:(s.cumsum().cummax()-s.cumsum()).max()
Ld=pd.read_pickle("/home/claude/duo/legs300.pkl"); Ld["m"]=pd.PeriodIndex(Ld.xt,freq="M")
D=Ld[Ld.leg=="D"].groupby("m").net.sum().reindex(P,fill_value=0)
Zt=Ld[Ld.leg=="Z"].groupby("m").net.sum().reindex(P,fill_value=0)
def zrep(mr):
    ev,piv=run(maxr=mr); R=pd.DataFrame([(x[0],x[6]) for x in ev if x[1]=="ENTRY"],columns=["t","R"]); R=R[R.t>="2022-10-01"]
    return R.groupby(R.t.dt.to_period("M")).R.sum().reindex(P,fill_value=0)*500
Zv={"Z тестер (ризик≤4ATR)":Zt,"Z копія ризик≤6ATR":zrep(6.0)}
out=pd.read_pickle("twoside.pkl"); f=pd.read_pickle("h4feat.pkl")
T=pd.concat([out["лонг EMA50 (як раніше)"],out["шорт повний тренд D1, вихід 1R"]]).sort_values("t").reset_index(drop=True)
T=pd.concat([T,f.reindex(T.t,method="ffill").reset_index(drop=True)],axis=1)
def brake(T,k=4,H=48):
    keep=[]; s=0; u=pd.Timestamp(0)
    for r in T.itertuples():
        if r.t<u: keep.append(False); continue
        keep.append(True)
        if r.R<0:
            s+=1
            if s>=k: u=r.xt+pd.Timedelta(hours=H); s=0
        else: s=0
    return T[np.array(keep)]
lm=lambda x:x[x.t>="2022-10-01"].groupby(x.t.dt.to_period("M")).R.sum().reindex(P,fill_value=0)*250
Lv={"без L":pd.Series(0.0,index=P),
    "L без фільтра H4":lm(T),
    "L без фільтра + гальмо":lm(brake(T)),
    "L H4 EMA20":lm(T[T["c>e20"]==T.s]),
    "L H4 структура":lm(T[T.struct!=-T.s]),
    "L H4 структура + гальмо":lm(brake(T[T.struct!=-T.s])),
    "L H4 EMA20 + структура":lm(T[(T["c>e20"]==T.s)&(T.struct!=-T.s)])}
rows=[];NEG={}
for zn,z in Zv.items():
    for ln,l in Lv.items():
        tot=z+D+l; neg=tot[tot<0]; NEG[(zn,ln)]=set(neg.index)
        rows.append((zn,ln,round(tot.sum()),round(dd(tot)),len(neg),round(tot.min()),", ".join(p.strftime("%y-%m") for p in neg.index)))
O=pd.DataFrame(rows,columns=["нога Z","нога L","прибуток $","просадка $","мінус-міс","гірший $","мінусові місяці"]).sort_values(["мінус-міс","просадка $"])
pd.set_option("display.width",320); pd.set_option("display.max_colwidth",200)
print(O.to_string(index=False))
pd.to_pickle(dict(Zv=Zv,Lv=Lv,D=D,NEG=NEG),"grid.pkl")
