#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_H4_PIVOT_PARENT_TO_M15_CHILD_VIRTUAL_FILL_AND_EXECUTION_BRIDGE_LAB_017"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SEED=20260905
COST_BPS=5.0
RR=1.5
LIMIT_MULT=.50
TTL=4
CHILD_MAX_BARS=48  # 12h on M15
PRIMARY="BREAK_CONFIRM_12H"
AUDITS=["COLOR_ONLY_12H","TWO_BAR_CONFIRM_12H"]
RULES=[PRIMARY]+AUDITS
PARENT_FAMILY="H4_7D_PIVOT_SWEEP_RECLAIM"

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

SRC16=HERE.parent/"BTC_REVERSAL_ORTHOGONAL_H4_PARENT_AND_NONOVERLAP_FAMILY_LAB_016"/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab016",SRC16)
L16=importlib.util.module_from_spec(spec); spec.loader.exec_module(L16)
L15=L16.L15; L14=L16.L14; L7=L16.L7; L6=L16.L6; L5=L16.L5


def pf(a):
    a=np.asarray(a,float); pos=float(a[a>0].sum()); neg=float(-a[a<0].sum())
    if neg==0: return np.inf if pos>0 else np.nan
    return pos/neg

def maxdd(a):
    return float(L6.max_dd_r(np.asarray(a,float))) if len(a) else 0.0

def maxloss(a):
    return int(L6.max_consecutive_loss(np.asarray(a,float))) if len(a) else 0


def frozen_parent_set(x):
    mc,mr,meta,cuts=L14.freeze_canonical_router(x)
    cut=float(cuts["T25"])
    canon=L16.canonical_selected(x,mc,mr,cut)
    h=L16.h4_table(x)
    raw=L16.family_h4_rows(h,PARENT_FAMILY)
    e=L16.make_event_frame(x,raw,PARENT_FAMILY)
    scored=L14.score_events(e,mc,mr)
    pre=scored[(scored.router_side=="REV")&(scored.router_conf>=cut)].copy().sort_values("event_time")
    post,removed=L16.remove_canonical_overlap(pre,canon)
    post=post.sort_values("event_time").reset_index(drop=True)
    return post,pre,raw,canon,mc,mr,cut,removed


def child_condition(x,k,d,rule):
    op=float(x.btc_open.iloc[k]); cl=float(x.btc_close.iloc[k])
    if not np.isfinite(op) or not np.isfinite(cl): return False
    if rule=="COLOR_ONLY_12H":
        return bool(cl<op) if d>0 else bool(cl>op)
    if rule=="BREAK_CONFIRM_12H":
        if k<1: return False
        if d>0:
            return bool(cl<op and cl<float(x.btc_low.iloc[k-1]))
        return bool(cl>op and cl>float(x.btc_high.iloc[k-1]))
    if rule=="TWO_BAR_CONFIRM_12H":
        if k<2: return False
        c0=float(x.btc_close.iloc[k-2]); c1=float(x.btc_close.iloc[k-1]); c2=cl
        if d>0:
            return bool(c2<c1<c0)
        return bool(c2>c1>c0)
    raise ValueError(rule)


def make_children(x,parents,rule):
    rows=[]
    n=len(x)
    for pid,p in parents.iterrows():
        pi=int(p.event_i); d=float(p.impulse_dir)
        exit_i=min(pi+L5.H24,n-1)
        found=None
        for k in range(pi+1,min(pi+1+CHILD_MAX_BARS,exit_i+1,n)):
            if child_condition(x,k,d,rule):
                found=k; break
        if found is None: continue
        k=int(found)
        hi=float(x.btc_high.iloc[k]); lo=float(x.btc_low.iloc[k]); cl=float(x.btc_close.iloc[k]); op=float(x.btc_open.iloc[k])
        rng=hi-lo
        if not np.isfinite(rng) or rng<=0: continue
        rows.append(dict(
            parent_id=int(pid), parent_time=pd.Timestamp(p.event_time), parent_i=pi,
            signal_time=pd.Timestamp(x.index[k]), signal_i=k,
            event_time=pd.Timestamp(p.event_time), event_i=k,
            impulse_dir=d, split=p.split, child_rule=rule,
            event_open=op,event_high=hi,event_low=lo,event_close=cl,
            child_range=rng,parent_exit_i=exit_i,
            router_conf=float(p.router_conf),p_rev=float(p.p_rev),p_cont=float(p.p_cont)
        ))
    return pd.DataFrame(rows).sort_values("signal_time").reset_index(drop=True) if rows else pd.DataFrame()


def execute_child_virtual(x,children):
    if len(children)==0: return children.copy()
    rows=[]; n=len(x)
    for idx,r in children.iterrows():
        i=int(r.signal_i); pi=int(r.parent_i); d=float(r.impulse_dir); rng=float(r.child_range)
        entry=float(r.event_close+d*LIMIT_MULT*rng)
        exit_i=min(int(r.parent_exit_i),n-1)
        fill=None
        stop_scan=min(i+1+TTL,exit_i+1,n)
        for k in range(i+1,stop_scan):
            hi=float(x.btc_high.iloc[k]); lo=float(x.btc_low.iloc[k])
            if (d>0 and hi>=entry) or (d<0 and lo<=entry):
                fill=k; break
        q=r.to_dict(); q["source_row"]=int(idx); q["entry"]=entry
        if fill is None:
            q.update(filled=False,fill_time=pd.NaT,fill_i=np.nan,outcome="NO_FILL",gross_R=0.0,cost_R=0.0,signal_net_R=0.0,stop_frac=float(rng/entry),exit_time=pd.NaT)
            rows.append(q); continue
        sl=entry+d*rng; tp=entry-d*RR*rng
        outcome="TIME_EXIT"; gross=np.nan; actual_exit=exit_i
        for k in range(fill,exit_i+1):
            hi=float(x.btc_high.iloc[k]); lo=float(x.btc_low.iloc[k])
            if d>0:
                hit_sl=hi>=sl; hit_tp=lo<=tp
            else:
                hit_sl=lo<=sl; hit_tp=hi>=tp
            if hit_sl and hit_tp:
                outcome="SL"; gross=-1.0; actual_exit=k; break
            if hit_sl:
                outcome="SL"; gross=-1.0; actual_exit=k; break
            if hit_tp:
                outcome="TP"; gross=RR; actual_exit=k; break
        if outcome=="TIME_EXIT":
            px=float(x.btc_close.iloc[exit_i]); gross=float(-d*(px-entry)/rng)
        stop_frac=float(rng/entry); cost=float((COST_BPS/10000.0)/stop_frac)
        q.update(filled=True,fill_time=pd.Timestamp(x.index[fill]),fill_i=int(fill),outcome=outcome,gross_R=float(gross),cost_R=cost,signal_net_R=float(gross-cost),stop_frac=stop_frac,exit_time=pd.Timestamp(x.index[actual_exit]))
        rows.append(q)
    s=pd.DataFrame(rows).sort_values("signal_time").reset_index(drop=True)
    gaps=s.signal_time.diff().dt.total_seconds().div(86400.0)
    s["episode_7d"]=(gaps.isna() | (gaps>7.0)).cumsum().astype(int)
    s["prior_virtual_fills"]=0
    for eid,q in s.groupby("episode_7d",sort=True):
        prior=[]
        for idx,r in q.sort_values("signal_time").iterrows():
            t=pd.Timestamp(r.signal_time); nprior=0
            for pr in prior:
                if bool(pr["filled"]) and pd.notna(pr["fill_time"]) and pd.Timestamp(pr["fill_time"])<t:
                    nprior+=1
            s.loc[idx,"prior_virtual_fills"]=nprior
            prior.append(r.to_dict())
    s["vf1_mature"]=s.prior_virtual_fills>=1
    s["real_fill"]=s.vf1_mature & s.filled
    s["real_R"]=np.where(s.vf1_mature,s.signal_net_R,0.0)
    return s


def episode_stats(d):
    if len(d)==0: return 0,0,0,np.nan,np.nan
    ep=[]
    for eid,q in d.groupby("episode_7d",sort=True):
        ep.append(float(q.real_R.sum()))
    arr=np.asarray(ep,float); total=float(d.real_R.sum())
    worst=float(arr.min()) if len(arr) else np.nan
    loeo=float(np.min(total-arr)) if len(arr) else np.nan
    return len(arr),int((arr>0).sum()),int((arr<0).sum()),worst,loeo


def summarize_rule(rule,parents,s,windows):
    rows=[]
    for w,(a,b,months) in windows.items():
        p=parents[(parents.event_time>=a)&(parents.event_time<b)].copy()
        d=s[(s.parent_time>=a)&(s.parent_time<b)].copy().sort_values("signal_time") if len(s) else s.copy()
        child_n=len(d); parent_n=len(p); found_rate=float(child_n/parent_n) if parent_n else np.nan
        vr=d[d.filled] if len(d) else d
        rf=d[d.real_fill] if len(d) else d
        rr=d.real_R.to_numpy(float) if len(d) else np.array([])
        rrf=rf.real_R.to_numpy(float) if len(rf) else np.array([])
        ne,pe,nege,worst,loeo=episode_stats(d)
        rows.append(dict(rule=rule,window=w,eligible_parents=parent_n,children=child_n,child_found_rate=found_rate,virtual_fills=int(len(vr)),virtual_fill_rate=float(len(vr)/child_n) if child_n else np.nan,mature_admit=int(d.vf1_mature.sum()) if len(d) else 0,real_fills=int(len(rf)),fills_per_month=float(len(rf)/months),mean_R_per_fill=float(rrf.mean()) if len(rrf) else np.nan,cum_R=float(rr.sum()) if len(rr) else 0.0,profit_factor=pf(rr),max_dd_R=maxdd(rr),max_consecutive_losses=maxloss(rr),episodes=ne,positive_episodes=pe,negative_episodes=nege,worst_episode_R=worst,worst_loeo_remaining_R=loeo))
    return pd.DataFrame(rows)


def canonical_stream(x,mc,mr,cut):
    e=L14.make_events_q(x,.975)
    e=e[e.event_time<pd.Timestamp("2026-09-01",tz="UTC")].copy()
    e=L14.score_events(e,mc,mr)
    sel=e[(e.router_side=="REV")&(e.router_conf>=cut)].copy()
    return L14.execute_virtual(x,sel)


def union_summary(canon_s,child_s):
    rows=[]
    for w,(a,b,months) in WINS.items():
        if w=="AUG2026_REUSED_AUDIT": continue
        c=canon_s[(canon_s.event_time>=a)&(canon_s.event_time<b)&(canon_s.real_fill)].copy()
        c["src"]="CANON"; c["trade_time"]=c.fill_time
        f=child_s[(child_s.parent_time>=a)&(child_s.parent_time<b)&(child_s.real_fill)].copy()
        f["src"]="H4_M15_CHILD"; f["trade_time"]=f.fill_time
        z=pd.concat([c[["src","trade_time","real_R"]],f[["src","trade_time","real_R"]]],ignore_index=True).sort_values("trade_time")
        r=z.real_R.to_numpy(float) if len(z) else np.array([])
        rows.append(dict(window=w,real_fills=len(z),fills_per_month=float(len(z)/months),canonical_fills=int((z.src=="CANON").sum()) if len(z) else 0,incremental_child_fills=int((z.src=="H4_M15_CHILD").sum()) if len(z) else 0,cum_R=float(r.sum()) if len(r) else 0.0,mean_R_per_fill=float(r.mean()) if len(r) else np.nan,profit_factor=pf(r),max_dd_R=maxdd(r)))
    return pd.DataFrame(rows)


def getrow(tab,rule,w):
    q=tab[(tab.rule==rule)&(tab.window==w)]
    return q.iloc[0] if len(q) else None


def primary_verdict(tab,union):
    a=getrow(tab,PRIMARY,"2025_H2"); b=getrow(tab,PRIMARY,"2026_JAN_JUL"); p=getrow(tab,PRIMARY,"POOLED_RECENT")
    u=union[union.window=="POOLED_RECENT"].iloc[0]
    gates={
        "h2_parents_ge_15":int(a.eligible_parents)>=15,
        "y2026_parents_ge_15":int(b.eligible_parents)>=15,
        "child_found_ge_50pct_both":float(a.child_found_rate)>=.50 and float(b.child_found_rate)>=.50,
        "h2_real_fills_ge_4":int(a.real_fills)>=4,
        "y2026_real_fills_ge_4":int(b.real_fills)>=4,
        "mean_R_positive_both":bool(np.isfinite(a.mean_R_per_fill) and np.isfinite(b.mean_R_per_fill) and a.mean_R_per_fill>0 and b.mean_R_per_fill>0),
        "pf_gt_12_both":bool(np.isfinite(a.profit_factor) and np.isfinite(b.profit_factor) and a.profit_factor>1.2 and b.profit_factor>1.2),
        "cumR_positive_both":float(a.cum_R)>0 and float(b.cum_R)>0,
        "pooled_freq_ge_050pm":float(p.fills_per_month)>=.50,
        "pooled_loeo_positive":bool(np.isfinite(p.worst_loeo_remaining_R) and p.worst_loeo_remaining_R>0),
        "pooled_maxdd_le_4R":float(p.max_dd_R)<=4.0,
        "union_freq_ge_220pm_and_cumR_gt_12":float(u.fills_per_month)>=2.20 and float(u.cum_R)>12.0,
    }
    n=int(sum(bool(v) for v in gates.values()))
    critical=["child_found_ge_50pct_both","mean_R_positive_both","pf_gt_12_both","cumR_positive_both","pooled_freq_ge_050pm"]
    if n>=10 and all(gates[k] for k in critical): status="PASS_H4_TO_M15_EXECUTION_BRIDGE"
    elif n>=7 and float(a.cum_R)>0 and float(b.cum_R)>0 and np.isfinite(a.profit_factor) and np.isfinite(b.profit_factor) and a.profit_factor>1 and b.profit_factor>1 and p.fills_per_month>0: status="WATCH_H4_TO_M15_BRIDGE"
    else: status="FAIL_H4_TO_M15_EXECUTION_BRIDGE"
    return dict(verdict=status,gates_passed=n,gates_total=len(gates),gates=gates)


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def report(tab,hist,union,v,meta):
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","",f"Frozen orthogonal parent: `{PARENT_FAMILY}`; frozen T25 cutoff **{meta['t25_cutoff']:.6f}**.","","Primary child: `BREAK_CONFIRM_12H`; H4 supplies context only, M15 child supplies entry/SL geometry.","","## Parent / child census and economics","","| Rule | Window | H4 parents | Children | Found | Virtual fills | Mature | Real fills | Fills/mo | Mean R/fill | Cum R | PF | DD R | LOEO worst |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for rule in RULES:
        for w in ["2025_H2","2026_JAN_JUL","POOLED_RECENT","AUG2026_REUSED_AUDIT"]:
            r=getrow(tab,rule,w)
            fr=f"{r.child_found_rate*100:.1f}%" if np.isfinite(r.child_found_rate) else "—"
            mr=f"{r.mean_R_per_fill:+.3f}" if np.isfinite(r.mean_R_per_fill) else "—"
            lr=f"{r.worst_loeo_remaining_R:+.2f}" if np.isfinite(r.worst_loeo_remaining_R) else "—"
            lines.append(f"| {rule} | {w} | {int(r.eligible_parents)} | {int(r.children)} | {fr} | {int(r.virtual_fills)} | {int(r.mature_admit)} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {mr} | {r.cum_R:+.2f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} | {lr} |")
    lines += ["","## Canonical + primary child union","","| Window | Fills | Fills/mo | Canonical | Incremental child | Cum R | Mean R/fill | PF | DD R |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in union.iterrows():
        lines.append(f"| {r.window} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {int(r.canonical_fills)} | {int(r.incremental_child_fills)} | {r.cum_R:+.2f} | {r.mean_R_per_fill:+.3f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} |")
    lines += ["","## Primary gates"]
    for k,z in v["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} → {v['verdict']}**","","## Historical descriptive audit — primary","","| Window | Parents | Children | Real fills | Cum R | Mean R/fill | PF | DD R |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in hist[hist.rule==PRIMARY].iterrows():
        mr=f"{r.mean_R_per_fill:+.3f}" if np.isfinite(r.mean_R_per_fill) else "—"
        lines.append(f"| {r.window} | {int(r.eligible_parents)} | {int(r.children)} | {int(r.real_fills)} | {r.cum_R:+.2f} | {mr} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} |")
    lines += ["","## Frozen mechanics / caveats","- Strict ±24h canonical non-overlap is applied to the H4 parent before M15 child search.","- `NO_CHILD` and unfilled shadow limits carry 0R; only VF1-mature child opportunities can contribute real PnL.","- VF1 uses only whether a prior child virtual limit filled before the current child signal; prior outcome is not used.","- `COLOR_ONLY_12H` and `TWO_BAR_CONFIRM_12H` are audit-only and cannot rescue the primary verdict.","- 2025H2/2026 are reused research windows; August 2026 is consumed/reused audit only.","- 5 bps is a frozen stress assumption, not a claim of exact current FTMO BTC all-in cost.","- No live allocation is authorized."]
    return "\n".join(lines)+"\n"


def main():
    x=L5.make_panel(L5.load(L5.downloads()))
    parents,pre,raw,canon,mc,mr,cut,removed=frozen_parent_set(x)
    streams={}; tabs=[]; hist=[]
    for j,rule in enumerate(RULES):
        ch=make_children(x,parents,rule)
        s=execute_child_virtual(x,ch)
        streams[rule]=s
        tabs.append(summarize_rule(rule,parents,s,WINS))
        hist.append(summarize_rule(rule,parents,s,HIST_WINS))
        if len(s): s.to_csv(OUT/f"stream_{rule.lower()}.csv",index=False)
    tab=pd.concat(tabs,ignore_index=True); htab=pd.concat(hist,ignore_index=True)
    canon_s=canonical_stream(x,mc,mr,cut)
    union=union_summary(canon_s,streams[PRIMARY])
    v=primary_verdict(tab,union)
    meta=dict(t25_cutoff=cut,raw_h4_parents=len(raw),t25_pre=len(pre),removed_24h=removed,orthogonal_parents=len(parents),canonical_selected=len(canon))
    tab.to_csv(OUT/"child_bridge_summary.csv",index=False); htab.to_csv(OUT/"historical_summary.csv",index=False); union.to_csv(OUT/"canonical_plus_child_union.csv",index=False)
    parents.to_csv(OUT/"frozen_orthogonal_h4_parents.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps({**v,"meta":meta},indent=2,allow_nan=True),encoding="utf-8")
    (OUT/"REPORT.md").write_text(report(tab,htab,union,v,meta),encoding="utf-8")
    print(json.dumps({**v,"meta":meta},indent=2)); print((OUT/"REPORT.md").read_text())

if __name__=="__main__": main()
