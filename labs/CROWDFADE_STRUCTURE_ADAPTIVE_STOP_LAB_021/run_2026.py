from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_STRUCTURE_ADAPTIVE_STOP_LAB_021')
DATA=ROOT/'stress_data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.5
CONF=.25; CONF_TTL=3600; RETRACE=.60; PTTL=1200; COST=.5
SL_WIDE=4.5; SL_NARROW=3.0; TP_ATR=10.; HOLD=86400; MAXDAY=3

MODES=[
    ('WIDE_4P5_BASELINE',0),
    ('TREND_ADAPTIVE_3_OR_4P5',1),
    ('BREAKOUT_ADAPTIVE_3_OR_4P5',2),
    ('TREND_AND_BREAKOUT_3_OR_4P5',3),
    ('TREND_WIDE_ELSE_3',4),
    ('BREAKOUT_WIDE_ELSE_3',5),
    ('FIXED_3P0_CONTROL',6),
]

def ex(z,o):
    d=DATA/o;d.mkdir(parents=True,exist_ok=True)
    if not list(d.rglob('*.csv')):
        with zipfile.ZipFile(DATA/z) as q:q.extractall(d)
    return list(d.rglob('*.csv'))[0]

def prep():
    sf=ex('BTCUSDT_sec.csv.zip','sec'); ff=ex('BTCUSDT_flow_2021-01-2026-08.csv.zip','flow')
    s=pd.read_csv(sf,usecols=['ts','o','h','l','c']).sort_values('ts').drop_duplicates('ts')
    ts=s.ts.to_numpy(np.int64);O=s.o.to_numpy(float);H=s.h.to_numpy(float);L=s.l.to_numpy(float);C=s.c.to_numpy(float)

    b=(ts//900)*900
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]; en=np.r_[st[1:],len(ts)]
    bt=b[st]; bh=np.maximum.reduceat(H,st); bl=np.minimum.reduceat(L,st); bc=C[en-1]
    pc=np.r_[bc[0],bc[:-1]]
    tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    ema50=pd.Series(bc).ewm(span=50,adjust=False).mean().to_numpy()
    ema50_lag4=pd.Series(ema50).shift(4).to_numpy()
    prior20_high=pd.Series(bh).shift(1).rolling(20,min_periods=20).max().to_numpy()
    prior20_low=pd.Series(bl).shift(1).rolling(20,min_periods=20).min().to_numpy()
    av=bt+900

    f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    f=f[pd.to_numeric(f.sum_open_interest,errors='coerce')>0].copy()
    f['t']=pd.to_datetime(f.create_time,utc=True,errors='coerce')
    f=f.dropna(subset=['t']).sort_values('t').drop_duplicates('t')
    ft=f.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    r=pd.to_numeric(f.count_long_short_ratio,errors='coerce')
    mu=r.rolling(72,min_periods=72).mean(); sd=r.rolling(72,min_periods=72).std(ddof=0)
    z=((r-mu)/sd.replace(0,np.nan)).to_numpy()

    starts=np.arange(((ts[0]+899)//900)*900,ts[-1]-900+1,900,dtype=np.int64)
    idx2=np.searchsorted(ts,starts+900)-1
    ok=(idx2>=0)&(idx2<len(ts));starts=starts[ok];idx2=idx2[ok]
    dt=starts+900;cl=C[idx2]
    fi=np.searchsorted(ft,dt,'left')-1; ai=np.searchsorted(av,dt,'right')-1
    g=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    return ts,O,H,L,C,dt[g],cl[g],z[fi[g]],atr[ai[g]],ema50[ai[g]],ema50_lag4[ai[g]],prior20_high[ai[g]],prior20_low[ai[g]]

@njit(cache=True)
def stop_mult(mode,side,cl,ema,ema_lag4,ph,pl):
    if not (np.isfinite(ema) and np.isfinite(ema_lag4) and np.isfinite(ph) and np.isfinite(pl)):
        return SL_WIDE, False, False
    trend_align=(side>0 and cl>ema and ema>ema_lag4) or (side<0 and cl<ema and ema<ema_lag4)
    breakout_align=(side>0 and cl>ph) or (side<0 and cl<pl)
    narrow=False
    if mode==1:narrow=trend_align
    elif mode==2:narrow=breakout_align
    elif mode==3:narrow=trend_align and breakout_align
    elif mode==4:return (SL_WIDE if trend_align else SL_NARROW), trend_align, breakout_align
    elif mode==5:return (SL_WIDE if breakout_align else SL_NARROW), trend_align, breakout_align
    elif mode==6:return SL_NARROW, trend_align, breakout_align
    return SL_NARROW if narrow else SL_WIDE, trend_align, breakout_align

@njit(cache=True)
def sim(ts,O,H,L,C,dt,cl,zd,ad,ema,emalag,ph,pl,mode):
    cap=len(dt)
    ets=np.zeros(cap,np.int64); sides=np.zeros(cap,np.int8); rs=np.zeros(cap)
    reasons=np.zeros(cap,np.int8); sms=np.zeros(cap); trs=np.zeros(cap,np.int8); brs=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0

    while k<len(dt)-2:
        t=int(dt[k]);d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=zd[k];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=cl[k];a=ad[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a;ci=-1;j=k+1
        while j<len(dt) and dt[j]<=t+CONF_TTL:
            if (side>0 and cl[j]>=lev) or (side<0 and cl[j]<=lev):ci=j;break
            j+=1
        if ci<0:k+=1;continue

        entry=cl[ci]-side*RETRACE*a
        ps=np.searchsorted(ts,int(dt[ci])+1);pe=np.searchsorted(ts,int(dt[ci])+PTTL,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):ei=q;break
        if ei<0:k=ci+1;continue

        sm,tr,br=stop_mult(mode,side,cl[k],ema[k],emalag[k],ph[k],pl[k])
        risk=sm*a;sl=entry-side*risk;tp=entry+side*TP_ATR*a
        xe=min(len(ts)-1,np.searchsorted(ts,int(ts[ei])+HOLD,'left'))
        xp=C[xe];xi=xe;reason=0
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;xi=q;reason=-1;break
            if th:xp=tp;xi=q;reason=1;break

        R=side*(xp-entry)/risk-(COST/10000.)*entry/risk
        ets[n]=ts[ei];sides[n]=side;rs[n]=R;reasons[n]=reason;sms[n]=sm
        trs[n]=1 if tr else 0;brs[n]=1 if br else 0;n+=1
        dc+=1;last=entry;la=a;has=True;k=np.searchsorted(dt,int(ts[xi])+1)

    return ets[:n],sides[:n],rs[:n],reasons[:n],sms[:n],trs[:n],brs[:n]

def stats(a,months_div=6.0):
    a=np.asarray(a,float)
    if not len(a):return {'N':0}
    eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq]);dd=float((pk[1:]-eq).max())
    p=a[a>0].sum();n=abs(a[a<0].sum())
    return {'N':int(len(a)),'trades_per_month':float(len(a)/months_div),'WR':float((a>0).mean()),
            'EV':float(a.mean()),'SumR':float(a.sum()),'PF':float(p/n) if n else 99.,
            'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd else 99.}

def summarize(res):
    ets,sides,r,reasons,sm,tr,br=res
    months=pd.to_datetime(ets,unit='s',utc=True).to_period('M').astype(str) if len(ets) else np.array([])
    um=sorted(set(months)); names={-1:'SL',0:'TIME',1:'TP'}
    both=(tr>0)&(br>0)
    return {'all':stats(r),
      'exit_mix':{names[x]:int((reasons==x).sum()) for x in [-1,0,1]},
      'positive_months':int(sum(stats(r[months==m],1.0)['SumR']>0 for m in um)) if len(r) else 0,
      'monthly':{m:stats(r[months==m],1.0) for m in um},
      'by_side':{'LONG':stats(r[sides>0]),'SHORT':stats(r[sides<0])},
      'structure_counts':{'narrow_stop':int((sm<SL_WIDE).sum()),'wide_stop':int((sm>=SL_WIDE).sum()),
                          'trend_aligned':int((tr>0).sum()),'breakout_aligned':int((br>0).sum()),'both_aligned':int(both.sum())}}

def main():
    arr=prep(); sim(*[x[:2000] for x in arr],0)
    rows=[]
    for name,mode in MODES:
        rows.append({'name':name,**summarize(sim(*arr,mode))})
    b=rows[0]
    for x in rows:
        a=x['all'];bb=b['all']
        x['vs_baseline']={'dEV':float(a['EV']-bb['EV']),'dPF':float(a['PF']-bb['PF']),
                          'dMaxDD_R':float(a['MaxDD_R']-bb['MaxDD_R']),'dSumR':float(a['SumR']-bb['SumR']),
                          'dN':int(a['N']-bb['N'])}
    out={'lab':'CROWDFADE_STRUCTURE_ADAPTIVE_STOP_LAB_021','period':'2026 seconds forward-shadow/stress',
         'hypothesis':'Use 3.0 ATR only when structure supports trade; otherwise retain 4.5 ATR.',
         'trend_rule':'LONG: close>EMA50 and EMA50>EMA50[-4]; SHORT mirror',
         'breakout_rule':'LONG: close>prior 20 M15 high; SHORT: close<prior 20 M15 low',
         'warning':'stop execution is simulated on 1-second OHLC, not exchange tick sequence',
         'results':rows}
    (OUT/'stress_2026.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
