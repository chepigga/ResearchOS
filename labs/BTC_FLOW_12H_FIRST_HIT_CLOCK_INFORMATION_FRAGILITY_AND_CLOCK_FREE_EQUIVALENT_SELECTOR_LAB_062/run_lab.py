#!/usr/bin/env python3
from __future__ import annotations

import io, json, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

LAB = "BTC_FLOW_12H_FIRST_HIT_CLOCK_INFORMATION_FRAGILITY_AND_CLOCK_FREE_EQUIVALENT_SELECTOR_LAB_062"
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"; OUT.mkdir(parents=True, exist_ok=True)
LABS = HERE.parent
SRC22 = LABS / "BTC_BINANCE_RETAIL_FLOW_DIRECTION_X_H4_PIVOT_M15_PRICE_TIMING_LAB_022" / "output" / "flow_only_nonoverlap.csv"
SRC41 = LABS / "BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041" / "output" / "all_touch_elasticity_stream.csv"
SRC43 = LABS / "BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043" / "output" / "short_response_router_stream.csv"

FLOW_LOOKBACK = pd.Timedelta(days=90); EVENT_LOOKBACK = pd.Timedelta(days=90)
FLOW_MIN_N=1000; EVENT_MIN_N=40; COOLDOWN=pd.Timedelta(hours=12)
LEVEL_BARS=48; ACCEPT_BARS=4; STOP_ATR=2.5; TP_R=1.5
RISK_PCT=.25; PRIMARY_BPS=5.0; STRESS_BPS=10.0
FRAGILITY_HORIZON=pd.Timedelta(hours=72)
SESSION=requests.Session(); SESSION.headers.update({"User-Agent":"ResearchOS-LAB062/1.0"})


def j(x):
    if x is None: return None
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(float,np.floating)): return None if not np.isfinite(float(x)) else float(x)
    if isinstance(x,pd.Timestamp): return x.isoformat()
    if isinstance(x,dict): return {str(k):j(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [j(v) for v in x]
    return x

def qstats(v):
    a=pd.to_numeric(pd.Series(v),errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
    if not len(a): return {'n':0}
    return {'n':int(len(a)),'min':float(a.min()),'p05':float(a.quantile(.05)),'p50':float(a.quantile(.5)),'p95':float(a.quantile(.95)),'max':float(a.max()),'mean':float(a.mean())}

def ts_num(s):
    v=pd.to_numeric(s,errors='coerce'); med=v.dropna().abs().median() if v.notna().any() else np.nan
    unit='us' if pd.notna(med) and med>1e14 else ('ms' if pd.notna(med) and med>1e11 else 's')
    return pd.to_datetime(v,unit=unit,errors='coerce',utc=True)

def parse_metric_zip(content):
    z=zipfile.ZipFile(io.BytesIO(content)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:return pd.DataFrame()
    d=pd.read_csv(z.open(names[0])); d.columns=[str(c).strip() for c in d.columns]
    tc='create_time' if 'create_time' in d.columns else ('timestamp' if 'timestamp' in d.columns else None)
    if tc is None or 'count_long_short_ratio' not in d.columns:return pd.DataFrame()
    t=d[tc]; time=ts_num(t) if pd.api.types.is_numeric_dtype(t) else pd.to_datetime(t.astype(str).str.strip(),errors='coerce',utc=True)
    return pd.DataFrame({'time':time,'ratio':pd.to_numeric(d['count_long_short_ratio'],errors='coerce')}).dropna()

def parse_kline_zip(content):
    z=zipfile.ZipFile(io.BytesIO(content)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:return pd.DataFrame()
    d=pd.read_csv(z.open(names[0]),header=None)
    if d.shape[1]<11:return pd.DataFrame()
    x=pd.DataFrame({'time':ts_num(d.iloc[:,0]),'open':pd.to_numeric(d.iloc[:,1],errors='coerce'),'high':pd.to_numeric(d.iloc[:,2],errors='coerce'),'low':pd.to_numeric(d.iloc[:,3],errors='coerce'),'close':pd.to_numeric(d.iloc[:,4],errors='coerce'),'quote':pd.to_numeric(d.iloc[:,7],errors='coerce'),'taker_buy_quote':pd.to_numeric(d.iloc[:,10],errors='coerce')})
    return x.dropna()

def get(url, parser, timeout=30):
    try:
        r=SESSION.get(url,timeout=timeout)
        if r.status_code!=200:return None,r.status_code
        return parser(r.content),200
    except Exception as e:return None,type(e).__name__


def load_sources():
    f22=pd.read_csv(SRC22); f22['signal_time']=pd.to_datetime(f22.signal_time,utc=True,errors='coerce'); f22['side']=pd.to_numeric(f22.side,errors='coerce').astype('Int64')
    f22=f22.dropna(subset=['signal_time','side']).sort_values('signal_time')
    h41=pd.read_csv(SRC41,usecols=lambda c:c in {'signal_time','response_60','pressure_mag_60','fut_elasticity_60','side','state'})
    h41['signal_time']=pd.to_datetime(h41.signal_time,utc=True,errors='coerce'); h41['response_60']=pd.to_numeric(h41.response_60,errors='coerce')
    h41=h41.dropna(subset=['signal_time','response_60']).sort_values('signal_time')
    r43=pd.read_csv(SRC43,usecols=lambda c:c in {'signal_time','side','state','response_router'})
    r43['signal_time']=pd.to_datetime(r43.signal_time,utc=True,errors='coerce'); r43['side']=pd.to_numeric(r43.side,errors='coerce')
    r43=r43.dropna(subset=['signal_time','side']).sort_values('signal_time')
    return f22,h41,r43


def download_metrics(start,end):
    days=list(pd.date_range(start.normalize(),end.normalize(),freq='D')); base='https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT'
    parts=[]; man=[]
    def one(t):
        ds=t.strftime('%Y-%m-%d'); fn=f'BTCUSDT-metrics-{ds}.zip'; d,s=get(f'{base}/{fn}',parse_metric_zip); return d,{'date':ds,'status':s,'rows':0 if d is None else len(d)}
    with ThreadPoolExecutor(max_workers=40) as ex:
        fs=[ex.submit(one,t) for t in days]
        for f in as_completed(fs):
            d,m=f.result(); man.append(m)
            if d is not None and len(d):parts.append(d)
    pd.DataFrame(man).sort_values('date').to_csv(OUT/'metrics_manifest.csv',index=False)
    if not parts: raise RuntimeError('No metrics')
    raw=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last')
    m=raw.set_index('time').ratio.resample('15min',label='left',closed='left').last().ffill(limit=2).dropna().to_frame('ratio')
    m['delta_ls_12']=m.ratio-m.ratio.shift(12)
    prior=m.delta_ls_12.shift(1)
    m['q20']=prior.rolling('90D',min_periods=FLOW_MIN_N).quantile(.20); m['q80']=prior.rolling('90D',min_periods=FLOW_MIN_N).quantile(.80)
    side=np.zeros(len(m),dtype=np.int8); valid=m[['delta_ls_12','q20','q80']].notna().all(axis=1).to_numpy()
    dv=m.delta_ls_12.to_numpy(float); q20=m.q20.to_numpy(float); q80=m.q80.to_numpy(float)
    side[valid & (dv<=q20)]=1; side[valid & (dv>=q80)]=-1; m['side']=side
    return m


def download_futures(start,end):
    months=list(pd.period_range(start.to_period('M'),end.to_period('M'),freq='M')); parts=[]; man=[]
    base='https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m'
    def one(p):
        ym=f'{p.year}-{p.month:02d}'; fn=f'BTCUSDT-15m-{ym}.zip'; d,s=get(f'{base}/{fn}',parse_kline_zip,45); return d,{'month':ym,'status':s,'rows':0 if d is None else len(d)}
    with ThreadPoolExecutor(max_workers=16) as ex:
        fs=[ex.submit(one,p) for p in months]
        for f in as_completed(fs):
            d,m=f.result(); man.append(m)
            if d is not None and len(d):parts.append(d)
    pd.DataFrame(man).sort_values('month').to_csv(OUT/'futures_manifest.csv',index=False)
    if not parts: raise RuntimeError('No futures')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').set_index('time')
    x=x[(x.index>=start)&(x.index<=end+pd.Timedelta(hours=12))]
    pc=x.close.shift(1); tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr14']=tr.rolling(14,min_periods=14).mean(); x['prior12_low']=x.low.shift(1).rolling(LEVEL_BARS,min_periods=LEVEL_BARS).min()
    delta=2*x.taker_buy_quote-x.quote; ds=delta.rolling(4,min_periods=4).sum().shift(1)
    x['netdelta60_raw']=ds; x['netdelta60_medabs']=ds.abs().shift(1).rolling(90*96,min_periods=30*96).median(); x['disp60_px']=x.close.shift(1)-x.close.shift(5)
    return x


def eligible_signal(t,fut):
    return t in fut.index and t+pd.Timedelta(hours=12) in fut.index and np.isfinite(float(fut.at[t,'atr14'])) and float(fut.at[t,'atr14'])>0

def build_frozen_flow(m,fut,scan_start,scan_end):
    rows=[]; last=None
    z=m[(m.index>=scan_start)&(m.index<=scan_end)]
    for t,r in z.iterrows():
        s=int(r.side)
        if s==0: continue
        if last is not None and t-last<COOLDOWN: continue
        if not eligible_signal(t,fut): continue
        rows.append({'signal_time':t,'side':s}); last=t
    return pd.DataFrame(rows)

def build_onsets(m,fut,scan_start,scan_end):
    z=m[(m.index>=scan_start-pd.Timedelta(minutes=15))&(m.index<=scan_end)].copy(); prev=z.side.shift(1)
    mask=(z.side==-1)&(prev!=-1)
    times=z.index[mask]
    return pd.DataFrame([{'signal_time':t,'side':-1} for t in times if t>=scan_start and eligible_signal(t,fut)])

def build_all_short(m,fut,scan_start,scan_end):
    z=m[(m.index>=scan_start)&(m.index<=scan_end)&(m.side==-1)]
    return pd.DataFrame([{'signal_time':t,'side':-1} for t in z.index if eligible_signal(t,fut)])


def activation(cands,fut):
    if cands.empty:return pd.DataFrame()
    idx=fut.index; rows=[]
    for fid,r in enumerate(cands.itertuples(index=False)):
        t=pd.Timestamp(r.signal_time); loc=idx.get_indexer([t])[0]
        if loc<0:continue
        horizon=t+pd.Timedelta(hours=12); hi=idx.get_indexer([horizon])[0]
        if hi<0:continue
        atr=float(fut.iloc[loc].atr14); level=float(fut.iloc[loc].prior12_low); sig=float(fut.iloc[loc].close)
        if not(np.isfinite(atr) and atr>0 and np.isfinite(level)):continue
        touch_i=None
        end=min(hi,loc+48)
        lows=fut.low.iloc[loc:end+1].to_numpy(float)
        hits=np.flatnonzero(lows<=level)
        if len(hits):touch_i=loc+int(hits[0])
        state='NO_TOUCH'; ct=pd.NaT; cp=np.nan; touch=pd.NaT; response=np.nan
        if touch_i is not None:
            touch=idx[touch_i]; e=min(touch_i+ACCEPT_BARS,end+1); closes=fut.close.iloc[touch_i:e].to_numpy(float)
            acc=np.flatnonzero(closes<=level)
            if len(acc):
                ai=touch_i+int(acc[0]); state='ACCEPT'; ct=idx[ai]; cp=float(fut.close.iloc[ai])
            elif e-touch_i>=ACCEPT_BARS:
                ai=e-1; state='REJECT'; ct=idx[ai]; cp=float(fut.close.iloc[ai])
            else:
                state='UNRESOLVED'
            if state in ('ACCEPT','REJECT'):
                disp=float(fut.iloc[touch_i].disp60_px)
                if np.isfinite(disp): response=-disp/atr
        rows.append({'flow_id':fid,'signal_time':t,'side':-1,'signal_close':sig,'atr14':atr,'level':level,'touch_time':touch,'class_time':ct,'class_price':cp,'state':state,'response_60':response})
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)


def classify_frozen_router(a,h41):
    z=a.copy(); z['response_med90']=np.nan; z['prior_n']=0; z['response_router']='UNRESOLVED'
    ht=h41.signal_time.to_numpy(dtype='datetime64[ns]'); hv=h41.response_60.to_numpy(float)
    for i,r in z.iterrows():
        if not np.isfinite(r.response_60):continue
        t=pd.Timestamp(r.signal_time); lo=np.searchsorted(ht,np.datetime64((t-EVENT_LOOKBACK).tz_localize(None)),'left'); hi=np.searchsorted(ht,np.datetime64(t.tz_localize(None)),'left')
        vals=hv[lo:hi]; vals=vals[np.isfinite(vals)]; z.at[i,'prior_n']=len(vals)
        if len(vals)<EVENT_MIN_N:continue
        med=float(np.median(vals)); z.at[i,'response_med90']=med; z.at[i,'response_router']='HIGH_RESPONSE' if float(r.response_60)>med else 'LOW_RESPONSE'
    return z

def classify_native_router(a):
    z=a.copy(); z['response_med90']=np.nan; z['prior_n']=0; z['response_router']='UNRESOLVED'
    hist_t=[]; hist_v=[]
    for i,r in z.sort_values('signal_time').iterrows():
        t=pd.Timestamp(r.signal_time)
        if np.isfinite(r.response_60):
            vals=[v for tt,v in zip(hist_t,hist_v) if tt>=t-EVENT_LOOKBACK]
            z.at[i,'prior_n']=len(vals)
            if len(vals)>=EVENT_MIN_N:
                med=float(np.median(vals)); z.at[i,'response_med90']=med; z.at[i,'response_router']='HIGH_RESPONSE' if float(r.response_60)>med else 'LOW_RESPONSE'
            hist_t.append(t); hist_v.append(float(r.response_60))
            # keep only relevant history periodically
            if len(hist_t)>5000:
                keep=[k for k,tt in enumerate(hist_t) if tt>=t-EVENT_LOOKBACK]
                hist_t=[hist_t[k] for k in keep]; hist_v=[hist_v[k] for k in keep]
    return z


def first_passage(path,entry,D):
    fav=entry-.5*D; adv=entry+.5*D
    for tt,b in path.iterrows():
        if float(b.high)>=adv:return 'ADVERSE_FIRST',tt
        if float(b.low)<=fav:return 'FAVORABLE_FIRST',tt
    return 'NONE_120',pd.NaT

def net_r(entry,exitpx,D,bps):return float((entry-exitpx)/D-(bps/10000.0)*entry/D)
def simulate(r,fut):
    t=pd.Timestamp(r.signal_time); base={'signal_time':t,'entry_time':pd.NaT,'exit_time':pd.NaT,'traded':False,'exit_reason':'NO_TRADE','net_r_5bps':0.0,'net_r_10bps':0.0}
    if r.response_router!='HIGH_RESPONSE' or r.state!='ACCEPT' or pd.isna(r.class_time) or not np.isfinite(r.class_price):return base
    et=pd.Timestamp(r.class_time); ep=float(r.class_price); D=STOP_ATR*float(r.atr14); lvl=float(r.level); horizon=t+pd.Timedelta(hours=12)
    if et not in fut.index or horizon not in fut.index:return base
    p=fut[(fut.index>et)&(fut.index<=horizon)]; stop=ep+D; tp=ep-TP_R*D; reason='TIME'; xt=horizon; xp=float(fut.at[horizon,'close'])
    for tt,b in p.iterrows():
        if float(b.high)>=stop:reason='SL';xt=tt;xp=stop;break
        if float(b.low)<=tp:reason='TP';xt=tt;xp=tp;break
    parent_xt=xt; parent_reason=reason
    end120=min(et+pd.Timedelta(minutes=120),parent_xt); fps,fpt=first_passage(fut[(fut.index>et)&(fut.index<=end120)],ep,D)
    persistent=False
    if fps=='ADVERSE_FIRST':
        include_end=parent_reason=='TIME'; pc=fut[(fut.index>fpt)&((fut.index<=parent_xt) if include_end else (fut.index<parent_xt))]; consec=0
        for tt,b in pc.iterrows():
            c=float(b.close)
            if c<=ep:break
            if c>lvl:
                consec+=1
                if consec>=2:xt=tt;xp=c;reason='PERSISTENT_FAILURE_EXIT';persistent=True;break
            else:consec=0
    return {'signal_time':t,'entry_time':et,'exit_time':xt,'traded':True,'exit_reason':reason,'parent_exit_reason':parent_reason,'fp_state':fps,'persistent_exit':persistent,'net_r_5bps':net_r(ep,xp,D,PRIMARY_BPS),'net_r_10bps':net_r(ep,xp,D,STRESS_BPS)}

def pf(v):
    a=np.asarray(v,float); gp=a[a>0].sum(); gl=-a[a<0].sum(); return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)
def maxdd(v):
    a=np.asarray(v,float); c=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,c]); dd=peak[1:]-c; return float(dd.max()) if len(dd) else 0.0

def max_concurrency(t):
    if t.empty:return 0
    ev=[]
    for r in t.itertuples(index=False):ev.append((pd.Timestamp(r.entry_time),1));ev.append((pd.Timestamp(r.exit_time),-1))
    ev.sort(key=lambda x:(x[0],x[1])) # exits before entries at same timestamp
    cur=mx=0
    for _,d in ev:cur+=d;mx=max(mx,cur)
    return int(mx)

def summarize(name,a,ex,start,end):
    ax=a[(a.signal_time>=start)&(a.signal_time<=end)].copy(); x=ex[(ex.signal_time>=start)&(ex.signal_time<=end)&(ex.traded==True)].copy().sort_values('entry_time')
    r5=x.net_r_5bps.to_numpy(float) if len(x) else np.array([]); r10=x.net_r_10bps.to_numpy(float) if len(x) else np.array([])
    weeks=max((end-start).total_seconds()/604800.0,1e-9)
    gaps=x.entry_time.diff().dt.total_seconds()/3600 if len(x) else pd.Series(dtype=float)
    return {'selector':name,'start':start,'end':end,'candidate_n':int(len(ax)),'touch_n':int(ax.touch_time.notna().sum()),'high_response_n':int((ax.response_router=='HIGH_RESPONSE').sum()),'accept_trade_n':int(len(x)),'trades_per_week':float(len(x)/weeks),'ev_5bps':float(r5.mean()) if len(r5) else np.nan,'pf_5bps':pf(r5),'ev_10bps':float(r10.mean()) if len(r10) else np.nan,'pf_10bps':pf(r10),'cum_r_5bps':float(r5.sum()) if len(r5) else 0.0,'maxdd_r_5bps':maxdd(r5),'dd_pct_025':maxdd(r5)*RISK_PCT,'win_rate_5bps':float((r5>0).mean()) if len(r5) else np.nan,'max_concurrent':max_concurrency(x),'trade_gap_lt12h_share':float((gaps<12).mean()) if gaps.notna().any() else 0.0,'tp_n':int((x.exit_reason=='TP').sum()),'sl_n':int((x.exit_reason=='SL').sum()),'persistent_n':int((x.exit_reason=='PERSISTENT_FAILURE_EXIT').sum()),'time_n':int((x.exit_reason=='TIME').sum())}

def yearly(name,ex,start,end):
    x=ex[(ex.signal_time>=start)&(ex.signal_time<=end)&(ex.traded==True)].copy(); rows=[]
    for y,g in x.groupby(x.signal_time.dt.year):
        r=g.net_r_5bps.to_numpy(float); rows.append({'selector':name,'year':int(y),'n':len(g),'ev5':float(r.mean()),'pf5':pf(r),'cumR':float(r.sum())})
    return pd.DataFrame(rows)


def event_set(d):return set(zip(pd.to_datetime(d.signal_time,utc=True).astype(str),pd.to_numeric(d.side,errors='coerce').astype(int)))
def union_match(a,b):
    A=event_set(a);B=event_set(b);U=A|B;return {'a_n':len(A),'b_n':len(B),'intersection_n':len(A&B),'union_n':len(U),'union_match':1.0 if not U else len(A&B)/len(U)}


def fragility(m,baseline,scan_start,scan_end):
    idx=m.index; sides=m.side.to_numpy(np.int8); pos={t:i for i,t in enumerate(idx)}; rows=[]
    bev=[(pd.Timestamp(r.signal_time),int(r.side)) for r in baseline.itertuples(index=False)]
    event_times=[t for t,_ in bev]
    for k,(e,es) in enumerate(bev):
        if e<scan_start or e>scan_end or e not in pos:continue
        prev=event_times[k-1] if k>0 else None; eend=min(e+FRAGILITY_HORIZON,scan_end)
        i0=pos[e]; i1=idx.searchsorted(eend,side='right')
        bl=[]; al=[]; last_b=prev; last_a=prev; diverged=False; resync=None
        for ii in range(i0,i1):
            t=idx[ii]; s=int(sides[ii]); sa=0 if ii==i0 else s
            if s!=0 and (last_b is None or t-last_b>=COOLDOWN) and eligible_signal(t,FUT_GLOBAL):bl.append((t,s));last_b=t
            if sa!=0 and (last_a is None or t-last_a>=COOLDOWN) and eligible_signal(t,FUT_GLOBAL):al.append((t,sa));last_a=t
            if last_b!=last_a:diverged=True
            elif diverged and resync is None:resync=(t-e).total_seconds()/3600.0
        A=set(bl);B=set(al); changed=len(A^B)
        rows.append({'deleted_event_time':e,'deleted_side':es,'changed_event_count_72h':changed,'changes_ge1':changed>=1,'changes_ge2':changed>=2,'resync_hours':resync})
    return pd.DataFrame(rows)

FUT_GLOBAL=None

def main():
    global FUT_GLOBAL
    f22,h41,r43=load_sources()
    src_start=f22.signal_time.min(); src_end=f22.signal_time.max(); raw_start=src_start-FLOW_LOOKBACK-pd.Timedelta(days=5); fut_start=raw_start-pd.Timedelta(days=35); fut_end=src_end+pd.Timedelta(hours=12)
    print('source',src_start,src_end,'downloading metrics',raw_start,src_end)
    m=download_metrics(raw_start,src_end); print('metrics rows',len(m))
    fut=download_futures(fut_start,fut_end); FUT_GLOBAL=fut; print('futures rows',len(fut))
    scan_start=max(src_start,m.index.min()+FLOW_LOOKBACK); scan_end=min(src_end,fut.index.max()-pd.Timedelta(hours=12))

    base_all=build_frozen_flow(m,fut,scan_start-pd.Timedelta(hours=24),scan_end)
    base_all=base_all[base_all.signal_time>=scan_start].reset_index(drop=True)
    persisted=f22[(f22.signal_time>=scan_start)&(f22.signal_time<=scan_end)][['signal_time','side']].copy()
    parity=union_match(persisted,base_all)

    base_short=base_all[base_all.side==-1].copy(); onset=build_onsets(m,fut,scan_start,scan_end); allshort=build_all_short(m,fut,scan_start,scan_end)
    print('candidates baseline/onset/allshort',len(base_short),len(onset),len(allshort),'parity',parity)

    a_base=activation(base_short,fut); a_on=activation(onset,fut); a_all=activation(allshort,fut)
    a_base=classify_frozen_router(a_base,h41); a_on_fr=classify_frozen_router(a_on,h41); a_on_nat=classify_native_router(a_on.copy()); a_all=classify_frozen_router(a_all,h41)

    # Router parity against persisted SHORT router where timestamps overlap.
    cmp=a_base[['signal_time','state','response_router']].merge(r43[r43.side==-1][['signal_time','state','response_router']],on='signal_time',suffixes=('_new','_persisted'))
    router_match=float(((cmp.state_new.astype(str)==cmp.state_persisted.astype(str))&(cmp.response_router_new.astype(str)==cmp.response_router_persisted.astype(str))).mean()) if len(cmp) else np.nan
    parity['router_overlap_n']=int(len(cmp)); parity['router_state_match']=router_match
    (OUT/'baseline_parity.json').write_text(json.dumps(j(parity),indent=2))

    ex_base=pd.DataFrame([simulate(r,fut) for r in a_base.itertuples(index=False)]); ex_fr=pd.DataFrame([simulate(r,fut) for r in a_on_fr.itertuples(index=False)]); ex_nat=pd.DataFrame([simulate(r,fut) for r in a_on_nat.itertuples(index=False)]); ex_all=pd.DataFrame([simulate(r,fut) for r in a_all.itertuples(index=False)])
    for name,a,ex in [('FROZEN_FIRST_HIT_12H',a_base,ex_base),('SHORT_RUN_ONSET_FROZEN_ROUTER',a_on_fr,ex_fr),('SHORT_RUN_ONSET_NATIVE_ROUTER',a_on_nat,ex_nat),('ALL_SHORT_STATE_DIAGNOSTIC',a_all,ex_all)]:
        a.to_csv(OUT/f'{name.lower()}_activation.csv',index=False); ex.to_csv(OUT/f'{name.lower()}_execution.csv',index=False)

    full_start=scan_start; full_end=scan_end; hist_end=min(pd.Timestamp('2024-12-31 23:59:59',tz='UTC'),full_end); conf_start=max(pd.Timestamp('2025-01-01',tz='UTC'),full_start)
    summaries=[]; yr=[]
    sels=[('FROZEN_FIRST_HIT_12H',a_base,ex_base),('SHORT_RUN_ONSET_FROZEN_ROUTER',a_on_fr,ex_fr),('SHORT_RUN_ONSET_NATIVE_ROUTER',a_on_nat,ex_nat),('ALL_SHORT_STATE_DIAGNOSTIC',a_all,ex_all)]
    for name,a,ex in sels:
        summaries.append({**summarize(name,a,ex,full_start,full_end),'slice':'FULL'})
        if hist_end>=full_start:summaries.append({**summarize(name,a,ex,full_start,hist_end),'slice':'2021_2024'})
        if full_end>=conf_start:summaries.append({**summarize(name,a,ex,conf_start,full_end),'slice':'2025_PLUS_REUSED'})
        y=yearly(name,ex,full_start,full_end);yr.append(y)
    sm=pd.DataFrame(summaries); sm.to_csv(OUT/'summary.csv',index=False); ydf=pd.concat(yr,ignore_index=True); ydf.to_csv(OUT/'yearly.csv',index=False)

    frag=fragility(m,base_all,scan_start,scan_end); frag.to_csv(OUT/'first_hit_single_state_deletion_fragility.csv',index=False)
    fragmetrics={'n':int(len(frag)),'alter_ge1_share':float(frag.changes_ge1.mean()) if len(frag) else np.nan,'alter_ge2_share':float(frag.changes_ge2.mean()) if len(frag) else np.nan,'changed_event_count_72h':qstats(frag.changed_event_count_72h if len(frag) else []),'resync_hours':qstats(frag.resync_hours if len(frag) else [])}

    def row(sel,sl):
        q=sm[(sm.selector==sel)&(sm['slice']==sl)];return None if q.empty else q.iloc[0]
    rb=row('FROZEN_FIRST_HIT_12H','2025_PLUS_REUSED'); rf=row('SHORT_RUN_ONSET_FROZEN_ROUTER','2025_PLUS_REUSED'); rn=row('SHORT_RUN_ONSET_NATIVE_ROUTER','2025_PLUS_REUSED')
    yfull=ydf.groupby('selector').apply(lambda g: float((g.ev5>0).mean()) if len(g) else np.nan,include_groups=False).to_dict()
    baseline_ok=parity['union_match']>=.995 and (pd.isna(router_match) or router_match>=.995)
    enough=rf is not None and int(rf.accept_trade_n)>=30
    b_ratio=(float(rf.ev_5bps)/float(rb.ev_5bps)) if rb is not None and np.isfinite(rb.ev_5bps) and rb.ev_5bps>0 else np.nan
    n_ratio=(float(rn.ev_5bps)/float(rb.ev_5bps)) if rn is not None and rb is not None and np.isfinite(rb.ev_5bps) and rb.ev_5bps>0 else np.nan
    b_gates={'n_ge30':bool(rf is not None and rf.accept_trade_n>=30),'ev5_gt0':bool(rf is not None and rf.ev_5bps>0),'pf5_ge1_20':bool(rf is not None and rf.pf_5bps>=1.20),'ev10_gt0':bool(rf is not None and rf.ev_10bps>0),'dd025_le4':bool(rf is not None and rf.dd_pct_025<=4),'ev5_ge70pct_baseline':bool(np.isfinite(b_ratio) and b_ratio>=.70),'positive_year_share_ge60':bool(yfull.get('SHORT_RUN_ONSET_FROZEN_ROUTER',0)>=.60),'max_concurrent_le4':bool(rf is not None and rf.max_concurrent<=4)}
    n_gates={'n_ge30':bool(rn is not None and rn.accept_trade_n>=30),'ev5_gt0':bool(rn is not None and rn.ev_5bps>0),'pf5_ge1_20':bool(rn is not None and rn.pf_5bps>=1.20),'ev10_gt0':bool(rn is not None and rn.ev_10bps>0),'dd025_le4':bool(rn is not None and rn.dd_pct_025<=4),'ev5_ge60pct_baseline':bool(np.isfinite(n_ratio) and n_ratio>=.60),'positive_year_share_ge60':bool(yfull.get('SHORT_RUN_ONSET_NATIVE_ROUTER',0)>=.60),'max_concurrent_le4':bool(rn is not None and rn.max_concurrent<=4)}
    if not baseline_ok:verdict='FAIL_BASELINE_REPLICATION'
    elif not enough:verdict='INSUFFICIENT_DATA'
    elif all(b_gates.values()) and all(n_gates.values()):verdict='CLOCK_FREE_NATIVE_SUPPORTED'
    elif all(b_gates.values()):verdict='CLOCK_FREE_EQUIVALENT_SUPPORTED'
    elif rf.ev_5bps<=0 or rf.pf_5bps<1 or rf.dd_pct_025>4:verdict='CLOCK_IS_ECONOMICALLY_MATERIAL'
    else:verdict='WATCH_CLOCK_FREE_PROMISING_NOT_EQUIVALENT'

    metrics={'lab':LAB,'source_range':[src_start,src_end],'formal_range':[scan_start,scan_end],'baseline_parity':parity,'information_fragility':fragmetrics,'positive_year_share':yfull,'frozen_router_2025':None if rb is None else rb.to_dict(),'onset_frozen_router_2025':None if rf is None else rf.to_dict(),'onset_native_router_2025':None if rn is None else rn.to_dict(),'onset_frozen_ev_ratio_to_baseline':b_ratio,'onset_native_ev_ratio_to_baseline':n_ratio,'frozen_router_gates':b_gates,'native_router_gates':n_gates,'verdict':verdict,'frozen_short_v1_changed':False,'live_allocation':0,'no_tuning':True}
    (OUT/'metrics.json').write_text(json.dumps(j(metrics),indent=2))
    report=f"""# {LAB} — REPORT\n\n## Verdict\n**{verdict}**\n\n## Baseline parity\n{json.dumps(j(parity),indent=2)}\n\n## Information fragility\n{json.dumps(j(fragmetrics),indent=2)}\n\n## Clock-free gates — frozen router\n{json.dumps(j(b_gates),indent=2)}\n\n## Clock-free gates — native router\n{json.dumps(j(n_gates),indent=2)}\n\nFrozen SHORT v1 unchanged. Live allocation remains 0.\n"""
    (OUT/'REPORT.md').write_text(report)
    print(json.dumps(j(metrics),indent=2))

if __name__=='__main__':main()
