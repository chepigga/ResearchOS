from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from numba import njit
import importlib.util
_core_path=Path(__file__).resolve().parents[1]/'CROWDFADE_V200_SEQUENTIAL_CHANGE_LABS_033_035'/'run.py'
_spec=importlib.util.spec_from_file_location('crowdfade_core_033_035',_core_path)
core=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# v200 execution/exit shell stays frozen.
RETRACE=0.60
PENDING_TTL=1200
SL=4.5
TP=10.0
HOLD=86400
COST_BPS=0.50
MAXDAY=3
ANTI_REPEAT_ATR=1.0
CONF_TTL=3600

Z_LADDER=[2.05,1.75,1.50,1.25,1.00]
CONF_LADDER=[0.25,0.20,0.15]

def link_data():
    # Workflow puts data here. Core loader expects its own sibling data dir, so use local loaders below.
    pass

def load_flow():
    return core.load_flow()

def load_hist_price():
    return core.load_hist_price()

def load_sec_price():
    return core.load_sec_price()

def prep(raw,ft,fz,start,end):
    return core.prep(raw,ft,fz,start,end)

@njit(cache=True)
def sim_freq(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,
             z_core,z_lane,mode,conf_atr,cancel_flip):
    # mode:
    # 0 = global threshold z_core only
    # 1 = high-Z core >= z_core PLUS mid-Z lane >= z_lane requiring H1+H4 aligned with trade direction
    cap=len(dt)
    R=np.zeros(cap); ST=np.zeros(cap,np.int64); CT=np.zeros(cap,np.int64); ET=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8); ORIGZ=np.zeros(cap); CONFZ=np.zeros(cap); LANE=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    armed=0; core_armed=0; lane_armed=0; confirmed=0; pending=0; nofill=0; zcancel=0

    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:
            k+=1; continue
        d=t//86400
        if d!=day:
            day=d; dc=0
        if dc>=MAXDAY:
            k+=1; continue

        z=Z[k]
        az=abs(z)
        side=-1 if z>0 else (1 if z<0 else 0)
        if side==0:
            k+=1; continue

        lane=0
        eligible=False
        if az>=z_core:
            eligible=True; lane=0
        elif mode==1 and az>=z_lane:
            # Mid-Z lane only when CrowdFade direction follows aligned H1 + H4 trend.
            if H1[k]==side and H4[k]==side and H1[k]!=0:
                eligible=True; lane=1
        if not eligible:
            k+=1; continue

        sig=QC[k]; siga=A[k]
        if has and abs(sig-last)<ANTI_REPEAT_ATR*la:
            k+=1; continue

        armed+=1
        if lane==0: core_armed+=1
        else: lane_armed+=1

        lev=sig+side*conf_atr*siga
        ci=-1
        j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j; break
            j+=1
        if ci<0:
            k+=1; continue
        confirmed+=1

        cz=Z[ci]
        if cancel_flip and z*cz<0.0:
            zcancel+=1
            k=ci+1; continue

        entry=QC[ci]-side*RETRACE*siga
        ps=np.searchsorted(ts,dt[ci]+1)
        pe=np.searchsorted(ts,dt[ci]+PENDING_TTL,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):
                ei=q; break
        pending+=1
        if ei<0:
            nofill+=1
            k=ci+1; continue

        risk=SL*siga
        sl=entry-side*risk
        tp=entry+side*TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD,'left'))
        xp=C[xe]; ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:
                xp=sl; ex=q; break
            if th:
                xp=tp; ex=q; break

        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr; ST[n]=t; CT[n]=dt[ci]; ET[n]=ts[ei]; SIDE[n]=side
        ORIGZ[n]=z; CONFZ[n]=cz; LANE[n]=lane; n+=1

        dc+=1; last=entry; la=siga; has=True; nextts=ts[ex]+1
        k=np.searchsorted(dt,nextts)

    return (R[:n],ST[:n],CT[:n],ET[:n],SIDE[:n],ORIGZ[:n],CONFZ[:n],LANE[:n],
            armed,core_armed,lane_armed,confirmed,pending,nofill,zcancel)

def metrics(x):
    return core.metrics(np.asarray(x,float))

def run_one(arr,z_core=2.05,z_lane=2.05,mode=0,conf=0.25,cancel=True,period='hist'):
    z=sim_freq(*arr,z_core,z_lane,mode,conf,cancel)
    R,st,ct,et,side,oz,cz,lane,armed,core_armed,lane_armed,confirmed,pending,nofill,zcancel=z
    m=metrics(R)
    months=60 if period=='hist' else 6
    m.update({
      'armed':int(armed),'core_armed':int(core_armed),'lane_armed':int(lane_armed),
      'confirmed':int(confirmed),'pending':int(pending),'no_fill':int(nofill),'cancel_z':int(zcancel),
      'fill_rate_pending':float(len(R)/pending) if pending else 0.0,
      'confirm_rate_armed':float(confirmed/armed) if armed else 0.0,
      'trades_per_month':float(len(R)/months)
    })
    df=pd.DataFrame({'signal_ts':st,'confirm_ts':ct,'entry_ts':et,'R':R,'side':side,
                     'orig_z':oz,'confirm_z':cz,'lane':lane})
    if len(df):
        df['signal_time_utc']=pd.to_datetime(df.signal_ts,unit='s',utc=True)
        if period=='hist':
            grp=df.groupby(df.signal_time_utc.dt.year)
        else:
            grp=df.groupby(df.signal_time_utc.dt.strftime('%Y-%m'))
        m['periods']={str(k):metrics(g.R.to_numpy(float)) for k,g in grp}
        m['positive_periods']=sum(v['SumR']>0 for v in m['periods'].values())
    else:
        m['periods']={};m['positive_periods']=0
    return m,df

def robust_enough(m,b,dd_mult=1.25,rdd_floor=.75):
    return (m['EV']>0 and m['PF']>1.0 and
            m['MaxDD_R']<=b['MaxDD_R']*dd_mult and
            m['R_DD']>=b['R_DD']*rdd_floor)

def fmt(m):
    return f"N={m['N']} ({m['trades_per_month']:.1f}/mo) EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f}"

def main():
    ft,fz=load_flow()
    hist=prep(load_hist_price(),ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=prep(load_sec_price(),ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))

    # JIT warmup
    _=sim_freq(*[x[:min(2000,len(x))] for x in hist],2.05,2.05,0,.25,True)

    # Current research candidate foundation: v200 geometry + cancel-sign-flip.
    bh,bhdf=run_one(hist,2.05,2.05,0,.25,True,'hist')
    bf,bfdf=run_one(fwd,2.05,2.05,0,.25,True,'fwd')

    # LAB037A: global Z only.
    global_h={};global_f={}
    for zth in Z_LADDER:
        k=f'{zth:.2f}'
        global_h[k],_=run_one(hist,zth,zth,0,.25,True,'hist')
        global_f[k],_=run_one(fwd,zth,zth,0,.25,True,'fwd')

    # LAB037B: preserve 2.05 high-Z core, add lower-Z lane only with H1+H4 aligned to trade.
    lane_h={};lane_f={}
    for zl in [1.75,1.50,1.25,1.00]:
        k=f'{zl:.2f}'
        lane_h[k],_=run_one(hist,2.05,zl,1,.25,True,'hist')
        lane_f[k],_=run_one(fwd,2.05,zl,1,.25,True,'fwd')

    # Select the highest-frequency lane that remains inside conservative robustness envelope in both samples.
    eligible=[]
    for zl in [1.75,1.50,1.25,1.00]:
        k=f'{zl:.2f}'
        h=lane_h[k];f=lane_f[k]
        if robust_enough(h,bh) and robust_enough(f,bf):
            gain=min(h['trades_per_month']/bh['trades_per_month'],f['trades_per_month']/bf['trades_per_month'])
            eligible.append((gain,-abs(zl-2.05),zl))
    if eligible:
        eligible.sort(reverse=True); selected_lane=eligible[0][2]
    else:
        selected_lane=2.05

    # LAB037C confirmation relaxation ONLY on selected lane architecture.
    conf_h={};conf_f={}
    lane_mode=0 if selected_lane==2.05 else 1
    for cf in CONF_LADDER:
        k=f'{cf:.2f}'
        conf_h[k],_=run_one(hist,2.05,selected_lane,lane_mode,cf,True,'hist')
        conf_f[k],_=run_one(fwd,2.05,selected_lane,lane_mode,cf,True,'fwd')

    result={
      'lab':'CROWDFADE_V200_FREQUENCY_EXPANSION_LAB_037',
      'goal':'increase v200 trade frequency toward v191 without relaxing passive-entry quality',
      'frozen':{'retrace_ATR':RETRACE,'TTL_min':20,'SL_ATR':SL,'TP_ATR':TP,'hold_h':24,'flat_risk':True,'cancel_sign_flip':True},
      'baseline':{'historical':bh,'forward':bf},
      'LAB037A_GLOBAL_Z_FRONTIER':{'historical':global_h,'forward':global_f},
      'LAB037B_MID_Z_TREND_LANE':{
        'definition':'core absZ>=2.05 unchanged; additional mid-Z trades require H1 and H4 both aligned with CrowdFade direction',
        'historical':lane_h,'forward':lane_f,'selected_lane_threshold':selected_lane
      },
      'LAB037C_CONFIRMATION_FRONTIER':{
        'architecture':('core only' if selected_lane==2.05 else f'core2.05 + aligned lane>={selected_lane:.2f}'),
        'historical':conf_h,'forward':conf_f
      },
      'limitations':[
        'BTC only. ETH/SOL transfer must be checked before production.',
        '2021-2025 is discovery/in-sample; 2026 Mar-Aug is reused forward-shadow.',
        'This LAB deliberately keeps retrace 0.60 and TTL20 because LAB033 rejected relaxing them.',
        'The frequency target is a frontier, not an instruction to maximize trade count.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))

    rows=[]
    for lab,hset,fset in [('037A',global_h,global_f),('037B',lane_h,lane_f),('037C',conf_h,conf_f)]:
        for v,m in hset.items():
            rows.append({'lab':lab,'variant':v,'period':'historical',**{k:m[k] for k in ['N','trades_per_month','EV','PF','SumR','MaxDD_R','R_DD','positive_periods','armed','confirmed','pending','fill_rate_pending']}})
        for v,m in fset.items():
            rows.append({'lab':lab,'variant':v,'period':'2026',**{k:m[k] for k in ['N','trades_per_month','EV','PF','SumR','MaxDD_R','R_DD','positive_periods','armed','confirmed','pending','fill_rate_pending']}})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)

    lines=['# LAB037 — v200 frequency expansion toward v191','',
           'Frozen execution: retrace .60 ATR, TTL20, SL4.5, TP10, H24, cancel-sign-flip ON.','',
           '## Baseline research candidate',
           f"- Hist: {fmt(bh)}",f"- 2026: {fmt(bf)}",'',
           '## LAB037A — global Z frontier']
    for zth in Z_LADDER:
        k=f'{zth:.2f}';lines += [f"- Z{k}: hist {fmt(global_h[k])} | 2026 {fmt(global_f[k])}"]
    lines += ['','## LAB037B — add mid-Z lane only when H1+H4 aligned with trade']
    for zl in [1.75,1.50,1.25,1.00]:
        k=f'{zl:.2f}'; lines += [f"- lane >= {k}: hist {fmt(lane_h[k])} | 2026 {fmt(lane_f[k])}"]
    lines += ['',f"Selected lane for next step: **{selected_lane:.2f}**",'',
              '## LAB037C — M15 confirmation threshold on selected architecture']
    for cf in CONF_LADDER:
        k=f'{cf:.2f}'; lines += [f"- confirm {k} ATR: hist {fmt(conf_h[k])} | 2026 {fmt(conf_f[k])}"]
    lines += ['','## Limitations']+[f'- {x}' for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
