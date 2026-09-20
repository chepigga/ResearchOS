from pathlib import Path
import json, zipfile, io, math
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Frozen v200 core
ZTH=2.05
CONF=0.25
CONF_TTL=3600
SL=4.5
TP=10.0
HOLD=86400
COST_BPS=0.50
MAXDAY=3
ANTI_REPEAT_ATR=1.0

RETRACES=[0.60,0.45,0.40,0.30]
TTLS=[1200,1800]

def load_flow():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if not names: raise RuntimeError('flow zip has no csv')
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
        if not names: return None
        with z.open(names[0]) as f:
            r=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
    ts=pd.to_numeric(r.iloc[:,0],errors='coerce')
    # Binance Vision moved some timestamps to microseconds; infer safely.
    med=np.nanmedian(ts.to_numpy(float))
    if med>1e15: ts=(ts//1_000_000).astype('Int64')
    elif med>1e12: ts=(ts//1000).astype('Int64')
    else: ts=ts.astype('Int64')
    out=pd.DataFrame({
        'ts':ts,
        'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),
        'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),
        'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),
        'c':pd.to_numeric(r.iloc[:,4],errors='coerce')})
    return out.dropna()

def load_hist_price():
    parts=[]
    for zp in sorted((DATA/'hist_1m').glob('BTCUSDT-1m-*.zip')):
        q=read_binance_kline_zip(zp)
        if q is not None and len(q): parts.append(q)
    if not parts: raise RuntimeError('no historical monthly 1m files')
    p=pd.concat(parts,ignore_index=True).drop_duplicates('ts').sort_values('ts')
    return tuple(p[x].to_numpy(np.float64 if x!='ts' else np.int64) for x in ['ts','o','h','l','c'])

def load_sec_price():
    zp=DATA/'BTCUSDT_sec.csv.zip'
    with zipfile.ZipFile(zp) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if not names: raise RuntimeError('sec zip has no csv')
        with z.open(names[0]) as f:
            s=pd.read_csv(f,usecols=['ts','o','h','l','c'])
    s=s.sort_values('ts').drop_duplicates('ts')
    return (s.ts.to_numpy(np.int64),s.o.to_numpy(float),s.h.to_numpy(float),s.l.to_numpy(float),s.c.to_numpy(float))

def tf_states(ts,C,sec):
    b=(ts//sec)*sec
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]
    en=np.r_[st[1:],len(ts)]
    close=C[en-1]; bt=b[st]
    ema=pd.Series(close).ewm(span=50,adjust=False).mean().to_numpy()
    lag4=pd.Series(ema).shift(4).to_numpy()
    state=np.where((close>ema)&(ema>lag4),1,np.where((close<ema)&(ema<lag4),-1,0)).astype(np.int64)
    return (bt+sec).astype(np.int64),state

def prep(raw,ft,fz,start_ts,end_ts):
    ts,O,H,L,C=raw
    order=np.argsort(ts); ts=ts[order];O=O[order];H=H[order];L=L[order];C=C[order]
    keep=np.r_[True,ts[1:]!=ts[:-1]]
    ts=ts[keep];O=O[keep];H=H[keep];L=L[keep];C=C[keep]

    b=(ts//900)*900
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]
    en=np.r_[st[1:],len(ts)]
    bt=b[st]; bh=np.maximum.reduceat(H,st); bl=np.minimum.reduceat(L,st); bc=C[en-1]
    pc=np.r_[bc[0],bc[:-1]]
    tr=np.maximum(bh-bl,np.maximum(np.abs(bh-pc),np.abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    av=bt+900

    h1t,h1s=tf_states(ts,C,3600)
    h4t,h4s=tf_states(ts,C,14400)
    dt=av.copy(); qh=bh.copy(); ql=bl.copy(); qc=bc.copy()
    fi=np.searchsorted(ft,dt,'left')-1
    h1i=np.searchsorted(h1t,dt,'right')-1
    h4i=np.searchsorted(h4t,dt,'right')-1
    fi0=np.maximum(fi,0)
    good=(dt>=start_ts)&(dt<end_ts)&(fi>=0)&(h1i>=0)&(h4i>=0)&np.isfinite(atr)&np.isfinite(fz[fi0])
    good &= ((dt-ft[fi0])>=0)&((dt-ft[fi0])<=600)

    return (ts,O,H,L,C,dt[good],qh[good],ql[good],qc[good],fz[fi[good]],atr[good],h1s[h1i[good]],h4s[h4i[good]])

# zflip_mode: 0 preserve; 1 cancel any sign flip; 2 cancel only if opposite threshold is reached
# atr_mode: 0 frozen signal ATR for execution; 1 max(signal ATR, current ATR at confirm) for retrace/SL/TP
@njit(cache=True)
def sim(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,retrace,pttl,zflip_mode,atr_mode):
    cap=len(dt)
    R=np.zeros(cap); SIDE=np.zeros(cap,np.int8); ST=np.zeros(cap,np.int64); CT=np.zeros(cap,np.int64); ET=np.zeros(cap,np.int64)
    ORIGZ=np.zeros(cap); CONFZ=np.zeros(cap); SIGATR=np.zeros(cap); CURATR=np.zeros(cap); FILLATR=np.zeros(cap)
    CEX=np.zeros(cap); CB=np.zeros(cap,np.int8); H1A=np.zeros(cap,np.int8); H4A=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    armed=0;confirmed_count=0;pending=0;no_fill=0;cancel_z=0

    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=Z[k]
        side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=QC[k]; siga=A[k]
        if has and abs(sig-last)<ANTI_REPEAT_ATR*la:k+=1;continue
        armed+=1

        lev=sig+side*CONF*siga;ci=-1;maxcrowd=0.
        crowd=-side
        j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/siga
            if exc>maxcrowd:maxcrowd=exc
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j;break
            j+=1
        if ci<0:k+=1;continue
        confirmed_count+=1

        cz=Z[ci]
        cancel=False
        if zflip_mode==1:
            cancel=(z*cz<0.0)
        elif zflip_mode==2:
            if side>0: cancel=(cz>=ZTH)
            else: cancel=(cz<=-ZTH)
        if cancel:
            cancel_z+=1;k=ci+1;continue

        curA=A[ci]
        execA=siga
        if atr_mode==1 and curA>execA: execA=curA

        entry=QC[ci]-side*retrace*execA
        ps=np.searchsorted(ts,dt[ci]+1);pe=np.searchsorted(ts,dt[ci]+pttl,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):
                ei=q;break
        pending+=1
        if ei<0:
            no_fill+=1;k=ci+1;continue

        # Current completed-M15 ATR available at fill.
        fillj=np.searchsorted(dt,ts[ei],'right')-1
        fillA=A[fillj] if fillj>=0 else curA

        risk=SL*execA;sl=entry-side*risk;tp=entry+side*TP*execA
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break

        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;SIDE[n]=side;ST[n]=t;CT[n]=dt[ci];ET[n]=ts[ei]
        ORIGZ[n]=z;CONFZ[n]=cz;SIGATR[n]=siga;CURATR[n]=curA;FILLATR[n]=fillA
        CEX[n]=maxcrowd;CB[n]=ci-k;H1A[n]=H1[k];H4A[n]=H4[k];n+=1

        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt,nextts)

    return (R[:n],SIDE[:n],ST[:n],CT[:n],ET[:n],ORIGZ[:n],CONFZ[:n],SIGATR[:n],CURATR[:n],FILLATR[:n],
            CEX[:n],CB[:n],H1A[:n],H4A[:n],armed,confirmed_count,pending,no_fill,cancel_z)

def metrics(x):
    x=np.asarray(x,float)
    if len(x)==0:return {'N':0,'WR':0,'EV':0,'SumR':0,'PF':0,'MaxDD_R':0,'R_DD':0,'MaxConsecutiveLosses':0}
    eq=np.cumsum(x);pk=np.maximum.accumulate(np.r_[0.,eq])[1:];dd=pk-eq
    pos=x[x>0].sum();neg=abs(x[x<0].sum());cur=mx=0
    for v in x:
        if v<0:cur+=1;mx=max(mx,cur)
        else:cur=0
    return {'N':int(len(x)),'WR':float((x>0).mean()),'EV':float(x.mean()),'SumR':float(x.sum()),
            'PF':float(pos/neg) if neg>0 else 99.,'MaxDD_R':float(dd.max()),'R_DD':float(x.sum()/dd.max()) if dd.max()>0 else 99.,
            'MaxConsecutiveLosses':int(mx)}

def run_one(arr,retrace,pttl,zflip=0,atrmode=0,period='hist'):
    z=sim(*arr,retrace,pttl,zflip,atrmode)
    R,side,st,ct,et,oz,cz,sa,ca,fa,cex,cb,h1,h4,armed,confirmed,pending,no_fill,cancel_z=z
    df=pd.DataFrame({'signal_ts':st,'confirm_ts':ct,'entry_ts':et,'R':R,'side':side,'orig_z':oz,'confirm_z':cz,
                     'signal_atr':sa,'confirm_atr':ca,'fill_atr':fa,'atr_expansion_confirm':np.divide(ca,sa,out=np.zeros_like(ca),where=sa>0),
                     'atr_expansion_fill':np.divide(fa,sa,out=np.zeros_like(fa),where=sa>0),'crowd_exc_atr':cex,'confirm_bars':cb,'h1':h1,'h4':h4})
    if len(df):
        df['signal_time_utc']=pd.to_datetime(df.signal_ts,unit='s',utc=True)
        if period=='hist':
            labs=df.signal_time_utc.dt.year.astype(str)
            sub={str(y):metrics(df.loc[labs==str(y),'R']) for y in range(2021,2026)}
        else:
            labs=df.signal_time_utc.dt.to_period('M').astype(str)
            sub={m:metrics(df.loc[labs==m,'R']) for m in sorted(set(labs))}
    else: sub={}
    m=metrics(R)
    m.update({'armed':int(armed),'confirmed':int(confirmed),'pending':int(pending),'no_fill':int(no_fill),'cancel_z':int(cancel_z),
              'fill_rate_pending':float(len(R)/pending) if pending else 0.,
              'confirm_rate_armed':float(confirmed/armed) if armed else 0.,
              'positive_periods':int(sum(v['SumR']>0 for v in sub.values())),'periods':sub})
    return m,df

def score_guard(candidate,baseline):
    # Preregistered conservative guard, not an optimizer:
    # tolerate at most 10% deterioration in R/DD and require nonnegative EV/PF>1.
    if candidate['EV']<=0 or candidate['PF']<=1: return False
    if baseline['R_DD']>0 and candidate['R_DD'] < 0.90*baseline['R_DD']: return False
    return True

def choose_retrace(hres,fres):
    baseh=hres['0.60'];basef=fres['0.60']
    eligible=[]
    for r in [0.45,0.40,0.30]:
        k=f'{r:.2f}';h=hres[k];f=fres[k]
        if score_guard(h,baseh) and score_guard(f,basef):
            trade_gain=(f['N']-basef['N'])/max(1,basef['N'])
            if trade_gain>=0.10:
                robustness=min(h['R_DD']/max(baseh['R_DD'],1e-9),f['R_DD']/max(basef['R_DD'],1e-9))
                eligible.append((robustness,-abs(r-0.60),r))
    if not eligible:return 0.60
    eligible.sort(reverse=True)
    return eligible[0][2]

def choose_ttl(h20,h30,f20,f30):
    if not (score_guard(h30,h20) and score_guard(f30,f20)): return 1200
    gain=(f30['N']-f20['N'])/max(1,f20['N'])
    return 1800 if gain>=0.05 else 1200

def bucket_report(df,col,bins,labels):
    if not len(df):return {}
    q=pd.cut(df[col],bins=bins,labels=labels,include_lowest=True,right=False)
    return {str(l):metrics(df.loc[q==l,'R']) for l in labels}

def main():
    ft,fz=load_flow()
    hist=prep(load_hist_price(),ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=prep(load_sec_price(),ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))

    # Warm JIT
    _=sim(*[x[:min(2000,len(x))] for x in hist],0.60,1200,0,0)

    # LAB033A: RETRACE only, TTL frozen 20m
    h033={};f033={}
    for r in RETRACES:
        k=f'{r:.2f}'
        h033[k],_=run_one(hist,r,1200,0,0,'hist')
        f033[k],_=run_one(fwd,r,1200,0,0,'fwd')
    selected_retrace=choose_retrace(h033,f033)

    # LAB033B: TTL only, using selected retrace from 033A
    h20,dh20=run_one(hist,selected_retrace,1200,0,0,'hist')
    h30,dh30=run_one(hist,selected_retrace,1800,0,0,'hist')
    f20,df20=run_one(fwd,selected_retrace,1200,0,0,'fwd')
    f30,df30=run_one(fwd,selected_retrace,1800,0,0,'fwd')
    selected_ttl=choose_ttl(h20,h30,f20,f30)
    base_h=h20 if selected_ttl==1200 else h30
    base_f=f20 if selected_ttl==1200 else f30
    base_df=df20 if selected_ttl==1200 else df30

    # LAB034A: diagnostic only
    diag={
      'atr_expansion_confirm':bucket_report(base_df,'atr_expansion_confirm',[0,0.90,1.10,1.25,1.50,99],['<0.90','0.90-1.10','1.10-1.25','1.25-1.50','>=1.50']),
      'crowd_exc_atr':bucket_report(base_df,'crowd_exc_atr',[0,0.50,1.00,1.50,99],['<0.50','0.50-1.00','1.00-1.50','>=1.50'])
    }

    # LAB034B: dynamic execution ATR only
    hdyn,dh_dyn=run_one(hist,selected_retrace,selected_ttl,0,1,'hist')
    fdyn,df_dyn=run_one(fwd,selected_retrace,selected_ttl,0,1,'fwd')
    dynamic_pass=score_guard(hdyn,base_h) and score_guard(fdyn,base_f)
    selected_atrmode=1 if dynamic_pass and min(hdyn['R_DD']/max(base_h['R_DD'],1e-9),fdyn['R_DD']/max(base_f['R_DD'],1e-9))>=1.0 else 0

    # LAB035: Z-flip policies, full causal rerun on candidate geometry
    hz={};fzr={};zdfs={}
    for mode,name in [(0,'PRESERVE'),(1,'CANCEL_SIGN_FLIP'),(2,'CANCEL_OPPOSITE_THRESHOLD')]:
        hz[name],_=run_one(hist,selected_retrace,selected_ttl,mode,selected_atrmode,'hist')
        fzr[name],zdfs[name]=run_one(fwd,selected_retrace,selected_ttl,mode,selected_atrmode,'fwd')

    out={
      'lab_series':'CROWDFADE_V200_SEQUENTIAL_CHANGE_LABS_033_035',
      'frozen':{'Z':ZTH,'confirm_ATR':CONF,'confirm_TTL_min':60,'SL_ATR':SL,'TP_ATR':TP,'hold_h':24,'cost_bps':COST_BPS,'max_trades_day':MAXDAY,'anti_repeat_ATR':ANTI_REPEAT_ATR},
      'data':{'historical':'Binance USD-M BTCUSDT 1m 2021-2025 monthly archives','forward_shadow':'BTCUSDT second data 2026-03..2026-08','flow':'BTCUSDT_flow_2021-01-2026-08 release asset'},
      'LAB033A_RETRACE':{'question':'Does relaxing only passive retrace improve reachability without damaging risk-adjusted edge?','TTL_min':20,'historical':h033,'forward':f033,'selected_retrace_ATR':selected_retrace},
      'LAB033B_TTL':{'question':'After retrace decision, does TTL 30m add useful fills vs 20m?','retrace_ATR':selected_retrace,'historical':{'20m':h20,'30m':h30},'forward':{'20m':f20,'30m':f30},'selected_TTL_min':selected_ttl//60},
      'LAB034A_VOL_DIAGNOSTIC':diag,
      'LAB034B_DYNAMIC_EXEC_ATR':{'question':'Use max(signalATR,currentATR at confirmation) for retrace/SL/TP only; confirmation threshold remains frozen.','baseline':{'historical':base_h,'forward':base_f},'dynamic':{'historical':hdyn,'forward':fdyn},'selected_atr_mode':'MAX_SIGNAL_CURRENT' if selected_atrmode==1 else 'FROZEN_SIGNAL_ATR'},
      'LAB035_Z_FLIP':{'question':'Should the original event survive crowd Z reversal before entry?','historical':hz,'forward':fzr},
      'selection_rules':{
        'LAB033A':'candidate must EV>0, PF>1, R/DD >=90% of baseline in both samples, and >=10% forward trade-count gain; among eligible choose most robust R/DD ratio, then smallest parameter move',
        'LAB033B':'30m must pass same R/DD guards and add >=5% forward trades',
        'LAB034B':'dynamic ATR selected only if guards pass and minimum historical/forward R/DD ratio vs baseline is >=1.0',
        'LAB035':'no automatic promotion; report all three because cancellation may remove right-tail reversals'
      },
      'limitations':['2021-2025 is discovery/in-sample.','2026 Mar-Aug is reused forward-shadow/stress, not pristine OOS.','BTC only; ETH/SOL transfer is not proven.','Historical path uses M1; 2026 forward uses second OHLC; same-bar stop-first.','LAB036 broker execution requires fresh IC Markets/GetLeveraged logs and is not inferred from Binance replay.']
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))

    rows=[]
    for k,v in h033.items(): rows.append({'lab':'033A','variant':'retrace_'+k,'period':'historical',**{x:v[x] for x in ['N','EV','PF','SumR','MaxDD_R','R_DD','fill_rate_pending']}})
    for k,v in f033.items(): rows.append({'lab':'033A','variant':'retrace_'+k,'period':'2026','N':v['N'],'EV':v['EV'],'PF':v['PF'],'SumR':v['SumR'],'MaxDD_R':v['MaxDD_R'],'R_DD':v['R_DD'],'fill_rate_pending':v['fill_rate_pending']})
    for name,m in [('20m',h20),('30m',h30)]: rows.append({'lab':'033B','variant':name,'period':'historical',**{x:m[x] for x in ['N','EV','PF','SumR','MaxDD_R','R_DD','fill_rate_pending']}})
    for name,m in [('20m',f20),('30m',f30)]: rows.append({'lab':'033B','variant':name,'period':'2026',**{x:m[x] for x in ['N','EV','PF','SumR','MaxDD_R','R_DD','fill_rate_pending']}})
    for name,m in hz.items(): rows.append({'lab':'035','variant':name,'period':'historical',**{x:m[x] for x in ['N','EV','PF','SumR','MaxDD_R','R_DD','fill_rate_pending']}})
    for name,m in fzr.items(): rows.append({'lab':'035','variant':name,'period':'2026',**{x:m[x] for x in ['N','EV','PF','SumR','MaxDD_R','R_DD','fill_rate_pending']}})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
    base_df.to_csv(OUT/'candidate_forward_trades.csv',index=False)

    def line(m): return f"N={m['N']} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f} fill={m['fill_rate_pending']:.1%}"
    md=['# CrowdFade v200 sequential change LABs 033–035','',
        'Frozen: Z2.05 -> M15 confirm 0.25 ATR -> SL4.5 -> TP10 -> H24 -> flat risk.','',
        '## LAB033A — passive retrace only']
    for k in ['0.60','0.45','0.40','0.30']:
        md += [f"- {k} ATR | hist {line(h033[k])} | 2026 {line(f033[k])}"]
    md += ['',f"Selected by preregistered guard: **{selected_retrace:.2f} ATR**",'','## LAB033B — TTL only']
    md += [f"- 20m | hist {line(h20)} | 2026 {line(f20)}",f"- 30m | hist {line(h30)} | 2026 {line(f30)}",f"Selected: **{selected_ttl//60}m**",'',
           '## LAB034A — volatility expansion diagnostic',json.dumps(diag,indent=2),'','## LAB034B — dynamic execution ATR',
           f"- baseline hist {line(base_h)} | 2026 {line(base_f)}",f"- dynamic hist {line(hdyn)} | 2026 {line(fdyn)}",f"Selected: **{'max(signal,current)' if selected_atrmode else 'frozen signal ATR'}**",'',
           '## LAB035 — Z flip persistence']
    for name in ['PRESERVE','CANCEL_SIGN_FLIP','CANCEL_OPPOSITE_THRESHOLD']:
        md += [f"- {name} | hist {line(hz[name])} | 2026 {line(fzr[name])} | z-cancel forward={fzr[name]['cancel_z']}"]
    md += ['','LAB035 has **no automatic promotion**; interpretation must consider losses avoided and right-tail winners removed.','',
           '## Limitations']+[f"- {x}" for x in out['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(md))

    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
