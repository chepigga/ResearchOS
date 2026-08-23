#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss

LAB='XAU_STRONG_BIAS_ACCEPTED_SIDE_INTERNAL_STRUCTURE_MAP_LAB_011'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
HOLDOUT=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
ANCHOR_HOUR=1
BAND_K=1.618
MIN_CELL=50
P_GATE=0.75
BOOT_N=4000
SEED=20260823
LEVELS=('MID','HIGH','LOW')
BIAS_STATES=('RECLAIM','FAILED_RECOVERY','EXPAND','TEST','HOLD','CHOP')
INTERNAL_STATES=('LEVEL_RETEST','EXPAND','SHALLOW_PULLBACK','DEEP_PULLBACK','BASE','HOLD')

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def load_prices(path:Path)->pd.DataFrame:
    use=['time','open','high','low','close','tick_volume']
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
    if 'model_event' in e: e=e[e.model_event.astype(bool)]
    e=e[(e.family=='VWAP_VOLUME')&(e.break_time<HOLDOUT)].copy()
    req=['break_i','dir','level','break_time','split','year']; miss=[c for c in req if c not in e]
    if miss: raise ValueError(miss)
    return e[req].drop_duplicates(['level','break_i','break_time','dir']).sort_values(['break_time','level','dir']).reset_index(drop=True)
def bias_state(vals:np.ndarray)->str:
    start=float(vals[0]); end=float(vals[-1]); frac=float((vals>0).mean()); mn=float(vals.min()); mx=float(vals.max())
    if end<=-0.05 or frac<0.40:return 'RECLAIM'
    if mn<=-0.05 and end>=0.05 and frac>=0.60:return 'FAILED_RECOVERY'
    if frac>=0.80 and (end-start)>=0.10 and (mx-start)>=0.15:return 'EXPAND'
    if np.min(np.abs(vals))<=0.05 and end>0 and frac>=0.60:return 'TEST'
    if frac>=0.80 and mn>-0.05:return 'HOLD'
    return 'CHOP'
def fit_map(train,key,target):
    g=train.groupby(key)[target].agg(['sum','count']); return {str(k):(int(v['sum']),int(v['count'])) for k,v in g.iterrows()}
def smooth(sc): s,n=sc; return (s+1.0)/(n+2.0)
def build_bias_events(br,df):
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
            vals=int(r.dir)*(close[idx]-lv)/a; toks.append(bias_state(vals))
        if not ok: continue
        fidx=np.arange(di+1,fe+1); flv=line[fidx]
        if not np.isfinite(flv).all(): continue
        fdist=int(r.dir)*(close[fidx]-flv)/a
        rows.append({'break_i':bi,'break_time':r.break_time,'dir':int(r.dir),'level':r.level,'split':r.split,'year':int(r.year),'atr0':a,'decision_i':di,'decision_time':df.at[di,'time'],'snapshot':toks[-1],'last2':'>'.join(toks[-2:]),'ordered_path':'>'.join(toks),'acceptance_persists':int((fdist>0).sum()>=20)})
    return pd.DataFrame(rows)
def score_bias(ev):
    tr=ev[ev.break_time<DISC_END].copy(); snap=fit_map(tr,'snapshot','acceptance_persists'); exact=fit_map(tr,'ordered_path','acceptance_persists'); last2=fit_map(tr,'last2','acceptance_persists'); base=(tr.acceptance_persists.sum()+1.0)/(len(tr)+2.0)
    out=[]
    for r in ev.itertuples(index=False):
        ss=snap.get(str(r.snapshot)); ps=smooth(ss) if ss else base; ee=exact.get(str(r.ordered_path)); ll=last2.get(str(r.last2))
        if ee and ee[1]>=MIN_CELL: p=smooth(ee); src='EXACT_3'
        elif ll and ll[1]>=MIN_CELL: p=smooth(ll); src='LAST_2'
        else: p=ps; src='SNAPSHOT'
        d=r._asdict(); d.update(p_accept=float(p),bias_source=src,strong_accept=bool(p>=P_GATE)); out.append(d)
    return pd.DataFrame(out)
def internal_state(block:np.ndarray,prior_peak:float)->str:
    mn=float(block.min()); mx=float(block.max()); end=float(block[-1]); dd=prior_peak-mn; rec=end-mn
    if mn<=0.05: return 'LEVEL_RETEST'
    if (mx-prior_peak)>=0.15 and (end-prior_peak)>=0.05: return 'EXPAND'
    if dd>=0.10 and dd<0.25 and mn>0.10 and rec>=0.05 and end>=prior_peak-0.10: return 'SHALLOW_PULLBACK'
    if dd>=0.25 and mn>0.05: return 'DEEP_PULLBACK'
    if (mx-mn)<=0.20 and mn>0.10: return 'BASE'
    return 'HOLD'
def bag_key(tokens):
    c=Counter(tokens); return '|'.join(f'{s}:{c.get(s,0)}' for s in INTERNAL_STATES)
def build_internal(strong,df):
    times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64); close=df.close.to_numpy(float); lines={lev:df[lev].to_numpy(float) for lev in LEVELS}; rows=[]
    for r in strong.itertuples(index=False):
        bi=int(r.break_i); end=bi+60
        if end>=len(df) or times[end]!=times[bi]+60 or df.at[end,'time']>=HOLDOUT: continue
        line=lines[str(r.level)]; idx=np.arange(bi+1,end+1); lv=line[idx]
        if not np.isfinite(lv).all(): continue
        vals=int(r.dir)*(close[idx]-lv)/float(r.atr0)
        toks=[]
        for start_off in (16,21,26):
            block=vals[start_off-1:start_off+4]; prior=vals[:start_off-1]
            if len(block)!=5 or len(prior)==0: toks=[]; break
            toks.append(internal_state(block,float(prior.max())))
        if len(toks)!=3: continue
        peak30=float(vals[:30].max()); fut=vals[30:60]; new_thr=peak30+0.30
        ni=np.flatnonzero(fut>=new_thr); fi=np.flatnonzero(fut<=0.05); nidx=int(ni[0]) if len(ni) else 999; fidx=int(fi[0]) if len(fi) else 999
        if nidx<fidx: outcome='NEW_LEG'; target=1
        elif fidx<nidx: outcome='LEVEL_FAILURE'; target=0
        else: outcome='UNRESOLVED'; target=np.nan
        d=r._asdict(); d.update(internal_path='>'.join(toks),internal_last2='>'.join(toks[-2:]),internal_snapshot=toks[-1],internal_bag=bag_key(toks),any_level_retest=('LEVEL_RETEST' in toks),n_expand=toks.count('EXPAND'),n_shallow=toks.count('SHALLOW_PULLBACK'),n_deep=toks.count('DEEP_PULLBACK'),peak_T30=peak30,outcome=outcome,new_leg_target=target,future_acceptance=int((fut>0).sum()>=20),terminal_side=int(fut[-1]>0),future_extension=float(fut.max()-peak30)); rows.append(d)
    return pd.DataFrame(rows)
def add_internal_probs(train,test):
    tr=train[train.new_leg_target.notna()].copy(); te=test[test.new_leg_target.notna()].copy(); snap=fit_map(tr,'internal_snapshot','new_leg_target'); bag=fit_map(tr,'internal_bag','new_leg_target'); exact=fit_map(tr,'internal_path','new_leg_target'); last2=fit_map(tr,'internal_last2','new_leg_target'); base=(tr.new_leg_target.sum()+1)/(len(tr)+2)
    ps=[]; pb=[]; po=[]; src=[]
    for r in te.itertuples(index=False):
        ss=snap.get(str(r.internal_snapshot)); p0=smooth(ss) if ss else base; bb=bag.get(str(r.internal_bag)); p1=smooth(bb) if bb and bb[1]>=MIN_CELL else p0; ee=exact.get(str(r.internal_path)); ll=last2.get(str(r.internal_last2))
        if ee and ee[1]>=MIN_CELL: p2=smooth(ee); so='EXACT_3'
        elif ll and ll[1]>=MIN_CELL: p2=smooth(ll); so='LAST_2'
        else: p2=p0; so='SNAPSHOT'
        ps.append(p0); pb.append(p1); po.append(p2); src.append(so)
    te['p_snapshot']=ps; te['p_bag']=pb; te['p_ordered']=po; te['prob_source']=src; return te
def auc(y,p):
    y=np.asarray(y,int); p=np.asarray(p,float); return float(roc_auc_score(y,p)) if len(np.unique(y))>1 else np.nan
def metrics(sc):
    y=sc.new_leg_target.astype(int); out={'n':int(len(sc)),'base_rate':float(y.mean())}
    for n in ('snapshot','bag','ordered'):
        p=sc[f'p_{n}']; out[f'{n}_auc']=auc(y,p); out[f'{n}_brier']=float(brier_score_loss(y,p))
    out['ordered_minus_snapshot']=out['ordered_auc']-out['snapshot_auc']; out['ordered_minus_bag']=out['ordered_auc']-out['bag_auc']; return out
def weekly_diffs(sc):
    z=sc.copy(); z['week']=pd.to_datetime(z.break_time).dt.to_period('W-MON').astype(str); rows=[]
    for w,g in z.groupby('week'):
        if len(g)<20 or g.new_leg_target.nunique()<2: continue
        ao=auc(g.new_leg_target,g.p_ordered); rows.append({'week':w,'ord_snap':ao-auc(g.new_leg_target,g.p_snapshot),'ord_bag':ao-auc(g.new_leg_target,g.p_bag)})
    return pd.DataFrame(rows)
def boot(v,seed):
    a=np.asarray(pd.Series(v).dropna(),float)
    if len(a)<8:return {'n':int(len(a)),'mean':float(a.mean()) if len(a) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.array([rng.choice(a,size=len(a),replace=True).mean() for _ in range(BOOT_N)]); return {'n':int(len(a)),'mean':float(a.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}
def calibration(sc):
    z=sc.copy(); z['rank']=z.p_ordered.rank(method='first',pct=True); z['quintile']=pd.cut(z['rank'],[0,.2,.4,.6,.8,1],labels=['Q1','Q2','Q3','Q4','Q5'],include_lowest=True); return z.groupby('quintile',observed=True).agg(n=('new_leg_target','size'),mean_p=('p_ordered','mean'),actual=('new_leg_target','mean')).reset_index()
def subgroup_auc(sc,col):
    return pd.DataFrame([{col:k,'n':len(g),'auc':auc(g.new_leg_target,g.p_ordered),'base_rate':g.new_leg_target.mean()} for k,g in sc.groupby(col)])
def path_table(disc,conf):
    def agg(x,prefix):
        g=x.groupby('internal_path').agg(total=('outcome','size'),resolved=('new_leg_target',lambda s:s.notna().sum()),new_leg=('outcome',lambda s:(s=='NEW_LEG').sum()),level_failure=('outcome',lambda s:(s=='LEVEL_FAILURE').sum()),unresolved=('outcome',lambda s:(s=='UNRESOLVED').sum()),acceptance=('future_acceptance','mean')); g[f'{prefix}_new_leg_rate_all']=g.new_leg/g.total; g[f'{prefix}_new_leg_rate_resolved']=g.new_leg/g.resolved.replace(0,np.nan); return g[["total","resolved","new_leg","level_failure","unresolved","acceptance",f'{prefix}_new_leg_rate_all',f'{prefix}_new_leg_rate_resolved']].add_prefix(prefix+'_')
    return agg(disc,'disc').join(agg(conf,'conf'),how='outer').reset_index().sort_values('conf_total',ascending=False)
def matched_orders(pt):
    if pt.empty:return pd.DataFrame()
    z=pt.copy(); z['bag']=z.internal_path.map(lambda p:bag_key(str(p).split('>'))); rows=[]
    for b,g in z.groupby('bag'):
        g=g[(g.disc_total>=50)&(g.conf_total>=50)&g.conf_new_leg_rate_all.notna()]
        if len(g)<2: continue
        lo=g.sort_values('conf_new_leg_rate_all').iloc[0]; hi=g.sort_values('conf_new_leg_rate_all').iloc[-1]; rows.append({'bag':b,'low_path':lo.internal_path,'low_disc_rate':lo.disc_new_leg_rate_all,'low_conf_rate':lo.conf_new_leg_rate_all,'high_path':hi.internal_path,'high_disc_rate':hi.disc_new_leg_rate_all,'high_conf_rate':hi.conf_new_leg_rate_all,'conf_gap':hi.conf_new_leg_rate_all-lo.conf_new_leg_rate_all})
    return pd.DataFrame(rows).sort_values('conf_gap',ascending=False) if rows else pd.DataFrame()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input',type=Path); ap.add_argument('--break-census',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    h=sha256(a.input)
    if h!=CANONICAL_SHA: raise RuntimeError(f'SHA mismatch {h}')
    df=add_atr_vwap(load_prices(a.input)); br=load_breaks(a.break_census); bev=score_bias(build_bias_events(br,df)); strong=bev[bev.strong_accept].copy(); internal=build_internal(strong,df); internal.to_csv(out/'events.csv.gz',index=False,compression='gzip')
    disc=internal[internal.break_time<DISC_END].copy(); conf=internal[(internal.break_time>=DISC_END)&(internal.break_time<HOLDOUT)].copy(); sc=add_internal_probs(disc,conf); sc.to_csv(out/'confirmation_scored.csv.gz',index=False,compression='gzip')
    m=metrics(sc); wk=weekly_diffs(sc); wk.to_csv(out/'weekly_auc_diffs.csv',index=False); bs=boot(wk.ord_snap,SEED); bb=boot(wk.ord_bag,SEED+1); cal=calibration(sc); cal.to_csv(out/'calibration.csv',index=False); pt=path_table(disc,conf); pt.to_csv(out/'path_table.csv',index=False); mo=matched_orders(pt); mo.to_csv(out/'matched_order_examples.csv',index=False)
    da=subgroup_auc(sc.assign(direction=np.where(sc.dir>0,'BUY','SELL')),'direction'); da.to_csv(out/'direction_auc.csv',index=False); la=subgroup_auc(sc,'level'); la.to_csv(out/'level_auc.csv',index=False); ya=subgroup_auc(sc.assign(eval_year=pd.to_datetime(sc.break_time).dt.year),'eval_year'); ya.to_csv(out/'yearly_auc.csv',index=False)
    def cohort(x): return {'n':int(len(x)),'new_leg_rate_all':float((x.outcome=='NEW_LEG').mean()) if len(x) else np.nan,'resolved_rate':float(x.new_leg_target.notna().mean()) if len(x) else np.nan,'new_leg_rate_resolved':float(x.new_leg_target.dropna().mean()) if x.new_leg_target.notna().any() else np.nan,'future_acceptance':float(x.future_acceptance.mean()) if len(x) else np.nan}
    adv={'DISCOVERY':{'NO_LEVEL_RETEST':cohort(disc[~disc.any_level_retest]),'ANY_LEVEL_RETEST':cohort(disc[disc.any_level_retest])},'CONFIRMATION':{'NO_LEVEL_RETEST':cohort(conf[~conf.any_level_retest]),'ANY_LEVEL_RETEST':cohort(conf[conf.any_level_retest])}}; pd.DataFrame([{'split':sp,'cohort':co,**vals} for sp,d in adv.items() for co,vals in d.items()]).to_csv(out/'level_retest_adverse.csv',index=False)
    constructive=[]
    for _,r in pt.iterrows():
        if 'LEVEL_RETEST' in str(r.internal_path): continue
        if r.get('disc_total',0)>=100 and r.get('conf_total',0)>=100 and r.get('disc_new_leg_rate_all',0)>=0.70 and r.get('conf_new_leg_rate_all',0)>=0.70: constructive.append(str(r.internal_path))
    calgap=float(cal.iloc[-1].actual-cal.iloc[0].actual) if len(cal)>=2 else np.nan; dau={str(r.direction):float(r.auc) for r in da.itertuples(index=False)}; lau={str(r.level):float(r.auc) for r in la.itertuples(index=False)}; yau={int(r.eval_year):float(r.auc) for r in ya.itertuples(index=False)}
    dg=adv['DISCOVERY']['NO_LEVEL_RETEST']['new_leg_rate_all']-adv['DISCOVERY']['ANY_LEVEL_RETEST']['new_leg_rate_all']; cg=adv['CONFIRMATION']['NO_LEVEL_RETEST']['new_leg_rate_all']-adv['CONFIRMATION']['ANY_LEVEL_RETEST']['new_leg_rate_all']
    gates={'G0_DATA_CAUSALITY':bool(h==CANONICAL_SHA and (internal.break_time<HOLDOUT).all()),'G1_POWER':bool(len(conf)>=2000 and sc.shape[0]>=1200),'G2_LEVEL_RETEST_ADVERSE':bool(dg>=0.15 and cg>=0.15),'G3_INTERNAL_PATH_PREDICTIVE':bool(m['ordered_auc']>=0.65),'G4_ORDER_INCREMENTAL':bool(m['ordered_minus_snapshot']>=0.01 and bs['ci95'][0] is not None and bs['ci95'][0]>0),'G5_ORDER_BEATS_BAG':bool(m['ordered_minus_bag']>=0.01 and bb['ci95'][0] is not None and bb['ci95'][0]>0),'G6_CONSTRUCTIVE_PATH_EXISTS':bool(len(constructive)>0),'G7_DIRECTION_MIRROR':bool(dau.get('BUY',0)>=0.60 and dau.get('SELL',0)>=0.60),'G8_LEVEL_BREADTH':bool(all(lau.get(k,0)>=0.60 for k in LEVELS)),'G9_YEAR_TRANSFER':bool(yau.get(2024,0)>=0.60 and yau.get(2025,0)>=0.60),'G10_CALIBRATION':bool(calgap>=0.25)}
    if all(gates.values()): status='INTERNAL_STRUCTURE_MAP_CONFIRMED'
    elif all(gates[k] for k in ['G0_DATA_CAUSALITY','G1_POWER','G2_LEVEL_RETEST_ADVERSE','G3_INTERNAL_PATH_PREDICTIVE','G6_CONSTRUCTIVE_PATH_EXISTS','G7_DIRECTION_MIRROR','G8_LEVEL_BREADTH','G9_YEAR_TRANSFER','G10_CALIBRATION']): status='INTERNAL_STRUCTURE_USEFUL_ORDER_NOT_INCREMENTAL'
    elif gates['G2_LEVEL_RETEST_ADVERSE'] and (not gates['G3_INTERNAL_PATH_PREDICTIVE'] or not gates['G6_CONSTRUCTIVE_PATH_EXISTS']): status='DEEP_RETEST_ADVERSE_BUT_NO_INTERNAL_EDGE'
    elif not gates['G0_DATA_CAUSALITY']: status='INVALID_DATA_CAUSALITY'
    else: status='NO_ACCEPTED_SIDE_INTERNAL_STRUCTURE_EDGE'
    verdict={'status':status,'gates':gates,'census':{'strong_bias_discovery':int(len(disc)),'strong_bias_confirmation':int(len(conf)),'resolved_confirmation':int(len(sc)),'confirmation_unresolved_rate':float((conf.outcome=='UNRESOLVED').mean())},'primary_confirmation':m,'weekly_order_minus_snapshot':bs,'weekly_order_minus_bag':bb,'level_retest_adverse':adv,'constructive_paths':constructive[:20],'calibration_gap':calgap,'direction_auc':dau,'level_auc':lau,'year_auc':yau,'holdout_opened':False}; (out/'verdict.json').write_text(json.dumps(verdict,indent=2),encoding='utf-8')
    audit={'lab':LAB,'version':VERSION,'canonical_sha':h,'raw_rows_pre_holdout':len(df),'breaks':len(br),'bias_events':len(bev),'strong_bias_events':len(strong),'mapped_internal_events':len(internal),'holdout_opened':False}; (out/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    top=pt.head(12); path_lines=[f"- `{r.internal_path}`: Discovery N {int(r.disc_total) if pd.notna(r.disc_total) else 0}, new-leg {r.disc_new_leg_rate_all*100 if pd.notna(r.disc_new_leg_rate_all) else np.nan:.1f}%; Confirmation N {int(r.conf_total) if pd.notna(r.conf_total) else 0}, new-leg {r.conf_new_leg_rate_all*100 if pd.notna(r.conf_new_leg_rate_all) else np.nan:.1f}%" for r in top.itertuples(index=False)]
    rep=f'''# {LAB} — {VERSION} REPORT\n\n**Verdict:** `{status}`  \n**Holdout opened:** `false`\n\n## Strong-bias universe\n\n- Discovery: **{len(disc):,}**\n- Confirmation: **{len(conf):,}**\n- Confirmation resolved NEW_LEG vs LEVEL_FAILURE: **{len(sc):,}**\n- Confirmation unresolved: **{(conf.outcome=='UNRESOLVED').mean()*100:.1f}%**\n\n## Old-level return is adverse\n\nDiscovery NEW_LEG rate: no LEVEL_RETEST **{adv['DISCOVERY']['NO_LEVEL_RETEST']['new_leg_rate_all']*100:.1f}%** vs any LEVEL_RETEST **{adv['DISCOVERY']['ANY_LEVEL_RETEST']['new_leg_rate_all']*100:.1f}%** (gap {dg*100:+.1f} pp).\n\nConfirmation: no LEVEL_RETEST **{adv['CONFIRMATION']['NO_LEVEL_RETEST']['new_leg_rate_all']*100:.1f}%** vs any LEVEL_RETEST **{adv['CONFIRMATION']['ANY_LEVEL_RETEST']['new_leg_rate_all']*100:.1f}%** (gap {cg*100:+.1f} pp).\n\n## Internal ordered-path prediction — resolved target\n\n- SNAPSHOT AUC: **{m['snapshot_auc']:.4f}**\n- BAG AUC: **{m['bag_auc']:.4f}**\n- ORDERED_PATH AUC: **{m['ordered_auc']:.4f}**\n- ordered - snapshot: **{m['ordered_minus_snapshot']:+.4f}**, weekly CI **{bs['ci95']}**\n- ordered - bag: **{m['ordered_minus_bag']:+.4f}**, weekly CI **{bb['ci95']}**\n- ordered Brier: **{m['ordered_brier']:.4f}**\n- probability Q5-Q1 actual NEW_LEG gap: **{calgap*100:+.1f} pp**\n\n## Most frequent internal paths\n\n'''+ '\n'.join(path_lines) + f'''\n\n## Constructive paths passing frozen 70% / N>=100 transfer gate\n\n{chr(10).join('- `'+p+'`' for p in constructive[:20]) if constructive else '- none'}\n\n## Breadth\n\n- BUY AUC: **{dau.get('BUY',np.nan):.4f}**\n- SELL AUC: **{dau.get('SELL',np.nan):.4f}**\n- MID/HIGH/LOW: **{lau.get('MID',np.nan):.4f} / {lau.get('HIGH',np.nan):.4f} / {lau.get('LOW',np.nan):.4f}**\n- 2024 / 2025 H1: **{yau.get(2024,np.nan):.4f} / {yau.get(2025,np.nan):.4f}**\n\n## Frozen gates\n\n''' + '\n'.join(f"- {k}: {'PASS' if v else 'FAIL'}" for k,v in gates.items()) + '''\n\nNo entry/economics or holdout opening is authorized.\n'''; (out/'REPORT.md').write_text(rep,encoding='utf-8')
    print(json.dumps(verdict,indent=2))
if __name__=='__main__': main()
