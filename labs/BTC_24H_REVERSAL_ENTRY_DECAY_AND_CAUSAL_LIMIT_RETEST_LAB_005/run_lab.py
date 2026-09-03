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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LAB="BTC_24H_REVERSAL_ENTRY_DECAY_AND_CAUSAL_LIMIT_RETEST_LAB_005"
SEED=20260903
OUT=Path(__file__).resolve().parent/"output"; CACHE=Path(__file__).resolve().parent/"cache"
OUT.mkdir(parents=True,exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)
START_MONTH="2021-01"; END_MONTH="2026-08"; INTERVAL="15m"
BASE="https://data.binance.vision/data/spot/monthly/klines"
COLS=["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_base","taker_quote","ignore"]
ROLL=30*24*4; IMPULSE_Q=.975; COOLDOWN=16; H24=96
CORE=["impulse_dir","btc_z15","btc_z60","btc_z4h","btc_z24h","btc_vol_z","btc_range_z","btc_corr7d_lag","hour_sin","hour_cos"]
MARKET_DELAYS={"MKT_0":0,"MKT_15":1,"MKT_30":2,"MKT_60":4}
LIMITS={"LIMIT_R0.50_T60":(0.50,4),"LIMIT_R0.25_T60_AUDIT":(0.25,4),"LIMIT_R1.00_T60_AUDIT":(1.00,4)}
PRIMARY_LIMIT="LIMIT_R0.50_T60"

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
    x["impulse_dir"]=np.sign(x.btc_lr60).astype(float)
    return x
def parent_indices(x):
    cand=np.flatnonzero(x.impulse_raw.fillna(False).to_numpy()); chosen=[]; last=-10**9
    for i in cand:
        if i-last>=COOLDOWN: chosen.append(i); last=i
    return chosen
def split_year(ts):
    y=ts.year
    return "DEV_2021_2024" if y<=2024 else ("BRIDGE_2025" if y==2025 else "OOS_2026")
def make_events(x):
    rows=[]; n=len(x)
    for i in parent_indices(x):
        if i<10 or i+H24>=n or i+6>=n: continue
        d=float(x.impulse_dir.iloc[i]);
        if not np.isfinite(d) or d==0: continue
        entry=float(x.btc_open.iloc[i+1]); exitp=float(x.btc_close.iloc[i+H24])
        if not np.isfinite(entry) or entry<=0 or not np.isfinite(exitp): continue
        r={k:(d if k=="impulse_dir" else float(x[k].iloc[i])) for k in CORE}
        r.update(event_i=i,event_time=x.index[i],split=split_year(x.index[i]),event_open=float(x.btc_open.iloc[i]),event_high=float(x.btc_high.iloc[i]),event_low=float(x.btc_low.iloc[i]),event_close=float(x.btc_close.iloc[i]),common_exit=float(exitp))
        r["raw_24h"]=exitp/entry-1.0; r["cont_24h"]=d*r["raw_24h"]; r["rev_24h"]=-d*r["raw_24h"]
        rows.append(r)
    return pd.DataFrame(rows).replace([np.inf,-np.inf],np.nan)
def fit_pipe(d,features,target):
    m=Pipeline([("imp",SimpleImputer(strategy="median")),("sc",StandardScaler()),("lr",LogisticRegression(C=.5,max_iter=4000,random_state=SEED))])
    m.fit(d[features],d[target].astype(int)); return m
def freeze_selector(e):
    e=e.copy(); dev=e[e.split=="DEV_2021_2024"].copy()
    cont_thr=float(dev.cont_24h.quantile(.75)); rev_thr=float(dev.rev_24h.quantile(.75))
    e["tail_cont"]=(e.cont_24h>=cont_thr).astype(int); e["tail_rev"]=(e.rev_24h>=rev_thr).astype(int)
    dev=e[e.split=="DEV_2021_2024"].copy()
    mc=fit_pipe(dev,CORE,"tail_cont"); mr=fit_pipe(dev,CORE,"tail_rev")
    pc_dev=mc.predict_proba(dev[CORE])[:,1]; pr_dev=mr.predict_proba(dev[CORE])[:,1]
    q80=float(np.quantile(np.maximum(pc_dev,pr_dev),.80))
    pc=mc.predict_proba(e[CORE])[:,1]; pr=mr.predict_proba(e[CORE])[:,1]
    e["p_cont"]=pc; e["p_rev"]=pr; e["router_conf"]=np.maximum(pc,pr); e["router_side"]=np.where(pc>=pr,"CONT","REV")
    e["selected_top20"]=(e.router_conf>=q80); e["selected_rev"]=(e.selected_top20 & (e.router_side=="REV"))
    return e,{"cont_thr":cont_thr,"rev_thr":rev_thr,"router_q80":q80}
def rev_return(d,entry,exitp): return float(-d*(exitp/entry-1.0))
def path_stats(x,d,start_i,end_i,entry):
    if end_i<start_i: return np.nan,np.nan
    hi=float(x.btc_high.iloc[start_i:end_i+1].max()); lo=float(x.btc_low.iloc[start_i:end_i+1].min())
    if d>0:
        mfe=(entry-lo)/entry; mae=(hi-entry)/entry
    else:
        mfe=(hi-entry)/entry; mae=(entry-lo)/entry
    return float(mfe),float(mae)
def execute_event(x,row):
    i=int(row.event_i); d=float(row.impulse_dir); exitp=float(row.common_exit); out=[]
    for name,delay in MARKET_DELAYS.items():
        k=i+1+delay
        if k>=i+H24: continue
        entry=float(x.btc_open.iloc[k]); mfe,mae=path_stats(x,d,k,i+H24,entry)
        out.append(dict(method=name,filled=True,fill_bar=k,entry=entry,price_improvement_vs_mkt0=np.nan,rev_return=rev_return(d,entry,exitp),mfe=mfe,mae=mae))
    m0=float(x.btc_open.iloc[i+1])
    event_range=float(row.event_high-row.event_low)
    for name,(mult,ttl) in LIMITS.items():
        limit=float(row.event_close + d*mult*event_range)
        fill=None
        for k in range(i+1,min(i+1+ttl,i+H24)):
            if (d>0 and float(x.btc_high.iloc[k])>=limit) or (d<0 and float(x.btc_low.iloc[k])<=limit):
                fill=k; break
        if fill is None:
            out.append(dict(method=name,filled=False,fill_bar=np.nan,entry=np.nan,price_improvement_vs_mkt0=np.nan,rev_return=np.nan,mfe=np.nan,mae=np.nan))
        else:
            mfe,mae=path_stats(x,d,fill,i+H24,limit)
            improvement=(limit-m0)*d/m0
            out.append(dict(method=name,filled=True,fill_bar=fill,entry=limit,price_improvement_vs_mkt0=float(improvement),rev_return=rev_return(d,limit,exitp),mfe=mfe,mae=mae))
    return out
def bootstrap_mean(a,n=2000):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if len(a)<2: return np.nan,np.nan,np.nan
    rng=np.random.default_rng(SEED+len(a)*23); means=a[rng.integers(0,len(a),size=(n,len(a)))].mean(1); lo,hi=np.quantile(means,[.025,.975]); return float(a.mean()),float(lo),float(hi)
def run_exec(x,e):
    rows=[]
    for idx,r in e[e.selected_rev].iterrows():
        for z in execute_event(x,r):
            z.update(event_row=int(idx),event_time=r.event_time,split=r.split,impulse_dir=r.impulse_dir)
            rows.append(z)
    return pd.DataFrame(rows)
def summarize(exec_df):
    rows=[]
    for (sp,method),d in exec_df.groupby(["split","method"]):
        filled=d[d.filled].copy(); m,lo,hi=bootstrap_mean(filled.rev_return)
        rows.append(dict(split=sp,method=method,signal_n=len(d),filled_n=len(filled),fill_rate=len(filled)/len(d) if len(d) else np.nan,mean_rev=m,ci_lo=lo,ci_hi=hi,positive_rate=float((filled.rev_return>0).mean()) if len(filled) else np.nan,mean_mfe=float(filled.mfe.mean()) if len(filled) else np.nan,mean_mae=float(filled.mae.mean()) if len(filled) else np.nan,mean_price_improvement=float(filled.price_improvement_vs_mkt0.mean()) if len(filled) and filled.price_improvement_vs_mkt0.notna().any() else np.nan))
    return pd.DataFrame(rows)
def matched_limit(exec_df,limit_name):
    lim=exec_df[(exec_df.method==limit_name)&(exec_df.filled)][["event_row","split","rev_return"]].rename(columns={"rev_return":"limit_rev"})
    m0=exec_df[exec_df.method=="MKT_0"][["event_row","split","rev_return"]].rename(columns={"rev_return":"mkt0_rev"})
    q=lim.merge(m0,on=["event_row","split"],how="inner"); q["delta"]=q.limit_rev-q.mkt0_rev
    rows=[]
    for sp,d in q.groupby("split"):
        m,lo,hi=bootstrap_mean(d.delta)
        rows.append(dict(split=sp,limit=limit_name,n=len(d),mean_delta=m,ci_lo=lo,ci_hi=hi,limit_mean=float(d.limit_rev.mean()),mkt0_matched_mean=float(d.mkt0_rev.mean())))
    return pd.DataFrame(rows)
def verdict(summary,matched,e):
    def s(sp,method,col):
        q=summary[(summary.split==sp)&(summary.method==method)]
        return float(q.iloc[0][col]) if len(q) else np.nan
    def m(sp,col):
        q=matched[matched.split==sp]
        return float(q.iloc[0][col]) if len(q) else np.nan
    oos_sel=int(e[(e.split=="OOS_2026")&e.selected_rev].shape[0]); bridge_sel=int(e[(e.split=="BRIDGE_2025")&e.selected_rev].shape[0])
    decay_bridge=s("BRIDGE_2025","MKT_0","mean_rev")>s("BRIDGE_2025","MKT_30","mean_rev") and s("BRIDGE_2025","MKT_30","mean_rev")>=s("BRIDGE_2025","MKT_60","mean_rev")
    decay_oos=s("OOS_2026","MKT_0","mean_rev")>s("OOS_2026","MKT_30","mean_rev") and s("OOS_2026","MKT_30","mean_rev")>=s("OOS_2026","MKT_60","mean_rev")
    gates={
      "oos_selected_rev_ge_15":oos_sel>=15,
      "bridge_selected_rev_ge_15":bridge_sel>=15,
      "entry_decay_bridge":bool(decay_bridge),
      "entry_decay_oos":bool(decay_oos),
      "primary_limit_fill_bridge_ge_0.30":s("BRIDGE_2025",PRIMARY_LIMIT,"fill_rate")>=.30,
      "primary_limit_fill_oos_ge_0.30":s("OOS_2026",PRIMARY_LIMIT,"fill_rate")>=.30,
      "primary_limit_matched_delta_bridge_positive":m("BRIDGE_2025","mean_delta")>0,
      "primary_limit_matched_delta_oos_positive":m("OOS_2026","mean_delta")>0,
    }
    n=sum(gates.values())
    if all(gates.values()): v="PASS_CAUSAL_LIMIT_RETEST_EXECUTION"
    elif n>=6 and gates["primary_limit_matched_delta_oos_positive"]: v="WATCH_LIMIT_RETEST_EXECUTION"
    else: v="FAIL_NO_ROBUST_LIMIT_RETEST_ADVANTAGE"
    return dict(verdict=v,gates_passed=int(n),gates_total=len(gates),gates=gates,oos_selected_rev=oos_sel,bridge_selected_rev=bridge_sel)
def pct(x): return "—" if not np.isfinite(x) else f"{100*x:+.3f}%"
def pp(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
def write_report(x,e,thr,summary,matched,v):
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","","Role: frozen-selector execution decay / causal limit-retest study; not a production strategy.","","## Frozen selector","","- Parent impulse: completed BTC 60m |return| >= prior 30d 97.5th percentile; 4h cooldown.","- Selector: exact LAB003 BTC-only CORE, DEV-trained logistic CONT/REV router, DEV q80 top bucket.","- This LAB executes only events frozen as top-20% and routed REV.",f"- DEV CONT tail threshold: **{pct(thr['cont_thr'])}**; REV tail threshold: **{pct(thr['rev_thr'])}**.",f"- Frozen router q80: **{thr['router_q80']:.6f}**.","","## Execution definitions","","- MKT_0 = next M15 open after impulse.","- MKT_15 / MKT_30 / MKT_60 = delayed market entries; all use the same common LAB003 exit at parent +24h, isolating entry decay.","- Primary limit = opposite-direction reversal order at event close + impulse_dir × 0.50 × event M15 range; TTL 60m; no market fallback.","- Limit fill uses only subsequent M15 high/low touch; filled price is the preset limit. Secondary 0.25×/1.00× levels are audit only.","","## Frozen reversal signal census",""]
    for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
        n=int(e[(e.split==sp)&e.selected_rev].shape[0]); lines.append(f"- {sp}: **{n}** selected REV events")
    lines += ["","## Entry decay / fill results","","| Split | Method | Signals | Filled | Fill | Mean REV | 95% CI | Positive | MFE | MAE | Price improvement |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    order=["MKT_0","MKT_15","MKT_30","MKT_60","LIMIT_R0.50_T60","LIMIT_R0.25_T60_AUDIT","LIMIT_R1.00_T60_AUDIT"]
    for sp in ["DEV_2021_2024","BRIDGE_2025","OOS_2026"]:
        for method in order:
            q=summary[(summary.split==sp)&(summary.method==method)]
            if not len(q): continue
            r=q.iloc[0]; lines.append(f"| {sp} | {method} | {int(r.signal_n)} | {int(r.filled_n)} | {pp(r.fill_rate)} | {pct(r.mean_rev)} | [{pct(r.ci_lo)}, {pct(r.ci_hi)}] | {pp(r.positive_rate)} | {pct(r.mean_mfe)} | {pct(r.mean_mae)} | {pct(r.mean_price_improvement)} |")
    lines += ["","## Primary limit matched comparison","","Matched comparison uses only events where the primary limit actually filled, versus MKT_0 on those same events.","","| Split | N | Limit mean | MKT_0 matched | Delta | 95% CI |","|---|---:|---:|---:|---:|---:|"]
    for _,r in matched.iterrows(): lines.append(f"| {r.split} | {int(r.n)} | {pct(r.limit_mean)} | {pct(r.mkt0_matched_mean)} | {pct(r.mean_delta)} | [{pct(r.ci_lo)}, {pct(r.ci_hi)}] |")
    lines += ["","## Gates",""]
    for k,val in v["gates"].items(): lines.append(f"- {'PASS' if val else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} -> {v['verdict']}**","","## Interpretation","","A positive result means execution timing/price placement improves the already-frozen LAB003 reversal selector. It does not authorize live trading or optimize SL/TP. R:R mapping is a later LAB and must remain >=1:1.5.","","No 2026 tuning of selector, limit distance, TTL, delay clocks, or fallback behavior is authorized after this run."]
    (OUT/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")
def main():
    b=load(downloads()); x=make_panel(b); e=make_events(x); e,thr=freeze_selector(e); ex=run_exec(x,e); sm=summarize(ex); matched=matched_limit(ex,PRIMARY_LIMIT); v=verdict(sm,matched,e)
    e.to_csv(OUT/"events_with_frozen_selector.csv",index=False); ex.to_csv(OUT/"execution_events.csv",index=False); sm.to_csv(OUT/"execution_summary.csv",index=False); matched.to_csv(OUT/"primary_limit_matched.csv",index=False)
    (OUT/"thresholds.json").write_text(json.dumps({k:float(vv) for k,vv in thr.items()},indent=2)); (OUT/"verdict.json").write_text(json.dumps(v,indent=2))
    audit={"lab":LAB,"seed":SEED,"coverage_start":str(x.index.min()),"coverage_end":str(x.index.max()),"bars":int(len(x)),"selector":"LAB003 exact BTC-only CORE top20 router, REV only","primary_limit":PRIMARY_LIMIT,"limit_definition":{"distance_event_range":0.50,"ttl_m15_bars":4,"market_fallback":False},"common_exit":"parent impulse bar + 96 M15 closes","oos_tuned":False}
    (OUT/"audit.json").write_text(json.dumps(audit,indent=2)); write_report(x,e,thr,sm,matched,v); print(json.dumps(v,indent=2)); print((OUT/"REPORT.md").read_text())
if __name__=="__main__": main()
