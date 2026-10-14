import numpy as np,pandas as pd,alt,pickle
TE=pd.Timestamp("2025-01-01",tz="UTC"); OUT={}
assets={"BTC":"/home/claude/data/BTCUSDT_flow_2021-01-2026-08.csv.zip","ETH":"/home/claude/data/alt/ETH_flow.csv","SOL":"/home/claude/data/alt/SOL_flow.csv"}
V={"D":(2.0,1.0,True),"D2":(1.5,0.5,True),"D'":(2.0,1.0,False)}
rows=[]
for a,p in assets.items():
    M=alt.load(p); T0=pd.Timestamp("2022-01-01",tz="UTC")
    for nm,(x,zm,tr) in V.items():
        S=alt.signals(M,x,zm,tr)
        for fill in ("close","stop"):
            t,e=alt.sim(M,S,fill=fill); OUT[(a,nm,fill)]=(t,e)
            t=t[t.t>=T0]
            for seg,m,mo in [("2022-24",t.t<TE,36),("2025-26",t.t>=TE,(t.t.max()-TE).days/30.44)]:
                tt=t[m]; ee=e[(e.index>=T0)&((e.index<TE) if seg=="2022-24" else (e.index>=TE))]; ee=ee-ee.iloc[0]
                dd=float((ee.cummax()-ee).max())
                rows.append(dict(asset=a,var=nm,fill=fill,seg=seg,n_mo=len(tt)/mo,ev=tt.net_r.mean(),R_mo=tt.net_r.sum()/mo,R_dd=tt.net_r.sum()/dd))
            yr=t.groupby(t.t.dt.year).net_r.sum().round(1).to_dict()
            print(a,nm,fill,"R по роках:",yr,flush=True)
R=pd.DataFrame(rows); R.to_csv("out_oos/ALT_D.csv",index=False)
pickle.dump(OUT,open("alt_out.pkl","wb"))
pd.set_option("display.width",250)
print(R.pivot_table(index=["asset","var"],columns=["fill","seg"],values=["ev","R_mo","R_dd"],sort=False).round(2).to_string())
print(R[R.fill=="close"].pivot_table(index=["asset","var"],columns="seg",values="n_mo",sort=False).round(1).to_string())
