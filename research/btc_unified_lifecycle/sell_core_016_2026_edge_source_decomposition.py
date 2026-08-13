#!/usr/bin/env python3
"""SELL_CORE_016 — 2026_EDGE_SOURCE_DECOMPOSITION.

Purpose: attribute the exceptional 2026 SELL performance of the frozen B3 x exact LH+BOS
construction. This is NOT a selector search and introduces no new threshold.

Frozen execution: SELL, next M1 open, SL=1.5 x completed H1 ATR14, no TP,
48h primary / 72h sensitivity, $27.5/BTC cost proxy.

Source ladder:
A GLOBAL_H4_CLOCK       every canonical H4 clock
B H4_BEAR               canonical H4 ST DOWN
C B3                     H4 ST DOWN, age 27..50
D LH_BOS                 exact user LR=2 LH+BOS on original hourly :20 grid
E B3_X_LH_BOS            D inside C

Exact timing decomposition for E uses FIRST E per H4 ST episode:
- ACTUAL: exact LH+BOS timestamp.
- SAME_AGE_OTHER_CLOCKS: all other original :20 hourly clocks in the same H4 ST episode
  and exact same H4 ST age. This holds occurrence episode and market-clock age fixed.
- B3_ONSET_SAME_EPISODE: first B3 clock in that same ST episode (future-defined episode
  membership; descriptive source attribution only, never a causal entry rule).
- OCCURRENCE vs NON_OCCURRENCE B3 onset: asks whether episodes that will later contain
  LH+BOS were already special at B3 onset. Future-conditioned and descriptive only.

Primary focus years 2024/2025/2026; 2020-2023 retained as long-history diagnostics.
Inference clusters/resamples by H4 ST episode. P/L never selects a threshold.
"""
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path('sell_core_016_out'); OUT.mkdir(exist_ok=True)
COST_USD=27.5; HOLDS=(48,72); BOOT=20000; SEED=416016


def load014():
    p=Path('sell_core_014_b3_lhbos_long_history.py'); s=p.read_text()
    bad="prim=S[(S.phase_min==20)&(((S.view=='NATIVE')&(S.hold_h==48))|((S.view=='CANONICAL')&(S.hold_h.isin([48,72])))]"
    good="prim=S[(S.phase_min==20)&(((S.view=='NATIVE')&(S.hold_h==48))|((S.view=='CANONICAL')&(S.hold_h.isin([48,72]))))]"
    if bad in s: s=s.replace(bad,good,1)
    ns={'__name__':'sell014','__file__':str(p)}; exec(compile(s,str(p),'exec'),ns); return ns


def pf(z):
    x=np.asarray(pd.Series(z).dropna(),float); gp=x[x>0].sum(); gl=-x[x<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def generic_replay(events,m1,H,h1):
    if len(events)==0:return pd.DataFrame()
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float)
    hct=h1.close_time.to_numpy('datetime64[ns]'); HA=h1.atr14.to_numpy(float)
    rows=[]
    for r in events.sort_values('time').itertuples(index=False):
        sig=pd.Timestamp(r.time); j=int(np.searchsorted(mt,np.datetime64(sig),'right'))
        q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1)
        if j>=len(O) or q<0 or not np.isfinite(HA[q]) or HA[q]<=0: continue
        entry=float(O[j]); sd=1.5*float(HA[q]); sl=entry+sd; d=r._asdict()
        d.update(entry_time=pd.Timestamp(m1.time.iloc[j]),entry=entry,stop_dist=sd)
        for hh in HOLDS:
            te=sig+pd.Timedelta(hours=hh); je=int(np.searchsorted(mt,np.datetime64(te),'left'))
            if je<=j or je>=len(O): d[f'R{hh}']=np.nan; d[f'pct{hh}']=np.nan; d[f'exit{hh}']='NA'; continue
            hit=np.flatnonzero(H[j:je]>=sl)
            if hit.size:
                rr=-1-COST_USD/sd; px=-(sd/entry*100)-COST_USD/entry*100; ex='SL'
            else:
                xp=float(O[je]); rr=(entry-xp)/sd-COST_USD/sd; px=(entry-xp)/entry*100-COST_USD/entry*100; ex='TIME'
            d[f'R{hh}']=rr; d[f'pct{hh}']=px; d[f'exit{hh}']=ex
        rows.append(d)
    return pd.DataFrame(rows)


def metrics(g,label,year=None):
    r={'source':label,'year':year if year is not None else 'ALL','N':len(g),
       'episodes':int(g.episode_id.nunique()) if len(g) and 'episode_id' in g else np.nan}
    for hh in HOLDS:
        z=g[f'R{hh}'].dropna() if len(g) else pd.Series(dtype=float)
        r.update({f'EV_R{hh}':float(z.mean()) if len(z) else np.nan,f'PF{hh}':pf(z),
                  f'EV_pct{hh}':float(g[f'pct{hh}'].mean()) if len(g) else np.nan,
                  f'SL_rate{hh}':float((g[f'exit{hh}']=='SL').mean()) if len(g) else np.nan})
    return r


def episode_boot_mean(g,col,seed):
    z=g.dropna(subset=[col]).copy();
    if len(z)==0:return {'CI_lo':np.nan,'CI_hi':np.nan,'P_gt0':np.nan}
    a=z.groupby('episode_id')[col].agg(['sum','count']).to_numpy(float)
    if len(a)<3:return {'CI_lo':np.nan,'CI_hi':np.nan,'P_gt0':np.nan}
    rng=np.random.default_rng(seed); idx=rng.integers(0,len(a),size=(BOOT,len(a))); s=a[idx].sum(axis=1); v=s[:,0]/s[:,1]
    return {'CI_lo':float(np.quantile(v,.025)),'CI_hi':float(np.quantile(v,.975)),'P_gt0':float((v>0).mean())}


def paired_boot(actual,control_mean,col,seed):
    p=actual[['episode_id',col]].merge(control_mean[['episode_id',col]],on='episode_id',suffixes=('_actual','_ctrl'))
    if len(p)<3:return p,{'N':len(p),'delta':np.nan,'CI_lo':np.nan,'CI_hi':np.nan,'P_gt0':np.nan}
    d=(p[f'{col}_actual']-p[f'{col}_ctrl']).to_numpy(float); rng=np.random.default_rng(seed)
    v=rng.choice(d,size=(BOOT,len(d)),replace=True).mean(axis=1)
    return p,{'N':len(p),'delta':float(d.mean()),'CI_lo':float(np.quantile(v,.025)),'CI_hi':float(np.quantile(v,.975)),'P_gt0':float((v>0).mean())}


def make_h4_clock(h4):
    x=h4.copy().dropna(subset=['st_dir','st_age']).sort_values('time')
    x['st_dir']=x.st_dir.astype(int); x['st_age']=x.st_age.astype(int)
    if 'episode_id' not in x:
        x['episode_id']=(x.st_dir.ne(x.st_dir.shift())|((x.time-x.time.shift())>pd.Timedelta(hours=4,minutes=1))).cumsum().astype(int)
    x['year']=pd.to_datetime(x.time).dt.year
    return x


def main():
    mod=load014(); m1,m5,start,npre,nfr=mod['load_long'](); H,L,C,a60,labels,h4,h1=mod['prep'](m1,m5)
    # Original user hourly grid: START_WARMUP=20000 means mod phase=0 is minute :20.
    hourly=mod['clocks'](m1,labels,h4,0).copy(); hourly['year']=pd.to_datetime(hourly.time).dt.year
    h4c=make_h4_clock(h4)

    # Source populations. H4 rows already carry causal BAR_OPEN lag1 state from prep().
    pops={
      'A_GLOBAL_H4_CLOCK':h4c,
      'B_H4_BEAR':h4c[h4c.st_dir.eq(-1)],
      'C_B3':h4c[h4c.st_dir.eq(-1)&h4c.st_age.between(27,50)],
      'D_LH_BOS':hourly[hourly.lhbos],
      'E_B3_X_LH_BOS':hourly[hourly.intersection],
    }
    ledgers={}; summary=[]; yearly=[]; boots=[]
    for lab,e in pops.items():
        tr=generic_replay(e,m1,H,h1); tr['source']=lab; ledgers[lab]=tr
        tr.to_csv(OUT/f'{lab}.csv',index=False); summary.append(metrics(tr,lab))
        for y,g in tr.groupby('year'): yearly.append(metrics(g,lab,int(y)))
        for hh in HOLDS:
            b=episode_boot_mean(tr,f'R{hh}',SEED+hh+len(lab)); b.update(source=lab,hold_h=hh,N=len(tr),episodes=tr.episode_id.nunique()); boots.append(b)

    # FIRST exact E per continuous H4 ST episode.
    E=ledgers['E_B3_X_LH_BOS'].sort_values('time').groupby('episode_id',as_index=False).first()
    E.to_csv(OUT/'E_FIRST_PER_EPISODE.csv',index=False)
    # Same exact H4 age, same episode, other hourly :20 clocks. Exclude actual timestamp.
    controls=[]
    onset=[]
    for r in E.itertuples(index=False):
        cand=hourly[(hourly.episode_id==r.episode_id)&(hourly.st_age==r.st_age)&(hourly.time!=r.time)].copy()
        if len(cand): controls.append(cand)
        b3ep=hourly[(hourly.episode_id==r.episode_id)&hourly.b3].sort_values('time')
        if len(b3ep): onset.append(b3ep.iloc[[0]])
    CTRL_EVENTS=pd.concat(controls,ignore_index=True) if controls else pd.DataFrame()
    ONSET_EVENTS=pd.concat(onset,ignore_index=True) if onset else pd.DataFrame()
    CTRL=generic_replay(CTRL_EVENTS,m1,H,h1) if len(CTRL_EVENTS) else pd.DataFrame()
    ONSET=generic_replay(ONSET_EVENTS,m1,H,h1) if len(ONSET_EVENTS) else pd.DataFrame()
    CTRL.to_csv(OUT/'same_age_other_clocks.csv',index=False); ONSET.to_csv(OUT/'b3_onset_same_occurrence_episode.csv',index=False)

    timing_rows=[]
    for y in sorted(E.year.unique()):
        a=E[E.year==y].copy(); c=CTRL[CTRL.year==y].copy() if len(CTRL) else pd.DataFrame(); o=ONSET[ONSET.year==y].copy() if len(ONSET) else pd.DataFrame()
        for hh in HOLDS:
            cm=c.groupby('episode_id',as_index=False)[f'R{hh}'].mean() if len(c) else pd.DataFrame(columns=['episode_id',f'R{hh}'])
            _,st=paired_boot(a,cm,f'R{hh}',SEED+y+hh); st.update(year=int(y),comparison='ACTUAL_MINUS_SAME_AGE_OTHER_CLOCKS',hold_h=hh); timing_rows.append(st)
            om=o[['episode_id',f'R{hh}']] if len(o) else pd.DataFrame(columns=['episode_id',f'R{hh}'])
            _,so=paired_boot(a,om,f'R{hh}',SEED+500+y+hh); so.update(year=int(y),comparison='ACTUAL_MINUS_B3_ONSET_SAME_EPISODE',hold_h=hh); timing_rows.append(so)
    # 2024-26 pooled exact-timing test and all-history diagnostic.
    for tag,yrs in [('RECENT_2024_2026',[2024,2025,2026]),('ALL_2020_2026',sorted(E.year.unique()))]:
        a=E[E.year.isin(yrs)].copy(); c=CTRL[CTRL.year.isin(yrs)].copy(); o=ONSET[ONSET.year.isin(yrs)].copy()
        for hh in HOLDS:
            cm=c.groupby('episode_id',as_index=False)[f'R{hh}'].mean(); _,st=paired_boot(a,cm,f'R{hh}',SEED+1000+hh); st.update(year=tag,comparison='ACTUAL_MINUS_SAME_AGE_OTHER_CLOCKS',hold_h=hh); timing_rows.append(st)
            om=o[['episode_id',f'R{hh}']]; _,so=paired_boot(a,om,f'R{hh}',SEED+1500+hh); so.update(year=tag,comparison='ACTUAL_MINUS_B3_ONSET_SAME_EPISODE',hold_h=hh); timing_rows.append(so)
    TIM=pd.DataFrame(timing_rows); TIM.to_csv(OUT/'timing_decomposition.csv',index=False)

    # Future-conditioned occurrence attribution at B3 onset: occurrence episodes vs all other B3 episodes.
    # This cannot be a trading rule; it only tells where source value lives.
    b3first=h4c[h4c.st_dir.eq(-1)&h4c.st_age.between(27,50)].sort_values('time').groupby('episode_id',as_index=False).first()
    b3first['occurrence_episode']=b3first.episode_id.isin(set(E.episode_id)).astype(int)
    B3ON=generic_replay(b3first,m1,H,h1); B3ON['occurrence_episode']=B3ON.episode_id.isin(set(E.episode_id)).astype(int)
    B3ON.to_csv(OUT/'b3_onset_all_episodes_occurrence_flag.csv',index=False)
    occ=[]
    for y,g in B3ON.groupby('year'):
        for flag,gg in g.groupby('occurrence_episode'):
            r=metrics(gg,'B3_ONSET_OCCURRENCE' if flag else 'B3_ONSET_NON_OCCURRENCE',int(y)); occ.append(r)
    for flag,gg in B3ON[B3ON.year.isin([2024,2025,2026])].groupby('occurrence_episode'):
        occ.append(metrics(gg,'B3_ONSET_OCCURRENCE' if flag else 'B3_ONSET_NON_OCCURRENCE','RECENT_2024_2026'))
    OCC=pd.DataFrame(occ); OCC.to_csv(OUT/'occurrence_source_attribution.csv',index=False)

    S=pd.DataFrame(summary); Y=pd.DataFrame(yearly); B=pd.DataFrame(boots)
    S.to_csv(OUT/'source_ladder_summary.csv',index=False); Y.to_csv(OUT/'source_ladder_yearly.csv',index=False); B.to_csv(OUT/'source_ladder_bootstrap.csv',index=False)

    # Compact report, preserving the supplied H2 benchmark without inventing its missing implementation.
    recent=Y[Y.year.isin([2024,2025,2026])]
    t48=TIM[TIM.hold_h.eq(48)]
    lines=['# SELL_CORE_016 — 2026_EDGE_SOURCE_DECOMPOSITION','',
      '## Frozen question','',
      'Where does the 2026 B3×LH+BOS SELL edge live: global short drift, H4 bear state, B3, LH+BOS occurrence, or exact LH+BOS timing?','',
      '## Source ladder — full history','',S.to_markdown(index=False),'',
      '## Source ladder — 2024/2025/2026','',recent.to_markdown(index=False),'',
      '## Exact timing attribution — 48h','',t48.to_markdown(index=False),'',
      '## Future-conditioned occurrence attribution at B3 onset (descriptive only)','',OCC.to_markdown(index=False),'',
      '## Interpretation rules','',
      '- If E is strong but SAME_AGE other clocks in the same episode/age are similarly strong, exact LH+BOS timing is not the source.',
      '- If B3 onset is already strong specifically in episodes that later contain LH+BOS, value is episode occurrence/selection rather than timestamp.',
      '- If A/B/C are already strongly positive in 2026, part of E is broad regime drift.',
      '- Future-conditioned occurrence groups are source attribution only and cannot be promoted as causal entries.','',
      '## External benchmark supplied by user','',
      '- `H2 age<=2`: EV +0.073%, 2/3 years, ~12/week. Exact historical detector implementation was not found in ResearchOS, so SELL_CORE_016 does **not** reconstruct or retest it.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
