from pathlib import Path
import json, importlib.util, numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
p=ROOT.parent/'CROWDFADE_BUY_FLOW_MECHANISM_PATH_LAB_078'/'run.py'
s=importlib.util.spec_from_file_location('l78',p); l78=importlib.util.module_from_spec(s); s.loader.exec_module(l78)
l78.DATA=DATA; l78.OUT=OUT
l77=l78.lab77; l54=l78.lab54; l43=l78.lab43
l77.DATA=DATA; l54.DATA=DATA; l78.lab53.DATA=DATA; l43.DATA=DATA
ENTRY=['oi_ch15','taker_delta15','price_ch15','atr_pct','ret15_atr','ret30_atr','ret60_atr','eff30','eff60','with_h1','with_h4','with_aligned']
POST=['p1_oi5','p1_oi15','p1_taker5','p1_taker15','p1_px5','p1_px15']

def metrics(x): return l43.metrics(np.asarray(x,float))
def ai(a,q): return np.searchsorted(a,q,'right')-1

def lineage():
    flow=l77.load_flow_raw(); micro=l77.load_micro(); ft,fz=l43.load_flow()
    hr=l43.load_hist(); sr=l43.load_sec()
    hp=l43.prep(hr,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fp=l43.prep(sr,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    out=[]; ctx={}
    for lab,p in [('historical',hp),('forward_2026',fp)]:
        d=l54.build_dataset(lab,p,l54.load_flow_meta(),l54.load_1m_microstructure())
        d=d[d.side==1].copy().reset_index(drop=True)
        d=l77.add_flow_5_15(d,flow,micro); d=l77.add_exit_timing(d,p); d=l78.add_price_returns(d,p); d=l78.add_mechanisms(d); d=l78.path_stats_and_fixed_tp(d,p)
        d['period']=lab; out.append(d); ctx[lab]=p
    return pd.concat(out,ignore_index=True),ctx,flow,micro

def post1r(d,ctx,flow,micro):
    for c in POST:d[c]=np.nan
    ft=flow.ts.to_numpy(np.int64); oi=flow.oi.to_numpy(float); mt=micro.ts.to_numpy(np.int64)
    t5=micro.taker_delta5.to_numpy(float); t15=micro.taker_delta15.to_numpy(float)
    for per,p in ctx.items():
        ts,O,H,L,C,*_=p
        for i in d.index[d.period==per]:
            r=d.loc[i]
            if not np.isfinite(r.time_to_1R_min): continue
            t=int(r.entry_ts+round(r.time_to_1R_min*60)); fi=ai(ft,t); mi=ai(mt,t)
            if fi>=0:
                for w,c in [(5,'p1_oi5'),(15,'p1_oi15')]:
                    j=ai(ft,t-w*60)
                    if j>=0 and oi[j]>0:d.at[i,c]=oi[fi]/oi[j]-1
            if mi>=0:d.at[i,'p1_taker5']=t5[mi]; d.at[i,'p1_taker15']=t15[mi]
            k=ai(ts,t)
            for w,c in [(5,'p1_px5'),(15,'p1_px15')]:
                j=ai(ts,t-w*60)
                if j>=0 and k>=0 and C[j]>0:d.at[i,c]=C[k]/C[j]-1
    return d

def contrast(train,test,features,label):
    sd={f:train[f].std(ddof=0) for f in features}; rows=[]
    for per,d in [('historical',train),('forward_2026',test)]:
        for f in features:
            a=d[d[label]==1][f].dropna(); b=d[d[label]==0][f].dropna()
            if len(a)<3 or len(b)<3 or not np.isfinite(sd[f]) or sd[f]<=0:continue
            rows.append([per,f,len(a),len(b),a.mean(),b.mean(),(a.mean()-b.mean())/sd[f]])
    return pd.DataFrame(rows,columns=['period','feature','N_bad','N_good','bad_mean','good_mean','std_diff_bad_minus_good'])

def quartiles(train,test,features,label):
    rows=[]
    for f in features:
        x=train[f].dropna()
        if len(x)<40 or x.nunique()<8:continue
        q=np.unique(np.quantile(x,[0,.25,.5,.75,1]))
        if len(q)<4:continue
        for per,d in [('historical',train),('forward_2026',test)]:
            z=d.dropna(subset=[f]).copy(); z['bin']=pd.cut(z[f],q,include_lowest=True,duplicates='drop')
            for b,g in z.groupby('bin',observed=True):
                m=metrics(g.R)
                rows.append([per,f,str(b),len(g),m.get('EV',np.nan),m.get('PF',np.nan),g[label].mean(),g.time_to_2R_min.notna().mean()])
    return pd.DataFrame(rows,columns=['period','feature','bin','N','EV_R','PF','bad_rate','reach2R'])

def thresholds(train,test):
    rows=[]
    for f in ['oi_ch15','taker_delta15','price_ch15','atr_pct','eff60']:
        x=train[f].dropna()
        for q,side in [(.25,'LOW'),(.75,'HIGH')]:
            th=x.quantile(q)
            for per,d in [('historical',train),('forward_2026',test)]:
                mask=d[f]<=th if side=='LOW' else d[f]>=th
                for st,mk in [('PASS',mask),('REST',~mask)]:
                    g=d[mk & d[f].notna()]
                    if len(g):
                        m=metrics(g.R); rows.append([f,side,q,th,per,st,len(g),m.get('EV',np.nan),m.get('PF',np.nan),g.entry_fail.mean(),g.giveback_after_1R.mean()])
    return pd.DataFrame(rows,columns=['feature','side','q','threshold','period','state','N','EV_R','PF','entry_fail','giveback1R'])

def main():
    d,ctx,flow,micro=lineage(); d=d[d.mech_15=='NEW_LONG_EXPANSION'].copy().reset_index(drop=True); d=post1r(d,ctx,flow,micro)
    d['entry_fail']=(d.R<=0).astype(int); d['post1r_fail']=np.where(d.time_to_1R_min.notna(),d.giveback_after_1R,np.nan)
    h=d[d.period=='historical'].copy(); f=d[d.period=='forward_2026'].copy()
    h1=h[h.time_to_1R_min.notna()].copy(); f1=f[f.time_to_1R_min.notna()].copy(); h1['post1r_fail']=h1.giveback_after_1R.astype(int); f1['post1r_fail']=f1.giveback_after_1R.astype(int)
    ce=contrast(h,f,ENTRY,'entry_fail'); cp=contrast(h1,f1,POST,'post1r_fail'); qe=quartiles(h,f,ENTRY,'entry_fail'); qp=quartiles(h1,f1,POST,'post1r_fail'); th=thresholds(h,f)
    d.to_csv(OUT/'nle_events_enriched.csv',index=False); ce.to_csv(OUT/'entry_feature_contrast.csv',index=False); cp.to_csv(OUT/'post1r_feature_contrast.csv',index=False); qe.to_csv(OUT/'entry_train_quartiles.csv',index=False); qp.to_csv(OUT/'post1r_train_quartiles.csv',index=False); th.to_csv(OUT/'train_thresholds_to_2026.csv',index=False)
    e26=ce[ce.period=='forward_2026'].assign(absd=lambda x:x.std_diff_bad_minus_good.abs()).sort_values('absd',ascending=False)
    p26=cp[cp.period=='forward_2026'].assign(absd=lambda x:x.std_diff_bad_minus_good.abs()).sort_values('absd',ascending=False)
    summary={'lab':'LAB079_NLE_2026_FAILURE_DECOMP','N_hist':len(h),'N_2026':len(f),'N_hist_1R':len(h1),'N_2026_1R':len(f1),'EV_hist':float(h.R.mean()),'EV_2026':float(f.R.mean()),'entry_fail_hist':float(h.entry_fail.mean()),'entry_fail_2026':float(f.entry_fail.mean()),'giveback1R_hist':float(h1.post1r_fail.mean()),'giveback1R_2026':float(f1.post1r_fail.mean()),'top_entry_2026':e26.head(8).to_dict('records'),'top_post1r_2026':p26.head(8).to_dict('records'),'anti_curve_fit':'Quartiles/thresholds derived on 2021-2025 only; applied unchanged to 2026. No production rule promoted.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB079 — NLE 2026 FAILURE DECOMPOSITION\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## Entry contrasts\n\n'+e26.to_markdown(index=False)+'\n\n## Post-1R contrasts\n\n'+p26.to_markdown(index=False)+'\n\n## TRAIN thresholds → 2026\n\n'+th.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())
if __name__=='__main__': main()
