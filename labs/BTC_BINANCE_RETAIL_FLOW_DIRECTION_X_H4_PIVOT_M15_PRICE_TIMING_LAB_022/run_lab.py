#!/usr/bin/env python3
from __future__ import annotations
import io, json, math, glob, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import requests

LAB='BTC_BINANCE_RETAIL_FLOW_DIRECTION_X_H4_PIVOT_M15_PRICE_TIMING_LAB_022'
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
ROOT=HERE.parent
STREAM=ROOT/'BTC_REVERSAL_H4_PIVOT_M15_TWO_BAR_CONFIRM_FORMAL_REPLICATION_AND_CANONICAL_UNION_LAB_018'/'output'/'two_bar_confirm_vf1_stream.csv'
COST_BPS=5.0
FLOW_LOOKBACK_DAYS=90
FLOW_MIN_N=1000
HORIZON_BARS=48
STOP_ATR=1.5
UTC='UTC'

WINS={
 '2021':('2021-01-01','2022-01-01'),
 '2022':('2022-01-01','2023-01-01'),
 '2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),
 '2025_H1':('2025-01-01','2025-07-01'),
 '2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),
 'AUG2026_REUSED_AUDIT':('2026-08-01','2026-09-01'),
 'ALL_PRE_AUG':('2021-01-01','2026-08-01'),
 'POOLED_RECENT':('2025-07-01','2026-08-01'),
}

def b(v): return str(v).strip().lower() in {'true','1','yes'}

def tstat(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if len(a)<2:return np.nan
    s=a.std(ddof=1)
    return float(a.mean()/(s/math.sqrt(len(a)))) if s>0 else np.nan

def pf(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    pos=a[a>0].sum(); neg=-a[a<0].sum()
    if neg==0:return np.inf if pos>0 else np.nan
    return float(pos/neg)

def maxdd(a):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if not len(a): return 0.0
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq]); return float(np.max(peak[1:]-eq))

def load_price():
    parts=[]
    for p in sorted(glob.glob('btc15/**/*.csv',recursive=True)):
        d=pd.read_csv(p)
        req={'time','open','high','low','close'}
        if not req.issubset(d.columns): continue
        d=d[['time','open','high','low','close']].copy()
        d['time']=pd.to_datetime(d.time,errors='coerce',utc=True)
        for c in ['open','high','low','close']: d[c]=pd.to_numeric(d[c],errors='coerce')
        parts.append(d.dropna())
    if not parts: raise RuntimeError('No btc15 price CSVs loaded')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    pc=x.close.shift(1)
    tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr14']=tr.rolling(14,min_periods=14).mean()
    x=x.set_index('time')
    return x

def load_stream():
    s=pd.read_csv(STREAM)
    for c in ['parent_time','signal_time','fill_time','exit_time','event_time']:
        if c in s.columns:s[c]=pd.to_datetime(s[c],errors='coerce',utc=True)
    for c in ['filled','vf1_mature','real_fill']:
        if c in s.columns:s[c]=s[c].map(b)
    for c in ['impulse_dir','entry','event_close','child_range']:
        if c in s.columns:s[c]=pd.to_numeric(s[c],errors='coerce')
    s['price_side']=np.where(s.impulse_dir<0,1,-1) # +1 BUY, -1 SELL reversal
    return s

def detect_price_offset(price,s):
    cand=[pd.Timedelta(minutes=-15),pd.Timedelta(0),pd.Timedelta(minutes=15)]
    rows=[]
    q=s.dropna(subset=['signal_time','event_close']).head(100)
    for off in cand:
        er=[]
        for r in q.itertuples():
            t=r.signal_time+off
            if t in price.index:
                er.append(abs(float(price.loc[t,'close'])-float(r.event_close))/max(abs(float(r.event_close)),1e-9))
        rows.append((off,float(np.median(er)) if er else np.inf,len(er)))
    rows.sort(key=lambda z:z[1]); best=rows[0]
    if best[2]<20 or best[1]>0.003: raise RuntimeError(f'Price parity failed offsets={rows}')
    return best,rows

def month_iter(start='2021-01',end='2026-08'):
    for p in pd.period_range(start,end,freq='M'): yield p.year,p.month

def parse_metrics_zip(content,label):
    z=zipfile.ZipFile(io.BytesIO(content)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:return pd.DataFrame()
    d=pd.read_csv(z.open(names[0]))
    # Binance archive schema uses create_time and count_long_short_ratio.
    tc='create_time' if 'create_time' in d.columns else ('timestamp' if 'timestamp' in d.columns else None)
    rc='count_long_short_ratio' if 'count_long_short_ratio' in d.columns else None
    if tc is None or rc is None: raise RuntimeError(f'Unexpected metrics schema {label}: {list(d.columns)}')
    d=d[[tc,rc]].rename(columns={tc:'time',rc:'ratio'})
    if np.issubdtype(d['time'].dtype,np.number): d['time']=pd.to_datetime(d.time,unit='ms',errors='coerce',utc=True)
    else: d['time']=pd.to_datetime(d.time,errors='coerce',utc=True)
    d['ratio']=pd.to_numeric(d.ratio,errors='coerce')
    return d.dropna()

def download_metrics():
    ses=requests.Session(); parts=[]; manifest=[]
    base='https://data.binance.vision/data/futures/um/monthly/metrics/BTCUSDT'
    for y,m in month_iter():
        fn=f'BTCUSDT-metrics-{y}-{m:02d}.zip'; url=f'{base}/{fn}'
        try:r=ses.get(url,timeout=30)
        except Exception as e:
            manifest.append(dict(year=y,month=m,status='EXC',rows=0,note=str(e))); continue
        if r.status_code==200:
            try:d=parse_metrics_zip(r.content,fn); parts.append(d); manifest.append(dict(year=y,month=m,status=200,rows=len(d),note='monthly'))
            except Exception as e:manifest.append(dict(year=y,month=m,status='PARSE_FAIL',rows=0,note=str(e)))
        else: manifest.append(dict(year=y,month=m,status=r.status_code,rows=0,note='monthly_missing'))
    man=pd.DataFrame(manifest); man.to_csv(OUT/'metrics_download_manifest.csv',index=False)
    if not parts: raise RuntimeError('No Binance monthly metrics archives loaded')
    d=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last')
    # causal M15 last observation at/before each 15-minute bucket endpoint/label.
    d=d.set_index('time')['ratio'].resample('15min',label='left',closed='left').last().ffill(limit=2).dropna().to_frame()
    d['delta_ls_12']=d.ratio-d.ratio.shift(12)
    return d

def flow_state(flow,t):
    # current observation at or before t; thresholds use strictly earlier observations only.
    pos=flow.index.searchsorted(t,side='right')-1
    if pos<12:return None
    tt=flow.index[pos]; cur=float(flow.delta_ls_12.iloc[pos])
    hist=flow.loc[(flow.index>=tt-pd.Timedelta(days=FLOW_LOOKBACK_DAYS))&(flow.index<tt),'delta_ls_12'].dropna()
    if len(hist)<FLOW_MIN_N or not np.isfinite(cur):return None
    q20=float(hist.quantile(.20)); q80=float(hist.quantile(.80))
    side=1 if cur<=q20 else (-1 if cur>=q80 else 0)
    return dict(flow_time=tt,ratio=float(flow.ratio.iloc[pos]),delta_ls_12=cur,q20=q20,q80=q80,flow_side=side,history_n=len(hist))

def pxrow(price,t,off):
    tt=t+off
    return price.loc[tt] if tt in price.index else None,tt

def add_common_clock(price,flow,s,off):
    rows=[]
    for r in s.itertuples():
        if pd.isna(r.signal_time):continue
        pr,pt=pxrow(price,r.signal_time,off)
        fs=flow_state(flow,r.signal_time)
        if pr is None or fs is None or not np.isfinite(pr.atr14) or pr.atr14<=0:continue
        endt=pt+pd.Timedelta(hours=12)
        if endt not in price.index:continue
        move=(float(price.loc[endt,'close'])-float(pr.close))/float(pr.atr14)
        d=r._asdict(); d.update(fs); d.update(signal_price_time=pt,signal_close=float(pr.close),atr14_signal=float(pr.atr14),future12_move_atr=move)
        d['price_signed12_atr']=float(r.price_side*move)
        d['flow_signed12_atr']=float(fs['flow_side']*move) if fs['flow_side']!=0 else np.nan
        d['flow_extreme']=fs['flow_side']!=0
        d['flow_agree']=fs['flow_side']==r.price_side and fs['flow_side']!=0
        d['flow_conflict']=fs['flow_side']==-r.price_side and fs['flow_side']!=0
        rows.append(d)
    return pd.DataFrame(rows)

def summarize_clean(d,label,mask_col=None):
    q=d.copy() if mask_col is None else d[d[mask_col]].copy()
    col='price_signed12_atr' if label=='PRICE_ONLY' else 'flow_signed12_atr'
    a=pd.to_numeric(q[col],errors='coerce').dropna().to_numpy(float)
    return dict(sample=label,n=len(a),mean_atr=float(a.mean()) if len(a) else np.nan,cum_atr=float(a.sum()),t=tstat(a),hit_rate=float((a>0).mean()) if len(a) else np.nan,pf=pf(a),dd_atr=maxdd(a))

def bounded_trade(price,r,off,use_stop=True):
    if not bool(r.filled) or pd.isna(r.fill_time) or not np.isfinite(r.entry):return None
    # map persisted fill label with same technical offset.
    ft=r.fill_time+off
    if ft not in price.index:return None
    atr=float(price.loc[ft,'atr14'])
    if not np.isfinite(atr) or atr<=0:return None
    side=int(r.price_side); entry=float(r.entry); stop=entry-side*STOP_ATR*atr
    endt=ft+pd.Timedelta(hours=12)
    if endt not in price.index:return None
    exit_px=float(price.loc[endt,'close']); exit_t=endt; stopped=False
    if use_stop:
        path=price.loc[(price.index>=ft)&(price.index<=endt)]
        for t,z in path.iterrows():
            hit=(float(z.low)<=stop) if side>0 else (float(z.high)>=stop)
            if hit:
                exit_px=stop; exit_t=t; stopped=True; break
    gross=side*(exit_px-entry)/atr
    cost=(entry*(COST_BPS/10000.0))/atr
    return dict(fill_price_time=ft,execution_atr=atr,side=side,exit_time_12h=exit_t,stopped=stopped,gross_atr=gross,cost_atr=cost,net_atr=gross-cost)

def make_exec(price,common,off,use_stop=True,require_vf1=False):
    rows=[]
    for _,r in common.iterrows():
        if not bool(r.flow_agree) or not bool(r.filled):continue
        if require_vf1 and not bool(r.vf1_mature):continue
        z=bounded_trade(price,r,off,use_stop)
        if z is None:continue
        d=r.to_dict(); d.update(z); rows.append(d)
    return pd.DataFrame(rows)

def summarize_exec(d,label):
    a=pd.to_numeric(d.net_atr,errors='coerce').dropna().to_numpy(float) if len(d) else np.array([])
    return dict(sample=label,n=len(a),mean_net_atr=float(a.mean()) if len(a) else np.nan,cum_net_atr=float(a.sum()),t=tstat(a),pf=pf(a),dd_atr=maxdd(a),stop_rate=float(d.stopped.mean()) if len(d) and 'stopped' in d else np.nan,long_n=int((d.side==1).sum()) if len(d) else 0,short_n=int((d.side==-1).sum()) if len(d) else 0)

def window_table(d,kind='exec'):
    rows=[]
    tc='signal_time'
    for w,(a,b_) in WINS.items():
        a=pd.Timestamp(a,tz=UTC); b_=pd.Timestamp(b_,tz=UTC); q=d[(d[tc]>=a)&(d[tc]<b_)].copy()
        z=summarize_exec(q,w) if kind=='exec' else summarize_clean(q,w,'flow_extreme')
        z['window']=w; rows.append(z)
    return pd.DataFrame(rows)

def flow_only_reference(price,flow):
    rows=[]; last=None
    for t,r in flow.dropna(subset=['delta_ls_12']).iterrows():
        if t<pd.Timestamp('2021-01-01',tz=UTC) or t>=pd.Timestamp('2026-09-01',tz=UTC):continue
        fs=flow_state(flow,t)
        if fs is None or fs['flow_side']==0:continue
        if last is not None and t-last<pd.Timedelta(hours=12):continue
        if t not in price.index or t+pd.Timedelta(hours=12) not in price.index:continue
        atr=float(price.loc[t,'atr14']);
        if not np.isfinite(atr) or atr<=0:continue
        mv=(float(price.loc[t+pd.Timedelta(hours=12),'close'])-float(price.loc[t,'close']))/atr
        rows.append(dict(signal_time=t,side=fs['flow_side'],signed12_atr=fs['flow_side']*mv)); last=t
    return pd.DataFrame(rows)

def coverage_2022(flow):
    a=pd.Timestamp('2022-01-01',tz=UTC); b_=pd.Timestamp('2023-01-01',tz=UTC)
    expected=len(pd.date_range(a,b_-pd.Timedelta(minutes=15),freq='15min'))
    got=int(flow.loc[(flow.index>=a)&(flow.index<b_),'ratio'].notna().sum())
    return got/expected if expected else np.nan,got,expected

def report(clean,exsum,extab,flowref,gates,meta):
    def f(x):
        if pd.isna(x):return '—'
        if np.isinf(x):return 'inf'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f"**Verdict: {meta['verdict']} — {sum(gates.values())}/{len(gates)}**",'',
           '## Data/parity',f"- Metrics rows M15: **{meta['flow_rows']}**, range {meta['flow_start']} .. {meta['flow_end']}",f"- 2022 coverage: **{meta['coverage_2022']:.1%}**",f"- Price label offset selected by close parity: **{meta['price_offset_minutes']} min**, median close error {meta['price_parity_error']:.6f}",'',
           '## Part A — clean 12h direction at frozen H4/M15 child clock','', '| Sample | N | Mean ATR | Cum ATR | t | Hit | PF |','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in clean.iterrows(): lines.append(f"| {r['sample']} | {int(r.n)} | {f(r.mean_atr)} | {f(r.cum_atr)} | {f(r.t)} | {f(r.hit_rate)} | {f(r.pf)} |")
    lines += ['', '## Part B — FLOW agrees with price timing, local-extreme fill, SL1.5ATR, no TP, TIME12H','', '| Window | N | Mean net ATR | Cum net ATR | t | PF | DD | Stop rate | Long/Short |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in extab.iterrows(): lines.append(f"| {r.window} | {int(r.n)} | {f(r.mean_net_atr)} | {f(r.cum_net_atr)} | {f(r.t)} | {f(r.pf)} | {f(r.dd_atr)} | {f(r.stop_rate)} | {int(r.long_n)}/{int(r.short_n)} |")
    lines += ['', '## Execution audits','', '| Sample | N | Mean net ATR | Cum net ATR | PF | Stop rate |','|---|---:|---:|---:|---:|---:|']
    for _,r in exsum.iterrows(): lines.append(f"| {r['sample']} | {int(r.n)} | {f(r.mean_net_atr)} | {f(r.cum_net_atr)} | {f(r.pf)} | {f(r.stop_rate)} |")
    lines += ['', '## Non-overlapping flow-only reference', f"N={len(flowref)}, mean={f(flowref.signed12_atr.mean() if len(flowref) else np.nan)} ATR, t={f(tstat(flowref.signed12_atr if len(flowref) else []))}.",'','## Gates']
    for k,v in gates.items(): lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ['', '## Guardrail','Retail-flow thresholds here are causal trailing-90d quintiles because the earlier standalone absolute thresholds were not persisted. No cutoff/horizon/stop/TP rescue is allowed. August 2026 is reused audit only. Live allocation remains **0**.']
    return '\n'.join(lines)+'\n'

def main():
    price=load_price(); stream=load_stream(); best,offsets=detect_price_offset(price,stream); off=best[0]
    flow=download_metrics()
    common=add_common_clock(price,flow,stream,off)
    common.to_csv(OUT/'common_clock_child_signals.csv',index=False)
    clean_rows=[summarize_clean(common,'PRICE_ONLY')]
    q=common[common.flow_extreme].copy(); clean_rows.append(summarize_clean(q,'FLOW_EXTREME'))
    qa=common[common.flow_agree].copy(); clean_rows.append(summarize_clean(qa,'FLOW_PRICE_AGREE'))
    qc=common[common.flow_conflict].copy(); clean_rows.append(summarize_clean(qc,'FLOW_PRICE_CONFLICT'))
    clean=pd.DataFrame(clean_rows); clean.to_csv(OUT/'clean_direction_summary.csv',index=False)

    bounded=make_exec(price,common,off,True,False); nostop=make_exec(price,common,off,False,False); vf1=make_exec(price,common,off,True,True)
    bounded.to_csv(OUT/'bounded_agreement_trades.csv',index=False); nostop.to_csv(OUT/'nostop_agreement_trades.csv',index=False); vf1.to_csv(OUT/'vf1_bounded_agreement_trades.csv',index=False)
    exsum=pd.DataFrame([summarize_exec(bounded,'PRIMARY_SL15_TIME12'),summarize_exec(nostop,'AUDIT_NOSTOP_TIME12'),summarize_exec(vf1,'AUDIT_VF1_SL15_TIME12')]); exsum.to_csv(OUT/'execution_summary.csv',index=False)
    extab=window_table(bounded,'exec'); extab.to_csv(OUT/'execution_by_window.csv',index=False)
    flowref=flow_only_reference(price,flow); flowref.to_csv(OUT/'flow_only_nonoverlap.csv',index=False)
    cov,got,expected=coverage_2022(flow)

    pre=bounded[bounded.signal_time<pd.Timestamp('2026-08-01',tz=UTC)]
    pre_clean=common[common.signal_time<pd.Timestamp('2026-08-01',tz=UTC)]
    flowpre=pre_clean[pre_clean.flow_extreme]
    agreepre=pre_clean[pre_clean.flow_agree]
    price_mean=float(pre_clean.price_signed12_atr.mean()) if len(pre_clean) else np.nan
    agree_mean=float(agreepre.flow_signed12_atr.mean()) if len(agreepre) else np.nan
    y22=pre[(pre.signal_time>=pd.Timestamp('2022-01-01',tz=UTC))&(pre.signal_time<pd.Timestamp('2023-01-01',tz=UTC))&(pre.side==-1)]
    recent=pre[(pre.signal_time>=pd.Timestamp('2025-07-01',tz=UTC))]
    nospre=nostop[nostop.signal_time<pd.Timestamp('2026-08-01',tz=UTC)]
    ar=pre.net_atr.to_numpy(float) if len(pre) else np.array([])
    gates={
      'metrics_2022_coverage_ge_90pct':bool(cov>=.90),
      'partA_flow_extreme_n_ge_30':len(flowpre)>=30,
      'partA_flow_mean_positive':bool(len(flowpre) and flowpre.flow_signed12_atr.mean()>0),
      'partA_agreement_mean_gt_price_only':bool(len(agreepre) and np.isfinite(price_mean) and agree_mean>price_mean),
      'partB_bounded_n_ge_12':len(pre)>=12,
      'partB_bounded_mean_positive':bool(len(pre) and np.mean(ar)>0),
      'partB_bounded_pf_gt_1_25':bool(len(pre) and np.isfinite(pf(ar)) and pf(ar)>1.25),
      'stress_2022_short_n_ge_3_and_cum_positive':bool(len(y22)>=3 and y22.net_atr.sum()>0),
      'recent_2025h2_2026_cum_positive':bool(len(recent) and recent.net_atr.sum()>0),
      'nostop_time12_mean_positive':bool(len(nospre) and nospre.net_atr.mean()>0),
    }
    score=sum(gates.values()); critical=['metrics_2022_coverage_ge_90pct','partA_flow_mean_positive','partB_bounded_n_ge_12','partB_bounded_mean_positive','recent_2025h2_2026_cum_positive']
    if score>=8 and all(gates[k] for k in critical): verdict='PASS_FLOW_X_PRICE_TIMING_BRIDGE'
    elif gates['partA_flow_mean_positive'] and (not gates['partB_bounded_n_ge_12'] or gates['partB_bounded_mean_positive']): verdict='WATCH_DIRECTIONAL_FLOW_EXECUTION_BRIDGE'
    else: verdict='FAIL_NO_TRANSFERABLE_FLOW_X_PRICE_TIMING_EDGE'
    meta=dict(verdict=verdict,flow_rows=len(flow),flow_start=str(flow.index.min()),flow_end=str(flow.index.max()),coverage_2022=cov,coverage_2022_rows=got,coverage_2022_expected=expected,price_offset_minutes=int(off.total_seconds()/60),price_parity_error=best[1],price_offset_audit=[(int(o.total_seconds()/60),e,n) for o,e,n in offsets],common_child_signals=len(common),pre_aug_bounded=len(pre))
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,allow_nan=True),encoding='utf-8')
    rep=report(clean,exsum,extab,flowref,gates,meta); (OUT/'REPORT.md').write_text(rep,encoding='utf-8')
    print(rep)

if __name__=='__main__': main()
