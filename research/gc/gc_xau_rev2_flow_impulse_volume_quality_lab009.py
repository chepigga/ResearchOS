#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
LAB2=ROOT/'gc_xau_micro_lead_lag_flow_burst_lab002.py'
LAB5=ROOT/'gc_xau_repeated_failed_attack_causal_execution_lab005.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
REV=ROOT/'GC_XAU_DOMINANCE_REVERSAL_MECHANISM_AND_TIMING_LAB007D_EVENTS.csv'

OUT_JSON=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009.json'
OUT_MD=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009.md'
OUT_EVENTS=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009_EVENTS.csv'

CLOCK_OFFSET_MIN=180
WINDOWS=(0,5,15,30)
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
STALE_MS=2000

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

def window_stats(gt,start_ms,end_ms,d,gatr):
    tt=gt.time_msc.to_numpy(np.int64)
    i=int(np.searchsorted(tt,start_ms,side='left'))
    j=int(np.searchsorted(tt,end_ms,side='left'))
    if j<=i:return None
    z=gt.iloc[i:j]
    buy=float(z.loc[z.sgn==1,'vol'].sum())
    sell=float(z.loc[z.sgn==-1,'vol'].sum())
    vol=buy+sell
    if vol<=0:return None
    aligned_buy=buy if d>0 else sell
    aligned_sell=sell if d>0 else buy
    openp=float(z['last'].iloc[0]); closep=float(z['last'].iloc[-1])
    aligned_df=(aligned_buy-aligned_sell)/vol
    return {
      'volume':vol,
      'aligned_volume':aligned_buy,
      'opposite_volume':aligned_sell,
      'aligned_share':aligned_buy/vol,
      'aligned_delta_frac':aligned_df,
      'signed_impulse_atr':d*(closep-openp)/gatr if gatr>0 else np.nan,
      'impulse_efficiency':(d*(closep-openp)/gatr)/vol if gatr>0 and vol>0 else np.nan,
    }

def xau_outcome(t,bid,ask,mid,start_ms,d,atr):
    i=first_idx(t,start_ms)
    if i is None:return None
    end_target=start_ms+300000
    j=int(np.searchsorted(t,end_target,side='right'))-1
    if j<=i:return None
    m0=float(mid[i])
    signed=d*(mid[i:j+1]-m0)/atr
    hit2=bool(np.nanmax(signed)>=2.0)
    hit3=bool(np.nanmax(signed)>=3.0)
    ix50=np.flatnonzero(signed>=0.50)
    t50=float((t[i+ix50[0]]-t[i])/1000.0) if len(ix50) else np.nan
    entry=float(ask[i] if d>0 else bid[i])
    exitp=float(bid[j] if d>0 else ask[j])
    fixed=float(d*(exitp-entry)/atr)
    return {'hit2':hit2,'hit3':hit3,'t50_s':t50,'fixed5m_atr':fixed,'entry_i':i,'end_i':j,'mid0':m0}

def select_tail(df,feature):
    train=df[(df.period=='TRAIN') & df[feature].notna()].copy()
    if len(train)<40:return None
    q20=float(train[feature].quantile(.20));q80=float(train[feature].quantile(.80))
    base2=float(train.hit2.mean()) if len(train) else np.nan
    cand=[]
    for side,thr in [('Q1',q20),('Q5',q80)]:
        z=train[train[feature]<=thr] if side=='Q1' else train[train[feature]>=thr]
        rate=float(z.hit2.mean()) if len(z) else np.nan
        lift=rate/base2 if base2>0 and np.isfinite(rate) else np.nan
        cand.append((lift,side,thr))
    cand=[x for x in cand if np.isfinite(x[0])]
    if not cand:return None
    cand.sort(reverse=True,key=lambda x:x[0])
    return cand[0][1],cand[0][2]

def eval_tail(df,feature,side,thr):
    out={}
    for p in ('TRAIN','VALID','POST_CHECK'):
        base=df[(df.period==p) & df[feature].notna()]
        z=base[base[feature]<=thr] if side=='Q1' else base[base[feature]>=thr]
        base2=float(base.hit2.mean()) if len(base) else None
        r2=float(z.hit2.mean()) if len(z) else None
        lift=(r2/base2) if (r2 is not None and base2 is not None and base2>0) else None
        ev=float(z.fixed5m_atr.mean()) if len(z) else None
        out[p]={'n':int(len(z)),'base_n':int(len(base)),'hit2':r2,'base2':base2,'lift2':lift,
                'hit3':float(z.hit3.mean()) if len(z) else None,'ev':ev,
                't50_med':float(z.loc[z.hit2==True,'t50_s'].dropna().median()) if len(z.loc[z.hit2==True,'t50_s'].dropna()) else None}
    return out

def gate(s):
    tr=s['TRAIN'];va=s['VALID']
    c={
      'train_n_ge30':tr['n']>=30,
      'valid_n_ge30':va['n']>=30,
      'train_lift_ge125':tr['lift2'] is not None and tr['lift2']>=1.25,
      'valid_lift_ge120':va['lift2'] is not None and va['lift2']>=1.20,
      'train_ev_pos':tr['ev'] is not None and tr['ev']>0,
      'valid_ev_pos':va['ev'] is not None and va['ev']>0,
    }
    c['pass']=all(c.values())
    return c

def main():
    l2=load(LAB2,'l2');l5=load(LAB5,'l5');lt=load(LT,'lt')
    work=ROOT/'_lab009';work.mkdir(exist_ok=True)
    base=l2.load(l2.BASE,'base')
    az=work/'amp.zip'
    if not az.exists():base.download(base.AMP_URL,az)
    if base.sha(az)!=base.AMP_SHA:raise SystemExit('AMP SHA mismatch')
    gt=l2.read_amp_ticks(az)
    gatrmap=l2.m1_atr_map(gt)
    sig=l5.build_signals(gt,gatrmap)
    smap={int(r.gc_t0_ms):r for r in sig.itertuples(index=False)}

    rev=pd.read_csv(REV)
    rev=rev[rev.clock=='REV2'].copy().sort_values('gc_t0_ms')

    t,bid,ask,_=lt.read_xau_ticks();mid=(bid+ask)/2.0
    xm1=lt.build_xau_m1(t,bid,ask);xatrmap=lt.xau_atr_lookup(xm1)

    rows=[]
    for rr in rev.itertuples(index=False):
        gc0=int(rr.gc_t0_ms); d=int(rr.reversal_dir)
        sr=smap.get(gc0)
        if sr is None:continue

        gprev=((gc0//60000)*60000)-60000
        gatr=float(gatrmap.get(gprev,np.nan))
        broker0=gc0+CLOCK_OFFSET_MIN*60000
        xprev=((broker0//60000)*60000)-60000
        xatr=float(xatrmap.get(xprev,np.nan))
        if not np.isfinite(gatr) or gatr<=0 or not np.isfinite(xatr) or xatr<=0:continue

        a1vol=float(sr.attack1_volume);a2vol=float(sr.attack2_volume)
        a1df=float(sr.attack1_delta/a1vol) if a1vol>0 else np.nan
        a2df=float(sr.attack2_delta/a2vol) if a2vol>0 else np.nan
        aligned_a2df=d*a2df
        basefeat={
          'attack1_volume':a1vol,
          'attack2_volume':a2vol,
          'volume_ratio_2_to_1':a2vol/a1vol if a1vol>0 else np.nan,
          'attack1_delta_frac_aligned':d*a1df,
          'attack2_delta_frac_aligned':aligned_a2df,
          'abs_attack2_delta_frac':abs(a2df),
          'attack2_signed_impact':float(sr.attack2_impact),
          'impact_deterioration':float(sr.impact_deterioration),
          'rev2_aligned_aggr_share':(1+aligned_a2df)/2 if np.isfinite(aligned_a2df) else np.nan,
        }

        for w in WINDOWS:
            clock_ms=broker0+w*1000
            xout=xau_outcome(t,bid,ask,mid,clock_ms,d,xatr)
            if xout is None:continue
            rec={'gc_t0_ms':gc0,'period':period(gc0),'window_s':w,'direction':d,**basefeat,**xout}

            if w>0:
                post=window_stats(gt,gc0,gc0+w*1000,d,gatr)
                pre=window_stats(gt,gc0-w*1000,gc0,d,gatr)
                if post:
                    rec.update({
                      'post_volume':post['volume'],
                      'post_aligned_volume':post['aligned_volume'],
                      'post_opposite_volume':post['opposite_volume'],
                      'post_aligned_share':post['aligned_share'],
                      'post_aligned_delta_frac':post['aligned_delta_frac'],
                      'post_signed_impulse_atr':post['signed_impulse_atr'],
                      'post_impulse_efficiency':post['impulse_efficiency'],
                    })
                else:
                    rec.update({k:np.nan for k in ['post_volume','post_aligned_volume','post_opposite_volume','post_aligned_share','post_aligned_delta_frac','post_signed_impulse_atr','post_impulse_efficiency']})
                if pre:
                    rec['pre_volume']=pre['volume']
                    rec['pre_aligned_delta_frac']=pre['aligned_delta_frac']
                    rec['volume_acceleration']=post['volume']/pre['volume'] if post and pre['volume']>0 else np.nan
                    rec['aligned_delta_acceleration']=post['aligned_delta_frac']-pre['aligned_delta_frac'] if post else np.nan
                else:
                    rec['pre_volume']=np.nan;rec['pre_aligned_delta_frac']=np.nan;rec['volume_acceleration']=np.nan;rec['aligned_delta_acceleration']=np.nan

                i0=first_idx(t,broker0);iw=first_idx(t,clock_ms)
                if i0 is not None and iw is not None:
                    xau_move=d*(float(mid[iw])-float(mid[i0]))/xatr
                else:xau_move=np.nan
                rec['xau_signed_move_confirm_atr']=xau_move
                rec['gc_xau_lead_gap']=rec.get('post_signed_impulse_atr',np.nan)-xau_move if np.isfinite(xau_move) else np.nan
            rows.append(rec)

    ev=pd.DataFrame(rows)
    ev.to_csv(OUT_EVENTS,index=False)

    layerA=['attack1_volume','attack2_volume','volume_ratio_2_to_1','attack1_delta_frac_aligned',
            'attack2_delta_frac_aligned','abs_attack2_delta_frac','attack2_signed_impact',
            'impact_deterioration','rev2_aligned_aggr_share']
    layerB=['post_volume','post_aligned_volume','post_opposite_volume','post_aligned_share',
            'post_aligned_delta_frac','post_signed_impulse_atr','post_impulse_efficiency',
            'volume_acceleration','aligned_delta_acceleration','xau_signed_move_confirm_atr','gc_xau_lead_gap']

    results=[];survivors=[]
    for w in WINDOWS:
        sub=ev[ev.window_s==w].copy()
        feats=layerA if w==0 else layerB
        for feat in feats:
            if feat not in sub.columns:continue
            sel=select_tail(sub,feat)
            if sel is None:continue
            side,thr=sel
            summ=eval_tail(sub,feat,side,thr)
            g=gate(summ)
            row={'window_s':w,'feature':feat,'side':side,'threshold':thr,'summary':summ,'gate':g}
            results.append(row)
            if g['pass']:survivors.append(row)

    bases={}
    for w in WINDOWS:
        sub=ev[ev.window_s==w]
        bases[str(w)]={}
        for p in ('TRAIN','VALID','POST_CHECK'):
            z=sub[sub.period==p]
            bases[str(w)][p]={'n':int(len(z)),'hit2':float(z.hit2.mean()) if len(z) else None,
                              'hit3':float(z.hit3.mean()) if len(z) else None,
                              'ev':float(z.fixed5m_atr.mean()) if len(z) else None}

    out={'lab':'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009','status':'REV2_QUALITY_DISCOVERY_NOT_OOS',
         'base_by_clock':bases,'results':results,
         'survivors':[{'window_s':r['window_s'],'feature':r['feature'],'side':r['side'],'threshold':r['threshold']} for r in survivors]}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(v,d=3):
        return 'NA' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{v:.{d}f}'
    lines=['# GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009','',
           'Status: REV2_QUALITY_DISCOVERY_NOT_OOS','',
           '## Base by confirmation clock','',
           '| Clock | Period | N | +2ATR | +3ATR | Fixed5m EV ATR |',
           '|---:|---|---:|---:|---:|---:|']
    for w in WINDOWS:
        for p in ('TRAIN','VALID','POST_CHECK'):
            b=bases[str(w)][p]
            lines.append(f"| {w}s | {p} | {b['n']} | {f(None if b['hit2'] is None else b['hit2']*100,1)}% | {f(None if b['hit3'] is None else b['hit3']*100,1)}% | {f(b['ev'])} |")
    lines+=['','## Frozen TRAIN-tail tests','',
            '| Clock | Feature | Tail | Thr | Train N | T lift | T EV | Valid N | V lift | V EV | Post lift | Post EV | Gate |',
            '|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    ordered=sorted(results,key=lambda r:(0 if r['gate']['pass'] else 1,-(r['summary']['VALID']['lift2'] or -999)))
    for r in ordered:
        tr=r['summary']['TRAIN'];va=r['summary']['VALID'];po=r['summary']['POST_CHECK']
        lines.append(f"| {r['window_s']}s | {r['feature']} | {r['side']} | {f(r['threshold'],4)} | {tr['n']} | {f(tr['lift2'],2)}x | {f(tr['ev'])} | {va['n']} | {f(va['lift2'],2)}x | {f(va['ev'])} | {f(po['lift2'],2)}x | {f(po['ev'])} | {'PASS' if r['gate']['pass'] else 'FAIL'} |")
    lines+=['',f"Survivors: {out['survivors'] if out['survivors'] else 'NONE'}",'',
            'Delayed 5s/15s/30s features are evaluated only from their confirmation-end clock; no future leakage from REV2 t0.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
