import zipfile, json, math
from pathlib import Path
import numpy as np
import pandas as pd

SIGNALS='research/btc_unified_lifecycle/U01_EXACT_MT5_DIRECTIONAL_SIGNALS_COMPACT.csv'
M1ZIP='btc_1m.zip'
OUT=Path('u02_out'); OUT.mkdir(exist_ok=True)
SPREAD_USD=27.5
HORIZONS_MIN=[15,30,60,120,240,480]
ANCHORS=[
 ('2026-08-03 19:00:19',63680.48),
 ('2026-08-03 20:00:20',63702.77),
 ('2026-08-03 23:02:29',63789.35),
 ('2026-08-04 00:14:39',63693.69),
 ('2026-08-07 03:15:08',64246.05),
]

def load_m1():
    fs=[]
    with zipfile.ZipFile(M1ZIP) as z:
        for n in z.namelist():
            if n.lower().endswith('.csv') and ('2026-08' in n or '2026-07' in n):
                with z.open(n) as f: fs.append(pd.read_csv(f,usecols=['time','open','high','low','close']))
    x=pd.concat(fs,ignore_index=True)
    x['time']=pd.to_datetime(x['time'],format='%Y.%m.%d %H:%M',errors='coerce')
    for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.dropna().sort_values('time').drop_duplicates('time').set_index('time')

def align_offset(m1):
    rows=[]
    for off in range(-5,6):
        errs=[]; close_err=[]; inside=0
        for ts,px in ANCHORS:
            t=(pd.Timestamp(ts)+pd.Timedelta(hours=off)).floor('min')
            if t not in m1.index: continue
            r=m1.loc[t]
            gap=max(float(r.low)-px,0.0,px-float(r.high))
            errs.append(gap/px*100.0)
            close_err.append(abs(float(r.close)-px)/px*100.0)
            inside += int(float(r.low)<=px<=float(r.high))
        rows.append(dict(offset_hours=off,n=len(errs),inside=inside,median_interval_error_pct=float(np.median(errs)) if errs else np.nan,median_close_error_pct=float(np.median(close_err)) if close_err else np.nan,mean_close_error_pct=float(np.mean(close_err)) if close_err else np.nan))
    a=pd.DataFrame(rows).sort_values(['inside','median_interval_error_pct','median_close_error_pct'],ascending=[False,True,True])
    best=int(a.iloc[0].offset_hours)
    return best,a

def pf(v):
    s=pd.Series(v).dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def enrich(signals,m1,off):
    s=signals.copy(); s['signal_time']=pd.to_datetime(s.signal_time)
    s['utc_time']=s.signal_time+pd.Timedelta(hours=off)
    out=[]
    for _,r in s.iterrows():
        t0=r.utc_time.floor('min')+pd.Timedelta(minutes=1) # causal next-minute entry proxy
        if t0 not in m1.index: continue
        entry=float(m1.loc[t0,'open']); d=1.0 if r.side=='BUY' else -1.0
        q=r.to_dict(); q['entry_time_utc']=t0; q['entry_proxy']=entry
        for hm in HORIZONS_MIN:
            te=t0+pd.Timedelta(minutes=hm)
            # final close is last fully observed minute ending at te; use bar at te-1min
            tc=te-pd.Timedelta(minutes=1)
            if tc not in m1.index: q[f'ret_{hm}m']=np.nan; q[f'mfe_{hm}m']=np.nan; q[f'mae_{hm}m']=np.nan; continue
            final=float(m1.loc[tc,'close'])
            w=m1.loc[t0:tc]
            ret=d*(final-entry)/entry*100.0
            if d>0:
                mfe=(float(w.high.max())-entry)/entry*100.0; mae=(float(w.low.min())-entry)/entry*100.0
            else:
                mfe=(entry-float(w.low.min()))/entry*100.0; mae=(entry-float(w.high.max()))/entry*100.0
            q[f'ret_{hm}m']=ret; q[f'stress_{hm}m']=ret-SPREAD_USD/entry*100.0; q[f'mfe_{hm}m']=mfe; q[f'mae_{hm}m']=mae
        out.append(q)
    return pd.DataFrame(out)

def stats(g,label):
    d={'label':label,'N':len(g)}
    for hm in HORIZONS_MIN:
        v=g[f'ret_{hm}m']; sv=g[f'stress_{hm}m']
        d[f'EV_{hm}m']=float(v.mean()); d[f'WR_{hm}m']=float((v>0).mean()); d[f'PF_{hm}m']=pf(v)
        d[f'STRESS_EV_{hm}m']=float(sv.mean()); d[f'STRESS_PF_{hm}m']=pf(sv)
        d[f'MFE_MED_{hm}m']=float(g[f'mfe_{hm}m'].median()); d[f'MAE_MED_{hm}m']=float(g[f'mae_{hm}m'].median())
    return d

def main():
    m1=load_m1(); sig=pd.read_csv(SIGNALS)
    off,align=align_offset(m1); align.to_csv(OUT/'offset_alignment.csv',index=False)
    x=enrich(sig,m1,off); x.to_csv(OUT/'u02_exact_signal_outcomes.csv',index=False)
    # Primary unique-event view = first directional SmartMock poll of each 15m-gap episode.
    first=x.sort_values('signal_time').groupby('episode15',as_index=False).first()
    first.to_csv(OUT/'u02_episode_first_signal_outcomes.csv',index=False)
    # Also capture actual exact execution-poll rows, not as primary edge estimate.
    execs=x[x.disposition.eq('EXEC')].copy(); execs.to_csv(OUT/'u02_exec_poll_outcomes.csv',index=False)
    rows=[]
    rows.append(stats(x,'ALL_POLLS'))
    for side,g in x.groupby('side'): rows.append(stats(g,f'POLL_{side}'))
    for disp,g in x.groupby(['side','disposition']): rows.append(stats(g,f'POLL_{disp[0]}_{disp[1]}'))
    rows.append(stats(first,'ALL_EPISODE_FIRST'))
    for side,g in first.groupby('side'): rows.append(stats(g,f'EPISODE_FIRST_{side}'))
    for disp,g in first.groupby(['side','disposition']): rows.append(stats(g,f'EPISODE_FIRST_{disp[0]}_{disp[1]}'))
    rows.append(stats(execs,'EXACT_EXEC_POLLS'))
    pd.DataFrame(rows).to_csv(OUT/'u02_summary_metrics.csv',index=False)
    summary={
      'offset_hours_server_to_binance_utc':off,
      'alignment_best':align.iloc[0].to_dict(),
      'directional_polls':int(len(x)),
      'episodes_15m_gap':int(first.episode15.nunique()),
      'episodes_by_side':first.side.value_counts().to_dict(),
      'tags':x.tag.value_counts().to_dict(),
      'dispositions':x.disposition.value_counts().to_dict(),
      'exact_exec_polls':int(len(execs)),
      'note':'Entry/outcomes use Binance BTCUSDT next-minute open after exact MT5 signal. Alignment only uses five exact execution prices. No threshold tuning.'
    }
    (OUT/'u02_summary.json').write_text(json.dumps(summary,indent=2,default=str))
    print(json.dumps(summary,indent=2,default=str))
    print('\nEPISODE FIRST SIGNALS')
    print(first[['episode15','signal_time','side','conf','dist','pre','disposition','ret_60m','ret_120m','ret_240m','mfe_120m','mae_120m']].to_string(index=False))
    print('\nSUMMARY')
    print(pd.DataFrame(rows)[['label','N','EV_60m','PF_60m','EV_120m','PF_120m','EV_240m','PF_240m','STRESS_EV_120m']].to_string(index=False))
if __name__=='__main__': main()
