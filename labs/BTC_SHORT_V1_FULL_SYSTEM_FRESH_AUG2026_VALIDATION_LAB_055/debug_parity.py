from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent; LABS=HERE.parent; OUT=HERE/'output'
new=pd.read_csv(OUT/'full_system_stream.csv')
old=pd.read_csv(LABS/'BTC_SHORT_ACCEPT25_PERSISTENT_FAILURE_EXIT_VS_SEVERE_ADVERSE1R_EXECUTION_LAB_053'/'output'/'execution_stream.csv')
new['signal_time']=pd.to_datetime(new.signal_time,utc=True); pre=new[(new.signal_time<pd.Timestamp('2026-08-01',tz='UTC')) & new.traded.astype(str).str.lower().eq('true')]
old=old[old.policy=='PERSISTENT_EXIT']
a=set(pre.flow_id.astype(int)); b=set(old.flow_id.astype(int))
extra=sorted(a-b); missing=sorted(b-a)
cols=[c for c in ['flow_id','signal_time','state','entry_time','horizon','parent_exit_reason','final_exit_reason','eligible','covered'] if c in pre.columns]
pd.concat([pre[pre.flow_id.astype(int).isin(extra)][cols].assign(diff='EXTRA'),pre[pre.flow_id.astype(int).isin(missing)][cols].assign(diff='MISSING')]).to_csv(OUT/'parity_diff.csv',index=False)
print('extra',extra,'missing',missing)
