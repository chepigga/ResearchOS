from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

L150=loadmod("lab150",ROOT/"labs/LAB150_SELECTIVE_CONCURRENCY_OVERLAP_RISK_20261009/run_lab150.py")

OUT=Path("lab151_out");OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
RISK_PER_TRADE_PCT=0.25
BT=L150.BT;BO=L150.BO;BC=L150.BC

RULE_NAMES=[
    "ONE_POSITION",
    "SECOND_OPEN_MTM_GE0",
    "SECOND_MTM_GE0_SAME_SIDE",
    "SECOND_SAME_SIDE",
    "SECOND_ANY",
]

def mtm_r(row, bar_i, cost):
    entry=float(BO[int(row.entry_i)])
    side=int(row.side);atr=float(row.atr)
    return float(side*(BC[bar_i]-entry)/atr-(cost/10000.0)*entry/atr)

def accept_events(cost,rule_name):
    d=L150.raw_events(cost)
    active=[];rows=[];skipped=0
    for _,r in d.iterrows():
        now=pd.Timestamp(r.entry_time);now_i=int(r.entry_i)
        active=[x for x in active if pd.Timestamp(x.exit_time)>now]
        if len(active)==0:
            rows.append(r.to_dict());active=[r]
            continue
        if len(active)>=2:
            skipped+=1;continue
        op=active[0]
        allow=False
        if rule_name=="ONE_POSITION":
            allow=False
        elif rule_name=="SECOND_ANY":
            allow=True
        elif rule_name=="SECOND_SAME_SIDE":
            allow=int(op.side)==int(r.side)
        elif rule_name=="SECOND_OPEN_MTM_GE0":
            allow=mtm_r(op,now_i,cost)>=0
        elif rule_name=="SECOND_MTM_GE0_SAME_SIDE":
            allow=(mtm_r(op,now_i,cost)>=0) and (int(op.side)==int(r.side))
        else:
            raise ValueError(rule_name)
        if allow:
            rows.append(r.to_dict());active.append(r)
        else:
            skipped+=1
    t=pd.DataFrame(rows).sort_values(["entry_time","source"]).reset_index(drop=True)
    return t,skipped

def booked_stats(t):
    x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    q=t.sort_values("exit_time")
    ce=q.net_r.cumsum();dd=float((ce.cummax()-ce).max())
    a=pd.Timestamp(t.entry_time.min());b=pd.Timestamp(t.exit_time.max())
    months=max((b.year-a.year)*12+b.month-a.month+1,1)
    return dict(n=len(t),trades_month=len(t)/months,ev=float(x.mean()),
                pf=float(pos/neg) if neg>0 else np.inf,r_month=float(x.sum()/months),
                booked_dd_r=dd,booked_dd_pct=dd*RISK_PER_TRADE_PCT)

def equity_curve(t,cost):
    # Causal close-to-close MTM equity; intrabar exit bar uses final realized R.
    start_i=int(t.entry_i.min());end_i=int(t.exit_i.max())
    entries={}
    exits={}
    for rid,r in t.iterrows():
        entries.setdefault(int(r.entry_i),[]).append((rid,r))
        exits.setdefault(int(r.exit_i),[]).append((rid,r))
    active={}
    realized=0.0
    rows=[]
    max_open=0
    for i in range(start_i,end_i+1):
        if i in entries:
            for rid,r in entries[i]:
                active[rid]=r
        floating=0.0
        for rid,r in active.items():
            if i>=int(r.exit_i):
                floating+=float(r.net_r)
            else:
                floating+=mtm_r(r,i,cost)
        equity=realized+floating
        open_count=sum(1 for r in active.values() if i<int(r.exit_i))
        max_open=max(max_open,open_count)
        rows.append(dict(time=BT.iloc[i],bar_i=i,equity_r=equity,realized_r=realized,
                         floating_r=floating,open_count=open_count))
        if i in exits:
            # crystallize after marking this exit bar at final net_r; next bar starts realized.
            for rid,r in exits[i]:
                if rid in active:
                    realized+=float(r.net_r)
                    del active[rid]
    return pd.DataFrame(rows),max_open

def prop_metrics(eq):
    e=eq.copy()
    e["peak_r"]=e.equity_r.cummax()
    e["dd_r"]=e.peak_r-e.equity_r
    max_dd_r=float(e.dd_r.max())

    # Worst simultaneous floating basket P/L.
    min_float_r=float(e.floating_r.min())
    min_eq_r=float(e.equity_r.min())

    # Daily metrics based on UTC day boundaries.
    e["day"]=pd.to_datetime(e.time,utc=True).dt.floor("D")
    daily=[]
    prev_close=0.0
    for day,g in e.groupby("day",sort=True):
        g=g.sort_values("time")
        day_start_equity=prev_close
        min_equity=float(g.equity_r.min())
        max_equity=float(g.equity_r.max())
        # Prop-style day-start loss: day-start equity minus worst intraday equity.
        loss_from_day_start=max(0.0,day_start_equity-min_equity)
        # Also report intraday peak-to-trough inside same day.
        running_peak=np.maximum.accumulate(np.r_[day_start_equity,g.equity_r.to_numpy(float)])
        vals=np.r_[day_start_equity,g.equity_r.to_numpy(float)]
        intraday_dd=float(np.max(running_peak-vals))
        close_eq=float(g.equity_r.iloc[-1])
        daily.append(dict(day=day,day_start_r=day_start_equity,min_equity_r=min_equity,
                          max_equity_r=max_equity,close_equity_r=close_eq,
                          loss_from_day_start_r=loss_from_day_start,
                          intraday_peak_dd_r=intraday_dd))
        prev_close=close_eq
    d=pd.DataFrame(daily)
    return dict(
        max_mtm_dd_r=max_dd_r,
        max_mtm_dd_pct=max_dd_r*RISK_PER_TRADE_PCT,
        worst_floating_r=min_float_r,
        worst_floating_pct=min_float_r*RISK_PER_TRADE_PCT,
        min_equity_r=min_eq_r,
        max_daily_start_loss_r=float(d.loss_from_day_start_r.max()),
        max_daily_start_loss_pct=float(d.loss_from_day_start_r.max())*RISK_PER_TRADE_PCT,
        max_intraday_peak_dd_r=float(d.intraday_peak_dd_r.max()),
        max_intraday_peak_dd_pct=float(d.intraday_peak_dd_r.max())*RISK_PER_TRADE_PCT,
        days_gt_4pct=int((d.loss_from_day_start_r*RISK_PER_TRADE_PCT>4.0).sum()),
        days_gt_5pct=int((d.loss_from_day_start_r*RISK_PER_TRADE_PCT>5.0).sum()),
        daily_df=d
    )

summary=[];all_eq=[];all_daily=[];all_trades=[]
for cost in COSTS:
    for rule in RULE_NAMES:
        t,sk=accept_events(cost,rule)
        b=booked_stats(t)
        eq,max_open=equity_curve(t,cost)
        pm=prop_metrics(eq)
        row=dict(cost_bps=cost,rule=rule,skipped=sk,max_open_positions=max_open,
                 max_nominal_open_risk_pct=max_open*RISK_PER_TRADE_PCT,**b,
                 max_mtm_dd_r=pm["max_mtm_dd_r"],max_mtm_dd_pct=pm["max_mtm_dd_pct"],
                 worst_floating_r=pm["worst_floating_r"],worst_floating_pct=pm["worst_floating_pct"],
                 max_daily_start_loss_r=pm["max_daily_start_loss_r"],
                 max_daily_start_loss_pct=pm["max_daily_start_loss_pct"],
                 max_intraday_peak_dd_r=pm["max_intraday_peak_dd_r"],
                 max_intraday_peak_dd_pct=pm["max_intraday_peak_dd_pct"],
                 days_gt_4pct=pm["days_gt_4pct"],days_gt_5pct=pm["days_gt_5pct"])
        summary.append(row)

        et=eq.copy();et["rule"]=rule;et["cost_bps"]=cost;all_eq.append(et)
        dd=pm["daily_df"].copy();dd["rule"]=rule;dd["cost_bps"]=cost;all_daily.append(dd)
        tt=t.copy();tt["rule"]=rule;tt["cost_bps"]=cost;all_trades.append(tt)

S=pd.DataFrame(summary)
S.to_csv(OUT/"LAB151_summary.csv",index=False)
pd.concat(all_daily,ignore_index=True).to_csv(OUT/"LAB151_daily_dd.csv",index=False)
pd.concat(all_trades,ignore_index=True).to_csv(OUT/"LAB151_trades.csv",index=False)
# Equity curves are large; save compact selected fields only.
pd.concat(all_eq,ignore_index=True).to_csv(OUT/"LAB151_equity_curves.csv",index=False)

# Frozen screen: stress PF>=1.65, MTM DD<=5%, daily start loss<=4%, max nominal open risk<=0.50%, maximize R/mo.
stress=S[(S.cost_bps==7.5)&(S.pf>=1.65)&(S.max_mtm_dd_pct<=5.0)&
         (S.max_daily_start_loss_pct<=4.0)&(S.max_nominal_open_risk_pct<=0.50)].copy()
stress=stress.sort_values(["r_month","pf"],ascending=False)
winner=str(stress.iloc[0].rule) if len(stress) else "NONE"

lines=["# LAB151 — CONCURRENT MTM PROP-DD REPLAY","",
       "Universe frozen from LAB150: A + B3_HIGH + R48_HIGH + EARLY_EPISODE.",
       "Per-trade risk scale: 0.25%. Max tested concurrency: 2 positions.",
       "Equity is replayed bar-by-bar on BTC M5. Open positions are marked to M5 close; an exit bar is marked at the frozen realized trade result.",
       "Daily prop proxy: loss from UTC day-start equity to the day's minimum equity. Intraday peak-to-trough DD is also reported separately.",
       ""]
for cost in COSTS:
    lines.append(f"## {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].sort_values("r_month",ascending=False).iterrows():
        lines.append(
            f"- {r.rule}: N={int(r.n)} ({r.trades_month:.2f}/mo), PF={r.pf:.2f}, EV={r.ev:+.3f}R, "
            f"R/mo={r.r_month:+.2f}, MTM DD={r.max_mtm_dd_pct:.2f}%, daily-start loss={r.max_daily_start_loss_pct:.2f}%, "
            f"intraday peak DD={r.max_intraday_peak_dd_pct:.2f}%, worst floating={r.worst_floating_pct:.2f}%, "
            f"max open risk={r.max_nominal_open_risk_pct:.2f}%, days>4%={int(r.days_gt_4pct)}, days>5%={int(r.days_gt_5pct)}")
lines += ["","## Frozen decision screen",
          "Require stress PF>=1.65, MTM DD<=5%, max day-start loss<=4%, and nominal open risk<=0.50%; maximize stress R/month.",
          f"Winner: **{winner}**.",
          "",
          "Important: this is still BTC TRAIN discovery. Daily-loss calculation is a prop-style proxy on UTC boundaries; a broker/prop firm's exact reset timezone and equity rule must be applied before live sizing."]
(OUT/"LAB151_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB151_meta.json").write_text(json.dumps(dict(
    risk_per_trade_pct=RISK_PER_TRADE_PCT,costs=COSTS,rules=RULE_NAMES,winner=winner,
    daily_proxy="UTC day-start equity to daily minimum equity",
    caveat="BTC TRAIN discovery; exact prop reset timezone/rules not applied"
),indent=2))
print("\n".join(lines))
