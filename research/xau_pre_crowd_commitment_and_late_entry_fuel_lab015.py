#!/usr/bin/env python3
"""XAU_PRE_CROWD_COMMITMENT_AND_LATE_ENTRY_FUEL_LAB_015

Causal pre-crowd test.
Hypothesis: enter BEFORE an obvious breakout/crowd commitment in the same direction,
then let late breakout traders and stops provide continuation fuel.

No future leakage:
- precursor state at completed M1 bar t uses only t and earlier completed bars;
- executable entry is first tick of minute t+1;
- future crowd commitment within 5/10/20m is LABEL/diagnostic only and is never
  required for a trade to exist;
- selector locked on 2023-24 discovery + 2025 validation; 2026 untouched OOS.
"""
from __future__ import annotations
import argparse,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd

COMMISSION_RATE_SIDE=0.000007
PROX_CUT=0.10; MAX_PROX=0.20; ATTACK_ATR=0.10; ATTACK_MIN=2
COMP_MAX_ATR=1.00; RESILIENCE_MAX_ATR=0.75; DWELL_ATR=0.30; DWELL_MIN=4; PRESSURE_MIN_ATR=0.10
SCORES=(3,4,5); CROWD_HORIZONS=(5,10,20); CROWD_COMMIT_ATR=0.20
RISK_MODES=('ATR0.50','ATR0.75','ATR1.00','STRUCT_F0.50'); RRS=(1.5,2.0,2.5); HORIZONS=(60,120,240)
SIGNAL_COOLDOWN_MIN=60; PAYOFF_DECLUSTER_MIN=240
DISC_N=100; VAL_N=40; FINAL_N=20; DISC_EV=0.03; DISC_PF=1.08; MIN_STATE_PREPASS=2

def args():
 p=argparse.ArgumentParser()
 for k in ['bars','labels','audit','raw_zip','outdir']: p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
 return p.parse_args()

def pf(a):
 a=np.asarray(a,float);a=a[np.isfinite(a)];gp=a[a>0].sum();gl=-a[a<0].sum();return float(gp/gl) if gl>0 else None

def stats(a):
 a=np.asarray(a,float);a=a[np.isfinite(a)]
 if not len(a):return dict(n=0,mean_R=None,pf=None,win_rate=None,sum_R=0.0,max_dd_R=None)
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
  if f.get('valid_rows',0)>0 and f.get('first_time_msc') is not None:out.append((f['member'],int(f['first_time_msc']),int(f['last_time_msc'])))
 return sorted(out,key=lambda z:z[1])

def physical_cooldown(df,gap=SIGNAL_COOLDOWN_MIN):
 if df.empty:return df
 keep=[];last={'BUY':-10**18,'SELL':-10**18}
 for idx,r in df.sort_values(['minute','side']).iterrows():
  m=int(r.minute);s=r.side
  if m-last[s]>=gap:keep.append(idx);last[s]=m
 return df.loc[keep].sort_values(['minute','side']).reset_index(drop=True)

def build_precursors(x):
 hi=x.mid_high.to_numpy(float);lo=x.mid_low.to_numpy(float);cl=x.mid_close.to_numpy(float);atr=x.atr14_causal.to_numpy(float)
 mins=x.minute.to_numpy(np.int64);ft=x.first_time_msc.to_numpy(np.int64);fb=x.first_bid.to_numpy(float);fa=x.first_ask.to_numpy(float);yr=x.year.to_numpy(int)
 prior_hi=pd.Series(hi).shift(1).rolling(60,min_periods=60).max().to_numpy();prior_lo=pd.Series(lo).shift(1).rolling(60,min_periods=60).min().to_numpy()
 rows=[];base_rows=[];n=len(x)
 for i in range(60,n-max(HORIZONS)-2):
  a=float(atr[i])
  if not np.isfinite(a) or a<=0:continue
  for side in ('BUY','SELL'):
   level=float(prior_hi[i] if side=='BUY' else prior_lo[i])
   if not np.isfinite(level):continue
   if side=='BUY':
    dist=(level-cl[i])/a
    if dist<0 or dist>MAX_PROX:continue
   else:
    dist=(cl[i]-level)/a
    if dist<0 or dist>MAX_PROX:continue
   h20=hi[i-19:i+1];l20=lo[i-19:i+1];c10=cl[i-9:i+1];h10=hi[i-9:i+1];l10=lo[i-9:i+1]
   if side=='BUY':
    attacks=int(np.sum(h20>=level-ATTACK_ATR*a));resilience=(level-np.nanmin(l10))/a;dwell=int(np.sum((level-c10)<=DWELL_ATR*a));pressure=(cl[i]-cl[i-5])/a;local_extreme=float(np.nanmin(l10))
   else:
    attacks=int(np.sum(l20<=level+ATTACK_ATR*a));resilience=(np.nanmax(h10)-level)/a;dwell=int(np.sum((c10-level)<=DWELL_ATR*a));pressure=(cl[i-5]-cl[i])/a;local_extreme=float(np.nanmax(h10))
   compression=(np.nanmax(h10)-np.nanmin(l10))/a
   score=int((attacks>=ATTACK_MIN)+(compression<=COMP_MAX_ATR)+(resilience<=RESILIENCE_MAX_ATR)+(dwell>=DWELL_MIN)+(pressure>=PRESSURE_MIN_ATR))
   prox='P0_0.10' if dist<=PROX_CUT else 'P0.10_0.20'
   crowd={};lat=None
   for h in CROWD_HORIZONS:
    fut=cl[i+1:i+h+1];hit=np.flatnonzero(fut>=level+CROWD_COMMIT_ATR*a) if side=='BUY' else np.flatnonzero(fut<=level-CROWD_COMMIT_ATR*a)
    crowd[f'crowd_commit_{h}']=bool(len(hit))
    if h==max(CROWD_HORIZONS) and len(hit):lat=int(hit[0]+1)
   base_rows.append(dict(idx=i,minute=int(mins[i]),side=side,year=int(yr[i]),dist_atr=float(dist),score=score,**crowd))
   if score not in SCORES:continue
   en=i+1;state=f'{side}|{prox}|S{score}'
   rows.append(dict(signal_idx=i,minute=int(mins[i]),signal_time_msc=int(ft[i]),side=side,state=state,prox_bucket=prox,score=score,level=level,dist_atr=float(dist),attacks=attacks,compression_atr=float(compression),resilience_atr=float(resilience),dwell=dwell,pressure_atr=float(pressure),local_extreme=local_extreme,atr_signal=a,entry_idx=en,entry_minute=int(mins[en]),entry_time_msc=int(ft[en]),entry_bid=float(fb[en]),entry_ask=float(fa[en]),atr_entry=float(atr[en]),year=int(yr[en]),crowd_latency_20=lat,**crowd))
 base=pd.DataFrame(base_rows);s=pd.DataFrame(rows)
 if s.empty:return base,s
 s=physical_cooldown(s);s['signal_id']=np.arange(len(s),dtype=np.int64);return base,s

def crowd_transfer_table(base,s):
 if s.empty:return pd.DataFrame()
 rows=[]
 for state,g in s.groupby('state'):
  z=dict(state=state,side=g.side.iloc[0],score=int(g.score.iloc[0]),prox_bucket=g.prox_bucket.iloc[0])
  for nm,yrs in [('train',{2023,2024}),('val',{2025}),('final',{2026})]:
   q=g[g.year.isin(yrs)];b=base[(base.side==g.side.iloc[0])&base.year.isin(yrs)];z[f'{nm}_n']=int(len(q))
   for h in CROWD_HORIZONS:
    qr=float(q[f'crowd_commit_{h}'].mean()) if len(q) else None;br=float(b[f'crowd_commit_{h}'].mean()) if len(b) else None
    z[f'{nm}_commit{h}']=qr;z[f'{nm}_baseline{h}']=br;z[f'{nm}_lift{h}']=float(qr/br) if qr is not None and br is not None and br>0 else None
  rows.append(z)
 return pd.DataFrame(rows).sort_values(['train_commit20','val_commit20'],ascending=False).reset_index(drop=True)

def risk_distance(r,mode):
 a=float(r.atr_entry);entry=float(r.entry_ask if r.side=='BUY' else r.entry_bid)
 if mode=='ATR0.50':return .50*a
 if mode=='ATR0.75':return .75*a
 if mode=='ATR1.00':return 1.00*a
 ext=float(r.local_extreme);raw=(entry-ext) if r.side=='BUY' else (ext-entry);return max(raw+.10*a,.50*a)

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
   for ii in cand:
    st=int(starts[ii]);en=st+max_h-1;a0=int(np.searchsorted(tt,st));a1=int(np.searchsorted(tt,en,side='right'))
    if a1<=a0:continue
    if ii not in chunks:chunks[ii]=[[],[],[]]
    chunks[ii][0].append(tt[a0:a1]);chunks[ii][1].append(bid[a0:a1]);chunks[ii][2].append(ask[a0:a1])
   if n%100==0:print('[RAW]',n,'signals with chunks',len(chunks),flush=True)
 cache={}
 for ii,parts in chunks.items():
  tt=np.concatenate(parts[0]);bid=np.concatenate(parts[1]);ask=np.concatenate(parts[2])
  if len(tt)>1:
   o=np.argsort(tt,kind='stable');tt,bid,ask=tt[o],bid[o],ask[o];keep=np.r_[True,tt[1:]!=tt[:-1]];tt,bid,ask=tt[keep],bid[keep],ask[keep]
  cache[ii]=(tt,bid,ask)
 out=[]
 for ii,r in s.iterrows():
  if ii not in cache:continue
  tt,bid,ask=cache[ii];buy=r.side=='BUY';exit_px=bid if buy else ask;entry=float(r.entry_ask if buy else r.entry_bid);a=float(r.atr_entry)
  if not np.isfinite(a) or a<=0:continue
  for mode in RISK_MODES:
   risk=float(risk_distance(r,mode))
   if not np.isfinite(risk) or risk<=0:continue
   risk_atr=risk/a
   if risk_atr>5.0:continue
   sl=entry-risk if buy else entry+risk;comm_R=2.0*COMMISSION_RATE_SIDE*entry/risk
   for rr in RRS:
    tp=entry+rr*risk if buy else entry-rr*risk
    for hz in HORIZONS:
     end_t=int(r.entry_time_msc)+hz*60000-1;mask=tt<=end_t;p=exit_px[mask];ts=tt[mask]
     if not len(p):continue
     hit=np.flatnonzero(((p>=tp)|(p<=sl)) if buy else ((p<=tp)|(p>=sl)))
     if len(hit):
      j=int(hit[0]);is_tp=(p[j]>=tp) if buy else (p[j]<=tp);R=(rr-comm_R) if is_tp else (-1.-comm_R);oc='TP' if is_tp else 'SL';ht=int(ts[j])
     else:
      pnl=(p[-1]-entry) if buy else (entry-p[-1]);R=pnl/risk-comm_R;oc='TIME';ht=-1
     out.append(dict(signal_id=int(r.signal_id),state=r.state,side=r.side,year=int(r.year),entry_minute=int(r.entry_minute),crowd_commit_20=bool(r.crowd_commit_20),crowd_latency_20=r.crowd_latency_20,risk_mode=mode,rr=float(rr),horizon=int(hz),payoff=f'{mode}|RR{rr:.1f}|H{hz}',risk_atr=float(risk_atr),R=float(R),outcome=oc,hit_time_msc=ht))
 return pd.DataFrame(out)

def decluster(g,gap_min=PAYOFF_DECLUSTER_MIN):
 if g.empty:return g
 g=g.sort_values(['entry_minute','signal_id']).drop_duplicates('signal_id');keep=[];last=-10**18
 for idx,r in g.iterrows():
  m=int(r.entry_minute)
  if m-last>=gap_min:keep.append(idx);last=m
 return g.loc[keep]

def aggregate(ex,crowd_table):
 rows=[];crowd_idx=crowd_table.set_index('state') if len(crowd_table) else None
 for (state,payoff),g0 in ex.groupby(['state','payoff']):
  z=dict(state=state,payoff=payoff,side=g0.side.iloc[0],risk_mode=g0.risk_mode.iloc[0],rr=float(g0.rr.iloc[0]),horizon=int(g0.horizon.iloc[0]),risk_atr_median=float(g0.risk_atr.median()))
  for nm,yrs in [('train',{2023,2024}),('val',{2025}),('final',{2026})]:
   g=decluster(g0[g0.year.isin(yrs)]);st=stats(g.R)
   for k,v in st.items():z[nm+'_'+k]=v
   z[nm+'_commit20']=float(g.crowd_commit_20.mean()) if len(g) else None
   gc=g[g.crowd_commit_20];gn=g[~g.crowd_commit_20];z[nm+'_R_if_commit20']=float(gc.R.mean()) if len(gc) else None;z[nm+'_R_if_no_commit20']=float(gn.R.mean()) if len(gn) else None
  if crowd_idx is not None and state in crowd_idx.index:
   cr=crowd_idx.loc[state]
   for col in ['train_lift20','val_lift20','final_lift20','train_commit20','val_commit20','final_commit20']:z['precursor_'+col]=cr.get(col)
  rows.append(z)
 c=pd.DataFrame(rows)
 if c.empty:return c
 c['fuel_transfer']=(c.precursor_train_lift20>=1.05)&(c.precursor_val_lift20>=1.00)&(c.precursor_val_commit20>=.70*c.precursor_train_commit20)
 c['discovery_pass']=(c.train_n>=DISC_N)&(c.train_mean_R>=DISC_EV)&(c.train_pf>=DISC_PF)
 c['validation_pass']=(c.val_n>=VAL_N)&(c.val_mean_R>0)&(c.val_pf>1)
 c['prepass']=c.discovery_pass&c.validation_pass&c.fuel_transfer;c['state_prepass_count']=c.groupby('state').prepass.transform('sum').astype(int)
 c['locked_before_2026']=c.prepass&(c.state_prepass_count>=MIN_STATE_PREPASS);c['final_pass']=(c.final_n>=FINAL_N)&(c.final_mean_R>0)&(c.final_pf>1)
 return c.sort_values(['locked_before_2026','state_prepass_count','train_mean_R','val_mean_R'],ascending=[False,False,False,False]).reset_index(drop=True)

def yearly_locked(ex,c):
 if c.empty or not c.locked_before_2026.any():return pd.DataFrame()
 keys=c.loc[c.locked_before_2026,['state','payoff']].drop_duplicates();z=ex.merge(keys,on=['state','payoff'],how='inner');rows=[]
 for (state,payoff,year),g in z.groupby(['state','payoff','year']):rows.append(dict(state=state,payoff=payoff,year=int(year),**stats(decluster(g).R)))
 return pd.DataFrame(rows).sort_values(['state','payoff','year'])

def main():
 a=args();a.outdir.mkdir(parents=True,exist_ok=True);x=load_full(a.bars,a.labels);base,s=build_precursors(x)
 if s.empty:raise RuntimeError('no causal precursor signals')
 crowd=crowd_transfer_table(base,s);print('near-level base',len(base),'signals',len(s),'states',s.state.nunique(),flush=True)
 base.to_parquet(a.outdir/'near_level_base.parquet',index=False);s.to_parquet(a.outdir/'precursor_signals.parquet',index=False);crowd.to_csv(a.outdir/'crowd_commitment_transfer.csv',index=False)
 ex=replay(a.raw_zip,audit_files(a.audit),s)
 if ex.empty:raise RuntimeError('no exact payoff rows')
 ex.to_parquet(a.outdir/'exact_payoffs.parquet',index=False);c=aggregate(ex,crowd);c.to_csv(a.outdir/'candidate_transfer.csv',index=False);yearly_locked(ex,c).to_csv(a.outdir/'locked_yearly.csv',index=False)
 locked=int(c.locked_before_2026.sum()) if len(c) else 0;pos=int((c.locked_before_2026&c.final_pass).sum()) if len(c) else 0;locked_states=int(c.loc[c.locked_before_2026,'state'].nunique()) if locked else 0
 positive_discovery=int(((c.train_n>=DISC_N)&(c.train_mean_R>0)).sum()) if len(c) else 0;positive_validation=int(((c.val_n>=VAL_N)&(c.val_mean_R>0)).sum()) if len(c) else 0
 fuel_states=int(((crowd.train_lift20>=1.05)&(crowd.val_lift20>=1.00)).sum()) if len(crowd) else 0;best=c.iloc[0].to_dict() if len(c) else None
 verdict='FAIL_NO_PRE2026_PRE_CROWD_EDGE' if locked==0 else ('PASS_PRE_CROWD_FUEL_OOS' if pos>0 else 'FAIL_OOS_TRANSFER')
 out={'lab':'XAU_PRE_CROWD_COMMITMENT_AND_LATE_ENTRY_FUEL_LAB_015','hypothesis':'causal pre-break precursor -> enter before obvious crowd commitment -> late entrants/stops provide same-direction fuel','no_future_leakage':'future crowd commitment is label/diagnostic only; signal and entry exist without knowing it','near_level_base_rows':int(len(base)),'precursor_signals':int(len(s)),'precursor_states':int(s.state.nunique()),'candidate_configs':int(len(c)),'fuel_states_pre2026':fuel_states,'positive_discovery_configs':positive_discovery,'positive_validation_configs':positive_validation,'locked_configs_pre2026':locked,'locked_states_pre2026':locked_states,'locked_positive_2026':pos,'best_config':best,'verdict':verdict}
 (a.outdir/'verdict.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,indent=2,default=str),flush=True)
if __name__=='__main__':main()
