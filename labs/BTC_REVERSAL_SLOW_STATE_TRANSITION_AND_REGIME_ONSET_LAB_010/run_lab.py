#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_SLOW_STATE_TRANSITION_AND_REGIME_ONSET_LAB_010"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SRC9=HERE.parent/"BTC_REVERSAL_SLOW_REGIME_AND_IMPULSE_ACCEPTANCE_PERSISTENCE_LAB_009"/"run_lab.py"
spec9=importlib.util.spec_from_file_location("lab009",SRC9); L9=importlib.util.module_from_spec(spec9); spec9.loader.exec_module(L9)
L7=L9.L7; L6=L9.L6; L5=L9.L5

PRIMARY="TRANSITION_COMBINED"
TEST_BUCKETS=L9.TEST_BUCKETS
PRIMARY_YEARS=L9.PRIMARY_YEARS
RECENT_YEARS=L9.RECENT_YEARS
TEST_START=L9.TEST_START

TREND_FEATURES=[
    "d7_aligned_ret30d","d30_aligned_ret30d",
    "d7_aligned_ret60d","d30_aligned_ret60d",
    "d7_aligned_ret90d","d30_aligned_ret90d",
    "curve_ret30_60","curve_ret60_90",
]
EFF_FEATURES=[
    "d7_eff30d","d30_eff30d","d7_eff60d","d30_eff60d","d7_eff90d","d30_eff90d",
]
VOL_FEATURES=[
    "d7_rv30d","d30_rv30d","d7_rv60d","d30_rv60d","d7_rv90d","d30_rv90d",
    "d7_rv30_90_ratio","d30_rv30_90_ratio",
]
POSITION_FEATURES=[
    "d7_oriented_pos30d","d30_oriented_pos30d","d7_oriented_pos90d","d30_oriented_pos90d",
]
FAMILIES={
    "TREND_TRANSITION":TREND_FEATURES,
    "EFFICIENCY_TRANSITION":EFF_FEATURES,
    "VOL_TRANSITION":VOL_FEATURES,
    "POSITION_TRANSITION":POSITION_FEATURES,
}
FAMILIES[PRIMARY]=TREND_FEATURES+EFF_FEATURES+VOL_FEATURES+POSITION_FEATURES
PRIMARY_FEATURES=FAMILIES[PRIMARY]


def safe_at(s,i):
    if i<0 or i>=len(s): return np.nan
    v=s.iloc[i]
    return float(v) if np.isfinite(v) else np.nan


def oriented_pos(v,d):
    if not np.isfinite(v): return np.nan
    return float(v if d>0 else 1.0-v)


def add_transition_features(x,signals):
    s=signals.copy(); rows=[]
    lags={"d7":7*96,"d30":30*96}
    for _,r0 in s.iterrows():
        r=r0.to_dict(); i=int(r0.event_i); d=float(r0.impulse_dir)
        # Direction-aligned slow-return transition.
        for horizon in [30,60,90]:
            col=f"slow_ret{horizon}d"; cur=safe_at(x[col],i)
            for tag,lag in lags.items():
                old=safe_at(x[col],i-lag)
                r[f"{tag}_aligned_ret{horizon}d"]=float(d*(cur-old)) if np.isfinite(cur) and np.isfinite(old) else np.nan
        r["curve_ret30_60"]=float(d*(safe_at(x.slow_ret30d,i)-safe_at(x.slow_ret60d,i))) if np.isfinite(safe_at(x.slow_ret30d,i)) and np.isfinite(safe_at(x.slow_ret60d,i)) else np.nan
        r["curve_ret60_90"]=float(d*(safe_at(x.slow_ret60d,i)-safe_at(x.slow_ret90d,i))) if np.isfinite(safe_at(x.slow_ret60d,i)) and np.isfinite(safe_at(x.slow_ret90d,i)) else np.nan
        # Efficiency transition.
        for horizon in [30,60,90]:
            col=f"slow_eff{horizon}d"; cur=safe_at(x[col],i)
            for tag,lag in lags.items():
                old=safe_at(x[col],i-lag)
                r[f"{tag}_eff{horizon}d"]=float(cur-old) if np.isfinite(cur) and np.isfinite(old) else np.nan
        # Volatility transition.
        for horizon in [30,60,90]:
            col=f"slow_rv{horizon}d"; cur=safe_at(x[col],i)
            for tag,lag in lags.items():
                old=safe_at(x[col],i-lag)
                r[f"{tag}_rv{horizon}d"]=float(cur-old) if np.isfinite(cur) and np.isfinite(old) else np.nan
        cur_ratio=safe_at(x.slow_rv30_90_ratio,i)
        for tag,lag in lags.items():
            old=safe_at(x.slow_rv30_90_ratio,i-lag)
            r[f"{tag}_rv30_90_ratio"]=float(cur_ratio-old) if np.isfinite(cur_ratio) and np.isfinite(old) else np.nan
        # Event-direction oriented range-position transition.
        for horizon in [30,90]:
            col=f"slow_pos{horizon}d"; cur=oriented_pos(safe_at(x[col],i),d)
            for tag,lag in lags.items():
                old=oriented_pos(safe_at(x[col],i-lag),d)
                r[f"{tag}_oriented_pos{horizon}d"]=float(cur-old) if np.isfinite(cur) and np.isfinite(old) else np.nan
        rows.append(r)
    z=pd.DataFrame(rows).replace([np.inf,-np.inf],np.nan)
    return z.sort_values("event_time").reset_index(drop=True) if len(z) else z


def pf(a): return L6.pf(np.asarray(a,float))
def maxdd(a): return L6.max_dd_r(np.asarray(a,float))
def maxloss(a): return L6.max_consecutive_loss(np.asarray(a,float))


def walk_forward(signals,features,family):
    metrics=[]; preds=[]
    for b in TEST_BUCKETS:
        test=signals[signals.bucket==b].copy(); train=signals[signals.event_time<TEST_START[b]].copy()
        if len(test)==0 or len(train)<20:
            metrics.append(dict(family=family,bucket=b,train_n=len(train),signals=len(test),on_n=0,coverage=np.nan,
                base_filled=int(test.filled.sum()) if len(test) else 0,gated_filled=0,
                base_cum_R=float(test.signal_net_R.sum()) if len(test) else 0.0,gated_cum_R=0.0,
                delta_cum_R=float(-test.signal_net_R.sum()) if len(test) else 0.0,
                base_ev_per_opportunity=float(test.signal_net_R.mean()) if len(test) else np.nan,
                gated_ev_per_opportunity=np.nan,gated_ev_per_traded_signal=np.nan,
                base_pf=pf(test.signal_net_R) if len(test) else np.nan,gated_pf=np.nan,
                base_maxdd_R=maxdd(test.signal_net_R) if len(test) else np.nan,gated_maxdd_R=np.nan,
                base_max_consecutive_losses=maxloss(test.signal_net_R) if len(test) else 0,gated_max_consecutive_losses=0,threshold=np.nan))
            continue
        m=L9.model_pipe(); m.fit(train[features],train.signal_net_R.to_numpy(float))
        train_score=m.predict(train[features]); threshold=float(np.median(train_score)); score=m.predict(test[features]); on=score>=threshold
        metrics.append(L9.eval_bucket(test,on,family,b,len(train),threshold))
        for (_,r),sc,z in zip(test.iterrows(),score,on):
            preds.append(dict(family=family,bucket=b,signal_id=int(r.signal_id),event_time=r.event_time,
                              score=float(sc),threshold=threshold,gate_on=bool(z),signal_net_R=float(r.signal_net_R),filled=bool(r.filled)))
    return pd.DataFrame(metrics),pd.DataFrame(preds)


def pooled(preds,family,buckets):
    p=preds[(preds.family==family)&(preds.bucket.isin(buckets))].sort_values("event_time")
    if len(p)==0: return {}
    base=p.signal_net_R.to_numpy(float); gated=np.where(p.gate_on.to_numpy(bool),base,0.0)
    return dict(signals=len(p),coverage=float(p.gate_on.mean()),base_cum_R=float(base.sum()),gated_cum_R=float(gated.sum()),
                delta_cum_R=float(gated.sum()-base.sum()),base_ev=float(base.mean()),gated_ev=float(gated.mean()),
                base_pf=pf(base),gated_pf=pf(gated),base_maxdd_R=maxdd(base),gated_maxdd_R=maxdd(gated),
                base_max_consecutive_losses=maxloss(base),gated_max_consecutive_losses=maxloss(gated))


def family_pooled(preds):
    rows=[]
    for fam in FAMILIES:
        a=pooled(preds,fam,PRIMARY_YEARS); r=pooled(preds,fam,RECENT_YEARS)
        if not a: continue
        rows.append(dict(family=fam,signals=a["signals"],coverage=a["coverage"],base_cum_R=a["base_cum_R"],
                         gated_cum_R=a["gated_cum_R"],delta_cum_R=a["delta_cum_R"],base_maxdd_R=a["base_maxdd_R"],
                         gated_maxdd_R=a["gated_maxdd_R"],recent_base_cum_R=r.get("base_cum_R",np.nan),
                         recent_gated_cum_R=r.get("gated_cum_R",np.nan),recent_delta_R=r.get("delta_cum_R",np.nan)))
    return pd.DataFrame(rows)


def make_verdict(pm,pp):
    a=pooled(pp,PRIMARY,PRIMARY_YEARS); r=pooled(pp,PRIMARY,RECENT_YEARS)
    def row(b):
        q=pm[pm.bucket==b]
        return q.iloc[0] if len(q) else None
    y22,y24,y25,y26=row("2022"),row("2024"),row("2025"),row("2026_JAN_JUL")
    pos_years=sum((row(b) is not None and float(row(b).gated_cum_R)>0) for b in PRIMARY_YEARS)
    base_recent=r.get("base_cum_R",np.nan); gated_recent=r.get("gated_cum_R",np.nan)
    retain70=bool(np.isfinite(base_recent) and base_recent>0 and gated_recent>=.70*base_recent)
    retain50=bool(np.isfinite(base_recent) and base_recent>0 and gated_recent>=.50*base_recent)
    gates={
        "pooled_gated_cum_gt_base":a.get("gated_cum_R",-np.inf)>a.get("base_cum_R",np.inf),
        "pooled_gated_maxdd_lt_base":a.get("gated_maxdd_R",np.inf)<a.get("base_maxdd_R",-np.inf),
        "year_2022_delta_positive":bool(y22 is not None and y22.delta_cum_R>0),
        "year_2024_delta_positive":bool(y24 is not None and y24.delta_cum_R>0),
        "year_2025_gated_positive":bool(y25 is not None and y25.gated_cum_R>0),
        "y2026_jan_jul_gated_positive":bool(y26 is not None and y26.gated_cum_R>0),
        "positive_years_ge_4_of_5":pos_years>=4,
        "pooled_coverage_25_to_75pct":.25<=a.get("coverage",np.nan)<=.75,
        "recent_retains_ge_70pct_base":retain70,
        "recent_gated_maxdd_le_base":r.get("gated_maxdd_R",np.inf)<=r.get("base_maxdd_R",-np.inf),
    }
    n=int(sum(bool(v) for v in gates.values()))
    required=["pooled_gated_cum_gt_base","year_2022_delta_positive","year_2024_delta_positive",
              "year_2025_gated_positive","y2026_jan_jul_gated_positive","recent_retains_ge_70pct_base"]
    if n>=8 and all(gates[k] for k in required): verdict="PASS_SLOW_STATE_TRANSITION_ONSET"
    elif n>=6 and gates["year_2025_gated_positive"] and gates["y2026_jan_jul_gated_positive"] and retain50:
        verdict="WATCH_PARTIAL_TRANSITION_ONSET"
    else: verdict="FAIL_NO_ROBUST_TRANSITION_ONSET"
    return dict(verdict=verdict,gates_passed=n,gates_total=len(gates),gates=gates,positive_years=int(pos_years),
                pooled=a,recent=r,recent_retains_50pct=retain50,recent_retains_70pct=retain70)


def frozen_2025_coefficients(signals):
    train=signals[signals.event_time<pd.Timestamp("2025-01-01",tz="UTC")].copy()
    m=L9.model_pipe(); m.fit(train[PRIMARY_FEATURES],train.signal_net_R.to_numpy(float))
    threshold=float(np.median(m.predict(train[PRIMARY_FEATURES])))
    co=m.named_steps["ridge"].coef_
    df=pd.DataFrame({"feature":PRIMARY_FEATURES,"std_coefficient":co})
    df["abs_coefficient"]=df.std_coefficient.abs(); df=df.sort_values("abs_coefficient",ascending=False)
    return df,threshold,float(m.named_steps["ridge"].intercept_)


def onset_2025(preds):
    p=preds[(preds.family==PRIMARY)&(preds.bucket=="2025")].sort_values("event_time").copy()
    rows=[]
    for name,start,end in [
        ("2025_H1",pd.Timestamp("2025-01-01",tz="UTC"),pd.Timestamp("2025-07-01",tz="UTC")),
        ("2025_H2",pd.Timestamp("2025-07-01",tz="UTC"),pd.Timestamp("2026-01-01",tz="UTC")),
    ]:
        q=p[(p.event_time>=start)&(p.event_time<end)]
        if len(q)==0:
            rows.append(dict(period=name,signals=0,on_n=0,coverage=np.nan,base_cum_R=0.0,gated_cum_R=0.0,delta_R=0.0,mean_score=np.nan,threshold=np.nan)); continue
        base=q.signal_net_R.to_numpy(float); gated=np.where(q.gate_on.to_numpy(bool),base,0.0)
        rows.append(dict(period=name,signals=len(q),on_n=int(q.gate_on.sum()),coverage=float(q.gate_on.mean()),
                         base_cum_R=float(base.sum()),gated_cum_R=float(gated.sum()),delta_R=float(gated.sum()-base.sum()),
                         mean_score=float(q.score.mean()),threshold=float(q.threshold.iloc[0])))
    return pd.DataFrame(rows)


def year_feature_means(signals):
    buckets=["2021","2022","2023","2024","2025","2026_JAN_JUL"]
    rows=[]
    for b in buckets:
        q=signals[signals.bucket==b]
        r={"bucket":b,"n":len(q)}
        for f in PRIMARY_FEATURES: r[f]=float(q[f].mean()) if len(q) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def report(pm,fam,v,coef,thr,intercept,onset):
    p=pm[pm.family==PRIMARY]
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","",
           "Role: causal pre-impulse slow-state transition/onset gate over the frozen reversal branch; research only.","",
           "## Frozen base","- Exact frozen REV selector + `LIMIT_R0.50_T60` + SL 1R + TP 1.5R + 5 bps.",
           "- Transition features are computed from slow-state series ending before the current 60m impulse window.",
           "- No acceptance-history, router-score, current impulse-shape, or post-impulse path feature enters the primary gate.",
           "- Ridge alpha = 10.0; ON threshold = median training score.","",
           "## Primary transition walk-forward","",
           "| Year | Signals | ON | Coverage | Base Cum R | Gated Cum R | Δ R | Base EV/op | Gate EV/op | EV/traded | Base PF | Gate PF | Base DD | Gate DD |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in p.iterrows():
        if int(r.signals)==0:
            lines.append(f"| {r.bucket} | 0 | 0 | — | +0.00 | +0.00 | +0.00 | — | — | — | — | — | — | — |")
        else:
            lines.append(f"| {r.bucket} | {int(r.signals)} | {int(r.on_n)} | {r.coverage*100:.1f}% | {r.base_cum_R:+.2f} | {r.gated_cum_R:+.2f} | {r.delta_cum_R:+.2f} | {r.base_ev_per_opportunity:+.3f} | {r.gated_ev_per_opportunity:+.3f} | {r.gated_ev_per_traded_signal:+.3f} | {fmtpf(r.base_pf)} | {fmtpf(r.gated_pf)} | {r.base_maxdd_R:.2f} | {r.gated_maxdd_R:.2f} |")
    a=v["pooled"]; rec=v["recent"]
    lines += ["","## Pooled primary",
              f"- 2022→2026 BASE **{a.get('base_cum_R',np.nan):+.2f}R** → GATED **{a.get('gated_cum_R',np.nan):+.2f}R**; delta **{a.get('delta_cum_R',np.nan):+.2f}R**.",
              f"- Pooled coverage **{a.get('coverage',np.nan)*100:.1f}%**; DD {a.get('base_maxdd_R',np.nan):.2f}R → {a.get('gated_maxdd_R',np.nan):.2f}R.",
              f"- Recent 2025+2026 BASE **{rec.get('base_cum_R',np.nan):+.2f}R** → GATED **{rec.get('gated_cum_R',np.nan):+.2f}R**; DD {rec.get('base_maxdd_R',np.nan):.2f}R → {rec.get('gated_maxdd_R',np.nan):.2f}R.","",
              "## 2025 onset localization","","| Period | Signals | ON | Coverage | Base Cum R | Gated Cum R | Δ R | Mean score | Frozen threshold |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in onset.iterrows():
        if int(r.signals): lines.append(f"| {r.period} | {int(r.signals)} | {int(r.on_n)} | {r.coverage*100:.1f}% | {r.base_cum_R:+.2f} | {r.gated_cum_R:+.2f} | {r.delta_R:+.2f} | {r.mean_score:+.4f} | {r.threshold:+.4f} |")
        else: lines.append(f"| {r.period} | 0 | 0 | — | +0.00 | +0.00 | +0.00 | — | — |")
    lines += ["","## Audit transition families","","| Family | Coverage | Base Cum R | Gated Cum R | Δ R | Base DD | Gate DD | Recent Δ R |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in fam.iterrows(): lines.append(f"| {r.family} | {r.coverage*100:.1f}% | {r.base_cum_R:+.2f} | {r.gated_cum_R:+.2f} | {r.delta_cum_R:+.2f} | {r.base_maxdd_R:.2f} | {r.gated_maxdd_R:.2f} | {r.recent_delta_R:+.2f} |")
    lines += ["",f"## Frozen 2025 transition coefficients",f"2025 threshold from 2021–2024 train = **{thr:+.4f}R-score**; intercept **{intercept:+.4f}**.","",
              "| Feature | Std coefficient |","|---|---:|"]
    for _,r in coef.head(16).iterrows(): lines.append(f"| {r.feature} | {r.std_coefficient:+.4f} |")
    lines += ["","## Gates"]
    for k,z in v["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} → {v['verdict']}**","",
              "## Causality/status","- 2022/2024 are mechanism-discovery years; inherited selector was fit on full DEV 2021–2024.",
              "- 2025 is the key onset transfer check: its transition gate is trained only on 2021–2024 outcomes.",
              "- 2026 is a reused forward-transfer audit; August has zero frozen REV opportunities.",
              "- Audit families cannot rescue a failed primary combined transition gate.",
              "- No live allocation is authorized by this LAB."]
    return "\n".join(lines)+"\n"


def main():
    x,hf,ff=L7.load_panel(); x=L9.enrich_slow_panel(x)
    base,meta,parents=L9.build_signals(x); signals=add_transition_features(x,base)
    metrics=[]; preds=[]
    for fam,features in FAMILIES.items():
        m,p=walk_forward(signals,features,fam); metrics.append(m); preds.append(p)
    metrics=pd.concat(metrics,ignore_index=True); preds=pd.concat(preds,ignore_index=True)
    pm=metrics[metrics.family==PRIMARY].copy(); fam=family_pooled(preds); v=make_verdict(pm,preds)
    coef,thr,intercept=frozen_2025_coefficients(signals); onset=onset_2025(preds); yf=year_feature_means(signals)
    signals.to_csv(OUT/"transition_signals.csv",index=False); metrics.to_csv(OUT/"walk_forward_metrics.csv",index=False)
    preds.to_csv(OUT/"walk_forward_predictions.csv",index=False); fam.to_csv(OUT/"family_pooled.csv",index=False)
    coef.to_csv(OUT/"frozen_2025_coefficients.csv",index=False); onset.to_csv(OUT/"onset_2025_h1_h2.csv",index=False)
    yf.to_csv(OUT/"year_transition_feature_means.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,allow_nan=True),encoding="utf-8")
    rep=report(metrics,fam,v,coef,thr,intercept,onset); (OUT/"REPORT.md").write_text(rep,encoding="utf-8")
    print(json.dumps(v,indent=2)); print(rep)

if __name__=="__main__": main()
