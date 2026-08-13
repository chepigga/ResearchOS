#!/usr/bin/env python3
"""U02C9 — ordered cheap-component ablation inside B3 H1-CHoCH population.

Frozen candidate order from prior discussion:
1 HTF BUY bias
2 PRE >= 60
3 LateEntry geometry pass (BUY dist <= 1.35 if breakout-probe else <= 1.5)
4 microBreakUp
5 BUY_BEAR_D1 veto pass
6 knife/panic safety pass
7 bullish FVG/OB overlap

Two views are reported without outcome-driven reordering:
A) ONE-AT-A-TIME: H1 CHoCH + candidate.
B) CUMULATIVE: H1 CHoCH + all candidates up through that step.

BOS H1 is omitted because U02C8 proved it is identical to H1 CHoCH in this B3 population.
All selectors use the U02C6B/U02C7 causal architecture: next fixed H4 clock after occurrence;
same-year, same-B3-age risk-set controls; matching on comparison-time RV168 + ATR%;
SL=1.5 H1 ATR, no TP, 48h exit, same cost proxy.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import u02c2_v283_market_clock_conditional as base
import u02c2_fast_v283_shadow as fast
import u02c5_periodic_state_entry_ablation as u5
import u02c6_b3_v283_occurrence_selection as a
import u02c7_pure_choch_occurrence_selection as c7

OUT=Path('u02c9_out'); OUT.mkdir(exist_ok=True)
SEED=28309


def build_panel(m1):
    x=m1[m1.time>=pd.Timestamp('2023-06-01')].reset_index(drop=True)
    m5=fast.rs(x,'5min'); m15=fast.rs(x,'15min'); h1=fast.rs(x,'1h'); h4=fast.rs(x,'4h'); d1=fast.rs(x,'1D')
    for df in [m15,h1,h4,d1]: df['atr14']=fast.atr(df)
    h1['ema50']=fast.ema(h1.close,50); h4['ema50']=fast.ema(h4.close,50); d1['ema50']=fast.ema(d1.close,50)
    b1,_,_=fast.precompute_bos(h1,60); b15,_,_=fast.precompute_bos(m15,60); b4,_,_=fast.precompute_bos(h4,50); bd,_,_=fast.precompute_bos(d1,30)
    h1av=h1.atr14.to_numpy(float); c1=fast.precompute_choch(h1,h1av)
    ct1=h1.close_time.to_numpy('datetime64[ns]'); ct4=h4.close_time.to_numpy('datetime64[ns]'); ctd=d1.close_time.to_numpy('datetime64[ns]'); ct15=m15.close_time.to_numpy('datetime64[ns]')
    av15=np.full(len(m15),np.nan)
    for i,t in enumerate(ct15):
        q=int(np.searchsorted(ct1,t,'right')-1)
        if q>=0: av15[i]=h1av[q]
    c15=fast.precompute_choch(m15,av15)
    bf,sf,bo,so=fast.fvgob_arrays(h1,h1av)
    cb,cs=fast.compression_arrays(m15,m15.atr14.to_numpy(float))
    ex=fast.extended_arrays(h1,h4,d1,h1av)
    lfh,lfl=fast.latest_fractals_m1(x)
    tm1=x.time.to_numpy('datetime64[ns]')
    h1ema=h1.ema50.to_numpy(float); h4ema=h4.ema50.to_numpy(float); h4close=h4.close.to_numpy(float); h1close=h1.close.to_numpy(float)
    d1close=d1.close.to_numpy(float); d1ema=d1.ema50.to_numpy(float); d1atr=d1.atr14.to_numpy(float)
    m15O=m15.open.to_numpy(float);m15C=m15.close.to_numpy(float);m15H=m15.high.to_numpy(float);m15L=m15.low.to_numpy(float);atr15=m15.atr14.to_numpy(float)
    rows=[]
    for im,r in enumerate(m5.itertuples(index=False)):
        t=pd.Timestamp(r.time)
        if t<pd.Timestamp('2024-01-01'): continue
        nt=np.datetime64(t)
        n1=int(np.searchsorted(ct1,nt,'right')-1); n4=int(np.searchsorted(ct4,nt,'right')-1); nd=int(np.searchsorted(ctd,nt,'right')-1); n15=int(np.searchsorted(ct15,nt,'right')-1); nm1=int(np.searchsorted(tm1,nt,'left')-1)
        if min(n1,n4,nd,n15,nm1)<60: continue
        if c1[n1]!=1: continue
        ah=h1av[n1]; a15=atr15[n15]
        if not np.isfinite(ah) or ah<=0 or not np.isfinite(a15) or a15<=0: continue
        ht=fast.htf_bias_at(bd,b4,b1,nd,n4,n1,h4ema,h4close)
        live=float(r.open); ask=live+fast.SPREAD; bid=live
        mup=bool(np.isfinite(lfh[nm1]) and ask>lfh[nm1]); mdn=bool(np.isfinite(lfl[nm1]) and bid<lfl[nm1])
        e1=h1ema[n1]; slope=(e1-h1ema[n1-1])/ah; dist=(bid-e1)/ah; imp=abs(h1close[n1]-h1close[n1-1])/ah
        o=m15O[n15]; cc=m15C[n15]; hi=m15H[n15]; lo=m15L[n15]; body=abs(cc-o); rng=hi-lo; panic=0
        if rng>0 and body/a15>=1.8:
            if cc<o and (cc-lo)/rng<=.20: panic=-1
            elif cc>o and (hi-cc)/rng<=.20: panic=1
        score=0
        if ht!=0: score+=15
        if (ht==1 and b1[n1]==1) or (ht==-1 and b1[n1]==-1): score+=30
        if (ht==1 and mup) or (ht==-1 and mdn): score+=25
        if ht==1 and ex['bH4'][n1]: score+=25
        if ht==-1 and ex['sH4'][n1]: score+=25
        if ht==1 and ex['bPDL'][n1]: score+=20
        if ht==-1 and ex['sPDH'][n1]: score+=20
        if ht==1 and ex['bW'][n1]: score+=15
        if ht==-1 and ex['sW'][n1]: score+=15
        if ht==-1 and (ex['sH4'][n1] or ex['sPDH'][n1] or ex['sW'][n1]): score+=5
        if (ht==1 and b15[n15]==1) or (ht==-1 and b15[n15]==-1): score+=15
        if ht==1 and bf[n1] and bo[n1]: score+=12
        if ht==-1 and sf[n1] and so[n1]: score+=12
        if (ht==1 and slope>.02) or (ht==-1 and slope<-.02): score+=8
        if (ht==1 and cb[n15] and mup) or (ht==-1 and cs[n15] and mdn): score+=10
        if (ht==1 and b1[n1]==-1) or (ht==-1 and b1[n1]==1): score-=20
        if panic!=0: score-=20
        if (ht==1 and mdn) or (ht==-1 and mup): score-=15
        if ht==1 and -.3>dist>-2.5: score+=15
        if ht==-1 and .3<dist<2.5: score+=15
        if ht==1 and dist>2: score-=20
        if ht==1 and dist>3.5: score-=20
        if ht==-1 and dist<-2: score-=20
        if ht==-1 and dist<-3.5: score-=20
        if ht==1 and c1[n1]==1: score+=12
        if ht==-1 and c1[n1]==-1: score+=12
        if ht==1 and c1[n1]==-1: score-=10
        if ht==-1 and c1[n1]==1: score-=10
        if c1[n1]==1 and c15[n15]==1: score+=8
        if c1[n1]==-1 and c15[n15]==-1: score+=8
        if c15[n15]!=0 and not mup and im>=5:
            hh=float(m5.high.iloc[im-5:im].max()); ll=float(m5.low.iloc[im-5:im].min())
            if (ht==1 and ask>hh) or (ht==-1 and ask<ll): score+=20
        if ht==-1 and b1[n1]==1 and c1[n1]==1 and b15[n15]>=0 and dist<2.5: score+=30
        if ht==1 and b1[n1]==-1 and c1[n1]==-1 and b15[n15]<=0 and dist>-2.5: score+=30
        score=int(max(0,min(100,score)))
        brk=(ht==1 and score>=35 and mup and dist<2.2 and panic==0) or (ht==-1 and score>=35 and mdn and dist>-2.2 and panic==0)
        late_limit=1.35 if brk else 1.5
        mom2=(d1close[nd]-d1close[nd-2])/d1atr[nd] if nd>=55 and np.isfinite(d1atr[nd]) and d1atr[nd]>0 else 0.0
        eidx=(live-d1ema[nd])/d1atr[nd] if nd>=55 and np.isfinite(d1atr[nd]) and d1atr[nd]>0 else 0.0
        d1pass=not (mom2<-1.5 and eidx<-.5)
        knife=False
        if body>a15*1.5 and rng>0 and body/rng>.70:
            bull=cc>o
            if not bull: knife=True
        safety=(not knife) and (panic!=-1)
        rows.append({'time':t,'htf_buy':int(ht==1),'pre60':int(score>=60),'pre40':int(score>=40),'late_pass':int(dist<=late_limit),'micro_up':int(mup),'d1_pass':int(d1pass),'safety_pass':int(safety),'fvgob_overlap':int(bo[n1]),'bosH1':int(b1[n1]),'pre':score,'dist':dist,'late_limit':late_limit,'panic':panic,'knife':int(knife),'mom2':mom2,'eidx':eidx})
    return pd.DataFrame(rows),m5


def selector_times(panel,mask):
    return pd.DatetimeIndex(panel.loc[mask,'time']).sort_values()


def v283_episode_flags(eps):
    sh=pd.read_csv(a.SHADOW); sh['time']=pd.to_datetime(sh.time)
    sh=sh[(sh.action=='BUY')&(sh.pass_stateless==1)].sort_values('time')
    st=sh.time.to_numpy('datetime64[ns]'); vals=[]
    for e in eps.itertuples(index=False):
        aa=np.searchsorted(st,np.datetime64(e.start),'left'); bb=np.searchsorted(st,np.datetime64(e.end),'left'); vals.append(int(bb>aa))
    return pd.Series(vals,index=eps.index)


def run_selector(name,times,eps,m1,h1):
    ex=c7.mark_selector(eps,times,name)
    treated=c7.causal_entries(ex,m1,h1)
    p,rs=c7.riskset_pairs(treated,ex,h1,m1,name)
    s,y,b=c7.summarize(name,treated,p,rs)
    return ex,treated,p,rs,s,y,b


def main():
    m1=base.load_zip(base.M1ZIP); m5_clock=base.load_zip(base.M5ZIP)
    panel,_=build_panel(m1); panel.to_csv(OUT/'choch_m5_component_panel.csv',index=False)
    h1=a.h1_controls(m1)
    clock=u5.build_clock(m5_clock); eps=u5.state_episodes(clock); eps=eps[eps.state=='B3_BUY'].copy().reset_index(drop=True)
    eps['v283_occurs']=v283_episode_flags(eps)
    _,events=c7.build_choch_events(m1); base_times=events['H1']
    independent=[('BASE_H1_CHOCH',None),('C1_HTF_BUY','htf_buy'),('C2_PRE60','pre60'),('C3_LATE_PASS','late_pass'),('C4_MICRO_UP','micro_up'),('C5_D1_PASS','d1_pass'),('C6_SAFETY_PASS','safety_pass'),('C7_FVGOB_OVERLAP','fvgob_overlap')]
    cumulative_cols=[]; specs=[]
    for nm,col in independent:
        if col is None: specs.append(('INDEPENDENT',nm,base_times))
        else: specs.append(('INDEPENDENT',nm,selector_times(panel,panel[col]==1)))
    for nm,col in independent[1:]:
        cumulative_cols.append(col); mask=np.ones(len(panel),dtype=bool)
        for cc in cumulative_cols: mask &= (panel[cc].to_numpy()==1)
        specs.append(('CUMULATIVE','LADDER_'+nm,selector_times(panel,mask)))
    sums=[]; yrs=[]; bals=[]; cens=[]; overlaps=[]
    for view,name,times in specs:
        ex,tr,p,rs,s,y,b=run_selector(name,times,eps,m1,h1)
        if len(s): s.insert(0,'view',view); sums.append(s)
        if len(y): y.insert(0,'view',view); yrs.append(y)
        if len(b): b.insert(0,'view',view); bals.append(b)
        occ=int(ex.occurs.sum()); v=int(ex.v283_occurs.sum()); inter=int(((ex.occurs==1)&(ex.v283_occurs==1)).sum()); union=int(((ex.occurs==1)|(ex.v283_occurs==1)).sum())
        cens.append({'view':view,'selector':name,'episodes_occurrence':occ,'causal_entries':len(tr),'median_delay_h':ex.loc[ex.occurs==1,'occurrence_delay_h'].median()})
        overlaps.append({'view':view,'selector':name,'selector_episodes':occ,'v283_episodes':v,'intersection':inter,'v283_coverage':inter/v if v else np.nan,'precision_vs_v283':inter/occ if occ else np.nan,'extra_vs_v283':occ-inter,'missed_v283':v-inter,'jaccard':inter/union if union else np.nan})
        ex.to_csv(OUT/f"episodes_{name}.csv",index=False)
    sm=pd.concat(sums,ignore_index=True) if sums else pd.DataFrame(); yr=pd.concat(yrs,ignore_index=True) if yrs else pd.DataFrame(); bal=pd.concat(bals,ignore_index=True) if bals else pd.DataFrame(); cen=pd.DataFrame(cens); ov=pd.DataFrame(overlaps)
    sm.to_csv(OUT/'summary.csv',index=False);yr.to_csv(OUT/'yearly.csv',index=False);bal.to_csv(OUT/'balance.csv',index=False);cen.to_csv(OUT/'census.csv',index=False);ov.to_csv(OUT/'overlap_precision.csv',index=False)
    k1=sm[sm.estimator=='K1'].merge(ov,on=['view','selector'],how='left') if len(sm) else pd.DataFrame()
    cols=['view','selector','N_treated','treated_EV_R','control_EV_R','delta_R','CI_R_lo','CI_R_hi','P_delta_R_gt0','selector_episodes','v283_coverage','precision_vs_v283','extra_vs_v283','missed_v283']
    k1=k1[cols] if len(k1) else k1; k1.to_csv(OUT/'ordered_k1.csv',index=False)
    report=['# U02C9 — ORDERED CHEAP v283 COMPONENT LADDER','','**Frozen order:** HTF BUY → PRE>=60 → LateEntry pass → microUp → D1 veto pass → knife/panic pass → FVG/OB overlap.','','Two views: independent one-at-a-time and cumulative ladder. No outcome-driven reordering. BOS omitted because U02C8 proved redundancy.','','## Ordered K1 results','',k1.to_markdown(index=False) if len(k1) else 'NO RESULTS','','## K5 / full summary','',sm.to_markdown(index=False) if len(sm) else 'NO RESULTS','','## Yearly','',yr.to_markdown(index=False) if len(yr) else 'NO RESULTS','','## Overlap / precision vs accepted v283 episodes','',ov.to_markdown(index=False),'','## Rule','','Interpret components in the preregistered order. A cheap replacement candidate must materially improve precision and causal excess versus pure H1 CHoCH, retain useful v283 coverage, and not rely on a single year.']
    (OUT/'REPORT.md').write_text('\n'.join(report))
    (OUT/'summary.json').write_text(json.dumps({'order':['HTF_BUY','PRE60','LATE_PASS','MICRO_UP','D1_PASS','SAFETY_PASS','FVGOB_OVERLAP'],'views':['independent','cumulative'],'seed':SEED},indent=2))
    print(k1.to_string(index=False)); print('\nOVERLAP\n',ov.to_string(index=False))

if __name__=='__main__': main()
