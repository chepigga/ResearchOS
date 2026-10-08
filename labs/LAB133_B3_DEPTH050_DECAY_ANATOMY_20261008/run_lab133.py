#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB132_B3_COUNTERTREND_ATTACK_EXHAUSTION_20261008/run_lab132.py"
spec=importlib.util.spec_from_file_location("lab132",SRC)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OUT=Path("lab133_out"); OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
DEPTH=0.50

# LAB132 already guarantees BTC TRAIN only and builds the 0.5ATR Z+OI attack universe.
ev=m.ev[m.ev.depth==DEPTH].copy().reset_index(drop=True)

def parse_intervals(s):
    return np.array([float(x) for x in str(s).split("|") if str(x)!=""],dtype=float)

rows=[]
for _,r in ev.iterrows():
    x=parse_intervals(r.intervals)
    if len(x)!=5: 
        continue
    # Five causal milestone durations for 0.1,0.2,0.3,0.4,0.5 ATR.
    d01,d02,d03,d04,d05=x.tolist()
    early=np.mean(x[:2])
    mid=x[2]
    late=np.mean(x[3:])
    deltas=np.diff(x)
    pos_steps=int(np.sum(deltas>0))
    neg_steps=int(np.sum(deltas<0))
    # Mechanistic descriptors, not return-fit:
    # 1) terminal stall: final 0.1 ATR is slowest segment of attack.
    terminal_stall=bool(d05>=np.max(x[:-1]))
    # 2) late-half deterioration: final two segments slower than first two.
    late_slower=bool(late>early)
    # 3) two-step terminal deterioration: both 0.4 and 0.5 segments slower than their predecessors.
    terminal_two_step=bool((d04>d03) and (d05>d04))
    # 4) broad deterioration: at least 3 of 4 transitions take longer.
    broad_decay=bool(pos_steps>=3)
    # 5) terminal stall + late-half deterioration = concise exhaustion shape.
    exhaustion_shape=bool(terminal_stall and late_slower)
    rows.append(dict(
        **r.to_dict(),
        d01=d01,d02=d02,d03=d03,d04=d04,d05=d05,
        early_mean=early,mid_bar=mid,late_mean=late,
        late_early_ratio=float(late/max(early,1e-9)),
        terminal_ratio=float(d05/max(d01,1e-9)),
        pos_steps=pos_steps,neg_steps=neg_steps,
        terminal_stall=terminal_stall,late_slower=late_slower,
        terminal_two_step=terminal_two_step,broad_decay=broad_decay,
        exhaustion_shape=exhaustion_shape
    ))
df=pd.DataFrame(rows)
df.to_csv(OUT/"LAB133_depth050_anatomy_events.csv",index=False)

# Predeclared anatomy groups. POSITIVE_SLOPE is the surviving LAB132 candidate/control comparison.
GATES={
    "CONTROL_ZOI": lambda d: pd.Series(True,index=d.index),
    "POSITIVE_SLOPE": lambda d: d.decay_slope>0,
    "TERMINAL_STALL": lambda d: d.terminal_stall,
    "LATE_SLOWER": lambda d: d.late_slower,
    "TERMINAL_TWO_STEP": lambda d: d.terminal_two_step,
    "BROAD_DECAY_3OF4": lambda d: d.broad_decay,
    "EXHAUSTION_SHAPE": lambda d: d.exhaustion_shape,
    "POS_SLOPE_AND_STALL": lambda d: (d.decay_slope>0)&(d.terminal_stall),
    "POS_SLOPE_AND_EXHAUSTION": lambda d: (d.decay_slope>0)&(d.exhaustion_shape),
}

def sim_one(ei,side,atr,cost):
    entry=float(m.BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr
    end=min(ei+m.MAX_H*12-1,len(m.b)-1)
    gross=side*(m.BC[end]-entry)/atr;reason="TIME";xi=end
    for j in range(ei,end+1):
        hs=(m.BL[j]<=sl) if side>0 else (m.BH[j]>=sl)
        ht=(m.BH[j]>=tp) if side>0 else (m.BL[j]<=tp)
        if hs and ht:gross=-1;reason="BOTH_STOP_FIRST";xi=j;break
        if hs:gross=-1;reason="SL";xi=j;break
        if ht:gross=3;reason="TP";xi=j;break
    return float(gross-(cost/10000.0)*entry/atr),reason,xi

summary=[];alltr=[]
for cost in COSTS:
  for gate,fn in GATES.items():
    s=df[fn(df)].sort_values("entry_time")
    open_until=pd.Timestamp.min.tz_localize("UTC"); trs=[]
    for _,r in s.iterrows():
        if r.entry_time<open_until: continue
        net,reason,xi=sim_one(int(r.entry_i),int(r.side),float(r.atr),cost)
        xt=m.BT.iloc[xi];open_until=xt
        trs.append(dict(cost_bps=cost,gate=gate,signal_time=r.signal_time,entry_time=r.entry_time,exit_time=xt,
                        side="BUY" if r.side>0 else "SELL",net_r=net,reason=reason,
                        d01=r.d01,d02=r.d02,d03=r.d03,d04=r.d04,d05=r.d05,
                        decay_slope=r.decay_slope,late_early_ratio=r.late_early_ratio,
                        terminal_ratio=r.terminal_ratio,pos_steps=r.pos_steps))
    t=pd.DataFrame(trs)
    if t.empty: continue
    alltr.append(t)
    pos=t.loc[t.net_r>0,"net_r"].sum();neg=-t.loc[t.net_r<0,"net_r"].sum()
    months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
    ce=t.net_r.cumsum();ddr=float((ce.cummax()-ce).max())
    summary.append(dict(cost_bps=cost,gate=gate,n=len(t),trades_month=len(t)/months,
                        ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                        wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),
                        r_month=float(t.net_r.sum()/months),realized_dd_r=ddr,
                        tp_rate=float((t.reason=="TP").mean()),
                        sl_rate=float(t.reason.isin(["SL","BOTH_STOP_FIRST"]).mean()),
                        time_rate=float((t.reason=="TIME").mean())))
sm=pd.DataFrame(summary)
sm.to_csv(OUT/"LAB133_depth050_execution.csv",index=False)
if alltr: pd.concat(alltr,ignore_index=True).to_csv(OUT/"LAB133_depth050_trades.csv",index=False)

# Compare each morphology directly to CONTROL and to POSITIVE_SLOPE.
comp=[]
for cost in COSTS:
    c=sm[(sm.cost_bps==cost)&(sm.gate=="CONTROL_ZOI")].iloc[0]
    p=sm[(sm.cost_bps==cost)&(sm.gate=="POSITIVE_SLOPE")].iloc[0]
    for gate in GATES:
        q=sm[(sm.cost_bps==cost)&(sm.gate==gate)]
        if not len(q): continue
        q=q.iloc[0]
        comp.append(dict(cost_bps=cost,gate=gate,n=int(q.n),ev=float(q.ev),pf=float(q.pf),
                         delta_ev_vs_control=float(q.ev-c.ev),delta_pf_vs_control=float(q.pf-c.pf),
                         delta_ev_vs_posslope=float(q.ev-p.ev),delta_pf_vs_posslope=float(q.pf-p.pf)))
pd.DataFrame(comp).to_csv(OUT/"LAB133_increment_vs_control.csv",index=False)

# Pure descriptive anatomy by each 0.1ATR interval quartile. TRAIN-only atlas, never used as a promotion rule here.
anat=[]
for col in ["d01","d02","d03","d04","d05","late_early_ratio","terminal_ratio","pos_steps"]:
    d=df.copy()
    if col=="pos_steps":
        d["_bin"]=d[col].astype(str)
    else:
        try:d["_bin"]=pd.qcut(d[col],4,duplicates="drop")
        except:d["_bin"]="ALL"
    for grp,g in d.groupby("_bin",observed=True):
        if len(g)<20:continue
        vals=[]
        for _,r in g.iterrows():
            net,_,_=sim_one(int(r.entry_i),int(r.side),float(r.atr),2.81)
            vals.append(net)
        a=np.asarray(vals,float);pos=a[a>0].sum();neg=-a[a<0].sum()
        anat.append(dict(dimension=col,group=str(grp),n=len(a),ev=float(a.mean()),
                         pf=float(pos/neg) if neg>0 else np.inf,wr=float((a>0).mean())))
pd.DataFrame(anat).to_csv(OUT/"LAB133_interval_anatomy.csv",index=False)

lines=["# LAB133 — B3 0.50 ATR DECAY ANATOMY","",
       "Protocol: BTC TRAIN only. No BTC OOS return inspection.",
       "Scope is intentionally narrow: only LAB132 0.50 H1ATR countertrend attacks with fresh countertrend Z, Z strengthening >=0.25, OI rising, and reclaim.",
       "Execution remains frozen: next M5 after reclaim, SL=1 H1ATR, TP=3R, max48h, stop-first.","",
       "Attack is decomposed into five causal 0.1ATR milestone durations: d01..d05.","",
       "Predeclared shapes:",
       "- TERMINAL_STALL: final 0.1ATR takes at least as long as every previous segment.",
       "- LATE_SLOWER: mean(d04,d05) > mean(d01,d02).",
       "- TERMINAL_TWO_STEP: d04>d03 and d05>d04.",
       "- BROAD_DECAY_3OF4: at least 3 of 4 interval-to-interval changes are slower.",
       "- EXHAUSTION_SHAPE: TERMINAL_STALL + LATE_SLOWER.",
       "- POS_SLOPE_AND_STALL / POS_SLOPE_AND_EXHAUSTION: refine LAB132 positive-slope candidate with morphology.","",
       "## TRAIN execution @2.81bps"]
for gate in GATES:
    q=sm[(sm.cost_bps==2.81)&(sm.gate==gate)]
    if len(q):
        r=q.iloc[0]
        lines.append(f"- {gate}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, R/mo={r.r_month:+.2f}, DD={r.realized_dd_r:.1f}R")
lines += ["","## Stress @7.5bps"]
for gate in ["CONTROL_ZOI","POSITIVE_SLOPE","TERMINAL_STALL","EXHAUSTION_SHAPE","POS_SLOPE_AND_STALL","POS_SLOPE_AND_EXHAUSTION"]:
    q=sm[(sm.cost_bps==7.5)&(sm.gate==gate)]
    if len(q):
        r=q.iloc[0]
        lines.append(f"- {gate}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}")
lines += ["","## Decision rule",
          "Do not choose a quartile threshold from this LAB. The only promotable shapes are the predeclared causal morphology gates above.",
          "A useful B3 refinement should materially improve PF/EV versus POSITIVE_SLOPE while retaining enough events to matter.",
          "If no morphology does that, retain LAB132 POSITIVE_SLOPE as the best B3 TRAIN hypothesis and stop tuning BTC."]
(OUT/"LAB133_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB133_meta.json").write_text(json.dumps(dict(
    protocol="BTC TRAIN only; no BTC OOS inspection",
    depth_atr=0.5,
    universe="LAB132 0.5ATR Z+OI countertrend attacks",
    intervals="five 0.1 H1ATR causal milestone durations",
    predeclared_gates=list(GATES.keys()),
    execution="next M5 after reclaim, SL1 H1ATR, TP3R, max48h",
    caveat="quartile anatomy descriptive only; no return-fit thresholds"
),indent=2))
print("\n".join(lines))
