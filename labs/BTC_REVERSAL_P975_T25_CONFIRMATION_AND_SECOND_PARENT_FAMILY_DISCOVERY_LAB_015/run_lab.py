#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_P975_T25_CONFIRMATION_AND_SECOND_PARENT_FAMILY_DISCOVERY_LAB_015"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SEED=20260905

SRC14=HERE.parent/"BTC_REVERSAL_VF1_MATURE_SELECTOR_AND_PARENT_EVENT_BREADTH_TRANSFER_LAB_014"/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab014",SRC14)
L14=importlib.util.module_from_spec(spec); spec.loader.exec_module(L14)
L7=L14.L7; L6=L14.L6; L5=L14.L5

CONFIRM_CELL="P975_T25"
DISCOVERY_FAMILIES=["RANGE60_EXTREME","VOLUME60_SHOCK","PERSISTENT60_MOVE"]
RECENT_WINS={
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


def build_thresholds(x):
    w=L5.ROLL
    abs60=x.btc_lr60.abs()
    canon=abs60.rolling(w,min_periods=w//2).quantile(.975).shift(1)
    q95=abs60.rolling(w,min_periods=w//2).quantile(.95).shift(1)
    q90=abs60.rolling(w,min_periods=w//2).quantile(.90).shift(1)
    range60=(x.btc_high.rolling(4).max()-x.btc_low.rolling(4).min())/x.btc_close
    range975=range60.rolling(w,min_periods=w//2).quantile(.975).shift(1)
    vol60=x.btc_quote_volume.rolling(4).sum()
    vol975=vol60.rolling(w,min_periods=w//2).quantile(.975).shift(1)
    r15=x.btc_lr15
    den=r15.abs().rolling(4).sum()
    eff=(r15.rolling(4).sum().abs()/den.replace(0,np.nan))
    poscnt=(r15>0).rolling(4).sum(); negcnt=(r15<0).rolling(4).sum()
    return dict(canon=canon,q95=q95,q90=q90,range60=range60,range975=range975,vol60=vol60,vol975=vol975,eff=eff,poscnt=poscnt,negcnt=negcnt)


def custom_events(x,family,thr):
    z=x.copy()
    abs60=z.btc_lr60.abs(); direction=np.sign(z.btc_lr60).astype(float)
    below=abs60 < thr["canon"]
    if family=="RANGE60_EXTREME":
        flag=(thr["range60"]>=thr["range975"]) & below
    elif family=="VOLUME60_SHOCK":
        flag=(thr["vol60"]>=thr["vol975"]) & (abs60>=thr["q90"]) & below
    elif family=="PERSISTENT60_MOVE":
        same=((direction>0)&(thr["poscnt"]>=3)) | ((direction<0)&(thr["negcnt"]>=3))
        flag=(abs60>=thr["q95"]) & below & (thr["eff"]>=.75) & same
    else:
        raise ValueError(family)
    flag=flag.fillna(False) & direction.ne(0)
    z["impulse_raw"]=flag
    z["impulse_dir"]=direction
    e=L5.make_events(z)
    if len(e): e["parent_family"]=family
    return e


def score_select_execute(x,e,mc,mr,cut,family):
    if len(e)==0:
        return pd.DataFrame(),pd.DataFrame()
    q=e[e.event_time<pd.Timestamp("2026-09-01",tz="UTC")].copy()
    q=L14.score_events(q,mc,mr)
    sel=q[(q.router_side=="REV")&(q.router_conf>=cut)].copy()
    sel["parent_family"]=family
    s=L14.execute_virtual(x,sel)
    if len(s): s["parent_family"]=family
    return s,sel


def summarize_stream(name,s,windows,seed0):
    rows=[]
    for j,(w,(a,b,m)) in enumerate(windows.items()):
        r=L14.window_summary(name,s,w,a,b,m,seed0+j*31)
        r["family"]=name
        rows.append(r)
    return pd.DataFrame(rows)


def row(tab,fam,window):
    q=tab[(tab.family==fam)&(tab.window==window)]
    return q.iloc[0] if len(q) else None


def confirm_verdict(tab):
    a=row(tab,CONFIRM_CELL,"2025_H2"); b=row(tab,CONFIRM_CELL,"2026_JAN_JUL"); p=row(tab,CONFIRM_CELL,"POOLED_RECENT")
    gates={
        "h2_fills_ge_10":int(a.real_fills)>=10,
        "y2026_fills_ge_10":int(b.real_fills)>=10,
        "h2_mean_R_ge_040":float(a.mean_R_per_fill)>=.40,
        "y2026_mean_R_ge_040":float(b.mean_R_per_fill)>=.40,
        "pf_ge_2_both":float(a.profit_factor)>=2.0 and float(b.profit_factor)>=2.0,
        "cumR_positive_both":float(a.cum_R)>0 and float(b.cum_R)>0,
        "maxdd_le_25_both":float(a.max_dd_R)<=2.5 and float(b.max_dd_R)<=2.5,
        "pooled_cumR_ge_12":float(p.cum_R)>=12.0,
        "pooled_freq_ge_15pm":float(p.fills_per_month)>=1.5,
        "pooled_all_loeo_positive":float(p.worst_loeo_remaining_R)>0,
    }
    n=int(sum(gates.values()))
    critical=["h2_mean_R_ge_040","y2026_mean_R_ge_040","pf_ge_2_both","cumR_positive_both"]
    if n>=9 and all(gates[k] for k in critical): v="PASS_CONFIRM_P975_T25"
    elif n>=7 and float(a.cum_R)>0 and float(b.cum_R)>0 and float(a.profit_factor)>1.5 and float(b.profit_factor)>1.5: v="WATCH_CONFIRM_P975_T25"
    else: v="FAIL_CONFIRM_P975_T25"
    return {"verdict":v,"gates_passed":n,"gates_total":len(gates),"gates":gates}


def discovery_status(tab,fam):
    a=row(tab,fam,"2025_H2"); b=row(tab,fam,"2026_JAN_JUL"); p=row(tab,fam,"POOLED_RECENT")
    gates={
        "h2_fills_ge_6":int(a.real_fills)>=6,
        "y2026_fills_ge_7":int(b.real_fills)>=7,
        "mean_positive_both":bool(np.isfinite(a.mean_R_per_fill) and np.isfinite(b.mean_R_per_fill) and a.mean_R_per_fill>0 and b.mean_R_per_fill>0),
        "pf_gt_12_both":bool(np.isfinite(a.profit_factor) and np.isfinite(b.profit_factor) and a.profit_factor>1.2 and b.profit_factor>1.2),
        "cum_positive_both":float(a.cum_R)>0 and float(b.cum_R)>0,
        "pooled_freq_ge_075":float(p.fills_per_month)>=.75,
        "pooled_loeo_positive":bool(np.isfinite(p.worst_loeo_remaining_R) and p.worst_loeo_remaining_R>0),
    }
    promising=all(gates.values())
    return {"status":"PROMISING_DISCOVERY" if promising else "REJECT_DISCOVERY","gates":gates,"gates_passed":int(sum(gates.values())),"gates_total":len(gates)}


def overlap_stats(family_sel,canon_sel,fam):
    out={"family":fam,"selected_family":len(family_sel),"canonical_selected":len(canon_sel),"exact_timestamp_overlap":0,"within_24h_overlap":0,"within_24h_share":np.nan}
    if len(family_sel)==0 or len(canon_sel)==0: return out
    ct=np.array(pd.to_datetime(canon_sel.event_time,utc=True).astype("int64"))
    exact=0; near=0; day=24*3600*10**9
    for t in pd.to_datetime(family_sel.event_time,utc=True).astype("int64"):
        d=np.min(np.abs(ct-int(t)))
        if d==0: exact+=1
        if d<=day: near+=1
    out.update(exact_timestamp_overlap=exact,within_24h_overlap=near,within_24h_share=near/len(family_sel))
    return out


def combined_union_summary(canon_s,fam_s,fam):
    rows=[]
    for w,(a,b,m) in RECENT_WINS.items():
        if w=="AUG2026_REUSED_AUDIT": continue
        c=canon_s[(canon_s.event_time>=a)&(canon_s.event_time<b)].copy(); c["src"]="CANON"
        f=fam_s[(fam_s.event_time>=a)&(fam_s.event_time<b)].copy(); f["src"]=fam
        z=pd.concat([c,f],ignore_index=True).sort_values(["event_time","src"])
        if len(z)==0:
            rows.append(dict(family=fam,window=w,union_events=0,union_real_fills=0,fills_per_month=0.0,cum_R=0.0,mean_R_per_fill=np.nan,profit_factor=np.nan,max_dd_R=0.0))
            continue
        # canonical priority on exact event time
        z["priority"]=(z.src!="CANON").astype(int)
        z=z.sort_values(["event_time","priority"]).drop_duplicates("event_time",keep="first").sort_values("event_time")
        rr=z.real_R.to_numpy(float); rf=z.loc[z.real_fill,"real_R"].to_numpy(float)
        rows.append(dict(family=fam,window=w,union_events=len(z),union_real_fills=int(z.real_fill.sum()),fills_per_month=float(z.real_fill.sum()/m),cum_R=float(rr.sum()),mean_R_per_fill=float(rf.mean()) if len(rf) else np.nan,profit_factor=L14.pf(rr),max_dd_R=L14.maxdd(rr)))
    return rows


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def report(confirm_tab,hist_tab,disc_tab,disc_status,overlap,union,cv,cut):
    lines=[f"# {LAB}","",f"## Part A — P975_T25 confirmation","",f"**Verdict:** **{cv['verdict']}**  ",f"Frozen canonical T25 cutoff: **{cut:.6f}**","","| Window | Selected REV | Mature | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | LOEO worst |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for w in ["2025_H2","2026_JAN_JUL","POOLED_RECENT","AUG2026_REUSED_AUDIT"]:
        r=row(confirm_tab,CONFIRM_CELL,w)
        lines.append(f"| {w} | {int(r.selected_rev)} | {int(r.mature_admit)} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {r.mean_R_per_fill:+.3f} | {r.cum_R:+.2f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} | {r.worst_loeo_remaining_R:+.2f} |" if r.real_fills else f"| {w} | {int(r.selected_rev)} | {int(r.mature_admit)} | 0 | 0.00 | — | +0.00 | — | 0.00 | — |")
    lines += ["","### Part A gates"]
    for k,z in cv["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {cv['gates_passed']}/{cv['gates_total']} → {cv['verdict']}**","","### Historical descriptive audit","","| Window | Fills | Cum R | Mean R/fill | PF | DD R |","|---|---:|---:|---:|---:|---:|"]
    for _,r in hist_tab.iterrows():
        lines.append(f"| {r.window} | {int(r.real_fills)} | {r.cum_R:+.2f} | {r.mean_R_per_fill:+.3f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} |" if r.real_fills else f"| {r.window} | 0 | +0.00 | — | — | 0.00 |")
    lines += ["","## Part B — second parent-family discovery","","Discovery is non-promotional; a positive family needs its own replication LAB.","","| Family | Window | Selected REV | Mature | Fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | LOEO worst |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for fam in DISCOVERY_FAMILIES:
        for w in ["2025_H2","2026_JAN_JUL","POOLED_RECENT","AUG2026_REUSED_AUDIT"]:
            r=row(disc_tab,fam,w)
            lines.append(f"| {fam} | {w} | {int(r.selected_rev)} | {int(r.mature_admit)} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {r.mean_R_per_fill:+.3f} | {r.cum_R:+.2f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} | {r.worst_loeo_remaining_R:+.2f} |" if r.real_fills else f"| {fam} | {w} | {int(r.selected_rev)} | {int(r.mature_admit)} | 0 | 0.00 | — | +0.00 | — | {r.max_dd_R:.2f} | — |")
    lines += ["","### Discovery verdicts"]
    for fam in DISCOVERY_FAMILIES:
        z=disc_status[fam]; lines.append(f"- **{fam}: {z['status']} ({z['gates_passed']}/{z['gates_total']})**")
        for k,v in z["gates"].items(): lines.append(f"  - {'PASS' if v else 'FAIL'} `{k}`")
    lines += ["","### Overlap with canonical P975_T25 selected events","","| Family | Selected | Exact overlap | Within ±24h | Share |","|---|---:|---:|---:|---:|"]
    for _,r in overlap.iterrows():
        sh=f"{r.within_24h_share*100:.1f}%" if np.isfinite(r.within_24h_share) else "—"
        lines.append(f"| {r.family} | {int(r.selected_family)} | {int(r.exact_timestamp_overlap)} | {int(r.within_24h_overlap)} | {sh} |")
    lines += ["","### Descriptive canonical + discovery union","","| Family added | Window | Real fills | Fills/mo | Cum R | Mean R/fill | PF | DD R |","|---|---|---:|---:|---:|---:|---:|---:|"]
    for _,r in union.iterrows():
        lines.append(f"| {r.family} | {r.window} | {int(r.union_real_fills)} | {r.fills_per_month:.2f} | {r.cum_R:+.2f} | {r.mean_R_per_fill:+.3f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} |" if r.union_real_fills else f"| {r.family} | {r.window} | 0 | 0.00 | +0.00 | — | — | 0.00 |")
    lines += ["","## Status","- Part A uses reused research windows; it is a formal re-freeze, not fresh prospective confirmation.","- Part B is discovery-only and cannot become canonical from this LAB.","- August 2026 remains consumed/reused audit only.","- No live allocation is authorized by LAB015 alone."]
    return "\n".join(lines)+"\n"


def main():
    x,hf,ff=L7.load_panel()
    mc,mr,meta,cuts=L14.freeze_canonical_router(x)
    cut=cuts["T25"]

    # Part A exact frozen P975_T25
    canon_s,canon_all=L14.build_cell(x,"P975",.975,"T25",cut,mc,mr)
    confirm_tab=summarize_stream(CONFIRM_CELL,canon_s,RECENT_WINS,1000)
    hist_tab=summarize_stream(CONFIRM_CELL,canon_s,HIST_WINS,2000)
    cv=confirm_verdict(confirm_tab)

    # selected canonical stream before VF1 for overlap diagnostics
    canon_sel=canon_all[(canon_all.router_side=="REV")&(canon_all.router_conf>=cut)].copy()

    thr=build_thresholds(x)
    disc_rows=[]; overlap_rows=[]; union_rows=[]; disc_status={}; family_streams={}; family_selected={}
    for j,fam in enumerate(DISCOVERY_FAMILIES):
        e=custom_events(x,fam,thr)
        s,sel=score_select_execute(x,e,mc,mr,cut,fam)
        family_streams[fam]=s; family_selected[fam]=sel
        t=summarize_stream(fam,s,RECENT_WINS,3000+j*200)
        disc_rows.append(t)
        overlap_rows.append(overlap_stats(sel,canon_sel,fam))
        union_rows.extend(combined_union_summary(canon_s,s,fam))

    disc_tab=pd.concat(disc_rows,ignore_index=True) if disc_rows else pd.DataFrame()
    for fam in DISCOVERY_FAMILIES: disc_status[fam]=discovery_status(disc_tab,fam)
    overlap=pd.DataFrame(overlap_rows); union=pd.DataFrame(union_rows)

    verdict={"part_a":cv,"part_b":disc_status,"canonical_t25_cutoff":cut,"historical_files":hf,"fresh_daily_files":ff}
    confirm_tab.to_csv(OUT/"part_a_confirmation_summary.csv",index=False)
    hist_tab.to_csv(OUT/"part_a_historical_audit.csv",index=False)
    canon_s.to_csv(OUT/"part_a_p975_t25_signal_stream.csv",index=False)
    disc_tab.to_csv(OUT/"part_b_discovery_summary.csv",index=False)
    overlap.to_csv(OUT/"part_b_overlap.csv",index=False)
    union.to_csv(OUT/"part_b_union_summary.csv",index=False)
    for fam,s in family_streams.items(): s.to_csv(OUT/f"discovery_{fam}_signal_stream.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps(verdict,indent=2,allow_nan=True),encoding="utf-8")
    rep=report(confirm_tab,hist_tab,disc_tab,disc_status,overlap,union,cv,cut)
    (OUT/"REPORT.md").write_text(rep,encoding="utf-8")
    print(json.dumps(verdict,indent=2,allow_nan=True)); print(rep)

if __name__=="__main__": main()
