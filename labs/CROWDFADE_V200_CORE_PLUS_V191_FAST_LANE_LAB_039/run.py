from pathlib import Path
import json, math, zipfile, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Reuse frozen data parsing / metrics from the validated v200 lab runner.
_core_path=Path(__file__).resolve().parents[1]/'CROWDFADE_V200_SEQUENTIAL_CHANGE_LABS_033_035'/'run.py'
_spec=importlib.util.spec_from_file_location('crowdfade_core_033_035',_core_path)
core=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

# ---------- v200 CORE frozen research candidate ----------
CORE_Z=2.05
CORE_CONFIRM=.25
CORE_CONFIRM_TTL=3600
CORE_RETRACE=.60
CORE_PENDING_TTL=1200
CORE_SL=4.5
CORE_TP=10.0
CORE_HOLD=86400

# ---------- v191 FAST canonical defaults ----------
FAST_Z=1.00
FAST_CONFIRM=.30
FAST_CONFIRM_TTL=10800   # 36 M5 ~= 3h
FAST_SL=1.50
FAST_HOLD=21600          # 6h
FAST_EXIT_Z=.75
FAST_BE_AT=.50
FAST_BE_LOCK=.15
FAST_TRAIL_ATR=.50
FAST_TRAIL_ARM=2.50
FAST_PAUSE_ATR=1.00
MAXDAY=3

COST_BPS=.50

def load_flow_local():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        with z.open(names[0]) as f:
            r=pd.read_csv(f,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
    r['t']=pd.to_datetime(r.create_time,utc=True,errors='coerce')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['t','ratio']).sort_values('t').drop_duplicates('t')
    mu=r.ratio.rolling(72,min_periods=72).mean()
    sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    ft=r.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    return ft,r.z.to_numpy(float)

def read_binance_kline_zip(path):
    with zipfile.ZipFile(path) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        with z.open(names[0]) as f:
            r=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
    ts=pd.to_numeric(r.iloc[:,0],errors='coerce')
    med=np.nanmedian(ts.to_numpy(float))
    if med>1e15: ts=(ts//1_000_000).astype('Int64')
    elif med>1e12: ts=(ts//1000).astype('Int64')
    else: ts=ts.astype('Int64')
    q=pd.DataFrame({'ts':ts,'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),
                    'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),
                    'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),
                    'c':pd.to_numeric(r.iloc[:,4],errors='coerce')})
    return q.dropna()

def load_hist():
    parts=[]
    for zp in sorted((DATA/'hist_1m').glob('BTCUSDT-1m-*.zip')):
        parts.append(read_binance_kline_zip(zp))
    p=pd.concat(parts,ignore_index=True).drop_duplicates('ts').sort_values('ts')
    return tuple(p[x].to_numpy(np.int64 if x=='ts' else np.float64) for x in ['ts','o','h','l','c'])

def load_sec():
    zp=DATA/'BTCUSDT_sec.csv.zip'
    with zipfile.ZipFile(zp) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        with z.open(names[0]) as f:
            s=pd.read_csv(f,usecols=['ts','o','h','l','c'])
    s=s.sort_values('ts').drop_duplicates('ts')
    return (s.ts.to_numpy(np.int64),s.o.to_numpy(float),s.h.to_numpy(float),s.l.to_numpy(float),s.c.to_numpy(float))

def prep_m15(raw,ft,fz,start,end):
    return core.prep(raw,ft,fz,start,end)

def prep_m5(raw,ft,fz,start,end):
    ts,O,H,L,C=raw
    order=np.argsort(ts);ts=ts[order];O=O[order];H=H[order];L=L[order];C=C[order]
    keep=np.r_[True,ts[1:]!=ts[:-1]]
    ts=ts[keep];O=O[keep];H=H[keep];L=L[keep];C=C[keep]

    # M15 ATR, completed bars only.
    b15=(ts//900)*900
    st15=np.r_[0,np.flatnonzero(b15[1:]!=b15[:-1])+1]
    en15=np.r_[st15[1:],len(ts)]
    bt15=b15[st15]; bh15=np.maximum.reduceat(H,st15); bl15=np.minimum.reduceat(L,st15); bc15=C[en15-1]
    pc=np.r_[bc15[0],bc15[:-1]]
    tr=np.maximum(bh15-bl15,np.maximum(np.abs(bh15-pc),np.abs(bl15-pc)))
    atr15=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    av15=bt15+900

    # M5 completed-close signal cadence.
    b5=(ts//300)*300
    st5=np.r_[0,np.flatnonzero(b5[1:]!=b5[:-1])+1]
    en5=np.r_[st5[1:],len(ts)]
    bt5=b5[st5]; c5=C[en5-1]; av5=bt5+300

    fi=np.searchsorted(ft,av5,'left')-1
    ai=np.searchsorted(av15,av5,'right')-1
    fi0=np.maximum(fi,0);ai0=np.maximum(ai,0)
    good=(av5>=start)&(av5<end)&(fi>=0)&(ai>=0)&np.isfinite(fz[fi0])&np.isfinite(atr15[ai0])
    good &= ((av5-ft[fi0])>=0)&((av5-ft[fi0])<=600)

    return (ts,O,H,L,C,av5[good],c5[good],fz[fi[good]],atr15[ai[good]])

@njit(cache=True)
def core_events(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4):
    cap=len(dt)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=Z[k]
        side=-1 if z>=CORE_Z else (1 if z<=-CORE_Z else 0)
        if side==0:k+=1;continue
        sig=QC[k];siga=A[k]
        if has and abs(sig-last)<1.0*la:k+=1;continue

        lev=sig+side*CORE_CONFIRM*siga
        ci=-1;j=k+1
        while j<len(dt) and dt[j]<=t+CORE_CONFIRM_TTL:
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j;break
            j+=1
        if ci<0:k+=1;continue
        if z*Z[ci]<0.0:
            k=ci+1;continue

        entry=QC[ci]-side*CORE_RETRACE*siga
        ps=np.searchsorted(ts,dt[ci]+1);pe=np.searchsorted(ts,dt[ci]+CORE_PENDING_TTL,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):
                ei=q;break
        if ei<0:
            k=ci+1;continue

        risk=CORE_SL*siga;sl=entry-side*risk;tp=entry+side*CORE_TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+CORE_HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break
        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;ST[n]=t;ET[n]=ts[ei];XT[n]=ts[ex];SIDE[n]=side;n+=1
        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1
        k=np.searchsorted(dt,nextts)
    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n]

@njit(cache=True)
def fast_events(ts,O,H,L,C,dt5,C5,Z5,A5,mid_only,exit_mode,cancel_flip):
    # exit_mode 0=v191 management, 1=v200 exit geometry.
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0

    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue

        z=Z5[k];az=abs(z)
        if az<FAST_Z or (mid_only and az>=CORE_Z):
            k+=1;continue
        side=-1 if z>0 else 1
        sig=C5[k];siga=A5[k]
        if has and abs(sig-last)<FAST_PAUSE_ATR*la:
            k+=1;continue

        # v191 confirmation: live quote monitored during <=36 M5.
        # Replay approximation: first raw close crossing 0.30 ATR, sampled at raw resolution.
        target=sig+side*FAST_CONFIRM*siga
        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+FAST_CONFIRM_TTL,'right')
        ci=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and C[q]>=target) or (side<0 and C[q]<=target):
                ci=q;break
        if ci<0:
            k+=1;continue

        # Current Z at confirmation from latest valid M5 state.
        zk=np.searchsorted(dt5,ts[ci],'right')-1
        if zk<0:
            k+=1;continue
        if cancel_flip and z*Z5[zk]<0.0:
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        entry=C[ci]
        ei=ci

        if exit_mode==1:
            risk=CORE_SL*siga;sl=entry-side*risk;tp=entry+side*CORE_TP*siga
            xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+CORE_HOLD,'left'))
            xp=C[xe];ex=xe
            for q in range(ei+1,xe+1):
                sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
                th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
                if sh:xp=sl;ex=q;break
                if th:xp=tp;ex=q;break
            rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        else:
            # v191 management: SL1.5, BE .5=>+.15, trailing .5 arm2.5,
            # signal exit at opposite z .75, time exit H6. No TP.
            risk=FAST_SL*siga
            curstop=entry-side*risk
            peak=entry
            xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+FAST_HOLD,'left'))
            xp=C[xe];ex=xe
            for q in range(ei+1,xe+1):
                # Existing protective stop is active before this bar's management update.
                hit=(side>0 and L[q]<=curstop) or (side<0 and H[q]>=curstop)
                if hit:
                    xp=curstop;ex=q;break

                close=C[q]
                prof=side*(close-entry)
                if prof>=FAST_BE_AT*siga:
                    belvl=entry+side*FAST_BE_LOCK*siga
                    if (side>0 and belvl>curstop) or (side<0 and belvl<curstop):
                        curstop=belvl

                if side>0:
                    if close>peak:peak=close
                    mfe=(peak-entry)/siga
                    if mfe>=FAST_TRAIL_ARM:
                        tr=peak-FAST_TRAIL_ATR*siga
                        if tr>curstop:curstop=tr
                else:
                    if close<peak:peak=close
                    mfe=(entry-peak)/siga
                    if mfe>=FAST_TRAIL_ARM:
                        tr=peak+FAST_TRAIL_ATR*siga
                        if tr<curstop:curstop=tr

                zi=np.searchsorted(dt5,ts[q],'right')-1
                if zi>=0:
                    znow=Z5[zi]
                    against=(side>0 and znow>=FAST_EXIT_Z) or (side<0 and znow<=-FAST_EXIT_Z)
                    if against:
                        xp=close;ex=q;break
            rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk

        R[n]=rr;ST[n]=t;ET[n]=ts[ei];XT[n]=ts[ex];SIDE[n]=side;n+=1
        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1
        k=np.searchsorted(dt5,nextts)

    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n]

def df_from(z,lane):
    R,st,et,xt,side=z
    return pd.DataFrame({'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,'lane':lane})

def metrics_arr(r):
    return core.metrics(np.asarray(r,float))

def lane_metrics(df,months):
    m=metrics_arr(df.R.to_numpy(float))
    m['trades_per_month']=len(df)/months
    return m

def portfolio(core_df,fast_df,fast_mult,months):
    a=core_df[['R','signal_ts','entry_ts','exit_ts','lane']].copy();a['w']=1.0
    b=fast_df[['R','signal_ts','entry_ts','exit_ts','lane']].copy();b['w']=fast_mult
    p=pd.concat([a,b],ignore_index=True)
    p['weighted_R']=p.R*p.w
    # Equity is realized on exit; ties broken CORE first, then signal time.
    p['lane_order']=np.where(p.lane.eq('CORE'),0,1)
    p=p.sort_values(['exit_ts','lane_order','signal_ts']).reset_index(drop=True)
    m=metrics_arr(p.weighted_R.to_numpy(float))
    m['trades']=len(p);m['trades_per_month']=len(p)/months
    m['core_trades']=len(a);m['fast_trades']=len(b)
    m['raw_sumR']=float(p.R.sum());m['weighted_sumR']=float(p.weighted_R.sum())

    # Peak simultaneous planned stop-risk, in CORE risk units.
    ev=[]
    for _,r in p.iterrows():
        ev.append((int(r.entry_ts),1,float(r.w)))
        ev.append((int(r.exit_ts),-1,float(r.w)))
    ev.sort(key=lambda x:(x[0],x[1])) # close before open at identical time
    cur=0.;mx=0.
    for _,typ,w in ev:
        cur += w if typ==1 else -w
        if cur>mx:mx=cur
    m['max_concurrent_risk_units']=float(mx)
    return m,p

def fmt(m):
    return f"N={m.get('N',m.get('trades',0))} ({m.get('trades_per_month',0):.1f}/mo) EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f}"

def run_period(raw,ft,fz,start,end,months,label):
    m15=prep_m15(raw,ft,fz,start,end)
    m5=prep_m5(raw,ft,fz,start,end)

    core_df=df_from(core_events(*m15),'CORE')
    fast191=df_from(fast_events(*m5,True,0,True),'FAST191')
    fastv200=df_from(fast_events(*m5,True,1,True),'FASTV200')
    fastall=df_from(fast_events(*m5,False,0,False),'V191_REF')

    out={
      'CORE':lane_metrics(core_df,months),
      'FAST_MID_V191_EXIT':lane_metrics(fast191,months),
      'FAST_MID_V200_EXIT':lane_metrics(fastv200,months),
      'V191_LIKE_FULL_REFERENCE':lane_metrics(fastall,months),
      'portfolios':{}
    }
    pdfs={}
    for fname,fdf in [('FAST191',fast191),('FASTV200',fastv200)]:
        for mult in [0.50,0.40]:
            k=f'CORE_PLUS_{fname}_RISK{mult:.2f}'
            pm,pdf=portfolio(core_df,fdf,mult,months)
            out['portfolios'][k]=pm;pdfs[k]=pdf

    core_df.to_csv(OUT/f'{label}_core.csv',index=False)
    fast191.to_csv(OUT/f'{label}_fast191.csv',index=False)
    fastv200.to_csv(OUT/f'{label}_fastv200.csv',index=False)
    return out,pdfs

def main():
    ft,fz=load_flow_local()
    hist_raw=load_hist();fwd_raw=load_sec()

    hist,hpdf=run_period(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
                         int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),60,'historical')
    fwd,fpdf=run_period(fwd_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
                        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),6,'forward')

    result={
      'lab':'V200_CORE_PLUS_V191_FAST_LANE_LAB_039',
      'architecture':{
        'CORE':'v200 frozen research candidate: |Z|>=2.05, M15 confirm .25, passive .60, TTL20, SL4.5, TP10, H24, cancel sign flip',
        'FAST':'incremental lane only: 1.0<=|Z|<2.05; v191 cadence M5 / confirm .30 / <=3h / market; ATR M15; pause 1 ATR; max 3/day',
        'FAST_EXIT_A':'v191: SL1.5, BE .5=>+.15, trail .5 arm2.5, ExitZ .75, H6',
        'FAST_EXIT_B':'v200: SL4.5, TP10, H24, no BE/trail/signal-exit',
        'portfolio_risk':'CORE 1.0 risk unit; FAST 0.50x or 0.40x; independent lanes may overlap, concurrency audited'
      },
      'historical':hist,'forward':fwd,
      'limitations':[
        'BTC only; ETH/SOL transfer is required.',
        '2021-2025 is discovery/in-sample; 2026 Mar-Aug is reused forward-shadow.',
        'v191 live confirmation is timer/quote based; replay approximates market confirmation using first raw close crossing 0.30 ATR.',
        'v191 broker spread, BE/freeze-level execution and slippage are not modeled beyond flat 0.5 bps research cost.',
        'v191 score-based lot weighting is intentionally omitted; FAST risk is fixed at 0.50x/0.40x for clean lane attribution.',
        'CORE and FAST are independent concurrent lanes in portfolio mode; same-symbol aggregate exposure is represented by max_concurrent_risk_units.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))

    rows=[]
    for period,d in [('historical',hist),('2026',fwd)]:
        for k in ['CORE','FAST_MID_V191_EXIT','FAST_MID_V200_EXIT','V191_LIKE_FULL_REFERENCE']:
            m=d[k];rows.append({'period':period,'variant':k,**{x:m[x] for x in ['N','trades_per_month','EV','PF','SumR','MaxDD_R','R_DD','MaxConsecutiveLosses']}})
        for k,m in d['portfolios'].items():
            rows.append({'period':period,'variant':k,'N':m['trades'],'trades_per_month':m['trades_per_month'],
                         'EV':m['EV'],'PF':m['PF'],'SumR':m['SumR'],'MaxDD_R':m['MaxDD_R'],'R_DD':m['R_DD'],
                         'MaxConsecutiveLosses':m['MaxConsecutiveLosses'],'max_concurrent_risk_units':m['max_concurrent_risk_units']})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)

    lines=['# LAB039 — V200 CORE + V191 FAST LANE','',
           'CORE remains untouched. FAST only handles 1.0 <= |Z| < 2.05.','',
           '## Standalone lanes',
           f"- Hist CORE: {fmt(hist['CORE'])}",
           f"- Hist FAST + v191 exits: {fmt(hist['FAST_MID_V191_EXIT'])}",
           f"- Hist FAST + v200 exits: {fmt(hist['FAST_MID_V200_EXIT'])}",
           f"- Hist v191-like full reference: {fmt(hist['V191_LIKE_FULL_REFERENCE'])}",
           f"- 2026 CORE: {fmt(fwd['CORE'])}",
           f"- 2026 FAST + v191 exits: {fmt(fwd['FAST_MID_V191_EXIT'])}",
           f"- 2026 FAST + v200 exits: {fmt(fwd['FAST_MID_V200_EXIT'])}",
           f"- 2026 v191-like full reference: {fmt(fwd['V191_LIKE_FULL_REFERENCE'])}",'',
           '## Combined portfolio']
    for k in hist['portfolios']:
        hm=hist['portfolios'][k];fm=fwd['portfolios'][k]
        lines.append(f"- {k}: hist {fmt(hm)} maxRisk={hm['max_concurrent_risk_units']:.2f}u | 2026 {fmt(fm)} maxRisk={fm['max_concurrent_risk_units']:.2f}u")
    lines += ['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
