#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit

LAB='XAU_POST_TOUCH_SEQUENCE_RETEST_ENTRY_CAUSAL_LAB_005'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
HOLDOUT=np.datetime64('2025-07-01T00:00:00')
DISC_END=pd.Timestamp('2024-01-01')
ANCHOR_HOUR=1
BAND_K=1.618
SIGNAL_THR=0.10
RETEST_MINUTES=15
RETEST_ZONE_ATR=0.05
CONFIRM_CLOSE_ATR=0.03
RISK_ATR=0.50
HOLD_MINUTES=60
TARGETS=(1.5,2.0)
COMMISSION_PRICE=0.05
LEVEL_RANK={'MID':0,'HIGH':1,'LOW':2}


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load_prices(path:Path)->pd.DataFrame:
    use=['time','open','high','low','close','ask_open','ask_high','ask_low','ask_close','tick_volume']
    df=pd.read_csv(path,sep=';',usecols=use)
    df['time']=pd.to_datetime(df.time,format='%Y.%m.%d %H:%M',errors='coerce')
    for c in use:
        if c!='time': df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=use).sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    df=df[df.time<pd.Timestamp('2025-07-01')].copy().reset_index(drop=True)
    return df


def add_vwap_lines(df:pd.DataFrame)->pd.DataFrame:
    o=df.copy()
    o['session']=(o.time-pd.Timedelta(hours=ANCHOR_HOUR)).dt.floor('D')
    p=(o.high+o.low+o.close)/3.0
    v=o.tick_volume.clip(lower=0).fillna(0)
    gv=v.groupby(o.session).cumsum()
    gpv=(p*v).groupby(o.session).cumsum()
    gp2=((p*p)*v).groupby(o.session).cumsum()
    mid=gpv/gv.replace(0,np.nan)
    var=(gp2/gv.replace(0,np.nan)-mid*mid).clip(lower=0)
    sd=np.sqrt(var)
    o['MID']=mid; o['HIGH']=mid+BAND_K*sd; o['LOW']=mid-BAND_K*sd
    return o


def load_events(path:Path)->pd.DataFrame:
    e=pd.read_csv(path,compression='gzip')
    e['time']=pd.to_datetime(e.time)
    e=e[e.time<pd.Timestamp('2025-07-01')].copy()
    req=['i','time','level','arrival_side','atr0','final_side_1m_atr','final_side_3m_atr','label_0p5','split']
    miss=[c for c in req if c not in e.columns]
    if miss: raise ValueError(f'missing LAB002 event columns {miss}')
    return e


def build_signals(e:pd.DataFrame, clock:int)->pd.DataFrame:
    scol=f'final_side_{clock}m_atr'
    z=e[np.isfinite(e[scol])].copy()
    z['s']=z[scol].astype(float)
    z=z[(z.s>=SIGNAL_THR)|(z.s<=-SIGNAL_THR)].copy()
    z['branch']=np.where(z.s>=SIGNAL_THR,'BACK','THROUGH')
    z['dir']=np.where(z.branch.eq('BACK'),z.arrival_side,-z.arrival_side).astype(int)
    z['decision_i']=z.i.astype(int)+clock
    z['decision_time']=z.time+pd.to_timedelta(clock,unit='m')
    z['signal_correct']=np.where(z.branch.eq('BACK'),z.label_0p5.eq('REJECTION'),z.label_0p5.eq('ACCEPTANCE'))
    z['level_rank']=z.level.map(LEVEL_RANK).astype(int)
    return z


def dedupe_decisions(z:pd.DataFrame)->pd.DataFrame:
    x=z.copy(); x['abs_s']=x.s.abs()
    x=x.sort_values(['decision_time','dir','abs_s','level_rank'],ascending=[True,True,False,True])
    x=x.drop_duplicates(['decision_time','dir'],keep='first')
    counts=x.groupby('decision_time').dir.nunique()
    conflict=set(counts[counts>1].index)
    if conflict: x=x[~x.decision_time.isin(conflict)]
    return x.sort_values('decision_time').reset_index(drop=True)

@njit
def find_retest(dec_i, d, atr0, level_code, times_m, high, low, close, mid, highline, lowline):
    n=len(close); start=dec_i+1
    if start>=n: return -1,-1
    end_time=times_m[dec_i]+RETEST_MINUTES
    for j in range(start,n):
        if times_m[j]>end_time: break
        if level_code==0: lev=mid[j]
        elif level_code==1: lev=highline[j]
        else: lev=lowline[j]
        if not np.isfinite(lev): continue
        touch=(low[j] <= lev+RETEST_ZONE_ATR*atr0) and (high[j] >= lev-RETEST_ZONE_ATR*atr0)
        if not touch: continue
        hold=d*(close[j]-lev)/atr0
        if hold < CONFIRM_CLOSE_ATR: continue
        k=j+1
        if k<n and times_m[k]==times_m[j]+1: return j,k
    return -1,-1

@njit
def sim_trade(entry_i,d,entry,risk,target,times_m,bh,bl,bc,ah,al,ac):
    end_time=times_m[entry_i]+HOLD_MINUTES; tp=entry+d*target*risk; sl=entry-d*risk; last=entry_i
    for j in range(entry_i,len(bc)):
        if times_m[j]>end_time: break
        last=j
        if d>0: ht=bh[j]>=tp; hs=bl[j]<=sl
        else: ht=al[j]<=tp; hs=ah[j]>=sl
        if ht and hs: return -1.0,j,2
        if hs: return -1.0,j,0
        if ht: return target,j,1
    exitp=bc[last] if d>0 else ac[last]; r=d*(exitp-entry)/risk
    if r < -1.0: r=-1.0
    if r > target: r=target
    return r,last,3

@njit
def sim_market(dec_i,d,entry,risk,target,times_m,bh,bl,bc,ah,al,ac):
    start=dec_i+1
    if start>=len(bc): return np.nan,-1,4
    end_time=times_m[dec_i]+HOLD_MINUTES; tp=entry+d*target*risk; sl=entry-d*risk; last=start
    for j in range(start,len(bc)):
        if times_m[j]>end_time: break
        last=j
        if d>0: ht=bh[j]>=tp; hs=bl[j]<=sl
        else: ht=al[j]<=tp; hs=ah[j]>=sl
        if ht and hs: return -1.0,j,2
        if hs: return -1.0,j,0
        if ht: return target,j,1
    exitp=bc[last] if d>0 else ac[last]; r=d*(exitp-entry)/risk
    if r < -1.0: r=-1.0
    if r > target: r=target
    return r,last,3


def enrich_retests(z:pd.DataFrame,df:pd.DataFrame,clock:int)->pd.DataFrame:
    times_m=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    bh=df.high.to_numpy(float); bl=df.low.to_numpy(float); bc=df.close.to_numpy(float)
    ah=df.ask_high.to_numpy(float); al=df.ask_low.to_numpy(float); ac=df.ask_close.to_numpy(float)
    ao=df.ask_open.to_numpy(float); bo=df.open.to_numpy(float)
    mid=df.MID.to_numpy(float); hi=df.HIGH.to_numpy(float); lo=df.LOW.to_numpy(float)
    rows=[]
    for r in z.itertuples(index=False):
        di=int(r.decision_i); d=int(r.dir); atr=float(r.atr0); lc=LEVEL_RANK[str(r.level)]
        if di>=len(df) or df.at[int(r.i),'time']!=r.time or df.at[di,'time']!=r.decision_time: continue
        conf_i,entry_i=find_retest(di,d,atr,lc,times_m,bh,bl,bc,mid,hi,lo)
        filled=entry_i>=0; market_entry=ac[di] if d>0 else bc[di]
        base={'event_i':int(r.i),'touch_time':r.time,'decision_i':di,'decision_time':r.decision_time,'clock':clock,'level':r.level,'arrival_side':int(r.arrival_side),'branch':r.branch,'dir':d,'s':float(r.s),'atr0':atr,'label_0p5':r.label_0p5,'signal_correct':bool(r.signal_correct),'split':r.split,'year':int(r.year),'filled':bool(filled),'market_entry':float(market_entry)}
        if not filled:
            base.update(retest_confirm_i=-1,retest_confirm_time=pd.NaT,entry_i=-1,entry_time=pd.NaT,wait_confirm_min=np.nan,wait_entry_min=np.nan,retest_entry=np.nan,entry_improvement_atr=np.nan); rows.append(base); continue
        entry=ao[entry_i] if d>0 else bo[entry_i]; imp=d*(market_entry-entry)/atr
        base.update(retest_confirm_i=int(conf_i),retest_confirm_time=df.at[conf_i,'time'],entry_i=int(entry_i),entry_time=df.at[entry_i,'time'],wait_confirm_min=(df.at[conf_i,'time']-r.decision_time).total_seconds()/60,wait_entry_min=(df.at[entry_i,'time']-r.decision_time).total_seconds()/60,retest_entry=float(entry),entry_improvement_atr=float(imp)); rows.append(base)
    return pd.DataFrame(rows)


def simulate_all(x:pd.DataFrame,df:pd.DataFrame,target:float)->pd.DataFrame:
    y=x.copy(); times_m=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    bh=df.high.to_numpy(float); bl=df.low.to_numpy(float); bc=df.close.to_numpy(float); ah=df.ask_high.to_numpy(float); al=df.ask_low.to_numpy(float); ac=df.ask_close.to_numpy(float)
    gross=[]; net=[]; stress05=[]; stress10=[]; exit_i=[]; outcome=[]; market_net=[]; market_gross=[]
    for r in y.itertuples(index=False):
        if not r.filled:
            gross.append(np.nan); net.append(np.nan); stress05.append(np.nan); stress10.append(np.nan); exit_i.append(-1); outcome.append('UNFILLED'); market_net.append(np.nan); market_gross.append(np.nan); continue
        risk=RISK_ATR*float(r.atr0); gr,ei,oc=sim_trade(int(r.entry_i),int(r.dir),float(r.retest_entry),risk,target,times_m,bh,bl,bc,ah,al,ac); comm=COMMISSION_PRICE/risk; nr=gr-comm
        gross.append(float(gr)); net.append(float(nr)); stress05.append(float(nr-0.05/risk)); stress10.append(float(nr-0.10/risk)); exit_i.append(int(ei)); outcome.append(['SL','TP','SAME_BAR_LOSS','TIME'][oc] if oc<4 else 'NA')
        mgr,_,_=sim_market(int(r.decision_i),int(r.dir),float(r.market_entry),risk,target,times_m,bh,bl,bc,ah,al,ac); market_gross.append(float(mgr)); market_net.append(float(mgr-comm))
    y[f'gross_R_{target}']=gross; y[f'net_R_{target}']=net; y[f'stress05_R_{target}']=stress05; y[f'stress10_R_{target}']=stress10; y[f'exit_i_{target}']=exit_i; y[f'outcome_{target}']=outcome; y[f'market_gross_R_{target}']=market_gross; y[f'market_net_R_{target}']=market_net; y[f'uplift_R_{target}']=y[f'net_R_{target}']-y[f'market_net_R_{target}']
    y[f'exit_time_{target}']=[df.at[ei,'time'] if ei>=0 else pd.NaT for ei in exit_i]
    return y


def build_serial(x:pd.DataFrame,target:float)->tuple[pd.DataFrame,pd.DataFrame]:
    rows=[]; lifecycles=[]; busy_until=pd.Timestamp.min
    for r in x.sort_values('decision_time').itertuples(index=False):
        if r.decision_time <= busy_until: continue
        if not r.filled:
            expire=r.decision_time+pd.Timedelta(minutes=RETEST_MINUTES); lifecycles.append({'decision_time':r.decision_time,'filled':False,'busy_until':expire,'event_i':r.event_i}); busy_until=expire; continue
        ex=getattr(r,f'exit_time_{target}')
        if pd.isna(ex): continue
        lifecycles.append({'decision_time':r.decision_time,'filled':True,'busy_until':ex,'event_i':r.event_i}); rows.append(r._asdict()); busy_until=ex
    return pd.DataFrame(rows),pd.DataFrame(lifecycles)


def pf(vals):
    v=pd.Series(vals).dropna(); pos=v[v>0].sum(); neg=-v[v<0].sum(); return float(pos/neg) if neg>0 else (float('inf') if pos>0 else np.nan)

def maxdd(vals):
    v=np.asarray(pd.Series(vals).dropna(),float)
    if len(v)==0:return np.nan
    c=np.cumsum(v); peak=np.maximum.accumulate(np.r_[0,c]); dd=peak[1:]-c; return float(dd.max())

def max_consec_loss(vals):
    m=0;c=0
    for v in pd.Series(vals).dropna():
        if v<0:c+=1;m=max(m,c)
        else:c=0
    return int(m)

def stats(tr:pd.DataFrame,target:float)->dict:
    col=f'net_R_{target}'
    if tr.empty:return {'n':0}
    v=tr[col].dropna(); weeks=pd.to_datetime(tr.entry_time).dt.to_period('W-MON').astype(str).nunique(); daily=tr.assign(day=pd.to_datetime(tr.entry_time).dt.date).groupby('day')[col].sum()
    return {'n':int(len(v)),'trades_per_week':float(len(v)/weeks) if weeks else np.nan,'ev':float(v.mean()),'pf':pf(v),'positive_rate':float((v>0).mean()),'total_R':float(v.sum()),'gross_ev':float(tr[f'gross_R_{target}'].mean()),'tp_rate':float((tr[f'outcome_{target}']=='TP').mean()),'max_dd_R':maxdd(v),'worst_day_R':float(daily.min()) if len(daily) else np.nan,'max_consec_losses':max_consec_loss(v),'stress05_ev':float(tr[f'stress05_R_{target}'].mean()),'stress10_ev':float(tr[f'stress10_R_{target}'].mean()),'buy_ev':float(tr.loc[tr.dir==1,col].mean()),'sell_ev':float(tr.loc[tr.dir==-1,col].mean()),'back_ev':float(tr.loc[tr.branch=='BACK',col].mean()),'through_ev':float(tr.loc[tr.branch=='THROUGH',col].mean()),'mean_entry_improvement_atr':float(tr.entry_improvement_atr.mean()),'median_entry_improvement_atr':float(tr.entry_improvement_atr.median()),'median_wait_entry_min':float(tr.wait_entry_min.median())}

def bootstrap_weekly(tr:pd.DataFrame,col:str,seed:int=20260823)->dict:
    if tr.empty:return {'n_weeks':0,'mean':None,'ci95':[None,None]}
    w=tr.assign(week=pd.to_datetime(tr.entry_time).dt.to_period('W-MON').astype(str)).groupby('week')[col].mean().dropna().to_numpy(float)
    if len(w)<8:return {'n_weeks':int(len(w)),'mean':float(w.mean()) if len(w) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); boot=np.empty(4000)
    for i in range(len(boot)): boot[i]=rng.choice(w,size=len(w),replace=True).mean()
    return {'n_weeks':int(len(w)),'mean':float(w.mean()),'ci95':[float(np.quantile(boot,.025)),float(np.quantile(boot,.975))]}

def fill_diag(x:pd.DataFrame)->dict:
    if x.empty:return {}
    f=x.filled; fc=x.loc[f,'signal_correct'].mean() if f.any() else np.nan; uc=x.loc[~f,'signal_correct'].mean() if (~f).any() else np.nan
    return {'eligible':int(len(x)),'fills':int(f.sum()),'fill_rate':float(f.mean()),'median_wait_confirm_min':float(x.loc[f,'wait_confirm_min'].median()) if f.any() else None,'median_wait_entry_min':float(x.loc[f,'wait_entry_min'].median()) if f.any() else None,'filled_signal_correct_rate':float(fc) if np.isfinite(fc) else None,'unfilled_signal_correct_rate':float(uc) if np.isfinite(uc) else None,'adverse_selection_gap':float(fc-uc) if np.isfinite(fc) and np.isfinite(uc) else None,'missed_directional_move_rate':float(x.loc[~f,'signal_correct'].mean()) if (~f).any() else None}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('canonical',type=Path); ap.add_argument('events',type=Path); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); a.outdir.mkdir(parents=True,exist_ok=True)
    h=sha256(a.canonical)
    if h!=CANONICAL_SHA: raise RuntimeError(f'canonical SHA mismatch {h}')
    df=add_vwap_lines(load_prices(a.canonical)); e=load_events(a.events); ask_ok=all(c in df for c in ['ask_open','ask_high','ask_low','ask_close'])
    samp=e.iloc[::max(1,len(e)//1000)]; lineage=all(int(r.i)<len(df) and df.at[int(r.i),'time']==r.time for r in samp.itertuples())
    if not lineage: raise RuntimeError('LAB002 event index/time lineage mismatch')
    all_clock={}; summaries=[]; serial_store={}; lifecycle_store={}
    for clock in (1,3):
        sig=build_signals(e,clock); ded=dedupe_decisions(sig); en=enrich_retests(ded,df,clock)
        for t in TARGETS: en=simulate_all(en,df,t)
        all_clock[clock]=en; en.to_csv(a.outdir/f'candidates_T{clock}.csv.gz',index=False,compression='gzip')
        for t in TARGETS:
            for split in ['DISCOVERY','CONFIRMATION']:
                q=en[en.split==split].copy(); serial,life=build_serial(q,t); serial_store[(clock,t,split)]=serial; lifecycle_store[(clock,t,split)]=life; s=stats(serial,t); s.update(clock=clock,target=t,split=split,serial_accepted=int(len(life)),serial_fill_rate=float(life.filled.mean()) if len(life) else np.nan); summaries.append(s)
    summary=pd.DataFrame(summaries); summary.to_csv(a.outdir/'summary.csv',index=False)
    primary=serial_store[(3,1.5,'CONFIRMATION')]; disc=serial_store[(3,1.5,'DISCOVERY')]; prim_life=lifecycle_store[(3,1.5,'CONFIRMATION')]
    st=stats(primary,1.5); sd=stats(disc,1.5); st2=stats(serial_store[(3,2.0,'CONFIRMATION')],2.0); w=bootstrap_weekly(primary,'net_R_1.5'); up=bootstrap_weekly(primary,'uplift_R_1.5',20260823)
    fill_conf=fill_diag(all_clock[3][all_clock[3].split=='CONFIRMATION']); fill_disc=fill_diag(all_clock[3][all_clock[3].split=='DISCOVERY']); fill_conf['serial_accepted']=int(len(prim_life)); fill_conf['serial_fills']=int(prim_life.filled.sum()) if len(prim_life) else 0; fill_conf['serial_fill_rate']=float(prim_life.filled.mean()) if len(prim_life) else None
    yearly=[]
    for yr,g in primary.assign(entry_year=pd.to_datetime(primary.entry_time).dt.year).groupby('entry_year'):
        d=stats(g,1.5); d['year']=int(yr); yearly.append(d)
    pd.DataFrame(yearly).to_csv(a.outdir/'yearly.csv',index=False)
    diag=[]; z=all_clock[3][all_clock[3].split=='CONFIRMATION']
    for group in ['branch','dir','level']:
        for k,g in z.groupby(group):
            d=fill_diag(g); d['group']=group; d['value']=str(k); diag.append(d)
    pd.DataFrame(diag).to_csv(a.outdir/'fill_diagnostics.csv',index=False); primary.to_csv(a.outdir/'primary_serial_trades.csv.gz',index=False,compression='gzip')
    gates={'G0_DATA_EXECUTION':bool(h==CANONICAL_SHA and ask_ok and lineage),'G1_FILL_POWER':bool(len(primary)>=500 and fill_conf.get('serial_fill_rate',0)>=.10),'G2_CONFIRMATION_EV':bool(st.get('ev',-999)>0 and st.get('pf',0)>1.0),'G3_WEEK_CLUSTER_CI':bool(w['ci95'][0] is not None and w['ci95'][0]>0),'G4_SPLIT_TRANSFER':bool(st.get('ev',-999)>0 and sd.get('ev',-999)>0),'G5_2R_SURVIVAL':bool(st2.get('ev',-999)>=0),'G6_DIRECTION_BREADTH':bool(st.get('buy_ev',-999)>0 and st.get('sell_ev',-999)>0),'G7_BRANCH_BREADTH':bool(st.get('back_ev',-999)>0 and st.get('through_ev',-999)>0),'G8_PROP_DD_PROXY':bool(st.get('max_dd_R',999)<=20 and st.get('worst_day_R',-999)>-16),'G9_COST_STRESS':bool(st.get('stress10_ev',-999)>0),'G10_RETEST_UPLIFT':bool(up['ci95'][0] is not None and up['ci95'][0]>0)}
    if not gates['G0_DATA_EXECUTION']: status='INVALID_EXECUTION_DATA'
    elif all(gates.values()): status='GO_TO_REPLICATION'
    elif gates['G2_CONFIRMATION_EV'] and gates['G3_WEEK_CLUSTER_CI'] and gates['G4_SPLIT_TRANSFER'] and gates['G10_RETEST_UPLIFT']: status='RETEST_EDGE_NARROW'
    elif gates['G10_RETEST_UPLIFT'] and not gates['G2_CONFIRMATION_EV']: status='RETEST_IMPROVES_BUT_NOT_PROFITABLE'
    else: status='NO_RETEST_EXECUTABLE_EDGE'
    audit={'lab':LAB,'version':VERSION,'canonical_sha256':h,'raw_preholdout_rows':int(len(df)),'lab002_events':int(len(e)),'ask_execution_present':bool(ask_ok),'lineage_ok':bool(lineage),'holdout_opened':False}
    verdict={'status':status,'gates':gates,'primary_confirmation':st,'primary_discovery':sd,'confirmation_2R':st2,'weekly_ev_bootstrap':w,'paired_retest_vs_market_bootstrap':up,'fill_confirmation':fill_conf,'fill_discovery':fill_disc,'holdout_opened':False}
    (a.outdir/'audit.json').write_text(json.dumps(audit,indent=2,default=str)); (a.outdir/'verdict.json').write_text(json.dumps(verdict,indent=2,default=str)); print(json.dumps(audit,indent=2)); print(json.dumps(verdict,indent=2))
if __name__=='__main__': main()
