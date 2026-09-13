#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, importlib.util, json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_HIGH_FREQUENCY_EXECUTION_LAYER_DISCOVERY_LAB_001'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
LAB13_PATH=ROOT/'labs'/'XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013'/'run_lab.py'
LAB16_PATH=ROOT/'labs'/'XAU_CONTEXT_SETUP_CONFIRMATION_OB_IMBALANCE_LIQUIDITY_PRICE_ACTION_LAB_016'/'run_lab.py'
XAU_SHA='db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b'
EVAL_START=pd.Timestamp('2023-01-01 00:00:00')
EVAL_END=pd.Timestamp('2026-07-01 00:00:00')
GATES=[50,75]
FAMILIES=['SWEEP_RECLAIM','OB_RETEST','FVG_RETEST','BOS_RETEST']
PRIORITY={'SWEEP_RECLAIM':0,'OB_RETEST':1,'FVG_RETEST':2,'BOS_RETEST':3}
COMMISSION_RATE_PER_DEAL=0.000007
SPREAD_STRESS=[0.20,0.40]
RISK_PCT_PER_R=0.25


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


@dataclass
class Episode:
    eid:int
    start:pd.Timestamp
    end:pd.Timestamp
    max_evidence:int


@dataclass
class Candidate:
    gate:int
    episode:int
    family:str
    activation:pd.Timestamp
    expiry:pd.Timestamp
    entry_type:str
    signal_close:float
    level:Optional[float]=None
    cancel_time:Optional[pd.Timestamp]=None
    evidence:int=0


def build_parent_context(xau_path:Path):
    lab8=load_module(LAB8_PATH,'hf_lab8')
    lab9=load_module(LAB9_PATH,'hf_lab9')
    lab10=load_module(LAB10_PATH,'hf_lab10')
    lab13=load_module(LAB13_PATH,'hf_lab13')
    lab16=load_module(LAB16_PATH,'hf_lab16')
    m1=lab8.read_xau_native(xau_path)
    m15=lab16.to_m15(m1)
    h4=lab8.to_h4(m1)
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
    pop=d.regime.eq('PULLBACK')&d.G1_VOL_COMPRESSION.fillna(False)&d.D14_CONCORDANCE.ne(0)
    d=lab16.add_confirmation(d,m15,pop)
    q=d.loc[pop].copy()
    if len(q)!=397:
        raise RuntimeError(f'LAB016 population parity failed population={len(q)}')
    bull=q[q.D14_CONCORDANCE.eq(1)].copy()
    return m1.sort_values('time').reset_index(drop=True),m15.sort_index(),h4.sort_index(),q,bull


def make_episodes(bull:pd.DataFrame,gate:int)->list[Episode]:
    z=bull[bull.SETUP_CONFIRMATION_PCT.ge(gate)].copy().sort_values('available_time')
    raw=[]
    for _,r in z.iterrows():
        s=pd.Timestamp(r.available_time); e=s+pd.Timedelta(hours=24)
        raw.append((s,e,int(r.SETUP_CONFIRMATION_PCT)))
    if not raw: return []
    out=[]; cs,ce,ev=raw[0]
    eid=1
    for s,e,x in raw[1:]:
        if s<=ce:
            ce=max(ce,e); ev=max(ev,x)
        else:
            out.append(Episode(eid,cs,ce,ev)); eid+=1; cs,ce,ev=s,e,x
    out.append(Episode(eid,cs,ce,ev))
    return out


def latest_evidence(bull_gate:pd.DataFrame,t:pd.Timestamp)->int:
    g=bull_gate[(pd.to_datetime(bull_gate.available_time)<=t)&(pd.to_datetime(bull_gate.available_time)>t-pd.Timedelta(hours=24))]
    return int(g.iloc[-1].SETUP_CONFIRMATION_PCT) if len(g) else 0


def m15_features(m15:pd.DataFrame)->pd.DataFrame:
    z=m15.copy()
    z['prior20_low']=z.low.rolling(20,min_periods=20).min().shift(1)
    z['prior4_high']=z.high.rolling(4,min_periods=4).max().shift(1)
    z['prior8_high']=z.high.rolling(8,min_periods=8).max().shift(1)
    z['body']=(z.close-z.open).abs()
    z['bar_end']=z.index+pd.Timedelta(minutes=15)
    return z


def last_bearish_mid(z:pd.DataFrame,i:int)->Optional[float]:
    for j in range(i-1,max(-1,i-5),-1):
        if j<0: break
        r=z.iloc[j]
        if r.close<r.open:
            return float((r.high+r.low)/2.0)
    return None


def cancel_time_fvg(z:pd.DataFrame,i:int,activation:pd.Timestamp,expiry:pd.Timestamp,lower:float)->Optional[pd.Timestamp]:
    # Bars after trigger only. Cancellation becomes known at their close.
    for j in range(i+1,len(z)):
        r=z.iloc[j]; bend=z.index[j]+pd.Timedelta(minutes=15)
        if bend>expiry: break
        if float(r.close)<lower:
            return bend
    return None


def generate_candidates(m15:pd.DataFrame,bull:pd.DataFrame,gate:int,episodes:list[Episode])->list[Candidate]:
    z=m15_features(m15)
    bg=bull[bull.SETUP_CONFIRMATION_PCT.ge(gate)].copy().sort_values('available_time')
    out=[]
    if not episodes: return out
    for ep in episodes:
        # Trigger bar must close while context is active.
        inds=np.flatnonzero(((z.bar_end>=ep.start)&(z.bar_end<ep.end)).to_numpy())
        for i in inds:
            r=z.iloc[i]; act=pd.Timestamp(r.bar_end); ev=latest_evidence(bg,act)
            if not np.isfinite(r.atr14_m15) or r.atr14_m15<=0: continue
            exp=min(act+pd.Timedelta(hours=3),ep.end)

            # A: sweep -> reclaim, market at next M15 open (= trigger close time).
            ref=r.prior20_low
            if np.isfinite(ref) and float(r.low)<float(ref) and float(r.close)>float(ref):
                out.append(Candidate(gate,ep.eid,'SWEEP_RECLAIM',act,act,'MARKET',float(r.close),evidence=ev))

            # B: bullish displacement -> most recent bearish OB midpoint.
            p4=r.prior4_high
            if np.isfinite(p4) and float(r.body)>=float(r.atr14_m15) and float(r.close)>float(p4):
                mid=last_bearish_mid(z,i)
                if mid is not None and mid<float(r.close):
                    out.append(Candidate(gate,ep.eid,'OB_RETEST',act,exp,'LIMIT',float(r.close),level=mid,evidence=ev))

            # C: bullish 3-candle FVG.
            if i>=2:
                lower=float(z.iloc[i-2].high); upper=float(r.low)
                if upper>lower:
                    mid=(lower+upper)/2.0
                    if mid<float(r.close):
                        ct=cancel_time_fvg(z,i,act,exp,lower)
                        out.append(Candidate(gate,ep.eid,'FVG_RETEST',act,exp,'LIMIT',float(r.close),level=mid,cancel_time=ct,evidence=ev))

            # D: BOS -> retest prior-8 high.
            p8=r.prior8_high
            if np.isfinite(p8) and float(r.close)>float(p8) and float(p8)<float(r.close):
                out.append(Candidate(gate,ep.eid,'BOS_RETEST',act,exp,'LIMIT',float(r.close),level=float(p8),evidence=ev))
    return out


def fill_candidate(c:Candidate,m1:pd.DataFrame)->Optional[dict]:
    t=m1.time
    end=c.expiry
    if c.cancel_time is not None:
        end=min(end,c.cancel_time)
    if c.entry_type=='MARKET':
        g=m1[(t>=c.activation)&(t<=(c.activation+pd.Timedelta(minutes=1)))]
        if g.empty:
            g=m1[t>=c.activation].head(1)
        if g.empty or pd.Timestamp(g.iloc[0].time)>c.activation+pd.Timedelta(minutes=2): return None
        r=g.iloc[0]
        return {'fill_time':pd.Timestamp(r.time),'entry':float(r.open),'family':c.family,'gate':c.gate,'episode':c.episode,'activation':c.activation,'evidence':c.evidence}
    if c.level is None: return None
    g=m1[(t>=c.activation)&(t<end)]
    if g.empty: return None
    hit=g[(g.low<=c.level)|(g.open<=c.level)]
    if hit.empty: return None
    r=hit.iloc[0]
    px=float(r.open) if float(r.open)<=c.level else float(c.level)
    return {'fill_time':pd.Timestamp(r.time),'entry':px,'family':c.family,'gate':c.gate,'episode':c.episode,'activation':c.activation,'evidence':c.evidence}


def attach_exit(fill:dict,m1:pd.DataFrame,m15:pd.DataFrame)->Optional[dict]:
    ft=pd.Timestamp(fill['fill_time']); entry=float(fill['entry'])
    hist=m15[m15.index<ft].tail(8)
    if len(hist)<8: return None
    atr=float(hist.iloc[-1].atr14_m15)
    if not np.isfinite(atr) or atr<=0: return None
    struct=float(hist.low.min())-0.10*atr
    sl=min(struct,entry-1.00*atr)
    dist=entry-sl
    if not np.isfinite(dist) or dist<=0 or dist>2.50*atr: return None
    tp=entry+1.50*dist
    deadline=ft+pd.Timedelta(hours=8)
    path=m1[(m1.time>=ft)&(m1.time<deadline)].copy()
    exit_time=None; exit_price=None; reason=None
    for _,r in path.iterrows():
        o,h,l=float(r.open),float(r.high),float(r.low)
        rt=pd.Timestamp(r.time)
        if o<=sl:
            exit_time,exit_price,reason=rt,o,'SL_GAP'; break
        if o>=tp:
            exit_time,exit_price,reason=rt,o,'TP_GAP'; break
        hit_sl=l<=sl; hit_tp=h>=tp
        if hit_sl and hit_tp:
            exit_time,exit_price,reason=rt,sl,'SL_AMBIG'; break
        if hit_sl:
            exit_time,exit_price,reason=rt,sl,'SL'; break
        if hit_tp:
            exit_time,exit_price,reason=rt,tp,'TP'; break
    if exit_time is None:
        x=m1[m1.time>=deadline].head(1)
        if x.empty: return None
        r=x.iloc[0]; exit_time=pd.Timestamp(r.time); exit_price=float(r.open); reason='TIME'
    gross=(exit_price-entry)/dist
    commission_r=2.0*entry*COMMISSION_RATE_PER_DEAL/dist
    net_comm=gross-commission_r
    net20=net_comm-SPREAD_STRESS[0]/dist
    net40=net_comm-SPREAD_STRESS[1]/dist
    z=dict(fill)
    z.update({'atr15':atr,'sl':sl,'tp':tp,'stop_dist':dist,'exit_time':exit_time,'exit_price':exit_price,'reason':reason,
              'holding_hours':(exit_time-ft).total_seconds()/3600.0,'gross_r':gross,'commission_r':commission_r,
              'net_comm_r':net_comm,'net20_r':net20,'net40_r':net40})
    return z


def prepare_fills(cands:list[Candidate],m1:pd.DataFrame,m15:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for c in cands:
        f=fill_candidate(c,m1)
        if f is None: continue
        x=attach_exit(f,m1,m15)
        if x is not None: rows.append(x)
    if not rows: return pd.DataFrame()
    z=pd.DataFrame(rows).sort_values(['fill_time','family','activation']).reset_index(drop=True)
    return z


def select_portfolio(fills:pd.DataFrame,families:set[str],router:bool=False)->pd.DataFrame:
    if fills.empty: return fills.copy()
    z=fills[fills.family.isin(families)].copy()
    z['prio']=z.family.map(PRIORITY).fillna(99)
    z=z.sort_values(['fill_time','prio','activation']).reset_index(drop=True)
    selected=[]; flat_after=pd.Timestamp.min; cooldown_until=pd.Timestamp.min; day_counts={}
    for _,r in z.iterrows():
        ft=pd.Timestamp(r.fill_time)
        if ft<EVAL_START or ft>=EVAL_END: continue
        if ft<flat_after or ft<cooldown_until: continue
        day=ft.normalize()
        if day_counts.get(day,0)>=2: continue
        selected.append(r.to_dict())
        et=pd.Timestamp(r.exit_time)
        flat_after=et
        cooldown_until=et+pd.Timedelta(minutes=60)
        day_counts[day]=day_counts.get(day,0)+1
    if not selected: return pd.DataFrame(columns=z.columns)
    return pd.DataFrame(selected).sort_values('fill_time').reset_index(drop=True)


def max_consecutive_losses(v:pd.Series)->int:
    best=cur=0
    for x in v.to_numpy(float):
        if x<0: cur+=1; best=max(best,cur)
        else: cur=0
    return int(best)


def max_dd_r(v:pd.Series)->float:
    if len(v)==0:return np.nan
    c=np.r_[0.0,np.cumsum(v.to_numpy(float))]
    peak=np.maximum.accumulate(c)
    return float(np.max(peak-c))


def pf(v:pd.Series)->float:
    a=v[v>0].sum(); b=-v[v<0].sum()
    return float(a/b) if b>0 else (np.inf if a>0 else np.nan)


def block_stats(tr:pd.DataFrame)->pd.DataFrame:
    blocks=[('2023',pd.Timestamp('2023-01-01'),pd.Timestamp('2024-01-01')),
            ('2024',pd.Timestamp('2024-01-01'),pd.Timestamp('2025-01-01')),
            ('2025',pd.Timestamp('2025-01-01'),pd.Timestamp('2026-01-01')),
            ('2026H1',pd.Timestamp('2026-01-01'),pd.Timestamp('2026-07-01'))]
    rows=[]
    for name,a,b in blocks:
        g=tr[(tr.fill_time>=a)&(tr.fill_time<b)]
        rows.append({'block':name,'n':len(g),'expectancy_net40':float(g.net40_r.mean()) if len(g) else np.nan,
                     'cum_net40_r':float(g.net40_r.sum()) if len(g) else 0.0})
    return pd.DataFrame(rows)


def monthly_stats(tr:pd.DataFrame)->pd.DataFrame:
    months=pd.period_range('2023-01','2026-06',freq='M')
    rows=[]
    p=pd.to_datetime(tr.fill_time).dt.to_period('M') if len(tr) else pd.Series([],dtype='period[M]')
    for m in months:
        g=tr[p.eq(m)] if len(tr) else tr
        rows.append({'month':str(m),'trades':len(g),'net40_r':float(g.net40_r.sum()) if len(g) else 0.0,
                     'expectancy_net40':float(g.net40_r.mean()) if len(g) else np.nan})
    return pd.DataFrame(rows)


def summarize_variant(name:str,gate:int,tr:pd.DataFrame)->tuple[dict,pd.DataFrame,pd.DataFrame]:
    mon=monthly_stats(tr); blk=block_stats(tr)
    n=len(tr); exp=float(tr.net40_r.mean()) if n else np.nan; pfx=pf(tr.net40_r) if n else np.nan
    dd=max_dd_r(tr.net40_r) if n else np.nan; dd_pct=dd*RISK_PCT_PER_R if np.isfinite(dd) else np.nan
    pos_blocks=int((blk.expectancy_net40>0).sum())
    min_block=float(blk.cum_net40_r.min()) if len(blk) else np.nan
    mean_tm=float(mon.trades.mean()); median_tm=float(mon.trades.median()); pct10=float((mon.trades>=10).mean())
    viable=bool(n>=420 and mean_tm>=10 and np.isfinite(exp) and exp>=0.15 and np.isfinite(pfx) and pfx>=1.35 and
                np.isfinite(dd_pct) and dd_pct<=4.0 and max_consecutive_losses(tr.net40_r)<=8 and
                (float(tr.holding_hours.median()) if n else np.inf)<=8.0 and pos_blocks>=3 and min_block>=-5.0)
    if viable and 20<=mean_tm<=40: cls='TARGET_FREQUENCY'
    elif viable and 10<=mean_tm<20: cls='VIABLE_LOW_FREQUENCY'
    elif viable and mean_tm>40: cls='OVERACTIVE'
    else: cls='NOT_VIABLE'
    top_abs=float(tr.net40_r.abs().max()/max(abs(tr.net40_r).sum(),1e-12)) if n else np.nan
    s={'variant':name,'gate':gate,'trades':n,'mean_trades_month':mean_tm,'median_trades_month':median_tm,
       'pct_months_ge10':pct10,'gross_expectancy_r':float(tr.gross_r.mean()) if n else np.nan,
       'commission_expectancy_r':float(tr.net_comm_r.mean()) if n else np.nan,
       'spread20_expectancy_r':float(tr.net20_r.mean()) if n else np.nan,'spread40_expectancy_r':exp,
       'pf_spread40':pfx,'cum_spread40_r':float(tr.net40_r.sum()) if n else 0.0,
       'mean_spread40_r_month':float(mon.net40_r.mean()),'max_dd_r':dd,'max_dd_pct_at_025':dd_pct,
       'max_consecutive_losses':max_consecutive_losses(tr.net40_r) if n else 0,
       'win_rate_net40':float((tr.net40_r>0).mean()) if n else np.nan,
       'median_hold_h':float(tr.holding_hours.median()) if n else np.nan,
       'p90_hold_h':float(tr.holding_hours.quantile(.9)) if n else np.nan,
       'timeout_frac':float(tr.reason.eq('TIME').mean()) if n else np.nan,
       'positive_blocks':pos_blocks,'min_block_cum_r':min_block,'classification':cls,
       'top_abs_trade_share':top_abs}
    return s,mon,blk


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xau-m1',required=True); ap.add_argument('--out',required=True)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    p=Path(args.xau_m1)
    if sha256(p)!=XAU_SHA: raise RuntimeError('Canonical XAU SHA mismatch')
    m1,m15,h4,q,bull=build_parent_context(p)
    parent={'population_all_sides':len(q),'bull_population':len(bull),
            'bull_e50_h4':int(bull.SETUP_CONFIRMATION_PCT.ge(50).sum()),
            'bull_e75_h4':int(bull.SETUP_CONFIRMATION_PCT.ge(75).sum())}

    all_summ=[]; trade_outputs=[]; monthly_outputs=[]; block_outputs=[]; trigger_diag=[]; router_comp=[]
    for gate in GATES:
        eps=make_episodes(bull,gate)
        cands=generate_candidates(m15,bull,gate,eps)
        fills=prepare_fills(cands,m1,m15)
        # Trigger/fill diagnostics by family.
        for fam in FAMILIES:
            ntr=sum(1 for c in cands if c.family==fam)
            nf=int((fills.family==fam).sum()) if len(fills) else 0
            trigger_diag.append({'gate':gate,'family':fam,'episodes':len(eps),'raw_triggers':ntr,'valid_fills_after_stop_filter':nf,
                                 'fill_or_valid_rate':nf/ntr if ntr else np.nan})
        for fam in FAMILIES:
            tr=select_portfolio(fills,{fam})
            name=f'E{gate}_{fam}'
            s,mon,blk=summarize_variant(name,gate,tr); all_summ.append(s)
            if len(tr): tr2=tr.copy(); tr2['variant']=name; trade_outputs.append(tr2)
            mon2=mon.copy(); mon2['variant']=name; monthly_outputs.append(mon2)
            blk2=blk.copy(); blk2['variant']=name; block_outputs.append(blk2)
        tr=select_portfolio(fills,set(FAMILIES),router=True)
        name=f'E{gate}_OR_ROUTER'
        s,mon,blk=summarize_variant(name,gate,tr); all_summ.append(s)
        if len(tr):
            tr2=tr.copy(); tr2['variant']=name; trade_outputs.append(tr2)
            comp=tr.family.value_counts().rename_axis('source').reset_index(name='trades'); comp['gate']=gate; router_comp.append(comp)
        mon2=mon.copy(); mon2['variant']=name; monthly_outputs.append(mon2)
        blk2=blk.copy(); blk2['variant']=name; block_outputs.append(blk2)

    summary_df=pd.DataFrame(all_summ)
    trades_df=pd.concat(trade_outputs,ignore_index=True) if trade_outputs else pd.DataFrame()
    months_df=pd.concat(monthly_outputs,ignore_index=True)
    blocks_df=pd.concat(block_outputs,ignore_index=True)
    trigger_df=pd.DataFrame(trigger_diag)
    router_df=pd.concat(router_comp,ignore_index=True) if router_comp else pd.DataFrame(columns=['source','trades','gate'])

    # Deterministic discovery selection.
    rank={'TARGET_FREQUENCY':0,'VIABLE_LOW_FREQUENCY':1,'OVERACTIVE':1,'NOT_VIABLE':2}
    summary_df['_rank']=summary_df.classification.map(rank)
    ordered=summary_df.sort_values(['_rank','mean_spread40_r_month','pf_spread40','max_dd_pct_at_025'],ascending=[True,False,False,True])
    winner=ordered.iloc[0].variant if len(ordered) and ordered.iloc[0].classification!='NOT_VIABLE' else None
    if (summary_df.classification=='TARGET_FREQUENCY').any(): verdict='HIGH_FREQUENCY_EXECUTION_CANDIDATE_FOUND'
    elif summary_df.classification.isin(['VIABLE_LOW_FREQUENCY','OVERACTIVE']).any(): verdict='EXECUTION_EDGE_FOUND_FREQUENCY_BELOW_TARGET'
    else: verdict='NO_HIGH_FREQUENCY_EXECUTION_METHOD_SUPPORTED'

    summary={'lab':LAB,'verdict':verdict,'discovery_winner':winner,'parent':parent,
             'evaluation_window':[str(EVAL_START),str(EVAL_END-pd.Timedelta(seconds=1))],
             'variants':json.loads(summary_df.drop(columns=['_rank']).to_json(orient='records'))}
    summary_df.drop(columns=['_rank']).to_csv(out/'variant_summary.csv',index=False)
    trades_df.to_csv(out/'trades.csv',index=False)
    months_df.to_csv(out/'monthly.csv',index=False)
    blocks_df.to_csv(out/'calendar_blocks.csv',index=False)
    trigger_df.to_csv(out/'trigger_fill_diagnostics.csv',index=False)
    router_df.to_csv(out/'router_composition.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))

    show=summary_df.drop(columns=['_rank']).sort_values(['classification','mean_spread40_r_month'],ascending=[True,False])
    lines=[f'# {LAB}',f'**Verdict: {verdict}**',f'**Discovery winner: {winner or "NONE"}**','',
           '## Frozen parent counts','',pd.DataFrame([parent]).to_markdown(index=False),'',
           '## Variant summary','',show.to_markdown(index=False,floatfmt='.4f'),'',
           '## Trigger / fill diagnostics','',trigger_df.to_markdown(index=False,floatfmt='.4f'),'',
           '## OR-router composition','',router_df.to_markdown(index=False) if len(router_df) else '_No router trades_','',
           '## Calendar blocks','',blocks_df.to_markdown(index=False,floatfmt='.4f'),'',
           '## Boundary','This is execution-layer discovery on reused XAU history. No selected method is production-validated until a separately preregistered temporal/OOS replication passes.']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
