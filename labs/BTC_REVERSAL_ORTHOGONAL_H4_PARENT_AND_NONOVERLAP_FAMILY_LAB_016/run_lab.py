#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_ORTHOGONAL_H4_PARENT_AND_NONOVERLAP_FAMILY_LAB_016"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SEED=20260905
FAMILIES=["H4_DISPLACEMENT_EXTREME","H4_FAILED_EXTENSION","H4_7D_PIVOT_SWEEP_RECLAIM"]
WINS={
    "2025_H2":(pd.Timestamp("2025-07-01",tz="UTC"),pd.Timestamp("2026-01-01",tz="UTC"),6.0),
    "2026_JAN_JUL":(pd.Timestamp("2026-01-01",tz="UTC"),pd.Timestamp("2026-08-01",tz="UTC"),7.0),
    "POOLED_RECENT":(pd.Timestamp("2025-07-01",tz="UTC"),pd.Timestamp("2026-08-01",tz="UTC"),13.0),
    "AUG2026_REUSED_AUDIT":(pd.Timestamp("2026-08-01",tz="UTC"),pd.Timestamp("2026-09-01",tz="UTC"),1.0),
}
HIST_WINS={
    "2021":(pd.Timestamp("2021-01-01",tz="UTC"),pd.Timestamp("2022-01-01",tz="UTC"),12.0),
    "2022":(pd.Timestamp("2022-01-01",tz="UTC"),pd.Timestamp("2023-01-01",tz="UTC"),12.0),
    "2023":(pd.Timestamp("2023-01-01",tz="UTC"),pd.Timestamp("2024-01-01",tz="UTC"),12.0),
    "2024":(pd.Timestamp("2024-01-01",tz="UTC"),pd.Timestamp("2025-01-01",tz="UTC"),12.0),
    "2025_H1":(pd.Timestamp("2025-01-01",tz="UTC"),pd.Timestamp("2025-07-01",tz="UTC"),6.0),
}

SRC15=HERE.parent/"BTC_REVERSAL_P975_T25_CONFIRMATION_AND_SECOND_PARENT_FAMILY_DISCOVERY_LAB_015"/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab015",SRC15)
L15=importlib.util.module_from_spec(spec); spec.loader.exec_module(L15)
L14=L15.L14; L7=L15.L7; L6=L15.L6; L5=L15.L5


def split_year(ts):
    y=ts.year
    return "DEV_2021_2024" if y<=2024 else ("BRIDGE_2025" if y==2025 else "OOS_2026")


def h4_table(x):
    rows=[]
    hours={3,7,11,15,19,23}
    for i,t in enumerate(x.index):
        if i<16 or i+L5.H24>=len(x): continue
        if t.minute!=45 or t.hour not in hours: continue
        j=i-15
        q=x.iloc[j:i+1]
        op=float(q.btc_open.iloc[0]); hi=float(q.btc_high.max()); lo=float(q.btc_low.min()); cl=float(q.btc_close.iloc[-1])
        prev_close=float(x.btc_close.iloc[i-16])
        if not np.isfinite(prev_close) or prev_close<=0 or cl<=0: continue
        ret=float(np.log(cl/prev_close))
        last60=float(np.log(cl/float(x.btc_close.iloc[i-4])))
        # prior 7d excludes the entire current H4 block
        p0=max(0,j-7*96); prior=x.iloc[p0:j]
        p_hi=float(prior.btc_high.max()) if len(prior)>=3*96 else np.nan
        p_lo=float(prior.btc_low.min()) if len(prior)>=3*96 else np.nan
        rows.append(dict(event_i=i,event_time=t,h4_open=op,h4_high=hi,h4_low=lo,h4_close=cl,h4_range=hi-lo,h4_ret=ret,last60_ret=last60,prior7d_high=p_hi,prior7d_low=p_lo))
    h=pd.DataFrame(rows)
    if len(h)==0: return h
    # 30d of completed H4 bars = 180 bars; shifted one completed H4 observation
    minp=90
    h["absret_q975"]=h.h4_ret.abs().rolling(180,min_periods=minp).quantile(.975).shift(1)
    h["absret_q950"]=h.h4_ret.abs().rolling(180,min_periods=minp).quantile(.950).shift(1)
    return h


def family_h4_rows(h,family):
    if len(h)==0: return h.copy()
    z=h.copy(); ar=z.h4_ret.abs(); d=np.sign(z.h4_ret)
    if family=="H4_DISPLACEMENT_EXTREME":
        flag=(ar>=z.absret_q975) & d.ne(0)
        z["impulse_dir"]=d
    elif family=="H4_FAILED_EXTENSION":
        opp=np.sign(z.last60_ret)==-d
        enough=z.last60_ret.abs()>=.25*ar
        flag=(ar>=z.absret_q950) & d.ne(0) & opp & enough
        z["impulse_dir"]=d
    elif family=="H4_7D_PIVOT_SWEEP_RECLAIM":
        rng=z.h4_range.replace(0,np.nan)
        hi_sweep=(z.h4_high>z.prior7d_high) & (z.h4_close<z.prior7d_high) & ((z.h4_high-z.prior7d_high)>=.10*rng)
        lo_sweep=(z.h4_low<z.prior7d_low) & (z.h4_close>z.prior7d_low) & ((z.prior7d_low-z.h4_low)>=.10*rng)
        # ambiguous two-sided sweep is excluded
        flag=(hi_sweep ^ lo_sweep)
        z["impulse_dir"]=np.where(hi_sweep,1.0,np.where(lo_sweep,-1.0,np.nan))
    else:
        raise ValueError(family)
    q=z[flag.fillna(False)].copy().sort_values("event_time")
    # 4h cooldown: H4 bars are already 4h apart; keep exact >=4h separation
    keep=[]; last=None
    for idx,r in q.iterrows():
        t=pd.Timestamp(r.event_time)
        if last is None or (t-last)>=pd.Timedelta(hours=4):
            keep.append(idx); last=t
    return q.loc[keep].copy()


def make_event_frame(x,hrows,family):
    rows=[]
    n=len(x)
    for _,hr in hrows.iterrows():
        i=int(hr.event_i); d=float(hr.impulse_dir)
        if i<10 or i+L5.H24>=n or not np.isfinite(d) or d==0: continue
        entry=float(x.btc_open.iloc[i+1]); exitp=float(x.btc_close.iloc[i+L5.H24])
        if not np.isfinite(entry) or entry<=0 or not np.isfinite(exitp): continue
        r={k:(d if k=="impulse_dir" else float(x[k].iloc[i])) for k in L5.CORE}
        r.update(event_i=i,event_time=x.index[i],split=split_year(x.index[i]),event_open=float(hr.h4_open),event_high=float(hr.h4_high),event_low=float(hr.h4_low),event_close=float(hr.h4_close),common_exit=exitp,parent_family=family)
        r["raw_24h"]=exitp/entry-1.0; r["cont_24h"]=d*r["raw_24h"]; r["rev_24h"]=-d*r["raw_24h"]
        rows.append(r)
    return pd.DataFrame(rows).replace([np.inf,-np.inf],np.nan)


def canonical_selected(x,mc,mr,cut):
    e=L14.make_events_q(x,.975)
    e=e[e.event_time<pd.Timestamp("2026-09-01",tz="UTC")].copy()
    e=L14.score_events(e,mc,mr)
    return e[(e.router_side=="REV")&(e.router_conf>=cut)].copy().sort_values("event_time")


def remove_canonical_overlap(sel,canon):
    if len(sel)==0 or len(canon)==0:
        return sel.copy(),0
    ct=pd.to_datetime(canon.event_time,utc=True).astype("int64").to_numpy()
    keep=[]; removed=0; day=24*3600*10**9
    for idx,r in sel.iterrows():
        t=int(pd.Timestamp(r.event_time).value)
        if np.min(np.abs(ct-t))<=day:
            removed+=1
        else:
            keep.append(idx)
    return sel.loc[keep].copy(),removed


def score_filter_execute(x,e,mc,mr,cut,canon,family):
    if len(e)==0: return pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),0
    scored=L14.score_events(e,mc,mr)
    pre=scored[(scored.router_side=="REV")&(scored.router_conf>=cut)].copy().sort_values("event_time")
    post,removed=remove_canonical_overlap(pre,canon)
    s=L14.execute_virtual(x,post)
    if len(s): s["parent_family"]=family
    return s,pre,post,removed


def summarize(name,s,seed0):
    rows=[]
    for j,(w,(a,b,m)) in enumerate(WINS.items()):
        r=L14.window_summary(name,s,w,a,b,m,seed0+j*37); r["family"]=name; rows.append(r)
    return pd.DataFrame(rows)


def hist_summary(name,s,seed0):
    rows=[]
    for j,(w,(a,b,m)) in enumerate(HIST_WINS.items()):
        r=L14.window_summary(name,s,w,a,b,m,seed0+j*41); r["family"]=name; rows.append(r)
    return pd.DataFrame(rows)


def getrow(tab,fam,w):
    q=tab[(tab.family==fam)&(tab.window==w)]
    return q.iloc[0] if len(q) else None


def family_verdict(tab,fam):
    a=getrow(tab,fam,"2025_H2"); b=getrow(tab,fam,"2026_JAN_JUL"); p=getrow(tab,fam,"POOLED_RECENT")
    gates={
        "h2_selected_ge_10":int(a.selected_rev)>=10,
        "y2026_selected_ge_10":int(b.selected_rev)>=10,
        "h2_real_fills_ge_5":int(a.real_fills)>=5,
        "y2026_real_fills_ge_5":int(b.real_fills)>=5,
        "mean_R_positive_both":bool(np.isfinite(a.mean_R_per_fill) and np.isfinite(b.mean_R_per_fill) and a.mean_R_per_fill>0 and b.mean_R_per_fill>0),
        "pf_gt_12_both":bool(np.isfinite(a.profit_factor) and np.isfinite(b.profit_factor) and a.profit_factor>1.2 and b.profit_factor>1.2),
        "cumR_positive_both":float(a.cum_R)>0 and float(b.cum_R)>0,
        "pooled_freq_ge_075":float(p.fills_per_month)>=.75,
        "pooled_loeo_positive":bool(np.isfinite(p.worst_loeo_remaining_R) and p.worst_loeo_remaining_R>0),
        "pooled_maxdd_le_4R":float(p.max_dd_R)<=4.0,
    }
    n=int(sum(bool(v) for v in gates.values()))
    critical=["mean_R_positive_both","pf_gt_12_both","cumR_positive_both"]
    status="PROMISING_ORTHOGONAL_H4_DISCOVERY" if n>=8 and all(gates[k] for k in critical) else "REJECT_ORTHOGONAL_H4_DISCOVERY"
    return dict(status=status,gates_passed=n,gates_total=len(gates),gates=gates)


def union_summary(canon_s,fam_s,fam):
    rows=[]
    for w,(a,b,m) in WINS.items():
        if w=="AUG2026_REUSED_AUDIT": continue
        c=canon_s[(canon_s.event_time>=a)&(canon_s.event_time<b)].copy(); c["src"]="CANON"
        f=fam_s[(fam_s.event_time>=a)&(fam_s.event_time<b)].copy(); f["src"]=fam
        z=pd.concat([c,f],ignore_index=True).sort_values("event_time")
        rr=z.real_R.to_numpy(float) if len(z) else np.array([])
        rf=z[z.real_fill] if len(z) else z
        famfills=int((rf.src==fam).sum()) if len(rf) else 0
        rows.append(dict(family=fam,window=w,real_fills=int(len(rf)),fills_per_month=float(len(rf)/m),incremental_h4_fills=famfills,h4_fill_share=float(famfills/len(rf)) if len(rf) else np.nan,cum_R=float(rr.sum()) if len(rr) else 0.0,mean_R_per_fill=float(rf.real_R.mean()) if len(rf) else np.nan,profit_factor=L14.pf(rr) if len(rr) else np.nan,max_dd_R=L14.maxdd(rr) if len(rr) else 0.0))
    return rows


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def report(tab,hist,status,counts,union,cut):
    lines=[f"# {LAB}","",f"Role: strict non-overlap H4 parent-family discovery outside ±24h of frozen canonical `P975_T25`; frozen `T25 + VF1 + LIMIT0.5/SL1/TP1.5/5bps`.","",f"Frozen T25 cutoff: **{cut:.6f}**","","## Orthogonality census","","| Family | Raw H4 parents | T25 REV pre-filter | Removed ±24h canonical | Non-overlap selected | Removal share |","|---|---:|---:|---:|---:|---:|"]
    for c in counts:
        share=c['removed']/c['pre'] if c['pre'] else np.nan
        lines.append(f"| {c['family']} | {c['raw']} | {c['pre']} | {c['removed']} | {c['post']} | {share*100:.1f}% |" if np.isfinite(share) else f"| {c['family']} | {c['raw']} | 0 | 0 | 0 | — |")
    lines += ["","## Non-overlap H4 family economics","","| Family | Window | Selected | Mature | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | LOEO worst |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for fam in FAMILIES:
        for w in ["2025_H2","2026_JAN_JUL","POOLED_RECENT","AUG2026_REUSED_AUDIT"]:
            r=getrow(tab,fam,w)
            if r.real_fills:
                lines.append(f"| {fam} | {w} | {int(r.selected_rev)} | {int(r.mature_admit)} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {r.mean_R_per_fill:+.3f} | {r.cum_R:+.2f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} | {r.worst_loeo_remaining_R:+.2f} |")
            else:
                lines.append(f"| {fam} | {w} | {int(r.selected_rev)} | {int(r.mature_admit)} | 0 | 0.00 | — | +0.00 | — | {r.max_dd_R:.2f} | — |")
    lines += ["","## Discovery verdicts"]
    for fam in FAMILIES:
        z=status[fam]; lines.append(f"- **{fam}: {z['status']} ({z['gates_passed']}/{z['gates_total']})**")
        for k,v in z['gates'].items(): lines.append(f"  - {'PASS' if v else 'FAIL'} `{k}`")
    lines += ["","## Canonical + H4 descriptive union","","| H4 family added | Window | Real fills | Fills/mo | Incremental H4 fills | H4 fill share | Cum R | Mean R/fill | PF | DD R |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in union:
        lines.append(f"| {r['family']} | {r['window']} | {r['real_fills']} | {r['fills_per_month']:.2f} | {r['incremental_h4_fills']} | {r['h4_fill_share']*100:.1f}% | {r['cum_R']:+.2f} | {r['mean_R_per_fill']:+.3f} | {fmtpf(r['profit_factor'])} | {r['max_dd_R']:.2f} |" if r['real_fills'] else f"| {r['family']} | {r['window']} | 0 | 0.00 | 0 | — | +0.00 | — | — | 0.00 |")
    lines += ["","## Historical descriptive audit","","| Family | Window | Fills | Cum R | Mean R/fill | PF | DD R |","|---|---|---:|---:|---:|---:|---:|"]
    for _,r in hist.iterrows():
        lines.append(f"| {r.family} | {r.window} | {int(r.real_fills)} | {r.cum_R:+.2f} | {r.mean_R_per_fill:+.3f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} |" if r.real_fills else f"| {r.family} | {r.window} | 0 | +0.00 | — | — | 0.00 |")
    lines += ["","## Status","- LAB016 is discovery-only; even a promising H4 family needs its own frozen replication LAB.","- 2025H2/2026 are reused research windows, not fresh holdouts.","- August 2026 is consumed/reused audit only.","- No live allocation is authorized."]
    return "\n".join(lines)+"\n"


def main():
    x,_,_=L7.load_panel()
    mc,mr,meta,cuts=L14.freeze_canonical_router(x); cut=cuts["T25"]
    canon_sel=canonical_selected(x,mc,mr,cut)
    canon_s=L14.execute_virtual(x,canon_sel)
    h=h4_table(x)
    tabs=[]; hists=[]; counts=[]; status={}; unions=[]; streams=[]
    for n,fam in enumerate(FAMILIES):
        hr=family_h4_rows(h,fam); e=make_event_frame(x,hr,fam)
        s,pre,post,removed=score_filter_execute(x,e,mc,mr,cut,canon_sel,fam)
        t=summarize(fam,s,1000+n*100); ht=hist_summary(fam,s,2000+n*100)
        tabs.append(t); hists.append(ht); streams.append(s)
        counts.append(dict(family=fam,raw=len(e),pre=len(pre),removed=removed,post=len(post)))
        status[fam]=family_verdict(t,fam)
        unions += union_summary(canon_s,s,fam)
        e.to_csv(OUT/f"{fam}_all_parents.csv",index=False)
        pre.to_csv(OUT/f"{fam}_t25_pre_orthogonality.csv",index=False)
        post.to_csv(OUT/f"{fam}_nonoverlap_selected.csv",index=False)
        s.to_csv(OUT/f"{fam}_vf1_stream.csv",index=False)
    tab=pd.concat(tabs,ignore_index=True); hist=pd.concat(hists,ignore_index=True); union=pd.DataFrame(unions); census=pd.DataFrame(counts)
    tab.to_csv(OUT/"family_recent_summary.csv",index=False); hist.to_csv(OUT/"family_historical_summary.csv",index=False); union.to_csv(OUT/"canonical_plus_h4_union.csv",index=False); census.to_csv(OUT/"orthogonality_census.csv",index=False)
    verdict={"families":status,"t25_cutoff":cut,"canonical_selected":len(canon_sel),"census":counts}
    (OUT/"verdict.json").write_text(json.dumps(verdict,indent=2,allow_nan=True),encoding="utf-8")
    rep=report(tab,hist,status,counts,unions,cut); (OUT/"REPORT.md").write_text(rep,encoding="utf-8")
    print(json.dumps(verdict,indent=2,allow_nan=True)); print(rep)

if __name__=="__main__": main()
