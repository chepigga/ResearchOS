#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_H4_BUY_PARENT_RANGE_COMPRESSION_AND_M15_RESPONSE_SCALE_LAB_021"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
ROOT=HERE.parent
SRC=ROOT/"BTC_REVERSAL_H4_BUY_EDGE_REGIME_ONSET_AND_2025H2_STRUCTURAL_TRANSITION_LAB_020"/"output"/"buy_child_causal_features.csv"
SEED=20260906
BOOT=5000
UTC="UTC"
WINS={
 "HIST_PRE_RECENT":(pd.Timestamp("2021-01-01",tz=UTC),pd.Timestamp("2025-07-01",tz=UTC)),
 "2025_H1":(pd.Timestamp("2025-01-01",tz=UTC),pd.Timestamp("2025-07-01",tz=UTC)),
 "2025_H2":(pd.Timestamp("2025-07-01",tz=UTC),pd.Timestamp("2026-01-01",tz=UTC)),
 "2026_JAN_JUL":(pd.Timestamp("2026-01-01",tz=UTC),pd.Timestamp("2026-08-01",tz=UTC)),
 "POOLED_RECENT":(pd.Timestamp("2025-07-01",tz=UTC),pd.Timestamp("2026-08-01",tz=UTC)),
 "ALL_PRE_AUG":(pd.Timestamp("2021-01-01",tz=UTC),pd.Timestamp("2026-08-01",tz=UTC)),
 "AUG2026_REUSED_AUDIT":(pd.Timestamp("2026-08-01",tz=UTC),pd.Timestamp("2026-09-01",tz=UTC)),
}
PR_BINS=[-np.inf,.01,.015,.02,.03,np.inf]
PR_LABELS=["LT1","1_1P5","1P5_2","2_3","GE3"]
RR_BINS=[-np.inf,.15,.25,np.inf]
RR_LABELS=["LOW","MID","HIGH"]

def b(v): return str(v).strip().lower() in {"true","1","yes"}
def pf(a):
    a=np.asarray(a,float); p=float(a[a>0].sum()); n=float(-a[a<0].sum())
    if n==0:return np.inf if p>0 else np.nan
    return p/n
def maxdd(a):
    a=np.asarray(a,float)
    if len(a)==0:return 0.0
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.,eq]); return float((peak[1:]-eq).max()) if len(eq) else 0.0
def spearman(x,y):
    x=pd.Series(x,dtype=float); y=pd.Series(y,dtype=float)
    if len(x)<3 or x.nunique()<2 or y.nunique()<2:return np.nan
    return float(x.rank(method="average").corr(y.rank(method="average")))
def econ(q):
    r=q.loc[q.real_fill,"real_R"].astype(float).to_numpy()
    return dict(opps=int(len(q)),fills=int(len(r)),cum_R=float(r.sum()) if len(r) else 0.0,
                mean_R=float(r.mean()) if len(r) else np.nan,profit_factor=pf(r),max_dd_R=maxdd(r),
                positive_rate=float((r>0).mean()) if len(r) else np.nan)
def wsel(d,w):
    a,z=WINS[w]; return d[(d.parent_time>=a)&(d.parent_time<z)].copy()
def fmt(x):
    if pd.isna(x):return "—"
    if np.isinf(x):return "inf"
    return f"{float(x):.3f}"

def bootstrap_recent(d):
    q=wsel(d,"POOLED_RECENT"); q=q[q.real_fill].copy()
    groups=[g.copy() for _,g in q.groupby("episode_7d",sort=True)]
    rng=np.random.default_rng(SEED); rhos=[]; diffs=[]
    for _ in range(BOOT):
        pick=rng.integers(0,len(groups),size=len(groups)); z=pd.concat([groups[i] for i in pick],ignore_index=True)
        rhos.append(spearman(z.parent_range_pct,z.real_R))
        c=z[z.parent_range_pct<.015].real_R.to_numpy(float); l=z[z.parent_range_pct>=.015].real_R.to_numpy(float)
        diffs.append(float(c.mean()-l.mean()) if len(c) and len(l) else np.nan)
    rq=np.nanpercentile(rhos,[2.5,50,97.5]); dq=np.nanpercentile(diffs,[2.5,50,97.5])
    return dict(episodes=len(groups),rho_low=float(rq[0]),rho_median=float(rq[1]),rho_high=float(rq[2]),
                diff_low=float(dq[0]),diff_median=float(dq[1]),diff_high=float(dq[2]))

def main():
    d=pd.read_csv(SRC)
    d["parent_time"]=pd.to_datetime(d.parent_time,utc=True)
    d["real_fill"]=d.real_fill.map(b)
    for c in ["real_R","parent_range_pct","child_parent_range_ratio","prior_virtual_fills"]: d[c]=pd.to_numeric(d[c],errors="coerce")
    # lineage parity from LAB019/LAB020 BUY stream
    assert int(wsel(d,"HIST_PRE_RECENT").real_fill.sum())==23
    assert int(wsel(d,"2025_H2").real_fill.sum())==8
    assert int(wsel(d,"2026_JAN_JUL").real_fill.sum())==6
    assert int(wsel(d,"AUG2026_REUSED_AUDIT").real_fill.sum())==2

    d["parent_bin"]=pd.cut(d.parent_range_pct,PR_BINS,labels=PR_LABELS,right=False)
    d["response_bin"]=pd.cut(d.child_parent_range_ratio,RR_BINS,labels=RR_LABELS,right=False)
    d["parent_class"]=np.where(d.parent_range_pct<.015,"COMPACT","LARGE")
    d["vf_class"]=np.where(d.prior_virtual_fills>=2,"VF2PLUS","VF1")

    # Fixed-bin economics
    rows=[]
    for w in ["HIST_PRE_RECENT","2025_H1","2025_H2","2026_JAN_JUL","POOLED_RECENT","AUG2026_REUSED_AUDIT"]:
        q=wsel(d,w)
        for lab in PR_LABELS:
            e=econ(q[q.parent_bin==lab]); rows.append(dict(window=w,parent_bin=lab,**e))
    bins=pd.DataFrame(rows)

    # compact vs large
    cr=[]
    for w in WINS:
        q=wsel(d,w)
        for pc in ["COMPACT","LARGE","ALL"]:
            z=q if pc=="ALL" else q[q.parent_class==pc]
            cr.append(dict(window=w,parent_class=pc,**econ(z)))
    comp=pd.DataFrame(cr)

    # threshold-free correlation
    cors=[]
    for w in ["HIST_PRE_RECENT","2025_H2","2026_JAN_JUL","POOLED_RECENT","ALL_PRE_AUG","AUG2026_REUSED_AUDIT"]:
        q=wsel(d,w); q=q[q.real_fill]
        cors.append(dict(window=w,n=len(q),spearman_parent_range_vs_R=spearman(q.parent_range_pct,q.real_R)))
    cors=pd.DataFrame(cors)
    boot=bootstrap_recent(d)

    # response interaction
    ir=[]
    for w in ["HIST_PRE_RECENT","2025_H2","2026_JAN_JUL","POOLED_RECENT","AUG2026_REUSED_AUDIT"]:
        q=wsel(d,w)
        for pc in ["COMPACT","LARGE"]:
            for rr in RR_LABELS:
                ir.append(dict(window=w,parent_class=pc,response_bin=rr,**econ(q[(q.parent_class==pc)&(q.response_bin==rr)])))
    inter=pd.DataFrame(ir)

    # VF interaction among compact/large
    vr=[]
    for w in ["HIST_PRE_RECENT","POOLED_RECENT","2025_H2","2026_JAN_JUL"]:
        q=wsel(d,w)
        for pc in ["COMPACT","LARGE"]:
            for vf in ["VF1","VF2PLUS"]:
                vr.append(dict(window=w,parent_class=pc,vf_class=vf,**econ(q[(q.parent_class==pc)&(q.vf_class==vf)])))
    vf=pd.DataFrame(vr)

    def row(df,**kw):
        q=df.copy()
        for k,v in kw.items(): q=q[q[k]==v]
        return q.iloc[0]
    rec_c=row(comp,window="POOLED_RECENT",parent_class="COMPACT"); rec_l=row(comp,window="POOLED_RECENT",parent_class="LARGE")
    h2c=row(comp,window="2025_H2",parent_class="COMPACT"); y26c=row(comp,window="2026_JAN_JUL",parent_class="COMPACT")
    hist_c=row(comp,window="HIST_PRE_RECENT",parent_class="COMPACT"); hist_all=row(comp,window="HIST_PRE_RECENT",parent_class="ALL")
    rr=row(cors,window="POOLED_RECENT")
    ch=row(inter,window="POOLED_RECENT",parent_class="COMPACT",response_bin="HIGH")
    cl=row(inter,window="POOLED_RECENT",parent_class="COMPACT",response_bin="LOW")
    cm=row(inter,window="POOLED_RECENT",parent_class="COMPACT",response_bin="MID")
    lh=row(inter,window="POOLED_RECENT",parent_class="LARGE",response_bin="HIGH")
    lowmid_fills=int(cl.fills+cm.fills); lowmid_R=float(cl.cum_R+cm.cum_R); lowmid_mean=lowmid_R/lowmid_fills if lowmid_fills else np.nan
    cv1=row(vf,window="POOLED_RECENT",parent_class="COMPACT",vf_class="VF1"); cv2=row(vf,window="POOLED_RECENT",parent_class="COMPACT",vf_class="VF2PLUS")

    gates={
      "recent_compact_cumR_positive":float(rec_c.cum_R)>0,
      "recent_compact_mean_gt_large":np.isfinite(rec_c.mean_R) and np.isfinite(rec_l.mean_R) and float(rec_c.mean_R)>float(rec_l.mean_R),
      "recent_spearman_negative":np.isfinite(rr.spearman_parent_range_vs_R) and float(rr.spearman_parent_range_vs_R)<0,
      "bootstrap_compact_minus_large_low_gt_0":boot["diff_low"]>0,
      "bootstrap_spearman_high_lt_0":boot["rho_high"]<0,
      "both_recent_windows_compact_positive":float(h2c.cum_R)>0 and float(y26c.cum_R)>0,
      "response_scale_supportive":int(ch.fills)>=2 and lowmid_fills>=2 and np.isfinite(ch.mean_R) and np.isfinite(lowmid_mean) and float(ch.mean_R)>float(lowmid_mean),
      "large_not_rescued_by_high_response":np.isfinite(lh.mean_R) and np.isfinite(ch.mean_R) and float(lh.mean_R)<=float(ch.mean_R),
      "vf_maturity_supportive":int(cv1.fills)>=2 and int(cv2.fills)>=2 and np.isfinite(cv1.mean_R) and np.isfinite(cv2.mean_R) and float(cv2.mean_R)>=float(cv1.mean_R),
      "historical_compact_improves_baseline":np.isfinite(hist_c.mean_R) and np.isfinite(hist_all.mean_R) and float(hist_c.mean_R)>float(hist_all.mean_R),
    }
    score=sum(bool(v) for v in gates.values())
    critical=["recent_compact_cumR_positive","recent_compact_mean_gt_large","recent_spearman_negative","bootstrap_compact_minus_large_low_gt_0","bootstrap_spearman_high_lt_0","both_recent_windows_compact_positive"]
    if score>=8 and all(gates[k] for k in critical): verdict="PASS_MECHANISTIC_PARENT_COMPRESSION"
    elif score>=6 and all(gates[k] for k in ["recent_compact_cumR_positive","recent_compact_mean_gt_large","recent_spearman_negative","both_recent_windows_compact_positive"]): verdict="WATCH_PARENT_COMPRESSION_PARTIAL"
    else: verdict="FAIL_NO_ROBUST_PARENT_COMPRESSION_MECHANISM"

    bins.to_csv(OUT/"parent_range_bins.csv",index=False); comp.to_csv(OUT/"compact_vs_large.csv",index=False); cors.to_csv(OUT/"spearman.csv",index=False)
    inter.to_csv(OUT/"response_interaction.csv",index=False); vf.to_csv(OUT/"vf_interaction.csv",index=False)
    d.to_csv(OUT/"buy_opportunities_with_mechanism_classes.csv",index=False)
    with open(OUT/"verdict.json","w") as f: json.dump({"verdict":verdict,"score":score,"gates":gates,"bootstrap":boot},f,indent=2)

    L=[]; ap=L.append
    ap(f"# {LAB}\n"); ap(f"**Verdict: {verdict} — {score}/10**\n")
    ap("## Parent compression — compact vs large\n")
    ap("| Window | Class | Opps | Fills | CumR | MeanR | PF | DD |")
    ap("|---|---|---:|---:|---:|---:|---:|---:|")
    for _,x in comp[comp.window.isin(["HIST_PRE_RECENT","2025_H1","2025_H2","2026_JAN_JUL","POOLED_RECENT","AUG2026_REUSED_AUDIT"])].iterrows():
        if x.parent_class=="ALL":continue
        ap(f"| {x.window} | {x.parent_class} | {int(x.opps)} | {int(x.fills)} | {x.cum_R:+.2f} | {fmt(x.mean_R)} | {fmt(x.profit_factor)} | {x.max_dd_R:.2f} |")
    ap("\n## Fixed parent-range bins — pooled recent\n")
    ap("| Bin | Opps | Fills | CumR | MeanR | PF | DD |")
    ap("|---|---:|---:|---:|---:|---:|---:|")
    for _,x in bins[bins.window=="POOLED_RECENT"].iterrows(): ap(f"| {x.parent_bin} | {int(x.opps)} | {int(x.fills)} | {x.cum_R:+.2f} | {fmt(x.mean_R)} | {fmt(x.profit_factor)} | {x.max_dd_R:.2f} |")
    ap("\n## Threshold-free monotonicity\n")
    for _,x in cors.iterrows(): ap(f"- {x.window}: N={int(x.n)}, Spearman rho={fmt(x.spearman_parent_range_vs_R)}")
    ap(f"- Recent episode-bootstrap rho 95% CI: [{boot['rho_low']:+.3f}, {boot['rho_high']:+.3f}], median {boot['rho_median']:+.3f}")
    ap(f"- Recent compact-minus-large meanR bootstrap 95% CI: [{boot['diff_low']:+.3f}, {boot['diff_high']:+.3f}], median {boot['diff_median']:+.3f}R")
    ap("\n## M15 response-scale interaction — pooled recent\n")
    ap("| Parent | Response | Fills | CumR | MeanR | PF |")
    ap("|---|---|---:|---:|---:|---:|")
    for _,x in inter[inter.window=="POOLED_RECENT"].iterrows(): ap(f"| {x.parent_class} | {x.response_bin} | {int(x.fills)} | {x.cum_R:+.2f} | {fmt(x.mean_R)} | {fmt(x.profit_factor)} |")
    ap("\n## VF maturity interaction — pooled recent\n")
    ap("| Parent | VF | Fills | CumR | MeanR | PF |")
    ap("|---|---|---:|---:|---:|---:|")
    for _,x in vf[vf.window=="POOLED_RECENT"].iterrows(): ap(f"| {x.parent_class} | {x.vf_class} | {int(x.fills)} | {x.cum_R:+.2f} | {fmt(x.mean_R)} | {fmt(x.profit_factor)} |")
    ap("\n## Gates")
    for k,v in gates.items(): ap(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    ap("\n## Guardrail\nReused-data mechanism test only. No cutoff or router is promoted. Live allocation remains **0** pending separately preregistered replication and execution/cost parity.")
    report="\n".join(L); (OUT/"REPORT.md").write_text(report)
    print(report)

if __name__=="__main__": main()
