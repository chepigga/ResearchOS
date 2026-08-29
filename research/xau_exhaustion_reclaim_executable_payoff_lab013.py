#!/usr/bin/env python3
"""XAU_EXHAUSTION_RECLAIM_EXECUTABLE_PAYOFF_LAB_013
Frozen executable test of LAB012 exhaustion states.
Causal entry: first tick of M1 after completed stabilization+reclaim trigger.
SL: beyond exhaustion extreme + frozen ATR buffer. TP: 1.5R/2R/2.5R.
2023-24 discovery -> 2025 validation -> 2026 untouched OOS. Exact Bid/Ask ticks.
"""
from __future__ import annotations
import argparse,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd
import xau_forced_exit_path_asymmetry_and_exhaustion_lab012 as l12
COMMISSION_RATE_SIDE=0.000007
BUFFERS=(0.10,0.20); RRS=(1.5,2.0,2.5); HORIZONS=(60,120,240)
DISC_N=80; VAL_N=30; FINAL_N=20; DISC_EV=0.03; DISC_PF=1.08

def args():
 p=argparse.ArgumentParser()
 for k in ['bars','labels','audit','raw_zip','outdir']: p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
 return p.parse_args()

def pf(a):
 a=np.asarray(a,float);a=a[np.isfinite(a)];gp=a[a>0].sum();gl=-a[a<0].sum();return float(gp/gl) if gl>0 else None

def stats(a):
 a=np.asarray(a,float);a=a[np.isfinite(a)]
 if not len(a): return dict(n=0,mean_R=None,pf=None,win_rate=None,sum_R=0.0,max_dd_R=None)
 eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=pk[1:]-eq
 return dict(n=int(len(a)),mean_R=float(a.mean()),pf=pf(a),win_rate=float((a>0).mean()),sum_R=float(a.sum()),max_dd_R=float(dd.max()))

def load_full(bp,lp):
 b=pd.read_parquet(bp);l=pd.read_parquet(lp)
 cols=['minute','timestamp_from_time_msc','first_time_msc','first_bid','first_ask','mid_open','mid_high','mid_low','mid_close']
 x=b[cols].merge(l[['minute','atr14_causal']],on='minute',validate='one_to_one').sort_values('minute').reset_index(drop=True)
 x['year']=pd.to_datetime(x.timestamp_from_time_msc).dt.year.astype(int);return x

def files(audit):
 j=json.loads(audit.read_text());out=[]
 for f in j.get('files',[]):
  if f.get('valid_rows',0)>0 and f.get('first_time_msc') is not None: out.append((f['member'],int(f['first_time_msc']),int(f['last_time_msc'])))
 return sorted(out,key=lambda z:z[1])

def build_signals(x):
 # Recreate frozen LAB012 lineage exactly.
 d=l12.build_forced_exit_events(x[['minute','timestamp_from_time_msc','mid_open','mid_high','mid_low','mid_close','atr14_causal','year']].copy())
 p=l12.path_rows(x,d); e=l12.exhaustion_rows(x,p)
 if e.empty:return d,e,pd.DataFrame()
 es=l12.summarize_exhaust(e); stable=es[es.eligible].copy()
 stable['age_ratio']=np.maximum(stable.train_age_median,stable.val_age_median)/np.maximum(1.0,np.minimum(stable.train_age_median,stable.val_age_median))
 stable['mfe_gap']=(stable.train_pre_exhaust_mfe_median-stable.val_pre_exhaust_mfe_median).abs()
 stable_cells=set(stable.loc[(stable.age_ratio<=1.75)&(stable.mfe_gap<=0.50),'exhaust_cell'])
 e=e[e.exhaust_cell.isin(stable_cells)].copy()
 hi=x.mid_high.to_numpy(float);lo=x.mid_low.to_numpy(float);mins=x.minute.to_numpy(np.int64);ft=x.first_time_msc.to_numpy(np.int64);fb=x.first_bid.to_numpy(float);fa=x.first_ask.to_numpy(float);atr=x.atr14_causal.to_numpy(float);yr=x.year.to_numpy(int)
 rows=[]
 for r in e.itertuples(index=False):
  k=int(r.exhaust_idx);en=k+1
  if en>=len(x) or not np.isfinite(atr[en]) or atr[en]<=0:continue
  sell=(r.inverse_side=='SELL')
  sw=int(r.stab_win)
  # frozen extreme used by LAB012 stabilization window, known at trigger k
  extreme=float(np.nanmin(lo[k-sw:k])) if sell else float(np.nanmax(hi[k-sw:k]))
  rows.append(dict(origin_idx=int(r.origin_idx),exhaust_cell=r.exhaust_cell,side=r.inverse_side,entry_idx=en,entry_minute=int(mins[en]),entry_time_msc=int(ft[en]),entry_bid=float(fb[en]),entry_ask=float(fa[en]),atr_entry=float(atr[en]),exhaust_extreme=extreme,year=int(yr[en])))
 s=pd.DataFrame(rows).sort_values(['entry_minute','exhaust_cell']).drop_duplicates(['origin_idx','exhaust_cell'])
 return d,e,s.reset_index(drop=True)

def replay(raw_zip,fr,s):
 if s.empty:return pd.DataFrame()
 starts=s.entry_time_msc.to_numpy(np.int64); order=np.argsort(starts);ss=starts[order];cache={}
 with zipfile.ZipFile(raw_zip) as z:
  names=set(z.namelist())
  for n,(member,f0,f1) in enumerate(fr,1):
   if member not in names:continue
   p=np.searchsorted(ss,f1,side='right');cand=order[:p];cand=cand[(starts[cand]+240*60000>=f0)]
   if not len(cand):continue
   with z.open(member) as fh:df=pd.read_csv(fh,usecols=['time_msc','bid','ask'])
   if df.empty:continue
   tt=df.time_msc.to_numpy(np.int64);bid=df.bid.to_numpy(float);ask=df.ask.to_numpy(float)
   for i in cand:
    if i in cache:continue
    st=int(starts[i]);en=st+240*60000-1;a0=np.searchsorted(tt,st);a1=np.searchsorted(tt,en,side='right')
    if a1>a0:cache[i]=(tt[a0:a1],bid[a0:a1],ask[a0:a1])
   if n%100==0:print('[RAW]',n,'cache',len(cache),flush=True)
 out=[]
 for i,r in s.iterrows():
  if i not in cache:continue
  tt,bid,ask=cache[i];buy=r.side=='BUY';px=bid if buy else ask;entry=float(r.entry_ask if buy else r.entry_bid);a=float(r.atr_entry);ext=float(r.exhaust_extreme)
  for buf in BUFFERS:
   sl=ext-buf*a if buy else ext+buf*a; risk=(entry-sl) if buy else (sl-entry)
   if risk<=0 or risk/a>5:continue
   comm=2*COMMISSION_RATE_SIDE*entry/risk
   for rr in RRS:
    tp=entry+rr*risk if buy else entry-rr*risk
    for hz in HORIZONS:
     mask=tt<=int(r.entry_time_msc)+hz*60000-1;p=px[mask];ts=tt[mask]
     if not len(p):continue
     hit=np.flatnonzero(((p>=tp)|(p<=sl)) if buy else ((p<=tp)|(p>=sl)))
     if len(hit):
      j=int(hit[0]);is_tp=(p[j]>=tp) if buy else (p[j]<=tp);R=(rr-comm) if is_tp else (-1-comm);oc='TP' if is_tp else 'SL';ht=int(ts[j])
     else:
      pnl=(p[-1]-entry) if buy else (entry-p[-1]);R=pnl/risk-comm;oc='TIME';ht=-1
     out.append(dict(signal_id=i,exhaust_cell=r.exhaust_cell,year=r.year,entry_minute=r.entry_minute,buffer_atr=buf,rr=rr,horizon=hz,payoff=f'B{buf:.2f}|RR{rr:.1f}|H{hz}',R=float(R),outcome=oc,hit_time_msc=ht,risk_atr=float(risk/a)))
 return pd.DataFrame(out)

def aggregate(ex):
 rows=[]
 for (c,p),g0 in ex.groupby(['exhaust_cell','payoff']):
  z={'exhaust_cell':c,'payoff':p,'buffer_atr':g0.buffer_atr.iloc[0],'rr':g0.rr.iloc[0],'horizon':g0.horizon.iloc[0],'risk_atr_median':float(g0.risk_atr.median())}
  for nm,yrs in [('train',{2023,2024}),('val',{2025}),('final',{2026})]:
   g=g0[g0.year.isin(yrs)].sort_values('entry_minute').drop_duplicates('signal_id');st=stats(g.R)
   for k,v in st.items():z[nm+'_'+k]=v
  rows.append(z)
 c=pd.DataFrame(rows)
 c['discovery_pass']=(c.train_n>=DISC_N)&(c.train_mean_R>=DISC_EV)&(c.train_pf>=DISC_PF)
 c['validation_pass']=(c.val_n>=VAL_N)&(c.val_mean_R>0)&(c.val_pf>1)
 c['locked_before_2026']=c.discovery_pass&c.validation_pass
 c['final_pass']=(c.final_n>=FINAL_N)&(c.final_mean_R>0)&(c.final_pf>1)
 return c.sort_values(['locked_before_2026','train_mean_R','val_mean_R'],ascending=[False,False,False])

def main():
 a=args();a.outdir.mkdir(parents=True,exist_ok=True);x=load_full(a.bars,a.labels);d,e,s=build_signals(x)
 print('forced',len(d),'stable exhaustion events',len(e),'signals',len(s),flush=True)
 s.to_parquet(a.outdir/'executable_signals.parquet',index=False)
 ex=replay(a.raw_zip,files(a.audit),s);ex.to_parquet(a.outdir/'exact_payoffs.parquet',index=False)
 c=aggregate(ex);c.to_csv(a.outdir/'candidate_transfer.csv',index=False)
 locked=int(c.locked_before_2026.sum());pos=int((c.locked_before_2026&c.final_pass).sum());best=c.iloc[0].to_dict() if len(c) else None
 verdict='FAIL_NO_PRE2026_EXECUTABLE_EDGE' if locked==0 else ('PASS_EXECUTABLE_OOS' if pos>0 else 'FAIL_OOS_TRANSFER')
 out={'lab':'XAU_EXHAUSTION_RECLAIM_EXECUTABLE_PAYOFF_LAB_013','forced_exit_rows':int(len(d)),'stable_exhaustion_events':int(len(e)),'unique_executable_signals':int(len(s)),'candidate_configs':int(len(c)),'locked_pre2026':locked,'locked_positive_2026':pos,'best_config':best,'verdict':verdict}
 (a.outdir/'verdict.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
