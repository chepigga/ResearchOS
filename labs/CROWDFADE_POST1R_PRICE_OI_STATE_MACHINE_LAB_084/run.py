from pathlib import Path
import json, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_NLE_EXHAUSTION_AFTER_1R_LAB_080'/'output'/'nle_lab080_events.csv'

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:return {'N':0,'EV_R':np.nan,'WR':np.nan,'PF':np.nan,'SumR':0.0,'MaxDD_R':np.nan}
    w=x[x>0].sum(); l=-x[x<0].sum()
    eq=np.cumsum(x); peak=np.maximum.accumulate(np.r_[0,eq]); dd=peak[1:]-eq
    return {'N':len(x),'EV_R':float(x.mean()),'WR':float((x>0).mean()),'PF':float(w/l) if l>0 else np.nan,
            'SumR':float(x.sum()),'MaxDD_R':float(dd.max()) if len(dd) else 0.0}

def add_period(d):
    y=d.entry_dt.dt.year
    d['era']=np.select([y<=2024,y==2025,y==2026],['2021_2024','2025','2026'],default='OTHER')
    return d

def state_machine(d,thr):
    d['PRICE_BURST']=d.p1_px15>=thr['px_q75']
    d['OI_EXPAND']=d.p1_oi15>=thr['oi_q75']
    d['TAKER_CONFIRM']=d.p1_taker5>=thr['taker_q75']
    d['state']=np.select([
      ~d.PRICE_BURST,
      d.PRICE_BURST & ~d.OI_EXPAND,
      d.PRICE_BURST & d.OI_EXPAND & ~d.TAKER_CONFIRM,
      d.PRICE_BURST & d.OI_EXPAND & d.TAKER_CONFIRM
    ],[
      'S0_NO_PRICE_BURST',
      'S1_PRICE_ONLY',
      'S2_PRICE_OI',
      'S3_PRICE_OI_TAKER'
    ],default='NA')
    return d

def management(d):
    # Current runner outcome from frozen lineage.
    d['R_CURRENT']=d.R.astype(float)
    # Counterfactual lock +1R: if current final <1R after already reaching +1R, lock to +1R.
    # This is intentionally conservative/idealized as a management upper-bound diagnostic, not production fill simulation.
    d['R_LOCK_1R']=np.where(d.R_CURRENT<1.0,1.0,d.R_CURRENT)
    # Tighter trail proxy: preserve half of excess above +1R, minimum +0.75R.
    d['R_TIGHT_TRAIL']=np.where(d.R_CURRENT>=1.0,1.0+0.5*(d.R_CURRENT-1.0),0.75)
    return d

def summarize(d):
    rows=[]
    for era,g in d.groupby('era'):
        if era=='OTHER':continue
        for st,h in g.groupby('state'):
            for strat,col in [('CURRENT','R_CURRENT'),('LOCK_1R','R_LOCK_1R'),('TIGHT_TRAIL','R_TIGHT_TRAIL')]:
                m=metrics(h[col]); rows.append({'era':era,'state':st,'strategy':strat,**m,
                    'giveback1R':float(h.giveback_after_1R.mean()),'reach2R':float(h.time_to_2R_min.notna().mean()),'reach3R':float(h.time_to_3R_min.notna().mean())})
    return pd.DataFrame(rows)

def state_quality(d):
    rows=[]
    for era,g in d.groupby('era'):
        if era=='OTHER':continue
        for st,h in g.groupby('state'):
            m=metrics(h.R_CURRENT)
            rows.append({'era':era,'state':st,**m,
              'giveback1R':float(h.giveback_after_1R.mean()),
              'reach2R':float(h.time_to_2R_min.notna().mean()),
              'reach3R':float(h.time_to_3R_min.notna().mean()),
              'px15_mean':float(h.p1_px15.mean()),'oi15_mean':float(h.p1_oi15.mean()),'taker5_mean':float(h.p1_taker5.mean())})
    return pd.DataFrame(rows)

def main():
    d=pd.read_csv(SRC)
    d=d[d.time_to_1R_min.notna()].copy()
    d['entry_dt']=pd.to_datetime(d.entry_ts,unit='s',utc=True).dt.tz_convert(None)
    train=d[d.period=='historical']
    thr={'px_q75':float(train.p1_px15.quantile(.75)),
         'oi_q75':float(train.p1_oi15.quantile(.75)),
         'taker_q75':float(train.p1_taker5.quantile(.75))}
    d=add_period(d); d=state_machine(d,thr); d=management(d)

    q=state_quality(d); s=summarize(d)
    q.to_csv(OUT/'state_quality_by_era.csv',index=False)
    s.to_csv(OUT/'management_by_era_state.csv',index=False)
    d.to_csv(OUT/'lab084_events.csv',index=False)

    # identify regime-sensitive state by change in CURRENT EV 2021-24 -> 2026
    p=q.pivot(index='state',columns='era',values='EV_R')
    ranking=[]
    for st,row in p.iterrows():
        if '2021_2024' in row and '2026' in row and pd.notna(row['2021_2024']) and pd.notna(row['2026']):
            ranking.append({'state':st,'EV_2021_2024':float(row['2021_2024']),'EV_2026':float(row['2026']),
                            'delta':float(row['2026']-row['2021_2024'])})
    ranking=sorted(ranking,key=lambda x:x['delta'])

    summary={'lab':'LAB084_POST1R_PRICE_BURST_OI_STATE_MACHINE','thresholds_train_q75':thr,
             'states':['S0_NO_PRICE_BURST','S1_PRICE_ONLY','S2_PRICE_OI','S3_PRICE_OI_TAKER'],
             'regime_sensitive_ranking':ranking,
             'note':'LOCK_1R and TIGHT_TRAIL are counterfactual management diagnostics after +1R, not production execution simulations.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB084 — POST_1R PRICE_BURST × OI STATE MACHINE\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## State quality\n\n'+q.to_markdown(index=False)+'\n\n## Management\n\n'+s.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
