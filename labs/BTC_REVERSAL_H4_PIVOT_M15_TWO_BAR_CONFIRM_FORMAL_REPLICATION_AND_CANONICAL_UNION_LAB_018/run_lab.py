#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_H4_PIVOT_M15_TWO_BAR_CONFIRM_FORMAL_REPLICATION_AND_CANONICAL_UNION_LAB_018"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
PRIMARY="TWO_BAR_CONFIRM_12H"

SRC17V3=HERE.parent/"BTC_REVERSAL_H4_PIVOT_PARENT_TO_M15_CHILD_VIRTUAL_FILL_AND_EXECUTION_BRIDGE_LAB_017"/"run_lab_v3.py"
spec=importlib.util.spec_from_file_location("lab017v3",SRC17V3)
V3=importlib.util.module_from_spec(spec); spec.loader.exec_module(V3)
L17=V3.L17

WINS=L17.WINS
HIST=L17.HIST_WINS


def pf(a): return L17.pf(np.asarray(a,float)) if len(a) else np.nan
def maxdd(a): return L17.maxdd(np.asarray(a,float)) if len(a) else 0.0

def equity_stats(a,risk):
    eq=peak=1.0; mdd=0.0
    for r in np.asarray(a,float):
        eq*=max(0.0,1.0+risk*r); peak=max(peak,eq); mdd=max(mdd,(peak-eq)/peak)
    return (eq-1.0)*100.0,mdd*100.0

def max_concurrent(d):
    if len(d)==0: return 0
    q=d.dropna(subset=["fill_time","exit_time"]).copy()
    if len(q)==0: return 0
    starts=pd.to_datetime(q.fill_time,utc=True).to_numpy(); ends=pd.to_datetime(q.exit_time,utc=True).to_numpy()
    mx=0
    for t in starts: mx=max(mx,int(np.sum((starts<=t)&(ends>t))))
    return mx

def canonical_window(canon,a,b,months):
    d=canon[(canon.event_time>=a)&(canon.event_time<b)&(canon.real_fill)].copy().sort_values("fill_time")
    r=d.real_R.to_numpy(float)
    return dict(real_fills=len(d),fills_per_month=len(d)/months,cum_R=float(r.sum()) if len(r) else 0.0,mean_R=float(r.mean()) if len(r) else np.nan,pf=pf(r),dd=maxdd(r))

def module_extra(s,a,b,months):
    d=s[(s.parent_time>=a)&(s.parent_time<b)].copy().sort_values("signal_time")
    rf=d[d.real_fill].copy().sort_values("fill_time")
    r=rf.real_R.to_numpy(float)
    ne,pe,ng,worst,loeo=L17.episode_stats(d)
    return dict(parents=int(d.parent_id.nunique()) if len(d) else 0,children=len(d),virtual_fills=int(d.filled.sum()) if len(d) else 0,mature=int(d.vf1_mature.sum()) if len(d) else 0,real_fills=len(rf),fills_per_month=len(rf)/months,mean_R=float(r.mean()) if len(r) else np.nan,cum_R=float(r.sum()) if len(r) else 0.0,pf=pf(r),dd=maxdd(r),loeo=loeo,max_concurrent=max_concurrent(rf))

def build_union(canon,child,a,b,months):
    c=canon[(canon.event_time>=a)&(canon.event_time<b)&(canon.real_fill)].copy()
    c["src"]="CANON"; c["window_time"]=c.event_time
    h=child[(child.parent_time>=a)&(child.parent_time<b)&(child.real_fill)].copy()
    h["src"]="H4_TWO_BAR"; h["window_time"]=h.parent_time
    cols=["src","window_time","fill_time","exit_time","real_R","impulse_dir"]
    z=pd.concat([c[cols],h[cols]],ignore_index=True).sort_values("fill_time")
    r=z.real_R.to_numpy(float) if len(z) else np.array([])
    er25,ed25=equity_stats(r,.0025); er50,ed50=equity_stats(r,.005)
    mc=max_concurrent(z)
    return dict(real_fills=len(z),fills_per_month=len(z)/months,canonical_fills=int((z.src=="CANON").sum()) if len(z) else 0,h4_fills=int((z.src=="H4_TWO_BAR").sum()) if len(z) else 0,cum_R=float(r.sum()) if len(r) else 0.0,mean_R=float(r.mean()) if len(r) else np.nan,pf=pf(r),dd=maxdd(r),max_concurrent=mc,risk_load_025_pct=mc*.25,risk_load_050_pct=mc*.50,equity_return_025_pct=er25,equity_dd_025_pct=ed25,equity_return_050_pct=er50,equity_dd_050_pct=ed50),z

def monthly_table(canon,child):
    a=pd.Timestamp("2025-07-01",tz="UTC"); b=pd.Timestamp("2026-08-01",tz="UTC")
    c=canon[(canon.event_time>=a)&(canon.event_time<b)&(canon.real_fill)].copy(); c["src"]="CANON"; c["t"]=c.fill_time
    h=child[(child.parent_time>=a)&(child.parent_time<b)&(child.real_fill)].copy(); h["src"]="H4_TWO_BAR"; h["t"]=h.fill_time
    z=pd.concat([c[["src","t","real_R"]],h[["src","t","real_R"]]],ignore_index=True)
    if len(z)==0: return pd.DataFrame()
    z["month"]=pd.to_datetime(z.t,utc=True).dt.to_period("M").astype(str)
    g=z.groupby(["month","src"]).real_R.agg(["count","sum"]).reset_index()
    piv=g.pivot(index="month",columns="src",values="sum").fillna(0.0)
    cnt=g.pivot(index="month",columns="src",values="count").fillna(0).astype(int)
    out=pd.DataFrame(index=sorted(set(g.month)))
    for src in ["CANON","H4_TWO_BAR"]:
        out[f"{src}_fills"]=cnt[src] if src in cnt else 0
        out[f"{src}_R"]=piv[src] if src in piv else 0.0
    out["UNION_R"]=out.get("CANON_R",0)+out.get("H4_TWO_BAR_R",0)
    return out.reset_index(names="month")

def direction_table(child):
    rows=[]
    for w,(a,b,months) in WINS.items():
        if w=="AUG2026_REUSED_AUDIT": continue
        d=child[(child.parent_time>=a)&(child.parent_time<b)&(child.real_fill)].copy()
        d["reversal_side"]=np.where(d.impulse_dir<0,"BUY","SELL")
        for side,q in d.groupby("reversal_side"):
            r=q.real_R.to_numpy(float)
            rows.append(dict(window=w,side=side,n=len(q),cum_R=float(r.sum()),mean_R=float(r.mean()),profit_factor=pf(r),max_dd_R=maxdd(r)))
    return pd.DataFrame(rows)

def verdict(summary,union,canon_summary,lineage):
    def row(w): return summary[summary.window==w].iloc[0]
    a=row("2025_H2"); b=row("2026_JAN_JUL"); p=row("POOLED_RECENT")
    u=union[union.window=="POOLED_RECENT"].iloc[0]; c=canon_summary[canon_summary.window=="POOLED_RECENT"].iloc[0]
    gates={
      "lineage_exact":bool(lineage),
      "h2_real_fills_ge_8":int(a.real_fills)>=8,
      "y2026_real_fills_ge_5":int(b.real_fills)>=5,
      "mean_R_positive_both":float(a.mean_R)>0 and float(b.mean_R)>0,
      "pf_gt_1_30_both":float(a.profit_factor)>1.30 and float(b.profit_factor)>1.30,
      "cumR_positive_both":float(a.cum_R)>0 and float(b.cum_R)>0,
      "pooled_ev_ge_0_25R":float(p.mean_R)>=.25,
      "pooled_pf_ge_1_50":float(p.profit_factor)>=1.50,
      "pooled_loeo_positive":bool(np.isfinite(p.loeo_worst) and float(p.loeo_worst)>0),
      "pooled_maxdd_le_3R":float(p.max_dd_R)<=3.0,
      "union_freq_ge_3_per_month":float(u.fills_per_month)>=3.0,
      "union_incremental_cumR_ge_2R":float(u.cum_R)-float(c.cum_R)>=2.0,
      "union_pf_ge_1_75":float(u.profit_factor)>=1.75,
      "union_maxdd_le_4R":float(u.max_dd_R)<=4.0,
      "union_max_concurrent_risk_050_lt_4pct":float(u.risk_load_050_pct)<4.0,
      "union_positive_both_recent_windows":all(float(union[union.window==w].iloc[0].cum_R)>0 for w in ["2025_H2","2026_JAN_JUL"]),
    }
    n=sum(bool(v) for v in gates.values())
    critical=["lineage_exact","mean_R_positive_both","pf_gt_1_30_both","cumR_positive_both","pooled_ev_ge_0_25R","pooled_pf_ge_1_50","pooled_loeo_positive","union_freq_ge_3_per_month","union_incremental_cumR_ge_2R","union_positive_both_recent_windows"]
    if n>=14 and all(gates[k] for k in critical): v="PASS_FORMAL_TWO_BAR_REPLICATION_REUSED"
    elif n>=11 and float(a.cum_R)>0 and float(b.cum_R)>0 and float(u.cum_R)>float(c.cum_R): v="WATCH_TWO_BAR_REPLICATION"
    else: v="FAIL_TWO_BAR_REPLICATION"
    return dict(verdict=v,gates_passed=int(n),gates_total=len(gates),gates=gates)

def main():
    x,_,_=L17.L7.load_panel()
    parents,pre,raw,_=V3.load_frozen_parents(x)
    lineage=(len(raw)==610 and len(pre)==294 and len(parents)==213 and (len(pre)-len(parents))==81)
    child=L17.execute_child_virtual(x,L17.make_children(x,parents,PRIMARY))
    canon=V3.load_frozen_canonical_stream()

    # Reproduce formal module summary using frozen primary.
    base=L17.summarize_rule(PRIMARY,parents,child,WINS)
    extras=[]
    for w,(a,b,m) in WINS.items():
        e=module_extra(child,a,b,m); e["window"]=w; extras.append(e)
    ex=pd.DataFrame(extras)
    summary=base.drop(columns=[c for c in ["fills_per_month","mean_R_per_fill","cum_R","profit_factor","max_dd_R","worst_loeo_remaining_R"] if c in base.columns]).merge(ex,on="window",how="left")
    summary=summary.rename(columns={"mean_R":"mean_R","pf":"profit_factor","dd":"max_dd_R","loeo":"loeo_worst"})

    unions=[]; canonrows=[]; union_trades=[]
    for w,(a,b,m) in WINS.items():
        if w=="AUG2026_REUSED_AUDIT": continue
        cu=canonical_window(canon,a,b,m); cu["window"]=w; canonrows.append(cu)
        uu,z=build_union(canon,child,a,b,m); uu["window"]=w; unions.append(uu); z["window"]=w; union_trades.append(z)
    union=pd.DataFrame(unions); csum=pd.DataFrame(canonrows)
    direction=direction_table(child); monthly=monthly_table(canon,child)
    v=verdict(summary,union,csum,lineage)

    child.to_csv(OUT/"two_bar_confirm_vf1_stream.csv",index=False)
    summary.to_csv(OUT/"two_bar_formal_summary.csv",index=False)
    csum.to_csv(OUT/"canonical_summary.csv",index=False)
    union.to_csv(OUT/"canonical_plus_two_bar_union.csv",index=False)
    direction.to_csv(OUT/"direction_split.csv",index=False)
    monthly.to_csv(OUT/"monthly_distribution.csv",index=False)
    pd.concat(union_trades,ignore_index=True).to_csv(OUT/"union_trades.csv",index=False)

    lines=[f"# {LAB}","",f"**Verdict: {v['verdict']} — {v['gates_passed']}/{v['gates_total']}**","","Frozen primary: exact LAB017 audit `TWO_BAR_CONFIRM_12H` promoted before this run; exact LAB016 213-parent lineage; exact LAB015 canonical stream.","","## H4 two-bar module","","| Window | Parents | Real fills | Fills/mo | Mean R | Cum R | PF | DD R | LOEO worst | Max concurrent |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in summary.iterrows():
        lines.append(f"| {r.window} | {int(r.eligible_parents)} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {r.mean_R:+.3f} | {r.cum_R:+.2f} | {r.profit_factor:.3f} | {r.max_dd_R:.2f} | {r.loeo_worst:+.2f} | {int(r.max_concurrent)} |" if r.real_fills else f"| {r.window} | {int(r.eligible_parents)} | 0 | 0.00 | — | +0.00 | — | 0.00 | — | 0 |")
    lines += ["","## Canonical + H4 two-bar union","","| Window | Fills | Fills/mo | Canon | H4 | Cum R | Mean R | PF | DD R | Max conc | Risk load @0.5% | Eq ret @0.25% | Eq DD @0.25% | Eq ret @0.5% | Eq DD @0.5% |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in union.iterrows():
        lines.append(f"| {r.window} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {int(r.canonical_fills)} | {int(r.h4_fills)} | {r.cum_R:+.2f} | {r.mean_R:+.3f} | {r.profit_factor:.3f} | {r.max_dd_R:.2f} | {int(r.max_concurrent)} | {r.risk_load_050_pct:.2f}% | {r.equity_return_025_pct:+.2f}% | {r.equity_dd_025_pct:.2f}% | {r.equity_return_050_pct:+.2f}% | {r.equity_dd_050_pct:.2f}% |")
    lines += ["","## Direction split","","| Window | Side | N | Cum R | Mean R | PF | DD R |","|---|---|---:|---:|---:|---:|---:|"]
    for _,r in direction.iterrows(): lines.append(f"| {r.window} | {r.side} | {int(r.n)} | {r.cum_R:+.2f} | {r.mean_R:+.3f} | {r.profit_factor:.3f} | {r.max_dd_R:.2f} |")
    lines += ["","## Gates"]
    for k,val in v["gates"].items(): lines.append(f"- {'PASS' if val else 'FAIL'} — `{k}`")
    lines += ["","## Status","- This is formal replication on reused research windows, **not fresh OOS**.","- August 2026 remains consumed/reused audit only.","- No parameter or child-rule rescue is allowed after this run.","- Live allocation remains **0**; M1/raw execution parity, exact prop costs/slippage, future fresh replication, and full prop-rule implementation are still required."]
    (OUT/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    meta=dict(lineage_exact=lineage,raw=610,t25_pre=294,removed=81,parents=213,recent_h2=22,recent_2026=21,primary=PRIMARY)
    (OUT/"verdict.json").write_text(json.dumps({**v,"meta":meta},indent=2,allow_nan=True),encoding="utf-8")
    print(json.dumps({**v,"meta":meta},indent=2)); print((OUT/"REPORT.md").read_text())

if __name__=="__main__": main()
