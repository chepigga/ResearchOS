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

LAB="BTC_POST_IMPULSE_RANGE_STATE_AND_24H_REVERSAL_ROUTER_LAB_004"
SEED=20260903
OUT=Path(__file__).resolve().parent/"output"; CACHE=Path(__file__).resolve().parent/"cache"
OUT.mkdir(parents=True,exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)
START_MONTH="2021-01"; END_MONTH="2026-08"; INTERVAL="15m"
BASE="https://data.binance.vision/data/spot/monthly/klines"
COLS=["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_base","taker_quote","ignore"]
ROLL=30*24*4; IMPULSE_Q=.975; COOLDOWN=16; H24=96
CLOCKS={"D15":1,"D30":2,"D60":4}; PRIMARY="D30"
CORE=["impulse_dir","btc_z15","btc_z60","btc_z4h","btc_z24h","btc_vol_z","btc_range_z","btc_corr7d_lag","hour_sin","hour_cos"]
FAMILIES={
 "RANGE_STATE":["event_range_z","decision_range_z","post_pre_range_ratio","range_persistence"],
 "EXHAUSTION":["impulse_eff60","event_clv_signed","post_signed_ret","retrace_frac","opp_bar_share"],
 "ACCEPTANCE":["impulse_break_pre60","decision_accept","failed_accept","max_extension","decision_clv_signed"],
 "RECOVERY_SEQUENCE":["post_signed_eff","terminal_opp_streak","first_post_signed","post_signed_ret","opp_bar_share"],
 "VOLUME_RESPONSE":["event_vol_z","post_pre_vol_ratio","decision_vol_z","post_vol_slope"],
}

def months(a,b): return [str(x) for x in pd.period_range(a,b,freq="M")]
def url(m): return f"{BASE}/BTCUSDT/{INTERVAL}/BTCUSDT-{INTERVAL}-{m}.zip"
def get_one(m):
    p=CACHE/f"BTCUSDT-{INTERVAL}-{m}.zip"
    if p.exists() and p.stat().st_size>100: return p
    for k in range(4):
        try:
            r=requests.get(url(m),timeout=45)
            if r.status_code==404: return None
            r.raise_for_status()
            if len(r.content)<100: return None
            p.write_bytes(r.content); return p
        except Exception as e:
            if k==3: print("WARN",m,e,file=sys.stderr); return None
            time.sleep(1.5*(k+1))
def downloads():
    out=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        fut={ex.submit(get_one,m):m for m in months(START_MONTH,END_MONTH)}
        for f in as_completed(fut):
            p=f.result()
            if p: out.append(p)
    out=sorted(out); print("BTCUSDT",len(out),"monthly files"); return out
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
    if not fs: raise RuntimeError("No BTC data")
    return pd.concat(fs,ignore_index=True).sort_values("time").drop_duplicates("time").set_index("time")
def rz(s,w=ROLL):
    mu=s.rolling(w,min_periods=max(100,w//4)).mean().shift(1); sd=s.rolling(w,min_periods=max(100,w//4)).std(ddof=0).shift(1)
    return (s-mu)/sd.replace(0,np.nan)
def make_panel(b):
    x=b.add_prefix("btc_"); c=x.btc_close
    x["btc_lr15"]=np.log(c).diff(); x["btc_lr60"]=np.log(c/c.shift(4)); x["btc_lr4h"]=np.log(c/c.shift(16)); x["btc_lr24h"]=np.log(c/c.shift(96))
    for k in ["15","60","4h","24h"]: x[f"btc_z{k}"]=rz(x[f"btc_lr{k}"])
    x["btc_vol_z"]=rz(np.log1p(x.btc_quote_volume)); x["btc_range"]=(x.btc_high-x.btc_low)/x.btc_close; x["btc_range_z"]=rz(x.btc_range)
    x["btc_corr7d_lag"]=x.btc_lr15.rolling(7*96,min_periods=3*96).corr(x.btc_lr15.shift(1)).shift(1)
    h=x.index.hour+x.index.minute/60; x["hour_sin"]=np.sin(2*np.pi*h/24); x["hour_cos"]=np.cos(2*np.pi*h/24)
    x["impulse_thr"]=x.btc_lr60.abs().rolling(ROLL,min_periods=ROLL//2).quantile(IMPULSE_Q).shift(1); x["impulse_raw"]=x.btc_lr60.abs()>=x.impulse_thr
    return x

def parent_indices(x):
    cand=np.flatnonzero(x.impulse_raw.fillna(False).to_numpy()); chosen=[]; last=-10**9
    for i in cand:
        if i-last>=COOLDOWN: chosen.append(i); last=i
    return chosen

def clv_signed(x,j,d):
    den=x.btc_high.iloc[j]-x.btc_low.iloc[j]
    if not np.isfinite(den) or den<=0: return np.nan
    clv=(x.btc_close.iloc[j]-x.btc_low.iloc[j])/den
    return float((2*clv-1) if d>0 else (1-2*clv))
def terminal_opp(signs,d):
    n=0
    for s in signs[::-1]:
        if np.isfinite(s) and s*d<0: n+=1
        else: break
    return float(n)

def event_table(x,delay):
    rows=[]; n=len(x); parents=parent_indices(x)
    for i in parents:
        j=i+delay; entry_i=j+1; exit_i=j+H24
        if i<20 or exit_i>=n: continue
        d=float(np.sign(x.btc_lr60.iloc[i]));
        if d==0 or not np.isfinite(d): continue
        entry=float(x.btc_open.iloc[entry_i]); exitp=float(x.btc_close.iloc[exit_i])
        if not np.isfinite(entry) or entry<=0 or not np.isfinite(exitp): continue
        raw=exitp/entry-1.0; rev=-d*raw
        r={k:float(x[k].iloc[i]) if np.isfinite(x[k].iloc[i]) else np.nan for k in CORE if k!="impulse_dir"}
        r["impulse_dir"]=d; r["event_time"]=x.index[i]; r["decision_time"]=x.index[j]; r["entry_time"]=x.index[entry_i]; r["entry"]=entry; r["raw_24h"]=raw; r["rev_24h"]=rev
        r["event_range_z"]=float(x.btc_range_z.iloc[i]); r["decision_range_z"]=float(x.btc_range_z.iloc[j]); r["event_vol_z"]=float(x.btc_vol_z.iloc[i]); r["decision_vol_z"]=float(x.btc_vol_z.iloc[j])
        pre_rng=x.btc_range.iloc[max(0,i-16):i]; post_rng=x.btc_range.iloc[i+1:j+1]
        r["post_pre_range_ratio"]=float(post_rng.mean()/pre_rng.mean()) if len(post_rng) and pre_rng.mean()>0 else np.nan
        r["range_persistence"]=float(np.mean(post_rng.to_numpy()>pre_rng.median())) if len(post_rng) else np.nan
        abs4=x.btc_lr15.iloc[i-3:i+1].abs().sum(); r["impulse_eff60"]=float(abs(x.btc_lr60.iloc[i])/abs4) if abs4>0 else np.nan
        r["event_clv_signed"]=clv_signed(x,i,d)
        signed_post=float(d*np.log(x.btc_close.iloc[j]/x.btc_close.iloc[i])); r["post_signed_ret"]=signed_post
        impulse_abs=abs(float(x.btc_lr60.iloc[i])); r["retrace_frac"]=float(max(0,-signed_post)/impulse_abs) if impulse_abs>0 else np.nan
        post_lr=x.btc_lr15.iloc[i+1:j+1].to_numpy(); post_sign=np.sign(post_lr); r["opp_bar_share"]=float(np.mean(post_sign*d<0)) if len(post_sign) else np.nan
        pre_hi=float(x.btc_high.iloc[i-4:i].max()); pre_lo=float(x.btc_low.iloc[i-4:i].min())
        imp_close=float(x.btc_close.iloc[i]); dec_close=float(x.btc_close.iloc[j])
        broke=(imp_close>pre_hi) if d>0 else (imp_close<pre_lo); accept=(dec_close>pre_hi) if d>0 else (dec_close<pre_lo)
        r["impulse_break_pre60"]=float(broke); r["decision_accept"]=float(accept); r["failed_accept"]=float(broke and not accept)
        seg_hi=float(x.btc_high.iloc[i:j+1].max()); seg_lo=float(x.btc_low.iloc[i:j+1].min())
        r["max_extension"]=float(np.log(seg_hi/imp_close)) if d>0 else float(np.log(imp_close/seg_lo))
        r["decision_clv_signed"]=clv_signed(x,j,d)
        path=float(np.nansum(np.abs(post_lr))); r["post_signed_eff"]=float(signed_post/path) if path>0 else 0.0
        r["terminal_opp_streak"]=terminal_opp(post_sign,d); r["first_post_signed"]=float(d*post_lr[0]) if len(post_lr) and np.isfinite(post_lr[0]) else np.nan
        pre_vol=x.btc_quote_volume.iloc[max(0,i-16):i]; post_vol=x.btc_quote_volume.iloc[i+1:j+1]
        r["post_pre_vol_ratio"]=float(post_vol.mean()/pre_vol.mean()) if len(post_vol) and pre_vol.mean()>0 else np.nan
        if len(post_vol)>=2:
            y=np.log1p(post_vol.to_numpy(float)); r["post_vol_slope"]=float(np.polyfit(np.arange(len(y)),y,1)[0])
        else: r["post_vol_slope"]=0.0
        yr=x.index[i].year; r["split"]="DEV_2021_2024" if yr<=2024 else ("BRIDGE_2025" if yr==2025 else "OOS_2026")
        rows.append(r)
    return pd.DataFrame(rows).replace([np.inf,-np.inf],np.nan)

def fit_pipe(d,features,target):
    m=Pipeline([("imp",SimpleImputer(strategy="median")),("sc",StandardScaler()),("lr",LogisticRegression(C=.5,max_iter=4000,random_state=SEED))])
    m.fit(d[features],d[target].astype(int)); return m
def metrics(y,p):
    if len(np.unique(y))<2: return np.nan,np.nan,np.nan
    return float(roc_auc_score(y,p)),float(brier_score_loss(y,p)),float(log_loss(y,p,labels=[0,1]))
def boot(a,n=1500):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if len(a)<2: return np.nan,np.nan,np.nan
    rng=np.random.default_rng(SEED+len(a)*19); means=a[rng.integers(0,len(a),size=(n,len(a)))].mean(1); lo,hi=np.quantile(means,[.025,.975]); return float(a.mean()),float(lo),float(hi)
def model_sets():
    out={"CORE":CORE.copy()}
    for fam,fs in FAMILIES.items(): out[f"CORE_PLUS__{fam}"]=list(dict.fromkeys(CORE+fs))
    allpost=[]
    for fs in FAMILIES.values(): allpost.extend(fs)
    out["FULL_POST"]=list(dict.fromkeys(CORE+allpost)); return out

def score_clock(e,clock):
    dev=e[e.split=="DEV_2021_2024"].copy(); thr=float(dev.rev_24h.quantile(.75)); e=e.copy(); e["tail_rev"]=(e.rev_24h>=thr).astype(int)
    sets=model_sets(); rows=[]; router=[]
    for name,fs in sets.items():
        m=fit_pipe(dev,fs,"tail_rev"); pdev=m.predict_proba(dev[fs])[:,1]; q80=float(np.quantile(pdev,.80))
        for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
            d=e[e.split==sp].copy(); p=m.predict_proba(d[fs])[:,1]; auc,br,ll=metrics(d.tail_rev.to_numpy(),p); top=p>=q80; vals=d.rev_24h.to_numpy()[top]
            mean,lo,hi=boot(vals); hit=float(d.tail_rev.to_numpy()[top].mean()) if top.sum() else np.nan
            rows.append(dict(clock=clock,split=sp,model=name,n=len(d),auc=auc,brier=br,logloss=ll))
            router.append(dict(clock=clock,split=sp,model=name,n_total=len(d),n_top=int(top.sum()),top_hit=hit,top_mean_rev=mean,top_ci_lo=lo,top_ci_hi=hi,threshold=thr,q80=q80))
    return pd.DataFrame(rows),pd.DataFrame(router),thr

def summarize_components(mm,rr):
    rows=[]
    def m(sp,model,col): return float(mm[(mm.split==sp)&(mm.model==model)].iloc[0][col])
    def r(sp,model,col): return float(rr[(rr.split==sp)&(rr.model==model)].iloc[0][col])
    for fam in FAMILIES:
        name=f"CORE_PLUS__{fam}"
        row={"family":fam}
        for sp in ["BRIDGE_2025","OOS_2026"]:
            row[f"auc_delta_{sp}"]=m(sp,name,"auc")-m(sp,"CORE","auc")
            row[f"brier_imp_{sp}"]=m(sp,"CORE","brier")-m(sp,name,"brier")
            row[f"return_delta_{sp}"]=r(sp,name,"top_mean_rev")-r(sp,"CORE","top_mean_rev")
            row[f"hit_delta_{sp}"]=r(sp,name,"top_hit")-r(sp,"CORE","top_hit")
        row["robust_transfer"]=bool(row["auc_delta_BRIDGE_2025"]>0 and row["auc_delta_OOS_2026"]>0 and row["return_delta_BRIDGE_2025"]>0 and row["return_delta_OOS_2026"]>0 and row["brier_imp_OOS_2026"]>0)
        rows.append(row)
    return pd.DataFrame(rows)
def verdict(mm,rr,comp):
    def m(sp,model,col): return float(mm[(mm.split==sp)&(mm.model==model)].iloc[0][col])
    def r(sp,model,col): return float(rr[(rr.split==sp)&(rr.model==model)].iloc[0][col])
    oos_n=int(rr[(rr.split=="OOS_2026")&(rr.model=="CORE")].iloc[0].n_total)
    robust=comp[comp.robust_transfer].family.tolist()
    gates={"oos_events_ge_100":oos_n>=100,"core_oos_auc_ge_0.55":m("OOS_2026","CORE","auc")>=.55,"core_oos_top_return_positive":r("OOS_2026","CORE","top_mean_rev")>0,"named_transferable_family_found":len(robust)>0}
    if all(gates.values()): v="PASS_POST_IMPULSE_REVERSAL_MECHANISM"
    elif sum(gates.values())>=3: v="WATCH_PARTIAL_POST_IMPULSE_MECHANISM"
    else: v="FAIL_NO_TRANSFERABLE_POST_IMPULSE_MECHANISM"
    return {"verdict":v,"gates":gates,"gates_passed":int(sum(gates.values())),"gates_total":len(gates),"robust_families":robust,"core_oos_auc":m("OOS_2026","CORE","auc"),"core_oos_top_mean_rev":r("OOS_2026","CORE","top_mean_rev"),"core_oos_top_hit":r("OOS_2026","CORE","top_hit")}
def pct(x): return "—" if not np.isfinite(x) else f"{100*x:+.3f}%"
def ppf(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
def report(allmm,allrr,comp,v,thresholds,events):
    mm=allmm[allmm.clock==PRIMARY]; rr=allrr[allrr.clock==PRIMARY]
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","","Role: leakage-safe post-impulse BTC reversal-router study; not a production strategy.","","## Primary causal clock","","- Parent impulse: frozen 60m |return| >= prior 30d 97.5th percentile, 4h cooldown.","- Observe exactly **+30m** (2 completed M15 bars) after impulse, then enter at next M15 open.","- Direction: opposite parent impulse. Outcome: 24h from delayed entry.",f"- DEV-only REV-tail threshold: **{pct(thresholds[PRIMARY])}**.","","## Event census",""]
    for sp,n in events[PRIMARY].groupby("split").size().items(): lines.append(f"- {sp}: **{n:,}** events")
    lines += ["","## CORE reproduction at delayed clock","","| Split | AUC | Brier | N top | Tail hit | Mean reversal 24h | 95% CI |","|---|---:|---:|---:|---:|---:|---:|"]
    for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
        a=mm[(mm.split==sp)&(mm.model=="CORE")].iloc[0]; r=rr[(rr.split==sp)&(rr.model=="CORE")].iloc[0]
        lines.append(f"| {sp} | {a.auc:.4f} | {a.brier:.4f} | {int(r.n_top)} | {ppf(r.top_hit)} | {pct(r.top_mean_rev)} | [{pct(r.top_ci_lo)}, {pct(r.top_ci_hi)}] |")
    lines += ["","## Post-impulse family transfer (+30m primary)","","| Family | Bridge AUC Δ | OOS AUC Δ | Bridge return Δ | OOS return Δ | OOS Brier imp | OOS hit Δ | Transfer |","|---|---:|---:|---:|---:|---:|---:|---|"]
    for _,r in comp.iterrows(): lines.append(f"| {r.family} | {r.auc_delta_BRIDGE_2025:+.4f} | {r.auc_delta_OOS_2026:+.4f} | {pct(r.return_delta_BRIDGE_2025)} | {pct(r.return_delta_OOS_2026)} | {r.brier_imp_OOS_2026:+.5f} | {r.hit_delta_OOS_2026*100:+.1f} pp | {'ROBUST' if r.robust_transfer else 'NO'} |")
    lines += ["","## Secondary clock audit (CORE only)","","| Clock | Split | AUC | N top | Tail hit | Mean reversal |","|---|---|---:|---:|---:|---:|"]
    for clock in ["D15","D30","D60"]:
        for sp in ["BRIDGE_2025","OOS_2026"]:
            a=allmm[(allmm.clock==clock)&(allmm.split==sp)&(allmm.model=="CORE")].iloc[0]; r=allrr[(allrr.clock==clock)&(allrr.split==sp)&(allrr.model=="CORE")].iloc[0]
            lines.append(f"| {clock} | {sp} | {a.auc:.4f} | {int(r.n_top)} | {ppf(r.top_hit)} | {pct(r.top_mean_rev)} |")
    lines += ["","## Gates",""]
    for k,val in v["gates"].items(): lines.append(f"- {'PASS' if val else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} -> {v['verdict']}**","",f"Transferable named families: **{', '.join(v['robust_families']) if v['robust_families'] else 'none'}**.","","## Interpretation","","A family is promoted only when its incremental contribution over the frozen event-time CORE has the same positive sign in bridge 2025 and OOS 2026 and improves OOS Brier. +15m/+60m are audit clocks only and cannot rescue a failed +30m primary result. No 2026 threshold or family tuning is authorized after this run."]
    (OUT/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")
def main():
    b=load(downloads()); x=make_panel(b); allmm=[]; allrr=[]; thresholds={}; events={}
    for clock,d in CLOCKS.items():
        e=event_table(x,d); mm,rr,thr=score_clock(e,clock); allmm.append(mm); allrr.append(rr); thresholds[clock]=float(thr); events[clock]=e
    allmm=pd.concat(allmm,ignore_index=True); allrr=pd.concat(allrr,ignore_index=True)
    pmm=allmm[allmm.clock==PRIMARY].copy(); prr=allrr[allrr.clock==PRIMARY].copy(); comp=summarize_components(pmm,prr); v=verdict(pmm,prr,comp)
    allmm.to_csv(OUT/"model_metrics.csv",index=False); allrr.to_csv(OUT/"router_summary.csv",index=False); comp.to_csv(OUT/"family_transfer.csv",index=False)
    events[PRIMARY].to_csv(OUT/"primary_events.csv",index=False)
    (OUT/"thresholds.json").write_text(json.dumps({k:float(vv) for k,vv in thresholds.items()},indent=2))
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2))
    audit={"lab":LAB,"seed":SEED,"coverage_start":str(x.index.min()),"coverage_end":str(x.index.max()),"bars":int(len(x)),"primary_clock":PRIMARY,"clock_bars":CLOCKS,"impulse_q":IMPULSE_Q,"cooldown_bars":COOLDOWN,"oos_tuned":False,"entry":"next M15 open after observation clock","feature_cutoff":"decision bar close"}
    (OUT/"audit.json").write_text(json.dumps(audit,indent=2)); report(allmm,allrr,comp,v,thresholds,events)
    print(json.dumps(v,indent=2)); print((OUT/"REPORT.md").read_text())
if __name__=="__main__": main()
