#!/usr/bin/env python3
"""XAU_EXHAUSTION_STATE_COMPRESSION_STRUCTURAL_RISK_SCALE_LAB_014

Compressed executable test of the LAB012 exhaustion thesis.

Important correction vs LAB013:
LAB012 exhaustion is defined as stabilization of the forced-exit/liquidation leg
followed by a reclaim opposite that leg. Therefore the post-exhaustion trade
direction is the ORIGINAL crowd direction (BUY_CROWD -> BUY,
SELL_CROWD -> SELL), not LAB013's inverse_side.

Compression removes breakout/commitment/underperformance lineage from the
selector. State uses only:
  trade side + stabilization age bucket + reclaim strength + liquidation depth.

Risk is structural, not tiny:
  ATR 0.50 / 0.75 / 1.00, plus swing-based risk floored at 0.50 ATR.
TP = 1.5R / 2.0R / 2.5R. Horizon = 60 / 120 / 240 minutes.

Selection:
  2023-24 discovery -> 2025 validation -> 2026 untouched OOS.
Execution:
  exact Bid/Ask raw ticks with cross-file horizon stitching.
"""
from __future__ import annotations
import argparse,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd
import xau_forced_exit_path_asymmetry_and_exhaustion_lab012 as l12

COMMISSION_RATE_SIDE=0.000007
AGE_BUCKETS=((20,'A0_20'),(60,'A21_60'),(120,'A61_120'))
DEPTH_CUTS=(1.50,3.00)
RISK_MODES=('ATR0.50','ATR0.75','ATR1.00','SWING_F0.50')
RRS=(1.5,2.0,2.5); HORIZONS=(60,120,240); DECLUSTER_MIN=240
DISC_N=150; VAL_N=50; FINAL_N=30; DISC_EV=0.03; DISC_PF=1.08; MIN_STATE_PREPASS=2

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
 return dict(n=int(len(a)),mean_R=float(a.mean()),pf=pf(a),win_rate=float((a>0).mean()),sum_R=float(a.sum()),max_dd_R=float(dd.max()) if len(dd) else 0.0)

def load_full(bp,lp):
 b=pd.read_parquet(bp);l=pd.read_parquet(lp)
 cols=['minute','timestamp_from_time_msc','first_time_msc','first_bid','first_ask','mid_open','mid_high','mid_low','mid_close']
 x=b[cols].merge(l[['minute','atr14_causal']],on='minute',validate='one_to_one').sort_values('minute').reset_index(drop=True)
 x['year']=pd.to_datetime(x.timestamp_from_time_msc).dt.year.astype(int);return x

def audit_files(audit):
 j=json.loads(audit.read_text());out=[]
 for f in j.get('files',[]):
  if f.get('valid_rows',0)>0 and f.get('first_time_msc') is not None: out.append((f['member'],int(f['first_time_msc']),int(f['last_time_msc'])))
 return sorted(out,key=lambda z:z[1])

def age_bucket(age):
 age=int(age)
 for mx,name in AGE_BUCKETS:
  if age<=mx:return name
 return None

def depth_bucket(v):
 v=float(v)
 if not np.isfinite(v):return None
 if v<DEPTH_CUTS[0]:return 'D0_1.5'
 if v<DEPTH_CUTS[1]:return 'D1.5_3'
 return 'D3P'

def build_compressed_signals(x):
 base=['minute','timestamp_from_time_msc','mid_open','mid_high','mid_low','mid_close','atr14_causal','year']
 d=l12.build_forced_exit_events(x[base].copy());p=l12.path_rows(x,d);e=l12.exhaustion_rows(x,p)
 if e.empty:return d,e,pd.DataFrame(),pd.DataFrame()
 es=l12.summarize_exhaust(e);stable=es[es.eligible].copy()
 stable['age_ratio']=np.maximum(stable.train_age_median,stable.val_age_median)/np.maximum(1.0,np.minimum(stable.train_age_median,stable.val_age_median))
 stable['mfe_gap']=(stable.train_pre_exhaust_mfe_median-stable.val_pre_exhaust_mfe_median).abs()
 stable_cells=set(stable.loc[(stable.age_ratio<=1.75)&(stable.mfe_gap<=0.50),'exhaust_cell'])
 e=e[e.exhaust_cell.isin(stable_cells)].copy()
 lineage=d[['origin_idx','cell','forced_idx','forced_minute','forced_close','atr']].drop_duplicates(['origin_idx','cell'])
 e=e.merge(lineage,on=['origin_idx','cell'],how='left',validate='many_to_one')
 hi=x.mid_high.to_numpy(float);lo=x.mid_low.to_numpy(float);mins=x.minute.to_numpy(np.int64);ft=x.first_time_msc.to_numpy(np.int64);fb=x.first_bid.to_numpy(float);fa=x.first_ask.to_numpy(float);atr=x.atr14_causal.to_numpy(float);yr=x.year.to_numpy(int)
 rows=[]
 for r in e.itertuples(index=False):
  k=int(r.exhaust_idx);q=int(r.forced_idx);en=k+1
  if en>=len(x) or q<0 or q>=k or not np.isfinite(atr[en]) or atr[en]<=0:continue
  trade_side='BUY' if r.crowd_side=='BUY_CROWD' else 'SELL'
  ab=age_bucket(r.age_min);db=depth_bucket(r.pre_exhaust_mfe_atr)
  if ab is None or db is None:continue
  liq_extreme=float(np.nanmin(lo[q+1:k+1])) if trade_side=='BUY' else float(np.nanmax(hi[q+1:k+1]))
  if not np.isfinite(liq_extreme):continue
  state=f'{trade_side}|{ab}|RC{float(r.reclaim_atr):.2f}|{db}'
  rows.append(dict(origin_idx=int(r.origin_idx),crowd_side=r.crowd_side,trade_side=trade_side,state=state,age_bucket=ab,reclaim_atr=float(r.reclaim_atr),depth_bucket=db,liquidation_depth_atr=float(r.pre_exhaust_mfe_atr),forced_idx=q,exhaust_idx=k,exhaust_age_min=int(r.age_min),entry_idx=en,entry_minute=int(mins[en]),entry_time_msc=int(ft[en]),entry_bid=float(fb[en]),entry_ask=float(fa[en]),atr_entry=float(atr[en]),liquidation_extreme=liq_extreme,year=int(yr[en])))
 s=pd.DataFrame(rows)
 if s.empty:return d,e,s,pd.DataFrame()
 s=s.sort_values(['origin_idx','state','exhaust_idx','entry_minute']).drop_duplicates(['origin_idx','state'],keep='first').reset_index(drop=True);s['signal_id']=np.arange(len(s),dtype=np.int64)
 sr=[]
 for st,g in s.groupby('state'):
  sr.append(dict(state=st,trade_side=g.trade_side.iloc[0],age_bucket=g.age_bucket.iloc[0],reclaim_atr=float(g.reclaim_atr.iloc[0]),depth_bucket=g.depth_bucket.iloc[0],train_struct_n=int(g.year.isin([2023,2024]).sum()),val_struct_n=int((g.year==2025).sum()),final_struct_n=int((g.year==2026).sum())))
 return d,e,s,pd.DataFrame(sr).sort_values('state').reset_index(drop=True)

def risk_distance(r,mode):
 a=float(r.atr_entry);entry=float(r.entry_ask if r.trade_side=='BUY' else r.entry_bid)
 if mode=='ATR0.50':return 0.50*a
 if mode=='ATR0.75':return 0.75*a
 if mode=='ATR1.00':return 1.00*a
 ext=float(r.liquidation_extreme);raw=(entry-ext) if r.trade_side=='BUY' else (ext-entry)
 return max(raw+0.10*a,0.50*a)

def replay(raw_zip,fr,s):
 if s.empty:return pd.DataFrame()
 starts=s.entry_time_msc.to_numpy(np.int64);order=np.argsort(starts);ss=starts[order];max_h=max(HORIZONS)*60000;chunks={}
 with zipfile.ZipFile(raw_zip) as z:
  names=set(z.namelist())
  for n,(member,f0,f1) in enumerate(fr,1):
   if member not in names:continue
   p=int(np.searchsorted(ss,f1,side='right'));cand=order[:p];cand=cand[(starts[cand]+max_h>=f0)]
   if not len(cand):continue
   with z.open(member) as fh:df=pd.read_csv(fh,usecols=['time_msc','bid','ask'])
   if df.empty:continue
   tt=df.time_msc.to_numpy(np.int64);bid=df.bid.to_numpy(float);ask=df.ask.to_numpy(float)
   for i in cand:
    st=int(starts[i]);en=st+max_h-1;a0=int(np.searchsorted(tt,st));a1=int(np.searchsorted(tt,en,side='right'))
    if a1<=a0:continue
    if i not in chunks:chunks[i]=[[],[],[]]
    chunks[i][0].append(tt[a0:a1]);chunks[i][1].append(bid[a0:a1]);chunks[i][2].append(ask[a0:a1])
   if n%100==0:print('[RAW]',n,'signals with chunks',len(chunks),flush=True)
 cache={}
 for i,parts in chunks.items():
  tt=np.concatenate(parts[0]);bid=np.concatenate(parts[1]);ask=np.concatenate(parts[2])
  if len(tt)>1:
   o=np.argsort(tt,kind='stable');tt,bid,ask=tt[o],bid[o],ask[o];keep=np.r_[True,tt[1:]!=tt[:-1]];tt,bid,ask=tt[keep],bid[keep],ask[keep]
  cache[i]=(tt,bid,ask)
 out=[]
 for i,r in s.iterrows():
  if i not in cache:continue
  tt,bid,ask=cache[i];buy=r.trade_side=='BUY';exit_px=bid if buy else ask;entry=float(r.entry_ask if buy else r.entry_bid);a=float(r.atr_entry)
  for mode in RISK_MODES:
   risk=float(risk_distance(r,mode))
   if not np.isfinite(risk) or risk<=0:continue
   risk_atr=risk/a
   if risk_atr>6.0:continue
   sl=entry-risk if buy else entry+risk;comm_R=2.0*COMMISSION_RATE_SIDE*entry/risk
   for rr in RRS:
    tp=entry+rr*risk if buy else entry-rr*risk
    for hz in HORIZONS:
     end_t=int(r.entry_time_msc)+hz*60000-1;mask=tt<=end_t;p=exit_px[mask];ts=tt[mask]
     if not len(p):continue
     hit=np.flatnonzero(((p>=tp)|(p<=sl)) if buy else ((p<=tp)|(p>=sl)))
     if len(hit):
      j=int(hit[0]);is_tp=(p[j]>=tp) if buy else (p[j]<=tp);R=(rr-comm_R) if is_tp else (-1.0-comm_R);oc='TP' if is_tp else 'SL';ht=int(ts[j])
     else:
      pnl=(p[-1]-entry) if buy else (entry-p[-1]);R=pnl/risk-comm_R;oc='TIME';ht=-1
     out.append(dict(signal_id=int(r.signal_id),state=r.state,trade_side=r.trade_side,year=int(r.year),entry_minute=int(r.entry_minute),risk_mode=mode,rr=float(rr),horizon=int(hz),payoff=f'{mode}|RR{rr:.1f}|H{hz}',risk_atr=float(risk_atr),R=float(R),outcome=oc,hit_time_msc=ht))
 return pd.DataFrame(out)

def decluster(g,gap_min=DECLUSTER_MIN):
 if g.empty:return g
 g=g.sort_values(['entry_minute','signal_id']).drop_duplicates('signal_id');keep=[];last=-10**18
 for idx,r in g.iterrows():
  m=int(r.entry_minute)
  if m-last>=gap_min:keep.append(idx);last=m
 return g.loc[keep]

def aggregate(ex):
 rows=[]
 for (st,payoff),g0 in ex.groupby(['state','payoff']):
  z=dict(state=st,payoff=payoff,trade_side=g0.trade_side.iloc[0],risk_mode=g0.risk_mode.iloc[0],rr=float(g0.rr.iloc[0]),horizon=int(g0.horizon.iloc[0]),risk_atr_median=float(g0.risk_atr.median()))
  for nm,yrs in [('train',{2023,2024}),('val',{2025}),('final',{2026})]:
   g=decluster(g0[g0.year.isin(yrs)]);stt=stats(g.R)
   for k,v in stt.items():z[nm+'_'+k]=v
  rows.append(z)
 c=pd.DataFrame(rows)
 if c.empty:return c
 c['discovery_pass']=(c.train_n>=DISC_N)&(c.train_mean_R>=DISC_EV)&(c.train_pf>=DISC_PF)
 c['validation_pass']=(c.val_n>=VAL_N)&(c.val_mean_R>0)&(c.val_pf>1)
 c['prepass']=c.discovery_pass&c.validation_pass;c['state_prepass_count']=c.groupby('state').prepass.transform('sum').astype(int)
 c['locked_before_2026']=c.prepass&(c.state_prepass_count>=MIN_STATE_PREPASS)
 c['final_pass']=(c.final_n>=FINAL_N)&(c.final_mean_R>0)&(c.final_pf>1)
 return c.sort_values(['locked_before_2026','state_prepass_count','train_mean_R','val_mean_R'],ascending=[False,False,False,False]).reset_index(drop=True)

def yearly_locked(ex,c):
 if c.empty or not c.locked_before_2026.any():return pd.DataFrame()
 keys=c.loc[c.locked_before_2026,['state','payoff']].drop_duplicates();z=ex.merge(keys,on=['state','payoff'],how='inner');rows=[]
 for (st,payoff,year),g in z.groupby(['state','payoff','year']):
  q=stats(decluster(g).R);rows.append(dict(state=st,payoff=payoff,year=int(year),**q))
 return pd.DataFrame(rows).sort_values(['state','payoff','year'])

def main():
 a=args();a.outdir.mkdir(parents=True,exist_ok=True);x=load_full(a.bars,a.labels);d,e,s,screen=build_compressed_signals(x)
 print('forced',len(d),'stable exhaustion events',len(e),'compressed signals',len(s),'states',len(screen),flush=True)
 if s.empty:raise RuntimeError('no compressed exhaustion signals')
 s.to_parquet(a.outdir/'compressed_signals.parquet',index=False);screen.to_csv(a.outdir/'compressed_state_screen.csv',index=False)
 ex=replay(a.raw_zip,audit_files(a.audit),s)
 if ex.empty:raise RuntimeError('no exact payoff rows')
 ex.to_parquet(a.outdir/'exact_payoffs.parquet',index=False);c=aggregate(ex);c.to_csv(a.outdir/'candidate_transfer.csv',index=False);yearly_locked(ex,c).to_csv(a.outdir/'locked_yearly.csv',index=False)
 locked=int(c.locked_before_2026.sum()) if len(c) else 0;pos=int((c.locked_before_2026&c.final_pass).sum()) if len(c) else 0;locked_states=int(c.loc[c.locked_before_2026,'state'].nunique()) if locked else 0
 best=c.iloc[0].to_dict() if len(c) else None
 verdict='FAIL_NO_PRE2026_COMPRESSED_EDGE' if locked==0 else ('PASS_COMPRESSED_EXECUTABLE_OOS' if pos>0 else 'FAIL_OOS_TRANSFER')
 out={'lab':'XAU_EXHAUSTION_STATE_COMPRESSION_STRUCTURAL_RISK_SCALE_LAB_014','correction_vs_lab013':'post-exhaustion trade direction follows original crowd/reclaim direction; LAB013 traded inverse_side/liquidation direction','forced_exit_rows':int(len(d)),'stable_exhaustion_rows':int(len(e)),'compressed_signals':int(len(s)),'compressed_states':int(len(screen)),'candidate_configs':int(len(c)),'locked_configs_pre2026':locked,'locked_states_pre2026':locked_states,'locked_positive_2026':pos,'best_config':best,'verdict':verdict}
 (a.outdir/'verdict.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
