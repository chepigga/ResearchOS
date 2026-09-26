from pathlib import Path
import json, zipfile, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p58=ROOT.parent/'CROWDFADE_CF191G_SEQUENTIAL_ABSORPTION_DECAY_LAB_058'/'run.py'
sp=importlib.util.spec_from_file_location('lab58',p58)
lab58=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab58)
lab54=lab58.lab54; lab53=lab58.lab53; lab43=lab58.lab43
lab58.DATA=DATA; lab54.DATA=DATA; lab53.DATA=DATA; lab43.DATA=DATA

EXPECT={
    'historical': {'N':5297,'SumR':700.3704107793633,'absN':122},
    'forward_2026': {'N':544,'SumR':35.49784078156513,'absN':12},
}
HORIZONS=[1,3,5]

def metrics_r(a):
    return lab43.metrics(np.asarray(a,float))

def load_m1_full():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
        ot=(pd.to_numeric(q.iloc[:,0],errors='coerce')//1000).astype('Int64')
        op=pd.to_numeric(q.iloc[:,1],errors='coerce')
        hi=pd.to_numeric(q.iloc[:,2],errors='coerce')
        lo=pd.to_numeric(q.iloc[:,3],errors='coerce')
        cl=pd.to_numeric(q.iloc[:,4],errors='coerce')
        x=pd.DataFrame({'open_ts':ot,'open':op,'high':hi,'low':lo,'close':cl}).dropna()
        x['end_ts']=x.open_ts.astype(np.int64)+60
        rows.append(x)
    return pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)

def classify_resolution(m1,entry_ts,side):
    ends=m1.end_ts.to_numpy(np.int64)
    hi=m1.high.to_numpy(float);lo=m1.low.to_numpy(float);cl=m1.close.to_numpy(float)
    j=np.searchsorted(ends,int(entry_ts),'left')
    if j>=len(ends) or ends[j]!=int(entry_ts) or j<4:
        return None
    idx=np.arange(j-4,j+1)
    expected=np.arange(int(entry_ts)-240,int(entry_ts)+1,60)
    if not np.array_equal(ends[idx],expected):
        return None
    ah=float(np.max(hi[idx])); al=float(np.min(lo[idx]))
    result={'anchor_high':ah,'anchor_low':al,'anchor_range':ah-al}
    first_type='UNRESOLVED';first_n=np.nan;first_close=np.nan;first_ts=np.nan
    for n in range(1,6):
        q=j+n
        if q>=len(ends) or ends[q]!=int(entry_ts)+60*n:
            break
        c=float(cl[q])
        release=(c>ah) if side>0 else (c<al)
        reject=(c<al) if side>0 else (c>ah)
        if release or reject:
            first_type='RELEASE' if release else 'REJECTION'
            first_n=n;first_close=c;first_ts=int(ends[q])
            break
    for h in HORIZONS:
        if np.isfinite(first_n) and first_n<=h:
            result[f'resolution_{h}m']=first_type
            result[f'resolution_minute_{h}m']=int(first_n)
            result[f'resolution_close_{h}m']=first_close
            result[f'resolution_ts_{h}m']=int(first_ts)
        else:
            result[f'resolution_{h}m']='UNRESOLVED'
            result[f'resolution_minute_{h}m']=np.nan
            result[f'resolution_close_{h}m']=np.nan
            result[f'resolution_ts_{h}m']=np.nan
    return result

def manage_delayed_1m(m1,entry_ts,side,entry,atr):
    ends=m1.end_ts.to_numpy(np.int64)
    hi=m1.high.to_numpy(float);lo=m1.low.to_numpy(float);cl=m1.close.to_numpy(float)
    j=np.searchsorted(ends,int(entry_ts),'left')
    if j>=len(ends) or ends[j]!=int(entry_ts):
        return (np.nan,np.nan,'NO_DATA')
    stop0=entry-side*lab53.SL_ATR*atr
    pending=stop0;peak=entry
    hold_end=int(entry_ts)+lab53.HOLD_S
    xe=min(len(ends)-1,np.searchsorted(ends,hold_end,'left'))
    xp=float(cl[xe]);ex=xe;reason='TIME_EXIT'
    for q in range(j+1,xe+1):
        stop=pending
        if (side>0 and lo[q]<=stop) or (side<0 and hi[q]>=stop):
            xp=stop;ex=q
            reason='PROFIT_STOP' if ((side>0 and stop>entry) or (side<0 and stop<entry)) else 'INITIAL_STOP'
            break
        if side>0:
            if hi[q]>peak:peak=hi[q]
            mfe=(peak-entry)/atr
        else:
            if lo[q]<peak:peak=lo[q]
            mfe=(entry-peak)/atr
        ns=stop
        if mfe>=lab53.G_BE_ARM:
            lvl=entry+side*lab53.G_BE_LOCK*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):ns=lvl
        if mfe>=lab53.G_TRAIL_ARM:
            lvl=peak-side*lab53.G_TRAIL_GAP*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):ns=lvl
        pending=ns
    rr=side*(xp-entry)/(lab53.SL_ATR*atr)-(lab53.COST_BPS/10000.)*entry/(lab53.SL_ATR*atr)
    return float(rr),int(ends[ex]),reason

def build_period(label,p,m1seq,m1full):
    df,seq=lab58.build(label,p,m1seq)
    exp=EXPECT[label]
    if len(df)!=exp['N'] or abs(float(df.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'control parity fail {label}')
    a=df[df.adverse_decay_corner].copy().reset_index(drop=True)
    if len(a)!=exp['absN']:
        raise RuntimeError(f'LAB058 adverse universe parity fail {label}: {len(a)} vs {exp["absN"]}')
    rows=[]
    for _,r in a.iterrows():
        res=classify_resolution(m1full,int(r.entry_ts),int(r.side))
        if res is None:
            continue
        row=r.to_dict();row.update(res)
        row['side_name']='BUY' if int(r.side)>0 else 'SELL'
        row['candidate_time']=pd.to_datetime(int(r.entry_ts),unit='s',utc=True).strftime('%Y-%m-%d %H:%M:%S')
        # Primary 3m local delayed-release replay only.
        if row['resolution_3m']=='RELEASE':
            dentry=float(row['resolution_close_3m']);dts=int(row['resolution_ts_3m'])
            rr,ets,reason=manage_delayed_1m(m1full,dts,int(r.side),dentry,float(r.atr))
            row['delayed_release_entry']=dentry
            row['delayed_release_R']=rr
            row['delayed_release_exit_ts']=ets
            row['delayed_release_exit_reason']=reason
            row['delayed_minus_original_R']=rr-float(r.R) if np.isfinite(rr) else np.nan
        else:
            row['delayed_release_entry']=np.nan
            row['delayed_release_R']=np.nan
            row['delayed_release_exit_ts']=np.nan
            row['delayed_release_exit_reason']=''
            row['delayed_minus_original_R']=np.nan
        rows.append(row)
    out=pd.DataFrame(rows)
    if len(out)!=exp['absN']:
        raise RuntimeError(f'resolution event loss {label}: {len(out)} vs {exp["absN"]}')
    out['period']=label
    return out

def describe(g,period,horizon,state):
    m=metrics_r(g.R.to_numpy(float))
    return {
      'period':period,'horizon_min':horizon,'state':state,'N':len(g),
      'EV_R':m.get('EV',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),
      'WR':m.get('WR',np.nan),'MaxDD_R':m.get('MaxDD_R',np.nan),
      'mean_mfe15':float(g.mfe_15m.mean()) if len(g) else np.nan,
      'mean_mae15':float(g.mae_15m.mean()) if len(g) else np.nan,
      'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
      'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
      'mean_ret60':float(g.ret_60m.mean()) if len(g) else np.nan,
      'impulse60_rate':float(g.impulse60.mean()) if len(g) else np.nan,
      'mean_resolution_minute':float(g[f'resolution_minute_{horizon}m'].mean()) if len(g) else np.nan,
      'mean_delayed_release_R':float(g.delayed_release_R.mean()) if len(g) and state=='RELEASE' and horizon==3 else np.nan,
      'mean_original_R_for_release':float(g.R.mean()) if len(g) and state=='RELEASE' and horizon==3 else np.nan,
      'mean_delayed_minus_original_R':float(g.delayed_minus_original_R.mean()) if len(g) and state=='RELEASE' and horizon==3 else np.nan,
    }

def summarize(events):
    rows=[]
    for period in ['historical','forward_2026']:
        d=events[events.period==period]
        for h in HORIZONS:
            col=f'resolution_{h}m'
            for state in ['RELEASE','REJECTION','UNRESOLVED']:
                rows.append(describe(d[d[col]==state],period,h,state))
    return pd.DataFrame(rows)

def checks(summary):
    out={}
    for period in ['historical','forward_2026']:
        r=summary[(summary.period==period)&(summary.horizon_min==3)&(summary.state=='RELEASE')].iloc[0]
        j=summary[(summary.period==period)&(summary.horizon_min==3)&(summary.state=='REJECTION')].iloc[0]
        out[period]={
          'release_N':int(r.N),'rejection_N':int(j.N),
          'release_EV_gt_rejection':bool(r.EV_R>j.EV_R) if np.isfinite(r.EV_R) and np.isfinite(j.EV_R) else False,
          'release_PF_gt_rejection':bool(r.PF>j.PF) if np.isfinite(r.PF) and np.isfinite(j.PF) else False,
          'release_MFE60_gt_rejection':bool(r.mean_mfe60>j.mean_mfe60) if np.isfinite(r.mean_mfe60) and np.isfinite(j.mean_mfe60) else False,
          'release_MAE60_lt_rejection':bool(r.mean_mae60<j.mean_mae60) if np.isfinite(r.mean_mae60) and np.isfinite(j.mean_mae60) else False,
          'release_impulse60_gt_rejection':bool(r.impulse60_rate>j.impulse60_rate) if np.isfinite(r.impulse60_rate) and np.isfinite(j.impulse60_rate) else False,
          'mean_delayed_minus_original_R':float(r.mean_delayed_minus_original_R) if np.isfinite(r.mean_delayed_minus_original_R) else None
        }
    primary=all(out[p][k] for p in out for k in [
      'release_EV_gt_rejection','release_PF_gt_rejection','release_MFE60_gt_rejection',
      'release_MAE60_lt_rejection','release_impulse60_gt_rejection'])
    return out,primary

def main():
    # m1seq includes quote/taker fields for exact LAB058 universe.
    m1seq=lab58.load_m1()
    m1full=load_m1_full()
    ft,fz=lab43.load_flow()
    hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))

    dh=build_period('historical',hist,m1seq,m1full)
    df=build_period('forward_2026',fwd,m1seq,m1full)
    events=pd.concat([dh,df],ignore_index=True)
    events.to_csv(OUT/'absorption_resolution_events.csv',index=False)

    summary=summarize(events)
    summary.to_csv(OUT/'release_rejection_summary.csv',index=False)
    ck,primary=checks(summary)

    cols=['period','candidate_time','side_name','R','anchor_high','anchor_low',
          'resolution_1m','resolution_3m','resolution_5m',
          'resolution_minute_3m','resolution_close_3m',
          'mfe_15m','mae_15m','mfe_60m','mae_60m','ret_60m','impulse60',
          'delayed_release_R','delayed_minus_original_R']
    events[cols].to_csv(OUT/'event_audit_compact.csv',index=False)

    result={
      'lab':'CROWDFADE_CF191G_ABSORPTION_RELEASE_REJECTION_LAB_059',
      'universe':{
        'historical':int((events.period=='historical').sum()),
        'forward_2026':int((events.period=='forward_2026').sum())},
      'primary_horizon_min':3,
      'checks':ck,
      'all_primary_signs_repeat_both_periods':bool(primary),
      'limitations':[
        'Diagnostic only; no stateful wait/veto was tested.',
        'Release/rejection uses completed 1m closes beyond the frozen 5m absorption range.',
        'Delayed release replay is local/non-stateful and uses 1m management with frozen CF191g geometry.',
        'BTCUSDT only; ETH/SOL transfer not established.',
        '2026 Mar-Aug is reused shadow/stress, not pristine OOS.',
        'Small rejection counts may limit inference.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    lines=['# LAB059 — ABSORPTION RELEASE VS REJECTION','',
      'Execution-timing diagnostic only. CF191g signal core unchanged.','',
      '## Frozen adverse-decay universe','',
      f"- 2021–2025: N={(events.period=='historical').sum()}",
      f"- 2026 Mar–Aug: N={(events.period=='forward_2026').sum()}",'',
      '## Resolution summary','',summary.to_markdown(index=False),'',
      '## Primary 3m checks','',json.dumps(ck,indent=2),'',
      f"All preregistered primary signs repeat in both periods: **{primary}**",'',
      '## Compact event audit','',events[cols].to_markdown(index=False),'',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
