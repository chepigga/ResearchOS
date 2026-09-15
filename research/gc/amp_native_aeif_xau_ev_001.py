#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path('research/gc')
CONF=ROOT/'AMP_GC_OOS_001_CONFIRMED_EVENTS.csv'
XAU=Path('XAUUSD_M1_2026.csv')
OUT_TRADES=ROOT/'AMP_NATIVE_AEIF_XAU_EV_001_TRADES.csv'
OUT_JSON=ROOT/'AMP_NATIVE_AEIF_XAU_EV_001_RESULT.json'
OUT_MD=ROOT/'AMP_NATIVE_AEIF_XAU_EV_001.md'

# Frozen historical execution candidate. No optimization.
ATR_N=20
TP_R=3.0
MAX_HOLD_MIN=240
SPREAD_POINT=0.01


def max_dd(r):
    eq=np.cumsum(np.asarray(r,float)); peak=np.maximum.accumulate(np.r_[0.0,eq])[1:]
    return float(np.max(peak-eq)) if len(eq) else 0.0

def pf(r):
    r=np.asarray(r,float); gp=r[r>0].sum(); gl=-r[r<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else 0.0)

def streak(r):
    best=cur=0
    for x in r:
        if x<0: cur+=1; best=max(best,cur)
        else: cur=0
    return best

def summarize(df,col):
    r=df[col].astype(float).to_numpy() if len(df) else np.array([])
    return {
        'n':int(len(r)), 'ev_r':float(r.mean()) if len(r) else None,
        'sum_r':float(r.sum()) if len(r) else 0.0,
        'wr_pct':float((r>0).mean()*100) if len(r) else None,
        'pf':pf(r), 'max_dd_r':max_dd(r), 'max_consecutive_losses':streak(r)
    }

def load_xau():
    x=pd.read_csv(XAU,sep=';')
    x['t']=pd.to_datetime(x['time'],format='%Y.%m.%d %H:%M')
    for c in ['open','high','low','close','spread']:
        x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x.sort_values('t').reset_index(drop=True)
    # Build XAU M5 and standard Wilder ATR20. ATR available only from last completed M5 bar.
    m=x.set_index('t').resample('5min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'))
    m=m.dropna().copy()
    pc=m.close.shift(1)
    m['tr']=pd.concat([(m.high-m.low),(m.high-pc).abs(),(m.low-pc).abs()],axis=1).max(axis=1)
    m.iloc[0,m.columns.get_loc('tr')]=np.nan
    m['atr20']=m.tr.ewm(alpha=1/ATR_N,adjust=False,min_periods=ATR_N).mean()
    return x,m

def simulate_one(e,x,m,spread_aware=False):
    t=pd.Timestamp(e.xau_target_file_time)
    hit=x.index[x.t.eq(t)]
    if len(hit)!=1: return None
    i=int(hit[0])
    # Risk uses ATR20 from the previous completed M5 bar.
    atr_key=t.floor('5min')-pd.Timedelta(minutes=5)
    if atr_key not in m.index or pd.isna(m.at[atr_key,'atr20']): return None
    atr=float(m.at[atr_key,'atr20'])
    if atr<=0: return None
    side=e.side
    row=x.iloc[i]
    spr=float(row.spread)*SPREAD_POINT if spread_aware else 0.0
    entry=float(row.open)+(spr if side=='LONG' else 0.0)
    sl=entry-atr if side=='LONG' else entry+atr
    tp=entry+TP_R*atr if side=='LONG' else entry-TP_R*atr
    exit_t=t; exit_px=entry; reason='NO_DATA'; same_bar_ambiguous=0
    last_i=i
    for j in range(i,min(i+MAX_HOLD_MIN,len(x))):
        rr=x.iloc[j]
        if j>i and rr.t-x.iloc[j-1].t>pd.Timedelta(minutes=1):
            # session/maintenance gap: exit on previous close
            p=x.iloc[j-1]
            sp=float(p.spread)*SPREAD_POINT if spread_aware else 0.0
            exit_t=p.t; exit_px=float(p.close)+(sp if side=='SHORT' else 0.0); reason='SESSION_CLOSE'; last_i=j-1; break
        sp=float(rr.spread)*SPREAD_POINT if spread_aware else 0.0
        if side=='LONG':
            lo=float(rr.low); hi=float(rr.high)
        else:
            lo=float(rr.low)+sp; hi=float(rr.high)+sp
        sl_hit=(lo<=sl) if side=='LONG' else (hi>=sl)
        tp_hit=(hi>=tp) if side=='LONG' else (lo<=tp)
        if sl_hit and tp_hit:
            same_bar_ambiguous=1; exit_t=rr.t; exit_px=sl; reason='SL_SAME_BAR_CONSERVATIVE'; last_i=j; break
        if sl_hit:
            exit_t=rr.t; exit_px=sl; reason='SL'; last_i=j; break
        if tp_hit:
            exit_t=rr.t; exit_px=tp; reason='TP'; last_i=j; break
        last_i=j
    else:
        pass
    if reason=='NO_DATA':
        p=x.iloc[last_i]
        sp=float(p.spread)*SPREAD_POINT if spread_aware else 0.0
        exit_t=p.t; exit_px=float(p.close)+(sp if side=='SHORT' else 0.0); reason='TIME240'
    r=(exit_px-entry)/atr if side=='LONG' else (entry-exit_px)/atr
    return {'entry_file_time':t,'side':side,'entry':entry,'atr20':atr,'sl':sl,'tp':tp,'exit_file_time':exit_t,'exit':exit_px,'reason':reason,'r':float(r),'same_bar_ambiguous':same_bar_ambiguous}

def single_position(trades):
    kept=[]; busy_until=None
    for tr in trades:
        if busy_until is not None and tr['entry_file_time']<=busy_until: continue
        kept.append(tr); busy_until=tr['exit_file_time']
    return kept

def main():
    c=pd.read_csv(CONF)
    c=c[(c.xau_history_in_range.astype(str).str.lower()=='true') & (c.xau_exact_timestamp_eligible.astype(str).str.lower()=='true')].copy()
    c['xau_target_file_time']=pd.to_datetime(c.xau_target_file_time)
    c=c.sort_values('xau_target_file_time').reset_index(drop=True)
    x,m=load_xau()
    gross=[]; spread=[]
    for e in c.itertuples(index=False):
        g=simulate_one(e,x,m,False); s=simulate_one(e,x,m,True)
        if g is not None and s is not None:
            g['core_bar_utc']=e.core_bar_utc; g['confirm_bar_utc']=e.confirm_bar_utc
            s['core_bar_utc']=e.core_bar_utc; s['confirm_bar_utc']=e.confirm_bar_utc
            gross.append(g); spread.append(s)
    gross_sp=single_position(gross); spread_sp=single_position(spread)
    # Align by entry time after single-position selection.
    smap={tr['entry_file_time']:tr for tr in spread_sp}
    rows=[]
    for g in gross_sp:
        s=smap.get(g['entry_file_time'])
        if s is None: continue
        rows.append({
            'core_bar_utc':g['core_bar_utc'],'confirm_bar_utc':g['confirm_bar_utc'],'entry_file_time':g['entry_file_time'],
            'side':g['side'],'atr20':g['atr20'],'gross_entry':g['entry'],'gross_exit':g['exit'],'gross_exit_time':g['exit_file_time'],
            'gross_reason':g['reason'],'gross_r':g['r'],'spread_r':s['r'],'spread_reason':s['reason'],'same_bar_ambiguous':max(g['same_bar_ambiguous'],s['same_bar_ambiguous'])
        })
    out=pd.DataFrame(rows)
    out.to_csv(OUT_TRADES,index=False)
    result={
        'lab':'AMP_NATIVE_AEIF_XAU_EV_001','status':'COMPLETED_FROZEN_EXECUTION','input_exact_timestamp_candidates':int(len(c)),
        'execution':{'sl':'1.0 ATR20(M5)','atr_method':'Wilder','tp_r':TP_R,'max_hold_minutes':MAX_HOLD_MIN,'session_close_exit':True,'single_position':True,'be':False,'partials':False,'trailing':False},
        'price_only':summarize(out,'gross_r'),'spread_diagnostic':summarize(out,'spread_r'),
        'long_price_only':summarize(out[out.side=='LONG'],'gross_r'),'short_price_only':summarize(out[out.side=='SHORT'],'gross_r'),
        'same_bar_ambiguous':int(out.same_bar_ambiguous.sum()) if len(out) else 0,
        'note':'Spread diagnostic assumes MT5 OHLC are Bid and spread points are 0.01 price units; commission/slippage excluded. No parameters optimized on AMP OOS.'
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    p=result['price_only']; s=result['spread_diagnostic']
    verdict='POSITIVE_EV' if p['ev_r'] is not None and p['ev_r']>0 else 'NON_POSITIVE_EV'
    md=f'''# AMP_NATIVE_AEIF_XAU_EV_001\n\n## Verdict: **{verdict}**\n\nFrozen AMP-native AEIF signals were executed on historical XAU using the frozen candidate: SL 1×ATR20(M5), TP 3R, max 240m/session close, single-position, no BE/partials/trailing. No retuning.\n\n### Price-only frozen execution\n- N: **{p['n']}**\n- EV: **{p['ev_r']:+.3f}R**\n- Sum: **{p['sum_r']:+.3f}R**\n- WR: **{p['wr_pct']:.1f}%**\n- PF: **{p['pf']:.2f}**\n- MaxDD: **{p['max_dd_r']:.2f}R**\n- Max consecutive losses: **{p['max_consecutive_losses']}**\n\n### Spread diagnostic\n- EV: **{s['ev_r']:+.3f}R**\n- Sum: **{s['sum_r']:+.3f}R**\n- PF: **{s['pf']:.2f}**\n- MaxDD: **{s['max_dd_r']:.2f}R**\n\n### Direction split, price-only\n- LONG: N={result['long_price_only']['n']}, EV={result['long_price_only']['ev_r']:+.3f}R\n- SHORT: N={result['short_price_only']['n']}, EV={result['short_price_only']['ev_r']:+.3f}R\n\nSame-M1 SL+TP ambiguity events: **{result['same_bar_ambiguous']}** (handled conservatively as SL).\n\nCoverage is limited by the available XAU history ending 2026-09-08 file clock; later AMP signals are not included.\n'''
    OUT_MD.write_text(md,encoding='utf-8')
    print(md)
    print(json.dumps(result,indent=2,default=str))

if __name__=='__main__': main()
