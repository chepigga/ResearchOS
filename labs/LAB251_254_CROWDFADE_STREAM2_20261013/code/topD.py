import os, zipfile
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import engD as E
BT,BO,BH,BL,BC,BA,N,TE,COST=E.BT,E.BO,E.BH,E.BL,E.BC,E.BA,E.N,E.TE,E.COST
z=zipfile.ZipFile("/home/claude/data/BTCUSDT_flow_2021-01-2026-08.csv.zip"); n=[x for x in z.namelist() if x.endswith(".csv")][0]
f=pd.read_csv(z.open(n)); f["time"]=pd.to_datetime(f.create_time,utc=True,errors="coerce")
f=f.dropna(subset=["time"]).drop_duplicates("time").set_index("time").sort_index()
def ser(col): return f[col].astype(float).resample("5min").last().reindex(BT,method="ffill")
def zz(s,w): m=s.rolling(w,min_periods=w).mean(); sd=s.rolling(w,min_periods=w).std(ddof=0); return ((s-m)/sd).to_numpy()
topA=ser("count_toptrader_long_short_ratio"); topP=ser("sum_toptrader_long_short_ratio"); tak=ser("sum_taker_long_short_vol_ratio")
F={"топ-акаунти z24":zz(topA,288),"топ-позиції z24":zz(topP,288),"топ-позиції z6":zz(topP,72),
   "taker z6":zz(np.log(tak),72),"taker за 1 год (log сума)":np.log(tak).rolling(12).sum().to_numpy()}
c=pd.Series(BC); f24=((c.shift(-288)-c)/pd.Series(BA)).to_numpy()
def solo(i,s):
    e0=BO[i]; R=3*BA[i]; end=min(i+576-1,N-1)
    for j in range(i,end+1):
        if (BL[j]<=e0-R) if s>0 else (BH[j]>=e0+R): return -1-COST/1e4*e0/R
    return s*(BC[end]-e0)/R-COST/1e4*e0/R
rows=[]
for i,sd in E.SIG:
    r=dict(seg="2021-24" if BT[i]<TE else "2025-26",drift24=sd*f24[i],R=solo(i+1,sd))
    for k,v in F.items(): r[k]=sd*v[i]   # >0: метрика "на нашому боці" (великі/агресори в бік угоди)
    rows.append(r)
D=pd.DataFrame(rows)
print("сигналів D:",D.groupby("seg").size().to_dict())
pd.set_option("display.width",250)
for k in F:
    thr=0.5 if "z" in k else 0.0
    D["cat"]=np.where(D[k]>thr,"на нашому боці",np.where(D[k]<-thr,"проти нас","нейтрально"))
    g=D.dropna(subset=[k]).groupby(["cat","seg"]).agg(n=("R","size"),R=("R","mean"),drift24=("drift24","mean")).unstack("seg").round(2)
    print(f"\n== {k}  (поріг {thr})"); print(g.to_string())
