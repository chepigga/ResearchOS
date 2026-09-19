#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
SRC_EVENTS=ROOT/'GC_XAU_REV2_FLOW_IMPULSE_VOLUME_QUALITY_LAB009_EVENTS.csv'
SRC_THRESH=ROOT/'GC_XAU_REV2_IMPULSE_VOLUME_THRESHOLD_STABILITY_AND_INTERSECTION_LAB009C.json'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'

OUT_JSON=ROOT/'GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011.json'
OUT_MD=ROOT/'GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011.md'
OUT_LEDGER=ROOT/'GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011_LEDGER.csv'
OUT_MC=ROOT/'GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011_MONTECARLO.csv'
OUT_LOPO=ROOT/'GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011_LOPO.csv'

CLOCK_OFFSET_MIN=180
STALE_MS=2000
HORIZON_MS=300000
SL_ATR=2.25
TP_ATR=4.50
COMMISSION_RATE_SIDE=0.000007
N_BOOT=10000
N_MC=10000
SEED=260919

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    return m

def first_idx(t,target,maxlag=STALE_MS):
    i=int(np.searchsorted(t,target,side='left'))
    if i>=len(t): return None
    lag=int(t[i]-target)
    if lag<0 or lag>maxlag:return None
    return i

def end_idx(t,target):
    i=int(np.searchsorted(t,target,side='right'))-1
    return i if i>=0 else None

def pf(vals):
    x=np.asarray(vals,float)
    if not len(x): return None
    pos=x[x>0].sum(); neg=-x[x<0].sum()
    if neg==0:return float('inf') if pos>0 else None
    return float(pos/neg)

def dd_stats(vals):
    x=np.asarray(vals,float)
    if not len(x): return 0.0,0
    eq=np.cumsum(x)
    peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1]
    dd=peak-eq
    maxdd=float(np.max(dd)) if len(dd) else 0.0
    cur=best=0
    for v in x:
        if v<0:cur+=1;best=max(best,cur)
        else:cur=0
    return maxdd,int(best)

def stats(vals):
    x=np.asarray(vals,float)
    dd,streak=dd_stats(x)
    return {
      'n':int(len(x)),
      'ev_r':float(np.mean(x)) if len(x) else None,
      'pf':pf(x) if len(x) else None,
      'wr_pct':float((x>0).mean()*100) if len(x) else None,
      'cum_r':float(x.sum()) if len(x) else None,
      'maxdd_r':dd,
      'maxdd_pct_at_025':dd*0.25,
      'max_consec_losses':streak
    }

def sim_one(t,bid,ask,entry_i,end_i,d,entry,atr):
    slpx=entry-d*SL_ATR*atr
    tppx=entry+d*TP_ATR*atr
    if d>0:
        px=bid[entry_i:end_i+1]
        slhits=np.flatnonzero(px<=slpx); tphits=np.flatnonzero(px>=tppx)
    else:
        px=ask[entry_i:end_i+1]
        slhits=np.flatnonzero(px>=slpx); tphits=np.flatnonzero(px<=tppx)
    si=int(slhits[0]) if len(slhits) else None
    ti=int(tphits[0]) if len(tphits) else None
    if si is not None and (ti is None or si<=ti):
        return -1.0,'SL',int(t[entry_i+si]-t[entry_i])
    if ti is not None:
        return TP_ATR/SL_ATR,'TP',int(t[entry_i+ti]-t[entry_i])
    exitpx=float(bid[end_i] if d>0 else ask[end_i])
    rr=float(d*(exitpx-entry)/(SL_ATR*atr))
    return rr,'TIME',int(t[end_i]-t[entry_i])

def frozen_q65():
    ev=pd.read_csv(SRC_EVENTS)
    th=json.loads(SRC_THRESH.read_text())
    imp=float(th['thresholds']['Q65']['impulse'])
    av=float(th['thresholds']['Q65']['aligned_volume'])
    d5=ev[ev.window_s==5][['gc_t0_ms','period','direction','post_signed_impulse_atr']].copy()
    d30=ev[ev.window_s==30][['gc_t0_ms','period','direction','post_aligned_volume']].copy()
    m=d5.merge(d30,on=['gc_t0_ms','period','direction'],how='inner')
    z=m[(m.post_signed_impulse_atr>=imp)&(m.post_aligned_volume>=av)].copy()
    return z.sort_values('gc_t0_ms').reset_index(drop=True),imp,av

def bootstrap_iid(x,rng,n=N_BOOT):
    N=len(x); means=np.empty(n)
    for i in range(n):
        means[i]=np.mean(rng.choice(x,size=N,replace=True))
    return means

def bootstrap_block(x,rng,block=3,n=N_BOOT):
    N=len(x); means=np.empty(n)
    starts=np.arange(max(1,N-block+1))
    for i in range(n):
        out=[]
        while len(out)<N:
            s=int(rng.choice(starts))
            out.extend(x[s:min(N,s+block)].tolist())
        means[i]=np.mean(np.asarray(out[:N],float))
    return means

def mc_permute(x,rng,n=N_MC):
    dds=np.empty(n);streaks=np.empty(n,dtype=int)
    for i in range(n):
        y=rng.permutation(x)
        dds[i],streaks[i]=dd_stats(y)
    return dds,streaks

def main():
    lt=load(LT,'lt')
    sig,imp_thr,av_thr=frozen_q65()

    t,bid,ask,_=lt.read_xau_ticks()
    xm1=lt.build_xau_m1(t,bid,ask)
    xatr=lt.xau_atr_lookup(xm1)

    rows=[]
    for r in sig.itertuples(index=False):
        broker0=int(r.gc_t0_ms)+CLOCK_OFFSET_MIN*60000+30000
        i=first_idx(t,broker0)
        if i is None:continue
        j=end_idx(t,broker0+HORIZON_MS)
        if j is None or j<=i:continue
        prev=((broker0//60000)*60000)-60000
        atr=float(xatr.get(prev,np.nan))
        if not np.isfinite(atr) or atr<=0:continue
        d=int(r.direction)
        entry=float(ask[i] if d>0 else bid[i])
        gross_r,reason,hold=sim_one(t,bid,ask,i,j,d,entry,atr)

        commission_r=(2.0*COMMISSION_RATE_SIDE*entry)/(SL_ATR*atr)
        net_r=gross_r-commission_r
        utc=pd.to_datetime(int(r.gc_t0_ms),unit='ms',utc=True)
        iso=utc.isocalendar()
        rows.append({
          'gc_t0_ms':int(r.gc_t0_ms),'utc':utc.isoformat(),'period':r.period,'direction':d,
          'entry_price':entry,'atr':atr,'gross_r':gross_r,'commission_r':commission_r,'net_r':net_r,
          'reason':reason,'hold_ms':hold,'iso_year':int(iso.year),'iso_week':int(iso.week),
          'post_signed_impulse_atr':float(r.post_signed_impulse_atr),
          'post_aligned_volume':float(r.post_aligned_volume)
        })

    led=pd.DataFrame(rows).sort_values('gc_t0_ms').reset_index(drop=True)
    led.to_csv(OUT_LEDGER,index=False)

    split_stats={}
    for p in ('TRAIN','VALID','POST_CHECK','FULL'):
        z=led if p=='FULL' else led[led.period==p]
        split_stats[p]=stats(z.net_r.to_numpy(float))

    exact_cost={
      'commission_rate_side_pct':COMMISSION_RATE_SIDE*100,
      'median_commission_r':float(led.commission_r.median()),
      'mean_commission_r':float(led.commission_r.mean()),
      'min_commission_r':float(led.commission_r.min()),
      'max_commission_r':float(led.commission_r.max()),
      'gross_full':stats(led.gross_r.to_numpy(float)),
      'net_full':stats(led.net_r.to_numpy(float)),
    }

    rng=np.random.default_rng(SEED)
    x=led.net_r.to_numpy(float)
    iid=bootstrap_iid(x,rng)
    blk=bootstrap_block(x,rng,3)
    dds,streaks=mc_permute(x,rng)

    boot={
      'iid':{
        'p_ev_gt0':float((iid>0).mean()),
        'ev_ci95':[float(np.quantile(iid,.025)),float(np.quantile(iid,.975))],
        'median_ev':float(np.median(iid))
      },
      'block3':{
        'p_ev_gt0':float((blk>0).mean()),
        'ev_ci95':[float(np.quantile(blk,.025)),float(np.quantile(blk,.975))],
        'median_ev':float(np.median(blk))
      }
    }
    mc={
      'maxdd_r_median':float(np.median(dds)),
      'maxdd_r_p95':float(np.quantile(dds,.95)),
      'maxdd_r_p99':float(np.quantile(dds,.99)),
      'maxdd_pct_p95_at_025':float(np.quantile(dds,.95)*0.25),
      'streak_median':float(np.median(streaks)),
      'streak_p95':float(np.quantile(streaks,.95)),
      'streak_p99':float(np.quantile(streaks,.99))
    }
    pd.DataFrame({'maxdd_r':dds,'max_consec_losses':streaks}).to_csv(OUT_MC,index=False)

    lopo=[]
    # Leave one split out
    for leave in ('TRAIN','VALID','POST_CHECK'):
        z=led[led.period!=leave]
        s=stats(z.net_r.to_numpy(float))
        lopo.append({'type':'split','leave_out':leave,**s})

    # Leave one ISO week out
    for (yr,wk),_ in led.groupby(['iso_year','iso_week']):
        z=led[~((led.iso_year==yr)&(led.iso_week==wk))]
        s=stats(z.net_r.to_numpy(float))
        lopo.append({'type':'iso_week','leave_out':f'{yr}-W{wk:02d}',**s})
    ldf=pd.DataFrame(lopo)
    ldf.to_csv(OUT_LOPO,index=False)

    week=ldf[ldf.type=='iso_week']
    split=ldf[ldf.type=='split']
    lopo_summary={
      'week_count':int(len(week)),
      'min_remaining_ev_week':float(week.ev_r.min()) if len(week) else None,
      'min_remaining_pf_week':float(week.pf.replace([np.inf],np.nan).min()) if len(week) else None,
      'all_week_remaining_ev_positive':bool((week.ev_r>0).all()) if len(week) else None,
      'split_leaveout':split.to_dict(orient='records')
    }

    out={
      'lab':'GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011',
      'status':'FROZEN_VALIDATION_NOT_PRISTINE_OOS',
      'frozen':{'impulse_q65':imp_thr,'aligned_volume_q65':av_thr,'sl_atr':SL_ATR,'tp_atr':TP_ATR,'timeout_s':300},
      'split_stats_exact_cost':split_stats,
      'exact_cost':exact_cost,
      'bootstrap':boot,
      'monte_carlo':mc,
      'leave_one_period_out':lopo_summary
    }
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')

    def f(v,d=3):
        if v is None or (isinstance(v,float) and not np.isfinite(v)):return 'NA'
        return f'{v:.{d}f}'

    lines=['# GC_XAU_REV2_Q65_FROZEN_OOS_BOOTSTRAP_MONTECARLO_LOPO_COST_LAB011','',
           'Status: FROZEN_VALIDATION_NOT_PRISTINE_OOS','',
           'Frozen: Q65 impulse + Q65 aligned volume; entry REV2+30s; SL 2.25 ATR; TP 4.50 ATR; timeout 300s.','',
           'POST_CHECK is not pristine OOS because it was inspected in prior discovery labs.','',
           '## Exact FTMO metals commission conversion','',
           f"- Commission per side: {COMMISSION_RATE_SIDE*100:.6f}% of notional",
           f"- Commission R/trade: median {f(exact_cost['median_commission_r'],4)}, mean {f(exact_cost['mean_commission_r'],4)}, range {f(exact_cost['min_commission_r'],4)}–{f(exact_cost['max_commission_r'],4)}",
           '',
           '| Split | N | EV R | PF | CumR | WR | MaxDD R | DD% @0.25 | Streak |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in ('TRAIN','VALID','POST_CHECK','FULL'):
        s=split_stats[p]
        lines.append(f"| {p} | {s['n']} | {f(s['ev_r'])} | {f(s['pf'])} | {f(s['cum_r'])} | {f(s['wr_pct'],1)}% | {f(s['maxdd_r'])} | {f(s['maxdd_pct_at_025'])}% | {s['max_consec_losses']} |")
    lines += ['','## Bootstrap','',
              f"- IID: P(EV>0) {boot['iid']['p_ev_gt0']:.3f}; 95% CI [{f(boot['iid']['ev_ci95'][0])}, {f(boot['iid']['ev_ci95'][1])}] R/trade",
              f"- Block-3: P(EV>0) {boot['block3']['p_ev_gt0']:.3f}; 95% CI [{f(boot['block3']['ev_ci95'][0])}, {f(boot['block3']['ev_ci95'][1])}] R/trade",
              '',
              '## Monte Carlo path risk','',
              f"- MaxDD median {f(mc['maxdd_r_median'])}R; p95 {f(mc['maxdd_r_p95'])}R; p99 {f(mc['maxdd_r_p99'])}R",
              f"- p95 DD at 0.25% risk: {f(mc['maxdd_pct_p95_at_025'])}%",
              f"- Losing streak median {f(mc['streak_median'],1)}; p95 {f(mc['streak_p95'],1)}; p99 {f(mc['streak_p99'],1)}",
              '',
              '## Leave-one-period-out','',
              f"- ISO weeks tested: {lopo_summary['week_count']}",
              f"- Minimum remaining EV after removing any week: {f(lopo_summary['min_remaining_ev_week'])}R",
              f"- Minimum remaining PF after removing any week: {f(lopo_summary['min_remaining_pf_week'])}",
              f"- Remaining EV positive for every removed week: {lopo_summary['all_week_remaining_ev_positive']}",
              '']
    for r in lopo_summary['split_leaveout']:
        lines.append(f"- Leave {r['leave_out']}: N={r['n']}, EV={f(r['ev_r'])}R, PF={f(r['pf'])}, CumR={f(r['cum_r'])}")
    lines += ['','True independent OOS requires fresh future REV2 events collected after this freeze.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
