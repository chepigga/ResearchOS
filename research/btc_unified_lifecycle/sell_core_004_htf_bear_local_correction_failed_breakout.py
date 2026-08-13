#!/usr/bin/env python3
"""SELL_CORE_004 — HTF_BEAR_TREND x LOCAL_BULL_CORRECTION x FAILED_BREAKOUT.

Preregistered from user's visual model before outcomes:
1) HTF_BEAR_TREND = canonical H4 Supertrend ATR10 x3 DOWN, U05 BAR_OPEN lag1.
2) LOCAL_BULL_CORRECTION at M15 decision close = last completed H1 has:
     close > EMA20, EMA20 > EMA20 4 completed H1 bars ago, close > close 4 completed H1 bars ago.
   Four H1 bars = one H4 block; no threshold grid.
3) FAILED_BREAKOUT = an M15 bar trades above the last causally confirmed M15 swing high
   (pivot strength=2) and closes back below that swing level on the same M15 bar.
   The pivot must have been confirmed before the breakout bar begins. One event per swept pivot.
4) Entry = next M1 open after M15 close. SELL only.
5) Common outcomes = SL 1.5 x completed H1 ATR14; no TP; 48h primary / 72h sensitivity;
   $27.5/BTC cost proxy.
6) Timing null = for each HTF_BEAR+CORRECTION failed-breakout event, match 5 non-event M15
   decision times from same calendar year + exact H4 ST age + same correction state, nearest H1 ATR%.
   Compare exact event timing vs matched same-state times; cluster bootstrap by continuous H4 ST episode.
7) Occurrence diagnostic = delay execution to next fixed H4 boundary after the event and replay same outcome.
8) Market-clock decomposition reported without using age to select the primary pattern. Frozen SELL_B3 27..50 is diagnostic.

Price window is frozen unified Binance 2024-01-01 through 2026-08-10.
"""
from pathlib import Path
import json, zipfile
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base

M1ZIP='btc_1m.zip'; M5ZIP='btc_5m.zip'; OUT=Path('sell_core_004_out'); OUT.mkdir(exist_ok=True)
START=pd.Timestamp('2024-01-01'); COST_USD=27.5; STOP_ATR=1.5; HOLDS=(48,72); BOOT=20000; SEED=404004


def pf(x):
    z=pd.Series(x).dropna(); gp=z[z>0].sum(); gl=-z[z<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def ema(s,n): return s.ewm(span=n,adjust=False,min_periods=n).mean()


def make_h1(m1):
    h=base.resample(m1,'1h')
    pc=h.close.shift(1); tr=pd.concat([h.high-h.low,(h.high-pc).abs(),(h.low-pc).abs()],axis=1).max(axis=1)
    h['atr14']=base.wilder(tr,14); h['ema20']=ema(h.close,20)
    h['corr']=(h.close>h.ema20)&(h.ema20>h.ema20.shift(4))&(h.close>h.close.shift(4))
    h['atr_pct']=h.atr14/h.close*100.0
    return h


def make_clock(m5):
    h4=base.h4_supertrend(m5)
    hs=h4[['time','st_dir','st_age','st_dist_atr']].copy()
    for c in ['st_dir','st_age','st_dist_atr']: hs[c]=hs[c].shift(1)
    hs=hs.dropna(subset=['st_dir']).copy(); hs['st_dir']=hs.st_dir.astype(int); hs['st_age']=hs.st_age.astype(int)
    hs['bucket']=np.select([hs.st_age<=11,hs.st_age<=27,hs.st_age<=58],['B1','B2','B3'],default='B4')
    prev_t=hs.time.shift(); prev_d=hs.st_dir.shift()
    new=(prev_t.isna())|(hs.st_dir.ne(prev_d))|((hs.time-prev_t)>pd.Timedelta(hours=4,minutes=1))
    hs['st_episode_id']=new.cumsum().astype(int)
    return hs


def make_m15(m5):
    return base.resample(m5,'15min')


def attach_states(m15,h1,clock):
    x=m15.copy().sort_values('time'); x['decision_time']=x.close_time
    # H4 BAR_OPEN lag1 state as known at decision time.
    c=clock.sort_values('time')
    x=pd.merge_asof(x.sort_values('decision_time'),c,left_on='decision_time',right_on='time',direction='backward',suffixes=('','_h4'))
    # H1 state: only rows whose close_time <= decision time.
    hh=h1[['close_time','close','ema20','atr14','atr_pct','corr']].rename(columns={'close':'h1_close','close_time':'h1_close_time'}).sort_values('h1_close_time')
    x=pd.merge_asof(x.sort_values('decision_time'),hh,left_on='decision_time',right_on='h1_close_time',direction='backward')
    return x


def add_last_confirmed_pivot(x,strength=2):
    z=x.copy().reset_index(drop=True); H=z.high.to_numpy(float); n=len(z)
    piv=[]
    for p in range(strength,n-strength):
        # strict against left, >= against right to avoid duplicate flat highs.
        if H[p]>np.max(H[p-strength:p]) and H[p]>=np.max(H[p+1:p+strength+1]):
            confirm_idx=p+strength+1  # first bar whose OPEN occurs after pivot is fully confirmed
            if confirm_idx<n: piv.append((confirm_idx,p,float(H[p]),z.time.iloc[p]))
    by_confirm={}
    for ci,p,price,pt in piv: by_confirm.setdefault(ci,[]).append((p,price,pt))
    last_price=np.nan; last_p=-1; last_time=pd.NaT
    lp=[]; li=[]; lt=[]
    for i in range(n):
        if i in by_confirm:
            # most recent pivot confirmed at this bar open
            p,price,pt=max(by_confirm[i],key=lambda a:a[0]); last_p=p; last_price=price; last_time=pt
        lp.append(last_price); li.append(last_p); lt.append(last_time)
    z['swing_high']=lp; z['swing_idx']=li; z['swing_time']=lt
    return z


def detect_events(x):
    z=add_last_confirmed_pivot(x,2)
    z['failed_breakout']=(z.swing_high.notna())&(z.high>z.swing_high)&(z.close<z.swing_high)
    # one event per pivot; keep first causal sweep/reclaim only.
    ev=z[z.failed_breakout].copy().sort_values('decision_time')
    ev=ev.drop_duplicates(subset=['swing_idx'],keep='first')
    return z,ev


def replay(rows,m1,h1,signal_col='decision_time',label='EXACT'):
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float); C=m1.close.to_numpy(float)
    hct=h1.close_time.to_numpy('datetime64[ns]'); HA=h1.atr14.to_numpy(float)
    out=[]
    for r in rows.itertuples(index=False):
        sig=pd.Timestamp(getattr(r,signal_col)); j=int(np.searchsorted(mt,np.datetime64(sig),'left'))
        q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1)
        if j>=len(O) or q<0 or not np.isfinite(HA[q]) or HA[q]<=0: continue
        entry=float(O[j]); sd=STOP_ATR*float(HA[q]); sl=entry+sd; d=r._asdict(); d.update(exec_label=label,signal_time=sig,entry_time=pd.Timestamp(mt[j]),entry=entry,stop_dist=sd,atr_h1=float(HA[q]))
        for hh in HOLDS:
            te=sig+pd.Timedelta(hours=hh); je=int(np.searchsorted(mt,np.datetime64(te),'left'))
            if je<=j or je>=len(O):
                d[f'R{hh}']=np.nan; d[f'pct{hh}']=np.nan; d[f'exit{hh}']='NA'; continue
            hit=np.flatnonzero(H[j:je]>=sl)
            if hit.size:
                rr=-1.0-COST_USD/sd; pct=-(sd/entry*100.0)-COST_USD/entry*100.0; ex='SL'
            else:
                ep=float(O[je]); rr=(entry-ep)/sd-COST_USD/sd; pct=(entry-ep)/entry*100.0-COST_USD/entry*100.0; ex='TIME'
            d[f'R{hh}']=rr; d[f'pct{hh}']=pct; d[f'exit{hh}']=ex
        out.append(d)
    return pd.DataFrame(out)


def metrics(g,name):
    row={'branch':name,'N':len(g),'episodes':g.st_episode_id.nunique() if 'st_episode_id' in g else np.nan}
    for hh in HOLDS:
        z=g[f'R{hh}'].dropna(); row.update({f'EV_R{hh}':float(z.mean()) if len(z) else np.nan,f'PF{hh}':pf(z),f'WR{hh}':float((z>0).mean()) if len(z) else np.nan,f'EV_pct{hh}':float(g[f'pct{hh}'].mean()) if len(g) else np.nan,f'SL_rate{hh}':float((g[f'exit{hh}']=='SL').mean()) if len(g) else np.nan})
    return row


def layer_table(ev_replayed):
    sets=[('FAILED_BREAKOUT_ANY',np.ones(len(ev_replayed),bool)),('FAILED_BREAKOUT_HTF_BEAR',ev_replayed.st_dir.eq(-1).to_numpy()),('HTF_BEAR_LOCAL_CORR_FAILED_BREAKOUT',(ev_replayed.st_dir.eq(-1)&ev_replayed['corr'].fillna(False)).to_numpy()),('PRIMARY_PLUS_SELL_B3_27_50',(ev_replayed.st_dir.eq(-1)&ev_replayed['corr'].fillna(False)&ev_replayed.st_age.between(27,50)).to_numpy())]
    return pd.DataFrame([metrics(ev_replayed[m],n) for n,m in sets])


def bootstrap_ev(g,col='R48',seed=SEED):
    z=g[['st_episode_id',col]].dropna(); ids=z.st_episode_id.unique()
    if len(ids)<5:return (np.nan,np.nan,np.nan)
    sums=z.groupby('st_episode_id')[col].agg(['sum','count']); arr=sums.to_numpy(float); rng=np.random.default_rng(seed); vals=[]
    for _ in range(BOOT):
        s=arr[rng.integers(0,len(arr),len(arr))].sum(axis=0); vals.append(s[0]/s[1])
    v=np.asarray(vals); return float(np.quantile(v,.025)),float(np.quantile(v,.975)),float((v>0).mean())


def matched_timing_null(primary,candidates,m1,h1):
    # Non-event candidate decisions in same year + exact ST age + HTF bear + correction; nearest H1 ATR%.
    pool=candidates[(candidates.st_dir==-1)&candidates['corr'].fillna(False)&(~candidates.failed_breakout)].copy()
    pool['year']=pool.decision_time.dt.year; primary=primary.copy(); primary['year']=primary.decision_time.dt.year
    controls=[]; match_rows=[]
    for i,r in primary.iterrows():
        p=pool[(pool.year==r.year)&(pool.st_age==r.st_age)].copy()
        if len(p)<1: continue
        p['dist']=(p.atr_pct-r.atr_pct).abs(); p=p.sort_values(['dist','decision_time']).head(5)
        for _,q in p.iterrows():
            d=q.to_dict(); d['matched_event_key']=int(i); controls.append(d)
        match_rows.append({'event_key':int(i),'riskset_N':len(pool[(pool.year==r.year)&(pool.st_age==r.st_age)]),'K':len(p)})
    ctrl=pd.DataFrame(controls)
    if ctrl.empty:return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    cr=replay(ctrl,m1,h1,'decision_time','MATCHED_CONTROL')
    er=primary.copy(); er['event_key']=er.index.astype(int)
    # event replays already include outcomes; pair by event key and mean matched controls.
    cr['event_key']=cr.matched_event_key.astype(int)
    means=cr.groupby('event_key').agg(control_R48=('R48','mean'),control_pct48=('pct48','mean'),control_R72=('R72','mean'),control_pct72=('pct72','mean')).reset_index()
    pair=er.merge(means,on='event_key',how='inner')
    for hh in HOLDS:
        pair[f'delta_R{hh}']=pair[f'R{hh}']-pair[f'control_R{hh}']; pair[f'delta_pct{hh}']=pair[f'pct{hh}']-pair[f'control_pct{hh}']
    return cr,pair,pd.DataFrame(match_rows)


def bootstrap_delta(pair,col,seed):
    z=pair[['st_episode_id',col]].dropna(); ids=z.st_episode_id.unique()
    if len(ids)<5:return {'mean':np.nan,'lo':np.nan,'hi':np.nan,'P_gt0':np.nan}
    a=z.groupby('st_episode_id')[col].agg(['sum','count']).to_numpy(float); obs=float(z[col].mean()); rng=np.random.default_rng(seed); vals=[]
    for _ in range(BOOT):
        s=a[rng.integers(0,len(a),len(a))].sum(axis=0); vals.append(s[0]/s[1])
    v=np.asarray(vals); return {'mean':obs,'lo':float(np.quantile(v,.025)),'hi':float(np.quantile(v,.975)),'P_gt0':float((v>0).mean())}


def next_h4_times(x):
    z=x.copy(); z['next_h4_time']=z.decision_time.dt.floor('4h')+pd.Timedelta(hours=4); return z


def main():
    m1=base.load_zip(M1ZIP); m5=base.load_zip(M5ZIP); m1=m1[m1.time>=START].copy(); m5=m5[m5.time>=START-pd.Timedelta(days=60)].copy()
    h1=make_h1(m1); clock=make_clock(m5); m15=make_m15(m5); cand=attach_states(m15,h1,clock); cand=cand[cand.decision_time>=START].dropna(subset=['st_dir','st_age','atr14']).copy()
    cand,events=detect_events(cand); cand.to_csv(OUT/'m15_candidate_state.csv',index=False); events.to_csv(OUT/'failed_breakout_events_detected.csv',index=False)
    er=replay(events,m1,h1,'decision_time','EXACT_FAILED_BREAKOUT'); er.to_csv(OUT/'failed_breakout_exact_replay.csv',index=False)
    layers=layer_table(er); layers.to_csv(OUT/'layer_metrics.csv',index=False)
    # Yearly primary.
    primary=er[(er.st_dir==-1)&er['corr'].fillna(False)].copy(); primary['year']=primary.decision_time.dt.year
    yr=[]
    for y,g in primary.groupby('year'): yr.append({'year':int(y),**metrics(g,'PRIMARY')})
    pd.DataFrame(yr).to_csv(OUT/'yearly_primary.csv',index=False)
    # Bucket decomposition.
    primary['bucket']=np.select([primary.st_age<=11,primary.st_age<=27,primary.st_age<=58],['B1','B2','B3'],default='B4')
    buckets=pd.DataFrame([{'bucket':b,**metrics(g,'PRIMARY')} for b,g in primary.groupby('bucket')]); buckets.to_csv(OUT/'market_clock_buckets.csv',index=False)
    # Cluster bootstrap raw EV.
    ci=[]
    for hh in HOLDS:
        lo,hi,p=bootstrap_ev(primary,f'R{hh}',SEED+hh); ci.append({'hold_h':hh,'EV_R':primary[f'R{hh}'].mean(),'CI_lo':lo,'CI_hi':hi,'P_EV_gt0':p,'EV_pct':primary[f'pct{hh}'].mean()})
    pd.DataFrame(ci).to_csv(OUT/'primary_cluster_bootstrap.csv',index=False)
    # Timing null.
    cr,pair,match=matched_timing_null(primary,cand,m1,h1); cr.to_csv(OUT/'matched_controls.csv',index=False); pair.to_csv(OUT/'timing_pairs.csv',index=False); match.to_csv(OUT/'matching_audit.csv',index=False)
    td=[]
    if len(pair):
        for hh in HOLDS:
            a=bootstrap_delta(pair,f'delta_R{hh}',SEED+100+hh); b=bootstrap_delta(pair,f'delta_pct{hh}',SEED+200+hh); td.append({'hold_h':hh,'N_pairs':len(pair),'event_EV_R':pair[f'R{hh}'].mean(),'control_EV_R':pair[f'control_R{hh}'].mean(),'delta_R':a['mean'],'CI_R_lo':a['lo'],'CI_R_hi':a['hi'],'P_delta_R_gt0':a['P_gt0'],'event_EV_pct':pair[f'pct{hh}'].mean(),'control_EV_pct':pair[f'control_pct{hh}'].mean(),'delta_pct':b['mean'],'CI_pct_lo':b['lo'],'CI_pct_hi':b['hi'],'P_delta_pct_gt0':b['P_gt0']})
    TD=pd.DataFrame(td); TD.to_csv(OUT/'same_state_timing_null.csv',index=False)
    # Coarse occurrence: next fixed H4 execution after primary event.
    nh=next_h4_times(primary); nr=replay(nh,m1,h1,'next_h4_time','NEXT_H4_AFTER_OCCURRENCE'); nr.to_csv(OUT/'next_h4_occurrence_replay.csv',index=False)
    nextmet=pd.DataFrame([metrics(nr,'NEXT_H4_AFTER_OCCURRENCE')]); nextmet.to_csv(OUT/'next_h4_metrics.csv',index=False)
    # Descriptive geometry.
    geom=pd.DataFrame({'N_events':[len(events)],'N_htf_bear':[int((events.st_dir==-1).sum())],'N_htf_bear_corr':[int(((events.st_dir==-1)&events['corr'].fillna(False)).sum())],'median_sweep_pct':[float(((events.high-events.swing_high)/events.swing_high*100).median())],'median_h4_age_primary':[float(primary.st_age.median()) if len(primary) else np.nan]})
    geom.to_csv(OUT/'census.csv',index=False)
    report=['# SELL_CORE_004 — HTF_BEAR_TREND × LOCAL_BULL_CORRECTION × FAILED_BREAKOUT','',
    '**Visual hypothesis formalized before outcomes:** global H4 bearish regime → local H1 bullish correction → M15 sweep of a known swing high with same-bar close back below.','',
    '## Layering','',layers.to_markdown(index=False),'','## Primary yearly', '',pd.DataFrame(yr).to_markdown(index=False),'','## Market-clock decomposition','',buckets.to_markdown(index=False),'','## Primary cluster bootstrap','',pd.DataFrame(ci).to_markdown(index=False),'','## Same-state timing null','',TD.to_markdown(index=False) if len(TD) else 'No matched pairs.','','## Next-H4 occurrence diagnostic','',nextmet.to_markdown(index=False),'','## Census','',geom.to_markdown(index=False),'',
    '### Interpretation rule','',
    'The visual mechanism is promoted only if adding HTF bear + local correction improves the failed-breakout population, the primary event is positive across years with usable N, and either exact timing beats same-state controls or the next-H4 occurrence replay shows that the event is a useful episode selector. B3 is diagnostic, not required by construction.']
    (OUT/'REPORT.md').write_text('\n'.join(report))
    print('\n'.join(report))

if __name__=='__main__': main()
