#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit, prange

LAB='XAU_POST_TOUCH_SEQUENCE_EXECUTION_ECONOMICS_LAB_004'
VERSION='v001-fast-replay'
SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
HOLDOUT=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
ANCHOR_HOUR=1
BAND_K=1.618
TOUCH_ATR=.05
REARM_ATR=.25
DECISION_THRESHOLD=.10
CLOCKS=(1,3,5)
RISK_ATR=.50
TARGETS=(1.5,2.0)
HORIZON_MIN=60
COMMISSION_PRICE_RT=.05
LEVEL_PRIORITY={'MID':0,'HIGH':1,'LOW':2}
NS_MIN=60*1_000_000_000


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load(path:Path)->pd.DataFrame:
    df=pd.read_csv(path,sep=';')
    need=['time','open','high','low','close','ask_high','ask_low','ask_close','tick_volume']
    miss=[c for c in need if c not in df.columns]
    if miss: raise ValueError(f'missing columns {miss}')
    keep=[c for c in ['time','open','high','low','close','ask_high','ask_low','ask_close','tick_volume','spread_mean'] if c in df.columns]
    df=df[keep].copy()
    df['time']=pd.to_datetime(df.time,format='%Y.%m.%d %H:%M',errors='coerce')
    for c in df.columns:
        if c!='time': df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=need).sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    return df


def wilder_atr(h,l,c,n=14):
    pc=c.shift(1)
    tr=pd.concat([(h-l),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()


def add_atr_levels(df):
    x=df.set_index('time')
    m=x.resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna()
    m['atr']=wilder_atr(m.high,m.low,m.close)
    a=m[['atr']].reset_index(); a['avail']=a.time+pd.Timedelta(minutes=15); a=a[['avail','atr']].dropna().sort_values('avail')
    o=pd.merge_asof(df.sort_values('time'),a,left_on='time',right_on='avail',direction='backward').drop(columns='avail')
    o['session']=(o.time-pd.Timedelta(hours=ANCHOR_HOUR)).dt.floor('D')
    p=(o.high+o.low+o.close)/3.0; v=o.tick_volume.clip(lower=0).fillna(0)
    gv=v.groupby(o.session).cumsum(); gpv=(p*v).groupby(o.session).cumsum(); gp2=((p*p)*v).groupby(o.session).cumsum()
    vm=gpv/gv.replace(0,np.nan); vs=np.sqrt((gp2/gv.replace(0,np.nan)-vm*vm).clip(lower=0))
    cnt=o.groupby('session').cumcount()+1; cm=p.groupby(o.session).cumsum()/cnt; cm2=(p*p).groupby(o.session).cumsum()/cnt; cs=np.sqrt((cm2-cm*cm).clip(lower=0))
    o['VWAP_MID']=vm; o['VWAP_HIGH']=vm+BAND_K*vs; o['VWAP_LOW']=vm-BAND_K*vs
    o['MEAN_MID']=cm; o['MEAN_HIGH']=cm+BAND_K*cs; o['MEAN_LOW']=cm-BAND_K*cs
    return o


def fast_touch_indices(df, col, level_name):
    level=df[col].to_numpy(float); atr=df.atr.to_numpy(float); cl=df.close.to_numpy(float); lo=df.low.to_numpy(float); hi=df.high.to_numpy(float)
    n=len(df); idx=np.arange(n)
    valid=np.isfinite(level)&np.isfinite(atr)&(atr>0)
    dist=np.full(n,np.nan); dist[valid]=np.abs(cl[valid]-level[valid])/atr[valid]
    near=valid & (lo <= level+TOUCH_ATR*atr) & (hi >= level-TOUCH_ATR*atr)
    near &= (idx>=6) & (idx < n-HORIZON_MIN-max(CLOCKS)-2)
    near_idx=np.flatnonzero(near); rearm_idx=np.flatnonzero(valid & (dist>=REARM_ATR))
    session=df.session.to_numpy()
    out=[]; start_idx=6; touch_count={}
    while True:
        nptr=np.searchsorted(near_idx,start_idx,side='left')
        if nptr>=len(near_idx): break
        i=int(near_idx[nptr])
        arr=0
        for j in range(i-1,i-6,-1):
            if j<0 or not valid[j]: continue
            d=(cl[j]-level[j])/atr[j]
            if abs(d)>TOUCH_ATR:
                arr=1 if d>0 else -1; break
        if arr==0:
            start_idx=i+1; continue
        key=session[i]
        tn=touch_count.get(key,0)+1; touch_count[key]=tn
        out.append((i,arr,tn))
        rp=np.searchsorted(rearm_idx,i+1,side='left')
        if rp>=len(rearm_idx): break
        start_idx=int(rearm_idx[rp])
    return out


def build_vwap_from_parent(df,parent_path:Path):
    p=pd.read_csv(parent_path,compression='gzip')
    p['time']=pd.to_datetime(p.time)
    rows=[]
    for r in p[['i','level','arrival_side','touch_number','atr0']].itertuples(index=False):
        i=int(r.i)
        if i<0 or i>=len(df): continue
        for k in CLOCKS:
            di=i+k
            if di>=len(df): continue
            if df.at[di,'time'] != df.at[i,'time']+pd.Timedelta(minutes=k): continue
            col='VWAP_'+r.level
            s=int(r.arrival_side)*(float(df.at[di,'close'])-float(df.at[di,col]))/float(r.atr0)
            if s>=DECISION_THRESHOLD: state='BACK'; direction=int(r.arrival_side)
            elif s<=-DECISION_THRESHOLD: state='THROUGH'; direction=-int(r.arrival_side)
            else: state='NEUTRAL'; direction=0
            rows.append((i,di,'VWAP_VOLUME',r.level,int(r.arrival_side),int(r.touch_number),k,float(r.atr0),float(s),state,direction))
    return rows


def build_mean_fast(df):
    rows=[]
    times_ns=df.time.to_numpy(dtype='datetime64[ns]').astype('int64')
    for lev in ['MID','HIGH','LOW']:
        col='MEAN_'+lev
        for i,arr,tn in fast_touch_indices(df,col,lev):
            atr0=float(df.at[i,'atr'])
            for k in CLOCKS:
                di=i+k
                if di>=len(df) or times_ns[di]-times_ns[i] != k*NS_MIN: continue
                s=arr*(float(df.at[di,'close'])-float(df.at[di,col]))/atr0
                if s>=DECISION_THRESHOLD: state='BACK'; direction=arr
                elif s<=-DECISION_THRESHOLD: state='THROUGH'; direction=-arr
                else: state='NEUTRAL'; direction=0
                rows.append((i,di,'ANCHOR_MEAN',lev,arr,tn,k,atr0,float(s),state,direction))
    return rows


def candidates(df,parent_path):
    rows=build_vwap_from_parent(df,parent_path)+build_mean_fast(df)
    x=pd.DataFrame(rows,columns=['touch_i','decision_i','family','level','arrival_side','touch_number','clock','atr0','signed_side','state','direction'])
    x['touch_time']=df.time.to_numpy()[x.touch_i.to_numpy(int)]
    x['decision_time']=df.time.to_numpy()[x.decision_i.to_numpy(int)]
    x['split']=np.where(x.decision_time<DISC_END,'DISCOVERY',np.where(x.decision_time<HOLDOUT,'CONFIRMATION','HOLDOUT'))
    return x

@njit(parallel=True)
def sim_numba(dec_i, direction, atr0, target, time_ns, bid_h,bid_l,bid_c,ask_h,ask_l,ask_c):
    n=len(dec_i); gross=np.empty(n,np.float64); exit_i=np.empty(n,np.int64); outcome=np.empty(n,np.int8); entry=np.empty(n,np.float64); risk=np.empty(n,np.float64)
    for q in prange(n):
        di=dec_i[q]; d=direction[q]; r=RISK_ATR*atr0[q]; risk[q]=r
        e=ask_c[di] if d>0 else bid_c[di]; entry[q]=e
        tp=e+d*target*r; sl=e-d*r; end_ns=time_ns[di]+HORIZON_MIN*NS_MIN
        last=di; done=False
        j=di+1
        while j<len(time_ns) and time_ns[j]<=end_ns:
            last=j
            if d>0:
                ht=bid_h[j]>=tp; hs=bid_l[j]<=sl
            else:
                ht=ask_l[j]<=tp; hs=ask_h[j]>=sl
            if ht and hs:
                gross[q]=-1.0; exit_i[q]=j; outcome[q]=3; done=True; break
            elif ht:
                gross[q]=target; exit_i[q]=j; outcome[q]=1; done=True; break
            elif hs:
                gross[q]=-1.0; exit_i[q]=j; outcome[q]=2; done=True; break
            j+=1
        if not done:
            if last==di:
                gross[q]=0.0; exit_i[q]=di; outcome[q]=4
            else:
                xp=bid_c[last] if d>0 else ask_c[last]
                z=d*(xp-e)/r
                if z<-1.0: z=-1.0
                if z>target: z=target
                gross[q]=z; exit_i[q]=last; outcome[q]=4
    return gross,exit_i,outcome,entry,risk


def simulate(df,cands):
    sig=cands[cands.direction!=0].copy().reset_index(drop=True)
    time_ns=df.time.to_numpy(dtype='datetime64[ns]').astype('int64')
    arrays=[df[c].to_numpy(float) for c in ['high','low','close','ask_high','ask_low','ask_close']]
    out=[]
    for target in TARGETS:
        gross,ei,oc,en,risk=sim_numba(sig.decision_i.to_numpy(np.int64),sig.direction.to_numpy(np.int64),sig.atr0.to_numpy(float),float(target),time_ns,*arrays)
        z=sig.copy(); z['target']=target; z['entry']=en; z['risk_price']=risk; z['exit_i']=ei; z['exit_time']=df.time.to_numpy()[ei]
        names=np.array(['','TP','SL','SAME_BAR_LOSS','TIME'],dtype=object); z['outcome']=names[oc]
        z['gross_R']=gross; z['commission_R']=COMMISSION_PRICE_RT/risk; z['net_R']=gross-z.commission_R; z['net_R_stress_0p05']=z.net_R-.05/risk; z['net_R_stress_0p10']=z.net_R-.10/risk
        out.append(z)
    return pd.concat(out,ignore_index=True)


def dedup_signal_stream(x):
    y=x.copy(); y['abs_s']=y.signed_side.abs(); y['levpri']=y.level.map(LEVEL_PRIORITY)
    y=y.sort_values(['decision_time','direction','abs_s','levpri'],ascending=[True,True,False,True]).drop_duplicates(['decision_time','direction'],keep='first')
    counts=y.groupby('decision_time').direction.nunique(); ok=counts[counts==1].index
    return y[y.decision_time.isin(ok)].sort_values('decision_time').drop(columns=['abs_s','levpri']).reset_index(drop=True)


def serial_portfolio(x):
    stream=dedup_signal_stream(x); chosen=[]; last_exit=None
    for r in stream.itertuples(index=False):
        t=pd.Timestamp(r.decision_time)
        if last_exit is not None and t<=last_exit: continue
        chosen.append(r._asdict()); last_exit=pd.Timestamp(r.exit_time)
    return pd.DataFrame(chosen)


def pf(v):
    v=np.asarray(v,float); pos=v[v>0].sum(); neg=-v[v<0].sum(); return float(pos/neg) if neg>0 else (float('inf') if pos>0 else np.nan)

def maxdd(v):
    c=np.r_[0,np.cumsum(np.asarray(v,float))]; p=np.maximum.accumulate(c); return float(np.max(p-c))
def max_consec(v):
    m=cur=0
    for z in v:
        if z<0: cur+=1; m=max(m,cur)
        else: cur=0
    return int(m)
def stats(g,view):
    if len(g)==0: return {}
    v=g.net_R.to_numpy(float); span=max((pd.Timestamp(g.decision_time.max())-pd.Timestamp(g.decision_time.min())).total_seconds()/604800,1/7)
    day=g.assign(day=pd.to_datetime(g.decision_time).dt.floor('D')).groupby('day').net_R.sum()
    return {'view':view,'n':int(len(g)),'trades_per_week':float(len(g)/span),'ev_R':float(v.mean()),'pf':pf(v),'win_rate':float((v>0).mean()),'tp_rate':float((g.outcome=='TP').mean()),'total_R':float(v.sum()),'max_dd_R':maxdd(v),'worst_day_R':float(day.min()),'max_consecutive_losses':max_consec(v),'buy_n':int((g.direction>0).sum()),'sell_n':int((g.direction<0).sum()),'buy_ev_R':float(g.loc[g.direction>0,'net_R'].mean()) if (g.direction>0).any() else np.nan,'sell_ev_R':float(g.loc[g.direction<0,'net_R'].mean()) if (g.direction<0).any() else np.nan,'ev_stress_0p05':float(g.net_R_stress_0p05.mean()),'ev_stress_0p10':float(g.net_R_stress_0p10.mean())}
def weekly_ci(g):
    z=g.copy(); t=pd.to_datetime(z.decision_time); z['week']=(t-pd.to_timedelta(t.dt.weekday,unit='D')).dt.floor('D'); vals=z.groupby('week').net_R.mean().to_numpy(float)
    rng=np.random.default_rng(20260822); boots=np.array([rng.choice(vals,len(vals),replace=True).mean() for _ in range(4000)])
    return {'n_weeks':int(len(vals)),'mean_R':float(vals.mean()),'ci95':[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))]}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input',type=Path); ap.add_argument('--parent-vwap-events',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args()
    out=a.outdir; out.mkdir(parents=True,exist_ok=True); h=sha256(a.input)
    if h!=SHA: raise RuntimeError(f'SHA mismatch {h}')
    df=load(a.input); raw=len(df); df=df[df.time<HOLDOUT].copy().reset_index(drop=True); df=add_atr_levels(df)
    c=candidates(df,a.parent_vwap_events); sim=simulate(df,c)
    summaries=[]; serials={}; keys=['split','family','clock','target']
    for key,g in sim.groupby(keys):
        r=dict(zip(keys,key)); r.update(stats(g,'INDEPENDENT')); summaries.append(r)
        ser=serial_portfolio(g); serials[key]=ser; r=dict(zip(keys,key)); r.update(stats(ser,'SERIAL')); summaries.append(r)
    summary=pd.DataFrame(summaries); summary.to_csv(out/'summary.csv',index=False)
    yearly=[]
    for key,ser in serials.items():
        if ser.empty: continue
        z=ser.copy(); z['year']=pd.to_datetime(z.decision_time).dt.year
        for year,g in z.groupby('year'):
            r=dict(zip(keys,key)); r['year']=int(year); r.update(stats(g,'SERIAL')); yearly.append(r)
    pd.DataFrame(yearly).to_csv(out/'yearly.csv',index=False)
    c.groupby(['split','family','clock','state']).size().rename('n').reset_index().to_csv(out/'signal_census.csv',index=False)
    def pick(split,fam,clock,target):
        z=summary[(summary.view=='SERIAL')&(summary.split==split)&(summary.family==fam)&(summary.clock==clock)&np.isclose(summary.target,target)]
        return z.iloc[0].to_dict() if len(z) else None
    conf=pick('CONFIRMATION','VWAP_VOLUME',3,1.5); disc=pick('DISCOVERY','VWAP_VOLUME',3,1.5); conf2=pick('CONFIRMATION','VWAP_VOLUME',3,2.0); conf1=pick('CONFIRMATION','VWAP_VOLUME',1,1.5); conf5=pick('CONFIRMATION','VWAP_VOLUME',5,1.5); mean3=pick('CONFIRMATION','ANCHOR_MEAN',3,1.5)
    ser=serials[('CONFIRMATION','VWAP_VOLUME',3,1.5)]; ci=weekly_ci(ser)
    gates={'G0_DATA_EXECUTION':True,'G1_CONFIRMATION_EV':bool(conf['ev_R']>0 and conf['pf']>1),'G2_WEEK_CLUSTER_CI':bool(ci['ci95'][0]>0),'G3_SPLIT_TRANSFER':bool(conf['ev_R']>0 and disc['ev_R']>0),'G4_2R_SURVIVAL':bool(conf2['ev_R']>=0),'G5_T1_EXECUTABLE':bool(conf1['ev_R']>0),'G6_DIRECTION_BREADTH':bool(conf['buy_ev_R']>0 and conf['sell_ev_R']>0),'G7_PROP_DD_PROXY':bool(conf['max_dd_R']<=20 and conf['worst_day_R']>-16),'G8_COST_STRESS':bool(conf['ev_stress_0p10']>0)}
    if all(gates.values()): status='GO_TO_REPLICATION'
    elif gates['G1_CONFIRMATION_EV'] and gates['G3_SPLIT_TRANSFER']: status='PROMISING_BUT_NOT_ROBUST'
    else: status='NO_EXECUTABLE_EDGE'
    audit={'lab':LAB,'version':VERSION,'sha256':h,'raw_rows':raw,'preholdout_rows':len(df),'candidate_rows':len(c),'signal_rows':int((c.direction!=0).sum()),'simulated_rows':len(sim),'parent_vwap_events':str(a.parent_vwap_events),'holdout_opened':False}
    verdict={'status':status,'gates':gates,'primary_confirmation':conf,'primary_discovery':disc,'confirmation_T1_1p5R':conf1,'confirmation_T5_1p5R':conf5,'confirmation_T3_2R':conf2,'confirmation_anchor_mean_T3_1p5R':mean3,'weekly_cluster_ci':ci,'holdout_opened':False}
    (out/'audit.json').write_text(json.dumps(audit,indent=2,default=str)); (out/'verdict.json').write_text(json.dumps(verdict,indent=2,default=str))
    print(json.dumps(audit,indent=2)); print(json.dumps(verdict,indent=2,default=str))
if __name__=='__main__': main()
