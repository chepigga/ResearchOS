from pathlib import Path
import json, zipfile, urllib.request, time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'
DATA.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
TRADES=pd.read_csv(ROOT/'RECENT_TRADES.csv')

START='2026-09-17'; END='2026-09-25'
LB=2016

def download_days():
    base='https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1m'
    days=pd.date_range(START,END,freq='D')
    paths=[]
    for d in days:
        day=d.strftime('%Y-%m-%d')
        name=f'BTCUSDT-1m-{day}.zip'
        p=DATA/name
        if not p.exists() or p.stat().st_size<1000:
            url=f'{base}/{name}'
            for attempt in range(5):
                try:
                    urllib.request.urlretrieve(url,p)
                    break
                except Exception:
                    if p.exists(): p.unlink()
                    if attempt==4: raise
                    time.sleep(2+attempt)
        paths.append(p)
    return paths

def read_1m(paths):
    rows=[]
    for p in paths:
        with zipfile.ZipFile(p) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
        raw=pd.to_numeric(q.iloc[:,0],errors='coerce')
        op=pd.to_numeric(q.iloc[:,1],errors='coerce')
        hi=pd.to_numeric(q.iloc[:,2],errors='coerce')
        lo=pd.to_numeric(q.iloc[:,3],errors='coerce')
        cl=pd.to_numeric(q.iloc[:,4],errors='coerce')
        x=pd.DataFrame({'raw':raw,'open':op,'high':hi,'low':lo,'close':cl}).dropna()
        r=x.raw.to_numpy(np.int64)
        sec=np.where(r>10**14,r//1_000_000,r//1000)
        x['open_ts']=sec
        x['end_ts']=sec+60
        rows.append(x[['open_ts','end_ts','open','high','low','close']])
    m=pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)
    return m

def build_clock(m):
    ts=m.open_ts.to_numpy(np.int64)
    O=m.open.to_numpy(float);H=m.high.to_numpy(float);L=m.low.to_numpy(float);C=m.close.to_numpy(float)

    b15=(ts//900)*900
    st15=np.r_[0,np.flatnonzero(b15[1:]!=b15[:-1])+1]
    en15=np.r_[st15[1:],len(ts)]
    bt15=b15[st15]
    h15=np.maximum.reduceat(H,st15); l15=np.minimum.reduceat(L,st15); c15=C[en15-1]
    pc=np.r_[c15[0],c15[:-1]]
    tr=np.maximum(h15-l15,np.maximum(np.abs(h15-pc),np.abs(l15-pc)))
    atr15=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    av15=bt15+900

    b5=(ts//300)*300
    st5=np.r_[0,np.flatnonzero(b5[1:]!=b5[:-1])+1]
    en5=np.r_[st5[1:],len(ts)]
    bt5=b5[st5]; c5=C[en5-1]; av5=bt5+300
    ai=np.searchsorted(av15,av5,'right')-1
    A=np.full(len(av5),np.nan)
    good=ai>=0
    A[good]=atr15[ai[good]]
    vm=A/c5
    vp=np.full(len(vm),np.nan)
    for k in range(LB,len(vm)):
        h=vm[k-LB:k]
        if np.all(np.isfinite(h)) and np.isfinite(vm[k]):
            vp[k]=float(np.mean(h<=vm[k]))
    return pd.DataFrame({'decision_ts':av5,'close5':c5,'atr15':A,'vol_metric':vm,'vol_pct':vp})

def state15(m,decision_ts,side,entry_ref,atr):
    ends=m.end_ts.to_numpy(np.int64)
    closes=m.close.to_numpy(float)
    j=np.searchsorted(ends,decision_ts+60,'left')
    idx=np.arange(j,j+15)
    expected=np.arange(decision_ts+60,decision_ts+16*60,60)
    if idx[-1]>=len(ends) or not np.array_equal(ends[idx],expected):
        return None
    c=closes[idx]
    steps=np.diff(np.r_[entry_ref,c])
    exp=float(side*(c[-1]-entry_ref)/atr)
    eff=float(side*(c[-1]-entry_ref)/(np.sum(np.abs(steps))+1e-12))
    persist=float(np.mean(side*steps>0))
    return {
      'close15':float(c[-1]),'expansion15_atr':exp,'eff15':eff,'persist15':persist,
      'failed_early':bool(exp<=0 or eff<=0)
    }

def approx_stopcap(m, row, entry_ref, close15):
    side=1 if row.side=='BUY' else -1
    entry=float(row.entry_price); sl=float(row.initial_sl); risk=abs(entry-sl)
    delta15=close15-entry_ref
    mapped15=entry+delta15
    exit15_r=side*(mapped15-entry)/risk
    if exit15_r<=-0.75:
        return float(exit15_r),'immediate_at_15m'

    cap=entry+side*(-0.75*risk)
    exit_utc=(pd.Timestamp(row.exit_server)-pd.Timedelta(hours=int(row.server_tz_offset_hours))).tz_localize('UTC')
    exit_ts=int(exit_utc.timestamp())
    t15=int(pd.Timestamp(row.decision_utc,tz='UTC').timestamp())+15*60
    x=m[(m.open_ts>=t15)&(m.open_ts<exit_ts)]
    if len(x):
        if side>0:
            mapped_low=entry+(x.low.to_numpy(float)-entry_ref)
            if np.any(mapped_low<=cap):
                return -0.75,'cap_hit'
        else:
            mapped_high=entry+(x.high.to_numpy(float)-entry_ref)
            if np.any(mapped_high>=cap):
                return -0.75,'cap_hit'
    actual_r=side*(float(row.exit_price)-entry)/risk
    return float(actual_r),'cap_not_hit'

def main():
    m=read_1m(download_days())
    clock=build_clock(m)
    results=[]
    for _,r in TRADES.iterrows():
        dt=pd.Timestamp(r.decision_utc,tz='UTC')
        dts=int(dt.timestamp())
        q=clock[clock.decision_ts==dts]
        if len(q)!=1:
            raise RuntimeError(f'missing decision clock {r.decision_utc}')
        q=q.iloc[0]
        side=1 if r.side=='BUY' else -1
        st=state15(m,dts,side,float(q.close5),float(q.atr15))
        if st is None: raise RuntimeError(f'missing 15m state {r.decision_utc}')
        high=bool(float(q.vol_pct)>=0.80)
        hvfe=bool(high and st['failed_early'])
        risk=abs(float(r.entry_price)-float(r.initial_sl))
        actual_r=float(side*(float(r.exit_price)-float(r.entry_price))/risk)
        delta15=float(st['close15']-float(q.close5))
        mapped15=float(r.entry_price)+delta15
        exit15_r=float(side*(mapped15-float(r.entry_price))/risk)
        stopcap_r,stopcap_mode=approx_stopcap(m,r,float(q.close5),float(st['close15']))
        results.append({
          **r.to_dict(),
          'binance_entry_ref':float(q.close5),
          'entry_atr15':float(q.atr15),
          'vol_percentile_7d':float(q.vol_pct),
          'high_vol':high,
          **st,
          'HVFE':hvfe,
          'actual_R':actual_r,
          'exit15_shadow_R':exit15_r if hvfe else actual_r,
          'stopcap075_shadow_R':stopcap_r if hvfe else actual_r,
          'stopcap_mode':stopcap_mode if hvfe else 'not_HVFE'
        })
    out=pd.DataFrame(results)
    out.to_csv(OUT/'recent_trade_audit.csv',index=False)

    summary={
      'N':int(len(out)),
      'HVFE_N':int(out.HVFE.sum()),
      'actual_losers':int((out.actual_R<0).sum()),
      'HVFE_among_losers':int(((out.HVFE)&(out.actual_R<0)).sum()),
      'actual_winners':int((out.actual_R>0).sum()),
      'HVFE_among_winners':int(((out.HVFE)&(out.actual_R>0)).sum()),
      'actual_sum_R':float(out.actual_R.sum()),
      'exit15_shadow_sum_R':float(out.exit15_shadow_R.sum()),
      'stopcap075_shadow_sum_R':float(out.stopcap075_shadow_R.sum()),
      'actual_mean_R':float(out.actual_R.mean()),
      'exit15_shadow_mean_R':float(out.exit15_shadow_R.mean()),
      'stopcap075_shadow_mean_R':float(out.stopcap075_shadow_R.mean()),
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    cols=['broker','decision_utc','side','entry_price','exit_price','actual_R','vol_percentile_7d',
          'expansion15_atr','eff15','persist15','HVFE','exit15_shadow_R','stopcap075_shadow_R','stopcap_mode']
    report=['# LAB071 — RECENT LIVE CF191g HVFE AUDIT','',out[cols].to_markdown(index=False),'',
            '## Summary','',json.dumps(summary,indent=2),
            '','N=4 is a recent forward case study, not statistical proof. BTC only.']
    (OUT/'REPORT.md').write_text('\n'.join(report))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
