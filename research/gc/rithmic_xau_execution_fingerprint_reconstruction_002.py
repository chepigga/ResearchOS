#!/usr/bin/env python3
"""RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002
Historical Rithmic/XAU execution parity only. AMP data is never read.
"""
from __future__ import annotations
import itertools,json,math
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path('research/gc'); RITH=ROOT/'RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CONFIRMED_EVENTS.csv'; XAU=Path('XAUUSD_M1_2026.csv')
OUT=ROOT/'RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002.json'; OUTMD=ROOT/'RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002.md'; OUTCSV=ROOT/'RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002_CANDIDATES.csv'
TA={'n':51,'ev':.563,'sum':28.69,'pf':2.15,'dd':3.42}; TS={'n':46,'ev':.666,'sum':30.63,'pf':2.33,'dd':3.32}

def stats(tr):
 r=np.array([z['r'] for z in tr],float)
 if not len(r): return dict(n=0,ev=None,sum=0,pf=0,dd=0,streak=0)
 eq=np.cumsum(r); pk=np.maximum.accumulate(np.r_[0.,eq])[1:]; gp=r[r>0].sum(); gl=-r[r<0].sum(); cur=best=0
 for v in r:
  if v<0: cur+=1; best=max(best,cur)
  else: cur=0
 return dict(n=len(r),ev=float(r.mean()),sum=float(r.sum()),pf=float(gp/gl if gl else np.inf),dd=float(np.max(pk-eq)),streak=best)

def score(a,s):
 return 2*abs(a['n']-51)+4*abs(s['n']-46)+8*abs(a['ev']-.563)+.25*abs(a['sum']-28.69)+2*abs(a['pf']-2.15)+.8*abs(a['dd']-3.42)+10*abs(s['ev']-.666)+.25*abs(s['sum']-30.63)+2*abs(s['pf']-2.33)+.8*abs(s['dd']-3.32)

def load():
 x=pd.read_csv(XAU,sep=';'); x['t']=pd.to_datetime(x.time,format='%Y.%m.%d %H:%M')
 for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c],errors='coerce')
 x=x.sort_values('t').reset_index(drop=True)
 m=x.set_index('t').resample('5min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna(); pc=m.close.shift(1)
 m['tr']=pd.concat([(m.high-m.low),(m.high-pc).abs(),(m.low-pc).abs()],axis=1).max(axis=1); m.iloc[0,m.columns.get_loc('tr')]=np.nan
 m['atr_wilder']=m.tr.ewm(alpha=1/20,adjust=False,min_periods=20).mean(); m['atr_sma']=m.tr.rolling(20,min_periods=20).mean()
 e=pd.read_csv(RITH); e['entry_utc']=pd.to_datetime(e.entry_eligible_utc,utc=True); e['t']=e.entry_utc.dt.tz_convert(None)+pd.Timedelta(hours=2); avail=set(x.t)
 e=e[e.t.isin(avail)].sort_values('t').reset_index(drop=True); assert len(e)==51,len(e)
 return x,m,e

def main():
 x,m,e=load(); tt=x.t.to_numpy(dtype='datetime64[ns]'); tn=tt.astype('int64'); op=x.open.to_numpy(float); hi=x.high.to_numpy(float); lo=x.low.to_numpy(float); cl=x.close.to_numpy(float)
 idx={pd.Timestamp(t):i for i,t in enumerate(tt)}
 gaps=np.r_[np.nan,(tn[1:]-tn[:-1])/60e9]
 def trade(ev,cfg):
  t=pd.Timestamp(ev.t); i=idx[t]; key=t.floor('5min')-(pd.Timedelta(minutes=5) if cfg['atr_anchor']=='prev' else pd.Timedelta(0)); col='atr_wilder' if cfg['atr_kind']=='wilder' else 'atr_sma'
  if key not in m.index or pd.isna(m.at[key,col]): return None
  atr=float(m.at[key,col]); entry=float(op[i] if cfg['entry_kind']=='open' else cl[i-1]); side=ev.side; sl=entry-atr if side=='LONG' else entry+atr; tp=entry+3*atr if side=='LONG' else entry-3*atr
  hend=(t+pd.Timedelta(minutes=240)).value; end=int(np.searchsorted(tn,hend,side='right')-1); start=i if cfg['include_entry_bar'] else i+1; xt=None; xp=None
  for j in range(start,min(end+1,len(x))):
   if j>i and cfg['session_gap_min'] is not None and gaps[j]>=cfg['session_gap_min']: xt=pd.Timestamp(tt[j-1]); xp=float(cl[j-1]); break
   sh=(lo[j]<=sl) if side=='LONG' else (hi[j]>=sl); th=(hi[j]>=tp) if side=='LONG' else (lo[j]<=tp)
   if sh: xt=pd.Timestamp(tt[j]); xp=sl; break
   if th: xt=pd.Timestamp(tt[j]); xp=tp; break
  if xt is None: k=end if cfg['time_exit']=='last_leq' else (idx.get(t+pd.Timedelta(minutes=240),end)); xt=pd.Timestamp(tt[k]); xp=float(cl[k])
  r=(xp-entry)/atr if side=='LONG' else (entry-xp)/atr
  return dict(entry_t=t,exit_t=xt,side=side,r=float(r))
 def single(tr,b):
  out=[]; busy=None
  for z in tr:
   if busy is not None and ((z['entry_t']<busy) if b=='strict' else (z['entry_t']<=busy)): continue
   out.append(z); busy=z['exit_t']
  return out
 axes={'atr_kind':['wilder','sma'],'atr_anchor':['prev','entry'],'entry_kind':['open','prev_close'],'session_gap_min':[None,15,30,60,90],'time_exit':['last_leq','exact_or_prev'],'include_entry_bar':[True,False],'single_boundary':['strict','inclusive']}; keys=list(axes); rows=[]
 for vals in itertools.product(*(axes[k] for k in keys)):
  cfg=dict(zip(keys,vals)); tr=[trade(ev,cfg) for ev in e.itertuples(index=False)]; tr=[z for z in tr if z]; a=stats(tr); s=stats(single(tr,cfg['single_boundary'])); rec={**cfg,'all_n':a['n'],'all_ev':a['ev'],'all_sum':a['sum'],'all_pf':a['pf'],'all_dd':a['dd'],'sp_n':s['n'],'sp_ev':s['ev'],'sp_sum':s['sum'],'sp_pf':s['pf'],'sp_dd':s['dd'],'sp_streak':s['streak']}; rec['score']=score(a,s); rows.append(rec)
 df=pd.DataFrame(rows).sort_values(['score','sp_n']).reset_index(drop=True); df.to_csv(OUTCSV,index=False); top=df.head(20).to_dict('records'); best=top[0]; res={'lab':'RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002','amp_data_used':False,'candidate_count':len(df),'targets':{'all':TA,'single_position':TS},'best':best,'top20':top,'exact_count_candidates':int(((df.all_n==51)&(df.sp_n==46)).sum())}; OUT.write_text(json.dumps(res,indent=2,default=str))
 md=['# RITHMIC_XAU_EXECUTION_FINGERPRINT_RECONSTRUCTION_002','','**AMP data used: NO. Historical Rithmic/XAU parity only.**','',f"Candidates: **{len(df)}**; exact 51→46 count candidates: **{res['exact_count_candidates']}**.",'','## Best candidate','']+[f"- {k}: `{best[k]}`" for k in keys]+['',f"All 51: EV **{best['all_ev']:+.4f}R**, Sum **{best['all_sum']:+.3f}R**, PF **{best['all_pf']:.3f}**, DD **{best['all_dd']:.3f}R**",f"Single: N **{best['sp_n']}**, EV **{best['sp_ev']:+.4f}R**, Sum **{best['sp_sum']:+.3f}R**, PF **{best['sp_pf']:.3f}**, DD **{best['sp_dd']:.3f}R**",'', 'Targets: all 51 +0.563R/+28.69R/PF2.15/DD3.42; single 46 +0.666R/+30.63R/PF2.33/DD3.32.']; OUTMD.write_text('\n'.join(md)+'\n'); print(OUTMD.read_text()); print(json.dumps(res,indent=2,default=str))
if __name__=='__main__': main()
