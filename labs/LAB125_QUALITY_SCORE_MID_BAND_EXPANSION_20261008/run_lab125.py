#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
spec=importlib.util.spec_from_file_location("lab124",SRC)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

OUT=Path("lab125_out"); OUT.mkdir(exist_ok=True)
df=m.df.copy()
BT=m.BT; BO=m.BO; BC=m.BC
COSTS=[2.81,7.5]
TRAIN_END=m.TRAIN_END

# Fixed score windows, centered on LAB124 mid-band.
A=m.qA;B=m.qB;C=m.qC
WINDOWS={
    "B_ONLY":(B,A),
    "BC_EXACT":(C,A),
    "MID_52_A":(52.0,A),
    "MID_50_A":(50.0,A),
    "MID_47_A":(47.0,A),
    "MID_45_A":(45.0,A),
    "MID_49_65":(49.0,65.0),
    "MID_47_65":(47.0,65.0),
}

def sim_subset(sub,cost,label):
    s=sub.sort_values("entry_time").copy()
    open_until=pd.Timestamp.min.tz_localize("UTC"); rows=[]; eq=[]; cum=0.0
    for _,r in s.iterrows():
        if r.entry_time<open_until: continue
        net,reason,xi=m.sim_one(int(r.entry_i),int(r.side),float(r.atr),cost)
        start=cum; entry=float(BO[int(r.entry_i)])
        for j in range(int(r.entry_i),xi+1):
            mtm=int(r.side)*(BC[j]-entry)/r.atr-(cost/10000.0)*entry/r.atr
            if j==xi: mtm=net
            eq.append((BT.iloc[j],start+mtm))
        cum+=net; open_until=BT.iloc[xi]
        rows.append(dict(label=label,cost_bps=cost,split=r["split"],phase=r.phase,tier=r.tier,score=r.score,
                         signal_time=r.signal_time,entry_time=r.entry_time,exit_time=BT.iloc[xi],
                         side="BUY" if r.side>0 else "SELL",net_r=net,reason=reason))
    t=pd.DataFrame(rows)
    if t.empty:return t,{}
    ep=pd.DataFrame(eq,columns=["time","equity"]).sort_values("time").drop_duplicates("time",keep="last")
    dd=float((ep.equity.cummax()-ep.equity).max())
    months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
    met=dict(trades_month=len(t)/months,r_month=t.net_r.sum()/months,maxdd_r=dd)
    return t,met

# Feature anatomy
x=df.copy()
x["zbin"]=pd.cut(x.abs_z,[1,1.5,2,2.5,np.inf],right=False,labels=["1-1.5","1.5-2","2-2.5","2.5+"])
x["delaybin"]=pd.cut(x.delay_min,[-1,60,120,240,99999],right=True,labels=["<=60","60-120","120-240",">240"])
x["breakbin"]=pd.cut(x.break_strength,[-np.inf,0.03,0.08,0.15,np.inf],right=False,labels=["<.03",".03-.08",".08-.15",".15+"])
x["entrybin"]=pd.cut(x.entry_improvement,[-np.inf,0,0.10,0.30,np.inf],right=False,labels=["<=0","0-.1",".1-.3",">.3"])
x["extbin"]=pd.cut(x.ext_abs,[0,m.EXT80,m.EXT90,np.inf],right=False,labels=["BASE","Q80-Q90","Q90+"])
x["oibin"]=pd.cut(x.oi4h,[-np.inf,m.OI70,m.OI85,np.inf],right=False,labels=["BASE","Q70-Q85","Q85+"])

def standalone_stats(sub,cost=2.81):
    t,_=sim_subset(sub,cost,"tmp")
    if t.empty:return None
    out=[]
    for split in ["ALL","TRAIN","OOS"]:
        q=t if split=="ALL" else t[t.split==split]
        if q.empty:continue
        pos=q.loc[q.net_r>0,"net_r"].sum();neg=-q.loc[q.net_r<0,"net_r"].sum()
        out.append(dict(split=split,n=len(q),ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,total_r=float(q.net_r.sum())))
    return pd.DataFrame(out)

an=[]
for dim in ["tier","phase","side","zbin","delaybin","breakbin","entrybin","extbin","oibin","dz_crowd"]:
    for group,g in x.groupby(dim,observed=True):
        if len(g)<15:continue
        st=standalone_stats(g,2.81)
        if st is None:continue
        for _,r in st.iterrows():
            an.append(dict(dimension=dim,group=str(group),split=r["split"],n=int(r.n),ev=r.ev,pf=r.pf,total_r=r.total_r))
pd.DataFrame(an).to_csv(OUT/"LAB125_anatomy.csv",index=False)

# Fixed score-window portfolios
alltr=[];summ=[]
for cost in COSTS:
    for name,(lo,hi) in WINDOWS.items():
        sub=df[(df.score>=lo)&(df.score<hi)]
        t,meta=sim_subset(sub,cost,name)
        if t.empty:continue
        alltr.append(t)
        for split in ["ALL","TRAIN","OOS"]:
            q=t if split=="ALL" else t[t.split==split]
            if q.empty:continue
            pos=q.loc[q.net_r>0,"net_r"].sum();neg=-q.loc[q.net_r<0,"net_r"].sum()
            summ.append(dict(portfolio=name,cost_bps=cost,split=split,n=len(q),ev=float(q.net_r.mean()),
                             pf=float(pos/neg) if neg>0 else np.inf,total_r=float(q.net_r.sum()),
                             trades_month=meta["trades_month"] if split=="ALL" else np.nan,
                             r_month=meta["r_month"] if split=="ALL" else np.nan,
                             maxdd_r=meta["maxdd_r"] if split=="ALL" else np.nan))
pd.DataFrame(summ).to_csv(OUT/"LAB125_score_windows.csv",index=False)

# TRAIN-only salvage scan inside D tier. Only simple one-dimensional subgroups; select by TRAIN PF,
# minimum sample and cross-year sign stability. OOS is never used in selection.
d=x[x.tier=="D"].copy()
candidates=[]
defs=[]
for dim in ["phase","side","zbin","delaybin","breakbin","entrybin","extbin","oibin","dz_crowd"]:
    for group,g in d.groupby(dim,observed=True):
        if len(g)<25:continue
        t,_=sim_subset(g,2.81,f"{dim}={group}")
        tr=t[t.split=="TRAIN"].copy()
        if len(tr)<20:continue
        pos=tr.loc[tr.net_r>0,"net_r"].sum();neg=-tr.loc[tr.net_r<0,"net_r"].sum()
        pf=float(pos/neg) if neg>0 else np.inf;ev=float(tr.net_r.mean())
        tr["year"]=tr.entry_time.dt.year
        yrs=[]
        for y,gy in tr.groupby("year"):
            if len(gy)>=3: yrs.append(float(gy.net_r.sum()))
        pos_years=sum(v>0 for v in yrs); n_years=len(yrs)
        candidates.append(dict(dimension=dim,group=str(group),train_n=len(tr),train_ev=ev,train_pf=pf,
                               pos_years=pos_years,n_years=n_years))
        if pf>=1.25 and ev>0 and len(tr)>=20 and n_years>=3 and pos_years>=max(2,n_years-1):
            defs.append((dim,str(group)))
scan=pd.DataFrame(candidates).sort_values(["train_pf","train_n"],ascending=[False,False])
scan.to_csv(OUT/"LAB125_D_salvage_scan.csv",index=False)

# Build BC + union of train-qualified D subgroups.
maskD=pd.Series(False,index=x.index)
for dim,group in defs:
    maskD |= (x[dim].astype(str)==group)
salv=x[(x.tier=="D")&maskD].copy()
salv.to_csv(OUT/"LAB125_selected_D_salvage_candidates.csv",index=False)

exp=[]
for cost in COSTS:
    for name,sub in {
        "BC_BASE": x[x.tier.isin(["B","C"])],
        "BC_PLUS_D_SALVAGE": pd.concat([x[x.tier.isin(["B","C"])],salv]).drop_duplicates("signal_time"),
        "B_PLUS_D_SALVAGE": pd.concat([x[x.tier=="B"],salv]).drop_duplicates("signal_time"),
    }.items():
        t,meta=sim_subset(sub,cost,name)
        if t.empty:continue
        alltr.append(t)
        for split in ["ALL","TRAIN","OOS"]:
            q=t if split=="ALL" else t[t.split==split]
            if q.empty:continue
            pos=q.loc[q.net_r>0,"net_r"].sum();neg=-q.loc[q.net_r<0,"net_r"].sum()
            exp.append(dict(portfolio=name,cost_bps=cost,split=split,n=len(q),ev=float(q.net_r.mean()),
                            pf=float(pos/neg) if neg>0 else np.inf,total_r=float(q.net_r.sum()),
                            trades_month=meta["trades_month"] if split=="ALL" else np.nan,
                            r_month=meta["r_month"] if split=="ALL" else np.nan,
                            maxdd_r=meta["maxdd_r"] if split=="ALL" else np.nan))
pd.DataFrame(exp).to_csv(OUT/"LAB125_expansion_portfolios.csv",index=False)
pd.concat(alltr,ignore_index=True).to_csv(OUT/"LAB125_trades.csv",index=False)

# Report
sw=pd.DataFrame(summ); ex=pd.DataFrame(exp)
lines=["# LAB125 — QUALITY SCORE MID-BAND EXPANSION","",
       f"Frozen LAB124 score cutoffs: A>={A:.1f}, B>={B:.1f}, C>={C:.1f}.",
       "Primary question: can the profitable mid-band be widened toward 3–4 trades/month without importing D-tier noise?",
       "Score windows are fixed around the LAB124 B/C zone. Separately, D-tier salvage is TRAIN-only and therefore explicitly exploratory/train-mined.",
       "Execution remains frozen: SWING3_BREAK -> next M5 open, SL1 H1 ATR, TP3R, max48h, one position.",
       ""]
for cost in COSTS:
    lines.append(f"## Fixed score windows @ {cost} bps")
    for name in WINDOWS:
        a=sw[(sw.portfolio==name)&(sw.cost_bps==cost)&(sw.split=="ALL")]
        o=sw[(sw.portfolio==name)&(sw.cost_bps==cost)&(sw.split=="OOS")]
        if len(a):
            aa=a.iloc[0];extra=""
            if len(o):
                oo=o.iloc[0];extra=f" | OOS N={int(oo.n)} EV={oo.ev:+.3f} PF={oo.pf:.2f}"
            lines.append(f"- {name}: N={int(aa.n)} ({aa.trades_month:.2f}/mo) EV={aa.ev:+.3f} PF={aa.pf:.2f} R/mo={aa.r_month:+.2f} DD={aa.maxdd_r:.1f}R{extra}")
    lines.append("")
lines.append("## TRAIN-only D salvage rules")
if defs:
    for dim,group in defs: lines.append(f"- {dim} = {group}")
else:
    lines.append("- None passed the TRAIN stability gate.")
lines.append("")
for cost in COSTS:
    lines.append(f"## Expansion portfolios @ {cost} bps")
    for name in ["BC_BASE","B_PLUS_D_SALVAGE","BC_PLUS_D_SALVAGE"]:
        a=ex[(ex.portfolio==name)&(ex.cost_bps==cost)&(ex.split=="ALL")]
        o=ex[(ex.portfolio==name)&(ex.cost_bps==cost)&(ex.split=="OOS")]
        if len(a):
            aa=a.iloc[0];extra=""
            if len(o):
                oo=o.iloc[0];extra=f" | OOS N={int(oo.n)} EV={oo.ev:+.3f} PF={oo.pf:.2f}"
            lines.append(f"- {name}: N={int(aa.n)} ({aa.trades_month:.2f}/mo) EV={aa.ev:+.3f} PF={aa.pf:.2f} R/mo={aa.r_month:+.2f} DD={aa.maxdd_r:.1f}R{extra}")
    lines.append("")
(OUT/"LAB125_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB125_meta.json").write_text(json.dumps(dict(
    source="LAB124 imported and rerun",
    score_cutoffs=dict(A=A,B=B,C=C),
    fixed_windows=WINDOWS,
    d_salvage_rules=defs,
    caveat="D salvage rules are TRAIN-mined hypothesis generation; OOS repeatedly inspected; no production claim"
),indent=2))
print("\n".join(lines))
