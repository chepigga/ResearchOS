from pathlib import Path
import json, math, zipfile
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_V190_HISTORICAL_REPLAY_001')
DATA=ROOT/'data'
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Frozen CrowdFade v1.90 core parameters from CrowdFadeMulti_v190.mq5
OFF=1.50
STOP=1.00
VALID_BARS=36      # 3h on M5
PAUSE_BARS=36      # 3h on M5, anchored at ORDER SEND
HOLD_BARS=72       # 6h on M5
BE_AT=0.50
BE_LOCK=0.15
TRAIL_ARM=2.50
TRAIL_DIST=0.50
ZTH=1.00
ZWIN=72            # 6h / 5m
Z40WIN=480          # 40h / 5m
# Existing canonical sim charges half quoted spread because passive entry earns one side.
HALF_SPREAD_R=0.054/2.0


def unzip_if_needed():
    for zname in ['btc_5m.zip','BTCUSDT_flow_2021-01-2026-08.csv.zip']:
        zp=DATA/zname
        out=DATA/(zp.stem+'_unz')
        if not out.exists():
            out.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(zp) as z: z.extractall(out)


def load_price():
    files=sorted((DATA/'btc_5m_unz').rglob('BTCUSDT-5m-*.csv'))
    parts=[]
    for f in files:
        d=pd.read_csv(f,usecols=['time','open','high','low','close','volume','trades'])
        d['time']=pd.to_datetime(d['time'],format='%Y.%m.%d %H:%M',errors='coerce')
        parts.append(d)
    d=pd.concat(parts,ignore_index=True)
    d=d.dropna(subset=['time']).sort_values('time').drop_duplicates('time',keep='last')
    d=d[(d.time>=pd.Timestamp('2021-01-01')) & (d.time<pd.Timestamp('2026-09-01'))]
    d=d[d.volume>0].reset_index(drop=True)
    return d


def load_flow():
    fs=list((DATA/'BTCUSDT_flow_2021-01-2026-08.csv_unz').rglob('BTCUSDT_flow.csv'))
    if not fs: raise FileNotFoundError('BTCUSDT_flow.csv')
    f=pd.read_csv(fs[0],usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    f['time']=pd.to_datetime(f['create_time'],errors='coerce')
    f=f[(f.sum_open_interest>0)&f.time.notna()].sort_values('time').drop_duplicates('time',keep='last')
    r=f['count_long_short_ratio'].astype(float)
    m=r.rolling(ZWIN,min_periods=ZWIN).mean()
    sd=r.rolling(ZWIN,min_periods=ZWIN).std(ddof=0)
    f['z']=(r-m)/sd.replace(0,np.nan)
    m40=r.rolling(Z40WIN,min_periods=20).mean()
    sd40=r.rolling(Z40WIN,min_periods=20).std(ddof=0)
    f['z40']=(r-m40)/sd40.replace(0,np.nan)
    return f[['time','z','z40','count_long_short_ratio']].reset_index(drop=True)


def add_atr(d):
    x=d.set_index('time')
    q=x.resample('15min',label='left',closed='left').agg(
        open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum'))
    q=q.dropna(subset=['close'])
    pc=q.close.shift(1)
    tr=pd.concat([(q.high-q.low).abs(),(q.high-pc).abs(),(q.low-pc).abs()],axis=1).max(axis=1)
    q['atr']=tr.rolling(14,min_periods=14).mean()
    # MQL CopyBuffer(iATR M15, shift=1): ATR becomes usable only when its M15 bar has closed.
    a=q[['atr']].reset_index().rename(columns={'time':'bar_time'})
    a['time']=a['bar_time']+pd.Timedelta(minutes=15)
    a=a[['time','atr']].dropna()
    return pd.merge_asof(d.sort_values('time'),a.sort_values('time'),on='time',direction='backward',allow_exact_matches=True)


def attach_flow(d,f,allow_exact=False):
    return pd.merge_asof(d.sort_values('time'),f.sort_values('time'),on='time',direction='backward',allow_exact_matches=allow_exact)


def stats(r, years):
    r=np.asarray(r,float)
    if len(r)==0: return {}
    eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0.0,eq])
    dd=(peak[1:]-eq).max() if len(eq) else 0.0
    pos=r[r>0]; neg=r[r<0]
    pf=pos.sum()/abs(neg.sum()) if len(neg) and neg.sum()!=0 else np.inf
    se=r.std(ddof=1)/math.sqrt(len(r)) if len(r)>1 else np.nan
    streak=best=0
    for v in r:
        streak=streak+1 if v<0 else 0; best=max(best,streak)
    return dict(N=int(len(r)),WR=float((r>0).mean()),EV=float(r.mean()),t=float(r.mean()/se) if se>0 else np.nan,
                PF=float(pf),SumR=float(r.sum()),Ryr=float(r.sum()/years),MaxDD_R=float(dd),
                R_DD=float((r.sum()/years)/dd) if dd>0 else np.inf,MaxLossStreak=int(best),
                MedianR=float(np.median(r)))


def replay(d, cost_r=HALF_SPREAD_R):
    # arrays for speed
    T=d.time.to_numpy(); O=d.open.to_numpy(float); H=d.high.to_numpy(float); L=d.low.to_numpy(float); C=d.close.to_numpy(float)
    A=d.atr.to_numpy(float); Z=d.z.to_numpy(float)
    N=len(d); rows=[]; n_orders=0; n_active_decisions=0
    i=0; next_allowed=0
    while i < N-2:
        if i < next_allowed:
            i+=1; continue
        z=Z[i]; a=A[i]
        if not np.isfinite(z) or not np.isfinite(a) or a<=0:
            i+=1; continue
        side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:
            i+=1; continue
        n_active_decisions += 1
        # EA sends one pending order at first eligible M5 decision and anchors cooldown NOW.
        order_i=i; n_orders+=1
        e=O[i] + OFF*a if side<0 else O[i]-OFF*a
        sl=e + STOP*a if side<0 else e-STOP*a
        # Pending is valid 3h. Because order is placed at M5 open, current-bar touch is causally possible.
        fill=None
        end=min(N,order_i+VALID_BARS)
        for j in range(order_i,end):
            if (H[j]>=e) if side<0 else (L[j]<=e):
                fill=j; break
        if fill is None:
            next_allowed=order_i+PAUSE_BARS
            i=max(i+1,next_allowed)
            continue

        mfe=0.0; peak_price=e; kind='time'; exit_i=fill; exit_px=None; armed=False
        # Canonical conservative ambiguity rule on fill bar: if initial stop is in same OHLC, stop wins.
        if (H[fill]>=sl) if side<0 else (L[fill]<=sl):
            exit_px=sl; kind='stop'; exit_i=fill
        else:
            # Track fill-bar favorable excursion for diagnostics only, as canonical sim does not arm exits on fill bar.
            mfe=max(0.0, ((e-L[fill]) if side<0 else (H[fill]-e))/a)
            peak_price=(min(e,L[fill]) if side<0 else max(e,H[fill]))
            last=min(N-1,fill+HOLD_BARS)
            for j in range(fill+1,last+1):
                # 1) existing stop has priority within a bar.
                if (H[j]>=sl) if side<0 else (L[j]<=sl):
                    exit_px=sl; kind='trail' if armed else ('be' if ((side<0 and sl<e) or (side>0 and sl>e)) else 'stop'); exit_i=j; break
                # 2) update real favorable peak and MFE.
                if side<0: peak_price=min(peak_price,L[j]); fav=(e-peak_price)/a
                else: peak_price=max(peak_price,H[j]); fav=(peak_price-e)/a
                mfe=max(mfe,fav)
                # 3) breakeven lock.
                if mfe>=BE_AT:
                    ns=e + side*BE_LOCK*a
                    if (ns<sl) if side<0 else (ns>sl): sl=ns
                # 4) real-price peak trailing with frozen ATR snapshot.
                if mfe>=TRAIL_ARM:
                    armed=True
                    ns=peak_price + TRAIL_DIST*a if side<0 else peak_price-TRAIL_DIST*a
                    if (ns<sl) if side<0 else (ns>sl): sl=ns
                # 5) opposite-z exit. At M5 resolution use bar close once that bar is complete.
                zj=Z[j]
                if np.isfinite(zj) and ((zj<=-ZTH) if side<0 else (zj>=ZTH)):
                    exit_px=C[j]; kind='signal'; exit_i=j; break
            if exit_px is None:
                exit_i=last; exit_px=C[last]; kind='time'
        gross=side*(exit_px-e)/a
        net=gross-cost_r
        rows.append(dict(order_time=T[order_i],fill_time=T[fill],exit_time=T[exit_i],side='SELL' if side<0 else 'BUY',
                         z=float(z),atr=float(a),entry=float(e),exit=float(exit_px),gross_R=float(gross),R=float(net),
                         kind=kind,mfe=float(mfe),lag_bars=int(fill-order_i),hold_bars=int(exit_i-fill),toxic=bool(mfe<0.5)))
        # no new order while position exists; cooldown is anchored at order send, not fill
        next_allowed=max(order_i+PAUSE_BARS, exit_i+1)
        i=max(i+1,next_allowed)
    return pd.DataFrame(rows), dict(active_decisions=n_active_decisions,orders=n_orders,fills=len(rows),fill_rate=len(rows)/n_orders if n_orders else np.nan)


def yearly(tr):
    q=tr.copy(); q['year']=pd.to_datetime(q.order_time).dt.year
    out=[]
    for y,g in q.groupby('year'):
        s=stats(g.R.values,1.0); s['year']=int(y); out.append(s)
    return pd.DataFrame(out)


def main():
    unzip_if_needed(); p=load_price(); f=load_flow(); p=add_atr(p)
    summaries={}
    for mode,exact in [('STRICT_CAUSAL',False),('EXACT_TIMESTAMP_SENSITIVITY',True)]:
        d=attach_flow(p,f,allow_exact=exact).dropna(subset=['atr','z']).reset_index(drop=True)
        years=(d.time.iloc[-1]-d.time.iloc[0]).total_seconds()/(365.25*86400)
        tr,meta=replay(d,HALF_SPREAD_R)
        tr.to_csv(OUT/f'trades_{mode}.csv',index=False)
        yearly(tr).to_csv(OUT/f'yearly_{mode}.csv',index=False)
        s=stats(tr.R.values,years); s.update(meta); s['years']=years
        s['gross']=stats(tr.gross_R.values,years)
        s['full_spread_cost']=stats((tr.gross_R-0.054).values,years)
        s['toxic_rate']=float(tr.toxic.mean()) if len(tr) else np.nan
        s['median_fill_lag_min']=float(tr.lag_bars.median()*5) if len(tr) else np.nan
        s['exit_kinds']=tr.kind.value_counts().to_dict()
        summaries[mode]=s
    (OUT/'summary.json').write_text(json.dumps(summaries,indent=2,default=float))
    print(json.dumps(summaries,indent=2,default=float))

if __name__=='__main__': main()
