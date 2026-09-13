#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, importlib.util, json
from pathlib import Path

import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_BROAD_PARENT_PERMISSION_AND_M15_OR_EXECUTION_LAB_002'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB1_PATH=ROOT/'labs'/'XAU_CONTEXT_HIGH_FREQUENCY_EXECUTION_LAYER_DISCOVERY_LAB_001'/'run_lab.py'
XAU_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
EVAL_START=pd.Timestamp('2023-01-01 00:00:00')
EVAL_END=pd.Timestamp('2026-07-01 00:00:00')
FAMILIES={'SWEEP_RECLAIM','OB_RETEST','FVG_RETEST','BOS_RETEST'}
BASE_EXPECTED={'trades':98,'ev40':0.0752983797,'pf40':1.1407351575,'ddpct':1.9209036869}


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); assert spec.loader is not None
    spec.loader.exec_module(mod); return mod


class M1Fast:
    def __init__(self,m1:pd.DataFrame):
        z=m1.sort_values('time').reset_index(drop=True)
        self.df=z
        self.t=pd.to_datetime(z.time).to_numpy(dtype='datetime64[ns]')
        self.o=z.open.to_numpy(float); self.h=z.high.to_numpy(float); self.l=z.low.to_numpy(float)
    def left(self,t:pd.Timestamp)->int:
        return int(np.searchsorted(self.t,np.datetime64(pd.Timestamp(t)),side='left'))


def build_full_context(p:Path,hf):
    m1,m15,h4,q,bull=hf.build_parent_context(p)
    lab8=hf.load_module(hf.LAB8_PATH,'bp_lab8')
    lab9=hf.load_module(hf.LAB9_PATH,'bp_lab9')
    lab10=hf.load_module(hf.LAB10_PATH,'bp_lab10')
    lab13=hf.load_module(hf.LAB13_PATH,'bp_lab13')
    router=lab8.load_router_module()
    ctx=router.add_router(h4)
    ctx=lab8.add_forward_metrics(ctx)
    ctx=ctx.dropna(subset=['available_time','atr14']).copy()
    allbars,onset=lab8.make_episodes(ctx)
    if len(allbars)!=6216 or len(onset)!=610:
        raise RuntimeError(f'Parent parity failed bars={len(allbars)} episodes={len(onset)}')
    d=lab9.add_roles(allbars)
    d=lab10.add_components_and_candidates(d)
    d=lab13.add_prediction_candidates(d)
    d['D14_CONCORDANCE']=np.where((d.D1_HTF_BIAS==d.D2_TREND_PRESSURE)&d.D1_HTF_BIAS.ne(0),d.D1_HTF_BIAS,0).astype(int)
    return m1,m15,d,q,bull


def synthetic_parent(rows:pd.DataFrame)->pd.DataFrame:
    z=rows[['available_time']].copy().sort_values('available_time')
    z['SETUP_CONFIRMATION_PCT']=100
    return z


def parent_sources(d:pd.DataFrame,q:pd.DataFrame,bull:pd.DataFrame)->dict[str,pd.DataFrame]:
    out={}
    out['P0_BASELINE_E75']=bull[bull.SETUP_CONFIRMATION_PCT.ge(75)].copy()
    b=d.D14_CONCORDANCE.eq(1)
    g=d.G1_VOL_COMPRESSION.fillna(False)
    out['P1_PULLBACK_D14']=synthetic_parent(d[b & d.regime.eq('PULLBACK')])
    out['P2_G1_D14']=synthetic_parent(d[b & g])
    out['P3_EXPANSION_D14']=synthetic_parent(d[b & d.regime.eq('EXPANSION')])
    out['P4_PULLBACK_OR_EXPANSION_D14']=synthetic_parent(d[b & d.regime.isin(['PULLBACK','EXPANSION'])])
    out['P5_NONRANGE_D14']=synthetic_parent(d[b & ~d.regime.eq('RANGE')])
    out['P6_D14_ALL']=synthetic_parent(d[b])
    return out


def fill_candidate_fast(c,hf,mf:M1Fast):
    end=c.expiry
    if c.cancel_time is not None: end=min(end,c.cancel_time)
    i=mf.left(c.activation)
    if c.entry_type=='MARKET':
        if i>=len(mf.t): return None
        tt=pd.Timestamp(mf.t[i])
        if tt>c.activation+pd.Timedelta(minutes=2): return None
        return {'fill_time':tt,'entry':float(mf.o[i]),'family':c.family,'gate':c.gate,'episode':c.episode,
                'activation':c.activation,'evidence':c.evidence}
    if c.level is None:return None
    j=mf.left(end)
    if i>=j:return None
    hit=np.flatnonzero((mf.l[i:j]<=c.level)|(mf.o[i:j]<=c.level))
    if len(hit)==0:return None
    k=i+int(hit[0]); px=float(mf.o[k]) if float(mf.o[k])<=c.level else float(c.level)
    return {'fill_time':pd.Timestamp(mf.t[k]),'entry':px,'family':c.family,'gate':c.gate,'episode':c.episode,
            'activation':c.activation,'evidence':c.evidence}


def attach_exit_fast(fill,hf,mf:M1Fast,m15:pd.DataFrame):
    ft=pd.Timestamp(fill['fill_time']); entry=float(fill['entry'])
    hist=m15[m15.index<ft].tail(8)
    if len(hist)<8:return None
    atr=float(hist.iloc[-1].atr14_m15)
    if not np.isfinite(atr) or atr<=0:return None
    struct=float(hist.low.min())-0.10*atr
    sl=min(struct,entry-1.00*atr); dist=entry-sl
    if not np.isfinite(dist) or dist<=0 or dist>2.50*atr:return None
    tp=entry+1.50*dist; deadline=ft+pd.Timedelta(hours=8)
    i=mf.left(ft); j=mf.left(deadline)
    exit_time=None; exit_price=None; reason=None
    for k in range(i,min(j,len(mf.t))):
        o,h,l=float(mf.o[k]),float(mf.h[k]),float(mf.l[k]); rt=pd.Timestamp(mf.t[k])
        if o<=sl: exit_time,exit_price,reason=rt,o,'SL_GAP'; break
        if o>=tp: exit_time,exit_price,reason=rt,o,'TP_GAP'; break
        hit_sl=l<=sl; hit_tp=h>=tp
        if hit_sl and hit_tp: exit_time,exit_price,reason=rt,sl,'SL_AMBIG'; break
        if hit_sl: exit_time,exit_price,reason=rt,sl,'SL'; break
        if hit_tp: exit_time,exit_price,reason=rt,tp,'TP'; break
    if exit_time is None:
        k=mf.left(deadline)
        if k>=len(mf.t):return None
        exit_time=pd.Timestamp(mf.t[k]); exit_price=float(mf.o[k]); reason='TIME'
    gross=(exit_price-entry)/dist
    commission_r=2.0*entry*hf.COMMISSION_RATE_PER_DEAL/dist
    net_comm=gross-commission_r
    net20=net_comm-hf.SPREAD_STRESS[0]/dist
    net40=net_comm-hf.SPREAD_STRESS[1]/dist
    z=dict(fill); z.update({'atr15':atr,'sl':sl,'tp':tp,'stop_dist':dist,'exit_time':exit_time,'exit_price':exit_price,
        'reason':reason,'holding_hours':(exit_time-ft).total_seconds()/3600.0,'gross_r':gross,'commission_r':commission_r,
        'net_comm_r':net_comm,'net20_r':net20,'net40_r':net40})
    return z


def prepare_fills_fast(cands,hf,mf,m15):
    rows=[]
    for c in cands:
        f=fill_candidate_fast(c,hf,mf)
        if f is None:continue
        x=attach_exit_fast(f,hf,mf,m15)
        if x is not None: rows.append(x)
    return pd.DataFrame(rows).sort_values(['fill_time','family','activation']).reset_index(drop=True) if rows else pd.DataFrame()


def permission_stats(eps)->tuple[float,float]:
    hrs=0.0
    for e in eps:
        a=max(pd.Timestamp(e.start),EVAL_START); b=min(pd.Timestamp(e.end),EVAL_END)
        if b>a: hrs+=(b-a).total_seconds()/3600.0
    total=(EVAL_END-EVAL_START).total_seconds()/3600.0
    return hrs,hrs/total if total else np.nan


def eval_count(parent:pd.DataFrame)->int:
    t=pd.to_datetime(parent.available_time)
    return int(((t>=EVAL_START)&(t<EVAL_END)).sum())


def summarize(name:str,parent:pd.DataFrame,eps,tr:pd.DataFrame,hf)->tuple[dict,pd.DataFrame,pd.DataFrame]:
    mon=hf.monthly_stats(tr); blk=hf.block_stats(tr)
    n=len(tr); exp=float(tr.net40_r.mean()) if n else np.nan; pfx=hf.pf(tr.net40_r) if n else np.nan
    dd=hf.max_dd_r(tr.net40_r) if n else np.nan; ddpct=dd*hf.RISK_PCT_PER_R if np.isfinite(dd) else np.nan
    mean_tm=float(mon.trades.mean()); med_tm=float(mon.trades.median()); pct10=float((mon.trades>=10).mean())
    pos_blocks=int((blk.expectancy_net40>0).sum()); min_block=float(blk.cum_net40_r.min()) if len(blk) else np.nan
    mcl=hf.max_consecutive_losses(tr.net40_r) if n else 0
    med_hold=float(tr.holding_hours.median()) if n else np.nan
    top_abs=float(tr.net40_r.abs().max()/max(tr.net40_r.abs().sum(),1e-12)) if n else np.nan
    h1=bool(mean_tm>=10 and med_tm>=8 and pct10>=0.60)
    h2=bool(n>=300 and np.isfinite(exp) and exp>=0.05 and np.isfinite(pfx) and pfx>=1.10 and
            np.isfinite(ddpct) and ddpct<=4.0 and mcl<=8 and med_hold<=8.0 and pos_blocks>=3 and
            min_block>=-5.0 and np.isfinite(top_abs) and top_abs<=0.05)
    target=bool(h2 and mean_tm>=20 and med_tm>=15 and pct10>=0.75)
    if target: cls='TARGET_FREQUENCY'
    elif h1 and h2: cls='VIABLE_MEDIUM_FREQUENCY'
    elif h2: cls='EDGE_ONLY'
    elif h1: cls='FREQUENCY_ONLY'
    else: cls='NOT_VIABLE'
    ph,pct=permission_stats(eps)
    s={'parent':name,'qualifying_h4_all':len(parent),'qualifying_h4_eval':eval_count(parent),'episodes_all':len(eps),
       'permission_hours_eval':ph,'permission_pct_eval':pct,'trades':n,'mean_trades_month':mean_tm,
       'median_trades_month':med_tm,'pct_months_ge10':pct10,'gross_expectancy_r':float(tr.gross_r.mean()) if n else np.nan,
       'commission_expectancy_r':float(tr.net_comm_r.mean()) if n else np.nan,'spread20_expectancy_r':float(tr.net20_r.mean()) if n else np.nan,
       'spread40_expectancy_r':exp,'pf_spread40':pfx,'cum_spread40_r':float(tr.net40_r.sum()) if n else 0.0,
       'mean_spread40_r_month':float(mon.net40_r.mean()),'max_dd_r':dd,'max_dd_pct_at_025':ddpct,
       'max_consecutive_losses':mcl,'win_rate_net40':float((tr.net40_r>0).mean()) if n else np.nan,
       'median_hold_h':med_hold,'p90_hold_h':float(tr.holding_hours.quantile(.9)) if n else np.nan,
       'timeout_frac':float(tr.reason.eq('TIME').mean()) if n else np.nan,'positive_blocks':pos_blocks,
       'min_block_cum_r':min_block,'top_abs_trade_share':top_abs,'h1_frequency':h1,'h2_edge':h2,'h3_both':bool(h1 and h2),
       'classification':cls}
    return s,mon,blk


def baseline_parity(s:dict)->tuple[bool,dict]:
    checks={
      'trades': int(s['trades'])==BASE_EXPECTED['trades'],
      'ev40': abs(float(s['spread40_expectancy_r'])-BASE_EXPECTED['ev40'])<=1e-6,
      'pf40': abs(float(s['pf_spread40'])-BASE_EXPECTED['pf40'])<=1e-6,
      'ddpct': abs(float(s['max_dd_pct_at_025'])-BASE_EXPECTED['ddpct'])<=1e-6,
    }
    return all(checks.values()),checks


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1)
    if sha256(p)!=XAU_SHA: raise RuntimeError('Canonical XAU SHA mismatch')
    hf=load_module(LAB1_PATH,'hf_lab001_frozen')
    m1,m15,d,q,bull=build_full_context(p,hf); mf=M1Fast(m1)
    parents=parent_sources(d,q,bull)

    summaries=[]; trades_all=[]; months_all=[]; blocks_all=[]; diag=[]; comps=[]
    for name,parent in parents.items():
        eps=hf.make_episodes(parent,75)
        cands=hf.generate_candidates(m15,parent,75,eps)
        fills=prepare_fills_fast(cands,hf,mf,m15)
        tr=hf.select_portfolio(fills,FAMILIES,router=True)
        s,mon,blk=summarize(name,parent,eps,tr,hf); summaries.append(s)
        if len(tr):
            x=tr.copy(); x['parent']=name; trades_all.append(x)
            c=x.family.value_counts().rename_axis('source').reset_index(name='trades'); c['parent']=name; comps.append(c)
        mm=mon.copy(); mm['parent']=name; months_all.append(mm)
        bb=blk.copy(); bb['parent']=name; blocks_all.append(bb)
        for fam in sorted(FAMILIES):
            ntr=sum(1 for c in cands if c.family==fam and EVAL_START<=pd.Timestamp(c.activation)<EVAL_END)
            nf=int(((fills.family==fam)&(pd.to_datetime(fills.fill_time)>=EVAL_START)&(pd.to_datetime(fills.fill_time)<EVAL_END)).sum()) if len(fills) else 0
            diag.append({'parent':name,'family':fam,'raw_triggers_eval':ntr,'valid_fills_eval':nf,'valid_rate':nf/ntr if ntr else np.nan})

    sdf=pd.DataFrame(summaries)
    tdf=pd.concat(trades_all,ignore_index=True) if trades_all else pd.DataFrame()
    mdf=pd.concat(months_all,ignore_index=True); bdf=pd.concat(blocks_all,ignore_index=True)
    ddf=pd.DataFrame(diag); cdf=pd.concat(comps,ignore_index=True) if comps else pd.DataFrame(columns=['source','trades','parent'])
    base=sdf[sdf.parent.eq('P0_BASELINE_E75')].iloc[0].to_dict(); parity,checks=baseline_parity(base)
    broad=sdf[~sdf.parent.eq('P0_BASELINE_E75')].copy()
    if not parity:
        verdict='TECHNICAL_PARITY_BLOCKED'; winner=None
    else:
        rank={'TARGET_FREQUENCY':0,'VIABLE_MEDIUM_FREQUENCY':1,'EDGE_ONLY':2,'FREQUENCY_ONLY':3,'NOT_VIABLE':4}
        broad['_rank']=broad.classification.map(rank)
        eligible=broad[broad.h2_edge].copy()
        if len(eligible):
            winner=eligible.sort_values(['mean_spread40_r_month','spread40_expectancy_r','pf_spread40','max_dd_pct_at_025'],ascending=[False,False,False,True]).iloc[0].parent
        else: winner=None
        if (broad.classification=='TARGET_FREQUENCY').any(): verdict='BROAD_PARENT_TARGET_FREQUENCY_CANDIDATE_FOUND'
        elif (broad.classification=='VIABLE_MEDIUM_FREQUENCY').any(): verdict='BROAD_PARENT_MEDIUM_FREQUENCY_CANDIDATE_FOUND'
        elif (broad.classification=='EDGE_ONLY').any(): verdict='BROAD_PARENT_EDGE_FOUND_FREQUENCY_STILL_LOW'
        elif (broad.classification=='FREQUENCY_ONLY').any(): verdict='FREQUENCY_LIFT_FOUND_BUT_EDGE_NOT_PRESERVED'
        else: verdict='BROAD_PARENT_PERMISSION_NOT_SUPPORTED'
        broad.drop(columns=['_rank'],inplace=True)

    summary={'lab':LAB,'verdict':verdict,'discovery_winner':winner,'baseline_parity_pass':parity,'baseline_checks':checks,
             'evaluation_window':[str(EVAL_START),str(EVAL_END-pd.Timedelta(seconds=1))],
             'parents':json.loads(sdf.to_json(orient='records'))}
    sdf.to_csv(out/'parent_summary.csv',index=False); tdf.to_csv(out/'trades.csv',index=False); mdf.to_csv(out/'monthly.csv',index=False)
    bdf.to_csv(out/'calendar_blocks.csv',index=False); ddf.to_csv(out/'trigger_fill_diagnostics.csv',index=False); cdf.to_csv(out/'router_composition.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    lines=[f'# {LAB}',f'**Verdict: {verdict}**',f'**Discovery winner: {winner or "NONE"}**',f'**Baseline parity: {parity} {checks}**','',
           '## Parent summary','',sdf.to_markdown(index=False,floatfmt='.4f'),'','## Calendar blocks','',bdf.to_markdown(index=False,floatfmt='.4f'),'',
           '## Trigger / fill diagnostics','',ddf.to_markdown(index=False,floatfmt='.4f'),'','## OR-router composition','',
           cdf.to_markdown(index=False) if len(cdf) else '_No trades_','',
           '## Boundary','Discovery only on reused XAU history. Any selected parent must be frozen and replicated on a separate temporal/fresh-OOS sample before EA or production use.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
