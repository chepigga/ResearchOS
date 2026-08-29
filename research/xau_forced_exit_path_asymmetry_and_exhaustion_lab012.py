#!/usr/bin/env python3
"""XAU_FORCED_EXIT_PATH_ASYMMETRY_AND_EXHAUSTION_LAB_012

Diagnostic-only price+time lab. No trade selection/payoff optimization.
Start state is frozen LAB011 crowd forced-exit event. Measure post-exit path at
5/10/20/40/60/120 completed M1 bars and detect causal exhaustion candidates.
Discovery 2023-24 -> validation 2025 -> 2026 untouched descriptive OOS.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd

BREAK_ATR=(0.10,0.20); COMMIT_MIN=(3,5); COMMIT_ATR=(0.20,0.35)
UNDER_MIN=(5,10,15); MAX_EXTRA_PROGRESS_ATR=(0.10,0.20); RETURN_MODE=('LEVEL','ENTRY_ZONE')
HORIZONS=(5,10,20,40,60,120)
STAB_WIN=(3,5,10); RECLAIM_ATR=(0.10,0.20,0.30)
DISC_N=80; VAL_N=30

def args():
 p=argparse.ArgumentParser()
 for k in ['bars','labels','outdir']: p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
 return p.parse_args()

def load(bp,lp):
 b=pd.read_parquet(bp);l=pd.read_parquet(lp)
 cols=['minute','timestamp_from_time_msc','mid_open','mid_high','mid_low','mid_close']
 x=b[cols].merge(l[['minute','atr14_causal']],on='minute',validate='one_to_one').sort_values('minute').reset_index(drop=True)
 x['year']=pd.to_datetime(x.timestamp_from_time_msc).dt.year.astype(int);return x

def build_forced_exit_events(x):
 hi=x.mid_high.to_numpy(float);lo=x.mid_low.to_numpy(float);cl=x.mid_close.to_numpy(float);atr=x.atr14_causal.to_numpy(float);yr=x.year.to_numpy(int)
 mins=x.minute.to_numpy(np.int64)
 prior_hi=pd.Series(hi).shift(1).rolling(60,min_periods=60).max().to_numpy();prior_lo=pd.Series(lo).shift(1).rolling(60,min_periods=60).min().to_numpy()
 rows=[];n=len(x)
 for br in BREAK_ATR:
  buy_idx=np.flatnonzero(np.isfinite(atr)&(atr>0)&(cl>=prior_hi+br*atr));sell_idx=np.flatnonzero(np.isfinite(atr)&(atr>0)&(cl<=prior_lo-br*atr))
  for crowd,idxs in [('BUY_CROWD',buy_idx),('SELL_CROWD',sell_idx)]:
   last=-999999
   for i in idxs:
    if i-last<60 or i+150>=n: continue
    last=i; level=float(prior_hi[i] if crowd=='BUY_CROWD' else prior_lo[i]);a=float(atr[i]);first=float(cl[i])
    for cm in COMMIT_MIN:
     j=i+cm-1
     prog=((cl[j]-level)/a) if crowd=='BUY_CROWD' else ((level-cl[j])/a)
     for ca in COMMIT_ATR:
      if prog<ca: continue
      commit=float(cl[j]); crowd_entry=(first+commit)/2.0
      for um in UNDER_MIN:
       e=j+um
       wh=hi[j+1:e+1];wl=lo[j+1:e+1]
       extra=(np.nanmax(wh)-commit)/a if crowd=='BUY_CROWD' else (commit-np.nanmin(wl))/a
       for mx in MAX_EXTRA_PROGRESS_ATR:
        if extra>mx: continue
        for mode in RETURN_MODE:
         threshold=level if mode=='LEVEL' else crowd_entry;trig=None
         for q in range(e,e+11):
          ok=(cl[q]<=threshold) if crowd=='BUY_CROWD' else (cl[q]>=threshold)
          if ok: trig=q;break
         if trig is None: continue
         inv='SELL' if crowd=='BUY_CROWD' else 'BUY'
         rows.append(dict(origin_idx=i,crowd_side=crowd,inverse_side=inv,break_atr=br,commit_min=cm,commit_atr=ca,under_min=um,max_extra_progress_atr=mx,return_mode=mode,level=level,crowd_entry_proxy=crowd_entry,forced_idx=trig,forced_minute=int(mins[trig]),forced_close=float(cl[trig]),atr=float(a),year=int(yr[trig]),cell=f'{crowd}|B{br:.2f}|C{cm}_{ca:.2f}|U{um}_{mx:.2f}|{mode}'))
 if not rows:return pd.DataFrame()
 return pd.DataFrame(rows).sort_values(['forced_minute','cell']).drop_duplicates(['origin_idx','cell']).reset_index(drop=True)

def path_rows(x,d):
 hi=x.mid_high.to_numpy(float);lo=x.mid_low.to_numpy(float);cl=x.mid_close.to_numpy(float)
 out=[]
 for r in d.itertuples(index=False):
  q=int(r.forced_idx);a=float(r.atr);base=float(r.forced_close);sell=(r.inverse_side=='SELL')
  z={'origin_idx':r.origin_idx,'cell':r.cell,'crowd_side':r.crowd_side,'inverse_side':r.inverse_side,'year':r.year,'forced_idx':q,'forced_minute':r.forced_minute,'forced_close':base,'atr':a}
  for h in HORIZONS:
   hh=hi[q+1:q+h+1];ll=lo[q+1:q+h+1];cc=float(cl[q+h])
   mfe=(base-np.nanmin(ll))/a if sell else (np.nanmax(hh)-base)/a
   mae=(np.nanmax(hh)-base)/a if sell else (base-np.nanmin(ll))/a
   end=(base-cc)/a if sell else (cc-base)/a
   z[f'mfe_{h}']=float(mfe);z[f'mae_{h}']=float(mae);z[f'end_{h}']=float(end);z[f'giveback_{h}']=float(mfe-end)
  out.append(z)
 return pd.DataFrame(out)

def exhaustion_rows(x,p):
 hi=x.mid_high.to_numpy(float);lo=x.mid_low.to_numpy(float);cl=x.mid_close.to_numpy(float)
 rows=[]
 for r in p.itertuples(index=False):
  q=int(r.forced_idx);a=float(r.atr);base=float(r.forced_close);sell=(r.inverse_side=='SELL')
  # Exhaustion is only knowable after a local adverse extreme has stopped extending.
  for sw in STAB_WIN:
   start=q+1
   for k in range(start+sw, q+121):
    prev_hi=np.nanmax(hi[k-sw:k]);prev_lo=np.nanmin(lo[k-sw:k])
    # no meaningful new extension during stabilization window, <=0.05 ATR
    if sell:
     ext=(prev_lo-np.nanmin(lo[k-sw+1:k+1]))/a
     stable=ext<=0.05
     extreme=prev_lo
    else:
     ext=(np.nanmax(hi[k-sw+1:k+1])-prev_hi)/a
     stable=ext<=0.05
     extreme=prev_hi
    if not stable: continue
    for rc in RECLAIM_ATR:
     # reclaim opposite the forced-exit leg; trigger uses completed close k
     ok=(cl[k]>=extreme+rc*a) if sell else (cl[k]<=extreme-rc*a)
     if ok:
      age=k-q
      rows.append(dict(origin_idx=r.origin_idx,cell=r.cell,crowd_side=r.crowd_side,inverse_side=r.inverse_side,year=r.year,stab_win=sw,reclaim_atr=rc,exhaust_idx=k,age_min=age,pre_exhaust_mfe_atr=(base-extreme)/a if sell else (extreme-base)/a,exhaust_cell=f'{r.cell}|STAB{sw}|RC{rc:.2f}'))
      break
    if any(rr['origin_idx']==r.origin_idx and rr['cell']==r.cell and rr['stab_win']==sw for rr in rows[-3:]): break
 return pd.DataFrame(rows)

def summarize_paths(p):
 rows=[]
 for (cell,year),g in p.groupby(['cell','year']):
  z={'cell':cell,'year':int(year),'n':len(g)}
  for h in HORIZONS:
   for m in ['mfe','mae','end','giveback']:
    a=g[f'{m}_{h}'].to_numpy(float);z[f'{m}_{h}_mean']=float(np.nanmean(a));z[f'{m}_{h}_median']=float(np.nanmedian(a))
   z[f'asym_{h}_median']=float(np.nanmedian(g[f'mfe_{h}']-g[f'mae_{h}']))
  rows.append(z)
 return pd.DataFrame(rows)

def summarize_exhaust(e):
 if e.empty:return pd.DataFrame()
 rows=[]
 for c,g in e.groupby('exhaust_cell'):
  tr=g[g.year.isin([2023,2024])];va=g[g.year==2025];fi=g[g.year==2026]
  rows.append(dict(exhaust_cell=c,train_n=len(tr),val_n=len(va),final_n=len(fi),train_age_median=float(tr.age_min.median()) if len(tr) else None,val_age_median=float(va.age_min.median()) if len(va) else None,final_age_median=float(fi.age_min.median()) if len(fi) else None,train_pre_exhaust_mfe_median=float(tr.pre_exhaust_mfe_atr.median()) if len(tr) else None,val_pre_exhaust_mfe_median=float(va.pre_exhaust_mfe_atr.median()) if len(va) else None,final_pre_exhaust_mfe_median=float(fi.pre_exhaust_mfe_atr.median()) if len(fi) else None,eligible=bool(len(tr)>=DISC_N and len(va)>=VAL_N)))
 return pd.DataFrame(rows).sort_values(['eligible','train_n'],ascending=[False,False])

def main():
 a=args();a.outdir.mkdir(parents=True,exist_ok=True);x=load(a.bars,a.labels);d=build_forced_exit_events(x);print('forced-exit rows',len(d),flush=True)
 if d.empty: raise RuntimeError('no forced-exit events')
 p=path_rows(x,d);ps=summarize_paths(p);e=exhaustion_rows(x,p);es=summarize_exhaust(e)
 d.to_parquet(a.outdir/'forced_exit_events.parquet',index=False);p.to_parquet(a.outdir/'post_exit_paths.parquet',index=False);ps.to_csv(a.outdir/'path_summary_by_year.csv',index=False);e.to_parquet(a.outdir/'exhaustion_events.parquet',index=False);es.to_csv(a.outdir/'exhaustion_candidates.csv',index=False)
 # No trade PASS/FAIL. Verdict asks only whether a repeatable exhaustion state exists pre-2026.
 elig=es[es.eligible] if len(es) else es
 stable=0
 if len(elig):
  q=elig.dropna(subset=['train_age_median','val_age_median','train_pre_exhaust_mfe_median','val_pre_exhaust_mfe_median']).copy()
  q['age_ratio']=np.maximum(q.train_age_median,q.val_age_median)/np.maximum(1.0,np.minimum(q.train_age_median,q.val_age_median))
  q['mfe_gap']=(q.train_pre_exhaust_mfe_median-q.val_pre_exhaust_mfe_median).abs()
  stable=int(((q.age_ratio<=1.75)&(q.mfe_gap<=0.50)).sum())
 verdict='PASS_EXHAUSTION_STATE_EXISTS' if stable>0 else 'FAIL_NO_STABLE_EXHAUSTION_STATE'
 out={'lab':'XAU_FORCED_EXIT_PATH_ASYMMETRY_AND_EXHAUSTION_LAB_012','forced_exit_rows':int(len(d)),'path_rows':int(len(p)),'exhaustion_rows':int(len(e)),'eligible_exhaustion_cells_pre2026':int(len(elig)),'stable_exhaustion_cells_pre2026':stable,'verdict':verdict}
 (a.outdir/'verdict.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
