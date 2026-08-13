#!/usr/bin/env python3
"""SELL_CORE_005B — acceptance-safe correction of SELL_CORE_005.

This is NOT a new hypothesis. It fixes a causal validity bug found before accepting 005A:
a resistance object must stop existing after acceptance above it.

For every causal H1/H4 swing-high resistance and every causal descending H4 trendline:
- ACTIVE after confirmation;
- first interaction resolves the object:
    close > resistance => ACCEPTED / INVALIDATED, never tradable later;
    high > resistance AND close < resistance => FAILED_BREAKOUT event, then retired;
- untouched objects remain active.

All context, entry, exit, controls and preregistered modules are unchanged from SELL_CORE_005A.
"""
from pathlib import Path
import bisect
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import sell_core_004_htf_bear_local_correction_failed_breakout as p4
import sell_core_005_htf_resistance_failed_breakout as a

M1ZIP=a.M1ZIP; M5ZIP=a.M5ZIP; START=a.START; HOLDS=a.HOLDS; BOOT=a.BOOT; SEED=405105
OUT=Path('sell_core_005b_out'); OUT.mkdir(exist_ok=True)


def horizontal_lifecycle(cand,pivots,prefix,module):
    """Online causal active-level engine. Each level is resolved once at first high-cross interaction."""
    if pivots.empty:return pd.DataFrame(), {'total':0,'failed':0,'accepted':0,'untouched':0}
    piv=pivots.sort_values('effective_time').reset_index(drop=True)
    active=[]  # sorted tuples (price, unique_seq, pivot_row_dict)
    pi=0; seq=0; events=[]; accepted=0
    for _,bar in cand.sort_values('time').iterrows():
        t=pd.Timestamp(bar.time)
        while pi<len(piv) and pd.Timestamp(piv.effective_time.iloc[pi])<=t:
            pr=piv.iloc[pi].to_dict(); price=float(pr[f'{prefix}_res'])
            bisect.insort(active,(price,seq,pr)); seq+=1; pi+=1
        if not active:continue
        # Only levels strictly below current M15 high are interacted with.
        cut=bisect.bisect_left(active,(float(bar.high),-10**18,{}))
        if cut<=0:continue
        touched=active[:cut]; active=active[cut:]
        keep=[]
        for level,uid,pr in touched:
            if float(bar.close)>level:
                accepted+=1
            elif float(bar.close)<level:
                d=bar.to_dict(); d.update(pr); d['module']=module; d['res_key']=f'{module}_{uid}'; d['res_level']=level; d['lifecycle']='FAILED_BREAKOUT'
                events.append(d)
            else:
                keep.append((level,uid,pr))
        for item in keep:bisect.insort(active,item)
    # pivots confirmed after last candidate bar count as untouched too.
    untouched=len(active)+(len(piv)-pi)
    ev=pd.DataFrame(events)
    return ev,{'total':len(piv),'failed':len(events),'accepted':accepted,'untouched':untouched}


def trendline_lifecycle(cand,tls):
    if tls.empty:return pd.DataFrame(), {'total':0,'failed':0,'accepted':0,'untouched':0}
    times=cand.time.to_numpy('datetime64[ns]'); H=cand.high.to_numpy(float); C=cand.close.to_numpy(float)
    events=[]; accepted=0; untouched=0
    for r in tls.itertuples(index=False):
        eff=pd.Timestamp(r.effective_time); start=int(np.searchsorted(times,np.datetime64(eff),'left'))
        if start>=len(cand):untouched+=1; continue
        tsec=(cand.time.iloc[start:]-pd.Timestamp(r.tl_p2_time)).dt.total_seconds().to_numpy(float)
        line=float(r.tl_p2_price)+float(r.tl_slope_per_sec)*tsec
        hi=H[start:]; cl=C[start:]
        interact=(cl>line)|((hi>line)&(cl<line))
        hit=np.flatnonzero(interact)
        if not hit.size:untouched+=1; continue
        j=start+int(hit[0]); lev=float(line[int(hit[0])])
        if C[j]>lev:
            accepted+=1; continue
        d=cand.iloc[j].to_dict(); d.update({
            'effective_time':eff,'tl_p1_idx':int(r.tl_p1_idx),'tl_p2_idx':int(r.tl_p2_idx),
            'tl_p1_time':pd.Timestamp(r.tl_p1_time),'tl_p2_time':pd.Timestamp(r.tl_p2_time),
            'tl_p1_price':float(r.tl_p1_price),'tl_p2_price':float(r.tl_p2_price),
            'tl_slope_per_sec':float(r.tl_slope_per_sec),'tl_key':str(r.tl_key),
            'tl_level':lev,'module':'H4_DESC_TRENDLINE','res_key':'TL_'+str(r.tl_key),'res_level':lev,
            'lifecycle':'FAILED_BREAKOUT'})
        events.append(d)
    return pd.DataFrame(events),{'total':len(tls),'failed':len(events),'accepted':accepted,'untouched':untouched}


def detect_acceptance_safe(cand,h1,h4raw):
    h1ps=a.pivot_stream(h1,'h1',2); h4ps=a.pivot_stream(h4raw,'h4',2); tls=a.trendline_stream(h4raw,2)
    e1,s1=horizontal_lifecycle(cand,h1ps,'h1','H1_HORIZONTAL')
    e4,s4=horizontal_lifecycle(cand,h4ps,'h4','H4_HORIZONTAL')
    et,st=trendline_lifecycle(cand,tls)
    parts=[x for x in [e1,e4,et] if len(x)]
    allmod=pd.concat(parts,ignore_index=True,sort=False).sort_values('decision_time') if parts else pd.DataFrame()
    if len(allmod):
        info=allmod.groupby('decision_time').module.apply(lambda s:'+'.join(sorted(set(s)))).rename('module_combo').reset_index()
        comb=allmod.sort_values(['decision_time','module']).drop_duplicates('decision_time',keep='first').drop(columns=['module'],errors='ignore').merge(info,on='decision_time',how='left')
        comb['module']='COMBINED_OR'; comb['res_key']='OR_'+comb.decision_time.astype(str)
    else:comb=allmod.copy()
    audit=pd.DataFrame([
        {'module':'H1_HORIZONTAL',**s1},{'module':'H4_HORIZONTAL',**s4},{'module':'H4_DESC_TRENDLINE',**st}
    ])
    return {'H1_HORIZONTAL':e1,'H4_HORIZONTAL':e4,'H4_DESC_TRENDLINE':et,'COMBINED_OR':comb},audit


def main():
    m1=base.load_zip(M1ZIP); m5=base.load_zip(M5ZIP)
    m1=m1[m1.time>=START].copy(); m5=m5[m5.time>=START-pd.Timedelta(days=90)].copy()
    h1=p4.make_h1(m1); clock=p4.make_clock(m5); m15=p4.make_m15(m5)
    cand=p4.attach_states(m15,h1,clock); cand=cand[cand.decision_time>=START].dropna(subset=['st_dir','st_age','atr14']).copy()
    h4raw=base.resample(m5,'4h')
    mods,audit=detect_acceptance_safe(cand,h1,h4raw); audit.to_csv(OUT/'resistance_lifecycle_audit.csv',index=False)
    for n,e in mods.items():e.to_csv(OUT/f'events_{n}.csv',index=False)
    reps=a.replay_modules(mods,m1,h1)
    for n,r in reps.items():r.to_csv(OUT/f'replay_{n}.csv',index=False)
    layers=a.layer_metrics(reps); layers.to_csv(OUT/'layer_metrics.csv',index=False)

    yearly=[]; buckets=[]; boot=[]
    for name,r in reps.items():
        if not len(r):continue
        pr=r[a.ctx_mask(r)].copy(); pr['year']=pr.decision_time.dt.year
        pr['bucket']=np.select([pr.st_age<=11,pr.st_age<=27,pr.st_age<=58],['B1','B2','B3'],default='B4')
        for y,g in pr.groupby('year'):yearly.append({'module':name,'year':int(y),**a.metric(g,'PRIMARY')})
        for b,g in pr.groupby('bucket'):buckets.append({'module':name,'bucket':b,**a.metric(g,'PRIMARY')})
        for hh in HOLDS:
            q=a.cluster_boot_ev(pr,f'R{hh}',SEED+hh+sum(map(ord,name))); boot.append({'module':name,'hold_h':hh,**q,'EV_pct':float(pr[f'pct{hh}'].mean())})
    Y=pd.DataFrame(yearly); B=pd.DataFrame(buckets); BT=pd.DataFrame(boot)
    Y.to_csv(OUT/'yearly_primary.csv',index=False); B.to_csv(OUT/'market_clock_buckets.csv',index=False); BT.to_csv(OUT/'cluster_bootstrap.csv',index=False)

    comb=reps['COMBINED_OR']; primary=comb[a.ctx_mask(comb)].copy() if len(comb) else comb
    generic=a.build_generic_failed_breakouts(cand)
    cr,pair,ma=a.matched_location_control(primary,generic,m1,h1); cr.to_csv(OUT/'matched_generic_controls.csv',index=False); pair.to_csv(OUT/'location_pairs.csv',index=False); ma.to_csv(OUT/'matching_audit.csv',index=False)
    comp=[]
    for hh in HOLDS:
        d=a.boot_delta(pair,f'delta_R{hh}',SEED+1000+hh); dp=a.boot_delta(pair,f'delta_pct{hh}',SEED+2000+hh)
        comp.append({'hold_h':hh,'N_pairs':len(pair),'event_EV_R':float(pair[f'R{hh}'].mean()) if len(pair) else np.nan,'control_EV_R':float(pair[f'control_R{hh}'].mean()) if len(pair) else np.nan,'delta_R':d['delta'],'CI_R_lo':d['lo'],'CI_R_hi':d['hi'],'P_delta_R_gt0':d['P_gt0'],'event_EV_pct':float(pair[f'pct{hh}'].mean()) if len(pair) else np.nan,'control_EV_pct':float(pair[f'control_pct{hh}'].mean()) if len(pair) else np.nan,'delta_pct':dp['delta'],'CI_pct_lo':dp['lo'],'CI_pct_hi':dp['hi'],'P_delta_pct_gt0':dp['P_gt0']})
    CP=pd.DataFrame(comp); CP.to_csv(OUT/'matched_location_vs_generic.csv',index=False)

    nh=a.next_h4_replay(primary,m1,h1); nh.to_csv(OUT/'next_h4_replay.csv',index=False); NH=pd.DataFrame([a.metric(nh,'NEXT_H4_AFTER_LOCATION_FAILURE')]) if len(nh) else pd.DataFrame(); NH.to_csv(OUT/'next_h4_metrics.csv',index=False)
    census=pd.DataFrame([{'module':n,'events':len(e),'primary_events':int(a.ctx_mask(e).sum()) if len(e) else 0,'primary_episodes':int(e[a.ctx_mask(e)].st_episode_id.nunique()) if len(e) else 0} for n,e in mods.items()]); census.to_csv(OUT/'census.csv',index=False)

    lines=['# SELL_CORE_005B — HTF_RESISTANCE_LOCATION × FAILED_BREAKOUT — ACCEPTANCE-SAFE','',
           '**Correction:** a resistance is retired immediately after any M15 close above it. Only the first unresolved interaction can become a failed breakout. All other SELL_CORE_005 definitions remain frozen.','',
           '## Resistance lifecycle audit','',audit.to_markdown(index=False),'','## Layering','',layers.to_markdown(index=False),'','## Cluster bootstrap — PRIMARY','',BT.to_markdown(index=False) if len(BT) else 'none','','## Yearly PRIMARY','',Y.to_markdown(index=False) if len(Y) else 'none','','## Market-clock diagnostic','',B.to_markdown(index=False) if len(B) else 'none','','## Matched location value vs generic failed breakout','',CP.to_markdown(index=False) if len(CP) else 'none','','## Next-H4 occurrence','',NH.to_markdown(index=False) if len(NH) else 'none','','## Census','',census.to_markdown(index=False),'','## Interpretation','',
           'Promote only if acceptance-safe HTF location produces positive R and price-space EV, transfers across years, and improves versus matched generic failed-breakouts.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
