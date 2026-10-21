import pandas as pd,numpy as np
T=pd.read_pickle("/tmp/claude-0/-home-claude/879a62a8-009b-5e46-ab07-25d07c2b7f01/scratchpad/zos2/r1.xlsx.pkl")
Z=T.groupby(T.xt.dt.to_period("M")).net.sum()
d=pd.read_pickle("d1.pkl"); d=d[d.index.dayofweek<5]
d["rng"]=d.high-d.low; d["atr"]=d.rng.rolling(14).mean(); d["med120"]=d.rng.rolling(120).median()
M=[]
for p,g in d.groupby(d.index.to_period("M")):
    if len(g)<10: continue
    prev=d[d.index<g.index[0]]
    if len(prev)<130: continue
    atr=prev.atr.iloc[-1]; c0=prev.close.iloc[-1]
    net=g.close.iloc[-1]-c0; path=np.abs(g.close.diff().fillna(g.close.iloc[0]-c0)).sum()
    M.append(dict(m=p,ret=net/atr,vol=g.rng.mean()/prev.med120.iloc[-1],er=abs(net)/path,
                  pre60=(c0-prev.close.iloc[-61])/atr, rng_m=(g.high.max()-g.low.min())/atr))
M=pd.DataFrame(M).set_index("m"); M["zos"]=Z.reindex(M.index).fillna(0)
M=M[M.index>=pd.Period("2022-06","M")]
pd.set_option("display.width",200)
print(M.round(2).to_string())
print("\nкореляції з результатом ZOS:",M.corr()["zos"].round(2).to_dict())
for c in ("ret","vol","er","pre60"):
    q=pd.qcut(M[c],3,labels=["низ","сер","верх"]); print(c,M.groupby(q,observed=True).zos.agg(["mean","count",lambda s:(s<0).mean()]).round(2).to_dict("index"))
M.to_pickle("months.pkl")
