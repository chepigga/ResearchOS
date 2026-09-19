#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
LAB5=ROOT/'gc_xau_repeated_failed_attack_causal_execution_lab005.py'
LAB2=ROOT/'gc_xau_micro_lead_lag_flow_burst_lab002.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_BIG_MOVE_DISCRIMINATOR_INSIDE_REPEATED_FAILED_ATTACK_LAB006.json'
OUT_MD=ROOT/'GC_XAU_BIG_MOVE_DISCRIMINATOR_INSIDE_REPEATED_FAILED_ATTACK_LAB006.md'
OUT_EVENTS=ROOT/'GC_XAU_BIG_MOVE_DISCRIMINATOR_INSIDE_REPEATED_FAILED_ATTACK_LAB006_EVENTS.csv'

CLOCK_OFFSET_MIN=180
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
STALE_MS=2000
FEATURES=[
 'attack1_impact','attack2_impact','impact_deterioration',
 'attack1_delta_frac','attack2_delta_frac','abs_delta_frac_1','abs_delta_frac_2',
 'attack1_volume','attack2_volume','volume_ratio_2_to_1','persistence_abs_delta',
 'efficiency1','efficiency2','efficiency_deterioration',
 'prior30_abs_move_atr','prior30_signed_pred_move_atr',
 'prior60_signed_pred_move_atr','prior60_range_atr',
 'gc_pred_60_atr','gc_minus_xau_signed_context'
]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    return m

def period(ms):
    t=pd.to_datetime(ms,unit='ms',utc=True)
    if t<TRAIN_END:return 'TRAIN'
    if t<VALID_END:return 'VALID'
    return 'POST_CHECK'

def first_idx(t,target,maxlag=STALE_MS):
    i=int(np.searchsorted(t,target,side='left'))
    if i>=len(t):return None
    lag=int(t[i]-target)
    if lag<0 or lag>maxlag:return None
    return i

def exact_gc_window(gt,start_ms,end_ms):
    tt=gt.time_msc.to_numpy(np.int64)
    i=int(np.searchsorted(tt,start_ms,side='left'))
    j=int(np.searchsorted(tt,end_ms,side='left'))
    if j<=i:return None
    z=gt.iloc[i:j]
    buy=float(z.loc[z.sgn==1,'vol'].sum())
    sell=float(z.loc[z.sgn==-1,'vol'].sum())
    vol=buy+sell
    if vol<=0:return None
    return {
      'open':float(z['last'].iloc[0]),
      'close':float(z['last'].iloc[-1]),
      'high':float(z['last'].max()),
      'low':float(z['last'].min()),
      'buy':buy,'sell':sell,'volume':vol,'delta':buy-sell,
      'delta_frac':(buy-sell)/vol
    }

def future_hits(t,mid,start_i,end_i,m0,d,atr):
    s=d*(mid[start_i:end_i+1]-m0)/atr
    return bool(np.nanmax(s)>=2.0), bool(np.nanmax(s)>=3.0)

def pct_rate(z,col):
    if len(z)==0:return None
    return float(z[col].mean())

def lift(rate,base):
    if rate is None or base is None:return None
    if base<=0:return None
    return float(rate/base)

def side_mask(x,side,thr):
    if side=='Q1':return x<=thr
    return x>=thr

def summarize_bin(df,feature,side,thr,subset):
    out={}
    for p in ('TRAIN','VALID','POST_CHECK'):
        base=df[(df.period==p) & ((df.quiet_start==True) if subset=='QUIET' else True)].copy()
        xv=pd.to_numeric(base[feature],errors='coerce')
        z=base[side_mask(xv,side,thr)]
        b2=pct_rate(base,'big2');b3=pct_rate(base,'big3')
        r2=pct_rate(z,'big2');r3=pct_rate(z,'big3')
        out[p]={
          'n':int(len(z)),
          'big2_rate':r2,'big3_rate':r3,
          'base2_rate':b2,'base3_rate':b3,
          'big2_lift':lift(r2,b2),'big3_lift':lift(r3,b3)
        }
    return out

def survives(s):
    tr=s['TRAIN'];va=s['VALID']
    checks={
      'train_n_ge100':tr['n']>=100,
      'valid_n_ge100':va['n']>=100,
      'train_big2_lift_ge125':tr['big2_lift'] is not None and tr['big2_lift']>=1.25,
      'valid_big2_lift_ge120':va['big2_lift'] is not None and va['big2_lift']>=1.20,
      'train_big3_lift_ge120':tr['big3_lift'] is not None and tr['big3_lift']>=1.20,
      'valid_big3_lift_ge115':va['big3_lift'] is not None and va['big3_lift']>=1.15,
    }
    checks['pass']=all(checks.values())
    return checks

def main():
    l5=load(LAB5,'l5');l2=load(LAB2,'l2');lt=load(LT,'lt')
    work=ROOT/'_lab006disc';work.mkdir(exist_ok=True)
    base=l2.load(l2.BASE,'base')
    az=work/'amp.zip'
    if not az.exists():base.download(base.AMP_URL,az)
    if base.sha(az)!=base.AMP_SHA:raise SystemExit('AMP SHA mismatch')

    gt=l2.read_amp_ticks(az)
    gatr=l2.m1_atr_map(gt)
    sig=l5.build_signals(gt,gatr)

    t,bid,ask,_=lt.read_xau_ticks()
    mid=(bid+ask)/2.0
    xm1=lt.build_xau_m1(t,bid,ask)
    xatr=lt.xau_atr_lookup(xm1)

    rows=[]
    for r in sig.itertuples(index=False):
        gc_t0=int(r.gc_t0_ms)
        broker=gc_t0+CLOCK_OFFSET_MIN*60000
        i=first_idx(t,broker)
        p30=first_idx(t,broker-30000,maxlag=5000)
        p60=first_idx(t,broker-60000,maxlag=5000)
        hard=first_idx(t,broker+300000,maxlag=5000)
        if None in (i,p30,p60,hard):continue

        prev=((broker//60000)*60000)-60000
        atr=float(xatr.get(prev,np.nan))
        gprev=((gc_t0//60000)*60000)-60000
        gatrv=float(gatr.get(gprev,np.nan))
        if not np.isfinite(atr) or atr<=0 or not np.isfinite(gatrv) or gatrv<=0:continue

        d=int(r.direction)
        m0=float(mid[i])
        prior30_signed=d*(m0-float(mid[p30]))/atr
        prior60_signed=d*(m0-float(mid[p60]))/atr
        prior30_abs=abs(m0-float(mid[p30]))/atr
        path60=mid[p60:i+1]
        prior60_range=(float(np.nanmax(path60))-float(np.nanmin(path60)))/atr if len(path60) else np.nan
        quiet=prior30_abs<=.25

        a1df=float(r.attack1_delta/r.attack1_volume) if r.attack1_volume>0 else np.nan
        a2df=float(r.attack2_delta/r.attack2_volume) if r.attack2_volume>0 else np.nan
        ad1=abs(a1df);ad2=abs(a2df)
        eps=1e-9
        eff1=float(r.attack1_impact)/max(ad1,eps)
        eff2=float(r.attack2_impact)/max(ad2,eps)

        g60=exact_gc_window(gt,gc_t0-60000,gc_t0)
        if g60 is None:continue
        gc_pred60=d*(g60['close']-g60['open'])/gatrv

        big2,big3=future_hits(t,mid,i,hard,m0,d,atr)
        rows.append({
          'gc_t0_ms':gc_t0,'event_utc':pd.to_datetime(gc_t0,unit='ms',utc=True).isoformat(),
          'period':period(gc_t0),'direction':d,'quiet_start':bool(quiet),
          'big2':bool(big2),'big3':bool(big3),
          'attack1_impact':float(r.attack1_impact),
          'attack2_impact':float(r.attack2_impact),
          'impact_deterioration':float(r.impact_deterioration),
          'attack1_delta_frac':a1df,'attack2_delta_frac':a2df,
          'abs_delta_frac_1':ad1,'abs_delta_frac_2':ad2,
          'attack1_volume':float(r.attack1_volume),'attack2_volume':float(r.attack2_volume),
          'volume_ratio_2_to_1':float(r.attack2_volume/r.attack1_volume) if r.attack1_volume>0 else np.nan,
          'persistence_abs_delta':min(ad1,ad2),
          'efficiency1':eff1,'efficiency2':eff2,
          'efficiency_deterioration':eff1-eff2,
          'prior30_abs_move_atr':prior30_abs,
          'prior30_signed_pred_move_atr':prior30_signed,
          'prior60_signed_pred_move_atr':prior60_signed,
          'prior60_range_atr':prior60_range,
          'gc_pred_60_atr':gc_pred60,
          'gc_minus_xau_signed_context':gc_pred60-prior60_signed,
          'utc_hour':pd.to_datetime(gc_t0,unit='ms',utc=True).hour
        })

    ev=pd.DataFrame(rows)
    ev.to_csv(OUT_EVENTS,index=False)

    trainq=ev[(ev.period=='TRAIN')&(ev.quiet_start==True)].copy()
    results={}
    survivors=[]
    for feat in FEATURES:
        x=pd.to_numeric(trainq[feat],errors='coerce').dropna()
        if len(x)<500:continue
        q20=float(x.quantile(.20));q80=float(x.quantile(.80))
        candidates=[]
        for side,thr in (('Q1',q20),('Q5',q80)):
            s=summarize_bin(ev,feat,side,thr,'QUIET')
            tr=s['TRAIN']
            score=-1e9 if tr['big2_lift'] is None else tr['big2_lift']
            candidates.append((score,side,thr,s))
        candidates.sort(key=lambda z:z[0],reverse=True)
        _,side,thr,s=candidates[0]
        checks=survives(s)
        results[feat]={'side':side,'threshold':thr,'summary':s,'gate':checks}
        if checks['pass']:
            score=min(s['TRAIN']['big2_lift'],s['VALID']['big2_lift'])
            survivors.append((score,feat))

    survivors.sort(reverse=True)
    pair=None
    if len(survivors)>=2:
        f1=survivors[0][1];f2=survivors[1][1]
        r1=results[f1];r2=results[f2]
        psummary={}
        for p in ('TRAIN','VALID','POST_CHECK'):
            basep=ev[(ev.period==p)&(ev.quiet_start==True)].copy()
            m1=side_mask(pd.to_numeric(basep[f1],errors='coerce'),r1['side'],r1['threshold'])
            m2=side_mask(pd.to_numeric(basep[f2],errors='coerce'),r2['side'],r2['threshold'])
            z=basep[m1&m2]
            b2=pct_rate(basep,'big2');b3=pct_rate(basep,'big3')
            r2v=pct_rate(z,'big2');r3v=pct_rate(z,'big3')
            psummary[p]={
              'n':int(len(z)),'big2_rate':r2v,'big3_rate':r3v,
              'big2_lift':lift(r2v,b2),'big3_lift':lift(r3v,b3)
            }
        pair={'features':[f1,f2],'summary':psummary}

    bases={}
    for subset in ('ALL','QUIET'):
        bases[subset]={}
        for p in ('TRAIN','VALID','POST_CHECK'):
            z=ev[ev.period==p]
            if subset=='QUIET':z=z[z.quiet_start==True]
            bases[subset][p]={'n':int(len(z)),'big2_rate':pct_rate(z,'big2'),'big3_rate':pct_rate(z,'big3')}

    out={
      'lab':'GC_XAU_BIG_MOVE_DISCRIMINATOR_INSIDE_REPEATED_FAILED_ATTACK_LAB006',
      'status':'CAUSAL_DISCRIMINATOR_DISCOVERY_NOT_OOS',
      'base_rates':bases,
      'results':results,
      'survivors':[x[1] for x in survivors],
      'pair':pair
    }
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(x,d=2):
        return 'NA' if x is None or (isinstance(x,float) and not np.isfinite(x)) else f'{x:.{d}f}'
    lines=[
      '# GC_XAU_BIG_MOVE_DISCRIMINATOR_INSIDE_REPEATED_FAILED_ATTACK_LAB006','',
      'Status: CAUSAL_DISCRIMINATOR_DISCOVERY_NOT_OOS','',
      '## Base causal hit rates','',
      '| Subset | Period | N | +2 ATR <=5m | +3 ATR <=5m |',
      '|---|---|---:|---:|---:|'
    ]
    for subset in ('ALL','QUIET'):
        for p in ('TRAIN','VALID','POST_CHECK'):
            b=bases[subset][p]
            lines.append(f"| {subset} | {p} | {b['n']} | {f(None if b['big2_rate'] is None else b['big2_rate']*100,1)}% | {f(None if b['big3_rate'] is None else b['big3_rate']*100,1)}% |")
    lines += ['','## Frozen TRAIN-tail feature tests','',
              '| Feature | Tail | Threshold | Train N | T +2 lift | T +3 lift | Valid N | V +2 lift | V +3 lift | Post +2 lift | Gate |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    ordered=sorted(results.items(),key=lambda kv: (0 if kv[1]['gate']['pass'] else 1, -(kv[1]['summary']['VALID']['big2_lift'] or -999)))
    for feat,r in ordered:
        tr=r['summary']['TRAIN'];va=r['summary']['VALID'];po=r['summary']['POST_CHECK']
        lines.append(f"| {feat} | {r['side']} | {f(r['threshold'],4)} | {tr['n']} | {f(tr['big2_lift'])}x | {f(tr['big3_lift'])}x | {va['n']} | {f(va['big2_lift'])}x | {f(va['big3_lift'])}x | {f(po['big2_lift'])}x | {'PASS' if r['gate']['pass'] else 'FAIL'} |")
    lines += ['',f"Survivors: {out['survivors'] if out['survivors'] else 'NONE'}"]
    if pair:
        lines += ['',f"Top-two pair: {pair['features']}"]
        for p in ('TRAIN','VALID','POST_CHECK'):
            x=pair['summary'][p]
            lines.append(f"- {p}: N={x['n']}, +2 lift={f(x['big2_lift'])}x, +3 lift={f(x['big3_lift'])}x")
    lines += ['','No execution optimization was performed. Thresholds are TRAIN-only quintile edges, frozen before VALID/POST evaluation.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
