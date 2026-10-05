from pathlib import Path
import json, importlib.util, numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
p79=ROOT.parent/'CROWDFADE_NLE_2026_FAILURE_DECOMP_LAB_079'/'run.py'
sp=importlib.util.spec_from_file_location('l79',p79); l79=importlib.util.module_from_spec(sp); sp.loader.exec_module(l79)
l79.DATA=DATA; l79.OUT=OUT
l78=l79.l78; l77=l79.l77; l54=l79.l54; l43=l79.l43
l78.DATA=DATA; l77.DATA=DATA; l54.DATA=DATA; l43.DATA=DATA; l78.lab53.DATA=DATA
LOCKS=[0.5,0.75,1.0]
def metrics(x): return l43.metrics(np.asarray(x,float))
def build():
    d,ctx,flow,micro=l79.lineage(); d=d[d.mech_15=='NEW_LONG_EXPANSION'].copy().reset_index(drop=True); d=l79.post1r(d,ctx,flow,micro)
    return d,ctx
def train_thresholds(h1):
    return {
      'oi15_q75':float(h1.p1_oi15.quantile(.75)),
      'px15_q75':float(h1.p1_px15.quantile(.75)),
      'taker5_q75':float(h1.p1_taker5.quantile(.75)),
      'atr_q25':float(h1.atr_pct.quantile(.25)),
      'eff30_med':float(h1.eff30.quantile(.50))
    }
def tag(d,t):
    a=(d.p1_oi15>=t['oi15_q75']).astype(int)
    b=(d.p1_px15>=t['px15_q75']).astype(int)
    c=(d.p1_taker5>=t['taker5_q75']).astype(int)
    burst=a+b+c
    d['burst_score']=burst
    d['EXH_CORE']=(burst>=2)
    d['EXH_REGIME']=d.EXH_CORE & ((d.atr_pct>t['atr_q25']) | (d.eff30<t['eff30_med']))
    d['EXH_STRICT']=d.EXH_CORE & (d.atr_pct>t['atr_q25']) & (d.eff30<t['eff30_med'])
    return d
def lock_counterfactual(d,ctx,state,lockR):
    out=d.R.to_numpy(float).copy()
    for per,p in ctx.items():
        ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
        idx=d.index[(d.period==per)&d[state]&d.time_to_1R_min.notna()]
        for i in idx:
            r=d.loc[i]; k=int(r.entry_k); ep=float(C5[k]); atr=float(A5[k]); t1=int(r.entry_ts+round(r.time_to_1R_min*60))
            rr,ex,reason=l78.lab53.manage_cf191g(dt5,H5,L5,C5,k,1,ep,atr)
            exit_ts=int(dt5[ex]); s=np.searchsorted(ts,t1,'right'); e=np.searchsorted(ts,exit_ts,'right')
            stop=ep+lockR*l78.lab53.SL_ATR*atr
            if e>s and np.nanmin(L[s:e])<=stop: out[i]=lockR
    return out
def summarize(d,col):
    rows=[]
    for per,g in [('historical',d[d.period=='historical']),('forward_2026',d[d.period=='forward_2026'])]:
        m=metrics(g[col]); rows.append({'period':per,'strategy':col,'N':len(g),'EV_R':m.get('EV',np.nan),'WR':m.get('WR',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),'MaxDD_R':m.get('MaxDD_R',np.nan)})
    return rows
def main():
    d,ctx=build(); h1=d[(d.period=='historical')&d.time_to_1R_min.notna()].copy()
    t=train_thresholds(h1); d=tag(d,t)
    states=['EXH_CORE','EXH_REGIME','EXH_STRICT']
    for s in states:
        for lock in LOCKS:
            d[f'{s}_LOCK_{lock:g}R']=lock_counterfactual(d,ctx,s,lock)
    rows=[]
    d['CURRENT']=d.R
    for c in ['CURRENT']+[f'{s}_LOCK_{x:g}R' for s in states for x in LOCKS]:
        rows += summarize(d,c)
    seq=pd.DataFrame(rows); seq.to_csv(OUT/'sequential_equity_metrics.csv',index=False)
    st=[]
    for per,g in d.groupby('period'):
        for s in states:
            z=g[g[s] & g.time_to_1R_min.notna()]
            n=g[g.time_to_1R_min.notna()]
            st.append({'period':per,'state':s,'N_reached1R':len(n),'N_exhaustion':len(z),'exhaustion_rate':len(z)/len(n) if len(n) else np.nan,'current_EV_exhaustion':float(z.R.mean()) if len(z) else np.nan,'giveback_exhaustion':float(z.giveback_after_1R.mean()) if len(z) else np.nan,'current_EV_normal':float(n[~n[s]].R.mean()) if len(n[~n[s]]) else np.nan,'giveback_normal':float(n[~n[s]].giveback_after_1R.mean()) if len(n[~n[s]]) else np.nan})
    st=pd.DataFrame(st); st.to_csv(OUT/'state_quality.csv',index=False)
    # choose only by historical improvement, then report unchanged on 2026
    h=seq[seq.period=='historical'].copy(); base=float(h[h.strategy=='CURRENT'].EV_R.iloc[0]); h['delta_EV_vs_current']=h.EV_R-base
    candidates=h[h.strategy!='CURRENT'].sort_values(['delta_EV_vs_current','MaxDD_R'],ascending=[False,True])
    best=candidates.iloc[0].strategy if len(candidates) else None
    f=seq[seq.period=='forward_2026']; fb=float(f[f.strategy=='CURRENT'].EV_R.iloc[0]); fr=f[f.strategy==best].iloc[0] if best is not None and len(f[f.strategy==best]) else None
    summary={'lab':'LAB080_NLE_EXHAUSTION_AFTER_1R','preregistered_states':{
      'EXH_CORE':'at least 2 of {post1R OI15 >= TRAIN Q75, post1R Price15 >= TRAIN Q75, post1R Taker5 >= TRAIN Q75}',
      'EXH_REGIME':'EXH_CORE and (entry ATR > TRAIN Q25 or entry eff30 < TRAIN median)',
      'EXH_STRICT':'EXH_CORE and entry ATR > TRAIN Q25 and entry eff30 < TRAIN median'
    },'train_thresholds':t,'management_grid':'If exhaustion state is active at +1R, tighten floor to +0.5R/+0.75R/+1.0R; otherwise preserve current runner. Candidate selection uses historical only.','historical_selected_candidate':best,'historical_base_EV':base,'historical_selected_EV':float(candidates.iloc[0].EV_R) if len(candidates) else None,'forward_2026_base_EV':fb,'forward_2026_selected_EV':float(fr.EV_R) if fr is not None else None,'forward_2026_selected_PF':float(fr.PF) if fr is not None else None,'forward_2026_selected_MaxDD_R':float(fr.MaxDD_R) if fr is not None else None,'note':'Diagnostic management LAB only; no production change unless TRAIN-selected rule transfers to 2026 without DD deterioration.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    d.to_csv(OUT/'nle_lab080_events.csv',index=False)
    (OUT/'REPORT.md').write_text('# LAB080 — NLE EXHAUSTION STATE AFTER +1R\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## State quality\n\n'+st.to_markdown(index=False)+'\n\n## Sequential equity metrics\n\n'+seq.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())
if __name__=='__main__': main()
