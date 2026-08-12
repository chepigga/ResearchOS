from pathlib import Path
import json
import numpy as np
import pandas as pd

OUT=Path('u06_out'); OUT.mkdir(exist_ok=True)
EP='u05_out/u05_episode_market_clock_map.csv'
EV='lab020_events.csv'

def label_core(e):
    e=e.copy()
    e['core_state']='OTHER'
    e.loc[(e.side=='BUY')&(e.H4_ST_AGE_BARS>58)&(e.H4_ST_DIR==-1),'core_state']='BUY_TIER_A'
    e.loc[(e.side=='BUY')&(e.H4_ST_AGE_BARS>58)&(e.H4_ST_DIR==1),'core_state']='BUY_TIER_B'
    e.loc[(e.side=='SELL')&(e.H4_ST_AGE_BARS>26)&(e.H4_ST_AGE_BARS<=50),'core_state']='SELL_B3_RECENT'
    return e

def row_event(r,prefix):
    if r is None:return {prefix+'_time':pd.NaT,prefix+'_state':None,prefix+'_age':np.nan,prefix+'_h4dir':np.nan,prefix+'_net48':np.nan,prefix+'_stress48':np.nan}
    return {prefix+'_time':r.entry_time,prefix+'_state':r.core_state,prefix+'_age':r.H4_ST_AGE_BARS,prefix+'_h4dir':r.H4_ST_DIR,prefix+'_net48':getattr(r,'NET48_SPREAD_PCT',np.nan),prefix+'_stress48':getattr(r,'NET48_STRESS_PCT',np.nan)}

def main():
    ep=pd.read_csv(EP); ep['signal_time']=pd.to_datetime(ep.signal_time); ep['oracle_utc']=ep.signal_time-pd.Timedelta(hours=3)
    ev=pd.read_csv(EV); ev['entry_time']=pd.to_datetime(ev.entry_time); ev=label_core(ev).sort_values('entry_time')
    recent=ev[(ev.entry_time>=pd.Timestamp('2026-08-01'))&(ev.entry_time<pd.Timestamp('2026-08-11'))].copy()
    recent.to_csv(OUT/'u06_core_events_aug1_10.csv',index=False)
    out=[]
    for q in ep.itertuples(index=False):
        same=recent[recent.side==q.side]
        prev=same[same.entry_time<=q.oracle_utc]
        nxt=same[same.entry_time>q.oracle_utc]
        prev_r=prev.iloc[-1] if len(prev) else None; next_r=nxt.iloc[0] if len(nxt) else None
        target='BUY_TIER_A' if q.side=='BUY' else 'SELL_B3_RECENT'
        tar=recent[(recent.side==q.side)&(recent.core_state==target)]
        prev_t=tar[tar.entry_time<=q.oracle_utc]; next_t=tar[tar.entry_time>q.oracle_utc]
        prev_t_r=prev_t.iloc[-1] if len(prev_t) else None; next_t_r=next_t.iloc[0] if len(next_t) else None
        r={'episode15':q.episode15,'oracle_server':q.signal_time,'oracle_utc':q.oracle_utc,'side':q.side,'tag':q.tag,'oracle_disposition':q.disposition,'oracle_h4dir':q.st_dir,'oracle_age':q.st_age,'oracle_state':q.unified_state,'target_state':target}
        for pref,z in [('prev_same',prev_r),('next_same',next_r),('prev_target',prev_t_r),('next_target',next_t_r)]:
            if z is not None and not hasattr(z,'entry_time'): z=type('R',(),z.to_dict())()
            r.update(row_event(z,pref))
        r['hours_from_prev_target']=(q.oracle_utc-r['prev_target_time']).total_seconds()/3600 if pd.notna(r['prev_target_time']) else np.nan
        r['hours_to_next_target']=(r['next_target_time']-q.oracle_utc).total_seconds()/3600 if pd.notna(r['next_target_time']) else np.nan
        out.append(r)
    o=pd.DataFrame(out); o.to_csv(OUT/'u06_oracle_to_core_transfer.csv',index=False)
    # Episode-level transition conclusions.
    summary={
      'oracle_episodes':len(o),
      'buy_episodes':int((o.side=='BUY').sum()),
      'buy_already_tier_a_clock':int(((o.side=='BUY')&(o.oracle_state=='BUY_TIER_A')).sum()),
      'sell_episodes':int((o.side=='SELL').sum()),
      'sell_pre_b3_clock':int(((o.side=='SELL')&(o.oracle_age<27)).sum()),
      'sell_with_next_b3_within_12h':int(((o.side=='SELL')&(o.hours_to_next_target>=0)&(o.hours_to_next_target<=12)).sum()),
      'interpretation':'Exact Aug1-10 lifecycle ordering only. No threshold tuning. Core event outcomes are frozen LAB020 values.'
    }
    (OUT/'u06_summary.json').write_text(json.dumps(summary,indent=2,default=str))
    print('ORACLE -> CORE')
    cols=['episode15','oracle_utc','side','oracle_disposition','oracle_age','oracle_state','prev_target_time','hours_from_prev_target','prev_target_net48','next_target_time','hours_to_next_target','next_target_net48']
    print(o[cols].to_string(index=False))
    print('\nCORE EVENTS AUG1-10')
    show=[c for c in ['entry_time','side','H4_ST_DIR','H4_ST_AGE_BARS','core_state','NET48_SPREAD_PCT','NET48_STRESS_PCT'] if c in recent.columns]
    print(recent[show].to_string(index=False))
    print('\nSUMMARY'); print(json.dumps(summary,indent=2,default=str))
if __name__=='__main__':main()
