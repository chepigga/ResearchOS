from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]

def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

L148=loadmod("lab148",ROOT/"labs/LAB148_ACTIVE_Z_RESCUE_ANATOMY_20261009/run_lab148.py")
L138=loadmod("lab138",ROOT/"labs/LAB138_A_B3HIGH_R48_PORTFOLIO_20261008/run_lab138.py")

OUT=Path("lab149_out");OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
RISK=0.25

# Frozen rescue candidate from LAB148.
RES=L148.df[L148.df.episode_age_min<=L148.thr["age_q40"]].copy().sort_values("entry_time")
# Note: LAB148 q40 is 5m on this TRAIN universe.

def rescue_rows(cost):
    rows=[]
    for _,r in RES.iterrows():
        net,reason,xi=L148.sim(int(r.entry_i),int(r.side),float(r.atr),cost)
        rows.append(dict(source="EARLY_EPISODE",entry_time=r.entry_time,exit_time=L148.BT.iloc[xi],
                         net_r=float(net),side="BUY" if int(r.side)>0 else "SELL",
                         signal_time=r.episode_start,anchor_time=r.anchor_time,
                         episode_age_min=float(r.episode_age_min)))
    return pd.DataFrame(rows)

def a_rows(cost):
    pool=L138.A.make_events(cost)
    s=pool[pool.engine=="A"].copy()
    return s.rename(columns={"engine":"source"})[["source","entry_time","exit_time","net_r"]]

def canonical_full(cost):
    # Exact LAB138 canonical portfolio: A + B3_HIGH + R48_HIGH.
    return L138.portfolio(cost,L138.r48_high,"R48_HIGH").copy()

def replay(pool,priority):
    s=pool.copy()
    s["pri"]=s.source.map(priority).fillna(99)
    s=s.sort_values(["entry_time","pri"])
    rows=[];open_until=pd.Timestamp.min.tz_localize("UTC");skipped=0
    for _,r in s.iterrows():
        if pd.Timestamp(r.entry_time)<open_until:
            skipped+=1;continue
        rows.append(r);open_until=pd.Timestamp(r.exit_time)
    return pd.DataFrame(rows),skipped

def stats(t):
    x=t.net_r.to_numpy(float)
    pos=x[x>0].sum();neg=-x[x<0].sum()
    ce=np.cumsum(x);dd=float(np.max(np.maximum.accumulate(ce)-ce))
    a=pd.Timestamp(t.entry_time.min());b=pd.Timestamp(t.exit_time.max())
    months=max((b.year-a.year)*12+b.month-a.month+1,1)
    return dict(n=len(t),trades_month=len(t)/months,ev=float(x.mean()),
                pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),
                total_r=float(x.sum()),r_month=float(x.sum()/months),
                dd_r=dd,dd_pct=dd*RISK)

def nearest_hours(ref_times,t):
    arr=pd.to_datetime(ref_times,utc=True).astype("int64").to_numpy()
    if len(arr)==0:return np.inf
    x=pd.Timestamp(t)
    if x.tzinfo is None:x=x.tz_localize("UTC")
    else:x=x.tz_convert("UTC")
    xv=int(x.value);k=np.searchsorted(arr,xv);ds=[]
    if k<len(arr):ds.append(abs(arr[k]-xv)/3.6e12)
    if k>0:ds.append(abs(arr[k-1]-xv)/3.6e12)
    return min(ds) if ds else np.inf

summary=[];trades=[];inc=[];overlap=[]
for cost in COSTS:
    rr=rescue_rows(cost)

    # A-only baseline, then A + rescue.
    a0,_=replay(a_rows(cost),{"A":0})
    ar,skip_ar=replay(pd.concat([a_rows(cost),rr],ignore_index=True,sort=False),
                      {"A":0,"EARLY_EPISODE":1})

    # Full canonical LAB138 baseline, then full + rescue.
    full=canonical_full(cost)
    if cost==2.81 and len(full)!=282:
        raise RuntimeError(f"LAB138 canonical parity failed: {len(full)} != 282")
    fr,skip_fr=replay(pd.concat([full,rr],ignore_index=True,sort=False),
                      {"A":0,"B3_HIGH":1,"R48_HIGH":2,"EARLY_EPISODE":3})

    for name,t in [("A_ONLY",a0),("A_PLUS_EARLY_EPISODE",ar),
                   ("FULL_CANONICAL",full),("FULL_PLUS_EARLY_EPISODE",fr)]:
        s=stats(t);s.update(cost_bps=cost,portfolio=name)
        summary.append(s)
        tt=t.copy();tt["cost_bps"]=cost;tt["portfolio"]=name;trades.append(tt)

    # Attribution of accepted rescue trades.
    for name,t in [("A_PLUS_EARLY_EPISODE",ar),("FULL_PLUS_EARLY_EPISODE",fr)]:
        add=t[t.source=="EARLY_EPISODE"].copy()
        if len(add):
            q=stats(add)
            summary.append(dict(cost_bps=cost,portfolio=name+"_RESCUE_ATTR",
                                n=q["n"],trades_month=q["trades_month"],ev=q["ev"],pf=q["pf"],wr=q["wr"],
                                total_r=q["total_r"],r_month=q["r_month"],dd_r=q["dd_r"],dd_pct=q["dd_pct"]))

    for base_name,new_name,base,new in [
        ("A_ONLY","A_PLUS_EARLY_EPISODE",a0,ar),
        ("FULL_CANONICAL","FULL_PLUS_EARLY_EPISODE",full,fr)]:
        b=stats(base);n=stats(new)
        inc.append(dict(cost_bps=cost,comparison=new_name,
                        delta_n=n["n"]-b["n"],delta_trades_month=n["trades_month"]-b["trades_month"],
                        delta_ev=n["ev"]-b["ev"],delta_pf=n["pf"]-b["pf"],
                        delta_r_month=n["r_month"]-b["r_month"],
                        delta_dd_r=n["dd_r"]-b["dd_r"],delta_dd_pct=n["dd_pct"]-b["dd_pct"]))

    if cost==2.81:
        for refname,ref in [("A_ONLY",a0),("FULL_CANONICAL",full)]:
            rtimes=pd.to_datetime(ref.entry_time,utc=True).sort_values()
            z=rr.copy();z["nearest_h"]=z.entry_time.map(lambda t:nearest_hours(rtimes,t))
            overlap.append(dict(reference=refname,raw_rescue=len(z),
                                within_6h=int((z.nearest_h<=6).sum()),within_6h_pct=float((z.nearest_h<=6).mean()),
                                within_12h=int((z.nearest_h<=12).sum()),within_12h_pct=float((z.nearest_h<=12).mean()),
                                unique_gt12h=int((z.nearest_h>12).sum()),unique_gt12h_pct=float((z.nearest_h>12).mean())))

S=pd.DataFrame(summary)
# Main portfolios only first
main=S[~S.portfolio.str.endswith("_RESCUE_ATTR")].copy()
main.to_csv(OUT/"LAB149_portfolio_summary.csv",index=False)
S[S.portfolio.str.endswith("_RESCUE_ATTR")].to_csv(OUT/"LAB149_rescue_attribution.csv",index=False)
pd.DataFrame(inc).to_csv(OUT/"LAB149_increment.csv",index=False)
pd.DataFrame(overlap).to_csv(OUT/"LAB149_overlap.csv",index=False)
pd.concat(trades,ignore_index=True).to_csv(OUT/"LAB149_portfolio_trades.csv",index=False)

lines=["# LAB149 — A + EARLY_EPISODE RESCUE PORTFOLIO","",
       "BTC TRAIN only. EARLY_EPISODE definition is frozen from LAB148 before this portfolio test.",
       f"Frozen rescue rule: ACTIVE_Z_RESCUE with episode_age <= q40 = {L148.thr['age_q40']:.0f} minutes.",
       "Execution unchanged: SL=1 H1ATR / TP=3R / max48h.",
       "One-position chronology. Priority: A > B3_HIGH > R48_HIGH > EARLY_EPISODE.",
       f"Raw EARLY_EPISODE candidate events: {len(RES)}.",
       "",
       "## Temporal overlap @2.81bps"]
for o in overlap:
    lines.append(f"- vs {o['reference']}: <=6h {o['within_6h']} ({o['within_6h_pct']:.1%}), <=12h {o['within_12h']} ({o['within_12h_pct']:.1%}), unique >12h {o['unique_gt12h']} ({o['unique_gt12h_pct']:.1%})")

for cost in COSTS:
    lines += ["",f"## {cost:.2f}bps"]
    for p in ["A_ONLY","A_PLUS_EARLY_EPISODE","FULL_CANONICAL","FULL_PLUS_EARLY_EPISODE"]:
        r=main[(main.cost_bps==cost)&(main.portfolio==p)].iloc[0]
        lines.append(f"- {p}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R / {r.dd_pct:.2f}%")
    lines.append("  Increment:")
    ii=pd.DataFrame(inc)[pd.DataFrame(inc).cost_bps==cost]
    for _,r in ii.iterrows():
        lines.append(f"  - {r.comparison}: +{int(r.delta_n)} trades, {r.delta_trades_month:+.2f}/mo, EV delta {r.delta_ev:+.3f}R, PF delta {r.delta_pf:+.2f}, R/mo {r.delta_r_month:+.2f}, DD {r.delta_dd_pct:+.2f}%")

lines += ["","## Decision rule",
          "Promote EARLY_EPISODE only if it adds meaningful accepted frequency and preserves/improves the full canonical portfolio at both costs.",
          "Research target: full portfolio stress PF >=1.45, positive incremental R/month, and no disproportionate DD increase.",
          "This is a composition test on BTC TRAIN, not fresh validation."]
(OUT/"LAB149_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB149_meta.json").write_text(json.dumps(dict(
    rescue_rule=f"ACTIVE_Z_RESCUE episode_age <= {L148.thr['age_q40']:.0f} minutes",
    priority="A > B3_HIGH > R48_HIGH > EARLY_EPISODE",
    risk_pct=RISK,
    costs=COSTS,
    caveat="BTC TRAIN composition test only"
),indent=2))
print("\n".join(lines))
