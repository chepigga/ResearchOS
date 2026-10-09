from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

L149=loadmod("lab149",ROOT/"labs/LAB149_A_PLUS_EARLY_EPISODE_RESCUE_PORTFOLIO_20261009/run_lab149.py")
L148=L149.L148
L138=L149.L138
A134=L138.A
R=L138.R

OUT=Path("lab150_out");OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
RISK=0.25
BT=L148.BT;BO=L148.BO;BH=L148.BH;BL=L148.BL;BC=L148.BC;BA=L148.BA
IDX={pd.Timestamp(t):i for i,t in enumerate(BT)}

def ix(t):
    x=pd.Timestamp(t)
    if x.tzinfo is None:x=x.tz_localize("UTC")
    else:x=x.tz_convert("UTC")
    return int(IDX[x])

def sim_generic(ei,side,atr,cost):
    entry=float(BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+48*12-1,len(BT)-1)
    gross=side*(BC[end]-entry)/atr;reason="TIME";xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason="BOTH_STOP_FIRST";xi=j;break
        if hs:gross=-1;reason="SL";xi=j;break
        if ht:gross=3;reason="TP";xi=j;break
    return float(gross-(cost/10000.0)*entry/atr),reason,xi

def raw_events(cost):
    rows=[]
    # A raw
    for _,r in A134.a_ev.iterrows():
        ei=ix(r.entry_time);net,reason,xi=sim_generic(ei,int(r.side),float(r.atr),cost)
        rows.append(dict(source="A",entry_time=BT.iloc[ei],entry_i=ei,exit_time=BT.iloc[xi],exit_i=xi,
                         side=int(r.side),atr=float(r.atr),net_r=net,reason=reason))
    # B3 HIGH raw
    for _,r in A134.b_high.iterrows():
        ei=ix(r.entry_time);net,reason,xi=sim_generic(ei,int(r.side),float(r.atr),cost)
        rows.append(dict(source="B3_HIGH",entry_time=BT.iloc[ei],entry_i=ei,exit_time=BT.iloc[xi],exit_i=xi,
                         side=int(r.side),atr=float(r.atr),net_r=net,reason=reason))
    # R48 HIGH raw
    for _,r in L138.r48_high.iterrows():
        ei=ix(r.entry_time);net,reason,xi=sim_generic(ei,int(r.side),float(r.atr),cost)
        rows.append(dict(source="R48_HIGH",entry_time=BT.iloc[ei],entry_i=ei,exit_time=BT.iloc[xi],exit_i=xi,
                         side=int(r.side),atr=float(r.atr),net_r=net,reason=reason))
    # Rescue EARLY_EPISODE raw
    for _,r in L149.RES.iterrows():
        ei=ix(r.entry_time);net,reason,xi=sim_generic(ei,int(r.side),float(r.atr),cost)
        rows.append(dict(source="EARLY_EPISODE",entry_time=BT.iloc[ei],entry_i=ei,exit_time=BT.iloc[xi],exit_i=xi,
                         side=int(r.side),atr=float(r.atr),net_r=net,reason=reason))
    d=pd.DataFrame(rows)
    pri={"A":0,"B3_HIGH":1,"R48_HIGH":2,"EARLY_EPISODE":3}
    d["pri"]=d.source.map(pri)
    return d.sort_values(["entry_time","pri"]).reset_index(drop=True)

def mtm_r(openrow, now_i, cost):
    entry=float(BO[int(openrow.entry_i)]);side=int(openrow.side);atr=float(openrow.atr)
    r=side*(BC[now_i]-entry)/atr-(cost/10000.0)*entry/atr
    return float(r)

def one_position_audit(cost):
    d=raw_events(cost)
    accepted=[];blocked=[]
    current=None
    for _,r in d.iterrows():
        if current is None or pd.Timestamp(r.entry_time)>=pd.Timestamp(current.exit_time):
            current=r
            accepted.append(r.to_dict())
            continue
        now_i=int(r.entry_i)
        age_h=(pd.Timestamp(r.entry_time)-pd.Timestamp(current.entry_time)).total_seconds()/3600
        rem_h=(pd.Timestamp(current.exit_time)-pd.Timestamp(r.entry_time)).total_seconds()/3600
        mr=mtm_r(current,now_i,cost)
        blocked.append(dict(
            cost_bps=cost,blocked_source=r.source,blocked_entry_time=r.entry_time,blocked_side=int(r.side),
            blocked_net_r=float(r.net_r),blocked_reason=r.reason,
            open_source=current.source,open_entry_time=current.entry_time,open_exit_time=current.exit_time,
            open_side=int(current.side),open_final_net_r=float(current.net_r),
            same_side=bool(int(r.side)==int(current.side)),open_age_h=age_h,open_remaining_h=rem_h,
            open_mtm_r=mr,blocked_entry_i=int(r.entry_i),open_entry_i=int(current.entry_i)
        ))
    return pd.DataFrame(accepted),pd.DataFrame(blocked),d

def summarize(t):
    if t.empty:return dict(n=0,trades_month=0,ev=np.nan,pf=np.nan,r_month=0,dd_r=np.nan,dd_pct=np.nan)
    x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    # sort by exit realization for booked DD
    q=t.sort_values("exit_time")
    ce=q.net_r.cumsum();dd=float((ce.cummax()-ce).max())
    a=pd.Timestamp(t.entry_time.min());b=pd.Timestamp(t.exit_time.max())
    months=max((b.year-a.year)*12+b.month-a.month+1,1)
    return dict(n=len(t),trades_month=len(t)/months,ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                r_month=float(x.sum()/months),dd_r=dd,dd_pct=dd*RISK)

# Selective two-position simulations.
RULES={
 "ONE_POSITION":lambda openpos,new,now_i,cost:False,
 "SECOND_ANY":lambda openpos,new,now_i,cost:True,
 "SECOND_SAME_SIDE":lambda openpos,new,now_i,cost:int(openpos.side)==int(new.side),
 "SECOND_OPPOSITE_SIDE":lambda openpos,new,now_i,cost:int(openpos.side)!=int(new.side),
 "SECOND_OPEN_MTM_GE0":lambda openpos,new,now_i,cost:mtm_r(openpos,now_i,cost)>=0,
 "SECOND_OPEN_MTM_GE05":lambda openpos,new,now_i,cost:mtm_r(openpos,now_i,cost)>=0.5,
 "SECOND_OPEN_MTM_GE1":lambda openpos,new,now_i,cost:mtm_r(openpos,now_i,cost)>=1.0,
 "SECOND_OPEN_AGE_GE12H":lambda openpos,new,now_i,cost:(pd.Timestamp(new.entry_time)-pd.Timestamp(openpos.entry_time)).total_seconds()/3600>=12,
 "SECOND_OPEN_AGE_GE24H":lambda openpos,new,now_i,cost:(pd.Timestamp(new.entry_time)-pd.Timestamp(openpos.entry_time)).total_seconds()/3600>=24,
}

def selective(cost,rule_name):
    d=raw_events(cost)
    rule=RULES[rule_name]
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
        if rule(op,r,now_i,cost):
            rows.append(r.to_dict());active.append(r)
        else:
            skipped+=1
    return pd.DataFrame(rows),skipped

audit_rows=[];pair_rows=[];blocked_all=[];port_rows=[]
for cost in COSTS:
    acc,blk,raw=one_position_audit(cost)
    blocked_all.append(blk)
    # source/pair anatomy
    for (osrc,bsrc,same),g in blk.groupby(["open_source","blocked_source","same_side"]):
        x=g.blocked_net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
        pair_rows.append(dict(cost_bps=cost,open_source=osrc,blocked_source=bsrc,same_side=same,n=len(g),
                              ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                              win_rate=float((x>0).mean()),median_open_mtm_r=float(g.open_mtm_r.median()),
                              median_open_age_h=float(g.open_age_h.median()),median_remaining_h=float(g.open_remaining_h.median())))
    # blocked quality by causal state bins
    for label,mask in [
        ("ALL_BLOCKED",pd.Series(True,index=blk.index)),
        ("SAME_SIDE",blk.same_side),
        ("OPPOSITE_SIDE",~blk.same_side),
        ("OPEN_MTM_NEG",blk.open_mtm_r<0),
        ("OPEN_MTM_GE0",blk.open_mtm_r>=0),
        ("OPEN_MTM_GE05",blk.open_mtm_r>=0.5),
        ("OPEN_MTM_GE1",blk.open_mtm_r>=1.0),
        ("OPEN_AGE_GE12H",blk.open_age_h>=12),
        ("OPEN_AGE_GE24H",blk.open_age_h>=24),
    ]:
        g=blk[mask]
        if len(g)==0:continue
        x=g.blocked_net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
        audit_rows.append(dict(cost_bps=cost,group=label,n=len(g),ev=float(x.mean()),
                               pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),
                               r_total=float(x.sum()),median_open_mtm_r=float(g.open_mtm_r.median())))
    # source-level blocked
    for src,g in blk.groupby("blocked_source"):
        x=g.blocked_net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
        audit_rows.append(dict(cost_bps=cost,group="BLOCKED_"+src,n=len(g),ev=float(x.mean()),
                               pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),
                               r_total=float(x.sum()),median_open_mtm_r=float(g.open_mtm_r.median())))
    # portfolio rules
    for rn in RULES:
        t,sk=selective(cost,rn);s=summarize(t);s.update(cost_bps=cost,rule=rn,skipped=sk)
        port_rows.append(s)

AUD=pd.DataFrame(audit_rows);PAIR=pd.DataFrame(pair_rows);PORT=pd.DataFrame(port_rows)
AUD.to_csv(OUT/"LAB150_blocked_signal_quality.csv",index=False)
PAIR.to_csv(OUT/"LAB150_source_pair_anatomy.csv",index=False)
PORT.to_csv(OUT/"LAB150_selective_concurrency.csv",index=False)
pd.concat(blocked_all,ignore_index=True).to_csv(OUT/"LAB150_blocked_signals.csv",index=False)

# Frozen selection screen: stress PF>=1.65, R/mo > one-position, max 2 positions.
base=PORT[(PORT.cost_bps==7.5)&(PORT.rule=="ONE_POSITION")].iloc[0]
rank=PORT[(PORT.cost_bps==7.5)&(PORT.pf>=1.65)&(PORT.r_month>base.r_month)].sort_values(["r_month","pf"],ascending=False)
winner=str(rank.iloc[0].rule) if len(rank) else "NONE"

lines=["# LAB150 — SELECTIVE CONCURRENCY / OVERLAP-RISK AUDIT","",
       "Universe: frozen A + B3_HIGH + R48_HIGH + EARLY_EPISODE raw signals.",
       "Question: which profitable signals are blocked by an existing position, and can a second trade be allowed under a causal low-overlap-risk rule?",
       "All individual trades use frozen SL1 H1ATR / TP3R / 48h. Max concurrency tested = 2 positions.",
       "",
       "## Blocked-signal quality"]
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for _,r in AUD[AUD.cost_bps==cost].sort_values("ev",ascending=False).iterrows():
        lines.append(f"- {r.group}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, total={r.r_total:+.1f}R, median open MTM={r.median_open_mtm_r:+.2f}R")
lines += ["","## Selective concurrency"]
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for _,r in PORT[PORT.cost_bps==cost].sort_values("r_month",ascending=False).iterrows():
        lines.append(f"- {r.rule}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, booked DD={r.dd_pct:.2f}%, skipped={int(r.skipped)}")
lines += ["","## Source-pair anatomy @7.5bps"]
for _,r in PAIR[PAIR.cost_bps==7.5].sort_values(["pf","n"],ascending=False).iterrows():
    if r.n<5:continue
    ss="same" if r.same_side else "opposite"
    lines.append(f"- open {r.open_source} -> blocked {r.blocked_source} ({ss} side): N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.win_rate:.1%}, open MTM med={r.median_open_mtm_r:+.2f}R, age={r.median_open_age_h:.1f}h")
lines += ["","## Decision",
          f"Frozen stress selection screen winner: **{winner}**.",
          "A concurrency rule is only interesting if it raises stress R/month without collapsing PF. Booked DD is not full concurrent mark-to-market DD; any candidate still needs a proper MTM prop-DD replay.",
          "BTC TRAIN discovery only; no production promotion here."]
(OUT/"LAB150_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB150_meta.json").write_text(json.dumps(dict(
    universe="A+B3_HIGH+R48_HIGH+EARLY_EPISODE raw signals",
    max_concurrency=2,risk_per_trade_pct=RISK,costs=COSTS,winner=winner,
    caveat="TRAIN discovery; booked DD only, not full MTM concurrent DD"
),indent=2))
print("\n".join(lines))
