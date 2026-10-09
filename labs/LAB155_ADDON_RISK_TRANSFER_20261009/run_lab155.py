from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

L150=loadmod("lab150",ROOT/"labs/LAB150_SELECTIVE_CONCURRENCY_OVERLAP_RISK_20261009/run_lab150.py")
OUT=Path("lab155_out");OUT.mkdir(exist_ok=True)

BT=L150.BT;BO=L150.BO;BH=L150.BH;BL=L150.BL;BC=L150.BC
COSTS=[2.81,7.5]
RISK=0.25
MAX_H_BARS=48*12
PRI={"A":0,"B3_HIGH":1,"R48_HIGH":2,"EARLY_EPISODE":3}
MODES=["TP3_NO_TRANSFER","LOCK2_NO_TRANSFER","LOCK2_BE","LOCK2_BE_COSTS","LOCK2_LOCK025"]

def raw_signals(cost):
    d=L150.raw_events(cost).copy()
    return d[["source","entry_time","entry_i","side","atr","pri"]].copy().sort_values(["entry_i","pri"]).reset_index(drop=True)

def init_pos(r,cost,exit_mode):
    ei=int(r.entry_i);side=int(r.side);atr=float(r.atr);entry=float(BO[ei])
    return dict(source=str(r.source),pri=int(r.pri),entry_i=ei,entry_time=BT.iloc[ei],side=side,atr=atr,entry=entry,
                stop_r=-1.0,tp_r=3.0,partial=False,realized_half=0.0,
                cost_r=(cost/10000.0)*entry/atr,end_i=min(ei+MAX_H_BARS-1,len(BT)-1),
                exit_mode=exit_mode,addon_parent=False,exit_i=None,exit_time=None,net_r=None,reason=None)

def total_mtm_at_open(p,i):
    px=float(BO[i]);r=int(p["side"])*(px-float(p["entry"]))/float(p["atr"])
    if p["partial"]:
        return 1.5+0.5*r-float(p["cost_r"])
    return r-float(p["cost_r"])

def total_mtm_at_close(p,i):
    px=float(BC[i]);r=int(p["side"])*(px-float(p["entry"]))/float(p["atr"])
    if p["partial"]:
        return 1.5+0.5*r-float(p["cost_r"])
    return r-float(p["cost_r"])

def stop_price(p):
    return float(p["entry"])+int(p["side"])*float(p["stop_r"])*float(p["atr"])

def finish(p,i,gross,reason):
    p["exit_i"]=i;p["exit_time"]=BT.iloc[i];p["net_r"]=float(gross-float(p["cost_r"]));p["reason"]=reason
    return p

def evaluate_bar(p,i):
    side=int(p["side"]);entry=float(p["entry"]);atr=float(p["atr"]);sp=stop_price(p)
    # TP3 baseline
    if p["exit_mode"]=="TP3":
        tp=entry+side*3*atr
        hs=(BL[i]<=sp) if side>0 else (BH[i]>=sp)
        ht=(BH[i]>=tp) if side>0 else (BL[i]<=tp)
        if hs and ht:return finish(p,i,float(p["stop_r"]),"BOTH_STOP_FIRST")
        if hs:return finish(p,i,float(p["stop_r"]),"SL")
        if ht:return finish(p,i,3.0,"TP3")
    else:
        # HALF TP3 + runner lock2
        if not p["partial"]:
            tp=entry+side*3*atr
            hs=(BL[i]<=sp) if side>0 else (BH[i]>=sp)
            ht=(BH[i]>=tp) if side>0 else (BL[i]<=tp)
            if hs and ht:return finish(p,i,float(p["stop_r"]),"BOTH_STOP_FIRST")
            if hs:return finish(p,i,float(p["stop_r"]),"SL")
            if ht:
                p["partial"]=True;p["realized_half"]=1.5
                # management becomes effective from next bar, but store now
                p["stop_r"]=max(float(p["stop_r"]),2.0)
                return None
        else:
            sp=stop_price(p)
            hs=(BL[i]<=sp) if side>0 else (BH[i]>=sp)
            if hs:
                gross=1.5+0.5*float(p["stop_r"])
                return finish(p,i,gross,"RUNNER_STOP")
    # time exit at close
    if i>=int(p["end_i"]):
        rr=side*(float(BC[i])-entry)/atr
        gross=rr if p["exit_mode"]=="TP3" else (rr if not p["partial"] else 1.5+0.5*rr)
        return finish(p,i,gross,"TIME" if not p["partial"] else "TIME_RUNNER")
    return None

def transfer_first_stop(p,mode):
    # Never worsen an already protected runner stop.
    if mode=="LOCK2_BE":
        target=0.0
    elif mode=="LOCK2_BE_COSTS":
        target=float(p["cost_r"])
    elif mode=="LOCK2_LOCK025":
        target=0.25
    else:
        return
    p["stop_r"]=max(float(p["stop_r"]),target)

def replay(cost,mode):
    raw=raw_signals(cost)
    by_i={}
    for _,r in raw.iterrows():by_i.setdefault(int(r.entry_i),[]).append(r)
    exit_mode="TP3" if mode=="TP3_NO_TRANSFER" else "LOCK2"
    active=[];closed=[];skipped=0;addons=0
    start=int(raw.entry_i.min());end=int(raw.entry_i.max())+MAX_H_BARS
    end=min(end,len(BT)-1)
    equity_rows=[];realized=0.0

    for i in range(start,end+1):
        # Entries at current open are decided before current-bar high/low is known.
        sigs=by_i.get(i,[])
        if sigs:
            sigs=sorted(sigs,key=lambda r:int(r.pri))
            for r in sigs:
                allow=False;is_addon=False
                if len(active)==0:
                    allow=True
                elif len(active)==1:
                    p=active[0]
                    allow=(int(p["side"])==int(r.side) and total_mtm_at_open(p,i)>=0)
                    is_addon=allow
                if allow:
                    if is_addon:
                        addons+=1
                        if mode in ("LOCK2_BE","LOCK2_BE_COSTS","LOCK2_LOCK025"):
                            transfer_first_stop(active[0],mode)
                    np_=init_pos(r,cost,exit_mode);np_["addon_parent"]=is_addon
                    active.append(np_)
                else:
                    skipped+=1

        # Evaluate current bar after entries. For a newly opened position, same-bar SL/TP
        # is allowed because the trade exists from the open.
        still=[]
        for p in active:
            done=evaluate_bar(p,i)
            if done is None:
                still.append(p)
            else:
                closed.append(done);realized+=float(done["net_r"])
        active=still

        # MTM equity at bar close.
        floating=sum(total_mtm_at_close(p,i) for p in active)
        equity_rows.append(dict(time=BT.iloc[i],equity_r=realized+floating,realized_r=realized,
                                floating_r=floating,open_count=len(active)))

        if i>int(raw.entry_i.max()) and not active:
            break

    t=pd.DataFrame(closed)
    eq=pd.DataFrame(equity_rows)
    return t,eq,skipped,addons

def stats(t,eq):
    x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    a=pd.Timestamp(t.entry_time.min());b=pd.Timestamp(t.exit_time.max())
    months=max((b.year-a.year)*12+b.month-a.month+1,1)
    e=eq.copy();e["peak"]=e.equity_r.cummax();e["dd"]=e.peak-e.equity_r
    maxdd=float(e.dd.max())
    e["day"]=pd.to_datetime(e.time,utc=True).dt.floor("D")
    prev=0.0;max_day=0.0;max_intra=0.0
    for _,g in e.groupby("day"):
        vals=np.r_[prev,g.equity_r.to_numpy(float)]
        max_day=max(max_day,max(0.0,prev-float(g.equity_r.min())))
        rp=np.maximum.accumulate(vals);max_intra=max(max_intra,float(np.max(rp-vals)))
        prev=float(g.equity_r.iloc[-1])
    return dict(n=len(t),trades_month=len(t)/months,ev=float(x.mean()),
                pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),
                total_r=float(x.sum()),r_month=float(x.sum()/months),
                mtm_dd_r=maxdd,mtm_dd_pct=maxdd*RISK,daily_start_loss_pct=max_day*RISK,
                intraday_peak_dd_pct=max_intra*RISK,worst_floating_pct=float(e.floating_r.min())*RISK)

summary=[];attrib=[];alltr=[]
for cost in COSTS:
    for mode in MODES:
        t,eq,sk,adds=replay(cost,mode);s=stats(t,eq);s.update(cost_bps=cost,mode=mode,skipped=sk,addons=adds);summary.append(s)
        tt=t.copy();tt["cost_bps"]=cost;tt["mode"]=mode;alltr.append(tt)
        for src,g in t.groupby("source"):
            x=g.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
            attrib.append(dict(cost_bps=cost,mode=mode,source=src,n=len(g),ev=float(x.mean()),
                               pf=float(pos/neg) if neg>0 else np.inf,total_r=float(x.sum())))

S=pd.DataFrame(summary);AT=pd.DataFrame(attrib)
S.to_csv(OUT/"LAB155_summary.csv",index=False)
AT.to_csv(OUT/"LAB155_engine_attribution.csv",index=False)
pd.concat(alltr,ignore_index=True).to_csv(OUT/"LAB155_trades.csv",index=False)

# stress screen: runner must beat TP3 R/mo; transfer candidate should reduce MTM DD or daily loss without >10% R/mo sacrifice vs LOCK2 no-transfer.
stress=S[S.cost_bps==7.5].copy()
base=stress[stress.mode=="LOCK2_NO_TRANSFER"].iloc[0]
cands=stress[stress.mode.isin(["LOCK2_BE","LOCK2_BE_COSTS","LOCK2_LOCK025"])].copy()
cands=cands[(cands.r_month>=0.90*base.r_month)&((cands.mtm_dd_pct<base.mtm_dd_pct)|(cands.daily_start_loss_pct<base.daily_start_loss_pct))]
cands=cands.sort_values(["mtm_dd_pct","r_month"],ascending=[True,False])
winner=str(cands.iloc[0].mode) if len(cands) else "LOCK2_NO_TRANSFER"

lines=["# LAB155 — ADD-ON RISK TRANSFER","",
       "Exact causal M5 event-loop replay. Add-on decision uses current entry OPEN, never the future close of that M5 bar.",
       "Base exit candidate from LAB154: 50% at 3R, remaining 50% protected at +2R after TP3.",
       "When a same-side add-on is opened, test moving the first position stop only at that moment.",
       ""]
for cost in COSTS:
    lines.append(f"## {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].sort_values("r_month",ascending=False).iterrows():
        lines.append(f"- {r.mode}: N={int(r.n)} ({r.trades_month:.2f}/mo), addons={int(r.addons)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, MTM DD={r.mtm_dd_pct:.2f}%, daily={r.daily_start_loss_pct:.2f}%, worst float={r.worst_floating_pct:.2f}%")
lines += ["",f"Frozen screen winner: **{winner}**.",
          "BE transfer never lowers an already tighter stop (for example, a runner already locked at +2R).",
          "This is TRAIN/development evidence. The exact-causal event loop supersedes earlier same-bar-close MTM gating when results differ."]
(OUT/"LAB155_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB155_meta.json").write_text(json.dumps(dict(winner=winner,modes=MODES,
    causal_fix="addon MTM evaluated at current M5 open; entries processed before current-bar exits",
    caveat="TRAIN/development"),indent=2))
print("\n".join(lines))
