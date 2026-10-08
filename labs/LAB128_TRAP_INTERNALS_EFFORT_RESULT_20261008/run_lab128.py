#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, zipfile
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB127_FAILED_COUNTERTREND_DEPTH_TRAP_QUALITY_20261008/run_lab127.py"
spec=importlib.util.spec_from_file_location("lab127",SRC)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OUT=Path("lab128_out"); OUT.mkdir(exist_ok=True)
SEC_ZIP=Path("BTCUSDT_sec.csv.zip")
COSTS=[2.81,7.5]
DEPTHS=[0.50,0.75,1.00]

# LAB127 trap table already contains causal signal/hit/reclaim indices and trap-quality fields.
tr=m.traps[m.traps.depth.isin(DEPTHS)].copy()
tr["hit_time"]=tr.hit_i.map(lambda x:m.BT.iloc[int(x)])
tr["reclaim_time"]=tr.reclaim_i.map(lambda x:m.BT.iloc[int(x)])
tr["entry_time"]=tr.entry_i.map(lambda x:m.BT.iloc[int(x)])

# Restrict to second-level coverage after aggregation is known.
def ts_to_dt(s):
    x=pd.to_numeric(s,errors="coerce")
    med=float(x.dropna().median()) if x.notna().any() else 0
    if med>1e17: unit="ns"
    elif med>1e14: unit="us"
    elif med>1e11: unit="ms"
    else: unit="s"
    return pd.to_datetime(x,unit=unit,utc=True,errors="coerce")

# Stream 1-second file to causal 1-minute aggregates.
parts=[]
with zipfile.ZipFile(SEC_ZIP) as z:
    names=[n for n in z.namelist() if n.lower().endswith(".csv")]
    if not names: raise RuntimeError("No CSV inside BTCUSDT_sec.csv.zip")
    with z.open(names[0]) as fh:
        for ch in pd.read_csv(fh,chunksize=750_000):
            need=["ts","o","h","l","c","bv","sv","bn","sn","bnot","snot"]
            miss=[c for c in need if c not in ch.columns]
            if miss: raise RuntimeError(f"Missing second-level columns: {miss}")
            ch=ch[need].copy()
            ch["time"]=ts_to_dt(ch.ts)
            for c in need[1:]: ch[c]=pd.to_numeric(ch[c],errors="coerce")
            ch=ch.dropna(subset=["time","h","l","c","bnot","snot","bn","sn"])
            ch["minute"]=ch.time.dt.floor("min")
            g=ch.groupby("minute",sort=False).agg(
                o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last"),
                bv=("bv","sum"),sv=("sv","sum"),bn=("bn","sum"),sn=("sn","sum"),
                bnot=("bnot","sum"),snot=("snot","sum")
            ).reset_index()
            parts.append(g)
sec=pd.concat(parts,ignore_index=True)
sec=sec.groupby("minute",sort=True).agg(
    o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last"),
    bv=("bv","sum"),sv=("sv","sum"),bn=("bn","sum"),sn=("sn","sum"),
    bnot=("bnot","sum"),snot=("snot","sum")
).reset_index().sort_values("minute").reset_index(drop=True)
sec.to_csv(OUT/"LAB128_sec_1m_aggregate.csv",index=False)
cover_start=sec.minute.min(); cover_end=sec.minute.max()

tr=tr[(tr.hit_time>=cover_start)&(tr.reclaim_time<=cover_end)].copy().reset_index(drop=True)
if tr.empty: raise RuntimeError("No LAB127 traps overlap second-level coverage")

# Chronological DEV60/HOLDOUT40 split inside the genuinely available second-level period.
cut_idx=max(int(len(tr)*0.60)-1,0)
cut_time=tr.sort_values("signal_time").iloc[cut_idx].signal_time
tr["sec_split"]=np.where(tr.signal_time<=cut_time,"DEV60","HOLDOUT40")

# Helpers to slice minute data efficiently.
mins=sec["minute"]
def sec_window(t0,t1):
    t0=pd.Timestamp(t0)
    t1=pd.Timestamp(t1)
    if t0.tzinfo is None: t0=t0.tz_localize("UTC")
    else: t0=t0.tz_convert("UTC")
    if t1.tzinfo is None: t1=t1.tz_localize("UTC")
    else: t1=t1.tz_convert("UTC")
    i0=int(mins.searchsorted(t0,side="left"))
    i1=int(mins.searchsorted(t1,side="right"))
    return sec.iloc[i0:i1]

features=[]
for _,r in tr.iterrows():
    w=sec_window(r.hit_time,r.reclaim_time)
    if len(w)<1: continue
    side=int(r.side)               # trend / intended trade direction
    crowd_side=-side               # countertrend crowd attack direction
    crowd_not=float(w.snot.sum()) if crowd_side<0 else float(w.bnot.sum())
    trend_not=float(w.bnot.sum()) if crowd_side<0 else float(w.snot.sum())
    crowd_n=float(w.sn.sum()) if crowd_side<0 else float(w.bn.sum())
    trend_n=float(w.bn.sum()) if crowd_side<0 else float(w.sn.sum())
    total_not=crowd_not+trend_not
    total_n=crowd_n+trend_n
    not_imb=(crowd_not-trend_not)/total_not if total_not>0 else np.nan
    trade_imb=(crowd_n-trend_n)/total_n if total_n>0 else np.nan

    hit_px=float(m.BC[int(r.hit_i)])
    if side>0:
        worst=float(w.l.min())
        extra_adverse=max(0.0,(hit_px-worst)/float(r.atr))
    else:
        worst=float(w.h.max())
        extra_adverse=max(0.0,(worst-hit_px)/float(r.atr))

    dur=max(float(r.reclaim_min),1.0)
    crowd_not_per_min=crowd_not/dur
    total_not_per_min=total_not/dur

    # Price result per unit "effort". Higher stall_score means high crowd effort with little extra price progress.
    # Log effort stabilizes scale over 2026; thresholds are learned on DEV only.
    log_effort=np.log1p(crowd_not_per_min)
    stall_score=log_effort/(0.10+extra_adverse)
    imbalance_stall=max(not_imb,0.0)/(0.10+extra_adverse)

    # Number of minute bars that pushed to fresh adverse extremes after initial hit.
    fresh_ext=0
    running=hit_px
    if side>0:
        for v in w.l.to_numpy(float):
            if v<running:
                fresh_ext+=1; running=v
    else:
        for v in w.h.to_numpy(float):
            if v>running:
                fresh_ext+=1; running=v

    features.append(dict(
        depth=float(r.depth),signal_i=int(r.signal_i),hit_i=int(r.hit_i),reclaim_i=int(r.reclaim_i),entry_i=int(r.entry_i),
        signal_time=r.signal_time,hit_time=r.hit_time,reclaim_time=r.reclaim_time,entry_time=r.entry_time,
        sec_split=r.sec_split,side=side,atr=float(r.atr),
        reclaim_min=float(r.reclaim_min),new_extreme=bool(r.new_extreme),
        z_strength=float(r.z_strength),z_strengthened=bool(r.z_strengthened),
        oi_delta=float(r.oi_delta) if pd.notna(r.oi_delta) else np.nan,oi_build=bool(r.oi_build),
        impulse_reclaim=bool(r.impulse_reclaim),
        crowd_notional=crowd_not,trend_notional=trend_not,total_notional=total_not,
        crowd_trades=crowd_n,trend_trades=trend_n,
        notional_imbalance=not_imb,trade_imbalance=trade_imb,
        crowd_notional_per_min=crowd_not_per_min,total_notional_per_min=total_not_per_min,
        extra_adverse_atr=extra_adverse,fresh_adverse_extremes=fresh_ext,
        log_effort=log_effort,stall_score=stall_score,imbalance_stall=imbalance_stall
    ))
ft=pd.DataFrame(features).dropna(subset=["stall_score","notional_imbalance","extra_adverse_atr"])
ft.to_csv(OUT/"LAB128_trap_internals.csv",index=False)

# DEV-only thresholds, never HOLDOUT tuned.
dev=ft[ft.sec_split=="DEV60"]
Q={
    "effort70":float(dev.log_effort.quantile(.70)),
    "imb70":float(dev.notional_imbalance.quantile(.70)),
    "stall70":float(dev.stall_score.quantile(.70)),
    "istall70":float(dev.imbalance_stall.quantile(.70)),
    "progress30":float(dev.extra_adverse_atr.quantile(.30)),
    "extreme30":float(dev.fresh_adverse_extremes.quantile(.30)),
}
(OUT/"LAB128_dev_thresholds.json").write_text(json.dumps(Q,indent=2))

# Predeclared effort×result gates.
GATES={
    "ALL":lambda d:pd.Series(True,index=d.index),
    "HIGH_EFFORT":lambda d:d.log_effort>=Q["effort70"],
    "CROWD_DOMINANT":lambda d:d.notional_imbalance>=Q["imb70"],
    "LOW_PROGRESS":lambda d:d.extra_adverse_atr<=Q["progress30"],
    "HIGH_STALL":lambda d:d.stall_score>=Q["stall70"],
    "IMBALANCE_STALL":lambda d:d.imbalance_stall>=Q["istall70"],
    "EFFORT_LOW_RESULT":lambda d:(d.log_effort>=Q["effort70"])&(d.extra_adverse_atr<=Q["progress30"]),
    "DOMINANT_LOW_RESULT":lambda d:(d.notional_imbalance>=Q["imb70"])&(d.extra_adverse_atr<=Q["progress30"]),
    "EFFORT_STALL_ZOI":lambda d:(d.stall_score>=Q["stall70"])&(d.z_strengthened)&(d.oi_build),
    "DOM_STALL_ZOI":lambda d:(d.imbalance_stall>=Q["istall70"])&(d.z_strengthened)&(d.oi_build),
    "STALL_IMPULSE":lambda d:(d.stall_score>=Q["stall70"])&(d.impulse_reclaim),
}

def sim(ei,side,atr,cost):
    entry=float(m.BO[ei]);dist=1.5*atr;sl=entry-side*dist;tp=entry+side*3.0*dist
    end=min(ei+48*12-1,len(m.b)-1);gross=side*(m.BC[end]-entry)/dist;reason="TIME";xi=end
    for j in range(ei,end+1):
        hs=(m.BL[j]<=sl) if side>0 else (m.BH[j]>=sl)
        ht=(m.BH[j]>=tp) if side>0 else (m.BL[j]<=tp)
        if hs and ht:gross=-1;reason="BOTH_STOP_FIRST";xi=j;break
        if hs:gross=-1;reason="SL";xi=j;break
        if ht:gross=3.0;reason="TP";xi=j;break
    return float(gross-(cost/10000.0)*entry/dist),reason,xi

summary=[];trades=[]
for cost in COSTS:
  for depth in DEPTHS:
    d0=ft[ft.depth==depth]
    for gate,fn in GATES.items():
      s=d0[fn(d0)].sort_values("entry_time")
      if s.empty: continue
      open_until=pd.Timestamp.min.tz_localize("UTC"); rows=[]
      for _,r in s.iterrows():
        if r.entry_time<open_until: continue
        net,reason,xi=sim(int(r.entry_i),int(r.side),float(r.atr),cost)
        xt=m.BT.iloc[xi];open_until=xt
        rows.append(dict(cost_bps=cost,depth=depth,gate=gate,sec_split=r.sec_split,
                         signal_time=r.signal_time,entry_time=r.entry_time,exit_time=xt,
                         side="BUY" if r.side>0 else "SELL",net_r=net,reason=reason,
                         stall_score=r.stall_score,imbalance_stall=r.imbalance_stall,
                         notional_imbalance=r.notional_imbalance,extra_adverse_atr=r.extra_adverse_atr,
                         z_strengthened=r.z_strengthened,oi_build=r.oi_build,impulse_reclaim=r.impulse_reclaim))
      t=pd.DataFrame(rows)
      if t.empty: continue
      trades.append(t)
      months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
      for split in ["ALL","DEV60","HOLDOUT40"]:
        q=t if split=="ALL" else t[t.sec_split==split]
        if q.empty: continue
        pos=q.loc[q.net_r>0,"net_r"].sum(); neg=-q.loc[q.net_r<0,"net_r"].sum()
        summary.append(dict(cost_bps=cost,depth=depth,gate=gate,split=split,n=len(q),
                            ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                            wr=float((q.net_r>0).mean()),total_r=float(q.net_r.sum()),
                            trades_month=len(t)/months if split=="ALL" else np.nan,
                            r_month=t.net_r.sum()/months if split=="ALL" else np.nan))
sm=pd.DataFrame(summary)
sm.to_csv(OUT/"LAB128_summary.csv",index=False)
if trades: pd.concat(trades,ignore_index=True).to_csv(OUT/"LAB128_trades.csv",index=False)

# Rank on DEV60 only, min N30 because second-level coverage is only six months.
rank=sm[(sm.cost_bps==2.81)&(sm.split=="DEV60")&(sm.n>=30)].copy()
rank["rank_score"]=rank.ev.clip(-2,2)+0.15*np.log(rank.pf.clip(.1,10))
rank=rank.sort_values(["rank_score","pf","n"],ascending=False)
rank.to_csv(OUT/"LAB128_dev_ranking.csv",index=False)

top=[]
for _,r in rank.head(20).iterrows():
    h=sm[(sm.cost_bps==2.81)&(sm.split=="HOLDOUT40")&(sm.depth==r.depth)&(sm.gate==r.gate)]
    s75=sm[(sm.cost_bps==7.5)&(sm.split=="HOLDOUT40")&(sm.depth==r.depth)&(sm.gate==r.gate)]
    a=sm[(sm.cost_bps==2.81)&(sm.split=="ALL")&(sm.depth==r.depth)&(sm.gate==r.gate)]
    d=dict(depth=float(r.depth),gate=r.gate,dev_n=int(r.n),dev_ev=float(r.ev),dev_pf=float(r.pf))
    if len(h):
        q=h.iloc[0];d.update(hold_n=int(q.n),hold_ev=float(q.ev),hold_pf=float(q.pf))
    if len(s75):
        q=s75.iloc[0];d.update(hold75_ev=float(q.ev),hold75_pf=float(q.pf))
    if len(a):
        q=a.iloc[0];d.update(all_n=int(q.n),trades_month=float(q.trades_month),r_month=float(q.r_month))
    top.append(d)
pd.DataFrame(top).to_csv(OUT/"LAB128_top_dev_selected.csv",index=False)

lines=["# LAB128 — TRAP INTERNALS: EFFORT × RESULT","",
       f"Second-level coverage used: {cover_start} → {cover_end}.",
       f"Eligible LAB127 traps are split chronologically inside that coverage: DEV60 through {cut_time}, HOLDOUT40 after.",
       "Effort = aggressor notional/trade imbalance in the countertrend crowd direction between adverse-depth hit and reclaim.",
       "Result = additional adverse price progress after the hit, in H1 ATR. High effort + low progress = absorption/stall hypothesis.",
       "Execution is frozen: next M5 after reclaim, SL1.5 H1ATR, TP3R, max48h. No execution-grid mining.",
       "All thresholds are derived from DEV60 only. HOLDOUT40 is a development holdout, not pristine future validation.","",
       f"DEV thresholds: effort70={Q['effort70']:.3f}, imbalance70={Q['imb70']:.3f}, stall70={Q['stall70']:.3f}, imbalance_stall70={Q['istall70']:.3f}, low-progress30={Q['progress30']:.3f} ATR.","",
       "## Top DEV-selected @2.81bps"]
for d in top[:15]:
    lines.append(f"- depth {d['depth']:.2f} / {d['gate']}: DEV N={d['dev_n']} EV={d['dev_ev']:+.3f} PF={d['dev_pf']:.2f} | HOLD N={d.get('hold_n',0)} EV={d.get('hold_ev',float('nan')):+.3f} PF={d.get('hold_pf',float('nan')):.2f} | HOLD7.5 PF={d.get('hold75_pf',float('nan')):.2f} | {d.get('trades_month',float('nan')):.2f}/mo")
(OUT/"LAB128_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB128_meta.json").write_text(json.dumps(dict(
    second_level_coverage=[str(cover_start),str(cover_end)],split_cut=str(cut_time),
    depths=DEPTHS,execution="next M5 after reclaim, SL1.5 H1ATR, TP3R, 48h",
    effort_features=["crowd_notional_per_min","notional_imbalance","trade_imbalance"],
    result_features=["extra_adverse_atr","fresh_adverse_extremes"],
    thresholds=Q,
    caveat="2026 second-level-only sub-study; chronological DEV/HOLDOUT inside already-inspected history; research only"
),indent=2))
print("\n".join(lines))
