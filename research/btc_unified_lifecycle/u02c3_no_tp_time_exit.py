#!/usr/bin/env python3
from pathlib import Path
import numpy as np, pandas as pd
import u02c2_v283_market_clock_conditional as m

OUT=Path('u02c3_out'); OUT.mkdir(exist_ok=True)
H=[24,48,72]
COST=27.5

def pf(s):
 s=pd.Series(s).dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum(); return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def build_events():
 sh=pd.read_csv(m.SHADOW); sh['time']=pd.to_datetime(sh.time)
 sh=sh[(sh.time>=m.START)&(sh.action!='WAIT')&(sh.pass_stateless==1)].copy()
 m5=m.load_zip(m.M5ZIP); h4=m.h4_supertrend(m5)
 sh=m.attach_clock(sh,h4).dropna(subset=['st_age','st_dir']).copy(); sh['market_state']=sh.apply(m.state_label,axis=1)
 ep=m.episode_first(sh); ep['market_state']=ep.apply(m.state_label,axis=1)
 return ep

def replay(ep):
 m1=m.load_zip(m.M1ZIP); h1=m.h1_atr_from_m1(m1)
 mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); Hh=m1.high.to_numpy(float); Ll=m1.low.to_numpy(float); C=m1.close.to_numpy(float)
 hct=h1.close_time.to_numpy('datetime64[ns]'); ha=h1.atr14.to_numpy(float)
 rows=[]
 for r in ep.itertuples(index=False):
  sig=pd.Timestamp(r.time); et=sig+pd.Timedelta(minutes=1); j=int(np.searchsorted(mt,np.datetime64(et),'left'))
  q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1)
  if j>=len(O) or q<0 or not np.isfinite(ha[q]): continue
  entry=float(O[j]); sd=1.5*float(ha[q]); d=1.0 if r.action=='BUY' else -1.0; sl=entry-d*sd
  costR=COST/sd; costPct=COST/entry*100.0
  z=r._asdict(); z.update(entry_time=et,entry=entry,stop_dist=sd,cost_R=costR,cost_pct=costPct)
  for hh in H:
   tend=sig+pd.Timedelta(hours=hh); je=int(np.searchsorted(mt,np.datetime64(tend),'left'))
   if je<=j or je>=len(O): z[f'notp{hh}_R']=np.nan; z[f'notp{hh}_pct']=np.nan; z[f'exit{hh}']='NA'; continue
   hi=Hh[j:je]; lo=Ll[j:je]
   stop=np.flatnonzero(lo<=sl) if d>0 else np.flatnonzero(hi>=sl)
   if stop.size:
    rr=-1.0-costR; pp=-(sd/entry*100.0)-costPct; ex='SL'
   else:
    endp=float(O[je]); rr=d*(endp-entry)/sd-costR; pp=d*(endp-entry)/entry*100.0-costPct; ex='TIME'
   z[f'notp{hh}_R']=rr; z[f'notp{hh}_pct']=pp; z[f'exit{hh}']=ex
  rows.append(z)
 return pd.DataFrame(rows)

def metrics(x):
 rows=[]
 for (side,state),g in x.groupby(['action','market_state']):
  r={'side':side,'state':state,'N':len(g)}
  for hh in H:
   a=g[f'notp{hh}_R'].dropna(); p=g[f'notp{hh}_pct'].dropna(); r[f'EV{hh}_R']=a.mean(); r[f'PF{hh}_R']=pf(a); r[f'WR{hh}']=(a>0).mean(); r[f'EV{hh}_pct']=p.mean(); r[f'PF{hh}_pct']=pf(p); r[f'SL{hh}_rate']=(g[f'exit{hh}']=='SL').mean()
  rows.append(r)
 return pd.DataFrame(rows)

def yearly(x):
 x=x.copy(); x['yr']=x.time.dt.year; rows=[]
 for (y,s,st),g in x.groupby(['yr','action','market_state']):
  rows.append({'year':int(y),'side':s,'state':st,'N':len(g),'EV24_R':g.notp24_R.mean(),'EV24_pct':g.notp24_pct.mean(),'PF24':pf(g.notp24_R),'EV48_R':g.notp48_R.mean(),'EV48_pct':g.notp48_pct.mean(),'PF48':pf(g.notp48_R),'EV72_R':g.notp72_R.mean(),'EV72_pct':g.notp72_pct.mean(),'PF72':pf(g.notp72_R)})
 return pd.DataFrame(rows)

def main():
 ep=build_events(); x=replay(ep); x.to_csv(OUT/'events_no_tp.csv',index=False)
 sm=metrics(x); sm.to_csv(OUT/'state_matrix_no_tp.csv',index=False)
 yr=yearly(x); yr.to_csv(OUT/'yearly_no_tp.csv',index=False)
 focus=sm[sm.state.isin(['TIER_A','TIER_B','SELL_B3','OTHER_B1','OTHER_B2','OTHER_B3','OTHER_B4','TRANSITION'])]
 print('NO-TP STOP-OR-TIME MATRIX'); print(focus.to_string(index=False)); print('\nYEARLY'); print(yr.to_string(index=False))
 rep=['# U02C3 — v283 market-clock matrix, NO TP / stop-or-time','', 'Same episode-first v283 shadow and canonical H4 clock as U02C2. Exit is SL=1.5×H1 ATR or time exit; no profit target. Cost proxy $27.5/BTC.','',sm.to_markdown(index=False),'','## Yearly','',yr.to_markdown(index=False)]
 (OUT/'REPORT.md').write_text('\n'.join(rep))
if __name__=='__main__': main()
