#!/usr/bin/env python3
from __future__ import annotations
import io, json, math, zipfile, re, requests
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path("lab139_out"); OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]
RISK=0.25
SYMBOLS=['ETHUSDT','SOLUSDT']
START='2021-01'
END='2024-12'

# Frozen thresholds — copied from BTC TRAIN research, NO retuning on ETH/SOL.
A_EXT=1.53
A_OI4H=0.00867
B3_DEPTH=0.50
B3_Z_STRENGTH=0.25
R48_MEAN_MARGIN=0.689
R48_OI_BUILD=0.00350
MAX_H=48
Z_WIN=72

def norm(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())
def pick(cols,prefs):
    nc={norm(c):c for c in cols}
    for p in prefs:
        if norm(p) in nc:return nc[norm(p)]
    for p in prefs:
        pp=norm(p)
        for k,v in nc.items():
            if pp in k or k in pp:return v
    return None

def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        unit='ns' if med>1e17 else ('us' if med>1e14 else ('ms' if med>1e11 else 's'))
        return pd.to_datetime(x,unit=unit,utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

def load_flow(path):
    if str(path).endswith('.zip'):
        with zipfile.ZipFile(path) as z:
            names=[n for n in z.namelist() if n.lower().endswith('.csv')]
            if not names: raise RuntimeError(f'no csv in {path}')
            with z.open(names[0]) as fh:d=pd.read_csv(fh)
    else:d=pd.read_csv(path)
    tc=pick(d.columns,['create_time','time'])
    rc=pick(d.columns,['count_long_short_ratio'])
    oi=pick(d.columns,['sum_open_interest_value','sum_open_interest'])
    if not all([tc,rc,oi]): raise RuntimeError(f'missing flow fields {path}: {d.columns.tolist()}')
    x=d[[tc,rc,oi]].copy()
    x['time']=ptime(x[tc]);x['ratio']=pd.to_numeric(x[rc],errors='coerce');x['oi']=pd.to_numeric(x[oi],errors='coerce')
    x=x.dropna().sort_values('time').drop_duplicates('time',keep='last')
    x=x[(x.ratio>0)&(x.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
    mu=x.ratio.rolling(Z_WIN,min_periods=Z_WIN).mean();sd=x.ratio.rolling(Z_WIN,min_periods=Z_WIN).std(ddof=0)
    x['z']=(x.ratio-mu)/sd.replace(0,np.nan)
    return x

def month_iter(start,end):
    a=pd.Period(start,freq='M');b=pd.Period(end,freq='M')
    while a<=b:
        yield a
        a+=1

def load_price(symbol):
    parts=[]
    for per in month_iter(START,END):
        ym=str(per)
        url=f'https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/5m/{symbol}-5m-{ym}.zip'
        try:
            r=requests.get(url,timeout=30)
            if r.status_code!=200: continue
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                n=z.namelist()[0]
                with z.open(n) as fh:
                    q=pd.read_csv(fh,header=None)
            if q.shape[1]<5: continue
            q=q.iloc[:,:6]
            q.columns=['open_time','open','high','low','close','volume']
            q['time']=pd.to_datetime(pd.to_numeric(q.open_time,errors='coerce'),unit='ms',utc=True,errors='coerce')
            for c in ['open','high','low','close']:q[c]=pd.to_numeric(q[c],errors='coerce')
            parts.append(q[['time','open','high','low','close']].dropna())
        except Exception:
            continue
    if not parts:raise RuntimeError(f'no price data for {symbol}')
    p=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time')
    p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    return p

def build(symbol):
    flow_path=Path('ETH_flow.csv.zip' if symbol=='ETHUSDT' else 'SOL_flow.csv')
    f=load_flow(flow_path)
    p=load_price(symbol)
    # common 2021-2024
    start=max(p.time.min(),f.time.min(),pd.Timestamp('2021-01-01',tz='UTC'))
    end=min(p.time.max(),f.time.max(),pd.Timestamp('2024-12-31 23:55',tz='UTC'))
    p=p[(p.time>=start)&(p.time<=end)].copy()
    f=f[(f.time>=start)&(f.time<=end)].copy()

    h1=p.set_index('time').resample('1h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    prev=h1.close.shift(1)
    tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
    h1['atr']=tr.rolling(14,min_periods=14).mean()
    h1['ema20']=h1.close.ewm(span=20,adjust=False).mean()
    h1['extension']=(h1.close-h1.ema20)/h1.atr
    h1['close_time']=h1.time+pd.Timedelta(hours=1)

    h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    h4['ema50']=h4.close.ewm(span=50,adjust=False).mean()
    h4['lag6']=h4.ema50.shift(6)
    h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.lag6),-1,0))
    hp=h4.close.shift(1)
    htr=pd.concat([(h4.high-h4.low),(h4.high-hp).abs(),(h4.low-hp).abs()],axis=1).max(axis=1)
    h4['atr']=htr.rolling(14,min_periods=14).mean()
    h4['body_atr']=(h4.close-h4.open)/h4.atr
    age=[];cur=0;pv=0
    for v in h4.trend:
        if v!=0 and v==pv:cur+=1
        elif v!=0:cur=1
        else:cur=0
        age.append(cur);pv=v
    h4['trend_age']=age
    imp=(h4.body_atr.abs()>=0.8)&(np.sign(h4.body_atr)==h4.trend)
    ia=[];cnt=999
    for x in imp.fillna(False):
        cnt=0 if x else min(cnt+1,999);ia.append(cnt)
    h4['impulse_age']=ia
    h4['close_time']=h4.time+pd.Timedelta(hours=4)

    b=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','extension']].dropna().sort_values('close_time'),
                    left_on='time',right_on='close_time',direction='backward')
    b=pd.merge_asof(b.sort_values('time'),h4[['close_time','trend','trend_age','impulse_age']].dropna().sort_values('close_time'),
                    left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
    b=pd.merge_asof(b.sort_values('time'),f[['time','z','oi']].dropna().sort_values('time'),
                    on='time',direction='backward',tolerance=pd.Timedelta('5min'))
    b=b.dropna(subset=['atr','extension','trend','trend_age','impulse_age','z','oi']).reset_index(drop=True)
    return b

def phase(age,imp_age):
    if age<=3:return 'BIRTH'
    if imp_age<=2:return 'REACCEL'
    if age<=12:return 'CONT'
    if age<=24:return 'MATURE'
    return 'LATE'

def generate(symbol,b):
    T=b.time.reset_index(drop=True);O=b.open.to_numpy(float);H=b.high.to_numpy(float);L=b.low.to_numpy(float);C=b.close.to_numpy(float)
    ATR=b.atr.to_numpy(float);Z=b.z.to_numpy(float);OI=b.oi.to_numpy(float)
    events=[]
    def swing3(i,side,maxbars=72):
        for j in range(i+1,min(i+maxbars,len(b)-2)+1):
            lo=max(i,j-3)
            ref=float(np.max(H[lo:j])) if side>0 else float(np.min(L[lo:j]))
            if (C[j]>ref if side>0 else C[j]<ref):return j+1
        return None

    # Engine A
    for i in range(1,len(b)-MAX_H*12-2):
        if not(abs(Z[i])>=1 and abs(Z[i-1])<1):continue
        side=-1 if Z[i]>0 else 1
        trend=int(b.trend.iloc[i]);age=int(b.trend_age.iloc[i]);imp_age=int(b.impulse_age.iloc[i])
        if trend==0 or trend==side:continue
        if phase(age,imp_age) not in ('CONT','REACCEL'):continue
        ext=float(b.extension.iloc[i])
        if not((side>0 and ext<0) or (side<0 and ext>0)):continue
        if abs(ext)<A_EXT:continue
        if i<48:continue
        oi4=OI[i]/OI[i-48]-1
        if oi4<A_OI4H:continue
        ei=swing3(i,side)
        if ei is not None:events.append(dict(engine='A',signal_i=i,entry_i=ei,side=side,atr=float(ATR[i]),signal_time=T.iloc[i],entry_time=T.iloc[ei]))

    # B3 HIGH
    for i in range(1,len(b)-MAX_H*12-2):
        if not(abs(Z[i])>=1 and abs(Z[i-1])<1):continue
        trend=int(b.trend.iloc[i]);age=int(b.trend_age.iloc[i])
        if trend==0 or age<4:continue
        crowd=1 if Z[i]>0 else -1
        if crowd!=-trend:continue
        atr=float(ATR[i]);anchor=float(C[i])
        hits=[];levels=[]
        ok=True
        for k in range(1,6):
            level=anchor-trend*(0.1*k)*atr;levels.append(level);hit=None
            st=i+1 if not hits else hits[-1]
            for j in range(st,min(i+73,len(b)-2)):
                if (L[j]<=level if trend>0 else H[j]>=level):hit=j;break
            if hit is None:ok=False;break
            hits.append(hit)
        if not ok:continue
        hit=hits[-1]
        if np.sign(Z[hit])!=crowd or abs(Z[hit])-abs(Z[i])<B3_Z_STRENGTH:continue
        if OI[hit]<=OI[i]:continue
        idx=[i]+hits;ints=np.diff(np.asarray(idx,dtype=int))
        if not(ints[3]>ints[2] and ints[4]>ints[3]):continue
        last_wave_start=levels[-2];re=None
        for j in range(hit,min(hit+73,len(b)-2)):
            if (C[j]>last_wave_start if trend>0 else C[j]<last_wave_start):re=j;break
        if re is not None:
            ei=re+1;events.append(dict(engine='B3_HIGH',signal_i=i,entry_i=ei,side=trend,atr=atr,signal_time=T.iloc[i],entry_time=T.iloc[ei]))

    # R48 HIGH
    R=48*12
    rh=b.high.shift(1).rolling(R,min_periods=R).max().to_numpy(float)
    rl=b.low.shift(1).rolling(R,min_periods=R).min().to_numpy(float)
    last=-9999
    for i in range(R+1,len(b)-MAX_H*12-8):
        if i-last<24:continue
        up=C[i]>rh[i];dn=C[i]<rl[i]
        if up==dn:continue
        side=1 if up else -1;boundary=float(rh[i] if up else rl[i]);atr=float(ATR[i])
        idx=np.arange(i+1,i+7)
        outs=((C[idx]>boundary) if side>0 else (C[idx]<boundary))
        if int(np.sum(outs))<4:continue
        # no retest and strong mean acceptance
        retest=bool(np.any(L[idx]<=boundary)) if side>0 else bool(np.any(H[idx]>=boundary))
        if retest:continue
        mean_margin=float(np.mean((C[idx]-boundary)*side/atr))
        if mean_margin<R48_MEAN_MARGIN:continue
        ei=i+7
        oich=OI[ei]/OI[i]-1
        if oich<R48_OI_BUILD:continue
        last=i
        events.append(dict(engine='R48_HIGH',signal_i=i,entry_i=ei,side=side,atr=atr,signal_time=T.iloc[i],entry_time=T.iloc[ei]))

    return pd.DataFrame(events).sort_values('entry_time').reset_index(drop=True)

def sim_port(symbol,b,ev,cost):
    T=b.time.reset_index(drop=True);O=b.open.to_numpy(float);H=b.high.to_numpy(float);L=b.low.to_numpy(float);C=b.close.to_numpy(float)
    rows=[]
    for _,r in ev.iterrows():
        ei=int(r.entry_i);side=int(r.side);atr=float(r.atr);entry=float(O[ei])
        sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(b)-1)
        gross=side*(C[end]-entry)/atr;reason='TIME';xi=end
        for j in range(ei,end+1):
            hs=(L[j]<=sl) if side>0 else (H[j]>=sl)
            ht=(H[j]>=tp) if side>0 else (L[j]<=tp)
            if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
            if hs:gross=-1;reason='SL';xi=j;break
            if ht:gross=3;reason='TP';xi=j;break
        net=float(gross-(cost/10000.0)*entry/atr)
        rows.append(dict(symbol=symbol,engine=r.engine,entry_time=r.entry_time,exit_time=T.iloc[xi],side='BUY' if side>0 else 'SELL',net_r=net,reason=reason))
    t=pd.DataFrame(rows).sort_values('entry_time')
    # one-position chronology, priority A>B3>R48
    pri={'A':0,'B3_HIGH':1,'R48_HIGH':2};t['pri']=t.engine.map(pri);t=t.sort_values(['entry_time','pri'])
    acc=[];open_until=pd.Timestamp.min.tz_localize('UTC')
    for _,r in t.iterrows():
        if r.entry_time<open_until:continue
        open_until=r.exit_time;acc.append(r)
    return pd.DataFrame(acc)

def stats(t):
    if t.empty:return dict(n=0,ev=np.nan,pf=np.nan,wr=np.nan,total_r=0,dd_r=np.nan)
    pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
    ce=t.net_r.cumsum();dd=float((ce.cummax()-ce).max())
    return dict(n=len(t),ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),dd_r=dd)

summ=[];year=[];side=[];eng=[];alltr=[]
for sym in SYMBOLS:
    b=build(sym)
    ev=generate(sym,b)
    ev.to_csv(OUT/f'{sym}_events.csv',index=False)
    for cost in COSTS:
        t=sim_port(sym,b,ev,cost)
        if t.empty:continue
        t['cost_bps']=cost;t['year']=pd.to_datetime(t.entry_time,utc=True).dt.year
        alltr.append(t)
        s=stats(t)
        months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
        s.update(symbol=sym,cost_bps=cost,trades_month=len(t)/months,r_month=t.net_r.sum()/months,dd_pct=s['dd_r']*RISK,
                 buy_n=int((t.side=='BUY').sum()),sell_n=int((t.side=='SELL').sum()))
        summ.append(s)
        for y,g in t.groupby('year'):
            q=stats(g);q.update(symbol=sym,cost_bps=cost,year=int(y));year.append(q)
        for sd,g in t.groupby('side'):
            q=stats(g);q.update(symbol=sym,cost_bps=cost,side=sd);side.append(q)
        for e,g in t.groupby('engine'):
            q=stats(g);q.update(symbol=sym,cost_bps=cost,engine=e);eng.append(q)

pd.DataFrame(summ).to_csv(OUT/'LAB139_summary.csv',index=False)
pd.DataFrame(year).to_csv(OUT/'LAB139_yearly.csv',index=False)
pd.DataFrame(side).to_csv(OUT/'LAB139_side.csv',index=False)
pd.DataFrame(eng).to_csv(OUT/'LAB139_engine.csv',index=False)
if alltr:pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB139_trades.csv',index=False)

# strict no-tuning validation decision
sm=pd.DataFrame(summ)
lines=['# LAB139 — PRODUCTION VALIDATION TRANSFER: ETH + SOL','',
       'Definitions are frozen from BTC TRAIN. No ETH/SOL threshold tuning.',
       'This is independent-symbol validation, not broker execution validation.',
       'Portfolio = Engine A + B3_HIGH + R48_HIGH; one-position chronology; SL1 H1ATR / TP3R / max48h.',
       'Frozen BTC-derived thresholds: A ext>=1.53ATR, OI4h>=+0.867%; B3 depth0.5ATR, Z strengthen>=0.25; R48 mean acceptance>=0.689ATR, OI acceptance build>=+0.350%.','']
for cost in COSTS:
    lines.append(f'## {cost:.2f}bps')
    for sym in SYMBOLS:
        q=sm[(sm.symbol==sym)&(sm.cost_bps==cost)]
        if len(q):
            r=q.iloc[0]
            lines.append(f"- {sym}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R / {r.dd_pct:.2f}%, BUY/SELL={int(r.buy_n)}/{int(r.sell_n)}")
lines += ['','## Frozen pass criteria',
          '- Each symbol must have positive EV at 7.5bps.',
          '- At least one of ETH/SOL should achieve PF >=1.30 at 7.5bps and the other should not be materially negative (PF >=0.95).',
          '- No single side or single year may explain essentially all profits.',
          '- If these fail, portfolio is NOT production-validated and we do not write a funded/live EA yet.',
          '- Even if they pass, broker-specific spread/commission/swap/slippage and live-feed parity remain required before production deployment.']
(OUT/'LAB139_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB139_meta.json').write_text(json.dumps(dict(symbols=SYMBOLS,period=[START,END],costs=COSTS,risk_pct=RISK,
    frozen_thresholds=dict(A_EXT=A_EXT,A_OI4H=A_OI4H,B3_DEPTH=B3_DEPTH,B3_Z_STRENGTH=B3_Z_STRENGTH,
                           R48_MEAN_MARGIN=R48_MEAN_MARGIN,R48_OI_BUILD=R48_OI_BUILD),
    caveat='independent-symbol transfer; no threshold tuning; broker execution validation still separate'),indent=2))
print('\n'.join(lines))
