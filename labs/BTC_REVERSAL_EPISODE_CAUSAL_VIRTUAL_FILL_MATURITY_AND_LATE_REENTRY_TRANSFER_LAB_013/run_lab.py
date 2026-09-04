#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_EPISODE_CAUSAL_VIRTUAL_FILL_MATURITY_AND_LATE_REENTRY_TRANSFER_LAB_013"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SEED=20260904
KNOWN_DELAY=pd.Timedelta(hours=24,minutes=15)

SRC12=HERE.parent/"BTC_REVERSAL_EPISODE_ORDINAL_REENTRY_AND_CLUSTER_RISK_CAP_LAB_012"/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab012",SRC12)
L12=importlib.util.module_from_spec(spec); spec.loader.exec_module(L12)

WINS={
    "2025_H2":(pd.Timestamp("2025-07-01",tz="UTC"),pd.Timestamp("2026-01-01",tz="UTC")),
    "2026_JAN_JUL":(pd.Timestamp("2026-01-01",tz="UTC"),pd.Timestamp("2026-08-01",tz="UTC")),
}
POLICIES=["BASE_ALL","VF1_MATURE","VF2_MATURE","OPP2_MATURE","VF1_KNOWN_OUTCOME","KNOWN_POSITIVE"]
PRIMARY="VF1_MATURE"


def add_maturity_state(s):
    s=s.sort_values("event_time").reset_index(drop=True).copy()
    cols=["prior_opportunities","prior_virtual_fills","prior_known_outcomes","prior_known_positive","prior_known_negative","hours_since_episode_start","hours_since_first_virtual_fill"]
    for c in cols: s[c]=np.nan
    for eid,q in s.groupby("episode_7d",sort=True):
        prior=[]
        episode_start=pd.Timestamp(q.event_time.min())
        for idx,r in q.sort_values("event_time").iterrows():
            t=pd.Timestamp(r.event_time)
            fills=[]; known=[]
            for pr in prior:
                if bool(pr["filled"]) and pd.notna(pr["fill_time"]):
                    ft=pd.Timestamp(pr["fill_time"])
                    if ft < t: fills.append(pr)
                if bool(pr["filled"]) and pd.Timestamp(pr["event_time"])+KNOWN_DELAY <= t:
                    known.append(pr)
            s.loc[idx,"prior_opportunities"]=len(prior)
            s.loc[idx,"prior_virtual_fills"]=len(fills)
            s.loc[idx,"prior_known_outcomes"]=len(known)
            s.loc[idx,"prior_known_positive"]=sum(float(z["signal_net_R"])>0 for z in known)
            s.loc[idx,"prior_known_negative"]=sum(float(z["signal_net_R"])<0 for z in known)
            s.loc[idx,"hours_since_episode_start"]=(t-episode_start).total_seconds()/3600.0
            if fills:
                first_ft=min(pd.Timestamp(z["fill_time"]) for z in fills)
                s.loc[idx,"hours_since_first_virtual_fill"]=(t-first_ft).total_seconds()/3600.0
            prior.append(r.to_dict())
    for c in ["prior_opportunities","prior_virtual_fills","prior_known_outcomes","prior_known_positive","prior_known_negative"]:
        s[c]=s[c].fillna(0).astype(int)
    s["accept_BASE_ALL"]=True
    s["accept_VF1_MATURE"]=s.prior_virtual_fills>=1
    s["accept_VF2_MATURE"]=s.prior_virtual_fills>=2
    s["accept_OPP2_MATURE"]=s.prior_opportunities>=2
    s["accept_VF1_KNOWN_OUTCOME"]=(s.prior_virtual_fills>=1)&(s.prior_known_outcomes>=1)
    s["accept_KNOWN_POSITIVE"]=s.prior_known_positive>=1
    return s


def subwin(s,name):
    a,b=WINS[name]
    return s[(s.event_time>=a)&(s.event_time<b)].copy().sort_values("event_time")


def pooled_recent(s):
    return s[(s.event_time>=WINS["2025_H2"][0])&(s.event_time<WINS["2026_JAN_JUL"][1])].copy().sort_values("event_time")


def policy_table(s):
    rows=[]; off=100
    for w in ["2025_H2","2026_JAN_JUL"]:
        d=subwin(s,w)
        for p in POLICIES:
            rows.append(L12.policy_summary(d,p,w,off)); off+=19
    d=pooled_recent(s)
    for p in POLICIES:
        rows.append(L12.policy_summary(d,p,"POOLED_RECENT",off)); off+=19
    return pd.DataFrame(rows)


def maturity_bucket_table(s):
    rows=[]
    windows={**WINS,"POOLED_RECENT":(WINS["2025_H2"][0],WINS["2026_JAN_JUL"][1])}
    for w,(a,b) in windows.items():
        d=s[(s.event_time>=a)&(s.event_time<b)].copy()
        d["vf_bucket"]=d.prior_virtual_fills.map(lambda x:"3+" if x>=3 else str(int(x)))
        for bucket in ["0","1","2","3+"]:
            q=d[d.vf_bucket==bucket]; fills=q[q.filled]
            ar=q.signal_net_R.to_numpy(float); fr=fills.signal_net_R.to_numpy(float)
            rows.append(dict(window=w,prior_virtual_fill_bucket=bucket,opportunities=len(q),fills=len(fills),opportunity_mean_R=float(ar.mean()) if len(ar) else np.nan,fill_mean_R=float(fr.mean()) if len(fr) else np.nan,fill_positive_rate=float((fr>0).mean()) if len(fr) else np.nan,cum_R=float(ar.sum()) if len(ar) else 0.0,median_hours_since_episode_start=float(q.hours_since_episode_start.median()) if len(q) else np.nan,median_hours_since_first_virtual_fill=float(q.hours_since_first_virtual_fill.median()) if len(q) and q.hours_since_first_virtual_fill.notna().any() else np.nan))
    return pd.DataFrame(rows)


def historical_table(s):
    ranges={
        "2021":(pd.Timestamp("2021-01-01",tz="UTC"),pd.Timestamp("2022-01-01",tz="UTC")),
        "2022":(pd.Timestamp("2022-01-01",tz="UTC"),pd.Timestamp("2023-01-01",tz="UTC")),
        "2023":(pd.Timestamp("2023-01-01",tz="UTC"),pd.Timestamp("2024-01-01",tz="UTC")),
        "2024":(pd.Timestamp("2024-01-01",tz="UTC"),pd.Timestamp("2025-01-01",tz="UTC")),
        "2025_H1":(pd.Timestamp("2025-01-01",tz="UTC"),pd.Timestamp("2025-07-01",tz="UTC")),
    }
    rows=[]
    for w,(a,b) in ranges.items():
        d=s[(s.event_time>=a)&(s.event_time<b)].copy()
        for p in ["BASE_ALL",PRIMARY]:
            z=L12.policy_summary(d,p,w,700+len(rows)*13)
            rows.append(z)
    return pd.DataFrame(rows)


def getrow(t,w,p):
    q=t[(t.window==w)&(t.policy==p)]
    return q.iloc[0]


def mechanism_stats(s):
    d=pooled_recent(s)
    f=d[d.filled].copy()
    early=f[f.prior_virtual_fills==0].signal_net_R.to_numpy(float)
    mature=f[f.prior_virtual_fills>=1].signal_net_R.to_numpy(float)
    return dict(
        early_fill_n=int(len(early)),early_fill_mean_R=float(early.mean()) if len(early) else np.nan,early_fill_positive=float((early>0).mean()) if len(early) else np.nan,
        mature_fill_n=int(len(mature)),mature_fill_mean_R=float(mature.mean()) if len(mature) else np.nan,mature_fill_positive=float((mature>0).mean()) if len(mature) else np.nan,
    )


def make_verdict(t,s):
    b25=getrow(t,"2025_H2","BASE_ALL"); b26=getrow(t,"2026_JAN_JUL","BASE_ALL"); bp=getrow(t,"POOLED_RECENT","BASE_ALL")
    p25=getrow(t,"2025_H2",PRIMARY); p26=getrow(t,"2026_JAN_JUL",PRIMARY); pp=getrow(t,"POOLED_RECENT",PRIMARY)
    mech=mechanism_stats(s)
    def retain(p,b): return float(p.cum_R/b.cum_R) if b.cum_R>0 else np.nan
    r25=retain(p25,b25); r26=retain(p26,b26); rp=retain(pp,bp)
    gates={
        "h2_2025_cum_positive":float(p25.cum_R)>0,
        "y2026_cum_positive":float(p26.cum_R)>0,
        "pooled_cum_positive":float(pp.cum_R)>0,
        "pooled_retains_ge_70pct_base":bool(np.isfinite(rp) and rp>=.70),
        "h2_2025_retains_ge_70pct_base":bool(np.isfinite(r25) and r25>=.70),
        "y2026_retains_ge_70pct_base":bool(np.isfinite(r26) and r26>=.70),
        "pooled_pf_ge_base":bool(np.isfinite(pp.profit_factor) and np.isfinite(bp.profit_factor) and pp.profit_factor>=bp.profit_factor),
        "pooled_maxdd_le_base":float(pp.max_dd_R)<=float(bp.max_dd_R),
        "vf0_fill_mean_nonpositive":bool(np.isfinite(mech["early_fill_mean_R"]) and mech["early_fill_mean_R"]<=0),
        "vf1plus_fill_mean_positive":bool(np.isfinite(mech["mature_fill_mean_R"]) and mech["mature_fill_mean_R"]>0),
        "pooled_all_loeo_positive":float(pp.worst_loeo_remaining_R)>0,
        "pooled_cluster_bootstrap_ci_low_gt_0":float(pp.bootstrap_ci025)>0,
    }
    n=int(sum(bool(v) for v in gates.values()))
    first8=list(gates.keys())[:8]
    if n>=10 and all(gates[k] for k in first8): verdict="PASS_CAUSAL_VIRTUAL_FILL_MATURITY_TRANSFER"
    elif gates["h2_2025_cum_positive"] and gates["y2026_cum_positive"] and gates["pooled_cum_positive"] and np.isfinite(rp) and rp>=.50 and n>=7:
        verdict="WATCH_CAUSAL_MATURITY_PARTIAL"
    else: verdict="FAIL_VIRTUAL_FILL_MATURITY_DOES_NOT_TRANSFER"
    return dict(verdict=verdict,gates_passed=n,gates_total=len(gates),gates=gates,retain_2025H2=r25,retain_2026=r26,retain_pooled=rp,mechanism=mech)


def report(t,mb,hist,v):
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","","Role: causal virtual-fill maturity / late-reentry transfer audit over the exact frozen reversal branch; no new selector, entry geometry, stop, target, or regime gate.","","## Primary and audit policy economics","","| Window | Policy | Admit | Fills | Cum R | EV/op | PF | Max DD | Worst ep | Top ep share | LOEO worst | Boot CI low | Max ep fills |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in t.iterrows():
        pf="inf" if np.isinf(r.profit_factor) else (f"{r.profit_factor:.3f}" if np.isfinite(r.profit_factor) else "—")
        share=f"{r.top_episode_positive_share*100:.1f}%" if np.isfinite(r.top_episode_positive_share) else "—"
        lines.append(f"| {r.window} | {r.policy} | {int(r.admitted_signals)} | {int(r.fills)} | {r.cum_R:+.2f} | {r.ev_per_opportunity:+.3f} | {pf} | {r.max_dd_R:.2f} | {r.worst_episode_R:+.2f} | {share} | {r.worst_loeo_remaining_R:+.2f} | {r.bootstrap_ci025:+.3f} | {int(r.max_episode_fills)} |")
    lines += ["","## Virtual-fill maturity buckets","","| Window | Prior virtual fills | Opps | Fills | Fill mean R | Fill positive | Cum R | Median h from ep start | Median h from first VF |","|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in mb.iterrows():
        fm=f"{r.fill_mean_R:+.3f}" if np.isfinite(r.fill_mean_R) else "—"; fp=f"{r.fill_positive_rate*100:.1f}%" if np.isfinite(r.fill_positive_rate) else "—"; hs=f"{r.median_hours_since_episode_start:.1f}" if np.isfinite(r.median_hours_since_episode_start) else "—"; hf=f"{r.median_hours_since_first_virtual_fill:.1f}" if np.isfinite(r.median_hours_since_first_virtual_fill) else "—"
        lines.append(f"| {r.window} | {r.prior_virtual_fill_bucket} | {int(r.opportunities)} | {int(r.fills)} | {fm} | {fp} | {r.cum_R:+.2f} | {hs} | {hf} |")
    p=getrow(t,"POOLED_RECENT",PRIMARY); b=getrow(t,"POOLED_RECENT","BASE_ALL")
    lines += ["","## Primary VF1 interpretation",f"- Pooled BASE: **{b.cum_R:+.2f}R** → VF1: **{p.cum_R:+.2f}R**; retention **{v['retain_pooled']*100:.1f}%**.",f"- Pooled PF: **{b.profit_factor:.3f} → {p.profit_factor:.3f}**; max DD **{b.max_dd_R:.2f}R → {p.max_dd_R:.2f}R**.",f"- Max real fills in one episode under VF1: **{int(p.max_episode_fills)}** = up to **{int(p.max_episode_fills)*0.25:.2f}%** initial episode budget at 0.25%/trade or **{int(p.max_episode_fills)*0.50:.2f}%** at 0.50%/trade.",f"- Early virtual-fill bucket: N={v['mechanism']['early_fill_n']}, mean **{v['mechanism']['early_fill_mean_R']:+.3f}R/fill**. Mature bucket >=1 prior VF: N={v['mechanism']['mature_fill_n']}, mean **{v['mechanism']['mature_fill_mean_R']:+.3f}R/fill**.","","## Historical descriptive audit","","| Window | Policy | Admit | Fills | Cum R | PF | DD |","|---|---|---:|---:|---:|---:|---:|"]
    for _,r in hist.iterrows():
        pf="inf" if np.isinf(r.profit_factor) else (f"{r.profit_factor:.3f}" if np.isfinite(r.profit_factor) else "—")
        lines.append(f"| {r.window} | {r.policy} | {int(r.admitted_signals)} | {int(r.fills)} | {r.cum_R:+.2f} | {pf} | {r.max_dd_R:.2f} |")
    lines += ["","## Gates"]
    for k,z in v["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} → {v['verdict']}**","","## Status","- `VF1_MATURE` is the only primary maturity rule; audit policies cannot rescue it.","- Virtual fill knowledge requires actual frozen fill_time strictly before the current event; no future path is used to activate VF1.","- Outcome-aware audits delay prior outcomes by +24h15m.","- 2025 H2 and 2026 Jan-Jul are reused research windows, not fresh holdouts.","- August 2026 remains consumed and has zero frozen REV opportunities.","- No live allocation is authorized by LAB013 alone."]
    return "\n".join(lines)+"\n"


def main():
    s,meta=L12.build_base()
    s=add_maturity_state(s)
    t=policy_table(s)
    mb=maturity_bucket_table(s)
    hist=historical_table(s)
    v=make_verdict(t,s)
    OUT.mkdir(parents=True,exist_ok=True)
    s.to_csv(OUT/"signals_with_causal_maturity_state.csv",index=False)
    t.to_csv(OUT/"policy_economics.csv",index=False)
    mb.to_csv(OUT/"maturity_bucket_economics.csv",index=False)
    hist.to_csv(OUT/"historical_audit.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,default=str),encoding="utf-8")
    (OUT/"REPORT.md").write_text(report(t,mb,hist,v),encoding="utf-8")
    print(json.dumps({"verdict":v["verdict"],"score":f"{v['gates_passed']}/{v['gates_total']}","pooled_retention":v["retain_pooled"],"early_fill_mean":v["mechanism"]["early_fill_mean_R"],"mature_fill_mean":v["mechanism"]["mature_fill_mean_R"]},indent=2))

if __name__=="__main__": main()
