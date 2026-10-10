from __future__ import annotations
import json, re, zipfile
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab160_out");OUT.mkdir(exist_ok=True)

PROFILE_H=24
PROFILE_BINS=40
VALUE_FRAC=0.70
ANCHOR_MINUTES=60
HORIZONS_H=[1,3,6,12,24,48]
LEVELS=[0.5,1.0,2.0,3.0]

def norm(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())
def pick(cols,prefs):
    nc={norm(c):c for c in cols}
    for p in prefs:
        if norm(p) in nc:return nc[norm(p)]
    for p in prefs:
        pp=norm(p)
        for k,v in nc.items():
            if pp in k or k in pp:return v
    return None

def load_zip(zp):
    with zipfile.ZipFile(zp) as z:
        fs=[]
        for n in z.namelist():
            if not n.lower().endswith(".csv"): continue
            with z.open(n) as fh:
                d=pd.read_csv(fh)
            if len(d): fs.append(d)
        if not fs: raise RuntimeError(f"no csv in {zp}")
        if len(fs)==1:return fs[0]
        common=set(fs[0].columns)
        for d in fs[1:]: common &= set(d.columns)
        cols=list(common)
        return pd.concat([d[cols] for d in fs],ignore_index=True)

def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors="coerce")
        med=float(x.dropna().median()) if x.notna().any() else 0
        unit="ns" if med>1e17 else ("us" if med>1e14 else ("ms" if med>1e11 else "s"))
        return pd.to_datetime(x,unit=unit,utc=True,errors="coerce")
    return pd.to_datetime(s,utc=True,errors="coerce")

# ---------- 5m BTC OHLCV ----------
raw=load_zip(Path("btc_5m.zip"))
tc=pick(raw.columns,["time","timestamp","open_time","datetime"])
oc=pick(raw.columns,["open"]);hc=pick(raw.columns,["high"]);lc=pick(raw.columns,["low"]);cc=pick(raw.columns,["close"])
vc=pick(raw.columns,["quote_volume","quoteassetvolume","volume","base_volume","vol"])
if None in (tc,oc,hc,lc,cc) or vc is None:
    raise RuntimeError(f"missing price/volume columns {list(raw.columns)}")
p=raw[[tc,oc,hc,lc,cc,vc]].copy()
p["time"]=ptime(p[tc])
for c,n in [(oc,"open"),(hc,"high"),(lc,"low"),(cc,"close"),(vc,"volume")]:
    p[n]=pd.to_numeric(p[c],errors="coerce")
p=p[["time","open","high","low","close","volume"]].dropna().sort_values("time").drop_duplicates("time",keep="last")
p=p.set_index("time").resample("5min").agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),volume=("volume","sum")).dropna().reset_index()

# ---------- completed H1 ATR14 ----------
h1=p.set_index("time").resample("1h",label="left",closed="left").agg(
    open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1["atr14"]=tr.rolling(14,min_periods=14).mean()
h1["close_time"]=h1.time+pd.Timedelta(hours=1)

# ---------- flow ----------
fr=load_zip(Path("BTCUSDT_flow_2021-01-2026-08.csv.zip"))
ft=pick(fr.columns,["create_time","time"])
ratio_col=pick(fr.columns,["count_long_short_ratio"])
oi_col=pick(fr.columns,["sum_open_interest_value","sum_open_interest"])
if None in (ft,ratio_col,oi_col):
    raise RuntimeError(f"flow columns missing {list(fr.columns)}")
f=fr[[ft,ratio_col,oi_col]].copy()
f["time"]=ptime(f[ft])
f["ratio"]=pd.to_numeric(f[ratio_col],errors="coerce")
f["oi"]=pd.to_numeric(f[oi_col],errors="coerce")
f=f.dropna().sort_values("time").drop_duplicates("time",keep="last")
f=f[(f.ratio>0)&(f.oi>0)].set_index("time").resample("5min").last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean()
sd=f.ratio.rolling(72,min_periods=72).std(ddof=0)
f["z"]=(f.ratio-mu)/sd.replace(0,np.nan)
for h in [1,4,12,24]:
    f[f"oi_{h}h"]=f.oi/f.oi.shift(h*12)-1

# ---------- causal profile ----------
def vap_profile(w,bins=PROFILE_BINS):
    lo=float(w.low.min());hi=float(w.high.max())
    if not np.isfinite(lo+hi) or hi<=lo:return None
    edges=np.linspace(lo,hi,bins+1);v=np.zeros(bins,float)
    span=(w.high-w.low).to_numpy(float)
    lows=w.low.to_numpy(float); highs=w.high.to_numpy(float); vols=w.volume.to_numpy(float); closes=w.close.to_numpy(float)
    for a,b,vol,cl in zip(lows,highs,vols,closes):
        if not np.isfinite(vol) or vol<=0: continue
        if b<=a:
            k=min(bins-1,max(0,int((cl-lo)/(hi-lo)*bins)));v[k]+=vol;continue
        k0=max(0,min(bins-1,int(np.floor((a-lo)/(hi-lo)*bins))))
        k1=max(0,min(bins-1,int(np.floor((b-lo)/(hi-lo)*bins))))
        for k in range(k0,k1+1):
            ol=max(a,edges[k]);oh=min(b,edges[k+1])
            if oh>ol:v[k]+=vol*(oh-ol)/(b-a)
    if v.sum()<=0:return None
    centers=(edges[:-1]+edges[1:])/2
    poc=int(np.argmax(v));target=VALUE_FRAC*v.sum()
    L=R=poc;tot=v[poc]
    while tot<target and (L>0 or R<bins-1):
        lv=v[L-1] if L>0 else -1;rv=v[R+1] if R<bins-1 else -1
        if rv>=lv and R<bins-1:R+=1;tot+=v[R]
        elif L>0:L-=1;tot+=v[L]
        else:break
    return dict(lo=lo,hi=hi,edges=edges,vol=v,centers=centers,
                poc=float(centers[poc]),val=float(edges[L]),vah=float(edges[R+1]))

def shape_name(prof):
    centers=prof["centers"];v=prof["vol"];tot=v.sum()
    q1=prof["lo"]+(prof["hi"]-prof["lo"])/3
    q2=prof["lo"]+2*(prof["hi"]-prof["lo"])/3
    poc=prof["poc"];low=v[centers<q1].sum()/tot;high=v[centers>q2].sum()/tot
    peaks=np.argsort(v)[-2:]
    double=(abs(int(peaks[-1])-int(peaks[-2]))>=max(6,len(v)//4) and v[peaks[-2]]>=0.70*v[peaks[-1]])
    if double:return "DOUBLE"
    if poc>=q2 and high>low*1.15:return "P"
    if poc<=q1 and low>high*1.15:return "b"
    return "D"

def local_density(prof,price):
    k=int(np.searchsorted(prof["edges"],price,side="right")-1)
    k=min(len(prof["vol"])-1,max(0,k))
    return float(prof["vol"][k]/max(prof["vol"].mean(),1e-12))

# Hourly unbiased anchors, no trading-entry filters.
p_idx={pd.Timestamp(t):i for i,t in enumerate(p.time)}
start=max(p.time.min(),f.time.min())+pd.Timedelta(hours=PROFILE_H+24)
end=min(p.time.max(),f.time.max())-pd.Timedelta(hours=max(HORIZONS_H))
anchors=pd.date_range(start.ceil(f"{ANCHOR_MINUTES}min"),end.floor(f"{ANCHOR_MINUTES}min"),freq=f"{ANCHOR_MINUTES}min",tz="UTC")

rows=[]
for n,at in enumerate(anchors):
    i=int(p.time.searchsorted(at,side="left"))
    if i<PROFILE_H*12 or i>=len(p):continue
    atrr=h1[h1.close_time<=at].tail(1)
    flow=f[f.time<=at].tail(1)
    if atrr.empty or flow.empty:continue
    atr=float(atrr.atr14.iloc[0])
    z=float(flow.z.iloc[0])
    if not np.isfinite(atr) or atr<=0 or not np.isfinite(z):continue

    prof=vap_profile(p.iloc[i-PROFILE_H*12:i])
    oldi=max(0,i-6*12)
    oldprof=vap_profile(p.iloc[max(0,oldi-PROFILE_H*12):oldi]) if oldi>=PROFILE_H*12 else None
    if prof is None:continue
    px=float(p.open.iloc[i])
    zone="ABOVE_VAH" if px>prof["vah"] else ("BELOW_VAL" if px<prof["val"] else "VALUE")
    pos=(px-prof["poc"])/atr
    mig=(prof["poc"]-oldprof["poc"])/atr if oldprof is not None else np.nan

    row=dict(time=at,price=px,atr=atr,z=z,abs_z=abs(z),
             crowd_side=("LONG_HEAVY" if z>0 else "SHORT_HEAVY"),
             oi1h=float(flow["oi_1h"].iloc[0]),oi4h=float(flow["oi_4h"].iloc[0]),
             oi12h=float(flow["oi_12h"].iloc[0]),oi24h=float(flow["oi_24h"].iloc[0]),
             profile_shape=shape_name(prof),profile_zone=zone,
             poc=prof["poc"],val=prof["val"],vah=prof["vah"],
             poc_pos_atr=pos,poc_migration_atr=mig,local_density=local_density(prof,px))

    maxbars=max(HORIZONS_H)*12
    future=p.iloc[i:i+maxbars]
    if len(future)<maxbars:continue
    highs=future.high.to_numpy(float);lows=future.low.to_numpy(float);closes=future.close.to_numpy(float)
    for h in HORIZONS_H:
        nb=h*12;hh=highs[:nb];ll=lows[:nb]
        row[f"close_{h}h_atr"]=(float(closes[nb-1])-px)/atr
        row[f"mfe_up_{h}h_atr"]=(float(np.max(hh))-px)/atr
        row[f"mfe_dn_{h}h_atr"]=(px-float(np.min(ll)))/atr
        row[f"range_{h}h_atr"]=(float(np.max(hh))-float(np.min(ll)))/atr
        row[f"dir_{h}h"]="UP" if row[f"close_{h}h_atr"]>0 else ("DOWN" if row[f"close_{h}h_atr"]<0 else "FLAT")
    for lv in LEVELS:
        up_idx=np.where(highs>=px+lv*atr)[0]
        dn_idx=np.where(lows<=px-lv*atr)[0]
        u=int(up_idx[0]) if len(up_idx) else 10**9
        d=int(dn_idx[0]) if len(dn_idx) else 10**9
        if u==10**9 and d==10**9:first="NONE"
        elif u<d:first="UP"
        elif d<u:first="DOWN"
        else:first="BOTH"
        row[f"first_{lv:g}atr"]=first
        row[f"t_up_{lv:g}atr_h"]=u/12 if u<10**9 else np.nan
        row[f"t_dn_{lv:g}atr_h"]=d/12 if d<10**9 else np.nan
    rows.append(row)

A=pd.DataFrame(rows)
if A.empty:raise RuntimeError("no atlas rows")

# Frozen state buckets, descriptive only.
A["z_bucket"]=pd.cut(A.abs_z,[-np.inf,.5,.75,1.0,1.5,2.0,np.inf],
                     labels=["<.5",".5-.75",".75-1","1-1.5","1.5-2",">=2"],right=False)
A["oi4_bucket"]=pd.cut(A.oi4h,[-np.inf,-.00867,-.0035,0,.0035,.00867,np.inf],
                       labels=["<=-.867%","-.867--.35%","-.35-0","0-.35%",".35-.867%",">=.867%"],right=False)
A["density_bucket"]=pd.cut(A.local_density,[-np.inf,.6,1.0,1.4,np.inf],
                           labels=["LOW","MIDLOW","MIDHIGH","HIGH"],right=False)
A.to_csv(OUT/"LAB160_atlas.csv",index=False)

def agg(g,h):
    c=g[f"close_{h}h_atr"].to_numpy(float)
    up=g[f"mfe_up_{h}h_atr"].to_numpy(float);dn=g[f"mfe_dn_{h}h_atr"].to_numpy(float)
    return dict(n=len(g),close_mean=float(np.mean(c)),close_median=float(np.median(c)),
                p_close_up=float(np.mean(c>0)),mfe_up_mean=float(np.mean(up)),mfe_dn_mean=float(np.mean(dn)),
                asym=float(np.mean(up-dn)))

# 1D feature summaries
summ=[]
for feat in ["profile_shape","profile_zone","z_bucket","oi4_bucket","density_bucket","crowd_side"]:
    for val,g in A.groupby(feat,observed=True):
        if len(g)<50:continue
        for h in HORIZONS_H:
            summ.append(dict(feature=feat,value=str(val),horizon_h=h,**agg(g,h)))
S=pd.DataFrame(summ);S.to_csv(OUT/"LAB160_feature_summary.csv",index=False)

# Joint state atlas. No outcome-driven threshold fitting.
joint=[]
keys=["profile_shape","profile_zone","z_bucket","oi4_bucket","crowd_side"]
for vals,g in A.groupby(keys,observed=True):
    if len(g)<30:continue
    for h in [6,12,24,48]:
        q=agg(g,h)
        joint.append(dict(**{k:str(v) for k,v in zip(keys,vals)},horizon_h=h,**q))
J=pd.DataFrame(joint);J.to_csv(OUT/"LAB160_joint_state_atlas.csv",index=False)

# First-hit directional table for meaningful move labels.
hit=[]
for lv in LEVELS:
    col=f"first_{lv:g}atr"
    for (shape,zone,zb,ob),g in A.groupby(["profile_shape","profile_zone","z_bucket","oi4_bucket"],observed=True):
        if len(g)<30:continue
        vcx=g[col].value_counts(normalize=True)
        hit.append(dict(level_atr=lv,profile_shape=str(shape),profile_zone=str(zone),z_bucket=str(zb),oi4_bucket=str(ob),
                        n=len(g),p_up=float(vcx.get("UP",0)),p_down=float(vcx.get("DOWN",0)),
                        p_none=float(vcx.get("NONE",0)),p_both=float(vcx.get("BOTH",0)),
                        edge=float(vcx.get("UP",0)-vcx.get("DOWN",0))))
H=pd.DataFrame(hit);H.to_csv(OUT/"LAB160_first_hit_atlas.csv",index=False)

# Surface top descriptive states at 24h, minimum n=60.
top=J[(J.horizon_h==24)&(J.n>=60)].copy()
top["abs_asym"]=top.asym.abs()
top=top.sort_values(["abs_asym","n"],ascending=[False,False]).head(30)
top.to_csv(OUT/"LAB160_top_24h_states.csv",index=False)

lines=["# LAB160 — PRICE TRAJECTORY × CROWD × OI × PROFILE STATE ATLAS","",
"Purpose: rebuild from price movement first. There are NO entry rules, no SL/TP, no A/B3/R48 gates, and no portfolio logic in this LAB.",
f"Universe: unbiased BTC anchors every {ANCHOR_MINUTES} minutes.",
f"Profile: causal trailing {PROFILE_H}h, {PROFILE_BINS} bins, 70% value area, reconstructed from M5 OHLCV.",
"Context at each anchor: global crowd Z (72xM5), OI change 1/4/12/24h, profile shape, VAH/VAL/POC zone, local volume density, POC migration.",
"Future-only labels: close displacement, upside/downside MFE, range at 1/3/6/12/24/48h, and first hit of +/-0.5/1/2/3 ATR.",
"All thresholds are frozen descriptive buckets; no P/L optimization and no trade selection.","",
f"Atlas rows: {len(A):,}.",
"",
"## Strongest descriptive 24h joint states (absolute MFE asymmetry; n>=60)"
]
for _,r in top.iterrows():
    lines.append(f"- {r.profile_shape}/{r.profile_zone}/Z {r.z_bucket}/OI4 {r.oi4_bucket}/{r.crowd_side}: N={int(r.n)}, close={r.close_mean:+.3f}ATR, P(up close)={r.p_close_up:.1%}, MFEup={r.mfe_up_mean:.2f}, MFEdn={r.mfe_dn_mean:.2f}, asym={r.asym:+.2f}ATR")

# global baseline trajectory
lines+=["","## Global baseline"]
for h in HORIZONS_H:
    q=agg(A,h)
    lines.append(f"- {h}h: close={q['close_mean']:+.3f}ATR, P(up)={q['p_close_up']:.1%}, MFEup={q['mfe_up_mean']:.2f}, MFEdn={q['mfe_dn_mean']:.2f}, asym={q['asym']:+.2f}ATR")

lines+=["","## Decision discipline",
"LAB160 does not define trades. Its job is to identify repeatable market states that precede directional movement.",
"Next LAB should freeze a small number of state hypotheses from this atlas and test direction classification without execution rules.",
"Because volume-at-price is reconstructed from M5 bars, any promising profile mechanism should later be checked on the second-level/tick-native dataset.",
"BTC data used here is development data already inspected in prior research; this is not pristine OOS validation."]
(OUT/"LAB160_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB160_meta.json").write_text(json.dumps(dict(
    anchor_minutes=ANCHOR_MINUTES,profile_hours=PROFILE_H,profile_bins=PROFILE_BINS,
    horizons_h=HORIZONS_H,levels_atr=LEVELS,
    ratio_column=ratio_col,oi_column=oi_col,volume_column=vc,
    caveat="descriptive TRAIN/development atlas; no entries"
),indent=2))
print("\n".join(lines))
