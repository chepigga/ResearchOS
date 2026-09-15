#!/usr/bin/env python3
from pathlib import Path
import json, math
import numpy as np, pandas as pd
ROOT=Path('research/gc'); RITH=ROOT/'RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CONFIRMED_EVENTS.csv'; XAU=Path('XAUUSD_M1_2026.csv')
OUT=ROOT/'RITHMIC_XAU_LAB022_BASELINE_PARITY_001.json'; MD=ROOT/'RITHMIC_XAU_LAB022_BASELINE_PARITY_001.md'
TARGET={'n':51,'ev':.250,'sum':12.75,'wr':54.9,'dd':3.24,'buy_ev':.325,'sell_ev':.188}

def met(r):
 r=np.asarray(r,float); eq=np.cumsum(r); pk=np.maximum.accumulate(np.r_[0.,eq])[1:]
 return {'n':len(r),'ev':float(r.mean()),'sum':float(r.sum()),'wr':float((r>0).mean()*100),'dd':float(np.max(pk-eq))}
def main():
 x=pd.read_csv(XAU,sep=';'); x['t']=pd.to_datetime(x.time,format='%Y.%m.%d %H:%M');
 for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c],errors='coerce')
 x=x.sort_values('t').reset_index(drop=True); m=x.set_index('t').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna(); pc=m.close.shift(1); m['tr']=pd.concat([(m.high-m.low),(m.high-pc).abs(),(m.low-pc).abs()],axis=1).max(axis=1); m.iloc[0,m.columns.get_loc('tr')]=np.nan; m['w']=m.tr.ewm(alpha=1/20,adjust=False,min_periods=20).mean(); m['s']=m.tr.rolling(20,min_periods=20).mean()
 e=pd.read_csv(RITH); e['t']=pd.to_datetime(e.entry_eligible_utc,utc=True).dt.tz_convert(None)+pd.Timedelta(hours=2); avail=set(x.t); e=e[e.t.isin(avail)].sort_values('t'); assert len(e)==51
 ti={t:i for i,t in enumerate(x.t)}; candidates=[]
 for atrkind in ['w','s']:
  for anchor in ['prev','entry']:
   for entkind in ['open','prev_close']:
    rr=[]; sides=[]
    for ev in e.itertuples(index=False):
     i=ti[ev.t]; key=ev.t.floor('5min')-(pd.Timedelta(minutes=5) if anchor=='prev' else pd.Timedelta(0)); atr=float(m.at[key,atrkind]); ent=float(x.iloc[i].open if entkind=='open' else x.iloc[i-1].close); sl=ent-atr if ev.side=='LONG' else ent+atr; tp=ent+1.5*atr if ev.side=='LONG' else ent-1.5*atr; horizon=ev.t+pd.Timedelta(minutes=30); sub=x[(x.t>=ev.t)&(x.t<=horizon)]; out=None
     for z in sub.itertuples(index=False):
      sh=(z.low<=sl) if ev.side=='LONG' else (z.high>=sl); th=(z.high>=tp) if ev.side=='LONG' else (z.low<=tp)
      if sh: out=-1.; break
      if th: out=1.5; break
     if out is None:
      z=sub.iloc[-1]; out=(float(z.close)-ent)/atr if ev.side=='LONG' else (ent-float(z.close))/atr
     rr.append(out); sides.append(ev.side)
    a=met(rr); buy=met([r for r,s in zip(rr,sides) if s=='LONG']); sell=met([r for r,s in zip(rr,sides) if s=='SHORT']); sc=abs(a['ev']-.25)+abs(a['wr']-54.9)/20+abs(buy['ev']-.325)+abs(sell['ev']-.188)
    candidates.append({'atr':atrkind,'anchor':anchor,'entry':entkind,**a,'buy_ev':buy['ev'],'sell_ev':sell['ev'],'score':sc})
 candidates=sorted(candidates,key=lambda q:q['score']); res={'lab':'RITHMIC_XAU_LAB022_BASELINE_PARITY_001','amp_data_used':False,'target':TARGET,'candidates':candidates,'best':candidates[0]}; OUT.write_text(json.dumps(res,indent=2)); b=candidates[0]; MD.write_text(f"# RITHMIC_XAU_LAB022_BASELINE_PARITY_001\n\nBest of implementation-equivalent ATR/entry conventions on current release XAU file:\n\n- EV **{b['ev']:+.3f}R** vs historical **+0.250R**\n- Sum **{b['sum']:+.3f}R** vs **+12.75R**\n- WR **{b['wr']:.1f}%** vs **54.9%**\n- DD **{b['dd']:.2f}R** vs **3.24R**\n- BUY EV **{b['buy_ev']:+.3f}R** vs **+0.325R**\n- SELL EV **{b['sell_ev']:+.3f}R** vs **+0.188R**\n\nAMP data used: **NO**.\n")
 print(MD.read_text()); print(json.dumps(res,indent=2))
if __name__=='__main__': main()
