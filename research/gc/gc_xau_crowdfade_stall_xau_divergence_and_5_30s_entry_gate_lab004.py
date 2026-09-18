#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
LAB2=ROOT/'gc_xau_micro_lead_lag_flow_burst_lab002.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_CROWDFade_STALL_XAU_DIVERGENCE_AND_5_30S_ENTRY_GATE_LAB004.json'
OUT_MD=ROOT/'GC_XAU_CROWDFade_STALL_XAU_DIVERGENCE_AND_5_30S_ENTRY_GATE_LAB004.md'
OUT_EVENTS=ROOT/'GC_XAU_CROWDFade_STALL_XAU_DIVERGENCE_AND_5_30S_ENTRY_GATE_LAB004_EVENTS.csv'

TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
OFFSET=180
STALE_MS=2000
HOLD=(120,300)
ENTRIES=('MARKET_5S','LIMIT_010_FROM_5S','CONFIRM_010','CONFIRM_AFTER_NEGATIVE')
STATES=('ALL','DIVERGE_EARLY','STALL_THEN_GO','CROWD_PERSISTS','REVERSAL_CONFIRM')
GEOMS={'G1':(0.25,0.50),'G2':(0.30,0.45)}

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    return m

def first_idx(t,target):
    i=int(np.searchsorted(t,target,side='left'))
    if i>=len(t) or t[i]-target>STALE_MS:
        return None
    return i

def period(ms):
    x=pd.to_datetime(ms,unit='ms',utc=True)
    return 'TRAIN' if x<TRAIN_END else ('VALID' if x<VALID_END else 'POST_CHECK')

def pf(v):
    v=np.asarray(v,float)
    p=v[v>0].sum(); n=-v[v<0].sum()
    return float(p/n) if n>0 else (float('inf') if p>0 else None)

def sim_rr(t,b,a,start_i,d,entry,atr,deadline,slatr,tpatr):
    sl=entry-d*slatr*atr
    tp=entry+d*tpatr*atr
    end=int(np.searchsorted(t,deadline,side='right'))
    end=min(end,len(t))
    for j in range(start_i,end):
        px=float(b[j] if d>0 else a[j])
        if (d>0 and px<=sl) or (d<0 and px>=sl):
            return -1.0,'SL'
        if (d>0 and px>=tp) or (d<0 and px<=tp):
            return tpatr/slatr,'TP'
    j=first_idx(t,deadline)
    if j is None:
        return np.nan,'NOEXIT'
    px=float(b[j] if d>0 else a[j])
    return d*(px-entry)/(slatr*atr),'TIMEOUT'

def frozen_stall_events(l2,gt):
    atrmap=l2.m1_atr_map(gt)
    gb=l2.causal_features(l2.aggregate_window(gt,30),30,atrmap)
    idxs=l2.select_events(gb,30,'FADE_STALL')
    return gb,idxs

def state_flags(r5,r10,r30):
    return {
        'ALL':True,
        'DIVERGE_EARLY': bool(r5>0 and r10>0),
        'STALL_THEN_GO': bool(r5<=0.05 and r30>r5),
        'CROWD_PERSISTS': bool(r5<0 and r10<0),
        'REVERSAL_CONFIRM': bool(r5<=0 and r30>0),
    }

def find_entry(kind,t,b,a,mid,broker_end,d,atr):
    i5=first_idx(t,broker_end+5000)
    if i5 is None: return None
    if kind=='MARKET_5S':
        return i5, float(a[i5] if d>0 else b[i5])

    if kind=='LIMIT_010_FROM_5S':
        ep=float(a[i5] if d>0 else b[i5])
        lp=ep-d*0.10*atr
        end=int(np.searchsorted(t,broker_end+30000,side='right'))
        for j in range(i5,min(end,len(t))):
            if (d>0 and a[j]<=lp) or (d<0 and b[j]>=lp):
                return j,float(lp)
        return None

    i0=first_idx(t,broker_end)
    if i0 is None: return None
    m0=float(mid[i0])

    if kind=='CONFIRM_010':
        level=m0+d*0.10*atr
        end=int(np.searchsorted(t,broker_end+30000,side='right'))
        for j in range(i0,min(end,len(t))):
            if (d>0 and mid[j]>=level) or (d<0 and mid[j]<=level):
                return j,float(a[j] if d>0 else b[j])
        return None

    if kind=='CONFIRM_AFTER_NEGATIVE':
        neg=m0-d*0.05*atr
        endneg=int(np.searchsorted(t,broker_end+15000,side='right'))
        neg_i=None
        for j in range(i0,min(endneg,len(t))):
            if (d>0 and mid[j]<=neg) or (d<0 and mid[j]>=neg):
                neg_i=j; break
        if neg_i is None: return None
        end=int(np.searchsorted(t,broker_end+30000,side='right'))
        for j in range(neg_i,min(end,len(t))):
            if (d>0 and mid[j]>=m0) or (d<0 and mid[j]<=m0):
                return j,float(a[j] if d>0 else b[j])
        return None

    raise ValueError(kind)

def main():
    l2=load(LAB2,'l2'); lt=load(LT,'lt')
    work=ROOT/'_lab004stall'; work.mkdir(exist_ok=True)
    az=work/'amp.zip'
    base=l2.load(l2.BASE,'base')
    if not az.exists(): base.download(base.AMP_URL,az)
    if base.sha(az)!=base.AMP_SHA: raise SystemExit('AMP SHA mismatch')
    gt=l2.read_amp_ticks(az)
    gb,idxs=frozen_stall_events(l2,gt)

    t,b,a,_=lt.read_xau_ticks()
    mid=(b+a)/2.0
    xm1=lt.build_xau_m1(t,b,a)
    xatr=lt.xau_atr_lookup(xm1)

    rows=[]
    for idx,d in idxs:
        r=gb.iloc[idx]
        end_ms=int(r.end_ms)
        broker_end=end_ms+OFFSET*60000
        i0=first_idx(t,broker_end)
        if i0 is None: continue
        prev=((broker_end//60000)*60000)-60000
        atr=float(xatr.get(prev,np.nan))
        if not np.isfinite(atr) or atr<=0: continue
        m0=float(mid[i0])

        vals={}
        ok=True
        for sec in (5,10,30):
            j=first_idx(t,broker_end+sec*1000)
            if j is None: ok=False; break
            vals[sec]=d*(float(mid[j])-m0)/atr
        if not ok: continue
        flags=state_flags(vals[5],vals[10],vals[30])

        for state,on in flags.items():
            if not on: continue
            for entkind in ENTRIES:
                rec={
                    'state':state,'entry_kind':entkind,'period':period(end_ms),
                    'gc_end_ms':end_ms,'gc_end_utc':pd.to_datetime(end_ms,unit='ms',utc=True).isoformat(),
                    'direction':d,'side':'LONG' if d>0 else 'SHORT',
                    'r5':vals[5],'r10':vals[10],'r30':vals[30],
                    'slope_5_30':vals[30]-vals[5],'xau_atr':atr,
                    'gc_delta_frac':float(r.delta_frac),'gc_volume':float(r.volume),'gc_impact':float(r.impact)
                }
                ent=find_entry(entkind,t,b,a,mid,broker_end,d,atr)
                if ent is None:
                    rec.update({'filled':False,'fill_delay_ms':np.nan,'entry_price':np.nan})
                    for h in HOLD: rec[f'hold_{h}s_atr']=np.nan
                    for g in GEOMS:
                        rec[f'{g}_r']=np.nan;rec[f'{g}_reason']='NOFILL'
                    rows.append(rec);continue

                ei,ep=ent
                rec.update({'filled':True,'fill_delay_ms':int(t[ei]-broker_end),'entry_price':ep})
                for h in HOLD:
                    j=first_idx(t,broker_end+h*1000)
                    if j is None: rec[f'hold_{h}s_atr']=np.nan
                    else:
                        xp=float(b[j] if d>0 else a[j])
                        rec[f'hold_{h}s_atr']=d*(xp-ep)/atr
                for g,(sl,tp) in GEOMS.items():
                    rr,reason=sim_rr(t,b,a,ei,d,ep,atr,broker_end+300000,sl,tp)
                    rec[f'{g}_r']=rr;rec[f'{g}_reason']=reason
                rows.append(rec)

    ev=pd.DataFrame(rows)
    ev.to_csv(OUT_EVENTS,index=False)

    result={}
    candidates=[]
    for state in STATES:
        for ent in ENTRIES:
            key=f'{state}__{ent}'
            result[key]={}
            for p in ('TRAIN','VALID','POST_CHECK','FULL'):
                z=ev[(ev.state==state)&(ev.entry_kind==ent)]
                if p!='FULL': z=z[z.period==p]
                f=z[z.filled]
                out={'signals':int(len(z)),'fills':int(len(f)),
                     'fill_rate':float(len(f)/len(z)) if len(z) else None}
                for h in HOLD:
                    v=f[f'hold_{h}s_atr'].dropna().to_numpy(float)
                    out[f'hold{h}_ev']=float(v.mean()) if len(v) else None
                    out[f'hold{h}_wr']=float((v>0).mean()*100) if len(v) else None
                rr={}
                for g in GEOMS:
                    v=f[f'{g}_r'].dropna().to_numpy(float)
                    rr[g]={'n':int(len(v)),'ev_r':float(v.mean()) if len(v) else None,
                           'pf':pf(v) if len(v) else None,'wr':float((v>0).mean()*100) if len(v) else None}
                out['rr']=rr
                result[key][p]=out

            tr=result[key]['TRAIN']; va=result[key]['VALID']
            gate=(tr['fills']>=10 and va['fills']>=10 and
                  tr['hold120_ev'] is not None and tr['hold120_ev']>0 and
                  va['hold120_ev'] is not None and va['hold120_ev']>0 and
                  va['hold300_ev'] is not None and va['hold300_ev']>=0 and
                  any(va['rr'][g]['ev_r'] is not None and va['rr'][g]['ev_r']>0 and
                      va['rr'][g]['pf'] is not None and va['rr'][g]['pf']>=1.10 for g in GEOMS))
            result[key]['gate_pass']=bool(gate)
            if gate: candidates.append(key)

    OUT_JSON.write_text(json.dumps({'lab':'GC_XAU_CROWDFade_STALL_XAU_DIVERGENCE_AND_5_30S_ENTRY_GATE_LAB004',
                                    'candidates':candidates,'results':result},indent=2),encoding='utf-8')
    def ff(x): return 'NA' if x is None else f'{x:+.3f}'
    lines=['# GC_XAU_CROWDFade_STALL_XAU_DIVERGENCE_AND_5_30S_ENTRY_GATE_LAB004','',
           'Frozen parent trigger: 30s_FADE_STALL.','',
           '| State / Entry | Gate | TrFill | Tr120 | VaFill | Va120 | Va300 | Va G1 EV/PF | Va G2 EV/PF | Post120 |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for key,v in result.items():
        tr=v['TRAIN'];va=v['VALID'];po=v['POST_CHECK']
        g1=va['rr']['G1'];g2=va['rr']['G2']
        lines.append(f"| {key} | {'PASS' if v['gate_pass'] else 'FAIL'} | {tr['fills']} | {ff(tr['hold120_ev'])} | {va['fills']} | {ff(va['hold120_ev'])} | {ff(va['hold300_ev'])} | {ff(g1['ev_r'])}/{ff(g1['pf'])} | {ff(g2['ev_r'])}/{ff(g2['pf'])} | {ff(po['hold120_ev'])} |")
    lines += ['',f'Candidates: {candidates if candidates else "NONE"}','',
              'POST_CHECK was not used for candidate selection. No trigger threshold sweep was performed.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
