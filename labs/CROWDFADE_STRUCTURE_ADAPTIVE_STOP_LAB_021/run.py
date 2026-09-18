from pathlib import Path
import zipfile,json
import numpy as np,pandas as pd
from numba import njit

ROOT=Path('labs/CROWDFADE_STRUCTURE_ADAPTIVE_STOP_LAB_021')
DATA=ROOT/'data'; KDIR=DATA/'klines1m'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

ZTH=2.5
CONF=.25; CONF_TTL_MIN=60; RETRACE=.60; PASSIVE_TTL_MIN=20; COST=.50; MAXDAY=3
SL_WIDE=4.5; SL_NARROW=3.0; TP_ATR=10.0; HOLD_H=24

MODES=[
    ('WIDE_4P5_BASELINE',0),
    ('TREND_ADAPTIVE_3_OR_4P5',1),
    ('BREAKOUT_ADAPTIVE_3_OR_4P5',2),
    ('TREND_AND_BREAKOUT_3_OR_4P5',3),
    ('TREND_WIDE_ELSE_3',4),
    ('BREAKOUT_WIDE_ELSE_3',5),
]

def load_1m():
    ps=[]
    for zp in sorted(KDIR.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            with z.open(z.namelist()[0]) as f:r=pd.read_csv(f,header=None)
        ps.append(pd.DataFrame({
            'ms':pd.to_numeric(r.iloc[:,0],errors='coerce'),
            'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),
            'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),
            'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),
            'c':pd.to_numeric(r.iloc[:,4],errors='coerce')
        }).dropna())
    p=pd.concat(ps,ignore_index=True).drop_duplicates('ms').sort_values('ms')
    p['time']=pd.to_datetime(p.ms.astype('int64'),unit='ms',utc=True).astype('datetime64[ns, UTC]')
    return p[['time','o','h','l','c']].reset_index(drop=True)

def load_flow():
    d=DATA/'flow'; d.mkdir(exist_ok=True); zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    if not list(d.glob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(d)
    r=pd.read_csv(list(d.glob('*.csv'))[0],usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
    r['time']=pd.to_datetime(r.create_time,utc=True,errors='coerce').astype('datetime64[ns, UTC]')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['time','ratio']).sort_values('time').drop_duplicates('time')
    mu=r.ratio.rolling(72,min_periods=72).mean(); sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    return r[['time','z']].dropna()

def prep():
    p=load_1m(); f=load_flow()
    q=p.set_index('time').resample('15min',label='left',closed='left').agg(
        o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna()
    pc=q.c.shift(); tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs()))
    q['atr']=tr.rolling(14,min_periods=14).mean()
    q['ema50']=q.c.ewm(span=50,adjust=False).mean()
    q['ema50_lag4']=q.ema50.shift(4)
    q['prior20_high']=q.h.shift(1).rolling(20,min_periods=20).max()
    q['prior20_low']=q.l.shift(1).rolling(20,min_periods=20).min()
    q['av']=(q.index+pd.Timedelta(minutes=15)).astype('datetime64[ns, UTC]')

    a=q[['av','atr','ema50','ema50_lag4','prior20_high','prior20_low']].dropna(subset=['atr']).reset_index(drop=True)
    p=pd.merge_asof(p.sort_values('time'),a,left_on='time',right_on='av',direction='backward')
    p=pd.merge_asof(p.sort_values('time'),f,on='time',direction='backward',
                    tolerance=pd.Timedelta(minutes=10)).dropna(subset=['atr','z'])
    p=p[(p.time>='2021-01-01')&(p.time<'2026-01-01')].copy().reset_index(drop=True)
    p['ts']=(p.time.astype('int64')//10**9).astype('int64')

    q=p.set_index('time').resample('15min',label='left',closed='left').agg(
        c=('c','last'),h=('h','max'),l=('l','min'),z=('z','last'),atr=('atr','last'),
        ema50=('ema50','last'),ema50_lag4=('ema50_lag4','last'),
        prior20_high=('prior20_high','last'),prior20_low=('prior20_low','last')).dropna(subset=['c','z','atr']).reset_index()
    q['close_ts']=(q.time.astype('int64')//10**9).astype('int64')+900
    q['yr']=q.time.dt.year.astype('int64')
    q['daykey']=(q.time.dt.year*10000+q.time.dt.month*100+q.time.dt.day).astype('int64')
    return p,q

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
    return SL_NARROW if narrow else SL_WIDE, trend_align, breakout_align

@njit(cache=True)
def sim(ts,O,H,L,C,dt,CL,Z,A,EMA,EMALAG,PH,PL,Y,DAY,mode):
    sums=np.zeros(5);cnt=np.zeros(5,np.int64)
    n=0;eq=0.;pk=0.;dd=0.;pos=0.;neg=0.;wins=0
    slh=0;tph=0;timeh=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    narrow_n=0;wide_n=0;trend_n=0;break_n=0;both_n=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        if DAY[k]!=day:day=DAY[k];dc=0
        if dc>=MAXDAY:k+=1;continue
        z=Z[k];side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:k+=1;continue
        sig=CL[k];a=A[k]
        if has and abs(sig-last)<la:k+=1;continue

        lev=sig+side*CONF*a;ci=-1
        for j in range(k+1,min(len(dt)-2,k+CONF_TTL_MIN//15)+1):
            if (side>0 and CL[j]>=lev) or (side<0 and CL[j]<=lev):ci=j;break
        if ci<0:k+=1;continue

        entry=CL[ci]-side*RETRACE*a
        ps=np.searchsorted(ts,dt[ci])+1;pe=np.searchsorted(ts,dt[ci]+PASSIVE_TTL_MIN*60,'right');ei=-1
        for j in range(ps,min(len(ts),pe)):
            if (side>0 and L[j]<=entry) or (side<0 and H[j]>=entry):ei=j;break
        if ei<0:k=ci+1;continue

        sm,tr,br=stop_mult(mode,side,CL[k],EMA[k],EMALAG[k],PH[k],PL[k])
        if sm<SL_WIDE:narrow_n+=1
        else:wide_n+=1
        if tr:trend_n+=1
        if br:break_n+=1
        if tr and br:both_n+=1

        risk=sm*a;sl=entry-side*risk;tp=entry+side*TP_ATR*a
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD_H*3600,'left'))
        xp=C[xe];ex=xe;reason=0
        for j in range(ei+1,xe+1):
            sh=(side>0 and L[j]<=sl) or (side<0 and H[j]>=sl)
            th=(side>0 and H[j]>=tp) or (side<0 and L[j]<=tp)
            if sh:xp=sl;ex=j;reason=-1;break
            if th:xp=tp;ex=j;reason=1;break
        if reason<0:slh+=1
        elif reason>0:tph+=1
        else:timeh+=1

        R=side*(xp-entry)/risk-(COST/10000.)*entry/risk
        yi=Y[ci]-2021
        if 0<=yi<5:sums[yi]+=R;cnt[yi]+=1
        if R>0:wins+=1;pos+=R
        elif R<0:neg-=R
        n+=1;eq+=R;pk=max(pk,eq);dd=max(dd,pk-eq)
        dc+=1;last=entry;la=a;has=True;nextts=ts[ex]+60;k=np.searchsorted(dt,nextts)
    return sums,cnt,n,eq,eq/n if n else -999.,pos/neg if neg>0 else 99.,dd,wins/n if n else 0.,slh,tph,timeh,narrow_n,wide_n,trend_n,break_n,both_n

def rec(name,r):
    s,c,n,total,ev,pf,dd,wr,slh,tph,timeh,nn,wn,tn,bn,bon=r
    return {'name':name,'N':int(n),'trades_per_month':float(n/60.0),'positive_years':int(np.sum(s>0)),
      'annual':{str(2021+i):{'SumR':float(s[i]),'N':int(c[i]),'EV':float(s[i]/c[i]) if c[i] else 0.} for i in range(5)},
      'agg':{'SumR':float(total),'EV':float(ev),'PF':float(pf),'MaxDD_R':float(dd),'R_DD':float(total/max(dd,1e-9)),'WR':float(wr)},
      'exit_mix':{'SL':int(slh),'TP':int(tph),'TIME':int(timeh)},
      'structure_counts':{'narrow_stop':int(nn),'wide_stop':int(wn),'trend_aligned':int(tn),'breakout_aligned':int(bn),'both_aligned':int(bon)}}

def main():
    p,q=prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
         q.close_ts.to_numpy(np.int64),q.c.to_numpy(float),q.z.to_numpy(float),q.atr.to_numpy(float),
         q.ema50.to_numpy(float),q.ema50_lag4.to_numpy(float),q.prior20_high.to_numpy(float),q.prior20_low.to_numpy(float),
         q.yr.to_numpy(np.int64),q.daykey.to_numpy(np.int64)]
    sim(*[x[:1000] for x in arr],0)
    rows=[rec(name,sim(*arr,mode)) for name,mode in MODES]
    b=rows[0]
    for x in rows:
        x['vs_baseline']={'dEV':float(x['agg']['EV']-b['agg']['EV']),'dPF':float(x['agg']['PF']-b['agg']['PF']),
                          'dMaxDD_R':float(x['agg']['MaxDD_R']-b['agg']['MaxDD_R']),
                          'dSumR':float(x['agg']['SumR']-b['agg']['SumR']),'dN':int(x['N']-b['N'])}
    out={'lab':'CROWDFADE_STRUCTURE_ADAPTIVE_STOP_LAB_021',
         'hypothesis':'Use 3.0 ATR only when structure supports trade; otherwise retain 4.5 ATR.',
         'trend_rule':'LONG: close>EMA50 and EMA50>EMA50[-4]; SHORT mirror',
         'breakout_rule':'LONG: close>prior 20 M15 high; SHORT: close<prior 20 M15 low',
         'frozen_signal_entry':{'ZLong':2.5,'ZShort':2.5,'ConfirmATR':CONF,'RetraceATR':RETRACE,'LimitTTL_min':PASSIVE_TTL_MIN,'TP_ATR':TP_ATR},
         'results':rows}
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
