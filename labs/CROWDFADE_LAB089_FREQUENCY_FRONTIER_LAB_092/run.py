from pathlib import Path
import json, zipfile, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'/'all_1m'
SRC=ROOT.parent/'CROWDFADE_EXTREME_LS_TRAP_TRIGGER_LAB_089'/'output'/'dedup_events.csv'

CAND={1:15.0,-1:10.0}
TPS={1:2.5,-1:2.0}
COST_BPS=0.5
HOLD_MIN=120

def load_bars():
    rows=[]
    for zp in sorted(DATA.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
        q.columns=['open_ms','open','high','low','close']
        q['ts_open']=(pd.to_numeric(q.open_ms,errors='coerce')//1000).astype('Int64')
        for c in ['open','high','low','close']: q[c]=pd.to_numeric(q[c],errors='coerce')
        q=q.dropna().copy(); q['ts_open']=q.ts_open.astype(np.int64)
        rows.append(q[['ts_open','open','high','low','close']])
    return pd.concat(rows,ignore_index=True).sort_values('ts_open').drop_duplicates('ts_open').reset_index(drop=True)

def freeze_thresholds(d):
    out={}
    for sd,w in CAND.items():
        tr=d[(d.dataset=='historical')&(d.side==sd)&(d.window_min==w)]
        out[sd]={
          'window_min':w,
          'dls_q50':float(tr.dls.quantile(.5)),
          'doi_q50':float(tr.doi.quantile(.5)),
          'rej_q50':float((-tr.price_crowd_R).quantile(.5))
        }
    return out

def apply_admission(g,thr,name):
    A=g.dls>=thr['dls_q50']
    B=g.doi>=thr['doi_q50']
    C=(-g.price_crowd_R)>=thr['rej_q50']
    if name=='ALL_3_OF_3': return A&B&C
    if name=='PRICE_LS': return C&A
    if name=='PRICE_OI': return C&B
    if name=='PRICE_PLUS_1OF2': return C&(A|B)
    if name=='ANY_2_OF_3': return (A.astype(int)+B.astype(int)+C.astype(int))>=2
    if name=='BASE': return np.ones(len(g),dtype=bool)
    raise ValueError(name)

def replay(row,bars,ts_arr):
    sd=int(row.side); tpR=TPS[sd]; atr=float(row.atr); t=int(row.ts)
    k=int(np.searchsorted(ts_arr,t,side='left'))
    if k>=len(bars): return None
    ep=float(bars.open.iloc[k]); stop=ep-sd*atr; tp=ep+sd*tpR*atr
    e=int(np.searchsorted(ts_arr,t+HOLD_MIN*60,side='right'))
    exit_px=float(bars.close.iloc[min(e-1,len(bars)-1)]); exit_ts=int(ts_arr[min(e-1,len(bars)-1)]); outcome='TIME'
    for q in range(k,min(e,len(bars))):
        hi=float(bars.high.iloc[q]); lo=float(bars.low.iloc[q])
        hit_sl=(lo<=stop) if sd>0 else (hi>=stop)
        hit_tp=(hi>=tp) if sd>0 else (lo<=tp)
        if hit_sl or hit_tp:
            if hit_sl:
                exit_px=stop; outcome='SL'
            else:
                exit_px=tp; outcome='TP'
            exit_ts=int(ts_arr[q]); break
    grossR=sd*(exit_px-ep)/atr
    costR=(ep*(COST_BPS/10000.0))/atr
    return {'entry_ts':int(ts_arr[k]),'exit_ts':exit_ts,'netR':grossR-costR,'grossR':grossR,'outcome':outcome}

def metrics(g):
    x=g.netR.to_numpy(float)
    if len(x)==0:return {'N':0}
    w=x[x>0].sum(); l=-x[x<0].sum()
    eq=np.cumsum(x); peak=np.maximum.accumulate(np.r_[0,eq]); dd=peak[1:]-eq
    return {'N':len(x),'EV_R':float(x.mean()),'WR':float((x>0).mean()),
            'PF':float(w/l) if l>0 else np.nan,'SumR':float(x.sum()),
            'MaxDD_R':float(dd.max()) if len(dd) else 0.0,
            'Recovery':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else np.nan}

def monthly_stats(g):
    if len(g)==0:return {}
    z=g.copy(); z['month']=pd.to_datetime(z.entry_ts,unit='s',utc=True).dt.to_period('M').astype(str)
    m=z.groupby('month').agg(N=('netR','size'),SumR=('netR','sum')).reset_index()
    return {
      'months':int(len(m)),
      'trades_per_month_mean':float(m.N.mean()),
      'trades_per_month_median':float(m.N.median()),
      'trades_per_month_min':int(m.N.min()),
      'trades_per_month_max':int(m.N.max()),
      'negative_months':int((m.SumR<0).sum()),
      'positive_months':int((m.SumR>0).sum()),
      'flat_months':int((m.SumR==0).sum()),
      'monthly_SumR_mean':float(m.SumR.mean()),
      'monthly_SumR_median':float(m.SumR.median())
    }

def main():
    d=pd.read_csv(SRC)
    d=d[d.apply(lambda r: float(r.window_min)==CAND[int(r.side)],axis=1)].copy().reset_index(drop=True)
    thr=freeze_thresholds(d)
    bars=load_bars(); ts_arr=bars.ts_open.to_numpy(np.int64)
    modes=['ALL_3_OF_3','PRICE_LS','PRICE_OI','PRICE_PLUS_1OF2','ANY_2_OF_3','BASE']

    evrows=[]
    for sd,w in CAND.items():
        g=d[(d.side==sd)&(d.window_min==w)].copy()
        for mode in modes:
            h=g[apply_admission(g,thr[sd],mode)].copy()
            for _,r in h.iterrows():
                z=replay(r,bars,ts_arr)
                if z is not None:
                    evrows.append({'dataset':r.dataset,'side':sd,'admission':mode,'signal_ts':int(r.ts),**z})
    ev=pd.DataFrame(evrows)
    ev.to_csv(OUT/'frequency_frontier_events.csv',index=False)

    rows=[]
    for (ds,sd,mode),g in ev.groupby(['dataset','side','admission']):
        m=metrics(g.sort_values('entry_ts'))
        ms=monthly_stats(g)
        rows.append({'dataset':ds,'side':'BUY' if sd>0 else 'SELL','admission':mode,**m,**ms})
    side=pd.DataFrame(rows); side.to_csv(OUT/'frontier_by_side.csv',index=False)

    rows=[]
    for (ds,mode),g in ev.groupby(['dataset','admission']):
        m=metrics(g.sort_values('entry_ts')); ms=monthly_stats(g)
        rows.append({'dataset':ds,'admission':mode,**m,**ms})
    total=pd.DataFrame(rows); total.to_csv(OUT/'frontier_total.csv',index=False)

    # explicit target-band score: prefer 20-40 trades/mo, positive EV, PF>1.5, lower DD
    cand=[]
    for _,r in total.iterrows():
        in_band=(20<=r.trades_per_month_mean<=40)
        score=(1 if in_band else 0, r.EV_R, r.PF, -r.MaxDD_R)
        cand.append({**r.to_dict(),'in_target_20_40':bool(in_band),'score_tuple':str(score)})
    ranked=pd.DataFrame(cand)
    ranked.to_csv(OUT/'frontier_ranked.csv',index=False)

    summary={
      'lab':'LAB092_LAB089_FREQUENCY_FRONTIER',
      'frozen_execution':{'BUY':'MARKET TP2.5R SL1R','SELL':'MARKET TP2.0R SL1R','max_hold_min':HOLD_MIN,'cost_bps_rt':COST_BPS},
      'frozen_thresholds':{'BUY':thr[1],'SELL':thr[-1]},
      'admissions':modes,
      'goal':'Find admission with 20-40 trades/month while preserving positive EV/PF and acceptable DD.',
      'limitations':['2026 Mar-Aug reused diagnostic, not pristine OOS.','Binance futures 1m execution proxy, not broker-native fills.','Sequential trade DD ignores concurrency/margin interaction.']
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB092 — LAB089 FREQUENCY FRONTIER\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## Total\n\n'+total.to_markdown(index=False)+'\n\n## By side\n\n'+side.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
