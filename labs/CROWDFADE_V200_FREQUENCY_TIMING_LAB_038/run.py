from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

_core_path=Path(__file__).resolve().parents[1]/'CROWDFADE_V200_SEQUENTIAL_CHANGE_LABS_033_035'/'run.py'
_spec=importlib.util.spec_from_file_location('crowdfade_core_033_035',_core_path)
core=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

ZTH=2.05
CONF_ATR=0.25
RETRACE=0.60
PENDING_TTL=1200
SL=4.5
TP=10.0
COST_BPS=0.50
MAXDAY=3
ANTI_REPEAT_ATR=1.0

CONF_TTLS=[3600,5400,7200,10800]   # 60/90/120/180m
HOLDS=[86400,64800,43200,28800,21600] # 24/18/12/8/6h

@njit(cache=True)
def sim(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,confirm_ttl,hold_sec):
    cap=len(dt)
    R=np.zeros(cap); ST=np.zeros(cap,np.int64); CT=np.zeros(cap,np.int64); ET=np.zeros(cap,np.int64)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    armed=0; confirmed=0; pending=0; nofill=0; zcancel=0; timeexit=0; tpexit=0; slexit=0

    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:
            k+=1; continue
        d=t//86400
        if d!=day:
            day=d;dc=0
        if dc>=MAXDAY:
            k+=1;continue
        z=Z[k]
        side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:
            k+=1;continue
        sig=QC[k];siga=A[k]
        if has and abs(sig-last)<ANTI_REPEAT_ATR*la:
            k+=1;continue
        armed+=1

        lev=sig+side*CONF_ATR*siga
        ci=-1
        j=k+1
        while j<len(dt) and dt[j]<=t+confirm_ttl:
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j;break
            j+=1
        if ci<0:
            k+=1;continue
        confirmed+=1

        # LAB035B candidate: cancel stale original event on crowd sign flip.
        cz=Z[ci]
        if z*cz<0.0:
            zcancel+=1
            k=ci+1;continue

        entry=QC[ci]-side*RETRACE*siga
        ps=np.searchsorted(ts,dt[ci]+1)
        pe=np.searchsorted(ts,dt[ci]+PENDING_TTL,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):
                ei=q;break
        pending+=1
        if ei<0:
            nofill+=1;k=ci+1;continue

        risk=SL*siga
        sl=entry-side*risk
        tp=entry+side*TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+hold_sec,'left'))
        xp=C[xe];ex=xe;reason=0
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:
                xp=sl;ex=q;reason=-1;break
            if th:
                xp=tp;ex=q;reason=1;break
        if reason<0:slexit+=1
        elif reason>0:tpexit+=1
        else:timeexit+=1

        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;ST[n]=t;CT[n]=dt[ci];ET[n]=ts[ei];n+=1
        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1
        k=np.searchsorted(dt,nextts)

    return R[:n],ST[:n],CT[:n],ET[:n],armed,confirmed,pending,nofill,zcancel,timeexit,tpexit,slexit

def metrics(x):
    return core.metrics(np.asarray(x,float))

def run_one(arr,confirm_ttl,hold_sec,period):
    z=sim(*arr,confirm_ttl,hold_sec)
    R,st,ct,et,armed,confirmed,pending,nofill,zcancel,timeexit,tpexit,slexit=z
    m=metrics(R)
    months=60 if period=='hist' else 6
    m.update({
      'trades_per_month':float(len(R)/months),
      'armed':int(armed),'confirmed':int(confirmed),'pending':int(pending),'no_fill':int(nofill),
      'cancel_z':int(zcancel),'confirm_rate':float(confirmed/armed) if armed else 0,
      'fill_rate':float(len(R)/pending) if pending else 0,
      'time_exit':int(timeexit),'tp_exit':int(tpexit),'sl_exit':int(slexit)
    })
    if len(R):
      d=pd.DataFrame({'ts':st,'R':R});d['t']=pd.to_datetime(d.ts,unit='s',utc=True)
      grp=d.groupby(d.t.dt.year) if period=='hist' else d.groupby(d.t.dt.strftime('%Y-%m'))
      m['periods']={str(k):metrics(g.R.to_numpy(float)) for k,g in grp}
      m['positive_periods']=sum(v['SumR']>0 for v in m['periods'].values())
    else:
      m['periods']={};m['positive_periods']=0
    return m

def fmt(m):
    return f"N={m['N']} ({m['trades_per_month']:.1f}/mo) EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f} time={m['time_exit']}"

def guard(m,b):
    return (m['EV']>0 and m['PF']>1 and m['MaxDD_R']<=1.25*b['MaxDD_R'] and m['R_DD']>=0.80*b['R_DD'])

def main():
    ft,fz=core.load_flow()
    hist=core.prep(core.load_hist_price(),ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=core.prep(core.load_sec_price(),ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    _=sim(*[x[:min(2000,len(x))] for x in hist],3600,86400)

    bh=run_one(hist,3600,86400,'hist');bf=run_one(fwd,3600,86400,'fwd')

    # 038A confirmation TTL only; H24 frozen.
    th={};tf={}
    for sec in CONF_TTLS:
      k=str(sec//60)
      th[k]=run_one(hist,sec,86400,'hist');tf[k]=run_one(fwd,sec,86400,'fwd')

    eligible=[]
    for sec in CONF_TTLS[1:]:
      k=str(sec//60);h=th[k];f=tf[k]
      if guard(h,bh) and guard(f,bf):
        gain=min(h['trades_per_month']/bh['trades_per_month'],f['trades_per_month']/bf['trades_per_month'])
        eligible.append((gain,-sec,sec))
    selected_ttl=max(eligible)[2] if eligible else 3600

    # 038B hold only with selected TTL.
    hh={};hf={}
    base_th=th[str(selected_ttl//60)];base_tf=tf[str(selected_ttl//60)]
    for sec in HOLDS:
      k=str(sec//3600)
      hh[k]=run_one(hist,selected_ttl,sec,'hist');hf[k]=run_one(fwd,selected_ttl,sec,'fwd')

    elig_h=[]
    for sec in HOLDS[1:]:
      k=str(sec//3600);h=hh[k];f=hf[k]
      if guard(h,base_th) and guard(f,base_tf):
        gain=min(h['trades_per_month']/base_th['trades_per_month'],f['trades_per_month']/base_tf['trades_per_month'])
        elig_h.append((gain,-abs(sec-86400),sec))
    selected_hold=max(elig_h)[2] if elig_h else 86400

    # 038C interaction corners, including v191-like timing envelope.
    combos=[(3600,86400),(10800,86400),(3600,43200),(10800,43200),(3600,21600),(10800,21600),
            (selected_ttl,selected_hold)]
    seen=set();ch={};cf={}
    for ttl,hold in combos:
      key=f'C{ttl//60}_H{hold//3600}'
      if key in seen:continue
      seen.add(key)
      ch[key]=run_one(hist,ttl,hold,'hist');cf[key]=run_one(fwd,ttl,hold,'fwd')

    out={
      'lab':'CROWDFADE_V200_FREQUENCY_TIMING_LAB_038',
      'goal':'increase frequency without weakening Z/retrace price quality',
      'frozen':{'Z':2.05,'confirm_ATR':.25,'retrace_ATR':.60,'pending_TTL_min':20,'SL_ATR':4.5,'TP_ATR':10,'cancel_sign_flip':True},
      'baseline':{'historical':bh,'forward':bf},
      'LAB038A_CONFIRM_TTL':{'historical':th,'forward':tf,'selected_min':selected_ttl//60},
      'LAB038B_HOLD':{'confirm_TTL_min':selected_ttl//60,'historical':hh,'forward':hf,'selected_h':selected_hold//3600},
      'LAB038C_INTERACTION':{'historical':ch,'forward':cf},
      'limitations':['BTC only','2026 is reused forward-shadow','shorter hold can increase frequency by changing occupancy and therefore later signal reachability']
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    rows=[]
    for lab,hs,fs in [('038A',th,tf),('038B',hh,hf),('038C',ch,cf)]:
      for k,m in hs.items():rows.append({'lab':lab,'variant':k,'period':'historical',**{x:m[x] for x in ['N','trades_per_month','EV','PF','SumR','MaxDD_R','R_DD','positive_periods','time_exit','tp_exit','sl_exit']}})
      for k,m in fs.items():rows.append({'lab':lab,'variant':k,'period':'2026',**{x:m[x] for x in ['N','trades_per_month','EV','PF','SumR','MaxDD_R','R_DD','positive_periods','time_exit','tp_exit','sl_exit']}})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)

    lines=['# LAB038 — v200 frequency through timing/occupancy','',
           'Frozen: Z2.05, M15 confirm .25ATR, retrace .60, pending TTL20, SL4.5, TP10, sign-flip cancel.','',
           '## Baseline',f"- hist {fmt(bh)}",f"- 2026 {fmt(bf)}",'','## LAB038A — confirmation TTL']
    for sec in CONF_TTLS:
      k=str(sec//60);lines.append(f"- {k}m: hist {fmt(th[k])} | 2026 {fmt(tf[k])}")
    lines += ['',f"Selected TTL: **{selected_ttl//60}m**",'','## LAB038B — max hold']
    for sec in HOLDS:
      k=str(sec//3600);lines.append(f"- H{k}: hist {fmt(hh[k])} | 2026 {fmt(hf[k])}")
    lines += ['',f"Selected hold: **{selected_hold//3600}h**",'','## LAB038C — interaction corners']
    for k in ch:lines.append(f"- {k}: hist {fmt(ch[k])} | 2026 {fmt(cf[k])}")
    lines += ['','## Limitations']+[f'- {x}' for x in out['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
