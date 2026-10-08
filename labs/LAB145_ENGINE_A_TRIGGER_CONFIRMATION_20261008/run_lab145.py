from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
spec=importlib.util.spec_from_file_location("lab124",SRC)
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)

OUT=Path("lab145_out");OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
MAX_H=48
SEARCH_BARS=72
BT=A.BT;BO=A.BO;BH=A.BH;BL=A.BL;BC=A.BC;BA=A.BA
# Frozen Engine A context only: TRAIN + CONT/REACCEL.
CTX=A.df[(A.df["split"]=="TRAIN") & (A.df.phase.isin(["CONT","REACCEL"]))].copy().reset_index(drop=True)

def first_swing3(i,side,min_delay_bars=0):
    start=i+1+min_delay_bars
    for j in range(start,min(i+SEARCH_BARS,len(BT)-2)+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:return j,ref
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:return j,ref
    return None,None

def acceptance_trigger(i,side,nclose=2,window=3):
    j1,ref=first_swing3(i,side,0)
    if j1 is None:return None
    cap=float(np.min(BL[i:j1+1])) if side>0 else float(np.max(BH[i:j1+1]))
    for j in range(j1,min(j1+12,len(BT)-2)+1):
        lo=max(j1,j-window+1)
        closes=BC[lo:j+1]
        ok=int(np.sum(closes>ref))>=nclose if side>0 else int(np.sum(closes<ref))>=nclose
        no_new=(np.min(BL[j1:j+1])>cap) if side>0 else (np.max(BH[j1:j+1])<cap)
        if ok and no_new:return j
    return None

def two_step(i,side,retrace_atr=0.10):
    j1,ref=first_swing3(i,side,0)
    if j1 is None:return None
    atr=float(BA[i])
    cap=float(np.min(BL[i:j1+1])) if side>0 else float(np.max(BH[i:j1+1]))
    fav=float(BH[j1]) if side>0 else float(BL[j1])
    pull=None;break_level=None
    end=min(i+SEARCH_BARS,len(BT)-2)
    for j in range(j1+1,end+1):
        if side>0:
            fav=max(fav,float(BH[j]))
            if float(L:=BL[j])<=fav-retrace_atr*atr:
                if L<=cap: return None
                pull=j;break_level=fav;break
        else:
            fav=min(fav,float(BL[j]))
            if float(H:=BH[j])>=fav+retrace_atr*atr:
                if H>=cap:return None
                pull=j;break_level=fav;break
    if pull is None:return None
    for j in range(pull+1,end+1):
        if side>0:
            if BL[j]<=cap:return None
            if BC[j]>break_level:return j
        else:
            if BH[j]>=cap:return None
            if BC[j]<break_level:return j
    return None

def build_variant(name):
    rows=[]
    for _,r in CTX.iterrows():
        i=int(r.signal_i);side=int(r.side);atr=float(r.atr)
        if name=="BASE_SWING3":
            j,_=first_swing3(i,side,0)
        elif name=="SWING3_MIN30":
            j,_=first_swing3(i,side,6)
        elif name=="SWING3_MIN60":
            j,_=first_swing3(i,side,12)
        elif name=="ACCEPT_2OF3":
            j=acceptance_trigger(i,side,2,3)
        elif name=="ACCEPT_3OF3":
            j=acceptance_trigger(i,side,3,3)
        elif name=="TWO_STEP_R10":
            j=two_step(i,side,.10)
        elif name=="TWO_STEP_R20":
            j=two_step(i,side,.20)
        else: raise ValueError(name)
        if j is None or j+1>=len(BT):continue
        ei=j+1
        rows.append(dict(signal_time=BT.iloc[i],trigger_time=BT.iloc[j],entry_time=BT.iloc[ei],
                         signal_i=i,trigger_i=j,entry_i=ei,side=side,atr=atr,
                         delay_min=(BT.iloc[ei]-BT.iloc[i]).total_seconds()/60))
    return pd.DataFrame(rows)

def sim_one(ei,side,atr,cost):
    entry=float(BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(BT)-1)
    gross=side*(BC[end]-entry)/atr;reason="TIME";xi=end;mfe=0.0;mae=0.0
    for j in range(ei,end+1):
        fav=((BH[j]-entry)*side/atr) if side>0 else ((entry-BL[j])/atr)
        adv=((entry-BL[j])/atr) if side>0 else ((BH[j]-entry)/atr)
        mfe=max(mfe,float(fav));mae=max(mae,float(adv))
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason="BOTH_STOP_FIRST";xi=j;break
        if hs:gross=-1;reason="SL";xi=j;break
        if ht:gross=3;reason="TP";xi=j;break
    net=float(gross-(cost/10000.0)*entry/atr)
    return net,reason,xi,mfe,mae

def stats(t):
    if t.empty:return {}
    x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    ce=np.cumsum(x);dd=float(np.max(np.maximum.accumulate(ce)-ce))
    a=pd.Timestamp(t.entry_time.min());b=pd.Timestamp(t.exit_time.max());months=max((b.year-a.year)*12+b.month-a.month+1,1)
    losers=t[t.net_r<0]
    return dict(n=len(t),trades_month=len(t)/months,ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                wr=float((x>0).mean()),r_month=float(x.sum()/months),dd_r=dd,
                median_delay_min=float(t.delay_min.median()),
                stop_rate=float(t.reason.isin(["SL","BOTH_STOP_FIRST"]).mean()),
                loser_median_mfe=float(losers.mfe_r.median()) if len(losers) else np.nan,
                loser_reached_1r=float((losers.mfe_r>=1).mean()) if len(losers) else np.nan)

variants=["BASE_SWING3","SWING3_MIN30","SWING3_MIN60","ACCEPT_2OF3","ACCEPT_3OF3","TWO_STEP_R10","TWO_STEP_R20"]
summary=[];alltr=[]
for name in variants:
    v=build_variant(name)
    for cost in COSTS:
        rows=[];open_until=pd.Timestamp.min.tz_localize("UTC")
        for _,r in v.sort_values("entry_time").iterrows():
            if r.entry_time<open_until:continue
            net,reason,xi,mfe,mae=sim_one(int(r.entry_i),int(r.side),float(r.atr),cost)
            open_until=BT.iloc[xi]
            q=r.to_dict();q.update(exit_time=BT.iloc[xi],net_r=net,reason=reason,mfe_r=mfe,mae_r=mae)
            rows.append(q)
        t=pd.DataFrame(rows)
        s=stats(t);s.update(variant=name,cost_bps=cost,raw_signals=len(v),fill_rate=len(v)/len(CTX));summary.append(s)
        if len(t):
            t["variant"]=name;t["cost_bps"]=cost;alltr.append(t)

S=pd.DataFrame(summary);S.to_csv(OUT/"LAB145_trigger_summary.csv",index=False)
if alltr:pd.concat(alltr,ignore_index=True).to_csv(OUT/"LAB145_trades.csv",index=False)

# Frozen decision rule: at stress cost, require PF >= baseline PF and at least 60% of baseline trade frequency;
# rank by R/month, then EV.
b=S[(S.variant=="BASE_SWING3")&(S.cost_bps==7.5)].iloc[0]
eligible=S[(S.cost_bps==7.5)&(S.pf>=b.pf)&(S.trades_month>=0.60*b.trades_month)].sort_values(["r_month","ev"],ascending=False)
winner=str(eligible.iloc[0].variant) if len(eligible) else "BASE_SWING3"

lines=["# LAB145 — ENGINE A TRIGGER CONFIRMATION","",
       "Engine A context is frozen. Only the M5 entry trigger changes.",
       f"Frozen context cohort: {len(CTX)} TRAIN CONT/REACCEL events.",
       "Execution stays SL=1 H1ATR / TP=3R / max48h / one-position chronology.",
       "",
       "Two-step trigger: first SWING3 -> pullback of at least 0.10/0.20 H1ATR without a new capitulation extreme -> close breaks the post-break favorable extreme -> next M5 open.",
       "Acceptance trigger: after first SWING3, require 2/3 or 3/3 closes beyond the broken SWING3 reference, with no new capitulation extreme.",
       ""]
for cost in COSTS:
    lines.append(f"## {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].sort_values("r_month",ascending=False).iterrows():
        lines.append(f"- {r.variant}: N={int(r.n)} ({r.trades_month:.2f}/mo), raw fill={r.fill_rate:.1%}, delay={r.median_delay_min:.0f}m, EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R, stop={r.stop_rate:.1%}, loser MFE={r.loser_median_mfe:.2f}R, losers>=1R={r.loser_reached_1r:.1%}")
lines += ["",f"Frozen-rule winner: **{winner}**.",
          "This is BTC TRAIN discovery, not fresh validation. Context thresholds were not changed."]
(OUT/"LAB145_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB145_meta.json").write_text(json.dumps(dict(winner=winner,context="A TRAIN CONT+REACCEL frozen",variants=variants,
    decision_rule="stress PF >= baseline and >=60% baseline frequency; rank by R/month then EV"),indent=2))
print("\n".join(lines))
