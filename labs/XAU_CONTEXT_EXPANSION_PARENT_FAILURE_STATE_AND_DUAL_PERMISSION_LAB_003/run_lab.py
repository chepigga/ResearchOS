#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_EXPANSION_PARENT_FAILURE_STATE_AND_DUAL_PERMISSION_LAB_003'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB1_PATH=ROOT/'labs'/'XAU_CONTEXT_HIGH_FREQUENCY_EXECUTION_LAYER_DISCOVERY_LAB_001'/'run_lab.py'
LAB2_PATH=ROOT/'labs'/'XAU_CONTEXT_BROAD_PARENT_PERMISSION_AND_M15_OR_EXECUTION_LAB_002'/'run_lab.py'
XAU_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
EVAL_START=pd.Timestamp('2023-01-01 00:00:00')
EVAL_END=pd.Timestamp('2026-07-01 00:00:00')
FAMILIES={'SWEEP_RECLAIM','OB_RETEST','FVG_RETEST','BOS_RETEST'}
C0_EXPECT={'trades':98,'ev40':0.0752983797,'pf40':1.1407351575,'ddpct':1.9209036869}
C1_EXPECT={'trades':444,'mean_tm':10.5714285714,'ev40':0.0311535506,'cum40':13.8321764606,'ddpct':5.3881719123}


def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); assert spec.loader is not None
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod


def synthetic_parent(rows:pd.DataFrame)->pd.DataFrame:
    z=rows[['available_time']].copy().sort_values('available_time')
    z['SETUP_CONFIRMATION_PCT']=100
    return z


def merge_intervals(intervals,hf):
    if not intervals:return []
    raw=sorted(intervals,key=lambda x:x[0])
    out=[]; cs,ce,ev=raw[0]; eid=1
    for s,e,x in raw[1:]:
        if s<=ce:
            ce=max(ce,e); ev=max(ev,x)
        else:
            out.append(hf.Episode(eid,cs,ce,ev)); eid+=1; cs,ce,ev=s,e,x
    out.append(hf.Episode(eid,cs,ce,ev))
    return out


def episodes_duration(parent:pd.DataFrame,hours:int,hf):
    intervals=[]
    for _,r in parent.sort_values('available_time').iterrows():
        s=pd.Timestamp(r.available_time); intervals.append((s,s+pd.Timedelta(hours=hours),int(r.SETUP_CONFIRMATION_PCT)))
    return merge_intervals(intervals,hf)


def dual_episodes(core:pd.DataFrame,exp:pd.DataFrame,exp_hours:int,hf):
    ints=[]
    for _,r in core.sort_values('available_time').iterrows():
        s=pd.Timestamp(r.available_time); ints.append((s,s+pd.Timedelta(hours=24),int(r.SETUP_CONFIRMATION_PCT)))
    for _,r in exp.sort_values('available_time').iterrows():
        s=pd.Timestamp(r.available_time); ints.append((s,s+pd.Timedelta(hours=exp_hours),100))
    return merge_intervals(ints,hf)


def combined_parent(core:pd.DataFrame,exp:pd.DataFrame)->pd.DataFrame:
    a=core[['available_time','SETUP_CONFIRMATION_PCT']].copy()
    b=synthetic_parent(exp)
    z=pd.concat([a,b],ignore_index=True).sort_values('available_time')
    return z.drop_duplicates('available_time',keep='last').reset_index(drop=True)


def permission_stats(eps):
    hrs=0.0
    for e in eps:
        a=max(pd.Timestamp(e.start),EVAL_START); b=min(pd.Timestamp(e.end),EVAL_END)
        if b>a:hrs+=(b-a).total_seconds()/3600.0
    total=(EVAL_END-EVAL_START).total_seconds()/3600.0
    return hrs,hrs/total


def evaluate(parent_name,parent,eps,tr,hf,kind):
    mon=hf.monthly_stats(tr); blk=hf.block_stats(tr)
    n=len(tr); ev=float(tr.net40_r.mean()) if n else np.nan; pfx=hf.pf(tr.net40_r) if n else np.nan
    dd=hf.max_dd_r(tr.net40_r) if n else np.nan; ddpct=dd*hf.RISK_PCT_PER_R if np.isfinite(dd) else np.nan
    mcl=hf.max_consecutive_losses(tr.net40_r) if n else 0
    mean_tm=float(mon.trades.mean()); med_tm=float(mon.trades.median())
    pct8=float((mon.trades>=8).mean()); pct10=float((mon.trades>=10).mean())
    posblk=int((blk.expectancy_net40>0).sum()); minblk=float(blk.cum_net40_r.min())
    medhold=float(tr.holding_hours.median()) if n else np.nan
    topabs=float(tr.net40_r.abs().max()/max(tr.net40_r.abs().sum(),1e-12)) if n else np.nan
    h2=bool(kind=='EXP' and n>=180 and mean_tm>=4 and ev>=0.08 and pfx>=1.20 and ddpct<=4.0 and mcl<=8 and posblk>=3 and minblk>=-5 and medhold<=8 and topabs<=0.05)
    h3=bool(kind=='DUAL' and n>=300 and mean_tm>=8 and med_tm>=6 and pct8>=0.50 and ev>=0.08 and pfx>=1.20 and ddpct<=4.0 and mcl<=8 and posblk>=3 and minblk>=-5 and medhold<=8 and topabs<=0.05)
    target=bool(h3 and mean_tm>=10 and med_tm>=8 and pct8>=0.60)
    hrs,pct=permission_stats(eps)
    t=pd.to_datetime(parent.available_time)
    return {
        'variant':parent_name,'kind':kind,'qualifying_h4_all':len(parent),'qualifying_h4_eval':int(((t>=EVAL_START)&(t<EVAL_END)).sum()),
        'episodes_all':len(eps),'permission_hours_eval':hrs,'permission_pct_eval':pct,'trades':n,
        'mean_trades_month':mean_tm,'median_trades_month':med_tm,'pct_months_ge8':pct8,'pct_months_ge10':pct10,
        'gross_expectancy_r':float(tr.gross_r.mean()) if n else np.nan,'commission_expectancy_r':float(tr.net_comm_r.mean()) if n else np.nan,
        'spread20_expectancy_r':float(tr.net20_r.mean()) if n else np.nan,'spread40_expectancy_r':ev,'pf_spread40':pfx,
        'cum_spread40_r':float(tr.net40_r.sum()) if n else 0.0,'mean_spread40_r_month':float(mon.net40_r.mean()),
        'max_dd_r':dd,'max_dd_pct_at_025':ddpct,'max_consecutive_losses':mcl,'win_rate_net40':float((tr.net40_r>0).mean()) if n else np.nan,
        'median_hold_h':medhold,'p90_hold_h':float(tr.holding_hours.quantile(.9)) if n else np.nan,'timeout_frac':float(tr.reason.eq('TIME').mean()) if n else np.nan,
        'positive_blocks':posblk,'min_block_cum_r':minblk,'top_abs_trade_share':topabs,'h2_expansion_edge':h2,'h3_dual':h3,'target_dual':target
    },mon,blk


def run_variant(name,parent,eps,hf,lab2,mf,m15,kind):
    cands=hf.generate_candidates(m15,parent,75,eps)
    fills=lab2.prepare_fills_fast(cands,hf,mf,m15)
    tr=hf.select_portfolio(fills,FAMILIES,router=True)
    s,mon,blk=evaluate(name,parent,eps,tr,hf,kind)
    comp=tr.family.value_counts().rename_axis('source').reset_index(name='trades') if len(tr) else pd.DataFrame(columns=['source','trades'])
    comp['variant']=name
    return s,mon,blk,tr,comp,cands,fills


def parity(s0,s1):
    c0={
        'trades':int(s0['trades'])==C0_EXPECT['trades'],
        'ev40':abs(float(s0['spread40_expectancy_r'])-C0_EXPECT['ev40'])<=1e-6,
        'pf40':abs(float(s0['pf_spread40'])-C0_EXPECT['pf40'])<=1e-6,
        'ddpct':abs(float(s0['max_dd_pct_at_025'])-C0_EXPECT['ddpct'])<=1e-6,
    }
    c1={
        'trades':int(s1['trades'])==C1_EXPECT['trades'],
        'mean_tm':abs(float(s1['mean_trades_month'])-C1_EXPECT['mean_tm'])<=1e-6,
        'ev40':abs(float(s1['spread40_expectancy_r'])-C1_EXPECT['ev40'])<=1e-6,
        'cum40':abs(float(s1['cum_spread40_r'])-C1_EXPECT['cum40'])<=1e-6,
        'ddpct':abs(float(s1['max_dd_pct_at_025'])-C1_EXPECT['ddpct'])<=1e-6,
    }
    return all(c0.values()) and all(c1.values()),c0,c1


def stale_diag(raw_tr:pd.DataFrame,exp_raw:pd.DataFrame):
    times=np.sort(pd.to_datetime(exp_raw.available_time).to_numpy(dtype='datetime64[ns]'))
    rows=[]
    for _,r in raw_tr.iterrows():
        a=np.datetime64(pd.Timestamp(r.activation)); i=np.searchsorted(times,a,side='right')-1
        if i<0:continue
        dh=(pd.Timestamp(a)-pd.Timestamp(times[i])).total_seconds()/3600.0
        if dh<4:b='0-4h'
        elif dh<8:b='4-8h'
        elif dh<12:b='8-12h'
        else:b='12-24h'
        rows.append({'bucket':b,'net40_r':float(r.net40_r)})
    z=pd.DataFrame(rows)
    order=['0-4h','4-8h','8-12h','12-24h']
    out=[]
    for b in order:
        g=z[z.bucket.eq(b)] if len(z) else z
        out.append({'bucket':b,'trades':len(g),'ev40':float(g.net40_r.mean()) if len(g) else np.nan,'cum40':float(g.net40_r.sum()) if len(g) else 0.0,'pf40':hf_global.pf(g.net40_r) if len(g) else np.nan})
    return pd.DataFrame(out)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1)
    if sha256(p)!=XAU_SHA:raise RuntimeError('Canonical XAU SHA mismatch')
    hf=load_module(LAB1_PATH,'lab003_hf'); lab2=load_module(LAB2_PATH,'lab003_lab2')
    global hf_global; hf_global=hf
    m1,m15,d,q,bull=lab2.build_full_context(p,hf); mf=lab2.M1Fast(m1)
    d=d.sort_values('available_time').copy()
    d['adx_med100_prev']=pd.to_numeric(d.adx14,errors='coerce').rolling(100,min_periods=100).median().shift(1)
    d['prior6_high']=pd.to_numeric(d.high,errors='coerce').rolling(6,min_periods=6).max().shift(1)
    expmask=d.regime.eq('EXPANSION') & d.D14_CONCORDANCE.eq(1)
    expraw=d[expmask].copy()
    core=bull[bull.SETUP_CONFIRMATION_PCT.ge(75)].copy().sort_values('available_time')
    x={
      'X1_EXP_LIVE4H':expraw,
      'X2_EXP_FORMING_LIVE4H':d[expmask & d.display_role.eq('EXPANSION_FORMING')].copy(),
      'X3_EXP_MATURE_LIVE4H':d[expmask & d.display_role.eq('EXPANSION_MATURE')].copy(),
      'X4_EXP_ADX_HIGH_LIVE4H':d[expmask & d.adx_med100_prev.notna() & (d.adx14>=d.adx_med100_prev)].copy(),
      'X5_EXP_BREAKOUT_ACCEPT_LIVE4H':d[expmask & d.prior6_high.notna() & (d.close>d.prior6_high)].copy(),
      'X6_EXP_NO_G1_LIVE4H':d[expmask & ~d.G1_VOL_COMPRESSION.fillna(False)].copy(),
    }
    x={k:synthetic_parent(v) for k,v in x.items()}
    exp_parent=synthetic_parent(expraw)

    summaries=[]; months=[]; blocks=[]; trades=[]; comps=[]
    # controls
    c0eps=hf.make_episodes(core,75)
    s0,m,b,t,c,_,_=run_variant('C0_E75_CORE',core,c0eps,hf,lab2,mf,m15,'CONTROL'); summaries.append(s0); months.append(m.assign(variant='C0_E75_CORE')); blocks.append(b.assign(variant='C0_E75_CORE')); trades.append(t.assign(variant='C0_E75_CORE')); comps.append(c)
    c1eps=hf.make_episodes(exp_parent,75)
    s1,m,b,t_raw,c,_,_=run_variant('C1_EXPANSION_RAW_24H',exp_parent,c1eps,hf,lab2,mf,m15,'CONTROL'); summaries.append(s1); months.append(m.assign(variant='C1_EXPANSION_RAW_24H')); blocks.append(b.assign(variant='C1_EXPANSION_RAW_24H')); trades.append(t_raw.assign(variant='C1_EXPANSION_RAW_24H')); comps.append(c)
    parity_ok,c0checks,c1checks=parity(s0,s1)

    # standalone filtered expansion
    standalone={}
    for name,parent in x.items():
        eps=episodes_duration(parent,4,hf)
        s,m,b,t,c,_,_=run_variant(name,parent,eps,hf,lab2,mf,m15,'EXP')
        summaries.append(s); months.append(m.assign(variant=name)); blocks.append(b.assign(variant=name));
        if len(t):trades.append(t.assign(variant=name))
        comps.append(c); standalone[name]=(s,parent,eps)

    # D0 non-selectable diagnostic: core 24h + raw expansion 24h
    d0parent=combined_parent(core,exp_parent); d0eps=dual_episodes(core,exp_parent,24,hf)
    sd0,m,b,t,c,_,_=run_variant('D0_CORE_PLUS_RAW_EXP24H',d0parent,d0eps,hf,lab2,mf,m15,'DUAL_DIAG')
    summaries.append(sd0); months.append(m.assign(variant='D0_CORE_PLUS_RAW_EXP24H')); blocks.append(b.assign(variant='D0_CORE_PLUS_RAW_EXP24H'));
    if len(t):trades.append(t.assign(variant='D0_CORE_PLUS_RAW_EXP24H'))
    comps.append(c)

    dual_names=[]
    for i,(xname,parent) in enumerate(x.items(),start=1):
        name=f'D{i}_CORE_PLUS_{xname[3:]}'
        cp=combined_parent(core,parent); eps=dual_episodes(core,parent,4,hf)
        s,m,b,t,c,_,_=run_variant(name,cp,eps,hf,lab2,mf,m15,'DUAL')
        summaries.append(s); months.append(m.assign(variant=name)); blocks.append(b.assign(variant=name));
        if len(t):trades.append(t.assign(variant=name))
        comps.append(c); dual_names.append(name)

    sdf=pd.DataFrame(summaries); mdf=pd.concat(months,ignore_index=True); bdf=pd.concat(blocks,ignore_index=True)
    tdf=pd.concat(trades,ignore_index=True) if trades else pd.DataFrame(); cdf=pd.concat(comps,ignore_index=True)
    st=stale_diag(t_raw,exp_parent)
    fresh=float(st.loc[st.bucket.eq('0-4h'),'ev40'].iloc[0]) if len(st) else np.nan
    stale_below=bool(((st.bucket!='0-4h') & (st.ev40<fresh)).any()) if np.isfinite(fresh) else False
    sx1=sdf[sdf.variant.eq('X1_EXP_LIVE4H')].iloc[0]
    h1=bool(parity_ok and sx1.spread40_expectancy_r>s1['spread40_expectancy_r'] and sx1.pf_spread40>s1['pf_spread40'] and sx1.max_dd_pct_at_025<s1['max_dd_pct_at_025'] and stale_below)
    exp_pass=sdf[(sdf.kind=='EXP') & sdf.h2_expansion_edge].copy()
    dual_pass=sdf[(sdf.kind=='DUAL') & sdf.h3_dual].copy()
    target=sdf[(sdf.kind=='DUAL') & sdf.target_dual].copy()
    def choose(z):
        if z.empty:return None
        return z.sort_values(['mean_spread40_r_month','spread40_expectancy_r','pf_spread40','max_dd_pct_at_025'],ascending=[False,False,False,True]).iloc[0].variant
    winner_dual=choose(dual_pass); winner_exp=choose(exp_pass)
    if not parity_ok: verdict='TECHNICAL_PARITY_BLOCKED'
    elif len(target): verdict='TARGET_DUAL_PERMISSION_CANDIDATE_FOUND'; winner=choose(target)
    elif winner_dual: verdict='DUAL_PERMISSION_CANDIDATE_FOUND'; winner=winner_dual
    elif winner_exp: verdict='EXPANSION_FILTER_EDGE_FOUND_DUAL_NOT_READY'; winner=winner_exp
    elif h1: verdict='STALE_EXPANSION_FAILURE_CONFIRMED_BUT_NO_TRADABLE_FILTER'; winner=None
    else: verdict='EXPANSION_FAILURE_STATE_NOT_SUPPORTED'; winner=None

    # Parent feature counts
    feature_counts=pd.DataFrame([
      {'feature':'EXPANSION_RAW','bars':len(expraw)},
      {'feature':'FORMING','bars':int((expmask & d.display_role.eq('EXPANSION_FORMING')).sum())},
      {'feature':'MATURE','bars':int((expmask & d.display_role.eq('EXPANSION_MATURE')).sum())},
      {'feature':'ADX_HIGH','bars':int((expmask & d.adx_med100_prev.notna() & (d.adx14>=d.adx_med100_prev)).sum())},
      {'feature':'ADX_LOW','bars':int((expmask & d.adx_med100_prev.notna() & (d.adx14<d.adx_med100_prev)).sum())},
      {'feature':'BREAKOUT_ACCEPT','bars':int((expmask & d.prior6_high.notna() & (d.close>d.prior6_high)).sum())},
      {'feature':'G1_TRUE','bars':int((expmask & d.G1_VOL_COMPRESSION.fillna(False)).sum())},
      {'feature':'G1_FALSE','bars':int((expmask & ~d.G1_VOL_COMPRESSION.fillna(False)).sum())},
    ])

    sdf.to_csv(out/'variant_summary.csv',index=False); mdf.to_csv(out/'monthly.csv',index=False); bdf.to_csv(out/'calendar_blocks.csv',index=False); tdf.to_csv(out/'trades.csv',index=False); cdf.to_csv(out/'router_composition.csv',index=False); st.to_csv(out/'staleness_diagnostic.csv',index=False); feature_counts.to_csv(out/'parent_feature_counts.csv',index=False)
    summary={'lab':LAB,'verdict':verdict,'winner':winner,'parity_ok':parity_ok,'c0_checks':c0checks,'c1_checks':c1checks,'h1_stale_failure':h1,'winner_expansion':winner_exp,'winner_dual':winner_dual,'variants':json.loads(sdf.to_json(orient='records'))}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    lines=[f'# {LAB}',f'**Verdict: {verdict}**',f'**Winner: {winner or "NONE"}**',f'**Parity: {parity_ok} | C0 {c0checks} | C1 {c1checks}**',f'**H1 stale-tail failure: {h1}**','', '## Variant summary','',sdf.to_markdown(index=False,floatfmt='.4f'),'','## Staleness diagnostic','',st.to_markdown(index=False,floatfmt='.4f'),'','## Parent feature counts','',feature_counts.to_markdown(index=False),'','## Calendar blocks','',bdf.to_markdown(index=False,floatfmt='.4f'),'','## Router composition','',cdf.to_markdown(index=False),'','## Boundary','Discovery on reused XAU history only. Any selected winner requires frozen temporal/fresh-OOS replication before EA use.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
