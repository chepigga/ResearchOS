from pathlib import Path
import json, numpy as np, pandas as pd
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_NLE_EXHAUSTION_AFTER_1R_LAB_080'/'output'/'nle_lab080_events.csv'

FEATURES=[
  ('p1_oi15',+1.0),
  ('p1_px15',+1.0),
  ('p1_taker5',+1.0),
  ('atr_pct',+1.0),
  ('eff30',-1.0),
]

def pct_rank_train(train, full, col, sign):
    x=train[col].dropna().sort_values().to_numpy(float)
    vals=full[col].to_numpy(float)
    out=np.full(len(full),np.nan)
    if len(x)==0:return out
    mask=np.isfinite(vals)
    ranks=np.searchsorted(x,vals[mask],side='right')/len(x)
    out[mask]=ranks
    if sign<0: out[mask]=1.0-ranks
    return out

def metrics(g):
    if len(g)==0:return {}
    x=g.R.astype(float); w=x[x>0].sum(); l=-x[x<0].sum()
    return {'N':len(g),'EV_R':float(x.mean()),'WR':float((x>0).mean()),'PF':float(w/l) if l>0 else np.nan,
            'giveback1R':float(g.giveback_after_1R.mean()),
            'reach2R':float(g.time_to_2R_min.notna().mean()),
            'reach3R':float(g.time_to_3R_min.notna().mean()),
            'median_R':float(x.median())}

def deciles(d, edges):
    rows=[]
    for per,g in d.groupby('period'):
        z=g.copy()
        z['decile']=pd.cut(z.score,edges,labels=False,include_lowest=True,duplicates='drop')
        for k,h in z.groupby('decile',dropna=True):
            rows.append({'period':per,'decile':int(k)+1,'score_mean':float(h.score.mean()),**metrics(h)})
    return pd.DataFrame(rows)

def monotonic(df):
    rows=[]
    for per,g in df.groupby('period'):
        g=g.sort_values('decile')
        for target in ['EV_R','giveback1R','reach2R','reach3R']:
            if len(g)>=3:
                rho,p=spearmanr(g.decile,g[target],nan_policy='omit')
                rows.append({'period':per,'target':target,'spearman_rho':float(rho),'p_value':float(p)})
    return pd.DataFrame(rows)

def bootstrap_gap(d, n=5000, seed=42):
    rng=np.random.default_rng(seed); rows=[]
    for per,g in d.groupby('period'):
        lo=g[g.score<=g.score.quantile(.2)].R.to_numpy(float)
        hi=g[g.score>=g.score.quantile(.8)].R.to_numpy(float)
        if len(lo)<3 or len(hi)<3:continue
        sims=[]
        for _ in range(n):
            sims.append(rng.choice(hi,len(hi),True).mean()-rng.choice(lo,len(lo),True).mean())
        sims=np.asarray(sims)
        rows.append({'period':per,'N_low':len(lo),'N_high':len(hi),'EV_low':float(lo.mean()),'EV_high':float(hi.mean()),
                     'gap_high_minus_low':float(hi.mean()-lo.mean()),
                     'ci95_lo':float(np.quantile(sims,.025)),'ci95_hi':float(np.quantile(sims,.975))})
    return pd.DataFrame(rows)

def main():
    d=pd.read_csv(SRC)
    d=d[d.time_to_1R_min.notna()].copy().reset_index(drop=True)
    train=d[d.period=='historical'].copy()
    comps=[]
    for col,sgn in FEATURES:
        c=f's_{col}'
        d[c]=pct_rank_train(train,d,col,sgn)
        comps.append(c)
    d['score01']=d[comps].mean(axis=1)
    d['score']=100*d.score01
    train_scores=d.loc[d.period=='historical','score'].dropna()
    edges=np.unique(np.quantile(train_scores,np.linspace(0,1,11)))
    dec=deciles(d,edges); mono=monotonic(dec); boot=bootstrap_gap(d)

    # simple score bands frozen from historical deciles
    q80=float(train_scores.quantile(.8)); q90=float(train_scores.quantile(.9))
    bands=[]
    for per,g in d.groupby('period'):
        for name,mask in [('LOW_0_50',g.score<50),('MID_50_80',(g.score>=50)&(g.score<q80)),('HIGH_80_90',(g.score>=q80)&(g.score<q90)),('EXTREME_90_100',g.score>=q90)]:
            h=g[mask]; bands.append({'period':per,'band':name,'threshold_q80':q80,'threshold_q90':q90,**metrics(h)})
    bands=pd.DataFrame(bands)

    d.to_csv(OUT/'nle_score_events.csv',index=False)
    dec.to_csv(OUT/'decile_metrics.csv',index=False)
    mono.to_csv(OUT/'monotonicity.csv',index=False)
    boot.to_csv(OUT/'bootstrap_top_bottom_gap.csv',index=False)
    bands.to_csv(OUT/'score_bands.csv',index=False)

    s={'lab':'LAB082_NLE_CONTINUOUS_EXHAUSTION_SCORE','scope':'NLE trades that reached +1R only',
       'features':{c:('higher=more exhaustion' if s>0 else 'lower=more exhaustion') for c,s in FEATURES},
       'score':'mean of five TRAIN empirical percentile components ×100; no supervised fitting',
       'train_q80':q80,'train_q90':q90,
       'historical_monotonicity':mono[mono.period=='historical'].to_dict('records'),
       'forward_2026_monotonicity':mono[mono.period=='forward_2026'].to_dict('records'),
       'bootstrap_top_bottom':boot.to_dict('records'),
       'note':'Diagnostic only. Production promotion requires same directional monotonicity in forward data with adequate N.'}
    (OUT/'summary.json').write_text(json.dumps(s,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB082 — NLE CONTINUOUS EXHAUSTION SCORE\n\n'+json.dumps(s,indent=2,default=float)+'\n\n## Deciles\n\n'+dec.to_markdown(index=False)+'\n\n## Bands\n\n'+bands.to_markdown(index=False)+'\n\n## Monotonicity\n\n'+mono.to_markdown(index=False)+'\n\n## Bootstrap top-bottom\n\n'+boot.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())
if __name__=='__main__': main()
