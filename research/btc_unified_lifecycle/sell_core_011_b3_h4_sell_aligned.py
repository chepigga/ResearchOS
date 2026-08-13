#!/usr/bin/env python3
"""SELL_CORE_011 — B3 × H4_SELL_ALIGNED STATE VALIDATION.

Frozen before outcomes:
- Canonical H4 Supertrend = ATR10×3, U05 BAR_OPEN lag1 convention.
- SELL state = H4 ST DOWN (st_dir=-1) AND frozen SELL_B3 age 27..50 inclusive.
- No funding, FVG, CHoCH, v283, flow or extra price filters.
- Views: FIRST = first eligible H4 clock per continuous bearish ST episode;
         PERIODIC_4H = every eligible H4 clock.
- Phase robustness: 0h primary and +2h shift while carrying the same H4 state label.
- Entry: next M1 open one minute after signal timestamp.
- Stop: 1.5× completed H1 Wilder ATR14; no TP.
- 48h primary; 72h sensitivity; frozen cost $27.5/BTC.
- Inference: bootstrap by continuous H4 ST episode, not by trades.
- Age 27..50 is reported bar-for-bar only; no subrange may be promoted from this lab.
- Prop-risk diagnostic: max concurrent initial risk per ST episode = 0.5%.
  FIRST uses 0.5% per trade. PERIODIC uses 0.5%/(hold_h/4) per entry:
  48h => 0.041667%; 72h => 0.027778%.
"""
from pathlib import Path
import numpy as np, pandas as pd
import u02c2_v283_market_clock_conditional as base

OUT=Path('sell_core_011_out'); OUT.mkdir(exist_ok=True)
M1ZIP='btc_1m.zip'; M5ZIP='btc_5m.zip'
COST=27.5; STOP_ATR=1.5; BOOT=20000; SEED=411011
HOLDS=(48,72); PHASES=(0,2); EP_RISK=0.5


def pf(x):
    z=pd.Series(x).dropna(); gp=z[z>0].sum(); gl=-z[z<0].sum()
    return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)


def build_clock(m5):
    h4=base.h4_supertrend(m5)[['time','st_dir','st_age']].copy()
    h4['st_dir']=h4.st_dir.shift(1); h4['st_age']=h4.st_age.shift(1)
    h4=h4.dropna().copy(); h4.st_dir=h4.st_dir.astype(int); h4.st_age=h4.st_age.astype(int)
    new=h4.st_dir.ne(h4.st_dir.shift()) | ((h4.time-h4.time.shift())>pd.Timedelta(hours=4,minutes=1))
    h4['episode_id']=new.cumsum().astype(int)
    h4['eligible']=h4.st_dir.eq(-1)&h4.st_age.between(27,50)
    return h4


def make_rows(clock,view,phase):
    x=clock[clock.eligible].copy().sort_values('time')
    if view=='FIRST': x=x.groupby('episode_id',as_index=False).first()
    x['base_clock_time']=x.time
    x['signal_time']=x.time+pd.Timedelta(hours=phase)
    x['view']=view; x['phase_h']=phase
    return x


def replay(rows,m1,h1,hold_h):
    mt=m1.time.to_numpy('datetime64[ns]'); O=m1.open.to_numpy(float); H=m1.high.to_numpy(float)
    hct=h1.close_time.to_numpy('datetime64[ns]'); HA=h1.atr14.to_numpy(float)
    out=[]
    for r in rows.itertuples(index=False):
        sig=pd.Timestamp(r.signal_time); et=sig+pd.Timedelta(minutes=1)
        j=int(np.searchsorted(mt,np.datetime64(et),'left')); q=int(np.searchsorted(hct,np.datetime64(sig),'right')-1)
        if j>=len(O) or q<0 or not np.isfinite(HA[q]) or HA[q]<=0: continue
        je=int(np.searchsorted(mt,np.datetime64(sig+pd.Timedelta(hours=hold_h)),'left'))
        if je<=j or je>=len(O): continue
        entry=float(O[j]); sd=STOP_ATR*float(HA[q]); sl=entry+sd
        hit=np.flatnonzero(H[j:je]>=sl)
        if hit.size:
            rr=-1.0-COST/sd; pct=-(sd/entry*100.0)-COST/entry*100.0; ex='SL'
        else:
            xp=float(O[je]); rr=(entry-xp)/sd-COST/sd; pct=(entry-xp)/entry*100.0-COST/entry*100.0; ex='TIME'
        risk=EP_RISK if r.view=='FIRST' else EP_RISK/(hold_h/4.0)
        d=r._asdict(); d.update(entry_time=et,entry=entry,atr_h1=float(HA[q]),stop_dist=sd,hold_h=hold_h,R=rr,pct=pct,exit_type=ex,year=sig.year,risk_pct=risk,prop_return_pct=rr*risk)
        out.append(d)
    return pd.DataFrame(out)


def metrics(g):
    return {'N':len(g),'episodes':g.episode_id.nunique() if len(g) else 0,
            'EV_R':float(g.R.mean()) if len(g) else np.nan,'PF':pf(g.R),'WR':float((g.R>0).mean()) if len(g) else np.nan,
            'EV_pct':float(g.pct.mean()) if len(g) else np.nan,'SL_rate':float((g.exit_type=='SL').mean()) if len(g) else np.nan,
            'mean_age':float(g.st_age.mean()) if len(g) else np.nan}


def cluster_boot_mean(g,seed):
    z=g.dropna(subset=['R','pct']).copy(); ids=z.episode_id.unique()
    if len(ids)<4:return {'CI_R_lo':np.nan,'CI_R_hi':np.nan,'P_EV_R_gt0':np.nan,'CI_pct_lo':np.nan,'CI_pct_hi':np.nan,'P_EV_pct_gt0':np.nan}
    groups={e:z[z.episode_id==e] for e in ids}; rng=np.random.default_rng(seed); br=[]; bp=[]
    for _ in range(BOOT):
        samp=rng.choice(ids,size=len(ids),replace=True); b=pd.concat([groups[e] for e in samp],ignore_index=True)
        br.append(b.R.mean()); bp.append(b.pct.mean())
    br=np.asarray(br); bp=np.asarray(bp)
    return {'CI_R_lo':float(np.quantile(br,.025)),'CI_R_hi':float(np.quantile(br,.975)),'P_EV_R_gt0':float((br>0).mean()),
            'CI_pct_lo':float(np.quantile(bp,.025)),'CI_pct_hi':float(np.quantile(bp,.975)),'P_EV_pct_gt0':float((bp>0).mean())}


def episode_returns(g):
    return g.groupby('episode_id',as_index=False).agg(start=('signal_time','min'),end=('signal_time','max'),N=('R','size'),episode_return_pct=('prop_return_pct','sum'),mean_R=('R','mean'))


def boot_episode_return(ep,seed):
    z=ep.episode_return_pct.dropna().to_numpy(float)
    if len(z)<4:return {'mean_episode_return_pct':float(np.mean(z)) if len(z) else np.nan,'CI_lo':np.nan,'CI_hi':np.nan,'P_gt0':np.nan}
    rng=np.random.default_rng(seed); b=np.empty(BOOT)
    for i in range(BOOT): b[i]=rng.choice(z,size=len(z),replace=True).mean()
    return {'mean_episode_return_pct':float(z.mean()),'CI_lo':float(np.quantile(b,.025)),'CI_hi':float(np.quantile(b,.975)),'P_gt0':float((b>0).mean())}


def phase_pair(a,b,hold_h,view):
    aa=a[['episode_id','st_age','base_clock_time','R','pct']].copy(); bb=b[['episode_id','st_age','base_clock_time','R','pct']].copy()
    p=aa.merge(bb,on=['episode_id','st_age','base_clock_time'],suffixes=('_0','_2'))
    if len(p)==0:return p,{}
    p['dR']=p.R_2-p.R_0; p['dpct']=p.pct_2-p.pct_0
    ids=p.episode_id.unique(); groups={e:p[p.episode_id==e] for e in ids}; rng=np.random.default_rng(SEED+hold_h+(0 if view=='FIRST' else 1000)); bd=[]
    for _ in range(BOOT):
        samp=rng.choice(ids,size=len(ids),replace=True); q=pd.concat([groups[e] for e in samp],ignore_index=True); bd.append(q.dR.mean())
    bd=np.asarray(bd)
    return p,{'view':view,'hold_h':hold_h,'N_pairs':len(p),'episodes':len(ids),'EV0_R':float(p.R_0.mean()),'EV2_R':float(p.R_2.mean()),'delta_2_minus_0_R':float(p.dR.mean()),'CI_lo':float(np.quantile(bd,.025)),'CI_hi':float(np.quantile(bd,.975)),'P_delta_gt0':float((bd>0).mean()),'corr_R':float(p.R_0.corr(p.R_2))}


def main():
    m1=base.load_zip(M1ZIP); m5=base.load_zip(M5ZIP); h1=base.h1_atr_from_m1(m1); clock=build_clock(m5)
    clock.to_csv(OUT/'canonical_h4_clock.csv',index=False)
    parts=[]; summary=[]; yearly=[]; ages=[]; boots=[]; epboots=[]; phase_stats=[]
    saved={}
    for view in ['FIRST','PERIODIC_4H']:
        for ph in PHASES:
            rows=make_rows(clock,view,ph)
            for hh in HOLDS:
                tr=replay(rows,m1,h1,hh); tr.to_csv(OUT/f'trades_{view}_phase{ph}_{hh}h.csv',index=False); parts.append(tr); saved[(view,ph,hh)]=tr
                m=metrics(tr); cb=cluster_boot_mean(tr,SEED+ph*100+hh+(0 if view=='FIRST' else 10000)); summary.append({'view':view,'phase_h':ph,'hold_h':hh,**m,**cb})
                for y,g in tr.groupby('year'): yearly.append({'view':view,'phase_h':ph,'hold_h':hh,'year':int(y),**metrics(g)})
                for age,g in tr.groupby('st_age'): ages.append({'view':view,'phase_h':ph,'hold_h':hh,'st_age':int(age),**metrics(g)})
                ep=episode_returns(tr); ep.to_csv(OUT/f'episodes_{view}_phase{ph}_{hh}h.csv',index=False)
                eb=boot_episode_return(ep,SEED+hh+ph*100+(0 if view=='FIRST' else 2000)); epboots.append({'view':view,'phase_h':ph,'hold_h':hh,'episodes':len(ep),'risk_per_entry_pct':EP_RISK if view=='FIRST' else EP_RISK/(hh/4.0),**eb})
        for hh in HOLDS:
            p,st=phase_pair(saved[(view,0,hh)],saved[(view,2,hh)],hh,view); p.to_csv(OUT/f'phase_pairs_{view}_{hh}h.csv',index=False); phase_stats.append(st)
    A=pd.concat(parts,ignore_index=True); S=pd.DataFrame(summary); Y=pd.DataFrame(yearly); G=pd.DataFrame(ages); E=pd.DataFrame(epboots); P=pd.DataFrame(phase_stats)
    A.to_csv(OUT/'all_trades.csv',index=False); S.to_csv(OUT/'summary.csv',index=False); Y.to_csv(OUT/'yearly.csv',index=False); G.to_csv(OUT/'age_bar_by_bar.csv',index=False); E.to_csv(OUT/'episode_risk_bootstrap.csv',index=False); P.to_csv(OUT/'phase_robustness.csv',index=False)
    primary=S[(S.phase_h==0)&(S.hold_h==48)]
    yprim=Y[(Y.phase_h==0)&(Y.hold_h==48)]
    aprim=G[(G.phase_h==0)&(G.hold_h==48)]
    report=['# SELL_CORE_011 — B3 × H4_SELL_ALIGNED STATE VALIDATION','',
            '**Frozen state:** canonical H4 ST DOWN + age 27..50. No other gates.','',
            '## Primary 48h phase-0','',primary.to_markdown(index=False),'',
            '## Yearly 48h phase-0','',yprim.to_markdown(index=False),'',
            '## Phase robustness','',P.to_markdown(index=False),'',
            '## Episode-risk bootstrap','',E.to_markdown(index=False),'',
            '## Age 27..50 bar-for-bar — diagnostic only','',aprim.to_markdown(index=False),'',
            '## Interpretation boundary','',
            '- Do not promote an age subrange from this table.','- A state PASS requires positive R and price-space EV, useful cluster uncertainty, transfer across years, and no collapse under +2h phase shift.','- FIRST and PERIODIC are separate execution forms; periodic uses the 0.5% max-concurrent episode risk cap.']
    (OUT/'REPORT.md').write_text('\n'.join(report)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
