from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_CF191G_VOL_POSTENTRY_EXPANSION_LAB_068'/'output'/'vol_expansion_events.csv'

p53=ROOT.parent/'CROWDFADE_THREE_BOT_FIXES_HISTORICAL_REPLAY_LAB_053'/'run.py'
sp=importlib.util.spec_from_file_location('lab53',p53)
lab53=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab53)
lab43=lab53.lab43

EXPECT={
 'historical':{'N':5297,'SumR':700.3704107793633},
 'forward_2026':{'N':544,'SumR':35.49784078156513},
}
FRACTION=0.50

def metrics(a): return lab43.metrics(np.asarray(a,float))

def period_stats(r,st,period):
    m=metrics(r)
    t=pd.to_datetime(st,unit='s',utc=True)
    keys=t.year.astype(str).to_numpy() if period=='historical' else t.to_period('M').astype(str).to_numpy()
    details={}
    for key in sorted(set(keys)):
        details[str(key)]=metrics(np.asarray(r)[keys==key].astype(float))
    pos=sum(1 for x in details.values() if x.get('SumR',0)>0)
    return m,details,pos,len(details)

def event_stats(g):
    if len(g)==0:
        return {'actions':0,'total_saved_R':0.,'total_given_up_R':0.,'net_delta_R':0.,
                'acted_control_right_tail_share':np.nan,'acted_modified_mean_R_on_control_right_tail':np.nan}
    d=g.modified_R-g.R
    saved=np.maximum(d,0);given=np.maximum(-d,0)
    rt=g[g.R>=1.5]
    return {
      'actions':int(len(g)),
      'total_saved_R':float(saved.sum()),
      'total_given_up_R':float(given.sum()),
      'net_delta_R':float(d.sum()),
      'acted_control_right_tail_share':float((g.R>=1.5).mean()),
      'acted_modified_mean_R_on_control_right_tail':float(rt.modified_R.mean()) if len(rt) else np.nan,
    }

def checks(period,control,cand,cpos,npos,actions):
    min_actions=100 if period=='historical' else 20
    return {
      'R_DD_not_worse':bool(cand['R_DD']>=control['R_DD']),
      'SumR_ge_98pct_control':bool(cand['SumR']>=0.98*control['SumR']),
      'PF_ge_control_or_DD_better':bool(cand['PF']>=control['PF'] or cand['MaxDD_R']<control['MaxDD_R']),
      'max_consecutive_losses_not_worse':bool(cand['MaxConsecutiveLosses']<=control['MaxConsecutiveLosses']),
      'positive_periods_not_worse':bool(npos>=cpos),
      'event_count_meaningful':bool(actions>=min_actions),
    }

def main():
    df=pd.read_csv(SRC)
    required=['period','R','signal_ts','entry_ts','side','entry_price','entry_atr','close15',
              'vol_percentile_7d','early_state','active_at_15m']
    miss=[c for c in required if c not in df.columns]
    if miss: raise RuntimeError(f'missing columns: {miss}')

    # frozen control parity
    for p,e in EXPECT.items():
        d=df[df.period==p]
        if len(d)!=e['N'] or abs(float(d.R.sum())-e['SumR'])>1e-6:
            raise RuntimeError(f'parity fail {p}: {len(d)} {d.R.sum()}')

    high_failed=(df.vol_percentile_7d>=0.80)&(df.early_state=='FAILED_EARLY')&(df.active_at_15m.astype(bool))
    cost=(lab53.COST_BPS/10000.0)*df.entry_price/(lab53.SL_ATR*df.entry_atr)
    r15=df.side*(df.close15-df.entry_price)/(lab53.SL_ATR*df.entry_atr)-cost

    df['acted']=high_failed
    df['R_at_15m']=r15
    df['modified_R']=df.R
    df.loc[high_failed,'modified_R']=FRACTION*r15[high_failed]+(1.0-FRACTION)*df.loc[high_failed,'R']
    df['delta_R']=df.modified_R-df.R
    df['saved_R']=np.maximum(df.delta_R,0)
    df['given_up_R']=np.maximum(-df.delta_R,0)
    df.to_csv(OUT/'partial_events.csv',index=False)

    rows=[];ck={};details={}
    for period in ['historical','forward_2026']:
        d=df[df.period==period].copy()
        cm,cd,cpos,ctot=period_stats(d.R.to_numpy(float),d.signal_ts.to_numpy(np.int64),period)
        mm,md,mpos,mtot=period_stats(d.modified_R.to_numpy(float),d.signal_ts.to_numpy(np.int64),period)
        ag=d[d.acted]
        es=event_stats(ag)
        rows.append({'period':period,'variant':'CONTROL',**cm,'positive_periods':cpos,'periods_total':ctot,
                     'actions':0,'total_saved_R':0.,'total_given_up_R':0.,'net_delta_R':0.,
                     'acted_control_right_tail_share':np.nan,'acted_modified_mean_R_on_control_right_tail':np.nan})
        rows.append({'period':period,'variant':'REDUCE_50_RUNNER_50',**mm,'positive_periods':mpos,'periods_total':mtot,**es})
        ck[period]=checks(period,cm,mm,cpos,mpos,len(ag))
        details[f'{period}_CONTROL']=cd;details[f'{period}_PARTIAL']=md

    comp=pd.DataFrame(rows);comp.to_csv(OUT/'comparison.csv',index=False)
    overall=all(all(v.values()) for v in ck.values())
    result={
      'lab':'LAB070_HIGH_VOL_FAILED_EARLY_PARTIAL',
      'rule':'P80-100 + FAILED_EARLY + active at 15m -> close 50%, keep 50% frozen runner',
      'checks':ck,'PASS_BOTH_PERIODS':bool(overall),'period_details':details,
      'limitations':[
        'Partial reduction does not free occupancy; entry reachability remains identical to control.',
        'Uses frozen LAB068 event table and exact same 15m/P80/FAILED_EARLY state.',
        '50% fraction is preregistered and not tuned.',
        'BTCUSDT only; 2026 Mar-Aug reused shadow/stress.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB070 — HIGH-VOL FAILED-EARLY 50% REDUCTION + RUNNER','',
      '## Comparison','',comp.to_markdown(index=False),'',
      '## Checks','',json.dumps(ck,indent=2),'',
      f'PASS both periods: **{overall}**','',
      '## Limitations']+[f'- {x}' for x in result['limitations']]
    ))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
