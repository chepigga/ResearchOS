from pathlib import Path
import json
import numpy as np
import pandas as pd

OUT=Path('u08_out'); OUT.mkdir(exist_ok=True)
EV='lab020_events.csv'; EP='u05_out/u05_episode_market_clock_map.csv'
LOCKS=[24,48,72]

def core_label(e):
 e=e.copy(); e['branch']=''
 e.loc[(e.side=='BUY')&(e.H4_ST_AGE_BARS>58)&(e.H4_ST_DIR==-1),'branch']='BUY_TIER_A'
 e.loc[(e.side=='BUY')&(e.H4_ST_AGE_BARS>58)&(e.H4_ST_DIR==1),'branch']='BUY_TIER_B'
 e.loc[(e.side=='SELL')&(e.H4_ST_AGE_BARS>26)&(e.H4_ST_AGE_BARS<=50),'branch']='SELL_B3_RECENT'
 return e[e.branch!=''].copy()

def weeks_span(g):
 if len(g)<2:return np.nan
 return max((g.entry_time.max()-g.entry_time.min()).total_seconds()/604800,1e-9)

def accept_lock(g,hours,keycols):
 g=g.sort_values('entry_time'); last={}; keep=[]
 for i,r in g.iterrows():
  k=tuple(r[c] for c in keycols)
  ok=k not in last or r.entry_time-last[k]>=pd.Timedelta(hours=hours)
  if ok:last[k]=r.entry_time
  keep.append(ok)
 return g.loc[keep].copy()

def weekly(g,start,end):
 ix=pd.date_range(start.floor('D'),end.ceil('D'),freq='W-MON')
 if len(ix)<2:return {}
 w=g.set_index('entry_time').resample('W-MON').size().reindex(pd.date_range(g.entry_time.min().to_period('W').start_time,g.entry_time.max().to_period('W').start_time,freq='7D'),fill_value=0)
 return dict(weeks=len(w),mean=float(w.mean()),median=float(w.median()),p75=float(w.quantile(.75)),p90=float(w.quantile(.90)),zero_share=float((w==0).mean()),ge2_share=float((w>=2).mean()),ge4_share=float((w>=4).mean()),max=int(w.max()))

def phase_id(r):
 # Frozen H4_ST_AGE_BARS allows direct reconstruction of approximate phase start on 4h grid.
 bar=r.entry_time.floor('4h')
 return bar-pd.Timedelta(hours=4*int(r.H4_ST_AGE_BARS))

def main():
 e=pd.read_csv(EV); e['entry_time']=pd.to_datetime(e.entry_time); e['year']=e.entry_time.dt.year
 c=core_label(e); r=c[c.year>=2024].copy(); r['phase_start_est']=r.apply(phase_id,axis=1)
 start,end=r.entry_time.min(),r.entry_time.max(); span=(end-start).total_seconds()/604800
 rows=[]
 def add(label,g):
  rows.append(dict(label=label,N=len(g),freq_per_week=len(g)/span,**weekly(g,start,end)))
 add('RAW_ALL',r)
 for b,g in r.groupby('branch'):add('RAW_'+b,g)
 for h in LOCKS:
  x=accept_lock(r,h,['branch']); add(f'BRANCH_LOCK_{h}H_ALL',x)
  for b,g in x.groupby('branch'):add(f'BRANCH_LOCK_{h}H_{b}',g)
  x=accept_lock(r,h,['side']); add(f'SIDE_LOCK_{h}H_ALL',x)
  x=accept_lock(r,h,['portfolio_key']) if False else None
  # global one-position fixed holding window
  z=r.sort_values('entry_time'); last=None; keep=[]
  for i,q in z.iterrows():
   ok=last is None or q.entry_time-last>=pd.Timedelta(hours=h)
   if ok:last=q.entry_time
   keep.append(ok)
  add(f'GLOBAL_LOCK_{h}H_ALL',z.loc[keep])
 phase=r.sort_values('entry_time').drop_duplicates(['branch','phase_start_est'],keep='first'); add('ONE_PER_BRANCH_H4_PHASE_ALL',phase)
 for b,g in phase.groupby('branch'):add('ONE_PER_H4_PHASE_'+b,g)
 pd.DataFrame(rows).to_csv(OUT/'u08_frequency_scenarios.csv',index=False)
 r.to_csv(OUT/'u08_recent_core_events.csv',index=False)

 # Exact Oracle episodes: linked if target core event same direction occurs within +/-48h.
 ep=pd.read_csv(EP); ep['signal_time']=pd.to_datetime(ep.signal_time); ep['oracle_utc']=ep.signal_time-pd.Timedelta(hours=3)
 links=[]
 for q in ep.itertuples(index=False):
  target='BUY_TIER_A' if q.side=='BUY' else 'SELL_B3_RECENT'
  z=r[(r.branch==target)&((r.entry_time-q.oracle_utc).abs()<=pd.Timedelta(hours=48))]
  if len(z):
   z=z.assign(absd=(z.entry_time-q.oracle_utc).abs()).sort_values('absd'); a=z.iloc[0]
   links.append(dict(episode15=q.episode15,oracle_utc=q.oracle_utc,side=q.side,oracle_state=q.unified_state,target=target,linked=True,core_time=a.entry_time,delta_h=(a.entry_time-q.oracle_utc).total_seconds()/3600,core_net48=a.NET48_SPREAD_PCT))
  else:links.append(dict(episode15=q.episode15,oracle_utc=q.oracle_utc,side=q.side,oracle_state=q.unified_state,target=target,linked=False,core_time=pd.NaT,delta_h=np.nan,core_net48=np.nan))
 l=pd.DataFrame(links); l.to_csv(OUT/'u08_exact_oracle_lifecycle_links.csv',index=False)
 summary={
  'recent_span_weeks':span,
  'raw_core_N':len(r),'raw_core_freq_week':len(r)/span,
  'raw_by_branch':{b:{'N':len(g),'freq_week':len(g)/span} for b,g in r.groupby('branch')},
  'oracle_exact_episodes':len(l),'oracle_linked_within_48h':int(l.linked.sum()),'oracle_unlinked_candidates':int((~l.linked).sum()),
  'oracle_links':l.to_dict('records'),
  'note':'Oracle unlinked episodes are candidates only; U02 showed no standalone Oracle edge, so they are NOT added to approved tradable frequency.'
 }
 (OUT/'u08_summary.json').write_text(json.dumps(summary,indent=2,default=str))
 print('FREQUENCY SCENARIOS');print(pd.DataFrame(rows).to_string(index=False))
 print('\nORACLE LINKS');print(l.to_string(index=False))
 print('\nSUMMARY');print(json.dumps(summary,indent=2,default=str))
if __name__=='__main__':main()
