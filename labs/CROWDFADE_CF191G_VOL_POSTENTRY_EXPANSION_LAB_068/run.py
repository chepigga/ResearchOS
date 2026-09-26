from pathlib import Path
import json, zipfile, importlib.util
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
LB=2016
REASON={1:'INITIAL_STOP',2:'PROFIT_STOP',4:'TIME_EXIT'}
VOL_BUCKETS=['P0_20','P20_40','P40_60','P60_80','P80_100']

def metrics(a):
    return lab43.metrics(np.asarray(a,float))

def vol_bucket(x):
    if not np.isfinite(x): return 'NA'
    if x<0.2:return 'P0_20'
    if x<0.4:return 'P20_40'
    if x<0.6:return 'P40_60'
    if x<0.8:return 'P60_80'
    return 'P80_100'

def load_m1():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,2,3,4])
        raw=pd.to_numeric(q.iloc[:,0],errors='coerce')
        hi=pd.to_numeric(q.iloc[:,1],errors='coerce')
        lo=pd.to_numeric(q.iloc[:,2],errors='coerce')
        cl=pd.to_numeric(q.iloc[:,3],errors='coerce')
        x=pd.DataFrame({'raw_ts':raw,'high':hi,'low':lo,'close':cl}).dropna()
        rr=x.raw_ts.to_numpy(np.int64)
        sec=np.where(rr>10**14,rr//1_000_000,rr//1000)
        x['open_ts']=sec
        x['end_ts']=sec+60
        rows.append(x[['open_ts','end_ts','high','low','close']])
    return pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)

def build_vol_percentile(p):
    C5,A5=p[8],p[10]
    vm=A5/C5
    pct=np.full(len(vm),np.nan)
    for k in range(LB,len(vm)):
        hist=vm[k-LB:k]
        if np.all(np.isfinite(hist)) and np.isfinite(vm[k]):
            pct[k]=float(np.mean(hist<=vm[k]))
    return vm,pct

def path_features(m1,entry_ts,side,entry,atr):
    ends=m1.end_ts.to_numpy(np.int64); hi=m1.high.to_numpy(float); lo=m1.low.to_numpy(float); cl=m1.close.to_numpy(float)
    j=np.searchsorted(ends,int(entry_ts)+60,'left')
    if j>=len(ends) or ends[j]!=int(entry_ts)+60:
        return None
    idx=np.arange(j,j+15)
    if idx[-1]>=len(ends): return None
    expected=np.arange(int(entry_ts)+60,int(entry_ts)+16*60,60)
    if not np.array_equal(ends[idx],expected): return None

    closes=cl[idx]
    steps=np.diff(np.r_[entry,closes])
    expansion=float(side*(closes[-1]-entry)/atr)
    path_abs=float(np.sum(np.abs(steps)))
    eff=float(side*(closes[-1]-entry)/(path_abs+1e-12))
    persist=float(np.mean(side*steps>0))

    def close_at(mins):
        q=np.searchsorted(ends,int(entry_ts)+mins*60,'left')
        if q<len(ends) and ends[q]==int(entry_ts)+mins*60:
            return float(cl[q])
        return np.nan

    c15=float(closes[-1]); c30=close_at(30); c60=close_at(60); c120=close_at(120)
    out={
      'expansion15_atr':expansion,'eff15':eff,'persist15':persist,
      'close15':c15,
      'ret15_to_30_atr':float(side*(c30-c15)/atr) if np.isfinite(c30) else np.nan,
      'ret15_to_60_atr':float(side*(c60-c15)/atr) if np.isfinite(c60) else np.nan,
      'ret15_to_120_atr':float(side*(c120-c15)/atr) if np.isfinite(c120) else np.nan,
    }

    q60=np.searchsorted(ends,int(entry_ts)+60*60,'right')
    post_start=idx[-1]+1
    hh=hi[post_start:q60]; ll=lo[post_start:q60]
    if len(hh):
        if side>0:
            out['post15_mfe_to_60_atr']=float((np.max(hh)-c15)/atr)
            out['post15_mae_to_60_atr']=float((c15-np.min(ll))/atr)
        else:
            out['post15_mfe_to_60_atr']=float((c15-np.min(ll))/atr)
            out['post15_mae_to_60_atr']=float((np.max(hh)-c15)/atr)
    else:
        out['post15_mfe_to_60_atr']=np.nan
        out['post15_mae_to_60_atr']=np.nan

    if expansion>=0.50 and eff>=0.25 and persist>=0.60:
        label='EXPANSION_PERSISTENT'
    elif expansion<=0 or eff<=0:
        label='FAILED_EARLY'
    else:
        label='MIXED'
    out['early_state']=label
    return out

def build(label,p,m1):
    df=lab54.extract_cf191g_events(p)
    exp=EXPECT[label]
    if len(df)!=exp['N'] or abs(float(df.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'parity fail {label}: {len(df)} {df.R.sum()}')
    vm,vp=build_vol_percentile(p)
    dt5,H5,L5,C5,Z5,A5=p[5],p[6],p[7],p[8],p[9],p[10]

    rows=[]
    for _,r in df.iterrows():
        k=int(r.entry_k); side=int(r.side); et=int(r.entry_ts)
        entry=float(C5[k]); atr=float(A5[k])
        rr,ex,reason=lab53.manage_cf191g(dt5,H5,L5,C5,k,side,entry,atr)
        xt=int(dt5[int(ex)])
        feat=path_features(m1,et,side,entry,atr)
        row=r.to_dict()
        row.update({
          'entry_price':entry,'entry_atr':atr,
          'vol_metric_atr_pct':float(vm[k]) if np.isfinite(vm[k]) else np.nan,
          'vol_percentile_7d':float(vp[k]) if np.isfinite(vp[k]) else np.nan,
          'vol_bucket':vol_bucket(vp[k]),
          'control_exit_ts':xt,'control_exit_reason':REASON.get(int(reason),str(reason)),
          'active_at_15m':bool(xt>et+15*60),
          'right_tail_ge_1p5R':bool(float(r.R)>=1.5),
          'period':label
        })
        if feat is None:
            row.update({'expansion15_atr':np.nan,'eff15':np.nan,'persist15':np.nan,'close15':np.nan,
                        'ret15_to_30_atr':np.nan,'ret15_to_60_atr':np.nan,'ret15_to_120_atr':np.nan,
                        'post15_mfe_to_60_atr':np.nan,'post15_mae_to_60_atr':np.nan,'early_state':'NA'})
        else:
            row.update(feat)
        rows.append(row)
    return pd.DataFrame(rows)

def pf_ev(g):
    if len(g)==0:return (np.nan,np.nan,np.nan,np.nan)
    m=metrics(g.R.to_numpy(float))
    return (m.get('EV',np.nan),m.get('PF',np.nan),m.get('SumR',np.nan),m.get('MaxDD_R',np.nan))

def regime_summary(events):
    rows=[]
    for period in ['historical','forward_2026']:
        d=events[events.period==period]
        for vb in VOL_BUCKETS:
            g=d[d.vol_bucket==vb]
            ev,pf,sumr,dd=pf_ev(g)
            rows.append({
              'period':period,'vol_bucket':vb,'N':len(g),
              'EV_R':ev,'PF':pf,'SumR':sumr,'MaxDD_R':dd,
              'mean_expansion15_atr':float(g.expansion15_atr.mean()) if len(g) else np.nan,
              'median_expansion15_atr':float(g.expansion15_atr.median()) if len(g) else np.nan,
              'mean_eff15':float(g.eff15.mean()) if len(g) else np.nan,
              'mean_persist15':float(g.persist15.mean()) if len(g) else np.nan,
              'expansion_persistent_share':float((g.early_state=='EXPANSION_PERSISTENT').mean()) if len(g) else np.nan,
              'failed_early_share':float((g.early_state=='FAILED_EARLY').mean()) if len(g) else np.nan,
              'active15_share':float(g.active_at_15m.mean()) if len(g) else np.nan,
              'right_tail_share':float(g.right_tail_ge_1p5R.mean()) if len(g) else np.nan,
            })
    return pd.DataFrame(rows)

def state_summary(events,active_only=False):
    rows=[]
    src=events[events.active_at_15m] if active_only else events
    for period in ['historical','forward_2026']:
        d=src[src.period==period]
        for vb in ['P40_60','P80_100']:
            for st in ['EXPANSION_PERSISTENT','MIXED','FAILED_EARLY']:
                g=d[(d.vol_bucket==vb)&(d.early_state==st)]
                ev,pf,sumr,dd=pf_ev(g)
                rows.append({
                  'period':period,'active_only':active_only,'vol_bucket':vb,'early_state':st,'N':len(g),
                  'EV_R':ev,'PF':pf,'SumR':sumr,
                  'mean_ret15_to_60_atr':float(g.ret15_to_60_atr.mean()) if len(g) else np.nan,
                  'mean_post15_mfe_to_60_atr':float(g.post15_mfe_to_60_atr.mean()) if len(g) else np.nan,
                  'mean_post15_mae_to_60_atr':float(g.post15_mae_to_60_atr.mean()) if len(g) else np.nan,
                  'right_tail_share':float(g.right_tail_ge_1p5R.mean()) if len(g) else np.nan,
                  'initial_stop_share':float((g.control_exit_reason=='INITIAL_STOP').mean()) if len(g) else np.nan,
                })
    return pd.DataFrame(rows)

def main():
    m1=load_m1()
    ft,fz=lab43.load_flow();hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    dh=build('historical',hist,m1); df=build('forward_2026',fwd,m1)
    events=pd.concat([dh,df],ignore_index=True)
    events.to_csv(OUT/'vol_expansion_events.csv',index=False)

    rs=regime_summary(events); rs.to_csv(OUT/'regime_early_state_summary.csv',index=False)
    ss=state_summary(events,False); ss.to_csv(OUT/'state_outcomes_all.csv',index=False)
    sa=state_summary(events,True); sa.to_csv(OUT/'state_outcomes_active15.csv',index=False)

    checks={}
    # A: HIGH vs MID 2026 and historical differences
    for period in ['historical','forward_2026']:
        mid=rs[(rs.period==period)&(rs.vol_bucket=='P40_60')].iloc[0]
        hi=rs[(rs.period==period)&(rs.vol_bucket=='P80_100')].iloc[0]
        checks[period]={
          'mid_N':int(mid.N),'high_N':int(hi.N),
          'high_expansion_lt_mid':bool(hi.mean_expansion15_atr<mid.mean_expansion15_atr),
          'high_eff_lt_mid':bool(hi.mean_eff15<mid.mean_eff15),
          'high_persist_lt_mid':bool(hi.mean_persist15<mid.mean_persist15),
          'high_expansion_state_share_lt_mid':bool(hi.expansion_persistent_share<mid.expansion_persistent_share),
          'high_failed_share_gt_mid':bool(hi.failed_early_share>mid.failed_early_share),
          'expansion_gap_high_minus_mid':float(hi.mean_expansion15_atr-mid.mean_expansion15_atr),
          'eff_gap_high_minus_mid':float(hi.mean_eff15-mid.mean_eff15),
          'persistent_share_gap_high_minus_mid':float(hi.expansion_persistent_share-mid.expansion_persistent_share),
        }

    hist_gap=checks['historical']['expansion_gap_high_minus_mid']
    fwd_gap=checks['forward_2026']['expansion_gap_high_minus_mid']
    regime_shift=(
      checks['forward_2026']['high_expansion_lt_mid'] and
      checks['forward_2026']['high_eff_lt_mid'] and
      checks['forward_2026']['high_expansion_state_share_lt_mid'] and
      fwd_gap < hist_gap
    )

    # B: within HIGH, persistent > failed in both periods
    state_checks={}
    for period in ['historical','forward_2026']:
        p=ss[(ss.period==period)&(ss.vol_bucket=='P80_100')&(ss.early_state=='EXPANSION_PERSISTENT')].iloc[0]
        f=ss[(ss.period==period)&(ss.vol_bucket=='P80_100')&(ss.early_state=='FAILED_EARLY')].iloc[0]
        state_checks[period]={
          'persistent_N':int(p.N),'failed_N':int(f.N),
          'persistent_EV_gt_failed':bool(p.EV_R>f.EV_R) if np.isfinite(p.EV_R) and np.isfinite(f.EV_R) else False,
          'persistent_PF_gt_failed':bool(p.PF>f.PF) if np.isfinite(p.PF) and np.isfinite(f.PF) else False,
          'persistent_post15_MFE_gt_failed':bool(p.mean_post15_mfe_to_60_atr>f.mean_post15_mfe_to_60_atr),
          'persistent_post15_MAE_lt_failed':bool(p.mean_post15_mae_to_60_atr<f.mean_post15_mae_to_60_atr),
          'persistent_right_tail_gt_failed':bool(p.right_tail_share>f.right_tail_share),
        }
    ordering=all(all(v for k,v in state_checks[p].items() if not k.endswith('_N')) for p in state_checks)

    # C: high vs mid after fixed early state
    same_state=[]
    for period in ['historical','forward_2026']:
        for st in ['EXPANSION_PERSISTENT','MIXED','FAILED_EARLY']:
            m=ss[(ss.period==period)&(ss.vol_bucket=='P40_60')&(ss.early_state==st)].iloc[0]
            h=ss[(ss.period==period)&(ss.vol_bucket=='P80_100')&(ss.early_state==st)].iloc[0]
            same_state.append({
              'period':period,'early_state':st,'mid_N':int(m.N),'high_N':int(h.N),
              'mid_EV':m.EV_R,'high_EV':h.EV_R,
              'mid_PF':m.PF,'high_PF':h.PF,
              'mid_post15_MFE':m.mean_post15_mfe_to_60_atr,'high_post15_MFE':h.mean_post15_mfe_to_60_atr,
              'mid_post15_MAE':m.mean_post15_mae_to_60_atr,'high_post15_MAE':h.mean_post15_mae_to_60_atr,
            })
    same=pd.DataFrame(same_state);same.to_csv(OUT/'same_state_high_vs_mid.csv',index=False)

    result={
      'lab':'LAB068_VOL_POSTENTRY_EXPANSION',
      'regime_checks':checks,
      'regime_shift_hypothesis_supported':bool(regime_shift),
      'high_vol_state_ordering_supported_both_periods':bool(ordering),
      'state_checks':state_checks,
      'limitations':[
        'Diagnostic only; no stateful action.',
        'Early-state features use exactly first 15 completed 1m bars after fill.',
        'All-entry map includes market path even if frozen control exited before 15m; active15 subset is reported separately for management relevance.',
        'BTCUSDT only; 2026 Mar-Aug reused shadow/stress.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB068 — VOLATILITY × POST-ENTRY EXPANSION / DIRECTIONAL PERSISTENCE','',
      '## Entry-vol regime → early 15m state','',rs.to_markdown(index=False),'',
      '## MID/HIGH × early state — all entries','',ss.to_markdown(index=False),'',
      '## MID/HIGH × early state — active at 15m only','',sa.to_markdown(index=False),'',
      '## Same early state: HIGH vs MID','',same.to_markdown(index=False),'',
      '## Regime checks','',json.dumps(checks,indent=2),'',
      f'Regime-shift hypothesis supported: **{regime_shift}**','',
      '## HIGH-vol state ordering checks','',json.dumps(state_checks,indent=2),'',
      f'Persistent > failed ordering supported both periods: **{ordering}**'
    ]))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
