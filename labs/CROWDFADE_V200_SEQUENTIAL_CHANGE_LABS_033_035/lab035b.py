from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from numba import njit
import run as core

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

RETRACE=0.60
TTL=1200
ZFLIP_BASE=0
ZFLIP_CAND=1
ATRMODE=0
BOOT_REPS=20000
BLOCK_WEEKS=4
SEED=35035

@njit(cache=True)
def audit_preserve(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4,retrace,pttl):
    cap=len(dt)
    ST=np.zeros(cap,np.int64); CT=np.zeros(cap,np.int64); ET=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8); FILLED=np.zeros(cap,np.int8); FLIP=np.zeros(cap,np.int8)
    ORIGZ=np.zeros(cap); CONFZ=np.zeros(cap); R=np.full(cap,np.nan)
    CEX=np.zeros(cap); CB=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0

    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:
            k+=1; continue
        d=t//86400
        if d!=day:
            day=d; dc=0
        if dc>=core.MAXDAY:
            k+=1; continue
        z=Z[k]
        side=-1 if z>=core.ZTH else (1 if z<=-core.ZTH else 0)
        if side==0:
            k+=1; continue
        sig=QC[k]; siga=A[k]
        if has and abs(sig-last)<core.ANTI_REPEAT_ATR*la:
            k+=1; continue

        lev=sig+side*core.CONF*siga
        ci=-1; maxcrowd=0.
        crowd=-side
        j=k+1
        while j<len(dt) and dt[j]<=t+core.CONF_TTL:
            exc=((QH[j]-sig) if crowd>0 else (sig-QL[j]))/siga
            if exc>maxcrowd: maxcrowd=exc
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):
                ci=j; break
            j+=1
        if ci<0:
            k+=1; continue

        cz=Z[ci]
        isflip=1 if z*cz<0.0 else 0
        entry=QC[ci]-side*retrace*siga
        ps=np.searchsorted(ts,dt[ci]+1)
        pe=np.searchsorted(ts,dt[ci]+pttl,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):
                ei=q; break

        ST[n]=t; CT[n]=dt[ci]; SIDE[n]=side; ORIGZ[n]=z; CONFZ[n]=cz
        CEX[n]=maxcrowd; CB[n]=ci-k; FLIP[n]=isflip
        if ei<0:
            FILLED[n]=0; ET[n]=0; R[n]=np.nan; n+=1
            k=ci+1; continue

        FILLED[n]=1; ET[n]=ts[ei]
        risk=core.SL*siga
        sl=entry-side*risk
        tp=entry+side*core.TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+core.HOLD,'left'))
        xp=C[xe]; ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=tp)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=sl)
            if sh:
                xp=sl; ex=q; break
            if th:
                xp=tp; ex=q; break
        rr=side*(xp-entry)/risk-(core.COST_BPS/10000.)*entry/risk
        R[n]=rr; n+=1

        dc+=1; last=entry; la=siga; has=True; nextts=ts[ex]+1
        k=np.searchsorted(dt,nextts)

    return ST[:n],CT[:n],ET[:n],SIDE[:n],FILLED[:n],FLIP[:n],ORIGZ[:n],CONFZ[:n],R[:n],CEX[:n],CB[:n]

def load_data():
    ft,fz=core.load_flow()
    hist=core.prep(core.load_hist_price(),ft,fz,
        int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=core.prep(core.load_sec_price(),ft,fz,
        int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    return hist,fwd

def run_pair(arr,period):
    bm,bdf=core.run_one(arr,RETRACE,TTL,ZFLIP_BASE,ATRMODE,period)
    cm,cdf=core.run_one(arr,RETRACE,TTL,ZFLIP_CAND,ATRMODE,period)
    return bm,bdf,cm,cdf

def outer_decomp(bdf,cdf):
    keep=['signal_ts','R','entry_ts','side','orig_z','confirm_z','confirm_bars','crowd_exc_atr']
    b=bdf[keep].copy().rename(columns={x:f'b_{x}' for x in keep if x!='signal_ts'})
    c=cdf[keep].copy().rename(columns={x:f'c_{x}' for x in keep if x!='signal_ts'})
    m=b.merge(c,on='signal_ts',how='outer',indicator=True)
    m['delta_R']=m['c_R'].fillna(0)-m['b_R'].fillna(0)
    m['category']=np.where(m['_merge'].eq('both'),'COMMON',
                   np.where(m['_merge'].eq('left_only'),'REMOVED_BASE','ADDED_CAND'))
    m['baseline_sign_flip']=(m['b_orig_z']*m['b_confirm_z']<0).fillna(False)
    return m

def week_delta_series(pair,start,end):
    startdt=pd.to_datetime(start,unit='s',utc=True).floor('D')
    enddt=pd.to_datetime(end,unit='s',utc=True).ceil('D')
    idx=pd.date_range(startdt,enddt,freq='W-MON',tz='UTC')
    q=pair.copy()
    q['time']=pd.to_datetime(q.signal_ts,unit='s',utc=True)
    q['week']=q['time'].dt.to_period('W-SUN').apply(lambda p:p.start_time.tz_localize('UTC'))
    return q.groupby('week').delta_R.sum().reindex(idx,fill_value=0.0)

def moving_block_bootstrap(x,reps=BOOT_REPS,block=BLOCK_WEEKS,seed=SEED):
    x=np.asarray(x,float); n=len(x)
    rng=np.random.default_rng(seed)
    starts=np.arange(max(1,n-block+1))
    sums=np.empty(reps)
    nb=math.ceil(n/block)
    for r in range(reps):
        vals=[]
        for _ in range(nb):
            st=int(rng.choice(starts))
            vals.extend(x[st:min(n,st+block)].tolist())
        vals=np.asarray(vals[:n],float)
        sums[r]=vals.sum()
    return {
        'reps':reps,'block_weeks':block,
        'observed_sumR':float(x.sum()),
        'ci95_sumR':[float(np.quantile(sums,.025)),float(np.quantile(sums,.975))],
        'p_bootstrap_sumR_gt_0':float((sums>0).mean()),
        'median_sumR':float(np.median(sums))
    }

def concentration(pair):
    q=pair.copy()
    q['time']=pd.to_datetime(q.signal_ts,unit='s',utc=True)
    q['week']=q['time'].dt.to_period('W-SUN').astype(str)
    w=q.groupby('week').delta_R.sum().sort_values(ascending=False)
    pos=w[w>0]
    total_pos=pos.sum()
    return {
      'nonzero_weeks':int((w!=0).sum()),
      'positive_weeks':int((w>0).sum()),
      'negative_weeks':int((w<0).sum()),
      'net_delta_R':float(w.sum()),
      'total_positive_contribution_R':float(total_pos),
      'total_negative_contribution_R':float(w[w<0].sum()),
      'top1_share_of_positive':float(pos.head(1).sum()/total_pos) if total_pos>0 else 0,
      'top3_share_of_positive':float(pos.head(3).sum()/total_pos) if total_pos>0 else 0,
      'top5_share_of_positive':float(pos.head(5).sum()/total_pos) if total_pos>0 else 0,
      'net_after_removing_top3_positive_weeks_R':float(w.sum()-pos.head(3).sum()),
      'top10_weeks':[{'week':str(i),'delta_R':float(v)} for i,v in w.head(10).items()]
    }

def year_month_delta(pair,kind):
    q=pair.copy()
    q['time']=pd.to_datetime(q.signal_ts,unit='s',utc=True)
    q['bucket']=q.time.dt.year.astype(str) if kind=='year' else q.time.dt.strftime('%Y-%m')
    out=[]
    for b,g in q.groupby('bucket'):
        out.append({'bucket':b,'delta_R':float(g.delta_R.sum()),
                    'removed_R':float(-g.loc[g.category=='REMOVED_BASE','b_R'].fillna(0).sum()),
                    'added_R':float(g.loc[g.category=='ADDED_CAND','c_R'].fillna(0).sum()),
                    'common_delta_R':float(g.loc[g.category=='COMMON','delta_R'].sum()),
                    'changed_events':int((g.delta_R.abs()>1e-12).sum())})
    return out

def leave_one_year_out(pair):
    q=pair.copy(); q['year']=pd.to_datetime(q.signal_ts,unit='s',utc=True).dt.year
    total=float(q.delta_R.sum())
    return [{'left_out_year':int(y),'remaining_delta_R':float(total-q.loc[q.year==y,'delta_R'].sum())}
            for y in sorted(q.year.unique())]

def event_audit(arr):
    z=audit_preserve(*arr,RETRACE,TTL)
    st,ct,et,side,filled,flip,oz,cz,R,cex,cb=z
    e=pd.DataFrame({'signal_ts':st,'confirm_ts':ct,'entry_ts':et,'side':side,'filled':filled.astype(bool),
                    'sign_flip':flip.astype(bool),'orig_z':oz,'confirm_z':cz,'R':R,
                    'crowd_exc_atr':cex,'confirm_bars':cb})
    e['signal_time_utc']=pd.to_datetime(e.signal_ts,unit='s',utc=True)
    return e

def flip_breakdown(e):
    f=e[e.sign_flip].copy()
    ff=f[f.filled].copy()
    f['abs_confirm_z']=f.confirm_z.abs()
    f['flip_strength']=pd.cut(f.abs_confirm_z,[-np.inf,.5,1.0,core.ZTH,np.inf],
                              labels=['<0.5','0.5-1.0','1.0-2.05','>=2.05'])
    ff['abs_confirm_z']=ff.confirm_z.abs()
    ff['flip_strength']=pd.cut(ff.abs_confirm_z,[-np.inf,.5,1.0,core.ZTH,np.inf],
                               labels=['<0.5','0.5-1.0','1.0-2.05','>=2.05'])
    ff['direction']=np.where(ff.side>0,'BUY','SELL')
    return {
      'confirmed_flip_events':int(len(f)),
      'filled_flip_events':int(len(ff)),
      'fill_rate':float(len(ff)/len(f)) if len(f) else 0,
      'filled_metrics':core.metrics(ff.R.dropna().to_numpy(float)),
      'confirmed_by_strength':{str(k):int(v) for k,v in f.flip_strength.value_counts(sort=False).items()},
      'filled_by_strength':{
         str(k):{'N':int(len(g)),'SumR':float(g.R.sum()),'EV':float(g.R.mean()),'WR':float((g.R>0).mean())}
         for k,g in ff.groupby('flip_strength',observed=False) if len(g)
      },
      'filled_by_confirm_bar':{
         str(int(k)):{'N':int(len(g)),'SumR':float(g.R.sum()),'EV':float(g.R.mean()),'WR':float((g.R>0).mean())}
         for k,g in ff.groupby('confirm_bars') if len(g)
      },
      'filled_by_direction':{
         str(k):{'N':int(len(g)),'SumR':float(g.R.sum()),'EV':float(g.R.mean()),'WR':float((g.R>0).mean())}
         for k,g in ff.groupby('direction') if len(g)
      }
    }

def paired_stats(pair):
    common=pair[pair.category=='COMMON']
    rem=pair[pair.category=='REMOVED_BASE']
    add=pair[pair.category=='ADDED_CAND']
    return {
      'baseline_only_removed':{
        'N':int(len(rem)),'SumR':float(rem.b_R.sum()),'EV':float(rem.b_R.mean()) if len(rem) else 0,
        'direct_sign_flip_N':int(rem.baseline_sign_flip.sum()),
        'direct_sign_flip_SumR':float(rem.loc[rem.baseline_sign_flip,'b_R'].sum())
      },
      'candidate_only_added':{
        'N':int(len(add)),'SumR':float(add.c_R.sum()),'EV':float(add.c_R.mean()) if len(add) else 0
      },
      'common':{
        'N':int(len(common)),'baseline_SumR':float(common.b_R.sum()),
        'candidate_SumR':float(common.c_R.sum()),'delta_R':float(common.delta_R.sum()),
        'identical_entry_N':int((common.b_entry_ts==common.c_entry_ts).sum())
      },
      'reconciliation':{
        'baseline_total_R':float(pair.b_R.fillna(0).sum()),
        'candidate_total_R':float(pair.c_R.fillna(0).sum()),
        'delta_R':float(pair.delta_R.sum()),
        'decomp_delta_R':float(add.c_R.sum()-rem.b_R.sum()+common.delta_R.sum())
      }
    }

def main():
    hist,fwd=load_data()
    _=core.sim(*[x[:min(2000,len(x))] for x in hist],RETRACE,TTL,0,0)

    hb,hbdf,hc,hcdf=run_pair(hist,'hist')
    fb,fbdf,fc,fcdf=run_pair(fwd,'fwd')
    hp=outer_decomp(hbdf,hcdf)
    fp=outer_decomp(fbdf,fcdf)

    he=event_audit(hist)
    fe=event_audit(fwd)

    hweek=week_delta_series(hp,hist[0][0],hist[0][-1])
    fweek=week_delta_series(fp,fwd[0][0],fwd[0][-1])

    result={
      'lab':'LAB035B_SIGN_FLIP_STABILITY_AND_PAIRED_EVENT_AUDIT',
      'candidate':'CANCEL_SIGN_FLIP',
      'frozen':{'retrace_ATR':RETRACE,'TTL_min':TTL//60,'Z':core.ZTH,'confirm_ATR':core.CONF,
                'SL_ATR':core.SL,'TP_ATR':core.TP,'hold_h':core.HOLD/3600,'cost_bps':core.COST_BPS},
      'headline':{
        'historical_baseline':hb,'historical_candidate':hc,
        'forward_baseline':fb,'forward_candidate':fc
      },
      'paired_decomposition':{
        'historical':paired_stats(hp),
        'forward':paired_stats(fp)
      },
      'preserve_sequence_event_audit':{
        'historical':flip_breakdown(he),
        'forward':flip_breakdown(fe)
      },
      'stability':{
        'historical_year_delta':year_month_delta(hp,'year'),
        'forward_month_delta':year_month_delta(fp,'month'),
        'historical_leave_one_year_out':leave_one_year_out(hp),
        'historical_week_concentration':concentration(hp),
        'forward_week_concentration':concentration(fp),
        'historical_4week_block_bootstrap':moving_block_bootstrap(hweek.to_numpy(),seed=SEED),
        'forward_4week_block_bootstrap':moving_block_bootstrap(fweek.to_numpy(),seed=SEED+1)
      },
      'promotion_gate':{
        'requirements':[
          'historical total delta > 0',
          '>=4/5 historical years non-negative delta',
          'historical leave-one-year-out delta > 0 for every omitted year',
          'forward total delta > 0',
          '>=4/6 forward months non-negative delta',
          'historical 4-week bootstrap P(delta>0) >= 0.80',
          'forward 4-week bootstrap P(delta>0) >= 0.70',
          'after removing top 3 positive historical weeks, net delta remains > 0'
        ]
      },
      'limitations':[
        '2021-2025 is discovery/in-sample; 2026 Mar-Aug is reused forward-shadow, not pristine OOS.',
        'This audit is BTC only; ETH/SOL transfer is not established.',
        'Bootstrap is a descriptive stability diagnostic, not an independent significance test.',
        'Stateful cancellation changes future reachability; paired decomposition is therefore required and direct removed-trade PnL alone is insufficient.'
      ]
    }

    yd=result['stability']['historical_year_delta']
    md=result['stability']['forward_month_delta']
    loo=result['stability']['historical_leave_one_year_out']
    hcq=result['stability']['historical_week_concentration']
    gates={
      'historical_delta_positive':hp.delta_R.sum()>0,
      'historical_years_nonnegative_4of5':sum(x['delta_R']>=0 for x in yd)>=4,
      'leave_one_year_out_all_positive':all(x['remaining_delta_R']>0 for x in loo),
      'forward_delta_positive':fp.delta_R.sum()>0,
      'forward_months_nonnegative_4of6':sum(x['delta_R']>=0 for x in md)>=4,
      'historical_bootstrap_ge_080':result['stability']['historical_4week_block_bootstrap']['p_bootstrap_sumR_gt_0']>=.80,
      'forward_bootstrap_ge_070':result['stability']['forward_4week_block_bootstrap']['p_bootstrap_sumR_gt_0']>=.70,
      'hist_after_top3_positive_weeks_positive':hcq['net_after_removing_top3_positive_weeks_R']>0
    }
    result['promotion_gate']['checks']=gates
    result['promotion_gate']['pass']=bool(all(gates.values()))

    (OUT/'LAB035B_summary.json').write_text(json.dumps(result,indent=2))
    hp.to_csv(OUT/'LAB035B_historical_paired_events.csv',index=False)
    fp.to_csv(OUT/'LAB035B_forward_paired_events.csv',index=False)
    he.to_csv(OUT/'LAB035B_historical_preserve_confirmed_events.csv',index=False)
    fe.to_csv(OUT/'LAB035B_forward_preserve_confirmed_events.csv',index=False)

    def fmt(m):
        return f"N={m['N']} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f}"

    lines=[
      '# LAB035B — SIGN_FLIP_STABILITY_AND_PAIRED_EVENT_AUDIT','',
      'Frozen geometry: Z2.05 -> M15 confirm .25 ATR -> retrace .60 ATR -> TTL20 -> SL4.5 -> TP10 -> H24.','',
      '## Headline',
      f"- historical PRESERVE: {fmt(hb)}",
      f"- historical CANCEL_SIGN_FLIP: {fmt(hc)}",
      f"- forward PRESERVE: {fmt(fb)}",
      f"- forward CANCEL_SIGN_FLIP: {fmt(fc)}",'',
      '## Paired sequence decomposition',
      json.dumps(result['paired_decomposition'],indent=2),'',
      '## Preserve-sequence direct sign-flip event audit',
      json.dumps(result['preserve_sequence_event_audit'],indent=2),'',
      '## Stability','### Historical year delta'
    ]
    for x in yd:
        lines.append(f"- {x['bucket']}: {x['delta_R']:+.3f}R (removed {x['removed_R']:+.3f}, added {x['added_R']:+.3f}, common {x['common_delta_R']:+.3f})")
    lines += ['','### 2026 forward month delta']
    for x in md:
        lines.append(f"- {x['bucket']}: {x['delta_R']:+.3f}R")
    lines += ['','### Leave-one-year-out historical']
    for x in loo:
        lines.append(f"- exclude {x['left_out_year']}: remaining delta {x['remaining_delta_R']:+.3f}R")
    lines += ['','### Concentration / bootstrap',
      f"- historical after removing top-3 positive weeks: {hcq['net_after_removing_top3_positive_weeks_R']:+.3f}R",
      f"- historical top-3 share of positive contribution: {hcq['top3_share_of_positive']:.1%}",
      f"- historical bootstrap: {json.dumps(result['stability']['historical_4week_block_bootstrap'])}",
      f"- forward bootstrap: {json.dumps(result['stability']['forward_4week_block_bootstrap'])}",'',
      '## Promotion gate',
      f"- PASS: **{result['promotion_gate']['pass']}**",
      json.dumps(gates,indent=2),'',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'LAB035B_REPORT.md').write_text('\n'.join(lines))
    print((OUT/'LAB035B_REPORT.md').read_text())

if __name__=='__main__':
    main()
