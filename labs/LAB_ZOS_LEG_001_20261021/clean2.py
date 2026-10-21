import pandas as pd,numpy as np
exec(open("octs.py").read().split("exits=")[0])
F=pd.read_pickle("cleanF.pkl"); S={(tf,nm):sig for tf,nm,sig in strats}
er20=F["ER20"]
top=[("M15","RSI2 10/90 фейд",2.0,"ma",24),("M15","PDH/PDL фейд",1.0,2.0,8),("M15","Donchian20 фейд",2.0,2.0,24),("H1","RSI2 20/80 фейд",1.0,2.0,8)]
allT=[]
for tf,nm,s,t,hd in top:
    b=B[tf]; sg=S[(tf,nm)].copy(); sg[:60]=0
    r=pd.DataFrame(run(b,sg,s,t,hd,0),columns=["t","R"]); r["d"]=r.t.dt.normalize()
    dR=r.groupby("d").R.sum().reindex(d1.index,fill_value=0)
    feat=F.copy(); feat["фейд R за 10дн"]=dR.rolling(10).sum().shift(1); feat["фейд R за 20дн"]=dR.rolling(20).sum().shift(1)
    r=r.join(feat,on="d"); r["st"]=nm+" "+tf; allT.append(r)
T=pd.concat(allT); T["h"]=np.where(T.t<"2024-07-01","A","B")
T.to_pickle("cleanT.pkl")
cols=[c for c in T.columns if c not in ("t","R","d","st","h")]
pd.set_option("display.width",250)
for st,g in T.groupby("st"):
    g=g[g.ER20<0.2]
    print(f"\n=== {st}  (лише коридор ER20<0.2, n={len(g)}, сер {g.R.mean():+.3f}) — R/угоду по квінтилях ознаки, Q1=найменші; [A=22-24.06 | B=24.07-26]")
    for f in cols:
        q=pd.qcut(g[f],5,labels=False,duplicates="drop")
        a=g.groupby(q).R.mean(); hA=g[g.h=="A"].groupby(q[g.h=="A"]).R.mean(); hB=g[g.h=="B"].groupby(q[g.h=="B"]).R.mean()
        print(f"{f:22s} "+"  ".join(f"{a.get(i,np.nan):+.3f}[{hA.get(i,np.nan):+.2f}|{hB.get(i,np.nan):+.2f}]" for i in range(5)))
