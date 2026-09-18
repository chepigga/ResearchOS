#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
LAB2=ROOT/'gc_xau_micro_lead_lag_flow_burst_lab002.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_CROWDFade_STALL_EARLY_SIGNAL_TO_5MIN_UNWIND_LAB003.json'
OUT_MD=ROOT/'GC_XAU_CROWDFade_STALL_EARLY_SIGNAL_TO_5MIN_UNWIND_LAB003.md'
OUT_EVENTS=ROOT/'GC_XAU_CROWDFade_STALL_EARLY_SIGNAL_TO_5MIN_UNWIND_LAB003_EVENTS.csv'
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z'); VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
H=(10,30,60,120,180,300); STALE_MS=2000; OFFSET=180
VARIANTS=('MARKET_NOW','LIMIT_RETRACE_010','CONFIRM_005')
GEOMS={'G1':(0.25,0.50),'G2':(0.30,0.45)}

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader;spec.loader.exec_module(m);return m

def first_idx(t,target):
    i=int(np.searchsorted(t,target,side='left'))
    if i>=len(t) or t[i]-target>STALE_MS:return None
    return i

def period(ms):
    x=pd.to_datetime(ms,unit='ms',utc=True)
    return 'TRAIN' if x<TRAIN_END else ('VALID' if x<VALID_END else 'POST_CHECK')

def pf(v):
    v=np.asarray(v,float); p=v[v>0].sum(); n=-v[v<0].sum()
    return float(p/n) if n>0 else (float('inf') if p>0 else None)

def sim_rr(t,b,a,start_i,d,entry,atr,deadline,slatr,tpatr):
    sl=entry-d*slatr*atr; tp=entry+d*tpatr*atr
    end=int(np.searchsorted(t,deadline,side='right')); end=min(end,len(t))
    for j in range(start_i,end):
        px=float(b[j] if d>0 else a[j])
        if (d>0 and px<=sl) or (d<0 and px>=sl):
            return -1.0,'SL',j
        if (d>0 and px>=tp) or (d<0 and px<=tp):
            return tpatr/slatr,'TP',j
    j=first_idx(t,deadline)
    if j is None:return np.nan,'NOEXIT',None
    px=float(b[j] if d>0 else a[j])
    return d*(px-entry)/(slatr*atr),'TIMEOUT',j

def entry_variant(v,t,b,a,mid,broker_end,d,atr):
    i=first_idx(t,broker_end)
    if i is None:return None
    ib,ia=float(b[i]),float(a[i])
    if v=='MARKET_NOW':
        return i,(ia if d>0 else ib)
    if v=='LIMIT_RETRACE_010':
        lp=(ia-0.10*atr) if d>0 else (ib+0.10*atr)
        e=int(np.searchsorted(t,broker_end+30000,side='right'))
        for j in range(i,min(e,len(t))):
            if (d>0 and a[j]<=lp) or (d<0 and b[j]>=lp):
                return j,lp
        return None
    if v=='CONFIRM_005':
        m0=float(mid[i]); trigger=m0+d*0.05*atr
        e=int(np.searchsorted(t,broker_end+30000,side='right'))
        for j in range(i,min(e,len(t))):
            if (d>0 and mid[j]>=trigger) or (d<0 and mid[j]<=trigger):
                return j,(float(a[j]) if d>0 else float(b[j]))
        return None
    raise ValueError(v)

def main():
    l2=load(LAB2,'l2'); lt=load(LT,'lt')
    work=ROOT/'_lab003stall';work.mkdir(exist_ok=True)
    az=work/'amp.zip'
    if not az.exists(): l2.load(l2.BASE,'base').download(l2.load(l2.BASE,'base').AMP_URL,az)
    base=l2.load(l2.BASE,'base')
    if base.sha(az)!=base.AMP_SHA: raise SystemExit('AMP SHA mismatch')
    gt=l2.read_amp_ticks(az); atrmap=l2.m1_atr_map(gt)
    gb=l2.causal_features(l2.aggregate_window(gt,30),30,atrmap)
    idxs=l2.select_events(gb,30,'FADE_STALL')

    t,b,a,_=lt.read_xau_ticks(); mid=(b+a)/2
    xm1=lt.build_xau_m1(t,b,a); xatr=lt.xau_atr_lookup(xm1)
    rows=[]
    for idx,d in idxs:
        r=gb.iloc[idx]; end_ms=int(r.end_ms); broker_end=end_ms+OFFSET*60000
        ai=first_idx(t,broker_end)
        if ai is None: continue
        prev=((broker_end//60000)*60000)-60000
        atr=float(xatr.get(prev,np.nan))
        if not np.isfinite(atr) or atr<=0: continue
        m0=float(mid[ai]); path_end=first_idx(t,broker_end+300000)
        if path_end is None: continue
        path_mid=mid[ai:path_end+1]
        pred=d*(path_mid-m0)/atr
        mfe=float(np.nanmax(pred)); mae=float(np.nanmin(pred))
        imfe=int(np.nanargmax(pred)); tmfe=int(t[ai+imfe]-broker_end)
        base_rec={'gc_end_ms':end_ms,'gc_end_utc':pd.to_datetime(end_ms,unit='ms',utc=True).isoformat(),'period':period(end_ms),
                  'direction':d,'side':'LONG' if d>0 else 'SHORT','xau_atr':atr,'mfe_5m_atr':mfe,'mae_5m_atr':mae,'time_to_mfe_ms':tmfe,
                  'gc_delta_frac':float(r.delta_frac),'gc_volume':float(r.volume),'gc_impact':float(r.impact)}
        for h in H:
            j=first_idx(t,broker_end+h*1000)
            base_rec[f'mid_{h}s_atr']=np.nan if j is None else d*(float(mid[j])-m0)/atr
        for th in (0.25,0.50):
            hit='NONE'; hms=np.nan
            for j in range(ai,path_end+1):
                z=d*(float(mid[j])-m0)/atr
                if z>=th: hit='PRED';hms=int(t[j]-broker_end);break
                if z<=-th: hit='OPP';hms=int(t[j]-broker_end);break
            base_rec[f'fp_{th:.2f}_hit']=hit;base_rec[f'fp_{th:.2f}_ms']=hms

        for v in VARIANTS:
            ent=entry_variant(v,t,b,a,mid,broker_end,d,atr)
            rec=dict(base_rec);rec['variant']=v
            if ent is None:
                rec.update({'filled':False,'fill_delay_ms':np.nan,'entry_price':np.nan,'hold300_atr':np.nan})
                for g in GEOMS: rec[f'{g}_r']=np.nan;rec[f'{g}_reason']='NOFILL'
                rows.append(rec);continue
            ei,ep=ent; rec.update({'filled':True,'fill_delay_ms':int(t[ei]-broker_end),'entry_price':ep})
            j=first_idx(t,broker_end+300000)
            xp=float(b[j] if d>0 else a[j]); rec['hold300_atr']=d*(xp-ep)/atr
            for g,(sl,tp) in GEOMS.items():
                rr,reason,_=sim_rr(t,b,a,ei,d,ep,atr,broker_end+300000,sl,tp)
                rec[f'{g}_r']=rr;rec[f'{g}_reason']=reason
            rows.append(rec)
    ev=pd.DataFrame(rows);ev.to_csv(OUT_EVENTS,index=False)
    res={}
    for v in VARIANTS:
        res[v]={}
        for p in ('TRAIN','VALID','POST_CHECK','FULL'):
            z=ev[(ev.variant==v) & ((ev.period==p) if p!='FULL' else True)]
            f=z[z.filled]
            vals=f.hold300_atr.dropna().to_numpy(float)
            rr={}
            for g in GEOMS:
                x=f[f'{g}_r'].dropna().to_numpy(float)
                rr[g]={'n':int(len(x)),'ev_r':float(x.mean()) if len(x) else None,'pf':pf(x) if len(x) else None,'wr':float((x>0).mean()*100) if len(x) else None}
            res[v][p]={'signals':int(len(z)),'fills':int(len(f)),'fill_rate':float(len(f)/len(z)) if len(z) else None,
                       'hold300_ev_atr':float(vals.mean()) if len(vals) else None,'hold300_wr':float((vals>0).mean()*100) if len(vals) else None,'rr':rr}
    path={}
    z=ev[ev.variant=='MARKET_NOW']
    for p in ('TRAIN','VALID','POST_CHECK','FULL'):
        q=z if p=='FULL' else z[z.period==p]
        path[p]={'n':int(len(q)),'mfe_mean':float(q.mfe_5m_atr.mean()) if len(q) else None,'mae_mean':float(q.mae_5m_atr.mean()) if len(q) else None,
                 **{f'mid_{h}s_ev':float(q[f"mid_{h}s_atr"].mean()) if len(q) else None for h in H}}
    OUT_JSON.write_text(json.dumps({'lab':'GC_XAU_CROWDFade_STALL_EARLY_SIGNAL_TO_5MIN_UNWIND_LAB003','results':res,'path':path},indent=2),encoding='utf-8')
    def f(x):return 'NA' if x is None else f'{x:+.3f}'
    lines=['# GC_XAU_CROWDFade_STALL_EARLY_SIGNAL_TO_5MIN_UNWIND_LAB003','','Frozen trigger: 30s_FADE_STALL.','',
           '| Variant | Period | Fills | Fill% | Hold300 EV ATR | G1 EVR | G1 PF | G2 EVR | G2 PF |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for v in VARIANTS:
        for p in ('TRAIN','VALID','POST_CHECK'):
            x=res[v][p];g1=x['rr']['G1'];g2=x['rr']['G2']
            lines.append(f"| {v} | {p} | {x['fills']} | {0 if x['fill_rate'] is None else x['fill_rate']*100:.1f}% | {f(x['hold300_ev_atr'])} | {f(g1['ev_r'])} | {f(g1['pf'])} | {f(g2['ev_r'])} | {f(g2['pf'])} |")
    lines += ['','## Frozen path','',
              '| Period | N | 10s | 30s | 60s | 120s | 180s | 300s | MFE5m | MAE5m |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in ('TRAIN','VALID','POST_CHECK'):
        x=path[p];lines.append(f"| {p} | {x['n']} | {f(x['mid_10s_ev'])} | {f(x['mid_30s_ev'])} | {f(x['mid_60s_ev'])} | {f(x['mid_120s_ev'])} | {f(x['mid_180s_ev'])} | {f(x['mid_300s_ev'])} | {f(x['mfe_mean'])} | {f(x['mae_mean'])} |")
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(OUT_MD.read_text())
if __name__=='__main__':main()
