#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
LAB2=ROOT/'gc_xau_micro_lead_lag_flow_burst_lab002.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005.json'
OUT_MD=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005.md'
OUT_EVENTS=ROOT/'GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005_EVENTS.csv'

CLOCK_OFFSET_MIN=180
STALE_MS=2000
COOLDOWN_MS=60000
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
VARIANTS={
 'MARKET_NOW':(0.0,0),
 'LIMIT_005_15S':(0.05,15000),
 'LIMIT_005_30S':(0.05,30000),
 'LIMIT_010_15S':(0.10,15000),
 'LIMIT_010_30S':(0.10,30000),
}
GEOMS={'G15':(0.50,0.75),'G20':(0.50,1.00)}
FP_POS=(0.25,0.50,1.00,2.00,3.00)
FP_NEG=(0.25,0.50,1.00)

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader;spec.loader.exec_module(m);return m

def period(ms):
    t=pd.to_datetime(ms,unit='ms',utc=True)
    if t<TRAIN_END:return 'TRAIN'
    if t<VALID_END:return 'VALID'
    return 'POST_CHECK'

def first_idx(t,target,maxlag=STALE_MS):
    i=int(np.searchsorted(t,target,side='left'))
    if i>=len(t):return None,None
    lag=int(t[i]-target)
    if lag<0 or lag>maxlag:return None,lag
    return i,lag

def build_signals(gt,atrmap):
    width=30000
    bucket=(gt.time_msc.astype('int64')//width)*width
    x=gt.assign(bucket=bucket,
                buy=np.where(gt.sgn.eq(1),gt.vol,0.0),
                sell=np.where(gt.sgn.eq(-1),gt.vol,0.0))
    g=x.groupby('bucket',sort=True,observed=True)
    b=g['last'].agg(open='first',high='max',low='min',close='last')
    b['buy_vol']=g.buy.sum();b['sell_vol']=g.sell.sum()
    b['delta']=b.buy_vol-b.sell_vol;b['volume']=b.buy_vol+b.sell_vol
    b=b.reset_index();b['end_ms']=b.bucket+width
    b['crowd_dir']=np.sign(b.delta).astype(int)
    atr=[]
    for ms in b.end_ms.to_numpy(np.int64):
        prev=((ms//60000)*60000)-60000
        atr.append(atrmap.get(prev,np.nan))
    b['gc_atr']=atr
    b['impact']=b.crowd_dir*(b.close-b.open)/b.gc_atr
    rows=[];last=-10**18
    for i in range(1,len(b)):
        r1=b.iloc[i-1];r2=b.iloc[i]
        if int(r2.bucket)!=int(r1.end_ms):continue
        d1=int(r1.crowd_dir);d2=int(r2.crowd_dir)
        if d1==0 or d2==0 or d1!=d2:continue
        if not np.isfinite(r1.impact) or not np.isfinite(r2.impact):continue
        if float(r2.impact)>float(r1.impact):continue
        t0=int(r2.end_ms)
        if t0-last<COOLDOWN_MS:continue
        last=t0
        rows.append({'gc_t0_ms':t0,'crowd_dir':d2,'direction':-d2,
                     'attack1_delta':float(r1.delta),'attack2_delta':float(r2.delta),
                     'attack1_volume':float(r1.volume),'attack2_volume':float(r2.volume),
                     'attack1_impact':float(r1.impact),'attack2_impact':float(r2.impact),
                     'impact_deterioration':float(r1.impact-r2.impact)})
    return pd.DataFrame(rows)

def first_passage(times,mid,start_i,end_i,m0,d,atr):
    s=d*(mid[start_i:end_i+1]-m0)/atr
    out={}
    for th in FP_POS:
        ix=np.flatnonzero(s>=th)
        out[f'fp_pos_{th:.2f}_ms']=int(times[start_i+ix[0]]-times[start_i]) if len(ix) else np.nan
    for th in FP_NEG:
        ix=np.flatnonzero(s<=-th)
        out[f'fp_neg_{th:.2f}_ms']=int(times[start_i+ix[0]]-times[start_i]) if len(ix) else np.nan
    out['mfe5_atr']=float(np.nanmax(s));out['mae5_atr']=float(np.nanmin(s))
    return out

def find_entry(name,depth,expiry,t,bid,ask,start_i,broker_t0,d,atr):
    if name=='MARKET_NOW':
        return start_i,float(ask[start_i] if d>0 else bid[start_i])
    deadline=broker_t0+expiry
    end=int(np.searchsorted(t,deadline,side='right'))
    b0=float(bid[start_i]);a0=float(ask[start_i])
    limit=(a0-depth*atr) if d>0 else (b0+depth*atr)
    if d>0:
        z=np.flatnonzero(ask[start_i:end]<=limit)
    else:
        z=np.flatnonzero(bid[start_i:end]>=limit)
    if not len(z):return None,None
    j=start_i+int(z[0])
    return j,float(limit)

def sim_geom(t,bid,ask,entry_i,entry,d,atr,hard_i,slatr,tpatr):
    px=bid[entry_i:hard_i+1] if d>0 else ask[entry_i:hard_i+1]
    signed=d*(px-entry)/atr
    ihit_sl=np.flatnonzero(signed<=-slatr)
    ihit_tp=np.flatnonzero(signed>=tpatr)
    a=int(ihit_sl[0]) if len(ihit_sl) else None
    b=int(ihit_tp[0]) if len(ihit_tp) else None
    if a is not None and (b is None or a<=b):return -1.0,'SL'
    if b is not None:return float(tpatr/slatr),'TP'
    final=float(signed[-1]/slatr)
    return final,'TIME'

def pf(v):
    x=np.asarray(v,float);p=x[x>0].sum();n=-x[x<0].sum()
    if n==0:return float('inf') if p>0 else None
    return float(p/n)

def stat(v):
    x=np.asarray([a for a in v if np.isfinite(a)],float)
    return {'n':int(len(x)),'ev':float(x.mean()) if len(x) else None,
            'median':float(np.median(x)) if len(x) else None,
            'wr':float((x>0).mean()*100) if len(x) else None,
            'pf':pf(x) if len(x) else None}

def summarize(ev,subset,variant,p):
    z=ev[(ev.variant==variant)&((ev.period==p) if p!='FULL' else True)]
    if subset=='QUIET':z=z[z.quiet_start==True]
    f=z[z.filled==True]
    out={'signals':int(len(z)),'fills':int(len(f)),'fill_rate':float(len(f)/len(z)) if len(z) else None,
         'hold300':stat(f.hold300_atr.to_numpy(float))}
    for g in GEOMS:
        out[g]=stat(f[f'{g}_r'].to_numpy(float))
        out[g]['tp']=int((f[f'{g}_reason']=='TP').sum());out[g]['sl']=int((f[f'{g}_reason']=='SL').sum())
    # missed winner = causal signal reaches +2ATR from t0 but limit did not fill
    winners=z[z.hit2==True]
    out['plus2_signals']=int(len(winners))
    out['missed_plus2']=int((winners.filled==False).sum())
    out['missed_plus2_rate']=float((winners.filled==False).mean()) if len(winners) else None
    return out

def main():
    l2=load(LAB2,'l2');lt=load(LT,'lt')
    work=ROOT/'_lab005rfa';work.mkdir(exist_ok=True)
    base=l2.load(l2.BASE,'base');az=work/'amp.zip'
    if not az.exists():base.download(base.AMP_URL,az)
    if base.sha(az)!=base.AMP_SHA:raise SystemExit('AMP SHA mismatch')
    gt=l2.read_amp_ticks(az);gatr=l2.m1_atr_map(gt)
    sig=build_signals(gt,gatr)

    t,bid,ask,_=lt.read_xau_ticks();mid=(bid+ask)/2.0
    xm1=lt.build_xau_m1(t,bid,ask);xatr=lt.xau_atr_lookup(xm1)
    rows=[]
    for r in sig.itertuples(index=False):
        broker=int(r.gc_t0_ms)+CLOCK_OFFSET_MIN*60000
        i,lag=first_idx(t,broker)
        hard,_=first_idx(t,broker+300000,maxlag=5000)
        prior,_=first_idx(t,broker-30000,maxlag=5000)
        if i is None or hard is None or prior is None:continue
        prev=((broker//60000)*60000)-60000
        atr=float(xatr.get(prev,np.nan))
        if not np.isfinite(atr) or atr<=0:continue
        d=int(r.direction);m0=float(mid[i])
        quiet=abs(m0-float(mid[prior]))/atr<=.25
        fp=first_passage(t,mid,i,hard,m0,d,atr)
        base_rec={'gc_t0_ms':int(r.gc_t0_ms),'event_utc':pd.to_datetime(r.gc_t0_ms,unit='ms',utc=True).isoformat(),
                  'period':period(int(r.gc_t0_ms)),'crowd_dir':int(r.crowd_dir),'direction':d,'side':'LONG' if d>0 else 'SHORT',
                  'quiet_start':bool(quiet),'xau_atr':atr,'entry_lag_ms':lag,
                  'attack1_impact':float(r.attack1_impact),'attack2_impact':float(r.attack2_impact),
                  'impact_deterioration':float(r.impact_deterioration),**fp,
                  'hit2':bool(np.isfinite(fp['fp_pos_2.00_ms'])),'hit3':bool(np.isfinite(fp['fp_pos_3.00_ms']))}
        for name,(depth,expiry) in VARIANTS.items():
            ei,entry=find_entry(name,depth,expiry,t,bid,ask,i,broker,d,atr)
            rec=dict(base_rec);rec['variant']=name
            if ei is None:
                rec.update({'filled':False,'fill_delay_ms':np.nan,'entry_price':np.nan,'hold300_atr':np.nan})
                for g in GEOMS:rec[f'{g}_r']=np.nan;rec[f'{g}_reason']='NOFILL'
                rows.append(rec);continue
            rec['filled']=True;rec['fill_delay_ms']=int(t[ei]-broker);rec['entry_price']=float(entry)
            xp=float(bid[hard] if d>0 else ask[hard]);rec['hold300_atr']=d*(xp-entry)/atr
            for g,(sl,tp) in GEOMS.items():
                rr,reason=sim_geom(t,bid,ask,ei,float(entry),d,atr,hard,sl,tp)
                rec[f'{g}_r']=float(rr);rec[f'{g}_reason']=reason
            rows.append(rec)
    ev=pd.DataFrame(rows);ev.to_csv(OUT_EVENTS,index=False)

    baseev=ev[ev.variant=='MARKET_NOW'].copy()
    timing={}
    for subset in ('ALL','QUIET'):
        z=baseev if subset=='ALL' else baseev[baseev.quiet_start==True]
        timing[subset]={}
        for p in ('TRAIN','VALID','POST_CHECK','FULL'):
            q=z if p=='FULL' else z[z.period==p]
            w=q[q.hit2==True]
            vals=w['fp_pos_0.50_ms'].dropna().to_numpy(float)/1000.0
            timing[subset][p]={
              'n':int(len(q)),'plus2_rate':float(q.hit2.mean()) if len(q) else None,
              'plus3_rate':float(q.hit3.mean()) if len(q) else None,
              'median_t025_s':float(q['fp_pos_0.25_ms'].dropna().median()/1000) if len(q['fp_pos_0.25_ms'].dropna()) else None,
              'median_t050_s':float(q['fp_pos_0.50_ms'].dropna().median()/1000) if len(q['fp_pos_0.50_ms'].dropna()) else None,
              'median_t100_s':float(q['fp_pos_1.00_ms'].dropna().median()/1000) if len(q['fp_pos_1.00_ms'].dropna()) else None,
              'median_t050_on_plus2_s':float(np.median(vals)) if len(vals) else None,
              'mfe5_mean':float(q.mfe5_atr.mean()) if len(q) else None,'mae5_mean':float(q.mae5_atr.mean()) if len(q) else None,
            }

    execution={sub:{v:{p:summarize(ev,sub,v,p) for p in ('TRAIN','VALID','POST_CHECK','FULL')} for v in VARIANTS} for sub in ('ALL','QUIET')}

    viable=[]
    for sub in ('ALL','QUIET'):
        for v in VARIANTS:
            tr=execution[sub][v]['TRAIN'];va=execution[sub][v]['VALID']
            for g in GEOMS:
                if tr['fills']>=30 and va['fills']>=30 and tr['hold300']['ev'] is not None and tr['hold300']['ev']>0 and va['hold300']['ev'] is not None and va['hold300']['ev']>0 and va[g]['ev'] is not None and va[g]['ev']>0 and va[g]['pf'] is not None and va[g]['pf']>=1.10:
                    viable.append(f'{sub}:{v}:{g}')

    out={'lab':'GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005','status':'CAUSAL_EXECUTION_AUDIT_NOT_OOS',
         'timing':timing,'execution':execution,'historical_viable_candidates':viable}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(x):return 'NA' if x is None else f'{x:+.3f}'
    def pct(x):return 'NA' if x is None else f'{x*100:.1f}%'
    lines=['# GC_XAU_REPEATED_FAILED_ATTACK_CAUSAL_EXECUTION_LAB005','','Status: CAUSAL_EXECUTION_AUDIT_NOT_OOS','',
           '## Causal timing — no future XAU information in signal','',
           '| Subset | Period | N | +2ATR<=5m | +3ATR<=5m | med t0.25 | med t0.50 | med t1.0 | med t0.50 on +2 winners |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for sub in ('ALL','QUIET'):
        for p in ('TRAIN','VALID','POST_CHECK'):
            x=timing[sub][p]
            lines.append(f"| {sub} | {p} | {x['n']} | {pct(x['plus2_rate'])} | {pct(x['plus3_rate'])} | {('NA' if x['median_t025_s'] is None else f'{x['median_t025_s']:.1f}s')} | {('NA' if x['median_t050_s'] is None else f'{x['median_t050_s']:.1f}s')} | {('NA' if x['median_t100_s'] is None else f'{x['median_t100_s']:.1f}s')} | {('NA' if x['median_t050_on_plus2_s'] is None else f'{x['median_t050_on_plus2_s']:.1f}s')} |")
    lines+=['','## QUIET_START execution','',
            '| Variant | Period | Fills | Fill% | Hold300 EV ATR | G15 EV/PF | G20 EV/PF | Missed +2 winners |',
            '|---|---|---:|---:|---:|---:|---:|---:|']
    for v in VARIANTS:
        for p in ('TRAIN','VALID','POST_CHECK'):
            x=execution['QUIET'][v][p];g15=x['G15'];g20=x['G20']
            lines.append(f"| {v} | {p} | {x['fills']} | {pct(x['fill_rate'])} | {f(x['hold300']['ev'])} | {f(g15['ev'])}/{f(g15['pf'])} | {f(g20['ev'])}/{f(g20['pf'])} | {pct(x['missed_plus2_rate'])} |")
    lines+=['',f'Historical viable candidates: {viable if viable else "NONE"}','',
            'No signal threshold, session filter, entry depth, expiry, SL, TP, or timeout was optimized after seeing outcomes.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(OUT_MD.read_text())

if __name__=='__main__':main()
