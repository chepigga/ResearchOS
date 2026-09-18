#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
LAB2=ROOT/'gc_xau_micro_lead_lag_flow_burst_lab002.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_LARGE_MOVE_REVERSE_PRECURSOR_DISCOVERY_LAB004.json'
OUT_MD=ROOT/'GC_XAU_LARGE_MOVE_REVERSE_PRECURSOR_DISCOVERY_LAB004.md'
OUT_EVENTS=ROOT/'GC_XAU_LARGE_MOVE_REVERSE_PRECURSOR_DISCOVERY_LAB004_EVENTS.csv'
OUT_PRE=ROOT/'GC_XAU_LARGE_MOVE_REVERSE_PRECURSOR_DISCOVERY_LAB004_PRECURSORS.csv'

WINDOWS=(1,2,5,10,30,60)
CLOCK_OFFSET_MIN=180
MOVE_ATR=1.0
MOVE_HORIZON_MS=300000
DECLUSTER_MS=300000
CONTROL_OFFSETS_MIN=(-30,-20,20,30,40)
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader;spec.loader.exec_module(m);return m

def period_utc(ms_utc):
    t=pd.to_datetime(ms_utc,unit='ms',utc=True)
    if t<TRAIN_END:return 'TRAIN'
    if t<VALID_END:return 'VALID'
    return 'POST_CHECK'

def build_xau_seconds(times,bids,asks):
    sec=(times//1000)*1000
    mid=(bids+asks)/2.0
    d=pd.DataFrame({'sec':sec,'mid':mid})
    s=d.groupby('sec',sort=True).mid.last().reset_index()
    return s.sec.to_numpy(np.int64),s.mid.to_numpy(float)

def detect_large_moves(sec,mid,atr_map):
    # Candidate scan uses exact future first passage only after a cheap 300-row screen.
    n=len(sec)
    sf=pd.Series(mid)
    fw=pd.api.indexers.FixedForwardWindowIndexer(window_size=301)
    fmax=sf.rolling(fw,min_periods=2).max().to_numpy()
    fmin=sf.rolling(fw,min_periods=2).min().to_numpy()
    rows=[];last_accept=-10**18
    for i in range(n):
        broker_ms=int(sec[i])
        if broker_ms-last_accept<DECLUSTER_MS:continue
        prev_min=((broker_ms//60000)*60000)-60000
        atr=float(atr_map.get(prev_min,np.nan))
        if not np.isfinite(atr) or atr<=0:continue
        if max(fmax[i]-mid[i],mid[i]-fmin[i]) < MOVE_ATR*atr:continue
        end_time=broker_ms+MOVE_HORIZON_MS
        jend=int(np.searchsorted(sec,end_time,side='right'))
        hit_dir=0;hit_ms=None;hit_px=None
        up=mid[i]+MOVE_ATR*atr;dn=mid[i]-MOVE_ATR*atr
        for j in range(i+1,min(jend,n)):
            if sec[j]-broker_ms>MOVE_HORIZON_MS:break
            if mid[j]>=up:
                hit_dir=1;hit_ms=int(sec[j]-broker_ms);hit_px=float(mid[j]);break
            if mid[j]<=dn:
                hit_dir=-1;hit_ms=int(sec[j]-broker_ms);hit_px=float(mid[j]);break
        if hit_dir==0:continue
        # prior-30s quiet diagnostic
        p0=broker_ms-30000
        k=int(np.searchsorted(sec,p0,side='left'))
        prior_move=np.nan
        if k<i and broker_ms-sec[k]<=32000:
            prior_move=abs(mid[i]-mid[k])/atr
        rows.append({'broker_event_ms':broker_ms,'xau_mid0':float(mid[i]),'xau_atr':atr,'direction':hit_dir,
                     'side':'UP' if hit_dir>0 else 'DOWN','time_to_1atr_ms':hit_ms,'hit_price':hit_px,
                     'prior30_abs_move_atr':prior_move,'quiet_start':bool(np.isfinite(prior_move) and prior_move<=.25)})
        last_accept=broker_ms
    e=pd.DataFrame(rows)
    if not e.empty:
        e['gc_event_ms']=e.broker_event_ms-CLOCK_OFFSET_MIN*60000
        e['event_utc']=pd.to_datetime(e.gc_event_ms,unit='ms',utc=True).astype(str)
        e['period']=[period_utc(x) for x in e.gc_event_ms]
    return e

def agg_exact(gt,start_ms,end_ms):
    tt=gt.time_msc.to_numpy(np.int64)
    i=int(np.searchsorted(tt,start_ms,side='left'));j=int(np.searchsorted(tt,end_ms,side='left'))
    if j<=i:return None
    z=gt.iloc[i:j]
    buy=float(z.loc[z.sgn==1,'vol'].sum());sell=float(z.loc[z.sgn==-1,'vol'].sum());vol=buy+sell
    if vol<=0:return None
    op=float(z['last'].iloc[0]);cl=float(z['last'].iloc[-1]);hi=float(z['last'].max());lo=float(z['last'].min())
    delta=buy-sell;df=delta/vol
    return {'buy_vol':buy,'sell_vol':sell,'volume':vol,'delta':delta,'delta_frac':df,'open':op,'close':cl,'high':hi,'low':lo}

def latest_thresholds(b,end_ms):
    # b is LAB002 causal aligned buckets; use latest completed bucket before event.
    ends=b.end_ms.to_numpy(np.int64)
    i=int(np.searchsorted(ends,end_ms,side='right'))-1
    if i<0:return np.nan,np.nan
    r=b.iloc[i]
    return float(r.q90_abs_delta) if np.isfinite(r.q90_abs_delta) else np.nan, float(r.q75_vol) if np.isfinite(r.q75_vol) else np.nan

def gc_atr_for(ms,atrmap):
    prev=((ms//60000)*60000)-60000
    return float(atrmap.get(prev,np.nan))

def features_at(gt,atrmap,aligned,event_ms,move_dir):
    rec={}
    tmp={}
    for w in WINDOWS:
        x=agg_exact(gt,event_ms-w*1000,event_ms)
        q90,q75=latest_thresholds(aligned[w],event_ms)
        if x is None:
            for c in ('delta_frac','volume','impact','extreme','stall','trapped_opposite','chase_aligned'):rec[f'{w}s_{c}']=np.nan
            continue
        atr=gc_atr_for(event_ms,atrmap)
        cdir=int(np.sign(x['delta']))
        impact=np.nan if not np.isfinite(atr) or atr<=0 else cdir*(x['close']-x['open'])/atr
        extreme=bool(np.isfinite(q90) and np.isfinite(q75) and abs(x['delta_frac'])>=q90 and x['volume']>=q75 and cdir!=0)
        stall=bool(extreme and np.isfinite(impact) and impact<=.05)
        trapped=bool(stall and cdir==-move_dir)
        chase=bool(extreme and cdir==move_dir and np.isfinite(impact) and impact>.05)
        rec[f'{w}s_delta_frac']=x['delta_frac'];rec[f'{w}s_aligned_delta']=move_dir*x['delta_frac']
        rec[f'{w}s_volume']=x['volume'];rec[f'{w}s_impact']=impact
        rec[f'{w}s_extreme']=int(extreme);rec[f'{w}s_stall']=int(stall)
        rec[f'{w}s_trapped_opposite']=int(trapped);rec[f'{w}s_chase_aligned']=int(chase)
        tmp[w]=(x,cdir,impact)
    # sequence features
    x30=agg_exact(gt,event_ms-30000,event_ms)
    x5=agg_exact(gt,event_ms-5000,event_ms)
    rec['delta_flip']=0
    if x30 is not None and x5 is not None:
        rec['delta_flip']=int(np.sign(x30['delta'])==-move_dir and np.sign(x5['delta'])==move_dir)
    a=agg_exact(gt,event_ms-60000,event_ms-30000);b=agg_exact(gt,event_ms-30000,event_ms)
    rec['repeated_failed_attack']=0
    if a is not None and b is not None:
        atr=gc_atr_for(event_ms,atrmap)
        da=int(np.sign(a['delta']));db=int(np.sign(b['delta']))
        ia=da*(a['close']-a['open'])/atr if np.isfinite(atr) and atr>0 else np.nan
        ib=db*(b['close']-b['open'])/atr if np.isfinite(atr) and atr>0 else np.nan
        rec['repeated_failed_attack']=int(da==db and da==-move_dir and np.isfinite(ia) and np.isfinite(ib) and ib<=ia)
    return rec

def controls(events):
    rows=[]
    ems=events.gc_event_ms.to_numpy(np.int64)
    for r in events.itertuples(index=False):
        for off in CONTROL_OFFSETS_MIN:
            t=int(r.gc_event_ms+off*60000)
            # exclude controls within +/-5m of any large event
            j=int(np.searchsorted(ems,t))
            near=False
            for k in (j-1,j):
                if 0<=k<len(ems) and abs(int(ems[k])-t)<=300000:near=True
            if near:continue
            rows.append({'parent_event_ms':int(r.gc_event_ms),'gc_event_ms':t,'period':r.period,'direction':int(r.direction),'quiet_start':bool(r.quiet_start),'offset_min':off})
    return pd.DataFrame(rows)

def rate(df,col):
    x=pd.to_numeric(df[col],errors='coerce').dropna()
    return float(x.mean()) if len(x) else None

def summarize(events,pre,ctrlpre):
    signals=[]
    binary=[]
    for w in WINDOWS:
        binary += [f'{w}s_extreme',f'{w}s_stall',f'{w}s_trapped_opposite',f'{w}s_chase_aligned']
    binary += ['delta_flip','repeated_failed_attack']
    subsets=[('ALL',np.ones(len(events),dtype=bool)),('QUIET',events.quiet_start.to_numpy(bool))]
    for sname,mask in subsets:
        ids=set(events.loc[mask,'gc_event_ms'].astype(np.int64))
        pe=pre[pre.gc_event_ms.isin(ids)]
        pc=ctrlpre[ctrlpre.parent_event_ms.isin(ids)]
        for p in ('TRAIN','VALID','POST_CHECK','FULL'):
            ee=pe if p=='FULL' else pe[pe.period==p]
            cc=pc if p=='FULL' else pc[pc.period==p]
            for c in binary:
                er=rate(ee,c);cr=rate(cc,c)
                enr=None if er is None or cr is None else (float('inf') if cr==0 and er>0 else (er/cr if cr>0 else None))
                signals.append({'subset':sname,'period':p,'signal':c,'event_n':int(len(ee)),'control_n':int(len(cc)),
                                'event_rate':er,'control_rate':cr,'enrichment':enr})
    return pd.DataFrame(signals)

def main():
    l2=load(LAB2,'l2');lt=load(LT,'lt')
    work=ROOT/'_lab004reverse';work.mkdir(exist_ok=True)
    base=l2.load(l2.BASE,'base')
    az=work/'amp.zip'
    if not az.exists():base.download(base.AMP_URL,az)
    if base.sha(az)!=base.AMP_SHA:raise SystemExit('AMP SHA mismatch')
    gt=l2.read_amp_ticks(az);gatr=l2.m1_atr_map(gt)
    aligned={w:l2.causal_features(l2.aggregate_window(gt,w),w,gatr) for w in WINDOWS}
    xt,xb,xa,_=lt.read_xau_ticks();xm1=lt.build_xau_m1(xt,xb,xa);xatr=lt.xau_atr_lookup(xm1)
    sec,mid=build_xau_seconds(xt,xb,xa)
    events=detect_large_moves(sec,mid,xatr)
    events.to_csv(OUT_EVENTS,index=False)
    pres=[]
    for r in events.itertuples(index=False):
        z={'gc_event_ms':int(r.gc_event_ms),'event_utc':r.event_utc,'period':r.period,'direction':int(r.direction),'side':r.side,'quiet_start':bool(r.quiet_start)}
        z.update(features_at(gt,gatr,aligned,int(r.gc_event_ms),int(r.direction)));pres.append(z)
    pre=pd.DataFrame(pres)
    ctr=controls(events)
    cps=[]
    for r in ctr.itertuples(index=False):
        z=r._asdict();z.update(features_at(gt,gatr,aligned,int(r.gc_event_ms),int(r.direction)));cps.append(z)
    cpre=pd.DataFrame(cps)
    sig=summarize(events,pre,cpre);sig.to_csv(OUT_PRE,index=False)

    # stable candidates: event enrichment >1 in TRAIN and VALID, event rate >=5% valid; report POST but do not select on it.
    cand=[]
    for subset in ('ALL','QUIET'):
        for signal in sig.signal.unique():
            tr=sig[(sig.subset==subset)&(sig.period=='TRAIN')&(sig.signal==signal)]
            va=sig[(sig.subset==subset)&(sig.period=='VALID')&(sig.signal==signal)]
            if len(tr)==1 and len(va)==1:
                a=tr.iloc[0];b=va.iloc[0]
                if a.enrichment is not None and b.enrichment is not None and np.isfinite(a.enrichment) and np.isfinite(b.enrichment) and a.enrichment>1 and b.enrichment>1 and b.event_rate is not None and b.event_rate>=.05:
                    cand.append({'subset':subset,'signal':signal,'train_enrichment':float(a.enrichment),'valid_enrichment':float(b.enrichment),'valid_event_rate':float(b.event_rate),
                                 'score':float(min(a.enrichment,b.enrichment))})
    cand=sorted(cand,key=lambda x:x['score'],reverse=True)

    counts={}
    for p in ('TRAIN','VALID','POST_CHECK','FULL'):
        z=events if p=='FULL' else events[events.period==p]
        counts[p]={'n':int(len(z)),'up':int((z.direction==1).sum()),'down':int((z.direction==-1).sum()),'quiet':int(z.quiet_start.sum()),
                   'median_time_to_1atr_s':float(z.time_to_1atr_ms.median()/1000) if len(z) else None}
    out={'lab':'GC_XAU_LARGE_MOVE_REVERSE_PRECURSOR_DISCOVERY_LAB004','status':'EVENT_FIRST_DISCOVERY_NOT_OOS','large_move_definition':'+/-1 ATR first passage within 5m, 5m decluster',
         'counts':counts,'stable_precursor_candidates':cand[:20]}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    lines=['# GC_XAU_LARGE_MOVE_REVERSE_PRECURSOR_DISCOVERY_LAB004','','Status: EVENT_FIRST_DISCOVERY_NOT_OOS','',
           'Large move = first passage to +/-1.0 XAU ATR within 5 minutes; events de-clustered 5 minutes.','',
           '## Large XAU moves','',
           '| Period | N | UP | DOWN | Quiet-start | Median time to 1 ATR |',
           '|---|---:|---:|---:|---:|---:|']
    for p in ('TRAIN','VALID','POST_CHECK','FULL'):
        x=counts[p];lines.append(f"| {p} | {x['n']} | {x['up']} | {x['down']} | {x['quiet']} | {('NA' if x['median_time_to_1atr_s'] is None else f'{x['median_time_to_1atr_s']:.0f}s')} |")
    lines += ['','## Stable precursor candidates — TRAIN and VALID enrichment >1','',
              '| Rank | Subset | GC precursor | Train enrich | Valid enrich | Valid event rate | Post enrich |',
              '|---:|---|---|---:|---:|---:|---:|']
    for rank,c in enumerate(cand[:15],1):
        po=sig[(sig.subset==c['subset'])&(sig.period=='POST_CHECK')&(sig.signal==c['signal'])]
        pen=po.iloc[0].enrichment if len(po) else None
        lines.append(f"| {rank} | {c['subset']} | {c['signal']} | {c['train_enrichment']:.2f}x | {c['valid_enrichment']:.2f}x | {c['valid_event_rate']*100:.1f}% | {('NA' if pen is None or not np.isfinite(pen) else f'{pen:.2f}x')} |")
    lines += ['','POST_CHECK was not used to select candidates. No trading/execution optimization was performed.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(OUT_MD.read_text())

if __name__=='__main__':main()

# rerun marker after workflow commit-step fix
