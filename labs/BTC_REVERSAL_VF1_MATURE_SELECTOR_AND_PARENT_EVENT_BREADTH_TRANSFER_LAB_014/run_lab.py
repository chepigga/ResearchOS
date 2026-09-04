#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_VF1_MATURE_SELECTOR_AND_PARENT_EVENT_BREADTH_TRANSFER_LAB_014"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SEED=20260904; BOOT_N=4000; COST_BPS=5.0; RR=1.5

SRC7=HERE.parent/"BTC_REVERSAL_LIMIT_RETEST_YEARLY_STABILITY_AND_FRESH_AUG2026_REPLICATION_LAB_007"/"run_lab.py"
spec7=importlib.util.spec_from_file_location("lab007",SRC7); L7=importlib.util.module_from_spec(spec7); spec7.loader.exec_module(L7)
L6=L7.L6; L5=L7.L5

PARENT_QS={"P975":.975,"P970":.970,"P960":.960,"P950":.950}
ROUTER_TOP={"T20":.80,"T25":.75,"T30":.70,"T40":.60}
PRIMARY="P960_T30"; BASELINE="P975_T20"
NEIGHBORS=["P970_T30","P960_T25","P960_T40","P950_T30"]
WINS={
    "2025_H2":(pd.Timestamp("2025-07-01",tz="UTC"),pd.Timestamp("2026-01-01",tz="UTC"),6.0),
    "2026_JAN_JUL":(pd.Timestamp("2026-01-01",tz="UTC"),pd.Timestamp("2026-08-01",tz="UTC"),7.0),
    "POOLED_RECENT":(pd.Timestamp("2025-07-01",tz="UTC"),pd.Timestamp("2026-08-01",tz="UTC"),13.0),
    "AUG2026_REUSED_AUDIT":(pd.Timestamp("2026-08-01",tz="UTC"),pd.Timestamp("2026-09-01",tz="UTC"),1.0),
}


def pf(a):
    a=np.asarray(a,float); pos=float(a[a>0].sum()); neg=float(-a[a<0].sum())
    if neg==0: return np.inf if pos>0 else np.nan
    return pos/neg

def maxdd(a): return float(L6.max_dd_r(np.asarray(a,float))) if len(a) else np.nan
def maxloss(a): return int(L6.max_consecutive_loss(np.asarray(a,float))) if len(a) else 0

def make_events_q(x,q):
    z=x.copy()
    w=L5.ROLL
    z["impulse_thr"]=z.btc_lr60.abs().rolling(w,min_periods=w//2).quantile(q).shift(1)
    z["impulse_raw"]=z.btc_lr60.abs()>=z.impulse_thr
    return L5.make_events(z)


def freeze_canonical_router(x):
    e=make_events_q(x,.975).copy()
    dev=e[e.split=="DEV_2021_2024"].copy()
    cont_thr=float(dev.cont_24h.quantile(.75)); rev_thr=float(dev.rev_24h.quantile(.75))
    dev["tail_cont"]=(dev.cont_24h>=cont_thr).astype(int)
    dev["tail_rev"]=(dev.rev_24h>=rev_thr).astype(int)
    mc=L5.fit_pipe(dev,L5.CORE,"tail_cont"); mr=L5.fit_pipe(dev,L5.CORE,"tail_rev")
    pc=mc.predict_proba(dev[L5.CORE])[:,1]; pr=mr.predict_proba(dev[L5.CORE])[:,1]
    conf=np.maximum(pc,pr)
    cuts={name:float(np.quantile(conf,q)) for name,q in ROUTER_TOP.items()}
    return mc,mr,{"cont_thr":cont_thr,"rev_thr":rev_thr,**{f"router_{k}":v for k,v in cuts.items()}},cuts


def score_events(e,mc,mr):
    q=e.copy()
    pc=mc.predict_proba(q[L5.CORE])[:,1]; pr=mr.predict_proba(q[L5.CORE])[:,1]
    q["p_cont"]=pc; q["p_rev"]=pr; q["router_conf"]=np.maximum(pc,pr)
    q["router_side"]=np.where(pc>=pr,"CONT","REV")
    return q


def execute_virtual(x,e):
    rows=[]
    for idx,r in e.iterrows():
        rr=r.copy(); rr.name=idx
        z=L6.first_hit(x,rr,RR)
        d=r.to_dict(); d["source_row"]=int(idx)
        if z is None:
            d.update(filled=False,fill_time=pd.NaT,signal_net_R=0.0,gross_R=0.0,cost_R=0.0,outcome="NO_FILL",stop_frac=np.nan)
        else:
            cost=(COST_BPS/10000.0)/float(z["stop_frac"])
            d.update(filled=True,fill_time=pd.Timestamp(z["fill_time"]),signal_net_R=float(z["gross_R"]-cost),gross_R=float(z["gross_R"]),cost_R=float(cost),outcome=z["outcome"],stop_frac=float(z["stop_frac"]))
        rows.append(d)
    s=pd.DataFrame(rows).sort_values("event_time").reset_index(drop=True)
    if len(s)==0: return s
    gaps=s.event_time.diff().dt.total_seconds().div(86400.0)
    s["episode_7d"]=(gaps.isna() | (gaps>7.0)).cumsum().astype(int)
    s["prior_virtual_fills"]=0
    for eid,q in s.groupby("episode_7d",sort=True):
        prior=[]
        for i,r in q.sort_values("event_time").iterrows():
            t=pd.Timestamp(r.event_time)
            n=0
            for pr in prior:
                if bool(pr["filled"]) and pd.notna(pr["fill_time"]) and pd.Timestamp(pr["fill_time"])<t:
                    n+=1
            s.loc[i,"prior_virtual_fills"]=n
            prior.append(r.to_dict())
    s["vf1_mature"]=s.prior_virtual_fills>=1
    s["real_R"]=np.where(s.vf1_mature,s.signal_net_R,0.0)
    s["real_fill"]=(s.vf1_mature & s.filled)
    return s


def cluster_bootstrap(d,seed):
    groups=[q.real_R.to_numpy(float) for _,q in d.groupby("episode_7d",sort=True)]
    if not groups: return np.nan,np.nan
    rng=np.random.default_rng(seed); n=len(groups); vals=[]
    for _ in range(BOOT_N):
        ix=rng.integers(0,n,size=n); z=np.concatenate([groups[j] for j in ix]); vals.append(float(z.mean()))
    return tuple(float(x) for x in np.quantile(vals,[.025,.975]))


def window_summary(cell,s,wname,start,end,months,seed):
    d=s[(s.event_time>=start)&(s.event_time<end)].copy().sort_values("event_time")
    if len(d)==0:
        return dict(cell=cell,window=wname,selected_rev=0,mature_admit=0,real_fills=0,fills_per_month=0.0,mean_R_per_fill=np.nan,cum_R=0.0,profit_factor=np.nan,max_dd_R=0.0,max_consecutive_losses=0,episodes=0,positive_episodes=0,negative_episodes=0,worst_episode_R=np.nan,top_episode_positive_share=np.nan,worst_loeo_remaining_R=np.nan,bootstrap_ci025=np.nan,bootstrap_ci975=np.nan)
    r=d.real_R.to_numpy(float); rf=d.loc[d.real_fill,"real_R"].to_numpy(float)
    eps=[]
    for eid,q in d.groupby("episode_7d",sort=True):
        ar=q.real_R.to_numpy(float); eps.append((int(eid),float(ar.sum()),float(ar[ar>0].sum())))
    ep=pd.DataFrame(eps,columns=["episode","cum_R","positive_R"])
    total=float(r.sum()); gross=float(r[r>0].sum())
    top=float(ep.positive_R.max()/gross) if gross>0 and len(ep) else np.nan
    loeo=float((total-ep.cum_R).min()) if len(ep) else np.nan
    lo,hi=cluster_bootstrap(d,seed)
    return dict(cell=cell,window=wname,selected_rev=len(d),mature_admit=int(d.vf1_mature.sum()),real_fills=int(d.real_fill.sum()),fills_per_month=float(d.real_fill.sum()/months),mean_R_per_fill=float(rf.mean()) if len(rf) else np.nan,cum_R=total,profit_factor=pf(r),max_dd_R=maxdd(r),max_consecutive_losses=maxloss(r),episodes=len(ep),positive_episodes=int((ep.cum_R>0).sum()),negative_episodes=int((ep.cum_R<0).sum()),worst_episode_R=float(ep.cum_R.min()) if len(ep) else np.nan,top_episode_positive_share=top,worst_loeo_remaining_R=loeo,bootstrap_ci025=lo,bootstrap_ci975=hi)


def build_cell(x,parent_name,parent_q,top_name,cutoff,mc,mr):
    e=make_events_q(x,parent_q)
    e=e[e.event_time<pd.Timestamp("2026-09-01",tz="UTC")].copy()
    e=score_events(e,mc,mr)
    sel=e[(e.router_side=="REV")&(e.router_conf>=cutoff)].copy()
    sel["breadth_cell"]=f"{parent_name}_{top_name}"
    return execute_virtual(x,sel),e


def row(tab,cell,window):
    q=tab[(tab.cell==cell)&(tab.window==window)]
    return q.iloc[0] if len(q) else None


def plateau_ok(tab):
    ok=[]
    for c in NEIGHBORS:
        a=row(tab,c,"2025_H2"); b=row(tab,c,"2026_JAN_JUL"); p=row(tab,c,"POOLED_RECENT")
        z=bool(a is not None and b is not None and p is not None and a.mean_R_per_fill>0 and b.mean_R_per_fill>0 and p.profit_factor>1.3 and p.fills_per_month>=2.0)
        ok.append((c,z))
    return ok


def verdict(tab):
    p25=row(tab,PRIMARY,"2025_H2"); p26=row(tab,PRIMARY,"2026_JAN_JUL"); pp=row(tab,PRIMARY,"POOLED_RECENT"); bp=row(tab,BASELINE,"POOLED_RECENT")
    plateau=plateau_ok(tab); plateau_n=sum(z for _,z in plateau)
    retention=float(pp.cum_R/bp.cum_R) if bp is not None and bp.cum_R>0 else np.nan
    gates={
        "h2_2025_fills_ge_18":int(p25.real_fills)>=18,
        "y2026_fills_ge_21":int(p26.real_fills)>=21,
        "pooled_fills_ge_39":int(pp.real_fills)>=39,
        "h2_2025_mean_fill_R_ge_0.30":float(p25.mean_R_per_fill)>=.30,
        "y2026_mean_fill_R_ge_0.30":float(p26.mean_R_per_fill)>=.30,
        "recent_pf_ge_1.5_both":float(p25.profit_factor)>=1.5 and float(p26.profit_factor)>=1.5,
        "recent_maxdd_le_2.5R_both":float(p25.max_dd_R)<=2.5 and float(p26.max_dd_R)<=2.5,
        "recent_cum_R_positive_both":float(p25.cum_R)>0 and float(p26.cum_R)>0,
        "pooled_retains_ge_90pct_baseline_R":bool(np.isfinite(retention) and retention>=.90),
        "pooled_cluster_bootstrap_ci_low_gt_0":float(pp.bootstrap_ci025)>0,
        "pooled_all_loeo_positive":float(pp.worst_loeo_remaining_R)>0,
        "plateau_neighbors_ge_2":plateau_n>=2,
    }
    n=int(sum(bool(z) for z in gates.values()))
    critical=["h2_2025_fills_ge_18","y2026_fills_ge_21","pooled_fills_ge_39","h2_2025_mean_fill_R_ge_0.30","y2026_mean_fill_R_ge_0.30","recent_pf_ge_1.5_both","recent_cum_R_positive_both","plateau_neighbors_ge_2"]
    if n>=10 and all(gates[k] for k in critical):
        v="PASS_VF1_BREADTH_FREQUENCY_TRANSFER"
    elif float(p25.cum_R)>0 and float(p26.cum_R)>0 and float(p25.mean_R_per_fill)>0 and float(p26.mean_R_per_fill)>0 and float(p25.profit_factor)>1 and float(p26.profit_factor)>1 and float(pp.fills_per_month)>float(bp.fills_per_month):
        v="WATCH_VF1_BREADTH_QUALITY_BUT_FREQ_SHORT"
    else:
        v="FAIL_VF1_BREADTH_DESTROYS_EDGE"
    return {"verdict":v,"gates_passed":n,"gates_total":len(gates),"gates":gates,"primary":PRIMARY,"baseline":BASELINE,"pooled_R_retention":retention,"plateau":dict(plateau),"plateau_passed":plateau_n}


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def report(tab,v,meta,cuts):
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","","Role: upstream parent-event/router breadth transfer over frozen `VF1_MATURE`; no execution or maturity retuning.","","## Frozen router cutoffs"]
    for k in ["T20","T25","T30","T40"]: lines.append(f"- {k}: **{cuts[k]:.6f}** (canonical P97.5 DEV score distribution)")
    lines += ["",f"Primary cell: **{PRIMARY}**. Baseline: **{BASELINE}**.","","## Primary vs baseline","","| Cell | Window | Selected REV | Mature | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | Episodes | Worst ep | Boot CI low |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in [BASELINE,PRIMARY]:
        for w in ["2025_H2","2026_JAN_JUL","POOLED_RECENT","AUG2026_REUSED_AUDIT"]:
            r=row(tab,c,w)
            lines.append(f"| {c} | {w} | {int(r.selected_rev)} | {int(r.mature_admit)} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {r.mean_R_per_fill:+.3f} | {r.cum_R:+.2f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} | {int(r.episodes)} | {r.worst_episode_R:+.2f} | {r.bootstrap_ci025:+.3f} |" if r.real_fills else f"| {c} | {w} | {int(r.selected_rev)} | {int(r.mature_admit)} | 0 | 0.00 | — | +0.00 | — | {r.max_dd_R:.2f} | {int(r.episodes)} | — | — |")
    lines += ["","## Full breadth grid — pooled recent","","| Cell | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | Boot CI low |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    p=tab[tab.window=="POOLED_RECENT"].copy()
    for _,r in p.iterrows():
        lines.append(f"| {r.cell} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {r.mean_R_per_fill:+.3f} | {r.cum_R:+.2f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} | {r.bootstrap_ci025:+.3f} |" if r.real_fills else f"| {r.cell} | 0 | 0.00 | — | +0.00 | — | — | — |")
    lines += ["","## Plateau neighbors"]
    for c,z in v["plateau"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{c}`")
    lines += ["","## Gates"]
    for k,z in v["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    bp=row(tab,BASELINE,"POOLED_RECENT"); pp=row(tab,PRIMARY,"POOLED_RECENT")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} → {v['verdict']}**","","## Interpretation",f"- Baseline pooled VF1 frequency: **{bp.fills_per_month:.2f} fills/month**; primary breadth: **{pp.fills_per_month:.2f}/month**.",f"- Baseline pooled CumR **{bp.cum_R:+.2f}R** → primary **{pp.cum_R:+.2f}R**; retention **{v['pooled_R_retention']*100:.1f}%**.","- August 2026 is reused/consumed audit only and cannot promote.","- Broader parent universes are scored by the canonical frozen router; no breadth-specific refit occurred.","- No live allocation is authorized by this LAB."]
    return "\n".join(lines)+"\n"


def main():
    x,hf,ff=L7.load_panel()
    mc,mr,meta,cuts=freeze_canonical_router(x)
    all_rows=[]; cell_events=[]; seed=1000
    for pn,pq in PARENT_QS.items():
        for tn in ROUTER_TOP:
            cell=f"{pn}_{tn}"; s,_=build_cell(x,pn,pq,tn,cuts[tn],mc,mr)
            if len(s):
                s["cell"]=cell; cell_events.append(s)
            for w,(a,b,m) in WINS.items():
                all_rows.append(window_summary(cell,s,w,a,b,m,SEED+seed)); seed+=17
    tab=pd.DataFrame(all_rows)
    v=verdict(tab)
    tab.to_csv(OUT/"breadth_grid_summary.csv",index=False)
    if cell_events: pd.concat(cell_events,ignore_index=True).to_csv(OUT/"all_cell_selected_rev_virtual_state.csv",index=False)
    (OUT/"frozen_router_meta.json").write_text(json.dumps({"meta":meta,"cuts":cuts},indent=2),encoding="utf-8")
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,allow_nan=True),encoding="utf-8")
    rep=report(tab,v,meta,cuts); (OUT/"REPORT.md").write_text(rep,encoding="utf-8")
    print(json.dumps(v,indent=2)); print(rep)

if __name__=="__main__": main()
