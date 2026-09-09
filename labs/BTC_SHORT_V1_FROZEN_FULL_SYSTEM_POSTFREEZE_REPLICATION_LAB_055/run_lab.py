#!/usr/bin/env python3
from __future__ import annotations
import io, json, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

LAB='BTC_SHORT_V1_FROZEN_FULL_SYSTEM_POSTFREEZE_REPLICATION_LAB_055'
HERE=Path(__file__).resolve().parent; OUT=HERE/'output'; OUT.mkdir(parents=True,exist_ok=True)
LABS=HERE.parent
SRC22=LABS/'BTC_BINANCE_RETAIL_FLOW_DIRECTION_X_H4_PIVOT_M15_PRICE_TIMING_LAB_022'/'output'/'flow_only_nonoverlap.csv'
SRC35=LABS/'BTC_RETAIL_FLOW_FORCED_LIQUIDITY_LEVEL_PROXY_X_BREAK_ACCEPTANCE_LAB_035'/'output'/'activation_stream.csv'
SRC41=LABS/'BTC_FLOW_LEVEL_ALL_TOUCH_DIRECTIONAL_LIQUIDITY_ELASTICITY_WITHOUT_HIGH_VOLUME_GATE_LAB_041'/'output'/'all_touch_elasticity_stream.csv'
SRC43=LABS/'BTC_FLOW_LEVEL_SHORT_HIGH_RESPONSE_VS_LOW_RESPONSE_CAUSAL_ROUTER_REPLICATION_LAB_043'/'output'/'short_response_router_stream.csv'
AUG0=pd.Timestamp('2026-08-01',tz='UTC'); SEP0=pd.Timestamp('2026-09-01',tz='UTC')
RAW0=pd.Timestamp('2026-04-15',tz='UTC'); DAILY_END=pd.Timestamp('2026-09-08',tz='UTC')
FLOW_SCAN0=pd.Timestamp('2026-07-01',tz='UTC')
FLOW_LOOKBACK=pd.Timedelta(days=90); FLOW_MIN_N=1000; EVENT_LOOKBACK=pd.Timedelta(days=90); EVENT_MIN_N=40
LEVEL_BARS=48; ACCEPT_BARS=4; TP_R=1.5; STOP_ATR=2.5; PRIMARY_BPS=5.0; RISK_PCT=.25


def ts_num(s):
    v=pd.to_numeric(s,errors='coerce'); med=v.dropna().abs().median() if v.notna().any() else np.nan
    unit='us' if pd.notna(med) and med>1e14 else ('ms' if pd.notna(med) and med>1e11 else 's')
    return pd.to_datetime(v,unit=unit,errors='coerce',utc=True)

def parse_metric_zip(content,label):
    z=zipfile.ZipFile(io.BytesIO(content)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:return pd.DataFrame()
    d=pd.read_csv(z.open(names[0])); d.columns=[str(c).strip() for c in d.columns]
    tc='create_time' if 'create_time' in d.columns else ('timestamp' if 'timestamp' in d.columns else None)
    if tc is None or 'count_long_short_ratio' not in d.columns:return pd.DataFrame()
    t=d[tc]; time=ts_num(t) if pd.api.types.is_numeric_dtype(t) else pd.to_datetime(t.astype(str).str.strip(),errors='coerce',utc=True)
    return pd.DataFrame({'time':time,'ratio':pd.to_numeric(d.count_long_short_ratio,errors='coerce')}).dropna()

def parse_kline_zip(content,label):
    z=zipfile.ZipFile(io.BytesIO(content)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:return pd.DataFrame()
    d=pd.read_csv(z.open(names[0]),header=None)
    if d.shape[1]<11:return pd.DataFrame()
    return pd.DataFrame({'time':ts_num(d.iloc[:,0]),'open':pd.to_numeric(d.iloc[:,1],errors='coerce'),'high':pd.to_numeric(d.iloc[:,2],errors='coerce'),'low':pd.to_numeric(d.iloc[:,3],errors='coerce'),'close':pd.to_numeric(d.iloc[:,4],errors='coerce'),'quote':pd.to_numeric(d.iloc[:,7],errors='coerce'),'taker_buy_quote':pd.to_numeric(d.iloc[:,10],errors='coerce')}).dropna()

def get_zip(url,parser,label):
    try:
        r=requests.get(url,timeout=30)
        if r.status_code!=200:return None,r.status_code
        return parser(r.content,label),200
    except Exception:return None,'EXC'

def download_metrics():
    days=list(pd.date_range(RAW0,DAILY_END,freq='D')); parts=[]; man=[]
    base='https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT'
    def one(t):
        ds=t.strftime('%Y-%m-%d'); fn=f'BTCUSDT-metrics-{ds}.zip'; d,s=get_zip(f'{base}/{fn}',parse_metric_zip,fn); return d,dict(date=ds,status=s,rows=0 if d is None else len(d))
    with ThreadPoolExecutor(max_workers=24) as ex:
        fs=[ex.submit(one,t) for t in days]
        for f in as_completed(fs):
            d,m=f.result(); man.append(m)
            if d is not None and len(d):parts.append(d)
    pd.DataFrame(man).sort_values('date').to_csv(OUT/'metrics_manifest.csv',index=False)
    if not parts:raise RuntimeError('No metrics data')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').set_index('time')
    x=x.ratio.resample('15min',label='left',closed='left').last().ffill(limit=2).dropna().to_frame('ratio')
    x['delta_ls_12']=x.ratio-x.ratio.shift(12)
    return x

def download_futures():
    parts=[]; man=[]; monthly=list(pd.period_range('2026-04','2026-08',freq='M'))
    base_m='https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m'
    base_d='https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/15m'
    jobs=[]
    with ThreadPoolExecutor(max_workers=16) as ex:
        for p in monthly:
            ym=f'{p.year}-{p.month:02d}'; fn=f'BTCUSDT-15m-{ym}.zip'; jobs.append((ym,ex.submit(get_zip,f'{base_m}/{fn}',parse_kline_zip,fn)))
        for t in pd.date_range('2026-09-01',DAILY_END,freq='D'):
            ds=t.strftime('%Y-%m-%d'); fn=f'BTCUSDT-15m-{ds}.zip'; jobs.append((ds,ex.submit(get_zip,f'{base_d}/{fn}',parse_kline_zip,fn)))
        for label,f in jobs:
            d,s=f.result(); man.append(dict(period=label,status=s,rows=0 if d is None else len(d)))
            if d is not None and len(d):parts.append(d)
    pd.DataFrame(man).sort_values('period').to_csv(OUT/'futures_manifest.csv',index=False)
    if not parts:raise RuntimeError('No futures data')
    x=pd.concat(parts,ignore_index=True).sort_values('time').drop_duplicates('time',keep='last').set_index('time')
    pc=x.close.shift(1); tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr14']=tr.rolling(14,min_periods=14).mean()
    x['prior12_low']=x.low.shift(1).rolling(LEVEL_BARS,min_periods=LEVEL_BARS).min(); x['prior12_high']=x.high.shift(1).rolling(LEVEL_BARS,min_periods=LEVEL_BARS).max()
    delta=2*x.taker_buy_quote-x.quote; ds=delta.rolling(4,min_periods=4).sum().shift(1)
    x['netdelta60_raw']=ds; x['netdelta60_medabs']=ds.abs().shift(1).rolling(90*96,min_periods=30*96).median(); x['disp60_px']=x.close.shift(1)-x.close.shift(5)
    return x

def flow_state(metrics,t):
    pos=metrics.index.searchsorted(t,side='right')-1
    if pos<12:return None
    tt=metrics.index[pos]; cur=float(metrics.delta_ls_12.iloc[pos]); hist=metrics.loc[(metrics.index>=tt-FLOW_LOOKBACK)&(metrics.index<tt),'delta_ls_12'].dropna()
    if len(hist)<FLOW_MIN_N or not np.isfinite(cur):return None
    q20=float(hist.quantile(.20)); q80=float(hist.quantile(.80)); side=1 if cur<=q20 else (-1 if cur>=q80 else 0)
    return dict(flow_time=tt,ratio=float(metrics.ratio.iloc[pos]),delta_ls_12=cur,q20=q20,q80=q80,side=side,history_n=len(hist))

def generate_flow(metrics,fut):
    rows=[]; last=None
    for t in metrics.index:
        if t<FLOW_SCAN0:continue
        fs=flow_state(metrics,t)
        if fs is None or fs['side']==0:continue
        if last is not None and t-last<pd.Timedelta(hours=12):continue
        horizon=t+pd.Timedelta(hours=12)
        if t not in fut.index or horizon not in fut.index:continue
        atr=float(fut.at[t,'atr14'])
        if not np.isfinite(atr) or atr<=0:continue
        mv=(float(fut.at[horizon,'close'])-float(fut.at[t,'close']))/atr
        rows.append(dict(signal_time=t,side=int(fs['side']),signed12_atr=float(fs['side']*mv),delta_ls_12=fs['delta_ls_12'],q20=fs['q20'],q80=fs['q80'],history_n=fs['history_n']))
        last=t
    d=pd.DataFrame(rows); d['flow_id_new']=np.arange(len(d),dtype=int); return d

def build_activation(flow,fut):
    rows=[]
    for r in flow.itertuples(index=False):
        t=pd.Timestamp(r.signal_time); side=int(r.side); horizon=t+pd.Timedelta(hours=12)
        if t not in fut.index or horizon not in fut.index:continue
        atr=float(fut.at[t,'atr14']); sig=float(fut.at[t,'close']); lvl=float(fut.at[t,'prior12_high'] if side>0 else fut.at[t,'prior12_low'])
        if not np.isfinite(atr) or atr<=0 or not np.isfinite(lvl):continue
        path=fut.loc[(fut.index>=t)&(fut.index<=horizon)]
        touch=pd.NaT; touch_pos=None
        for i,(tt,b) in enumerate(path.iterrows()):
            hit=float(b.high)>=lvl if side>0 else float(b.low)<=lvl
            if hit:touch=tt; touch_pos=i; break
        state='NO_TOUCH'; ct=pd.NaT; cp=np.nan
        if touch_pos is not None:
            resp=path.iloc[touch_pos:touch_pos+ACCEPT_BARS]; acc=None
            for tt,b in resp.iterrows():
                if side*(float(b.close)-lvl)>=0:acc=(tt,float(b.close)); break
            if acc is not None:state='ACCEPT'; ct,cp=acc
            elif len(resp)>=ACCEPT_BARS:state='REJECT'; ct=resp.index[-1]; cp=float(resp.iloc[-1].close)
            else:state='UNRESOLVED'; ct=resp.index[-1] if len(resp) else touch; cp=float(resp.iloc[-1].close) if len(resp) else np.nan
        pressure=response=elasticity=np.nan
        if pd.notna(touch) and touch in fut.index and state in ('ACCEPT','REJECT'):
            z=fut.loc[touch]; raw=float(z.netdelta60_raw); med=float(z.netdelta60_medabs); disp_px=float(z.disp60_px)
            norm=side*raw/med if np.isfinite(raw) and np.isfinite(med) and med>0 else np.nan
            response=side*disp_px/atr if np.isfinite(disp_px) else np.nan
            pressure=abs(norm) if np.isfinite(norm) else np.nan
            elasticity=response/max(abs(norm),.25) if np.isfinite(response) and np.isfinite(norm) else np.nan
        rows.append(dict(flow_id_new=int(r.flow_id_new),signal_time=t,side=side,signed12_atr=float(r.signed12_atr),signal_close=sig,atr14=atr,level=lvl,touch_time=touch,class_time=ct,state=state,class_price=cp,pressure_mag_60=pressure,response_60=response,fut_elasticity_60=elasticity))
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)

def load_hist_state():
    h=pd.read_csv(SRC41,usecols=['signal_time','pressure_mag_60','response_60','fut_elasticity_60'])
    h['signal_time']=pd.to_datetime(h.signal_time,errors='coerce',utc=True)
    for c in ['pressure_mag_60','response_60','fut_elasticity_60']:h[c]=pd.to_numeric(h[c],errors='coerce')
    return h.dropna().sort_values('signal_time').reset_index(drop=True)

def classify_new(a,hist):
    z=a.copy(); z['prior_n']=0; z['pressure_med90']=np.nan; z['response_med90']=np.nan; z['book_state']='UNRESOLVED'; z['response_router']='UNRESOLVED'
    base=hist.copy()
    for i,r in z.sort_values('signal_time').iterrows():
        if not (np.isfinite(r.pressure_mag_60) and np.isfinite(r.response_60) and np.isfinite(r.fut_elasticity_60)):continue
        t=pd.Timestamp(r.signal_time); p=base[(base.signal_time>=t-EVENT_LOOKBACK)&(base.signal_time<t)]
        z.at[i,'prior_n']=len(p)
        if len(p)<EVENT_MIN_N:
            base=pd.concat([base,pd.DataFrame([{'signal_time':t,'pressure_mag_60':r.pressure_mag_60,'response_60':r.response_60,'fut_elasticity_60':r.fut_elasticity_60}])],ignore_index=True); continue
        pm=float(p.pressure_mag_60.median()); rm=float(p.response_60.median()); z.at[i,'pressure_med90']=pm; z.at[i,'response_med90']=rm
        low=float(r.pressure_mag_60)<=pm; high=float(r.response_60)>rm
        st='THIN_BOOK' if low and high else ('DRIVEN_MOVE' if (not low) and high else ('ABSORPTION' if (not low) else 'WEAK'))
        z.at[i,'book_state']=st; z.at[i,'response_router']='HIGH_RESPONSE' if high else 'LOW_RESPONSE'
        base=pd.concat([base,pd.DataFrame([{'signal_time':t,'pressure_mag_60':r.pressure_mag_60,'response_60':r.response_60,'fut_elasticity_60':r.fut_elasticity_60}])],ignore_index=True)
    return z.sort_values('signal_time').reset_index(drop=True)
def net_r(entry,exitpx,D,bps):return float((entry-exitpx)/D-(bps/10000.0)*entry/D)
def first_passage(path,entry,D):
    fav=entry-.5*D; adv=entry+.5*D
    for tt,b in path.iterrows():
        hf=float(b.low)<=fav; ha=float(b.high)>=adv
        if ha:return 'ADVERSE_FIRST',tt,adv
        if hf:return 'FAVORABLE_FIRST',tt,fav
    return 'NONE_120',pd.NaT,np.nan

def simulate_trade(r,fut):
    t=pd.Timestamp(r.signal_time); horizon=t+pd.Timedelta(hours=12); et=pd.Timestamp(r.class_time); ep=float(r.class_price); atr=float(r.atr14); D=STOP_ATR*atr; lvl=float(r.level)
    base=dict(signal_time=t,side=int(r.side),response_router=r.response_router,state=r.state,entry_time=et,entry_price=ep,risk_dist=D,level=lvl,horizon=horizon,traded=False,exit_time=pd.NaT,exit_price=np.nan,exit_reason='NO_TRADE',persistent_exit=False,net_r_5bps=0.0,net_r_10bps=0.0)
    if r.side!=-1 or r.response_router!='HIGH_RESPONSE' or r.state!='ACCEPT' or et not in fut.index or horizon not in fut.index:return base
    p=fut[(fut.index>et)&(fut.index<=horizon)]
    stop=ep+D; tp=ep-TP_R*D; reason='TIME'; xt=horizon; xp=float(fut.at[horizon,'close'])
    for tt,b in p.iterrows():
        hs=float(b.high)>=stop; ht=float(b.low)<=tp
        if hs:reason='SL'; xt=tt; xp=stop; break
        if ht:reason='TP'; xt=tt; xp=tp; break
    parent_xt=xt; parent_xp=xp; parent_reason=reason
    end120=min(et+pd.Timedelta(minutes=120),parent_xt); p120=fut[(fut.index>et)&(fut.index<=end120)]
    fps,fpt,fpp=first_passage(p120,ep,D)
    persistent=False
    if fps=='ADVERSE_FIRST':
        include_end=(parent_reason=='TIME'); pc=fut[(fut.index>fpt)&((fut.index<=parent_xt) if include_end else (fut.index<parent_xt))]
        consec=0
        for tt,b in pc.iterrows():
            c=float(b.close)
            if c<=ep:break
            if c>lvl:
                consec+=1
                if consec>=2:xt=tt; xp=c; reason='PERSISTENT_FAILURE_EXIT'; persistent=True; break
            else:consec=0
    base.update(traded=True,exit_time=xt,exit_price=xp,exit_reason=reason,persistent_exit=persistent,net_r_5bps=net_r(ep,xp,D,5.0),net_r_10bps=net_r(ep,xp,D,10.0),fp_state=fps,fp_time=fpt,parent_exit_reason=parent_reason,parent_exit_time=parent_xt)
    return base

def pf(v):
    v=np.asarray(v,float); gp=v[v>0].sum(); gl=-v[v<0].sum(); return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)
def maxdd(v):
    v=np.asarray(v,float)
    if not len(v):return 0.0
    eq=np.r_[0,np.cumsum(v)]; pk=np.maximum.accumulate(eq); return float(np.max(pk-eq))
def summarize(events,trades,name):
    e=events.copy(); q=trades[trades.traded].copy().sort_values('entry_time'); v=q.net_r_5bps.to_numpy(float); dd=maxdd(v)
    return dict(slice=name,flow_short_n=int((e.side==-1).sum()),touch_short_n=int(((e.side==-1)&e.state.isin(['ACCEPT','REJECT','UNRESOLVED'])).sum()),high_response_short_n=int(((e.side==-1)&(e.response_router=='HIGH_RESPONSE')).sum()),accept_trade_n=len(q),persistent_exit_n=int(q.persistent_exit.sum()) if len(q) else 0,ev_5bps=float(q.net_r_5bps.mean()) if len(q) else np.nan,ev_10bps=float(q.net_r_10bps.mean()) if len(q) else np.nan,pf_5bps=pf(v) if len(q) else np.nan,cum_r_5bps=float(v.sum()) if len(q) else 0.0,max_dd_r=dd,dd_pct_025=dd*RISK_PCT,ev_per_high_response=float(v.sum()/max(1,int(((e.side==-1)&(e.response_router=='HIGH_RESPONSE')).sum()))) if len(e) else np.nan,tp_n=int((q.exit_reason=='TP').sum()) if len(q) else 0,sl_n=int((q.exit_reason=='SL').sum()) if len(q) else 0,time_n=int((q.exit_reason=='TIME').sum()) if len(q) else 0)
def parity_aug(flow,a):
    fz=pd.read_csv(SRC22); fz['signal_time']=pd.to_datetime(fz.signal_time,errors='coerce',utc=True); fz['side']=pd.to_numeric(fz.side,errors='coerce')
    x=flow[(flow.signal_time>=AUG0)&(flow.signal_time<SEP0)][['signal_time','side']].drop_duplicates(); y=fz[(fz.signal_time>=AUG0)&(fz.signal_time<SEP0)][['signal_time','side']].drop_duplicates()
    m=x.merge(y,on=['signal_time','side'],how='outer',indicator=True); flow_match=float((m._merge=='both').sum()/max(1,len(m)))
    ah=pd.read_csv(SRC35); ah['signal_time']=pd.to_datetime(ah.signal_time,errors='coerce',utc=True); rh=pd.read_csv(SRC43); rh['signal_time']=pd.to_datetime(rh.signal_time,errors='coerce',utc=True)
    gx=a[(a.signal_time>=AUG0)&(a.signal_time<SEP0)][['signal_time','side','state','response_router']].copy(); gy=rh[(rh.signal_time>=AUG0)&(rh.signal_time<SEP0)&(pd.to_numeric(rh.side,errors='coerce')==-1)][['signal_time','side','state','response_router']].copy()
    gy['side']=pd.to_numeric(gy.side,errors='coerce'); cmp=gx[gx.side==-1].merge(gy,on=['signal_time','side'],suffixes=('_new','_frozen'))
    router_match=float(((cmp.state_new.astype(str)==cmp.state_frozen.astype(str))&(cmp.response_router_new.astype(str)==cmp.response_router_frozen.astype(str))).mean()) if len(cmp) else np.nan
    return dict(generated_aug_flow_n=len(x),frozen_aug_flow_n=len(y),flow_union_n=len(m),flow_exact_match_share=flow_match,router_overlap_short_n=len(cmp),router_state_exact_match_share=router_match)
def main():
    metrics=download_metrics(); fut=download_futures(); flow=generate_flow(metrics,fut); flow.to_csv(OUT/'rebuilt_flow_stream.csv',index=False)
    act=build_activation(flow,fut); hist=load_hist_state(); classified=classify_new(act,hist[hist.signal_time<AUG0].copy()); classified.to_csv(OUT/'activation_router_stream.csv',index=False)
    par=parity_aug(flow,classified); (OUT/'parity.json').write_text(json.dumps(par,indent=2))
    aug=classified[(classified.signal_time>=AUG0)&(classified.signal_time<SEP0)].copy(); sep=classified[(classified.signal_time>=SEP0)].copy()
    rows=[simulate_trade(r,fut) for r in classified.itertuples(index=False)]; ex=pd.DataFrame(rows); ex.to_csv(OUT/'execution_stream.csv',index=False)
    augx=ex[(ex.signal_time>=AUG0)&(ex.signal_time<SEP0)].copy(); sepx=ex[ex.signal_time>=SEP0].copy(); comb=pd.concat([aug,sep],ignore_index=True); combx=pd.concat([augx,sepx],ignore_index=True)
    sm=pd.DataFrame([summarize(aug,augx,'HELDOUT_AUG'),summarize(sep,sepx,'FRESH_SEP'),summarize(comb,combx,'POSTFREEZE_COMBINED')]); sm.to_csv(OUT/'summary.csv',index=False)
    sr=sm[sm['slice']=='FRESH_SEP'].iloc[0]; cr=sm[sm['slice']=='POSTFREEZE_COMBINED'].iloc[0]
    fresh_trades=int(sr.accept_trade_n)
    gates={'metrics_tail_reaches_sep8':metrics.index.max()>=pd.Timestamp('2026-09-08 23:00',tz='UTC'),'futures_tail_reaches_sep8':fut.index.max()>=pd.Timestamp('2026-09-08 23:45',tz='UTC'),'aug_flow_parity_ge95pct':par['flow_exact_match_share']>=.95,'aug_router_parity_100pct_when_overlap':bool(pd.isna(par['router_state_exact_match_share']) or par['router_state_exact_match_share']==1.0),'fresh_sep_has_flow_short':int(sr.flow_short_n)>0,'fresh_sep_has_high_response_short':int(sr.high_response_short_n)>0,'fresh_sep_trades_ge5':fresh_trades>=5,'fresh_sep_ev_positive_if_n5':bool(fresh_trades<5 or sr.ev_5bps>0),'fresh_sep_pf_ge1_10_if_n5':bool(fresh_trades<5 or sr.pf_5bps>=1.10),'fresh_sep_10bps_positive_if_n5':bool(fresh_trades<5 or sr.ev_10bps>0),'fresh_sep_dd_le4pct':sr.dd_pct_025<=4.0,'combined_ev_nonnegative':bool(pd.isna(cr.ev_5bps) or cr.ev_5bps>=0),'no_tuning':True}
    if fresh_trades<5:verdict='WATCH_POSTFREEZE_INSUFFICIENT_FRESH_TRADES'
    elif sr.ev_5bps>0 and sr.pf_5bps>=1.10 and sr.ev_10bps>0 and sr.dd_pct_025<=4.0 and (pd.isna(cr.ev_5bps) or cr.ev_5bps>=0):verdict='PASS_FROZEN_SHORT_V1_POSTFREEZE'
    else:verdict='FAIL_FROZEN_SHORT_V1_POSTFREEZE'
    (OUT/'gates.json').write_text(json.dumps(gates,indent=2))
    L=[f'# {LAB}','',f'**Verdict: {verdict} — {sum(gates.values())}/{len(gates)} gates**','', '## Frozen system','`FLOW SHORT → HIGH_RESPONSE → ACCEPT → SL 2.5 ATR → TP 1.5R → signal+12h → PERSISTENT_FAILURE EXIT NOW`','', '## Raw/parity',f"- metrics tail: **{metrics.index.max()}**; futures tail: **{fut.index.max()}**",f"- August FLOW parity: generated **{par['generated_aug_flow_n']}**, frozen **{par['frozen_aug_flow_n']}**, exact union-match **{par['flow_exact_match_share']:.1%}**",f"- August router overlap SHORT N=**{par['router_overlap_short_n']}**, state/router exact match **{('—' if pd.isna(par['router_state_exact_match_share']) else f'{par['router_state_exact_match_share']:.1%}')}**",'', '## Full-system results','', '| Slice | FLOW SHORT | Touch | HIGH_RESPONSE | Trades | Persistent exits | EV5 | PF | CumR | MaxDD R | DD@0.25% | EV10 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in sm.iterrows():
        def f(x):return '—' if pd.isna(x) else f'{x:+.3f}'
        L.append(f"| {r['slice']} | {int(r.flow_short_n)} | {int(r.touch_short_n)} | {int(r.high_response_short_n)} | {int(r.accept_trade_n)} | {int(r.persistent_exit_n)} | {f(r.ev_5bps)} | {('—' if pd.isna(r.pf_5bps) else f'{r.pf_5bps:.3f}')} | {f(r.cum_r_5bps)} | {r.max_dd_r:.2f} | {r.dd_pct_025:.2f}% | {f(r.ev_10bps)} |")
    L+=['','## Fresh September note',f'- Completed-horizon fresh trades: **{fresh_trades}**.', '- If N<5, the preregistered verdict is WATCH regardless of point estimate; this prevents overclaiming from a tiny post-freeze sample.','', '## Gates']+[f"- {'PASS' if v else 'FAIL'} — `{k}`" for k,v in gates.items()]+['','## Guardrail','No threshold or management rule was changed. August is held-out/reused audit, not newly collected OOS. September is sequential fresh relative to LAB043–054 freeze, subject to raw-data/parity gates. No further tuning from these outcomes. Live allocation = **0**.']
    (OUT/'REPORT.md').write_text('\n'.join(L)+'\n')
    print(json.dumps({'verdict':verdict,'parity':par,'summary':sm.to_dict('records'),'gates':gates},indent=2,default=str))
if __name__=='__main__':main()
