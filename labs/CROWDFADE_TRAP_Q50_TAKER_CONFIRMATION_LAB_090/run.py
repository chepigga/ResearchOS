from pathlib import Path
import json, zipfile, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'/'all_1m'
SRC=ROOT.parent/'CROWDFADE_EXTREME_LS_TRAP_TRIGGER_LAB_089'/'output'/'dedup_events.csv'

TAKER_WINDOWS=[1,3,5,10]
CANDIDATES={1:15.0,-1:10.0}  # side BUY=+1 uses 15m LAB089 candidate; SELL=-1 uses 10m
TARGET_COLS=['tp1p0R','tp1p5R','tp2p0R','tp2p5R']

def load_micro():
    rows=[]
    for zp in sorted(DATA.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,5,9])
        ts=(pd.to_numeric(q.iloc[:,0],errors='coerce')//1000).astype('Int64')
        vol=pd.to_numeric(q.iloc[:,1],errors='coerce')
        tb=pd.to_numeric(q.iloc[:,2],errors='coerce')
        x=pd.DataFrame({'ts_start':ts,'volume':vol,'taker_buy':tb}).dropna()
        x['ts']=x.ts_start.astype(np.int64)+60
        rows.append(x[['ts','volume','taker_buy']])
    m=pd.concat(rows,ignore_index=True).sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
    m['delta']=2*m.taker_buy-m.volume
    for w in TAKER_WINDOWS:
        sv=m.volume.rolling(w,min_periods=w).sum()
        sd=m.delta.rolling(w,min_periods=w).sum()
        m[f'taker_delta{w}']=sd/sv.replace(0,np.nan)
    return m

def add_taker(d,m):
    mt=m.ts.to_numpy(np.int64)
    mi=np.searchsorted(mt,d.ts.to_numpy(np.int64),'right')-1
    for w in TAKER_WINDOWS:
        arr=m[f'taker_delta{w}'].to_numpy(float)
        x=np.full(len(d),np.nan); g=mi>=0; x[g]=arr[mi[g]]
        d[f'taker_delta{w}']=x
        # crowd-direction taker pressure: positive = aggression in crowd direction
        d[f'crowd_taker{w}']=d.crowd_dir.to_numpy(float)*x
    return d

def frozen_q50_filter(d):
    # Recreate LAB089 ALL_Q50 using TRAIN medians separately by side/window.
    keep=np.zeros(len(d),dtype=bool)
    meta=[]
    for sd,w in CANDIDATES.items():
        tr=d[(d.dataset=='historical')&(d.side==sd)&(d.window_min==w)]
        qdls=float(tr.dls.quantile(.5)); qoi=float(tr.doi.quantile(.5)); qrej=float((-tr.price_crowd_R).quantile(.5))
        idx=d.index[(d.side==sd)&(d.window_min==w)]
        mask=(d.loc[idx,'dls']>=qdls)&(d.loc[idx,'doi']>=qoi)&((-d.loc[idx,'price_crowd_R'])>=qrej)
        keep[idx]=mask.to_numpy()
        meta.append({'side':'BUY' if sd>0 else 'SELL','window_min':w,'dls_q50':qdls,'doi_q50':qoi,'reject_q50':qrej})
    return d[keep].copy().reset_index(drop=True),meta

def summarize(g):
    if len(g)==0:return {'N':0}
    return {'N':len(g),'MFE60':float(g.mfe_60m.mean()),'MAE60':float(g.mae_60m.mean()),
            'MFE120':float(g.mfe_120m.mean()),'MAE120':float(g.mae_120m.mean()),
            'TP1R':float(g.tp1p0R.mean()),'TP1p5R':float(g.tp1p5R.mean()),
            'TP2R':float(g.tp2p0R.mean()),'TP2p5R':float(g.tp2p5R.mean())}

def main():
    d=pd.read_csv(SRC)
    d=d[d.apply(lambda r: float(r.window_min)==CANDIDATES[int(r.side)],axis=1)].copy().reset_index(drop=True)
    m=load_micro(); d=add_taker(d,m)
    q50,freeze=frozen_q50_filter(d)

    rows=[]; thresholds=[]
    for sd in [1,-1]:
      side='BUY' if sd>0 else 'SELL'
      for tw in TAKER_WINDOWS:
        tr=q50[(q50.dataset=='historical')&(q50.side==sd)&q50[f'crowd_taker{tw}'].notna()]
        if len(tr)==0: continue
        q50t=float(tr[f'crowd_taker{tw}'].quantile(.5))
        q75t=float(tr[f'crowd_taker{tw}'].quantile(.75))
        thresholds.append({'side':side,'taker_window_min':tw,'q50':q50t,'q75':q75t})
        for ds,g0 in q50[q50.side==sd].groupby('dataset'):
            x=g0[f'crowd_taker{tw}']
            states=[
              ('BASE',np.ones(len(g0),dtype=bool)),
              ('TAKER_AGAINST_CROWD',x<=0),
              ('TAKER_WITH_CROWD',x>0),
              ('TAKER_Q50',x>=q50t),
              ('TAKER_Q75',x>=q75t),
            ]
            for st,mask in states:
                g=g0[mask]
                rows.append({'dataset':ds,'side':side,'taker_window_min':tw,'state':st,
                             'taker_mean':float(g[f'crowd_taker{tw}'].mean()) if len(g) else np.nan,
                             **summarize(g)})

    res=pd.DataFrame(rows)
    res.to_csv(OUT/'taker_confirmation_matrix.csv',index=False)
    pd.DataFrame(thresholds).to_csv(OUT/'taker_train_thresholds.csv',index=False)
    q50.to_csv(OUT/'trap_q50_events_with_taker.csv',index=False)

    # delta vs base for ranking
    rank=[]
    for (ds,side,tw),g in res.groupby(['dataset','side','taker_window_min']):
        b=g[g.state=='BASE']
        if len(b)==0: continue
        B=b.iloc[0]
        for _,r in g[g.state!='BASE'].iterrows():
            rank.append({'dataset':ds,'side':side,'taker_window_min':tw,'state':r.state,'N':int(r.N),
                         'delta_TP1R':float(r.TP1R-B.TP1R),'delta_TP1p5R':float(r.TP1p5R-B.TP1p5R),
                         'delta_TP2R':float(r.TP2R-B.TP2R),'delta_TP2p5R':float(r.TP2p5R-B.TP2p5R),
                         'delta_MFE60':float(r.MFE60-B.MFE60),'delta_MAE60':float(r.MAE60-B.MAE60)})
    rank=pd.DataFrame(rank)
    rank.to_csv(OUT/'taker_uplift_vs_base.csv',index=False)

    summary={
      'lab':'LAB090_TRAP_Q50_TAKER_CONFIRMATION',
      'frozen_lab089_candidates':freeze,
      'taker_windows_min':TAKER_WINDOWS,
      'crowd_taker_definition':'crowd_dir * normalized net taker delta; positive means aggressive taker flow in crowd direction',
      'question':'Does taker confirmation add precision to frozen LAB089 Q50 trap, or merely reduce frequency/delay signal?',
      'thresholds_train':thresholds,
      'sample_counts':q50.groupby(['dataset','side']).size().to_dict(),
      'limitations':['LAB089 candidate and Q50 thresholds frozen before taker analysis.',
                     '2026 Mar-Aug is reused diagnostic data, not pristine OOS.',
                     'Taker confirmation is evaluated at the already-existing LAB089 decision timestamp; no later lookahead window added.',
                     'No production promotion unless uplift is directionally stable in historical and 2026 with usable N.']
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    (OUT/'REPORT.md').write_text('# LAB090 — TRAP_Q50 + TAKER CONFIRMATION\n\n'+json.dumps(summary,indent=2,default=str)+'\n\n## Matrix\n\n'+res.to_markdown(index=False)+'\n\n## Uplift\n\n'+rank.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
