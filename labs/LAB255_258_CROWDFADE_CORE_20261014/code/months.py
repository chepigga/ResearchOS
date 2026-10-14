import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L, engD3 as D3
tv,ev,_,_=L.replay(7.5,{},dict(mtr=np.zeros(L.N,int),ci=np.zeros(L.N,int),swl=None,swh=None,catr=None))
eqV=pd.Series(ev.equity_r.to_numpy(),index=pd.DatetimeIndex(ev.time)); eqV=eqV[~eqV.index.duplicated(keep="last")]
td,eqD=D3.sim(48,3); eqD=eqD[~eqD.index.duplicated(keep="last")]
idx=L.BT
def al(s): return s.reindex(s.index.union(idx)).ffill().reindex(idx).ffill().fillna(0.0)
V=al(eqV); Dd=al(eqD)
me=lambda s: s.groupby(s.index.tz_convert("UTC").strftime("%Y-%m")).last().diff().fillna(s.groupby(s.index.tz_convert("UTC").strftime("%Y-%m")).last().iloc[0])
mV=me(V)*0.25; mD=me(Dd)*0.10; mP=mV+mD
M=pd.DataFrame({"v157":mV,"D":mD,"разом":mP}).iloc[:-1]   # drop partial last month (Aug 2026, 10 days)
M["seg"]=np.where(M.index<"2025-01","2021-24","2025-26")
pd.set_option("display.width",200)
for c in ["v157","D","разом"]:
    g=M.groupby("seg")[c]
    print(c, {s:dict(months=len(x),losing=int((x<0).sum()),share=round((x<0).mean(),2),worst=round(x.min(),2)) for s,x in g})
# streaks for combined
x=(M["разом"]<0).astype(int); st=mx=0
for v in x: st=st+1 if v else 0; mx=max(mx,st)
print("max losing streak (combined):",mx)
print("losing months combined (% of account, risk 0.25/0.10):")
print(M[M["разом"]<0][["v157","D","разом"]].round(2).to_string())
q=M.groupby(M.index.str[:4])["разом"].sum().round(2); print("by year %:",q.to_dict())
