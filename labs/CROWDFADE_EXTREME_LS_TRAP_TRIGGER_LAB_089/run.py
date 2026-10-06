from pathlib import Path
import json, importlib.util, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p88=ROOT.parent/'CROWDFADE_LS_OI_PRICE_RESPONSE_TRAP_EDGE_LAB_088'/'run.py'
sp=importlib.util.spec_from_file_location('l88',p88)
l88=importlib.util.module_from_spec(sp); sp.loader.exec_module(l88)
l88.DATA=DATA; l88.OUT=OUT
l88.l54.DATA=DATA; l88.l54.lab53.DATA=DATA; l88.l43.DATA=DATA

WINDOWS=[5,7.5,10,15]
OI_FLAT=0.0002
EXTREME_Z=2.5
PRICE_REJECT_ATR=-0.10
COOLDOWN_MIN=30
TARGETS=[1.0,1.5,2.0,2.5]

def asof(a,q): return np.searchsorted(a,q,'right')-1

def load():
    flow=l88.l54.load_flow_meta().copy()
    ft,fz=l88.l43.load_flow()
    hist=l88.l43.prep(l88.l43.load_hist(),ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=l88.l43.prep(l88.l43.load_sec(),ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    return flow,{'historical':hist,'forward_2026':fwd}

def event_frame(label,p,flow):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    f=flow[(flow.ts>=ts[0])&(flow.ts<=ts[-1])&(flow.z.abs()>=EXTREME_Z)].copy().drop_duplicates('ts').reset_index(drop=True)
    fts=flow.ts.to_numpy(np.int64); ratio=flow.ratio.to_numpy(float); oi=flow.oi.to_numpy(float)
    rows=[]
    for _,r in f.iterrows():
        t=int(r.ts); z=float(r.z); crowd=1 if z>0 else -1; side=-crowd
        j=asof(ts,t); k=asof(dt5,t)
        if j<20 or k<2: continue
        atr=float(A5[k]); ep=float(C[j])
        if not np.isfinite(atr) or atr<=0: continue
        for w in WINDOWS:
            sec=int(round(w*60))
            fp=asof(fts,t-sec); jp=asof(ts,t-sec); fi=asof(fts,t)
            if fp<0 or jp<0 or fi<0 or oi[fp]<=0: continue
            dls=crowd*(ratio[fi]-ratio[fp])
            doi=oi[fi]/oi[fp]-1.0
            pr=crowd*(ep-float(C[jp]))/atr
            trigger=(dls>0 and doi>OI_FLAT and pr<PRICE_REJECT_ATR)
            if not trigger: continue
            rec={'dataset':label,'ts':t,'window_min':w,'z':z,'abs_z':abs(z),'crowd_dir':crowd,'side':side,
                 'entry':ep,'atr':atr,'dls':dls,'doi':doi,'price_crowd_R':pr}
            # forward outcomes from decision time
            for h in [30,60,120]:
                e=np.searchsorted(ts,t+h*60,'right'); s=j+1
                if e<=s:
                    rec[f'mfe_{h}m']=np.nan; rec[f'mae_{h}m']=np.nan
                else:
                    if side>0:
                        fav=(np.nanmax(H[s:e])-ep)/atr; adv=(ep-np.nanmin(L[s:e]))/atr
                    else:
                        fav=(ep-np.nanmin(L[s:e]))/atr; adv=(np.nanmax(H[s:e])-ep)/atr
                    rec[f'mfe_{h}m']=float(max(0,fav)); rec[f'mae_{h}m']=float(max(0,adv))
            e=np.searchsorted(ts,t+120*60,'right'); s=j+1
            for target in TARGETS:
                hit=0
                for q in range(s,e):
                    tp=(H[q]>=ep+target*atr) if side>0 else (L[q]<=ep-target*atr)
                    st=(L[q]<=ep-atr) if side>0 else (H[q]>=ep+atr)
                    if tp or st:
                        hit=int(tp and not st); break
                rec[f'tp{str(target).replace(".","p")}R']=hit
            rows.append(rec)
    return pd.DataFrame(rows)

def dedup(d):
    # keep first trigger after cooldown independently by dataset/window/side
    out=[]
    for (ds,w,sd),g in d.sort_values('ts').groupby(['dataset','window_min','side']):
        last=-10**18
        for i,r in g.iterrows():
            if int(r.ts)-last >= COOLDOWN_MIN*60:
                out.append(i); last=int(r.ts)
    x=d.loc[out].copy().sort_values(['dataset','window_min','ts']).reset_index(drop=True)
    return x

def bucket_summary(d,label):
    rows=[]
    for (ds,sd,w),g in d.groupby(['dataset','side','window_min']):
        row={'sample':label,'dataset':ds,'side':'BUY' if sd>0 else 'SELL','window_min':w,'N':len(g),
             'dls_mean':float(g.dls.mean()),'doi_mean':float(g.doi.mean()),'reject_mean_R':float(g.price_crowd_R.mean()),
             'MFE60':float(g.mfe_60m.mean()),'MAE60':float(g.mae_60m.mean()),
             'MFE120':float(g.mfe_120m.mean()),'MAE120':float(g.mae_120m.mean())}
        for t in TARGETS: row[f'TP{t}R']=float(g[f'tp{str(t).replace(".","p")}R'].mean())
        rows.append(row)
    return pd.DataFrame(rows)

def quantile_decomp(d):
    # thresholds frozen from historical dedup pooled per side/window
    rows=[]
    for (sd,w),tr in d[d.dataset=='historical'].groupby(['side','window_min']):
        qs={
          'dls_q50':float(tr.dls.quantile(.5)),'dls_q75':float(tr.dls.quantile(.75)),
          'doi_q50':float(tr.doi.quantile(.5)),'doi_q75':float(tr.doi.quantile(.75)),
          'rej_q50':float((-tr.price_crowd_R).quantile(.5)),'rej_q75':float((-tr.price_crowd_R).quantile(.75))
        }
        for ds,g in d[(d.side==sd)&(d.window_min==w)].groupby('dataset'):
            for name,mask in [
              ('BASE',np.ones(len(g),dtype=bool)),
              ('STRONG_DLS',g.dls>=qs['dls_q75']),
              ('STRONG_OI',g.doi>=qs['doi_q75']),
              ('STRONG_REJECT',(-g.price_crowd_R)>=qs['rej_q75']),
              ('ALL_Q50',(g.dls>=qs['dls_q50'])&(g.doi>=qs['doi_q50'])&((-g.price_crowd_R)>=qs['rej_q50'])),
              ('ALL_Q75',(g.dls>=qs['dls_q75'])&(g.doi>=qs['doi_q75'])&((-g.price_crowd_R)>=qs['rej_q75']))
            ]:
                h=g[mask]
                if len(h)==0: continue
                rows.append({'dataset':ds,'side':'BUY' if sd>0 else 'SELL','window_min':w,'state':name,'N':len(h),
                             **qs,'MFE60':float(h.mfe_60m.mean()),'MAE60':float(h.mae_60m.mean()),
                             'TP1R':float(h.tp1p0R.mean()),'TP1p5R':float(h.tp1p5R.mean()),
                             'TP2R':float(h.tp2p0R.mean()),'TP2p5R':float(h.tp2p5R.mean())})
    return pd.DataFrame(rows)

def main():
    flow,periods=load()
    raw=pd.concat([event_frame(label,p,flow) for label,p in periods.items()],ignore_index=True)
    dd=dedup(raw)
    raw.to_csv(OUT/'lab089_events.csv',index=False)
    dd.to_csv(OUT/'dedup_events.csv',index=False)

    sraw=bucket_summary(raw,'OVERLAP'); sdd=bucket_summary(dd,'DEDUP_30M')
    summ=pd.concat([sraw,sdd],ignore_index=True)
    summ.to_csv(OUT/'window_summary.csv',index=False)
    q=quantile_decomp(dd); q.to_csv(OUT/'strength_decomposition.csv',index=False)

    # Rank windows on historical dedup by TP2.0 and TP2.5, then report same in forward.
    rank=[]
    for sd in ['BUY','SELL']:
        h=sdd[(sdd.dataset=='historical')&(sdd.side==sd)].sort_values(['TP2.0R','TP2.5R'],ascending=False)
        for n,(_,r) in enumerate(h.iterrows(),1):
            f=sdd[(sdd.dataset=='forward_2026')&(sdd.side==sd)&(sdd.window_min==r.window_min)]
            rank.append({'side':sd,'rank_train':n,'window_min':r.window_min,'N_hist':int(r.N),
                         'TP2_hist':float(r['TP2.0R']),'TP2p5_hist':float(r['TP2.5R']),
                         'MFE60_hist':float(r.MFE60),
                         'N_2026':int(f.N.iloc[0]) if len(f) else 0,
                         'TP2_2026':float(f['TP2.0R'].iloc[0]) if len(f) else np.nan,
                         'TP2p5_2026':float(f['TP2.5R'].iloc[0]) if len(f) else np.nan,
                         'MFE60_2026':float(f.MFE60.iloc[0]) if len(f) else np.nan})
    rank=pd.DataFrame(rank); rank.to_csv(OUT/'window_ranking.csv',index=False)

    result={'lab':'LAB089_EXTREME_LS_TRAP_TRIGGER',
            'trigger':'|Z|>=2.5 AND directional ΔLS>0 AND ΔOI>+0.02% AND price response against crowd < -0.10 ATR',
            'windows_min':WINDOWS,'cooldown_min':COOLDOWN_MIN,
            'targets_R':TARGETS,'N_raw':int(len(raw)),'N_dedup':int(len(dd)),
            'window_ranking':rank.to_dict('records'),
            'limitations':['Primary inference uses 30m non-overlap dedup events.',
                           '2026 Mar-Aug is reused diagnostic data, not pristine OOS.',
                           'No taker/burst/H1-H4 features in this LAB.',
                           'No production promotion without stable historical and 2026 direction.']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB089 — EXTREME LS × ΔLS RISING × OI UP × PRICE AGAINST CROWD\n\n'+json.dumps(result,indent=2,default=float)+'\n\n## Window summary\n\n'+summ.to_markdown(index=False)+'\n\n## Strength decomposition\n\n'+q.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
