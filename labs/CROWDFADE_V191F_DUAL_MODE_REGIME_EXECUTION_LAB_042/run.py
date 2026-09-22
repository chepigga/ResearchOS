from pathlib import Path
import json, zipfile
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# LAB042: v191f entry shell, dual-mode management only.
ZTH=1.00
CONF_ATR=0.30
CONF_TTL=45*60
MIN_CONFIRM_Z=0.75
MAX_ADVERSE_ATR=0.75
MIN_RESPONSE_RATIO=0.50
PAUSE_ATR=1.00
MAXDAY=3
COST_BPS=0.50

# Current v191f management (control)
BASE_SL=1.50
BASE_BE_ARM=0.50
BASE_BE_LOCK=0.15
BASE_TRAIL_ARM=2.50
BASE_TRAIL_GAP=0.50
BASE_HOLD=6*3600

# Pre-registered scalp management: not optimized in this lab.
SCALP_SL=1.00
SCALP_BE_ARM=0.50
SCALP_BE_LOCK=0.15
SCALP_TRAIL_ARM=0.50
SCALP_TRAIL_GAP=0.50
SCALP_HOLD=30*60
SCALP_TP=0.80

# Variants
BASELINE=0
DUAL_A=1
DUAL_B=2
DUAL_C=3
ALL_SCALP=4
VARIANT_NAMES={0:'BASELINE_V191F',1:'DUAL_A_SCALP_COUNTER_MIXED',2:'DUAL_B_SCALP_COUNTER_MIXED_TP08',3:'DUAL_C_SCALP_COUNTER_ONLY_TP08',4:'ALL_SCALP_CONTROL'}

def load_flow():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:r=pd.read_csv(f,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
    r['t']=pd.to_datetime(r.create_time,utc=True,errors='coerce')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['t','ratio']).sort_values('t').drop_duplicates('t')
    mu=r.ratio.rolling(72,min_periods=72).mean(); sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    ft=r.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    return ft,r.z.to_numpy(float)

def read_zip(path):
    with zipfile.ZipFile(path) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:r=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
    ts=pd.to_numeric(r.iloc[:,0],errors='coerce'); med=np.nanmedian(ts.to_numpy(float))
    if med>1e15: ts=(ts//1_000_000).astype('Int64')
    elif med>1e12: ts=(ts//1000).astype('Int64')
    else: ts=ts.astype('Int64')
    q=pd.DataFrame({'ts':ts,'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),'c':pd.to_numeric(r.iloc[:,4],errors='coerce')})
    return q.dropna()

def load_hist():
    parts=[read_zip(zp) for zp in sorted((DATA/'hist_1m').glob('BTCUSDT-1m-*.zip'))]
    p=pd.concat(parts,ignore_index=True).drop_duplicates('ts').sort_values('ts')
    return tuple(p[x].to_numpy(np.int64 if x=='ts' else np.float64) for x in ['ts','o','h','l','c'])

def load_sec():
    with zipfile.ZipFile(DATA/'BTCUSDT_sec.csv.zip') as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:s=pd.read_csv(f,usecols=['ts','o','h','l','c'])
    s=s.sort_values('ts').drop_duplicates('ts')
    return tuple(s[x].to_numpy(np.int64 if x=='ts' else np.float64) for x in ['ts','o','h','l','c'])

def tf_states(ts,C,sec):
    b=(ts//sec)*sec; st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]; en=np.r_[st[1:],len(ts)]
    close=C[en-1]; bt=b[st]
    ema=pd.Series(close).ewm(span=50,adjust=False).mean().to_numpy(); lag4=pd.Series(ema).shift(4).to_numpy()
    state=np.where((close>ema)&(ema>lag4),1,np.where((close<ema)&(ema<lag4),-1,0)).astype(np.int64)
    return (bt+sec).astype(np.int64),state

def prep(raw,ft,fz,start,end):
    ts,O,H,L,C=raw
    order=np.argsort(ts); ts=ts[order];O=O[order];H=H[order];L=L[order];C=C[order]
    keep=np.r_[True,ts[1:]!=ts[:-1]]; ts=ts[keep];O=O[keep];H=H[keep];L=L[keep];C=C[keep]

    b15=(ts//900)*900; st15=np.r_[0,np.flatnonzero(b15[1:]!=b15[:-1])+1]; en15=np.r_[st15[1:],len(ts)]
    bt15=b15[st15]; bh15=np.maximum.reduceat(H,st15); bl15=np.minimum.reduceat(L,st15); bc15=C[en15-1]
    pc=np.r_[bc15[0],bc15[:-1]]; tr=np.maximum(bh15-bl15,np.maximum(np.abs(bh15-pc),np.abs(bl15-pc)))
    atr15=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); av15=bt15+900

    b5=(ts//300)*300; st5=np.r_[0,np.flatnonzero(b5[1:]!=b5[:-1])+1]; en5=np.r_[st5[1:],len(ts)]
    bt5=b5[st5]; c5=C[en5-1]; av5=bt5+300
    h1t,h1s=tf_states(ts,C,3600); h4t,h4s=tf_states(ts,C,14400)

    fi=np.searchsorted(ft,av5,'left')-1; ai=np.searchsorted(av15,av5,'right')-1
    h1i=np.searchsorted(h1t,av5,'right')-1; h4i=np.searchsorted(h4t,av5,'right')-1
    fi0=np.maximum(fi,0);ai0=np.maximum(ai,0);h1i0=np.maximum(h1i,0);h4i0=np.maximum(h4i,0)
    good=(av5>=start)&(av5<end)&(fi>=0)&(ai>=0)&(h1i>=0)&(h4i>=0)&np.isfinite(fz[fi0])&np.isfinite(atr15[ai0])
    good &= ((av5-ft[fi0])>=0)&((av5-ft[fi0])<=600)
    return (ts,O,H,L,C,av5[good],c5[good],fz[fi[good]],atr15[ai[good]],h1s[h1i[good]],h4s[h4i[good]])

@njit(cache=True)
def regime(side,h1,h4):
    if h1!=0 and h4!=0 and h1==h4:
        return 1 if side==h1 else -1
    return 0

@njit(cache=True)
def params_for(variant,reg):
    scalp=False; tp=0.0
    if variant==ALL_SCALP:
        scalp=True; tp=SCALP_TP
    elif variant==DUAL_A:
        scalp=(reg!=1); tp=0.0
    elif variant==DUAL_B:
        scalp=(reg!=1); tp=SCALP_TP if scalp else 0.0
    elif variant==DUAL_C:
        scalp=(reg==-1); tp=SCALP_TP if scalp else 0.0
    if scalp:
        return SCALP_SL,SCALP_BE_ARM,SCALP_BE_LOCK,SCALP_TRAIL_ARM,SCALP_TRAIL_GAP,SCALP_HOLD,tp
    return BASE_SL,BASE_BE_ARM,BASE_BE_LOCK,BASE_TRAIL_ARM,BASE_TRAIL_GAP,BASE_HOLD,0.0

@njit(cache=True)
def manage_trade(ts,H,L,C,ei,side,entry,atr,variant,reg):
    sl_atr,be_arm,be_lock,tr_arm,tr_gap,hold,tp_atr=params_for(variant,reg)
    init_risk=sl_atr*atr
    stop=entry-side*init_risk
    tp=entry+side*tp_atr*atr if tp_atr>0 else 0.0
    peak=entry
    xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+hold,'left'))
    xp=C[xe]; ex=xe; reason=3
    pending_stop=stop
    for q in range(ei+1,xe+1):
        stop=pending_stop
        sh=(side>0 and L[q]<=stop) or (side<0 and H[q]>=stop)
        th=tp_atr>0 and ((side>0 and H[q]>=tp) or (side<0 and L[q]<=tp))
        if sh:
            xp=stop; ex=q; reason=-1; break
        if th:
            xp=tp; ex=q; reason=1; break
        fav_high=(H[q]-entry)/atr if side>0 else (entry-L[q])/atr
        if side>0:
            if H[q]>peak: peak=H[q]
        else:
            if L[q]<peak: peak=L[q]
        ns=stop
        if be_arm>0 and fav_high>=be_arm:
            lvl=entry+side*be_lock*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns): ns=lvl
        mfe=(peak-entry)/atr if side>0 else (entry-peak)/atr
        if tr_arm>0 and mfe>=tr_arm:
            lvl=peak-side*tr_gap*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns): ns=lvl
        pending_stop=ns
    rr=side*(xp-entry)/init_risk-(COST_BPS/10000.)*entry/init_risk
    return rr,ex,reason

@njit(cache=True)
def simulate(ts,O,H,L,C,dt5,C5,Z5,A5,H1,H4,variant):
    cap=len(dt5)
    R=np.zeros(cap); ST=np.zeros(cap,np.int64); ET=np.zeros(cap,np.int64); XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8); REG=np.zeros(cap,np.int8); REASON=np.zeros(cap,np.int8)
    AGE=np.zeros(cap); ADV=np.zeros(cap); RESP=np.zeros(cap); CZ=np.zeros(cap)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts: k+=1; continue
        d=t//86400
        if d!=day: day=d; dc=0
        if dc>=MAXDAY: k+=1; continue
        z=Z5[k]; side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0: k+=1; continue
        sig=C5[k]; atr=A5[k]
        if has and abs(sig-last)<PAUSE_ATR*la: k+=1; continue

        ps=np.searchsorted(ts,t+1); pe=np.searchsorted(ts,t+CONF_TTL,'right')
        ci=-1; maxadv=0.; maxfav=0.; curz=0.
        target=sig+side*CONF_ATR*atr
        for q in range(ps,min(len(ts),pe)):
            adv=((H[q]-sig) if side<0 else (sig-L[q]))/atr
            fav=((sig-L[q]) if side<0 else (H[q]-sig))/atr
            if adv>maxadv: maxadv=adv
            if fav>maxfav: maxfav=fav
            if maxadv>MAX_ADVERSE_ATR:
                ci=-2; break
            if (side>0 and C[q]>=target) or (side<0 and C[q]<=target):
                ci=q; break
        if ci<0:
            k+=1; continue

        zi=np.searchsorted(dt5,ts[ci],'right')-1
        if zi<0: k+=1; continue
        curz=Z5[zi]
        if z*curz<=0.0 or abs(curz)<MIN_CONFIRM_Z:
            k=np.searchsorted(dt5,ts[ci])+1; continue
        response=maxfav/(maxadv+1e-9)
        if response<MIN_RESPONSE_RATIO:
            k=np.searchsorted(dt5,ts[ci])+1; continue

        entry=C[ci]; reg=regime(side,H1[k],H4[k])
        rr,ex,rs=manage_trade(ts,H,L,C,ci,side,entry,atr,variant,reg)
        R[n]=rr;ST[n]=t;ET[n]=ts[ci];XT[n]=ts[ex];SIDE[n]=side;REG[n]=reg;REASON[n]=rs
        AGE[n]=(ts[ci]-t)/60.;ADV[n]=maxadv;RESP[n]=response;CZ[n]=curz;n+=1
        dc+=1;last=entry;la=atr;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)
    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],REG[:n],REASON[:n],AGE[:n],ADV[:n],RESP[:n],CZ[:n]

def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'N':0,'WR':0.,'EV':0.,'PF':0.,'SumR':0.,'MaxDD_R':0.,'R_DD':0.,'MaxConsecutiveLosses':0}
    eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max())
    pos=a[a>0].sum(); neg=abs(a[a<0].sum())
    mcl=0;cur=0
    for x in a:
        if x<0:cur+=1;mcl=max(mcl,cur)
        else:cur=0
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV':float(a.mean()),'PF':float(pos/neg) if neg else 99.,'SumR':float(a.sum()),'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.,'MaxConsecutiveLosses':int(mcl)}

def make_df(z):
    R,st,et,xt,side,reg,rs,age,adv,resp,cz=z
    rsn=np.where(rs==-1,'STOP',np.where(rs==1,'TP','TIME'))
    rgn=np.where(reg==1,'ALIGNED_WITH',np.where(reg==-1,'ALIGNED_COUNTER','MIXED'))
    return pd.DataFrame({'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,'regime':rgn,'exit_reason':rsn,'confirm_age_min':age,'max_adverse_atr':adv,'response_ratio':resp,'confirm_z':cz})

def summarize(df,period_kind):
    out={'all':metrics(df.R)}
    out['regimes']={k:metrics(g.R) for k,g in df.groupby('regime')}
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    key=t.dt.year.astype(str) if period_kind=='year' else t.dt.strftime('%Y-%m')
    out['periods']={str(k):metrics(g.R) for k,g in df.groupby(key)}
    out['exit_reasons']={str(k):int(v) for k,v in df.exit_reason.value_counts().items()}
    return out

def run_period(raw,ft,fz,start,end,label):
    p=prep(raw,ft,fz,start,end)
    results={}
    for vid in [BASELINE,DUAL_A,DUAL_B,DUAL_C,ALL_SCALP]:
        z=simulate(*p,vid); df=make_df(z)
        df.to_csv(OUT/f'{label}_{VARIANT_NAMES[vid]}.csv',index=False)
        results[VARIANT_NAMES[vid]]=summarize(df,'year' if label=='historical' else 'month')
    return results

def fmt(m):
    return f"N={m['N']} WR={m['WR']:.1%} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f} MCL={m['MaxConsecutiveLosses']}"

def main():
    ft,fz=load_flow(); hist=load_hist(); sec=load_sec()
    h=run_period(hist,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),'historical')
    f=run_period(sec,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),'forward')
    result={
      'lab':'CROWDFADE_V191F_DUAL_MODE_REGIME_EXECUTION_LAB_042',
      'question':'Can v191f keep frequent entries while using short-horizon scalp management outside aligned-with-trend states to reduce chop drawdown without destroying expectancy?',
      'entry_shell':{'Z':1.0,'confirm_ATR':0.30,'confirm_TTL_min':45,'confirm_same_side':True,'min_abs_confirm_Z':0.75,'max_adverse_ATR':0.75,'min_response_ratio':0.50,'pause_ATR':1.0,'max_trades_day':3},
      'trend_definition':'Completed H1/H4: close vs EMA50 plus EMA50 4-bar slope; ALIGNED_WITH if trade follows both, ALIGNED_COUNTER if opposes both, otherwise MIXED.',
      'variants':{
        'BASELINE_V191F':'All states: SL1.5ATR, BE arm0.5 lock0.15, trail arm2.5 gap0.5, hold6h.',
        'DUAL_A_SCALP_COUNTER_MIXED':'ALIGNED_WITH baseline; COUNTER+MIXED: SL1.0, BE0.5/0.15, trail arm0.5 gap0.5, hold30m, no TP.',
        'DUAL_B_SCALP_COUNTER_MIXED_TP08':'As DUAL_A plus fixed TP0.8ATR in scalp states.',
        'DUAL_C_SCALP_COUNTER_ONLY_TP08':'Only ALIGNED_COUNTER uses scalp+TP0.8; MIXED and ALIGNED_WITH use baseline.',
        'ALL_SCALP_CONTROL':'All states use scalp+TP0.8; diagnostic control only.'},
      'historical':h,'forward_2026_shadow':f,
      'limitations':['BTCUSDT only; ETH/SOL transfer not established.','Historical 2021-2025 uses 1-minute OHLC; 2026 Mar-Aug uses second OHLC.','2026 is reused forward-shadow/stress, not pristine OOS.','v191f MT5 confirmation is tick/timer-based; replay uses raw bar closes for the +0.30ATR confirmation and conservative next-bar stop updates.','Flat 0.5bps research cost; broker-specific spread/slippage and IC vs GetLeveraged path divergence require live forward validation.']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    rows=[]
    for period,d in [('historical',h),('2026',f)]:
        for name,v in d.items(): rows.append({'period':period,'variant':name,**v['all']})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
    lines=['# LAB042 — V191F DUAL MODE REGIME EXECUTION','',result['question'],'','## Full-sample comparison']
    for period,d in [('Historical 2021-2025',h),('2026 Mar-Aug shadow',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items(): lines.append(f"- {name}: {fmt(v['all'])}")
    lines += ['','## Regime splits']
    for period,d in [('Historical',h),('2026',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items(): lines.append(f"- {name}: {json.dumps(v['regimes'])}")
    lines += ['','## Period consistency']
    for period,d in [('Historical',h),('2026',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items(): lines.append(f"- {name}: {json.dumps(v['periods'])}")
    lines += ['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
