#!/usr/bin/env python3
"""U02C2: historical v283 shadow-event x canonical H4 market-clock conditional matrix.

IMPORTANT:
- Historical v283 input is the existing source-faithful M5-open shadow scanner output,
  not accepted as exact MT5 parity.
- Canonical market clock is H4 Supertrend ATR(10), multiplier 3, using the U05
  parity winner: BAR_OPEN with one-bar causal lag.
- TRANSITION is preregistered BEFORE outcome inspection as H4 ST age 0..2.
- Primary sample is episode-first stateless-pass opportunities (gap >15m or side change).
- Raw passed polls are diagnostic only.
"""
from pathlib import Path
import json, zipfile
import numpy as np
import pandas as pd

SHADOW='u01_shadow/u01_v283_shadow_events.csv'
M1ZIP='btc_1m.zip'
M5ZIP='btc_5m.zip'
OUT=Path('u02c2_out'); OUT.mkdir(exist_ok=True)
COST_USD=27.5
HORIZONS=[2,8,24,48]
START=pd.Timestamp('2024-01-01')


def pf(x):
    s=pd.Series(x).dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def load_zip(path, fmt=None):
    fs=[]
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.lower().endswith('.csv'):
                with z.open(n) as f:
                    q=pd.read_csv(f,usecols=['time','open','high','low','close'])
                fs.append(q)
    x=pd.concat(fs,ignore_index=True)
    if pd.api.types.is_numeric_dtype(x['time']):
        med=pd.to_numeric(x.time,errors='coerce').median()
        unit='us' if med>1e14 else ('ms' if med>1e11 else 's')
        x['time']=pd.to_datetime(pd.to_numeric(x.time,errors='coerce'),unit=unit,utc=True).dt.tz_localize(None)
    else:
        if fmt is None:
            # Covers canonical ResearchOS frozen files like 2024.01.01 00:00.
            x['time']=pd.to_datetime(x.time,format='%Y.%m.%d %H:%M',errors='coerce',utc=True).dt.tz_localize(None)
            if x.time.isna().mean()>.5:
                x['time']=pd.to_datetime(x.time,errors='coerce',utc=True).dt.tz_localize(None)
        else:
            x['time']=pd.to_datetime(x.time,format=fmt,errors='coerce',utc=True).dt.tz_localize(None)
    for c in ['open','high','low','close']:
        x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time').reset_index(drop=True)


def resample(df,rule):
    z=(df.set_index('time').resample(rule,label='left',closed='left')
       .agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index())
    z['close_time']=z.time+pd.Timedelta(rule)
    return z


def wilder(s,n):
    # Same U05 implementation convention: ewm(alpha=1/n, adjust=False, min_periods=n).
    return s.ewm(alpha=1/n,adjust=False,min_periods=n).mean()


def h4_supertrend(m5,mult=3.0):
    x=resample(m5,'4h')
    pc=x.close.shift(1)
    tr=pd.concat([x.high-x.low,(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr10']=wilder(tr,10)
    hl2=(x.high+x.low)/2; bu=hl2+mult*x.atr10; bl=hl2-mult*x.atr10
    fu=bu.copy(); fl=bl.copy(); st=np.full(len(x),np.nan); d=np.zeros(len(x),dtype=int)
    start=x.atr10.first_valid_index()
    if start is None: return x
    for i in range(start,len(x)):
        if i==start:
            fu.iat[i]=bu.iat[i]; fl.iat[i]=bl.iat[i]; d[i]=1; st[i]=fl.iat[i]; continue
        fu.iat[i]=bu.iat[i] if (bu.iat[i]<fu.iat[i-1] or x.close.iat[i-1]>fu.iat[i-1]) else fu.iat[i-1]
        fl.iat[i]=bl.iat[i] if (bl.iat[i]>fl.iat[i-1] or x.close.iat[i-1]<fl.iat[i-1]) else fl.iat[i-1]
        if d[i-1]==-1: d[i]=1 if x.close.iat[i]>fu.iat[i] else -1
        else: d[i]=-1 if x.close.iat[i]<fl.iat[i] else 1
        st[i]=fl.iat[i] if d[i]==1 else fu.iat[i]
    x['st_dir']=d; x['st_line']=st
    age=np.zeros(len(x),dtype=int)
    for i in range(1,len(x)):
        age[i]=age[i-1]+1 if d[i]!=0 and d[i]==d[i-1] else 0
    x['st_age']=age
    x['st_dist_atr']=(x.close-x.st_line)/x.atr10
    return x


def attach_clock(events,h4):
    e=events.copy().sort_values('time')
    # U05 parity winner = BAR_OPEN, lag=1. State known at event t is previous H4 raw row.
    hs=h4[['time','st_dir','st_age','st_dist_atr']].copy()
    for c in ['st_dir','st_age','st_dist_atr']: hs[c]=hs[c].shift(1)
    hs=hs.dropna(subset=['st_dir']).sort_values('time')
    m=pd.merge_asof(e,hs,on='time',direction='backward')
    td=np.where(m.action.eq('BUY'),1,-1)
    m['h4_trade_relation']=td*m.st_dir
    return m


def state_label(r):
    age=int(r.st_age); side=r.action; rel=int(r.h4_trade_relation)
    # PREREGISTERED transition: first 3 H4 bars after ST flip (~12h), outcome-blind.
    if age<=2: return 'TRANSITION'
    if side=='BUY' and age>58 and rel==-1: return 'TIER_A'
    if side=='BUY' and age>58 and rel==1: return 'TIER_B'
    # Canonical recent SELL B3 from LAB023; priority over generic clock bucket.
    if side=='SELL' and 27<=age<=50: return 'SELL_B3'
    if age<=11: return 'OTHER_B1'
    if age<=27: return 'OTHER_B2'
    if age<=58: return 'OTHER_B3'
    return 'OTHER_B4'


def episode_first(passed):
    z=passed.sort_values('time').copy()
    prev_t=z.time.shift(1); prev_side=z.action.shift(1)
    new=(prev_t.isna()) | (z.action.ne(prev_side)) | ((z.time-prev_t)>pd.Timedelta(minutes=15))
    z['episode_id']=new.cumsum().astype(int)
    return z.groupby('episode_id',as_index=False).first()


def h1_atr_from_m1(m1):
    h=resample(m1,'1h')
    pc=h.close.shift(1); tr=pd.concat([h.high-h.low,(h.high-pc).abs(),(h.low-pc).abs()],axis=1).max(axis=1)
    h['atr14']=wilder(tr,14)
    return h


def add_outcomes(events,m1,h1):
    e=events.copy().sort_values('time').reset_index(drop=True)
    mt=m1.time.to_numpy(dtype='datetime64[ns]'); mo=m1.open.to_numpy(float); mh=m1.high.to_numpy(float); ml=m1.low.to_numpy(float); mc=m1.close.to_numpy(float)
    hct=h1.close_time.to_numpy(dtype='datetime64[ns]'); ha=h1.atr14.to_numpy(float)
    def atr_at(t):
        j=int(np.searchsorted(hct,np.datetime64(t),'right')-1)
        return float(ha[j]) if j>=0 and np.isfinite(ha[j]) else np.nan
    rows=[]
    for r in e.itertuples(index=False):
        # Causal common entry: next M1 open after the M5-open shadow event.
        t0=pd.Timestamp(r.time)+pd.Timedelta(minutes=1)
        j=int(np.searchsorted(mt,np.datetime64(t0),'left'))
        if j>=len(m1): continue
        entry=float(mo[j]); a=atr_at(r.time)
        if not np.isfinite(a) or a<=0: continue
        d=1.0 if r.action=='BUY' else -1.0
        sd=1.5*a; sl=entry-d*sd; tp=entry+d*1.5*sd; costR=COST_USD/sd
        q=r._asdict(); q.update(entry_time=t0,entry=entry,atr_h1=a,stop_dist=sd,cost_R=costR)
        end48=pd.Timestamp(r.time)+pd.Timedelta(hours=48)
        j48=min(int(np.searchsorted(mt,np.datetime64(end48),'left')),len(m1))
        if j48<=j: continue
        ph=mh[j:j48]; pl=ml[j:j48]
        if d>0:
            q['mfe48_R']=(float(ph.max())-entry)/sd; q['mae48_R']=(float(pl.min())-entry)/sd
        else:
            q['mfe48_R']=(entry-float(pl.min()))/sd; q['mae48_R']=(entry-float(ph.max()))/sd
        for hh in HORIZONS:
            te=pd.Timestamp(r.time)+pd.Timedelta(hours=hh)
            je=int(np.searchsorted(mt,np.datetime64(te),'left'))
            if je<=j or je>len(m1):
                q[f'real{hh}h_R']=np.nan; q[f'exit{hh}h']='NA'; q[f'term{hh}h_pct']=np.nan; continue
            hi=mh[j:je]; lo=ml[j:je]; endp=float(mo[je]) if je<len(m1) else float(mc[je-1])
            term=d*(endp-entry)/entry*100.0-COST_USD/entry*100.0
            if d>0:
                si=np.flatnonzero(lo<=sl); ti=np.flatnonzero(hi>=tp)
            else:
                si=np.flatnonzero(hi>=sl); ti=np.flatnonzero(lo<=tp)
            is_=int(si[0]) if si.size else 10**18; it=int(ti[0]) if ti.size else 10**18
            if it<is_: rr=1.5-costR; ex='TP'
            elif is_<it: rr=-1.0-costR; ex='SL'
            else: rr=d*(endp-entry)/sd-costR; ex='TIME'
            q[f'real{hh}h_R']=rr; q[f'exit{hh}h']=ex; q[f'term{hh}h_pct']=term
        rows.append(q)
    return pd.DataFrame(rows)


def metrics(df,view):
    rows=[]
    for (side,state),g in df.groupby(['action','market_state']):
        r={'view':view,'side':side,'state':state,'N':len(g),'events_per_week':len(g)/ANALYSIS_WEEKS,
           'MFE48_med_R':float(g.mfe48_R.median()),'MAE48_med_R':float(g.mae48_R.median())}
        for hh in HORIZONS:
            z=g[f'real{hh}h_R'].dropna(); r[f'EV{hh}h_R']=float(z.mean()) if len(z) else np.nan; r[f'PF{hh}h']=pf(z); r[f'WR{hh}h']=float((z>0).mean()) if len(z) else np.nan
            r[f'TERM_EV{hh}h_pct']=float(g[f'term{hh}h_pct'].mean())
        rows.append(r)
    return pd.DataFrame(rows)


def yearly_metrics(df):
    rows=[]
    x=df.copy(); x['year']=x.time.dt.year
    for (y,side,state),g in x.groupby(['year','action','market_state']):
        z=g.real24h_R.dropna(); rows.append({'year':int(y),'side':side,'state':state,'N':len(g),'EV24h_R':z.mean(),'PF24h':pf(z),'WR24h':(z>0).mean(),'EV48h_R':g.real48h_R.mean(),'PF48h':pf(g.real48h_R)})
    return pd.DataFrame(rows)


def aggregate_other(df):
    x=df.copy(); x['state5']=x.market_state.where(~x.market_state.str.startswith('OTHER_'),'OTHER_B1-B4')
    rows=[]
    for (side,state),g in x.groupby(['action','state5']):
        z=g.real24h_R.dropna(); rows.append({'side':side,'state':state,'N':len(g),'events_per_week':len(g)/ANALYSIS_WEEKS,'EV24h_R':z.mean(),'PF24h':pf(z),'WR24h':(z>0).mean(),'EV48h_R':g.real48h_R.mean(),'PF48h':pf(g.real48h_R),'MFE48_med_R':g.mfe48_R.median(),'MAE48_med_R':g.mae48_R.median()})
    return pd.DataFrame(rows)


def exact_aug_sanity():
    # Optional files staged by workflow. Exact MT5 panel stays separate from historical shadow.
    p=Path('exact_aug/u02_exec_poll_outcomes.csv'); c=Path('exact_aug/u05_signal_market_clock_map.csv')
    if not p.exists() or not c.exists(): return pd.DataFrame()
    e=pd.read_csv(p); m=pd.read_csv(c)
    z=e.merge(m[['signal_time','side','st_dir','st_age','h4_trade_relation']],on=['signal_time','side'],how='left')
    z['action']=z.side
    z['market_state']=z.apply(state_label,axis=1)
    return z


def main():
    global ANALYSIS_WEEKS
    sh=pd.read_csv(SHADOW); sh['time']=pd.to_datetime(sh.time)
    sh=sh[(sh.time>=START)&(sh.action!='WAIT')&(sh.pass_stateless==1)].copy()
    m5=load_zip(M5ZIP); h4=h4_supertrend(m5)
    sh=attach_clock(sh,h4).dropna(subset=['st_age','st_dir']).copy(); sh['market_state']=sh.apply(state_label,axis=1)
    ep=episode_first(sh); ep['market_state']=ep.apply(state_label,axis=1)
    m1=load_zip(M1ZIP); h1=h1_atr_from_m1(m1)
    data_end=min(m1.time.max(),sh.time.max()+pd.Timedelta(hours=48)); ANALYSIS_WEEKS=(data_end-START).total_seconds()/(7*86400)
    poll=add_outcomes(sh,m1,h1); eps=add_outcomes(ep,m1,h1)
    poll.to_csv(OUT/'historical_shadow_passed_polls.csv',index=False); eps.to_csv(OUT/'historical_shadow_episode_first.csv',index=False)
    pm=metrics(poll,'RAW_POLL_DIAGNOSTIC'); em=metrics(eps,'EPISODE_FIRST_PRIMARY')
    pd.concat([em,pm],ignore_index=True).to_csv(OUT/'state_matrix_detailed.csv',index=False)
    agg=aggregate_other(eps); agg.to_csv(OUT/'state_matrix_primary_5way.csv',index=False)
    yr=yearly_metrics(eps); yr.to_csv(OUT/'yearly_state_matrix.csv',index=False)
    tag=[]
    for (side,state,t),g in eps.groupby(['action','market_state','tag']):
        tag.append({'side':side,'state':state,'tag':t,'N':len(g),'EV24h_R':g.real24h_R.mean(),'PF24h':pf(g.real24h_R),'WR24h':(g.real24h_R>0).mean()})
    pd.DataFrame(tag).to_csv(OUT/'tag_x_state_matrix.csv',index=False)
    exact=exact_aug_sanity();
    if len(exact): exact.to_csv(OUT/'exact_aug_exec_state_sanity.csv',index=False)
    # Count positive years only where N>=5, to avoid treating tiny cells as stability evidence.
    stab=[]
    for (side,state),g in yr.groupby(['side','state']):
        valid=g[g.N>=5]; stab.append({'side':side,'state':state,'years_N5':len(valid),'positive_years_N5':int((valid.EV24h_R>0).sum()),'years_total':len(g)})
    stab=pd.DataFrame(stab); stab.to_csv(OUT/'year_stability.csv',index=False)
    summary={'mode':'HISTORICAL_V283_PARTIAL_SHADOW_NOT_MT5_PARITY','transition_prereg':'H4_ST_AGE 0..2, outcome-blind','clock':'H4 Supertrend ATR10 x3; U05 BAR_OPEN lag1 parity convention','population_raw_passed_polls':len(poll),'population_episode_first':len(eps),'analysis_weeks':ANALYSIS_WEEKS,'state_counts_episode':eps.groupby(['action','market_state']).size().to_dict(),'limitations':['historical shadow scanner is not exact MT5 parity','existing shadow implements v283 B/C SmartMock families and several stateless gates but not all A/D setup families or stateful delivery-memory gates','raw polls are correlated and diagnostic; episode-first is primary']}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    rep=['# BTC V283 MARKET-CLOCK CONDITIONAL LAB U02C2','',
         '**Status:** historical conditional SHADOW diagnostic — not exact MT5 parity.','',
         '## Preregistered market-clock states','',
         '- TRANSITION: H4 Supertrend age 0–2 (first ~12h after flip).','- TIER_A: BUY, H4 age >58, trade-coordinate relation −1.','- TIER_B: BUY, H4 age >58, relation +1.','- SELL_B3: SELL, H4 age 27–50.','- OTHER_B1: remaining age 3–11.','- OTHER_B2: remaining age 12–27.','- OTHER_B3: remaining age 28–58.','- OTHER_B4: remaining age >58.','',
         'Primary unit is episode-first opportunity; repeated raw M5 polls are diagnostic only. Common outcome: 1.5×H1 ATR stop, TP=1.5R, otherwise time exit; $27.5/BTC cost proxy.','',
         '## Primary 5-way matrix','',agg.to_markdown(index=False),'','## Detailed matrix','',em.to_markdown(index=False),'','## Year stability (N>=5/cell/year)','',stab.to_markdown(index=False),'','## Caveat','',
         'This closes conditional reachability/edge localization for the existing historical source-faithful shadow. It does NOT certify full v283 historical MT5 parity because the shadow does not implement all SmartMock A/D families and stateful delivery-memory gates. Exact August MT5 executions are kept as a separate sanity panel.']
    (OUT/'REPORT.md').write_text('\n'.join(rep))
    print('PRIMARY 5-WAY\n',agg.to_string(index=False)); print('\nDETAILED\n',em.to_string(index=False)); print('\nSTABILITY\n',stab.to_string(index=False)); print('\nSUMMARY\n',json.dumps(summary,indent=2,default=str))

if __name__=='__main__': main()
