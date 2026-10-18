"""Step 0: does M5-OHLCV volume profile reproduce the aggTrades (per-second VWAP) profile? 2026-03..2026-08."""
import numpy as np,pandas as pd,zipfile
from vp import *
d=pd.read_pickle("/home/claude/lab251/v5m.pkl")
z=zipfile.ZipFile("/home/claude/data/sec/BTCUSDT_sec.csv.zip")
S=pd.read_csv(z.open("BTCUSDT_sec.csv"),usecols=["ts","h","l","bv","sv","bnot","snot"],dtype={"ts":np.int64})
S=S[(S.bv+S.sv)>0]; S["t"]=pd.to_datetime(S.ts,unit="s",utc=True)
t0,t1=S.t.min().floor("1h"),min(S.t.max(),d.index[-1]).floor("1h"); print(t0,t1,len(S))
hours=pd.date_range(t0,t1,freq="1h")
S=S[S.t<t1+pd.Timedelta("1h")]
vw=(S.bnot+S.snot)/(S.bv+S.sv)
Ms=hourly_from_points(pd.DatetimeIndex(S.t),vw.to_numpy(),(S.bv+S.sv).to_numpy(),hours)
x=d[(d.index>=t0)&(d.index<t1+pd.Timedelta("1h"))]
Mb=hourly_from_bars(x.index,x.low.to_numpy(),x.high.to_numpy(),x.volume.to_numpy(),hours)
print("total vol sec vs 5m:",Ms.sum()/Mb.sum())
Cs=np.vstack([np.zeros(NB,np.float32),np.cumsum(Ms,0)]); Cb=np.vstack([np.zeros(NB,np.float32),np.cumsum(Mb,0)])
rows=[]
for W in (72,168,336):
    for h in range(W,len(hours),24):
        ps,pb=window(Cs,h,W),window(Cb,h,W)
        ss,pks,lvs=nodes(ps); sb,pkb,lvb=nodes(pb)
        nz=(ss>0)|(sb>0); cor=np.corrcoef(ss[nz],sb[nz])[0,1]
        Ls=np.array([m for a,m,c in lvs]); Lb=np.array([m for a,m,c in lvb])
        lv_match=np.mean([np.min(np.abs(Ls-m))<=2 for m in Lb]) if len(Lb) and len(Ls) else np.nan
        hv_match=np.mean([np.min(np.abs(pks-m))<=2 for m in pkb]) if len(pkb) and len(pks) else np.nan
        poc=abs(int(np.argmax(ss))-int(np.argmax(sb)))
        rows.append(dict(W=W,cor=cor,lvn_match=lv_match,hvn_match=hv_match,poc_bins=poc,n_hvn_s=len(pks),n_hvn_b=len(pkb),n_lvn_s=len(lvs),n_lvn_b=len(lvb)))
R=pd.DataFrame(rows)
print(R.groupby("W").agg(cor=("cor","mean"),cor_min=("cor","min"),hvn_match=("hvn_match","mean"),lvn_match=("lvn_match","mean"),
      poc_same=("poc_bins",lambda s:(s<=2).mean()),n_hvn=("n_hvn_s","mean"),n_lvn=("n_lvn_s","mean"),n_lvn_5m=("n_lvn_b","mean")).round(3).to_string())
R.to_csv("step0.csv",index=False)
