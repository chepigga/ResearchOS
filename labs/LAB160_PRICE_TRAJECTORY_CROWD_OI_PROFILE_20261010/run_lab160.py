from pathlib import Path
import zipfile, io, numpy as np, pandas as pd
O=Path("lab160_out");O.mkdir(exist_ok=True)
def load(z):
 with zipfile.ZipFile(z) as f:
  names=[n for n in f.namelist() if n.endswith(".csv")]
  if not names:raise ValueError(z)
  return pd.concat([pd.read_csv(io.BytesIO(f.read(n))) for n in names],ignore_index=True)
def col(d,*names):
 m={c.lower().replace("_",""):c for c in d.columns}
 for n in names:
  if n.lower().replace("_","") in m:return m[n.lower().replace("_","")]
 raise ValueError((names,list(d.columns)))
def times(s):
 if pd.api.types.is_numeric_dtype(s):
  v=s.dropna().median();return pd.to_datetime(s,unit=("ms" if v>1e11 else "s"),utc=True)
 return pd.to_datetime(s,utc=True)
p=load("btc_5m.zip");f=load("BTCUSDT_flow_2021-01-2026-08.csv.zip")
p["t"]=times(p[col(p,"time","timestamp","open_time","datetime")])
for a,opts in {"o":("open",),"h":("high",),"l":("low",),"c":("close",),"v":("quote_volume","volume","base_volume")}.items():
 p[a]=pd.to_numeric(p[col(p,*opts)],errors="coerce")
p=p[["t","o","h","l","c","v"]].dropna().sort_values("t").drop_duplicates("t").reset_index(drop=True)
f["t"]=times(f[col(f,"create_time","time")])
f["ratio"]=pd.to_numeric(f[col(f,"count_long_short_ratio")],errors="coerce")
f["oi"]=pd.to_numeric(f[col(f,"sum_open_interest_value","sum_open_interest")],errors="coerce")
f=f[["t","ratio","oi"]].dropna().sort_values("t").drop_duplicates("t")
f["z"]=(f.ratio-f.ratio.rolling(72,min_periods=72).mean())/f.ratio.rolling(72,min_periods=72).std(ddof=0)
f["oi4h"]=f.oi/f.oi.shift(48)-1
p=pd.merge_asof(p,f[["t","z","oi4h"]],on="t",direction="backward",tolerance=pd.Timedelta(minutes=5))
# completed H1 ATR, never the current unfinished hour
h=p.set_index("t").resample("1h").agg({"h":"max","l":"min","c":"last"}).dropna()
tr=pd.concat([h.h-h.l,(h.h-h.c.shift()).abs(),(h.l-h.c.shift()).abs()],axis=1).max(axis=1)
h["atr"]=tr.rolling(14,min_periods=14).mean()
a=h[["atr"]].copy();a.index=a.index+pd.Timedelta(hours=1);a=a.reset_index()
p=pd.merge_asof(p,a,on="t",direction="backward")
# causal trailing 24h volume-at-price, computed only at sampling timestamps
def profile(w):
 lo=w.l.min();hi=w.h.max()
 if hi<=lo:return "NA",np.nan,np.nan,np.nan
 e=np.linspace(lo,hi,41);v=np.zeros(40)
 for r in w.itertuples():
  if r.h<=r.l:v[np.clip(np.searchsorted(e,r.c)-1,0,39)]+=r.v;continue
  v+=np.maximum(0,np.minimum(e[1:],r.h)-np.maximum(e[:-1],r.l))/(r.h-r.l)*r.v
 if v.sum()<=0:return "NA",np.nan,np.nan,np.nan
 centers=(e[:-1]+e[1:])/2;k=np.argmax(v);poc=centers[k];q1=lo+(hi-lo)/3;q2=lo+2*(hi-lo)/3
 low=v[centers<q1].sum()/v.sum();high=v[centers>q2].sum()/v.sum()
 peaks=np.argsort(v)[-2:]
 if abs(peaks[-1]-peaks[-2])>=10 and v[peaks[-2]]>=.7*v[peaks[-1]]:shape="DOUBLE"
 elif poc>=q2 and high>low*1.15:shape="P"
 elif poc<=q1 and low>high*1.15:shape="b"
 else:shape="D"
 L=R=k;acc=v[k]
 while acc<.7*v.sum() and (L>0 or R<39):
  if R<39 and (L==0 or v[R+1]>=v[L-1]):R+=1;acc+=v[R]
  else:L-=1;acc+=v[L]
 return shape,poc,e[L],e[R+1]
# nonoverlapping anchor cohorts at 1h spacing; future trajectory is LABEL only
N=len(p);step=12;maxh=48*12
rows=[]
for i in range(24*12+24*12,N-maxh,step):
 r=p.iloc[i]
 if not np.isfinite(r.atr) or r.atr<=0 or not np.isfinite(r.z) or not np.isfinite(r.oi4h):continue
 sh,poc,val,vah=profile(p.iloc[i-288:i])
 if sh=="NA":continue
 px=float(r.o);atr=float(r.atr)
 row=dict(time=r.t,year=r.t.year,shape=sh,z=float(r.z),abs_z=abs(float(r.z)),oi4h=float(r.oi4h),price=px,atr=atr,
          poc_dist_atr=(px-poc)/atr,location=("ABOVE" if px>vah else "BELOW" if px<val else "INSIDE"))
 for hours in (1,3,6,12,24,48):
  end=i+hours*12;future=p.iloc[i:end]
  up=(future.h.max()-px)/atr;dn=(px-future.l.min())/atr
  row[f"up_mfe_{hours}h"]=up;row[f"down_mfe_{hours}h"]=dn
  row[f"close_{hours}h"]=(float(p.c.iloc[end-1])-px)/atr
  for k in (1,2,3):
   ub=np.flatnonzero(future.h.to_numpy()>=px+k*atr);db=np.flatnonzero(future.l.to_numpy()<=px-k*atr)
   u=int(ub[0]) if len(ub) else 999999;d=int(db[0]) if len(db) else 999999
   row[f"first_{k}atr_{hours}h"]=("UP" if u<d else "DOWN" if d<u else "TIE" if u<999999 else "NONE")
 rows.append(row)
D=pd.DataFrame(rows);D["z_band"]=pd.cut(D.abs_z,[0,.6,1,1.5,2,np.inf],labels=["0-.6",".6-1","1-1.5","1.5-2","2+"])
D["oi_band"]=pd.cut(D.oi4h,[-np.inf,0,.0035,.00867,np.inf],labels=["NEG","0-.35%",".35-.867%",".867%+"])
D.to_csv(O/"LAB160_price_trajectory_atlas.csv",index=False)
s=[]
for keys,g in D.groupby(["shape","location","z_band","oi_band"],observed=True):
 if len(g)<25:continue
 for hr in (3,6,12,24,48):
  for k in (1,2,3):
   v=g[f"first_{k}atr_{hr}h"]
   s.append(dict(shape=keys[0],location=keys[1],z_band=str(keys[2]),oi_band=str(keys[3]),horizon_h=hr,threshold_atr=k,
                 n=len(g),p_up_first=(v=="UP").mean(),p_down_first=(v=="DOWN").mean(),p_none=(v=="NONE").mean(),p_tie=(v=="TIE").mean(),
                 mean_close_atr=g[f"close_{hr}h"].mean(),mean_up_mfe=g[f"up_mfe_{hr}h"].mean(),mean_down_mfe=g[f"down_mfe_{hr}h"].mean()))
S=pd.DataFrame(s);S.to_csv(O/"LAB160_state_matrix.csv",index=False)
report=["# LAB160 PRICE TRAJECTORY × CROWD × OI × PROFILE STATE ATLAS","",
"Research only: no entries, stops, exits, sizing, or return-optimized thresholds.",
"Anchors every completed hour; horizon labels 1/3/6/12/24/48h. Forward H/L thresholds evaluated from anchor M5 open; simultaneous within-bar threshold crossings are TIE, not wins.",
"Profile: trailing 24h, 40 bins, reconstructed uniform bar volume across M5 high-low. Only past bars are used.",
"ATR: previous completed H1 rolling ATR14; Z: 72 M5 rolling global account ratio; OI: trailing 4h.",
"IMPORTANT: hourly anchors have overlapping future outcomes. N is not independent sample size; statistical inference needs block bootstrap.",
f"Rows: {len(D)}. Matrix rows (min25 per state): {len(S)}.","",
"## Coverage",D.groupby('year').size().to_string(),"",
"## Shape counts",D.groupby('shape').size().to_string(),"",
"## Preliminary descriptive table: 12h first ±2 ATR, by shape"]
for sh,g in D.groupby("shape"):
 v=g["first_2atr_12h"];report.append(f"- {sh}: N={len(g)}, UP={(v=='UP').mean():.3f}, DOWN={(v=='DOWN').mean():.3f}, NONE={(v=='NONE').mean():.3f}")
report+=["","Do not infer a profitable EA or a calibrated probability from this atlas. Next: LAB161 walk-forward directional quality model with purged/embargoed folds, followed by LAB162 execution/cost transfer."]
(O/"LAB160_REPORT.md").write_text("\n".join(report)+"\n")
print("\n".join(report))
