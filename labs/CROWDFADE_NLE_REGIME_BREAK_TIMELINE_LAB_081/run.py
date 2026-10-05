from pathlib import Path
import json, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_NLE_EXHAUSTION_AFTER_1R_LAB_080'/'output'/'nle_lab080_events.csv'

def stats(g):
    if len(g)==0:return {}
    x=g.R.astype(float)
    wins=x[x>0].sum(); losses=-x[x<0].sum()
    pf=float(wins/losses) if losses>0 else np.nan
    return {
      'N':int(len(g)),'EV_R':float(x.mean()),'WR':float((x>0).mean()),'PF':pf,
      'giveback1R':float(g.giveback_after_1R.mean()),
      'reach2R':float(g.time_to_2R_min.notna().mean()),
      'reach3R':float(g.time_to_3R_min.notna().mean())
    }

def grouped(d,freq,label):
    rows=[]
    for p,g in d.groupby(pd.Grouper(key='entry_dt',freq=freq)):
        if len(g)==0:continue
        base={'period':str(p.to_period(label))}
        for state_name,mask in [('ALL',pd.Series(True,index=g.index)),('EXH_CORE',g.EXH_CORE.astype(bool)),('NORMAL',~g.EXH_CORE.astype(bool))]:
            z=g[mask]
            s=stats(z)
            if not s:continue
            rows.append({**base,'state':state_name,**s})
    return pd.DataFrame(rows)

def rolling(d,window=12,minp=6):
    m=[]
    for p,g in d.groupby(pd.Grouper(key='entry_dt',freq='MS')):
        z=g[g.EXH_CORE.astype(bool)]
        m.append({'month':p,'N':len(z),'sumR':z.R.sum(),'sumWin':z.loc[z.R>0,'R'].sum(),'sumLoss':-z.loc[z.R<0,'R'].sum(),
                  'givebacks':z.giveback_after_1R.sum(),'reach2':z.time_to_2R_min.notna().sum(),'reach3':z.time_to_3R_min.notna().sum()})
    m=pd.DataFrame(m).sort_values('month')
    for c in ['N','sumR','sumWin','sumLoss','givebacks','reach2','reach3']:
        m[f'r{window}_{c}']=m[c].rolling(window,min_periods=minp).sum()
    m[f'r{window}_EV']=m[f'r{window}_sumR']/m[f'r{window}_N'].replace(0,np.nan)
    m[f'r{window}_PF']=m[f'r{window}_sumWin']/m[f'r{window}_sumLoss'].replace(0,np.nan)
    m[f'r{window}_giveback']=m[f'r{window}_givebacks']/m[f'r{window}_N'].replace(0,np.nan)
    m[f'r{window}_reach2']=m[f'r{window}_reach2']/m[f'r{window}_N'].replace(0,np.nan)
    m[f'r{window}_reach3']=m[f'r{window}_reach3']/m[f'r{window}_N'].replace(0,np.nan)
    return m

def breakpoint(d):
    z=d[d.EXH_CORE.astype(bool)].sort_values('entry_dt').reset_index(drop=True)
    vals=z.R.to_numpy(float)
    best=None
    # retrospective split, require >=40 observations each side
    for i in range(40,len(z)-40):
        a=vals[:i]; b=vals[i:]
        diff=float(a.mean()-b.mean())
        score=abs(diff)*np.sqrt(len(a)*len(b)/(len(a)+len(b)))
        if best is None or score>best['score']:
            best={'idx':i,'date':str(z.entry_dt.iloc[i].date()),'N_pre':len(a),'N_post':len(b),
                  'EV_pre':float(a.mean()),'EV_post':float(b.mean()),'delta':float(b.mean()-a.mean()),'score':score}
    return best

def quarterly_flip(q):
    x=q[q.state=='EXH_CORE'].copy()
    x['bad']=(x.EV_R<0) & (x.PF<1)
    for i in range(len(x)-1):
        if x.bad.iloc[i] and x.bad.iloc[i+1]:
            return {'first_two_consecutive_bad_quarters':x.period.iloc[i]}
    return {'first_two_consecutive_bad_quarters':None}

def main():
    d=pd.read_csv(SRC)
    d['entry_dt']=pd.to_datetime(d.entry_ts,unit='s',utc=True).dt.tz_convert(None)
    # only trades that actually reached +1R because exhaustion state is evaluated there
    d=d[d.time_to_1R_min.notna()].copy()
    monthly=grouped(d,'MS','M'); quarterly=grouped(d,'QS','Q')
    monthly.to_csv(OUT/'monthly_timeline.csv',index=False); quarterly.to_csv(OUT/'quarterly_timeline.csv',index=False)
    r6=rolling(d,6,3); r12=rolling(d,12,6)
    r6.to_csv(OUT/'rolling_6m.csv',index=False); r12.to_csv(OUT/'rolling_12m.csv',index=False)
    bp=breakpoint(d); flip=quarterly_flip(quarterly)

    # compare EXH vs NORMAL by quarter
    piv=quarterly.pivot(index='period',columns='state',values=['N','EV_R','PF','giveback1R','reach2R','reach3R'])
    piv.columns=['_'.join(map(str,c)) for c in piv.columns]; piv=piv.reset_index()
    if 'EV_R_EXH_CORE' in piv and 'EV_R_NORMAL' in piv:
        piv['EV_gap_EXH_minus_NORMAL']=piv.EV_R_EXH_CORE-piv.EV_R_NORMAL
        piv['giveback_gap']=piv.giveback1R_EXH_CORE-piv.giveback1R_NORMAL
    piv.to_csv(OUT/'quarterly_exh_vs_normal.csv',index=False)

    exq=quarterly[quarterly.state=='EXH_CORE'].copy()
    bad=exq[(exq.EV_R<0)&(exq.PF<1)].copy()
    first_neg=str(bad.period.iloc[0]) if len(bad) else None

    # first sustained 12m negative rolling window
    rr=r12.dropna(subset=['r12_EV']).copy()
    rr['neg']=(rr.r12_EV<0)&(rr.r12_PF<1)
    sustained=None
    for i in range(len(rr)-2):
        if rr.neg.iloc[i:i+3].all():
            sustained=str(rr.month.iloc[i].date()); break

    summary={
      'lab':'LAB081_NLE_REGIME_BREAK_TIMELINE',
      'scope':'NLE trades that reached +1R; EXH_CORE frozen from LAB080',
      'retrospective_best_breakpoint':bp,
      'first_negative_quarter':first_neg,
      'first_two_consecutive_bad_quarters':flip['first_two_consecutive_bad_quarters'],
      'first_3_consecutive_negative_12m_windows':sustained,
      'note':'Breakpoint is retrospective diagnosis, not a production switch. Monthly buckets can be sparse; quarterly/rolling confirmation has priority.'
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    (OUT/'REPORT.md').write_text('# LAB081 — NLE REGIME BREAK TIMELINE\n\n'+json.dumps(summary,indent=2)+'\n\n## Quarterly EXH vs NORMAL\n\n'+piv.to_markdown(index=False)+'\n\n## Monthly\n\n'+monthly.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())
if __name__=='__main__': main()
