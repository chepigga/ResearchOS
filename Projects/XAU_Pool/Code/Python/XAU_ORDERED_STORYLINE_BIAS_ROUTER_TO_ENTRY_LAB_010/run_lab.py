#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit

LAB='XAU_ORDERED_STORYLINE_BIAS_ROUTER_TO_ENTRY_LAB_010'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
HOLDOUT=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
ANCHOR_HOUR=1
BAND_K=1.618
MIN_CELL=50
P_GATE=0.75
P_LOW=0.25
RETEST_MIN=30
RETEST_ZONE_ATR=0.05
CONFIRM_CLOSE_ATR=0.03
RISK_ATR=0.50
HOLD_MIN=60
TARGETS=(1.5,2.0)
COMMISSION_PRICE=0.05
BOOT_N=4000
SEED=20260823
STATES=('RECLAIM','FAILED_RECOVERY','EXPAND','TEST','HOLD','CHOP')
LEVELS=('MID','HIGH','LOW')


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load_prices(path:Path)->pd.DataFrame:
    use=['time','open','high','low','close','ask_open','ask_high','ask_low','ask_close','tick_volume']
    x=pd.read_csv(path,sep=';',usecols=use)
    x['time']=pd.to_datetime(x.time,format='%Y.%m.%d %H:%M',errors='coerce')
    for c in use:
        if c!='time': x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x.dropna(subset=use).sort_values('time').drop_duplicates('time',keep='last')
    return x[x.time<HOLDOUT].reset_index(drop=True)

def wilder_atr(h,l,c,n=14):
    pc=c.shift(1); tr=pd.concat([(h-l),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def add_atr_vwap(df:pd.DataFrame)->pd.DataFrame:
    o=df.copy()
    m=o.set_index('time').resample('15min',label='left',closed='left').agg(high=('high','max'),low=('low','min'),close=('close','last')).dropna()
    m['atr']=wilder_atr(m.high,m.low,m.close)
    a=m[['atr']].reset_index(); a['avail']=a.time+pd.Timedelta(minutes=15); a=a[['avail','atr']].dropna().sort_values('avail')
    o=pd.merge_asof(o.sort_values('time'),a,left_on='time',right_on='avail',direction='backward').drop(columns='avail')
    o['session']=(o.time-pd.Timedelta(hours=ANCHOR_HOUR)).dt.floor('D')
    p=(o.high+o.low+o.close)/3.0; v=o.tick_volume.clip(lower=0).fillna(0)
    gv=v.groupby(o.session).cumsum(); gpv=(p*v).groupby(o.session).cumsum(); gp2=((p*p)*v).groupby(o.session).cumsum()
    mid=gpv/gv.replace(0,np.nan); var=(gp2/gv.replace(0,np.nan)-mid*mid).clip(lower=0); sd=np.sqrt(var)
    o['MID']=mid; o['HIGH']=mid+BAND_K*sd; o['LOW']=mid-BAND_K*sd
    return o.reset_index(drop=True)

def load_breaks(path:Path)->pd.DataFrame:
    e=pd.read_csv(path); e['break_time']=pd.to_datetime(e.break_time,errors='coerce')
    if 'model_event' in e.columns: e=e[e.model_event.astype(bool)]
    e=e[(e.family=='VWAP_VOLUME')&(e.break_time<HOLDOUT)].copy()
    req=['break_i','dir','level','break_time','split','year']; miss=[c for c in req if c not in e.columns]
    if miss: raise ValueError(miss)
    return e[req].drop_duplicates(['level','break_i','break_time','dir']).sort_values(['break_time','level','dir']).reset_index(drop=True)

def state_token(vals:np.ndarray)->str:
    start=float(vals[0]); end=float(vals[-1]); frac=float((vals>0).mean()); mn=float(vals.min()); mx=float(vals.max())
    if end<=-0.05 or frac<0.40:return 'RECLAIM'
    if mn<=-0.05 and end>=0.05 and frac>=0.60:return 'FAILED_RECOVERY'
    if frac>=0.80 and (end-start)>=0.10 and (mx-start)>=0.15:return 'EXPAND'
    if np.min(np.abs(vals))<=0.05 and end>0 and frac>=0.60:return 'TEST'
    if frac>=0.80 and mn>-0.05:return 'HOLD'
    return 'CHOP'

def fit_map(train:pd.DataFrame,key:str)->dict:
    g=train.groupby(key).acceptance_persists.agg(['sum','count'])
    return {str(k):(int(v['sum']),int(v['count'])) for k,v in g.iterrows()}
def smooth(sc): s,n=sc; return (s+1.0)/(n+2.0)

def build_bias_events(br:pd.DataFrame,df:pd.DataFrame)->pd.DataFrame:
    times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64); close=df.close.to_numpy(float); atr=df.atr.to_numpy(float)
    lines={lev:df[lev].to_numpy(float) for lev in LEVELS}; rows=[]
    for r in br.itertuples(index=False):
        bi=int(r.break_i)
        if bi<0 or bi>=len(df) or df.at[bi,'time']!=r.break_time: continue
        a=float(atr[bi]); line=lines[str(r.level)]
        if not np.isfinite(a) or a<=0: continue
        di=bi+15; fe=di+30
        if fe>=len(df) or times[fe]!=times[bi]+(fe-bi) or df.at[fe,'time']>=HOLDOUT: continue
        toks=[]; ok=True
        for b0 in (1,6,11):
            idx=np.arange(bi+b0,bi+b0+5); lv=line[idx]
            if not np.isfinite(lv).all(): ok=False; break
            vals=int(r.dir)*(close[idx]-lv)/a; toks.append(state_token(vals))
        if not ok: continue
        fidx=np.arange(di+1,fe+1); flv=line[fidx]
        if not np.isfinite(flv).all(): continue
        fdist=int(r.dir)*(close[fidx]-flv)/a
        rows.append({'break_i':bi,'break_time':r.break_time,'dir':int(r.dir),'level':r.level,'split':r.split,'year':int(r.year),'atr0':a,'decision_i':di,'decision_time':df.at[di,'time'],'snapshot':toks[-1],'last2':'>'.join(toks[-2:]),'ordered_path':'>'.join(toks),'acceptance_persists':int((fdist>0).sum()>=20)})
    return pd.DataFrame(rows)

def score_bias(ev:pd.DataFrame)->pd.DataFrame:
    tr=ev[ev.break_time<DISC_END].copy(); snap=fit_map(tr,'snapshot'); exact=fit_map(tr,'ordered_path'); last2=fit_map(tr,'last2'); base=(tr.acceptance_persists.sum()+1.0)/(len(tr)+2.0)
    rows=[]
    for r in ev.itertuples(index=False):
        ss=snap.get(str(r.snapshot)); ps=smooth(ss) if ss else base; ee=exact.get(str(r.ordered_path)); ll=last2.get(str(r.last2))
        if ee and ee[1]>=MIN_CELL: p=smooth(ee); src='EXACT_3'
        elif ll and ll[1]>=MIN_CELL: p=smooth(ll); src='LAST_2'
        else: p=ps; src='SNAPSHOT'
        d=r._asdict(); d.update(p_accept=float(p),backoff_source=src,strong_accept=bool(p>=P_GATE),strong_reject=bool(p<P_LOW)); rows.append(d)
    return pd.DataFrame(rows)

@njit
def find_retest(dec_i,d,atr0,level_code,times_m,high,low,close,mid,hi,lo):
    line=mid if level_code==0 else (hi if level_code==1 else lo)
    end_time=times_m[dec_i]+RETEST_MIN
    for j in range(dec_i+1,len(close)):
        if times_m[j]>end_time: break
        lev=line[j]
        if not np.isfinite(lev): continue
        touch=(low[j]<=lev+RETEST_ZONE_ATR*atr0) and (high[j]>=lev-RETEST_ZONE_ATR*atr0)
        if not touch: continue
        if d*(close[j]-lev)/atr0 < CONFIRM_CLOSE_ATR: continue
        k=j+1
        if k<len(close) and times_m[k]==times_m[j]+1: return j,k
    return -1,-1

@njit
def sim_trade(entry_i,d,entry,risk,target,times_m,bh,bl,bc,ah,al,ac):
    end_time=times_m[entry_i]+HOLD_MIN; tp=entry+d*target*risk; sl=entry-d*risk; last=entry_i
    for j in range(entry_i,len(bc)):
        if times_m[j]>end_time: break
        last=j
        if d>0: ht=bh[j]>=tp; hs=bl[j]<=sl
        else: ht=al[j]<=tp; hs=ah[j]>=sl
        if ht and hs:return -1.0,j,2
        if hs:return -1.0,j,0
        if ht:return target,j,1
    exitp=bc[last] if d>0 else ac[last]; rr=d*(exitp-entry)/risk
    if rr<-1:rr=-1.0
    if rr>target:rr=target
    return rr,last,3

def build_candidates(ev:pd.DataFrame,df:pd.DataFrame)->pd.DataFrame:
    times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    high=df.high.to_numpy(float); low=df.low.to_numpy(float); close=df.close.to_numpy(float); ao=df.ask_open.to_numpy(float); bo=df.open.to_numpy(float)
    mid=df.MID.to_numpy(float); hi=df.HIGH.to_numpy(float); lo=df.LOW.to_numpy(float); rows=[]; lmap={'MID':0,'HIGH':1,'LOW':2}
    for r in ev.itertuples(index=False):
        di=int(r.decision_i)
        if di>=len(df) or df.at[di,'time']!=r.decision_time: continue
        ci,ei=find_retest(di,int(r.dir),float(r.atr0),lmap[str(r.level)],times,high,low,close,mid,hi,lo)
        if ei<0: continue
        entry=ao[ei] if int(r.dir)>0 else bo[ei]
        d=r._asdict(); d.update(retest_confirm_i=int(ci),retest_confirm_time=df.at[ci,'time'],entry_i=int(ei),entry_time=df.at[ei,'time'],entry=float(entry),wait_entry_min=(df.at[ei,'time']-r.decision_time).total_seconds()/60)
        rows.append(d)
    return pd.DataFrame(rows)

def tkey(x):return str(x).replace('.','p')
def simulate(cand:pd.DataFrame,df:pd.DataFrame,target:float)->pd.DataFrame:
    y=cand.copy(); key=tkey(target); times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64)
    bh=df.high.to_numpy(float); bl=df.low.to_numpy(float); bc=df.close.to_numpy(float); ah=df.ask_high.to_numpy(float); al=df.ask_low.to_numpy(float); ac=df.ask_close.to_numpy(float)
    gross=[]; net=[]; stress=[]; out=[]; ext=[]
    for r in y.itertuples(index=False):
        risk=RISK_ATR*float(r.atr0); gr,xi,oc=sim_trade(int(r.entry_i),int(r.dir),float(r.entry),risk,target,times,bh,bl,bc,ah,al,ac); comm=COMMISSION_PRICE/risk; nr=gr-comm
        gross.append(float(gr)); net.append(float(nr)); stress.append(float(nr-0.10/risk)); out.append(['SL','TP','SAME_BAR_LOSS','TIME'][oc]); ext.append(df.at[xi,'time'])
    y[f'gross_R_{key}']=gross; y[f'net_R_{key}']=net; y[f'stress10_R_{key}']=stress; y[f'outcome_{key}']=out; y[f'exit_time_{key}']=ext
    return y

def pf(v):
    s=pd.Series(v).dropna(); pos=s[s>0].sum(); neg=-s[s<0].sum(); return float(pos/neg) if neg>0 else (float('inf') if pos>0 else np.nan)
def maxdd(v):
    a=np.asarray(pd.Series(v).dropna(),float)
    if not len(a):return np.nan
    c=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0,c]); return float((peak[1:]-c).max())
def max_consec(v):
    m=c=0
    for z in pd.Series(v).dropna():
        if z<0:c+=1;m=max(m,c)
        else:c=0
    return int(m)
def weeks_span(t):
    x=pd.to_datetime(pd.Series(t).dropna())
    if len(x)<2:return np.nan
    return max(1.0,(x.max()-x.min()).days/7.0)
def stats(x:pd.DataFrame,target=1.5)->dict:
    if x.empty:return {'n':0}
    k=tkey(target); v=x[f'net_R_{k}'].dropna(); daily=x.assign(day=pd.to_datetime(x.entry_time).dt.date).groupby('day')[f'net_R_{k}'].sum()
    return {'n':int(len(v)),'trades_per_week':float(len(v)/weeks_span(x.entry_time)),'ev':float(v.mean()),'pf':pf(v),'tp_rate':float((x[f'outcome_{k}']=='TP').mean()),'total_R':float(v.sum()),'gross_ev':float(x[f'gross_R_{k}'].mean()),'stress10_ev':float(x[f'stress10_R_{k}'].mean()),'max_dd_R':maxdd(v),'worst_day_R':float(daily.min()) if len(daily) else np.nan,'max_consec_losses':max_consec(v),'buy_ev':float(x.loc[x.dir==1,f'net_R_{k}'].mean()),'sell_ev':float(x.loc[x.dir==-1,f'net_R_{k}'].mean())}
def serial(x:pd.DataFrame,target=1.5)->pd.DataFrame:
    if x.empty:return x.copy()
    k=tkey(target); z=x.sort_values(['entry_time','break_time','level']).copy(); conflict=z.groupby('entry_time').dir.nunique(); bad=set(conflict[conflict>1].index)
    z=z[~z.entry_time.isin(bad)].copy(); rows=[]; busy=pd.Timestamp.min
    for r in z.itertuples(index=False):
        if r.entry_time<=busy: continue
        rows.append(r._asdict()); busy=getattr(r,f'exit_time_{k}')
    return pd.DataFrame(rows)
def boot_week_mean(x:pd.DataFrame,col:str,seed=SEED):
    z=x.copy(); z['week']=pd.to_datetime(z.entry_time).dt.to_period('W-MON').astype(str); w=z.groupby('week')[col].mean().dropna().to_numpy(float)
    if len(w)<8:return {'n_weeks':int(len(w)),'mean':float(w.mean()) if len(w) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(w,size=len(w),replace=True).mean() for _ in range(BOOT_N)])
    return {'n_weeks':int(len(w)),'mean':float(w.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}
def boot_incremental(allc:pd.DataFrame,routed:pd.DataFrame,col='net_R_1p5'):
    a=allc.copy(); r=routed.copy(); a['week']=pd.to_datetime(a.entry_time).dt.to_period('W-MON').astype(str); r['week']=pd.to_datetime(r.entry_time).dt.to_period('W-MON').astype(str)
    aw=a.groupby('week')[col].mean(); rw=r.groupby('week')[col].mean(); d=(rw-aw).dropna().to_numpy(float)
    if len(d)<8:return {'n_weeks':int(len(d)),'mean':float(d.mean()) if len(d) else None,'ci95':[None,None]}
    rng=np.random.default_rng(SEED+1); b=np.array([rng.choice(d,size=len(d),replace=True).mean() for _ in range(BOOT_N)])
    return {'n_weeks':int(len(d)),'mean':float(d.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input',type=Path); ap.add_argument('--break-census',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    h=sha256(a.input)
    if h!=CANONICAL_SHA: raise RuntimeError(f'SHA mismatch {h}')
    df=add_atr_vwap(load_prices(a.input)); br=load_breaks(a.break_census); bev=score_bias(build_bias_events(br,df)); cand=build_candidates(bev,df)
    for t in TARGETS: cand=simulate(cand,df,t)
    cand.to_csv(out/'candidates.csv.gz',index=False,compression='gzip')
    rows=[]; details={}
    for split in ['DISCOVERY','CONFIRMATION']:
        z=cand[cand.split==split].copy(); routed=z[z.strong_accept].copy(); low=z[z.strong_reject].copy()
        for t in TARGETS:
            for name,sub in [('BASELINE_INDEPENDENT',z),('ROUTED_INDEPENDENT',routed),('LOWP_INDEPENDENT',low),('BASELINE_SERIAL',serial(z,t)),('ROUTED_SERIAL',serial(routed,t))]:
                st=stats(sub,t); rows.append({'split':split,'target':t,'system':name,**st})
        if split=='CONFIRMATION':
            sbase=serial(z,1.5); sr=serial(routed,1.5); details['conf_baseline_serial']=stats(sbase,1.5); details['conf_routed_serial']=stats(sr,1.5); details['conf_routed_2R']=stats(serial(routed,2.0),2.0)
            details['weekly_routed']=boot_week_mean(sr,'net_R_1p5'); details['weekly_incremental']=boot_incremental(z,routed)
            details['conf_candidates']=int(len(z)); details['conf_routed_candidates']=int(len(routed)); details['conf_route_rate']=float(len(routed)/len(z)) if len(z) else np.nan
            details['level_ev']={lev:float(routed.loc[routed.level==lev,'net_R_1p5'].mean()) for lev in LEVELS}
            q=z.copy(); q['p_quartile']=pd.qcut(q.p_accept.rank(method='first'),4,labels=['Q1','Q2','Q3','Q4']); qtab=q.groupby('p_quartile',observed=True).agg(n=('net_R_1p5','size'),mean_p=('p_accept','mean'),ev=('net_R_1p5','mean'),tp=('outcome_1p5',lambda s:(s=='TP').mean())).reset_index(); qtab.to_csv(out/'probability_quartiles.csv',index=False); details['quartiles']=qtab.to_dict(orient='records')
            btab=routed.groupby('backoff_source').agg(n=('net_R_1p5','size'),ev=('net_R_1p5','mean'),mean_p=('p_accept','mean')).reset_index(); btab.to_csv(out/'backoff_diagnostics.csv',index=False)
    sm=pd.DataFrame(rows); sm.to_csv(out/'summary.csv',index=False)
    disc_r=stats(serial(cand[(cand.split=='DISCOVERY')&cand.strong_accept],1.5),1.5); conf=details['conf_routed_serial']; c2=details['conf_routed_2R']; wi=details['weekly_incremental']; wr=details['weekly_routed']
    level_ev=details['level_ev']; q=details['quartiles']
    gates={
      'G0_DATA_CAUSALITY':bool(h==CANONICAL_SHA and (cand.entry_time>=cand.decision_time+pd.Timedelta(minutes=2)).all() and (cand.entry_time<HOLDOUT).all()),
      'G1_POWER':bool(conf.get('n',0)>=300 and conf.get('trades_per_week',0)>=5),
      'G2_ROUTED_EV':bool(conf.get('ev',-9)>0 and conf.get('pf',0)>1),
      'G3_WEEK_CI':bool(wr['ci95'][0] is not None and wr['ci95'][0]>0),
      'G4_INCREMENTAL_LIFT':bool(details['conf_routed_serial'].get('n',0)>0 and float(cand[(cand.split=='CONFIRMATION')&cand.strong_accept].net_R_1p5.mean())>float(cand[cand.split=='CONFIRMATION'].net_R_1p5.mean()) and wi['ci95'][0] is not None and wi['ci95'][0]>0),
      'G5_SPLIT_TRANSFER':bool(disc_r.get('ev',-9)>0 and conf.get('ev',-9)>0),
      'G6_2R_SURVIVAL':bool(c2.get('ev',-9)>=0),
      'G7_DIRECTION_BREADTH':bool(conf.get('buy_ev',-9)>0 and conf.get('sell_ev',-9)>0),
      'G8_LEVEL_BREADTH':bool(all(np.isfinite(level_ev[k]) and level_ev[k]>=0 for k in LEVELS)),
      'G9_PROP_DD_PROXY':bool(conf.get('max_dd_R',999)<=20 and conf.get('worst_day_R',-999)>-16),
      'G10_COST_STRESS':bool(conf.get('stress10_ev',-9)>0),
      'G11_ROUTER_MONOTONICITY':bool(len(q)>=4 and float(q[-1]['ev'])>float(q[0]['ev']))
    }
    if all(gates.values()):status='BIAS_ROUTER_EXECUTABLE_EDGE'
    elif all(gates[k] for k in ['G2_ROUTED_EV','G3_WEEK_CI','G4_INCREMENTAL_LIFT','G5_SPLIT_TRANSFER']):status='BIAS_ROUTER_POSITIVE_BUT_NARROW'
    elif gates['G4_INCREMENTAL_LIFT'] and not gates['G2_ROUTED_EV']:status='BIAS_IMPROVES_BUT_NOT_PROFITABLE'
    elif not gates['G0_DATA_CAUSALITY']:status='INVALID_DATA_CAUSALITY'
    else:status='NO_BIAS_ROUTER_ENTRY_LIFT'
    verdict={'status':status,'gates':gates,'confirmation_baseline_serial':details['conf_baseline_serial'],'confirmation_routed_serial':conf,'confirmation_routed_2R':c2,'discovery_routed_serial':disc_r,'weekly_routed':wr,'weekly_incremental':wi,'candidate_counts':{'confirmation_all':details['conf_candidates'],'confirmation_routed':details['conf_routed_candidates'],'route_rate':details['conf_route_rate']},'level_ev':level_ev,'holdout_opened':False}
    (out/'verdict.json').write_text(json.dumps(verdict,indent=2),encoding='utf-8')
    audit={'lab':LAB,'version':VERSION,'canonical_sha':h,'raw_rows_pre_holdout':len(df),'breaks':len(br),'bias_events':len(bev),'entry_candidates':len(cand),'holdout_opened':False,'p_gate':P_GATE}
    (out/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    rep=f"""# {LAB} — {VERSION} REPORT\n\n**Verdict:** `{status}`  \n**Holdout opened:** `false`\n\n## Primary Confirmation — routed serial / 1.5R\n\n- N: **{conf.get('n',0):,}**\n- trades/week: **{conf.get('trades_per_week',np.nan):.2f}**\n- EV: **{conf.get('ev',np.nan):+.4f}R**\n- PF: **{conf.get('pf',np.nan):.3f}**\n- TP rate: **{conf.get('tp_rate',np.nan)*100:.2f}%**\n- gross EV: **{conf.get('gross_ev',np.nan):+.4f}R**\n- stress +$0.10 EV: **{conf.get('stress10_ev',np.nan):+.4f}R**\n- max DD: **{conf.get('max_dd_R',np.nan):.2f}R**\n- worst day: **{conf.get('worst_day_R',np.nan):+.2f}R**\n- BUY EV: **{conf.get('buy_ev',np.nan):+.4f}R**\n- SELL EV: **{conf.get('sell_ev',np.nan):+.4f}R**\n\n## Baseline versus Bias Router\n\nBaseline serial EV: **{details['conf_baseline_serial'].get('ev',np.nan):+.4f}R**, PF **{details['conf_baseline_serial'].get('pf',np.nan):.3f}**.  \nRouted serial EV: **{conf.get('ev',np.nan):+.4f}R**, PF **{conf.get('pf',np.nan):.3f}**.\n\nIndependent candidate route rate: **{details['conf_route_rate']*100:.2f}%** ({details['conf_routed_candidates']:,}/{details['conf_candidates']:,}).\n\nWeekly routed CI: **{wr['ci95']}**.  \nWeekly routed-minus-baseline independent EV CI: **{wi['ci95']}**.\n\n## 2R\n\nRouted serial EV: **{c2.get('ev',np.nan):+.4f}R**, PF **{c2.get('pf',np.nan):.3f}**.\n\n## Discovery transfer\n\nRouted serial EV: **{disc_r.get('ev',np.nan):+.4f}R**, PF **{disc_r.get('pf',np.nan):.3f}**.\n\n## Level breadth\n\n- MID: **{level_ev['MID']:+.4f}R**\n- HIGH: **{level_ev['HIGH']:+.4f}R**\n- LOW: **{level_ev['LOW']:+.4f}R**\n\n## Gates\n\n""" + '\n'.join([f"- {k}: {'PASS' if v else 'FAIL'}" for k,v in gates.items()]) + "\n\nNo holdout opening or live allocation is authorized.\n"
    (out/'REPORT.md').write_text(rep,encoding='utf-8')
    print(json.dumps(verdict,indent=2))

if __name__=='__main__':main()
