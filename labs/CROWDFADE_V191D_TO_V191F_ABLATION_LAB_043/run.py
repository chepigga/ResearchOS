from pathlib import Path
import json, zipfile
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

COST_BPS=0.50
MAXDAY=3
PAUSE_ATR=1.0

# v191 family frozen management
V191_Z=1.00
V191_CONFIRM_ATR=0.30
V191_SL=1.50
V191_BE_ARM=0.50
V191_BE_LOCK=0.15
V191_TRAIL_ARM=2.50
V191_TRAIL_GAP=0.50
V191_HOLD=6*3600

# v192 canonical immutable control
V192_Z=2.50
V192_CONFIRM_ATR=0.25
V192_CONFIRM_TTL=60*60
V192_RETRACE_ATR=0.60
V192_PENDING_TTL=20*60
V192_SL=4.50
V192_TP=10.0
V192_HOLD=24*3600

V191D=0
V191E_EXIT_OFF=1
V191E_SAMESIDE=2
V191F_FRESH45=3
V191F_MINZ=4
V191F_ADVERSE=5
V191F_FULL=6
NAMES={
0:'V191D_CONTROL',
1:'V191E1_EXITZ_OFF_ONLY',
2:'V191E2_SAMESIDE_CONFIRM',
3:'V191F1_FRESH45',
4:'V191F2_MIN_CONFIRM_Z075',
5:'V191F3_MAX_ADVERSE075',
6:'V191F4_FULL_RESPONSE050'
}

def load_flow():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:
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

def read_zip(path):
    with zipfile.ZipFile(path) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:r=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
    ts=pd.to_numeric(r.iloc[:,0],errors='coerce')
    med=np.nanmedian(ts.to_numpy(float))
    if med>1e15: ts=(ts//1_000_000).astype('Int64')
    elif med>1e12: ts=(ts//1000).astype('Int64')
    else: ts=ts.astype('Int64')
    q=pd.DataFrame({
      'ts':ts,
      'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),
      'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),
      'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),
      'c':pd.to_numeric(r.iloc[:,4],errors='coerce')})
    return q.dropna()

def load_hist():
    ps=[read_zip(x) for x in sorted((DATA/'hist_1m').glob('BTCUSDT-1m-*.zip'))]
    p=pd.concat(ps,ignore_index=True).drop_duplicates('ts').sort_values('ts')
    return tuple(p[x].to_numpy(np.int64 if x=='ts' else np.float64) for x in ['ts','o','h','l','c'])

def load_sec():
    with zipfile.ZipFile(DATA/'BTCUSDT_sec.csv.zip') as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:s=pd.read_csv(f,usecols=['ts','o','h','l','c'])
    s=s.sort_values('ts').drop_duplicates('ts')
    return tuple(s[x].to_numpy(np.int64 if x=='ts' else np.float64) for x in ['ts','o','h','l','c'])

def prep(raw,ft,fz,start,end):
    ts,O,H,L,C=raw
    order=np.argsort(ts); ts=ts[order];O=O[order];H=H[order];L=L[order];C=C[order]
    keep=np.r_[True,ts[1:]!=ts[:-1]]
    ts=ts[keep];O=O[keep];H=H[keep];L=L[keep];C=C[keep]

    # completed M15 ATR14
    b15=(ts//900)*900
    st15=np.r_[0,np.flatnonzero(b15[1:]!=b15[:-1])+1]
    en15=np.r_[st15[1:],len(ts)]
    bt15=b15[st15]; bh15=np.maximum.reduceat(H,st15); bl15=np.minimum.reduceat(L,st15); bc15=C[en15-1]
    pc=np.r_[bc15[0],bc15[:-1]]
    tr=np.maximum(bh15-bl15,np.maximum(np.abs(bh15-pc),np.abs(bl15-pc)))
    atr15=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    av15=bt15+900

    # completed M5 decision clock
    b5=(ts//300)*300
    st5=np.r_[0,np.flatnonzero(b5[1:]!=b5[:-1])+1]
    en5=np.r_[st5[1:],len(ts)]
    bt5=b5[st5]; h5=np.maximum.reduceat(H,st5); l5=np.minimum.reduceat(L,st5); c5=C[en5-1]; av5=bt5+300

    fi=np.searchsorted(ft,av5,'left')-1
    ai=np.searchsorted(av15,av5,'right')-1
    fi0=np.maximum(fi,0); ai0=np.maximum(ai,0)
    good=(av5>=start)&(av5<end)&(fi>=0)&(ai>=0)&np.isfinite(fz[fi0])&np.isfinite(atr15[ai0])
    good &= ((av5-ft[fi0])>=0)&((av5-ft[fi0])<=600)
    return (ts,O,H,L,C,av5[good],h5[good],l5[good],c5[good],fz[fi[good]],atr15[ai[good]])

@njit(cache=True)
def metrics_raw(a):
    n=len(a)
    if n==0:return 0,0.,0.,0.,0.,0.,0
    s=0.;pos=0.;neg=0.;wins=0;eq=0.;pk=0.;dd=0.;mcl=0;cur=0
    for i in range(n):
        x=a[i];s+=x;eq+=x
        if eq>pk:pk=eq
        if pk-eq>dd:dd=pk-eq
        if x>0:pos+=x;wins+=1;cur=0
        elif x<0:neg-=x;cur+=1;mcl=max(mcl,cur)
        else:cur=0
    pf=pos/neg if neg>0 else 99.
    return n,wins/n,s/n,pf,s,dd,mcl

@njit(cache=True)
def manage_v191(ts,H,L,C,dt5,Z5,ei,side,entry,atr,exit_z):
    stop=entry-side*V191_SL*atr
    peak=entry
    pending_stop=stop
    xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+V191_HOLD,'left'))
    xp=C[xe];ex=xe;reason=4
    for q in range(ei+1,xe+1):
        stop=pending_stop
        if (side>0 and L[q]<=stop) or (side<0 and H[q]>=stop):
            protected=(side>0 and stop>entry) or (side<0 and stop<entry)
            xp=stop;ex=q;reason=2 if protected else 1
            break
        if side>0:
            if H[q]>peak:peak=H[q]
            fav=(peak-entry)/atr
        else:
            if L[q]<peak:peak=L[q]
            fav=(entry-peak)/atr
        ns=stop
        if fav>=V191_BE_ARM:
            lvl=entry+side*V191_BE_LOCK*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):ns=lvl
        if fav>=V191_TRAIL_ARM:
            lvl=peak-side*V191_TRAIL_GAP*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):ns=lvl
        pending_stop=ns
        if exit_z>0:
            zi=np.searchsorted(dt5,ts[q],'right')-1
            if zi>=0:
                z=Z5[zi]
                if (side>0 and z>=exit_z) or (side<0 and z<=-exit_z):
                    xp=C[q];ex=q;reason=3;break
    rr=side*(xp-entry)/(V191_SL*atr)-(COST_BPS/10000.)*entry/(V191_SL*atr)
    return rr,ex,reason

@njit(cache=True)
def sim_v191(ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5,variant):
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8);RS=np.zeros(cap,np.int8);AGE=np.zeros(cap);CZ=np.zeros(cap);ADV=np.zeros(cap);RESP=np.zeros(cap)
    n=0;k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False
    ttl=10800 if variant<=V191E_SAMESIDE else 2700
    exit_z=0.75 if variant==V191D else 0.0
    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z0=Z5[k]
        side=-1 if z0>=V191_Z else (1 if z0<=-V191_Z else 0)
        if side==0:k+=1;continue
        sig=C5[k];atr=A5[k]
        if has and abs(sig-last)<PAUSE_ATR*la:k+=1;continue

        target=sig+side*V191_CONFIRM_ATR*atr
        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+ttl,'right')
        ci=-1;maxadv=0.;maxfav=0.
        for q in range(ps,min(len(ts),pe)):
            adv=((H[q]-sig) if side<0 else (sig-L[q]))/atr
            fav=((sig-L[q]) if side<0 else (H[q]-sig))/atr
            if adv>maxadv:maxadv=adv
            if fav>maxfav:maxfav=fav
            if variant>=V191F_ADVERSE and maxadv>0.75:
                ci=-2;break
            if (side>0 and C[q]>=target) or (side<0 and C[q]<=target):
                ci=q;break
        if ci<0:
            k+=1;continue

        zi=np.searchsorted(dt5,ts[ci],'right')-1
        if zi<0:k+=1;continue
        cz=Z5[zi]

        # v191d: cancel only if materially opposite at +/-0.75
        if variant<=V191E_EXIT_OFF:
            if (side>0 and cz>=0.75) or (side<0 and cz<=-0.75):
                k=np.searchsorted(dt5,ts[ci])+1;continue
        else:
            # v191e onward: exact same-side
            if (side>0 and cz>=0.0) or (side<0 and cz<=0.0):
                k=np.searchsorted(dt5,ts[ci])+1;continue

        if variant>=V191F_MINZ and abs(cz)<0.75:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        response=maxfav/(maxadv+1e-9)
        if variant>=V191F_FULL and response<0.50:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        entry=C[ci]
        rr,ex,reason=manage_v191(ts,H,L,C,dt5,Z5,ci,side,entry,atr,exit_z)
        R[n]=rr;ST[n]=t;ET[n]=ts[ci];XT[n]=ts[ex];SIDE[n]=side;RS[n]=reason
        AGE[n]=(ts[ci]-t)/60.;CZ[n]=cz;ADV[n]=maxadv;RESP[n]=response;n+=1
        dc+=1;last=entry;la=atr;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)
    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],RS[:n],AGE[:n],CZ[:n],ADV[:n],RESP[:n]

@njit(cache=True)
def sim_v192(ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5):
    # Build completed M15 decisions by taking every third completed M5 point.
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8);RS=np.zeros(cap,np.int8)
    n=0;k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False
    while k<len(dt5)-4:
        t=dt5[k]
        if t%900!=0:k+=1;continue
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z0=Z5[k]
        side=-1 if z0>=V192_Z else (1 if z0<=-V192_Z else 0)
        if side==0:k+=1;continue
        sig=C5[k];atr=A5[k]
        if has and abs(sig-last)<PAUSE_ATR*la:k+=1;continue

        target=sig+side*V192_CONFIRM_ATR*atr
        ci=-1;j=k+1
        while j<len(dt5) and dt5[j]<=t+V192_CONFIRM_TTL:
            if dt5[j]%900==0 and ((side>0 and C5[j]>=target) or (side<0 and C5[j]<=target)):
                ci=j;break
            j+=1
        if ci<0:k+=1;continue
        if z0*Z5[ci]<0.0:
            k=ci+1;continue

        entry=C5[ci]-side*V192_RETRACE_ATR*atr
        ps=np.searchsorted(ts,dt5[ci]+1);pe=np.searchsorted(ts,dt5[ci]+V192_PENDING_TTL,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):ei=q;break
        if ei<0:k=ci+1;continue

        risk=V192_SL*atr;sl=entry-side*risk;tp=entry+side*V192_TP*atr
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+V192_HOLD,'left'))
        xp=C[xe];ex=xe;reason=4
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;reason=1;break
            if th:xp=tp;ex=q;reason=5;break
        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;ST[n]=t;ET[n]=ts[ei];XT[n]=ts[ex];SIDE[n]=side;RS[n]=reason;n+=1
        dc+=1;last=entry;la=atr;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)
    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],RS[:n]

def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    pos=a[a>0].sum();neg=abs(a[a<0].sum())
    streak=best=0
    for x in a:
        streak=streak+1 if x<0 else 0;best=max(best,streak)
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV':float(a.mean()),'PF':float(pos/neg) if neg else 99.,
            'SumR':float(a.sum()),'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.,'MaxConsecutiveLosses':int(best)}

REASONS={1:'SL',2:'PROTECTED_STOP',3:'EXIT_Z',4:'TIME',5:'TP'}

def df191(z):
    R,st,et,xt,side,rs,age,cz,adv,resp=z
    return pd.DataFrame({'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,
      'exit_reason':[REASONS.get(int(x),'?') for x in rs],
      'confirm_age_min':age,'confirm_z':cz,'max_adverse_atr':adv,'response_ratio':resp})

def df192(z):
    R,st,et,xt,side,rs=z
    return pd.DataFrame({'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,
      'exit_reason':[REASONS.get(int(x),'?') for x in rs]})

def summarize(df,period_kind):
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    key=t.dt.year.astype(str) if period_kind=='year' else t.dt.strftime('%Y-%m')
    return {
      'all':metrics(df.R.to_numpy(float)),
      'periods':{str(k):metrics(g.R.to_numpy(float)) for k,g in df.groupby(key)},
      'side':{'BUY':metrics(df[df.side>0].R.to_numpy(float)),'SELL':metrics(df[df.side<0].R.to_numpy(float))},
      'exit_reasons':{str(k):int(v) for k,v in df.exit_reason.value_counts().items()},
      'confirm_age':({
         'median_min':float(df.confirm_age_min.median()),
         'p90_min':float(df.confirm_age_min.quantile(.9)),
         'max_min':float(df.confirm_age_min.max())} if 'confirm_age_min' in df.columns and len(df) else {})
    }

def run_period(raw,ft,fz,start,end,label):
    p=prep(raw,ft,fz,start,end)
    out={}
    d192=df192(sim_v192(*p)); d192.to_csv(OUT/f'{label}_V192_CANONICAL_CONTROL.csv',index=False)
    out['V192_CANONICAL_CONTROL']=summarize(d192,'year' if label=='historical' else 'month')
    for v in range(7):
        d=df191(sim_v191(*p,v));d.to_csv(OUT/f'{label}_{NAMES[v]}.csv',index=False)
        out[NAMES[v]]=summarize(d,'year' if label=='historical' else 'month')
    return out

def matched_delta(label):
    rows=[]
    names=['V191D_CONTROL']+[NAMES[i] for i in range(1,7)]
    dfs={n:pd.read_csv(OUT/f'{label}_{n}.csv') for n in names}
    for a,b in zip(names[:-1],names[1:]):
        A=dfs[a];B=dfs[b]
        ka=set(zip(A.signal_ts,A.side));kb=set(zip(B.signal_ts,B.side))
        onlyA=A[[((x,y) in ka-kb) for x,y in zip(A.signal_ts,A.side)]]
        onlyB=B[[((x,y) in kb-ka) for x,y in zip(B.signal_ts,B.side)]]
        rows.append({'from':a,'to':b,'N_from':len(A),'N_to':len(B),
          'removed_signal_count':len(ka-kb),'added_signal_count':len(kb-ka),
          'removed_trade_sumR':float(onlyA.R.sum()),'added_trade_sumR':float(onlyB.R.sum()),
          'full_sequence_deltaR':float(B.R.sum()-A.R.sum())})
    return rows

def fmt(m):
    return f"N={m['N']} WR={m['WR']:.1%} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f} MCL={m['MaxConsecutiveLosses']}"

def main():
    ft,fz=load_flow();hist=load_hist();sec=load_sec()
    h=run_period(hist,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),'historical')
    f=run_period(sec,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),'forward')
    mh=matched_delta('historical');mf=matched_delta('forward')
    result={'lab':'CROWDFADE_V191D_TO_V191F_ABLATION_LAB_043',
      'canonical_control':'CrowdFadeMulti_v192_Confirm.mq5 — immutable control geometry',
      'historical':h,'forward_2026_shadow':f,'matched_step_deltas':{'historical':mh,'forward_2026_shadow':mf},
      'limitations':['BTCUSDT only. ETH/SOL transfer is not tested here.','Historical 2021-2025 uses 1-minute OHLC; 2026 Mar-Aug uses second OHLC.','2026 is reused forward-shadow/stress, not pristine OOS.','v191 MT5 is tick/timer driven; replay uses raw close crossing for +0.30ATR confirmation and completed M5 Z snapshots.','v192 control is reconstructed from the frozen documented geometry on the same data frame, not a byte-level MT5 Strategy Tester run.','Flat 0.5bps cost proxy; IC/GetLeveraged spread/slippage divergence remains a separate forward-execution question.']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    rows=[]
    for period,d in [('historical',h),('2026',f)]:
        for name,v in d.items():rows.append({'period':period,'variant':name,**v['all']})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
    pd.DataFrame(mh).assign(period='historical').to_csv(OUT/'matched_deltas_historical.csv',index=False)
    pd.DataFrame(mf).assign(period='2026').to_csv(OUT/'matched_deltas_2026.csv',index=False)
    lines=['# LAB043 — v191d → v191e → v191f causal ablation','',
      'Immutable reference control: CrowdFadeMulti_v192_Confirm.mq5','',
      '## Full sample']
    for period,d in [('Historical 2021–2025',h),('2026 Mar–Aug shadow',f)]:
        lines+=['',f'### {period}']
        for name,v in d.items():lines.append(f"- {name}: {fmt(v['all'])}")
    lines+=['','## Step deltas — historical']
    for x in mh:lines.append('- '+json.dumps(x))
    lines+=['','## Step deltas — 2026']
    for x in mf:lines.append('- '+json.dumps(x))
    lines+=['','## Exit reasons / confirmation age']
    for period,d in [('Historical',h),('2026',f)]:
        lines+=['',f'### {period}']
        for name,v in d.items():
            lines.append(f"- {name}: exits={json.dumps(v['exit_reasons'])}; confirm_age={json.dumps(v['confirm_age'])}")
    lines+=['','## Period consistency']
    for period,d in [('Historical',h),('2026',f)]:
        lines+=['',f'### {period}']
        for name,v in d.items():lines.append(f"- {name}: {json.dumps(v['periods'])}")
    lines+=['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
