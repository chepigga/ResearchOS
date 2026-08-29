#!/usr/bin/env python3
"""XAU_CROWDED_ENTRY_UNDERPERFORMANCE_AND_FORCED_EXIT_LAB_011

Price+time crowd-inventory test.
Causality: prior 60m level uses completed bars only; breakout/commitment/underperformance/
forced-exit use completed M1 bars; inverse entry is first tick of next M1.
Selection: 2023-24 discovery -> 2025 validation -> 2026 untouched OOS.
Execution: Bid/Ask-aware exact tick replay from frozen raw XAU zip.
"""
from __future__ import annotations
import argparse,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd

COMMISSION_RATE_SIDE=0.000007; COOLDOWN=240
BREAK_ATR=(0.10,0.20); COMMIT_MIN=(3,5); COMMIT_ATR=(0.20,0.35)
UNDER_MIN=(5,10,15); MAX_EXTRA_PROGRESS_ATR=(0.10,0.20)
RETURN_MODE=('LEVEL','ENTRY_ZONE')
TARGET_ATR=(0.30,0.40); RR=(1.5,2.0); HORIZON=(10,20)
DISC_N=80; VAL_N=30; DISC_EV=0.03; DISC_PF=1.08; FINAL_N=20

def args():
 p=argparse.ArgumentParser();
 for k in ['bars','labels','audit','raw_zip','outdir']: p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
 return p.parse_args()

def pf(a):
 a=np.asarray(a,float);a=a[np.isfinite(a)]; gp=a[a>0].sum();gl=-a[a<0].sum();return float(gp/gl) if gl>0 else None

def stats(a):
 a=np.asarray(a,float);a=a[np.isfinite(a)]
 if not len(a): return dict(n=0,mean_R=None,pf=None,win_rate=None,sum_R=0.0,max_dd_R=None)
 eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=pk[1:]-eq
 return dict(n=int(len(a)),mean_R=float(a.mean()),pf=pf(a),win_rate=float((a>0).mean()),sum_R=float(a.sum()),max_dd_R=float(dd.max()) if len(dd) else 0.)

def load(bp,lp):
 b=pd.read_parquet(bp);l=pd.read_parquet(lp)
 cols=['minute','timestamp_from_time_msc','first_time_msc','first_bid','first_ask','mid_open','mid_high','mid_low','mid_close']
 x=b[cols].merge(l[['minute','atr14_causal']],on='minute',validate='one_to_one').sort_values('minute').reset_index(drop=True)
 x['year']=pd.to_datetime(x.timestamp_from_time_msc).dt.year.astype(int);return x

def build_events(x):
 hi=x.mid_high.to_numpy(float);lo=x.mid_low.to_numpy(float);cl=x.mid_close.to_numpy(float);atr=x.atr14_causal.to_numpy(float)
 mins=x.minute.to_numpy(np.int64);ft=x.first_time_msc.to_numpy(np.int64);fb=x.first_bid.to_numpy(float);fa=x.first_ask.to_numpy(float);yr=x.year.to_numpy(int)
 prior_hi=pd.Series(hi).shift(1).rolling(60,min_periods=60).max().to_numpy();prior_lo=pd.Series(lo).shift(1).rolling(60,min_periods=60).min().to_numpy()
 rows=[];n=len(x)
 # de-duplicate raw breakout origins by side/parameter with local 60m spacing later
 for br in BREAK_ATR:
  buy_idx=np.flatnonzero(np.isfinite(atr)&(atr>0)&(cl>=prior_hi+br*atr));sell_idx=np.flatnonzero(np.isfinite(atr)&(atr>0)&(cl<=prior_lo-br*atr))
  for side,idxs in [('BUY_CROWD',buy_idx),('SELL_CROWD',sell_idx)]:
   last=-999999
   for i in idxs:
    if i-last<60 or i+40>=n: continue
    last=i; level=float(prior_hi[i] if side=='BUY_CROWD' else prior_lo[i]); a=float(atr[i]); crowd_entry=float(cl[i])
    for cm in COMMIT_MIN:
     j=i+cm-1
     if j>=n-2: continue
     commit_prog=((cl[j]-level)/a) if side=='BUY_CROWD' else ((level-cl[j])/a)
     for ca in COMMIT_ATR:
      if commit_prog<ca: continue
      commit_close=float(cl[j]); crowd_entry=(float(cl[i])+commit_close)/2.0
      for um in UNDER_MIN:
       e=j+um
       if e>=n-2: continue
       wh=hi[j+1:e+1];wl=lo[j+1:e+1]
       extra=(np.nanmax(wh)-commit_close)/a if side=='BUY_CROWD' else (commit_close-np.nanmin(wl))/a
       for mx in MAX_EXTRA_PROGRESS_ATR:
        if extra>mx: continue
        eff=extra/max(ca,1e-9)
        for mode in RETURN_MODE:
         trig=None
         # after underperformance is known, wait <=10 completed bars for crowd pain/forced exit
         for q in range(e,e+11):
          if q>=n-1: break
          if side=='BUY_CROWD':
           threshold=level if mode=='LEVEL' else crowd_entry
           ok=cl[q] <= threshold
          else:
           threshold=level if mode=='LEVEL' else crowd_entry
           ok=cl[q] >= threshold
          if ok: trig=q;break
         if trig is None: continue
         en=trig+1
         inv='SELL' if side=='BUY_CROWD' else 'BUY'
         rows.append(dict(origin_idx=int(i),crowd_side=side,inverse_side=inv,break_atr=br,commit_min=cm,commit_atr=ca,under_min=um,max_extra_progress_atr=mx,return_mode=mode,level=level,crowd_entry_proxy=crowd_entry,efficiency=float(eff),entry_idx=en,entry_minute=int(mins[en]),entry_time_msc=int(ft[en]),entry_bid=float(fb[en]),entry_ask=float(fa[en]),atr_entry=float(atr[en]),entry_year=int(yr[en]),cell=f'{side}|B{br:.2f}|C{cm}_{ca:.2f}|U{um}_{mx:.2f}|{mode}'))
 if not rows:return pd.DataFrame()
 d=pd.DataFrame(rows).sort_values(['entry_minute','cell']).drop_duplicates(['origin_idx','cell'])
 return d.reset_index(drop=True)

def structural_screen(d):
 r=[]
 for c,g in d.groupby('cell'):
  f=g.iloc[0];tr=int(g.entry_year.isin([2023,2024]).sum());va=int((g.entry_year==2025).sum());fi=int((g.entry_year==2026).sum())
  r.append(dict(cell=c,crowd_side=f.crowd_side,break_atr=f.break_atr,commit_min=f.commit_min,commit_atr=f.commit_atr,under_min=f.under_min,max_extra_progress_atr=f.max_extra_progress_atr,return_mode=f.return_mode,train_struct_n=tr,val_struct_n=va,final_struct_n=fi,eligible=bool(tr>=DISC_N and va>=VAL_N)))
 return pd.DataFrame(r)

def files(audit):
 z=json.loads(audit.read_text()); out=[]
 for f in z.get('files',[]):
  if f.get('valid_rows',0)>0 and f.get('first_time_msc') is not None: out.append((f['member'],int(f['first_time_msc']),int(f['last_time_msc'])))
 return sorted(out,key=lambda x:x[1])

def unique_signals(d,s):
 cells=set(s.loc[s.eligible,'cell']);m=d[d.cell.isin(cells)].copy();
 u=m[['origin_idx','inverse_side','entry_idx','entry_minute','entry_time_msc','entry_bid','entry_ask','atr_entry','entry_year']].drop_duplicates().reset_index(drop=True);u['signal_uid']=np.arange(len(u));
 m=m.merge(u[['origin_idx','inverse_side','entry_idx','signal_uid']],on=['origin_idx','inverse_side','entry_idx'],how='inner');return u,m

def replay(raw_zip,fr,u):
 # one tick slice per physical signal, resolve all frozen payoff variants simultaneously
 outs=[]
 with zipfile.ZipFile(raw_zip) as z:
  names=set(z.namelist())
  # bucket signals by file overlap via start time; horizons max 20m
  starts=u.entry_time_msc.to_numpy(np.int64); order=np.argsort(starts); ss=starts[order]
  cache={}
  for k,(member,f0,f1) in enumerate(fr,1):
   if member not in names: continue
   p=int(np.searchsorted(ss,f1,side='right')); cand=order[:p]; cand=cand[(starts[cand]+20*60000>=f0)]
   if not len(cand): continue
   with z.open(member) as fh: df=pd.read_csv(fh,usecols=['time_msc','bid','ask'])
   if df.empty:continue
   tt=df.time_msc.to_numpy(np.int64);bid=df.bid.to_numpy(float);ask=df.ask.to_numpy(float)
   for ei in cand:
    if ei in cache: continue
    st=int(starts[ei]); en=st+20*60000-1; a0=np.searchsorted(tt,st);a1=np.searchsorted(tt,en,side='right')
    if a1>a0: cache[ei]=(tt[a0:a1],bid[a0:a1],ask[a0:a1])
   if k%100==0: print('[RAW]',k,'cache',len(cache),flush=True)
 for ei,r in u.iterrows():
  if ei not in cache:continue
  tt,bid,ask=cache[ei]; buy=r.inverse_side=='BUY'; px=bid if buy else ask; entry=r.entry_ask if buy else r.entry_bid; a=r.atr_entry
  for t in TARGET_ATR:
   for rr in RR:
    stop=t/rr;tp=entry+t*a if buy else entry-t*a;sl=entry-stop*a if buy else entry+stop*a;comm=2*COMMISSION_RATE_SIDE*entry/(stop*a)
    for hz in HORIZON:
     mask=tt<=r.entry_time_msc+hz*60000-1;p=px[mask];ts=tt[mask]
     if not len(p):continue
     hit=np.flatnonzero(((p>=tp)|(p<=sl)) if buy else ((p<=tp)|(p>=sl)))
     if len(hit):
      j=int(hit[0]);is_tp=(p[j]>=tp) if buy else (p[j]<=tp);R=(rr-comm) if is_tp else (-1-comm);out='TP' if is_tp else 'SL';ht=int(ts[j])
     else:
      pnl=(p[-1]-entry) if buy else (entry-p[-1]);R=pnl/(stop*a)-comm;out='TIME';ht=-1
     outs.append(dict(signal_uid=int(r.signal_uid),target_atr=t,rr=rr,horizon=hz,payoff=f'T{t:.2f}|RR{rr:.1f}|H{hz}',R_exact=float(R),outcome=out,hit_time_msc=ht))
 return pd.DataFrame(outs)

def aggregate(ex,m,s):
 z=ex.merge(m[['signal_uid','cell','entry_minute','entry_year']].drop_duplicates(),on='signal_uid',how='inner');rows=[]
 for (c,p),g0 in z.groupby(['cell','payoff']):
  row={'cell':c,'payoff':p,'target_atr':g0.target_atr.iloc[0],'rr':g0.rr.iloc[0],'horizon':g0.horizon.iloc[0]}
  for nm,yrs in [('train',{2023,2024}),('val',{2025}),('final',{2026})]:
   g=g0[g0.entry_year.isin(yrs)].sort_values('entry_minute').drop_duplicates('signal_uid');st=stats(g.R_exact)
   for k,v in st.items():row[nm+'_'+k]=v
  rows.append(row)
 c=pd.DataFrame(rows).merge(s[['cell','eligible']],on='cell',how='left')
 c['discovery_pass']=c.eligible&(c.train_n>=DISC_N)&(c.train_mean_R>=DISC_EV)&(c.train_pf>=DISC_PF)
 c['validation_pass']=(c.val_n>=VAL_N)&(c.val_mean_R>0)&(c.val_pf>1)
 c['locked_before_2026']=c.discovery_pass&c.validation_pass
 c['final_pass']=(c.final_n>=FINAL_N)&(c.final_mean_R>0)&(c.final_pf>1)
 return c.sort_values(['locked_before_2026','train_mean_R','val_mean_R'],ascending=[False,False,False])

def main():
 a=args();a.outdir.mkdir(parents=True,exist_ok=True);x=load(a.bars,a.labels);d=build_events(x);print('struct rows',len(d),flush=True)
 if d.empty:raise RuntimeError('no events')
 d.to_parquet(a.outdir/'crowd_inventory_events.parquet',index=False);s=structural_screen(d);s.to_csv(a.outdir/'structural_screen.csv',index=False)
 u,m=unique_signals(d,s);print('eligible cells',int(s.eligible.sum()),'unique signals',len(u),flush=True)
 ex=replay(a.raw_zip,files(a.audit),u);ex.to_parquet(a.outdir/'exact_payoffs.parquet',index=False);c=aggregate(ex,m,s);c.to_csv(a.outdir/'candidate_transfer.csv',index=False)
 locked=int(c.locked_before_2026.sum());pos=int((c.locked_before_2026&c.final_pass).sum());best=c.iloc[0].to_dict() if len(c) else None
 verdict='FAIL_NO_PRE2026_TRANSFER' if locked==0 else ('PASS' if pos>0 else 'FAIL_OOS')
 out={'lab':'XAU_CROWDED_ENTRY_UNDERPERFORMANCE_AND_FORCED_EXIT_LAB_011','structural_rows':int(len(d)),'eligible_cells_pre2026':int(s.eligible.sum()),'unique_physical_signals':int(len(u)),'locked_configs_pre2026':locked,'locked_positive_2026':pos,'best_config':best,'verdict':verdict}
 (a.outdir/'verdict.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
