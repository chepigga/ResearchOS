# LAB048_TRIGGER
from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Reuse validated LAB047/LAB046 construction and common loaders.
p47=Path(__file__).resolve().parents[1]/'CROWDFADE_V191_DUAL_TOXIC_GATE_EXIT_GEOMETRY_LAB_047'/'run.py'
spec=importlib.util.spec_from_file_location('lab047',p47)
lab047=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab047)

lab047.DATA=DATA
lab047.lab046.DATA=DATA
lab047.lab046.lab045.DATA=DATA
lab047.lab046.lab045.lab44.DATA=DATA
lab047.lab046.lab045.lab44.lab43.DATA=DATA

lab046=lab047.lab046
lab43=lab047.lab43

COST_BPS=lab43.COST_BPS
MAXDAY=lab43.MAXDAY
PAUSE_ATR=lab43.PAUSE_ATR
V191_Z=lab43.V191_Z
V191_CONFIRM_ATR=lab43.V191_CONFIRM_ATR

CONTROL=0
A3P5_G0P5=1
A5P0_G0P5=2
A2P5_G1P0=3
A3P5_G1P0=4
A5P0_G1P0=5
TRAIL_OFF=6

NAMES={
    CONTROL:'CONTROL_A2P5_G0P5',
    A3P5_G0P5:'A3P5_G0P5',
    A5P0_G0P5:'A5P0_G0P5',
    A2P5_G1P0:'A2P5_G1P0',
    A3P5_G1P0:'A3P5_G1P0',
    A5P0_G1P0:'A5P0_G1P0',
    TRAIL_OFF:'TRAIL_OFF',
}

REASONS={1:'SL',2:'PROTECTED_STOP',3:'EXIT_Z',4:'TIME'}

@njit(cache=True)
def trail_cfg(v):
    # arm_atr, gap_atr, use_trail
    if v==A3P5_G0P5:
        return 3.5,0.5,1
    if v==A5P0_G0P5:
        return 5.0,0.5,1
    if v==A2P5_G1P0:
        return 2.5,1.0,1
    if v==A3P5_G1P0:
        return 3.5,1.0,1
    if v==A5P0_G1P0:
        return 5.0,1.0,1
    if v==TRAIL_OFF:
        return 0.0,0.0,0
    return 2.5,0.5,1

@njit(cache=True)
def manage_trail(ts,H,L,C,dt5,Z5,ei,side,entry,atr,variant):
    arm,gap,use_trail=trail_cfg(variant)
    risk=1.50*atr
    stop=entry-side*risk
    peak=entry
    pending_stop=stop

    xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+21600,'left'))
    xp=C[xe]
    ex=xe
    reason=4

    for q in range(ei+1,xe+1):
        stop=pending_stop

        # Exact LAB047 control ordering: stop -> update peak -> BE -> trail -> ExitZ.
        if (side>0 and L[q]<=stop) or (side<0 and H[q]>=stop):
            protected=(side>0 and stop>entry) or (side<0 and stop<entry)
            xp=stop
            ex=q
            reason=2 if protected else 1
            break

        if side>0:
            if H[q]>peak:
                peak=H[q]
            fav=(peak-entry)/atr
        else:
            if L[q]<peak:
                peak=L[q]
            fav=(entry-peak)/atr

        ns=stop

        # Frozen BE from LAB047.
        if fav>=0.50:
            lvl=entry+side*0.15*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):
                ns=lvl

        # Only LAB048 dimension.
        if use_trail==1 and fav>=arm:
            lvl=peak-side*gap*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):
                ns=lvl

        pending_stop=ns

        # Frozen ExitZ.
        zi=np.searchsorted(dt5,ts[q],'right')-1
        if zi>=0:
            z=Z5[zi]
            if (side>0 and z>=0.75) or (side<0 and z<=-0.75):
                xp=C[q]
                ex=q
                reason=3
                break

    rr=side*(xp-entry)/risk-(COST_BPS/10000.0)*entry/risk
    return rr,ex,reason

@njit(cache=True)
def sim_trail(ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5,rapid,highvol,variant):
    cap=len(dt5)
    R=np.zeros(cap)
    ST=np.zeros(cap,np.int64)
    ET=np.zeros(cap,np.int64)
    XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8)
    RS=np.zeros(cap,np.int8)
    AGE=np.zeros(cap)
    CZ=np.zeros(cap)
    ADV=np.zeros(cap)
    SIGZ=np.zeros(cap)

    n=0
    k=0
    day=-1
    dc=0
    nextts=0
    last=0.0
    la=0.0
    has=False

    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts:
            k+=1
            continue

        d=t//86400
        if d!=day:
            day=d
            dc=0
        if dc>=MAXDAY:
            k+=1
            continue

        z0=Z5[k]
        side=-1 if z0>=V191_Z else (1 if z0<=-V191_Z else 0)
        if side==0:
            k+=1
            continue

        # Frozen LAB046 dual toxic-state veto.
        if rapid[k]==1 or highvol[k]==1:
            k+=1
            continue

        sig=C5[k]
        atr=A5[k]
        if has and abs(sig-last)<PAUSE_ATR*la:
            k+=1
            continue

        target=sig+side*V191_CONFIRM_ATR*atr
        ps=np.searchsorted(ts,t+1)
        pe=np.searchsorted(ts,t+2700,'right')
        ci=-1
        maxadv=0.0

        for q in range(ps,min(len(ts),pe)):
            adv=((H[q]-sig) if side<0 else (sig-L[q]))/atr
            if adv>maxadv:
                maxadv=adv
            if maxadv>0.75:
                ci=-2
                break
            if (side>0 and C[q]>=target) or (side<0 and C[q]<=target):
                ci=q
                break

        if ci<0:
            k+=1
            continue

        zi=np.searchsorted(dt5,ts[ci],'right')-1
        if zi<0:
            k+=1
            continue
        cz=Z5[zi]

        # Frozen v191d confirmation consistency.
        if (side>0 and cz>=0.75) or (side<0 and cz<=-0.75):
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        entry=C[ci]
        rr,ex,reason=manage_trail(ts,H,L,C,dt5,Z5,ci,side,entry,atr,variant)

        R[n]=rr
        ST[n]=t
        ET[n]=ts[ci]
        XT[n]=ts[ex]
        SIDE[n]=side
        RS[n]=reason
        AGE[n]=(ts[ci]-t)/60.0
        CZ[n]=cz
        ADV[n]=maxadv
        SIGZ[n]=z0
        n+=1

        dc+=1
        last=entry
        la=atr
        has=True
        nextts=ts[ex]+1
        k=np.searchsorted(dt5,nextts)

    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],RS[:n],AGE[:n],CZ[:n],ADV[:n],SIGZ[:n]

def make_df(z):
    R,st,et,xt,side,rs,age,cz,adv,sigz=z
    return pd.DataFrame({
        'R':R,
        'signal_ts':st,
        'entry_ts':et,
        'exit_ts':xt,
        'hold_min':(xt-et)/60.0,
        'side':side,
        'exit_reason':[REASONS.get(int(x),'?') for x in rs],
        'confirm_age_min':age,
        'confirm_z':cz,
        'max_adverse_atr':adv,
        'signal_z':sigz,
        'signal_abs_z':np.abs(sigz),
    })

def metrics(df):
    return lab43.metrics(df.R.to_numpy(float)) if len(df) else {'N':0}

def period_key(df,mode):
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    return t.dt.year.astype(str) if mode=='year' else t.dt.strftime('%Y-%m')

def period_stats(df,mode):
    if len(df)==0:
        return {}
    key=period_key(df,mode)
    return {str(k):metrics(g) for k,g in df.groupby(key,sort=True)}

def tail_diag(df,mode):
    if len(df)==0:
        return {}
    r=df.R.to_numpy(float)
    desc=np.sort(r)[::-1]
    pos=np.sort(r[r>0])[::-1]
    gross_pos=float(pos.sum()) if len(pos) else 0.0

    def top_sum(n):
        return float(pos[:n].sum()) if len(pos) else 0.0

    key=period_key(df,mode)
    period_trim={}
    for k,g in df.groupby(key,sort=True):
        vals=g.R.to_numpy(float)
        best=float(np.max(vals)) if len(vals) else 0.0
        raw=float(vals.sum())
        trim=raw-best
        period_trim[str(k)]={'raw_SumR':raw,'best_trade_R':best,'SumR_ex_best':trim,'positive_after_trim':bool(trim>0)}

    return {
        'max_trade_R':float(desc[0]) if len(desc) else None,
        'gross_positive_SumR':gross_pos,
        'top1_positive_SumR':top_sum(1),
        'top5_positive_SumR':top_sum(5),
        'top10_positive_SumR':top_sum(10),
        'top1_share_gross_positive':float(top_sum(1)/gross_pos) if gross_pos>0 else None,
        'top5_share_gross_positive':float(top_sum(5)/gross_pos) if gross_pos>0 else None,
        'top10_share_gross_positive':float(top_sum(10)/gross_pos) if gross_pos>0 else None,
        'SumR_ex_top1':float(r.sum()-desc[:1].sum()),
        'SumR_ex_top5':float(r.sum()-desc[:5].sum()),
        'SumR_ex_top10':float(r.sum()-desc[:10].sum()),
        'period_top1_trim':period_trim,
        'positive_periods_after_top1_trim':int(sum(1 for x in period_trim.values() if x['positive_after_trim'])),
        'periods_total':int(len(period_trim)),
    }

def summarize(df,mode):
    if not len(df):
        return {'all':{'N':0},'periods':{},'exit_reasons':{},'hold':{},'tail':{}}
    return {
        'all':metrics(df),
        'periods':period_stats(df,mode),
        'exit_reasons':{str(k):int(v) for k,v in df.exit_reason.value_counts().items()},
        'hold':{
            'median_min':float(df.hold_min.median()),
            'p90_min':float(df.hold_min.quantile(0.90)),
            'mean_min':float(df.hold_min.mean()),
        },
        'tail':tail_diag(df,mode),
    }

def matched_vs_control(base,other):
    kb=set(zip(base.signal_ts.astype(np.int64),base.side.astype(int)))
    ko=set(zip(other.signal_ts.astype(np.int64),other.side.astype(int)))
    onlyb=base[[((int(x),int(y)) in (kb-ko)) for x,y in zip(base.signal_ts,base.side)]]
    onlyo=other[[((int(x),int(y)) in (ko-kb)) for x,y in zip(other.signal_ts,other.side)]]
    common=kb&ko
    bm={(int(x),int(y)):float(r) for x,y,r in zip(base.signal_ts,base.side,base.R)}
    om={(int(x),int(y)):float(r) for x,y,r in zip(other.signal_ts,other.side,other.R)}
    return {
        'N_control':int(len(base)),
        'N_variant':int(len(other)),
        'frequency_ratio':float(len(other)/len(base)) if len(base) else None,
        'delta_N':int(len(other)-len(base)),
        'removed_signal_count':int(len(kb-ko)),
        'added_signal_count':int(len(ko-kb)),
        'common_signal_count':int(len(common)),
        'removed_trade_sumR':float(onlyb.R.sum()),
        'added_trade_sumR':float(onlyo.R.sum()),
        'common_signal_outcome_deltaR':float(sum(om[k]-bm[k] for k in common)),
        'full_sequence_deltaR':float(other.R.sum()-base.R.sum()),
    }

def parity_check(a,b,label):
    ok=(len(a)==len(b))
    if ok and len(a):
        ok=(
            np.array_equal(a[['signal_ts','side']].to_numpy(),b[['signal_ts','side']].to_numpy())
            and np.allclose(a.R.to_numpy(float),b.R.to_numpy(float),atol=1e-12,rtol=0)
        )
    if not ok:
        raise RuntimeError(label)

def run_period(raw,ft,fz,start,end,label):
    p=lab43.prep(raw,ft,fz,start,end)
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p

    vol,gap=lab046.build_signal_features(p)
    rapid=(np.isfinite(gap)&(gap<=30.0)).astype(np.int8)
    highvol=(vol==1).astype(np.int8)

    mode='year' if label=='historical' else 'month'
    out={}
    frames={}

    for v in range(7):
        d=make_df(sim_trail(*p,rapid,highvol,v))
        d.to_csv(OUT/f'{label}_{NAMES[v]}.csv',index=False)
        frames[NAMES[v]]=d
        out[NAMES[v]]=summarize(d,mode)

    # Hard parity anchors against LAB047.
    d47_control=lab047.make_df(lab047.sim_exit(*p,rapid,highvol,lab047.CONTROL))
    d47_off=lab047.make_df(lab047.sim_exit(*p,rapid,highvol,lab047.TRAIL_OFF))
    parity_check(frames['CONTROL_A2P5_G0P5'],d47_control,'LAB048 CONTROL parity failure vs LAB047 CONTROL')
    parity_check(frames['TRAIL_OFF'],d47_off,'LAB048 TRAIL_OFF parity failure vs LAB047 TRAIL_OFF')

    # Immutable v192 reference.
    d192=lab43.df192(lab43.sim_v192(*p))
    d192['hold_min']=(d192.exit_ts-d192.entry_ts)/60.0
    d192['exit_reason']='V192_NATIVE'
    d192.to_csv(OUT/f'{label}_V192_CANONICAL_CONTROL.csv',index=False)
    frames['V192_CANONICAL_CONTROL']=d192
    out['V192_CANONICAL_CONTROL']={
        'all':lab43.metrics(d192.R.to_numpy(float)),
        'periods':lab43.summarize(d192,mode)['periods'],
        'exit_reasons':lab43.summarize(d192,mode).get('exit_reasons',{}),
        'hold':{
            'median_min':float(d192.hold_min.median()),
            'p90_min':float(d192.hold_min.quantile(0.90)),
            'mean_min':float(d192.hold_min.mean()),
        },
        'tail':tail_diag(d192,mode),
    }

    control=frames['CONTROL_A2P5_G0P5']
    matched={}
    for name,d in frames.items():
        if name!='CONTROL_A2P5_G0P5':
            matched[name]=matched_vs_control(control,d)

    return out,frames,matched

def classify(name,h,f,hc,fc,hoff,foff):
    hm=h['all']; fm=f['all']
    hy=sum(1 for x in h.get('periods',{}).values() if x.get('SumR',0)>0)
    fy=sum(1 for x in f.get('periods',{}).values() if x.get('SumR',0)>0)

    base=(
        hm.get('N',0)>0 and fm.get('N',0)>0
        and hm.get('EV',-1)>0 and hm.get('PF',0)>1
        and fm.get('EV',-1)>0 and fm.get('PF',0)>1
        and hy>=4 and len(h.get('periods',{}))>=5
        and fy>=4 and len(f.get('periods',{}))>=6
        and hm.get('N',0)>=0.90*hc['all'].get('N',0)
        and fm.get('N',0)>=0.90*fc['all'].get('N',0)
    )

    dd_vs_off=(
        hm.get('MaxDD_R',np.inf)<=hoff['all'].get('MaxDD_R',np.inf)
        and fm.get('MaxDD_R',np.inf)<=foff['all'].get('MaxDD_R',np.inf)
    )

    ftd=f.get('tail',{})
    fot=foff.get('tail',{})
    tail_vs_off=(
        ftd.get('top1_share_gross_positive',np.inf)<=fot.get('top1_share_gross_positive',np.inf)
        and ftd.get('top5_share_gross_positive',np.inf)<=fot.get('top5_share_gross_positive',np.inf)
    )

    hist_improve=(hm.get('SumR',-np.inf)>hc['all'].get('SumR',-np.inf) or hm.get('R_DD',-np.inf)>hc['all'].get('R_DD',-np.inf))
    fwd_improve=(fm.get('SumR',-np.inf)>fc['all'].get('SumR',-np.inf) or fm.get('R_DD',-np.inf)>fc['all'].get('R_DD',-np.inf))

    hist_dominated=(hm.get('SumR',np.inf)<hc['all'].get('SumR',np.inf) and hm.get('R_DD',np.inf)<hc['all'].get('R_DD',np.inf))
    fwd_dominated=(fm.get('SumR',np.inf)<fc['all'].get('SumR',np.inf) and fm.get('R_DD',np.inf)<fc['all'].get('R_DD',np.inf))

    cross_sample_gain=((hist_improve and not fwd_dominated) or (fwd_improve and not hist_dominated))
    pareto=base and dd_vs_off and tail_vs_off and cross_sample_gain

    robust_trim=(
        h.get('tail',{}).get('positive_periods_after_top1_trim',0)>=3
        and f.get('tail',{}).get('positive_periods_after_top1_trim',0)>=3
        and h.get('tail',{}).get('SumR_ex_top5',-np.inf)>0
        and f.get('tail',{}).get('SumR_ex_top5',-np.inf)>0
    )
    robust_pareto=pareto and robust_trim

    if robust_pareto:
        verdict='ROBUST_PARETO'
    elif pareto:
        verdict='PARETO_ELIGIBLE'
    elif base:
        verdict='BASE_ROBUST_ONLY'
    else:
        verdict='FAILED_BASE_ROBUSTNESS'

    return {
        'role':'CONTROL_ANCHOR' if name=='CONTROL_A2P5_G0P5' else ('TRAIL_OFF_ANCHOR' if name=='TRAIL_OFF' else 'CANDIDATE'),
        'verdict':verdict,
        'base_robust':bool(base),
        'pareto_eligible':bool(pareto),
        'robust_pareto':bool(robust_pareto),
        'dd_vs_trail_off_ok':bool(dd_vs_off),
        'forward_tail_vs_trail_off_ok':bool(tail_vs_off),
        'cross_sample_gain_vs_control':bool(cross_sample_gain),
        'positive_historical_years':int(hy),
        'positive_forward_months':int(fy),
        'historical_positive_periods_after_top1_trim':int(h.get('tail',{}).get('positive_periods_after_top1_trim',0)),
        'forward_positive_periods_after_top1_trim':int(f.get('tail',{}).get('positive_periods_after_top1_trim',0)),
    }

def fmt(m):
    if m.get('N',0)==0:
        return 'N=0'
    return (
        f"N={m['N']} WR={m['WR']:.1%} EV={m['EV']:+.4f} PF={m['PF']:.3f} "
        f"Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f}"
    )

def main():
    ft,fz=lab43.load_flow()
    hist=lab43.load_hist()
    sec=lab43.load_sec()

    h,hframes,hm=run_period(
        hist,ft,fz,
        int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),
        'historical'
    )
    f,fframes,fm=run_period(
        sec,ft,fz,
        int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),
        'forward'
    )

    hc=h['CONTROL_A2P5_G0P5']
    fc=f['CONTROL_A2P5_G0P5']
    hoff=h['TRAIL_OFF']
    foff=f['TRAIL_OFF']

    decisions={}
    for name in NAMES.values():
        decisions[name]=classify(name,h[name],f[name],hc,fc,hoff,foff)

    result={
        'lab':'CROWDFADE_V191_TRAILING_RIGHT_TAIL_PARETO_LAB_048',
        'preregistration':'PREREG.md committed before execution.',
        'grid':{
            'CONTROL_A2P5_G0P5':{'arm_atr':2.5,'gap_atr':0.5},
            'A3P5_G0P5':{'arm_atr':3.5,'gap_atr':0.5},
            'A5P0_G0P5':{'arm_atr':5.0,'gap_atr':0.5},
            'A2P5_G1P0':{'arm_atr':2.5,'gap_atr':1.0},
            'A3P5_G1P0':{'arm_atr':3.5,'gap_atr':1.0},
            'A5P0_G1P0':{'arm_atr':5.0,'gap_atr':1.0},
            'TRAIL_OFF':{'arm_atr':None,'gap_atr':None},
        },
        'historical':h,
        'forward_2026_shadow':f,
        'matched_vs_control':{'historical':hm,'forward_2026_shadow':fm},
        'decisions':decisions,
        'limitations':[
            'BTCUSDT only; transfer to other crypto symbols is not established.',
            'Historical 2021-2025 uses 1m OHLC; 2026 Mar-Aug uses second OHLC.',
            '2026 is reused forward-shadow/stress, not pristine OOS.',
            'Grid was fixed before execution and was not selected from individual LAB047 winner paths.',
            'Every trailing candidate is a full stateful rerun; exits alter occupancy and later signal reachability.',
            'Trailing behavior is approximated on the common research execution frame; MT5 live execution remains separate.',
            'Flat 0.5bps cost proxy; broker-specific execution remains separate.',
        ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    rows=[]
    for period,d in [('historical',h),('2026',f)]:
        for name,v in d.items():
            row={'period':period,'variant':name,**v['all']}
            row.update({
                'median_hold_min':v.get('hold',{}).get('median_min',np.nan),
                'p90_hold_min':v.get('hold',{}).get('p90_min',np.nan),
                'max_trade_R':v.get('tail',{}).get('max_trade_R',np.nan),
                'top1_share_gross_positive':v.get('tail',{}).get('top1_share_gross_positive',np.nan),
                'top5_share_gross_positive':v.get('tail',{}).get('top5_share_gross_positive',np.nan),
                'SumR_ex_top1':v.get('tail',{}).get('SumR_ex_top1',np.nan),
                'SumR_ex_top5':v.get('tail',{}).get('SumR_ex_top5',np.nan),
                'positive_periods_after_top1_trim':v.get('tail',{}).get('positive_periods_after_top1_trim',np.nan),
            })
            rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)

    drows=[]
    for name,x in decisions.items():
        drows.append({
            'variant':name,**x,
            'hist_N':h[name]['all'].get('N',0),
            'hist_EV':h[name]['all'].get('EV',np.nan),
            'hist_PF':h[name]['all'].get('PF',np.nan),
            'hist_SumR':h[name]['all'].get('SumR',np.nan),
            'hist_DD':h[name]['all'].get('MaxDD_R',np.nan),
            'hist_R_DD':h[name]['all'].get('R_DD',np.nan),
            'hist_top1_share_gp':h[name]['tail'].get('top1_share_gross_positive',np.nan),
            'hist_top5_share_gp':h[name]['tail'].get('top5_share_gross_positive',np.nan),
            'hist_SumR_ex_top5':h[name]['tail'].get('SumR_ex_top5',np.nan),
            'fwd_N':f[name]['all'].get('N',0),
            'fwd_EV':f[name]['all'].get('EV',np.nan),
            'fwd_PF':f[name]['all'].get('PF',np.nan),
            'fwd_SumR':f[name]['all'].get('SumR',np.nan),
            'fwd_DD':f[name]['all'].get('MaxDD_R',np.nan),
            'fwd_R_DD':f[name]['all'].get('R_DD',np.nan),
            'fwd_top1_share_gp':f[name]['tail'].get('top1_share_gross_positive',np.nan),
            'fwd_top5_share_gp':f[name]['tail'].get('top5_share_gross_positive',np.nan),
            'fwd_SumR_ex_top5':f[name]['tail'].get('SumR_ex_top5',np.nan),
        })
    pd.DataFrame(drows).to_csv(OUT/'decision_table.csv',index=False)

    mrows=[]
    for period,matches in [('historical',hm),('2026',fm)]:
        for name,x in matches.items():
            mrows.append({'period':period,'variant':name,**x})
    pd.DataFrame(mrows).to_csv(OUT/'matched_reachability_vs_control.csv',index=False)

    lines=[
        '# LAB048 — V191 TRAILING RIGHT-TAIL PARETO','',
        'Entry/gates and all non-trailing management are frozen from LAB047 control.','',
        '**Only trailing arm/gap changes. All variants are stateful replays.**','',
        '## Aggregate results'
    ]

    for period,d in [('Historical 2021–2025',h),('2026 Mar–Aug shadow',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items():
            t=v.get('tail',{})
            lines.append(
                f"- {name}: {fmt(v['all'])}; "
                f"top1/gross+={t.get('top1_share_gross_positive')}; "
                f"top5/gross+={t.get('top5_share_gross_positive')}; "
                f"Sum ex top5={t.get('SumR_ex_top5')}; "
                f"trim-positive periods={t.get('positive_periods_after_top1_trim')}/{t.get('periods_total')}"
            )

    lines += ['','## Pre-registered decisions']
    for name,x in decisions.items():
        lines.append(f"- {name}: **{x['verdict']}** — {json.dumps(x)}")

    lines += ['','## Historical yearly metrics']
    for name,v in h.items():
        lines.append(f"- {name}: {json.dumps(v['periods'])}")

    lines += ['','## 2026 monthly metrics']
    for name,v in f.items():
        lines.append(f"- {name}: {json.dumps(v['periods'])}")

    lines += ['','## Historical top-1-trim by year']
    for name,v in h.items():
        lines.append(f"- {name}: {json.dumps(v.get('tail',{}).get('period_top1_trim',{}))}")

    lines += ['','## 2026 top-1-trim by month']
    for name,v in f.items():
        lines.append(f"- {name}: {json.dumps(v.get('tail',{}).get('period_top1_trim',{}))}")

    lines += ['','## Stateful reachability vs control — historical']
    for name,x in hm.items():
        lines.append(f"- {name}: {json.dumps(x)}")

    lines += ['','## Stateful reachability vs control — 2026']
    for name,x in fm.items():
        lines.append(f"- {name}: {json.dumps(x)}")

    lines += ['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
