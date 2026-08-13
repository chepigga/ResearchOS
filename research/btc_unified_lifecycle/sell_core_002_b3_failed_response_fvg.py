#!/usr/bin/env python3
"""SELL_CORE_002 — B3 × M15 FAILED_BULL_RESPONSE × FVG LOCATION.

Frozen before outcomes:
- SELL_B3 market-clock = H4 ST ATR10x3 BAR_OPEN lag1, age 27..50.
- Failed bull response source is the already-frozen LAB015 ledger; no new response detector.
- Primary response opportunity = first unique LAB015 trigger/entry inside each SELL_B3 episode.
- FVG location = during that LAB015 recovery sequence [breakdown_time, trigger_time],
  price first-touched a classical bearish M15 FVG aged 11..60 bars.
- Common outcome: SELL, SL=1.5×completed H1 ATR14, NO TP, 48h time exit,
  $27.5/BTC cost proxy, entry repriced to canonical frozen M1.
- Layering: B3 onset -> B3+FVG only -> B3+failed response -> B3+failed response+FVG.
- Trigger families F1/F2/F3 are descriptive only; no post-hoc family selection.
"""
from pathlib import Path
import json, zipfile
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base

OUT=Path('sell_core_002_out'); OUT.mkdir(exist_ok=True)
COST=27.5; STOP=1.5; EXIT_H=48; BOOT=20000; SEED=402002


def pf(x):
    z=pd.Series(x).dropna(); gp=z[z>0].sum(); gl=-z[z<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def resample_m15(m5):
    x=m5.set_index('time')
    y=x.resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
    return y


def build_clock(m5):
    h4=base.h4_supertrend(m5)
    c=h4[['time','st_dir','st_age','st_dist_atr']].copy()
    for col in ['st_dir','st_age','st_dist_atr']: c[col]=c[col].shift(1)
    c=c.dropna(subset=['st_dir','st_age']).copy(); c['st_dir']=c.st_dir.astype(int); c['st_age']=c.st_age.astype(int)
    c['sell_b3']=((c.st_age>=27)&(c.st_age<=50)).astype(int)
    prev=c.sell_b3.shift(fill_value=0); prevdir=c.st_dir.shift(); prevt=c.time.shift()
    new=((c.sell_b3==1)&((prev!=1)|(c.st_dir!=prevdir)|((c.time-prevt)>pd.Timedelta(hours=4,minutes=1))))
    eid=np.zeros(len(c),int); cur=0
    for i in range(len(c)):
        if c.sell_b3.iloc[i]==1:
            if bool(new.iloc[i]): cur+=1
            eid[i]=cur
    c['b3_episode_id']=eid
    return c


def bearish_fvg_touches(m15):
    bear=(m15.high < m15.low.shift(2)).to_numpy(); out=[]; n=len(m15)
    H=m15.high.to_numpy(float)
    for j in np.flatnonzero(bear):
        lower=float(m15.high.iloc[j]); upper=float(m15.low.iloc[j-2])
        k0=j+2; k1=min(j+200,n-1)
        if k0>k1: continue
        hit=np.flatnonzero(H[k0:k1+1]>=lower)
        if not hit.size: continue
        k=k0+int(hit[0]); age=k-j
        out.append({'fvg_birth_time':m15.time.iloc[j],'fvg_touch_time':m15.time.iloc[k],
                    'fvg_age_bars':age,'fvg_lower':lower,'fvg_upper':upper})
    return pd.DataFrame(out)


def attach_clock(events,clock,timecol):
    z=pd.merge_asof(events.sort_values(timecol),clock.sort_values('time'),left_on=timecol,right_on='time',direction='backward',allow_exact_matches=True)
    return z


def replay(rows,m1,h1,timecol='signal_time'):
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float)
    hct=h1.close_time.to_numpy('datetime64[ns]'); HA=h1.atr14.to_numpy(float)
    out=[]
    for r in rows.itertuples(index=False):
        sig=pd.Timestamp(getattr(r,timecol)); requested=pd.Timestamp(getattr(r,'requested_entry_time',sig))
        j=int(np.searchsorted(mt,np.datetime64(requested),'left')); q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1)
        if j>=len(O) or q<0 or not np.isfinite(HA[q]) or HA[q]<=0: continue
        tend=sig+pd.Timedelta(hours=EXIT_H); je=int(np.searchsorted(mt,np.datetime64(tend),'left'))
        if je<=j or je>=len(O): continue
        entry=float(O[j]); sd=STOP*float(HA[q]); sl=entry+sd
        hit=np.flatnonzero(H[j:je]>=sl)
        if hit.size:
            rr=-1-COST/sd; pct=-(sd/entry*100)-COST/entry*100; ex='SL'; exitp=sl
        else:
            exitp=float(O[je]); rr=(entry-exitp)/sd-COST/sd; pct=(entry-exitp)/entry*100-COST/entry*100; ex='TIME'
        d=r._asdict(); d.update(entry_time=m1.time.iloc[j],entry_price_repriced=entry,atr_h1=float(HA[q]),stop_dist=sd,
                                 exit_type=ex,exit_price=exitp,R=rr,pct=pct,year=sig.year,
                                 MFE_R=(entry-float(L[j:je].min()))/sd,MAE_R=(float(H[j:je].max())-entry)/sd)
        out.append(d)
    return pd.DataFrame(out)


def metrics(g):
    if len(g)==0: return {'N':0,'episodes':0,'EV_R':np.nan,'PF':np.nan,'WR':np.nan,'EV_pct':np.nan,'SL_rate':np.nan}
    return {'N':len(g),'episodes':g.b3_episode_id.nunique(),'EV_R':float(g.R.mean()),'PF':pf(g.R),'WR':float((g.R>0).mean()),
            'EV_pct':float(g.pct.mean()),'SL_rate':float((g.exit_type=='SL').mean())}


def boot_ev(g,seed):
    if len(g)<3: return (np.nan,np.nan,np.nan)
    ids=g.b3_episode_id.unique(); groups={e:g[g.b3_episode_id==e].R.mean() for e in ids}; vals=np.array(list(groups.values()),float)
    rng=np.random.default_rng(seed); idx=rng.integers(0,len(vals),size=(BOOT,len(vals))); b=vals[idx].mean(axis=1)
    return float(np.quantile(b,.025)),float(np.quantile(b,.975)),float((b>0).mean())


def main():
    m1=base.load_zip('btc_1m.zip'); m5=base.load_zip('btc_5m.zip'); h1=base.h1_atr_from_m1(m1); clock=build_clock(m5); m15=resample_m15(m5)
    fvg=bearish_fvg_touches(m15); fvg=fvg[fvg.fvg_age_bars.between(11,60)].copy(); fvg.to_csv(OUT/'bearish_fvg_mature_first_touches.csv',index=False)
    # B3 episode onset baseline
    b3=clock[clock.sell_b3==1].copy(); onset=b3.groupby('b3_episode_id',as_index=False).first(); onset['signal_time']=onset.time; onset['requested_entry_time']=onset.time+pd.Timedelta(minutes=1); onset['branch']='B3_ONSET'
    onset_r=replay(onset,m1,h1)
    # FVG-only: first mature bearish FVG touch within a B3 episode
    ft=attach_clock(fvg.rename(columns={'fvg_touch_time':'signal_time'}),clock,'signal_time'); ft=ft[ft.sell_b3==1].copy(); ft=ft.sort_values('signal_time').groupby('b3_episode_id',as_index=False).first(); ft['requested_entry_time']=ft.signal_time+pd.Timedelta(minutes=1); ft['branch']='B3_FVG_ONLY'
    fvg_r=replay(ft,m1,h1)
    # Existing LAB015 failed recovery ledger
    lab=pd.read_csv('lab15.csv')
    for c in ['breakdown_time','rebound_pivot_time','trigger_time','entry_time']:
        lab[c]=pd.to_datetime(lab[c],format='%Y.%m.%d %H:%M:%S',errors='coerce')
    lab=lab.dropna(subset=['trigger_time','entry_time','breakdown_time']).copy(); lab=lab[(lab.trigger_time>=m1.time.min())&(lab.trigger_time<=m1.time.max())]
    if 'ordering_quality' in lab: lab=lab[lab.ordering_quality==1]
    # Deduplicate same trigger timestamp/episode mechanics before mapping: preserve trigger types as joined label.
    agg=lab.groupby(['episode_id','trigger_time','entry_time','breakdown_time','rebound_pivot_time'],as_index=False).agg(
        trigger_types=('trigger_type',lambda s:'|'.join(sorted(set(map(str,s))))),old_entry_price=('entry_price','first'))
    fr=attach_clock(agg,clock,'trigger_time'); fr=fr[fr.sell_b3==1].copy(); fr=fr.sort_values('trigger_time').groupby('b3_episode_id',as_index=False).first()
    fr['signal_time']=fr.trigger_time; fr['requested_entry_time']=fr.entry_time; fr['branch']='B3_FAILED_RESPONSE'
    # FVG location during the failed bullish recovery sequence: any mature bearish FVG first-touch between breakdown and trigger.
    touch_times=fvg.fvg_touch_time.to_numpy('datetime64[ns]')
    loc=[]; loc_time=[]; loc_age=[]
    fvgs=fvg.sort_values('fvg_touch_time').reset_index(drop=True)
    times=fvgs.fvg_touch_time.to_numpy('datetime64[ns]')
    for r in fr.itertuples(index=False):
        a=np.datetime64(pd.Timestamp(r.breakdown_time)); b=np.datetime64(pd.Timestamp(r.trigger_time)); i=np.searchsorted(times,a,'left'); j=np.searchsorted(times,b,'right')
        if j>i:
            sub=fvgs.iloc[i:j]; loc.append(1); loc_time.append(sub.fvg_touch_time.iloc[-1]); loc_age.append(int(sub.fvg_age_bars.iloc[-1]))
        else:
            loc.append(0); loc_time.append(pd.NaT); loc_age.append(np.nan)
    fr['fvg_location']=loc; fr['location_touch_time']=loc_time; fr['location_fvg_age']=loc_age
    fr_r=replay(fr,m1,h1); combo_r=replay(fr[fr.fvg_location==1].copy(),m1,h1); combo_r['branch']='B3_FAILED_RESPONSE_FVG'
    # Parity sanity old vs repriced
    if len(fr_r): fr_r['old_entry_abs_diff']=abs(fr_r.entry_price_repriced-fr_r.old_entry_price)
    branches={'B3_ONSET':onset_r,'B3_FVG_ONLY':fvg_r,'B3_FAILED_RESPONSE':fr_r,'B3_FAILED_RESPONSE_FVG':combo_r}
    rows=[]; yrs=[]
    for name,g in branches.items():
        g.to_csv(OUT/f'{name}.csv',index=False); m=metrics(g); lo,hi,p=boot_ev(g,SEED+sum(map(ord,name))); rows.append({'branch':name,**m,'CI_lo':lo,'CI_hi':hi,'P_EV_gt0':p})
        for y,gy in g.groupby('year'): yrs.append({'branch':name,'year':int(y),**metrics(gy)})
    S=pd.DataFrame(rows); Y=pd.DataFrame(yrs); S.to_csv(OUT/'summary.csv',index=False);Y.to_csv(OUT/'yearly.csv',index=False)
    # trigger family descriptive only
    fam=[]
    if len(fr_r):
        for token in ['F1_LEVEL_REJECTION_BREAKDOWN','F2_CLOSE_RECLAIM_FAILURE','F3_LOWER_HIGH_BREAKDOWN']:
            q=fr_r[fr_r.trigger_types.str.contains(token,regex=False,na=False)]; fam.append({'family':token,**metrics(q)})
    pd.DataFrame(fam).to_csv(OUT/'trigger_family_descriptive.csv',index=False)
    # selected-episode onset comparator: same B3 episodes as failed response branch
    comp=[]
    for label,g in [('FAILED_RESPONSE',fr_r),('FAILED_RESPONSE_FVG',combo_r)]:
        ids=set(g.b3_episode_id); a=onset_r[onset_r.b3_episode_id.isin(ids)]
        comp.append({'selection':label,'event_EV_R':g.R.mean() if len(g) else np.nan,'same_episode_onset_EV_R':a.R.mean() if len(a) else np.nan,'delta_vs_onset':(g.R.mean()-a.R.mean()) if len(g) and len(a) else np.nan,'N_event':len(g),'N_onset':len(a)})
    pd.DataFrame(comp).to_csv(OUT/'same_episode_onset_comparison.csv',index=False)
    parity={'lab15_recent_rows':int(len(lab)),'b3_failed_response_episodes':int(len(fr_r)),'repriced_vs_old_median_abs_usd':float(fr_r.old_entry_abs_diff.median()) if len(fr_r) else None,
            'repriced_vs_old_p95_abs_usd':float(fr_r.old_entry_abs_diff.quantile(.95)) if len(fr_r) else None,'mature_bear_fvg_touches':int(len(fvg))}
    (OUT/'summary.json').write_text(json.dumps(parity,indent=2))
    report=['# SELL_CORE_002 — B3 × M15 FAILED_BULL_RESPONSE × FVG LOCATION','',
            '**Frozen mechanism:** existing LAB015 failed-recovery SELL events; SELL_B3 H4 age 27–50; mature bearish M15 FVG first-touch age 11–60 during the recovery leg; common SL1.5 ATR / no TP / 48h.','',
            '## Main layering','',S.to_markdown(index=False),'','## Yearly',Y.to_markdown(index=False),'','## Same selected episodes: event entry vs B3 onset',pd.DataFrame(comp).to_markdown(index=False),'','## Trigger families (descriptive only)',pd.DataFrame(fam).to_markdown(index=False),'','## Parity sanity','',f'`{json.dumps(parity)}`']
    (OUT/'REPORT.md').write_text('\n'.join(report))
    print(S.to_string(index=False)); print('\nYEARLY\n',Y.to_string(index=False)); print('\nCOMPARISON\n',pd.DataFrame(comp).to_string(index=False)); print('\nPARITY\n',json.dumps(parity,indent=2)); print('\nREPORT\n'); print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
