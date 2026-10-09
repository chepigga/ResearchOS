from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

L148=loadmod("lab148",ROOT/"labs/LAB148_ACTIVE_Z_RESCUE_ANATOMY_20261009/run_lab148.py")

OUT=Path("lab152_out");OUT.mkdir(exist_ok=True)
BT=L148.BT;BO=L148.BO;BH=L148.BH;BL=L148.BL;BC=L148.BC;BA=L148.BA
TRAIN_END=L148.TRAIN_END
COSTS=[2.81,7.5]
MAX_H=48
SEED=15209
NMC=2000
rng=np.random.default_rng(SEED)

def sim(ei,side,atr,cost):
    entry=float(BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(BT)-1)
    gross=side*(BC[end]-entry)/atr;xi=end;reason="TIME"
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;xi=j;reason="BOTH_STOP_FIRST";break
        if hs:gross=-1;xi=j;reason="SL";break
        if ht:gross=3;xi=j;reason="TP";break
    return float(gross-(cost/10000.0)*entry/atr),reason,xi

def onepos(events,cost):
    rows=[];open_until=pd.Timestamp.min.tz_localize("UTC")
    for _,r in events.sort_values("entry_time").iterrows():
        if pd.Timestamp(r.entry_time)<open_until:continue
        net,reason,xi=sim(int(r.entry_i),int(r.side),float(r.atr),cost)
        open_until=BT.iloc[xi]
        rows.append(dict(entry_time=r.entry_time,exit_time=BT.iloc[xi],side=int(r.side),net_r=net,reason=reason))
    return pd.DataFrame(rows)

def stats(t):
    x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    ce=np.cumsum(x);dd=float(np.max(np.maximum.accumulate(ce)-ce)) if len(x) else np.nan
    return dict(n=len(t),ev=float(x.mean()) if len(x) else np.nan,
                pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()) if len(x) else np.nan,
                total_r=float(x.sum()),dd_r=dd)

# Frozen EARLY_EPISODE from LAB148.
base=L148.df[L148.df.episode_age_min<=L148.thr["age_q40"]].copy().sort_values("entry_time")
# Sensitivity only; no threshold promotion.
sens={
    "AGE_LE5":L148.df[L148.df.episode_age_min<=5].copy(),
    "AGE_LE10":L148.df[L148.df.episode_age_min<=10].copy(),
    "AGE_LE15":L148.df[L148.df.episode_age_min<=15].copy(),
    "AGE_LE30":L148.df[L148.df.episode_age_min<=30].copy(),
    "EARLY_STRONG_Z":L148.df[(L148.df.episode_age_min<=5)&(L148.df.z_now>=L148.thr["znow_q60"])].copy(),
}

summary=[];trades=[]
for cost in COSTS:
    for name,e in sens.items():
        t=onepos(e,cost);s=stats(t);s.update(cost_bps=cost,variant=name);summary.append(s)
        tt=t.copy();tt["variant"]=name;tt["cost_bps"]=cost;trades.append(tt)

S=pd.DataFrame(summary);S.to_csv(OUT/"LAB152_robustness_summary.csv",index=False)
pd.concat(trades,ignore_index=True).to_csv(OUT/"LAB152_trades.csv",index=False)

# Yearly / chronological-half robustness for frozen AGE_LE5.
rob=[]
for cost in COSTS:
    t=onepos(base,cost)
    t["year"]=pd.to_datetime(t.entry_time,utc=True).dt.year
    med=pd.to_datetime(t.entry_time,utc=True).sort_values().iloc[len(t)//2]
    t["half"]=np.where(pd.to_datetime(t.entry_time,utc=True)<=med,"H1","H2")
    for typ,col in [("YEAR","year"),("HALF","half")]:
        for key,g in t.groupby(col):
            q=stats(g);rob.append(dict(cost_bps=cost,split_type=typ,split=str(key),**q))
ROB=pd.DataFrame(rob);ROB.to_csv(OUT/"LAB152_time_robustness.csv",index=False)

# Random/placebo controls on stress only.
cost=7.5
obs=onepos(base,cost);obs_s=stats(obs)
nraw=len(base)
side_vec=base.side.to_numpy(int)

# Candidate random M5 bars strictly in TRAIN with enough look-forward and valid ATR.
valid_idx=np.where((pd.to_datetime(BT,utc=True)<TRAIN_END).to_numpy() & np.isfinite(BA) & (np.arange(len(BT))<len(BT)-MAX_H*12-2))[0]
# Avoid earliest ATR warmup and require positive ATR.
valid_idx=valid_idx[np.asarray(BA)[valid_idx]>0]

def portfolio_from_idx(idx, sides):
    ev=pd.DataFrame(dict(entry_i=idx,side=sides,atr=np.asarray(BA)[idx],entry_time=pd.to_datetime(BT.iloc[idx]).to_numpy()))
    ev["entry_time"]=pd.to_datetime(ev.entry_time,utc=True)
    return onepos(ev,cost)

mc_uniform=[]
for k in range(NMC):
    idx=np.sort(rng.choice(valid_idx,size=nraw,replace=False))
    sides=rng.permutation(side_vec)
    t=portfolio_from_idx(idx,sides)
    s=stats(t);mc_uniform.append((s["ev"],s["pf"],s["total_r"],s["n"]))
mc_uniform=np.asarray(mc_uniform,float)

# Time-shift placebo: each real event shifted by a random 1-14 days, sign +/-,
# preserving side and approximate calendar regime. Snap to closest M5 bar.
bt_ns=pd.to_datetime(BT,utc=True).astype("int64").to_numpy()
def nearest_index(ts):
    x=int(pd.Timestamp(ts).value);k=np.searchsorted(bt_ns,x)
    if k<=0:return 0
    if k>=len(bt_ns):return len(bt_ns)-1
    return k if abs(bt_ns[k]-x)<abs(bt_ns[k-1]-x) else k-1

mc_shift=[]
base_times=pd.to_datetime(base.entry_time,utc=True)
for k in range(NMC):
    rows=[]
    for (_,r),tm in zip(base.iterrows(),base_times):
        days=int(rng.integers(1,15));sgn=1 if rng.random()<0.5 else -1
        ts=tm+pd.Timedelta(days=sgn*days)
        ei=nearest_index(ts)
        if ei<0 or ei>=len(BT)-MAX_H*12-2 or pd.Timestamp(BT.iloc[ei])>=TRAIN_END or not np.isfinite(BA[ei]) or BA[ei]<=0:
            continue
        rows.append(dict(entry_i=ei,side=int(r.side),atr=float(BA[ei]),entry_time=BT.iloc[ei]))
    if not rows:continue
    t=onepos(pd.DataFrame(rows),cost);s=stats(t);mc_shift.append((s["ev"],s["pf"],s["total_r"],s["n"]))
mc_shift=np.asarray(mc_shift,float)

def pct(arr,x,col,greater=True):
    a=arr[:,col]
    if greater:return float((np.sum(a>=x)+1)/(len(a)+1))
    return float((np.sum(a<=x)+1)/(len(a)+1))

placebo=dict(
    observed=obs_s,
    uniform=dict(
        runs=int(len(mc_uniform)),
        ev_median=float(np.median(mc_uniform[:,0])),ev_p95=float(np.quantile(mc_uniform[:,0],.95)),
        pf_median=float(np.median(mc_uniform[:,1])),pf_p95=float(np.quantile(mc_uniform[:,1],.95)),
        total_r_median=float(np.median(mc_uniform[:,2])),total_r_p95=float(np.quantile(mc_uniform[:,2],.95)),
        p_ev=pct(mc_uniform,obs_s["ev"],0),p_pf=pct(mc_uniform,obs_s["pf"],1),p_total=pct(mc_uniform,obs_s["total_r"],2)
    ),
    shifted=dict(
        runs=int(len(mc_shift)),
        ev_median=float(np.median(mc_shift[:,0])),ev_p95=float(np.quantile(mc_shift[:,0],.95)),
        pf_median=float(np.median(mc_shift[:,1])),pf_p95=float(np.quantile(mc_shift[:,1],.95)),
        total_r_median=float(np.median(mc_shift[:,2])),total_r_p95=float(np.quantile(mc_shift[:,2],.95)),
        p_ev=pct(mc_shift,obs_s["ev"],0),p_pf=pct(mc_shift,obs_s["pf"],1),p_total=pct(mc_shift,obs_s["total_r"],2)
    )
)
(OUT/"LAB152_placebo.json").write_text(json.dumps(placebo,indent=2))

lines=["# LAB152 — EARLY_EPISODE ROBUSTNESS + PLACEBO CONTROLS","",
       "Frozen signal = LAB148 EARLY_EPISODE (ACTIVE_Z_RESCUE, episode age <=5m).",
       "Execution unchanged: SL1 H1ATR / TP3R / 48h / one-position for standalone QA.",
       "Threshold sensitivity is descriptive only; no retuning/promotion from this LAB.",
       "",
       "## Threshold sensitivity"]
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].sort_values("variant").iterrows():
        lines.append(f"- {r.variant}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, total={r.total_r:+.1f}R, DD={r.dd_r:.1f}R")
lines += ["","## Time robustness (frozen <=5m)"]
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for _,r in ROB[ROB.cost_bps==cost].iterrows():
        lines.append(f"- {r.split_type} {r.split}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, total={r.total_r:+.1f}R, DD={r.dd_r:.1f}R")
lines += ["","## Placebo controls @7.5bps",
          f"- Observed: N={obs_s['n']}, EV={obs_s['ev']:+.3f}R, PF={obs_s['pf']:.2f}, total={obs_s['total_r']:+.1f}R",
          f"- Uniform random matched-count/side placebo ({len(mc_uniform)} runs): median EV={np.median(mc_uniform[:,0]):+.3f}R, p95 EV={np.quantile(mc_uniform[:,0],.95):+.3f}R, median PF={np.median(mc_uniform[:,1]):.2f}, p95 PF={np.quantile(mc_uniform[:,1],.95):.2f}, p(EV>=obs)={placebo['uniform']['p_ev']:.4f}",
          f"- ±1..14d time-shift placebo, same side ({len(mc_shift)} runs): median EV={np.median(mc_shift[:,0]):+.3f}R, p95 EV={np.quantile(mc_shift[:,0],.95):+.3f}R, median PF={np.median(mc_shift[:,1]):.2f}, p95 PF={np.quantile(mc_shift[:,1],.95):.2f}, p(EV>=obs)={placebo['shifted']['p_ev']:.4f}",
          "",
          "Interpretation: placebo significance supports non-random timing, but this remains TRAIN/development evidence; it is not pristine OOS validation."]
(OUT/"LAB152_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB152_meta.json").write_text(json.dumps(dict(seed=SEED,n_mc=NMC,costs=COSTS,
    frozen_rule="ACTIVE_Z_RESCUE episode_age<=5m",caveat="TRAIN QA; no pristine OOS"),indent=2))
print("\n".join(lines))
