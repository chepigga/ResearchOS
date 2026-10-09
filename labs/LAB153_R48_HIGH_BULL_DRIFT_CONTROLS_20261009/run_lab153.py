from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

R=loadmod("lab137",ROOT/"labs/LAB137_R48_ACCEPT_ANATOMY_20261008/run_lab137.py")

OUT=Path("lab153_out");OUT.mkdir(exist_ok=True)
BT=R.BT;BO=R.BO;BH=R.BH;BL=R.BL;BC=R.BC;BA=R.BA
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
COST=7.5
MAX_H=48
SEED=15309
NMC=2000
rng=np.random.default_rng(SEED)

r48=R.df[(~R.df.retest) &
         (R.df.mean_margin>=R.thr['mean_margin_q60']) &
         (R.df.oi_change>=R.thr['oi_q60'])].copy().sort_values("entry_time")

def sim(ei,side,atr,cost=COST):
    entry=float(BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(BT)-1)
    gross=side*(BC[end]-entry)/atr;xi=end;reason="TIME"
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;xi=j;reason="BOTH_STOP_FIRST";break
        if hs:gross=-1;xi=j;reason="SL";break
        if ht:gross=3;xi=j;reason="TP";break
    return float(gross-(cost/10000.0)*entry/atr),reason,xi

def onepos(events):
    rows=[];open_until=pd.Timestamp.min.tz_localize("UTC")
    for _,r in events.sort_values("entry_time").iterrows():
        if pd.Timestamp(r.entry_time)<open_until:continue
        net,reason,xi=sim(int(r.entry_i),int(r.side),float(r.atr))
        open_until=BT.iloc[xi]
        rows.append(dict(entry_time=r.entry_time,exit_time=BT.iloc[xi],side=int(r.side),net_r=net,reason=reason))
    return pd.DataFrame(rows)

def stats(t):
    x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
    ce=np.cumsum(x);dd=float(np.max(np.maximum.accumulate(ce)-ce)) if len(x) else np.nan
    return dict(n=len(t),ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                wr=float((x>0).mean()),total_r=float(x.sum()),dd_r=dd)

# observed
obs=onepos(r48);obs_s=stats(obs)

# same timestamps, force all LONG / force all SHORT / flip original side
same=[]
for label,sidefn in [
    ("OBSERVED",lambda r:int(r.side)),
    ("SAME_TIMES_ALL_LONG",lambda r:1),
    ("SAME_TIMES_ALL_SHORT",lambda r:-1),
    ("SAME_TIMES_FLIPPED",lambda r:-int(r.side)),
]:
    e=r48.copy()
    e["side"]=[sidefn(r) for _,r in e.iterrows()]
    t=onepos(e);s=stats(t);s["variant"]=label;same.append(s)
pd.DataFrame(same).to_csv(OUT/"LAB153_same_time_controls.csv",index=False)

# time robustness
rob=[]
obs2=obs.copy();obs2["year"]=pd.to_datetime(obs2.entry_time,utc=True).dt.year
med=pd.to_datetime(obs2.entry_time,utc=True).sort_values().iloc[len(obs2)//2]
obs2["half"]=np.where(pd.to_datetime(obs2.entry_time,utc=True)<=med,"H1","H2")
for typ,col in [("YEAR","year"),("HALF","half")]:
    for key,g in obs2.groupby(col):
        q=stats(g);rob.append(dict(split_type=typ,split=str(key),**q))
pd.DataFrame(rob).to_csv(OUT/"LAB153_time_robustness.csv",index=False)

# Valid random TRAIN bars.
valid=np.where((pd.to_datetime(BT,utc=True)<TRAIN_END).to_numpy() & np.isfinite(BA) & (np.asarray(BA)>0) &
               (np.arange(len(BT))<len(BT)-MAX_H*12-2))[0]

nraw=len(r48)
side_vec=r48.side.to_numpy(int)
year_targets=pd.to_datetime(r48.entry_time,utc=True).dt.year.value_counts().to_dict()
valid_by_year={}
for y in year_targets:
    valid_by_year[y]=valid[pd.to_datetime(BT.iloc[valid],utc=True).dt.year.to_numpy()==y]

def portfolio_idx(idx,sides):
    e=pd.DataFrame(dict(entry_i=idx,side=sides,atr=np.asarray(BA)[idx],entry_time=pd.to_datetime(BT.iloc[idx]).to_numpy()))
    e["entry_time"]=pd.to_datetime(e.entry_time,utc=True)
    return onepos(e)

# Monte Carlo controls
uniform_long=[];yearmatch_long=[];yearmatch_sidemix=[]
years=[]
for y,n in year_targets.items(): years += [y]*n
years=np.asarray(years)

for k in range(NMC):
    # uniform all long
    idx=np.sort(rng.choice(valid,size=nraw,replace=False))
    t=portfolio_idx(idx,np.ones(nraw,dtype=int));s=stats(t)
    uniform_long.append((s["ev"],s["pf"],s["total_r"],s["n"]))

    # year-matched all-long
    idxs=[]
    for y,n in year_targets.items():
        pool=valid_by_year[y]
        if len(pool)<n: raise RuntimeError("not enough year pool")
        idxs.extend(rng.choice(pool,size=n,replace=False).tolist())
    idx=np.array(sorted(idxs))
    t=portfolio_idx(idx,np.ones(len(idx),dtype=int));s=stats(t)
    yearmatch_long.append((s["ev"],s["pf"],s["total_r"],s["n"]))

    # year-matched, observed side-mix permuted
    sides=rng.permutation(side_vec)
    # preserve total count, not exact side/year interaction
    t=portfolio_idx(idx,sides[:len(idx)]);s=stats(t)
    yearmatch_sidemix.append((s["ev"],s["pf"],s["total_r"],s["n"]))

uniform_long=np.asarray(uniform_long,float)
yearmatch_long=np.asarray(yearmatch_long,float)
yearmatch_sidemix=np.asarray(yearmatch_sidemix,float)

def pge(arr,x,col):
    return float((np.sum(arr[:,col]>=x)+1)/(len(arr)+1))

controls={}
for name,arr in [("uniform_long",uniform_long),("yearmatch_long",yearmatch_long),("yearmatch_sidemix",yearmatch_sidemix)]:
    controls[name]=dict(
        runs=len(arr),
        ev_median=float(np.median(arr[:,0])),ev_p95=float(np.quantile(arr[:,0],.95)),
        pf_median=float(np.median(arr[:,1])),pf_p95=float(np.quantile(arr[:,1],.95)),
        total_r_median=float(np.median(arr[:,2])),total_r_p95=float(np.quantile(arr[:,2],.95)),
        p_ev=pge(arr,obs_s["ev"],0),p_pf=pge(arr,obs_s["pf"],1),p_total=pge(arr,obs_s["total_r"],2)
    )

# Bull-drift decomposition: observed BUY vs SELL and all-long same times.
side_stats=[]
for side,label in [(1,"OBS_BUY"),(-1,"OBS_SELL")]:
    g=obs[obs.side==side]
    if len(g):
        q=stats(g);q["group"]=label;side_stats.append(q)
pd.DataFrame(side_stats).to_csv(OUT/"LAB153_side_stats.csv",index=False)

(OUT/"LAB153_placebo.json").write_text(json.dumps(dict(observed=obs_s,controls=controls),indent=2))

same_df=pd.DataFrame(same)
lines=["# LAB153 — R48_HIGH VS RANDOM LONG / BULL-DRIFT CONTROLS","",
       "Frozen R48_HIGH = CLEAN_ACCEPT_OI from LAB137. Stress cost 7.5bps only for controls.",
       f"Raw R48_HIGH events: {len(r48)}; BUY={int((r48.side>0).sum())}, SELL={int((r48.side<0).sum())}.",
       "",
       "## Same-timestamp directional controls"]
for _,r in same_df.iterrows():
    lines.append(f"- {r.variant}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, total={r.total_r:+.1f}R, DD={r.dd_r:.1f}R")
lines += ["","## Time robustness"]
for r in rob:
    lines.append(f"- {r['split_type']} {r['split']}: N={r['n']}, EV={r['ev']:+.3f}R, PF={r['pf']:.2f}, total={r['total_r']:+.1f}R")
lines += ["","## Random / bull-drift controls"]
for name,c in controls.items():
    lines.append(f"- {name} ({c['runs']} runs): median EV={c['ev_median']:+.3f}R, p95 EV={c['ev_p95']:+.3f}R, median PF={c['pf_median']:.2f}, p95 PF={c['pf_p95']:.2f}, p(EV>=observed)={c['p_ev']:.4f}")
lines += ["","## Interpretation",
          "If SAME_TIMES_ALL_LONG approaches OBSERVED, part of R48_HIGH may be timing + BTC long drift rather than directional selectivity.",
          "If year-matched random LONG also approaches OBSERVED, bull-regime drift is a serious confound.",
          "If OBSERVED remains above the 95th percentile of both random controls, R48 timing/structure carries information beyond generic BTC long bias.",
          "TRAIN/development QA only; this is not pristine OOS validation."]
(OUT/"LAB153_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB153_meta.json").write_text(json.dumps(dict(seed=SEED,n_mc=NMC,cost_bps=COST,
    frozen_rule="R48_HIGH CLEAN_ACCEPT_OI",caveat="TRAIN QA, bull-drift controls"),indent=2))
print("\n".join(lines))
