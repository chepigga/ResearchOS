from pathlib import Path
import zipfile, json
import numpy as np, pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_TREND_TRANSITION_AND_REVERSAL_RISK_LAB_031')
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Current v200 live-candidate signal / frozen execution
ZTH=2.05
CONF=.25; CONF_TTL=3600
RETRACE=.60; PTTL=1200
SL=4.5; TP=10.0; HOLD=86400
COST_BPS=.50; MAXDAY=3

# Current LAB026 quality sizing, then a transition overlay.
RISK_MODES=[
 ('LAB026_BASE',1.00,False),
 ('STALE_H4_075',0.75,False),
 ('STALE_H4_050',0.50,False),
 ('STALE_H4_VETO',0.00,False),
 ('ALL_CONFLICT_075',0.75,True),
]

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

def tf_states(ts,C,sec):
    b=(ts//sec)*sec
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]
    en=np.r_[st[1:],len(ts)]
    close=C[en-1]; bt=b[st]
    ema=pd.Series(close).ewm(span=50,adjust=False).mean().to_numpy()
    lag4=pd.Series(ema).shift(4).to_numpy()
    state=np.where((close>ema)&(ema>lag4),1,np.where((close<ema)&(ema<lag4),-1,0)).astype(np.int64)
    av=(bt+sec).astype(np.int64)
    return av,state

def prep_from_arrays(ts,O,H,L,C,ft,fz,start_ts,end_ts):
    order=np.argsort(ts); ts=ts[order];O=O[order];H=H[order];L=L[order];C=C[order]
    keep=np.r_[True,ts[1:]!=ts[:-1]]
    ts=ts[keep];O=O[keep];H=H[keep];L=L[keep];C=C[keep]

    # completed M15 bars + ATR14 SMA true range
    b=(ts//900)*900
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]; en=np.r_[st[1:],len(ts)]
    bt=b[st]; bh=np.maximum.reduceat(H,st); bl=np.minimum.reduceat(L,st); bc=C[en-1]
    pc=np.r_[bc[0],bc[:-1]]
    tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    av=bt+900

    h1t,h1s=tf_states(ts,C,3600)
    h4t,h4s=tf_states(ts,C,14400)

    # M15 decision points use completed bars only
    dt=av.copy(); qh=bh.copy(); ql=bl.copy(); qc=bc.copy()
    fi=np.searchsorted(ft,dt,'left')-1
    ai=np.arange(len(dt))
    h1i=np.searchsorted(h1t,dt,'right')-1
    h4i=np.searchsorted(h4t,dt,'right')-1

    good=(dt>=start_ts)&(dt<end_ts)&(fi>=0)&(h1i>=1)&(h4i>=1)&np.isfinite(atr)&np.isfinite(fz[np.maximum(fi,0)])
    # enforce flow freshness <=10m, as in lineage
    fi0=np.maximum(fi,0)
    good &= ((dt-ft[fi0])>=0)&((dt-ft[fi0])<=600)

    return (ts,O,H,L,C,
            dt[good],qh[good],ql[good],qc[good],fz[fi[good]],atr[good],
            h1s[h1i[good]],h4s[h4i[good]],
            h1s[h1i[good]-1],h4s[h4i[good]-1])

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
def sim(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,H1P,H4P):
    cap=len(dt)
    R=np.zeros(cap); SIDE=np.zeros(cap,np.int8)
    H1A=np.zeros(cap,np.int8);H4A=np.zeros(cap,np.int8);H1PA=np.zeros(cap,np.int8);H4PA=np.zeros(cap,np.int8)
    CEX=np.zeros(cap); CB=np.zeros(cap,np.int8); ET=np.zeros(cap,np.int64); ST=np.zeros(cap,np.int64); ZA=np.zeros(cap)
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

        lev=sig+side*CONF*a;ci=-1;maxcrowd=0.
        crowd=-side
        j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/a
            if exc>maxcrowd:maxcrowd=exc
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
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]>=tp) # overwritten below for shorts
            if side<0: th=H[q]>=1e300  # reset impossible placeholder
            if side<0: th=L[q]<=tp
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break

        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;SIDE[n]=side;H1A[n]=H1[k];H4A[n]=H4[k];H1PA[n]=H1P[k];H4PA[n]=H4P[k]
        CEX[n]=maxcrowd;CB[n]=ci-k;ET[n]=ts[ei];ST[n]=t;ZA[n]=abs(z);n+=1
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt,nextts)
    return R[:n],SIDE[:n],H1A[:n],H4A[:n],H1PA[:n],H4PA[:n],CEX[:n],CB[:n],ET[:n],ST[:n],ZA[:n]

def metrics(x):
    x=np.asarray(x,float)
    if not len(x): return {'N':0}
    eq=np.cumsum(x);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
    pos=x[x>0].sum();neg=abs(x[x<0].sum())
    cur=mx=0
    for v in x:
        if v<0: cur+=1;mx=max(mx,cur)
        else: cur=0
    return {'N':int(len(x)),'WR':float((x>0).mean()),'EV':float(x.mean()),'SumR':float(x.sum()),
            'PF':float(pos/neg) if neg else 99.,'MaxDD_R':float(dd.max()) if len(dd) else 0.,
            'R_DD':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else 99.,
            'MaxConsecutiveLosses':int(mx)}

def classify(side,h1,h4,h1p,h4p,cex):
    aligned=(h1!=0)&(h4!=0)&(h1==h4)
    conflict=(h1!=0)&(h4!=0)&(h1==-h4)
    withtrend=aligned&(side==h1)
    counter=aligned&(side==-h1)
    follow_h1=conflict&(side==h1)
    follow_h4=conflict&(side==h4)
    other=~(aligned|conflict)

    # A causal onset flag: current H1/H4 conflict, but prior completed H1 was not already at current H1 state.
    onset=conflict&(h1p!=h1)
    persistent=conflict&(h1p==h1)

    state=np.full(len(side),'MIXED_NEUTRAL',dtype=object)
    state[withtrend]='ALIGNED_WITH'
    state[counter]='ALIGNED_COUNTER'
    state[follow_h1]='CONFLICT_FOLLOW_H1'
    state[follow_h4]='CONFLICT_FOLLOW_H4'

    # LAB026 current quality weights recomputed on the current Z=2.05 sequence.
    high=withtrend&(cex<=.75)
    low=aligned&(cex>.75)
    qmult=np.ones(len(side))
    qmult[high]=1.5
    qmult[low]=.75
    qstate=np.where(high,'HIGH',np.where(low,'LOW','NORMAL'))
    return state,conflict,follow_h1,follow_h4,onset,persistent,qmult,qstate

def period_report(name,arr):
    R,side,h1,h4,h1p,h4p,cex,cb,et,st,zabs=sim(*arr)
    state,conflict,fh1,fh4,onset,persistent,qmult,qstate=classify(side,h1,h4,h1p,h4p,cex)
    raw=pd.DataFrame({'signal_ts':st,'entry_ts':et,'R':R,'side':side,'h1':h1,'h4':h4,'h1_prev':h1p,'h4_prev':h4p,
                      'abs_z':zabs,'crowd_excursion_atr':cex,'confirm_bars':cb,'transition_state':state,
                      'conflict':conflict,'follow_h1':fh1,'follow_h4':fh4,'conflict_onset':onset,'conflict_persistent':persistent,
                      'lab026_quality':qstate,'lab026_mult':qmult})
    raw['signal_time_utc']=pd.to_datetime(raw.signal_ts,unit='s',utc=True)
    raw['entry_time_utc']=pd.to_datetime(raw.entry_ts,unit='s',utc=True)

    buckets={}
    for sname in ['ALIGNED_WITH','ALIGNED_COUNTER','CONFLICT_FOLLOW_H1','CONFLICT_FOLLOW_H4','MIXED_NEUTRAL']:
        m=state==sname;buckets[sname]=metrics(R[m])
    buckets['CONFLICT_ONSET']=metrics(R[onset])
    buckets['CONFLICT_PERSISTENT']=metrics(R[persistent])

    modes=[]
    seqs=[]
    for mname,mult,broad in RISK_MODES:
        overlay=np.ones(len(R))
        target=conflict if broad else fh4
        overlay[target]=mult
        weighted=R*qmult*overlay
        if name=='historical':
            labels=raw.signal_time_utc.dt.year.astype(str).to_numpy()
            wanted=[str(y) for y in range(2021,2026)]
            key='annual'
        else:
            labels=raw.signal_time_utc.dt.to_period('M').astype(str).to_numpy()
            wanted=sorted(set(labels));key='monthly'
        sub={lab:metrics(weighted[labels==lab]) for lab in wanted}
        eq=np.cumsum(weighted);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
        modes.append({'name':mname,'overlay_multiplier':mult,'overlay_target':'ALL_CONFLICT' if broad else 'CONFLICT_FOLLOW_H4',
                      'all':metrics(weighted),'positive_periods':int(sum(v.get('SumR',0)>0 for v in sub.values())),key:sub})
        q=raw.copy();q['mode']=mname;q['overlay_mult']=overlay;q['weighted_R']=weighted;q['equity_R']=eq;q['drawdown_R']=dd
        seqs.append(q)

    pd.concat(seqs,ignore_index=True).to_csv(OUT/f'equity_sequence_{name}.csv',index=False)
    raw.to_csv(OUT/f'trades_{name}.csv',index=False)

    return {'period':name,'z_threshold':ZTH,'baseline_raw':metrics(R),'state_buckets_raw':buckets,
            'state_counts':{k:int((state==k).sum()) for k in ['ALIGNED_WITH','ALIGNED_COUNTER','CONFLICT_FOLLOW_H1','CONFLICT_FOLLOW_H4','MIXED_NEUTRAL']},
            'conflict_onset_count':int(onset.sum()),'conflict_persistent_count':int(persistent.sum()),
            'lab026_quality_counts':{k:int((qstate==k).sum()) for k in ['HIGH','NORMAL','LOW']},
            'risk_modes':modes}

def main():
    hist=load_hist(); fwd=load_2026()
    # warm JIT
    sim(*[x[:min(3000,len(x))] for x in hist])
    out={
      'lab':'CROWDFADE_TREND_TRANSITION_AND_REVERSAL_RISK_LAB_031',
      'question':'Does H1/H4 transition state identify reversal risk, especially trades that follow stale H4 while H1 points opposite?',
      'frozen_candidate':{'Z':ZTH,'confirm_ATR':CONF,'confirm_TTL_min':CONF_TTL//60,'retrace_ATR':RETRACE,
                          'limit_TTL_min':PTTL//60,'SL_ATR':SL,'TP_ATR':TP,'hold_h':HOLD//3600,'cost_bps':COST_BPS,
                          'max_trades_day':MAXDAY,'anti_repeat_ATR':1.0},
      'trend_definition':{'H1_H4':'completed-bar close vs EMA50 plus EMA50 vs EMA50[-4] slope',
                          'ALIGNED_WITH':'H1=H4 non-neutral and trade side follows both',
                          'ALIGNED_COUNTER':'H1=H4 non-neutral and trade side opposes both',
                          'CONFLICT_FOLLOW_H1':'H1 and H4 opposite; trade follows H1 (newer timeframe)',
                          'CONFLICT_FOLLOW_H4':'H1 and H4 opposite; trade follows H4 and opposes H1 (stale-H4 risk hypothesis)',
                          'CONFLICT_ONSET':'H1/H4 conflict and prior completed H1 state was not already current H1 state'},
      'risk_test':'Start from current LAB026 quality multipliers HIGH=1.5/NORMAL=1/LOW=.75, then apply transition overlay only. No entry/exit changes.',
      'historical':period_report('historical',hist),
      'forward_shadow_2026':period_report('2026_Mar_Aug',fwd),
      'limitations':['BTCUSDT research lineage only.','2026 Mar-Aug is reused forward-shadow/stress, not pristine OOS.',
                     'September 18 live trades are not included because the released research flow archive ends August 2026.',
                     'Risk overlays preserve trade reachability except the explicit veto control; they are not broker margin simulations.']
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':
    main()
