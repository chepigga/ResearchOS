#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_2025H2_PROFIT_CONCENTRATION_AND_EPISODE_INDEPENDENCE_LAB_011"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SEED=20260903; BOOT_N=5000

SRC9=HERE.parent/"BTC_REVERSAL_SLOW_REGIME_AND_IMPULSE_ACCEPTANCE_PERSISTENCE_LAB_009"/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab009",SRC9)
L9=importlib.util.module_from_spec(spec); spec.loader.exec_module(L9)
L7=L9.L7; L6=L9.L6

WINS={
    "2025_H2":(pd.Timestamp("2025-07-01",tz="UTC"),pd.Timestamp("2026-01-01",tz="UTC")),
    "2026_JAN_JUL":(pd.Timestamp("2026-01-01",tz="UTC"),pd.Timestamp("2026-08-01",tz="UTC")),
}


def pf(a):
    a=np.asarray(a,float); pos=a[a>0].sum(); neg=-a[a<0].sum()
    if neg==0: return np.inf if pos>0 else np.nan
    return float(pos/neg)


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def assign_episode_ids(signals,gap_days):
    s=signals.sort_values("event_time").copy()
    gaps=s.event_time.diff().dt.total_seconds().div(86400.0)
    s[f"episode_{gap_days}d"]=(gaps.isna() | (gaps>gap_days)).cumsum().astype(int)
    return s


def build_base():
    x,_,_=L7.load_panel()
    x=L9.enrich_slow_panel(x)
    s,meta,_=L9.build_signals(x)
    s=s.sort_values("event_time").reset_index(drop=True)
    # episode assignment is global before window slicing
    for g in [3,7,14]:
        ids=assign_episode_ids(s[["signal_id","event_time"]].copy(),g)[["signal_id",f"episode_{g}d"]]
        s=s.merge(ids,on="signal_id",how="left")
    s["month"]=s.event_time.dt.strftime("%Y-%m")
    s["reversal_trade_side"]=np.where(s.impulse_dir>0,"SELL","BUY")
    return s,meta


def subwin(s,name):
    a,b=WINS[name]
    return s[(s.event_time>=a)&(s.event_time<b)].copy().sort_values("event_time")


def summary_row(name,d):
    a=d.signal_net_R.to_numpy(float)
    return dict(window=name,signals=len(d),fills=int(d.filled.sum()),cum_R=float(a.sum()),ev_R=float(a.mean()) if len(a) else np.nan,profit_factor=pf(a),positive_signals=int((a>0).sum()),negative_signals=int((a<0).sum()),no_fill_or_zero=int((a==0).sum()))


def monthly_table(d,name):
    months=pd.period_range(WINS[name][0].tz_localize(None),WINS[name][1].tz_localize(None)-pd.Timedelta(days=1),freq="M").strftime("%Y-%m")
    rows=[]
    for m in months:
        q=d[d.month==m]; a=q.signal_net_R.to_numpy(float)
        rows.append(dict(window=name,month=m,signals=len(q),fills=int(q.filled.sum()),cum_R=float(a.sum()),ev_R=float(a.mean()) if len(a) else np.nan,profit_factor=pf(a)))
    return pd.DataFrame(rows)


def direction_table(d,name):
    rows=[]
    for side in ["BUY","SELL"]:
        q=d[d.reversal_trade_side==side]; a=q.signal_net_R.to_numpy(float)
        rows.append(dict(window=name,reversal_trade_side=side,signals=len(q),fills=int(q.filled.sum()),cum_R=float(a.sum()),ev_R=float(a.mean()) if len(a) else np.nan,profit_factor=pf(a)))
    return pd.DataFrame(rows)


def episode_table(d,name,gap=7):
    col=f"episode_{gap}d"; rows=[]
    for eid,q in d.groupby(col,sort=True):
        a=q.signal_net_R.to_numpy(float); pos=a[a>0].sum()
        rows.append(dict(window=name,gap_days=gap,episode_id=int(eid),start=q.event_time.min(),end=q.event_time.max(),signals=len(q),fills=int(q.filled.sum()),cum_R=float(a.sum()),positive_R=float(pos),ev_R=float(a.mean()) if len(a) else np.nan,profit_factor=pf(a)))
    return pd.DataFrame(rows)


def concentration(d,episodes,name):
    a=d.signal_net_R.to_numpy(float); winners=np.sort(a[a>0])[::-1]
    gross_pos=float(winners.sum())
    top1=float(winners[:1].sum()/gross_pos) if gross_pos>0 else np.nan
    top3=float(winners[:3].sum()/gross_pos) if gross_pos>0 else np.nan
    top_episode=float(episodes.positive_R.max()/gross_pos) if gross_pos>0 and len(episodes) else np.nan
    return dict(window=name,gross_positive_R=gross_pos,gross_negative_R=float(-a[a<0].sum()),top1_winner_share=top1,top3_winner_share=top3,top_episode_positive_share=top_episode)


def leave_one_month_out(d,name):
    months=pd.period_range(WINS[name][0].tz_localize(None),WINS[name][1].tz_localize(None)-pd.Timedelta(days=1),freq="M").strftime("%Y-%m")
    total=float(d.signal_net_R.sum()); rows=[]
    for m in months:
        removed=float(d.loc[d.month==m,"signal_net_R"].sum())
        rows.append(dict(window=name,removed_month=m,removed_R=removed,remaining_R=total-removed))
    return pd.DataFrame(rows)


def leave_one_episode_out(d,episodes,name):
    total=float(d.signal_net_R.sum()); rows=[]
    for _,e in episodes.iterrows():
        rows.append(dict(window=name,removed_episode=int(e.episode_id),removed_R=float(e.cum_R),remaining_R=total-float(e.cum_R)))
    return pd.DataFrame(rows)


def cluster_bootstrap(d,name,gap=7):
    col=f"episode_{gap}d"; groups=[q.signal_net_R.to_numpy(float) for _,q in d.groupby(col,sort=True)]
    if not groups:
        return dict(window=name,episodes=0,draws=BOOT_N,mean_R=np.nan,ci025=np.nan,ci975=np.nan)
    rng=np.random.default_rng(SEED + (1 if name=="2025_H2" else 2))
    means=[]; n=len(groups)
    for _ in range(BOOT_N):
        ix=rng.integers(0,n,size=n)
        z=np.concatenate([groups[i] for i in ix])
        means.append(float(z.mean()))
    q=np.quantile(means,[.025,.975])
    return dict(window=name,episodes=n,draws=BOOT_N,mean_R=float(d.signal_net_R.mean()),ci025=float(q[0]),ci975=float(q[1]))


def gap_audit(d,name):
    rows=[]
    gross=float(d.loc[d.signal_net_R>0,"signal_net_R"].sum())
    for g in [3,7,14]:
        ep=episode_table(d,name,g)
        rows.append(dict(window=name,gap_days=g,episodes=len(ep),positive_episodes=int((ep.cum_R>0).sum()),negative_episodes=int((ep.cum_R<0).sum()),top_episode_positive_share=float(ep.positive_R.max()/gross) if gross>0 and len(ep) else np.nan,min_leave_one_episode_R=float((float(d.signal_net_R.sum())-ep.cum_R).min()) if len(ep) else np.nan))
    return pd.DataFrame(rows)


def verdict(all_summ,months,eps,conc,lomo,loeo,boots):
    def sm(w): return all_summ[all_summ.window==w].iloc[0]
    def cc(w): return conc[conc.window==w].iloc[0]
    def bt(w): return boots[w]
    m25=months[months.window=="2025_H2"]
    e25=eps[eps.window=="2025_H2"]
    e26=eps[eps.window=="2026_JAN_JUL"]
    c25=cc("2025_H2"); c26=cc("2026_JAN_JUL")
    gates={
        "h2_2025_cum_positive":float(sm("2025_H2").cum_R)>0,
        "h2_2025_positive_months_ge_4_of_6":int((m25.cum_R>0).sum())>=4,
        "h2_2025_all_lomo_positive":bool(len(lomo[lomo.window=="2025_H2"]) and (lomo[lomo.window=="2025_H2"].remaining_R>0).all()),
        "h2_2025_episodes_ge_4":len(e25)>=4,
        "h2_2025_positive_episodes_ge_3":int((e25.cum_R>0).sum())>=3,
        "h2_2025_all_loeo_positive":bool(len(loeo[loeo.window=="2025_H2"]) and (loeo[loeo.window=="2025_H2"].remaining_R>0).all()),
        "h2_2025_top1_share_le_35pct":bool(np.isfinite(c25.top1_winner_share) and c25.top1_winner_share<=.35),
        "h2_2025_top3_share_le_70pct":bool(np.isfinite(c25.top3_winner_share) and c25.top3_winner_share<=.70),
        "h2_2025_top_episode_share_le_50pct":bool(np.isfinite(c25.top_episode_positive_share) and c25.top_episode_positive_share<=.50),
        "h2_2025_cluster_bootstrap_ci_low_gt_0":bool(np.isfinite(bt("2025_H2")["ci025"]) and bt("2025_H2")["ci025"]>0),
        "y2026_jan_jul_cum_positive":float(sm("2026_JAN_JUL").cum_R)>0,
        "y2026_episode_breadth":bool(int((e26.cum_R>0).sum())>=3 and np.isfinite(c26.top_episode_positive_share) and c26.top_episode_positive_share<=.60),
    }
    n=int(sum(gates.values()))
    critical=["h2_2025_cum_positive","h2_2025_episodes_ge_4","h2_2025_all_loeo_positive","h2_2025_cluster_bootstrap_ci_low_gt_0","y2026_jan_jul_cum_positive"]
    if n>=10 and all(gates[k] for k in critical): v="PASS_BROAD_EPISODE_INDEPENDENT_EDGE"
    elif gates["h2_2025_cum_positive"] and gates["y2026_jan_jul_cum_positive"]: v="WATCH_POSITIVE_BUT_CONCENTRATED"
    else: v="FAIL_PROFIT_CONCENTRATED_OR_UNSTABLE"
    return dict(verdict=v,gates_passed=n,gates_total=len(gates),gates=gates)


def report(summ,months,dirs,eps,conc,lomo,loeo,boots,gapa,v):
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","","Role: structural concentration/episode-independence diagnosis of the exact frozen reversal branch; no new gate.","","## Frozen-window reconciliation","","| Window | Signals | Fills | Cum R | EV/op | PF |","|---|---:|---:|---:|---:|---:|"]
    for _,r in summ.iterrows(): lines.append(f"| {r.window} | {int(r.signals)} | {int(r.fills)} | {r.cum_R:+.2f} | {r.ev_R:+.3f} | {fmtpf(r.profit_factor)} |")
    lines += ["","## 2025 H2 monthly breadth","","| Month | Signals | Fills | Cum R | EV | PF |","|---|---:|---:|---:|---:|---:|"]
    for _,r in months[months.window=="2025_H2"].iterrows(): lines.append(f"| {r.month} | {int(r.signals)} | {int(r.fills)} | {r.cum_R:+.2f} | {r.ev_R:+.3f} | {fmtpf(r.profit_factor)} |")
    lines += ["","## Direction split","","| Window | Reversal side | Signals | Fills | Cum R | EV | PF |","|---|---|---:|---:|---:|---:|---:|"]
    for _,r in dirs.iterrows(): lines.append(f"| {r.window} | {r.reversal_trade_side} | {int(r.signals)} | {int(r.fills)} | {r.cum_R:+.2f} | {r.ev_R:+.3f} | {fmtpf(r.profit_factor)} |")
    lines += ["","## Primary 7d episodes","","| Window | Episode | Start | End | Signals | Fills | Cum R | EV |","|---|---:|---|---|---:|---:|---:|---:|"]
    for _,r in eps.iterrows(): lines.append(f"| {r.window} | {int(r.episode_id)} | {pd.Timestamp(r.start).date()} | {pd.Timestamp(r.end).date()} | {int(r.signals)} | {int(r.fills)} | {r.cum_R:+.2f} | {r.ev_R:+.3f} |")
    lines += ["","## Concentration"]
    for _,r in conc.iterrows():
        lines.append(f"- **{r.window}**: gross positive {r.gross_positive_R:+.2f}R; top-1 winner **{r.top1_winner_share*100:.1f}%**; top-3 **{r.top3_winner_share*100:.1f}%**; top 7d episode **{r.top_episode_positive_share*100:.1f}%** of gross positive R.")
    lines += ["","## Leave-one-out robustness"]
    for w in ["2025_H2","2026_JAN_JUL"]:
        lm=lomo[lomo.window==w]; le=loeo[loeo.window==w]
        lines.append(f"- **{w}**: worst leave-one-month-out remaining R = **{lm.remaining_R.min():+.2f}R**; worst leave-one-episode-out remaining R = **{le.remaining_R.min():+.2f}R**." if len(le) else f"- **{w}**: insufficient episodes.")
    lines += ["","## Episode-cluster bootstrap"]
    for w,b in boots.items(): lines.append(f"- **{w}**: mean **{b['mean_R']:+.3f}R/op**, 95% cluster CI **[{b['ci025']:+.3f}, {b['ci975']:+.3f}]**, episodes={b['episodes']}.")
    lines += ["","## Episode-gap audit (descriptive only)","","| Window | Gap | Episodes | Positive | Negative | Top episode share | Worst LOEO R |","|---|---:|---:|---:|---:|---:|---:|"]
    for _,r in gapa.iterrows(): lines.append(f"| {r.window} | {int(r.gap_days)}d | {int(r.episodes)} | {int(r.positive_episodes)} | {int(r.negative_episodes)} | {r.top_episode_positive_share*100:.1f}% | {r.min_leave_one_episode_R:+.2f} |")
    lines += ["","## Gates"]
    for k,z in v["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} → {v['verdict']}**","","## Status","- 2025 H2/2026 were seen in earlier LABs; this is not a fresh holdout.","- 3d/14d episode definitions are audit-only and cannot rescue the primary 7d verdict.","- No live allocation is authorized by this LAB alone."]
    return "\n".join(lines)+"\n"


def main():
    s,meta=build_base()
    wins={k:subwin(s,k) for k in WINS}
    summ=pd.DataFrame([summary_row(k,d) for k,d in wins.items()])
    months=pd.concat([monthly_table(d,k) for k,d in wins.items()],ignore_index=True)
    dirs=pd.concat([direction_table(d,k) for k,d in wins.items()],ignore_index=True)
    eps=pd.concat([episode_table(d,k,7) for k,d in wins.items()],ignore_index=True)
    conc=pd.DataFrame([concentration(d,episode_table(d,k,7),k) for k,d in wins.items()])
    lomo=pd.concat([leave_one_month_out(d,k) for k,d in wins.items()],ignore_index=True)
    loeo=pd.concat([leave_one_episode_out(d,episode_table(d,k,7),k) for k,d in wins.items()],ignore_index=True)
    boots={k:cluster_bootstrap(d,k,7) for k,d in wins.items()}
    gapa=pd.concat([gap_audit(d,k) for k,d in wins.items()],ignore_index=True)
    v=verdict(summ,months,eps,conc,lomo,loeo,boots)

    s.to_csv(OUT/"all_frozen_selected_rev_signals.csv",index=False)
    summ.to_csv(OUT/"window_summary.csv",index=False)
    months.to_csv(OUT/"monthly_summary.csv",index=False)
    dirs.to_csv(OUT/"direction_summary.csv",index=False)
    eps.to_csv(OUT/"episode7d_summary.csv",index=False)
    conc.to_csv(OUT/"concentration_summary.csv",index=False)
    lomo.to_csv(OUT/"leave_one_month_out.csv",index=False)
    loeo.to_csv(OUT/"leave_one_episode_out.csv",index=False)
    gapa.to_csv(OUT/"episode_gap_audit.csv",index=False)
    (OUT/"cluster_bootstrap.json").write_text(json.dumps(boots,indent=2,allow_nan=True),encoding="utf-8")
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,allow_nan=True),encoding="utf-8")
    rep=report(summ,months,dirs,eps,conc,lomo,loeo,boots,gapa,v)
    (OUT/"REPORT.md").write_text(rep,encoding="utf-8")
    print(json.dumps(v,indent=2)); print(rep)

if __name__=="__main__": main()
