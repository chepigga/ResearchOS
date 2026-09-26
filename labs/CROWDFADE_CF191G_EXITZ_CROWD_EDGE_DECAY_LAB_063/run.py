from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p54=ROOT.parent/'CROWDFADE_CF191G_CAUSAL_REGIME_IMPULSE_MODEL_LAB_054'/'run.py'
sp=importlib.util.spec_from_file_location('lab54',p54)
lab54=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab54)
lab53=lab54.lab53; lab43=lab54.lab43
lab54.DATA=DATA; lab53.DATA=DATA; lab43.DATA=DATA

EXPECT={
 'historical':{'N':5297,'SumR':700.3704107793633},
 'forward_2026':{'N':544,'SumR':35.49784078156513},
}
H=[15,30,60,120]
REASON={1:'INITIAL_STOP',2:'PROFIT_STOP',4:'TIME_EXIT'}

def metrics(a): return lab43.metrics(np.asarray(a,float))

def state(x):
    if not np.isfinite(x): return 'NA'
    if x>=0.75:return 'STRONG_PERSIST'
    if x>0:return 'WEAK_PERSIST'
    if x<=-0.75:return 'OPP_EXTREME'
    return 'SIGN_FLIP'

def build(label,p):
    df=lab54.extract_cf191g_events(p)
    rr,st,side,sk=lab53.sim_cf191g(*p,False)
    exp=EXPECT[label]
    if len(df)!=exp['N'] or abs(float(df.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'parity {label} {len(df)} {df.R.sum()}')
    df=lab54.add_targets(df,p)

    dt5,H5,L5,C5,Z5,A5=p[5],p[6],p[7],p[8],p[9],p[10]
    entry_edge=[];exit_ts=[];exit_reason=[]
    vals={h:[] for h in H}; states={h:[] for h in H}
    t_below=[];t_flip=[];t_opp=[]

    for _,r in df.iterrows():
        k=int(r.entry_k); side=int(r.side); et=int(r.entry_ts); entry=float(r.entry_price); atr=float(r.atr)
        e0=-side*float(Z5[k]); entry_edge.append(e0)
        rr0,ex,reason=lab53.manage_cf191g(dt5,H5,L5,C5,k,side,entry,atr)
        xt=int(dt5[int(ex)]); exit_ts.append(xt); exit_reason.append(REASON.get(int(reason),str(reason)))

        for h in H:
            target=et+h*60
            q=np.searchsorted(dt5,target,'left')
            if target>=xt or q>=len(dt5) or int(dt5[q])!=target:
                vals[h].append(np.nan);states[h].append('NOT_ACTIVE')
            else:
                ce=-side*float(Z5[q])
                vals[h].append(ce);states[h].append(state(ce))

        b=np.nan;f=np.nan;o=np.nan
        end=min(int(ex),np.searchsorted(dt5,et+6*3600,'right')-1)
        for q in range(k+1,end+1):
            ce=-side*float(Z5[q]); mins=(int(dt5[q])-et)/60.0
            if not np.isfinite(b) and ce<0.75:b=mins
            if not np.isfinite(f) and ce<=0:f=mins
            if not np.isfinite(o) and ce<=-0.75:o=mins
        t_below.append(b);t_flip.append(f);t_opp.append(o)

    df['entry_crowd_edge']=entry_edge
    df['control_exit_ts']=exit_ts;df['control_exit_reason']=exit_reason
    for h in H:
        df[f'crowd_edge_{h}m']=vals[h];df[f'exitz_state_{h}m']=states[h]
    df['first_below_0p75_min']=t_below
    df['first_sign_flip_min']=t_flip
    df['first_opp_extreme_min']=t_opp
    df['period']=label
    return df

def desc(g,period,h,state_name):
    m=metrics(g.R.to_numpy(float))
    return {
      'period':period,'horizon_min':h,'state':state_name,'N':len(g),
      'EV_R':m.get('EV',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),
      'WR':m.get('WR',np.nan),'MaxDD_R':m.get('MaxDD_R',np.nan),
      'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
      'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
      'mean_ret60':float(g.ret_60m.mean()) if len(g) else np.nan,
      'initial_stop_share':float((g.control_exit_reason=='INITIAL_STOP').mean()) if len(g) else np.nan,
      'right_tail_ge_1p5R':float((g.R>=1.5).mean()) if len(g) else np.nan,
    }

def main():
    ft,fz=lab43.load_flow(); hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    dh=build('historical',hist);df=build('forward_2026',fwd)
    events=pd.concat([dh,df],ignore_index=True);events.to_csv(OUT/'exitz_events.csv',index=False)

    rows=[]
    for period,d in [('historical',dh),('forward_2026',df)]:
        for h in H:
            col=f'exitz_state_{h}m'
            for s in ['STRONG_PERSIST','WEAK_PERSIST','SIGN_FLIP','OPP_EXTREME','NOT_ACTIVE']:
                rows.append(desc(d[d[col]==s],period,h,s))
    sm=pd.DataFrame(rows);sm.to_csv(OUT/'exitz_state_map.csv',index=False)

    checks={}
    for period in ['historical','forward_2026']:
        a=sm[(sm.period==period)&(sm.horizon_min==30)&(sm.state=='STRONG_PERSIST')].iloc[0]
        b=sm[(sm.period==period)&(sm.horizon_min==30)&(sm.state=='SIGN_FLIP')].iloc[0]
        o=sm[(sm.period==period)&(sm.horizon_min==30)&(sm.state=='OPP_EXTREME')].iloc[0]
        checks[period]={
          'strong_N':int(a.N),'sign_flip_N':int(b.N),'opp_extreme_N':int(o.N),
          'strong_EV_gt_signflip':bool(a.EV_R>b.EV_R) if np.isfinite(a.EV_R) and np.isfinite(b.EV_R) else False,
          'strong_PF_gt_signflip':bool(a.PF>b.PF) if np.isfinite(a.PF) and np.isfinite(b.PF) else False,
          'strong_MFE60_gt_signflip':bool(a.mean_mfe60>b.mean_mfe60) if np.isfinite(a.mean_mfe60) and np.isfinite(b.mean_mfe60) else False,
          'strong_MAE60_lt_signflip':bool(a.mean_mae60<b.mean_mae60) if np.isfinite(a.mean_mae60) and np.isfinite(b.mean_mae60) else False,
          'opp_extreme_not_better_EV_than_strong':bool(o.EV_R<=a.EV_R) if np.isfinite(o.EV_R) and np.isfinite(a.EV_R) else False,
        }
    primary=all(all(v for k,v in d.items() if not k.endswith('_N')) for d in checks.values())

    result={'lab':'LAB063_EXITZ_CROWD_EDGE_DECAY','primary_horizon_min':30,'checks':checks,
            'primary_pattern_repeats_both_periods':bool(primary),
            'limitations':['Diagnostic only; no stateful ExitZ action tested.',
                           'Only states while the frozen control position remains open are classified.',
                           'BTCUSDT only; 2026 Mar-Aug is reused shadow/stress, not pristine OOS.']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB063 — EXITZ / CROWD-EDGE DECAY MAP','',
      'Diagnostic only. CF191g entry and management unchanged.','',
      '## State map','',sm.to_markdown(index=False),'',
      '## Primary 30m checks','',json.dumps(checks,indent=2),'',
      f'Primary pattern repeats both periods: **{primary}**'
    ]))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
