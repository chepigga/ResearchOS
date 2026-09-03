#!/usr/bin/env python3
from __future__ import annotations
import io, json, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LAB="BTC_24H_RIGHT_TAIL_BTC_ONLY_CAUSAL_DECOMPOSITION_LAB_003"
SEED=20260903
OUT=Path(__file__).resolve().parent/"output"
CACHE=Path(__file__).resolve().parent/"cache"
OUT.mkdir(parents=True,exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)

START_MONTH="2021-01"; END_MONTH="2026-08"; INTERVAL="15m"
BASE="https://data.binance.vision/data/spot/monthly/klines"
COLS=["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_base","taker_quote","ignore"]
ROLL=30*24*4
IMPULSE_Q=.975
COOLDOWN=16
PRIMARY="24h"
HORIZON_BARS=96

CORE=["impulse_dir","btc_z15","btc_z60","btc_z4h","btc_z24h","btc_vol_z","btc_range_z","btc_corr7d_lag","hour_sin","hour_cos"]

FAMILIES={
    "IMPULSE_PATH":["impulse_eff60","impulse_consistency60","impulse_clv60","vol60_z"],
    "PRE_STATE":["pre4h_z","pre24h_z","pos7d","dist7d_high_z","dist7d_low_z"],
    "VOL_REGIME":["rv4h_z","rv24h_z","vol_ratio_24h_7d_z","atr4h_z"],
    "BREAK_ACCEPTANCE":["break4h_signed_z","break24h_signed_z","clv15_signed","range_pos4h_signed"],
    "TREND_REGIME":["trend7d_z","trend30d_z","trend_eff7d","trend_interaction"],
    "CALENDAR":["dow_sin","dow_cos","weekend"],
}

def months(a,b):
    return [str(x) for x in pd.period_range(a,b,freq="M")]

def url(sym,m):
    return f"{BASE}/{sym}/{INTERVAL}/{sym}-{INTERVAL}-{m}.zip"

def get_one(sym,m):
    p=CACHE/f"{sym}-{INTERVAL}-{m}.zip"
    if p.exists() and p.stat().st_size>100:
        return p
    for k in range(4):
        try:
            r=requests.get(url(sym,m),timeout=45)
            if r.status_code==404:
                return None
            r.raise_for_status()
            if len(r.content)<100:
                return None
            p.write_bytes(r.content)
            return p
        except Exception as e:
            if k==3:
                print("WARN",sym,m,e,file=sys.stderr)
                return None
            time.sleep(1.5*(k+1))

def downloads():
    jobs=[("BTCUSDT",m) for m in months(START_MONTH,END_MONTH)]
    out=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        fut={ex.submit(get_one,s,m):(s,m) for s,m in jobs}
        for f in as_completed(fut):
            p=f.result()
            if p: out.append(p)
    out=sorted(out)
    print("BTCUSDT",len(out),"monthly files")
    return out

def epoch(v):
    x=pd.to_numeric(v,errors="coerce")
    med=x.dropna().median()
    unit="us" if np.isfinite(med) and med>1e14 else "ms"
    return pd.to_datetime(x,unit=unit,utc=True,errors="coerce")

def read_month(p):
    with zipfile.ZipFile(p) as z:
        names=[n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names: return pd.DataFrame()
        raw=z.read(names[0])
    d=pd.read_csv(io.BytesIO(raw),header=None,names=COLS)
    d["time"]=epoch(d.open_time)
    for c in ["open","high","low","close","volume","quote_volume","trades"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    return d[["time","open","high","low","close","volume","quote_volume","trades"]].dropna()

def load(paths):
    fs=[read_month(p) for p in paths]
    fs=[x for x in fs if len(x)]
    if not fs: raise RuntimeError("No BTC data")
    return pd.concat(fs,ignore_index=True).sort_values("time").drop_duplicates("time").set_index("time")

def rz(s,w=ROLL):
    mu=s.rolling(w,min_periods=max(100,w//4)).mean().shift(1)
    sd=s.rolling(w,min_periods=max(100,w//4)).std(ddof=0).shift(1)
    return (s-mu)/sd.replace(0,np.nan)

def rolling_eff(close,bars):
    net=(close/close.shift(bars)-1).abs()
    path=close.pct_change().abs().rolling(bars,min_periods=bars).sum()
    return net/path.replace(0,np.nan)

def make_panel(b):
    x=b.add_prefix("btc_")
    c=x.btc_close
    x["btc_lr15"]=np.log(c).diff()
    x["btc_lr60"]=np.log(c/c.shift(4))
    x["btc_lr4h"]=np.log(c/c.shift(16))
    x["btc_lr24h"]=np.log(c/c.shift(96))
    for k in ["15","60","4h","24h"]:
        x[f"btc_z{k}"]=rz(x[f"btc_lr{k}"])
    x["btc_vol_z"]=rz(np.log1p(x.btc_quote_volume))
    x["btc_range"]=(x.btc_high-x.btc_low)/x.btc_close
    x["btc_range_z"]=rz(x.btc_range)
    x["btc_corr7d_lag"]=x.btc_lr15.rolling(7*96,min_periods=3*96).corr(x.btc_lr15.shift(1)).shift(1)

    h=x.index.hour+x.index.minute/60
    x["hour_sin"]=np.sin(2*np.pi*h/24)
    x["hour_cos"]=np.cos(2*np.pi*h/24)
    dow=x.index.dayofweek
    x["dow_sin"]=np.sin(2*np.pi*dow/7)
    x["dow_cos"]=np.cos(2*np.pi*dow/7)
    x["weekend"]=(dow>=5).astype(float)

    x["impulse_thr"]=x.btc_lr60.abs().rolling(ROLL,min_periods=ROLL//2).quantile(IMPULSE_Q).shift(1)
    x["impulse_raw"]=x.btc_lr60.abs()>=x.impulse_thr
    x["impulse_dir"]=np.sign(x.btc_lr60).astype(float)

    abs4=x.btc_lr15.abs().rolling(4,min_periods=4).sum()
    x["impulse_eff60"]=x.btc_lr60.abs()/abs4.replace(0,np.nan)
    signs=np.sign(x.btc_lr15)
    x["impulse_consistency60"]=(signs.rolling(4,min_periods=4).sum()/4.0)*x.impulse_dir
    hi60=x.btc_high.rolling(4,min_periods=4).max()
    lo60=x.btc_low.rolling(4,min_periods=4).min()
    pos60=(x.btc_close-lo60)/(hi60-lo60).replace(0,np.nan)
    x["impulse_clv60"]=np.where(x.impulse_dir>=0,2*pos60-1,1-2*pos60)
    v60=x.btc_quote_volume.rolling(4,min_periods=4).sum()
    x["vol60_z"]=rz(np.log1p(v60))

    x["pre4h"]=np.log(c.shift(4)/c.shift(20))
    x["pre24h"]=np.log(c.shift(4)/c.shift(100))
    x["pre4h_z"]=rz(x.pre4h)
    x["pre24h_z"]=rz(x.pre24h)
    prior7_hi=x.btc_high.rolling(7*96,min_periods=3*96).max().shift(4)
    prior7_lo=x.btc_low.rolling(7*96,min_periods=3*96).min().shift(4)
    base=c.shift(4)
    x["pos7d"]=(base-prior7_lo)/(prior7_hi-prior7_lo).replace(0,np.nan)
    x["dist7d_high_z"]=rz(np.log(base/prior7_hi))
    x["dist7d_low_z"]=rz(np.log(base/prior7_lo))

    rv4=x.btc_lr15.rolling(16,min_periods=16).std(ddof=0)
    rv24=x.btc_lr15.rolling(96,min_periods=48).std(ddof=0)
    rv7=x.btc_lr15.rolling(7*96,min_periods=3*96).std(ddof=0)
    x["rv4h_z"]=rz(rv4)
    x["rv24h_z"]=rz(rv24)
    x["vol_ratio_24h_7d_z"]=rz(rv24/rv7.replace(0,np.nan))
    prev_close=x.btc_close.shift(1)
    tr=pd.concat([(x.btc_high-x.btc_low),(x.btc_high-prev_close).abs(),(x.btc_low-prev_close).abs()],axis=1).max(axis=1)
    atr4=tr.rolling(16,min_periods=16).mean()/x.btc_close
    x["atr4h_z"]=rz(atr4)

    hi4=x.btc_high.rolling(16,min_periods=8).max().shift(1)
    lo4=x.btc_low.rolling(16,min_periods=8).min().shift(1)
    hi24=x.btc_high.rolling(96,min_periods=48).max().shift(1)
    lo24=x.btc_low.rolling(96,min_periods=48).min().shift(1)
    signed4=np.where(x.impulse_dir>=0,np.log(x.btc_close/hi4),np.log(lo4/x.btc_close))
    signed24=np.where(x.impulse_dir>=0,np.log(x.btc_close/hi24),np.log(lo24/x.btc_close))
    x["break4h_signed_z"]=rz(pd.Series(signed4,index=x.index))
    x["break24h_signed_z"]=rz(pd.Series(signed24,index=x.index))
    clv=(x.btc_close-x.btc_low)/(x.btc_high-x.btc_low).replace(0,np.nan)
    x["clv15_signed"]=np.where(x.impulse_dir>=0,2*clv-1,1-2*clv)
    pos4=(x.btc_close-lo4)/(hi4-lo4).replace(0,np.nan)
    x["range_pos4h_signed"]=np.where(x.impulse_dir>=0,2*pos4-1,1-2*pos4)

    ret7=np.log(c/c.shift(7*96))
    ret30=np.log(c/c.shift(30*96))
    x["trend7d_z"]=rz(ret7)
    x["trend30d_z"]=rz(ret30)
    x["trend_eff7d"]=rolling_eff(c,7*96)
    x["trend_interaction"]=x.trend7d_z*x.trend30d_z
    return x

def make_events(x):
    cand=np.flatnonzero(x.impulse_raw.fillna(False).to_numpy())
    chosen=[]; last=-10**9
    for i in cand:
        if i-last>=COOLDOWN:
            chosen.append(i); last=i
    e=x.iloc[chosen].copy()
    e["bar_i"]=chosen
    e["decision_time"]=e.index
    e["entry_time"]=x.index.to_series().shift(-1).iloc[chosen].to_numpy()
    e["entry"]=x.btc_open.shift(-1).iloc[chosen].to_numpy()
    fut=x.btc_close.shift(-HORIZON_BARS).iloc[chosen].to_numpy()
    raw=fut/e.entry.to_numpy()-1.0
    e["raw_24h"]=raw
    e["cont_24h"]=raw*e.impulse_dir.to_numpy()
    e["rev_24h"]=-e.cont_24h
    y=e.index.year
    e["split"]=np.where(y<=2024,"DEV_2021_2024",np.where(y==2025,"BRIDGE_2025","OOS_2026"))
    e=e.replace([np.inf,-np.inf],np.nan)
    return e.dropna(subset=["entry","cont_24h","btc_z60"])

def build_targets(e):
    dev=e[e.split=="DEV_2021_2024"]
    cont_thr=float(dev.cont_24h.quantile(.75))
    rev_thr=float(dev.rev_24h.quantile(.75))
    abs_thr=float(dev.raw_24h.abs().quantile(.75))
    e=e.copy()
    e["tail_cont_24h"]=(e.cont_24h>=cont_thr).astype(int)
    e["tail_rev_24h"]=(e.rev_24h>=rev_thr).astype(int)
    e["tail_abs_24h"]=(e.raw_24h.abs()>=abs_thr).astype(int)
    return e,{"cont_thr":cont_thr,"rev_thr":rev_thr,"abs_thr":abs_thr}

def fit_pipe(d,features,target):
    m=Pipeline([
        ("imp",SimpleImputer(strategy="median")),
        ("sc",StandardScaler()),
        ("lr",LogisticRegression(C=.5,max_iter=4000,random_state=SEED))
    ])
    m.fit(d[features],d[target].astype(int))
    return m

def safe_metrics(y,p):
    if len(np.unique(y))<2:
        return np.nan,np.nan,np.nan
    return float(roc_auc_score(y,p)),float(brier_score_loss(y,p)),float(log_loss(y,p,labels=[0,1]))

def bootstrap_mean(a,n=1500,seed=SEED):
    a=np.asarray(a,float)
    a=a[np.isfinite(a)]
    if len(a)<2:
        return np.nan,np.nan,np.nan
    rng=np.random.default_rng(seed+len(a)*17)
    idx=rng.integers(0,len(a),size=(n,len(a)))
    means=a[idx].mean(1)
    lo,hi=np.quantile(means,[.025,.975])
    return float(a.mean()),float(lo),float(hi)

def model_sets():
    sets={"CORE":CORE.copy()}
    for f in CORE:
        sets[f"DROP__{f}"]=[x for x in CORE if x!=f]
    for fam,feats in FAMILIES.items():
        sets[f"CORE_PLUS__{fam}"]=list(dict.fromkeys(CORE+feats))
    return sets

def train_and_score(e):
    sets=model_sets()
    dev=e[e.split=="DEV_2021_2024"].copy()
    fitted={}; q80={}; metric_rows=[]
    scored={sp:e[e.split==sp].copy() for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]}

    for name,feats in sets.items():
        fitted[(name,"CONT")]=fit_pipe(dev,feats,"tail_cont_24h")
        fitted[(name,"REV")]=fit_pipe(dev,feats,"tail_rev_24h")
        pdv_c=fitted[(name,"CONT")].predict_proba(dev[feats])[:,1]
        pdv_r=fitted[(name,"REV")].predict_proba(dev[feats])[:,1]
        q80[name]=float(np.quantile(np.maximum(pdv_c,pdv_r),.80))

    router_rows=[]; score_rows=[]
    for sp,d0 in scored.items():
        d=d0.copy()
        for name,feats in sets.items():
            pc=fitted[(name,"CONT")].predict_proba(d[feats])[:,1]
            pr=fitted[(name,"REV")].predict_proba(d[feats])[:,1]
            for side,p,target in [("CONT",pc,"tail_cont_24h"),("REV",pr,"tail_rev_24h")]:
                auc,brier,ll=safe_metrics(d[target].to_numpy(),p)
                metric_rows.append(dict(split=sp,model=name,side=side,n=len(d),auc=auc,brier=brier,logloss=ll))
            side=np.where(pc>=pr,"CONT","REV")
            conf=np.maximum(pc,pr)
            top=conf>=q80[name]
            chosen=np.where(side=="CONT",d.cont_24h,d.rev_24h)
            hit=np.where(side=="CONT",d.tail_cont_24h,d.tail_rev_24h)
            qret=chosen[top]; qhit=hit[top]
            m,lo,hi=bootstrap_mean(qret,seed=SEED+len(name)+len(sp))
            router_rows.append(dict(
                split=sp,model=name,n_total=len(d),n_top=int(top.sum()),
                top_tail_hit=float(np.mean(qhit)) if len(qhit) else np.nan,
                top_mean_chosen_ret=m,top_ci_lo=lo,top_ci_hi=hi,
                all_tail_hit=float(np.mean(hit)),all_mean_chosen_ret=float(np.mean(chosen)),
                top_cont_share=float(np.mean(side[top]=="CONT")) if top.sum() else np.nan
            ))
            if name=="CORE":
                tmp=d[["decision_time","entry_time","split","impulse_dir","entry","cont_24h","rev_24h","tail_cont_24h","tail_rev_24h"]].copy()
                tmp["core_side"]=side; tmp["core_conf"]=conf; tmp["core_top20"]=top; tmp["core_chosen_ret"]=chosen; tmp["core_tail_hit"]=hit
                score_rows.append(tmp)
    return pd.DataFrame(metric_rows),pd.DataFrame(router_rows),pd.concat(score_rows).sort_index()

def avg_auc(metrics,sp,model):
    q=metrics[(metrics.split==sp)&(metrics.model==model)]
    return float(q.auc.mean())

def router_val(router,sp,model,col):
    q=router[(router.split==sp)&(router.model==model)]
    return float(q.iloc[0][col])

def component_table(metrics,router):
    rows=[]
    for f in CORE:
        alt=f"DROP__{f}"
        row={"component_type":"CORE_FEATURE","component":f,"comparison":alt}
        for sp in ["BRIDGE_2025","OOS_2026"]:
            row[f"auc_delta_{sp}"]=avg_auc(metrics,sp,"CORE")-avg_auc(metrics,sp,alt)
            row[f"return_delta_{sp}"]=router_val(router,sp,"CORE","top_mean_chosen_ret")-router_val(router,sp,alt,"top_mean_chosen_ret")
            row[f"hit_delta_{sp}"]=router_val(router,sp,"CORE","top_tail_hit")-router_val(router,sp,alt,"top_tail_hit")
        row["robust_transfer"]=(
            row["auc_delta_BRIDGE_2025"]>0 and row["auc_delta_OOS_2026"]>0 and
            row["return_delta_BRIDGE_2025"]>0 and row["return_delta_OOS_2026"]>0 and
            row["hit_delta_OOS_2026"]>=0
        )
        rows.append(row)
    for fam in FAMILIES:
        alt=f"CORE_PLUS__{fam}"
        row={"component_type":"ADD_FAMILY","component":fam,"comparison":alt}
        for sp in ["BRIDGE_2025","OOS_2026"]:
            row[f"auc_delta_{sp}"]=avg_auc(metrics,sp,alt)-avg_auc(metrics,sp,"CORE")
            row[f"return_delta_{sp}"]=router_val(router,sp,alt,"top_mean_chosen_ret")-router_val(router,sp,"CORE","top_mean_chosen_ret")
            row[f"hit_delta_{sp}"]=router_val(router,sp,alt,"top_tail_hit")-router_val(router,sp,"CORE","top_tail_hit")
        row["robust_transfer"]=(
            row["auc_delta_BRIDGE_2025"]>0 and row["auc_delta_OOS_2026"]>0 and
            row["return_delta_BRIDGE_2025"]>0 and row["return_delta_OOS_2026"]>0 and
            row["hit_delta_OOS_2026"]>=0
        )
        rows.append(row)
    return pd.DataFrame(rows)

def verdict(router,components):
    core_bridge=router[(router.split=="BRIDGE_2025")&(router.model=="CORE")].iloc[0]
    core_oos=router[(router.split=="OOS_2026")&(router.model=="CORE")].iloc[0]
    stable=components[components.robust_transfer==True]
    stable_core=stable[stable.component_type=="CORE_FEATURE"]
    stable_add=stable[stable.component_type=="ADD_FAMILY"]
    gates={
        "oos_events_ge_100": bool(core_oos.n_total>=100),
        "core_oos_top_return_positive": bool(core_oos.top_mean_chosen_ret>0),
        "core_oos_tail_hit_ge_0.30": bool(core_oos.top_tail_hit>=.30),
        "core_bridge_not_catastrophic": bool(core_bridge.top_mean_chosen_ret>-0.005),
        "robust_core_feature_found": bool(len(stable_core)>=1),
        "robust_add_family_found": bool(len(stable_add)>=1),
    }
    if gates["oos_events_ge_100"] and gates["core_oos_top_return_positive"] and (gates["robust_core_feature_found"] or gates["robust_add_family_found"]):
        v="PASS_TRANSFERABLE_BTC_COMPONENT_FOUND"
    elif gates["oos_events_ge_100"] and gates["core_oos_top_return_positive"]:
        v="WATCH_CORE_EDGE_NOT_DECOMPOSED"
    else:
        v="FAIL_CORE_RIGHT_TAIL_NOT_REPRODUCED"
    return {
        "verdict":v,"gates":gates,
        "stable_components":stable[["component_type","component"]].to_dict("records"),
        "core_bridge_top_mean_return":float(core_bridge.top_mean_chosen_ret),
        "core_bridge_tail_hit":float(core_bridge.top_tail_hit),
        "core_oos_top_mean_return":float(core_oos.top_mean_chosen_ret),
        "core_oos_tail_hit":float(core_oos.top_tail_hit),
        "core_oos_n_top":int(core_oos.n_top),"core_oos_n_total":int(core_oos.n_total),
    }

def jdefault(o):
    if isinstance(o,(np.integer,)): return int(o)
    if isinstance(o,(np.floating,)): return float(o)
    if isinstance(o,(np.bool_,)): return bool(o)
    if isinstance(o,pd.Timestamp): return str(o)
    raise TypeError(type(o).__name__)

def pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:+.3f}%"

def pp(x):
    return "—" if not np.isfinite(x) else f"{100*x:+.1f} pp"

def write_report(x,e,thr,metrics,router,components,v):
    L=[
        f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","",
        "Role: leakage-safe predictive decomposition of the frozen BTC-only 24h right-tail router; not a live strategy and not proof of structural causality.","",
        "## Data / clock","",
        f"- Binance Spot BTCUSDT, completed 15m bars: `{x.index.min()}` -> `{x.index.max()}`.",
        f"- Bars: **{len(x):,}**.",
        f"- Events: DEV **{len(e[e.split=='DEV_2021_2024']):,}**, bridge **{len(e[e.split=='BRIDGE_2025']):,}**, OOS **{len(e[e.split=='OOS_2026']):,}**.",
        f"- Frozen 24h tail thresholds from DEV only: continuation **{pct(thr['cont_thr'])}**, reversal **{pct(thr['rev_thr'])}**, absolute **{pct(thr['abs_thr'])}**.",
        "- Entry/outcome starts at next 15m open. No post-decision feature is used.","",
        "## CORE reproduction","",
        "| Split | N top | Tail hit | Mean chosen 24h | 95% CI | CONT share |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
        r=router[(router.split==sp)&(router.model=="CORE")].iloc[0]
        L.append(f"| {sp} | {int(r.n_top)} | {100*r.top_tail_hit:.1f}% | {pct(r.top_mean_chosen_ret)} | [{pct(r.top_ci_lo)}, {pct(r.top_ci_hi)}] | {100*r.top_cont_share:.1f}% |")
    L += ["","## Core feature DROP decomposition","",
          "| Feature | Bridge AUC Δ | OOS AUC Δ | Bridge return Δ | OOS return Δ | OOS hit Δ | Transfer |",
          "|---|---:|---:|---:|---:|---:|---|"]
    q=components[components.component_type=="CORE_FEATURE"].copy().sort_values("return_delta_OOS_2026",ascending=False)
    for _,r in q.iterrows():
        L.append(f"| {r.component} | {r.auc_delta_BRIDGE_2025:+.4f} | {r.auc_delta_OOS_2026:+.4f} | {pct(r.return_delta_BRIDGE_2025)} | {pct(r.return_delta_OOS_2026)} | {pp(r.hit_delta_OOS_2026)} | {'ROBUST' if r.robust_transfer else 'NO'} |")
    L += ["","Positive DROP contribution means the CORE got worse when that feature was removed.","",
          "## Frozen CORE_PLUS family tests","",
          "| Family | Bridge AUC Δ | OOS AUC Δ | Bridge return Δ | OOS return Δ | OOS hit Δ | Transfer |",
          "|---|---:|---:|---:|---:|---:|---|"]
    q=components[components.component_type=="ADD_FAMILY"].copy().sort_values("return_delta_OOS_2026",ascending=False)
    for _,r in q.iterrows():
        L.append(f"| {r.component} | {r.auc_delta_BRIDGE_2025:+.4f} | {r.auc_delta_OOS_2026:+.4f} | {pct(r.return_delta_BRIDGE_2025)} | {pct(r.return_delta_OOS_2026)} | {pp(r.hit_delta_OOS_2026)} | {'ROBUST' if r.robust_transfer else 'NO'} |")
    L += ["","## Stable components",""]
    if v["stable_components"]:
        for z in v["stable_components"]:
            L.append(f"- **{z['component']}** ({z['component_type']})")
    else:
        L.append("- None under the preregistered transfer rule.")
    L += ["","## Gates",""]
    for k,val in v["gates"].items():
        L.append(f"- {'PASS' if val else 'FAIL'} — `{k}`")
    L += ["","## Interpretation","",
          "This LAB does not tune 2026. A robust component must improve bridge and OOS with the same sign. If the CORE reproduces but no component transfers, the correct conclusion is that the top-bucket effect is distributed/interaction-driven or unstable, not permission to optimize thresholds on OOS."]
    (OUT/"REPORT.md").write_text("\n".join(L),encoding="utf-8")

def main():
    paths=downloads(); b=load(paths); x=make_panel(b); e=make_events(x); e,thr=build_targets(e)
    metrics,router,scores=train_and_score(e); components=component_table(metrics,router); v=verdict(router,components)
    metrics.to_csv(OUT/"model_metrics.csv",index=False)
    router.to_csv(OUT/"router_summary.csv",index=False)
    components.to_csv(OUT/"component_transfer.csv",index=False)
    scores.reset_index(drop=False).to_csv(OUT/"core_event_scores.csv",index=False)
    (OUT/"thresholds.json").write_text(json.dumps(thr,indent=2,default=jdefault))
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,default=jdefault))
    audit={
        "lab":LAB,"seed":SEED,"primary":PRIMARY,"impulse_q":IMPULSE_Q,"cooldown_bars":COOLDOWN,
        "coverage_start":str(x.index.min()),"coverage_end":str(x.index.max()),"bars":len(x),
        "events":e.groupby("split").size().to_dict(),"target_threshold_source":"DEV_2021_2024_only",
        "core_features":CORE,"families":FAMILIES,"oos_tuned":False,"post_decision_features":False
    }
    (OUT/"audit.json").write_text(json.dumps(audit,indent=2,default=jdefault))
    write_report(x,e,thr,metrics,router,components,v)
    print(json.dumps(v,indent=2,default=jdefault)); print((OUT/"REPORT.md").read_text())

if __name__=="__main__": main()
