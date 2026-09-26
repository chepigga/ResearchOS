from pathlib import Path
import json, zipfile, importlib.util, urllib.request, time, math
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; AGG=DATA/'agg_daily'
OUT.mkdir(parents=True,exist_ok=True); AGG.mkdir(parents=True,exist_ok=True)

p65=ROOT.parent/'CROWDFADE_CF191G_H4_LIQUIDITY_SWEEP_REJECTION_OI_LAB_065'/'run.py'
sp=importlib.util.spec_from_file_location('lab65',p65)
lab65=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab65)
lab54=lab65.lab54; lab53=lab65.lab53; lab43=lab65.lab43
lab65.DATA=DATA; lab54.DATA=DATA; lab53.DATA=DATA; lab43.DATA=DATA

EXPECT_EVENTS={'historical':221,'forward_2026':21}
EXPECT_CF={'historical':(5297,700.3704107793633),'forward_2026':(544,35.49784078156513)}

def load_m1_price():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,2,3,4])
        ot=pd.to_numeric(q.iloc[:,0],errors='coerce')
        hi=pd.to_numeric(q.iloc[:,1],errors='coerce')
        lo=pd.to_numeric(q.iloc[:,2],errors='coerce')
        cl=pd.to_numeric(q.iloc[:,3],errors='coerce')
        x=pd.DataFrame({'raw_ts':ot,'high':hi,'low':lo,'close':cl}).dropna()
        raw=x.raw_ts.to_numpy(np.int64)
        sec=np.where(raw>10**14,raw//1_000_000,raw//1000)
        x['open_ts']=sec
        x['end_ts']=sec+60
        rows.append(x[['open_ts','end_ts','high','low','close']])
    return pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)

def classify_period(ts):
    if int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()) <= ts < int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()):
        return 'historical'
    if int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()) <= ts < int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()):
        return 'forward_2026'
    return None

def download_day(day):
    name=f'BTCUSDT-aggTrades-{day}.zip'
    p=AGG/name
    if p.exists() and p.stat().st_size>1000:
        return str(p)
    url=f'https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/{name}'
    tmp=p.with_suffix('.tmp')
    for attempt in range(5):
        try:
            urllib.request.urlretrieve(url,tmp)
            tmp.replace(p)
            return str(p)
        except Exception as e:
            if tmp.exists(): tmp.unlink()
            if attempt==4: raise
            time.sleep(2+attempt)
    return str(p)

def read_agg_day(path):
    with zipfile.ZipFile(path) as z:
        n=z.namelist()[0]
        with z.open(n) as f:
            q=pd.read_csv(f,header=None,low_memory=False)
    if q.shape[1] < 7:
        raise RuntimeError(f'bad aggTrades schema {path}: {q.shape}')
    price=pd.to_numeric(q.iloc[:,1],errors='coerce')
    qty=pd.to_numeric(q.iloc[:,2],errors='coerce')
    traw=pd.to_numeric(q.iloc[:,5],errors='coerce')
    x=pd.DataFrame({'price':price,'qty':qty,'raw_ts':traw}).dropna()
    raw=x.raw_ts.to_numpy(np.int64)
    sec=np.where(raw>10**14,raw//1_000_000,raw//1000)
    x['ts']=sec
    x['quote_notional']=x.price*x.qty
    return x[['ts','price','quote_notional']]

def weighted_quantile(price,weight,q):
    order=np.argsort(price)
    p=np.asarray(price)[order];w=np.asarray(weight)[order]
    cs=np.cumsum(w);tot=cs[-1]
    if tot<=0:return np.nan
    return float(p[np.searchsorted(cs,q*tot,'left')])

def profile_event(ev, trades):
    st=int(ev.open_ts);et=int(ev.end_ts)
    x=trades[(trades.ts>=st)&(trades.ts<et)]
    if len(x)==0:
        raise RuntimeError(f'no aggTrades for H4 {st}')
    prof=x.groupby('price',sort=True).quote_notional.sum()
    prices=prof.index.to_numpy(float);weights=prof.to_numpy(float)
    mx=np.nanmax(weights)
    candidates=prices[np.isclose(weights,mx,rtol=0,atol=max(1e-9,mx*1e-12))]
    vwap=float(np.sum(prices*weights)/np.sum(weights))
    poc=float(candidates[np.argmin(np.abs(candidates-vwap))])
    rng=float(ev.high-ev.low)
    loc=(poc-float(ev.low))/rng if rng>0 else np.nan
    lower_cut=float(ev.low)+rng/3.0; upper_cut=float(ev.low)+2*rng/3.0
    total=float(weights.sum())
    lower=float(weights[prices<=lower_cut].sum()/total)
    upper=float(weights[prices>=upper_cut].sum()/total)
    q15=weighted_quantile(prices,weights,0.15);q85=weighted_quantile(prices,weights,0.85)
    side=int(ev.event_side)
    if side>0:
        cls='POC_ALIGNED' if loc<=1/3 else ('POC_OPPOSITE' if loc>=2/3 else 'POC_MIDDLE')
    else:
        cls='POC_ALIGNED' if loc>=2/3 else ('POC_OPPOSITE' if loc<=1/3 else 'POC_MIDDLE')
    return {
      'poc':poc,'poc_location':loc,'lower_third_share':lower,'upper_third_share':upper,
      'q15_price':q15,'q85_price':q85,'profile_class':cls,'agg_trade_rows':int(len(x)),
      'profile_total_quote_notional':total
    }

def event_forward(ev,m1):
    ts=m1.end_ts.to_numpy(np.int64);hi=m1.high.to_numpy(float);lo=m1.low.to_numpy(float);cl=m1.close.to_numpy(float)
    t0=int(ev.end_ts); side=int(ev.event_side); entry=float(ev.close)
    out={}
    j=np.searchsorted(ts,t0,'left')
    if j>=len(ts) or ts[j]!=t0:
        out.update({f'ret_{h}h':np.nan for h in [1,4,8,12]})
        for h in [4,8,12]: out[f'mfe_{h}h']=out[f'mae_{h}h']=np.nan
        return out
    for h in [1,4,8,12]:
        q=np.searchsorted(ts,t0+h*3600,'left')
        if q<len(ts) and ts[q]==t0+h*3600:
            out[f'ret_{h}h']=float(side*(cl[q]-entry)/entry)
        else: out[f'ret_{h}h']=np.nan
    for h in [4,8,12]:
        q=np.searchsorted(ts,t0+h*3600,'right')
        hh=hi[j+1:q];ll=lo[j+1:q]
        if len(hh):
            if side>0:
                out[f'mfe_{h}h']=float((np.max(hh)-entry)/entry)
                out[f'mae_{h}h']=float((entry-np.min(ll))/entry)
            else:
                out[f'mfe_{h}h']=float((entry-np.min(ll))/entry)
                out[f'mae_{h}h']=float((np.max(hh)-entry)/entry)
        else:
            out[f'mfe_{h}h']=out[f'mae_{h}h']=np.nan
    return out

def summarize_events(ev):
    rows=[]
    for period in ['historical','forward_2026']:
        d=ev[ev.period==period]
        for cls in ['POC_ALIGNED','POC_MIDDLE','POC_OPPOSITE']:
            g=d[d.profile_class==cls]
            rows.append({
              'period':period,'profile_class':cls,'N':len(g),
              'mean_ret_1h':float(g.ret_1h.mean()) if len(g) else np.nan,
              'median_ret_1h':float(g.ret_1h.median()) if len(g) else np.nan,
              'mean_ret_4h':float(g.ret_4h.mean()) if len(g) else np.nan,
              'median_ret_4h':float(g.ret_4h.median()) if len(g) else np.nan,
              'mean_ret_8h':float(g.ret_8h.mean()) if len(g) else np.nan,
              'mean_ret_12h':float(g.ret_12h.mean()) if len(g) else np.nan,
              'mean_mfe_4h':float(g.mfe_4h.mean()) if len(g) else np.nan,
              'mean_mae_4h':float(g.mae_4h.mean()) if len(g) else np.nan,
              'mean_poc_location':float(g.poc_location.mean()) if len(g) else np.nan,
              'mean_lower_third_share':float(g.lower_third_share.mean()) if len(g) else np.nan,
              'mean_upper_third_share':float(g.upper_third_share.mean()) if len(g) else np.nan,
            })
    return pd.DataFrame(rows)

def cf_events_for_period(label,p):
    df=lab54.extract_cf191g_events(p)
    expN,expR=EXPECT_CF[label]
    if len(df)!=expN or abs(float(df.R.sum())-expR)>1e-6:
        raise RuntimeError(f'CF parity fail {label}: {len(df)} {df.R.sum()}')
    df=lab54.add_targets(df,p)
    df['period']=label
    return df

def cf_overlap(cf,ev):
    e=ev.sort_values('end_ts').reset_index(drop=True)
    ets=e.end_ts.to_numpy(np.int64)
    rows=[]
    for _,r in cf.iterrows():
        t=int(r.entry_ts)
        j=np.searchsorted(ets,t,'right')-1
        if j<0: continue
        er=e.iloc[j]
        if not (int(er.end_ts)<=t<int(er.end_ts)+4*3600): continue
        relation='SUPPORTIVE' if int(r.side)==int(er.event_side) else 'ADVERSE'
        rows.append({**r.to_dict(),
          'h4_event_end_ts':int(er.end_ts),'h4_event_side':int(er.event_side),
          'profile_class':er.profile_class,'relation':relation,
          'poc_location':float(er.poc_location)})
    return pd.DataFrame(rows)

def cf_summary(over):
    rows=[]
    if len(over)==0:return pd.DataFrame()
    for period in ['historical','forward_2026']:
        d=over[over.period==period]
        for relation in ['SUPPORTIVE','ADVERSE']:
            for pc in ['POC_ALIGNED','POC_MIDDLE','POC_OPPOSITE']:
                g=d[(d.relation==relation)&(d.profile_class==pc)]
                m=lab43.metrics(g.R.to_numpy(float)) if len(g) else {}
                rows.append({
                  'period':period,'relation':relation,'profile_class':pc,'N':len(g),
                  'EV_R':m.get('EV',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),
                  'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
                  'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
                })
    return pd.DataFrame(rows)

def main():
    h4=lab65.add_oi(lab65.load_h4())
    h4['period']=[classify_period(int(x)) for x in h4.end_ts]
    ev=h4[(h4.event_side!=0)&h4.period.notna()].copy().reset_index(drop=True)
    counts=ev.groupby('period').size().to_dict()
    for p,n in EXPECT_EVENTS.items():
        if int(counts.get(p,0))!=n:
            raise RuntimeError(f'LAB065 event-universe parity fail {p}: {counts.get(p,0)} != {n}')

    ev['day']=pd.to_datetime(ev.open_ts,unit='s',utc=True).dt.strftime('%Y-%m-%d')
    days=sorted(ev.day.unique())
    print(f'Composite events={len(ev)} unique_days={len(days)}')
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs={pool.submit(download_day,d):d for d in days}
        for k,f in enumerate(as_completed(futs),1):
            f.result()
            if k%20==0 or k==len(futs): print(f'downloaded {k}/{len(futs)} days')

    profiles=[]
    for day,g in ev.groupby('day',sort=True):
        trades=read_agg_day(AGG/f'BTCUSDT-aggTrades-{day}.zip')
        for idx,row in g.iterrows():
            p=profile_event(row,trades)
            p['idx']=idx;profiles.append(p)
    pdf=pd.DataFrame(profiles).set_index('idx')
    for c in pdf.columns: ev.loc[pdf.index,c]=pdf[c]

    m1=load_m1_price()
    fw=[]
    for _,r in ev.iterrows(): fw.append(event_forward(r,m1))
    fw=pd.DataFrame(fw,index=ev.index)
    for c in fw.columns: ev[c]=fw[c]
    ev.to_csv(OUT/'true_poc_h4_events.csv',index=False)

    esm=summarize_events(ev);esm.to_csv(OUT/'event_profile_outcomes.csv',index=False)
    checks={}
    for period in ['historical','forward_2026']:
        a=esm[(esm.period==period)&(esm.profile_class=='POC_ALIGNED')].iloc[0]
        o=esm[(esm.period==period)&(esm.profile_class=='POC_OPPOSITE')].iloc[0]
        checks[period]={
          'aligned_N':int(a.N),'opposite_N':int(o.N),
          'aligned_mean_ret4_gt_opposite':bool(a.mean_ret_4h>o.mean_ret_4h) if np.isfinite(a.mean_ret_4h) and np.isfinite(o.mean_ret_4h) else False,
          'aligned_median_ret4_gt_opposite':bool(a.median_ret_4h>o.median_ret_4h) if np.isfinite(a.median_ret_4h) and np.isfinite(o.median_ret_4h) else False,
          'aligned_mfe4_gt_opposite':bool(a.mean_mfe_4h>o.mean_mfe_4h) if np.isfinite(a.mean_mfe_4h) and np.isfinite(o.mean_mfe_4h) else False,
          'aligned_mae4_lt_opposite':bool(a.mean_mae_4h<o.mean_mae_4h) if np.isfinite(a.mean_mae_4h) and np.isfinite(o.mean_mae_4h) else False,
        }
    primary=all(all(v for k,v in checks[p].items() if not k.endswith('_N')) for p in checks)

    ft,fz=lab43.load_flow();hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwdp=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    cfh=cf_events_for_period('historical',hist);cff=cf_events_for_period('forward_2026',fwdp)
    over=pd.concat([cf_overlap(cfh,ev[ev.period=='historical']),cf_overlap(cff,ev[ev.period=='forward_2026'])],ignore_index=True)
    over.to_csv(OUT/'cf191g_true_poc_overlap_events.csv',index=False)
    csm=cf_summary(over);csm.to_csv(OUT/'cf191g_true_poc_overlap_summary.csv',index=False)

    result={
      'lab':'LAB066_TRUE_H4_POC_REJECTION',
      'event_counts':{k:int(v) for k,v in counts.items()},
      'unique_aggtrade_days':len(days),
      'event_checks':checks,
      'primary_event_pattern_repeats_both_periods':bool(primary),
      'cf191g_overlap_N':int(len(over)),
      'limitations':[
        'True POC uses exact aggTrade price levels weighted by quote notional.',
        'q15-q85 is central 70% price mass, not standard market-profile Value Area.',
        'Diagnostic only; no threshold/risk/entry/exit action.',
        'CF191g overlap classes with N<20 historical or N<5 in 2026 are shadow-only.',
        '2026 Mar-Aug is reused shadow/stress, not pristine OOS.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    lines=['# LAB066 — TRUE H4 VOLUME-PROFILE / POC REJECTION','',
      f"Composite H4 events: historical={counts.get('historical',0)}, forward_2026={counts.get('forward_2026',0)}; aggTrade days={len(days)}",'',
      '## Event-level true POC outcomes','',esm.to_markdown(index=False),'',
      '## Primary checks','',json.dumps(checks,indent=2),'',
      f'Primary POC-alignment pattern repeats both periods: **{primary}**','',
      '## CF191g overlap','',csm.to_markdown(index=False) if len(csm) else 'No overlaps','',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
