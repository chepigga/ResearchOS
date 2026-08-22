#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_POST_TOUCH_SEQUENCE_EXECUTION_ECONOMICS_LAB_004'
VERSION='v001'
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
STRESS_PRICE=(0.0,.05,.10)
LEVEL_PRIORITY={'MID':0,'HIGH':1,'LOW':2}


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
    if (df.high<df.low).any() or (df.ask_high<df.ask_low).any(): raise ValueError('OHLC integrity failure')
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


def add_levels(df):
    o=df.copy(); o['session']=(o.time-pd.Timedelta(hours=ANCHOR_HOUR)).dt.floor('D')
    p=(o.high+o.low+o.close)/3.0
    v=o.tick_volume.clip(lower=0).fillna(0)
    gv=v.groupby(o.session).cumsum(); gpv=(p*v).groupby(o.session).cumsum(); gp2=((p*p)*v).groupby(o.session).cumsum()
    vm=gpv/gv.replace(0,np.nan); vv=(gp2/gv.replace(0,np.nan)-vm*vm).clip(lower=0); vs=np.sqrt(vv)
    cnt=o.groupby('session').cumcount()+1; cm=p.groupby(o.session).cumsum()/cnt; cm2=(p*p).groupby(o.session).cumsum()/cnt; cs=np.sqrt((cm2-cm*cm).clip(lower=0))
    o['VWAP_MID']=vm; o['VWAP_HIGH']=vm+BAND_K*vs; o['VWAP_LOW']=vm-BAND_K*vs
    o['MEAN_MID']=cm; o['MEAN_HIGH']=cm+BAND_K*cs; o['MEAN_LOW']=cm-BAND_K*cs
    return o


def detect_touches(df,family,level_name):
    col=('VWAP_' if family=='VWAP_VOLUME' else 'MEAN_')+level_name
    lev=df[col].to_numpy(float); atr=df.atr.to_numpy(float); lo=df.low.to_numpy(float); hi=df.high.to_numpy(float); cl=df.close.to_numpy(float)
    n=len(df); armed=True; rows=[]; touch_no={}
    maxk=max(CLOCKS)
    for i in range(6,n-maxk-2):
        if not np.isfinite(lev[i]) or not np.isfinite(atr[i]) or atr[i]<=0: continue
        dist=abs(cl[i]-lev[i])/atr[i]
        if not armed:
            if dist>=REARM_ATR: armed=True
            else: continue
        near=(lo[i] <= lev[i]+TOUCH_ATR*atr[i]) and (hi[i] >= lev[i]-TOUCH_ATR*atr[i])
        if not near: continue
        arr=0
        for j in range(i-1,max(-1,i-6),-1):
            if not np.isfinite(lev[j]) or not np.isfinite(atr[j]) or atr[j]<=0: continue
            d=(cl[j]-lev[j])/atr[j]
            if abs(d)>TOUCH_ATR:
                arr=1 if d>0 else -1; break
        if arr==0: continue
        sess=df.at[i,'session']; key=(sess,level_name); tn=touch_no.get(key,0)+1; touch_no[key]=tn
        rows.append((i,family,level_name,arr,tn,col)); armed=False
    return rows


def build_candidates(df):
    all_t=[]
    for fam in ['VWAP_VOLUME','ANCHOR_MEAN']:
        for lev in ['MID','HIGH','LOW']:
            all_t.extend(detect_touches(df,fam,lev))
    rows=[]
    for i,fam,levname,arr,tn,col in all_t:
        atr0=float(df.at[i,'atr'])
        if not np.isfinite(atr0) or atr0<=0: continue
        for k in CLOCKS:
            di=i+k
            if di>=len(df): continue
            ok=True
            for z in range(1,k+1):
                if df.at[i+z,'time'] != df.at[i,'time']+pd.Timedelta(minutes=z): ok=False; break
            if not ok: continue
            levelk=float(df.at[di,col]); ck=float(df.at[di,'close'])
            if not np.isfinite(levelk): continue
            s=arr*(ck-levelk)/atr0
            if s>=DECISION_THRESHOLD:
                state='BACK'; direction=arr
            elif s<=-DECISION_THRESHOLD:
                state='THROUGH'; direction=-arr
            else:
                state='NEUTRAL'; direction=0
            rows.append(dict(touch_i=i,decision_i=di,touch_time=df.at[i,'time'],decision_time=df.at[di,'time'],family=fam,level=levname,arrival_side=arr,touch_number=tn,clock=k,atr0=atr0,level_touch=float(df.at[i,col]),level_decision=levelk,signed_side=float(s),state=state,direction=int(direction)))
    x=pd.DataFrame(rows)
    x['split']=np.where(x.decision_time<DISC_END,'DISCOVERY',np.where(x.decision_time<HOLDOUT,'CONFIRMATION','HOLDOUT'))
    return x


def simulate_one(df,row,target,A):
    di=int(row.decision_i); direction=int(row.direction); risk=RISK_ATR*float(row.atr0)
    if direction==0 or risk<=0: return None
    entry=float(df.at[di,'ask_close']) if direction>0 else float(df.at[di,'close'])
    tp=entry+direction*target*risk; sl=entry-direction*risk
    start=di+1; end_time=pd.Timestamp(row.decision_time)+pd.Timedelta(minutes=HORIZON_MIN)
    T=A['T']; end=int(np.searchsorted(T,np.datetime64(end_time),side='right')); end=min(end,len(df))
    if start>=end: return None
    if direction>0:
        h=A['bh'][start:end]; l=A['bl'][start:end]
        th=np.flatnonzero(h>=tp); sh=np.flatnonzero(l<=sl)
    else:
        l=A['al'][start:end]; h=A['ah'][start:end]
        th=np.flatnonzero(l<=tp); sh=np.flatnonzero(h>=sl)
    pt=int(th[0]) if len(th) else 10**9; ps=int(sh[0]) if len(sh) else 10**9
    if pt==ps and pt<10**9:
        gross=-1.0; outcome='SAME_BAR_LOSS'; exit_i=start+ps
    elif pt<ps:
        gross=float(target); outcome='TP'; exit_i=start+pt
    elif ps<pt:
        gross=-1.0; outcome='SL'; exit_i=start+ps
    else:
        exit_i=end-1
        exit_price=float(df.at[exit_i,'close']) if direction>0 else float(df.at[exit_i,'ask_close'])
        gross=direction*(exit_price-entry)/risk
        gross=float(np.clip(gross,-1.0,target)); outcome='TIME'
    comm=COMMISSION_PRICE_RT/risk
    base=gross-comm
    return dict(entry=entry,risk_price=risk,tp=tp,sl=sl,target=target,outcome=outcome,exit_i=int(exit_i),exit_time=df.at[exit_i,'time'],gross_R=gross,commission_R=comm,net_R=base,net_R_stress_0p05=base-.05/risk,net_R_stress_0p10=base-.10/risk)


def simulate_candidates(df,cands):
    sig=cands[cands.direction!=0].copy().reset_index(drop=True)
    A={'T':df.time.to_numpy(dtype='datetime64[ns]'),'bh':df.high.to_numpy(float),'bl':df.low.to_numpy(float),'ah':df.ask_high.to_numpy(float),'al':df.ask_low.to_numpy(float)}
    rows=[]
    for r in sig.itertuples(index=False):
        base=r._asdict()
        for target in TARGETS:
            z=simulate_one(df,r,target,A)
            if z is not None: rows.append(base|z)
    return pd.DataFrame(rows)


def dedup_signal_stream(x):
    rows=[]
    for t,g in x.groupby('decision_time',sort=True):
        keep=[]
        for d,gd in g.groupby('direction'):
            gd=gd.copy(); gd['abs_s']=gd.signed_side.abs(); gd['levpri']=gd.level.map(LEVEL_PRIORITY)
            gd=gd.sort_values(['abs_s','levpri'],ascending=[False,True])
            keep.append(gd.iloc[0])
        if len(keep)!=1: continue
        rows.append(keep[0])
    return pd.DataFrame(rows).drop(columns=['abs_s','levpri'],errors='ignore').sort_values('decision_time').reset_index(drop=True) if rows else pd.DataFrame(columns=x.columns)


def serial_portfolio(x):
    stream=dedup_signal_stream(x)
    if stream.empty: return stream
    chosen=[]; last_exit=None
    for r in stream.itertuples(index=False):
        if last_exit is not None and pd.Timestamp(r.decision_time)<=last_exit: continue
        chosen.append(r._asdict()); last_exit=pd.Timestamp(r.exit_time)
    return pd.DataFrame(chosen)


def pf(v):
    pos=v[v>0].sum(); neg=-v[v<0].sum()
    return float(pos/neg) if neg>0 else (float('inf') if pos>0 else np.nan)


def maxdd(v):
    c=np.cumsum(np.asarray(v,float)); c=np.r_[0,c]; peak=np.maximum.accumulate(c); return float(np.max(peak-c))


def max_consec_losses(v):
    m=cur=0
    for z in v:
        if z<0: cur+=1; m=max(m,cur)
        else: cur=0
    return int(m)


def summary_row(g,kind):
    if len(g)==0: return {}
    v=g.net_R.astype(float)
    span=max((pd.Timestamp(g.decision_time.max())-pd.Timestamp(g.decision_time.min())).total_seconds()/604800.0,1/7)
    days=g.assign(day=pd.to_datetime(g.decision_time).dt.floor('D')).groupby('day').net_R.sum()
    return dict(view=kind,n=int(len(g)),trades_per_week=float(len(g)/span),ev_R=float(v.mean()),pf=pf(v),win_rate=float((v>0).mean()),tp_rate=float((g.outcome=='TP').mean()),total_R=float(v.sum()),max_dd_R=maxdd(v),worst_day_R=float(days.min()) if len(days) else np.nan,max_consecutive_losses=max_consec_losses(v),buy_n=int((g.direction>0).sum()),sell_n=int((g.direction<0).sum()),buy_ev_R=float(g.loc[g.direction>0,'net_R'].mean()) if (g.direction>0).any() else np.nan,sell_ev_R=float(g.loc[g.direction<0,'net_R'].mean()) if (g.direction<0).any() else np.nan,ev_stress_0p05=float(g.net_R_stress_0p05.mean()),ev_stress_0p10=float(g.net_R_stress_0p10.mean()))


def weekly_ci(g):
    if len(g)==0: return {'n_weeks':0,'mean_R':None,'ci95':[None,None]}
    z=g.copy(); t=pd.to_datetime(z.decision_time); z['week']=(t-pd.to_timedelta(t.dt.weekday,unit='D')).dt.floor('D')
    vals=z.groupby('week').net_R.mean().to_numpy(float)
    if len(vals)<8: return {'n_weeks':int(len(vals)),'mean_R':float(np.mean(vals)) if len(vals) else None,'ci95':[None,None]}
    rng=np.random.default_rng(20260822); boots=np.array([rng.choice(vals,len(vals),replace=True).mean() for _ in range(4000)])
    return {'n_weeks':int(len(vals)),'mean_R':float(vals.mean()),'ci95':[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))]}


def build_outputs(sim):
    summaries=[]; serial_sets={}
    keys=['split','family','clock','target']
    for key,g in sim.groupby(keys):
        r=dict(zip(keys,key)); r.update(summary_row(g,'INDEPENDENT')); summaries.append(r)
        ser=serial_portfolio(g); serial_sets[key]=ser
        rr=dict(zip(keys,key)); rr.update(summary_row(ser,'SERIAL')); summaries.append(rr)
    summary=pd.DataFrame(summaries)
    yearly=[]
    for key,ser in serial_sets.items():
        if len(ser)==0: continue
        z=ser.copy(); z['year']=pd.to_datetime(z.decision_time).dt.year
        for y,g in z.groupby('year'):
            r=dict(zip(keys,key)); r['year']=int(y); r.update(summary_row(g,'SERIAL')); yearly.append(r)
    return summary,pd.DataFrame(yearly),serial_sets


def pick_summary(summary,split,family,clock,target):
    z=summary[(summary.view=='SERIAL')&(summary.split==split)&(summary.family==family)&(summary.clock==clock)&(np.isclose(summary.target,target))]
    return z.iloc[0].to_dict() if len(z) else None


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input',type=Path); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args()
    out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    h=sha256(a.input)
    if h!=SHA: raise RuntimeError(f'canonical SHA mismatch {h}')
    df=load(a.input); raw_rows=len(df); df=df[df.time<HOLDOUT].copy().reset_index(drop=True)
    df=add_atr(df); df=add_levels(df)
    cands=build_candidates(df)
    sim=simulate_candidates(df,cands)
    summary,yearly,serial_sets=build_outputs(sim)
    summary.to_csv(out/'summary.csv',index=False); yearly.to_csv(out/'yearly.csv',index=False)
    census=cands.groupby(['split','family','clock','state'],dropna=False).size().rename('n').reset_index(); census.to_csv(out/'signal_census.csv',index=False)
    conf=pick_summary(summary,'CONFIRMATION','VWAP_VOLUME',3,1.5); disc=pick_summary(summary,'DISCOVERY','VWAP_VOLUME',3,1.5); conf2=pick_summary(summary,'CONFIRMATION','VWAP_VOLUME',3,2.0); conf1=pick_summary(summary,'CONFIRMATION','VWAP_VOLUME',1,1.5)
    primary_key=('CONFIRMATION','VWAP_VOLUME',3,1.5); primary_ser=serial_sets.get(primary_key,pd.DataFrame())
    ci=weekly_ci(primary_ser)
    ask_ok=all(c in df.columns for c in ['ask_high','ask_low','ask_close'])
    gates={
      'G0_DATA_EXECUTION': bool(h==SHA and ask_ok),
      'G1_CONFIRMATION_EV': bool(conf and conf['ev_R']>0 and conf['pf']>1.0),
      'G2_WEEK_CLUSTER_CI': bool(ci['ci95'][0] is not None and ci['ci95'][0]>0),
      'G3_SPLIT_TRANSFER': bool(conf and disc and conf['ev_R']>0 and disc['ev_R']>0),
      'G4_2R_SURVIVAL': bool(conf2 and conf2['ev_R']>=0),
      'G5_T1_EXECUTABLE': bool(conf1 and conf1['ev_R']>0),
      'G6_DIRECTION_BREADTH': bool(conf and conf['buy_ev_R']>0 and conf['sell_ev_R']>0),
      'G7_PROP_DD_PROXY': bool(conf and conf['max_dd_R']<=20 and conf['worst_day_R']>-16),
      'G8_COST_STRESS': bool(conf and conf['ev_stress_0p10']>0),
    }
    if not gates['G0_DATA_EXECUTION']: status='INVALID_EXECUTION_DATA'
    elif all(gates.values()): status='GO_TO_REPLICATION'
    elif gates['G1_CONFIRMATION_EV'] and gates['G3_SPLIT_TRANSFER']: status='PROMISING_BUT_NOT_ROBUST'
    else: status='NO_EXECUTABLE_EDGE'
    audit={'lab':LAB,'version':VERSION,'sha256':h,'raw_rows':raw_rows,'preholdout_rows':len(df),'period_start':str(df.time.min()),'period_end':str(df.time.max()),'candidate_rows':int(len(cands)),'signal_rows':int((cands.direction!=0).sum()),'simulated_rows':int(len(sim)),'ask_available':bool(ask_ok),'holdout_opened':False}
    verdict={'status':status,'gates':gates,'primary_confirmation':conf,'primary_discovery':disc,'confirmation_2R':conf2,'confirmation_T1_1p5R':conf1,'weekly_cluster_ci':ci,'holdout_opened':False}
    (out/'audit.json').write_text(json.dumps(audit,indent=2,default=str))
    (out/'verdict.json').write_text(json.dumps(verdict,indent=2,default=str))
    print(json.dumps(audit,indent=2)); print(json.dumps(verdict,indent=2,default=str))

if __name__=='__main__': main()
