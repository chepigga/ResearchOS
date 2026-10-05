from pathlib import Path
import json, itertools, numpy as np, pandas as pd
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_NLE_CONTINUOUS_EXHAUSTION_SCORE_LAB_082'/'output'/'nle_score_events.csv'

COMPONENTS=['s_p1_oi15','s_p1_px15','s_p1_taker5','s_atr_pct','s_eff30']

def corr_rows(d):
    rows=[]
    for per,g in d.groupby('period'):
        for c in COMPONENTS:
            for target in ['R','giveback_after_1R']:
                x=g[c].astype(float); y=g[target].astype(float)
                m=np.isfinite(x)&np.isfinite(y)
                if m.sum()<8: continue
                rho,p=spearmanr(x[m],y[m])
                rows.append({'period':per,'component':c,'target':target,'N':int(m.sum()),'rho':float(rho),'p':float(p)})
    return pd.DataFrame(rows)

def timeline(d):
    rows=[]
    for c in COMPONENTS:
        for q,g in d.groupby(pd.Grouper(key='entry_dt',freq='QS')):
            if len(g)<5: continue
            x=g[c].astype(float); y=g.R.astype(float)
            m=np.isfinite(x)&np.isfinite(y)
            if m.sum()<5: continue
            rho,p=spearmanr(x[m],y[m])
            rows.append({'component':c,'quarter':str(q.to_period('Q')),'N':int(m.sum()),'rho_R':float(rho),'p_R':float(p)})
    return pd.DataFrame(rows)

def first_sign_flip(t):
    out=[]
    for c,g in t.groupby('component'):
        g=g.sort_values('quarter').reset_index(drop=True)
        # establish historical baseline sign from all 2021-2025 quarters weighted by N
        h=g[g.quarter.str[:4].astype(int)<=2025]
        base=np.sign(np.average(h.rho_R,weights=h.N)) if len(h) else 0
        flip=None
        for i in range(len(g)-1):
            r1=np.sign(g.rho_R.iloc[i]); r2=np.sign(g.rho_R.iloc[i+1])
            if base!=0 and r1==-base and r2==-base:
                flip=g.quarter.iloc[i]; break
        out.append({'component':c,'baseline_sign':int(base),'first_two_quarter_opposite_sign':flip})
    return pd.DataFrame(out)

def quantile_gap(d):
    rows=[]
    train=d[d.period=='historical']
    for c in COMPONENTS:
        q20=float(train[c].quantile(.2)); q80=float(train[c].quantile(.8))
        for per,g in d.groupby('period'):
            lo=g[g[c]<=q20]; hi=g[g[c]>=q80]
            if len(lo)<3 or len(hi)<3: continue
            rows.append({'period':per,'component':c,'N_low':len(lo),'N_high':len(hi),
                         'EV_low':float(lo.R.mean()),'EV_high':float(hi.R.mean()),
                         'gap_high_minus_low':float(hi.R.mean()-lo.R.mean()),
                         'giveback_low':float(lo.giveback_after_1R.mean()),
                         'giveback_high':float(hi.giveback_after_1R.mean())})
    return pd.DataFrame(rows)

def pair_interactions(d):
    rows=[]
    train=d[d.period=='historical']
    qs={c:float(train[c].quantile(.75)) for c in COMPONENTS}
    for a,b in itertools.combinations(COMPONENTS,2):
        for per,g in d.groupby('period'):
            both=g[(g[a]>=qs[a])&(g[b]>=qs[b])]
            neither=g[(g[a]<qs[a])&(g[b]<qs[b])]
            if len(both)<3 or len(neither)<3: continue
            rows.append({'period':per,'a':a,'b':b,'N_both':len(both),'N_neither':len(neither),
                         'EV_both':float(both.R.mean()),'EV_neither':float(neither.R.mean()),
                         'gap_both_minus_neither':float(both.R.mean()-neither.R.mean()),
                         'giveback_both':float(both.giveback_after_1R.mean()),
                         'giveback_neither':float(neither.giveback_after_1R.mean())})
    return pd.DataFrame(rows)

def main():
    d=pd.read_csv(SRC)
    d['entry_dt']=pd.to_datetime(d.entry_ts,unit='s',utc=True).dt.tz_convert(None)
    c=corr_rows(d); t=timeline(d); f=first_sign_flip(t); q=quantile_gap(d); p=pair_interactions(d)
    c.to_csv(OUT/'component_correlations.csv',index=False)
    t.to_csv(OUT/'quarterly_component_timeline.csv',index=False)
    f.to_csv(OUT/'first_sign_flip.csv',index=False)
    q.to_csv(OUT/'component_top_bottom_gap.csv',index=False)
    p.to_csv(OUT/'pair_interactions.csv',index=False)

    h=c[(c.period=='historical')&(c.target=='R')][['component','rho']].rename(columns={'rho':'rho_hist'})
    fw=c[(c.period=='forward_2026')&(c.target=='R')][['component','rho']].rename(columns={'rho':'rho_2026'})
    rank=h.merge(fw,on='component',how='outer')
    rank['sign_flip']=np.sign(rank.rho_hist)!=np.sign(rank.rho_2026)
    rank['delta_rho']=rank.rho_2026-rank.rho_hist
    rank=rank.sort_values('delta_rho')
    rank.to_csv(OUT/'driver_ranking.csv',index=False)

    summary={'lab':'LAB083_SCORE_SIGN_FLIP_DRIVER',
             'driver_ranking':rank.to_dict('records'),
             'first_sustained_opposite_sign_by_quarter':f.to_dict('records'),
             'note':'Diagnostic only. Component percentiles are frozen from LAB082 TRAIN mapping; no refit on 2026.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB083 — SCORE SIGN FLIP DRIVER\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## Correlations\n\n'+c.to_markdown(index=False)+'\n\n## Top-bottom gaps\n\n'+q.to_markdown(index=False)+'\n\n## Pair interactions\n\n'+p.to_markdown(index=False)+'\n\n## Quarterly timeline\n\n'+t.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
