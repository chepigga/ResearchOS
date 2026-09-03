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

LAB="BTC_REVERSAL_EDGE_ON_OFF_REGIME_AND_ROUTER_ABSTENTION_LAB_008"
SEED=20260903
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SRC7=HERE.parent/"BTC_REVERSAL_LIMIT_RETEST_YEARLY_STABILITY_AND_FRESH_AUG2026_REPLICATION_LAB_007"/"run_lab.py"
spec7=importlib.util.spec_from_file_location("lab007",SRC7); L7=importlib.util.module_from_spec(spec7); spec7.loader.exec_module(L7)
L6=L7.L6; L5=L7.L5
PRIMARY_RR=1.5; COST_BPS=5.0; RIDGE_ALPHA=5.0

FAMILIES={
    "ROUTER_ONLY":["router_margin","router_conf"],
    "TREND_ONLY":["signed_ret24h","signed_ret7d","signed_ret30d","eff24h","eff7d","extreme_pos7d"],
    "VOL_ONLY":["rv_ratio_4h24h","btc_range_z","btc_vol_z"],
    "IMPULSE_ONLY":["impulse_strength","btc_range_z","btc_vol_z"],
}
PRIMARY_FEATURES=list(dict.fromkeys(FAMILIES["ROUTER_ONLY"]+FAMILIES["TREND_ONLY"]+FAMILIES["VOL_ONLY"]+["impulse_strength"]))
FAMILIES["PRIMARY_COMBINED"]=PRIMARY_FEATURES
PRIMARY="PRIMARY_COMBINED"
TEST_BUCKETS=["2022","2023","2024","2025","2026_JAN_JUL","FRESH_AUG2026"]
TEST_START={
    "2022":pd.Timestamp("2022-01-01",tz="UTC"),
    "2023":pd.Timestamp("2023-01-01",tz="UTC"),
    "2024":pd.Timestamp("2024-01-01",tz="UTC"),
    "2025":pd.Timestamp("2025-01-01",tz="UTC"),
    "2026_JAN_JUL":pd.Timestamp("2026-01-01",tz="UTC"),
    "FRESH_AUG2026":pd.Timestamp("2026-08-01",tz="UTC"),
}
PRIMARY_YEARS=["2022","2023","2024","2025","2026_JAN_JUL"]
RECENT_YEARS=["2025","2026_JAN_JUL"]


def enrich_panel(x):
    x=x.copy(); c=x.btc_close; lr=x.btc_lr15
    n24=96; n7=7*96; n30=30*96
    x["reg_ret7d"]=np.log(c/c.shift(n7)); x["reg_ret30d"]=np.log(c/c.shift(n30))
    den24=lr.abs().rolling(n24,min_periods=n24//2).sum(); den7=lr.abs().rolling(n7,min_periods=n7//2).sum()
    x["reg_eff24h"]=np.log(c/c.shift(n24)).abs()/den24.replace(0,np.nan)
    x["reg_eff7d"]=x.reg_ret7d.abs()/den7.replace(0,np.nan)
    rv4=lr.rolling(16,min_periods=8).std(ddof=0); rv24=lr.rolling(n24,min_periods=48).std(ddof=0)
    x["reg_rv_ratio_4h24h"]=rv4/rv24.replace(0,np.nan)
    prior_hi=x.btc_high.rolling(n7,min_periods=n7//2).max().shift(1); prior_lo=x.btc_low.rolling(n7,min_periods=n7//2).min().shift(1)
    x["reg_pos7d"]=(c-prior_lo)/(prior_hi-prior_lo).replace(0,np.nan)
    x["reg_impulse_strength"]=x.btc_lr60.abs()/x.impulse_thr.replace(0,np.nan)
    return x


def first_hit_signal_net_r(x,row):
    r=row.copy(); r.name=row.name; r["split"]=row.bucket
    z=L6.first_hit(x,r,PRIMARY_RR)
    if z is None:
        return dict(filled=False,signal_net_R=0.0,gross_R=0.0,cost_R=0.0,outcome="NO_FILL",fill_time=pd.NaT,stop_frac=np.nan)
    cost=(COST_BPS/10000.0)/float(z["stop_frac"])
    return dict(filled=True,signal_net_R=float(z["gross_R"]-cost),gross_R=float(z["gross_R"]),cost_R=float(cost),outcome=z["outcome"],fill_time=z["fill_time"],stop_frac=float(z["stop_frac"]))


def build_signals(x):
    e,meta=L7.selected_table(x); sel=e[e.selected_rev].copy()
    rows=[]
    for idx,row in sel.iterrows():
        i=int(row.event_i); d=float(row.impulse_dir); pos=float(x.reg_pos7d.iloc[i]) if np.isfinite(x.reg_pos7d.iloc[i]) else np.nan
        r=row.to_dict(); r["signal_id"]=int(idx); r["router_margin"]=float(row.p_rev-row.p_cont); r["router_conf"]=float(row.router_conf)
        r["signed_ret24h"]=float(d*x.btc_lr24h.iloc[i]) if np.isfinite(x.btc_lr24h.iloc[i]) else np.nan
        r["signed_ret7d"]=float(d*x.reg_ret7d.iloc[i]) if np.isfinite(x.reg_ret7d.iloc[i]) else np.nan
        r["signed_ret30d"]=float(d*x.reg_ret30d.iloc[i]) if np.isfinite(x.reg_ret30d.iloc[i]) else np.nan
        r["eff24h"]=float(x.reg_eff24h.iloc[i]) if np.isfinite(x.reg_eff24h.iloc[i]) else np.nan
        r["eff7d"]=float(x.reg_eff7d.iloc[i]) if np.isfinite(x.reg_eff7d.iloc[i]) else np.nan
        r["extreme_pos7d"]=float(pos if d>0 else 1.0-pos) if np.isfinite(pos) else np.nan
        r["rv_ratio_4h24h"]=float(x.reg_rv_ratio_4h24h.iloc[i]) if np.isfinite(x.reg_rv_ratio_4h24h.iloc[i]) else np.nan
        r["impulse_strength"]=float(x.reg_impulse_strength.iloc[i]) if np.isfinite(x.reg_impulse_strength.iloc[i]) else np.nan
        rr=row.copy(); rr.name=idx
        r.update(first_hit_signal_net_r(x,rr)); rows.append(r)
    s=pd.DataFrame(rows).replace([np.inf,-np.inf],np.nan)
    if len(s): s=s.sort_values("event_time").reset_index(drop=True)
    return s,meta


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


def pooled_stats(pred,signals,buckets):
    p=pred[(pred.family==PRIMARY)&(pred.bucket.isin(buckets))].copy()
    if len(p)==0: return {}
    q=p.merge(signals[["signal_id","event_time"]],on=["signal_id","event_time"],how="left").sort_values("event_time")
    base=q.signal_net_R.to_numpy(float); gated=np.where(q.gate_on.to_numpy(bool),base,0.0)
    return dict(signals=len(q),coverage=float(q.gate_on.mean()),base_cum_R=float(base.sum()),gated_cum_R=float(gated.sum()),delta_cum_R=float(gated.sum()-base.sum()),base_ev=float(base.mean()),gated_ev=float(gated.mean()),base_pf=pf(base),gated_pf=pf(gated),base_maxdd_R=maxdd(base),gated_maxdd_R=maxdd(gated),base_max_consecutive_losses=maxloss(base),gated_max_consecutive_losses=maxloss(gated))


def family_pooled(metrics,preds,signals):
    rows=[]
    for fam in FAMILIES:
        p=preds[(preds.family==fam)&(preds.bucket.isin(PRIMARY_YEARS))].sort_values("event_time")
        if len(p)==0: continue
        base=p.signal_net_R.to_numpy(float); gated=np.where(p.gate_on.to_numpy(bool),base,0.0)
        rec=p[p.bucket.isin(RECENT_YEARS)]; rb=rec.signal_net_R.to_numpy(float); rg=np.where(rec.gate_on.to_numpy(bool),rb,0.0)
        rows.append(dict(family=fam,signals=len(p),coverage=float(p.gate_on.mean()),base_cum_R=float(base.sum()),gated_cum_R=float(gated.sum()),delta_cum_R=float(gated.sum()-base.sum()),base_maxdd_R=maxdd(base),gated_maxdd_R=maxdd(gated),recent_base_cum_R=float(rb.sum()),recent_gated_cum_R=float(rg.sum()),recent_delta_R=float(rg.sum()-rb.sum())))
    return pd.DataFrame(rows)


def make_verdict(primary_metrics,primary_preds,signals):
    pooled=pooled_stats(primary_preds,signals,PRIMARY_YEARS); recent=pooled_stats(primary_preds,signals,RECENT_YEARS)
    def row(b):
        q=primary_metrics[primary_metrics.bucket==b]
        return q.iloc[0] if len(q) else None
    y22=row("2022"); y24=row("2024"); y25=row("2025"); y26=row("2026_JAN_JUL")
    pos_years=sum((row(b) is not None and float(row(b).gated_cum_R)>0) for b in PRIMARY_YEARS)
    gates={
        "pooled_gated_cum_gt_base":pooled.get("gated_cum_R",-np.inf)>pooled.get("base_cum_R",np.inf),
        "pooled_gated_maxdd_lt_base":pooled.get("gated_maxdd_R",np.inf)<pooled.get("base_maxdd_R",-np.inf),
        "year_2022_delta_positive":bool(y22 is not None and y22.delta_cum_R>0),
        "year_2024_delta_positive":bool(y24 is not None and y24.delta_cum_R>0),
        "year_2025_gated_positive":bool(y25 is not None and y25.gated_cum_R>0),
        "y2026_jan_jul_gated_positive":bool(y26 is not None and y26.gated_cum_R>0),
        "positive_years_ge_4_of_5":pos_years>=4,
        "pooled_coverage_25_to_75pct":.25<=pooled.get("coverage",np.nan)<=.75,
        "recent_gated_cum_positive":recent.get("gated_cum_R",-np.inf)>0,
        "recent_gated_maxdd_le_base":recent.get("gated_maxdd_R",np.inf)<=recent.get("base_maxdd_R",-np.inf),
    }
    n=int(sum(bool(v) for v in gates.values()))
    required=["pooled_gated_cum_gt_base","year_2022_delta_positive","year_2024_delta_positive","year_2025_gated_positive","y2026_jan_jul_gated_positive"]
    if n>=8 and all(gates[k] for k in required): verdict="PASS_CAUSAL_ON_OFF_ABSTENTION_ROUTER"
    elif n>=6 and gates["recent_gated_cum_positive"] and gates["year_2025_gated_positive"] and gates["y2026_jan_jul_gated_positive"]: verdict="WATCH_PARTIAL_REGIME_ABSTENTION"
    else: verdict="FAIL_NO_ROBUST_ON_OFF_ROUTER"
    return dict(verdict=verdict,gates_passed=n,gates_total=len(gates),gates=gates,positive_years=int(pos_years),pooled=pooled,recent=recent)


def latest_coefficients(signals):
    train=signals[signals.event_time<pd.Timestamp("2026-01-01",tz="UTC")].copy(); m=model_pipe(); m.fit(train[PRIMARY_FEATURES],train.signal_net_R.to_numpy(float)); scores=m.predict(train[PRIMARY_FEATURES]); thr=float(np.median(scores)); co=m.named_steps["ridge"].coef_
    return pd.DataFrame({"feature":PRIMARY_FEATURES,"std_coefficient":co}).assign(abs_coefficient=lambda d:d.std_coefficient.abs()).sort_values("abs_coefficient",ascending=False),thr,float(m.named_steps["ridge"].intercept_)


def on_off_means(signals,preds):
    p=preds[(preds.family==PRIMARY)&(preds.bucket.isin(PRIMARY_YEARS))][["signal_id","gate_on"]]
    q=signals.merge(p,on="signal_id",how="inner")
    rows=[]
    for f in PRIMARY_FEATURES:
        on=q[q.gate_on][f]; off=q[~q.gate_on][f]
        rows.append(dict(feature=f,on_mean=float(on.mean()),off_mean=float(off.mean()),on_minus_off=float(on.mean()-off.mean())))
    return pd.DataFrame(rows)


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def report(pm,fam,v,coef,coef_thr,coef_int,signals):
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","","Role: causal event-time ON/OFF abstention layer over the frozen LAB006 reversal setup; research only.","","## Frozen base","- Exact frozen REV selector + `LIMIT_R0.50_T60` + SL 1R + TP 1.5R + 5 bps.","- Gate can only TRADE or ABSTAIN; it cannot change entry, stop, target, TTL, direction, or size.","- Ridge alpha = 5.0; ON threshold = median training score for each expanding yearly fit.","","## Causality boundary","- Gate features are known at impulse close and each yearly gate fit uses only prior completed signal outcomes.","- The inherited LAB003 selector was fit on full DEV 2021–2024, so 2022–2024 are conditional mechanism diagnostics, not end-to-end deployment-causal tests.","- 2025/2026 are stronger forward-transfer audits; August 2026 has zero frozen REV signals and cannot evaluate the gate.","","## Primary combined walk-forward","","| Year | Signals | ON | Coverage | Base Cum R | Gated Cum R | Δ R | Base EV/op | Gate EV/op | EV/traded | Base PF | Gate PF | Base DD R | Gate DD R |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in pm.iterrows():
        if r.signals==0:
            lines.append(f"| {r.bucket} | 0 | 0 | — | 0 | 0 | 0 | — | — | — | — | — | — | — |")
        else:
            lines.append(f"| {r.bucket} | {int(r.signals)} | {int(r.on_n)} | {r.coverage*100:.1f}% | {r.base_cum_R:+.2f} | {r.gated_cum_R:+.2f} | {r.delta_cum_R:+.2f} | {r.base_ev_per_opportunity:+.3f} | {r.gated_ev_per_opportunity:+.3f} | {r.gated_ev_per_traded_signal:+.3f} | {fmtpf(r.base_pf)} | {fmtpf(r.gated_pf)} | {r.base_maxdd_R:.2f} | {r.gated_maxdd_R:.2f} |")
    p=v["pooled"]; rec=v["recent"]
    lines += ["","## Pooled primary","",f"- 2022→2026 opportunities: **{p.get('signals',0)}**; gate coverage **{p.get('coverage',np.nan)*100:.1f}%**.",f"- BASE cum: **{p.get('base_cum_R',np.nan):+.2f}R** → GATED: **{p.get('gated_cum_R',np.nan):+.2f}R**; delta **{p.get('delta_cum_R',np.nan):+.2f}R**.",f"- BASE max DD: **{p.get('base_maxdd_R',np.nan):.2f}R** → GATED **{p.get('gated_maxdd_R',np.nan):.2f}R**.",f"- Recent 2025+2026 BASE **{rec.get('base_cum_R',np.nan):+.2f}R** → GATED **{rec.get('gated_cum_R',np.nan):+.2f}R**; DD {rec.get('base_maxdd_R',np.nan):.2f}R → {rec.get('gated_maxdd_R',np.nan):.2f}R.","","## Audit feature families","","| Family | Coverage | Base Cum R | Gated Cum R | Δ R | Base DD | Gate DD | Recent Δ R |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in fam.iterrows(): lines.append(f"| {r.family} | {r.coverage*100:.1f}% | {r.base_cum_R:+.2f} | {r.gated_cum_R:+.2f} | {r.delta_cum_R:+.2f} | {r.base_maxdd_R:.2f} | {r.gated_maxdd_R:.2f} | {r.recent_delta_R:+.2f} |")
    lines += ["","## 2026 gate model standardized coefficients","",f"Frozen 2026 ON threshold from 2021–2025 training scores: **{coef_thr:+.4f}R-score**; intercept **{coef_int:+.4f}**.","","| Feature | Std coefficient |","|---|---:|"]
    for _,r in coef.iterrows(): lines.append(f"| {r.feature} | {r.std_coefficient:+.4f} |")
    lines += ["","## Gates"]
    for k,z in v["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} → {v['verdict']}**","","## Interpretation","- Audit-family results cannot rescue the primary combined gate.","- 2022/2024 improvement is mechanism evidence only because the inherited DEV selector was not historically walk-forward in those years.","- A later end-to-end causal selector replication is mandatory before production or live risk."]
    return "\n".join(lines)+"\n"


def main():
    x,hf,ff=L7.load_panel(); x=enrich_panel(x); signals,meta=build_signals(x)
    allm=[]; allp=[]
    for fam,features in FAMILIES.items():
        m,p=walk_forward(signals,features,fam); allm.append(m); allp.append(p)
    metrics=pd.concat(allm,ignore_index=True); preds=pd.concat(allp,ignore_index=True) if allp else pd.DataFrame()
    pm=metrics[metrics.family==PRIMARY].copy(); fam=family_pooled(metrics,preds,signals); v=make_verdict(pm,preds,signals)
    coef,thr,inter=latest_coefficients(signals); means=on_off_means(signals,preds)
    signals.to_csv(OUT/"eligible_rev_signals_with_regime_features.csv",index=False)
    metrics.to_csv(OUT/"walkforward_year_metrics.csv",index=False); preds.to_csv(OUT/"walkforward_signal_predictions.csv",index=False)
    fam.to_csv(OUT/"family_pooled_audit.csv",index=False); coef.to_csv(OUT/"latest_2026_gate_coefficients.csv",index=False); means.to_csv(OUT/"primary_on_off_feature_means.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,allow_nan=True),encoding="utf-8")
    rep=report(pm,fam,v,coef,thr,inter,signals); (OUT/"REPORT.md").write_text(rep,encoding="utf-8")
    print(json.dumps(v,indent=2)); print(rep)

if __name__=="__main__": main()
