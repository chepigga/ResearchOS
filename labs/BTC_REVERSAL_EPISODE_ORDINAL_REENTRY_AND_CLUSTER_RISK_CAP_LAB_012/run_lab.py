#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_EPISODE_ORDINAL_REENTRY_AND_CLUSTER_RISK_CAP_LAB_012"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SEED=20260904; BOOT_N=5000
TTL=pd.Timedelta(minutes=60)
KNOWN_DELAY=pd.Timedelta(hours=24,minutes=15)

SRC11=HERE.parent/"BTC_REVERSAL_2025H2_PROFIT_CONCENTRATION_AND_EPISODE_INDEPENDENCE_LAB_011"/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab011",SRC11)
L11=importlib.util.module_from_spec(spec); spec.loader.exec_module(L11)
L6=L11.L6

WINS={
    "2025_H2":(pd.Timestamp("2025-07-01",tz="UTC"),pd.Timestamp("2026-01-01",tz="UTC")),
    "2026_JAN_JUL":(pd.Timestamp("2026-01-01",tz="UTC"),pd.Timestamp("2026-08-01",tz="UTC")),
}
POLICIES=["BASE_ALL","MAX1_FILL_SLOTS","MAX2_FILL_SLOTS","MAX3_FILL_SLOTS","LOSSSTOP_1R","MAX2_PLUS_LOSSSTOP_1R"]
PRIMARY="MAX2_FILL_SLOTS"


def pf(a):
    a=np.asarray(a,float); pos=a[a>0].sum(); neg=-a[a<0].sum()
    if neg==0: return np.inf if pos>0 else np.nan
    return float(pos/neg)


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def maxdd(a): return float(L6.max_dd_r(np.asarray(a,float))) if len(a) else np.nan

def maxloss(a): return int(L6.max_consecutive_loss(np.asarray(a,float))) if len(a) else 0


def build_base():
    s,meta=L11.build_base()
    s=s.sort_values("event_time").reset_index(drop=True).copy()
    s["opportunity_ordinal"]=s.groupby("episode_7d").cumcount()+1
    s["base_fill_ordinal"]=np.nan
    for eid,q in s.groupby("episode_7d",sort=False):
        k=0
        for idx,r in q.iterrows():
            if bool(r.filled):
                k+=1; s.loc[idx,"base_fill_ordinal"]=k
    return s,meta


def slot_state(accepted_rows,t):
    consumed=0; pending=0
    for r in accepted_rows:
        et=pd.Timestamp(r["event_time"])
        filled=bool(r["filled"])
        ft=pd.Timestamp(r["fill_time"]) if filled and pd.notna(r["fill_time"]) else pd.NaT
        if filled and pd.notna(ft) and ft<=t:
            consumed+=1
        elif t < et+TTL:
            pending+=1
    return consumed,pending


def simulate_policy(s,policy):
    accepted=np.zeros(len(s),dtype=bool)
    slot_cap=None
    if policy=="MAX1_FILL_SLOTS": slot_cap=1
    elif policy in ["MAX2_FILL_SLOTS","MAX2_PLUS_LOSSSTOP_1R"]: slot_cap=2
    elif policy=="MAX3_FILL_SLOTS": slot_cap=3
    use_lossstop=policy in ["LOSSSTOP_1R","MAX2_PLUS_LOSSSTOP_1R"]
    if policy=="BASE_ALL":
        return np.ones(len(s),dtype=bool)

    for eid,q in s.groupby("episode_7d",sort=True):
        accepted_rows=[]
        stop_triggered=False
        for idx,r in q.sort_values("event_time").iterrows():
            t=pd.Timestamp(r.event_time)
            if use_lossstop and not stop_triggered:
                known_sum=0.0
                for ar in accepted_rows:
                    if pd.Timestamp(ar["event_time"])+KNOWN_DELAY<=t:
                        known_sum+=float(ar["signal_net_R"])
                if known_sum<=-1.0:
                    stop_triggered=True
            if stop_triggered:
                continue
            if slot_cap is not None:
                consumed,pending=slot_state(accepted_rows,t)
                if consumed+pending>=slot_cap:
                    continue
            accepted[idx]=True
            accepted_rows.append(r.to_dict())
    return accepted


def apply_policies(s):
    z=s.copy()
    for p in POLICIES:
        z[f"accept_{p}"]=simulate_policy(z,p)
    return z


def subwin(s,name):
    a,b=WINS[name]
    return s[(s.event_time>=a)&(s.event_time<b)].copy().sort_values("event_time")


def policy_returns(d,policy):
    acc=d[f"accept_{policy}"].to_numpy(bool)
    base=d.signal_net_R.to_numpy(float)
    return np.where(acc,base,0.0), acc


def episode_policy_table(d,policy,window):
    rows=[]
    for eid,q in d.groupby("episode_7d",sort=True):
        r,acc=policy_returns(q,policy)
        accepted=q[acc]
        pos=float(r[r>0].sum())
        rows.append(dict(window=window,policy=policy,episode_id=int(eid),start=q.event_time.min(),end=q.event_time.max(),opportunities=len(q),admitted=int(acc.sum()),fills=int((acc & q.filled.to_numpy(bool)).sum()),cum_R=float(r.sum()),positive_R=pos,ev_per_op=float(r.mean()) if len(r) else np.nan))
    return pd.DataFrame(rows)


def cluster_bootstrap(d,policy,seed_offset=0):
    groups=[]
    for _,q in d.groupby("episode_7d",sort=True):
        r,_=policy_returns(q,policy); groups.append(r)
    if not groups:
        return dict(episodes=0,mean_R=np.nan,ci025=np.nan,ci975=np.nan)
    rng=np.random.default_rng(SEED+seed_offset)
    means=[]; n=len(groups)
    for _ in range(BOOT_N):
        ix=rng.integers(0,n,size=n)
        z=np.concatenate([groups[i] for i in ix])
        means.append(float(z.mean()))
    lo,hi=np.quantile(means,[.025,.975])
    full=np.concatenate(groups)
    return dict(episodes=n,mean_R=float(full.mean()),ci025=float(lo),ci975=float(hi))


def policy_summary(d,policy,window,seed_offset=0):
    r,acc=policy_returns(d,policy)
    admitted=d[acc]; fills=int((acc & d.filled.to_numpy(bool)).sum())
    ep=episode_policy_table(d,policy,window)
    gross_pos=float(r[r>0].sum())
    top_share=float(ep.positive_R.max()/gross_pos) if len(ep) and gross_pos>0 else np.nan
    total=float(r.sum())
    loeo=float((total-ep.cum_R).min()) if len(ep) else np.nan
    boot=cluster_bootstrap(d,policy,seed_offset)
    worst_ep=float(ep.cum_R.min()) if len(ep) else np.nan
    max_ep_fills=int(ep.fills.max()) if len(ep) else 0
    return dict(window=window,policy=policy,opportunities=len(d),admitted_signals=int(acc.sum()),fills=fills,fill_rate=float(fills/acc.sum()) if acc.sum() else np.nan,cum_R=total,ev_per_opportunity=float(r.mean()) if len(r) else np.nan,ev_per_admitted=float(admitted.signal_net_R.mean()) if len(admitted) else np.nan,profit_factor=pf(r),max_dd_R=maxdd(r),max_consecutive_losses=maxloss(r),episodes=len(ep),positive_episodes=int((ep.cum_R>0).sum()) if len(ep) else 0,negative_episodes=int((ep.cum_R<0).sum()) if len(ep) else 0,worst_episode_R=worst_ep,top_episode_positive_share=top_share,worst_loeo_remaining_R=loeo,bootstrap_ci025=boot["ci025"],bootstrap_ci975=boot["ci975"],max_episode_fills=max_ep_fills)


def ordinal_table(s):
    rows=[]
    windows={**WINS,"POOLED_RECENT":(WINS["2025_H2"][0],WINS["2026_JAN_JUL"][1])}
    for w,(a,b) in windows.items():
        d=s[(s.event_time>=a)&(s.event_time<b)&(s.filled)].copy()
        d["ordinal_bucket"]=d.base_fill_ordinal.map(lambda x:"4+" if x>=4 else str(int(x)))
        for ob in ["1","2","3","4+"]:
            q=d[d.ordinal_bucket==ob]; aR=q.signal_net_R.to_numpy(float)
            rows.append(dict(window=w,fill_ordinal=ob,n=len(q),mean_R=float(aR.mean()) if len(aR) else np.nan,median_R=float(np.median(aR)) if len(aR) else np.nan,positive_rate=float((aR>0).mean()) if len(aR) else np.nan,cum_R=float(aR.sum()) if len(aR) else 0.0))
    return pd.DataFrame(rows)


def policy_table(s):
    rows=[]; off=0
    for w in ["2025_H2","2026_JAN_JUL"]:
        d=subwin(s,w)
        for p in POLICIES:
            rows.append(policy_summary(d,p,w,off)); off+=17
    pooled=s[(s.event_time>=WINS["2025_H2"][0])&(s.event_time<WINS["2026_JAN_JUL"][1])].copy()
    for p in POLICIES:
        rows.append(policy_summary(pooled,p,"POOLED_RECENT",off)); off+=17
    return pd.DataFrame(rows)


def getrow(t,w,p):
    q=t[(t.window==w)&(t.policy==p)]
    return q.iloc[0]


def make_verdict(t,ordt):
    b25=getrow(t,"2025_H2","BASE_ALL"); b26=getrow(t,"2026_JAN_JUL","BASE_ALL"); bp=getrow(t,"POOLED_RECENT","BASE_ALL")
    p25=getrow(t,"2025_H2",PRIMARY); p26=getrow(t,"2026_JAN_JUL",PRIMARY); pp=getrow(t,"POOLED_RECENT",PRIMARY)
    o2=ordt[(ordt.window=="POOLED_RECENT")&(ordt.fill_ordinal=="2")].iloc[0]
    retain_pool=float(pp.cum_R/bp.cum_R) if bp.cum_R>0 else np.nan
    retain25=float(p25.cum_R/b25.cum_R) if b25.cum_R>0 else np.nan
    retain26=float(p26.cum_R/b26.cum_R) if b26.cum_R>0 else np.nan
    gates={
        "h2_2025_capped_cum_positive":float(p25.cum_R)>0,
        "y2026_capped_cum_positive":float(p26.cum_R)>0,
        "pooled_capped_cum_positive":float(pp.cum_R)>0,
        "pooled_retains_ge_70pct_base":bool(np.isfinite(retain_pool) and retain_pool>=.70),
        "h2_2025_retains_ge_60pct_base":bool(np.isfinite(retain25) and retain25>=.60),
        "y2026_retains_ge_60pct_base":bool(np.isfinite(retain26) and retain26>=.60),
        "pooled_maxdd_le_base":float(pp.max_dd_R)<=float(bp.max_dd_R),
        "worst_capped_episode_ge_minus_2_25R":float(pp.worst_episode_R)>=-2.25,
        "pooled_top_episode_share_le_60pct":bool(np.isfinite(pp.top_episode_positive_share) and pp.top_episode_positive_share<=.60),
        "pooled_all_loeo_positive":float(pp.worst_loeo_remaining_R)>0,
        "pooled_cluster_bootstrap_ci_low_gt_0":float(pp.bootstrap_ci025)>0,
        "ordinal_2_mean_positive":bool(int(o2.n)>0 and float(o2.mean_R)>0),
    }
    n=int(sum(bool(v) for v in gates.values()))
    critical=["h2_2025_capped_cum_positive","y2026_capped_cum_positive","pooled_capped_cum_positive","pooled_retains_ge_70pct_base","pooled_maxdd_le_base","worst_capped_episode_ge_minus_2_25R"]
    if n>=10 and all(gates[k] for k in critical): verdict="PASS_PROP_SAFE_EPISODE_HARVEST"
    elif gates["h2_2025_capped_cum_positive"] and gates["y2026_capped_cum_positive"] and gates["pooled_capped_cum_positive"]: verdict="WATCH_EPISODE_HARVEST_PARTIAL"
    else: verdict="FAIL_REENTRY_CAP_DOES_NOT_PRESERVE_EDGE"
    return dict(verdict=verdict,gates_passed=n,gates_total=len(gates),gates=gates,retain_pooled=retain_pool,retain_2025H2=retain25,retain_2026=retain26)


def report(t,ordt,v):
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","","Role: ordinal re-entry and causal cluster-risk-cap audit of the exact frozen reversal branch; no new selector or regime gate.","","## Fill ordinal economics","","| Window | Fill ordinal | N | Mean R | Median R | Positive | Cum R |","|---|---|---:|---:|---:|---:|---:|"]
    for _,r in ordt.iterrows():
        lines.append(f"| {r.window} | {r.fill_ordinal} | {int(r.n)} | {r.mean_R:+.3f} | {r.median_R:+.3f} | {r.positive_rate*100:.1f}% | {r.cum_R:+.2f} |" if r.n else f"| {r.window} | {r.fill_ordinal} | 0 | — | — | — | +0.00 |")
    lines += ["","## Policy economics","","| Window | Policy | Admit | Fills | Cum R | EV/op | PF | Max DD | Worst ep | Top ep share | LOEO worst | Boot CI low |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in t.iterrows():
        share=f"{r.top_episode_positive_share*100:.1f}%" if np.isfinite(r.top_episode_positive_share) else "—"
        lines.append(f"| {r.window} | {r.policy} | {int(r.admitted_signals)} | {int(r.fills)} | {r.cum_R:+.2f} | {r.ev_per_opportunity:+.3f} | {fmtpf(r.profit_factor)} | {r.max_dd_R:.2f} | {r.worst_episode_R:+.2f} | {share} | {r.worst_loeo_remaining_R:+.2f} | {r.bootstrap_ci025:+.3f} |")
    p=getrow(t,"POOLED_RECENT",PRIMARY); b=getrow(t,"POOLED_RECENT","BASE_ALL")
    lines += ["","## Primary MAX2 interpretation",f"- Pooled BASE: **{b.cum_R:+.2f}R** → MAX2: **{p.cum_R:+.2f}R**; retention **{v['retain_pooled']*100:.1f}%**.",f"- Pooled max DD: **{b.max_dd_R:.2f}R → {p.max_dd_R:.2f}R**.",f"- MAX2 worst episode: **{p.worst_episode_R:+.2f}R**; max filled trades in any episode: **{int(p.max_episode_fills)}**.",f"- Risk mapping: MAX2 = **0.50%** cumulative initial episode budget at 0.25%/trade or **1.00%** at 0.50%/trade.","","## Gates"]
    for k,z in v["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} → {v['verdict']}**","","## Status","- 2025 H2 and 2026 Jan–Jul are reused research windows, not fresh holdout.","- MAX1/MAX3/loss-stop policies are audit-only and cannot replace the preregistered MAX2 verdict.","- Loss-stop outcome knowledge is deliberately delayed to event+24h15m to avoid future leakage.","- This LAB does not authorize live allocation."]
    return "\n".join(lines)+"\n"


def main():
    s,meta=build_base(); s=apply_policies(s)
    ordt=ordinal_table(s); t=policy_table(s); v=make_verdict(t,ordt)
    s.to_csv(OUT/"signals_with_ordinals_and_policy_acceptance.csv",index=False)
    ordt.to_csv(OUT/"fill_ordinal_summary.csv",index=False)
    t.to_csv(OUT/"policy_summary.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,allow_nan=True),encoding="utf-8")
    rep=report(t,ordt,v); (OUT/"REPORT.md").write_text(rep,encoding="utf-8")
    print(json.dumps(v,indent=2)); print(rep)

if __name__=="__main__": main()
