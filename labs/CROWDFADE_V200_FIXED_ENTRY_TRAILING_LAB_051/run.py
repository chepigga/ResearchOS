from pathlib import Path
import zipfile, json
import numpy as np, pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_V200_FIXED_ENTRY_TRAILING_LAB_051')
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.05
CONF=.25; CONF_TTL=3600
RETRACE=.60; PTTL=1200
SL=4.5; TP=10.0; HOLD=86400
COST_BPS=.50; MAXDAY=3

MODES=[
 ('CONTROL',0.0,0.0),
 ('T25_G05',2.5,0.5),
 ('T35_G05',3.5,0.5),
 ('T50_G05',5.0,0.5),
 ('T80_G10',8.0,1.0),
 ('T80_G20',8.0,2.0),
]

EXPECT={
 'historical': {'N':1642,'SumR':122.39971058019937},
 '2026_Mar_Aug': {'N':176,'SumR':17.115236780278384},
}

def unzip_first(zp,outdir):
    outdir.mkdir(parents=True,exist_ok=True)
    if not list(outdir.rglob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(outdir)
    fs=list(outdir.rglob('*.csv'))
    if not fs: raise RuntimeError(f'No csv extracted from {zp}')
    return fs[0]

def load_flow(path):
    r=pd.read_csv(path,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
    r['t']=pd.to_datetime(r.create_time,utc=True,errors='coerce')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['t','ratio']).sort_values('t').drop_duplicates('t')
    mu=r.ratio.rolling(72,min_periods=72).mean()
    sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    ft=r.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    return ft,r.z.to_numpy(float)

def prep_from_arrays(ts,O,H,L,C,ft,fz,start_ts,end_ts):
    order=np.argsort(ts);ts=ts[order];O=O[order];H=H[order];L=L[order];C=C[order]
    keep=np.r_[True,ts[1:]!=ts[:-1]]
    ts=ts[keep];O=O[keep];H=H[keep];L=L[keep];C=C[keep]

    b=(ts//900)*900
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1];en=np.r_[st[1:],len(ts)]
    bt=b[st];bh=np.maximum.reduceat(H,st);bl=np.minimum.reduceat(L,st);bc=C[en-1]
    pc=np.r_[bc[0],bc[:-1]]
    tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    av=bt+900

    dt=av.copy();qc=bc.copy()
    fi=np.searchsorted(ft,dt,'left')-1
    fi0=np.maximum(fi,0)
    good=(dt>=start_ts)&(dt<end_ts)&(fi>=0)&np.isfinite(atr)&np.isfinite(fz[fi0])
    good &= ((dt-ft[fi0])>=0)&((dt-ft[fi0])<=600)
    return (ts,O,H,L,C,dt[good],qc[good],fz[fi[good]],atr[good])

def load_hist():
    ps=[]
    kdir=DATA/'hist_1m'
    for zp in sorted(kdir.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
        ps.append(pd.DataFrame({
          'ts':pd.to_numeric(r.iloc[:,0],errors='coerce')//1000,
          'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),
          'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),
          'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),
          'c':pd.to_numeric(r.iloc[:,4],errors='coerce')}).dropna())
    p=pd.concat(ps,ignore_index=True).drop_duplicates('ts').sort_values('ts')
    flow=unzip_first(DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip',DATA/'flow_hist')
    ft,fz=load_flow(flow)
    return prep_from_arrays(
      p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
      ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))

def load_2026():
    sf=unzip_first(DATA/'BTCUSDT_sec.csv.zip',DATA/'sec_2026')
    s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts')
    flow=unzip_first(DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip',DATA/'flow_2026')
    ft,fz=load_flow(flow)
    return prep_from_arrays(
      s.ts.to_numpy(np.int64),s.o.to_numpy(float),s.h.to_numpy(float),s.l.to_numpy(float),s.c.to_numpy(float),
      ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))

@njit(cache=True)
def extract_fixed_entries(ts,O,H,L,C,dt,QC,Z,A):
    cap=len(dt)
    EIDX=np.zeros(cap,np.int64); ENTRY=np.zeros(cap); ATR=np.zeros(cap); SIDE=np.zeros(cap,np.int8)
    ST=np.zeros(cap,np.int64); ET=np.zeros(cap,np.int64); BASE=np.zeros(cap)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=Z[k]
        side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=QC[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a;ci=-1
        j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j;break
            j+=1
        if ci<0:k+=1;continue

        entry=QC[ci]-side*RETRACE*a
        ps=np.searchsorted(ts,dt[ci]+1);pe=np.searchsorted(ts,dt[ci]+PTTL,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):
                ei=q;break
        if ei<0:k=ci+1;continue

        risk=SL*a;sl=entry-side*risk;tp=entry+side*TP*a
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break
        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk

        EIDX[n]=ei;ENTRY[n]=entry;ATR[n]=a;SIDE[n]=side;ST[n]=t;ET[n]=ts[ei];BASE[n]=rr;n+=1
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt,nextts)
    return EIDX[:n],ENTRY[:n],ATR[:n],SIDE[:n],ST[:n],ET[:n],BASE[:n]

@njit(cache=True)
def replay_fixed(ts,O,H,L,C,eidx,entry,atr,side,arm_atr,gap_atr):
    n=len(eidx)
    out=np.zeros(n); reason=np.zeros(n,np.int8); exit_ts=np.zeros(n,np.int64)
    # reason: -1 SL, 0 TIME, 1 TP, 2 TRAIL
    for i in range(n):
        ei=eidx[i]; ep=entry[i]; a=atr[i]; sd=side[i]
        risk=SL*a; stop0=ep-sd*risk; tp=ep+sd*TP*a
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD,'left'))
        xp=C[xe];ex=xe;why=0
        stop=stop0; pending=stop0; peak=ep
        active=False
        for q in range(ei+1,xe+1):
            stop=pending
            sh=(sd>0 and L[q]<=stop) or (sd<0 and H[q]>=stop)
            th=(sd>0 and H[q]>=tp) or (sd<0 and L[q]<=tp)
            if sh:
                xp=stop;ex=q;why=2 if active and abs(stop-stop0)>1e-12 else -1;break
            if th:
                xp=tp;ex=q;why=1;break

            if arm_atr>0.0:
                if sd>0:
                    if H[q]>peak: peak=H[q]
                    fav=(peak-ep)/a
                else:
                    if L[q]<peak: peak=L[q]
                    fav=(ep-peak)/a
                if fav>=arm_atr:
                    active=True
                    cand=peak-sd*gap_atr*a
                    if sd>0:
                        if cand>pending:pending=cand
                    else:
                        if cand<pending:pending=cand

        out[i]=sd*(xp-ep)/risk-(COST_BPS/10000.)*ep/risk
        reason[i]=why;exit_ts[i]=ts[ex]
    return out,reason,exit_ts

def metrics(x):
    x=np.asarray(x,float)
    if not len(x):return {'N':0}
    eq=np.cumsum(x);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
    pos=x[x>0].sum();neg=abs(x[x<0].sum())
    cur=mx=0
    for v in x:
        if v<0:cur+=1;mx=max(mx,cur)
        else:cur=0
    return {'N':int(len(x)),'WR':float((x>0).mean()),'EV':float(x.mean()),'SumR':float(x.sum()),
            'PF':float(pos/neg) if neg else 99.,'MaxDD_R':float(dd.max()) if len(dd) else 0.,
            'R_DD':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else 99.,
            'MaxConsecutiveLosses':int(mx)}

def run_period(name,arr):
    ts,O,H,L,C,dt,QC,Z,A=arr
    eidx,entry,atr,side,st,et,base=extract_fixed_entries(*arr)
    exp=EXPECT[name]
    parity={'N_expected':exp['N'],'N_actual':int(len(base)),
            'SumR_expected':exp['SumR'],'SumR_actual':float(base.sum()),
            'N_match':int(len(base))==exp['N'],'SumR_abs_diff':abs(float(base.sum())-exp['SumR'])}
    if not parity['N_match'] or parity['SumR_abs_diff']>1e-6:
        raise RuntimeError(f'BASE PARITY FAIL {name}: {parity}')

    labels=(pd.to_datetime(st,unit='s',utc=True).year.astype(str).to_numpy()
            if name=='historical' else
            pd.to_datetime(st,unit='s',utc=True).to_period('M').astype(str).to_numpy())
    wanted=sorted(set(labels))
    key='annual' if name=='historical' else 'monthly'

    rows=[];seqs=[]
    control=None
    for mname,arm,gap in MODES:
        if mname=='CONTROL':
            r=base.copy()
            reason=np.zeros(len(r),np.int8)
            xt=np.zeros(len(r),np.int64)
        else:
            r,reason,xt=replay_fixed(ts,O,H,L,C,eidx,entry,atr,side,arm,gap)
        if control is None:control=r.copy()
        sub={lab:metrics(r[labels==lab]) for lab in wanted}
        mm=metrics(r)
        delta=r-control
        rows.append({'name':mname,'arm_ATR':arm,'gap_ATR':gap,'all':mm,
                     'delta_vs_control':{'SumR':float(r.sum()-control.sum()),
                                         'EV':float(r.mean()-control.mean()),
                                         'MaxDD_R':float(mm['MaxDD_R']-metrics(control)['MaxDD_R'])},
                     'positive_periods':int(sum(v.get('SumR',0)>0 for v in sub.values())),
                     key:sub,
                     'exit_mix':{'SL':int((reason==-1).sum()),'TIME':int((reason==0).sum()),
                                 'TP':int((reason==1).sum()),'TRAIL':int((reason==2).sum())}})
        eq=np.cumsum(r);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
        seqs.append(pd.DataFrame({'mode':mname,'trade_index':np.arange(1,len(r)+1),
                                  'signal_ts':st,'entry_ts':et,'side':side,'entry':entry,'atr':atr,
                                  'R':r,'delta_R_vs_control':delta,'equity_R':eq,'drawdown_R':dd,
                                  'exit_reason_code':reason}))
    pd.concat(seqs,ignore_index=True).to_csv(OUT/f'equity_sequence_{name}.csv',index=False)
    return {'period':name,'fixed_entry_parity':parity,'results':rows}

def main():
    hist=load_hist();fwd=load_2026()
    extract_fixed_entries(*[x[:min(len(x),4000)] for x in hist])
    out={
      'lab':'CROWDFADE_V200_FIXED_ENTRY_TRAILING_LAB_051',
      'question':'What happens if trailing is added to frozen V200 Z2.05 without changing entries?',
      'frozen':{'Z':ZTH,'confirm_ATR':CONF,'confirm_TTL_min':60,'retrace_ATR':RETRACE,
                'pending_TTL_min':20,'SL_ATR':SL,'TP_ATR':TP,'hold_h':24,
                'cost_bps':COST_BPS,'max_trades_day':MAXDAY,'anti_repeat_ATR':1.0},
      'fixed_entry_rule':'Baseline no-trail occupancy generates entries once. Every trail variant replays exits on exactly those frozen entries; changed exit times cannot add/delete later entries.',
      'causality':'Trailing level is updated after each completed source observation and becomes active on the next observation.',
      'modes':[{'name':n,'arm_ATR':a,'gap_ATR':g} for n,a,g in MODES],
      'historical':run_period('historical',hist),
      'forward_shadow_2026':run_period('2026_Mar_Aug',fwd),
      'limitations':['BTCUSDT research lineage only.',
                     'Historical path is 1m OHLC; 2026 Mar-Aug uses frozen 1-second archive.',
                     '2026 is reused forward-shadow/stress, not pristine OOS.',
                     'This is a fixed-entry exit counterfactual, not a stateful rerun with changed occupancy.']
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    rows=[]
    for period_key in ['historical','forward_shadow_2026']:
        for x in out[period_key]['results']:
            rows.append({'period':period_key,'mode':x['name'],'arm_ATR':x['arm_ATR'],'gap_ATR':x['gap_ATR'],
                         **x['all'],'DeltaSumR':x['delta_vs_control']['SumR'],
                         'DeltaEV':x['delta_vs_control']['EV'],'DeltaDD':x['delta_vs_control']['MaxDD_R'],
                         'PositivePeriods':x['positive_periods'],**{f"Exit_{k}":v for k,v in x['exit_mix'].items()}})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
