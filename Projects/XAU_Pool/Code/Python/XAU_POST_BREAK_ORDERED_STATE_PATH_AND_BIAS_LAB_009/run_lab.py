#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

LAB='XAU_POST_BREAK_ORDERED_STATE_PATH_AND_BIAS_LAB_009'
VERSION='v001'
CANONICAL_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
HOLDOUT=pd.Timestamp('2025-07-01')
DISC_END=pd.Timestamp('2024-01-01')
ANCHOR_HOUR=1
BAND_K=1.618
CLOCKS=(15,30)
FUTURE_MIN=30
MIN_CELL=50
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
    use=['time','open','high','low','close','tick_volume']
    x=pd.read_csv(path,sep=';',usecols=use)
    x['time']=pd.to_datetime(x.time,format='%Y.%m.%d %H:%M',errors='coerce')
    for c in use:
        if c!='time': x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x.dropna(subset=use).sort_values('time').drop_duplicates('time',keep='last')
    x=x[x.time<HOLDOUT].reset_index(drop=True)
    return x

def wilder_atr(h,l,c,n=14):
    pc=c.shift(1)
    tr=pd.concat([(h-l),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def add_atr_and_lines(df:pd.DataFrame)->pd.DataFrame:
    o=df.copy()
    m=(o.set_index('time').resample('15min',label='left',closed='left').agg(high=('high','max'),low=('low','min'),close=('close','last')).dropna())
    m['atr']=wilder_atr(m.high,m.low,m.close)
    a=m[['atr']].reset_index(); a['avail']=a.time+pd.Timedelta(minutes=15)
    a=a[['avail','atr']].dropna().sort_values('avail')
    o=pd.merge_asof(o.sort_values('time'),a,left_on='time',right_on='avail',direction='backward').drop(columns='avail')
    o['session']=(o.time-pd.Timedelta(hours=ANCHOR_HOUR)).dt.floor('D')
    p=(o.high+o.low+o.close)/3.0; v=o.tick_volume.clip(lower=0).fillna(0)
    gv=v.groupby(o.session).cumsum(); gpv=(p*v).groupby(o.session).cumsum(); gp2=((p*p)*v).groupby(o.session).cumsum()
    mid=gpv/gv.replace(0,np.nan); var=(gp2/gv.replace(0,np.nan)-mid*mid).clip(lower=0); sd=np.sqrt(var)
    o['VWAP_MID']=mid; o['VWAP_HIGH']=mid+BAND_K*sd; o['VWAP_LOW']=mid-BAND_K*sd
    n=(pd.Series(np.ones(len(o)),index=o.index).groupby(o.session).cumsum()).astype(float)
    cp=p.groupby(o.session).cumsum(); cp2=(p*p).groupby(o.session).cumsum(); mm=cp/n; vv=(cp2/n-mm*mm).clip(lower=0); ss=np.sqrt(vv)
    o['MEAN_MID']=mm; o['MEAN_HIGH']=mm+BAND_K*ss; o['MEAN_LOW']=mm-BAND_K*ss
    return o.reset_index(drop=True)

def load_breaks(path:Path)->pd.DataFrame:
    e=pd.read_csv(path,compression='gzip'); e['break_time']=pd.to_datetime(e.break_time,errors='coerce'); e=e[e.break_time<HOLDOUT].copy()
    req=['family','level','break_i','break_time','dir','split','year']; miss=[c for c in req if c not in e.columns]
    if miss: raise ValueError(f'missing LAB008 columns {miss}')
    z=e[req].drop_duplicates(['family','level','break_i','break_time','dir']).copy()
    return z.sort_values(['break_time','family','level','dir']).reset_index(drop=True)

def state_token(vals:np.ndarray)->str:
    start=float(vals[0]); end=float(vals[-1]); frac=float((vals>0).mean()); mn=float(vals.min()); mx=float(vals.max())
    if end<=-0.05 or frac<0.40: return 'RECLAIM'
    if mn<=-0.05 and end>=0.05 and frac>=0.60: return 'FAILED_RECOVERY'
    if frac>=0.80 and (end-start)>=0.10 and (mx-start)>=0.15: return 'EXPAND'
    if np.min(np.abs(vals))<=0.05 and end>0 and frac>=0.60: return 'TEST'
    if frac>=0.80 and mn>-0.05: return 'HOLD'
    return 'CHOP'
def bag_key(tokens:list[str])->str:
    c=Counter(tokens); return '|'.join(f'{s}:{c.get(s,0)}' for s in STATES)
def level_array(df:pd.DataFrame,family:str,level:str)->np.ndarray:
    prefix='VWAP' if family=='VWAP_VOLUME' else 'MEAN'; return df[f'{prefix}_{level}'].to_numpy(float)
def build_story_events(breaks:pd.DataFrame,df:pd.DataFrame)->pd.DataFrame:
    times=(df.time.astype('int64')//60_000_000_000).to_numpy(np.int64); close=df.close.to_numpy(float); atr=df.atr.to_numpy(float)
    line_cache={(fam,lev):level_array(df,fam,lev) for fam in ['VWAP_VOLUME','ANCHOR_MEAN'] for lev in LEVELS}; rows=[]
    for r in breaks.itertuples(index=False):
        bi=int(r.break_i)
        if bi<0 or bi>=len(df) or df.at[bi,'time']!=r.break_time: continue
        a=float(atr[bi])
        if not np.isfinite(a) or a<=0: continue
        line=line_cache.get((str(r.family),str(r.level)))
        if line is None: continue
        for clock in CLOCKS:
            di=bi+clock; future_end=di+FUTURE_MIN
            if future_end>=len(df): continue
            if times[future_end] != times[bi] + future_end-bi: continue
            if df.at[future_end,'time']>=HOLDOUT: continue
            toks=[]; ok=True
            for b0 in range(1,clock+1,5):
                idx=np.arange(bi+b0,bi+b0+5); lv=line[idx]
                if not np.isfinite(lv).all(): ok=False; break
                vals=int(r.dir)*(close[idx]-lv)/a; toks.append(state_token(vals))
            if not ok: continue
            fidx=np.arange(di+1,di+FUTURE_MIN+1); flv=line[fidx]
            if not np.isfinite(flv).all(): continue
            fdist=int(r.dir)*(close[fidx]-flv)/a
            rows.append({'family':r.family,'level':r.level,'break_i':bi,'break_time':r.break_time,'dir':int(r.dir),'split':r.split,'year':int(r.year),'clock':clock,'snapshot':toks[-1],'bag':bag_key(toks),'ordered_path':'>'.join(toks),'last2':'>'.join(toks[-2:]) if len(toks)>=2 else toks[-1],'n_states':len(toks),'acceptance_persists':int((fdist>0).sum()>=20),'terminal_side':int(fdist[-1]>0),'no_deep_reclaim':int(np.min(fdist)>-0.05)})
    return pd.DataFrame(rows)
def fit_prob_map(train:pd.DataFrame,key:str,target:str)->dict:
    g=train.groupby(key)[target].agg(['sum','count']); return {str(k):(int(v['sum']),int(v['count'])) for k,v in g.iterrows()}
def smoothed(sc): s,n=sc; return (s+1.0)/(n+2.0)
def add_probs(train:pd.DataFrame,test:pd.DataFrame,target='acceptance_persists')->pd.DataFrame:
    snap=fit_prob_map(train,'snapshot',target); bag=fit_prob_map(train,'bag',target); exact=fit_prob_map(train,'ordered_path',target); last2=fit_prob_map(train,'last2',target); base=(float(train[target].sum())+1)/(len(train)+2)
    out=test.copy(); ps=[]; pb=[]; po=[]; src=[]
    for r in out.itertuples(index=False):
        ss=snap.get(str(r.snapshot)); p_snap=smoothed(ss) if ss else base
        bb=bag.get(str(r.bag)); p_bag=smoothed(bb) if bb and bb[1]>=MIN_CELL else p_snap
        ee=exact.get(str(r.ordered_path)); ll=last2.get(str(r.last2))
        if ee and ee[1]>=MIN_CELL: p_ord=smoothed(ee); source='EXACT'
        elif ll and ll[1]>=MIN_CELL: p_ord=smoothed(ll); source='LAST2'
        else: p_ord=p_snap; source='SNAPSHOT'
        ps.append(p_snap); pb.append(p_bag); po.append(p_ord); src.append(source)
    out['p_snapshot']=ps; out['p_bag']=pb; out['p_ordered']=po; out['ordered_source']=src; return out
def auc(y,p):
    y=np.asarray(y,int); p=np.asarray(p,float)
    if len(np.unique(y))<2:return np.nan
    return float(roc_auc_score(y,p))
def metrics(x:pd.DataFrame,target='acceptance_persists')->dict:
    y=x[target].to_numpy(int); out={'n':int(len(x)),'base_rate':float(y.mean())}
    for name in ['snapshot','bag','ordered']:
        p=x[f'p_{name}'].to_numpy(float); out[f'{name}_auc']=auc(y,p); out[f'{name}_brier']=float(brier_score_loss(y,p)); out[f'{name}_logloss']=float(log_loss(y,np.clip(p,1e-8,1-1e-8),labels=[0,1]))
    out['ordered_minus_snapshot_auc']=out['ordered_auc']-out['snapshot_auc']; out['ordered_minus_bag_auc']=out['ordered_auc']-out['bag_auc']; return out
def weekly_auc_diffs(x:pd.DataFrame,target='acceptance_persists')->pd.DataFrame:
    z=x.copy(); z['week']=pd.to_datetime(z.break_time).dt.to_period('W-MON').astype(str); rows=[]
    for w,g in z.groupby('week'):
        y=g[target]
        if len(g)<20 or y.nunique()<2: continue
        ao=auc(y,g.p_ordered); ass=auc(y,g.p_snapshot); ab=auc(y,g.p_bag); rows.append({'week':w,'ord_snap':ao-ass,'ord_bag':ao-ab})
    return pd.DataFrame(rows)
def boot_mean(v,seed):
    a=np.asarray(pd.Series(v).dropna(),float)
    if len(a)<8:return {'n':int(len(a)),'mean':float(a.mean()) if len(a) else None,'ci95':[None,None]}
    rng=np.random.default_rng(seed); b=np.empty(BOOT_N,float)
    for i in range(BOOT_N): b[i]=rng.choice(a,size=len(a),replace=True).mean()
    return {'n':int(len(a)),'mean':float(a.mean()),'ci95':[float(np.quantile(b,.025)),float(np.quantile(b,.975))]}
def calibration(x:pd.DataFrame)->pd.DataFrame:
    z=x.copy(); z['rank']=z.p_ordered.rank(method='first',pct=True); z['quintile']=pd.cut(z['rank'],[0,.2,.4,.6,.8,1],labels=['Q1','Q2','Q3','Q4','Q5'],include_lowest=True)
    return z.groupby('quintile',observed=True).agg(n=('acceptance_persists','size'),mean_p=('p_ordered','mean'),actual=('acceptance_persists','mean')).reset_index()
def subgroup_auc(x:pd.DataFrame,col:str)->pd.DataFrame:
    return pd.DataFrame([{col:k,'n':len(g),'auc':auc(g.acceptance_persists,g.p_ordered),'base_rate':g.acceptance_persists.mean()} for k,g in x.groupby(col)])
def path_table(train:pd.DataFrame,conf:pd.DataFrame)->pd.DataFrame:
    d=train.groupby('ordered_path').acceptance_persists.agg(['size','mean']).rename(columns={'size':'disc_n','mean':'disc_rate'}); c=conf.groupby('ordered_path').acceptance_persists.agg(['size','mean']).rename(columns={'size':'conf_n','mean':'conf_rate'})
    return d.join(c,how='outer').fillna({'disc_n':0,'conf_n':0}).reset_index().sort_values('conf_n',ascending=False)
def transition_table(x:pd.DataFrame)->pd.DataFrame:
    cnt=Counter()
    for p in x.ordered_path:
        t=str(p).split('>')
        for a,b in zip(t[:-1],t[1:]): cnt[(a,b)]+=1
    return pd.DataFrame([{'from':a,'to':b,'n':n} for (a,b),n in cnt.items()]).sort_values(['from','n'],ascending=[True,False])
def run_family_clock(ev:pd.DataFrame,family:str,clock:int):
    z=ev[(ev.family==family)&(ev.clock==clock)].copy(); tr=z[z.break_time<DISC_END].copy(); cf=z[(z.break_time>=DISC_END)&(z.break_time<HOLDOUT)].copy(); scored=add_probs(tr,cf); return tr,scored,metrics(scored)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input',type=Path); ap.add_argument('--lab008-events',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); out=a.outdir; out.mkdir(parents=True,exist_ok=True)
    h=sha256(a.input)
    if h!=CANONICAL_SHA: raise RuntimeError(f'canonical SHA mismatch {h}')
    raw=load_prices(a.input); df=add_atr_and_lines(raw); br=load_breaks(a.lab008_events); ev=build_story_events(br,df); ev.to_csv(out/'events.csv.gz',index=False,compression='gzip')
    summaries=[]; scored_primary=None; train_primary=None
    for fam in ['VWAP_VOLUME','ANCHOR_MEAN']:
        for clock in CLOCKS:
            tr,cf,m=run_family_clock(ev,fam,clock); summaries.append({'family':fam,'clock':clock,**m})
            if fam=='VWAP_VOLUME' and clock==15: scored_primary=cf; train_primary=tr
    sm=pd.DataFrame(summaries); sm.to_csv(out/'model_summary.csv',index=False)
    if scored_primary is None or train_primary is None: raise RuntimeError('missing primary')
    scored_primary.to_csv(out/'confirmation_T15_scored.csv.gz',index=False,compression='gzip')
    wk=weekly_auc_diffs(scored_primary); wk.to_csv(out/'weekly_auc_diffs.csv',index=False); bs=boot_mean(wk.ord_snap,SEED); bb=boot_mean(wk.ord_bag,SEED+1)
    cal=calibration(scored_primary); cal.to_csv(out/'calibration.csv',index=False); pt=path_table(train_primary,scored_primary); pt.to_csv(out/'path_table.csv',index=False); transition_table(scored_primary).to_csv(out/'transition_matrix.csv',index=False)
    da=subgroup_auc(scored_primary.assign(direction=np.where(scored_primary.dir>0,'BUY','SELL')),'direction'); da.to_csv(out/'direction_auc.csv',index=False); la=subgroup_auc(scored_primary,'level'); la.to_csv(out/'level_auc.csv',index=False); ya=subgroup_auc(scored_primary.assign(year=pd.to_datetime(scored_primary.break_time).dt.year),'year'); ya.to_csv(out/'yearly_auc.csv',index=False)
    pm=metrics(scored_primary); t30=sm[(sm.family=='VWAP_VOLUME')&(sm.clock==30)].iloc[0].to_dict(); top_bottom=float(cal.iloc[-1].actual-cal.iloc[0].actual) if len(cal)>=2 else np.nan
    gates={'G0_DATA_CAUSALITY':bool(h==CANONICAL_SHA and (ev.break_time<HOLDOUT).all()),'G1_POWER':bool(pm['n']>=8000),'G2_BIAS_AUC':bool(pm['ordered_auc']>=0.75),'G3_ORDER_BEATS_SNAPSHOT':bool(pm['ordered_minus_snapshot_auc']>=0.01 and bs['ci95'][0] is not None and bs['ci95'][0]>0),'G4_ORDER_BEATS_BAG':bool(pm['ordered_minus_bag_auc']>=0.01 and bb['ci95'][0] is not None and bb['ci95'][0]>0),'G5_BRIER_INCREMENTAL':bool(pm['ordered_brier']<pm['snapshot_brier'] and pm['ordered_brier']<pm['bag_brier']),'G6_CALIBRATION':bool(top_bottom>=0.25),'G7_DIRECTION_MIRROR':bool(len(da)==2 and da.auc.min()>=0.70),'G8_LEVEL_BREADTH':bool(set(la.level)==set(LEVELS) and la.auc.min()>=0.70),'G9_YEAR_TRANSFER':bool(set([2024,2025]).issubset(set(ya.year)) and ya[ya.year.isin([2024,2025])].auc.min()>=0.70),'G10_T30_SURVIVAL':bool(float(t30['ordered_auc'])>=0.70)}
    if all(gates.values()): status='ORDERED_STORYLINE_ADDS_BIAS_INFORMATION'
    elif gates['G0_DATA_CAUSALITY'] and gates['G1_POWER'] and gates['G2_BIAS_AUC'] and gates['G6_CALIBRATION'] and gates['G7_DIRECTION_MIRROR'] and gates['G8_LEVEL_BREADTH'] and gates['G9_YEAR_TRANSFER'] and (not gates['G3_ORDER_BEATS_SNAPSHOT'] or not gates['G4_ORDER_BEATS_BAG']): status='BIAS_STRONG_ORDER_NOT_INCREMENTAL'
    elif gates['G2_BIAS_AUC'] and gates['G3_ORDER_BEATS_SNAPSHOT'] and gates['G4_ORDER_BEATS_BAG']: status='ORDER_INCREMENTAL_BUT_NARROW'
    elif not gates['G0_DATA_CAUSALITY']: status='INVALID_DATA_CAUSALITY'
    else: status='NO_ORDERED_STORYLINE_EDGE'
    verdict={'status':status,'gates':gates,'primary_confirmation':pm,'weekly_order_minus_snapshot':bs,'weekly_order_minus_bag':bb,'calibration_top_minus_bottom':top_bottom,'t30_ordered_auc':float(t30['ordered_auc']),'holdout_opened':False}; (out/'verdict.json').write_text(json.dumps(verdict,indent=2),encoding='utf-8')
    audit={'canonical_sha':h,'raw_rows':len(raw),'preholdout_rows':len(df),'break_rows':len(br),'story_rows':len(ev),'primary_confirmation_n':pm['n'],'holdout_opened':False}; (out/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    top=pt.head(10); lines=[f'# {LAB} — {VERSION} REPORT','',f'**Verdict:** `{status}`  ','**Holdout opened:** `false`','','## Primary T+15 bias result','',f'- Confirmation N: **{pm["n"]:,}**',f'- acceptance base rate: **{pm["base_rate"]:.2%}**',f'- SNAPSHOT_STATE AUC: **{pm["snapshot_auc"]:.4f}**',f'- BAG_OF_STATES AUC: **{pm["bag_auc"]:.4f}**',f'- ORDERED_PATH AUC: **{pm["ordered_auc"]:.4f}**',f'- ordered − snapshot: **{pm["ordered_minus_snapshot_auc"]:+.4f}**',f'- ordered − bag: **{pm["ordered_minus_bag_auc"]:+.4f}**',f'- snapshot / bag / ordered Brier: **{pm["snapshot_brier"]:.4f} / {pm["bag_brier"]:.4f} / {pm["ordered_brier"]:.4f}**',f'- calibration Q5 − Q1 actual acceptance: **{top_bottom:+.2%}**','','## T+30 survival','',f'- ORDERED_PATH AUC: **{float(t30["ordered_auc"]):.4f}**','','## Breadth','']
    for r in da.itertuples(index=False): lines.append(f'- {r.direction}: N {r.n:,}, ordered AUC **{r.auc:.4f}**')
    for r in la.itertuples(index=False): lines.append(f'- {r.level}: N {r.n:,}, ordered AUC **{r.auc:.4f}**')
    for r in ya.itertuples(index=False): lines.append(f'- {int(r.year)}: N {r.n:,}, ordered AUC **{r.auc:.4f}**')
    lines += ['','## Most frequent ordered paths in Confirmation','']
    for r in top.itertuples(index=False): lines.append(f'- `{r.ordered_path}`: Discovery N {int(r.disc_n):,}, rate {float(r.disc_rate):.1%}; Confirmation N {int(r.conf_n):,}, rate {float(r.conf_rate):.1%}')
    lines += ['','## Frozen gates','']+[f'- {k}: {"PASS" if v else "FAIL"}' for k,v in gates.items()]
    interp='Bias persistence is strong, but the chronological order of coarse 5-minute states does not add enough OOS information beyond the final state / unordered state mix.' if status=='BIAS_STRONG_ORDER_NOT_INCREMENTAL' else ('The chronological storyline adds transferable OOS bias information beyond both the current state and the unordered set of states.' if status=='ORDERED_STORYLINE_ADDS_BIAS_INFORMATION' else 'The preregistered ordered-state representation does not provide robust transferable bias information under the frozen definitions.')
    lines += ['','## Interpretation','',interp,'','No entry/economics or holdout opening is authorized.']; (out/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8'); print(json.dumps(verdict,indent=2))
if __name__=='__main__': main()
