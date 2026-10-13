import os, zipfile
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
BT,BO,BH,BL,BC,BA,N=L.BT,L.BO,L.BH,L.BL,L.BC,L.BA,L.N
BZ=np.asarray(L.C["BZ"],float)
# OI + ratio from flow
with zipfile.ZipFile("/home/claude/data/BTCUSDT_flow_2021-01-2026-08.csv.zip") as z:
    n=[x for x in z.namelist() if x.endswith(".csv")][0]; f=pd.read_csv(z.open(n))
tc=[c for c in f.columns if "time" in c.lower()][0]
f["time"]=pd.to_datetime(f[tc],utc=True,errors="coerce") if not pd.api.types.is_numeric_dtype(f[tc]) else pd.to_datetime(f[tc],unit="ms",utc=True)
oic=[c for c in f.columns if "sum_open_interest_value" in c][0]
f=f.dropna(subset=["time"]).sort_values("time").drop_duplicates("time").set_index("time")
oi=f[oic].astype(float).resample("5min").last().reindex(BT,method="ffill").to_numpy()
ratio=f["count_long_short_ratio"].astype(float).resample("5min").last().reindex(BT,method="ffill").to_numpy()
np.save("oi.npy",oi); np.save("ratio.npy",ratio)
c=pd.Series(BC); a=pd.Series(BA)
# 1) z vs past/future returns (in ATR), sampled hourly
rows=[]
for h in [1,6,24,48]:
    k=h*12
    past=(c-c.shift(k))/a; fut=(c.shift(-k)-c)/a
    rows.append(dict(h=h,corr_z_past=np.corrcoef(BZ[k:-k:12],past[k:-k:12])[0,1],corr_z_future=np.corrcoef(BZ[k:-k:12],fut[k:-k:12])[0,1]))
print(pd.DataFrame(rows).round(3))
# conditional: future 24h return (side = -sign z) when |z|>=1, by whether price already moved
k=24*12; fut24=((c.shift(-k)-c)/a).to_numpy(); past6=((c-c.shift(72))/a).to_numpy()
m=np.isfinite(fut24)&np.isfinite(past6)&(np.abs(BZ)>=1); idx=np.arange(N)[m][::12]
side=-np.sign(BZ[idx]); fr=side*fut24[idx]; pr=side*past6[idx]
q=pd.qcut(pr,5,labels=["моцно проти","проти","нейтр","за","моцно за"])
print("fade |z|>=1: fut24 in side, by prior 6h move in side (ATR)")
print(pd.DataFrame({"prior6":pr,"fut24":fr,"q":q}).groupby("q",observed=True).agg(prior6=("prior6","median"),fut24=("fut24","mean"),n=("fut24","size")).round(2))
print("unconditional |z|>=1 fade fut24 mean", fr.mean().round(3), "| all bars random-side ~0")
