#!/usr/bin/env python3
from __future__ import annotations

import argparse, importlib.util, json, re, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_H1_CONTEXT_ALIGNED_BUY_SELL_FRESH_OOS_AND_EPISODE_INDEPENDENCE_LAB_008'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB006_PATH=ROOT/'labs'/'XAU_H1_CONTEXT_ALIGNED_EXECUTABLE_RR15_COST_YEAR_TRANSFER_LAB_006'/'run_lab.py'
MECH_PATH=ROOT/'Projects'/'XAU_Pool'/'Code'/'Python'/'XAU_POOL_SELECTION_LAB_001'/'step1_mechanics.py'
HIST_BUY=ROOT/'labs'/'XAU_H1_CONTEXT_ALIGNED_BUY_SELL_CAUSAL_ASYMMETRY_YEAR_TRANSFER_LAB_007'/'output'/'buy_only_ledger.csv'
HIST_SELL=ROOT/'labs'/'XAU_H1_CONTEXT_ALIGNED_BUY_SELL_CAUSAL_ASYMMETRY_YEAR_TRANSFER_LAB_007'/'output'/'sell_only_ledger.csv'

THRESH=0.55
STOP_ATR=1.5
TP_ATR=2.25
MAX_HOURS=120
COST_BPS=[1.0,2.0,3.0,5.0]
PRIMARY_BPS=2.0
RISK_PCT=0.25
FRESH_START=pd.Timestamp('2026-07-24 00:00:00')
FRESH_CAP=pd.Timestamp('2026-08-25 23:59:59.999000')
PARITY_START=pd.Timestamp('2025-01-01 00:00:00')
PARITY_END=pd.Timestamp('2026-07-23 23:59:59')
BOOT_N=5000
SEED=2026091008


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None; spec.loader.exec_module(mod); return mod


def load_lab006(): return load_module(LAB006_PATH,'lab006_for_008')
def load_mech(): return load_module(MECH_PATH,'xau_mech_for_008')


def parse_daily_raw_zip(path:Path):
    rows=[]; raw_min=None; raw_max=None; members=[]
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            m=re.search(r'(20\d{6})\.csv$',n)
            if not m: continue
            day=pd.Timestamp(m.group(1))
            if day < FRESH_START.normalize() or day > FRESH_CAP.normalize(): continue
            members.append(n)
        for n in sorted(members):
            with z.open(n) as f:
                d=pd.read_csv(f,usecols=['time_server','bid','ask','spread_price'])
            if d.empty: continue
            t=pd.to_datetime(d.time_server,format='%Y.%m.%d %H:%M:%S.%f',errors='coerce')
            d=d.loc[t.notna()].copy(); t=t.loc[t.notna()]
            if d.empty: continue
            d['time']=t.values
            for c in ['bid','ask','spread_price']: d[c]=pd.to_numeric(d[c],errors='coerce')
            d=d.dropna(subset=['time','bid','ask'])
            d=d[(d.time>=FRESH_START)&(d.time<=FRESH_CAP)].copy()
            if d.empty: continue
            mn=d.time.min(); mx=d.time.max(); raw_min=mn if raw_min is None or mn<raw_min else raw_min; raw_max=mx if raw_max is None or mx>raw_max else raw_max
            d['minute']=d.time.dt.floor('min')
            g=d.groupby('minute',sort=True).agg(
                open=('bid','first'),high=('bid','max'),low=('bid','min'),close=('bid','last'),
                ask_open=('ask','first'),ask_high=('ask','max'),ask_low=('ask','min'),ask_close=('ask','last'),
                spread_mean=('spread_price','mean'),volume=('bid','size')).reset_index().rename(columns={'minute':'time'})
            rows.append(g)
    if not rows: raise RuntimeError('No fresh raw ticks parsed from sealed archive')
    m1=pd.concat(rows,ignore_index=True).drop_duplicates('time',keep='last').sort_values('time').reset_index(drop=True)
    return m1, {'members_used':len(members),'raw_min':str(raw_min),'raw_max':str(raw_max),'m1_rows':len(m1),'m1_min':str(m1.time.min()),'m1_max':str(m1.time.max())}


def h1_frame(m1:pd.DataFrame):
    g=m1.set_index('time').resample('1h',origin='epoch',label='left',closed='left').agg(
        open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    pc=g.close.shift(1); tr=pd.concat([g.high-g.low,(g.high-pc).abs(),(g.low-pc).abs()],axis=1).max(axis=1)
    g['atr']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    g['atr100']=tr.ewm(alpha=1/100,adjust=False,min_periods=100).mean(); g['atr_ratio']=g.atr/g.atr100
    dirn=(g.close-g.close.shift(20)).abs(); vol=g.close.diff().abs().rolling(20).sum(); g['kaufman_er']=dirn/vol.replace(0,np.nan)
    s=g.close.rolling(1200,min_periods=1200).mean(); g['slope']=s-s.shift(240)
    af=tr.ewm(alpha=1/480,adjust=False,min_periods=480).mean(); ass=tr.ewm(alpha=1/4800,adjust=False,min_periods=4800).mean(); g['vr']=af/ass
    return g


def generate_h1_candidates(m1:pd.DataFrame,mech):
    g=h1_frame(m1); S=mech.build_signals(g,'H1'); S={k:v for k,v in S.items() if k!='P_IMPULSE'}
    names=sorted(S); A=np.vstack([np.asarray(S[k]) for k in names])
    ready=g[['atr','atr_ratio','kaufman_er','slope','vr']].notna().all(axis=1).to_numpy()
    rows=[]
    for d in (1,-1):
        ix=np.flatnonzero(((A==d).any(axis=0)) & ready)
        for i in ix:
            rec={'time':g.time.iloc[i],'tf':'H1','dir':d,'signal_close':float(g.close.iloc[i]),'signal_atr':float(g.atr.iloc[i])}
            for j,k in enumerate(names): rec['f_'+k]=int(A[j,i]==d)
            rows.append(rec)
    q=pd.DataFrame(rows).sort_values(['time','dir']).reset_index(drop=True)
    q['available_event_time']=q.time+pd.Timedelta(hours=1)
    return q


def validate_candidate_parity(cand:pd.DataFrame,pool_path:Path):
    p=pd.read_parquet(pool_path,columns=['time','tf','dir']); p.time=pd.to_datetime(p.time,errors='coerce')
    p=p[(p.tf=='H1')&(p.time>=PARITY_START)&(p.time<=PARITY_END)][['time','dir']].drop_duplicates().sort_values(['time','dir']).reset_index(drop=True)
    c=cand[(cand.time>=PARITY_START)&(cand.time<=PARITY_END)][['time','dir']].drop_duplicates().sort_values(['time','dir']).reset_index(drop=True)
    mp=p.merge(c,on=['time','dir'],how='outer',indicator=True)
    return {'stored_n':len(p),'rebuilt_n':len(c),'exact':bool((mp._merge=='both').all() and len(p)==len(c)),
            'stored_only':int((mp._merge=='left_only').sum()),'rebuilt_only':int((mp._merge=='right_only').sum())}


def add_context(cand:pd.DataFrame,m1:pd.DataFrame,lab002,router):
    h4=m1.set_index('time').resample('4h',origin='epoch',label='left',closed='left').agg(
        open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum')).dropna()
    ctx=router.add_router(h4)
    cols=['available_time','regime','bias','score_expansion','score_pullback','score_reversal','score_range']
    c=ctx[cols].dropna(subset=['available_time','regime']).sort_values('available_time').reset_index(drop=False)
    j=pd.merge_asof(cand.sort_values('available_event_time'),c,left_on='available_event_time',right_on='available_time',direction='backward',allow_exact_matches=True)
    j=j.dropna(subset=['score_expansion','score_pullback','score_reversal','score_range']).copy()
    j=lab002.add_continuous_fields(j,j.dir)
    j['is_high']=pd.to_numeric(j.context_score,errors='coerce')>THRESH
    return j


def first_idx(mask):
    q=np.flatnonzero(mask); return int(q[0]) if len(q) else None


def simulate_fresh_one(row,m1:pd.DataFrame,cap:pd.Timestamp):
    T=m1.time.to_numpy(dtype='datetime64[ns]'); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float); C=m1.close.to_numpy(float)
    start=np.datetime64(pd.Timestamp(row.available_event_time).to_datetime64()); planned_end=start+np.timedelta64(MAX_HOURS,'h'); cap64=np.datetime64(cap.to_datetime64())
    obs_end=min(planned_end,cap64); i0=int(np.searchsorted(T,start,side='left')); i1=int(np.searchsorted(T,obs_end,side='right'))
    if i0>=len(T) or i1<=i0: return None
    t=T[i0:i1]; hi=H[i0:i1]; lo=L[i0:i1]; cl=C[i0:i1]
    entry=float(row.signal_close); atr=float(row.signal_atr); d=int(row.dir); sd=STOP_ATR*atr; td=TP_ATR*atr
    if not np.isfinite(entry) or not np.isfinite(sd) or sd<=0: return None
    if d==1: sh=lo<=entry-sd; th=hi>=entry+td
    else: sh=hi>=entry+sd; th=lo<=entry-td
    isx=first_idx(sh); itp=first_idx(th); same=isx is not None and itp is not None and isx==itp
    if isx is not None and (itp is None or isx<=itp): state='SL'; gross=-1.0; ix=isx
    elif itp is not None: state='TP'; gross=1.5; ix=itp
    elif cap64 < planned_end: state='CENSORED'; gross=np.nan; ix=len(t)-1
    else: state='TIME'; ix=len(t)-1; gross=float(d*(cl[ix]-entry)/sd)
    rec={'entry_time':pd.Timestamp(start),'exit_time':pd.Timestamp(t[ix]),'hold_hours':float((t[ix]-start)/np.timedelta64(1,'h')),
         'state':state,'gross_r':gross,'samebar':bool(same),'entry_price':entry,'signal_atr':atr,'stop_distance':sd,'dir':d}
    for b in COST_BPS:
        cr=entry*(b/10000.0)/sd; rec[f'cost_r_{b:g}bps']=float(cr); rec[f'net_r_{b:g}bps']=float(gross-cr) if np.isfinite(gross) else np.nan
    return rec


def build_fresh_events(sel:pd.DataFrame,m1:pd.DataFrame,cap:pd.Timestamp):
    rows=[]
    for _,r in sel.sort_values('available_event_time').iterrows():
        q=simulate_fresh_one(r,m1,cap)
        if q is not None: rows.append(q)
    return pd.DataFrame(rows)


def route_leg(events:pd.DataFrame,d:int):
    z=events[events.dir.eq(d)].sort_values('entry_time').copy(); keep=[]; active=None; skipped=0
    for i,r in z.iterrows():
        et=pd.Timestamp(r.entry_time)
        if active is None or et>=active: keep.append(i); active=pd.Timestamp(r.exit_time)
        else: skipped+=1
    routed=z.loc[keep].sort_values('entry_time').reset_index(drop=True)
    resolved=routed[routed.state!='CENSORED'].copy().reset_index(drop=True)
    return routed,resolved,skipped


def max_dd(v):
    x=pd.to_numeric(v,errors='coerce').dropna().to_numpy(float)
    if not len(x): return np.nan
    eq=np.r_[0.0,np.cumsum(x)]; peak=np.maximum.accumulate(eq); return float(np.max(peak-eq))

def pf(v):
    x=pd.to_numeric(v,errors='coerce').dropna().to_numpy(float); gp=x[x>0].sum(); gl=-x[x<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def metrics(ledger:pd.DataFrame,bps:float):
    col=f'net_r_{bps:g}bps'; v=pd.to_numeric(ledger[col],errors='coerce').dropna(); n=len(v)
    cum=float(v.sum()) if n else np.nan; dd=max_dd(v); st=ledger.loc[v.index,'state'] if n else pd.Series(dtype=str)
    return {'bps':bps,'n':int(n),'ev_r':float(v.mean()) if n else np.nan,'pf':pf(v),'win_rate':float((v>0).mean()) if n else np.nan,
            'cum_r':cum,'max_dd_r':dd,'recovery_factor':float(cum/dd) if n and np.isfinite(dd) and dd>0 else np.nan,
            'tp_rate':float((st=='TP').mean()) if n else np.nan,'sl_rate':float((st=='SL').mean()) if n else np.nan,'time_rate':float((st=='TIME').mean()) if n else np.nan,
            'dd_pct_at_025':float(dd*RISK_PCT) if np.isfinite(dd) else np.nan,'median_hold_hours':float(pd.to_numeric(ledger.loc[v.index,'hold_hours'],errors='coerce').median()) if n else np.nan}


def weekly_bootstrap_ev(ledger:pd.DataFrame,bps:float,seed:int):
    col=f'net_r_{bps:g}bps'; z=ledger[['entry_time',col]].copy(); z[col]=pd.to_numeric(z[col],errors='coerce'); z=z.dropna()
    if z.empty: return {'weeks':0,'ci_lo':np.nan,'ci_hi':np.nan,'p_positive':np.nan}
    t=pd.to_datetime(z.entry_time,utc=True,errors='coerce'); z=z.loc[t.notna()].copy(); t=t.loc[z.index]; z['_week']=t.dt.to_period('W-SUN').astype(str).values
    a=z.groupby('_week')[col].agg(['count','sum']).to_numpy(float); rng=np.random.default_rng(seed); vals=[]
    for _ in range(BOOT_N):
        s=a[rng.integers(0,len(a),size=len(a))].sum(axis=0)
        if s[0]>0: vals.append(s[1]/s[0])
    v=np.asarray(vals,float); return {'weeks':int(len(a)),'draws':BOOT_N,'ci_lo':float(np.quantile(v,.025)),'ci_hi':float(np.quantile(v,.975)),'p_positive':float(np.mean(v>0))}


def descriptive_boot_diff(buy:pd.DataFrame,sell:pd.DataFrame,bps:float):
    col=f'net_r_{bps:g}bps'
    def w(d):
        z=d[['entry_time',col]].dropna().copy(); t=pd.to_datetime(z.entry_time,utc=True); z['_w']=t.dt.to_period('W-SUN').astype(str); return z.groupby('_w')[col].agg(['count','sum']).reset_index()
    a=w(buy).rename(columns={'count':'an','sum':'asum'}); b=w(sell).rename(columns={'count':'bn','sum':'bsum'}); q=a.merge(b,on='_w',how='outer').fillna(0)
    if q.empty: return {'weeks':0,'ci_lo':np.nan,'ci_hi':np.nan,'p_positive':np.nan}
    arr=q[['an','asum','bn','bsum']].to_numpy(float); rng=np.random.default_rng(SEED+9); vals=[]
    for _ in range(BOOT_N):
        s=arr[rng.integers(0,len(arr),size=len(arr))].sum(axis=0)
        if s[0]>0 and s[2]>0: vals.append(s[1]/s[0]-s[3]/s[2])
    if not vals: return {'weeks':len(arr),'ci_lo':np.nan,'ci_hi':np.nan,'p_positive':np.nan}
    v=np.asarray(vals); return {'weeks':len(arr),'draws':BOOT_N,'ci_lo':float(np.quantile(v,.025)),'ci_hi':float(np.quantile(v,.975)),'p_positive':float(np.mean(v>0))}


def episode_diagnostic(ledger:pd.DataFrame,bps:float,seed:int):
    col=f'net_r_{bps:g}bps'; z=ledger.copy(); z['entry_time']=pd.to_datetime(z.entry_time); z['exit_time']=pd.to_datetime(z.exit_time); z=z.sort_values('entry_time').reset_index(drop=True)
    ep=[]; eid=-1; prev_exit=None
    for _,r in z.iterrows():
        if prev_exit is None or (r.entry_time-prev_exit)>pd.Timedelta(hours=72): eid+=1
        ep.append(eid); prev_exit=r.exit_time
    z['episode']=ep
    e=z.groupby('episode').agg(start=('entry_time','min'),end=('exit_time','max'),n=(col,'count'),r=(col,'sum')).reset_index()
    pos=e[e.r>0].r.sort_values(ascending=False); pos_sum=float(pos.sum())
    largest=float(pos.iloc[0]/pos_sum) if len(pos) and pos_sum>0 else np.nan; top3=float(pos.head(3).sum()/pos_sum) if len(pos) and pos_sum>0 else np.nan
    t=pd.to_datetime(z.entry_time,utc=True); z['_week']=t.dt.to_period('W-SUN').astype(str); z['_month']=t.dt.to_period('M').astype(str)
    ws=z.groupby('_week')[col].sum(); wp=ws[ws>0].sort_values(ascending=False); top10=float(wp.head(10).sum()/wp.sum()) if len(wp) and wp.sum()>0 else np.nan
    ms=z.groupby('_month')[col].sum(); mp=ms[ms>0]; bestmo=float(mp.max()/mp.sum()) if len(mp) and mp.sum()>0 else np.nan
    boot=weekly_bootstrap_ev(z,bps,seed)
    out={'episodes':int(len(e)),'positive_episode_fraction':float((e.r>0).mean()) if len(e) else np.nan,'median_episode_r':float(e.r.median()) if len(e) else np.nan,
         'episode_order_max_dd_r':max_dd(e.r),'largest_positive_episode_share':largest,'top3_positive_episode_share':top3,
         'top10_positive_weeks_share':top10,'best_positive_month_share':bestmo,'bootstrap':boot}
    out['support']=bool(out['episodes']>=20 and np.isfinite(largest) and largest<=.35 and np.isfinite(top3) and top3<=.60 and boot['p_positive']>=.90)
    return out,e,z


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--canonical-m1',required=True); ap.add_argument('--fresh-zip',required=True); ap.add_argument('--pool',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    lab006=load_lab006(); lab002=lab006.load_lab002(); router=lab002.load_router_module(); mech=load_mech()
    old=lab002.read_xau_native(Path(a.canonical_m1)); fresh,rawmeta=parse_daily_raw_zip(Path(a.fresh_zip))
    # Primary cap uses only preregistered through Aug-25 data.
    cap=min(pd.Timestamp(rawmeta['raw_max']),FRESH_CAP)
    hist=old[old.time<FRESH_START].copy(); cols=['time','open','high','low','close','volume']
    combined=pd.concat([hist[cols],fresh[cols]],ignore_index=True).drop_duplicates('time',keep='last').sort_values('time').reset_index(drop=True)
    cand=generate_h1_candidates(combined,mech); parity=validate_candidate_parity(cand,Path(a.pool))
    if not parity['exact']: raise RuntimeError(f'Historical H1 mechanics parity failed: {parity}')
    j=add_context(cand,combined,lab002,router)
    sel=j[(j.available_event_time>=FRESH_START)&(j.available_event_time<=cap)&j.is_high&j.bias_compat_label.eq('ALIGNED')].copy()
    events=build_fresh_events(sel,fresh,cap)
    if events.empty: events=pd.DataFrame(columns=['entry_time','exit_time','state','dir']+[f'net_r_{b:g}bps' for b in COST_BPS])
    br,buysk,buyres= None,None,None
    buy_routed,buy,buy_skipped=route_leg(events,1); sell_routed,sell,sell_skipped=route_leg(events,-1)

    costrows=[]
    for name,led in [('BUY',buy),('SELL',sell)]:
        for b in COST_BPS: costrows.append({'leg':name,**metrics(led,b)})
    cost=pd.DataFrame(costrows); cost.to_csv(out/'fresh_costs.csv',index=False)
    buy_m=metrics(buy,PRIMARY_BPS); sell_m=metrics(sell,PRIMARY_BPS)
    buy_b=weekly_bootstrap_ev(buy,PRIMARY_BPS,SEED+1) if len(buy) else {'weeks':0,'ci_lo':np.nan,'ci_hi':np.nan,'p_positive':np.nan}
    sell_b=weekly_bootstrap_ev(sell,PRIMARY_BPS,SEED+2) if len(sell) else {'weeks':0,'ci_lo':np.nan,'ci_hi':np.nan,'p_positive':np.nan}
    diff=descriptive_boot_diff(buy,sell,PRIMARY_BPS) if len(buy)>=5 and len(sell)>=5 else {'weeks':0,'ci_lo':np.nan,'ci_hi':np.nan,'p_positive':np.nan}

    hb=pd.read_csv(HIST_BUY); hs=pd.read_csv(HIST_SELL)
    bd,be,bz=episode_diagnostic(hb,PRIMARY_BPS,SEED+3); sd,se,sz=episode_diagnostic(hs,PRIMARY_BPS,SEED+4)
    be.to_csv(out/'historical_buy_episodes.csv',index=False); se.to_csv(out/'historical_sell_episodes.csv',index=False)
    buy_routed.to_csv(out/'fresh_buy_routed.csv',index=False); sell_routed.to_csv(out/'fresh_sell_routed.csv',index=False)
    sel.to_csv(out/'fresh_selected_candidates.csv',index=False); cost.to_csv(out/'fresh_cost_sensitivity.csv',index=False)

    spread_bps=10000.0*fresh.spread_mean/fresh.close
    spread={'median_bps':float(spread_bps.median()),'mean_bps':float(spread_bps.mean()),'p95_bps':float(spread_bps.quantile(.95))}
    legs={}
    for name,m,boot,diag,led,routed in [('BUY',buy_m,buy_b,bd,buy,buy_routed),('SELL',sell_m,sell_b,sd,sell,sell_routed)]:
        m5=cost[(cost.leg==name)&(cost.bps==5.0)].iloc[0].to_dict()
        directional=bool(m['n']>=5 and np.isfinite(m['ev_r']) and m['ev_r']>0 and np.isfinite(m['pf']) and m['pf']>1.0)
        usable=bool(m['n']>=20 and m['ev_r']>0 and m['pf']>=1.10)
        native_next=bool(directional and diag['support'] and m5['ev_r']>0 and m5['pf']>1.0 and m['dd_pct_at_025']<=4.0)
        legs[name]={'primary':m,'bootstrap':boot,'fresh_directionally_positive':directional,'fresh_statistically_usable':usable,
                    'historical_episode':diag,'fresh_support_for_native_replication':native_next,
                    'routed_n':int(len(routed)),'resolved_n':int(len(led)),'censored_n':int((routed.state=='CENSORED').sum()) if len(routed) else 0}
    if legs['BUY']['fresh_support_for_native_replication'] and legs['SELL']['fresh_support_for_native_replication']: verdict='BOTH_LEGS_FRESH_SUPPORT_FOR_NATIVE_REPLICATION'
    elif legs['BUY']['fresh_support_for_native_replication']: verdict='BUY_FRESH_SUPPORT_SELL_NOT_SUPPORTED'
    elif legs['SELL']['fresh_support_for_native_replication']: verdict='SELL_FRESH_SUPPORT_BUY_NOT_SUPPORTED'
    elif legs['BUY']['fresh_directionally_positive'] or legs['SELL']['fresh_directionally_positive']: verdict='FRESH_MIXED_SHORT_TAIL'
    else: verdict='FRESH_OOS_NOT_SUPPORTIVE'
    summary={'lab':LAB,'status':'FRESH_OOS_PREREGISTERED_BOTH_LEGS','verdict':verdict,'promotion_authorized':False,
             'fresh_window':[str(FRESH_START),str(cap)],'raw_meta':rawmeta,'historical_mechanics_parity':parity,'fresh_spread':spread,
             'selected_rows':int(len(sel)),'selected_buy':int((sel.dir==1).sum()),'selected_sell':int((sel.dir==-1).sum()),
             'legs':legs,'fresh_buy_sell_bootstrap_diff':diff}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
    lines=[f'# {LAB}','',f'**Verdict: {verdict}**','',f'- Historical H1 mechanics parity: **{parity}**',
           f"- Fresh raw: {rawmeta['raw_min']} -> {rawmeta['raw_max']} | M1={rawmeta['m1_rows']}",
           f"- Fresh spread median/mean/p95: **{spread['median_bps']:.3f}/{spread['mean_bps']:.3f}/{spread['p95_bps']:.3f} bps**",
           f"- HIGH+ALIGNED selected: BUY **{(sel.dir==1).sum()}**, SELL **{(sel.dir==-1).sum()}**",'']
    for name in ['BUY','SELL']:
        x=legs[name]; m=x['primary']; e=x['historical_episode']; lines += [f'## {name}',
          f"- Fresh routed/resolved/censored: **{x['routed_n']}/{x['resolved_n']}/{x['censored_n']}**",
          f"- Fresh 2bps: N={m['n']}, EV **{m['ev_r']:+.5f}R**, PF **{m['pf']:.3f}**, CumR {m['cum_r']:+.2f}R, DD@0.25% {m['dd_pct_at_025']:.2f}%",
          f"- Fresh directionally positive: **{x['fresh_directionally_positive']}** | statistically usable: **{x['fresh_statistically_usable']}**",
          f"- Historical episodes: N={e['episodes']}, positive {e['positive_episode_fraction']:.1%}, largest+ share {e['largest_positive_episode_share']:.3f}, top3+ share {e['top3_positive_episode_share']:.3f}, weekly P(EV>0)={e['bootstrap']['p_positive']:.3f}, support **{e['support']}**",
          f"- Fresh support for native replication: **{x['fresh_support_for_native_replication']}**",'']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print('\n'.join(lines))

if __name__=='__main__': main()
