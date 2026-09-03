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

LAB="BTC_PAXG_24H_REGIME_AND_RIGHT_TAIL_TRANSFER_LAB_002"
SEED=20260903
OUT=Path(__file__).resolve().parent/"output"
CACHE=Path(__file__).resolve().parent/"cache"
OUT.mkdir(parents=True,exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)
START_MONTH="2021-01"; END_MONTH="2026-08"; INTERVAL="15m"
BASE="https://data.binance.vision/data/spot/monthly/klines"
COLS=["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_base","taker_quote","ignore"]
ROLL=30*24*4; IMPULSE_Q=.975; COOLDOWN=16; PRIMARY="24h"; HORIZONS={"12h":48,"24h":96,"48h":192}
BTC_ONLY=["impulse_dir","btc_z15","btc_z60","btc_z4h","btc_z24h","btc_vol_z","btc_range_z","btc_corr7d_lag","hour_sin","hour_cos"]
PAXG_ADD=["paxg_z15","paxg_z60","paxg_z4h","paxg_z24h","paxg_pre60_z","paxg_accel_z","paxg_vol_z","paxg_range_z","paxg_corr7d","paxg_corr30d","paxg_signed60","paxg_signed24h","div60_signed","div4h_signed","div24h_signed","corr_x_trend"]

def months(a,b): return [str(x) for x in pd.period_range(a,b,freq="M")]
def url(sym,m): return f"{BASE}/{sym}/{INTERVAL}/{sym}-{INTERVAL}-{m}.zip"
def get_one(sym,m):
    p=CACHE/f"{sym}-{INTERVAL}-{m}.zip"
    if p.exists() and p.stat().st_size>100: return p
    for k in range(4):
        try:
            r=requests.get(url(sym,m),timeout=45)
            if r.status_code==404: return None
            r.raise_for_status()
            if len(r.content)<100: return None
            p.write_bytes(r.content); return p
        except Exception as e:
            if k==3: print("WARN",sym,m,e,file=sys.stderr); return None
            time.sleep(1.5*(k+1))
def downloads():
    out={s:[] for s in ("BTCUSDT","PAXGUSDT")}; jobs=[(s,m) for s in out for m in months(START_MONTH,END_MONTH)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        fut={ex.submit(get_one,s,m):(s,m) for s,m in jobs}
        for f in as_completed(fut):
            s,m=fut[f]; p=f.result()
            if p: out[s].append(p)
    for s in out: out[s]=sorted(out[s]); print(s,len(out[s]),"monthly files")
    return out
def epoch(v):
    x=pd.to_numeric(v,errors="coerce"); med=x.dropna().median(); unit="us" if np.isfinite(med) and med>1e14 else "ms"
    return pd.to_datetime(x,unit=unit,utc=True,errors="coerce")
def read_month(p):
    with zipfile.ZipFile(p) as z:
        names=[n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names: return pd.DataFrame()
        raw=z.read(names[0])
    d=pd.read_csv(io.BytesIO(raw),header=None,names=COLS); d["time"]=epoch(d.open_time)
    for c in ["open","high","low","close","volume","quote_volume","trades"]: d[c]=pd.to_numeric(d[c],errors="coerce")
    return d[["time","open","high","low","close","volume","quote_volume","trades"]].dropna()
def load(paths):
    fs=[read_month(p) for p in paths]; fs=[x for x in fs if len(x)]
    if not fs: raise RuntimeError("No data")
    return pd.concat(fs,ignore_index=True).sort_values("time").drop_duplicates("time").set_index("time")
def rz(s,w=ROLL):
    mu=s.rolling(w,min_periods=max(100,w//4)).mean().shift(1); sd=s.rolling(w,min_periods=max(100,w//4)).std(ddof=0).shift(1)
    return (s-mu)/sd.replace(0,np.nan)
def make_panel(b,p):
    x=b.add_prefix("btc_").join(p.add_prefix("paxg_"),how="inner")
    for a in ("btc","paxg"):
        c=x[f"{a}_close"]; x[f"{a}_lr15"]=np.log(c).diff(); x[f"{a}_lr60"]=np.log(c/c.shift(4)); x[f"{a}_lr4h"]=np.log(c/c.shift(16)); x[f"{a}_lr24h"]=np.log(c/c.shift(96))
        for k in ("15","60","4h","24h"): x[f"{a}_z{k}"]=rz(x[f"{a}_lr{k}"])
        x[f"{a}_vol_z"]=rz(np.log1p(x[f"{a}_quote_volume"])); rr=(x[f"{a}_high"]-x[f"{a}_low"])/x[f"{a}_close"]; x[f"{a}_range_z"]=rz(rr)
    x["paxg_pre60"]=x.paxg_lr60.shift(4); x["paxg_pre60_z"]=rz(x.paxg_pre60); x["paxg_accel_z"]=x.paxg_z60-x.paxg_pre60_z
    x["paxg_corr7d"]=x.btc_lr15.rolling(7*96,min_periods=3*96).corr(x.paxg_lr15).shift(1); x["paxg_corr30d"]=x.btc_lr15.rolling(30*96,min_periods=10*96).corr(x.paxg_lr15).shift(1)
    x["btc_corr7d_lag"]=x.btc_lr15.rolling(7*96,min_periods=3*96).corr(x.btc_lr15.shift(1)).shift(1); h=x.index.hour+x.index.minute/60; x["hour_sin"]=np.sin(2*np.pi*h/24); x["hour_cos"]=np.cos(2*np.pi*h/24)
    x["impulse_thr"]=x.btc_lr60.abs().rolling(ROLL,min_periods=ROLL//2).quantile(IMPULSE_Q).shift(1); x["impulse_raw"]=x.btc_lr60.abs()>=x.impulse_thr; x["impulse_dir"]=np.sign(x.btc_lr60).astype(float)
    x["paxg_signed60"]=x.impulse_dir*x.paxg_z60; x["paxg_signed24h"]=x.impulse_dir*x.paxg_z24h; x["div60_signed"]=x.impulse_dir*(x.btc_z60-x.paxg_z60); x["div4h_signed"]=x.impulse_dir*(x.btc_z4h-x.paxg_z4h); x["div24h_signed"]=x.impulse_dir*(x.btc_z24h-x.paxg_z24h); x["corr_x_trend"]=x.paxg_corr30d*x.paxg_signed24h
    return x
def make_events(x):
    cand=np.flatnonzero(x.impulse_raw.fillna(False).to_numpy()); chosen=[]; last=-10**9
    for i in cand:
        if i-last>=COOLDOWN: chosen.append(i); last=i
    e=x.iloc[chosen].copy(); e["bar_i"]=chosen; e["decision_time"]=e.index; e["entry_time"]=x.index.to_series().shift(-1).iloc[chosen].to_numpy(); e["entry"]=x.btc_open.shift(-1).iloc[chosen].to_numpy()
    for name,bars in HORIZONS.items():
        fut=x.btc_close.shift(-bars).iloc[chosen].to_numpy(); raw=fut/e.entry.to_numpy()-1.0; e[f"raw_{name}"]=raw; e[f"cont_{name}"]=raw*e.impulse_dir.to_numpy(); e[f"rev_{name}"]=-e[f"cont_{name}"]
    y=e.index.year; e["split"]=np.where(y<=2024,"DEV_2021_2024",np.where(y==2025,"BRIDGE_2025","OOS_2026")); e=e.replace([np.inf,-np.inf],np.nan)
    return e.dropna(subset=["entry",f"cont_{PRIMARY}","btc_z60","paxg_z60","paxg_z24h","paxg_corr30d"])
def fit_pipe(d,features,target):
    m=Pipeline([("imp",SimpleImputer(strategy="median")),("sc",StandardScaler()),("lr",LogisticRegression(C=.5,max_iter=4000,random_state=SEED))]); m.fit(d[features],d[target].astype(int)); return m
def safe_metrics(y,p):
    if len(np.unique(y))<2: return (np.nan,np.nan,np.nan)
    return float(roc_auc_score(y,p)),float(brier_score_loss(y,p)),float(log_loss(y,p,labels=[0,1]))
def bootstrap_mean(a,n=1500,seed=SEED):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if len(a)<2: return (np.nan,np.nan,np.nan)
    rng=np.random.default_rng(seed+len(a)*13); idx=rng.integers(0,len(a),size=(n,len(a))); means=a[idx].mean(1); lo,hi=np.quantile(means,[.025,.975]); return float(a.mean()),float(lo),float(hi)
def build_targets(e):
    dev=e[e.split=="DEV_2021_2024"]; thr_cont=float(dev[f"cont_{PRIMARY}"].quantile(.75)); thr_rev=float(dev[f"rev_{PRIMARY}"].quantile(.75)); thr_abs=float(dev[f"raw_{PRIMARY}"].abs().quantile(.75))
    e[f"tail_cont_{PRIMARY}"]=(e[f"cont_{PRIMARY}"]>=thr_cont).astype(int); e[f"tail_rev_{PRIMARY}"]=(e[f"rev_{PRIMARY}"]>=thr_rev).astype(int); e[f"tail_abs_{PRIMARY}"]=(e[f"raw_{PRIMARY}"].abs()>=thr_abs).astype(int)
    return e,{"cont_thr":thr_cont,"rev_thr":thr_rev,"abs_thr":thr_abs}
def score_models(e,thresholds):
    dev=e[e.split=="DEV_2021_2024"].copy(); rows=[]; scored=[]; models={}
    for fs,feats in (("BTC_ONLY",BTC_ONLY),("BTC_PLUS_PAXG",BTC_ONLY+PAXG_ADD)):
        models[(fs,"cont")]=fit_pipe(dev,feats,f"tail_cont_{PRIMARY}"); models[(fs,"rev")]=fit_pipe(dev,feats,f"tail_rev_{PRIMARY}")
    for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
        d=e[e.split==sp].copy()
        for fs,feats in (("BTC_ONLY",BTC_ONLY),("BTC_PLUS_PAXG",BTC_ONLY+PAXG_ADD)):
            pc=models[(fs,"cont")].predict_proba(d[feats])[:,1]; pr=models[(fs,"rev")].predict_proba(d[feats])[:,1]; d[f"{fs}_p_cont"]=pc; d[f"{fs}_p_rev"]=pr
            for side,p,target in [("CONT",pc,f"tail_cont_{PRIMARY}"),("REV",pr,f"tail_rev_{PRIMARY}")]:
                auc,brier,ll=safe_metrics(d[target].to_numpy(),p); rows.append(dict(split=sp,model=fs,side=side,n=len(d),auc=auc,brier=brier,logloss=ll))
        scored.append(d)
    s=pd.concat(scored).sort_index(); devs=s[s.split=="DEV_2021_2024"].copy()
    for model in ("BTC_ONLY","BTC_PLUS_PAXG"):
        q80=float(np.maximum(devs[f"{model}_p_cont"],devs[f"{model}_p_rev"]).quantile(.80)); s[f"{model}_side"]=np.where(s[f"{model}_p_cont"]>=s[f"{model}_p_rev"],"CONT","REV"); s[f"{model}_conf"]=np.maximum(s[f"{model}_p_cont"],s[f"{model}_p_rev"]); s[f"{model}_top20"]=s[f"{model}_conf"]>=q80; s[f"{model}_chosen_ret"]=np.where(s[f"{model}_side"]=="CONT",s[f"cont_{PRIMARY}"],s[f"rev_{PRIMARY}"]); s[f"{model}_tail_hit"]=np.where(s[f"{model}_side"]=="CONT",s[f"tail_cont_{PRIMARY}"],s[f"tail_rev_{PRIMARY}"])
    return pd.DataFrame(rows),s
def regime_tables(e):
    z=e.paxg_z24h; corr=e.paxg_corr30d; e=e.copy(); e["gold_trend"]=np.select([z>=.5,z<=-.5],["GOLD_UP","GOLD_DOWN"],default="GOLD_NEUTRAL"); e["corr_regime"]=np.select([corr>=.15,corr<=-.15],["POS_CORR","NEG_CORR"],default="LOW_CORR"); e["regime"]=e.gold_trend.astype(str)+"__"+e.corr_regime.astype(str); rows=[]
    for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
        for reg,g in e[e.split==sp].groupby("regime"):
            m,lo,hi=bootstrap_mean(g[f"cont_{PRIMARY}"]); rows.append(dict(split=sp,regime=reg,n=len(g),cont_mean=m,cont_ci_lo=lo,cont_ci_hi=hi,cont_tail_rate=g[f"tail_cont_{PRIMARY}"].mean(),rev_tail_rate=g[f"tail_rev_{PRIMARY}"].mean(),abs24_mean=g[f"raw_{PRIMARY}"].abs().mean()))
    return pd.DataFrame(rows).sort_values(["split","n"],ascending=[True,False])
def summarize_router(s):
    rows=[]
    for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
        d=s[s.split==sp]
        for model in ("BTC_ONLY","BTC_PLUS_PAXG"):
            q=d[d[f"{model}_top20"]]; m,lo,hi=bootstrap_mean(q[f"{model}_chosen_ret"]); rows.append(dict(split=sp,model=model,n_total=len(d),n_top=len(q),top_tail_hit=q[f"{model}_tail_hit"].mean(),top_mean_chosen_ret=m,top_ci_lo=lo,top_ci_hi=hi,top_median_chosen_ret=q[f"{model}_chosen_ret"].median(),all_tail_hit=d[f"{model}_tail_hit"].mean(),all_mean_chosen_ret=d[f"{model}_chosen_ret"].mean()))
    return pd.DataFrame(rows)
def verdict(metrics,router):
    def mm(sp,model,side,col): return float(metrics[(metrics.split==sp)&(metrics.model==model)&(metrics.side==side)].iloc[0][col])
    def rr(sp,model,col): return float(router[(router.split==sp)&(router.model==model)].iloc[0][col])
    aa={}; bi={}
    for sp in ("BRIDGE_2025","OOS_2026"):
        aa[sp]=np.mean([mm(sp,"BTC_PLUS_PAXG",side,"auc")-mm(sp,"BTC_ONLY",side,"auc") for side in ("CONT","REV")]); bi[sp]=np.mean([mm(sp,"BTC_ONLY",side,"brier")-mm(sp,"BTC_PLUS_PAXG",side,"brier") for side in ("CONT","REV")])
    od=rr("OOS_2026","BTC_PLUS_PAXG","top_mean_chosen_ret")-rr("OOS_2026","BTC_ONLY","top_mean_chosen_ret"); bd=rr("BRIDGE_2025","BTC_PLUS_PAXG","top_mean_chosen_ret")-rr("BRIDGE_2025","BTC_ONLY","top_mean_chosen_ret"); oh=rr("OOS_2026","BTC_PLUS_PAXG","top_tail_hit")-rr("OOS_2026","BTC_ONLY","top_tail_hit"); bh=rr("BRIDGE_2025","BTC_PLUS_PAXG","top_tail_hit")-rr("BRIDGE_2025","BTC_ONLY","top_tail_hit"); n_oos=int(router[(router.split=="OOS_2026")&(router.model=="BTC_PLUS_PAXG")].iloc[0].n_total)
    gates={"oos_events_ge_100":n_oos>=100,"bridge_avg_auc_delta_positive":aa["BRIDGE_2025"]>0,"oos_avg_auc_delta_ge_0.02":aa["OOS_2026"]>=.02,"oos_avg_brier_improves":bi["OOS_2026"]>0,"bridge_top20_return_delta_positive":bd>0,"oos_top20_return_delta_positive":od>0,"oos_top20_tail_hit_delta_ge_0.05":oh>=.05,"transfer_same_sign":bd>0 and od>0}; gates={k:bool(val) for k,val in gates.items()}; n=int(sum(gates.values()))
    if n==len(gates): v="PASS_PAXG_RIGHT_TAIL_ROUTER"
    elif n>=5 and gates["oos_events_ge_100"] and gates["oos_top20_return_delta_positive"]: v="WATCH_RIGHT_TAIL_ROUTER"
    else: v="FAIL_NO_ROBUST_RIGHT_TAIL_TRANSFER"
    return dict(verdict=v,gates_passed=n,gates_total=len(gates),gates=gates,avg_auc_delta_bridge=float(aa["BRIDGE_2025"]),avg_auc_delta_oos=float(aa["OOS_2026"]),avg_brier_improvement_oos=float(bi["OOS_2026"]),bridge_top20_return_delta=float(bd),oos_top20_return_delta=float(od),bridge_top20_hit_delta=float(bh),oos_top20_hit_delta=float(oh))
def pct(x): return "—" if not np.isfinite(x) else f"{100*x:+.3f}%"
def ppf(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
def write_report(x,e,t,m,r,reg,v):
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","",f"Coverage: {x.index.min()} -> {x.index.max()} | bars {len(x):,}",f"DEV tail thresholds: CONT {pct(t['cont_thr'])}, REV {pct(t['rev_thr'])}, ABS {pct(t['abs_thr'])}",""]
    for sp,n in e.groupby("split").size().items(): lines.append(f"- {sp}: {n:,} events")
    lines += ["","## AUC","","|Split|Side|BTC|BTC+PAXG|Delta|","|---|---|---:|---:|---:|"]
    for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
        for side in ["CONT","REV"]:
            a=float(m[(m.split==sp)&(m.model=="BTC_ONLY")&(m.side==side)].iloc[0].auc); b=float(m[(m.split==sp)&(m.model=="BTC_PLUS_PAXG")&(m.side==side)].iloc[0].auc); lines.append(f"|{sp}|{side}|{a:.4f}|{b:.4f}|{b-a:+.4f}|")
    lines += ["","## Router top-20","","|Split|Model|N|Tail hit|Mean chosen return|95% CI|","|---|---|---:|---:|---:|---:|"]
    for _,q in r.iterrows(): lines.append(f"|{q.split}|{q.model}|{int(q.n_top)}|{ppf(q.top_tail_hit)}|{pct(q.top_mean_chosen_ret)}|[{pct(q.top_ci_lo)}, {pct(q.top_ci_hi)}]|")
    lines += ["",f"Bridge return delta: {pct(v['bridge_top20_return_delta'])}",f"OOS return delta: {pct(v['oos_top20_return_delta'])}",f"OOS tail-hit delta: {v['oos_top20_hit_delta']*100:+.1f} pp",f"Bridge avg AUC delta: {v['avg_auc_delta_bridge']:+.4f}",f"OOS avg AUC delta: {v['avg_auc_delta_oos']:+.4f}",f"OOS Brier improvement: {v['avg_brier_improvement_oos']:+.5f}","","## OOS regimes","","|Regime|N|Cont tail|Rev tail|Mean abs24|","|---|---:|---:|---:|---:|"]
    for _,q in reg[reg.split=="OOS_2026"].sort_values("n",ascending=False).head(8).iterrows(): lines.append(f"|{q.regime}|{int(q.n)}|{ppf(q.cont_tail_rate)}|{ppf(q.rev_tail_rate)}|{pct(q.abs24_mean)}|")
    lines += ["","## Gates"]+[f"- {'PASS' if val else 'FAIL'} — {k}" for k,val in v['gates'].items()]+["",f"Score {v['gates_passed']}/{v['gates_total']} -> {v['verdict']}","","No 2026 tuning is authorized after this result."]
    (OUT/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")
def main():
    paths=downloads(); b=load(paths["BTCUSDT"]); p=load(paths["PAXGUSDT"]); x=make_panel(b,p); e=make_events(x); e,t=build_targets(e); m,s=score_models(e,t); reg=regime_tables(e); r=summarize_router(s); v=verdict(m,r)
    m.to_csv(OUT/"model_metrics.csv",index=False); r.to_csv(OUT/"router_summary.csv",index=False); reg.to_csv(OUT/"regime_summary.csv",index=False)
    keep=["decision_time","entry_time","split","impulse_dir","entry",f"cont_{PRIMARY}",f"rev_{PRIMARY}",f"tail_cont_{PRIMARY}",f"tail_rev_{PRIMARY}","paxg_z24h","paxg_corr30d","BTC_ONLY_side","BTC_ONLY_conf","BTC_ONLY_top20","BTC_ONLY_chosen_ret","BTC_ONLY_tail_hit","BTC_PLUS_PAXG_side","BTC_PLUS_PAXG_conf","BTC_PLUS_PAXG_top20","BTC_PLUS_PAXG_chosen_ret","BTC_PLUS_PAXG_tail_hit"]
    s.reset_index(drop=False)[keep].to_csv(OUT/"event_scores.csv",index=False); (OUT/"thresholds.json").write_text(json.dumps(t,indent=2)); (OUT/"verdict.json").write_text(json.dumps(v,indent=2))
    audit={"lab":LAB,"seed":SEED,"primary":PRIMARY,"impulse_q":IMPULSE_Q,"cooldown_bars":COOLDOWN,"coverage_start":str(x.index.min()),"coverage_end":str(x.index.max()),"bars":len(x),"events":{str(k):int(val) for k,val in e.groupby("split").size().to_dict().items()},"paxg_forward_fill":False,"target_threshold_source":"DEV_2021_2024_only","oos_tuned":False}; (OUT/"audit.json").write_text(json.dumps(audit,indent=2)); write_report(x,e,t,m,r,reg,v); print(json.dumps(v,indent=2)); print((OUT/"REPORT.md").read_text())
if __name__=="__main__": main()
