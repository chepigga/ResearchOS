#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit

LAB='XAU_POST_TOUCH_RETEST_REACCELERATION_IFVG_CAUSAL_LAB_006'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
HOLDOUT_TS=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
ANCHOR_HOUR=1
BAND_K=1.618
HEALTH_MINUTES=5
REACCEL_PROGRESS_ATR=0.10
REACCEL_BODY_ATR=0.05
REACCEL_HOLD_ATR=0.05
FVG_LIFETIME_MIN=240
IFVG_RETEST_MAX_MIN=30
LOCAL_IFVG_PRE_MIN=5
RISK_ATR=0.50
HOLD_MINUTES=60
TARGETS=(1.5,2.0)
COMMISSION_PRICE=0.05
RETEST_MINUTES=15
LEVEL_RANK={'MID':0,'HIGH':1,'LOW':2}
BRANCHES=('PRIMARY_BOTH','REACCEL_ONLY','IFVG_ONLY')


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
    df=df.dropna(subset=use).sort_values('time').drop_duplicates('time',keep='last')
    df=df[df.time<HOLDOUT_TS].copy().reset_index(drop=True)
    return df


def add_vwap_lines(df:pd.DataFrame)->pd.DataFrame:
    o=df.copy(); o['session']=(o.time-pd.Timedelta(hours=ANCHOR_HOUR)).dt.floor('D')
    p=(o.high+o.low+o.close)/3.0; v=o.tick_volume.clip(lower=0).fillna(0)
    gv=v.groupby(o.session).cumsum(); gpv=(p*v).groupby(o.session).cumsum(); gp2=((p*p)*v).groupby(o.session).cumsum()
    mid=gpv/gv.replace(0,np.nan); var=(gp2/gv.replace(0,np.nan)-mid*mid).clip(lower=0); sd=np.sqrt(var)
    o['MID']=mid; o['HIGH']=mid+BAND_K*sd; o['LOW']=mid-BAND_K*sd
    return o


def load_candidates(path:Path)->pd.DataFrame:
    x=pd.read_csv(path,compression='gzip')
    for c in ['touch_time','decision_time','retest_confirm_time','entry_time','exit_time_1p5','exit_time_2p0']:
        if c in x: x[c]=pd.to_datetime(x[c],errors='coerce')
    x=x[x.decision_time<HOLDOUT_TS].copy()
    req=['event_i','touch_time','decision_i','decision_time','level','arrival_side','branch','dir','s','atr0','label_0p5','signal_correct','split','year','filled','retest_confirm_i','entry_i','retest_entry','net_R_1p5','market_net_R_1p5']
    miss=[c for c in req if c not in x]
    if miss: raise ValueError(f'missing LAB005 candidate columns: {miss}')
    x['level_rank']=x.level.map(LEVEL_RANK).astype(int)
    return x


def dedupe_parent(x:pd.DataFrame)->pd.DataFrame:
    z=x.copy(); z['abs_s']=z.s.abs()
    z=z.sort_values(['decision_time','dir','abs_s','level_rank'],ascending=[True,True,False,True]).drop_duplicates(['decision_time','dir'],keep='first')
    c=z.groupby('decision_time').dir.nunique(); conflicts=set(c[c>1].index)
    if conflicts: z=z[~z.decision_time.isin(conflicts)]
    return z.sort_values('decision_time').reset_index(drop=True)


def build_ifvg_events(df:pd.DataFrame)->pd.DataFrame:
    h=df.high.to_numpy(float); l=df.low.to_numpy(float); c=df.close.to_numpy(float); n=len(df); rows=[]
    bull=np.flatnonzero(l[2:]>h[:-2])+2
    bear=np.flatnonzero(h[2:]<l[:-2])+2
    for born in bull:
        lower=float(h[born-2]); upper=float(l[born]); e=min(n,born+1+FVG_LIFETIME_MIN)
        rr=np.flatnonzero(c[born+1:e]<lower)
        if not len(rr): continue
        inv=born+1+int(rr[0]); re=min(n,inv+1+IFVG_RETEST_MAX_MIN)
        m=(h[inv+1:re]>=lower)&(l[inv+1:re]<=upper)&(c[inv+1:re]<lower); q=np.flatnonzero(m)
        if len(q): rows.append((inv+1+int(q[0]),-1,int(born),int(inv),lower,upper))
    for born in bear:
        lower=float(h[born]); upper=float(l[born-2]); e=min(n,born+1+FVG_LIFETIME_MIN)
        rr=np.flatnonzero(c[born+1:e]>upper)
        if not len(rr): continue
        inv=born+1+int(rr[0]); re=min(n,inv+1+IFVG_RETEST_MAX_MIN)
        m=(l[inv+1:re]<=upper)&(h[inv+1:re]>=lower)&(c[inv+1:re]>upper); q=np.flatnonzero(m)
        if len(q): rows.append((inv+1+int(q[0]),1,int(born),int(inv),lower,upper))
    if not rows: return pd.DataFrame(columns=['i','dir','born','inv','lower','upper'])
    z=pd.DataFrame(rows,columns=['i','dir','born','inv','lower','upper']); z['width']=z.upper-z.lower
    return z.sort_values(['i','dir','width','born']).drop_duplicates(['i','dir'],keep='first').drop(columns='width').reset_index(drop=True)


def first_between(arr:np.ndarray, lo:int, hi:int)->int:
    if hi<lo or len(arr)==0: return -1
    p=np.searchsorted(arr,lo,side='left')
    if p<len(arr) and int(arr[p])<=hi: return int(arr[p])
    return -1


def health_map(x:pd.DataFrame,df:pd.DataFrame,ifvg:pd.DataFrame)->pd.DataFrame:
    op=df.open.to_numpy(float); cl=df.close.to_numpy(float); ao=df.ask_open.to_numpy(float); bo=df.open.to_numpy(float)
    times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    levels={k:df[k].to_numpy(float) for k in LEVEL_RANK}
    ifvg_dir={1:np.sort(ifvg.loc[ifvg.dir==1,'i'].to_numpy(int)), -1:np.sort(ifvg.loc[ifvg.dir==-1,'i'].to_numpy(int))}
    rows=[]
    for r in x.itertuples(index=False):
        base=r._asdict(); base['parent_retest']=bool(r.filled)
        di=int(r.decision_i)
        if di<0 or di>=len(df) or df.at[di,'time']!=r.decision_time:
            base.update(lineage_ok=False,reaccel=False,reaccel_i=-1,reaccel_time=pd.NaT,aligned_ifvg_by_reaccel=False,aligned_ifvg_i=-1,post_retest_ifvg=False,post_retest_ifvg_i=-1,primary_both=False,reaccel_only=False,ifvg_only=False)
            rows.append(base); continue
        base['lineage_ok']=True
        if not r.filled or int(r.retest_confirm_i)<0:
            base.update(reaccel=False,reaccel_i=-1,reaccel_time=pd.NaT,aligned_ifvg_by_reaccel=False,aligned_ifvg_i=-1,post_retest_ifvg=False,post_retest_ifvg_i=-1,primary_both=False,reaccel_only=False,ifvg_only=False)
            rows.append(base); continue
        j=int(r.retest_confirm_i); d=int(r.dir); atr=float(r.atr0); lev_arr=levels[str(r.level)]
        if j>=len(df) or pd.isna(r.retest_confirm_time) or df.at[j,'time']!=r.retest_confirm_time:
            base['lineage_ok']=False
            base.update(reaccel=False,reaccel_i=-1,reaccel_time=pd.NaT,aligned_ifvg_by_reaccel=False,aligned_ifvg_i=-1,post_retest_ifvg=False,post_retest_ifvg_i=-1,primary_both=False,reaccel_only=False,ifvg_only=False)
            rows.append(base); continue
        re_i=-1
        for k in range(j+1,min(len(df),j+1+HEALTH_MINUTES)):
            if times[k] != times[j] + (k-j): break
            lev=float(lev_arr[k])
            if not np.isfinite(lev): continue
            progress=d*(cl[k]-cl[j])/atr
            body=d*(cl[k]-op[k])/atr
            hold=d*(cl[k]-lev)/atr
            if progress>=REACCEL_PROGRESS_ATR and body>=REACCEL_BODY_ATR and hold>=REACCEL_HOLD_ATR:
                re_i=k; break
        post_ifvg=first_between(ifvg_dir[d],j,min(len(df)-1,j+HEALTH_MINUTES))
        local_ifvg=-1
        if re_i>=0:
            local_lo=max(di,j-LOCAL_IFVG_PRE_MIN)
            local_ifvg=first_between(ifvg_dir[d],local_lo,re_i)
        primary=(re_i>=0 and local_ifvg>=0)
        reonly=(re_i>=0)
        ionly=(post_ifvg>=0)
        base.update(reaccel=bool(reonly),reaccel_i=int(re_i),reaccel_time=(df.at[re_i,'time'] if re_i>=0 else pd.NaT),aligned_ifvg_by_reaccel=bool(local_ifvg>=0),aligned_ifvg_i=int(local_ifvg),post_retest_ifvg=bool(ionly),post_retest_ifvg_i=int(post_ifvg),primary_both=bool(primary),reaccel_only=bool(reonly),ifvg_only=bool(ionly))
        for name, sig_i in [('PRIMARY_BOTH', re_i if primary else -1),('REACCEL_ONLY', re_i if reonly else -1),('IFVG_ONLY', post_ifvg if ionly else -1)]:
            ei=sig_i+1 if sig_i>=0 else -1
            ok=ei<len(df) and ei>=0 and times[ei]==times[sig_i]+1
            if not ok: ei=-1
            ep=(ao[ei] if d>0 else bo[ei]) if ei>=0 else np.nan
            base[f'{name}_entry_i']=int(ei); base[f'{name}_entry_time']=df.at[ei,'time'] if ei>=0 else pd.NaT; base[f'{name}_entry']=float(ep) if np.isfinite(ep) else np.nan
            base[f'{name}_wait_min']=(df.at[ei,'time']-r.decision_time).total_seconds()/60 if ei>=0 else np.nan
            base[f'{name}_vs_retest_entry_atr']=d*(float(r.retest_entry)-ep)/atr if ei>=0 and np.isfinite(r.retest_entry) else np.nan
        rows.append(base)
    return pd.DataFrame(rows)

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
    exitp=bc[last] if d>0 else ac[last]
    rr=d*(exitp-entry)/risk
    if rr<-1.0: rr=-1.0
    if rr>target: rr=target
    return rr,last,3


def tkey(t:float)->str: return str(t).replace('.','p')

def simulate_branch(x:pd.DataFrame,df:pd.DataFrame,branch:str,target:float)->pd.DataFrame:
    y=x.copy(); key=tkey(target)
    times_m=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    bh=df.high.to_numpy(float); bl=df.low.to_numpy(float); bc=df.close.to_numpy(float); ah=df.ask_high.to_numpy(float); al=df.ask_low.to_numpy(float); ac=df.ask_close.to_numpy(float)
    vals=[]; gross=[]; stress05=[]; stress10=[]; out=[]; exi=[]; ext=[]
    for r in y.itertuples(index=False):
        ei=int(getattr(r,f'{branch}_entry_i'))
        if ei<0:
            vals.append(np.nan); gross.append(np.nan); stress05.append(np.nan); stress10.append(np.nan); out.append('NO_ENTRY'); exi.append(-1); ext.append(pd.NaT); continue
        d=int(r.dir); atr=float(r.atr0); risk=RISK_ATR*atr; entry=float(getattr(r,f'{branch}_entry'))
        gr,xi,oc=sim_trade(ei,d,entry,risk,target,times_m,bh,bl,bc,ah,al,ac)
        comm=COMMISSION_PRICE/risk; nr=gr-comm
        gross.append(float(gr)); vals.append(float(nr)); stress05.append(float(nr-0.05/risk)); stress10.append(float(nr-0.10/risk)); exi.append(int(xi)); ext.append(df.at[xi,'time']); out.append(['SL','TP','SAME_BAR_LOSS','TIME'][oc])
    y[f'{branch}_gross_R_{key}']=gross; y[f'{branch}_net_R_{key}']=vals; y[f'{branch}_stress05_R_{key}']=stress05; y[f'{branch}_stress10_R_{key}']=stress10; y[f'{branch}_outcome_{key}']=out; y[f'{branch}_exit_i_{key}']=exi; y[f'{branch}_exit_time_{key}']=ext
    return y


def build_serial(parent:pd.DataFrame,df:pd.DataFrame,branch:str,target:float)->tuple[pd.DataFrame,pd.DataFrame]:
    key=tkey(target); rows=[]; life=[]; busy=pd.Timestamp.min
    for r in parent.sort_values('decision_time').itertuples(index=False):
        if r.decision_time<=busy: continue
        if not r.filled:
            end=r.decision_time+pd.Timedelta(minutes=RETEST_MINUTES); life.append({'decision_time':r.decision_time,'status':'NO_RETEST','busy_until':end}); busy=end; continue
        jtime=r.retest_confirm_time
        ei=int(getattr(r,f'{branch}_entry_i'))
        if ei<0:
            end=jtime+pd.Timedelta(minutes=HEALTH_MINUTES); life.append({'decision_time':r.decision_time,'status':'NO_HEALTH','busy_until':end}); busy=end; continue
        ex=getattr(r,f'{branch}_exit_time_{key}')
        if pd.isna(ex): continue
        rows.append(r._asdict()); life.append({'decision_time':r.decision_time,'status':'TRADE','busy_until':ex}); busy=ex
    return pd.DataFrame(rows),pd.DataFrame(life)


def pf(v):
    s=pd.Series(v).dropna(); pos=s[s>0].sum(); neg=-s[s<0].sum(); return float(pos/neg) if neg>0 else (float('inf') if pos>0 else np.nan)
def maxdd(v):
    a=np.asarray(pd.Series(v).dropna(),float)
    if not len(a): return np.nan
    c=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0,c]); return float((peak[1:]-c).max())
def max_consec(v):
    m=c=0
    for z in pd.Series(v).dropna():
        if z<0: c+=1; m=max(m,c)
        else: c=0
    return int(m)
def weeks_span(times)->float:
    t=pd.to_datetime(pd.Series(times).dropna())
    if len(t)<2:return np.nan
    return max(1.0,(t.max()-t.min()).total_seconds()/(7*86400))
def stats(tr:pd.DataFrame,branch:str,target:float)->dict:
    key=tkey(target); col=f'{branch}_net_R_{key}'
    if tr.empty:return {'n':0}
    v=tr[col].dropna(); span=weeks_span(tr.decision_time)
    daily=tr.assign(day=pd.to_datetime(tr[f'{branch}_entry_time']).dt.date).groupby('day')[col].sum()
    return {'n':int(len(v)),'trades_per_week':float(len(v)/span) if np.isfinite(span) else None,'ev':float(v.mean()),'pf':pf(v),'positive_rate':float((v>0).mean()),'total_R':float(v.sum()),'gross_ev':float(tr[f'{branch}_gross_R_{key}'].mean()),'tp_rate':float((tr[f'{branch}_outcome_{key}']=='TP').mean()),'max_dd_R':maxdd(v),'worst_day_R':float(daily.min()) if len(daily) else None,'max_consec_losses':max_consec(v),'stress05_ev':float(tr[f'{branch}_stress05_R_{key}'].mean()),'stress10_ev':float(tr[f'{branch}_stress10_R_{key}'].mean()),'buy_ev':float(tr.loc[tr.dir==1,col].mean()),'sell_ev':float(tr.loc[tr.dir==-1,col].mean()),'back_ev':float(tr.loc[tr.branch=='BACK',col].mean()),'through_ev':float(tr.loc[tr.branch=='THROUGH',col].mean()),'correct_rate':float(tr.signal_correct.mean()),'median_wait_entry_min':float(tr[f'{branch}_wait_min'].median()),'median_vs_retest_entry_atr':float(tr[f'{branch}_vs_retest_entry_atr'].median())}


def bootstrap_weekly_mean(tr:pd.DataFrame,col:str,time_col:str,seed=20260823)->dict:
    if tr.empty:return {'n_weeks':0,'mean':None,'ci95':[None,None]}
    z=tr.copy(); z['week']=pd.to_datetime(z[time_col]).dt.to_period('W-SUN').astype(str); w=z.groupby('week')[col].mean().dropna().to_numpy(float)
    if len(w)<8:return {'n_weeks':int(len(w)),'mean':float(w.mean()) if len(w) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); boot=np.array([rng.choice(w,size=len(w),replace=True).mean() for _ in range(4000)])
    return {'n_weeks':int(len(w)),'mean':float(w.mean()),'ci95':[float(np.quantile(boot,.025)),float(np.quantile(boot,.975))]}


def bootstrap_correctness_uplift(x:pd.DataFrame,seed=20260823)->dict:
    z=x[x.filled].copy(); z['pass']=z.primary_both.astype(bool); z['week']=pd.to_datetime(z.decision_time).dt.to_period('W-SUN').astype(str)
    cells=[]
    for w,g in z.groupby('week'):
        a=g.loc[g['pass'],'signal_correct']; b=g.loc[~g['pass'],'signal_correct']
        if len(a) and len(b): cells.append(float(a.mean()-b.mean()))
    vals=np.array(cells,float)
    if len(vals)<8:return {'n_weeks':int(len(vals)),'mean':float(vals.mean()) if len(vals) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); boot=np.array([rng.choice(vals,size=len(vals),replace=True).mean() for _ in range(4000)])
    return {'n_weeks':int(len(vals)),'mean':float(vals.mean()),'ci95':[float(np.quantile(boot,.025)),float(np.quantile(boot,.975))]}


def selection_diag(x:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for split,g in x[x.filled].groupby('split'):
        for branch,flag in [('PRIMARY_BOTH','primary_both'),('REACCEL_ONLY','reaccel_only'),('IFVG_ONLY','ifvg_only')]:
            p=g[g[flag]].copy(); f=g[~g[flag]].copy()
            rows.append({'split':split,'branch':branch,'parent_retest_n':len(g),'pass_n':len(p),'pass_rate':len(p)/len(g) if len(g) else np.nan,'pass_correct':p.signal_correct.mean() if len(p) else np.nan,'fail_correct':f.signal_correct.mean() if len(f) else np.nan,'correct_uplift_pp':100*((p.signal_correct.mean() if len(p) else np.nan)-(f.signal_correct.mean() if len(f) else np.nan))})
    return pd.DataFrame(rows)


def independent_branch_stats(x:pd.DataFrame,branch:str,target:float,split:str)->dict:
    key=tkey(target); flag={'PRIMARY_BOTH':'primary_both','REACCEL_ONLY':'reaccel_only','IFVG_ONLY':'ifvg_only'}[branch]
    g=x[(x.split==split)&x[flag]&x[f'{branch}_net_R_{key}'].notna()].copy()
    if g.empty:return {'n':0,'ev':None,'pf':None,'correct_rate':None}
    return {'n':int(len(g)),'ev':float(g[f'{branch}_net_R_{key}'].mean()),'pf':pf(g[f'{branch}_net_R_{key}']),'correct_rate':float(g.signal_correct.mean()),'tp_rate':float((g[f'{branch}_outcome_{key}']=='TP').mean())}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('canonical',type=Path); ap.add_argument('candidates',type=Path); ap.add_argument('--outdir',type=Path,required=True)
    a=ap.parse_args(); a.outdir.mkdir(parents=True,exist_ok=True)
    h=sha256(a.canonical)
    if h!=CANONICAL_SHA: raise RuntimeError(f'canonical SHA mismatch {h}')
    df=add_vwap_lines(load_prices(a.canonical)); cand=load_candidates(a.candidates)
    ask_ok=all(c in df for c in ['ask_open','ask_high','ask_low','ask_close'])
    ifvg=build_ifvg_events(df)
    mapped=health_map(cand,df,ifvg)
    if not bool(mapped.lineage_ok.all()): raise RuntimeError(f'lineage failure rows={(~mapped.lineage_ok).sum()}')
    for branch in BRANCHES:
        for t in TARGETS: mapped=simulate_branch(mapped,df,branch,t)
    parent=dedupe_parent(mapped)
    serial={}
    for branch in BRANCHES:
        for t in TARGETS:
            tr,life=build_serial(parent,df,branch,t); serial[(branch,t)]=tr
    mapped.to_csv(a.outdir/'candidates_health.csv.gz',index=False,compression='gzip')
    primary_serial=serial[('PRIMARY_BOTH',1.5)]; primary_serial.to_csv(a.outdir/'primary_serial_trades.csv.gz',index=False,compression='gzip')
    sel=selection_diag(mapped); sel.to_csv(a.outdir/'selection_diagnostics.csv',index=False)
    rows=[]
    for split in ['DISCOVERY','CONFIRMATION']:
        for branch in BRANCHES:
            for t in TARGETS:
                tr=serial[(branch,t)]; g=tr[tr.split==split].copy(); rows.append({'split':split,'branch':branch,'target':t,**stats(g,branch,t)})
    summary=pd.DataFrame(rows); summary.to_csv(a.outdir/'summary.csv',index=False)
    yr=[]; tr=serial[('PRIMARY_BOTH',1.5)]
    for y,g in tr.groupby('year'): yr.append({'year':int(y),**stats(g,'PRIMARY_BOTH',1.5)})
    pd.DataFrame(yr).to_csv(a.outdir/'yearly.csv',index=False)
    conf=primary_serial[primary_serial.split=='CONFIRMATION'].copy(); disc=primary_serial[primary_serial.split=='DISCOVERY'].copy()
    conf2=serial[('PRIMARY_BOTH',2.0)]; conf2=conf2[conf2.split=='CONFIRMATION'].copy()
    cs=stats(conf,'PRIMARY_BOTH',1.5); ds=stats(disc,'PRIMARY_BOTH',1.5); c2=stats(conf2,'PRIMARY_BOTH',2.0)
    weekly=bootstrap_weekly_mean(conf,'PRIMARY_BOTH_net_R_1p5','PRIMARY_BOTH_entry_time')
    same=mapped[(mapped.split=='CONFIRMATION')&mapped.primary_both&mapped.PRIMARY_BOTH_net_R_1p5.notna()&mapped.net_R_1p5.notna()].copy(); same['delta_vs_lab005']=same.PRIMARY_BOTH_net_R_1p5-same.net_R_1p5
    paired=bootstrap_weekly_mean(same,'delta_vs_lab005','decision_time')
    health_boot_conf=bootstrap_correctness_uplift(mapped[mapped.split=='CONFIRMATION']); health_boot_disc=bootstrap_correctness_uplift(mapped[mapped.split=='DISCOVERY'])
    indep={}
    for split in ['DISCOVERY','CONFIRMATION']:
        indep[split]={b:independent_branch_stats(mapped,b,1.5,split) for b in BRANCHES}
    conf_primary_ind=indep['CONFIRMATION']['PRIMARY_BOTH']; conf_re_ind=indep['CONFIRMATION']['REACCEL_ONLY']
    def pass_fail(split):
        g=mapped[(mapped.split==split)&mapped.filled]; p=g[g.primary_both]; f=g[~g.primary_both]
        return {'parent_retest_n':int(len(g)),'primary_pass_n':int(len(p)),'primary_pass_rate':float(len(p)/len(g)) if len(g) else None,'pass_correct':float(p.signal_correct.mean()) if len(p) else None,'fail_correct':float(f.signal_correct.mean()) if len(f) else None,'uplift_pp':float(100*(p.signal_correct.mean()-f.signal_correct.mean())) if len(p) and len(f) else None}
    pfconf=pass_fail('CONFIRMATION'); pfdisc=pass_fail('DISCOVERY')
    g={'G0_DATA_EXECUTION':bool(h==CANONICAL_SHA and ask_ok),'G1_PRIMARY_POWER':bool(cs.get('n',0)>=300 and (cs.get('trades_per_week') or 0)>=15),'G2_CONFIRMATION_EV':bool(cs.get('n',0)>0 and cs.get('ev',-1)>0 and cs.get('pf',0)>1),'G3_WEEK_CLUSTER_CI':bool(weekly['ci95'][0] is not None and weekly['ci95'][0]>0),'G4_SPLIT_TRANSFER':bool(cs.get('ev',-1)>0 and ds.get('ev',-1)>0),'G5_2R_SURVIVAL':bool(c2.get('ev',-1)>=0),'G6_DIRECTION_BREADTH':bool(cs.get('buy_ev',-1)>0 and cs.get('sell_ev',-1)>0),'G7_BRANCH_BREADTH':bool(cs.get('back_ev',-1)>0 and cs.get('through_ev',-1)>0),'G8_PROP_DD_PROXY':bool(cs.get('max_dd_R',1e9)<=20 and cs.get('worst_day_R',-1e9)>-16),'G9_COST_STRESS':bool(cs.get('stress10_ev',-1)>0),'G10_HEALTH_SELECTION':bool((pfconf.get('uplift_pp') or -999)>=5 and (pfdisc.get('uplift_pp') or -999)>=5),'G11_IFVG_INCREMENTAL':bool((conf_primary_ind.get('n') or 0)>=300 and (conf_primary_ind.get('ev') or -999)>=(conf_re_ind.get('ev') or 999) and (conf_primary_ind.get('correct_rate') or -999)>=(conf_re_ind.get('correct_rate') or 999))}
    if not g['G0_DATA_EXECUTION']: status='INVALID_EXECUTION_DATA'
    elif all(g.values()): status='GO_TO_REPLICATION'
    elif all(g[k] for k in g if k!='G11_IFVG_INCREMENTAL') and not g['G11_IFVG_INCREMENTAL']: status='REACCEL_EDGE_IFVG_NOT_INCREMENTAL'
    elif g['G2_CONFIRMATION_EV'] and g['G3_WEEK_CLUSTER_CI'] and g['G4_SPLIT_TRANSFER'] and g['G10_HEALTH_SELECTION']: status='NARROW_HEALTH_SUBSET'
    elif g['G10_HEALTH_SELECTION'] and not g['G2_CONFIRMATION_EV']: status='HEALTH_FILTER_IMPROVES_BUT_NOT_PROFITABLE'
    else: status='NO_REACCEL_IFVG_EXECUTABLE_EDGE'
    audit={'lab':LAB,'version':VERSION,'canonical_sha256':h,'pre_holdout_rows':int(len(df)),'candidate_rows':int(len(cand)),'ifvg_events':int(len(ifvg)),'holdout_opened':False,'ask_execution_available':bool(ask_ok),'spec_parent':'LAB005 candidates_T3','health_minutes':HEALTH_MINUTES,'reaccel_thresholds_atr':[REACCEL_PROGRESS_ATR,REACCEL_BODY_ATR,REACCEL_HOLD_ATR]}
    verdict={'status':status,'gates':g,'primary_confirmation':cs,'primary_discovery':ds,'confirmation_2R':c2,'weekly_ev_bootstrap':weekly,'paired_vs_lab005_retest_bootstrap':paired,'health_selection_confirmation':pfconf,'health_selection_discovery':pfdisc,'health_selection_bootstrap_confirmation':health_boot_conf,'health_selection_bootstrap_discovery':health_boot_disc,'independent_ablation':indep,'holdout_opened':False}
    (a.outdir/'audit.json').write_text(json.dumps(audit,indent=2,default=str)); (a.outdir/'verdict.json').write_text(json.dumps(verdict,indent=2,default=str))
    report=f'''# {LAB} — v001 REPORT\n\n**Verdict:** `{status}`  \n**Holdout opened:** `false`\n\n## Audit\n\n- canonical SHA: `{h}`\n- pre-holdout rows: {len(df):,}\n- LAB005 parent candidate rows: {len(cand):,}\n- causal confirmed iFVG events: {len(ifvg):,}\n\n## Primary Confirmation — BOTH / T+3 / 1.5R / serial\n\n- N: **{cs.get('n',0):,}**\n- trades/week: **{cs.get('trades_per_week')}**\n- EV: **{cs.get('ev')}R**\n- PF: **{cs.get('pf')}**\n- TP rate: **{cs.get('tp_rate')}**\n- gross EV: **{cs.get('gross_ev')}R**\n- max DD: **{cs.get('max_dd_R')}R**\n- worst day: **{cs.get('worst_day_R')}R**\n- BUY EV: **{cs.get('buy_ev')}R**\n- SELL EV: **{cs.get('sell_ev')}R**\n- BACK EV: **{cs.get('back_ev')}R**\n- THROUGH EV: **{cs.get('through_ev')}R**\n- +$0.10 stress EV: **{cs.get('stress10_ev')}R**\n\nWeekly CI: **{weekly['ci95']}**.\n\n## Health selection\n\nConfirmation: parent retests {pfconf.get('parent_retest_n'):,}, BOTH pass {pfconf.get('primary_pass_n'):,} ({pfconf.get('primary_pass_rate'):.2%}); correctness pass **{pfconf.get('pass_correct'):.2%}** vs fail **{pfconf.get('fail_correct'):.2%}**, uplift **{pfconf.get('uplift_pp'):.2f} pp**.\n\nDiscovery: parent retests {pfdisc.get('parent_retest_n'):,}, BOTH pass {pfdisc.get('primary_pass_n'):,} ({pfdisc.get('primary_pass_rate'):.2%}); correctness pass **{pfdisc.get('pass_correct'):.2%}** vs fail **{pfdisc.get('fail_correct'):.2%}**, uplift **{pfdisc.get('uplift_pp'):.2f} pp**.\n\n## Ablation — independent Confirmation 1.5R\n\n- PRIMARY_BOTH: `{indep['CONFIRMATION']['PRIMARY_BOTH']}`\n- REACCEL_ONLY: `{indep['CONFIRMATION']['REACCEL_ONLY']}`\n- IFVG_ONLY: `{indep['CONFIRMATION']['IFVG_ONLY']}`\n\n## Frozen gates\n\n'''+"\n".join(f"- {k}: {'PASS' if v else 'FAIL'}" for k,v in g.items())+'''\n\n## Interpretation\n\nThe LAB changes only the post-retest health-confirmation dimension. The primary result must be judged on executable serial P&L and transfer, not on classification accuracy alone.\n\nNo holdout opening or live/EA allocation is authorized automatically.\n'''
    (a.outdir/'REPORT.md').write_text(report)
    print(json.dumps(audit,indent=2,default=str)); print(json.dumps(verdict,indent=2,default=str))

if __name__=='__main__': main()
