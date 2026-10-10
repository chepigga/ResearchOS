from pathlib import Path
import json
import pandas as pd,numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/LAB163_20261010';O.mkdir(exist_ok=True)
TFS={'D1':('1D',288),'H4':('4h',48),'H1':('1h',12),'M15':('15min',3),'M5':('5min',1)}
def structure(b):
 h=b.high.to_numpy();l=b.low.to_numpy();c=b.close.to_numpy();out=np.full((len(b),4),np.nan);highs=[];lows=[]
 for i in range(len(b)):
  p=i-2
  if p>=2:
   hh=h[p-2:p+3];ll=l[p-2:p+3]
   if np.isfinite(hh).all() and h[p]>np.max(np.r_[hh[:2],hh[3:]]):highs.append(h[p])
   if np.isfinite(ll).all() and l[p]<np.min(np.r_[ll[:2],ll[3:]]):lows.append(l[p])
  if len(highs)>=2 and len(lows)>=2 and np.isfinite(c[i]):
   trend=1 if highs[-1]>highs[-2] and lows[-1]>lows[-2] else (-1 if highs[-1]<highs[-2] and lows[-1]<lows[-2] else 0)
   phase=int(np.sign((c[i]-c[i-3])*trend)) if i>=3 and np.isfinite(c[i-3]) and trend else 0
   out[i]=[trend,phase,highs[-1],lows[-1]]
 return pd.DataFrame(out,index=b.index,columns=['trend','phase','last_high','last_low'])
def context(d):
 frames=[];audit={}
 for name,(freq,n) in TFS.items():
  b=d.resample(freq,closed='right',label='right',origin='start_day').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'});cnt=d.close.resample(freq,closed='right',label='right',origin='start_day').count();b.loc[cnt!=n,:]=np.nan;s=structure(b);cut=max(20,len(b)//2);assert np.allclose(structure(b.iloc[:cut]),s.iloc[:cut],equal_nan=True);frames.append(s.add_prefix(name+'_').reindex(d.index,method='ffill'));audit[name]=dict(bars=len(b),valid=int(s.trend.notna().sum()),first_valid=str(s.trend.first_valid_index()))
 return pd.concat(frames,axis=1),audit

def label_context(q,cx,times,sides):
 q=q.copy();v=cx.reindex(pd.DatetimeIndex(times)).reset_index(drop=True);sides=np.asarray(sides)
 for name in TFS:
  tr=v[name+'_trend'].to_numpy();q[name]=np.select([~np.isfinite(tr),tr==sides,tr==-sides],['UNKNOWN','WITH','AGAINST'],default='BALANCE');q[name+'_phase']=v[name+'_phase'].map({1:'IMPULSE',-1:'PULLBACK',0:'FLAT'}).fillna('UNKNOWN').to_numpy()
 q['higher_context']=np.select([(q.D1=='WITH')&(q.H4=='WITH'),(q.D1=='AGAINST')&(q.H4=='AGAINST'),(q.D1=='UNKNOWN')|(q.H4=='UNKNOWN')],['HIGHER_WITH','HIGHER_AGAINST','UNKNOWN'],default='MIXED_BALANCE')
 q['setup_context']=q.higher_context+'|H1_'+q.H1+'|M15_'+q.M15
 return q

def scenario(d,mode):
 c=d.close.to_numpy();h=d.high.to_numpy();l=d.low.to_numpy();a=d.atr.to_numpy();ti=d.index;profile=d[['POC_HVN','VAL','VAH','shape']];pending=None;last=-99999;rows=[];dayloc=np.searchsorted(ti.asi8,ti.normalize().asi8,side='right')-1
 for i in range(1,len(d)-288):
  if pending is None:
   if i-last<72 or not d.eligible_features.iloc[i-1] or not np.isfinite(a[i-1]):continue
   j=i-1 if mode=='ROLL24' else int(dayloc[i-1]);p=profile.iloc[j]
   if not np.isfinite(p.VAL+p.VAH+p.POC_HVN) or not(p.VAL<=c[i-1]<=p.VAH):continue
   side=1 if c[i]>p.VAH+.1*a[i-1] else (-1 if c[i]<p.VAL-.1*a[i-1] else 0)
   if not side:continue
   pending=dict(start=i,side=side,boundary=p.VAH if side==1 else p.VAL,poc=p.POC_HVN,atr=a[i-1],shape=p['shape'],snapshot=j,ext=h[i] if side==1 else l[i],reentry=-1);continue
  p=pending;sd=p['side'];p['ext']=max(p['ext'],h[i]) if sd==1 else min(p['ext'],l[i]);delta=sd*(c[i]-p['boundary'])/p['atr']
  if p['reentry']<0:
   if i-p['start']>72:pending=None;continue
   if delta<=-.1:p['reentry']=i
   continue
  if i-p['reentry']>36:pending=None;continue
  touch=h[i]>=p['boundary']-.1*p['atr'] if sd==1 else l[i]<=p['boundary']+.1*p['atr']
  if not touch or delta>-.1:continue
  direction=-sd;target=direction*(p['poc']-c[i]);stopprice=p['ext']+sd*.1*p['atr'];risk=direction*(c[i]-stopprice)
  pending=None
  if target<.5*a[i] or risk<=.1*a[i]:continue
  last=i;future=c[i+1:i+289];targ=np.flatnonzero(direction*(future-p['poc'])>=0);stop=np.flatnonzero(direction*(future-stopprice)<=0);jt=targ[0] if len(targ) else 999;jstop=stop[0] if len(stop) else 999;outcome='TARGET' if jt<jstop else ('STOP' if jstop<jt else 'TIMEOUT')
  rows.append(dict(mode=mode,time=ti[i],break_time=ti[p['start']],reentry_time=ti[p['reentry']],snapshot_time=ti[p['snapshot']],side=direction,shape=p['shape'],boundary=p['boundary'],poc=p['poc'],close=c[i],stop=stopprice,route_atr=target/a[i],risk_atr=risk/a[i],reward_risk=target/risk,outcome=outcome,oi4h=d.oi_change_48.iloc[i],z=d.crowd_z.iloc[i]))
 return pd.DataFrame(rows)

def main():
 d=pd.read_pickle(R/'results/LAB162_20261010/LAB162_tape.pkl');cx,audit=context(d);cx.to_pickle(O/'LAB163_context.pkl');cx.to_csv(O/'LAB163_context.csv.gz',compression='gzip');(O/'LAB163_context_audit.json').write_text(json.dumps(audit,indent=2))
 e=pd.read_csv(R/'results/LAB162_20261010/LAB162_encounters.csv',parse_dates=['time']);e=label_context(e,cx,e.time,e.side);e.to_csv(O/'LAB163_encounters.csv',index=False)
 s=pd.concat([scenario(d,mode) for mode in ['ROLL24','PRIOR_DAY']],ignore_index=True);s=label_context(s,cx,s.time,s.side);s['split']=np.select([s.time<pd.Timestamp('2024-01-01',tz='UTC'),s.time<pd.Timestamp('2025-01-01',tz='UTC')],['DISCOVERY','VALIDATION'],default='CHECK')
 for boundary in ['2024-01-01','2025-01-01']:
  t=pd.Timestamp(boundary,tz='UTC');s.loc[(s.time>=t-pd.Timedelta(hours=24))&(s.time<t),'split']='PURGED'
 s['week']=s.time.dt.strftime('%G-%V');s.to_csv(O/'LAB163_scenarios.csv',index=False);rows=[]
 for keys in [['mode'],['mode','higher_context'],['mode','shape'],['mode','setup_context']]:
  for key,q in s[s.split!='PURGED'].groupby(['split']+keys):
   record=dict(zip(['split']+keys,key));record.update(grouping='+'.join(keys),n=len(q),target_pct=100*(q.outcome=='TARGET').mean(),stop_pct=100*(q.outcome=='STOP').mean(),timeout_pct=100*(q.outcome=='TIMEOUT').mean(),route_atr_median=q.route_atr.median(),risk_atr_median=q.risk_atr.median(),rr_median=q.reward_risk.median());rows.append(record)
 pd.DataFrame(rows).to_csv(O/'LAB163_scenario_summary.csv',index=False);print('CONTEXT',audit,flush=True);print('ENCOUNTERS',len(e),'SCENARIOS',len(s),flush=True)
if __name__=='__main__':main()
