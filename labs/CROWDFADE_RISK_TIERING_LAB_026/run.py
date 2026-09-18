from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_RISK_TIERING_LAB_026')
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

HIST_SRC=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025/output/trades_diagnostic.csv')
FWD_SRC=Path('labs/CROWDFADE_CROWD_TREND_PRICE_RESPONSE_LAB_025/output/trades_2026_diagnostic.csv')

MODES=[
    ('BASELINE',1.0,1.0,1.0),
    ('HIGH_1P5_NORMAL_1_LOW_1',1.5,1.0,1.0),
    ('HIGH_1P5_NORMAL_1_LOW_0P75',1.5,1.0,0.75),
    ('HIGH_1P5_NORMAL_1_LOW_0P50',1.5,1.0,0.50),
]

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:
        return {'N':0}
    eq=np.cumsum(x)
    peak=np.maximum.accumulate(np.r_[0.0,eq])[1:]
    dd=peak-eq
    pos=x[x>0].sum()
    neg=abs(x[x<0].sum())
    max_consec=cur=0
    for v in x:
        if v<0:
            cur+=1
            max_consec=max(max_consec,cur)
        else:
            cur=0
    return {
        'N':int(len(x)),
        'WR':float((x>0).mean()),
        'EV_baseR_per_trade':float(x.mean()),
        'Sum_baseR':float(x.sum()),
        'PF':float(pos/neg) if neg>0 else 99.0,
        'MaxDD_baseR':float(dd.max()) if len(dd) else 0.0,
        'R_DD':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else 99.0,
        'MaxConsecutiveLosses':int(max_consec),
    }

def classify(df):
    high=(df['trend_relation']==1) & (df['crowd_excursion_atr']<=0.75)
    low=(df['trend_relation']!=0) & (df['crowd_excursion_atr']>0.75)
    quality=np.where(high,'HIGH',np.where(low,'LOW','NORMAL'))
    return high.to_numpy(),low.to_numpy(),quality

def apply_mode(raw,high,low,hi_mult,norm_mult,low_mult):
    mult=np.full(len(raw),norm_mult,dtype=float)
    mult[high]=hi_mult
    mult[low]=low_mult
    return raw*mult,mult

def max_loss_cluster(weighted):
    # worst contiguous negative-only cluster sum, useful for prop sizing
    worst=0.0
    cur=0.0
    for v in weighted:
        if v<0:
            cur+=v
            worst=min(worst,cur)
        else:
            cur=0.0
    return float(worst)

def run_hist():
    df=pd.read_csv(HIST_SRC)
    raw=df['R'].to_numpy(float)
    high,low,quality=classify(df)
    df['quality_state']=quality

    rows=[]
    seqs=[]
    for name,hm,nm,lm in MODES:
        wr,mult=apply_mode(raw,high,low,hm,nm,lm)
        eq=np.cumsum(wr)
        peak=np.maximum.accumulate(np.r_[0.0,eq])[1:]
        dd=peak-eq
        annual={}
        for y in range(2021,2026):
            mask=df['year'].to_numpy(int)==y
            annual[str(y)]=metrics(wr[mask])
        rows.append({
            'name':name,
            'multipliers':{'HIGH':hm,'NORMAL':nm,'LOW':lm},
            'all':metrics(wr),
            'positive_years':int(sum(v['Sum_baseR']>0 for v in annual.values())),
            'annual':annual,
            'state_counts':{
                'HIGH':int(high.sum()),
                'NORMAL':int((~high & ~low).sum()),
                'LOW':int(low.sum()),
            },
            'state_contribution_baseR':{
                'HIGH':float(wr[high].sum()),
                'NORMAL':float(wr[(~high)&(~low)].sum()),
                'LOW':float(wr[low].sum()),
            },
            'worst_negative_streak_sum_baseR':max_loss_cluster(wr),
        })
        seqs.append(pd.DataFrame({
            'mode':name,
            'trade_index':np.arange(1,len(df)+1),
            'year':df['year'].to_numpy(int),
            'quality_state':quality,
            'raw_R':raw,
            'risk_multiplier':mult,
            'weighted_R':wr,
            'equity_baseR':eq,
            'drawdown_baseR':dd,
        }))

    pd.concat(seqs,ignore_index=True).to_csv(OUT/'equity_sequence_2021_2025.csv',index=False)
    return {
        'period':'2021-2025 historical discovery',
        'source':str(HIST_SRC),
        'state_definition':{
            'HIGH':'trend_relation == WITH_TREND and crowd_excursion_atr <= 0.75',
            'LOW':'H1/H4 aligned (trend_relation != 0) and crowd_excursion_atr > 0.75',
            'NORMAL':'all remaining baseline trades',
        },
        'baseline_trade_count':int(len(df)),
        'results':rows,
    }

def run_fwd():
    df=pd.read_csv(FWD_SRC)
    raw=df['R'].to_numpy(float)
    high,low,quality=classify(df)
    df['quality_state']=quality
    times=pd.to_datetime(df['entry_ts'].astype('int64'),unit='s',utc=True)
    months=times.dt.to_period('M').astype(str).to_numpy()

    rows=[]
    seqs=[]
    for name,hm,nm,lm in MODES:
        wr,mult=apply_mode(raw,high,low,hm,nm,lm)
        eq=np.cumsum(wr)
        peak=np.maximum.accumulate(np.r_[0.0,eq])[1:]
        dd=peak-eq
        monthly={}
        for mo in sorted(set(months)):
            mask=months==mo
            monthly[mo]=metrics(wr[mask])
        rows.append({
            'name':name,
            'multipliers':{'HIGH':hm,'NORMAL':nm,'LOW':lm},
            'all':metrics(wr),
            'positive_months':int(sum(v['Sum_baseR']>0 for v in monthly.values())),
            'monthly':monthly,
            'state_counts':{
                'HIGH':int(high.sum()),
                'NORMAL':int((~high & ~low).sum()),
                'LOW':int(low.sum()),
            },
            'state_contribution_baseR':{
                'HIGH':float(wr[high].sum()),
                'NORMAL':float(wr[(~high)&(~low)].sum()),
                'LOW':float(wr[low].sum()),
            },
            'worst_negative_streak_sum_baseR':max_loss_cluster(wr),
        })
        seqs.append(pd.DataFrame({
            'mode':name,
            'trade_index':np.arange(1,len(df)+1),
            'entry_time_utc':times.astype(str),
            'month':months,
            'quality_state':quality,
            'raw_R':raw,
            'risk_multiplier':mult,
            'weighted_R':wr,
            'equity_baseR':eq,
            'drawdown_baseR':dd,
        }))

    pd.concat(seqs,ignore_index=True).to_csv(OUT/'equity_sequence_2026.csv',index=False)
    return {
        'period':'2026 seconds forward-shadow/stress',
        'source':str(FWD_SRC),
        'state_definition':{
            'HIGH':'trend_relation == WITH_TREND and crowd_excursion_atr <= 0.75',
            'LOW':'H1/H4 aligned (trend_relation != 0) and crowd_excursion_atr > 0.75',
            'NORMAL':'all remaining baseline trades',
        },
        'baseline_trade_count':int(len(df)),
        'results':rows,
    }

def main():
    hist=run_hist()
    fwd=run_fwd()
    out={
        'lab':'CROWDFADE_RISK_TIERING_LAB_026',
        'principle':'Position sizing only. Trade reachability, entry, exit, occupancy and anti-repeat sequence are unchanged.',
        'modes':[x[0] for x in MODES],
        'historical':hist,
        'forward_shadow_2026':fwd,
        'risk_examples':{
            'base_0.10pct':{
                'HIGH_1P5':0.15,
                'NORMAL_1P0':0.10,
                'LOW_0P75':0.075,
                'LOW_0P50':0.05,
            },
            'base_0.15pct':{
                'HIGH_1P5':0.225,
                'NORMAL_1P0':0.15,
                'LOW_0P75':0.1125,
                'LOW_0P50':0.075,
            },
            'base_0.25pct':{
                'HIGH_1P5':0.375,
                'NORMAL_1P0':0.25,
                'LOW_0P75':0.1875,
                'LOW_0P50':0.125,
            }
        }
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':
    main()
