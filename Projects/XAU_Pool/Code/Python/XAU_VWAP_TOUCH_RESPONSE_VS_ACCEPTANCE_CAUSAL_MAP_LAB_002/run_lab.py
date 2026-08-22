#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_VWAP_TOUCH_RESPONSE_VS_ACCEPTANCE_CAUSAL_MAP_LAB_002'
VERSION='v001'
CANONICAL='XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv'
SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
HOLDOUT=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
ANCHOR_HOUR=1
BAND_K=1.618
TOUCH_ATR=.05
REARM_ATR=.25
FEATURE_MIN=5
OUTCOME_MIN=60
PRIMARY_BARRIER=.50
SENS_BARRIERS=(.25,.50,.75)
FVG_LIFETIME_MIN=240
IFVG_RETEST_MAX_MIN=30


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load(path:Path)->pd.DataFrame:
    df=pd.read_csv(path,sep=';')
    cols=['time','open','high','low','close','ask_high','ask_low','ask_close','tick_volume','spread_mean']
    miss=[c for c in ['time','open','high','low','close','tick_volume'] if c not in df.columns]
    if miss: raise ValueError(f'missing {miss}')
    keep=[c for c in cols if c in df.columns]
    df=df[keep].copy()
    df['time']=pd.to_datetime(df.time,format='%Y.%m.%d %H:%M',errors='coerce')
    for c in df.columns:
        if c!='time': df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    return df


def wilder_atr(h,l,c,n=14):
    pc=c.shift(1)
    tr=pd.concat([(h-l),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()


def add_atr(df):
    x=df.set_index('time')
    m=x.resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna()
    m['atr']=wilder_atr(m.high,m.low,m.close)
    a=m[['atr']].reset_index(); a['avail']=a.time+pd.Timedelta(minutes=15)
    a=a[['avail','atr']].dropna().sort_values('avail')
    return pd.merge_asof(df.sort_values('time'),a,left_on='time',right_on='avail',direction='backward').drop(columns='avail')


def add_vwap(df):
    o=df.copy(); o['session']=(o.time-pd.Timedelta(hours=ANCHOR_HOUR)).dt.floor('D')
    p=(o.high+o.low+o.close)/3.0; v=o.tick_volume.fillna(0).clip(lower=0)
    gv=v.groupby(o.session).cumsum(); gpv=(p*v).groupby(o.session).cumsum(); gp2=((p*p)*v).groupby(o.session).cumsum()
    mid=gpv/gv.replace(0,np.nan); var=(gp2/gv.replace(0,np.nan)-mid*mid).clip(lower=0); sd=np.sqrt(var)
    o['MID']=mid; o['HIGH']=mid+BAND_K*sd; o['LOW']=mid-BAND_K*sd; o['band_width_atr']=(2*BAND_K*sd)/o.atr
    o['vwap_slope5_atr']=(mid-mid.shift(5))/o.atr
    return o


def build_ifvg_events(df):
    h,l,c=df.high.to_numpy(float),df.low.to_numpy(float),df.close.to_numpy(float); n=len(df); rows=[]
    bull=np.flatnonzero(l[2:]>h[:-2])+2; bear=np.flatnonzero(h[2:]<l[:-2])+2
    for born in bull:
        lower=float(h[born-2]); upper=float(l[born]); e=min(n,born+1+FVG_LIFETIME_MIN)
        rr=np.flatnonzero(c[born+1:e]<lower)
        if not len(rr): continue
        inv=born+1+int(rr[0]); re=min(n,inv+1+IFVG_RETEST_MAX_MIN)
        m=(h[inv+1:re]>=lower)&(l[inv+1:re]<=upper)&(c[inv+1:re]<lower); q=np.flatnonzero(m)
        if len(q): rows.append((inv+1+int(q[0]),-1,born,inv,lower,upper))
    for born in bear:
        lower=float(h[born]); upper=float(l[born-2]); e=min(n,born+1+FVG_LIFETIME_MIN)
        rr=np.flatnonzero(c[born+1:e]>upper)
        if not len(rr): continue
        inv=born+1+int(rr[0]); re=min(n,inv+1+IFVG_RETEST_MAX_MIN)
        m=(l[inv+1:re]<=upper)&(h[inv+1:re]>=lower)&(c[inv+1:re]>upper); q=np.flatnonzero(m)
        if len(q): rows.append((inv+1+int(q[0]),1,born,inv,lower,upper))
    if not rows: return pd.DataFrame(columns=['i','dir'])
    z=pd.DataFrame(rows,columns=['i','dir','born','inv','lower','upper']); z['w']=z.upper-z.lower
    return z.sort_values(['i','dir','w','born']).drop_duplicates(['i','dir']).drop(columns='w').reset_index(drop=True)


def detect_touches(df, level_name):
    level=df[level_name].to_numpy(float); atr=df.atr.to_numpy(float); lo=df.low.to_numpy(float); hi=df.high.to_numpy(float); cl=df.close.to_numpy(float)
    n=len(df); armed=True; rows=[]; touch_no={}
    for i in range(6,n-OUTCOME_MIN-2):
        if not np.isfinite(level[i]) or not np.isfinite(atr[i]) or atr[i]<=0: continue
        dist=abs(cl[i]-level[i])/atr[i]
        if not armed:
            if dist>=REARM_ATR: armed=True
            else: continue
        near=(lo[i] <= level[i]+TOUCH_ATR*atr[i]) and (hi[i] >= level[i]-TOUCH_ATR*atr[i])
        if not near: continue
        arr=0
        for j in range(i-1,max(-1,i-6),-1):
            if not np.isfinite(level[j]) or not np.isfinite(atr[j]) or atr[j]<=0: continue
            d=(cl[j]-level[j])/atr[j]
            if abs(d)>TOUCH_ATR:
                arr=1 if d>0 else -1; break
        if arr==0: continue
        sess=df.at[i,'session']; key=(sess,level_name); tn=touch_no.get(key,0)+1; touch_no[key]=tn
        rows.append((i,level_name,arr,tn)); armed=False
    return rows


def label_barrier(df,i,arr,L0,atr0,b):
    start=i+FEATURE_MIN+1
    t_end=df.at[i,'time']+pd.Timedelta(minutes=OUTCOME_MIN)
    times=df.time.to_numpy(dtype='datetime64[ns]'); end=int(np.searchsorted(times,np.datetime64(t_end),side='right'))
    end=min(end,len(df));
    if start>=end: return 'UNRESOLVED'
    h=df.high.to_numpy(float)[start:end]; l=df.low.to_numpy(float)[start:end]
    rej=L0+arr*b*atr0; acc=L0-arr*b*atr0
    if arr>0:
        r=np.flatnonzero(h>=rej); a=np.flatnonzero(l<=acc)
    else:
        r=np.flatnonzero(l<=rej); a=np.flatnonzero(h>=acc)
    pr=int(r[0]) if len(r) else 10**9; pa=int(a[0]) if len(a) else 10**9
    if pr==pa and pr<10**9: return 'AMBIGUOUS'
    if pr<pa: return 'REJECTION'
    if pa<pr: return 'ACCEPTANCE'
    return 'UNRESOLVED'


def features_for_touch(df,i,level_name,arr,ifvg_idx,prev_touch_time):
    if i+FEATURE_MIN>=len(df): return None
    for k in range(1,FEATURE_MIN+1):
        if df.at[i+k,'time'] != df.at[i,'time']+pd.Timedelta(minutes=k): return None
    atr0=float(df.at[i,'atr']); L0=float(df.at[i,level_name])
    if not np.isfinite(atr0) or atr0<=0 or not np.isfinite(L0): return None
    seq=[]; crosses=0; prev_sign=None; reclaim_min=np.nan; first_beyond=None; max_rej=0.0; max_pen=0.0
    for k in range(1,FEATURE_MIN+1):
        lev=float(df.at[i+k,level_name]); c=float(df.at[i+k,'close']); h=float(df.at[i+k,'high']); l=float(df.at[i+k,'low'])
        s=arr*(c-lev)/atr0; seq.append(s)
        sign=1 if s>0 else (-1 if s<0 else 0)
        if prev_sign is not None and sign!=0 and prev_sign!=0 and sign!=prev_sign: crosses+=1
        if sign!=0: prev_sign=sign
        if s<0 and first_beyond is None: first_beyond=k
        if first_beyond is not None and reclaim_min!=reclaim_min and s>0: reclaim_min=float(k)
        if arr>0:
            pen=max(0.0,(lev-l)/atr0); rej=max(0.0,(h-lev)/atr0)
        else:
            pen=max(0.0,(h-lev)/atr0); rej=max(0.0,(lev-l)/atr0)
        max_pen=max(max_pen,pen); max_rej=max(max_rej,rej)
    seq=np.array(seq,float); beyond=(seq<0); final=seq[-1]; pen_any=bool(beyond.any())
    if final<=-0.05 and beyond.sum()>=4: state='EARLY_ACCEPTANCE'
    elif final>=0.05 and pen_any: state='EARLY_REJECTION'
    elif (pen_any and final>0) or crosses>=2: state='RECLAIM_CHOP'
    elif not pen_any: state='NO_PENETRATION'
    else: state='OTHER'
    ret1=-arr*(df.at[i,'close']-df.at[i-1,'close'])/atr0
    ret5=-arr*(df.at[i,'close']-df.at[i-5,'close'])/atr0
    prior=np.diff(df.close.to_numpy(float)[i-5:i+1]); denom=np.abs(prior).sum(); eff=abs(df.at[i,'close']-df.at[i-5,'close'])/denom if denom>0 else np.nan
    hits=ifvg_idx[(ifvg_idx[:,0]>=i)&(ifvg_idx[:,0]<=i+FEATURE_MIN)] if len(ifvg_idx) else np.empty((0,2),int)
    if len(hits)==0: ifvg='NONE'
    else:
        dirs=set(int(x) for x in hits[:,1])
        if arr in dirs: ifvg='REJECTION_ALIGNED'
        elif -arr in dirs: ifvg='ACCEPTANCE_ALIGNED'
        else: ifvg='OTHER'
    mins_prev=np.nan if prev_touch_time is None else (df.at[i,'time']-prev_touch_time).total_seconds()/60
    row={'i':i,'time':df.at[i,'time'],'session':df.at[i,'session'],'year':df.at[i,'time'].year,'level':level_name,'arrival_side':arr,'arrival_from':'ABOVE' if arr>0 else 'BELOW','touch_number':None,'atr0':atr0,'level0':L0,'band_width_atr':float(df.at[i,'band_width_atr']), 'vwap_slope5_atr':float(df.at[i,'vwap_slope5_atr']),'approach_speed_1m_atr':float(ret1),'approach_speed_5m_atr':float(ret5),'approach_eff_5m':float(eff),'max_penetration_5m_atr':float(max_pen),'max_rejection_excursion_5m_atr':float(max_rej),'frac_closes_beyond_5m':float(beyond.mean()),'bars_beyond_5m':int(beyond.sum()),'cross_count_5m':int(crosses),'final_side_1m_atr':float(seq[0]),'final_side_3m_atr':float(seq[2]),'final_side_5m_atr':float(seq[4]),'reclaimed_by_1m':bool(first_beyond is not None and reclaim_min==1),'reclaimed_by_3m':bool(first_beyond is not None and np.isfinite(reclaim_min) and reclaim_min<=3),'reclaimed_by_5m':bool(first_beyond is not None and np.isfinite(reclaim_min) and reclaim_min<=5),'time_to_first_reclaim_min':float(reclaim_min) if np.isfinite(reclaim_min) else np.nan,'state_5m':state,'ifvg_0_5m':ifvg,'minutes_since_prev_touch':mins_prev}
    for b in SENS_BARRIERS: row[f'label_{str(b).replace(".","p")}']=label_barrier(df,i,arr,L0,atr0,b)
    return row


def add_buckets(e):
    x=e.copy()
    x['penetration_bucket']=pd.cut(x.max_penetration_5m_atr,[-np.inf,0,.025,.05,.10,np.inf],labels=['0','0-.025','.025-.05','.05-.10','>.10'])
    x['frac_beyond_bucket']=pd.cut(x.frac_closes_beyond_5m,[-.001,.001,.2,.4,.6,.8,1.001],labels=['0','0-.2','.2-.4','.4-.6','.6-.8','.8-1'])
    x['final5_bucket']=pd.cut(x.final_side_5m_atr,[-np.inf,-.10,-.05,0,.05,.10,np.inf],labels=['<=-.10','-.10--.05','-.05-0','0-.05','.05-.10','>.10'])
    x['approach5_bucket']=pd.cut(x.approach_speed_5m_atr,[-np.inf,-.25,0,.25,.5,1,np.inf],labels=['<-.25','-.25-0','0-.25','.25-.5','.5-1','>1'])
    x['touch_bucket']=np.where(x.touch_number>=4,'4+',x.touch_number.astype(str))
    return x


def rate_table(x,groups,label='label_0p5'):
    rows=[]
    for keys,g in x.groupby(groups,dropna=False,observed=False):
        if not isinstance(keys,tuple): keys=(keys,)
        d=dict(zip(groups,keys)); o=g[label]; res=o.isin(['REJECTION','ACCEPTANCE'])
        d.update(n=len(g),resolved=int(res.sum()),rejection=int((o=='REJECTION').sum()),acceptance=int((o=='ACCEPTANCE').sum()),unresolved=int((o=='UNRESOLVED').sum()),ambiguous=int((o=='AMBIGUOUS').sum()),rejection_rate=float((o[res]=='REJECTION').mean()) if res.any() else np.nan)
        rows.append(d)
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input',type=Path); ap.add_argument('--outdir',type=Path,required=True)
    a=ap.parse_args(); out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    h=sha256(a.input)
    if h!=SHA: raise RuntimeError(f'canonical SHA mismatch {h}')
    df=load(a.input); raw_rows=len(df); df=df[df.time<HOLDOUT].copy().reset_index(drop=True)
    df=add_atr(df); df=add_vwap(df)
    ifvg=build_ifvg_events(df); ifvg_idx=ifvg[['i','dir']].to_numpy(int) if len(ifvg) else np.empty((0,2),int)
    all_t=[]
    for lev in ['MID','HIGH','LOW']: all_t.extend(detect_touches(df,lev))
    all_t=sorted(all_t,key=lambda z:(z[0],z[1]))
    prev={}; rows=[]
    for i,lev,arr,tn in all_t:
        key=(df.at[i,'session'],lev); r=features_for_touch(df,i,lev,arr,ifvg_idx,prev.get(key));
        if r is None: continue
        r['touch_number']=tn; rows.append(r); prev[key]=df.at[i,'time']
    e=pd.DataFrame(rows); e['split']=np.where(e.time<DISC_END,'DISCOVERY','CONFIRMATION'); e=add_buckets(e)
    e.to_csv(out/'events.csv.gz',index=False,compression='gzip')
    census=rate_table(e,['split','year','level','arrival_from']); census.to_csv(out/'census.csv',index=False)
    states=rate_table(e,['split','state_5m']); states.to_csv(out/'state_map.csv',index=False)
    states_level=rate_table(e,['split','level','state_5m']); states_level.to_csv(out/'state_level_map.csv',index=False)
    ifvg_tab=rate_table(e,['split','state_5m','ifvg_0_5m']); ifvg_tab.to_csv(out/'ifvg_conditional_map.csv',index=False)
    for col in ['penetration_bucket','frac_beyond_bucket','final5_bucket','approach5_bucket','touch_bucket']:
        rate_table(e,['split',col]).to_csv(out/f'{col}_map.csv',index=False)
    sens=pd.concat([rate_table(e,['split'],f'label_{str(b).replace(".","p")}').assign(barrier_atr=b) for b in SENS_BARRIERS],ignore_index=True); sens.to_csv(out/'label_sensitivity.csv',index=False)
    sm=[]
    for st in ['EARLY_REJECTION','EARLY_ACCEPTANCE','RECLAIM_CHOP','NO_PENETRATION','OTHER']:
        z=states[states.state_5m==st].set_index('split')
        sm.append({'state':st,'disc_n':int(z.loc['DISCOVERY','resolved']) if 'DISCOVERY' in z.index else 0,'disc_rej_rate':float(z.loc['DISCOVERY','rejection_rate']) if 'DISCOVERY' in z.index else np.nan,'conf_n':int(z.loc['CONFIRMATION','resolved']) if 'CONFIRMATION' in z.index else 0,'conf_rej_rate':float(z.loc['CONFIRMATION','rejection_rate']) if 'CONFIRMATION' in z.index else np.nan})
    transfer=pd.DataFrame(sm); transfer.to_csv(out/'transfer_summary.csv',index=False)
    audit={'lab':LAB,'version':VERSION,'sha256':h,'raw_rows':raw_rows,'rows_pre_holdout':len(df),'period_start':str(df.time.min()),'period_end':str(df.time.max()),'holdout_opened':False,'ifvg_events_pre_holdout':len(ifvg),'touch_candidates':len(all_t),'mapped_events':len(e),'levels':e.level.value_counts().to_dict(),'splits':e.split.value_counts().to_dict()}
    (out/'audit.json').write_text(json.dumps(audit,indent=2,default=str))
    print(json.dumps(audit,indent=2)); print('\nTRANSFER\n',transfer.to_string(index=False)); print('\nSTATE LEVEL TOP\n',states_level.to_string(index=False))

if __name__=='__main__': main()
