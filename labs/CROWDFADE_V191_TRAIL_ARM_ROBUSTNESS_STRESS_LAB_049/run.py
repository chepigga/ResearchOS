# LAB049_TRIGGER
from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Reuse frozen LAB048/LAB047/LAB046 construction and data loaders.
p48=Path(__file__).resolve().parents[1]/'CROWDFADE_V191_TRAILING_RIGHT_TAIL_PARETO_LAB_048'/'run.py'
spec=importlib.util.spec_from_file_location('lab048',p48)
lab048=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab048)

lab048.DATA=DATA
lab048.lab047.DATA=DATA
lab048.lab047.lab046.DATA=DATA
lab048.lab047.lab046.lab045.DATA=DATA
lab048.lab047.lab046.lab045.lab44.DATA=DATA
lab048.lab047.lab046.lab045.lab44.lab43.DATA=DATA

lab047=lab048.lab047
lab046=lab048.lab046
lab43=lab048.lab43

MAXDAY=lab43.MAXDAY
PAUSE_ATR=lab43.PAUSE_ATR
V191_Z=lab43.V191_Z
V191_CONFIRM_ATR=lab43.V191_CONFIRM_ATR

CONTROL=0
BALANCED=1
AGGRESSIVE=2

CONFIG_NAMES={
    CONTROL:'CONTROL_A2P5_G0P5',
    BALANCED:'BALANCED_A3P5_G0P5',
    AGGRESSIVE:'AGGRESSIVE_A5P0_G0P5',
}

SCENARIOS={
    'S0_BASE':(0.5,0),
    'S1_COST_1BPS':(1.0,0),
    'S2_COST_2BPS':(2.0,0),
    'S3_DELAY_60S':(0.5,60),
    'S4_DELAY_180S':(0.5,180),
    'S5_ADVERSE_COMBINED':(2.0,180),
}

REASONS={1:'SL',2:'PROTECTED_STOP',3:'EXIT_Z',4:'TIME'}

@njit(cache=True)
def arm_cfg(config_id):
    if config_id==BALANCED:
        return 3.5
    if config_id==AGGRESSIVE:
        return 5.0
    return 2.5

@njit(cache=True)
def manage_stress(ts,H,L,C,dt5,Z5,ei,side,entry,atr,arm,cost_bps):
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

        # Frozen BE.
        if fav>=0.50:
            lvl=entry+side*0.15*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):
                ns=lvl

        # Frozen 0.5 ATR gap; only arm differs by frozen config.
        if fav>=arm:
            lvl=peak-side*0.50*atr
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

    rr=side*(xp-entry)/risk-(cost_bps/10000.0)*entry/risk
    return rr,ex,reason

@njit(cache=True)
def sim_stress(ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5,rapid,highvol,config_id,cost_bps,delay_sec):
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
    DELAY=np.zeros(cap)

    n=0
    k=0
    day=-1
    dc=0
    nextts=0
    last=0.0
    la=0.0
    has=False
    arm=arm_cfg(config_id)

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

        if (side>0 and cz>=0.75) or (side<0 and cz<=-0.75):
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        # Execution perturbation begins only after the original valid confirmation.
        ei=ci
        if delay_sec>0:
            ei=np.searchsorted(ts,ts[ci]+delay_sec,'left')
            if ei>=len(ts):
                break

        entry=C[ei]
        rr,ex,reason=manage_stress(ts,H,L,C,dt5,Z5,ei,side,entry,atr,arm,cost_bps)

        R[n]=rr
        ST[n]=t
        ET[n]=ts[ei]
        XT[n]=ts[ex]
        SIDE[n]=side
        RS[n]=reason
        AGE[n]=(ts[ci]-t)/60.0
        CZ[n]=cz
        ADV[n]=maxadv
        SIGZ[n]=z0
        DELAY[n]=(ts[ei]-ts[ci])
        n+=1

        dc+=1
        last=entry
        la=atr
        has=True
        nextts=ts[ex]+1
        k=np.searchsorted(dt5,nextts)

    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],RS[:n],AGE[:n],CZ[:n],ADV[:n],SIGZ[:n],DELAY[:n]

def make_df(z):
    R,st,et,xt,side,rs,age,cz,adv,sigz,delay=z
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
        'execution_delay_sec':delay,
    })

def metrics_r(r):
    arr=np.asarray(r,dtype=float)
    return lab43.metrics(arr) if len(arr) else {'N':0}

def metrics(df):
    return metrics_r(df.R.to_numpy(float))

def period_key(df,mode):
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    return t.dt.year.astype(str) if mode=='year' else t.dt.strftime('%Y-%m')

def period_stats(df,mode,r_override=None):
    if len(df)==0:
        return {}
    tmp=df.copy()
    if r_override is not None:
        tmp['R']=np.asarray(r_override,dtype=float)
    key=period_key(tmp,mode)
    return {str(k):metrics(g) for k,g in tmp.groupby(key,sort=True)}

def tail_diag(df,mode):
    if len(df)==0:
        return {}
    r=df.R.to_numpy(float)
    pos=np.sort(r[r>0])[::-1]
    gross=float(pos.sum()) if len(pos) else 0.0
    top1=float(pos[:1].sum()) if len(pos) else 0.0
    top5=float(pos[:5].sum()) if len(pos) else 0.0

    def clip_pack(cap):
        rc=np.where(r>0,np.minimum(r,cap),r)
        m=metrics_r(rc)
        ps=period_stats(df,mode,rc)
        return {
            'cap_R':float(cap),
            'N':int(m.get('N',0)),
            'EV':float(m.get('EV',np.nan)),
            'PF':float(m.get('PF',np.nan)),
            'SumR':float(m.get('SumR',np.nan)),
            'MaxDD_R':float(m.get('MaxDD_R',np.nan)),
            'R_DD':float(m.get('R_DD',np.nan)),
            'positive_periods':int(sum(1 for x in ps.values() if x.get('SumR',0)>0)),
            'periods_total':int(len(ps)),
            'periods':ps,
        }

    return {
        'max_trade_R':float(np.max(r)),
        'gross_positive_SumR':gross,
        'top1_positive_SumR':top1,
        'top5_positive_SumR':top5,
        'top1_share_gross_positive':float(top1/gross) if gross>0 else None,
        'top5_share_gross_positive':float(top5/gross) if gross>0 else None,
        'SumR_ex_top1':float(r.sum()-top1),
        'SumR_ex_top5':float(r.sum()-top5),
        'clip_5R':clip_pack(5.0),
        'clip_3R':clip_pack(3.0),
    }

def summarize(df,mode,with_tail=False):
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
        'tail':tail_diag(df,mode) if with_tail else {},
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

    results={}
    frames={}
    matched={}

    for scenario,(cost,delay) in SCENARIOS.items():
        results[scenario]={}
        frames[scenario]={}

        for config_id,name in CONFIG_NAMES.items():
            d=make_df(sim_stress(*p,rapid,highvol,config_id,float(cost),int(delay)))
            d.to_csv(OUT/f'{label}_{scenario}_{name}.csv',index=False)
            frames[scenario][name]=d
            results[scenario][name]=summarize(d,mode,with_tail=(scenario in ('S0_BASE','S5_ADVERSE_COMBINED')))

        control=frames[scenario]['CONTROL_A2P5_G0P5']
        matched[scenario]={}
        for name,d in frames[scenario].items():
            if name!='CONTROL_A2P5_G0P5':
                matched[scenario][name]=matched_vs_control(control,d)

    # S0 exact parity with LAB048 frozen configurations.
    map48={
        'CONTROL_A2P5_G0P5':lab048.CONTROL,
        'BALANCED_A3P5_G0P5':lab048.A3P5_G0P5,
        'AGGRESSIVE_A5P0_G0P5':lab048.A5P0_G0P5,
    }
    for name,v48 in map48.items():
        d48=lab048.make_df(lab048.sim_trail(*p,rapid,highvol,v48))
        parity_check(frames['S0_BASE'][name],d48,f'LAB049 S0 parity failure vs LAB048: {name}')

    # Immutable v192 S0 quality reference only.
    d192=lab43.df192(lab43.sim_v192(*p))
    d192['hold_min']=(d192.exit_ts-d192.entry_ts)/60.0
    d192.to_csv(OUT/f'{label}_S0_BASE_V192_CANONICAL_CONTROL.csv',index=False)
    v192=lab43.summarize(d192,mode)

    return results,frames,matched,v192

def verdict_for(name,h,f):
    all_positive=True
    for sc in SCENARIOS:
        hm=h[sc][name]['all']
        fm=f[sc][name]['all']
        ok=(
            hm.get('N',0)>0 and fm.get('N',0)>0
            and hm.get('EV',-1)>0 and hm.get('PF',0)>1
            and fm.get('EV',-1)>0 and fm.get('PF',0)>1
        )
        all_positive=all_positive and ok

    h5=h['S5_ADVERSE_COMBINED'][name]
    f5=f['S5_ADVERSE_COMBINED'][name]
    hy=sum(1 for x in h5['periods'].values() if x.get('SumR',0)>0)
    fy=sum(1 for x in f5['periods'].values() if x.get('SumR',0)>0)

    h0=h['S0_BASE'][name]
    f0=f['S0_BASE'][name]

    freq_ok=(
        h5['all'].get('N',0)>=0.90*h0['all'].get('N',0)
        and f5['all'].get('N',0)>=0.90*f0['all'].get('N',0)
    )
    dd_ok=(
        h5['all'].get('MaxDD_R',np.inf)<=2.0*h0['all'].get('MaxDD_R',np.inf)
        and f5['all'].get('MaxDD_R',np.inf)<=2.0*f0['all'].get('MaxDD_R',np.inf)
    )
    consistency=(hy>=3 and len(h5['periods'])>=5 and fy>=3 and len(f5['periods'])>=6)
    survivor=bool(all_positive and consistency and freq_ok and dd_ok)

    tail_ok=False
    if survivor:
        tail_ok=(
            h0['tail']['clip_3R']['SumR']>0
            and f0['tail']['clip_3R']['SumR']>0
            and h5['tail']['clip_3R']['SumR']>0
            and f5['tail']['clip_3R']['SumR']>0
            and h5['tail']['SumR_ex_top5']>0
            and f5['tail']['SumR_ex_top5']>0
        )

    return {
        'stress_survivor':survivor,
        'tail_robust':bool(survivor and tail_ok),
        'all_six_scenarios_positive_both_samples':bool(all_positive),
        'combined_positive_historical_years':int(hy),
        'combined_positive_forward_months':int(fy),
        'combined_frequency_ok':bool(freq_ok),
        'combined_dd_ok':bool(dd_ok),
    }

def add_dominance(decisions,h,f):
    hc=h['S5_ADVERSE_COMBINED']['CONTROL_A2P5_G0P5']['all']
    fc=f['S5_ADVERSE_COMBINED']['CONTROL_A2P5_G0P5']['all']

    for name,x in decisions.items():
        if name=='CONTROL_A2P5_G0P5':
            x['stress_dominant_vs_control']=False
            x['verdict']='TAIL_ROBUST_CONTROL' if x['tail_robust'] else ('STRESS_SURVIVOR_CONTROL' if x['stress_survivor'] else 'FAILED_STRESS')
            continue

        hm=h['S5_ADVERSE_COMBINED'][name]['all']
        fm=f['S5_ADVERSE_COMBINED'][name]['all']
        dominant=(
            x['tail_robust']
            and hm.get('SumR',-np.inf)>hc.get('SumR',-np.inf)
            and fm.get('SumR',-np.inf)>fc.get('SumR',-np.inf)
            and hm.get('R_DD',-np.inf)>hc.get('R_DD',-np.inf)
            and fm.get('R_DD',-np.inf)>fc.get('R_DD',-np.inf)
        )
        x['stress_dominant_vs_control']=bool(dominant)
        if dominant:
            x['verdict']='STRESS_DOMINANT_VS_CONTROL'
        elif x['tail_robust']:
            x['verdict']='TAIL_ROBUST'
        elif x['stress_survivor']:
            x['verdict']='STRESS_SURVIVOR'
        else:
            x['verdict']='FAILED_STRESS'

def fmt(m):
    return (
        f"N={m.get('N',0)} EV={m.get('EV',np.nan):+.4f} PF={m.get('PF',np.nan):.3f} "
        f"Sum={m.get('SumR',np.nan):+.2f}R DD={m.get('MaxDD_R',np.nan):.2f} "
        f"R/DD={m.get('R_DD',np.nan):.3f}"
    )

def main():
    ft,fz=lab43.load_flow()
    hist=lab43.load_hist()
    sec=lab43.load_sec()

    h,hframes,hm,hv192=run_period(
        hist,ft,fz,
        int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),
        'historical'
    )
    f,fframes,fm,fv192=run_period(
        sec,ft,fz,
        int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),
        'forward'
    )

    decisions={name:verdict_for(name,h,f) for name in CONFIG_NAMES.values()}
    add_dominance(decisions,h,f)

    result={
        'lab':'CROWDFADE_V191_TRAIL_ARM_ROBUSTNESS_STRESS_LAB_049',
        'preregistration':'PREREG.md committed before execution.',
        'frozen_configs':{
            'CONTROL_A2P5_G0P5':{'arm_atr':2.5,'gap_atr':0.5},
            'BALANCED_A3P5_G0P5':{'arm_atr':3.5,'gap_atr':0.5},
            'AGGRESSIVE_A5P0_G0P5':{'arm_atr':5.0,'gap_atr':0.5},
        },
        'scenarios':{k:{'cost_bps':v[0],'entry_delay_sec':v[1]} for k,v in SCENARIOS.items()},
        'historical':h,
        'forward_2026_shadow':f,
        'matched_vs_same_stress_control':{'historical':hm,'forward_2026_shadow':fm},
        'v192_s0_reference':{'historical':hv192,'forward_2026_shadow':fv192},
        'decisions':decisions,
        'limitations':[
            'BTCUSDT only; symbol transfer not established.',
            'Historical 2021-2025 uses 1m OHLC; 2026 Mar-Aug uses second OHLC.',
            '2026 is reused forward-shadow/stress, not pristine OOS.',
            'Delay stress executes at the first raw-frame close at/after the frozen delay; it is a reproducible perturbation, not a broker latency simulator.',
            'Cost stress scales the existing flat research cost term; it is not a complete venue fee/funding model.',
            'Right-tail clipping is diagnostic only and does not change occupancy.',
            'No trail arm/gap search occurs in LAB049.',
        ],
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    # Long-form stress table.
    rows=[]
    for period,d in [('historical',h),('2026',f)]:
        for sc in SCENARIOS:
            for name in CONFIG_NAMES.values():
                v=d[sc][name]
                rows.append({
                    'period':period,
                    'scenario':sc,
                    'variant':name,
                    **v['all'],
                    'median_hold_min':v['hold'].get('median_min',np.nan),
                    'p90_hold_min':v['hold'].get('p90_min',np.nan),
                })
    pd.DataFrame(rows).to_csv(OUT/'stress_matrix.csv',index=False)

    # Compact verdict table.
    drows=[]
    for name,x in decisions.items():
        h0=h['S0_BASE'][name]; f0=f['S0_BASE'][name]
        h5=h['S5_ADVERSE_COMBINED'][name]; f5=f['S5_ADVERSE_COMBINED'][name]
        drows.append({
            'variant':name,
            **x,
            'hist_S0_SumR':h0['all'].get('SumR',np.nan),
            'hist_S0_DD':h0['all'].get('MaxDD_R',np.nan),
            'hist_S0_R_DD':h0['all'].get('R_DD',np.nan),
            'fwd_S0_SumR':f0['all'].get('SumR',np.nan),
            'fwd_S0_DD':f0['all'].get('MaxDD_R',np.nan),
            'fwd_S0_R_DD':f0['all'].get('R_DD',np.nan),
            'hist_S5_SumR':h5['all'].get('SumR',np.nan),
            'hist_S5_PF':h5['all'].get('PF',np.nan),
            'hist_S5_DD':h5['all'].get('MaxDD_R',np.nan),
            'hist_S5_R_DD':h5['all'].get('R_DD',np.nan),
            'fwd_S5_SumR':f5['all'].get('SumR',np.nan),
            'fwd_S5_PF':f5['all'].get('PF',np.nan),
            'fwd_S5_DD':f5['all'].get('MaxDD_R',np.nan),
            'fwd_S5_R_DD':f5['all'].get('R_DD',np.nan),
            'hist_S0_clip3_SumR':h0['tail']['clip_3R']['SumR'],
            'fwd_S0_clip3_SumR':f0['tail']['clip_3R']['SumR'],
            'hist_S5_clip3_SumR':h5['tail']['clip_3R']['SumR'],
            'fwd_S5_clip3_SumR':f5['tail']['clip_3R']['SumR'],
            'hist_S5_ex_top5':h5['tail']['SumR_ex_top5'],
            'fwd_S5_ex_top5':f5['tail']['SumR_ex_top5'],
        })
    pd.DataFrame(drows).to_csv(OUT/'decision_table.csv',index=False)

    # Matched reachability.
    mrows=[]
    for period,src in [('historical',hm),('2026',fm)]:
        for sc,d in src.items():
            for name,x in d.items():
                mrows.append({'period':period,'scenario':sc,'variant':name,**x})
    pd.DataFrame(mrows).to_csv(OUT/'matched_reachability_vs_control.csv',index=False)

    # Tail diagnostic table.
    trows=[]
    for period,d in [('historical',h),('2026',f)]:
        for sc in ('S0_BASE','S5_ADVERSE_COMBINED'):
            for name in CONFIG_NAMES.values():
                t=d[sc][name]['tail']
                trows.append({
                    'period':period,
                    'scenario':sc,
                    'variant':name,
                    'max_trade_R':t['max_trade_R'],
                    'top1_share_gross_positive':t['top1_share_gross_positive'],
                    'top5_share_gross_positive':t['top5_share_gross_positive'],
                    'SumR_ex_top1':t['SumR_ex_top1'],
                    'SumR_ex_top5':t['SumR_ex_top5'],
                    'clip5_EV':t['clip_5R']['EV'],
                    'clip5_PF':t['clip_5R']['PF'],
                    'clip5_SumR':t['clip_5R']['SumR'],
                    'clip5_positive_periods':t['clip_5R']['positive_periods'],
                    'clip3_EV':t['clip_3R']['EV'],
                    'clip3_PF':t['clip_3R']['PF'],
                    'clip3_SumR':t['clip_3R']['SumR'],
                    'clip3_positive_periods':t['clip_3R']['positive_periods'],
                })
    pd.DataFrame(trows).to_csv(OUT/'tail_stress.csv',index=False)

    lines=[
        '# LAB049 — V191 TRAIL ARM ROBUSTNESS STRESS','',
        'Frozen arms: 2.5 / 3.5 / 5.0 ATR, all with 0.5 ATR gap.','',
        '**No new trailing parameter search.**','',
        '## Pre-registered verdicts'
    ]
    for name,x in decisions.items():
        lines.append(f"- {name}: **{x['verdict']}** — {json.dumps(x)}")

    lines += ['','## Stress matrix — historical']
    for sc in SCENARIOS:
        lines.append(f'### {sc}')
        for name in CONFIG_NAMES.values():
            lines.append(f"- {name}: {fmt(h[sc][name]['all'])}")

    lines += ['','## Stress matrix — 2026']
    for sc in SCENARIOS:
        lines.append(f'### {sc}')
        for name in CONFIG_NAMES.values():
            lines.append(f"- {name}: {fmt(f[sc][name]['all'])}")

    lines += ['','## S0 / S5 right-tail diagnostics']
    for period,d in [('historical',h),('2026',f)]:
        lines.append(f'### {period}')
        for sc in ('S0_BASE','S5_ADVERSE_COMBINED'):
            for name in CONFIG_NAMES.values():
                t=d[sc][name]['tail']
                lines.append(
                    f"- {sc} / {name}: max={t['max_trade_R']:+.2f}R; "
                    f"ex_top5={t['SumR_ex_top5']:+.2f}R; "
                    f"clip5={t['clip_5R']['SumR']:+.2f}R; "
                    f"clip3={t['clip_3R']['SumR']:+.2f}R; "
                    f"clip3 positive periods={t['clip_3R']['positive_periods']}/{t['clip_3R']['periods_total']}"
                )

    lines += ['','## S5 annual / monthly sequences']
    for name in CONFIG_NAMES.values():
        lines.append(f"- historical {name}: {json.dumps(h['S5_ADVERSE_COMBINED'][name]['periods'])}")
        lines.append(f"- forward {name}: {json.dumps(f['S5_ADVERSE_COMBINED'][name]['periods'])}")

    lines += ['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
