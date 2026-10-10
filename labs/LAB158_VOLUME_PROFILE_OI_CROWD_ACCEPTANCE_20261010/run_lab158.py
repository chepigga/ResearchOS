from __future__ import annotations
import importlib.util, json, re, zipfile
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=Path("lab158_out");OUT.mkdir(exist_ok=True)
COST=7.5
MODE="LOCK2_LOCK025"
PROFILE_H=24
PROFILE_BINS=40
RECENT_H=6
VALUE_FRAC=0.70
MIN_N=12

def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

L157=loadmod("lab157",ROOT/"labs/LAB157_CANDIDATE_ARCHITECTURE_FULL_REPLAY_20261009/run_lab157.py")
T=L157.T[(L157.T.cost_bps==COST)&(L157.T["mode"]==MODE)].copy().reset_index(drop=True)
T["entry_time"]=pd.to_datetime(T.entry_time,utc=True)
if "source" not in T.columns: raise RuntimeError("LAB157 trades missing source")

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
            if not n.lower().endswith(".csv"):continue
            with z.open(n) as fh:d=pd.read_csv(fh)
            if len(d):fs.append(d)
        if not fs:raise RuntimeError(f"no csv in {zp}")
        if len(fs)==1:return fs[0]
        common=set(fs[0].columns)
        for d in fs[1:]:common&=set(d.columns)
        cols=list(common)
        return pd.concat([d[cols] for d in fs],ignore_index=True)
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors="coerce");med=float(x.dropna().median()) if x.notna().any() else 0
        unit="ns" if med>1e17 else ("us" if med>1e14 else ("ms" if med>1e11 else "s"))
        return pd.to_datetime(x,unit=unit,utc=True,errors="coerce")
    return pd.to_datetime(s,utc=True,errors="coerce")

raw=load_zip(Path("btc_5m.zip"))
tc=pick(raw.columns,["time","timestamp","open_time","datetime"])
oc=pick(raw.columns,["open"]);hc=pick(raw.columns,["high"]);lc=pick(raw.columns,["low"]);cc=pick(raw.columns,["close"])
vc=pick(raw.columns,["quote_volume","quoteassetvolume","volume","base_volume","vol"])
if None in (tc,oc,hc,lc,cc):raise RuntimeError(f"OHLC missing; cols={list(raw.columns)}")
if vc is None:raise RuntimeError(f"VOLUME COLUMN NOT FOUND in btc_5m.zip; cols={list(raw.columns)}")
p=raw[[tc,oc,hc,lc,cc,vc]].copy()
p["time"]=ptime(p[tc])
for c,n in [(oc,"open"),(hc,"high"),(lc,"low"),(cc,"close"),(vc,"volume")]:
    p[n]=pd.to_numeric(p[c],errors="coerce")
p=p[["time","open","high","low","close","volume"]].dropna().sort_values("time").drop_duplicates("time",keep="last")
p=p.set_index("time").resample("5min").agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),volume=("volume","sum")).dropna().reset_index()

h1=p.set_index("time").resample("1h",label="left",closed="left").agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1["atr"]=tr.rolling(14,min_periods=14).mean()
h1["close_time"]=h1.time+pd.Timedelta(hours=1)

fraw=load_zip(Path("BTCUSDT_flow_2021-01-2026-08.csv.zip"))
ft=pick(fraw.columns,["create_time","time"])
fr=pick(fraw.columns,["count_long_short_ratio"])
fo=pick(fraw.columns,["sum_open_interest_value","sum_open_interest"])
if None in (ft,fr,fo):raise RuntimeError(f"flow cols missing: {list(fraw.columns)}")
f=fraw[[ft,fr,fo]].copy();f["time"]=ptime(f[ft])
f["ratio"]=pd.to_numeric(f[fr],errors="coerce");f["oi"]=pd.to_numeric(f[fo],errors="coerce")
f=f.dropna().sort_values("time").drop_duplicates("time",keep="last")
f=f[(f.ratio>0)&(f.oi>0)].set_index("time").resample("5min").last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean();sd=f.ratio.rolling(72,min_periods=72).std(ddof=0)
f["z"]=(f.ratio-mu)/sd.replace(0,np.nan)
f["oi4h"]=f.oi/f.oi.shift(48)-1

def vap_profile(w,bins=PROFILE_BINS):
    lo=float(w.low.min());hi=float(w.high.max())
    if not np.isfinite(lo+hi) or hi<=lo:return None
    edges=np.linspace(lo,hi,bins+1);v=np.zeros(bins,float)
    for r in w.itertuples():
        a=max(float(r.low),lo);b=min(float(r.high),hi);vol=float(r.volume)
        if vol<=0:continue
        if b<=a:
            k=min(bins-1,max(0,int((float(r.close)-lo)/(hi-lo)*bins)));v[k]+=vol;continue
        for k in range(bins):
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
    return dict(lo=lo,hi=hi,edges=edges,vol=v,centers=centers,poc=float(centers[poc]),val=float(edges[L]),vah=float(edges[R+1]),mean=float(v.mean()))

def bin_density(prof,price):
    e=prof["edges"];k=int(np.searchsorted(e,price,side="right")-1)
    k=min(len(prof["vol"])-1,max(0,k))
    return float(prof["vol"][k]/max(prof["mean"],1e-12))

def shape_name(prof):
    centers=prof["centers"];v=prof["vol"];tot=v.sum()
    q1=prof["lo"]+(prof["hi"]-prof["lo"])/3;q2=prof["lo"]+2*(prof["hi"]-prof["lo"])/3
    poc=prof["poc"]
    low=v[centers<q1].sum()/tot;high=v[centers>q2].sum()/tot
    peaks=np.argsort(v)[-2:]
    double=(abs(int(peaks[-1])-int(peaks[-2]))>=max(6,len(v)//4) and v[peaks[-2]]>=0.70*v[peaks[-1]])
    if double:return "DOUBLE"
    if poc>=q2 and high>low*1.15:return "P"
    if poc<=q1 and low>high*1.15:return "b"
    return "D"

rows=[]
for _,trd in T.iterrows():
    et=pd.Timestamp(trd.entry_time);side=1 if str(trd.side).upper()=="BUY" else -1
    i=int(p.time.searchsorted(et,side="left"))
    if i<=PROFILE_H*12+RECENT_H*12:continue
    past=p.iloc[max(0,i-PROFILE_H*12):i]
    old=p.iloc[max(0,i-(PROFILE_H+RECENT_H)*12):max(0,i-RECENT_H*12)]
    recent=p.iloc[max(0,i-RECENT_H*12):i]
    prof=vap_profile(past);oldp=vap_profile(old)
    if prof is None or oldp is None:continue
    px=float(p.open.iloc[i]) if i<len(p) else float(p.close.iloc[i-1])
    atrrow=h1[h1.close_time<=et].tail(1)
    if atrrow.empty or not np.isfinite(atrrow.atr.iloc[0]):continue
    atr=float(atrrow.atr.iloc[0])
    flow=f[f.time<=et].tail(1)
    if flow.empty:continue
    z=float(flow.z.iloc[0]);oi4=float(flow.oi4h.iloc[0])
    if not np.isfinite(z) or not np.isfinite(oi4):continue
    rv=max(float(recent.volume.sum()),1e-12)
    side_out=float(recent.loc[recent.close>(prof["vah"]) if side>0 else recent.close<(prof["val"]),"volume"].sum()/rv)
    adverse_out=float(recent.loc[recent.close<(prof["val"]) if side>0 else recent.close>(prof["vah"]),"volume"].sum()/rv)
    mig=side*(prof["poc"]-oldp["poc"])/atr
    density=bin_density(prof,px)
    pos=(px-prof["poc"])/atr
    rows.append(dict(entry_time=et,source=str(trd.source),side=str(trd.side),net_r=float(trd.net_r),
        z=z,abs_z=abs(z),oi4h=oi4,atr=atr,price=px,poc=prof["poc"],val=prof["val"],vah=prof["vah"],
        local_density=density,poc_migration_side_atr=mig,poc_pos_atr=side*pos,
        side_outside_share=side_out,adverse_outside_share=adverse_out,shape=shape_name(prof)))

D=pd.DataFrame(rows)
if D.empty:raise RuntimeError("No LAB158 feature rows")

thr={}
for src,g in D.groupby("source"):
    thr[src]={"density_q40":float(g.local_density.quantile(.40)),"density_q60":float(g.local_density.quantile(.60)),
              "sideout_q60":float(g.side_outside_share.quantile(.60)),"adverse_q40":float(g.adverse_outside_share.quantile(.40))}

def favorable(r):
    t=thr[r.source]
    if r.source=="R48":
        return (r.local_density>=t["density_q60"] and r.side_outside_share>=t["sideout_q60"] and r.poc_migration_side_atr>=0)
    return (r.local_density<=t["density_q40"] and r.adverse_outside_share<=t["adverse_q40"] and r.poc_migration_side_atr>=0)

D["profile_favorable"]=D.apply(favorable,axis=1)
D["crowd_bucket"]=pd.cut(D.abs_z,[-np.inf,1.0,1.5,2.0,np.inf],labels=["<1","1-1.5","1.5-2",">=2"],right=False)
D["oi_bucket"]=pd.cut(D.oi4h,[-np.inf,0,0.0035,0.00867,np.inf],labels=["NEG","0-.35%",".35-.867%",">=.867%"],right=False)
D["joint_high"]=D.profile_favorable & (D.abs_z>=1.5) & (D.oi4h>0)
D.to_csv(OUT/"LAB158_trade_features.csv",index=False)
Path(OUT/"LAB158_thresholds.json").write_text(json.dumps(dict(volume_column=vc,profile_hours=PROFILE_H,bins=PROFILE_BINS,value_fraction=VALUE_FRAC,thresholds=thr),indent=2))

def perf(g):
    x=g.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    return dict(n=len(g),ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),total_r=float(x.sum()))

summ=[]
for src,g in D.groupby("source"):
    for label,mask in [("ALL",pd.Series(True,index=g.index)),("PROFILE_FAVORABLE",g.profile_favorable),
                       ("PROFILE_OTHER",~g.profile_favorable),("JOINT_HIGH",g.joint_high),("JOINT_OTHER",~g.joint_high)]:
        q=g[mask]
        if len(q)>=MIN_N:summ.append(dict(source=src,group=label,**perf(q)))
S=pd.DataFrame(summ);S.to_csv(OUT/"LAB158_summary.csv",index=False)

matrix=[]
for (src,pf,zb,ob),g in D.groupby(["source","profile_favorable","crowd_bucket","oi_bucket"],observed=True):
    if len(g)<MIN_N:continue
    matrix.append(dict(source=src,profile_favorable=bool(pf),crowd_bucket=str(zb),oi_bucket=str(ob),**perf(g)))
M=pd.DataFrame(matrix);M.to_csv(OUT/"LAB158_joint_matrix.csv",index=False)

shape=[]
for (src,sh),g in D.groupby(["source","shape"]):
    if len(g)>=MIN_N:shape.append(dict(source=src,shape=sh,**perf(g)))
SH=pd.DataFrame(shape);SH.to_csv(OUT/"LAB158_shape_summary.csv",index=False)

lines=["# LAB158 — VOLUME PROFILE × OI × CROWD ACCEPTANCE","",
"Protocol: diagnostic overlay on exact LAB157 stress candidate trades (7.5bps, LOCK2_LOCK025). No trade rules changed.",
f"Volume source column: {vc} from btc_5m.zip.",
f"Causal profile: trailing {PROFILE_H}h only, {PROFILE_BINS} bins, 70% value area; each M5 bar volume distributed uniformly through its high-low range.",
"POC migration compares current trailing-24h POC with a trailing-24h profile ending 6h earlier.",
"Profile-favorable thresholds are source-specific q40/q60 distribution cutoffs only; NOT optimized on returns.",
"For A/B3/EARLY: favorable = low local acceptance + low adverse-side acceptance + POC migration toward trade.",
"For R48: favorable = high local acceptance + high trade-side outside-value volume + POC migration toward trade.",
"JOINT_HIGH additionally requires |Z|>=1.5 and OI4h>0.","","## Results by engine"]
for src in sorted(D.source.unique()):
    lines.append(f"### {src}")
    for _,r in S[S.source==src].iterrows():
        lines.append(f"- {r.group}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, total={r.total_r:+.1f}R")
lines+=["","## Profile shape"]
for src in sorted(D.source.unique()):
    q=SH[SH.source==src].sort_values("pf",ascending=False)
    if len(q):
        lines.append(f"### {src}")
        for _,r in q.iterrows():lines.append(f"- {r['shape']}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}")
lines+=["","## Interpretation discipline",
"LAB158 is a feature-discovery/acceptance diagnostic, not a promotion test.",
"Do not change forward EA from LAB158 alone. A useful feature must show consistent separation across engines/years and survive incremental exact-causal replay in LAB159.",
"5m volume-at-price is reconstructed from bar ranges, not native tick-by-price volume. If promising, validate on second-level/tick-native data where available."]
(OUT/"LAB158_REPORT.md").write_text("\n".join(lines)+"\n")
print("\n".join(lines))
