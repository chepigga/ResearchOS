#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
LAB='XAU_DOUBLE_NO_RETURN_CONFIRMED_STARTER_WINNER_MONETIZATION_LAB_027'; VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
EVENTS_SHA='7350b897f9ed9dbe8cef50975164596eeb6523b1e13c3151ec2621eed43e5674'
LAB025_SHA='18275ae3e4638b9d3714c96cc2f311b89df7daf500c44fbb3870c152f5b88619'
PARENT_SHA='09931377bb6258051e6de76b8bd3b56f92bf3cd06ea8ff2ec54751c72aea993a'
STARTER=.25; RISK_ATR=.50; COMM_PRICE=.05; HOLD=60; SEED=20260825; BOOT=4000

def sha(p):
 h=hashlib.sha256(); f=open(p,'rb')
 for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def mod(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def load_price(p):
 cols=['time','open','high','low','close','ask_open','ask_high','ask_low','ask_close']
 d=pd.read_csv(p,sep=';',usecols=cols); d.time=pd.to_datetime(d.time,format='%Y.%m.%d %H:%M'); return d

def sim(ev,df,after_target=2.0,trail=False,prefix='w'):
 t=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64); bo=df.open.values; bh=df.high.values; bl=df.low.values; bc=df.close.values; ao=df.ask_open.values; ah=df.ask_high.values; al=df.ask_low.values; ac=df.ask_close.values
 rows=[]; vio=0
 for r in ev.itertuples(index=False):
  if not bool(r.primary_promoted):
   rows.append((r.primary_gross_R,r.primary_net_R,r.primary_stress10_R,str(r.primary_outcome),pd.Timestamp(r.primary_exit_time),False,'FIRST_PROBATION_FAIL',np.nan)); continue
  ei=int(r.baseline_entry_i); d=int(r.dir); a=float(r.atr0); e=float(r.baseline_entry); risk=RISK_ATR*a; sl=e-d*risk; tp15=e+d*1.5*risk; tp_after=e+d*after_target*risk; end=t[ei]+HOLD
  pi=ei+5; alive=True; gross=None; outcome=''; xi=None; second_return=False; confirmed=False; confirm_i=ei+10
  limit=float(r.rr26_add_limit) if np.isfinite(r.rr26_add_limit) else np.nan
  for k in range(5):
   j=pi+k
   if j>=len(df) or t[j]!=t[pi]+k: vio+=1; alive=False; gross=0; outcome='CLOCK_FAIL'; xi=max(pi,j-1); break
   slh=(bl[j]<=sl) if d>0 else (ah[j]>=sl); tph=(bh[j]>=tp15) if d>0 else (al[j]<=tp15)
   if slh: gross=-STARTER; outcome='SECOND_SL'; xi=j; alive=False; break
   if tph: gross=STARTER*1.5; outcome='EARLY_TP15'; xi=j; alive=False; break
   touch=((al[j]<=limit) if d>0 else (bh[j]>=limit)) if np.isfinite(limit) else False
   if touch: second_return=True
  if alive and second_return:
   last=pi+4
   for j in range(pi+5,len(df)):
    if t[j]>end: break
    last=j; slh=(bl[j]<=sl) if d>0 else (ah[j]>=sl); tph=(bh[j]>=tp15) if d>0 else (al[j]<=tp15)
    if slh: gross=-STARTER; outcome='RETURN_SL'; xi=j; alive=False; break
    if tph: gross=STARTER*1.5; outcome='RETURN_TP15'; xi=j; alive=False; break
   if alive:
    px=bc[last] if d>0 else ac[last]; gross=STARTER*d*(px-e)/risk; outcome='RETURN_TIME'; xi=last; alive=False
  elif alive:
   confirmed=True
   last=pi+4
   for j in range(confirm_i,len(df)):
    if t[j]>end: break
    last=j; slh=(bl[j]<=sl) if d>0 else (ah[j]>=sl); cap=(bh[j]>=tp_after) if d>0 else (al[j]<=tp_after)
    if slh: gross=-STARTER; outcome='CONF_SL'; xi=j; alive=False; break
    if cap: gross=STARTER*after_target; outcome=f'CONF_TP{after_target:g}'; xi=j; alive=False; break
    if trail and j>=confirm_i+5:
     if d>0: boundary=np.min(bl[j-5:j]); sig=bc[j]<boundary
     else: boundary=np.max(ah[j-5:j]); sig=ac[j]>boundary
     if sig:
      nx=j+1
      if nx<len(df) and t[nx]==t[j]+1: px=bo[nx] if d>0 else ao[nx]; xi=nx
      else: px=bc[j] if d>0 else ac[j]; xi=j
      gross=STARTER*d*(px-e)/risk; outcome='CONF_TRAIL'; alive=False; break
   if alive:
    px=bc[last] if d>0 else ac[last]; gross=STARTER*d*(px-e)/risk; outcome='CONF_TIME'; xi=last; alive=False
  comm=STARTER*COMM_PRICE/risk; net=float(gross-comm); stress=float(net-STARTER*.10/risk)
  rows.append((float(gross),net,stress,outcome,df.at[int(xi),'time'],confirmed,'DOUBLE_NO_RETURN' if confirmed else ('SECOND_RETURN' if second_return else 'EARLY_RESOLVE'),float(limit) if np.isfinite(limit) else np.nan))
 cols=['gross_R','net_R','stress10_R','outcome','exit_time','confirmed','cohort','return_limit']; y=ev.copy()
 for i,c in enumerate(cols): y[f'{prefix}_{c}']=[x[i] for x in rows]
 y[f'{prefix}_promoted']=False; y[f'{prefix}_risk_budget_used']=STARTER
 return y,vio

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--events',type=Path,required=True);ap.add_argument('--lab025-runner',type=Path,required=True);ap.add_argument('--parent-runner',type=Path,required=True);ap.add_argument('--outdir',type=Path,required=True);a=ap.parse_args();o=a.outdir;o.mkdir(parents=True,exist_ok=True)
 for p,h in [(a.input,CANONICAL_SHA),(a.events,EVENTS_SHA),(a.lab025_runner,LAB025_SHA),(a.parent_runner,PARENT_SHA)]:
  if sha(p)!=h:raise RuntimeError(f'SHA mismatch {p}')
 l25=mod(a.lab025_runner,'l25'); parent=mod(a.parent_runner,'parent'); ev=pd.read_csv(a.events,compression='gzip',parse_dates=['break_time','baseline_entry_time','primary_exit_time','rr26_exit_time']); df=load_price(a.input)
 p2,v2=sim(ev,df,2.0,False,'w2'); p25,v25=sim(ev,df,2.5,False,'w25'); tr,vt=sim(ev,df,2.5,True,'trail')
 for c in [x for x in p25 if x.startswith('w25_')]:p2[c]=p25[c]
 for c in [x for x in tr if x.startswith('trail_')]:p2[c]=tr[c]
 conf=p2[p2.split=='CONFIRMATION'].copy();disc=p2[p2.split=='DISCOVERY'].copy()
 cs=l25.build_serial(conf,'w2',parent); ds=l25.build_serial(disc,'w2',parent); c25=l25.build_serial(conf,'w25',parent); ctr=l25.build_serial(conf,'trail',parent)
 cm=l25.stats(cs,'w2');dm=l25.stats(ds,'w2');m25=l25.stats(c25,'w25');mt=l25.stats(ctr,'trail')
 dq=l25.dedupe(conf,parent).copy(); dq['starter_control_net']=STARTER*dq.baseline_net_R_1p5
 confirmed=dq[dq.w2_confirmed.astype(bool)].copy(); nconf=len(confirmed); incr=float((confirmed.w2_net_R-confirmed.starter_control_net).mean()) if nconf else np.nan
 rows=[]
 for name,g in [('CONFIRMED_ALIVE',confirmed),('EARLY_TP15',dq[dq.w2_outcome=='EARLY_TP15']),('SECOND_RETURN',dq[dq.w2_cohort=='SECOND_RETURN']),('FIRST_PROBATION_FAIL',dq[dq.w2_cohort=='FIRST_PROBATION_FAIL'])]: rows.append({'cohort':name,'n':len(g),'w2_ev':g.w2_net_R.mean() if len(g) else np.nan,'starter_control_ev':g.starter_control_net.mean() if len(g) else np.nan,'baseline_full_ev':g.baseline_net_R_1p5.mean() if len(g) else np.nan})
 pd.DataFrame(rows).to_csv(o/'cohort_diagnostics.csv',index=False)
 cs2=cs.copy();cs2['week']=pd.to_datetime(cs2.baseline_entry_time).dt.to_period('W-MON').astype(str); ww=cs2.groupby('week').w2_net_R.mean().values; rng=np.random.default_rng(SEED);bb=np.array([rng.choice(ww,len(ww),replace=True).mean() for _ in range(BOOT)]); wci=[float(np.quantile(bb,.025)),float(np.quantile(bb,.975))]
 confirmed['diff']=confirmed.w2_net_R-confirmed.starter_control_net; confirmed['week']=confirmed.baseline_entry_time.dt.to_period('W-MON').astype(str); cw=confirmed.groupby('week')['diff'].mean().values
 if len(cw)>=8: bb=np.array([rng.choice(cw,len(cw),replace=True).mean() for _ in range(BOOT)]); cci=[float(np.quantile(bb,.025)),float(np.quantile(bb,.975))]
 else: cci=[None,None]
 bcs=parent.build_serial(conf,'BASELINE',1.5); bm=parent.stats(bcs,'BASELINE',1.5)
 gates={'G0_CAUSALITY':v2+v25+vt==0,'G1_CONFIRMED_POWER':nconf>=30,'G2_POSITIVE_ECONOMICS':cm['ev']>0,'G3_CONFIRMED_INCREMENTAL':bool(np.isfinite(incr) and incr>0),'G4_WEEKLY_ROBUSTNESS':wci[0]>0,'G5_TRANSFER':dm['ev']>0 and cm['ev']>0,'G6_DIRECTION_BREADTH':cm['buy_ev']>=0 and cm['sell_ev']>=0,'G7_STRESS':cm['stress10_ev']>0,'G8_PROP_DD':cm['worst_day_R']>-4 and cm['max_dd_R']<bm['max_dd_R'],'G9_TP25_SURVIVAL':m25['ev']>=0}
 status='DOUBLE_NO_RETURN_WINNER_MONETIZATION_EDGE' if all(gates.values()) else ('DOUBLE_NO_RETURN_CONFIRMED_BUT_MONETIZATION_NOT_POSITIVE' if gates['G1_CONFIRMED_POWER'] else 'INSUFFICIENT_CONFIRMED_ALIVE')
 verdict={'status':status,'gates':gates,'primary_confirmation':cm,'discovery':dm,'tp25':m25,'trail':mt,'confirmed_alive_n':nconf,'confirmed_incremental_vs_starter_control':incr,'confirmed_incremental_week_ci':cci,'weekly_ev_ci':wci,'full_immediate':bm,'violations':v2+v25+vt,'holdout_opened':False}
 pd.DataFrame([{'strategy':'TP2_PRIMARY',**cm},{'strategy':'TP2.5_SECONDARY',**m25},{'strategy':'TRAIL_SECONDARY',**mt},{'strategy':'FULL_IMMEDIATE',**bm}]).to_csv(o/'summary.csv',index=False); p2.to_csv(o/'events.csv.gz',index=False,compression='gzip')
 rep=f'''# {LAB} — {VERSION} REPORT\n\n**Verdict:** `{status}`  \n**Holdout opened:** `false`\n\n## Primary Confirmation — starter only, TP2 after double-no-return confirmation\n- N **{cm['n']}**, EV **{cm['ev']:+.4f}R**, PF **{cm['pf']:.3f}**, trades/week **{cm['trades_per_week']:.2f}**\n- BUY **{cm['buy_ev']:+.4f}R**, SELL **{cm['sell_ev']:+.4f}R**, stress10 **{cm['stress10_ev']:+.4f}R**\n- MaxDD **{cm['max_dd_R']:.2f}R**, worst day **{cm['worst_day_R']:.2f}R**\n- weekly EV CI **{wci}**\n\n## Double-no-return confirmed alive\n- N **{nconf}**\n- incremental TP2-vs-keep-TP1.5 starter **{incr:+.4f}R**, week CI **{cci}**\n\n## Secondary\n- TP2.5 EV **{m25['ev']:+.4f}R**, PF **{m25['pf']:.3f}**\n- structural trail proxy EV **{mt['ev']:+.4f}R**, PF **{mt['pf']:.3f}**\n\n## Controls / transfer\n- Discovery TP2 EV **{dm['ev']:+.4f}R**\n- Full immediate baseline EV **{bm['ev']:+.4f}R**, MaxDD **{bm['max_dd_R']:.2f}R**\n\n## Frozen gates\n'''+ '\n'.join(f'- {k}: **{"PASS" if v else "FAIL"}**' for k,v in gates.items())+'\n\nNo sensitivity rescue, no holdout opening, no EA/live authorization.\n'
 (o/'REPORT.md').write_text(rep);(o/'verdict.json').write_text(json.dumps(verdict,indent=2,default=str));(o/'audit.json').write_text(json.dumps({'canonical_sha':sha(a.input),'events_sha':sha(a.events),'lab025_sha':sha(a.lab025_runner),'parent_sha':sha(a.parent_runner),'confirmation_events':len(conf),'confirmed_alive':nconf,'violations':v2+v25+vt,'holdout_opened':False},indent=2)); print(json.dumps(verdict,indent=2,default=str))
if __name__=='__main__':main()
