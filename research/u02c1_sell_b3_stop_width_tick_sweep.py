import os, io, zipfile, hashlib, urllib.request
import numpy as np, pandas as pd
from pathlib import Path

COST_USD=27.5
WIDTHS=[1.5,2.0,2.5,3.0,4.0,5.0,7.5]
OUT=Path('u02c1'); OUT.mkdir(exist_ok=True)

c=pd.read_csv('continuation.csv')
c['entry_time']=pd.to_datetime(c.entry_time)
ev=c[(c.side=='SELL') & (c.H4_ST_AGE_BARS>=27) & (c.H4_ST_AGE_BARS<=50) &
     (c.entry_time>=pd.Timestamp('2024-01-01')) & (c.entry_time<pd.Timestamp('2027-01-01'))].copy()
ev=ev.sort_values('entry_time').reset_index(drop=True)
assert len(ev)==176, len(ev)
print('SELL_B3_N',len(ev),'FROM',ev.entry_time.min(),'TO',ev.entry_time.max())

def fetch_bytes(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ResearchOS/1.0'})
    with urllib.request.urlopen(req,timeout=120) as r: return r.read()

# Completed H1 Wilder ATR14 from official Binance monthly klines.
months=pd.period_range(ev.entry_time.min().to_period('M')-1, ev.entry_time.max().to_period('M'), freq='M')
hframes=[]
for per in months:
    ym=str(per)
    url=f'https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{ym}.zip'
    raw=fetch_bytes(url)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name=[n for n in z.namelist() if n.endswith('.csv')][0]
        q=pd.read_csv(z.open(name),header=None)
    q=q.iloc[:,:12]
    q.columns=['open_time','open','high','low','close','volume','close_time','quote_vol','trades','tb_base','tb_quote','ignore']
    for col in ['open','high','low','close']: q[col]=pd.to_numeric(q[col],errors='coerce')
    ots=pd.to_numeric(q.open_time,errors='coerce')
    unit='us' if ots.dropna().median()>1e14 else 'ms'
    q['bar_time']=pd.to_datetime(ots,unit=unit,utc=True).dt.tz_localize(None)
    hframes.append(q[['bar_time','open','high','low','close']])
h=pd.concat(hframes,ignore_index=True).dropna().drop_duplicates('bar_time').sort_values('bar_time').reset_index(drop=True)
pc=h.close.shift(1)
tr=pd.concat([h.high-h.low,(h.high-pc).abs(),(h.low-pc).abs()],axis=1).max(axis=1)
h['atr14']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
h['close_time']=h.bar_time+pd.Timedelta(hours=1)
hct=h.close_time.to_numpy(dtype='datetime64[ns]'); hatr=h.atr14.to_numpy(float)
def atr_at(ts):
    j=int(np.searchsorted(hct,np.datetime64(ts),'right')-1)
    return float(hatr[j]) if j>=0 and np.isfinite(hatr[j]) else np.nan

states=[]
for _,r in ev.iterrows():
    a=atr_at(r.entry_time)
    if not np.isfinite(a): raise RuntimeError(f'ATR missing {r.entry_time}')
    states.append(dict(zone_id=int(r.zone_id),signal_time=pd.Timestamp(r.entry_time),atr=float(a),entry=np.nan,entry_time=pd.NaT,
                       end_time=pd.NaT,terminal=np.nan,terminal_time=pd.NaT,max_price=-np.inf,min_price=np.inf,
                       stop_hits={w:pd.NaT for w in WIDTHS},frozen_entry=float(r.entry_price),
                       frozen_net48=float(r.NET48_SPREAD_PCT),year=int(r.year)))

min_day=ev.entry_time.min().normalize(); max_day=(ev.entry_time.max()+pd.Timedelta(hours=49)).normalize()
all_days=pd.date_range(min_day,max_day,freq='D')

def read_day(day):
    ds=day.strftime('%Y-%m-%d'); fn=f'BTCUSDT-aggTrades-{ds}.zip'
    url=f'https://data.binance.vision/data/spot/daily/aggTrades/BTCUSDT/{fn}'; chkurl=url+'.CHECKSUM'
    raw=fetch_bytes(url); chk=fetch_bytes(chkurl).decode().strip().split()[0]
    got=hashlib.sha256(raw).hexdigest()
    if got!=chk: raise RuntimeError(f'checksum mismatch {ds} {got} != {chk}')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name=[n for n in z.namelist() if n.endswith('.csv')][0]
        q=pd.read_csv(z.open(name),header=None,usecols=range(8))
    q.columns=['agg_id','price','qty','first','last','ts','buyer_maker','best']
    q['price']=pd.to_numeric(q.price,errors='coerce'); ts=pd.to_numeric(q.ts,errors='coerce')
    unit='us' if ts.dropna().median()>1e14 else 'ms'
    q['time']=pd.to_datetime(ts,unit=unit,utc=True).dt.tz_localize(None)
    return q[['time','price']].dropna().sort_values('time').reset_index(drop=True)

needed=[]
for day in all_days:
    ds=day; de=day+pd.Timedelta(days=1)
    mask=(ev.entry_time < de) & ((ev.entry_time+pd.Timedelta(hours=48)) >= ds)
    if mask.any(): needed.append(day)
print('UNIQUE_TICK_DAYS',len(needed))

for k,day in enumerate(needed,1):
    q=read_day(day); qt=q.time.to_numpy(dtype='datetime64[ns]'); qp=q.price.to_numpy(float)
    day_start=day; day_end=day+pd.Timedelta(days=1)
    active=[s for s in states if s['signal_time'] < day_end and s['signal_time']+pd.Timedelta(hours=48) >= day_start and pd.isna(s['terminal'])]
    for s in active:
        if not np.isfinite(s['entry']):
            j=int(np.searchsorted(qt,np.datetime64(s['signal_time']),'left'))
            if j>=len(q): continue
            s['entry']=float(qp[j]); s['entry_time']=pd.Timestamp(q.time.iloc[j]); s['end_time']=s['entry_time']+pd.Timedelta(hours=48); start_j=j
        else: start_j=0
        if not np.isfinite(s['entry']): continue
        end_bound=min(s['end_time'],day_end); j1=int(np.searchsorted(qt,np.datetime64(end_bound),'left')); path=qp[start_j:j1]
        if len(path):
            s['max_price']=max(s['max_price'],float(np.max(path))); s['min_price']=min(s['min_price'],float(np.min(path)))
            for w in WIDTHS:
                if pd.isna(s['stop_hits'][w]):
                    stop=s['entry']+w*s['atr']; hh=np.flatnonzero(path>=stop)
                    if hh.size: s['stop_hits'][w]=pd.Timestamp(q.time.iloc[start_j+int(hh[0])])
        if s['end_time'] < day_end:
            jt=int(np.searchsorted(qt,np.datetime64(s['end_time']),'left'))
            if jt<len(q): s['terminal']=float(qp[jt]); s['terminal_time']=pd.Timestamp(q.time.iloc[jt])
    if k%25==0 or k==len(needed): print('DAYS_DONE',k,'/',len(needed))

rows=[]
for s in states:
    if not np.isfinite(s['entry']) or not np.isfinite(s['terminal']): raise RuntimeError(f'incomplete event {s["zone_id"]} {s["signal_time"]}')
    adverse_atr=(s['max_price']-s['entry'])/s['atr']; favorable_atr=(s['entry']-s['min_price'])/s['atr']
    term_pct=(s['entry']-s['terminal'])/s['entry']*100.0 - COST_USD/s['entry']*100.0
    row=dict(zone_id=s['zone_id'],signal_time=s['signal_time'],entry_time=s['entry_time'],entry=s['entry'],atr_h1=s['atr'],terminal_time=s['terminal_time'],
             terminal=s['terminal'],adverse_atr=adverse_atr,favorable_atr=favorable_atr,terminal_net_pct=term_pct,
             frozen_entry=s['frozen_entry'],frozen_net48=s['frozen_net48'],year=s['year'])
    for w in WIDTHS:
        hit=not pd.isna(s['stop_hits'][w]); costR=COST_USD/(w*s['atr'])
        if hit:
            rr=-1.0-costR; pct=-(w*s['atr'])/s['entry']*100.0-COST_USD/s['entry']*100.0
        else:
            rr=(s['entry']-s['terminal'])/(w*s['atr'])-costR; pct=term_pct
        row[f'hit_{w:g}']=hit; row[f'R_{w:g}']=rr; row[f'pct_{w:g}']=pct
    rows.append(row)
r=pd.DataFrame(rows)

def pf(x):
    z=pd.Series(x).dropna(); gp=z[z>0].sum(); gl=-z[z<0].sum(); return float(gp/gl) if gl>0 else float('inf')
summary=[]
for w in WIDTHS:
    z=r[f'R_{w:g}']; p=r[f'pct_{w:g}']
    summary.append(dict(stop_atr=w,N=len(r),stop_hit_rate=float(r[f'hit_{w:g}'].mean()),EV_R=float(z.mean()),PF_R=pf(z),WR_R=float((z>0).mean()),
                        EV_pct=float(p.mean()),PF_pct=pf(p),WR_pct=float((p>0).mean())))
sm=pd.DataFrame(summary)
aq=r.adverse_atr.quantile([.25,.5,.75,.9,.95,.99]).rename('adverse_atr').reset_index().rename(columns={'index':'quantile'})
fq=r.favorable_atr.quantile([.25,.5,.75,.9,.95,.99]).rename('favorable_atr').reset_index().rename(columns={'index':'quantile'})
yearly=[]
for y,g in r.groupby('year'):
    for w in WIDTHS:
        z=g[f'R_{w:g}']; yearly.append(dict(year=int(y),stop_atr=w,N=len(g),stop_hit_rate=float(g[f'hit_{w:g}'].mean()),EV_R=float(z.mean()),PF_R=pf(z),WR_R=float((z>0).mean())))
yr=pd.DataFrame(yearly)
print('\n=== ADVERSE ATR QUANTILES ==='); print(aq.to_string(index=False))
print('\n=== STOP WIDTH SUMMARY ==='); print(sm.to_string(index=False))
print('\n=== YEARLY ==='); print(yr.to_string(index=False))
print('\nTERMINAL_DIRECTIONAL EV_pct',r.terminal_net_pct.mean(),'PF',pf(r.terminal_net_pct),'WR',float((r.terminal_net_pct>0).mean()))
r.to_csv(OUT/'events.csv',index=False); sm.to_csv(OUT/'summary.csv',index=False); yr.to_csv(OUT/'yearly.csv',index=False); aq.to_csv(OUT/'adverse_quantiles.csv',index=False); fq.to_csv(OUT/'favorable_quantiles.csv',index=False)
rep=['# U02C1 SELL B3 Stop-Width Binance Tick Sweep','',f'Events: {len(r)} (2024–2026), official Binance BTCUSDT aggTrades, 48h event windows.','',
     '## Adverse excursion in H1 ATR units','',aq.to_markdown(index=False),'','## Stop-width sweep','',sm.to_markdown(index=False),'','## Yearly','',yr.to_markdown(index=False),'',
     f'No-stop terminal directional 48h: EV={r.terminal_net_pct.mean():.6f}%, PF={pf(r.terminal_net_pct):.4f}, WR={(r.terminal_net_pct>0).mean():.3f}.','',
     'Stop widths are evaluated both in risk-normalized R and fixed-notional percentage. Wider stops are not credited merely for increasing win rate.']
(OUT/'REPORT.md').write_text('\n'.join(rep))
