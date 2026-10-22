import pandas as pd,numpy as np,sys
sys.path.insert(0,"/home/claude/zr"); from z102 import *
d1=pd.read_pickle("/home/claude/xau/d1.pkl")
tr=pd.concat([d1.high-d1.low,(d1.high-d1.close.shift()).abs(),(d1.low-d1.close.shift()).abs()],axis=1).max(axis=1)
atrd=(tr.rolling(14).mean()/d1.close).shift(1)          # ATR D1 у частках ціни, відомий до дня
ad=atrd.reindex(m15.index.normalize()).values
res={}
for nm,arr in [("фікс 0.8% (оригінал)",None)]+[(f"адаптивний {k}×ATR_D1",k*ad) for k in (0.4,0.5,0.6,0.7)]+[("адаптивний 0.5×ATR_D1, мін 0.5%",np.maximum(0.5*ad,0.005))]:
    ev,piv=run(dev_arr=arr)
    R=pd.DataFrame([(x[0],x[6]) for x in ev if x[1]=="ENTRY"],columns=["t","R"]); E=pd.DataFrame([x[:3] for x in ev],columns=["t","ev","d"])
    res[nm]=(R,E)
pd.to_pickle(res,"/home/claude/zr/adapt.pkl")
