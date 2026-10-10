from __future__ import annotations
import importlib.util, json, re, zipfile
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=Path("lab159_out");OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
MODE="LOCK2_LOCK025"
PROFILE_H=24
PROFILE_BINS=40
VALUE_FRAC=0.70
RISK=0.25

def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

L155=loadmod("lab155",ROOT/"labs/LAB155_ADDON_RISK_TRANSFER_20261009/run_lab155.py")
BT=L155.BT;BO=L155.BO;BH=L155.BH;BL=L155.BL;BC=L155.BC

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
        if not fs:raise RuntimeError("no csv")
        if len(fs)==1:return fs[0]
        common=set(fs[0].columns)
        for d in fs[1:]: common &= set(d.columns)
        cols=list(common)
        return pd.concat([d[cols] for d in fs],ignore_index=True)
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors="coerce");med=float(x.dropna().median()) if x.notna().any() else 0
        unit="ns" if med>1e17 else ("us" if med>1e14 else ("ms" if med>1e11 else "s"))
        return pd.to_datetime(x,unit=unit,utc=True,errors="coerce")
    return pd.to_datetime(s,utc=True,errors="coerce")

rawp=load_zip(Path("btc_5m.zip"))
tc=pick(rawp.columns,["time","timestamp","open_time","datetime"])
oc=pick(rawp.columns,["open"]);hc=pick(rawp.columns,["high"]);lc=pick(rawp.columns,["low"]);cc=pick(rawp.columns,["close"])
vc=pick(rawp.columns,["quote_volume","quoteassetvolume","volume","base_volume","vol"])
if None in (tc,oc,hc,lc,cc) or vc is None: raise RuntimeError(f"missing price/volume columns {list(rawp.columns)}")
p=rawp[[tc,oc,hc,lc,cc,vc]].copy();p["time"]=ptime(p[tc])
for c,n in [(oc,"open"),(hc,"high"),(lc,"low"),(cc,"close"),(vc,"volume")]:p[n]=pd.to_numeric(p[c],errors="coerce")
p=p[["time","open","high","low","close","volume"]].dropna().sort_values("time").drop_duplicates("time",keep="last")
p=p.set_index("time").resample("5min").agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),volume=("volume","sum")).dropna().reset_index()

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
    poc=int(np.argmax(v))
    return dict(lo=lo,hi=hi,centers=centers,vol=v,poc=float(centers[poc]))

def shape_name(prof):
    centers=prof["centers"];v=prof["vol"];tot=v.sum()
    q1=prof["lo"]+(prof["hi"]-prof["lo"])/3;q2=prof["lo"]+2*(prof["hi"]-prof["lo"])/3
    poc=prof["poc"];low=v[centers<q1].sum()/tot;high=v[centers>q2].sum()/tot
    peaks=np.argsort(v)[-2:]
    double=(abs(int(peaks[-1])-int(peaks[-2]))>=max(6,len(v)//4) and v[peaks[-2]]>=0.70*v[peaks[-1]])
    if double:return "DOUBLE"
    if poc>=q2 and high>low*1.15:return "P"
    if poc<=q1 and low>high*1.15:return "b"
    return "D"

# cache causal shape by raw signal entry index/time
def shape_at_time(t):
    i=int(p.time.searchsorted(pd.Timestamp(t),side="left"))
    if i<PROFILE_H*12:return "NA"
    prof=vap_profile(p.iloc[i-PROFILE_H*12:i])
    return shape_name(prof) if prof is not None else "NA"

shape_cache={}
def raw_with_shape(cost):
    d=L155.raw_signals(cost).copy()
    shapes=[]
    for t in d.entry_time:
        key=pd.Timestamp(t)
        if key not in shape_cache:shape_cache[key]=shape_at_time(key)
        shapes.append(shape_cache[key])
    d["profile_shape"]=shapes
    return d

VARIANTS={
    "BASE":lambda r: True,
    "R48_NOT_b":lambda r: not (r.source=="R48_HIGH" and r.profile_shape=="b"),
    "R48_D_ONLY":lambda r: not (r.source=="R48_HIGH" and r.profile_shape!="D"),
    "A_NO_DOUBLE":lambda r: not (r.source=="A" and r.profile_shape=="DOUBLE"),
    "B3_D_ONLY":lambda r: not (r.source=="B3_HIGH" and r.profile_shape!="D"),
    "COMBO_CONSERVATIVE":lambda r: not ((r.source=="R48_HIGH" and r.profile_shape=="b") or (r.source=="A" and r.profile_shape=="DOUBLE")),
    "COMBO_D_PREF":lambda r: not ((r.source=="R48_HIGH" and r.profile_shape!="D") or (r.source=="A" and r.profile_shape=="DOUBLE") or (r.source=="B3_HIGH" and r.profile_shape!="D")),
}

def replay_filtered(cost,variant):
    raw=raw_with_shape(cost)
    keep=raw.apply(VARIANTS[variant],axis=1)
    filtered_out=raw[~keep].copy()
    raw=raw[keep].copy().sort_values(["entry_i","pri"]).reset_index(drop=True)
    by_i={}
    for _,r in raw.iterrows():by_i.setdefault(int(r.entry_i),[]).append(r)

    active=[];closed=[];skipped=0;addons=0
    if raw.empty:return pd.DataFrame(),pd.DataFrame(),0,0,filtered_out
    start=int(raw.entry_i.min());end=min(int(raw.entry_i.max())+L155.MAX_H_BARS,len(BT)-1)
    equity_rows=[];realized=0.0
    for i in range(start,end+1):
        sigs=by_i.get(i,[])
        if sigs:
            sigs=sorted(sigs,key=lambda r:int(r.pri))
            for r in sigs:
                allow=False;is_addon=False
                if len(active)==0:allow=True
                elif len(active)==1:
                    op=active[0]
                    allow=(int(op["side"])==int(r.side) and L155.total_mtm_at_open(op,i)>=0)
                    is_addon=allow
                if allow:
                    if is_addon:
                        addons+=1;L155.transfer_first_stop(active[0],MODE)
                    np_=L155.init_pos(r,cost,"LOCK2");np_["addon_parent"]=is_addon;np_["profile_shape"]=str(r.profile_shape)
                    active.append(np_)
                else:skipped+=1

        still=[]
        for pos in active:
            done=L155.evaluate_bar(pos,i)
            if done is None:still.append(pos)
            else:closed.append(done);realized+=float(done["net_r"])
        active=still
        floating=sum(L155.total_mtm_at_close(pos,i) for pos in active)
        equity_rows.append(dict(time=BT.iloc[i],equity_r=realized+floating,realized_r=realized,floating_r=floating,open_count=len(active)))
        if i>int(raw.entry_i.max()) and not active:break

    return pd.DataFrame(closed),pd.DataFrame(equity_rows),skipped,addons,filtered_out

def perf(t):
    x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    maxls=0;cur=0
    for v in x:
        if v<0:cur+=1;maxls=max(maxls,cur)
        else:cur=0
    return dict(n=len(t),ev=float(x.mean()) if len(x) else np.nan,pf=float(pos/neg) if neg>0 else np.inf,
                wr=float((x>0).mean()) if len(x) else np.nan,total_r=float(x.sum()),max_consec_losses=maxls)

summary=[];engine=[];shape=[];year=[];filtered=[];alltr=[]
for cost in COSTS:
    for variant in VARIANTS:
        t,eq,sk,adds,fout=replay_filtered(cost,variant)
        if t.empty:continue
        s=L155.stats(t,eq);s.update(cost_bps=cost,variant=variant,skipped=sk,addons=adds,filtered_n=len(fout))
        summary.append(s)
        tt=t.copy();tt["cost_bps"]=cost;tt["variant"]=variant;alltr.append(tt)
        if len(fout):
            ff=fout.copy();ff["cost_bps"]=cost;ff["variant"]=variant;filtered.append(ff)
        for src,g in t.groupby("source"):engine.append(dict(cost_bps=cost,variant=variant,source=src,**perf(g)))
        for sh,g in t.groupby("profile_shape"):shape.append(dict(cost_bps=cost,variant=variant,profile_shape=sh,**perf(g)))
        ycol=pd.to_datetime(t.entry_time,utc=True).dt.year
        for y,g in t.groupby(ycol):year.append(dict(cost_bps=cost,variant=variant,year=int(y),**perf(g)))

S=pd.DataFrame(summary);E=pd.DataFrame(engine);SH=pd.DataFrame(shape);Y=pd.DataFrame(year);T=pd.concat(alltr,ignore_index=True)
S.to_csv(OUT/"LAB159_summary.csv",index=False)
E.to_csv(OUT/"LAB159_engine.csv",index=False)
SH.to_csv(OUT/"LAB159_shape.csv",index=False)
Y.to_csv(OUT/"LAB159_year.csv",index=False)
T.to_csv(OUT/"LAB159_trades.csv",index=False)
if filtered:pd.concat(filtered,ignore_index=True).to_csv(OUT/"LAB159_filtered_signals.csv",index=False)

base=S[(S.cost_bps==7.5)&(S.variant=="BASE")].iloc[0]
stress=S[S.cost_bps==7.5].copy()
stress["delta_rmo"]=stress.r_month-base.r_month
stress["delta_pf"]=stress.pf-base.pf
stress["delta_dd_pp"]=stress.mtm_dd_pct-base.mtm_dd_pct
rank=stress[(stress.r_month>=0.90*base.r_month)&(stress.pf>=base.pf)].sort_values(["mtm_dd_pct","r_month"],ascending=[True,False])
winner=str(rank.iloc[0].variant) if len(rank) else "BASE"

lines=["# LAB159 — PROFILE SHAPE INCREMENTAL REPLAY","",
"Exact-causal full portfolio replay on raw A+B3_HIGH+R48_HIGH+EARLY_EPISODE signals.",
"Execution frozen: HALF_TP3_LOCK2 + SECOND_MTM_GE0_SAME_SIDE + first stop LOCK025 on add-on + 0.25% risk.",
"Profile is causal trailing 24h / 40 bins; volume-at-price reconstructed from M5 OHLCV exactly as LAB158.",
"No return-fit threshold search: only LAB158 shape hypotheses are tested.","",
"## Portfolio"]
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].sort_values("r_month",ascending=False).iterrows():
        lines.append(f"- {r.variant}: N={int(r.n)} ({r.trades_month:.2f}/mo), filtered={int(r.filtered_n)}, addons={int(r.addons)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, MTM DD={r.mtm_dd_pct:.2f}%, daily={r.daily_start_loss_pct:.2f}%")

lines+=["","## Stress deltas vs BASE"]
for _,r in stress.sort_values("r_month",ascending=False).iterrows():
    lines.append(f"- {r.variant}: dR/mo={r.delta_rmo:+.2f}, dPF={r.delta_pf:+.2f}, dDD={r.delta_dd_pp:+.2f}pp")

lines+=["","## Stress yearly"]
for v in VARIANTS:
    q=Y[(Y.cost_bps==7.5)&(Y.variant==v)]
    if len(q):
        lines.append(f"### {v}")
        for _,r in q.iterrows():lines.append(f"- {int(r.year)}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, total={r.total_r:+.1f}R")

lines+=["","## Stress engine attribution"]
for v in VARIANTS:
    q=E[(E.cost_bps==7.5)&(E.variant==v)]
    if len(q):
        lines.append(f"### {v}")
        for _,r in q.iterrows():lines.append(f"- {r.source}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, total={r.total_r:+.1f}R")

lines+=["","## Decision",
f"Frozen screen winner: **{winner}**.",
"Promotion screen is conservative: stress R/mo must retain >=90% of BASE and PF must not fall; among survivors prefer lower MTM DD then higher R/mo.",
"LAB159 is still TRAIN/development evidence. Do not modify the forward EA unless the selected shape rule is robust by year and later survives pristine/forward validation.",
"Because profile is reconstructed from M5 OHLCV, any promoted rule should next be checked against second-level/tick-native volume data."]
(OUT/"LAB159_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB159_meta.json").write_text(json.dumps(dict(profile_hours=PROFILE_H,bins=PROFILE_BINS,variants=list(VARIANTS.keys()),winner=winner,caveat="TRAIN/development; M5 reconstructed volume-at-price"),indent=2))
print("\n".join(lines))
