#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, io, zipfile
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
BASE=ROOT/'gc_m1_orderflow_edge_discovery_003.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002.json'
OUT_MD=ROOT/'GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002.md'
OUT_EVENTS=ROOT/'GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002_EVENTS.csv'

WINDOWS=(1,2,5,10,30)
MECHS=('FADE_Q20','FADE_STALL','CHASE_Q80')
HORIZONS=(1,3,5,10,30,60)
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
CLOCK_OFFSET_MIN=180
COOLDOWN_MS=60000
STALE_MS=2000

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader; spec.loader.exec_module(m); return m

def read_amp_ticks(zp):
    with zipfile.ZipFile(zp) as zf:
        n=[x for x in zf.namelist() if x.lower().endswith('.csv')][0]
        with zf.open(n) as raw:
            d=pd.read_csv(io.TextIOWrapper(raw,encoding='utf-8-sig'),
                          usecols=['time_msc','last','volume','volume_real','is_buy','is_sell'],
                          low_memory=False)
    for c in ('time_msc','last','volume','volume_real','is_buy','is_sell'):
        d[c]=pd.to_numeric(d[c],errors='coerce')
    vr=d.volume_real.fillna(0); vi=d.volume.fillna(0)
    d['vol']=np.where(vr>0,vr,vi)
    buy=d.is_buy.fillna(0).astype(int).eq(1); sell=d.is_sell.fillna(0).astype(int).eq(1)
    d=d[((buy&~sell)|(sell&~buy)) & d.time_msc.notna() & d['last'].gt(0) & pd.Series(d.vol).gt(0)].copy()
    d['sgn']=np.where(buy[d.index],1,-1)
    d=d.sort_values('time_msc',kind='mergesort').reset_index(drop=True)
    return d[['time_msc','last','vol','sgn']]

def m1_atr_map(t):
    m=(t.time_msc.astype('int64')//60000)*60000
    x=t.assign(minute=m)
    g=x.groupby('minute',sort=True)['last'].agg(open='first',high='max',low='min',close='last').reset_index()
    pc=g.close.shift(1)
    tr=pd.concat([(g.high-g.low),(g.high-pc).abs(),(g.low-pc).abs()],axis=1).max(axis=1)
    tr.iloc[0]=np.nan
    g['atr14']=tr.rolling(14,min_periods=14).mean()
    return dict(zip(g.minute.astype(np.int64),g.atr14.astype(float)))

def aggregate_window(t,w):
    width=w*1000
    bucket=(t.time_msc.astype('int64')//width)*width
    x=t.assign(bucket=bucket,
               buy=np.where(t.sgn.eq(1),t.vol,0.0),
               sell=np.where(t.sgn.eq(-1),t.vol,0.0))
    g=x.groupby('bucket',sort=True,observed=True)
    b=g['last'].agg(open='first',high='max',low='min',close='last')
    b['buy_vol']=g.buy.sum(); b['sell_vol']=g.sell.sum()
    b['volume']=b.buy_vol+b.sell_vol
    b['delta']=b.buy_vol-b.sell_vol
    b['delta_frac']=b.delta/b.volume.replace(0,np.nan)
    b=b.reset_index()
    b['end_ms']=b.bucket+width
    return b

def causal_features(b,w,atr_map):
    from collections import deque
    b=b.copy()
    b['abs_delta']=b.delta_frac.abs()

    # Exact causal 1-hour clock lookback, excluding the current bucket.
    ridx=pd.to_datetime(b.end_ms,unit='ms',utc=True)
    ad=pd.Series(b.abs_delta.to_numpy(float),index=ridx)
    vv=pd.Series(b.volume.to_numpy(float),index=ridx)
    b['q90_abs_delta']=ad.rolling('3600s',closed='left',min_periods=60).quantile(.90).to_numpy()
    b['q75_vol']=vv.rolling('3600s',closed='left',min_periods=60).quantile(.75).to_numpy()

    atr=[]
    for ms in b.end_ms.to_numpy(np.int64):
        prev_min=((ms//60000)*60000)-60000
        atr.append(atr_map.get(prev_min,np.nan))
    b['gc_atr']=atr
    b['crowd_dir']=np.sign(b.delta).astype(int)
    b['impact']=b.crowd_dir*(b.close-b.open)/b.gc_atr
    b['extreme']=(b.abs_delta>=b.q90_abs_delta)&(b.volume>=b.q75_vol)&b.crowd_dir.ne(0)&b.gc_atr.gt(0)

    # Prior extreme-effort impacts from the preceding clock hour only.
    q20=np.full(len(b),np.nan); q80=np.full(len(b),np.nan)
    hist=deque()
    ends=b.end_ms.to_numpy(np.int64)
    impacts=b.impact.to_numpy(float)
    ex=b.extreme.to_numpy(bool)
    for i in np.flatnonzero(ex):
        now=int(ends[i]); cutoff=now-3600000
        while hist and hist[0][0] < cutoff:
            hist.popleft()
        vals=[v for _,v in hist]
        if len(vals)>=20:
            q20[i]=float(np.quantile(vals,.20)); q80[i]=float(np.quantile(vals,.80))
        if np.isfinite(impacts[i]):
            hist.append((now,float(impacts[i])))
    b['impact_q20']=q20; b['impact_q80']=q80
    return b

def first_idx(times,target):
    i=int(np.searchsorted(times,target,side='left'))
    if i>=len(times): return None,None
    lag=int(times[i]-target)
    if lag<0 or lag>STALE_MS: return None,lag
    return i,lag

def period(ms):
    t=pd.to_datetime(ms,unit='ms',utc=True)
    if t<TRAIN_END: return 'TRAIN'
    if t<VALID_END: return 'VALID'
    return 'POST_CHECK'

def select_events(b,w,mech):
    if mech=='FADE_Q20':
        mask=b.extreme & b.impact_q20.notna() & (b.impact<=b.impact_q20)
        direction=-b.crowd_dir
    elif mech=='FADE_STALL':
        mask=b.extreme & (b.impact<=0.05)
        direction=-b.crowd_dir
    elif mech=='CHASE_Q80':
        mask=b.extreme & b.impact_q80.notna() & (b.impact>=b.impact_q80)
        direction=b.crowd_dir
    else: raise ValueError(mech)
    rows=[]; last_accept=-10**18
    for i in np.flatnonzero(mask.to_numpy()):
        end_ms=int(b.iloc[i].end_ms)
        if end_ms-last_accept<COOLDOWN_MS: continue
        last_accept=end_ms
        rows.append((i,int(direction.iloc[i])))
    return rows

def metric(d,h):
    c=f'ret_{h}s_atr'; v=d[c].dropna().to_numpy(float)
    return {'n':int(len(v)),'ev':float(v.mean()) if len(v) else None,'median':float(np.median(v)) if len(v) else None,'wr':float((v>0).mean()*100) if len(v) else None}

def summarize(d):
    out={}
    for p in ('TRAIN','VALID','POST_CHECK','FULL'):
        z=d if p=='FULL' else d[d.period.eq(p)]
        out[p]={'all':{str(h):metric(z,h) for h in HORIZONS},
                'strict':{str(h):metric(z[z.pre_move_atr<=0],h) for h in HORIZONS},
                'loose':{str(h):metric(z[z.pre_move_atr<=.10],h) for h in HORIZONS}}
        v=z.pre_move_atr.dropna().to_numpy(float)
        out[p]['pre']={'n':int(len(v)),'median':float(np.median(v)) if len(v) else None,'mean':float(v.mean()) if len(v) else None}
    return out

def gate(s):
    tr=s['TRAIN']['all']; va=s['VALID']['all']; st=s['VALID']['strict']; pre=s['VALID']['pre']
    c={'train_n_ge20':tr['30']['n']>=20,'valid_n_ge20':va['30']['n']>=20,
       'train_5_pos':tr['5']['ev'] is not None and tr['5']['ev']>0,
       'valid_5_pos':va['5']['ev'] is not None and va['5']['ev']>0,
       'train_30_pos':tr['30']['ev'] is not None and tr['30']['ev']>0,
       'valid_30_pos':va['30']['ev'] is not None and va['30']['ev']>0,
       'valid_strict_n_ge5':st['30']['n']>=5,
       'valid_strict_5_pos':st['5']['ev'] is not None and st['5']['ev']>0,
       'valid_strict_30_pos':st['30']['ev'] is not None and st['30']['ev']>0,
       'valid_median_premove_le010':pre['median'] is not None and pre['median']<=.10}
    c['pass']=all(c.values()); return c

def main():
    base=load(BASE,'base'); lt=load(LT,'lt')
    work=ROOT/'_microlead002'; work.mkdir(parents=True,exist_ok=True)
    az=work/'amp.zip'
    if not az.exists(): base.download(base.AMP_URL,az)
    if base.sha(az)!=base.AMP_SHA: raise SystemExit('AMP SHA mismatch')
    t=read_amp_ticks(az); atr_map=m1_atr_map(t)
    xt,xb,xa,file_stats=lt.read_xau_ticks()
    xm1=lt.build_xau_m1(xt,xb,xa); xatr=lt.xau_atr_lookup(xm1)
    mid=(xb+xa)/2.0
    rows=[]
    for w in WINDOWS:
        b=causal_features(aggregate_window(t,w),w,atr_map)
        for mech in MECHS:
            for i,direction in select_events(b,w,mech):
                r=b.iloc[i]; end_ms=int(r.end_ms); start_ms=int(r.bucket)
                broker_end=end_ms+CLOCK_OFFSET_MIN*60000; broker_start=start_ms+CLOCK_OFFSET_MIN*60000
                ie,lag=first_idx(xt,broker_end); is0,_=first_idx(xt,broker_start)
                if ie is None or is0 is None: continue
                prev_min=((broker_end//60000)*60000)-60000
                atr=float(xatr.get(prev_min,np.nan))
                if not np.isfinite(atr) or atr<=0: continue
                entry=float(xa[ie] if direction>0 else xb[ie])
                pre=direction*(float(mid[ie])-float(mid[is0]))/atr
                rec={'window_s':w,'mechanism':mech,'period':period(end_ms),'gc_start_ms':start_ms,'gc_end_ms':end_ms,
                     'gc_end_utc':pd.to_datetime(end_ms,unit='ms',utc=True).isoformat(),'direction':direction,
                     'side':'LONG' if direction>0 else 'SHORT','gc_delta_frac':float(r.delta_frac),'gc_volume':float(r.volume),
                     'gc_impact':float(r.impact),'gc_q20':float(r.impact_q20) if np.isfinite(r.impact_q20) else np.nan,
                     'gc_q80':float(r.impact_q80) if np.isfinite(r.impact_q80) else np.nan,'xau_atr':atr,
                     'pre_move_atr':float(pre),'entry_lag_ms':lag,'entry_price':entry}
                for h in HORIZONS:
                    j,l=first_idx(xt,broker_end+h*1000)
                    if j is None:
                        rec[f'ret_{h}s_atr']=np.nan; rec[f'ret_{h}s_bps']=np.nan
                    else:
                        exitpx=float(xb[j] if direction>0 else xa[j])
                        pnl=direction*(exitpx-entry)
                        rec[f'ret_{h}s_atr']=pnl/atr; rec[f'ret_{h}s_bps']=pnl/entry*10000.0
                rows.append(rec)
    ev=pd.DataFrame(rows); ev.to_csv(OUT_EVENTS,index=False)
    results={}; passing=[]
    for w in WINDOWS:
        for mech in MECHS:
            key=f'{w}s_{mech}'; d=ev[(ev.window_s==w)&(ev.mechanism==mech)].copy()
            s=summarize(d); g=gate(s); results[key]={'window_s':w,'mechanism':mech,'summary':s,'gate':g}
            if g['pass']: passing.append(key)
    winner=None
    if passing:
        def score(k):
            s=results[k]['summary']
            vals=[s['TRAIN']['all']['5']['ev'],s['VALID']['all']['5']['ev'],s['TRAIN']['all']['30']['ev'],s['VALID']['all']['30']['ev'],s['VALID']['strict']['5']['ev'],s['VALID']['strict']['30']['ev']]
            return min(vals)
        winner=max(passing,key=score)
    out={'lab':'GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002','status':'HISTORICAL_BOUNDED_DISCOVERY_NOT_OOS',
         'passing':passing,'winner':winner,'results':results,'xau_file_stats':file_stats}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
    def f(x): return 'NA' if x is None else f'{x:+.3f}'
    lines=['# GC_XAU_MICRO_LEAD_LAG_FLOW_BURST_LAB002','','Status: HISTORICAL_BOUNDED_DISCOVERY_NOT_OOS','',
           '| Candidate | Gate | TrainN | Tr5 | Tr30 | ValidN | Va5 | Va30 | StrictN | S5 | S30 | PreMed | Post30 |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for k,v in results.items():
        s=v['summary']; g=v['gate']
        lines.append(f"| {k} | {'PASS' if g['pass'] else 'FAIL'} | {s['TRAIN']['all']['30']['n']} | {f(s['TRAIN']['all']['5']['ev'])} | {f(s['TRAIN']['all']['30']['ev'])} | {s['VALID']['all']['30']['n']} | {f(s['VALID']['all']['5']['ev'])} | {f(s['VALID']['all']['30']['ev'])} | {s['VALID']['strict']['30']['n']} | {f(s['VALID']['strict']['5']['ev'])} | {f(s['VALID']['strict']['30']['ev'])} | {f(s['VALID']['pre']['median'])} | {f(s['POST_CHECK']['all']['30']['ev'])} |")
    lines += ['',f'Passing: {passing if passing else "NONE"}',f'Nominated: {winner or "NONE"}','',
              'STRICT means XAU had not yet moved in the predicted direction during the GC burst itself.',
              'POST_CHECK was not used for nomination. Spread is embedded through executable Bid/Ask.',
              'Historical discovery only; no EA authorization.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
