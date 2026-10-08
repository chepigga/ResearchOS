from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB138_A_B3HIGH_R48_PORTFOLIO_20261008/run_lab138.py"
sp=importlib.util.spec_from_file_location("lab138",SRC)
M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)
R=M.R; A=M.A
BT=pd.to_datetime(R.BT,utc=True).reset_index(drop=True)
BO=np.asarray(R.BO,float);BH=np.asarray(R.BH,float);BL=np.asarray(R.BL,float);BC=np.asarray(R.BC,float)
N=len(BT);RISK=.25;COSTS=[2.81,7.5]
IDX={pd.Timestamp(t):i for i,t in enumerate(BT)}
def ix(t):
 t=pd.Timestamp(t);t=t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')
 return int(IDX[t])
def portfolio_entries():
 pool=A.make_events(2.81)
 s=pool[pool.engine.isin(['A','B3_HIGH'])].copy();s['pri']=s.engine.map({'A':0,'B3_HIGH':1})
 s=s.sort_values(['entry_time','pri']);base=[];ou=pd.Timestamp.min.tz_localize('UTC')
 for _,r in s.iterrows():
  if r.entry_time<ou:continue
  ou=r.exit_time;base.append(dict(source=r.engine,entry_time=r.entry_time,side=int(r.side),atr=float(r.atr)))
 base=pd.DataFrame(base)
 rh=R.df[(~R.df.retest)&(R.df.mean_margin>=R.thr['mean_margin_q60'])&(R.df.oi_change>=R.thr['oi_q60'])]
 rr=[]
 for _,r in rh.iterrows():
  net,reason,xi=R.sim_one(r,2.81)
  rr.append(dict(source='R48_HIGH',entry_time=r.entry_time,side=int(r.side),atr=float(r.atr),exit_time=BT.iloc[xi]))
 r48=pd.DataFrame(rr)
 allp=pd.concat([base,r48],ignore_index=True,sort=False);allp['pri']=allp.source.map({'A':0,'B3_HIGH':1,'R48_HIGH':2})
 allp=allp.sort_values(['entry_time','pri']);out=[];ou=pd.Timestamp.min.tz_localize('UTC')
 for _,r in allp.iterrows():
  if r.entry_time<ou:continue
  ei=ix(r.entry_time);z=sim(ei,int(r.side),float(r.atr),2.81,3,48)
  ou=z['exit_time'];out.append(dict(source=r.source,entry_i=ei,entry_time=BT.iloc[ei],side=int(r.side),atr=float(r.atr)))
 d=pd.DataFrame(out)
 if len(d)!=282:raise RuntimeError(f"parity {len(d)}")
 return d
def sim(ei,side,atr,cost,tp=3,max_h=48,runner=False,act=2,lock=.5,ch=1.5,entry_price=None):
 entry=float(BO[ei] if entry_price is None else entry_price);stop=entry-side*atr
 target=None if tp is None else entry+side*tp*atr;end=min(ei+max_h*12-1,N-1);best=entry;active=False
 gross=side*(BC[end]-entry)/atr;reason='TIME';xi=end
 for j in range(ei,end+1):
  hs=BL[j]<=stop if side>0 else BH[j]>=stop
  ht=False if target is None else (BH[j]>=target if side>0 else BL[j]<=target)
  if hs:gross=(stop-entry)*side/atr;reason='TRAIL' if active else 'SL';xi=j;break
  if ht:gross=tp;reason='TP';xi=j;break
  fav=BH[j] if side>0 else BL[j]
  if (fav-entry)*side>(best-entry)*side:best=float(fav)
  if runner and (best-entry)*side/atr>=act:
   active=True;lk=entry+side*lock*atr;cs=best-side*ch*atr;stop=max(stop,lk,cs) if side>0 else min(stop,lk,cs)
 net=float(gross-(cost/10000)*entry/atr)
 return dict(exit_i=xi,exit_time=BT.iloc[xi],net_r=net,reason=reason,entry=entry)
def stats(t):
 x=t.net_r.to_numpy(float);p=x[x>0].sum();n=-x[x<0].sum();ce=np.cumsum(x);dd=float(np.max(np.maximum.accumulate(ce)-ce))
 a=pd.Timestamp(t.entry_time.min());b=pd.Timestamp(t.exit_time.max());mo=max((b.year-a.year)*12+b.month-a.month+1,1)
 return dict(n=len(t),trades_month=len(t)/mo,ev=float(x.mean()),pf=float(p/n) if n>0 else np.inf,r_month=float(x.sum()/mo),dd_pct=dd*RISK)
ENTRIES=portfolio_entries()
