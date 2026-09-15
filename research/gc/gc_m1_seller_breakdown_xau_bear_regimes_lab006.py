#!/usr/bin/env python3
"""GC_M1_SELLER_BREAKDOWN_IN_XAU_BEAR_REGIMES_LAB_006

Historical drift-falsification diagnostic. Not OOS.

Goal:
Test whether the mirror SELL order-flow setup works specifically during periods where
historical XAU M1 finished lower, instead of relying on the secular bullish drift.

Frozen SELL setup (mirror of BUYER_BREAKOUT_LONG_001):
- GC M1 delta_frac <= causal prior240 Q10
- aggressive SELL volume >= causal prior240 Q75
- Low <= lowest Low of prior20 completed M1 bars
- bearish body
- close position <= 25% of current bar
- exact next M1 open entry

Controls:
- same bearish price breakdown WITHOUT extreme seller-flow gate
- original BUY-flow breakout inside the same bearish XAU regimes

Two XAU regime labels are reported:
1) EXPOST_BEAR_DAY: XAU session/date Close < Open. This is deliberately ex-post and
   used only as a drift-falsification slice, never as a deployable live gate.
2) CAUSAL_TRAILING_4H_DOWN: at the GC signal timestamp, XAU close is below its exact
   close 240 minutes earlier. This is causal and usable in principle.

Signal outcomes are measured on BOTH GC and XAU for 5/15/30/60 minutes.
XAU file clock is converted to UTC by -2h, based on the previously frozen transfer
forensic mapping. Only exact timestamp matches are admitted; no carry across gaps.
"""
from __future__ import annotations

import csv, importlib.util, io, json, math, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path('research/gc')
BASE=ROOT/'gc_m1_orderflow_edge_discovery_003.py'
XAU_URL='https://github.com/chepigga/ResearchOS/releases/download/GC/XAUUSD_M1_2026.csv'
XAU_FILE=ROOT/'_lab006_xau_m1.csv'
OUT_JSON=ROOT/'GC_M1_SELLER_BREAKDOWN_IN_XAU_BEAR_REGIMES_LAB_006.json'
OUT_MD=ROOT/'GC_M1_SELLER_BREAKDOWN_IN_XAU_BEAR_REGIMES_LAB_006.md'
OUT_EVENTS=ROOT/'GC_M1_SELLER_BREAKDOWN_IN_XAU_BEAR_REGIMES_LAB_006_EVENTS.csv'
H=(5,15,30,60)
XAU_CLOCK_OFFSET_H=2


def load_base():
    s=importlib.util.spec_from_file_location('edge003',BASE)
    m=importlib.util.module_from_spec(s); assert s and s.loader
    s.loader.exec_module(m); return m


def download_xau():
    if XAU_FILE.exists(): return
    req=urllib.request.Request(XAU_URL,headers={'User-Agent':'ResearchOS-LAB006/1.0'})
    with urllib.request.urlopen(req,timeout=180) as r, XAU_FILE.open('wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b: break
            f.write(b)


def _parse_dt(s):
    s=str(s).strip().strip('"')
    for fmt in ('%Y.%m.%d %H:%M:%S','%Y.%m.%d %H:%M','%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M','%Y-%m-%dT%H:%M:%S%z','%Y-%m-%dT%H:%M:%S'):
        try: return pd.Timestamp(pd.to_datetime(s,format=fmt,utc=False))
        except Exception: pass
    try: return pd.Timestamp(pd.to_datetime(s,utc=False))
    except Exception: return None


def load_xau():
    download_xau()
    sample=XAU_FILE.read_text(encoding='utf-8-sig',errors='replace')[:20000]
    try: sep=csv.Sniffer().sniff(sample,delimiters=',;\t').delimiter
    except Exception: sep=','
    raw=pd.read_csv(XAU_FILE,sep=sep,encoding='utf-8-sig',engine='python')
    raw.columns=[str(c).strip().strip('<>').upper() for c in raw.columns]

    # Standard MT5 bar export: DATE,TIME,OPEN,HIGH,LOW,CLOSE,...
    if {'DATE','TIME','OPEN','HIGH','LOW','CLOSE'}.issubset(raw.columns):
        t=pd.to_datetime(raw['DATE'].astype(str)+' '+raw['TIME'].astype(str),errors='coerce')
        x=pd.DataFrame({'file_time':t,'open':pd.to_numeric(raw.OPEN,errors='coerce'),'high':pd.to_numeric(raw.HIGH,errors='coerce'),'low':pd.to_numeric(raw.LOW,errors='coerce'),'close':pd.to_numeric(raw.CLOSE,errors='coerce')})
    elif {'OPEN','HIGH','LOW','CLOSE'}.issubset(raw.columns):
        # Find a date/time-like column.
        tc=None
        for c in raw.columns[:4]:
            z=pd.to_datetime(raw[c],errors='coerce')
            if z.notna().mean()>.8: tc=c; break
        if tc is None: raise RuntimeError(f'Cannot identify XAU time column: {list(raw.columns)}')
        x=pd.DataFrame({'file_time':pd.to_datetime(raw[tc],errors='coerce'),'open':pd.to_numeric(raw.OPEN,errors='coerce'),'high':pd.to_numeric(raw.HIGH,errors='coerce'),'low':pd.to_numeric(raw.LOW,errors='coerce'),'close':pd.to_numeric(raw.CLOSE,errors='coerce')})
    else:
        # Headerless/unknown fallback: parse rows and infer OHLC as first four numeric values after timestamp.
        rows=[]
        with XAU_FILE.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
            r=csv.reader(f,delimiter=sep)
            for row in r:
                if not row: continue
                dt=None; pos=None
                for i,v in enumerate(row[:4]):
                    q=_parse_dt(v)
                    if q is not None and not pd.isna(q): dt=q; pos=i; break
                if dt is None: continue
                nums=[]
                for v in row[(pos+1):]:
                    try: nums.append(float(v))
                    except Exception: pass
                if len(nums)>=4: rows.append((dt,*nums[:4]))
        x=pd.DataFrame(rows,columns=['file_time','open','high','low','close'])

    x=x.dropna().copy()
    # Frozen mapping from previous forensic: XAU file clock = UTC + 2h.
    x['time']=pd.to_datetime(x.file_time,errors='coerce')-pd.Timedelta(hours=XAU_CLOCK_OFFSET_H)
    x=x.dropna(subset=['time']).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    # Make UTC-aware without changing clock after explicit offset correction.
    x['time']=pd.to_datetime(x.time,utc=True)
    pc=x.close.shift(1)
    tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    tr.iloc[0]=np.nan
    x['atr14']=tr.rolling(14,min_periods=14).mean()
    x['close_240']=x.close.shift(240)
    # Require actual exact 240-minute spacing for causal state.
    x['time_240']=x.time.shift(240)
    x['causal_4h_down']=(x.time-x.time_240==pd.Timedelta(minutes=240))&(x.close<x.close_240)
    x['date_utc']=x.time.dt.date
    d=x.groupby('date_utc',sort=True).agg(day_open=('open','first'),day_close=('close','last'),bars=('close','size'))
    d['expost_bear_day']=d.day_close<d.day_open
    x=x.merge(d[['expost_bear_day']],left_on='date_utc',right_index=True,how='left')
    return x,d


def load_gc(m):
    work=ROOT/'_edge003_work'; work.mkdir(parents=True,exist_ok=True)
    rz=work/'rithmic.zip'; az=work/'amp.zip'
    if not rz.exists(): m.download(m.RITH_URL,rz)
    if not az.exists(): m.download(m.AMP_URL,az)
    if m.sha(rz)!=m.RITH_SHA or m.sha(az)!=m.AMP_SHA: raise RuntimeError('GC source SHA mismatch')
    return {'RITHMIC':m.load_rithmic(rz),'AMP':m.load_amp(az)}


def build_gc_events(b,feed):
    seller_flow=b.a_sell
    buyer_flow=b.a_buy
    sell_price=(b.low<=b.prior20_low)&(b.close<b.open)&(b.close_pos<=.25)
    buy_price=(b.high>=b.prior20_high)&(b.close>b.open)&(b.close_pos>=.75)
    specs={
        'SELL_OF': seller_flow&sell_price,
        'SELL_PRICE_NO_OF': (~seller_flow)&sell_price,
        'BUY_OF_IN_BEAR_CONTROL': buyer_flow&buy_price,
    }
    rows=[]
    for label,mask in specs.items():
        direction=-1 if label.startswith('SELL') else 1
        for i in np.flatnonzero(mask.fillna(False).to_numpy()):
            if i+1>=len(b): continue
            if b.iloc[i+1].time!=b.iloc[i].time+pd.Timedelta(minutes=1): continue
            atr=float(b.iloc[i].atr14)
            if not np.isfinite(atr) or atr<=0: continue
            ep=float(b.iloc[i+1].open)
            r={'feed':feed,'setup':label,'signal_time':b.iloc[i].time,'entry_time_gc':b.iloc[i+1].time,'gc_atr14':atr,'gc_entry':ep,'direction':direction}
            for h in H:
                j=i+h
                if j<len(b) and b.iloc[j].time==b.iloc[i+1].time+pd.Timedelta(minutes=h-1):
                    r[f'gc_{h}m_atr']=direction*(float(b.iloc[j].close)-ep)/atr
                else: r[f'gc_{h}m_atr']=np.nan
            rows.append(r)
    return pd.DataFrame(rows)


def attach_xau(e,x):
    if e.empty: return e
    ix=x.set_index('time')
    rows=[]
    for r in e.to_dict('records'):
        st=pd.Timestamp(r['signal_time']); et=st+pd.Timedelta(minutes=1)
        if st not in ix.index or et not in ix.index: continue
        sx=ix.loc[st]; ex=ix.loc[et]
        atr=float(sx.atr14)
        if not np.isfinite(atr) or atr<=0: continue
        r['xau_expost_bear_day']=bool(sx.expost_bear_day)
        r['xau_causal_4h_down']=bool(sx.causal_4h_down)
        r['xau_atr14']=atr; r['xau_entry']=float(ex.open); r['entry_time_xau']=et
        for h in H:
            ft=et+pd.Timedelta(minutes=h-1)
            if ft in ix.index:
                q=ix.loc[ft]
                # require exact continuous endpoint; intermediate gaps are excluded by checking count below
                win=x[(x.time>=et)&(x.time<=ft)]
                if len(win)==h and win.time.iloc[-1]-win.time.iloc[0]==pd.Timedelta(minutes=h-1):
                    r[f'xau_{h}m_atr']=r['direction']*(float(q.close)-float(ex.open))/atr
                    r[f'xau_{h}m_raw']=r['direction']*(float(q.close)-float(ex.open))
                else:
                    r[f'xau_{h}m_atr']=np.nan; r[f'xau_{h}m_raw']=np.nan
            else:
                r[f'xau_{h}m_atr']=np.nan; r[f'xau_{h}m_raw']=np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def metr(z,prefix,h):
    c=f'{prefix}_{h}m_atr'; v=z[c].dropna().to_numpy(float)
    return {'n':int(len(v)),'ev_atr':float(v.mean()) if len(v) else None,'median_atr':float(np.median(v)) if len(v) else None,'wr_pct':float((v>0).mean()*100) if len(v) else None}


def summarize(e):
    out={}
    regimes={'EXPOST_BEAR_DAY':e.xau_expost_bear_day,'CAUSAL_TRAILING_4H_DOWN':e.xau_causal_4h_down}
    for rn,rm in regimes.items():
        z=e[rm.fillna(False)].copy(); out[rn]={}
        for setup in ('SELL_OF','SELL_PRICE_NO_OF','BUY_OF_IN_BEAR_CONTROL'):
            q=z[z.setup==setup]
            out[rn][setup]={'events':int(len(q)),'GC':{str(h):metr(q,'gc',h) for h in H},'XAU':{str(h):metr(q,'xau',h) for h in H}}
    return out


def f(v): return 'NA' if v is None else f'{v:+.3f}'

def main():
    m=load_base(); x,d=load_xau(); gc=load_gc(m)
    all_events=[]; result={'lab':'GC_M1_SELLER_BREAKDOWN_IN_XAU_BEAR_REGIMES_LAB_006','status':'HISTORICAL_REGIME_DIAGNOSTIC_NOT_OOS','xau_clock_offset_hours':XAU_CLOCK_OFFSET_H,'xau_coverage':[str(x.time.min()),str(x.time.max())],'xau_days':int(len(d)),'xau_bear_days':int(d.expost_bear_day.sum()),'feeds':{}}
    for feed,b in gc.items():
        e=attach_xau(build_gc_events(b,feed),x)
        all_events.append(e); result['feeds'][feed]=summarize(e)
    E=pd.concat(all_events,ignore_index=True) if all_events else pd.DataFrame(); E.to_csv(OUT_EVENTS,index=False)
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    lines=['# GC_M1_SELLER_BREAKDOWN_IN_XAU_BEAR_REGIMES_LAB_006','',f"XAU coverage UTC after frozen -2h clock correction: `{x.time.min()}` → `{x.time.max()}`. Bear days: **{int(d.expost_bear_day.sum())}/{len(d)}**.",'','**EXPOST_BEAR_DAY is deliberately non-causal and used only to falsify bullish-drift explanations. CAUSAL_TRAILING_4H_DOWN is the deployable-style diagnostic.**','']
    for regime in ('EXPOST_BEAR_DAY','CAUSAL_TRAILING_4H_DOWN'):
        lines += [f'## {regime}','', '| Feed / setup | N | XAU 5m | XAU 15m | XAU 30m | XAU 60m | GC 15m |','|---|---:|---:|---:|---:|---:|---:|']
        for feed in ('RITHMIC','AMP'):
            for setup in ('SELL_OF','SELL_PRICE_NO_OF','BUY_OF_IN_BEAR_CONTROL'):
                q=result['feeds'][feed][regime][setup]
                lines.append(f"| {feed} {setup} | {q['events']} | {f(q['XAU']['5']['ev_atr'])} | {f(q['XAU']['15']['ev_atr'])} | {f(q['XAU']['30']['ev_atr'])} | {f(q['XAU']['60']['ev_atr'])} | {f(q['GC']['15']['ev_atr'])} |")
        lines.append('')
    lines += ['## Interpretation gate','','Evidence against simple bullish drift is stronger if SELL_OF is positive on XAU inside bearish regimes and outperforms SELL_PRICE_NO_OF, with similar sign on Rithmic and AMP. BUY_OF_IN_BEAR_CONTROL is reported as a sanity check. No thresholds are changed from the frozen mirrored breakout candidate.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
