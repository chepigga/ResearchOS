from pathlib import Path
import json
import numpy as np
import pandas as pd

OUT=Path('u03_out'); OUT.mkdir(exist_ok=True)
U02=Path('u02_out/u02_exact_signal_outcomes.csv')
H=[15,30,60,120,240,480]

def pf(v):
 s=pd.Series(v).dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum(); return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def metrics(g):
 d={'N':len(g)}
 for hm in H:
  v=g[f'ret_{hm}m']; d[f'EV_{hm}m']=float(v.mean()) if len(g) else np.nan; d[f'WR_{hm}m']=float((v>0).mean()) if len(g) else np.nan; d[f'PF_{hm}m']=pf(v)
  d[f'MFE_MED_{hm}m']=float(g[f'mfe_{hm}m'].median()) if len(g) else np.nan; d[f'MAE_MED_{hm}m']=float(g[f'mae_{hm}m'].median()) if len(g) else np.nan
 return d

def main():
 x=pd.read_csv(U02,parse_dates=['signal_time','utc_time','entry_time_utc'])
 rows=[]
 groups={
  'BUY_LATE_BLOCKED':x[(x.side=='BUY')&(x.disposition=='LATE')],
  'BUY_NOT_LATE':x[(x.side=='BUY')&(x.disposition!='LATE')],
  'SELL_ORACLE_BLOCKED':x[(x.side=='SELL')&(x.disposition=='ORACLE')],
  'SELL_NOT_ORACLE':x[(x.side=='SELL')&(x.disposition!='ORACLE')],
  'SELL_KNIFE_BLOCKED':x[(x.side=='SELL')&(x.disposition=='KNIFE')],
  'EXACT_EXEC':x[x.disposition=='EXEC'],
 }
 for label,g in groups.items(): rows.append({'label':label,**metrics(g)})
 pd.DataFrame(rows).to_csv(OUT/'u03_gate_group_metrics.csv',index=False)

 # Episode-level counterfactuals: first signal vs actual execution poll where present.
 ep=[]
 for eid,g in x.sort_values('signal_time').groupby('episode15'):
  first=g.iloc[0]; ex=g[g.disposition=='EXEC']
  er={'episode15':int(eid),'side':first.side,'first_time':first.signal_time,'first_disposition':first.disposition,'first_conf':first.conf,'first_dist':first.dist,'first_pre':first.pre}
  for hm in H: er[f'first_ret_{hm}m']=first[f'ret_{hm}m']; er[f'first_mfe_{hm}m']=first[f'mfe_{hm}m']; er[f'first_mae_{hm}m']=first[f'mae_{hm}m']
  if len(ex):
   q=ex.iloc[0]; er['exec_time']=q.signal_time; er['delay_min']=(q.signal_time-first.signal_time).total_seconds()/60.0; er['exec_dist']=q.dist; er['exec_pre']=q.pre
   for hm in H: er[f'exec_ret_{hm}m']=q[f'ret_{hm}m']; er[f'delta_exec_minus_first_{hm}m']=q[f'ret_{hm}m']-first[f'ret_{hm}m']
  else:
   er['exec_time']=pd.NaT; er['delay_min']=np.nan; er['exec_dist']=np.nan; er['exec_pre']=np.nan
   for hm in H: er[f'exec_ret_{hm}m']=np.nan; er[f'delta_exec_minus_first_{hm}m']=np.nan
  ep.append(er)
 ep=pd.DataFrame(ep); ep.to_csv(OUT/'u03_episode_gate_counterfactuals.csv',index=False)

 # Explicit conclusions encoded from non-optimized exact groups.
 late=groups['BUY_LATE_BLOCKED']; oracle=groups['SELL_ORACLE_BLOCKED']; knife=groups['SELL_KNIFE_BLOCKED']
 summary={
  'buy_late_poll_N':len(late),
  'buy_late_EV_1h':float(late.ret_60m.mean()),'buy_late_EV_2h':float(late.ret_120m.mean()),'buy_late_EV_4h':float(late.ret_240m.mean()),'buy_late_WR_2h':float((late.ret_120m>0).mean()),
  'sell_oracle_poll_N':len(oracle),
  'sell_oracle_EV_1h':float(oracle.ret_60m.mean()),'sell_oracle_EV_2h':float(oracle.ret_120m.mean()),'sell_oracle_EV_4h':float(oracle.ret_240m.mean()),'sell_oracle_WR_2h':float((oracle.ret_120m>0).mean()),
  'sell_knife_poll_N':len(knife),'sell_knife_EV_2h':float(knife.ret_120m.mean()),'sell_knife_EV_4h':float(knife.ret_240m.mean()),
  'bos_only_blocks_exact_log':0,
  'episode_count':int(ep.episode15.nunique()),
  'buy_episodes':int((ep.side=='BUY').sum()),'sell_episodes':int((ep.side=='SELL').sum()),
  'interpretation':'Descriptive exact-week ablation only. Poll rows are serially correlated; episode table is primary. No threshold tuning.'
 }
 (OUT/'u03_summary.json').write_text(json.dumps(summary,indent=2,default=str))
 print(json.dumps(summary,indent=2,default=str))
 print('\nEPISODE COUNTERFACTUAL')
 cols=['episode15','side','first_time','first_disposition','first_dist','first_ret_60m','first_ret_120m','first_ret_240m','exec_time','delay_min','exec_dist','exec_ret_60m','exec_ret_120m','exec_ret_240m','delta_exec_minus_first_120m']
 print(ep[cols].to_string(index=False))
 print('\nGATE GROUPS')
 print(pd.DataFrame(rows)[['label','N','EV_60m','WR_60m','EV_120m','WR_120m','EV_240m','WR_240m','MFE_MED_120m','MAE_MED_120m']].to_string(index=False))
if __name__=='__main__': main()
