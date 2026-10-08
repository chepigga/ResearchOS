#!/usr/bin/env python3
from __future__ import annotations
import json,re,zipfile
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab139_out"); OUT.mkdir(exist_ok=True)
COSTS=[2.81,7.5]; MAX_H=48
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")

# Frozen BTC-derived thresholds; NO re-estimation on validation symbols.
A_EXT=1.53
A_OI4=0.00867
B3_Z_STRENGTH=0.25
R48_MEAN_MARGIN=0.689
R48_OI=0.00350

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
        x=pd.to_numeric(s,errors='coerce')
        med=float(x.dropna().median()) if x.notna().any() else 0
        unit='ns' if med>1e17 else ('us' if med>1e14 else ('ms' if med>1e11 else 's'))
        return pd.to_datetime(x,unit=unit,utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

def load_flow(path):
    p=Path(path)
    if p.suffix=='.zip':
        with zipfile.ZipFile(p) as z:
            names=[n for n in z.namelist() if n.lower().endswith('.csv')]
            frames=[]
            for n in names:
                with z.open(n) as fh: frames.append(pd.read_csv(fh))
            d=pd.concat(frames,ignore_index=True) if len(frames)>1 else frames[0]
    else:d=pd.read_csv(p)
    tc=pick(d.columns,['create_time','time']);rc=pick(d.columns,['count_long_short_ratio','ratio']);oic=pick(d.columns,['sum_open_interest_value','sum_open_interest'])
    if None in (tc,rc,oic): raise RuntimeError(f"flow cols missing in {path}: {d.columns.tolist()[:30]}")
    x=d[[tc,rc,oic]].copy()
    x['time']=ptime(x[tc]);x['ratio']=pd.to_numeric(x[rc],errors='coerce');x['oi']=pd.to_numeric(x[oic],errors='coerce')
    x=x.dropna().sort_values('time').drop_duplicates('time',keep='last')
    x=x[(x.ratio>0)&(x.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
    mu=x.ratio.rolling(72,min_periods=72).mean();sd=x.ratio.rolling(72,min_periods=72).std(ddof=0)
    x['z']=(x.ratio-mu)/sd.replace(0,np.nan)
    x['oi4h']=x.oi/x.oi.shift(48)-1
    return x

def load_price_zip(path):
    with zipfile.ZipFile(path) as z:
        frames=[]
        for n in z.namelist():
            if not n.lower().endswith('.csv'):continue
            with z.open(n) as fh:
                try:d=pd.read_csv(fh)
                except:continue
            frames.append(d)
    if not frames:raise RuntimeError(f"no csv in {path}")
    d=pd.concat(frames,ignore_index=True)
    # Binance archive klines can be headerless.
    if all(str(c).isdigit() for c in d.columns[:5]):
        raise RuntimeError("unexpected parsed headerless archive")
    tc=pick(d.columns,['time','timestamp','open_time']); po=pick(d.columns,['open']); ph=pick(d.columns,['high']); pl=pick(d.columns,['low']); pc=pick(d.columns,['close'])
    if tc is None:
        # Re-read headerless files explicitly.
        frames=[]
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if not n.lower().endswith('.csv'):continue
                with z.open(n) as fh:
                    q=pd.read_csv(fh,header=None)
                if q.shape[1]>=5:
                    q=q.iloc[:,:5];q.columns=['time','open','high','low','close'];frames.append(q)
        d=pd.concat(frames,ignore_index=True);tc='time';po='open';ph='high';pl='low';pc='close'
    p=d[[tc,po,ph,pl,pc]].copy();p['time']=ptime(p[tc])
    for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
    return p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')

def load_price_dir(path):
    frames=[]
    for zp in sorted(Path(path).glob("*.zip")):
        try: frames.append(load_price_zip(zp))
        except Exception as e: print("skip",zp,e)
    if not frames:raise RuntimeError(f"no price data in {path}")
    p=pd.concat(frames,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last')
    return p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

def build_context(price,flow):
    p=price.copy()
    p['time']=pd.to_datetime(p['time'],utc=True).astype('datetime64[ns, UTC]')
    flow=flow.copy()
    flow['time']=pd.to_datetime(flow['time'],utc=True).astype('datetime64[ns, UTC]')
    h1=p.set_index('time').resample('1h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    prev=h1.close.shift(1)
    tr=pd.concat([(h1.high-h1.low),(h1.high-prev).abs(),(h1.low-prev).abs()],axis=1).max(axis=1)
    h1['atr']=tr.rolling(14,min_periods=14).mean();h1['ema20']=h1.close.ewm(span=20,adjust=False).mean()
    h1['extension']=(h1.close-h1.ema20)/h1.atr;h1['close_time']=(h1.time+pd.Timedelta(hours=1)).astype('datetime64[ns, UTC]')

    h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    h4['ema50']=h4.close.ewm(span=50,adjust=False).mean();h4['ema50_lag6']=h4.ema50.shift(6)
    h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
    hp=h4.close.shift(1);htr=pd.concat([(h4.high-h4.low),(h4.high-hp).abs(),(h4.low-hp).abs()],axis=1).max(axis=1)
    h4['atr14']=htr.rolling(14,min_periods=14).mean();h4['body_atr']=(h4.close-h4.open)/h4.atr14
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
    h4['impulse_age']=ia;h4['close_time']=(h4.time+pd.Timedelta(hours=4)).astype('datetime64[ns, UTC]')

    b=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','extension']].dropna().sort_values('close_time'),
                    left_on='time',right_on='close_time',direction='backward')
    b=pd.merge_asof(b.sort_values('time'),h4[['close_time','trend','trend_age','impulse_age']].dropna().sort_values('close_time'),
                    left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
    b=pd.merge_asof(b.sort_values('time'),flow[['time','z','oi','oi4h']].dropna().sort_values('time'),
                    on='time',direction='backward',tolerance=pd.Timedelta('5min'))
    return b.dropna(subset=['atr','extension','trend','trend_age','impulse_age','z','oi','oi4h']).reset_index(drop=True)

def phase(age,imp_age):
    if age<=3:return 'BIRTH'
    if imp_age<=2:return 'REACCEL'
    if age<=12:return 'CONT'
    if age<=24:return 'MATURE'
    return 'LATE'

def gen_events(symbol,b):
    BT=b.time.reset_index(drop=True);BO=b.open.to_numpy(float);BH=b.high.to_numpy(float);BL=b.low.to_numpy(float);BC=b.close.to_numpy(float);BA=b.atr.to_numpy(float);BZ=b.z.to_numpy(float);BOI=b.oi.to_numpy(float)
    events=[]

    def swing3(i,side):
        for j in range(i+1,min(i+73,len(b)-2)):
            lo=max(i,j-3)
            if side>0:
                ref=float(np.max(BH[lo:j]))
                if BC[j]>ref:return j+1
            else:
                ref=float(np.min(BL[lo:j]))
                if BC[j]<ref:return j+1
        return None

    # Engine A
    last=len(b)-MAX_H*12-2
    for i in range(1,last):
        if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
        side=-1 if BZ[i]>0 else 1
        trend=int(b.trend.iloc[i]);ext=float(b.extension.iloc[i]);oi4=float(b.oi4h.iloc[i])
        if trend==0 or trend==side:continue
        if not((side>0 and ext<0) or (side<0 and ext>0)):continue
        if abs(ext)<A_EXT or oi4<A_OI4:continue
        ph=phase(int(b.trend_age.iloc[i]),int(b.impulse_age.iloc[i]))
        if ph not in ('CONT','REACCEL'):continue
        ei=swing3(i,side)
        if ei is None:continue
        events.append(dict(engine='A',signal_i=i,entry_i=ei,signal_time=BT.iloc[i],entry_time=BT.iloc[ei],side=side,atr=float(BA[i])))

    # B3_HIGH
    for i in range(1,last):
        if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
        trend=int(b.trend.iloc[i]);age=int(b.trend_age.iloc[i])
        if trend==0 or age<4:continue
        crowd=1 if BZ[i]>0 else -1
        if crowd!=-trend:continue
        atr=float(BA[i]);anchor=float(BC[i]);hits=[];levels=[]
        ok=True
        for k in range(1,6):
            level=anchor-trend*(0.1*k)*atr;levels.append(level);hit=None
            start=i+1 if not hits else hits[-1]
            for j in range(start,min(i+73,len(b)-2)):
                touched=(BL[j]<=level) if trend>0 else (BH[j]>=level)
                if touched:hit=j;break
            if hit is None:ok=False;break
            hits.append(hit)
        if not ok:continue
        hit=hits[-1]; zh=float(BZ[hit])
        zstr=(abs(zh)-abs(BZ[i])) if np.sign(zh)==crowd else -abs(BZ[i])
        oich=float(BOI[hit]/BOI[i]-1)
        if zstr<B3_Z_STRENGTH or oich<=0:continue
        ints=np.diff(np.asarray([i]+hits,dtype=int))
        if not(ints[3]>ints[2] and ints[4]>ints[3]):continue
        last_wave_start=float(levels[-2]);re=None
        for j in range(hit,min(hit+73,len(b)-2)):
            if (BC[j]>last_wave_start if trend>0 else BC[j]<last_wave_start):
                re=j;break
        if re is None:continue
        ei=re+1
        events.append(dict(engine='B3_HIGH',signal_i=i,entry_i=ei,signal_time=BT.iloc[i],entry_time=BT.iloc[ei],side=trend,atr=atr))

    # R48_HIGH = accepted 48h breakout + no retest + BTC-frozen acceptance/OI thresholds
    R48=48*12
    rh=b.high.shift(1).rolling(R48,min_periods=R48).max().to_numpy(float)
    rl=b.low.shift(1).rolling(R48,min_periods=R48).min().to_numpy(float)
    last_evt=-9999
    for i in range(R48+1,last-8):
        if i-last_evt<24:continue
        up=BC[i]>rh[i];dn=BC[i]<rl[i]
        if up==dn:continue
        side=1 if up else -1;boundary=float(rh[i] if up else rl[i]);atr=float(BA[i])
        outs=[(BC[j]>boundary if side>0 else BC[j]<boundary) for j in range(i+1,i+7)]
        if sum(outs)<4:continue
        # LAB136 deduplicates the raw accepted-breakout universe BEFORE LAB137 quality gates.
        last_evt=i
        ei=i+7
        closes=BC[i+1:i+7]
        mean_margin=float(np.mean((closes-boundary)*side/atr))
        if side>0:retest=bool(np.any(BL[i+1:i+7]<=boundary))
        else:retest=bool(np.any(BH[i+1:i+7]>=boundary))
        oi_ch=float(BOI[ei]/BOI[i]-1) if BOI[i]>0 else np.nan
        if retest or mean_margin<R48_MEAN_MARGIN or oi_ch<R48_OI:continue
        events.append(dict(engine='R48_HIGH',signal_i=i,entry_i=ei,signal_time=BT.iloc[i],entry_time=BT.iloc[ei],side=side,atr=atr))

    ev=pd.DataFrame(events).sort_values('entry_time').reset_index(drop=True)
    return ev,(BT,BO,BH,BL,BC,BA)

def replay(symbol,b,ev,cost):
    BT,BO,BH,BL,BC,BA=gen_events(symbol,b)[1]
    rows=[]
    for _,r in ev.iterrows():
        ei=int(r.entry_i);side=int(r.side);atr=float(r.atr);entry=float(BO[ei])
        sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(b)-1)
        gross=side*(BC[end]-entry)/atr;reason='TIME';xi=end
        for j in range(ei,end+1):
            hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
            ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
            if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
            if hs:gross=-1;reason='SL';xi=j;break
            if ht:gross=3;reason='TP';xi=j;break
        net=float(gross-(cost/10000.0)*entry/atr)
        rows.append(dict(engine=r.engine,entry_time=r.entry_time,exit_time=BT.iloc[xi],side=side,net_r=net,reason=reason))
    raw=pd.DataFrame(rows).sort_values('entry_time')
    pri={'A':0,'B3_HIGH':1,'R48_HIGH':2};raw['pri']=raw.engine.map(pri)
    raw=raw.sort_values(['entry_time','pri'])
    acc=[];open_until=pd.Timestamp.min.tz_localize('UTC')
    for _,r in raw.iterrows():
        if r.entry_time<open_until:continue
        open_until=r.exit_time;acc.append(r)
    t=pd.DataFrame(acc)
    return t

def stats(t):
    if t.empty:return dict(n=0,ev=np.nan,pf=np.nan,wr=np.nan,total_r=0,dd_r=np.nan)
    pos=t.loc[t.net_r>0,'net_r'].sum();neg=-t.loc[t.net_r<0,'net_r'].sum()
    ce=t.net_r.cumsum();dd=float((ce.cummax()-ce).max())
    return dict(n=len(t),ev=float(t.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                wr=float((t.net_r>0).mean()),total_r=float(t.net_r.sum()),dd_r=dd)

symbols={
 'BTC':('BTCUSDT_flow_2021-01-2026-08.csv.zip','btc_5m.zip'),
 'ETH':('ETH_flow.csv.zip','prices_ETH'),
 'SOL':('SOL_flow.csv','prices_SOL'),
}
summ=[];yearly=[];trades=[]
for sym,(ff,pp) in symbols.items():
    flow=load_flow(ff)
    price=load_price_zip(pp) if str(pp).endswith('.zip') else load_price_dir(pp)
    # BTC is parity control against TRAIN-only LAB138. ETH/SOL remain fully independent transfer sets.
    if sym=='BTC':
        flow=flow[flow.time<TRAIN_END].copy()
        price=price[price.time<TRAIN_END].copy()
    # strict common coverage; no threshold fitting.
    start=max(flow.time.min(),price.time.min());end=min(flow.time.max(),price.time.max())
    flow=flow[(flow.time>=start)&(flow.time<=end)].copy();price=price[(price.time>=start)&(price.time<=end)].copy()
    b=build_context(price,flow)
    ev,_=gen_events(sym,b)
    ev.to_csv(OUT/f'LAB139_{sym}_events.csv',index=False)
    for cost in COSTS:
        t=replay(sym,b,ev,cost)
        if t.empty:continue
        t['symbol']=sym;t['cost_bps']=cost;trades.append(t)
        s=stats(t)
        months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
        counts=t.engine.value_counts().to_dict()
        s.update(symbol=sym,cost_bps=cost,start=str(start),end=str(end),trades_month=len(t)/months,
                 r_month=t.net_r.sum()/months,n_A=int(counts.get('A',0)),n_B3=int(counts.get('B3_HIGH',0)),n_R48=int(counts.get('R48_HIGH',0)),
                 buy_n=int((t.side>0).sum()),sell_n=int((t.side<0).sum()))
        summ.append(s)
        for y,g in t.groupby(pd.to_datetime(t.entry_time,utc=True).dt.year):
            q=stats(g);q.update(symbol=sym,cost_bps=cost,year=int(y));yearly.append(q)

sm=pd.DataFrame(summ);sm.to_csv(OUT/'LAB139_summary.csv',index=False)
pd.DataFrame(yearly).to_csv(OUT/'LAB139_yearly.csv',index=False)
if trades:pd.concat(trades,ignore_index=True).to_csv(OUT/'LAB139_trades.csv',index=False)

# Gate decision: BTC is parity sanity only. ETH/SOL are independent cross-symbol transfer.
lines=['# LAB139 — PRODUCTION VALIDATION / CROSS-SYMBOL FROZEN TRANSFER','',
       'No thresholds are re-estimated on ETH or SOL. Frozen BTC definitions are applied verbatim.',
       'Portfolio: Engine A + B3_HIGH + R48_HIGH, one-position chronology, SL1 H1ATR / TP3R / max48h.',
       'BTC is restricted to pre-2025 TRAIN and included only as implementation-parity control against LAB138. ETH/SOL use their full common coverage as independent transfer markets.','',
       'Frozen thresholds:',
       f'- Engine A: extension >= {A_EXT:.2f} H1ATR; OI4h >= {A_OI4:.3%}.',
       f'- B3_HIGH: 0.50 H1ATR attack; Z strengthening >= {B3_Z_STRENGTH:.2f}; OI rises; d04>d03 and d05>d04.',
       f'- R48_HIGH: 48h accepted breakout; no retest; mean acceptance margin >= {R48_MEAN_MARGIN:.3f} H1ATR; OI entry change >= {R48_OI:.3%}.','']
for cost in COSTS:
    lines.append(f'## Cost {cost:.2f}bps')
    for sym in ['BTC','ETH','SOL']:
        q=sm[(sm.symbol==sym)&(sm.cost_bps==cost)]
        if len(q):
            r=q.iloc[0]
            lines.append(f"- {sym}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R, legs A/B3/R48={int(r.n_A)}/{int(r.n_B3)}/{int(r.n_R48)}, BUY/SELL={int(r.buy_n)}/{int(r.sell_n)}")
    lines.append('')
lines += ['## Production-readiness interpretation',
          'PASS requires: BTC parity close to LAB138, and frozen ETH/SOL transfer to remain directionally positive without threshold changes; stronger evidence if both independent symbols have PF >1 after 7.5bps and at least one exceeds ~1.3.',
          'Even a cross-symbol PASS does not replace broker-execution parity. Final funded/live deployment still requires actual broker spread/commission/swap/slippage and verification that the live feeder g_ratio is exactly count_long_short_ratio.']
(OUT/'LAB139_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB139_meta.json').write_text(json.dumps(dict(
    protocol='frozen cross-symbol transfer; no threshold tuning',
    symbols=list(symbols.keys()),costs=COSTS,
    thresholds=dict(A_EXT=A_EXT,A_OI4=A_OI4,B3_Z_STRENGTH=B3_Z_STRENGTH,R48_MEAN_MARGIN=R48_MEAN_MARGIN,R48_OI=R48_OI),
    caveat='research validation only until broker/feed parity'
),indent=2))
print('\n'.join(lines))
