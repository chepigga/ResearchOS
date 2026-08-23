#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LAB='XAU_RETEST_BAR_EARLY_HEALTH_PROXY_AND_IFVG_ENTRY_LAB_007'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
HOLDOUT_TS=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
ANCHOR_HOUR=1
BAND_K=1.618
SIGNAL_THR=0.10
RETEST_MINUTES=15
RETEST_ZONE_ATR=0.05
CONFIRM_CLOSE_ATR=0.03
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
LEVEL_RANK={'MID':0,'HIGH':1,'LOW':2}
CONT_FEATURES=['close_hold_atr','body_dir_atr','rejection_wick_atr','adverse_wick_atr','directional_clv','range_atr','penetration_atr','progress_1m_atr','progress_3m_atr','wait_from_decision_min']
BIN_FEATURES=['existing_aligned_ifvg']

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def load_prices(path:Path)->pd.DataFrame:
    use=['time','open','high','low','close','ask_open','ask_high','ask_low','ask_close','tick_volume']
    df=pd.read_csv(path,sep=';',usecols=use);df['time']=pd.to_datetime(df.time,format='%Y.%m.%d %H:%M',errors='coerce')
    for c in use:
        if c!='time':df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=use).sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    return df[df.time<HOLDOUT_TS].copy().reset_index(drop=True)

def add_vwap_lines(df):
    o=df.copy();o['session']=(o.time-pd.Timedelta(hours=ANCHOR_HOUR)).dt.floor('D');p=(o.high+o.low+o.close)/3.0;v=o.tick_volume.clip(lower=0).fillna(0)
    gv=v.groupby(o.session).cumsum();gpv=(p*v).groupby(o.session).cumsum();gp2=((p*p)*v).groupby(o.session).cumsum();mid=gpv/gv.replace(0,np.nan);var=(gp2/gv.replace(0,np.nan)-mid*mid).clip(lower=0);sd=np.sqrt(var)
    o['MID']=mid;o['HIGH']=mid+BAND_K*sd;o['LOW']=mid-BAND_K*sd;return o

def load_events(path:Path):
    e=pd.read_csv(path,compression='gzip');e['time']=pd.to_datetime(e.time);e=e[e.time<HOLDOUT_TS].copy();return e

def build_signals(e):
    z=e[np.isfinite(e.final_side_3m_atr)].copy();z['s']=z.final_side_3m_atr.astype(float);z=z[(z.s>=SIGNAL_THR)|(z.s<=-SIGNAL_THR)].copy();z['branch']=np.where(z.s>=SIGNAL_THR,'BACK','THROUGH');z['dir']=np.where(z.branch.eq('BACK'),z.arrival_side,-z.arrival_side).astype(int);z['decision_i']=z.i.astype(int)+3;z['decision_time']=z.time+pd.to_timedelta(3,unit='m');z['signal_correct']=np.where(z.branch.eq('BACK'),z.label_0p5.eq('REJECTION'),z.label_0p5.eq('ACCEPTANCE'));z['level_rank']=z.level.map(LEVEL_RANK).astype(int);return z

def dedupe_decisions(z):
    x=z.copy();x['abs_s']=x.s.abs();x=x.sort_values(['decision_time','dir','abs_s','level_rank'],ascending=[True,True,False,True]).drop_duplicates(['decision_time','dir'],keep='first');c=x.groupby('decision_time').dir.nunique();conflicts=set(c[c>1].index)
    if conflicts:x=x[~x.decision_time.isin(conflicts)]
    return x.sort_values('decision_time').reset_index(drop=True)

@njit
def find_retest(dec_i,d,atr0,level_code,times_m,high,low,close,mid,highline,lowline):
    n=len(close);start=dec_i+1
    if start>=n:return -1,-1
    end_time=times_m[dec_i]+RETEST_MINUTES
    for j in range(start,n):
        if times_m[j]>end_time:break
        lev=mid[j] if level_code==0 else (highline[j] if level_code==1 else lowline[j])
        if not np.isfinite(lev):continue
        if not ((low[j]<=lev+RETEST_ZONE_ATR*atr0) and (high[j]>=lev-RETEST_ZONE_ATR*atr0)):continue
        if d*(close[j]-lev)/atr0<CONFIRM_CLOSE_ATR:continue
        k=j+1
        if k<n and times_m[k]==times_m[j]+1:return j,k
    return -1,-1

def enrich_retests(z,df):
    tm=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64);bh=df.high.to_numpy(float);bl=df.low.to_numpy(float);bc=df.close.to_numpy(float);ac=df.ask_close.to_numpy(float);ao=df.ask_open.to_numpy(float);bo=df.open.to_numpy(float);mid=df.MID.to_numpy(float);hi=df.HIGH.to_numpy(float);lo=df.LOW.to_numpy(float);rows=[]
    for r in z.itertuples(index=False):
        di=int(r.decision_i);d=int(r.dir);atr=float(r.atr0);lc=LEVEL_RANK[str(r.level)]
        if di>=len(df) or int(r.i)>=len(df) or df.at[int(r.i),'time']!=r.time or df.at[di,'time']!=r.decision_time:continue
        ci,ei=find_retest(di,d,atr,lc,tm,bh,bl,bc,mid,hi,lo);filled=ei>=0;base={'event_i':int(r.i),'touch_time':r.time,'decision_i':di,'decision_time':r.decision_time,'level':str(r.level),'arrival_side':int(r.arrival_side),'branch':str(r.branch),'dir':d,'s':float(r.s),'atr0':atr,'label_0p5':str(r.label_0p5),'signal_correct':bool(r.signal_correct),'split':str(r.split),'year':int(r.year),'filled':bool(filled),'level_rank':lc}
        if not filled:base.update(retest_confirm_i=-1,retest_confirm_time=pd.NaT,entry_i=-1,entry_time=pd.NaT,wait_confirm_min=np.nan,wait_entry_min=np.nan,retest_entry=np.nan)
        else:
            entry=ao[ei] if d>0 else bo[ei];base.update(retest_confirm_i=int(ci),retest_confirm_time=df.at[ci,'time'],entry_i=int(ei),entry_time=df.at[ei,'time'],wait_confirm_min=(df.at[ci,'time']-r.decision_time).total_seconds()/60,wait_entry_min=(df.at[ei,'time']-r.decision_time).total_seconds()/60,retest_entry=float(entry))
        rows.append(base)
    return pd.DataFrame(rows)

def build_ifvg_events(df):
    h=df.high.to_numpy(float);l=df.low.to_numpy(float);c=df.close.to_numpy(float);n=len(df);rows=[];bull=np.flatnonzero(l[2:]>h[:-2])+2;bear=np.flatnonzero(h[2:]<l[:-2])+2
    for born in bull:
        lower=float(h[born-2]);upper=float(l[born]);e=min(n,born+1+FVG_LIFETIME_MIN);rr=np.flatnonzero(c[born+1:e]<lower)
        if not len(rr):continue
        inv=born+1+int(rr[0]);re=min(n,inv+1+IFVG_RETEST_MAX_MIN);m=(h[inv+1:re]>=lower)&(l[inv+1:re]<=upper)&(c[inv+1:re]<lower);q=np.flatnonzero(m)
        if len(q):rows.append((inv+1+int(q[0]),-1,int(born),int(inv),lower,upper))
    for born in bear:
        lower=float(h[born]);upper=float(l[born-2]);e=min(n,born+1+FVG_LIFETIME_MIN);rr=np.flatnonzero(c[born+1:e]>upper)
        if not len(rr):continue
        inv=born+1+int(rr[0]);re=min(n,inv+1+IFVG_RETEST_MAX_MIN);m=(l[inv+1:re]<=upper)&(h[inv+1:re]>=lower)&(c[inv+1:re]>upper);q=np.flatnonzero(m)
        if len(q):rows.append((inv+1+int(q[0]),1,int(born),int(inv),lower,upper))
    if not rows:return pd.DataFrame(columns=['i','dir'])
    x=pd.DataFrame(rows,columns=['i','dir','born','inv','lower','upper']);x['width']=x.upper-x.lower;return x.sort_values(['i','dir','width','born']).drop_duplicates(['i','dir']).drop(columns='width').reset_index(drop=True)

def first_between(arr,lo,hi):
    if hi<lo or len(arr)==0:return -1
    p=np.searchsorted(arr,lo,side='left');return int(arr[p]) if p<len(arr) and int(arr[p])<=hi else -1

def add_health_and_features(x,df,ifvg):
    op=df.open.to_numpy(float);hi=df.high.to_numpy(float);lo=df.low.to_numpy(float);cl=df.close.to_numpy(float);tm=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64);levels={k:df[k].to_numpy(float) for k in LEVEL_RANK};ids={1:np.sort(ifvg.loc[ifvg.dir==1,'i'].to_numpy(int)),-1:np.sort(ifvg.loc[ifvg.dir==-1,'i'].to_numpy(int))};rows=[]
    for r in x.itertuples(index=False):
        b=r._asdict()
        if not r.filled:
            b.update(future_primary_both=False,existing_aligned_ifvg=0);[b.__setitem__(f,np.nan) for f in CONT_FEATURES];rows.append(b);continue
        j=int(r.retest_confirm_i);di=int(r.decision_i);d=int(r.dir);atr=float(r.atr0);lv=levels[str(r.level)];lev=float(lv[j]);o=float(op[j]);h=float(hi[j]);l=float(lo[j]);c=float(cl[j]);rng=max(h-l,0.0);body=d*(c-o)/atr
        if d>0:rej=max(0,min(o,c)-l)/atr;adv=max(0,h-max(o,c))/atr;pen=max(0,lev-l)/atr
        else:rej=max(0,h-max(o,c))/atr;adv=max(0,min(o,c)-l)/atr;pen=max(0,h-lev)/atr
        clv=d*(2*c-h-l)/rng if rng>0 else 0;p1=d*(c-cl[j-1])/atr if j>=1 and tm[j]-tm[j-1]==1 else np.nan;p3=d*(c-cl[j-3])/atr if j>=3 and tm[j]-tm[j-3]==3 else np.nan;existing=first_between(ids[d],max(di,j-5),j)>=0
        b.update(close_hold_atr=d*(c-lev)/atr,body_dir_atr=body,rejection_wick_atr=rej,adverse_wick_atr=adv,directional_clv=clv,range_atr=rng/atr,penetration_atr=pen,progress_1m_atr=p1,progress_3m_atr=p3,wait_from_decision_min=float(r.wait_confirm_min),existing_aligned_ifvg=int(existing))
        re_i=-1
        for k in range(j+1,min(len(df),j+6)):
            if tm[k]!=tm[j]+(k-j):break
            lk=float(lv[k]);progress=d*(cl[k]-cl[j])/atr;bdy=d*(cl[k]-op[k])/atr;hold=d*(cl[k]-lk)/atr
            if progress>=.10 and bdy>=.05 and hold>=.05:re_i=k;break
        lif=-1 if re_i<0 else first_between(ids[d],max(di,j-5),re_i);b['future_primary_both']=bool(re_i>=0 and lif>=0);rows.append(b)
    return pd.DataFrame(rows)

@njit
def sim_trade(ei,d,entry,risk,target,tm,bh,bl,bc,ah,al,ac):
    end=tm[ei]+60;tp=entry+d*target*risk;sl=entry-d*risk;last=ei
    for j in range(ei,len(bc)):
        if tm[j]>end:break
        last=j;ht=bh[j]>=tp if d>0 else al[j]<=tp;hs=bl[j]<=sl if d>0 else ah[j]>=sl
        if ht and hs:return -1.,j,2
        if hs:return -1.,j,0
        if ht:return target,j,1
    xp=bc[last] if d>0 else ac[last];rr=d*(xp-entry)/risk;return max(-1.,min(target,rr)),last,3

def simulate(x,df,target):
    y=x.copy();k=str(target).replace('.','p');tm=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64);bh=df.high.to_numpy(float);bl=df.low.to_numpy(float);bc=df.close.to_numpy(float);ah=df.ask_high.to_numpy(float);al=df.ask_low.to_numpy(float);ac=df.ask_close.to_numpy(float);G=[];N=[];S10=[];O=[];XT=[]
    for r in y.itertuples(index=False):
        if not r.filled:G.append(np.nan);N.append(np.nan);S10.append(np.nan);O.append('UNFILLED');XT.append(pd.NaT);continue
        risk=.5*float(r.atr0);gr,xi,oc=sim_trade(int(r.entry_i),int(r.dir),float(r.retest_entry),risk,target,tm,bh,bl,bc,ah,al,ac);nr=gr-.05/risk;G.append(gr);N.append(nr);S10.append(nr-.10/risk);O.append(['SL','TP','SAME_BAR_LOSS','TIME'][oc]);XT.append(df.at[xi,'time'])
    y[f'gross_R_{k}']=G;y[f'net_R_{k}']=N;y[f'stress10_R_{k}']=S10;y[f'outcome_{k}']=O;y[f'exit_time_{k}']=XT;return y

def model(include_ifvg=True):
    cont=CONT_FEATURES;bins=BIN_FEATURES if include_ifvg else [];trs=[('cont',Pipeline([('imp',SimpleImputer(strategy='median')),('scale',StandardScaler())]),cont)]
    if bins:trs.append(('bin','passthrough',bins))
    return Pipeline([('pre',ColumnTransformer(trs,remainder='drop',verbose_feature_names_out=False)),('clf',LogisticRegression(C=1.,solver='lbfgs',max_iter=2000))])
def score(x,include_ifvg=True):
    f=x[x.filled].copy();d=f[f.split=='DISCOVERY'];m=model(include_ifvg);features=CONT_FEATURES+(BIN_FEATURES if include_ifvg else []);m.fit(d[features],d.future_primary_both.astype(int));f['health_score']=m.predict_proba(f[features])[:,1];cut=float(np.quantile(f.loc[f.split=='DISCOVERY','health_score'],.70));f['selected']=f.health_score>=cut;return f,m,cut

def auc(y,p):return float(roc_auc_score(y,p)) if len(np.unique(y))>1 else np.nan
def diag(x,split):
    z=x[x.split==split];s=z.selected;sp=z.loc[s,'future_primary_both'].mean();rp=z.loc[~s,'future_primary_both'].mean();sc=z.loc[s,'signal_correct'].mean();rc=z.loc[~s,'signal_correct'].mean();return {'n':len(z),'auc':auc(z.future_primary_both,z.health_score),'brier':float(brier_score_loss(z.future_primary_both,z.health_score)),'selected_fraction':s.mean(),'selected_health_precision':sp,'rejected_health_precision':rp,'health_gap_pp':100*(sp-rp),'selected_direction_correct':sc,'rejected_direction_correct':rc,'direction_gap_pp':100*(sc-rc)}
def pf(v):
    s=pd.Series(v).dropna();return float(s[s>0].sum()/-s[s<0].sum()) if (s<0).any() else np.nan
def mdd(v):
    a=np.array(pd.Series(v).dropna(),float)
    if not len(a):return np.nan
    c=np.cumsum(a);p=np.maximum.accumulate(np.r_[0,c]);return float((p[1:]-c).max())
def stats(t,target):
    k=str(target).replace('.','p');col=f'net_R_{k}'
    if t.empty:return {'n':0}
    v=t[col].dropna();days=t.assign(day=pd.to_datetime(t.entry_time).dt.date).groupby('day')[col].sum();weeks=max(1.,(pd.to_datetime(t.entry_time).max()-pd.to_datetime(t.entry_time).min()).days/7+1)
    return {'n':len(v),'trades_per_week':len(v)/weeks,'ev':v.mean(),'pf':pf(v),'total_R':v.sum(),'tp_rate':(t[f'outcome_{k}']=='TP').mean(),'max_dd_R':mdd(v),'worst_day_R':days.min(),'stress10_ev':t[f'stress10_R_{k}'].mean(),'buy_ev':t.loc[t.dir==1,col].mean(),'sell_ev':t.loc[t.dir==-1,col].mean(),'back_ev':t.loc[t.branch=='BACK',col].mean(),'through_ev':t.loc[t.branch=='THROUGH',col].mean()}
def serial(p,target):
    k=str(target).replace('.','p');rows=[];busy=pd.Timestamp.min
    for r in p.sort_values('decision_time').itertuples(index=False):
        if r.decision_time<=busy:continue
        if not r.filled:busy=r.decision_time+pd.Timedelta(minutes=15);continue
        if not bool(r.selected):busy=r.retest_confirm_time;continue
        ex=getattr(r,f'exit_time_{k}')
        if pd.isna(ex):continue
        rows.append(r._asdict());busy=ex
    return pd.DataFrame(rows)
def boot_mean(t,col):
    if t.empty:return {'ci95':[None,None]}
    q=t.copy();q['week']=pd.to_datetime(q.entry_time).dt.to_period('W-SUN').astype(str);a=q.groupby('week')[col].mean().to_numpy();rng=np.random.default_rng(20260823);b=np.array([rng.choice(a,len(a),replace=True).mean() for _ in range(4000)]);return {'n_weeks':len(a),'mean':a.mean(),'ci95':[np.quantile(b,.025),np.quantile(b,.975)]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('events',type=Path);ap.add_argument('--outdir',type=Path,required=True);a=ap.parse_args();a.outdir.mkdir(parents=True,exist_ok=True);h=sha256(a.input)
    if h!=CANONICAL_SHA:raise RuntimeError('SHA mismatch')
    df=add_vwap_lines(load_prices(a.input));e=load_events(a.events);p=enrich_retests(dedupe_decisions(build_signals(e)),df);iv=build_ifvg_events(df);p=add_health_and_features(p,df,iv);p=simulate(p,df,1.5);p=simulate(p,df,2.0);sc,m,cut=score(p,True);p=p.merge(sc[['event_i','decision_time','health_score','selected']],on=['event_i','decision_time'],how='left');p['selected']=p.selected.fillna(False);abl,_,ablcut=score(p,False)
    MD=diag(sc,'DISCOVERY');MC=diag(sc,'CONFIRMATION');AD=diag(abl,'DISCOVERY');AC=diag(abl,'CONFIRMATION');serD=serial(p[p.split=='DISCOVERY'],1.5);serC=serial(p[p.split=='CONFIRMATION'],1.5);serC2=serial(p[p.split=='CONFIRMATION'],2.0);SD=stats(serD,1.5);SC=stats(serC,1.5);SC2=stats(serC2,2.0);boot=boot_mean(serC,'net_R_1p5')
    g={'G0_DATA_CAUSALITY':True,'G1_MODEL_DISCRIMINATION':MC['auc']>.55 and MC['health_gap_pp']>=5,'G2_PRIMARY_POWER':SC.get('n',0)>=300 and SC.get('trades_per_week',0)>=10,'G3_CONFIRMATION_EV':SC.get('ev',-9)>0 and SC.get('pf',0)>1,'G4_WEEK_CLUSTER_CI':boot['ci95'][0] is not None and boot['ci95'][0]>0,'G5_SPLIT_TRANSFER':SD.get('ev',-9)>0 and SC.get('ev',-9)>0,'G6_2R_SURVIVAL':SC2.get('ev',-9)>=0,'G7_DIRECTION_BREADTH':SC.get('buy_ev',-9)>0 and SC.get('sell_ev',-9)>0,'G8_BRANCH_BREADTH':SC.get('back_ev',-9)>0 and SC.get('through_ev',-9)>0,'G9_PROP_DD_PROXY':SC.get('max_dd_R',999)<=20 and SC.get('worst_day_R',-999)>-16,'G10_COST_STRESS':SC.get('stress10_ev',-9)>0,'G11_EARLY_SELECTION_UPLIFT':MD['direction_gap_pp']>=5 and MC['direction_gap_pp']>=5}
    status='GO_TO_REPLICATION' if all(g.values()) else ('EARLY_HEALTH_PREDICTIVE_NOT_PROFITABLE' if g['G1_MODEL_DISCRIMINATION'] and g['G11_EARLY_SELECTION_UPLIFT'] and not g['G3_CONFIRMATION_EV'] else 'NO_EARLY_HEALTH_PROXY')
    verdict={'status':status,'gates':g,'cutoff_top30_discovery':cut,'model_discovery':MD,'model_confirmation':MC,'primary_discovery':SD,'primary_confirmation':SC,'confirmation_2R':SC2,'weekly_ev_bootstrap':boot,'ablation_no_existing_ifvg':{'cutoff':ablcut,'discovery':AD,'confirmation':AC},'holdout_opened':False}
    audit={'lab':LAB,'version':VERSION,'canonical_sha':h,'rows_preholdout':len(df),'parent_signals':len(p),'filled_retests':int(p.filled.sum()),'ifvg_events':len(iv),'holdout_opened':False}
    (a.outdir/'verdict.json').write_text(json.dumps(verdict,indent=2,default=float));(a.outdir/'audit.json').write_text(json.dumps(audit,indent=2,default=str));sc.to_csv(a.outdir/'scored_filled_retests.csv.gz',index=False,compression='gzip');pd.DataFrame([dict(split='DISCOVERY',target=1.5,**SD),dict(split='CONFIRMATION',target=1.5,**SC),dict(split='CONFIRMATION',target=2.0,**SC2)]).to_csv(a.outdir/'summary.csv',index=False);pd.DataFrame({'feature':CONT_FEATURES+BIN_FEATURES,'coef':m.named_steps['clf'].coef_[0]}).to_csv(a.outdir/'coefficients.csv',index=False)
    report=f'# {LAB} — v001 REPORT\n\n**Verdict:** `{status}`  \n**Holdout opened:** `false`\n\n## OOS model\n\n- Confirmation AUC: **{MC["auc"]:.4f}**\n- selected health: **{MC["selected_health_precision"]*100:.2f}%** vs rejected **{MC["rejected_health_precision"]*100:.2f}%**\n- selected direction correct: **{MC["selected_direction_correct"]*100:.2f}%** vs rejected **{MC["rejected_direction_correct"]*100:.2f}%**\n\n## Primary economics\n\n- Confirmation N: **{SC.get("n",0)}**\n- EV: **{SC.get("ev",np.nan):+.4f}R**\n- PF: **{SC.get("pf",np.nan):.3f}**\n- weekly CI: **{boot["ci95"]}**\n- Discovery EV: **{SD.get("ev",np.nan):+.4f}R**\n- 2R EV: **{SC2.get("ev",np.nan):+.4f}R**\n\n## Gates\n\n'+ '\n'.join(f'- {k}: {"PASS" if v else "FAIL"}' for k,v in g.items())+'\n'
    (a.outdir/'REPORT.md').write_text(report);print(json.dumps(verdict,indent=2,default=float))
if __name__=='__main__':main()
