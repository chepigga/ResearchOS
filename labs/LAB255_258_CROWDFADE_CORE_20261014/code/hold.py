import io,contextlib,numpy as np,pandas as pd
exec(open("sw260.py").read().split("\nrows=[]")[0].replace('done.append(dict(entry_i=q["i0"],net_r=r,d_atr=q["d"]/q["a"]))','done.append(dict(entry_i=q["i0"],exit_i=i,net_r=r,d_atr=q["d"]/q["a"],pk=q["pk"]/q["d"],why=("stop" if res is not None and i<q["end"] and q["pk"]<6*q["a"] else ("trail" if i<q["end"] else "time"))))'))
t,e=sim(entries("NOW",0,"ATR3"))
t["h"]=(t.exit_i-t.entry_i)*5/60; t["seg"]=np.where(BT[t.entry_i.to_numpy(int)]<TE,"21-24","25-26")
print("== D2: утримання (год)"); print(t.groupby("seg").h.describe(percentiles=[.25,.5,.75]).round(1).to_string())
print(t.groupby(["seg","why"]).agg(n=("h","size"),h_med=("h","median"),R=("net_r","mean"),R_sum=("net_r","sum")).round(2).to_string())
t["pkb"]=pd.cut(t.pk,[-1,0.5,1,2,3,100],labels=["<0.5R","0.5-1R","1-2R","2-3R",">3R"])
print("\nмакс. прибуток під час угоди (пік, R) -> чим закінчилась:"); print(t.groupby(["seg","pkb"],observed=True).agg(n=("h","size"),R=("net_r","mean")).round(2).to_string())
# time in market
inm=np.zeros(N,bool)
for r in t.itertuples(): inm[int(r.entry_i):int(r.exit_i)+1]=True
for seg,m in [("21-24",BT<TE),("25-26",BT>=TE)]: print(seg,"D у ринку частку часу:",round(inm[m].mean(),2))
# A/B3 hold
L,TLD,RAW=g["g"]["L"],g["g"]["TLD"],g["g"]["RAW"]
tv,_,_,_=L.replay(7.5,{},TLD,raw=RAW[RAW.source.isin(["A","B3_HIGH"])].reset_index(drop=True))
tv["h"]=(tv.exit_i-tv.entry_i)*5/60
print("\nA/B3 утримання (год):"); print(tv.groupby("source").h.describe(percentiles=[.5]).round(1).to_string())
