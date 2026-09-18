from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_Z205_QUALITY_RISK_RECALIBRATION_LAB_032')
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

HIST=Path('labs/CROWDFADE_TREND_TRANSITION_AND_REVERSAL_RISK_LAB_031/output/trades_historical.csv')
FWD=Path('labs/CROWDFADE_TREND_TRANSITION_AND_REVERSAL_RISK_LAB_031/output/trades_2026_Mar_Aug.csv')

MODES=[
 ('FLAT_1_1_1',1.00,1.00,1.00),
 ('OLD_1P5_1_0P75',1.50,1.00,0.75),
 ('HI1P25_N1_LOW0P75',1.25,1.00,0.75),
 ('HI1P25_N1_LOW1',1.25,1.00,1.00),
 ('HI1_N1_LOW0P75',1.00,1.00,0.75),
]

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:return {'N':0}
    eq=np.cumsum(x)
    peak=np.maximum.accumulate(np.r_[0.0,eq])[1:]
    dd=peak-eq
    pos=x[x>0].sum(); neg=abs(x[x<0].sum())
    cur=mx=0
    for v in x:
        if v<0: cur+=1; mx=max(mx,cur)
        else: cur=0
    return {
      'N':int(len(x)),
      'WR':float((x>0).mean()),
      'EV':float(x.mean()),
      'SumR':float(x.sum()),
      'PF':float(pos/neg) if neg>0 else 99.0,
      'MaxDD_R':float(dd.max()) if len(dd) else 0.0,
      'R_DD':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else 99.0,
      'MaxConsecutiveLosses':int(mx)
    }

def apply(df,hm,nm,lm):
    q=df['lab026_quality'].astype(str).to_numpy()
    m=np.full(len(df),nm,dtype=float)
    m[q=='HIGH']=hm
    m[q=='LOW']=lm
    raw=df['R'].to_numpy(float)
    return raw*m,m

def run(path,period):
    df=pd.read_csv(path)
    raw=df.R.to_numpy(float)
    q=df.lab026_quality.astype(str).to_numpy()

    if period=='historical':
        t=pd.to_datetime(df.signal_time_utc,utc=True)
        labels=t.dt.year.astype(str).to_numpy()
        wanted=[str(y) for y in range(2021,2026)]
        subkey='annual'
    else:
        t=pd.to_datetime(df.signal_time_utc,utc=True)
        labels=t.dt.to_period('M').astype(str).to_numpy()
        wanted=sorted(set(labels))
        subkey='monthly'

    state_raw={s:metrics(raw[q==s]) for s in ['HIGH','NORMAL','LOW']}
    rows=[]; seqs=[]
    for name,hm,nm,lm in MODES:
        wr,mult=apply(df,hm,nm,lm)
        subs={lab:metrics(wr[labels==lab]) for lab in wanted}
        eq=np.cumsum(wr);pk=np.maximum.accumulate(np.r_[0.0,eq])[1:];dd=pk-eq
        row={
          'name':name,
          'multipliers':{'HIGH':hm,'NORMAL':nm,'LOW':lm},
          'all':metrics(wr),
          'positive_periods':int(sum(v.get('SumR',0)>0 for v in subs.values())),
          subkey:subs,
          'quality_contribution_R':{s:float(wr[q==s].sum()) for s in ['HIGH','NORMAL','LOW']}
        }
        rows.append(row)
        seqs.append(pd.DataFrame({
          'mode':name,
          'trade_index':np.arange(1,len(df)+1),
          'signal_time_utc':t.astype(str),
          'period_label':labels,
          'quality_state':q,
          'raw_R':raw,
          'risk_multiplier':mult,
          'weighted_R':wr,
          'equity_R':eq,
          'drawdown_R':dd
        }))

    pd.concat(seqs,ignore_index=True).to_csv(OUT/f'equity_sequence_{period}.csv',index=False)
    return {
      'period':period,
      'N':int(len(df)),
      'raw_flat':metrics(raw),
      'quality_counts':{s:int((q==s).sum()) for s in ['HIGH','NORMAL','LOW']},
      'quality_raw':state_raw,
      'results':rows
    }

def prop_examples(ddR):
    return {
      'base_0.10pct':round(ddR*0.10,4),
      'base_0.15pct':round(ddR*0.15,4),
      'base_0.25pct':round(ddR*0.25,4)
    }

def main():
    hist=run(HIST,'historical')
    fwd=run(FWD,'2026_Mar_Aug')

    ranking=[]
    for hm,fm in zip(hist['results'],fwd['results']):
        ranking.append({
          'name':hm['name'],
          'hist_R_DD':hm['all']['R_DD'],
          'hist_MaxDD_R':hm['all']['MaxDD_R'],
          'hist_positive_years':hm['positive_periods'],
          'fwd_R_DD':fm['all']['R_DD'],
          'fwd_MaxDD_R':fm['all']['MaxDD_R'],
          'fwd_positive_months':fm['positive_periods'],
          'fwd_PF':fm['all']['PF'],
          'fwd_SumR':fm['all']['SumR'],
          'prop_DD_pct_at_base_risk':prop_examples(fm['all']['MaxDD_R'])
        })

    out={
      'lab':'CROWDFADE_Z205_QUALITY_RISK_RECALIBRATION_LAB_032',
      'principle':'Risk-only recalibration on the exact Z=2.05 trade sequence emitted by LAB031. Signal, entry, exit, occupancy, anti-repeat and frequency are unchanged.',
      'frozen':{'Z':2.05,'confirm_ATR':0.25,'retrace_ATR':0.60,'limit_TTL_min':20,'SL_ATR':4.5,'TP_ATR':10.0,'hold_h':24},
      'modes':[{'name':n,'HIGH':h,'NORMAL':nn,'LOW':l} for n,h,nn,l in MODES],
      'historical':hist,
      'forward_shadow_2026':fwd,
      'ranking_inputs':ranking,
      'selection_rule':[
        'Require 5/5 positive historical years where possible.',
        'Prefer higher 2026 R/DD and PF, lower MaxDD, and more positive 2026 months.',
        'Do not promote extra risk if forward-shadow degrades materially versus flat risk.'
      ],
      'limitations':[
        'BTCUSDT research lineage only.',
        '2026 Mar-Aug is reused forward-shadow/stress, not pristine OOS.',
        'Normalized R sequence; not a broker-specific daily-DD/margin simulation.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__': main()
