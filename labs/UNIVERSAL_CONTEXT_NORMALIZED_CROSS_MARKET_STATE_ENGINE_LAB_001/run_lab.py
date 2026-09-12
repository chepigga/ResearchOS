#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

LAB = 'UNIVERSAL_CONTEXT_NORMALIZED_CROSS_MARKET_STATE_ENGINE_LAB_001'
STATES = ['EXPANSION','PULLBACK','RANGE','REVERSAL']
ALL_STATES = STATES + ['TRANSITION']
ROLL = 252
MINROLL = 126
BOOT_N = 5000
SEED = 2026091201
BTC_START = '2021-01'
BTC_END = '2026-07'
COMMON_START = pd.Timestamp('2023-06-01')
COMMON_END = pd.Timestamp('2026-07-17 23:59:59')


def wilder(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1.0/n, adjust=False, min_periods=n).mean()


def causal_pct(s: pd.Series) -> pd.Series:
    return s.rolling(ROLL, min_periods=MINROLL).rank(pct=True)


def read_generic_m1(path: Path, symbol: str) -> pd.DataFrame:
    first = path.open('r', encoding='utf-8', errors='ignore').readline()
    counts = {',': first.count(','), ';': first.count(';'), '\t': first.count('\t')}
    sep = max(counts, key=counts.get)
    raw = pd.read_csv(path, sep=sep, low_memory=False)
    lut = {str(c).strip().lower(): c for c in raw.columns}

    def get(names):
        for n in names:
            if n.lower() in lut:
                return raw[lut[n.lower()]]
        return None

    ts = get(['time','timestamp','datetime','date_time'])
    if ts is None:
        ds = get(['date','<date>'])
        tm = get(['<time>'])
        if ds is not None and tm is not None:
            ts = ds.astype(str).str.strip() + ' ' + tm.astype(str).str.strip()
        elif ds is not None:
            ts = ds
    if ts is None:
        raise RuntimeError(f'{symbol}: no time/date column; columns={list(raw.columns)[:20]}')

    out = pd.DataFrame({'time': pd.to_datetime(ts, errors='coerce')})
    aliases = {
        'open':['open','bid_open','<open>'],
        'high':['high','bid_high','<high>'],
        'low':['low','bid_low','<low>'],
        'close':['close','bid_close','<close>'],
    }
    for dst,names in aliases.items():
        x=get(names)
        if x is None:
            raise RuntimeError(f'{symbol}: missing {dst}; columns={list(raw.columns)[:20]}')
        out[dst]=pd.to_numeric(x,errors='coerce')
    out=out.dropna().drop_duplicates('time').sort_values('time').reset_index(drop=True)
    return out


def to_h4(m1: pd.DataFrame) -> pd.DataFrame:
    return (m1.set_index('time').sort_index()
            .resample('4h', origin='epoch', label='left', closed='left')
            .agg(open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last'))
            .dropna())


def fetch_btc_h1(start=BTC_START,end=BTC_END) -> tuple[pd.DataFrame,dict]:
    months=pd.period_range(start,end,freq='M')
    cols=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_base','taker_quote','ignore']
    frames=[]; missing=[]
    sess=requests.Session(); sess.headers.update({'User-Agent':'ResearchOS-universal-context/1.0'})
    for p in months:
        ym=str(p)
        url=f'https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{ym}.zip'
        try:
            r=sess.get(url,timeout=45)
            if r.status_code!=200:
                missing.append({'month':ym,'status':r.status_code}); continue
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                name=z.namelist()[0]
                frames.append(pd.read_csv(z.open(name),header=None,names=cols,low_memory=False))
        except Exception as e:
            missing.append({'month':ym,'status':str(e)})
    if not frames:
        raise RuntimeError('BTC: no Binance archive data')
    x=pd.concat(frames,ignore_index=True)
    ot=pd.to_numeric(x.open_time,errors='coerce')
    med=float(ot.dropna().median()); unit='us' if med>1e14 else 'ms'
    x['time']=pd.to_datetime(ot,unit=unit,utc=True,errors='coerce').dt.tz_convert(None)
    for c in ['open','high','low','close']:
        x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x[['time','open','high','low','close']].dropna().drop_duplicates('time').sort_values('time')
    meta={'missing_months':missing,'rows_h1':len(x),'first':str(x.time.min()),'last':str(x.time.max())}
    return x,meta


def btc_to_h4(h1: pd.DataFrame) -> pd.DataFrame:
    return (h1.set_index('time').sort_index()
            .resample('4h',origin='epoch',label='left',closed='left')
            .agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna())


def add_features(h4: pd.DataFrame) -> pd.DataFrame:
    d=h4.copy().sort_index()
    pc=d.close.shift(1)
    tr=pd.concat([(d.high-d.low).abs(),(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1)
    d['atr14']=wilder(tr,14)
    for n in [20,50,200]:
        d[f'ema{n}']=d.close.ewm(span=n,adjust=False,min_periods=n).mean()
    d['slope50_atr']=(d.ema50-d.ema50.shift(3))/d.atr14.replace(0,np.nan)

    delta=d.close.diff(); gain=delta.clip(lower=0); loss=(-delta).clip(lower=0)
    rs=wilder(gain,14)/wilder(loss,14).replace(0,np.nan)
    d['rsi14']=100-100/(1+rs)

    up=d.high.diff(); dn=-d.low.diff()
    plus_dm=pd.Series(np.where((up>dn)&(up>0),up,0.0),index=d.index)
    minus_dm=pd.Series(np.where((dn>up)&(dn>0),dn,0.0),index=d.index)
    plus_di=100*wilder(plus_dm,14)/d.atr14.replace(0,np.nan)
    minus_di=100*wilder(minus_dm,14)/d.atr14.replace(0,np.nan)
    dx=100*(plus_di-minus_di).abs()/(plus_di+minus_di).replace(0,np.nan)
    d['adx14']=wilder(dx,14)

    d['prior_hi20']=d.high.rolling(20,min_periods=20).max().shift(1)
    d['prior_lo20']=d.low.rolling(20,min_periods=20).min().shift(1)
    d['breakout']=(d.close>d.prior_hi20)|(d.close<d.prior_lo20)
    d['sweep']=((d.high>d.prior_hi20)&(d.close<d.prior_hi20))|((d.low<d.prior_lo20)&(d.close>d.prior_lo20))

    r24=d.high.rolling(24,min_periods=24).max()-d.low.rolling(24,min_periods=24).min()
    d['range24_atr']=r24/d.atr14.replace(0,np.nan)
    spread=pd.concat([d.ema20,d.ema50,d.ema200],axis=1).max(axis=1)-pd.concat([d.ema20,d.ema50,d.ema200],axis=1).min(axis=1)
    d['ema_spread_atr']=spread/d.atr14.replace(0,np.nan)
    d['dist20_atr']=(d.close-d.ema20).abs()/d.atr14.replace(0,np.nan)

    absdiff=d.close.diff().abs()
    d['er12']=(d.close-d.close.shift(12)).abs()/absdiff.rolling(12,min_periods=12).sum().replace(0,np.nan)

    cr=(d.high-d.low).replace(0,np.nan)
    upper=d.high-pd.concat([d.open,d.close],axis=1).max(axis=1)
    lower=pd.concat([d.open,d.close],axis=1).min(axis=1)-d.low
    d['rejection_wick']=pd.concat([upper,lower],axis=1).max(axis=1)/cr
    d['cross_ema20']=((d.close-d.ema20)*(d.close.shift(1)-d.ema20.shift(1))<0)

    d['stack_up']=(d.ema20>d.ema50)&(d.ema50>d.ema200)&(d.slope50_atr>0)
    d['stack_dn']=(d.ema20<d.ema50)&(d.ema50<d.ema200)&(d.slope50_atr<0)
    d['stack']=d.stack_up|d.stack_dn
    d['trend_dir']=np.select([d.stack_up,d.stack_dn],[1,-1],default=0).astype(int)

    d['p_atr']=causal_pct(d.atr14/d.close.replace(0,np.nan))
    d['p_adx']=causal_pct(d.adx14)
    d['p_range']=causal_pct(d.range24_atr)
    d['p_spread']=causal_pct(d.ema_spread_atr)
    d['p_dist20']=causal_pct(d.dist20_atr)
    d['p_er']=causal_pct(d.er12)
    d['p_slope']=causal_pct(d.slope50_atr.abs())
    d['p_wick']=causal_pct(d.rejection_wick)
    d['p_rsi']=causal_pct(d.rsi14)
    d['rsi_central']=(1-2*(d.p_rsi-.5).abs()).clip(0,1)
    d['rsi_turn']=(((d.p_rsi.shift(1)<.20)&(d.rsi14>d.rsi14.shift(1)))|
                   ((d.p_rsi.shift(1)>.80)&(d.rsi14<d.rsi14.shift(1))))
    d['adx_falling']=d.adx14<d.adx14.shift(1)
    d['stack_exists']=d['stack']|d['stack'].shift(1).fillna(False)
    return d


def add_state_engine(h4: pd.DataFrame) -> pd.DataFrame:
    d=add_features(h4)
    ready_cols=['ema200','atr14','rsi14','adx14','p_atr','p_adx','p_range','p_spread','p_dist20','p_er','p_slope','p_wick','p_rsi']
    ready=d[ready_cols].notna().all(axis=1)

    s=pd.DataFrame(index=d.index,dtype=float)
    s['EXPANSION']=(25*d.stack.astype(float)+15*d.breakout.astype(float)+15*d.p_atr+15*d.p_adx+10*d.p_range+10*d.p_er+10*d.p_dist20)
    s['PULLBACK']=(25*d.stack.astype(float)+25*(1-d.p_dist20)+15*d.p_adx+15*d.p_slope+10*d.rsi_central+10*(~d.breakout).astype(float))
    s['RANGE']=(25*(1-d.p_adx)+20*(1-d.p_spread)+20*(1-d.p_range)+15*(1-d.p_er)+10*(1-d.p_atr)+10*(~d.stack).astype(float))
    s['REVERSAL']=(25*d.sweep.astype(float)+15*d.cross_ema20.astype(float)+20*d.p_wick+20*d.rsi_turn.astype(float)+10*d.adx_falling.astype(float)+10*d.stack_exists.astype(float))
    s=s.where(ready,np.nan)
    sm=s.rolling(3,min_periods=3).mean()

    arr=sm.to_numpy(float)
    states=[]; gaps=[]; tops=[]
    cols=list(sm.columns)
    for row in arr:
        if not np.isfinite(row).any():
            states.append(None); gaps.append(np.nan); tops.append(np.nan); continue
        vals=np.where(np.isfinite(row),row,-np.inf)
        order=np.argsort(vals)
        top_i=int(order[-1]); second_i=int(order[-2])
        top=float(vals[top_i]); gap=float(top-vals[second_i])
        state='TRANSITION' if (top<50 or gap<8) else cols[top_i]
        states.append(state); gaps.append(gap); tops.append(top)
    d['regime']=states; d['score_gap']=gaps; d['top_score']=tops
    for c in STATES: d[f'score_{c.lower()}']=sm[c]
    d['available_time']=d.index+pd.Timedelta(hours=4)
    return d


def add_forward(d: pd.DataFrame) -> pd.DataFrame:
    z=d.copy().sort_index(); idx=pd.Series(z.index,index=z.index)
    atr=z.atr14.replace(0,np.nan)
    for n,hours in [(2,8),(3,12),(6,24)]:
        contiguous=pd.Series(True,index=z.index)
        highs=[]; lows=[]
        for i in range(1,n+1):
            contiguous &= idx.shift(-i).eq(idx+pd.Timedelta(hours=4*i))
            highs.append(z.high.shift(-i)); lows.append(z.low.shift(-i))
        fhi=pd.concat(highs,axis=1).max(axis=1).where(contiguous)
        flo=pd.concat(lows,axis=1).min(axis=1).where(contiguous)
        fclose=z.close.shift(-n).where(contiguous)
        ret=((fclose-z.close)/atr).where(contiguous)
        z[f'close_ret_{hours}h_atr']=ret
        z[f'range{hours}_atr']=((fhi-flo)/atr).where(contiguous)
        z[f'absclose{hours}_atr']=ret.abs()
    z['signed8_atr']=(z.trend_dir*z.close_ret_8h_atr).where(z.trend_dir.ne(0))
    z['signed24_atr']=(z.trend_dir*z.close_ret_24h_atr).where(z.trend_dir.ne(0))
    prior_dir=z.trend_dir.shift(1)
    z['reverse12_atr']=(-prior_dir*z.close_ret_12h_atr).where(prior_dir.ne(0))
    return z


def state_occupancy(d: pd.DataFrame, market: str) -> pd.DataFrame:
    q=d[d.regime.isin(ALL_STATES)].copy(); n=len(q)
    rows=[]
    for st in ALL_STATES:
        k=int(q.regime.eq(st).sum())
        rows.append({'market':market,'state':st,'n':k,'occupancy':k/n if n else np.nan})
    return pd.DataFrame(rows)


def effect_diff(d: pd.DataFrame, market: str, state: str, metric: str) -> dict:
    q=d[d.regime.isin(ALL_STATES)][['available_time','regime',metric]].dropna().copy()
    a=q[q.regime.eq(state)][metric]; b=q[~q.regime.eq(state)][metric]
    return {'market':market,'state':state,'metric':metric,'n_state':len(a),'n_other':len(b),
            'mean_state':float(a.mean()) if len(a) else np.nan,'mean_other':float(b.mean()) if len(b) else np.nan,
            'effect':float(a.mean()-b.mean()) if len(a) and len(b) else np.nan}


def one_mean(d: pd.DataFrame, market: str, state: str, metric: str, require_dir=False) -> dict:
    q=d[d.regime.eq(state)].copy()
    if require_dir: q=q[q.trend_dir.ne(0)]
    v=pd.to_numeric(q[metric],errors='coerce').dropna()
    return {'market':market,'state':state,'metric':metric,'n':len(v),'mean':float(v.mean()) if len(v) else np.nan}


def week_key(df: pd.DataFrame) -> pd.Series:
    return df.market.astype(str)+'|'+pd.to_datetime(df.available_time).dt.to_period('W-SUN').astype(str)


def pooled_boot_diff(all_df: pd.DataFrame,state: str,metric: str,seed: int) -> dict:
    q=all_df[all_df.regime.isin(ALL_STATES)][['market','available_time','regime',metric]].copy()
    q[metric]=pd.to_numeric(q[metric],errors='coerce'); q=q.dropna(subset=[metric])
    q['is_state']=q.regime.eq(state); q['cluster']=week_key(q)
    a=q[q.is_state][metric]; b=q[~q.is_state][metric]
    obs=float(a.mean()-b.mean()) if len(a) and len(b) else np.nan
    stats=[]
    for _,g in q.groupby('cluster'):
        aa=g[g.is_state][metric].to_numpy(float); bb=g[~g.is_state][metric].to_numpy(float)
        stats.append([len(aa),np.nansum(aa),len(bb),np.nansum(bb)])
    arr=np.asarray(stats,float); rng=np.random.default_rng(seed); draws=[]; m=len(arr)
    for _ in range(BOOT_N):
        x=arr[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0 and x[2]>0: draws.append(x[1]/x[0]-x[3]/x[2])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)) if len(dr) else np.nan,
            'ci_hi':float(np.quantile(dr,.975)) if len(dr) else np.nan,'n_state':len(a),'n_other':len(b),'clusters':m}


def pooled_boot_mean(all_df: pd.DataFrame,state: str,metric: str,seed: int,require_dir=False) -> dict:
    q=all_df[all_df.regime.eq(state)][['market','available_time','trend_dir',metric]].copy()
    if require_dir: q=q[q.trend_dir.ne(0)]
    q[metric]=pd.to_numeric(q[metric],errors='coerce'); q=q.dropna(subset=[metric])
    q['cluster']=week_key(q); obs=float(q[metric].mean()) if len(q) else np.nan
    stats=q.groupby('cluster')[metric].agg(['count','sum']).to_numpy(float)
    rng=np.random.default_rng(seed); draws=[]; m=len(stats)
    for _ in range(BOOT_N):
        x=stats[rng.integers(0,m,size=m)].sum(axis=0)
        if x[0]>0: draws.append(x[1]/x[0])
    dr=np.asarray(draws,float)
    return {'observed':obs,'ci_lo':float(np.quantile(dr,.025)) if len(dr) else np.nan,
            'ci_hi':float(np.quantile(dr,.975)) if len(dr) else np.nan,'n':len(q),'clusters':m}


def episodes(d: pd.DataFrame, market: str) -> pd.DataFrame:
    q=d[d.regime.isin(ALL_STATES)].copy().sort_index(); idx=pd.Series(q.index,index=q.index)
    new=q.regime.ne(q.regime.shift(1))|idx.diff().ne(pd.Timedelta(hours=4))
    q['episode_id']=new.cumsum(); e=q.groupby('episode_id').agg(state=('regime','first'),bars=('regime','size')).reset_index(drop=True)
    e['market']=market
    return e[['market','state','bars']]


def evaluate(markets: dict[str,pd.DataFrame], out: Path):
    frames=[]; occ=[]; eps=[]; meta_rows=[]
    for market,h4 in markets.items():
        z=add_forward(add_state_engine(h4)); z['market']=market
        ready=z[z.regime.isin(ALL_STATES)].copy()
        frames.append(ready); occ.append(state_occupancy(z,market)); eps.append(episodes(z,market))
        meta_rows.append({'market':market,'h4_rows':len(h4),'ready_bars':len(ready),'first':str(h4.index.min()),'last':str(h4.index.max())})
    all_df=pd.concat(frames).sort_values(['market','available_time'])
    occupancy=pd.concat(occ,ignore_index=True); episode_df=pd.concat(eps,ignore_index=True); market_meta=pd.DataFrame(meta_rows)

    effects=[]
    for market,z in all_df.groupby('market'):
        effects.append(effect_diff(z,market,'EXPANSION','range8_atr'))
        effects.append(effect_diff(z,market,'RANGE','range8_atr'))
        effects.append(one_mean(z,market,'PULLBACK','signed24_atr',True))
        effects.append(one_mean(z,market,'EXPANSION','signed8_atr',True))
        effects.append(one_mean(z,market,'REVERSAL','reverse12_atr',False))
    effects=pd.DataFrame(effects)

    pool_exp=pooled_boot_diff(all_df,'EXPANSION','range8_atr',SEED+1)
    pool_range=pooled_boot_diff(all_df,'RANGE','range8_atr',SEED+2)
    pool_pb=pooled_boot_mean(all_df,'PULLBACK','signed24_atr',SEED+3,True)
    pool_expdir=pooled_boot_mean(all_df,'EXPANSION','signed8_atr',SEED+4,True)
    pool_rev=pooled_boot_mean(all_df,'REVERSAL','reverse12_atr',SEED+5,False)

    def rows_metric(state,metric):
        return effects[(effects.state==state)&(effects.metric==metric)]
    ex=rows_metric('EXPANSION','range8_atr'); rg=rows_metric('RANGE','range8_atr')
    pb=rows_metric('PULLBACK','signed24_atr'); ed=rows_metric('EXPANSION','signed8_atr')

    h1=bool(len(ex)==3 and (ex.n_state>=100).all() and (ex.effect>0).all() and np.isfinite(pool_exp['ci_lo']) and pool_exp['ci_lo']>0)
    h2=bool(len(rg)==3 and (rg.n_state>=100).all() and (rg.effect<0).all() and np.isfinite(pool_range['ci_hi']) and pool_range['ci_hi']<0)
    h3=bool(len(pb)==3 and (pb.n>=100).all() and int((pb['mean']>0).sum())>=2 and np.isfinite(pool_pb['ci_lo']) and pool_pb['ci_lo']>0)
    h4=bool(len(ed)==3 and (ed.n>=100).all() and int((ed['mean']>0).sum())>=2 and np.isfinite(pool_expdir['ci_lo']) and pool_expdir['ci_lo']>0)

    h5_parts=[]
    for market,g in occupancy.groupby('market'):
        core=g[g.state.isin(STATES)].set_index('state').occupancy
        trans=float(g.loc[g.state.eq('TRANSITION'),'occupancy'].iloc[0])
        ok=(int((core>=.03).sum())>=3 and float(core.max())<=.75 and trans<=.50)
        h5_parts.append((market,ok,int((core>=.03).sum()),float(core.max()),trans))
    h5=bool(all(x[1] for x in h5_parts) and len(h5_parts)==3)

    primary=[h1,h2,h3,h4]
    if h1 and h2 and h3 and h4 and h5: verdict='UNIVERSAL_STATE_ENGINE_SUPPORTED'
    elif h5 and sum(primary)>=3: verdict='UNIVERSAL_STATE_ENGINE_PARTIAL_SUPPORT'
    else: verdict='UNIVERSAL_STATE_ENGINE_NOT_SUPPORTED'

    # Common-window diagnostics only.
    cw=all_df[(all_df.available_time>=COMMON_START)&(all_df.available_time<=COMMON_END)].copy()
    common=[]
    for market,z in cw.groupby('market'):
        common.append(effect_diff(z,market,'EXPANSION','range8_atr'))
        common.append(effect_diff(z,market,'RANGE','range8_atr'))
        common.append(one_mean(z,market,'PULLBACK','signed24_atr',True))
        common.append(one_mean(z,market,'EXPANSION','signed8_atr',True))
    common=pd.DataFrame(common)

    # Yearly occupancy.
    yrows=[]
    yy=all_df.copy(); yy['year']=pd.to_datetime(yy.available_time).dt.year
    for (market,year),g in yy.groupby(['market','year']):
        n=len(g)
        for st in ALL_STATES:
            k=int(g.regime.eq(st).sum()); yrows.append({'market':market,'year':int(year),'state':st,'n':k,'occupancy':k/n if n else np.nan})
    yearly=pd.DataFrame(yrows)

    summary={
        'lab':LAB,'verdict':verdict,
        'h1_expansion_range_pass':h1,'h2_range_compression_pass':h2,
        'h3_pullback_continuation_pass':h3,'h4_expansion_direction_pass':h4,'h5_state_breadth_pass':h5,
        'primary_pass_count':int(sum(primary)),
        'pool_expansion_range':pool_exp,'pool_range_range':pool_range,
        'pool_pullback_signed24':pool_pb,'pool_expansion_signed8':pool_expdir,'pool_reversal_reverse12':pool_rev,
        'h5_by_market':[{'market':a,'pass':b,'core_states_ge3pct':c,'max_core_occ':d,'transition_occ':e} for a,b,c,d,e in h5_parts],
        'common_window_start':str(COMMON_START),'common_window_end':str(COMMON_END)
    }

    out.mkdir(parents=True,exist_ok=True)
    market_meta.to_csv(out/'market_meta.csv',index=False)
    occupancy.to_csv(out/'occupancy.csv',index=False)
    effects.to_csv(out/'semantic_effects.csv',index=False)
    common.to_csv(out/'common_window_effects.csv',index=False)
    episode_df.to_csv(out/'episodes.csv',index=False)
    yearly.to_csv(out/'yearly_occupancy.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    def pct(x): return 'nan' if not np.isfinite(x) else f'{100*x:.1f}%'
    lines=[f'# {LAB}',f'**Verdict: {verdict}**','',
           '## Primary gates',
           f'- H1 EXPANSION future range: **{"PASS" if h1 else "FAIL"}** — pooled effect {pool_exp["observed"]:+.3f} ATR, CI [{pool_exp["ci_lo"]:+.3f}, {pool_exp["ci_hi"]:+.3f}].',
           f'- H2 RANGE compression: **{"PASS" if h2 else "FAIL"}** — pooled effect {pool_range["observed"]:+.3f} ATR, CI [{pool_range["ci_lo"]:+.3f}, {pool_range["ci_hi"]:+.3f}].',
           f'- H3 PULLBACK 24h trend follow-through: **{"PASS" if h3 else "FAIL"}** — pooled mean {pool_pb["observed"]:+.3f} ATR, CI [{pool_pb["ci_lo"]:+.3f}, {pool_pb["ci_hi"]:+.3f}].',
           f'- H4 EXPANSION 8h trend continuation: **{"PASS" if h4 else "FAIL"}** — pooled mean {pool_expdir["observed"]:+.3f} ATR, CI [{pool_expdir["ci_lo"]:+.3f}, {pool_expdir["ci_hi"]:+.3f}].',
           f'- H5 state breadth: **{"PASS" if h5 else "FAIL"}**.','',
           '## Market data / ready bars','',market_meta.to_markdown(index=False),'',
           '## State occupancy','',occupancy.pivot(index='market',columns='state',values='occupancy').to_markdown(floatfmt='.3f'),'',
           '## Per-market semantic effects','',effects.to_markdown(index=False,floatfmt='.4f'),'',
           '## H5 detail','']
    for a,b,c,d,e in h5_parts:
        lines.append(f'- {a}: {"PASS" if b else "FAIL"}; core>=3%: {c}/4; max core={pct(d)}; transition={pct(e)}.')
    lines += ['', '## Secondary REVERSAL pooled diagnostic',
              f'- reverse12 mean: {pool_rev["observed"]:+.3f} ATR, CI [{pool_rev["ci_lo"]:+.3f}, {pool_rev["ci_hi"]:+.3f}], N={pool_rev["n"]}.','',
              '## Common-window robustness (diagnostic only)','',common.to_markdown(index=False,floatfmt='.4f'),'',
              '## Boundary','No asset-specific threshold or outcome-driven retuning was used. This LAB validates state semantics only; it does not establish setup confirmation, entry timing, profit probability, or prop-firm execution economics.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2,default=str))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau',required=True); ap.add_argument('--eur',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out)
    xau=read_generic_m1(Path(args.xau),'XAUUSD'); eur=read_generic_m1(Path(args.eur),'EURUSD')
    btc_h1,btc_meta=fetch_btc_h1()
    if btc_meta['missing_months']:
        (out/'btc_missing.json').parent.mkdir(parents=True,exist_ok=True); (out/'btc_missing.json').write_text(json.dumps(btc_meta,indent=2))
        raise RuntimeError(f'BTC missing months: {btc_meta["missing_months"][:5]}')
    markets={'XAUUSD':to_h4(xau),'BTCUSDT':btc_to_h4(btc_h1),'EURUSD':to_h4(eur)}
    if any(len(v)<500 for v in markets.values()):
        raise RuntimeError({k:len(v) for k,v in markets.items()})
    evaluate(markets,out)

if __name__=='__main__':
    main()
