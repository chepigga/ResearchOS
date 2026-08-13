#!/usr/bin/env python3
"""SELL_CORE_005 — HTF_RESISTANCE_LOCATION x FAILED_BREAKOUT.

Preregistered before outcomes from the user's visual SELL model and SELL_CORE_004 failure:

Context (frozen from 004):
- HTF bear = canonical H4 Supertrend ATR10 x3 DOWN, U05 BAR_OPEN lag1.
- Local bull correction = last completed H1 close > EMA20, EMA20 rising vs 4 H1 bars ago,
  and H1 close > close 4 bars ago.

Location modules (NO outcome-driven threshold grid):
H1_HORIZONTAL:
- latest causally confirmed H1 swing high, pivot strength=2;
- M15 high trades ABOVE the level and same M15 bar closes BELOW it;
- pivot must be confirmed before M15 bar opens; first failure per pivot only.
H4_HORIZONTAL:
- identical construction on H4 swing highs, pivot strength=2.
H4_DESC_TRENDLINE:
- last two causally confirmed H4 swing highs, strength=2;
- second swing high must be lower than first;
- extend the line through the two pivot highs to current M15 bar OPEN time;
- M15 high trades above projected line and same M15 close returns below it;
- first failure per swing-pair only.
COMBINED_OR:
- union of the three modules, one event per M15 decision bar.

Execution/outcome:
- SELL next M1 open after M15 close;
- SL = 1.5 x completed H1 ATR14; no TP;
- 48h primary / 72h sensitivity; $27.5/BTC cost proxy.

Controls:
- layer each location module: location-only -> +HTF bear -> +local bull correction;
- compare COMBINED_OR primary against matched non-location generic M15 failed-breakouts
  from SELL_CORE_004 with same year + exact H4 ST age + nearest H1 ATR%;
- cluster bootstrap by continuous H4 ST episode;
- next-H4 occurrence diagnostic for COMBINED_OR primary;
- B1/B2/B3/B4 are diagnostics, not construction gates.

Frozen price window: unified Binance 2024-01-01 through 2026-08-10.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import sell_core_004_htf_bear_local_correction_failed_breakout as p4

M1ZIP='btc_1m.zip'; M5ZIP='btc_5m.zip'; OUT=Path('sell_core_005_out'); OUT.mkdir(exist_ok=True)
START=pd.Timestamp('2024-01-01'); HOLDS=(48,72); BOOT=20000; SEED=405005


def pivot_stream(bars, prefix, strength=2):
    """Return causal confirmation stream for swing highs.
    A pivot at p is first known when right-side bar p+strength has CLOSED.
    """
    x=bars.reset_index(drop=True).copy(); H=x.high.to_numpy(float); rows=[]
    for p in range(strength,len(x)-strength):
        if H[p]>np.max(H[p-strength:p]) and H[p]>=np.max(H[p+1:p+strength+1]):
            ci=p+strength
            rows.append({
                'effective_time':pd.Timestamp(x.close_time.iloc[ci]),
                f'{prefix}_pivot_idx':int(p),
                f'{prefix}_pivot_time':pd.Timestamp(x.time.iloc[p]),
                f'{prefix}_res':float(H[p]),
            })
    return pd.DataFrame(rows).sort_values('effective_time') if rows else pd.DataFrame()


def trendline_stream(h4,strength=2):
    ps=pivot_stream(h4,'h4tl',strength)
    if ps.empty:return ps
    rows=[]
    prev=None
    for r in ps.itertuples(index=False):
        cur={'effective_time':pd.Timestamp(r.effective_time),'idx':int(r.h4tl_pivot_idx),
             'time':pd.Timestamp(r.h4tl_pivot_time),'price':float(r.h4tl_res)}
        if prev is not None and cur['price']<prev['price'] and cur['time']>prev['time']:
            dt=(cur['time']-prev['time']).total_seconds()
            slope=(cur['price']-prev['price'])/dt
            rows.append({'effective_time':cur['effective_time'],
                         'tl_p1_idx':prev['idx'],'tl_p2_idx':cur['idx'],
                         'tl_p1_time':prev['time'],'tl_p2_time':cur['time'],
                         'tl_p1_price':prev['price'],'tl_p2_price':cur['price'],
                         'tl_slope_per_sec':slope,
                         'tl_key':f"{prev['idx']}_{cur['idx']}"})
        prev=cur
    return pd.DataFrame(rows).sort_values('effective_time') if rows else pd.DataFrame()


def attach_latest(cand,stream):
    if stream.empty:return cand.copy()
    return pd.merge_asof(cand.sort_values('time'),stream.sort_values('effective_time'),
                         left_on='time',right_on='effective_time',direction='backward')


def detect_location_events(cand,h1,h4raw):
    # Causal horizontal levels.
    h1ps=pivot_stream(h1,'h1',2); h4ps=pivot_stream(h4raw,'h4',2); tls=trendline_stream(h4raw,2)
    z=attach_latest(cand,h1ps); z=attach_latest(z,h4ps); z=attach_latest(z,tls)

    z['fail_h1']=(z.h1_res.notna())&(z.high>z.h1_res)&(z.close<z.h1_res)
    z['fail_h4']=(z.h4_res.notna())&(z.high>z.h4_res)&(z.close<z.h4_res)
    # Trendline projected to M15 BAR OPEN; all line anchors are known before bar open.
    secs=(z.time-z.tl_p2_time).dt.total_seconds()
    z['tl_level']=z.tl_p2_price+z.tl_slope_per_sec*secs
    z['fail_tl']=(z.tl_key.notna())&(secs>=0)&(z.high>z.tl_level)&(z.close<z.tl_level)

    # First failure per causal resistance object.
    e1=z[z.fail_h1].sort_values('decision_time').drop_duplicates('h1_pivot_idx',keep='first').copy(); e1['module']='H1_HORIZONTAL'; e1['res_key']='H1_'+e1.h1_pivot_idx.astype(int).astype(str)
    e4=z[z.fail_h4].sort_values('decision_time').drop_duplicates('h4_pivot_idx',keep='first').copy(); e4['module']='H4_HORIZONTAL'; e4['res_key']='H4_'+e4.h4_pivot_idx.astype(int).astype(str)
    et=z[z.fail_tl].sort_values('decision_time').drop_duplicates('tl_key',keep='first').copy(); et['module']='H4_DESC_TRENDLINE'; et['res_key']='TL_'+et.tl_key.astype(str)

    allmod=pd.concat([e1,e4,et],ignore_index=True,sort=False).sort_values('decision_time') if (len(e1)+len(e4)+len(et)) else pd.DataFrame()
    if len(allmod):
        # OR = one signal per M15 bar. Preserve which modules agreed.
        info=(allmod.groupby('decision_time').module.apply(lambda s:'+'.join(sorted(set(s)))).rename('module_combo').reset_index())
        comb=allmod.sort_values(['decision_time','module']).drop_duplicates('decision_time',keep='first').drop(columns=['module'],errors='ignore').merge(info,on='decision_time',how='left')
        comb['module']='COMBINED_OR'; comb['res_key']='OR_'+comb.decision_time.astype(str)
    else: comb=allmod.copy()
    return z,{'H1_HORIZONTAL':e1,'H4_HORIZONTAL':e4,'H4_DESC_TRENDLINE':et,'COMBINED_OR':comb}


def ctx_mask(x): return x.st_dir.eq(-1)&x['corr'].fillna(False)


def replay_modules(mods,m1,h1):
    out={}
    for name,e in mods.items():
        r=p4.replay(e,m1,h1,'decision_time',name) if len(e) else pd.DataFrame()
        if len(r):r['module']=name
        out[name]=r
    return out


def metric(g,name):
    if g is None or len(g)==0:
        d={'branch':name,'N':0,'episodes':0}
        for hh in HOLDS:d.update({f'EV_R{hh}':np.nan,f'PF{hh}':np.nan,f'WR{hh}':np.nan,f'EV_pct{hh}':np.nan,f'SL_rate{hh}':np.nan})
        return d
    return p4.metrics(g,name)


def layer_metrics(reps):
    rows=[]
    for name,r in reps.items():
        if not len(r):
            rows += [metric(r,f'{name}_ANY'),metric(r,f'{name}_HTF_BEAR'),metric(r,f'{name}_PRIMARY')]; continue
        rows.append(metric(r,f'{name}_ANY'))
        rows.append(metric(r[r.st_dir==-1],f'{name}_HTF_BEAR'))
        rows.append(metric(r[ctx_mask(r)],f'{name}_PRIMARY'))
    return pd.DataFrame(rows)


def cluster_boot_ev(g,col,seed):
    if len(g)==0:return {'EV':np.nan,'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    z=g[['st_episode_id',col]].dropna(); ids=z.st_episode_id.unique()
    if len(ids)<5:return {'EV':float(z[col].mean()),'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    a=z.groupby('st_episode_id')[col].agg(['sum','count']).to_numpy(float); rng=np.random.default_rng(seed); vals=[]
    for _ in range(BOOT):
        s=a[rng.integers(0,len(a),len(a))].sum(axis=0); vals.append(s[0]/s[1])
    v=np.asarray(vals); return {'EV':float(z[col].mean()),'lo':float(np.quantile(v,.025)),'hi':float(np.quantile(v,.975)),'P_gt0':float((v>0).mean())}


def build_generic_failed_breakouts(cand):
    _,ev=p4.detect_events(cand)
    return ev


def matched_location_control(primary,generic,m1,h1):
    """Compare location events with generic non-location M15 failed breakouts in same state."""
    if len(primary)==0:return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    loc_times=set(primary.decision_time)
    pool=generic[(generic.st_dir==-1)&generic['corr'].fillna(False)&(~generic.decision_time.isin(loc_times))].copy()
    pool['year']=pool.decision_time.dt.year
    p=primary.copy(); p['year']=p.decision_time.dt.year
    controls=[]; audit=[]
    for i,r in p.iterrows():
        q=pool[(pool.year==r.year)&(pool.st_age==r.st_age)].copy()
        if not len(q):continue
        q['dist']=(q.atr_pct-r.atr_pct).abs(); q=q.sort_values(['dist','decision_time']).head(5)
        for _,c in q.iterrows():
            d=c.to_dict(); d['event_key']=int(i); controls.append(d)
        audit.append({'event_key':int(i),'riskset_N':len(pool[(pool.year==r.year)&(pool.st_age==r.st_age)]),'K':len(q)})
    if not controls:return pd.DataFrame(),pd.DataFrame(),pd.DataFrame(audit)
    cr=p4.replay(pd.DataFrame(controls),m1,h1,'decision_time','GENERIC_FAILED_BREAKOUT_CONTROL'); cr['event_key']=cr.event_key.astype(int)
    pp=p.copy(); pp['event_key']=pp.index.astype(int)
    means=cr.groupby('event_key').agg(control_R48=('R48','mean'),control_pct48=('pct48','mean'),control_R72=('R72','mean'),control_pct72=('pct72','mean')).reset_index()
    pair=pp.merge(means,on='event_key',how='inner')
    for hh in HOLDS:
        pair[f'delta_R{hh}']=pair[f'R{hh}']-pair[f'control_R{hh}']; pair[f'delta_pct{hh}']=pair[f'pct{hh}']-pair[f'control_pct{hh}']
    return cr,pair,pd.DataFrame(audit)


def boot_delta(pair,col,seed):
    if len(pair)==0:return {'delta':np.nan,'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    z=pair[['st_episode_id',col]].dropna(); ids=z.st_episode_id.unique()
    if len(ids)<5:return {'delta':float(z[col].mean()),'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    a=z.groupby('st_episode_id')[col].agg(['sum','count']).to_numpy(float); rng=np.random.default_rng(seed); vals=[]
    for _ in range(BOOT):
        s=a[rng.integers(0,len(a),len(a))].sum(axis=0); vals.append(s[0]/s[1])
    v=np.asarray(vals); return {'delta':float(z[col].mean()),'lo':float(np.quantile(v,.025)),'hi':float(np.quantile(v,.975)),'P_gt0':float((v>0).mean())}


def next_h4_replay(primary,m1,h1):
    if not len(primary):return pd.DataFrame()
    x=primary.copy(); x['next_h4_time']=x.decision_time.dt.floor('4h')+pd.Timedelta(hours=4)
    return p4.replay(x,m1,h1,'next_h4_time','NEXT_H4_AFTER_LOCATION_FAILURE')


def main():
    m1=base.load_zip(M1ZIP); m5=base.load_zip(M5ZIP)
    m1=m1[m1.time>=START].copy(); m5=m5[m5.time>=START-pd.Timedelta(days=90)].copy()
    h1=p4.make_h1(m1); clock=p4.make_clock(m5); m15=p4.make_m15(m5)
    cand=p4.attach_states(m15,h1,clock); cand=cand[cand.decision_time>=START].dropna(subset=['st_dir','st_age','atr14']).copy()
    h4raw=base.resample(m5,'4h')

    state,mods=detect_location_events(cand,h1,h4raw)
    state.to_csv(OUT/'m15_state_with_htf_resistance.csv',index=False)
    for n,e in mods.items(): e.to_csv(OUT/f'events_{n}.csv',index=False)
    reps=replay_modules(mods,m1,h1)
    for n,r in reps.items(): r.to_csv(OUT/f'replay_{n}.csv',index=False)

    layers=layer_metrics(reps); layers.to_csv(OUT/'layer_metrics.csv',index=False)

    # Primary module-level yearly and bucket diagnostics.
    yearly=[]; buckets=[]; boot=[]
    for name,r in reps.items():
        if not len(r):continue
        pr=r[ctx_mask(r)].copy(); pr['year']=pr.decision_time.dt.year
        pr['bucket']=np.select([pr.st_age<=11,pr.st_age<=27,pr.st_age<=58],['B1','B2','B3'],default='B4')
        for y,g in pr.groupby('year'): yearly.append({'module':name,'year':int(y),**metric(g,'PRIMARY')})
        for b,g in pr.groupby('bucket'): buckets.append({'module':name,'bucket':b,**metric(g,'PRIMARY')})
        for hh in HOLDS:
            q=cluster_boot_ev(pr,f'R{hh}',SEED+hh+sum(map(ord,name)))
            boot.append({'module':name,'hold_h':hh,**q,'EV_pct':float(pr[f'pct{hh}'].mean())})
    pd.DataFrame(yearly).to_csv(OUT/'yearly_primary.csv',index=False)
    pd.DataFrame(buckets).to_csv(OUT/'market_clock_buckets.csv',index=False)
    pd.DataFrame(boot).to_csv(OUT/'cluster_bootstrap.csv',index=False)

    # Location-value control: COMBINED_OR primary vs non-location generic failed breakouts.
    comb=reps['COMBINED_OR']; primary=comb[ctx_mask(comb)].copy() if len(comb) else comb
    generic=build_generic_failed_breakouts(cand)
    cr,pair,audit=matched_location_control(primary,generic,m1,h1)
    cr.to_csv(OUT/'matched_generic_controls.csv',index=False); pair.to_csv(OUT/'location_pairs.csv',index=False); audit.to_csv(OUT/'matching_audit.csv',index=False)
    comp=[]
    for hh in HOLDS:
        d=boot_delta(pair,f'delta_R{hh}',SEED+1000+hh); dp=boot_delta(pair,f'delta_pct{hh}',SEED+2000+hh)
        comp.append({'hold_h':hh,'N_pairs':len(pair),'event_EV_R':float(pair[f'R{hh}'].mean()) if len(pair) else np.nan,
                     'control_EV_R':float(pair[f'control_R{hh}'].mean()) if len(pair) else np.nan,
                     'delta_R':d['delta'],'CI_R_lo':d['lo'],'CI_R_hi':d['hi'],'P_delta_R_gt0':d['P_gt0'],
                     'event_EV_pct':float(pair[f'pct{hh}'].mean()) if len(pair) else np.nan,
                     'control_EV_pct':float(pair[f'control_pct{hh}'].mean()) if len(pair) else np.nan,
                     'delta_pct':dp['delta'],'CI_pct_lo':dp['lo'],'CI_pct_hi':dp['hi'],'P_delta_pct_gt0':dp['P_gt0']})
    pd.DataFrame(comp).to_csv(OUT/'matched_location_vs_generic.csv',index=False)

    nh=next_h4_replay(primary,m1,h1); nh.to_csv(OUT/'next_h4_replay.csv',index=False)
    nhm=pd.DataFrame([metric(nh,'NEXT_H4_AFTER_LOCATION_FAILURE')]) if len(nh) else pd.DataFrame(); nhm.to_csv(OUT/'next_h4_metrics.csv',index=False)

    # Census / overlap.
    sets={n:set(e.decision_time) for n,e in mods.items() if n!='COMBINED_OR'}
    census=pd.DataFrame([{
        'module':n,'events':len(e),'primary_events':int(ctx_mask(e).sum()) if len(e) else 0,
        'primary_episodes':int(e[ctx_mask(e)].st_episode_id.nunique()) if len(e) else 0
    } for n,e in mods.items()])
    census.to_csv(OUT/'census.csv',index=False)
    overlap=pd.DataFrame([
        {'a':a,'b':b,'intersection':len(sets[a]&sets[b])}
        for i,a in enumerate(sets) for b in list(sets)[i+1:]
    ]); overlap.to_csv(OUT/'module_overlap.csv',index=False)

    # Report.
    Y=pd.DataFrame(yearly); B=pd.DataFrame(buckets); BT=pd.DataFrame(boot); CP=pd.DataFrame(comp)
    lines=['# SELL_CORE_005 — HTF_RESISTANCE_LOCATION × FAILED_BREAKOUT','',
           '**Frozen visual mechanism:** H4 bear → H1 bull correction → failed breakout specifically at causal HTF resistance.','',
           '## Location modules','',
           '- H1 horizontal: latest confirmed H1 swing high (strength=2), same-bar sweep + close back below.',
           '- H4 horizontal: latest confirmed H4 swing high (strength=2), same-bar sweep + close back below.',
           '- H4 descending trendline: last two confirmed H4 swing highs must descend; line projected causally; same-bar sweep + close back below.',
           '- Combined OR: one M15 signal bar if any module fires. No distance threshold/grid.','',
           '## Layering','',layers.to_markdown(index=False),'',
           '## Cluster bootstrap — PRIMARY only','',BT.to_markdown(index=False) if len(BT) else 'none','',
           '## Yearly PRIMARY','',Y.to_markdown(index=False) if len(Y) else 'none','',
           '## Market-clock diagnostic','',B.to_markdown(index=False) if len(B) else 'none','',
           '## Matched location value vs generic failed breakout','',CP.to_markdown(index=False) if len(CP) else 'none','',
           '## Next-H4 occurrence diagnostic','',nhm.to_markdown(index=False) if len(nhm) else 'none','',
           '## Census','',census.to_markdown(index=False),'',
           '## Interpretation rule','',
           'A location module is promoted only if PRIMARY is positive in R and price space, is not carried by one year, and location-conditioned failure improves on matched generic failed-breakout controls. Exact timing and next-H4 occurrence are reported separately.']
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
