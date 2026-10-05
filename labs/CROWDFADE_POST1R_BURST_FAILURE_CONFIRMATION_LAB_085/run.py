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

WINDOWS=[5,10,15]
RESP_THR_R=0.25

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:return {'N':0,'EV_R':np.nan,'WR':np.nan,'PF':np.nan,'SumR':0.0,'MaxDD_R':np.nan}
    w=x[x>0].sum(); l=-x[x<0].sum()
    eq=np.cumsum(x); peak=np.maximum.accumulate(np.r_[0,eq]); dd=peak[1:]-eq
    return {'N':len(x),'EV_R':float(x.mean()),'WR':float((x>0).mean()),
            'PF':float(w/l) if l>0 else np.nan,'SumR':float(x.sum()),
            'MaxDD_R':float(dd.max()) if len(dd) else 0.0}

def build():
    d,ctx,flow,micro=l79.lineage()
    d=d[d.mech_15=='NEW_LONG_EXPANSION'].copy().reset_index(drop=True)
    d=l79.post1r(d,ctx,flow,micro)
    d=d[d.time_to_1R_min.notna()].copy().reset_index(drop=True)
    return d,ctx

def add_era(d):
    dt=pd.to_datetime(d.entry_ts,unit='s',utc=True).dt.tz_convert(None)
    d['entry_dt']=dt
    y=dt.dt.year
    d['era']=np.select([y<=2024,y==2025,y==2026],['2021_2024','2025','2026'],default='OTHER')
    return d

def add_burst_response(d,ctx,px_q75):
    d['PRICE_BURST']=d.p1_px15>=px_q75
    for w in WINDOWS:
        d[f'resp{w}_R']=np.nan
        d[f'state{w}']='NO_BURST'
        d[f'confirm_ts_{w}']=np.nan
    for per,p in ctx.items():
        ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
        idx=d.index[d.period==per]
        for i in idx:
            r=d.loc[i]
            if not bool(r.PRICE_BURST): continue
            k=int(r.entry_k); ep=float(C5[k]); atr=float(A5[k]); rdist=1.5*atr
            t1=int(r.entry_ts+round(float(r.time_to_1R_min)*60))
            j1=np.searchsorted(ts,t1,'right')-1
            if j1<0: continue
            p1=float(C[j1])
            for w in WINDOWS:
                tc=t1+w*60
                jc=np.searchsorted(ts,tc,'right')-1
                if jc<0: continue
                resp=(float(C[jc])-p1)/rdist
                d.at[i,f'resp{w}_R']=resp
                d.at[i,f'confirm_ts_{w}']=tc
                if resp>=RESP_THR_R: st='CONTINUE'
                elif resp<=-RESP_THR_R: st='REJECT'
                else: st='STALL'
                d.at[i,f'state{w}']=st
    return d

def apply_floor_after_confirm(row,p,confirm_ts,floorR):
    # Causal: rule becomes active only after confirmation timestamp.
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    k=int(row.entry_k); ep=float(C5[k]); atr=float(A5[k]); rdist=1.5*atr
    stop=ep+floorR*rdist
    jc=np.searchsorted(ts,int(confirm_ts),'right')-1
    if jc<0:return float(row.R)
    cur=float(C[jc])
    # If price already below desired floor at confirmation, cannot retroactively fill there.
    if cur<=stop:
        return (cur-ep)/rdist
    # Determine original exit time from frozen manager.
    rr,ex,reason=l78.lab53.manage_cf191g(dt5,H5,L5,C5,k,1,ep,atr)
    exit_ts=int(dt5[ex])
    e=np.searchsorted(ts,exit_ts,'right')
    s=jc+1
    if e>s and np.nanmin(L[s:e])<=stop:
        return floorR
    return float(row.R)

def apply_exit_at_confirm(row,p,confirm_ts):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    k=int(row.entry_k); ep=float(C5[k]); atr=float(A5[k]); rdist=1.5*atr
    jc=np.searchsorted(ts,int(confirm_ts),'right')-1
    if jc<0:return float(row.R)
    return (float(C[jc])-ep)/rdist

def management(d,ctx):
    for w in WINDOWS:
        d[f'R_W{w}_LOCK']=''
        d[f'R_W{w}_EXIT']=''
        vals_lock=[]; vals_exit=[]
        for i,r in d.iterrows():
            base=float(r.R)
            if not bool(r.PRICE_BURST) or not np.isfinite(r[f'confirm_ts_{w}']):
                vals_lock.append(base); vals_exit.append(base); continue
            p=ctx[r.period]; st=r[f'state{w}']; tc=int(r[f'confirm_ts_{w}'])
            # Strategy A: CONTINUE=current; STALL=floor +0.75R; REJECT=floor +1R.
            if st=='STALL':
                a=apply_floor_after_confirm(r,p,tc,0.75)
            elif st=='REJECT':
                a=apply_floor_after_confirm(r,p,tc,1.0)
            else:
                a=base
            # Strategy B: CONTINUE=current; STALL=floor +0.75R; REJECT=market exit at confirmation.
            if st=='STALL':
                b=apply_floor_after_confirm(r,p,tc,0.75)
            elif st=='REJECT':
                b=apply_exit_at_confirm(r,p,tc)
            else:
                b=base
            vals_lock.append(a); vals_exit.append(b)
        d[f'R_W{w}_LOCK']=np.asarray(vals_lock,float)
        d[f'R_W{w}_EXIT']=np.asarray(vals_exit,float)
    return d

def state_summary(d):
    rows=[]
    for era,g in d.groupby('era'):
        if era=='OTHER': continue
        for w in WINDOWS:
            for st,h in g[g.PRICE_BURST].groupby(f'state{w}'):
                m=metrics(h.R)
                rows.append({'era':era,'window_min':w,'state':st,**m,
                             'giveback1R':float(h.giveback_after_1R.mean()),
                             'reach2R':float(h.time_to_2R_min.notna().mean()),
                             'reach3R':float(h.time_to_3R_min.notna().mean()),
                             'respR_mean':float(h[f'resp{w}_R'].mean())})
    return pd.DataFrame(rows)

def strategy_summary(d):
    rows=[]
    for era,g in d.groupby('era'):
        if era=='OTHER': continue
        cols=[('CURRENT','R')]
        for w in WINDOWS:
            cols += [(f'W{w}_LOCK',f'R_W{w}_LOCK'),(f'W{w}_EXIT',f'R_W{w}_EXIT')]
        for name,col in cols:
            m=metrics(g[col])
            rows.append({'era':era,'strategy':name,**m})
    return pd.DataFrame(rows)

def burst_only_strategy(d):
    rows=[]
    for era,g in d.groupby('era'):
        if era=='OTHER':continue
        b=g[g.PRICE_BURST]
        for name,col in [('CURRENT','R')]+[(f'W{w}_LOCK',f'R_W{w}_LOCK') for w in WINDOWS]+[(f'W{w}_EXIT',f'R_W{w}_EXIT') for w in WINDOWS]:
            m=metrics(b[col]); rows.append({'era':era,'strategy':name,**m})
    return pd.DataFrame(rows)

def main():
    d,ctx=build(); d=add_era(d)
    train=d[d.period=='historical']
    px_q75=float(train.p1_px15.quantile(.75))
    d=add_burst_response(d,ctx,px_q75)
    d=management(d,ctx)
    states=state_summary(d); strat=strategy_summary(d); burst=burst_only_strategy(d)
    d.to_csv(OUT/'lab085_events.csv',index=False)
    states.to_csv(OUT/'response_states.csv',index=False)
    strat.to_csv(OUT/'all_nle_strategy_metrics.csv',index=False)
    burst.to_csv(OUT/'burst_only_strategy_metrics.csv',index=False)

    # Choose candidate by 2021-24 only; report 2025 and 2026 unchanged.
    h=strat[strat.era=='2021_2024'].copy()
    base=float(h[h.strategy=='CURRENT'].EV_R.iloc[0])
    h['delta_ev']=h.EV_R-base
    cand=h[h.strategy!='CURRENT'].sort_values(['delta_ev','MaxDD_R'],ascending=[False,True])
    selected=str(cand.iloc[0].strategy) if len(cand) else None
    def row(era,name):
        z=strat[(strat.era==era)&(strat.strategy==name)]
        return z.iloc[0].to_dict() if len(z) else None
    summary={
      'lab':'LAB085_POST1R_BURST_FAILURE_CONFIRMATION',
      'price_burst_threshold_train_q75':px_q75,
      'response_definition':{'CONTINUE':f'>= +{RESP_THR_R}R after confirmation window','REJECT':f'<= -{RESP_THR_R}R','STALL':'between thresholds'},
      'windows_min':WINDOWS,
      'management_A':'CONTINUE current runner; STALL causal +0.75R floor; REJECT causal +1R floor',
      'management_B':'CONTINUE current runner; STALL causal +0.75R floor; REJECT market exit at confirmation',
      'historical_selected_candidate':selected,
      'selected_2021_2024':row('2021_2024',selected) if selected else None,
      'selected_2025':row('2025',selected) if selected else None,
      'selected_2026':row('2026',selected) if selected else None,
      'current_2026':row('2026','CURRENT'),
      'note':'All response states use only information available at +5/+10/+15m after first +1R passage. Floors activate only after confirmation; if price is already below desired floor, replay exits at contemporaneous close rather than granting an impossible retroactive fill.'
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB085 — POST_1R BURST FAILURE CONFIRMATION\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## Response states\n\n'+states.to_markdown(index=False)+'\n\n## All NLE strategy metrics\n\n'+strat.to_markdown(index=False)+'\n\n## Burst-only strategy metrics\n\n'+burst.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
