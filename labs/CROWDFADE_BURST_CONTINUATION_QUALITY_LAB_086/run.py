from pathlib import Path
import json, importlib.util, numpy as np, pandas as pd
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p79=ROOT.parent/'CROWDFADE_NLE_2026_FAILURE_DECOMP_LAB_079'/'run.py'
sp=importlib.util.spec_from_file_location('l79',p79)
l79=importlib.util.module_from_spec(sp); sp.loader.exec_module(l79)
l79.DATA=DATA; l79.OUT=OUT
l78=l79.l78; l77=l79.l77; l54=l79.l54; l43=l79.l43
l78.DATA=DATA; l77.DATA=DATA; l54.DATA=DATA; l43.DATA=DATA; l78.lab53.DATA=DATA

HORIZON_MIN=15

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:return {'N':0,'EV_R':np.nan,'WR':np.nan,'PF':np.nan}
    w=x[x>0].sum(); l=-x[x<0].sum()
    return {'N':len(x),'EV_R':float(x.mean()),'WR':float((x>0).mean()),'PF':float(w/l) if l>0 else np.nan}

def build():
    d,ctx,flow,micro=l79.lineage()
    d=d[d.mech_15=='NEW_LONG_EXPANSION'].copy().reset_index(drop=True)
    d=l79.post1r(d,ctx,flow,micro)
    d=d[d.time_to_1R_min.notna()].copy().reset_index(drop=True)
    train=d[d.period=='historical']
    px_q75=float(train.p1_px15.quantile(.75))
    d['PRICE_BURST']=d.p1_px15>=px_q75
    return d,ctx,flow,px_q75

def asof(src,q): return np.searchsorted(src,q,'right')-1

def quality_features(d,ctx,flow):
    for c in ['new_high_R','ft_eff','retrace_R','time_above','oi_cont15','net15_R']:
        d[c]=np.nan
    ft=flow.ts.to_numpy(np.int64); oi=flow.oi.to_numpy(float)
    for per,p in ctx.items():
        ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
        for i in d.index[(d.period==per)&d.PRICE_BURST]:
            r=d.loc[i]; k=int(r.entry_k); ep=float(C5[k]); atr=float(A5[k]); rdist=1.5*atr
            t1=int(r.entry_ts+round(float(r.time_to_1R_min)*60))
            j0=asof(ts,t1); j1=asof(ts,t1+HORIZON_MIN*60)
            if j0<0 or j1<=j0: continue
            burst=float(C[j0])
            hh=float(np.nanmax(H[j0+1:j1+1])); ll=float(np.nanmin(L[j0+1:j1+1]))
            closes=np.asarray(C[j0:j1+1],float)
            d.at[i,'new_high_R']=(hh-burst)/rdist
            d.at[i,'retrace_R']=max(0.0,(burst-ll)/rdist)
            d.at[i,'net15_R']=(float(C[j1])-burst)/rdist
            path=np.nansum(np.abs(np.diff(closes)))
            d.at[i,'ft_eff']=(float(C[j1])-burst)/path if path>0 else 0.0
            d.at[i,'time_above']=float(np.mean(closes[1:]>=burst))
            f0=asof(ft,t1); f1=asof(ft,t1+HORIZON_MIN*60)
            if f0>=0 and f1>=0 and oi[f0]>0:
                d.at[i,'oi_cont15']=oi[f1]/oi[f0]-1.0
    return d

def era(d):
    dt=pd.to_datetime(d.entry_ts,unit='s',utc=True).dt.tz_convert(None)
    d['entry_dt']=dt; y=dt.dt.year
    d['era']=np.select([y<=2024,y==2025,y==2026],['2021_2024','2025','2026'],default='OTHER')
    return d

def percentile_map(train,full,col,sign=1):
    x=np.sort(train[col].dropna().to_numpy(float)); v=full[col].to_numpy(float)
    out=np.full(len(full),np.nan); m=np.isfinite(v)
    if len(x):
        z=np.searchsorted(x,v[m],side='right')/len(x)
        out[m]=z if sign>0 else 1-z
    return out

def score(d):
    b=d[d.PRICE_BURST].copy().reset_index(drop=True)
    tr=b[b.era=='2021_2024'].copy()
    spec=[('new_high_R',1),('ft_eff',1),('retrace_R',-1),('time_above',1),('oi_cont15',1)]
    comps=[]
    for c,s in spec:
        n='q_'+c; b[n]=percentile_map(tr,b,c,s); comps.append(n)
    b['quality_score']=100*b[comps].mean(axis=1)
    return b,spec

def correlations(b,spec):
    rows=[]
    for er,g in b.groupby('era'):
        if er=='OTHER':continue
        for c,_ in spec+[('quality_score',1)]:
            x=g[c].astype(float); y=g.R.astype(float); m=np.isfinite(x)&np.isfinite(y)
            if m.sum()<3:continue
            rho,p=spearmanr(x[m],y[m])
            rows.append({'era':er,'feature':c,'N':int(m.sum()),'rho_R':float(rho),'p':float(p)})
    return pd.DataFrame(rows)

def quartiles(b):
    tr=b[b.era=='2021_2024']; edges=np.unique(np.quantile(tr.quality_score.dropna(),[0,.25,.5,.75,1]))
    rows=[]
    for er,g in b.groupby('era'):
        if er=='OTHER':continue
        z=g.copy(); z['quartile']=pd.cut(z.quality_score,edges,labels=False,include_lowest=True,duplicates='drop')
        for q,h in z.groupby('quartile',dropna=True):
            m=metrics(h.R)
            rows.append({'era':er,'quartile':int(q)+1,'score_mean':float(h.quality_score.mean()),**m,
                         'giveback1R':float(h.giveback_after_1R.mean()),
                         'reach2R':float(h.time_to_2R_min.notna().mean()),
                         'reach3R':float(h.time_to_3R_min.notna().mean()),
                         'new_high_R':float(h.new_high_R.mean()),'ft_eff':float(h.ft_eff.mean()),
                         'retrace_R':float(h.retrace_R.mean()),'time_above':float(h.time_above.mean()),
                         'oi_cont15':float(h.oi_cont15.mean())})
    return pd.DataFrame(rows),edges

def topbottom(b):
    tr=b[b.era=='2021_2024']; q20=float(tr.quality_score.quantile(.2)); q80=float(tr.quality_score.quantile(.8))
    rows=[]
    for er,g in b.groupby('era'):
        if er=='OTHER':continue
        lo=g[g.quality_score<=q20]; hi=g[g.quality_score>=q80]
        if len(lo)==0 or len(hi)==0:continue
        rows.append({'era':er,'q20':q20,'q80':q80,'N_low':len(lo),'N_high':len(hi),
                     'EV_low':float(lo.R.mean()),'EV_high':float(hi.R.mean()),
                     'gap_high_minus_low':float(hi.R.mean()-lo.R.mean()),
                     'giveback_low':float(lo.giveback_after_1R.mean()),'giveback_high':float(hi.giveback_after_1R.mean()),
                     'reach2_low':float(lo.time_to_2R_min.notna().mean()),'reach2_high':float(hi.time_to_2R_min.notna().mean())})
    return pd.DataFrame(rows)

def main():
    d,ctx,flow,pxq=build(); d=era(d); d=quality_features(d,ctx,flow)
    b,spec=score(d)
    corr=correlations(b,spec); q,edges=quartiles(b); tb=topbottom(b)
    b.to_csv(OUT/'burst_quality_events.csv',index=False)
    corr.to_csv(OUT/'feature_correlations.csv',index=False)
    q.to_csv(OUT/'quality_quartiles.csv',index=False)
    tb.to_csv(OUT/'quality_top_bottom.csv',index=False)

    # era state summary with a simple TRAIN median split
    med=float(b[b.era=='2021_2024'].quality_score.median())
    rows=[]
    for er,g in b.groupby('era'):
        if er=='OTHER':continue
        for st,mask in [('LOW_QUALITY',g.quality_score<med),('HIGH_QUALITY',g.quality_score>=med)]:
            h=g[mask]; m=metrics(h.R)
            rows.append({'era':er,'state':st,'threshold':med,**m,
                         'giveback1R':float(h.giveback_after_1R.mean()) if len(h) else np.nan,
                         'reach2R':float(h.time_to_2R_min.notna().mean()) if len(h) else np.nan,
                         'reach3R':float(h.time_to_3R_min.notna().mean()) if len(h) else np.nan})
    states=pd.DataFrame(rows); states.to_csv(OUT/'quality_state_by_era.csv',index=False)

    summary={'lab':'LAB086_BURST_CONTINUATION_QUALITY','burst_threshold_price15_train_q75':pxq,
             'quality_horizon_min':HORIZON_MIN,
             'features':{'new_high_R':'higher better','ft_eff':'higher better','retrace_R':'lower better','time_above':'higher better','oi_cont15':'higher better'},
             'score':'mean of TRAIN empirical percentile ranks; unsupervised by P/L',
             'train_quality_median':med,'quartile_edges':edges.tolist(),
             'correlations':corr.to_dict('records'),'top_bottom':tb.to_dict('records'),
             'note':'Diagnostic only. Forward 2025/2026 burst samples are very small; no production management rule is promoted.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB086 — BURST CONTINUATION QUALITY\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## Quartiles\n\n'+q.to_markdown(index=False)+'\n\n## States\n\n'+states.to_markdown(index=False)+'\n\n## Correlations\n\n'+corr.to_markdown(index=False)+'\n\n## Top-bottom\n\n'+tb.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
