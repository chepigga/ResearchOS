#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LAB="BTC_REVERSAL_SLOW_REGIME_AND_IMPULSE_ACCEPTANCE_PERSISTENCE_LAB_009"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SRC7=HERE.parent/"BTC_REVERSAL_LIMIT_RETEST_YEARLY_STABILITY_AND_FRESH_AUG2026_REPLICATION_LAB_007"/"run_lab.py"
spec7=importlib.util.spec_from_file_location("lab007",SRC7); L7=importlib.util.module_from_spec(spec7); spec7.loader.exec_module(L7)
L6=L7.L6; L5=L7.L5
PRIMARY_RR=1.5; COST_BPS=5.0; RIDGE_ALPHA=10.0

SLOW_FEATURES=[
    "aligned_ret30d","aligned_ret60d","aligned_ret90d",
    "eff30d","eff60d","eff90d",
    "rv30d","rv60d","rv90d","rv30_90_ratio",
    "oriented_pos30d","oriented_pos90d",
]
ACCEPT_FEATURES=[
    "accept_rate_10","accept_rate_20","mean_cont_10","mean_cont_20",
    "same_dir_accept_rate_10","same_dir_mean_cont_10",
    "accept_ewm20","accept_streak_signed","known_impulses_30d",
]
FAMILIES={
    "SLOW_ONLY":SLOW_FEATURES,
    "ACCEPTANCE_ONLY":ACCEPT_FEATURES,
    "SLOW_PLUS_ACCEPTANCE":SLOW_FEATURES+ACCEPT_FEATURES,
}
PRIMARY="SLOW_PLUS_ACCEPTANCE"
TEST_BUCKETS=["2022","2023","2024","2025","2026_JAN_JUL","FRESH_AUG2026"]
PRIMARY_YEARS=["2022","2023","2024","2025","2026_JAN_JUL"]
RECENT_YEARS=["2025","2026_JAN_JUL"]
TEST_START={
    "2022":pd.Timestamp("2022-01-01",tz="UTC"),
    "2023":pd.Timestamp("2023-01-01",tz="UTC"),
    "2024":pd.Timestamp("2024-01-01",tz="UTC"),
    "2025":pd.Timestamp("2025-01-01",tz="UTC"),
    "2026_JAN_JUL":pd.Timestamp("2026-01-01",tz="UTC"),
    "FRESH_AUG2026":pd.Timestamp("2026-08-01",tz="UTC"),
}


def enrich_slow_panel(x):
    x=x.copy(); c=x.btc_close; h=x.btc_high; l=x.btc_low; lr=x.btc_lr15.abs()
    for days in [30,60,90]:
        n=days*96
        pre=c.shift(4)
        ret=np.log(pre/c.shift(4+n))
        den=x.btc_lr15.abs().rolling(n,min_periods=n//2).sum().shift(4)
        rv=x.btc_lr15.rolling(n,min_periods=n//2).std(ddof=0).shift(4)
        hi=h.rolling(n,min_periods=n//2).max().shift(4)
        lo=l.rolling(n,min_periods=n//2).min().shift(4)
        pos=(pre-lo)/(hi-lo).replace(0,np.nan)
        x[f"slow_ret{days}d"]=ret
        x[f"slow_eff{days}d"]=ret.abs()/den.replace(0,np.nan)
        x[f"slow_rv{days}d"]=rv
        x[f"slow_pos{days}d"]=pos
    x["slow_rv30_90_ratio"]=x.slow_rv30d/x.slow_rv90d.replace(0,np.nan)
    return x


def first_hit_signal_net_r(x,row):
    rr=row.copy(); rr.name=row.name; rr["split"]=row.bucket
    z=L6.first_hit(x,rr,PRIMARY_RR)
    if z is None:
        return dict(filled=False,signal_net_R=0.0,gross_R=0.0,cost_R=0.0,outcome="NO_FILL",fill_time=pd.NaT,stop_frac=np.nan)
    cost=(COST_BPS/10000.0)/float(z["stop_frac"])
    return dict(filled=True,signal_net_R=float(z["gross_R"]-cost),gross_R=float(z["gross_R"]),cost_R=float(cost),outcome=z["outcome"],fill_time=z["fill_time"],stop_frac=float(z["stop_frac"]))


def acceptance_features(parents,t,current_dir):
    known=parents[parents.known_time<t].sort_values("event_time")
    if len(known)==0:
        return {k:np.nan for k in ACCEPT_FEATURES}
    def lastn(n): return known.tail(n)
    def arate(d): return float((d.cont_24h>0).mean()) if len(d) else np.nan
    def mcont(d): return float(d.cont_24h.mean()) if len(d) else np.nan
    a10=lastn(10); a20=lastn(20)
    same=known[known.impulse_dir==current_dir].tail(10)
    signs=np.where(a20.cont_24h.to_numpy(float)>0,1.0,-1.0)
    if len(signs):
        age=np.arange(len(signs)-1,-1,-1,dtype=float)
        w=np.power(.8,age)
        ewm=float(np.sum(w*signs)/np.sum(w))
        last=signs[-1]; streak=0
        for s in signs[::-1]:
            if s==last: streak+=1
            else: break
        streak=float(np.sign(last)*min(streak,5))
    else:
        ewm=np.nan; streak=np.nan
    cutoff=t-pd.Timedelta(days=30)
    n30=int(((known.event_time>=cutoff)&(known.event_time<t)).sum())
    return {
        "accept_rate_10":arate(a10),"accept_rate_20":arate(a20),
        "mean_cont_10":mcont(a10),"mean_cont_20":mcont(a20),
        "same_dir_accept_rate_10":arate(same),"same_dir_mean_cont_10":mcont(same),
        "accept_ewm20":ewm,"accept_streak_signed":streak,"known_impulses_30d":float(n30),
    }


def build_signals(x):
    e,meta=L7.selected_table(x)
    sel=e[e.selected_rev].copy()
    parents=L5.make_events(x).copy().sort_values("event_time")
    parents["known_time"]=parents.event_time+pd.Timedelta(hours=24,minutes=15)
    rows=[]
    for idx,row in sel.iterrows():
        i=int(row.event_i); d=float(row.impulse_dir); r=row.to_dict(); r["signal_id"]=int(idx)
        for days in [30,60,90]:
            ret=x[f"slow_ret{days}d"].iloc[i]; eff=x[f"slow_eff{days}d"].iloc[i]; rv=x[f"slow_rv{days}d"].iloc[i]; pos=x[f"slow_pos{days}d"].iloc[i]
            r[f"aligned_ret{days}d"]=float(d*ret) if np.isfinite(ret) else np.nan
            r[f"eff{days}d"]=float(eff) if np.isfinite(eff) else np.nan
            r[f"rv{days}d"]=float(rv) if np.isfinite(rv) else np.nan
            r[f"oriented_pos{days}d"]=float(pos if d>0 else 1.0-pos) if np.isfinite(pos) else np.nan
        ratio=x.slow_rv30_90_ratio.iloc[i]
        r["rv30_90_ratio"]=float(ratio) if np.isfinite(ratio) else np.nan
        r.update(acceptance_features(parents,pd.Timestamp(row.event_time),d))
        rr=row.copy(); rr.name=idx
        r.update(first_hit_signal_net_r(x,rr)); rows.append(r)
    s=pd.DataFrame(rows).replace([np.inf,-np.inf],np.nan)
    if len(s): s=s.sort_values("event_time").reset_index(drop=True)
    return s,meta,parents


def model_pipe():
    return Pipeline([
        ("imp",SimpleImputer(strategy="median",keep_empty_features=True)),
        ("sc",StandardScaler()),
        ("ridge",Ridge(alpha=RIDGE_ALPHA)),
    ])


def pf(a): return L6.pf(np.asarray(a,float))
def maxdd(a): return L6.max_dd_r(np.asarray(a,float))
def maxloss(a): return L6.max_consecutive_loss(np.asarray(a,float))


def eval_bucket(test,on,family,bucket,train_n,threshold):
    base=test.signal_net_R.to_numpy(float); gated=np.where(on,base,0.0); traded=base[on]
    return dict(
        family=family,bucket=bucket,train_n=int(train_n),signals=int(len(test)),on_n=int(on.sum()),coverage=float(on.mean()) if len(on) else np.nan,
        base_filled=int(test.filled.sum()),gated_filled=int((test.filled.to_numpy(bool)&on).sum()),
        base_cum_R=float(base.sum()),gated_cum_R=float(gated.sum()),delta_cum_R=float(gated.sum()-base.sum()),
        base_ev_per_opportunity=float(base.mean()) if len(base) else np.nan,gated_ev_per_opportunity=float(gated.mean()) if len(gated) else np.nan,
        gated_ev_per_traded_signal=float(traded.mean()) if len(traded) else np.nan,
        base_pf=pf(base),gated_pf=pf(gated),base_maxdd_R=maxdd(base),gated_maxdd_R=maxdd(gated),
        base_max_consecutive_losses=maxloss(base),gated_max_consecutive_losses=maxloss(gated),threshold=float(threshold)
    )


def walk_forward(signals,features,family):
    metrics=[]; preds=[]
    for b in TEST_BUCKETS:
        test=signals[signals.bucket==b].copy(); train=signals[signals.event_time<TEST_START[b]].copy()
        if len(test)==0 or len(train)<20:
            metrics.append(dict(family=family,bucket=b,train_n=len(train),signals=len(test),on_n=0,coverage=np.nan,base_filled=int(test.filled.sum()) if len(test) else 0,gated_filled=0,base_cum_R=float(test.signal_net_R.sum()) if len(test) else 0.0,gated_cum_R=0.0,delta_cum_R=float(-test.signal_net_R.sum()) if len(test) else 0.0,base_ev_per_opportunity=float(test.signal_net_R.mean()) if len(test) else np.nan,gated_ev_per_opportunity=np.nan,gated_ev_per_traded_signal=np.nan,base_pf=pf(test.signal_net_R) if len(test) else np.nan,gated_pf=np.nan,base_maxdd_R=maxdd(test.signal_net_R) if len(test) else np.nan,gated_maxdd_R=np.nan,base_max_consecutive_losses=maxloss(test.signal_net_R) if len(test) else 0,gated_max_consecutive_losses=0,threshold=np.nan))
            continue
        m=model_pipe(); m.fit(train[features],train.signal_net_R.to_numpy(float))
        train_score=m.predict(train[features]); threshold=float(np.median(train_score)); score=m.predict(test[features]); on=score>=threshold
        metrics.append(eval_bucket(test,on,family,b,len(train),threshold))
        for (_,r),sc,z in zip(test.iterrows(),score,on):
            preds.append(dict(family=family,bucket=b,signal_id=int(r.signal_id),event_time=r.event_time,score=float(sc),threshold=threshold,gate_on=bool(z),signal_net_R=float(r.signal_net_R),filled=bool(r.filled)))
    return pd.DataFrame(metrics),pd.DataFrame(preds)


def pooled_from_preds(pred,buckets):
    p=pred[(pred.family==PRIMARY)&(pred.bucket.isin(buckets))].sort_values("event_time")
    if len(p)==0: return {}
    base=p.signal_net_R.to_numpy(float); gated=np.where(p.gate_on.to_numpy(bool),base,0.0)
    return dict(signals=len(p),coverage=float(p.gate_on.mean()),base_cum_R=float(base.sum()),gated_cum_R=float(gated.sum()),delta_cum_R=float(gated.sum()-base.sum()),base_ev=float(base.mean()),gated_ev=float(gated.mean()),base_pf=pf(base),gated_pf=pf(gated),base_maxdd_R=maxdd(base),gated_maxdd_R=maxdd(gated),base_max_consecutive_losses=maxloss(base),gated_max_consecutive_losses=maxloss(gated))


def family_pooled(preds):
    rows=[]
    for fam in FAMILIES:
        p=preds[(preds.family==fam)&(preds.bucket.isin(PRIMARY_YEARS))].sort_values("event_time")
        if len(p)==0: continue
        base=p.signal_net_R.to_numpy(float); gated=np.where(p.gate_on.to_numpy(bool),base,0.0)
        rec=p[p.bucket.isin(RECENT_YEARS)]; rb=rec.signal_net_R.to_numpy(float); rg=np.where(rec.gate_on.to_numpy(bool),rb,0.0)
        rows.append(dict(family=fam,signals=len(p),coverage=float(p.gate_on.mean()),base_cum_R=float(base.sum()),gated_cum_R=float(gated.sum()),delta_cum_R=float(gated.sum()-base.sum()),base_maxdd_R=maxdd(base),gated_maxdd_R=maxdd(gated),recent_base_cum_R=float(rb.sum()),recent_gated_cum_R=float(rg.sum()),recent_delta_R=float(rg.sum()-rb.sum())))
    return pd.DataFrame(rows)


def make_verdict(pm,pp):
    pooled=pooled_from_preds(pp,PRIMARY_YEARS); recent=pooled_from_preds(pp,RECENT_YEARS)
    def row(b):
        q=pm[pm.bucket==b]
        return q.iloc[0] if len(q) else None
    y22=row("2022"); y24=row("2024"); y25=row("2025"); y26=row("2026_JAN_JUL")
    pos_years=sum((row(b) is not None and float(row(b).gated_cum_R)>0) for b in PRIMARY_YEARS)
    base_recent=recent.get("base_cum_R",np.nan); gated_recent=recent.get("gated_cum_R",np.nan)
    retain70=bool(np.isfinite(base_recent) and base_recent>0 and gated_recent>=.70*base_recent)
    retain50=bool(np.isfinite(base_recent) and base_recent>0 and gated_recent>=.50*base_recent)
    gates={
        "pooled_gated_cum_gt_base":pooled.get("gated_cum_R",-np.inf)>pooled.get("base_cum_R",np.inf),
        "pooled_gated_maxdd_lt_base":pooled.get("gated_maxdd_R",np.inf)<pooled.get("base_maxdd_R",-np.inf),
        "year_2022_delta_positive":bool(y22 is not None and y22.delta_cum_R>0),
        "year_2024_delta_positive":bool(y24 is not None and y24.delta_cum_R>0),
        "year_2025_gated_positive":bool(y25 is not None and y25.gated_cum_R>0),
        "y2026_jan_jul_gated_positive":bool(y26 is not None and y26.gated_cum_R>0),
        "positive_years_ge_4_of_5":pos_years>=4,
        "pooled_coverage_25_to_75pct":.25<=pooled.get("coverage",np.nan)<=.75,
        "recent_retains_ge_70pct_base":retain70,
        "recent_gated_maxdd_le_base":recent.get("gated_maxdd_R",np.inf)<=recent.get("base_maxdd_R",-np.inf),
    }
    n=int(sum(bool(v) for v in gates.values()))
    req=["pooled_gated_cum_gt_base","year_2022_delta_positive","year_2024_delta_positive","year_2025_gated_positive","y2026_jan_jul_gated_positive","recent_retains_ge_70pct_base"]
    if n>=8 and all(gates[k] for k in req): verdict="PASS_SLOW_REGIME_ACCEPTANCE_ROUTER"
    elif n>=6 and gates["year_2025_gated_positive"] and gates["y2026_jan_jul_gated_positive"] and retain50: verdict="WATCH_PARTIAL_SLOW_REGIME"
    else: verdict="FAIL_NO_ROBUST_SLOW_REGIME"
    return dict(verdict=verdict,gates_passed=n,gates_total=len(gates),gates=gates,positive_years=int(pos_years),pooled=pooled,recent=recent,recent_retains_ge_50pct_base=retain50)


def latest_coefficients(signals):
    train=signals[signals.event_time<pd.Timestamp("2026-01-01",tz="UTC")].copy(); m=model_pipe(); m.fit(train[FAMILIES[PRIMARY]],train.signal_net_R.to_numpy(float)); thr=float(np.median(m.predict(train[FAMILIES[PRIMARY]]))); co=m.named_steps["ridge"].coef_
    d=pd.DataFrame({"feature":FAMILIES[PRIMARY],"std_coefficient":co}); d["abs_coefficient"]=d.std_coefficient.abs(); d=d.sort_values("abs_coefficient",ascending=False)
    return d,thr,float(m.named_steps["ridge"].intercept_)


def feature_year_means(signals):
    feats=FAMILIES[PRIMARY]; rows=[]
    for b,d in signals.groupby("bucket"):
        r={"bucket":b,"n":len(d)}
        for f in feats: r[f]=float(d[f].mean())
        rows.append(r)
    return pd.DataFrame(rows)


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def report(pm,fam,v,coef,thr,intercept,signals,parents):
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","","Role: slow pre-impulse regime + prior-impulse acceptance persistence gate over the frozen reversal branch; research only.","","## Frozen base","- Exact frozen REV selector + `LIMIT_R0.50_T60` + SL 1R + TP 1.5R + 5 bps.","- Slow features end before the current 60m impulse window.","- Prior impulse outcomes enter only after +24h15m, strictly before the current signal.",f"- Ridge alpha = {RIDGE_ALPHA:.1f}; ON threshold = median training score.","","## Primary slow+acceptance walk-forward","","| Year | Signals | ON | Coverage | Base Cum R | Gated Cum R | Δ R | Base EV/op | Gate EV/op | EV/traded | Base PF | Gate PF | Base DD | Gate DD |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in pm.iterrows():
        cov="—" if pd.isna(r.coverage) else f"{r.coverage*100:.1f}%"
        lines.append(f"| {r.bucket} | {int(r.signals)} | {int(r.on_n)} | {cov} | {r.base_cum_R:+.2f} | {r.gated_cum_R:+.2f} | {r.delta_cum_R:+.2f} | {r.base_ev_per_opportunity:+.3f} | {r.gated_ev_per_opportunity:+.3f} | {r.gated_ev_per_traded_signal:+.3f} | {fmtpf(r.base_pf)} | {fmtpf(r.gated_pf)} | {r.base_maxdd_R:.2f} | {r.gated_maxdd_R:.2f} |")
    p=v["pooled"]; rec=v["recent"]
    lines += ["","## Pooled primary",f"- 2022→2026 BASE **{p.get('base_cum_R',np.nan):+.2f}R** → GATED **{p.get('gated_cum_R',np.nan):+.2f}R**; delta **{p.get('delta_cum_R',np.nan):+.2f}R**.",f"- Pooled coverage **{p.get('coverage',np.nan)*100:.1f}%**; DD {p.get('base_maxdd_R',np.nan):.2f}R → {p.get('gated_maxdd_R',np.nan):.2f}R.",f"- Recent 2025+2026 BASE **{rec.get('base_cum_R',np.nan):+.2f}R** → GATED **{rec.get('gated_cum_R',np.nan):+.2f}R**; DD {rec.get('base_maxdd_R',np.nan):.2f}R → {rec.get('gated_maxdd_R',np.nan):.2f}R.","","## Audit families","","| Family | Coverage | Base Cum R | Gated Cum R | Δ R | Base DD | Gate DD | Recent Δ R |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in fam.iterrows(): lines.append(f"| {r.family} | {r.coverage*100:.1f}% | {r.base_cum_R:+.2f} | {r.gated_cum_R:+.2f} | {r.delta_cum_R:+.2f} | {r.base_maxdd_R:.2f} | {r.gated_maxdd_R:.2f} | {r.recent_delta_R:+.2f} |")
    lines += ["","## 2026 slow+acceptance model coefficients",f"Frozen 2026 threshold from 2021–2025 train = **{thr:+.4f}R-score**; intercept **{intercept:+.4f}**.","","| Feature | Std coefficient |","|---|---:|"]
    for _,r in coef.iterrows(): lines.append(f"| {r.feature} | {r.std_coefficient:+.4f} |")
    lines += ["","## Gates"]
    for k,z in v["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} → {v['verdict']}**","","## Causality/status","- 2022/2024 are mechanism-discovery years and the inherited DEV selector was fit on full 2021–2024; they are not pristine end-to-end forward tests.","- 2025/2026 are reused forward-transfer audits; August was already consumed in LAB007 and has zero frozen REV signals.","- Audit families cannot rescue a failed primary combined gate.","- No live allocation is authorized by this LAB."]
    return "\n".join(lines)+"\n"


def main():
    x,_,_=L7.load_panel(); x=enrich_slow_panel(x)
    signals,meta,parents=build_signals(x)
    allm=[]; allp=[]
    for fam,features in FAMILIES.items():
        m,p=walk_forward(signals,features,fam); allm.append(m); allp.append(p)
    metrics=pd.concat(allm,ignore_index=True); preds=pd.concat(allp,ignore_index=True) if any(len(p) for p in allp) else pd.DataFrame()
    pm=metrics[metrics.family==PRIMARY].copy(); fam=family_pooled(preds); v=make_verdict(pm,preds)
    coef,thr,intercept=latest_coefficients(signals); ym=feature_year_means(signals)
    signals.to_csv(OUT/"signals_with_slow_acceptance_features.csv",index=False)
    metrics.to_csv(OUT/"walkforward_metrics.csv",index=False)
    preds.to_csv(OUT/"walkforward_predictions.csv",index=False)
    fam.to_csv(OUT/"family_pooled.csv",index=False)
    coef.to_csv(OUT/"coefficients_2026_fit.csv",index=False)
    ym.to_csv(OUT/"year_feature_means.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,allow_nan=True),encoding="utf-8")
    rep=report(pm,fam,v,coef,thr,intercept,signals,parents); (OUT/"REPORT.md").write_text(rep,encoding="utf-8")
    print(json.dumps(v,indent=2)); print(rep)

if __name__=="__main__": main()
