#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

LAB="BTC_REVERSAL_H4_BUY_EDGE_REGIME_ONSET_AND_2025H2_STRUCTURAL_TRANSITION_LAB_020"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
ROOT=HERE.parent
STREAM=ROOT/"BTC_REVERSAL_H4_PIVOT_M15_TWO_BAR_CONFIRM_FORMAL_REPLICATION_AND_CANONICAL_UNION_LAB_018"/"output"/"two_bar_confirm_vf1_stream.csv"
PARENTS=ROOT/"BTC_REVERSAL_ORTHOGONAL_H4_PARENT_AND_NONOVERLAP_FAMILY_LAB_016"/"output"/"H4_7D_PIVOT_SWEEP_RECLAIM_nonoverlap_selected.csv"
SRC17=ROOT/"BTC_REVERSAL_H4_PIVOT_PARENT_TO_M15_CHILD_VIRTUAL_FILL_AND_EXECUTION_BRIDGE_LAB_017"/"run_lab_v3.py"
spec=importlib.util.spec_from_file_location("lab017v3",SRC17)
V3=importlib.util.module_from_spec(spec); spec.loader.exec_module(V3)
L17=V3.L17

UTC="UTC"; SEED=20260906; BOOT=5000
T_H1_A=pd.Timestamp("2025-01-01",tz=UTC); T_H2_A=pd.Timestamp("2025-07-01",tz=UTC); T_2026=pd.Timestamp("2026-01-01",tz=UTC); T_AUG=pd.Timestamp("2026-08-01",tz=UTC); T_SEP=pd.Timestamp("2026-09-01",tz=UTC)
HIST_A=pd.Timestamp("2021-01-01",tz=UTC)
FEATURES=["ret_24h","ret_72h","ret_7d","range_pos_7d","range_pos_30d","rv_ratio_24h_7d","range_ratio_24h_7d","parent_range_pct","parent_body_frac","parent_reclaim_frac","router_conf","child_latency_h","child_parent_range_ratio","prior_virtual_fills","episode_age_h"]
STRUCTURAL=set(["ret_24h","ret_72h","ret_7d","range_pos_7d","range_pos_30d","rv_ratio_24h_7d","range_ratio_24h_7d","parent_range_pct","parent_body_frac","parent_reclaim_frac"])


def boolify(v):
    if isinstance(v,(bool,np.bool_)): return bool(v)
    return str(v).strip().lower() in {"true","1","yes"}

def prep(d):
    for c in ["parent_time","signal_time","event_time","fill_time","exit_time"]:
        if c in d.columns: d[c]=pd.to_datetime(d[c],utc=True,errors="coerce")
    for c in ["filled","vf1_mature","real_fill"]:
        if c in d.columns: d[c]=d[c].map(boolify)
    for c in ["real_R","signal_net_R","impulse_dir","router_conf","child_range","prior_virtual_fills"]:
        if c in d.columns: d[c]=pd.to_numeric(d[c],errors="coerce")
    return d

def pf(a):
    a=np.asarray(a,float); p=float(a[a>0].sum()); n=float(-a[a<0].sum())
    if n==0:return np.inf if p>0 else np.nan
    return p/n

def dd(a):
    a=np.asarray(a,float)
    if not len(a):return 0.0
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq]); return float((peak[1:]-eq).max())

def trade_metrics(d):
    r=d.real_R.to_numpy(float) if len(d) else np.array([])
    return dict(n=int(len(d)),cum_R=float(r.sum()) if len(r) else 0.0,mean_R=float(r.mean()) if len(r) else np.nan,profit_factor=pf(r),max_dd_R=dd(r))

def scan_cp(d):
    q=d.sort_values("fill_time").reset_index(drop=True)
    best=None
    for k in range(6,len(q)-5):
        a=q.iloc[:k].real_R.to_numpy(float); b=q.iloc[k:].real_R.to_numpy(float)
        delta=float(np.mean(b)-np.mean(a)); obj=abs(delta)
        row=dict(k=k,split_time=str(q.fill_time.iloc[k]),pre_n=len(a),post_n=len(b),pre_mean=float(np.mean(a)),post_mean=float(np.mean(b)),delta_mean=delta,abs_delta=obj,pre_cum=float(a.sum()),post_cum=float(b.sum()),pre_pf=pf(a),post_pf=pf(b),pre_dd=dd(a),post_dd=dd(b))
        if best is None or obj>best["abs_delta"]: best=row
    return best

def bootstrap_cp(d):
    groups=[q.copy() for _,q in d.groupby("episode_7d",sort=True) if q.real_fill.any()]
    if len(groups)<2:return dict(valid=0,in_band_fraction=np.nan,median_split=None,q25_split=None,q75_split=None)
    rng=np.random.default_rng(SEED); dates=[]
    for _ in range(BOOT):
        picks=rng.integers(0,len(groups),size=len(groups))
        z=pd.concat([groups[i] for i in picks],ignore_index=True).sort_values("fill_time")
        z=z[z.real_fill].copy()
        if len(z)<12: continue
        cp=scan_cp(z)
        if cp: dates.append(pd.Timestamp(cp["split_time"]))
    if not dates:return dict(valid=0,in_band_fraction=np.nan,median_split=None,q25_split=None,q75_split=None)
    ns=np.array([x.value for x in dates],dtype=np.int64)
    q=np.percentile(ns,[25,50,75]).astype(np.int64)
    band=[pd.Timestamp("2025-04-01",tz=UTC),pd.Timestamp("2025-10-01",tz=UTC)]
    frac=float(np.mean([(x>=band[0] and x<=band[1]) for x in dates]))
    return dict(valid=len(dates),in_band_fraction=frac,q25_split=str(pd.Timestamp(q[0],tz=UTC)),median_split=str(pd.Timestamp(q[1],tz=UTC)),q75_split=str(pd.Timestamp(q[2],tz=UTC)))

def safe_ret(close,i,n):
    if i-n<0:return np.nan
    a=float(close[i-n]); b=float(close[i]); return b/a-1.0 if np.isfinite(a) and a!=0 and np.isfinite(b) else np.nan

def trailing_range(high,low,close,i,n):
    j=max(0,i-n+1); h=np.asarray(high[j:i+1],float); l=np.asarray(low[j:i+1],float); c=float(close[i])
    if len(h)<max(10,n//4):return (np.nan,np.nan)
    hi=float(np.nanmax(h)); lo=float(np.nanmin(l)); rng=hi-lo
    pos=(c-lo)/rng if rng>0 else np.nan
    return rng,pos

def rv(close,i,n):
    j=max(1,i-n+1); x=np.asarray(close[j-1:i+1],float)
    if len(x)<max(10,n//4):return np.nan
    lr=np.diff(np.log(x)); return float(np.nanstd(lr,ddof=1)) if len(lr)>1 else np.nan

def build_features(stream,parents,x):
    p=parents.copy(); p["event_time"]=pd.to_datetime(p.event_time,utc=True)
    pidx=p.set_index("event_time")
    close=x.btc_close.to_numpy(float); high=x.btc_high.to_numpy(float); low=x.btc_low.to_numpy(float)
    # frozen episode first signal from all-direction stream
    first_sig=stream.groupby("episode_7d").signal_time.min().to_dict()
    rows=[]
    for idx,r in stream.iterrows():
        if float(r.impulse_dir)>=0: continue
        i=int(r.signal_i); pt=pd.Timestamp(r.parent_time)
        if pt not in pidx.index: raise RuntimeError(f"Missing parent {pt}")
        pr=pidx.loc[pt]
        if isinstance(pr,pd.DataFrame): pr=pr.iloc[0]
        r7,pos7=trailing_range(high,low,close,i,672); r30,pos30=trailing_range(high,low,close,i,2880); r24,_=trailing_range(high,low,close,i,96)
        rv24=rv(close,i,96); rv7=rv(close,i,672)
        phr=float(pr.event_high-pr.event_low); pclose=float(pr.event_close); pbody=abs(float(pr.event_close-pr.event_open))
        ep0=pd.Timestamp(first_sig[int(r.episode_7d)])
        d=dict(source_index=int(idx),parent_time=pt,signal_time=pd.Timestamp(r.signal_time),fill_time=pd.Timestamp(r.fill_time) if pd.notna(r.fill_time) else pd.NaT,real_fill=bool(r.real_fill),real_R=float(r.real_R),episode_7d=int(r.episode_7d),
               ret_24h=safe_ret(close,i,96),ret_72h=safe_ret(close,i,288),ret_7d=safe_ret(close,i,672),range_pos_7d=pos7,range_pos_30d=pos30,
               rv_ratio_24h_7d=(rv24/rv7 if np.isfinite(rv24) and np.isfinite(rv7) and rv7>0 else np.nan),range_ratio_24h_7d=(r24/r7 if np.isfinite(r24) and np.isfinite(r7) and r7>0 else np.nan),
               parent_range_pct=(phr/pclose if phr>0 and pclose!=0 else np.nan),parent_body_frac=(pbody/phr if phr>0 else np.nan),parent_reclaim_frac=((float(pr.event_close)-float(pr.event_low))/phr if phr>0 else np.nan),
               router_conf=float(r.router_conf),child_latency_h=(pd.Timestamp(r.signal_time)-pt).total_seconds()/3600.0,child_parent_range_ratio=(float(r.child_range)/phr if phr>0 else np.nan),prior_virtual_fills=float(r.prior_virtual_fills),episode_age_h=(pd.Timestamp(r.signal_time)-ep0).total_seconds()/3600.0)
        rows.append(d)
    return pd.DataFrame(rows).sort_values("signal_time").reset_index(drop=True)

def cliffs(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float); a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if not len(a) or not len(b):return np.nan
    diff=b[:,None]-a[None,:]
    return float((np.sum(diff>0)-np.sum(diff<0))/(len(a)*len(b)))

def smd(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float); a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if len(a)<2 or len(b)<2:return np.nan
    va=np.var(a,ddof=1); vb=np.var(b,ddof=1); sp=np.sqrt(((len(a)-1)*va+(len(b)-1)*vb)/(len(a)+len(b)-2))
    return float((np.mean(b)-np.mean(a))/sp) if sp>0 else np.nan

def compare(feat,a,b,label):
    rows=[]
    for f in FEATURES:
        av=a[f].to_numpy(float); bv=b[f].to_numpy(float)
        rows.append(dict(comparison=label,feature=f,n_a=int(np.isfinite(av).sum()),n_b=int(np.isfinite(bv).sum()),median_a=float(np.nanmedian(av)),median_b=float(np.nanmedian(bv)),smd=smd(av,bv),cliffs_delta=cliffs(av,bv)))
    return pd.DataFrame(rows)

def econ(q):
    q=q[q.real_fill].copy(); return trade_metrics(q)

def main():
    stream=prep(pd.read_csv(STREAM)); parents=prep(pd.read_csv(PARENTS)); x,_,_=L17.L7.load_panel()
    # lineage parity from LAB019
    buyfills=stream[(stream.impulse_dir<0)&(stream.real_fill)&(stream.parent_time<T_AUG)].copy()
    recent=buyfills[(buyfills.parent_time>=T_H2_A)&(buyfills.parent_time<T_AUG)]
    if len(recent)!=14: raise RuntimeError(f"Expected 14 recent BUY fills, got {len(recent)}")
    feat=build_features(stream,parents,x)

    cp=scan_cp(buyfills); boot=bootstrap_cp(buyfills)
    h1=feat[(feat.parent_time>=T_H1_A)&(feat.parent_time<T_H2_A)].copy(); h2=feat[(feat.parent_time>=T_H2_A)&(feat.parent_time<T_2026)].copy()
    hist=feat[(feat.parent_time>=HIST_A)&(feat.parent_time<T_H2_A)].copy(); recent_opp=feat[(feat.parent_time>=T_H2_A)&(feat.parent_time<T_AUG)].copy()
    c1=compare(feat,h1,h2,"2025_H1_vs_2025_H2"); c2=compare(feat,hist,recent_opp,"HIST_vs_POOLED_RECENT")
    comp=pd.concat([c1,c2],ignore_index=True)
    piv=comp.pivot(index="feature",columns="comparison",values="cliffs_delta")
    stable=[]
    for f in FEATURES:
        d1=float(piv.loc[f,"2025_H1_vs_2025_H2"]); d2=float(piv.loc[f,"HIST_vs_POOLED_RECENT"])
        ok=np.isfinite(d1) and np.isfinite(d2) and np.sign(d1)==np.sign(d2) and abs(d1)>=.33 and abs(d2)>=.33
        stable.append(dict(feature=f,delta_h1_h2=d1,delta_hist_recent=d2,stable_shift=bool(ok),structural=bool(f in STRUCTURAL)))
    stable=pd.DataFrame(stable)

    # Diagnostic regime-similarity model: period labels, never outcome labels.
    train=pd.concat([hist.assign(y=0),h2.assign(y=1)],ignore_index=True)
    model=Pipeline([("imp",SimpleImputer(strategy="median")),("sc",StandardScaler()),("lr",LogisticRegression(C=1.0,max_iter=2000,random_state=SEED))])
    model.fit(train[FEATURES],train.y)
    train["score"]=model.predict_proba(train[FEATURES])[:,1]
    thr=float(train.loc[train.y==1,"score"].median())
    coef=model.named_steps["lr"].coef_[0]
    coeftab=pd.DataFrame({"feature":FEATURES,"coef_standardized":coef}).sort_values("coef_standardized",key=np.abs,ascending=False)

    transfer_rows=[]; scored=[]
    for name,a,b in [("2026_JAN_JUL",T_2026,T_AUG),("AUG2026_REUSED_AUDIT",T_AUG,T_SEP)]:
        q=feat[(feat.parent_time>=a)&(feat.parent_time<b)].copy()
        q["regime_score"]=model.predict_proba(q[FEATURES])[:,1] if len(q) else np.array([])
        q["regime_like"]=q.regime_score>=thr if len(q) else False
        scored.append(q.assign(window=name))
        for flag in [True,False]:
            z=q[q.regime_like==flag] if len(q) else q
            e=econ(z)
            transfer_rows.append(dict(window=name,regime_like=flag,opportunities=len(z),real_fills=e["n"],cum_R=e["cum_R"],mean_R=e["mean_R"],profit_factor=e["profit_factor"],max_dd_R=e["max_dd_R"],median_score=float(z.regime_score.median()) if len(z) else np.nan))
    transfer=pd.DataFrame(transfer_rows)
    scored=pd.concat(scored,ignore_index=True) if scored else pd.DataFrame()
    t26=transfer[transfer.window=="2026_JAN_JUL"]
    hi=t26[t26.regime_like==True].iloc[0]; lo=t26[t26.regime_like==False].iloc[0]
    supportive=bool(int(hi.real_fills)>0 and float(hi.cum_R)>0 and float(hi.mean_R)>0 and int(lo.real_fills)>0 and float(hi.mean_R)>float(lo.mean_R))

    cp_time=pd.Timestamp(cp["split_time"]) if cp else pd.NaT
    cp_in_band=bool(pd.notna(cp_time) and cp_time>=pd.Timestamp("2025-04-01",tz=UTC) and cp_time<=pd.Timestamp("2025-10-01",tz=UTC))
    stable_n=int(stable.stable_shift.sum()); structural_n=int((stable.stable_shift & stable.structural).sum())
    gates={"best_change_point_near_2025H2":cp_in_band,"post_split_mean_gt_pre":bool(cp and cp["post_mean"]>cp["pre_mean"]),"stable_shifts_ge_3":stable_n>=3,"structural_stable_shift_ge_1":structural_n>=1,"2026_similarity_transfer_supportive":supportive}
    if all(gates.values()): verdict="PASS_CAUSAL_REGIME_ONSET_SUPPORTED"
    elif cp_in_band and stable_n>=2: verdict="WATCH_REGIME_ONSET_PARTIAL"
    else: verdict="FAIL_NO_CAUSAL_REGIME_ONSET_SUPPORT"

    feat.to_csv(OUT/"buy_child_causal_features.csv",index=False)
    comp.to_csv(OUT/"feature_shift_comparisons.csv",index=False)
    stable.to_csv(OUT/"stable_shift_features.csv",index=False)
    transfer.to_csv(OUT/"regime_similarity_transfer.csv",index=False)
    coeftab.to_csv(OUT/"regime_similarity_coefficients.csv",index=False)
    if len(scored): scored.to_csv(OUT/"transfer_scored_opportunities.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps(dict(verdict=verdict,gates=gates,stable_shift_count=stable_n,structural_stable_shift_count=structural_n,change_point=cp,change_point_bootstrap=boot,regime_threshold=thr),indent=2,allow_nan=True),encoding="utf-8")

    lines=[f"# {LAB}","",f"**Verdict: {verdict} — {sum(gates.values())}/{len(gates)}**","","## Part A — BUY outcome change point","",f"- Best split: **{cp['split_time']}**" if cp else "- No valid split",f"- Pre: N={cp['pre_n']}, mean {cp['pre_mean']:+.3f}R, PF {cp['pre_pf']:.3f}, DD {cp['pre_dd']:.2f}R" if cp else "",f"- Post: N={cp['post_n']}, mean {cp['post_mean']:+.3f}R, PF {cp['post_pf']:.3f}, DD {cp['post_dd']:.2f}R" if cp else "",f"- Mean shift: {cp['delta_mean']:+.3f}R/fill" if cp else "",f"- Episode-bootstrap best-split in Apr-Oct 2025: **{boot['in_band_fraction']:.1%}** (valid={boot['valid']}); IQR {boot['q25_split']} .. {boot['q75_split']}" if boot['valid'] else "","","## Part B — stable causal state shifts","","| Feature | Cliff H1→H2 | Cliff hist→recent | Stable | Structural |","|---|---:|---:|---|---|"]
    for _,r in stable.sort_values(["stable_shift","structural"],ascending=[False,False]).iterrows(): lines.append(f"| {r.feature} | {r.delta_h1_h2:+.3f} | {r.delta_hist_recent:+.3f} | {'YES' if r.stable_shift else 'no'} | {'yes' if r.structural else 'no'} |")
    lines += ["",f"Stable shifts: **{stable_n}**, structural: **{structural_n}**.","","## Part C — H2-regime similarity transfer",f"Frozen threshold = median H2-2025 training score = **{thr:.3f}**.","","| Window | Regime-like | Opps | Real fills | CumR | MeanR | PF | DD |","|---|---|---:|---:|---:|---:|---:|---:|"]
    for _,r in transfer.iterrows():
        pfv="—" if pd.isna(r.profit_factor) else ("inf" if np.isinf(r.profit_factor) else f"{r.profit_factor:.3f}")
        mean="—" if pd.isna(r.mean_R) else f"{r.mean_R:+.3f}"
        lines.append(f"| {r.window} | {'YES' if r.regime_like else 'no'} | {int(r.opportunities)} | {int(r.real_fills)} | {r.cum_R:+.2f} | {mean} | {pfv} | {r.max_dd_R:.2f} |")
    lines += ["","### Strongest period-fingerprint coefficients","","| Feature | Standardized coefficient |","|---|---:|"]
    for _,r in coeftab.head(8).iterrows(): lines.append(f"| {r.feature} | {r.coef_standardized:+.3f} |")
    lines += ["","## Gates"]+[f"- {'PASS' if v else 'FAIL'} — `{k}`" for k,v in gates.items()]+["","## Guardrail","This LAB is diagnostic. No calendar date, classifier threshold or feature cutoff is promoted to live trading. Any regime router must be separately preregistered and replicated. Live allocation remains **0**."]
    (OUT/"REPORT.md").write_text("\n".join([x for x in lines if x is not None])+"\n",encoding="utf-8")
    print((OUT/"REPORT.md").read_text())

if __name__=="__main__": main()
