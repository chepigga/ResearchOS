import os; os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np,pandas as pd,alt, lab251 as Lb
M=alt.load("/home/claude/data/BTCUSDT_flow_2021-01-2026-08.csv.zip")
a=pd.Series(M["A"],index=M["T"]); b=pd.Series(Lb.BA,index=Lb.BT); j=pd.concat([a,b],axis=1,join="inner").dropna()
print("ATR proxy / real ATR median:",round((j.iloc[:,0]/j.iloc[:,1]).median(),3))
TE=pd.Timestamp("2025-01-01",tz="UTC")
for fill in ("close","stop"):
  for nm,(x,zm,tr) in {"D":(2.0,1.0,True),"D2":(1.5,0.5,True),"D'":(2.0,1.0,False)}.items():
    t,e=alt.sim(M,alt.signals(M,x,zm,tr),fill=fill)
    for seg,m,mo in [("2021-24",t.t<TE,48),("2025-26",t.t>=TE,19.3)]:
        tt=t[m]; print(f"BTC-proxy fill={fill} {nm} {seg}: {len(tt)/mo:.1f}/міс EV {tt.net_r.mean():+.3f} R/міс {tt.net_r.sum()/mo:+.2f}")
