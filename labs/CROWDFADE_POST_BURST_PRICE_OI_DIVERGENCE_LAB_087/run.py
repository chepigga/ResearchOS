from pathlib import Path
import json, importlib.util, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p79=ROOT.parent/'CROWDFADE_NLE_2026_FAILURE_DECOMP_LAB_079'/'run.py'
sp=importlib.util.spec_from_file_location('l79',p79)
l79=importlib.util.module_from_spec(sp); sp.loader.exec_module(l79)
l79.DATA=DATA; l79.OUT=OUT
l78=l79.l78; l77=l79.l77; l54=l79.l54; l43=l79.l43
l78.DATA=DATA; l77.DATA=DATA; l54.DATA=DATA; l43.DATA=DATA; l78.lab53.DATA=DATA

OI_FLAT=0.0002
HORIZON_MIN=15
PRICE_CONT_R=0.0

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:return {'N':0,'EV_R':np.nan,'WR':np.nan,'PF':np.nan,'SumR':0.0,'MaxDD_R':np.nan}
    w=x[x>0].sum(); l=-x[x<0].sum()
    eq=np.cumsum(x); peak=np.maximum.accumulate(np.r_[0,eq]); dd=peak[1:]-eq
    return {'N':len(x),'EV_R':float(x.mean()),'WR':float((x>0).mean()),
            'PF':float(w/l) if l>0 else np.nan,'SumR':float(x.sum()),
            'MaxDD_R':float(dd.max()) if len(dd) else 0.0}

def asof(a,q): return np.searchsorted(a,q,'right')-1

def build():
    d,ctx,flow,micro=l79.lineage()
    d=d[d.mech_15=='NEW_LONG_EXPANSION'].copy().reset_index(drop=True)
    d=l79.post1r(d,ctx,flow,micro)
    d=d[d.time_to_1R_min.notna()].copy().reset_index(drop=True)
    tr=d[d.period=='historical']
    px_q75=float(tr.p1_px15.quantile(.75))
    d['PRICE_BURST']=d.p1_px15>=px_q75
    return d,ctx,flow,px_q75

def add_era(d):
    dt=pd.to_datetime(d.entry_ts,unit='s',utc=True).dt.tz_convert(None)
    d['entry_dt']=dt; y=dt.dt.year
    d['era']=np.select([y<=2024,y==2025,y==2026],['2021_2024','2025','2026'],default='OTHER')
    return d

def add_state(d,ctx,flow):
    d['post15_price_R']=np.nan; d['post15_oi']=np.nan; d['state']='NO_BURST'; d['confirm_ts']=np.nan
    ft=flow.ts.to_numpy(np.int64); oi=flow.oi.to_numpy(float)
    for per,p in ctx.items():
        ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
        for i in d.index[(d.period==per)&d.PRICE_BURST]:
            r=d.loc[i]; k=int(r.entry_k); ep=float(C5[k]); atr=float(A5[k]); rdist=1.5*atr
            t1=int(r.entry_ts+round(float(r.time_to_1R_min)*60))
            tc=t1+HORIZON_MIN*60
            j0=asof(ts,t1); j1=asof(ts,tc)
            if j0<0 or j1<0: continue
            pr=(float(C[j1])-float(C[j0]))/rdist
            f0=asof(ft,t1); f1=asof(ft,tc)
            oi_ch=np.nan
            if f0>=0 and f1>=0 and oi[f0]>0: oi_ch=oi[f1]/oi[f0]-1.0
            d.at[i,'post15_price_R']=pr; d.at[i,'post15_oi']=oi_ch; d.at[i,'confirm_ts']=tc
            if pr<=PRICE_CONT_R:
                st='PRICE_FAIL'
            else:
                if not np.isfinite(oi_ch): st='PRICE_CONT_OI_NA'
                elif oi_ch < -OI_FLAT: st='PRICE_CONT_OI_DOWN'
                elif oi_ch > OI_FLAT: st='PRICE_CONT_OI_UP'
                else: st='PRICE_CONT_OI_FLAT'
            d.at[i,'state']=st
    return d

def apply_floor(row,p,floorR):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    k=int(row.entry_k); ep=float(C5[k]); atr=float(A5[k]); rdist=1.5*atr
    tc=int(row.confirm_ts); stop=ep+floorR*rdist
    jc=asof(ts,tc)
    if jc<0:return float(row.R)
    cur=float(C[jc])
    if cur<=stop:return (cur-ep)/rdist
    rr,ex,reason=l78.lab53.manage_cf191g(dt5,H5,L5,C5,k,1,ep,atr)
    exit_ts=int(dt5[ex]); e=np.searchsorted(ts,exit_ts,'right'); s=jc+1
    if e>s and np.nanmin(L[s:e])<=stop:return floorR
    return float(row.R)

def add_management(d,ctx):
    out=[]
    for i,r in d.iterrows():
        base=float(r.R)
        if not bool(r.PRICE_BURST) or not np.isfinite(r.confirm_ts):
            out.append(base); continue
        if r.state=='PRICE_CONT_OI_UP':
            out.append(apply_floor(r,ctx[r.period],1.0))
        elif r.state=='PRICE_FAIL':
            out.append(apply_floor(r,ctx[r.period],1.0))
        elif r.state=='PRICE_CONT_OI_FLAT':
            out.append(apply_floor(r,ctx[r.period],0.75))
        else:
            out.append(base)
    d['R_STATE_MACHINE']=np.asarray(out,float)
    return d

def summarize_states(d):
    rows=[]
    for era,g in d.groupby('era'):
        if era=='OTHER':continue
        b=g[g.PRICE_BURST]
        for st,h in b.groupby('state'):
            m=metrics(h.R)
            rows.append({'era':era,'state':st,**m,
                         'giveback1R':float(h.giveback_after_1R.mean()),
                         'reach2R':float(h.time_to_2R_min.notna().mean()),
                         'reach3R':float(h.time_to_3R_min.notna().mean()),
                         'priceR_mean':float(h.post15_price_R.mean()),
                         'oi15_mean':float(h.post15_oi.mean())})
    return pd.DataFrame(rows)

def summarize_strategy(d):
    rows=[]
    for era,g in d.groupby('era'):
        if era=='OTHER':continue
        for name,col in [('CURRENT','R'),('STATE_MACHINE','R_STATE_MACHINE')]:
            rows.append({'era':era,'strategy':name,**metrics(g[col])})
    return pd.DataFrame(rows)

def main():
    d,ctx,flow,pxq=build(); d=add_era(d); d=add_state(d,ctx,flow); d=add_management(d,ctx)
    st=summarize_states(d); sm=summarize_strategy(d)
    d.to_csv(OUT/'lab087_events.csv',index=False); st.to_csv(OUT/'state_metrics.csv',index=False); sm.to_csv(OUT/'strategy_metrics.csv',index=False)

    # burst-only summary
    br=[]
    for era,g in d[d.PRICE_BURST].groupby('era'):
        if era=='OTHER':continue
        for name,col in [('CURRENT','R'),('STATE_MACHINE','R_STATE_MACHINE')]:
            br.append({'era':era,'strategy':name,**metrics(g[col])})
    br=pd.DataFrame(br); br.to_csv(OUT/'burst_only_strategy_metrics.csv',index=False)

    summary={'lab':'LAB087_POST_BURST_PRICE_CONTINUATION_OI_DIVERGENCE',
             'burst_threshold_price15_train_q75':pxq,'horizon_min':HORIZON_MIN,
             'price_continue_rule':'post-burst 15m close change > 0R',
             'oi_flat_band':OI_FLAT,
             'states':['PRICE_FAIL','PRICE_CONT_OI_DOWN','PRICE_CONT_OI_FLAT','PRICE_CONT_OI_UP'],
             'management':'after 15m confirmation: OI_UP or PRICE_FAIL -> causal +1R floor; OI_FLAT -> +0.75R floor; OI_DOWN -> current runner',
             'state_metrics':st.to_dict('records'),
             'strategy_metrics':sm.to_dict('records'),
             'burst_strategy_metrics':br.to_dict('records'),
             'note':'Diagnostic only; same state definitions applied unchanged to 2021-24, 2025 and 2026.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB087 — POST_BURST PRICE CONTINUATION × OI DIVERGENCE\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## States\n\n'+st.to_markdown(index=False)+'\n\n## Strategy\n\n'+sm.to_markdown(index=False)+'\n\n## Burst only\n\n'+br.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
