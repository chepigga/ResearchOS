from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

L150=loadmod("lab150",ROOT/"labs/LAB150_SELECTIVE_CONCURRENCY_OVERLAP_RISK_20261009/run_lab150.py")
OUT=Path("lab154_out");OUT.mkdir(exist_ok=True)

BT=L150.BT;BO=L150.BO;BH=L150.BH;BL=L150.BL;BC=L150.BC;BA=L150.BA
COSTS=[2.81,7.5]
RISK=0.25
MAX_H=48
PRI={"A":0,"B3_HIGH":1,"R48_HIGH":2,"EARLY_EPISODE":3}
VARIANTS=["TP3","TP4","HALF_TP3_TRAIL1","HALF_TP3_LOCK2"]

def raw_signals(cost):
    d=L150.raw_events(cost).copy()
    # use entry anatomy only; discard frozen TP3 outcome
    return d[["source","entry_time","entry_i","side","atr","pri"]].copy().sort_values(["entry_time","pri"]).reset_index(drop=True)

def path_trade(r,cost,variant):
    ei=int(r.entry_i); side=int(r.side); atr=float(r.atr); entry=float(BO[ei])
    sl0=entry-side*atr; end=min(ei+MAX_H*12-1,len(BT)-1)
    cost_r=(cost/10000.0)*entry/atr
    tp3=entry+side*3*atr; tp4=entry+side*4*atr
    partial_idx=None; realized_half=0.0; runner_stop=None; best=None
    reason="TIME"; xi=end; gross=side*(BC[end]-entry)/atr

    if variant in ("TP3","TP4"):
        target=tp3 if variant=="TP3" else tp4
        target_r=3.0 if variant=="TP3" else 4.0
        for j in range(ei,end+1):
            hs=(BL[j]<=sl0) if side>0 else (BH[j]>=sl0)
            ht=(BH[j]>=target) if side>0 else (BL[j]<=target)
            if hs and ht:
                gross=-1.0; reason="BOTH_STOP_FIRST"; xi=j; break
            if hs:
                gross=-1.0; reason="SL"; xi=j; break
            if ht:
                gross=target_r; reason=f"TP{int(target_r)}"; xi=j; break
        return dict(exit_i=xi,exit_time=BT.iloc[xi],net_r=float(gross-cost_r),reason=reason,
                    partial_i=None,variant=variant,entry_price=entry,atr=atr,side=side,cost_r=cost_r)

    # partial runner variants
    for j in range(ei,end+1):
        if partial_idx is None:
            hs=(BL[j]<=sl0) if side>0 else (BH[j]>=sl0)
            ht=(BH[j]>=tp3) if side>0 else (BL[j]<=tp3)
            if hs and ht:
                gross=-1.0; reason="BOTH_STOP_FIRST"; xi=j; break
            if hs:
                gross=-1.0; reason="SL"; xi=j; break
            if ht:
                partial_idx=j
                realized_half=1.5
                # Runner management begins next bar. For trail, initialize from completed TP bar extreme.
                if variant=="HALF_TP3_TRAIL1":
                    best=float(BH[j] if side>0 else BL[j])
                    runner_stop=best-side*atr
                else:
                    runner_stop=entry+side*2*atr
                continue
        else:
            # apply stop based only on information known before/in current bar
            hs=(BL[j]<=runner_stop) if side>0 else (BH[j]>=runner_stop)
            if hs:
                runner_r=side*(runner_stop-entry)/atr
                gross=realized_half+0.5*runner_r
                reason="RUNNER_STOP"; xi=j; break
            if variant=="HALF_TP3_TRAIL1":
                # update after evaluating current bar stop to avoid same-bar lookahead
                if side>0:
                    best=max(float(best),float(BH[j]))
                    runner_stop=max(float(runner_stop),best-atr)
                else:
                    best=min(float(best),float(BL[j]))
                    runner_stop=min(float(runner_stop),best+atr)
    else:
        if partial_idx is None:
            gross=side*(BC[end]-entry)/atr
        else:
            runner_r=side*(BC[end]-entry)/atr
            gross=realized_half+0.5*runner_r
            reason="TIME_RUNNER"
        xi=end
    return dict(exit_i=xi,exit_time=BT.iloc[xi],net_r=float(gross-cost_r),reason=reason,
                partial_i=partial_idx,variant=variant,entry_price=entry,atr=atr,side=side,cost_r=cost_r)

def mtm_total(tr,bar_i,cost):
    entry=float(tr.entry_price);atr=float(tr.atr);side=int(tr.side);cost_r=float(tr.cost_r)
    if tr.variant in ("TP3","TP4"):
        return float(side*(BC[bar_i]-entry)/atr-cost_r)
    pi=tr.partial_i
    if pi is None or bar_i<=int(pi):
        return float(side*(BC[bar_i]-entry)/atr-cost_r)
    return float(1.5+0.5*side*(BC[bar_i]-entry)/atr-cost_r)

def replay(cost,variant):
    raw=raw_signals(cost)
    cache={}
    accepted=[]
    active=[]
    skipped=0
    for idx,r in raw.iterrows():
        now=pd.Timestamp(r.entry_time); now_i=int(r.entry_i)
        # remove exited positions
        active=[x for x in active if int(x.exit_i)>now_i]
        key=(int(r.entry_i),str(r.source),int(r.side),float(r.atr))
        if key not in cache:
            q=r.to_dict(); q.update(path_trade(r,cost,variant)); cache[key]=q
        cand=pd.Series(cache[key])
        allow=False
        if len(active)==0:
            allow=True
        elif len(active)==1:
            op=active[0]
            allow=(int(op.side)==int(cand.side) and mtm_total(op,now_i,cost)>=0)
        if allow:
            accepted.append(cand.to_dict());active.append(cand)
        else:
            skipped+=1
    t=pd.DataFrame(accepted).sort_values(["entry_time","pri"]).reset_index(drop=True)
    return t,skipped

def stats(t):
    x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    ce=np.cumsum(x);dd=float(np.max(np.maximum.accumulate(ce)-ce))
    a=pd.Timestamp(t.entry_time.min());b=pd.Timestamp(t.exit_time.max())
    months=max((b.year-a.year)*12+b.month-a.month+1,1)
    return dict(n=len(t),trades_month=len(t)/months,ev=float(x.mean()),
                pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),
                total_r=float(x.sum()),r_month=float(x.sum()/months),booked_dd_r=dd,booked_dd_pct=dd*RISK)

def equity_curve(t,cost):
    start=int(t.entry_i.min());end=int(t.exit_i.max())
    by_entry={};by_exit={}
    for rid,r in t.iterrows():
        by_entry.setdefault(int(r.entry_i),[]).append((rid,r))
        by_exit.setdefault(int(r.exit_i),[]).append((rid,r))
    active={};realized=0.0;rows=[]
    for i in range(start,end+1):
        for rid,r in by_entry.get(i,[]):active[rid]=r
        floating=0.0
        for rid,r in active.items():
            if i>=int(r.exit_i): floating+=float(r.net_r)
            else: floating+=mtm_total(r,i,cost)
        eq=realized+floating
        rows.append(dict(time=BT.iloc[i],equity_r=eq,realized_r=realized,floating_r=floating,open_count=sum(i<int(r.exit_i) for r in active.values())))
        for rid,r in by_exit.get(i,[]):
            if rid in active:
                realized+=float(r.net_r);del active[rid]
    return pd.DataFrame(rows)

def mtm_metrics(eq):
    e=eq.copy();e["peak"]=e.equity_r.cummax();e["dd"]=e.peak-e.equity_r
    maxdd=float(e.dd.max())
    e["day"]=pd.to_datetime(e.time,utc=True).dt.floor("D")
    prev=0.0;max_day=0.0;max_intra=0.0
    for _,g in e.groupby("day"):
        vals=np.r_[prev,g.equity_r.to_numpy(float)]
        max_day=max(max_day,max(0.0,prev-float(g.equity_r.min())))
        rp=np.maximum.accumulate(vals);max_intra=max(max_intra,float(np.max(rp-vals)))
        prev=float(g.equity_r.iloc[-1])
    return dict(mtm_dd_r=maxdd,mtm_dd_pct=maxdd*RISK,daily_start_loss_pct=max_day*RISK,
                intraday_peak_dd_pct=max_intra*RISK,worst_floating_pct=float(e.floating_r.min())*RISK)

summary=[];attrib=[];alltr=[]
for cost in COSTS:
    for v in VARIANTS:
        t,sk=replay(cost,v);s=stats(t);m=mtm_metrics(equity_curve(t,cost))
        s.update(cost_bps=cost,variant=v,skipped=sk,**m);summary.append(s)
        tt=t.copy();tt["cost_bps"]=cost;tt["variant_name"]=v;alltr.append(tt)
        for src,g in t.groupby("source"):
            q=stats(g)
            attrib.append(dict(cost_bps=cost,variant=v,source=src,n=q["n"],ev=q["ev"],pf=q["pf"],total_r=q["total_r"]))

S=pd.DataFrame(summary);A=pd.DataFrame(attrib)
S.to_csv(OUT/"LAB154_summary.csv",index=False)
A.to_csv(OUT/"LAB154_engine_attribution.csv",index=False)
pd.concat(alltr,ignore_index=True).to_csv(OUT/"LAB154_trades.csv",index=False)

# frozen selection screen on stress: PF>=1.75, MTM DD<=5%, daily proxy<=2%, maximize R/mo.
rank=S[(S.cost_bps==7.5)&(S.pf>=1.75)&(S.mtm_dd_pct<=5.0)&(S.daily_start_loss_pct<=2.0)].sort_values(["r_month","pf"],ascending=False)
winner=str(rank.iloc[0].variant) if len(rank) else "TP3"

lines=["# LAB154 — RUNNER / PROFIT-TAIL FULL CHRONOLOGY REPLAY","",
       "Signals and entry logic are frozen from the 2026-10-09 baseline. Exit changes are replayed from raw signals, so changed holding time can block/unblock later trades.",
       "Portfolio rule remains SECOND_MTM_GE0_SAME_SIDE, max 2 positions, 0.25% risk per position.",
       ""]
for cost in COSTS:
    lines.append(f"## {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].sort_values("r_month",ascending=False).iterrows():
        lines.append(f"- {r.variant}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, MTM DD={r.mtm_dd_pct:.2f}%, daily={r.daily_start_loss_pct:.2f}%, skipped={int(r.skipped)}")
    lines.append("  Engine attribution:")
    for _,r in A[A.cost_bps==cost].sort_values(["variant","source"]).iterrows():
        lines.append(f"  - {r.variant} / {r.source}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, total={r.total_r:+.1f}R")
lines += ["",f"Frozen screen winner: **{winner}**.",
          "This is still TRAIN/development research; winner is a candidate for LAB155 interaction testing, not a production promotion."]
(OUT/"LAB154_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB154_meta.json").write_text(json.dumps(dict(winner=winner,variants=VARIANTS,
  selection="stress PF>=1.75, MTM DD<=5%, daily<=2%, maximize R/mo",
  caveat="TRAIN full chronology replay"),indent=2))
print("\n".join(lines))
