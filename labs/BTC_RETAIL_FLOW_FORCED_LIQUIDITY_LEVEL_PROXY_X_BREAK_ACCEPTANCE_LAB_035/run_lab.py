#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, io, json, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

LAB='BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC34=LABS/'BTC_FUTURES_RETAIL_CROWDING_X_SPOT_FLOW_DIVERGENCE_AND_OI_PROFITABILITY_MAP_LAB_034'/'run_lab.py'
spec=importlib.util.spec_from_file_location('lab034',SRC34); L34=importlib.util.module_from_spec(spec); spec.loader.exec_module(L34)
L34.OUT=OUT
PRE=pd.Timestamp('2026-08-01',tz='UTC'); AUG_END=pd.Timestamp('2026-09-01',tz='UTC')
START_MONTH='2020-12'; END_MONTH='2026-08'; SEED=20260908; BOOT_N=5000
LEVEL_BARS=48; ACCEPT_BARS=4
WINS={
 '2021':('2021-01-01','2022-01-01'),'2022':('2022-01-01','2023-01-01'),'2023':('2023-01-01','2024-01-01'),
 '2024':('2024-01-01','2025-01-01'),'2025_H1':('2025-01-01','2025-07-01'),'2025_H2':('2025-07-01','2026-01-01'),
 '2026_JAN_JUL':('2026-01-01','2026-08-01'),'AUG_REUSED':('2026-08-01','2026-09-01'),
 'ALL_PRE_AUG':('2021-01-01','2026-08-01'),'POOLED_RECENT':('2025-07-01','2026-08-01')}


def ts_from_num(s):
    v=pd.to_numeric(s,errors='coerce'); med=v.dropna().abs().median() if v.notna().any() else np.nan
    unit='us' if pd.notna(med) and med>1e14 else ('ms' if pd.notna(med) and med>1e11 else 's')
    return pd.to_datetime(v,unit=unit,errors='coerce',utc=True)


def parse_fut_kline(content,label):
    z=zipfile.ZipFile(io.BytesIO(content)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:return pd.DataFrame()
    d=pd.read_csv(z.open(names[0]),header=None)
    if d.shape[1]<6: raise RuntimeError(f'bad kline schema {label}: {d.shape}')
    x=pd.DataFrame({'time':ts_from_num(d.iloc[:,0]),'open':pd.to_numeric(d.iloc[:,1],errors='coerce'),'high':pd.to_numeric(d.iloc[:,2],errors='coerce'),'low':pd.to_numeric(d.iloc[:,3],errors='coerce'),'close':pd.to_numeric(d.iloc[:,4],errors='coerce')}).dropna()
    return x


def download_futures():
    periods=list(pd.period_range(START_MONTH,END_MONTH,freq='M')); base='https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m'; parts=[]; man=[]
    def one(p):
        ym=f'{p.year}-{p.month:02d}'; fn=f'BTCUSDT-15m-{ym}.zip'; url=f'{base}/{fn}'
        try:
            r=requests.get(url,timeout=30)
            if r.status_code!=200:return None,dict(month=ym,status=r.status_code,rows=0)
            q=parse_fut_kline(r.content,fn); return q,dict(month=ym,status=200,rows=len(q))
        except Exception as e:return None,dict(month=ym,status='EXC',rows=0,note=str(e))
    with ThreadPoolExecutor(max_workers=12) as ex:
        fut=[ex.submit(one,p) for p in periods]
        for f in as_completed(fut):
            d,m=f.result(); man.append(m)
            if d is not None and len(d):parts.append(d)
    pd.DataFrame(man).sort_values('month').to_csv(OUT/'futures_kline_manifest.csv',index=False)
    if not parts: raise RuntimeError('No futures klines')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').set_index('time')
    pc=x.close.shift(1); tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr14']=tr.rolling(14,min_periods=14).mean()
    x['prior12_low']=x.low.shift(1).rolling(LEVEL_BARS,min_periods=LEVEL_BARS).min()
    x['prior12_high']=x.high.shift(1).rolling(LEVEL_BARS,min_periods=LEVEL_BARS).max()
    return x


def load_inputs():
    flow=L34.load_flow(); metrics=L34.download_metrics(); fut=download_futures()
    return flow,metrics,fut


def dist_bin(x):
    if not np.isfinite(x):return 'NA'
    if x<=.5:return '<=0.5'
    if x<=1:return '0.5-1'
    if x<=2:return '1-2'
    return '>2'


def build_events(flow,metrics,fut):
    rows=[]
    for r in flow.itertuples():
        t=pd.Timestamp(r.signal_time); side=int(r.side)
        if t not in fut.index or t not in metrics.index:continue
        z=fut.loc[t]; atr=float(z.atr14)
        if not np.isfinite(atr) or atr<=0:continue
        lvl=float(z.prior12_high if side>0 else z.prior12_low)
        if not np.isfinite(lvl):continue
        sig=float(z.close); endt=t+pd.Timedelta(hours=12)
        if endt not in fut.index:continue
        end_close=float(fut.loc[endt,'close'])
        distance=max(0.0,(lvl-sig)/atr) if side>0 else max(0.0,(sig-lvl)/atr)
        path=fut.loc[(fut.index>=t)&(fut.index<=endt)]
        touch_time=pd.NaT; class_time=pd.NaT; state='NO_TOUCH'; class_px=np.nan
        touch_pos=None
        for i,(tt,b) in enumerate(path.iterrows()):
            hit=float(b.high)>=lvl if side>0 else float(b.low)<=lvl
            if hit:
                touch_time=tt; touch_pos=i; break
        if touch_pos is not None:
            resp=path.iloc[touch_pos:touch_pos+ACCEPT_BARS]
            acc=None
            for tt,b in resp.iterrows():
                ok=side*(float(b.close)-lvl)>=0
                if ok:
                    acc=(tt,float(b.close)); break
            if acc is not None:
                state='ACCEPT'; class_time,class_px=acc
            elif len(resp)>=ACCEPT_BARS:
                state='REJECT'; class_time=resp.index[-1]; class_px=float(resp.iloc[-1].close)
            else:
                state='UNRESOLVED'; class_time=resp.index[-1] if len(resp) else touch_time; class_px=float(resp.iloc[-1].close) if len(resp) else np.nan
        resid=side*(end_close-class_px)/atr if pd.notna(class_time) and np.isfinite(class_px) else np.nan
        m=metrics.loc[t]; oi=float(m.get('sum_open_interest',np.nan)); oi_prev=float(metrics.loc[t-pd.Timedelta(hours=3),'sum_open_interest']) if t-pd.Timedelta(hours=3) in metrics.index else np.nan
        oi3=np.log(oi)-np.log(oi_prev) if oi>0 and oi_prev>0 else np.nan
        oi_back=bool(np.isfinite(oi3) and oi3>0)
        oi_flush=np.nan; oi_flush_logchg=np.nan
        if pd.notna(touch_time) and pd.notna(class_time):
            pre_t=touch_time-pd.Timedelta(minutes=15); post_t=class_time+pd.Timedelta(hours=1)
            if pre_t in metrics.index and post_t in metrics.index:
                a=float(metrics.loc[pre_t,'sum_open_interest']); b=float(metrics.loc[post_t,'sum_open_interest'])
                if a>0 and b>0:
                    oi_flush_logchg=float(np.log(b)-np.log(a)); oi_flush=bool(oi_flush_logchg<0)
        rows.append(dict(flow_id=int(r.flow_id),signal_time=t,side=side,frozen_signed12_atr=float(r.signed12_atr),signal_close=sig,atr14=atr,level=lvl,distance_atr=distance,distance_bin=dist_bin(distance),oi_logchg_3h=oi3,oi_backed=oi_back,touch_time=touch_time,class_time=class_time,state=state,class_price=class_px,residual_atr=resid,oi_flush=oi_flush,oi_flush_logchg=oi_flush_logchg))
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)


def stats(q,label):
    a=pd.to_numeric(q.frozen_signed12_atr,errors='coerce').dropna().to_numpy(float)
    rr=pd.to_numeric(q.residual_atr,errors='coerce').dropna().to_numpy(float)
    return dict(sample=label,n=len(q),full_mean=float(a.mean()) if len(a) else np.nan,full_hit=float((a>0).mean()) if len(a) else np.nan,resid_n=len(rr),resid_mean=float(rr.mean()) if len(rr) else np.nan,resid_hit=float((rr>0).mean()) if len(rr) else np.nan)


def state_summary(d):
    pre=d[d.signal_time<PRE]; rows=[stats(pre,'ALL')]
    for s in ['NO_TOUCH','ACCEPT','REJECT','UNRESOLVED']:rows.append(stats(pre[pre.state==s],s))
    return pd.DataFrame(rows)


def distance_summary(d):
    pre=d[d.signal_time<PRE]; rows=[]
    for b in ['<=0.5','0.5-1','1-2','>2']:
        q=pre[pre.distance_bin==b]; acc=q[q.state=='ACCEPT']
        rows.append(dict(distance_bin=b,n=len(q),touch_rate=float(q.state.isin(['ACCEPT','REJECT','UNRESOLVED']).mean()) if len(q) else np.nan,accept_rate=float((q.state=='ACCEPT').mean()) if len(q) else np.nan,full_mean=float(q.frozen_signed12_atr.mean()) if len(q) else np.nan,accept_n=len(acc),accept_resid=float(acc.residual_atr.mean()) if len(acc) else np.nan))
    return pd.DataFrame(rows)


def oi_summary(d):
    pre=d[(d.signal_time<PRE)&(d.state=='ACCEPT')]; rows=[]
    for v,name in [(True,'OI_BACKED'),(False,'NO_OI_BACKING')]:
        q=pre[pre.oi_backed==v]; rows.append(stats(q,name))
    for v,name in [(True,'OI_FLUSH'),(False,'NO_OI_FLUSH')]:
        q=pre[pre.oi_flush==v]; rows.append(stats(q,name))
    return pd.DataFrame(rows)


def window_summary(d):
    rows=[]
    for w,(aa,bb) in WINS.items():
        a=pd.Timestamp(aa,tz='UTC'); b=pd.Timestamp(bb,tz='UTC'); q=d[(d.signal_time>=a)&(d.signal_time<b)&(d.state=='ACCEPT')]
        x=stats(q,w); x['window']=w; x['long_n']=int((q.side==1).sum()); x['short_n']=int((q.side==-1).sum()); rows.append(x)
    return pd.DataFrame(rows)


def bootstrap_gap(d):
    q=d[(d.signal_time<PRE)&(d.state.isin(['ACCEPT','REJECT']))&d.residual_atr.notna()].copy()
    epoch=pd.Timestamp('1970-01-01',tz='UTC'); q['cluster']=(((q.signal_time-epoch).dt.total_seconds())//(7*86400)).astype('int64')
    groups=[]
    for _,g in q.groupby('cluster'):
        a=g.loc[g.state=='ACCEPT','residual_atr'].to_numpy(float); r=g.loc[g.state=='REJECT','residual_atr'].to_numpy(float)
        groups.append((a.sum(),len(a),r.sum(),len(r)))
    arr=np.asarray(groups,float); rng=np.random.default_rng(SEED); vals=[]; m=len(arr)
    for _ in range(BOOT_N):
        z=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if z[1]>0 and z[3]>0:vals.append(float(z[0]/z[1]-z[2]/z[3]))
    acc=q[q.state=='ACCEPT'].residual_atr.mean(); rej=q[q.state=='REJECT'].residual_atr.mean(); v=np.asarray(vals,float)
    return dict(point=float(acc-rej),n_clusters=m,draws=len(v),ci_lo=float(np.quantile(v,.025)),ci_hi=float(np.quantile(v,.975)))


def parse_liq_zip(content,label):
    z=zipfile.ZipFile(io.BytesIO(content)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:return pd.DataFrame()
    d=pd.read_csv(z.open(names[0])); d.columns=[str(c).strip().lower() for c in d.columns]
    tc=next((c for c in ['time','timestamp','update_time','trade_time'] if c in d.columns),None)
    sc=next((c for c in ['side','s'] if c in d.columns),None)
    pc=next((c for c in ['average_price','avgprice','price','ap'] if c in d.columns),None)
    qc=next((c for c in ['executed_qty','orig_qty','original_quantity','qty','quantity','q'] if c in d.columns),None)
    if tc is None:return pd.DataFrame()
    t=d[tc]; time=ts_from_num(t) if pd.api.types.is_numeric_dtype(t) else pd.to_datetime(t,errors='coerce',utc=True)
    out=pd.DataFrame({'time':time})
    out['side']=d[sc].astype(str).str.upper() if sc else ''
    out['price']=pd.to_numeric(d[pc],errors='coerce') if pc else np.nan
    out['qty']=pd.to_numeric(d[qc],errors='coerce') if qc else np.nan
    out['notional']=out.price*out.qty
    return out.dropna(subset=['time'])


def liquidation_audit(d):
    eligible=d[(d.state=='ACCEPT')&(d.class_time<pd.Timestamp('2024-04-01',tz='UTC'))].copy()
    if eligible.empty:return pd.DataFrame(),dict(files_attempted=0,files_ok=0,events=0,matched_side_share=np.nan,mean_notional=np.nan)
    # deterministic evenly spaced sample of at most 120 accepted events
    ix=np.linspace(0,len(eligible)-1,min(120,len(eligible)),dtype=int); sample=eligible.iloc[np.unique(ix)].copy()
    dates=sorted(set(sample.class_time.dt.strftime('%Y-%m-%d'))); cache={}; man=[]; base='https://data.binance.vision/data/futures/um/daily/liquidationSnapshot/BTCUSDT'
    def one(ds):
        fn=f'BTCUSDT-liquidationSnapshot-{ds}.zip'; url=f'{base}/{fn}'
        try:
            r=requests.get(url,timeout=20)
            if r.status_code==200:return ds,parse_liq_zip(r.content,fn),200
            return ds,pd.DataFrame(),r.status_code
        except Exception:return ds,pd.DataFrame(),'EXC'
    with ThreadPoolExecutor(max_workers=16) as ex:
        fut=[ex.submit(one,ds) for ds in dates]
        for f in as_completed(fut):
            ds,z,s=f.result(); cache[ds]=z; man.append(dict(date=ds,status=s,rows=len(z)))
    pd.DataFrame(man).sort_values('date').to_csv(OUT/'liquidation_snapshot_manifest.csv',index=False)
    rows=[]
    for r in sample.itertuples():
        ds=r.class_time.strftime('%Y-%m-%d'); z=cache.get(ds,pd.DataFrame())
        if z.empty:continue
        a=r.touch_time-pd.Timedelta(minutes=15); b=r.class_time+pd.Timedelta(hours=1); q=z[(z.time>=a)&(z.time<=b)]
        expected='BUY' if int(r.side)>0 else 'SELL'; qm=q[q.side==expected] if 'side' in q else q
        rows.append(dict(flow_id=int(r.flow_id),signal_time=r.signal_time,side=int(r.side),touch_time=r.touch_time,class_time=r.class_time,liq_n=len(q),matched_n=len(qm),matched_share=float(len(qm)/len(q)) if len(q) else np.nan,matched_notional=float(qm.notional.sum(skipna=True)) if len(qm) else 0.0))
    out=pd.DataFrame(rows); out.to_csv(OUT/'direct_liquidation_audit.csv',index=False)
    man_df=pd.DataFrame(man); ok=int((man_df.status.astype(str)=='200').sum()) if len(man_df) else 0
    meta=dict(files_attempted=len(dates),files_ok=ok,events=len(out),matched_side_share=float(out.matched_n.sum()/out.liq_n.sum()) if len(out) and out.liq_n.sum()>0 else np.nan,mean_notional=float(out.matched_notional.mean()) if len(out) else np.nan)
    return out,meta


def main():
    flow,metrics,fut=load_inputs(); d=build_events(flow,metrics,fut); d.to_csv(OUT/'activation_stream.csv',index=False)
    pre=d[d.signal_time<PRE]; st=state_summary(d); ds=distance_summary(d); oi=oi_summary(d); ws=window_summary(d); boot=bootstrap_gap(d)
    st.to_csv(OUT/'state_summary.csv',index=False); ds.to_csv(OUT/'distance_map.csv',index=False); oi.to_csv(OUT/'oi_map.csv',index=False); ws.to_csv(OUT/'window_summary.csv',index=False)
    liq,liqmeta=liquidation_audit(d)
    baseline=float(pre.frozen_signed12_atr.mean()); acc=pre[pre.state=='ACCEPT']; rej=pre[pre.state=='REJECT']
    oib=acc[acc.oi_backed]; noin=acc[~acc.oi_backed]
    y22=acc[(acc.signal_time>=pd.Timestamp('2022-01-01',tz='UTC'))&(acc.signal_time<pd.Timestamp('2023-01-01',tz='UTC'))&(acc.side==-1)]
    recent=acc[(acc.signal_time>=pd.Timestamp('2025-07-01',tz='UTC'))]
    near=ds[ds.distance_bin=='<=0.5'].iloc[0]; far=ds[ds.distance_bin=='>2'].iloc[0]
    cov_fut=len(pre)/max(1,len(flow[flow.signal_time<PRE])); metric_n=int(pre.oi_logchg_3h.notna().sum()); cov_oi=metric_n/max(1,len(pre))
    gates={
      'frozen_flow_lineage_n_ge_3200':len(flow)>=3200,
      'futures_coverage_ge_99pct':cov_fut>=.99,
      'oi_metrics_coverage_ge_90pct':cov_oi>=.90,
      'touch_n_ge_500':int(pre.state.isin(['ACCEPT','REJECT','UNRESOLVED']).sum())>=500,
      'accept_n_ge_200':len(acc)>=200,
      'accept_residual_positive':len(acc)>0 and float(acc.residual_atr.mean())>0,
      'accept_minus_reject_residual_ge_0_20':len(rej)>0 and float(acc.residual_atr.mean()-rej.residual_atr.mean())>=.20,
      'cluster_boot_ci_lower_gt_zero':boot['ci_lo']>0,
      'accept_full_mean_beats_baseline_0_15':len(acc)>0 and float(acc.frozen_signed12_atr.mean()-baseline)>=.15,
      'oi_backed_accept_beats_no_oi_0_15':len(oib)>0 and len(noin)>0 and float(oib.frozen_signed12_atr.mean()-noin.frozen_signed12_atr.mean())>=.15,
      'stress_2022_short_accept_resid_positive_n30':len(y22)>=30 and float(y22.residual_atr.mean())>0,
      'recent_accept_resid_positive_n50':len(recent)>=50 and float(recent.residual_atr.mean())>0,
      'near_touch_rate_gt_far':np.isfinite(near.touch_rate) and np.isfinite(far.touch_rate) and near.touch_rate>far.touch_rate,
    }
    score=sum(gates.values()); critical=['frozen_flow_lineage_n_ge_3200','futures_coverage_ge_99pct','accept_n_ge_200','accept_residual_positive','cluster_boot_ci_lower_gt_zero','recent_accept_resid_positive_n50']
    if score>=10 and all(gates[k] for k in critical): verdict='PASS_FLOW_LEVEL_BREAK_ACCEPTANCE_ACTIVATION'
    elif gates['accept_residual_positive'] and (boot['point']>0 or gates['accept_full_mean_beats_baseline_0_15']): verdict='WATCH_LEVEL_ACCEPTANCE_DIRECTIONALLY_USEFUL_TRANSFER_INCOMPLETE'
    else: verdict='FAIL_NO_FORCED_LIQUIDITY_LEVEL_ACCEPTANCE_EDGE'
    meta=dict(verdict=verdict,flow_n=len(flow),event_n=len(d),pre_n=len(pre),baseline_full_mean=baseline,futures_cov=cov_fut,oi_cov=cov_oi,accept_n=len(acc),reject_n=len(rej),touch_n=int(pre.state.isin(['ACCEPT','REJECT','UNRESOLVED']).sum()),accept_full_mean=float(acc.frozen_signed12_atr.mean()) if len(acc) else np.nan,accept_resid_mean=float(acc.residual_atr.mean()) if len(acc) else np.nan,reject_resid_mean=float(rej.residual_atr.mean()) if len(rej) else np.nan,boot=boot,liq=liqmeta)
    (OUT/'verdict.json').write_text(json.dumps({'meta':meta,'gates':gates},indent=2,default=lambda x: bool(x) if isinstance(x,np.bool_) else (float(x) if isinstance(x,(np.floating,)) else int(x) if isinstance(x,(np.integer,)) else str(x))),encoding='utf-8')
    def f(x):
        if pd.isna(x):return '—'
        return f'{x:.3f}'
    lines=[f'# {LAB}','',f'**Verdict: {verdict} — {score}/{len(gates)}**','',
      '## Core',f'- frozen flow: **{len(flow)}**, classified pre-Aug: **{len(pre)}**',f'- baseline full 12h mean: **{f(baseline)} ATR**',f'- TOUCH: **{meta["touch_n"]}**, ACCEPT: **{len(acc)}**, REJECT: **{len(rej)}**',f'- ACCEPT full mean: **{f(meta["accept_full_mean"])} ATR**',f'- ACCEPT residual after break: **{f(meta["accept_resid_mean"])} ATR**',f'- REJECT residual after classification: **{f(meta["reject_resid_mean"])} ATR**',f'- ACCEPT-REJECT residual gap: **{f(boot["point"])} ATR**, 7d bootstrap 95% CI **[{f(boot["ci_lo"])}, {f(boot["ci_hi"])}]**','',
      '## Distance map','', '| Distance | N | Touch | Accept | Full mean | Accept N | Accept residual |','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in ds.iterrows():lines.append(f'| {r.distance_bin} | {int(r.n)} | {f(r.touch_rate)} | {f(r.accept_rate)} | {f(r.full_mean)} | {int(r.accept_n)} | {f(r.accept_resid)} |')
    lines+=['','## ACCEPT by window','', '| Window | N | Full mean | Residual | Hit residual | L/S |','|---|---:|---:|---:|---:|---:|']
    for _,r in ws.iterrows():lines.append(f'| {r.window} | {int(r.n)} | {f(r.full_mean)} | {f(r.resid_mean)} | {f(r.resid_hit)} | {int(r.long_n)}/{int(r.short_n)} |')
    lines+=['','## OI interaction','', '| Slice | N | Full mean | Residual |','|---|---:|---:|---:|']
    for _,r in oi.iterrows():lines.append(f'| {r["sample"]} | {int(r.n)} | {f(r.full_mean)} | {f(r.resid_mean)} |')
    lines+=['','## Direct liquidation archive audit',f'- files attempted: **{liqmeta["files_attempted"]}**, available: **{liqmeta["files_ok"]}**, event windows parsed: **{liqmeta["events"]}**',f'- matched forced-side share: **{f(liqmeta["matched_side_share"])}**', 'This audit is validation-only because Binance USD-M liquidationSnapshot coverage was discontinued/removed.','', '## Gates']
    for k,v in gates.items():lines.append(f'- {"PASS" if v else "FAIL"} — `{k}`')
    lines+=['','## Guardrail','The level is a frozen 12h directional extreme with OI backing only as an interaction label. It is not claimed to be the true liquidation price. No level/lookback/acceptance/stop/TP optimization was performed. August 2026 is reused audit only. Live allocation = **0**.']
    rep='\n'.join(lines)+'\n'; (OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__': main()
