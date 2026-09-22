from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd
from numba import njit

# LAB047_TRIGGER_AFTER_WORKFLOW\nROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Reuse exact LAB046 signal/gate construction and LAB043 data loaders/v192.
p46=Path(__file__).resolve().parents[1]/'CROWDFADE_V191_PREREGISTERED_TOXIC_STATE_GATES_LAB_046'/'run.py'
spec=importlib.util.spec_from_file_location('lab046',p46)
lab046=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab046)
lab046.DATA=DATA
lab046.lab045.DATA=DATA
lab046.lab045.lab44.DATA=DATA
lab046.lab045.lab44.lab43.DATA=DATA

lab44=lab046.lab045.lab44
lab43=lab44.lab43

COST_BPS=lab43.COST_BPS
MAXDAY=lab43.MAXDAY
PAUSE_ATR=lab43.PAUSE_ATR
V191_Z=lab43.V191_Z
V191_CONFIRM_ATR=lab43.V191_CONFIRM_ATR

CONTROL=0
EXITZ_OFF=1
BE_OFF=2
TRAIL_OFF=3
HOLD_3H=4
HOLD_2H=5
TP_1R=6
TP_1P5R=7
SL1_TP1=8
SL1_TP1P5=9

NAMES={
  0:'CONTROL_V191',
  1:'EXITZ_OFF',
  2:'BE_OFF',
  3:'TRAIL_OFF',
  4:'HOLD_3H',
  5:'HOLD_2H',
  6:'TP_1R',
  7:'TP_1P5R',
  8:'SL1_TP1',
  9:'SL1_TP1P5',
}

REASONS={1:'SL',2:'PROTECTED_STOP',3:'EXIT_Z',4:'TIME',5:'TP'}

@njit(cache=True)
def cfg(v):
    # sl_atr, tp_r (0=off), use_be, use_trail, hold_sec, exit_z
    if v==EXITZ_OFF:
        return 1.50,0.0,1,1,21600,0.0
    if v==BE_OFF:
        return 1.50,0.0,0,1,21600,0.75
    if v==TRAIL_OFF:
        return 1.50,0.0,1,0,21600,0.75
    if v==HOLD_3H:
        return 1.50,0.0,1,1,10800,0.75
    if v==HOLD_2H:
        return 1.50,0.0,1,1,7200,0.75
    if v==TP_1R:
        return 1.50,1.0,1,1,21600,0.75
    if v==TP_1P5R:
        return 1.50,1.5,1,1,21600,0.75
    if v==SL1_TP1:
        return 1.00,1.0,1,1,21600,0.75
    if v==SL1_TP1P5:
        return 1.00,1.5,1,1,21600,0.75
    return 1.50,0.0,1,1,21600,0.75

@njit(cache=True)
def manage_variant(ts,H,L,C,dt5,Z5,ei,side,entry,atr,variant):
    sl_atr,tp_r,use_be,use_trail,hold_sec,exit_z=cfg(variant)
    risk=sl_atr*atr
    stop=entry-side*risk
    peak=entry
    pending_stop=stop
    use_tp=tp_r>0.0
    tp=entry+side*tp_r*risk if use_tp else entry

    xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+hold_sec,'left'))
    xp=C[xe]
    ex=xe
    reason=4

    for q in range(ei+1,xe+1):
        stop=pending_stop

        # Conservative same-bar ordering: stop before TP, matching v192 convention.
        if (side>0 and L[q]<=stop) or (side<0 and H[q]>=stop):
            protected=(side>0 and stop>entry) or (side<0 and stop<entry)
            xp=stop
            ex=q
            reason=2 if protected else 1
            break

        if use_tp:
            if (side>0 and H[q]>=tp) or (side<0 and L[q]<=tp):
                xp=tp
                ex=q
                reason=5
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
        if use_be==1 and fav>=0.50:
            lvl=entry+side*0.15*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):
                ns=lvl

        if use_trail==1 and fav>=2.50:
            lvl=peak-side*0.50*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns):
                ns=lvl

        pending_stop=ns

        if exit_z>0.0:
            zi=np.searchsorted(dt5,ts[q],'right')-1
            if zi>=0:
                z=Z5[zi]
                if (side>0 and z>=exit_z) or (side<0 and z<=-exit_z):
                    xp=C[q]
                    ex=q
                    reason=3
                    break

    rr=side*(xp-entry)/risk-(COST_BPS/10000.0)*entry/risk
    return rr,ex,reason

@njit(cache=True)
def sim_exit(ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5,rapid,highvol,variant):
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

        # Frozen LAB046 SUPPORTED dual toxic-state gate:
        # skip RAPID_REPEAT<=30m OR HIGH_VOL.
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

        # Original v191d confirmation consistency retained.
        if (side>0 and cz>=0.75) or (side<0 and cz<=-0.75):
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        entry=C[ci]
        rr,ex,reason=manage_variant(ts,H,L,C,dt5,Z5,ci,side,entry,atr,variant)

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

def period_stats(df,mode):
    if len(df)==0:
        return {}
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    key=t.dt.year.astype(str) if mode=='year' else t.dt.strftime('%Y-%m')
    return {str(k):metrics(g) for k,g in df.groupby(key,sort=True)}

def summarize(df,mode):
    m=metrics(df)
    if not len(df):
        return {'all':m,'periods':{},'side':{},'exit_reasons':{},'hold':{},'r_distribution':{}}
    wins=df[df.R>0].R
    losses=df[df.R<0].R
    return {
      'all':m,
      'periods':period_stats(df,mode),
      'side':{
        'BUY':metrics(df[df.side>0]),
        'SELL':metrics(df[df.side<0]),
      },
      'exit_reasons':{str(k):int(v) for k,v in df.exit_reason.value_counts().items()},
      'hold':{
        'median_min':float(df.hold_min.median()),
        'p90_min':float(df.hold_min.quantile(0.90)),
        'mean_min':float(df.hold_min.mean()),
      },
      'r_distribution':{
        'winner_median_R':float(wins.median()) if len(wins) else None,
        'loser_median_R':float(losses.median()) if len(losses) else None,
      }
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

def classify(h,f,h_control,f_control):
    hm=h['all']; fm=f['all']
    agg=(hm.get('N',0)>0 and fm.get('N',0)>0 and
         hm.get('EV',-1)>0 and hm.get('PF',0)>1.0 and
         fm.get('EV',-1)>0 and fm.get('PF',0)>1.0)
    hy=sum(1 for x in h.get('periods',{}).values() if x.get('SumR',0)>0)
    fy=sum(1 for x in f.get('periods',{}).values() if x.get('SumR',0)>0)
    ht=len(h.get('periods',{})); ft=len(f.get('periods',{}))

    freq_ok=(
      hm.get('N',0)>=0.40*h_control['all'].get('N',0)
      and fm.get('N',0)>=0.40*f_control['all'].get('N',0)
    )
    dd_ok=not (
      hm.get('MaxDD_R',np.inf)>h_control['all'].get('MaxDD_R',np.inf)
      and fm.get('MaxDD_R',np.inf)>f_control['all'].get('MaxDD_R',np.inf)
    )
    consistency=(hy>=4 and ht>=5 and fy>=4 and ft>=6)

    if not agg:
        verdict='FAILED'
    elif consistency and freq_ok and dd_ok:
        verdict='SUPPORTIVE'
    else:
        verdict='MIXED'

    return {
      'verdict':verdict,
      'positive_historical_years':hy,
      'historical_years_total':ht,
      'positive_2026_months':fy,
      'forward_months_total':ft,
      'frequency_ok':bool(freq_ok),
      'dd_guard_ok':bool(dd_ok),
    }

def run_period(raw,ft,fz,start,end,label):
    p=lab43.prep(raw,ft,fz,start,end)
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    vol,gap=lab046.build_signal_features(p)\n    rapid=(np.isfinite(gap)&(gap<=30.0)).astype(np.int8)\n    highvol=(vol==1).astype(np.int8)

    out={}
    frames={}

    for v in range(10):
        d=make_df(sim_exit(*p,rapid,highvol,v))
        d.to_csv(OUT/f'{label}_{NAMES[v]}.csv',index=False)
        frames[NAMES[v]]=d
        out[NAMES[v]]=summarize(d,'year' if label=='historical' else 'month')

    # Immutable v192 common-frame reference.
    d192=lab43.df192(lab43.sim_v192(*p))
    d192['hold_min']=(d192.exit_ts-d192.entry_ts)/60.0
    d192.to_csv(OUT/f'{label}_V192_CANONICAL_CONTROL.csv',index=False)
    frames['V192_CANONICAL_CONTROL']=d192
    out['V192_CANONICAL_CONTROL']=lab43.summarize(d192,'year' if label=='historical' else 'month')

    # Hard control parity vs LAB046 SUPPORTED stateful gate.
    d46=lab046.sim_variant(p,lab046.SKIP_BOTH)
    control=frames['CONTROL_V191']
    parity=(len(d46)==len(control))
    if parity and len(control):
        parity=(
          np.array_equal(d46[['signal_ts','side']].to_numpy(),control[['signal_ts','side']].to_numpy())
          and np.allclose(d46.R.to_numpy(float),control.R.to_numpy(float),atol=1e-12,rtol=0)
        )
    if not parity:
        raise RuntimeError('LAB047 CONTROL parity failure vs LAB046 SKIP_BOTH')

    matched={}
    for name,d in frames.items():
        if name!='CONTROL_V191':
            matched[name]=matched_vs_control(control,d)

    return out,frames,matched

def fmt(m):
    if m.get('N',0)==0:
        return 'N=0'
    return (
      f"N={m['N']} WR={m['WR']:.1%} EV={m['EV']:+.4f} PF={m['PF']:.3f} "
      f"Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} "
      f"R/DD={m['R_DD']:.3f} MCL={m['MaxConsecutiveLosses']}"
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

    decisions={}
    for name in NAMES.values():
        decisions[name]=classify(h[name],f[name],h['CONTROL_V191'],f['CONTROL_V191'])

    result={
      'lab':'CROWDFADE_V191_DUAL_TOXIC_GATE_EXIT_GEOMETRY_LAB_047',
      'preregistration':'PREREG.md committed before runner execution.',
      'frozen_signal_population':'LAB046 SUPPORTED dual toxic gate: skip rapid-repeat<=30m OR HIGH_VOL; all entry rules unchanged.',
      'control_management':'SL1.5, BE0.5/0.15, trail2.5/0.5, ExitZ0.75, H6, no fixed TP.',
      'historical':h,
      'forward_2026_shadow':f,
      'matched_vs_control':{'historical':hm,'forward_2026_shadow':fm},
      'decisions':decisions,
      'limitations':[
        'BTCUSDT only; ETH/SOL transfer not established.',
        'Historical 2021-2025 uses 1m OHLC; 2026 Mar-Aug uses second OHLC.',
        '2026 is reused forward-shadow/stress, not pristine OOS.',
        'All LAB047 management variants were fixed before execution; no in-LAB threshold search.',
        'Every candidate is a full stateful rerun; changed exits alter occupancy and future signal reachability.',
        'For bars touching stop and TP in the same raw bar, stop is evaluated first as a conservative convention.',
        'v191 MT5 is tick/timer-driven; replay uses the same common research approximation as LAB043-046.',
        'Flat 0.5bps cost proxy; broker-specific forward execution remains separate.',
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    rows=[]
    for period,d in [('historical',h),('2026',f)]:
        for name,v in d.items():
            rows.append({'period':period,'variant':name,**v['all']})
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
          'fwd_N':f[name]['all'].get('N',0),
          'fwd_EV':f[name]['all'].get('EV',np.nan),
          'fwd_PF':f[name]['all'].get('PF',np.nan),
          'fwd_SumR':f[name]['all'].get('SumR',np.nan),
          'fwd_DD':f[name]['all'].get('MaxDD_R',np.nan),
          'fwd_R_DD':f[name]['all'].get('R_DD',np.nan),
          'hist_median_hold':h[name].get('hold',{}).get('median_min',np.nan),
          'fwd_median_hold':f[name].get('hold',{}).get('median_min',np.nan),
        })
    pd.DataFrame(drows).to_csv(OUT/'decision_table.csv',index=False)

    mrows=[]
    for period,matches in [('historical',hm),('2026',fm)]:
        for name,x in matches.items():
            mrows.append({'period':period,'variant':name,**x})
    pd.DataFrame(mrows).to_csv(OUT/'matched_reachability_vs_control.csv',index=False)

    lines=[
      '# LAB047 — V191 DUAL TOXIC GATE EXIT GEOMETRY','',
      'Signal/entry population frozen from the SUPPORTED LAB046 dual toxic-state gate.','',
      '**All exit variants are full stateful reruns. No entry retuning and no in-LAB exit threshold optimization.**','',
      '## Aggregate results'
    ]
    for period,d in [('Historical 2021–2025',h),('2026 Mar–Aug shadow',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items():
            lines.append(f"- {name}: {fmt(v['all'])}")
            if name in NAMES.values():
                lines.append(
                  f"  hold median={v['hold'].get('median_min')}m p90={v['hold'].get('p90_min')}m; "
                  f"exits={json.dumps(v['exit_reasons'])}"
                )

    lines += ['','## Pre-registered verdicts']
    for name,x in decisions.items():
        lines.append(
          f"- {name}: **{x['verdict']}**; years "
          f"{x['positive_historical_years']}/{x['historical_years_total']}; "
          f"2026 months {x['positive_2026_months']}/{x['forward_months_total']}; "
          f"freq_ok={x['frequency_ok']} dd_guard_ok={x['dd_guard_ok']}"
        )

    lines += ['','## Historical yearly sequence']
    for name,v in h.items():
        lines.append(f"- {name}: {json.dumps(v['periods'])}")

    lines += ['','## 2026 monthly sequence']
    for name,v in f.items():
        lines.append(f"- {name}: {json.dumps(v['periods'])}")

    lines += ['','## Stateful reachability delta vs CONTROL_V191 — historical']
    for name,x in hm.items():
        lines.append('- '+name+': '+json.dumps(x))

    lines += ['','## Stateful reachability delta vs CONTROL_V191 — 2026']
    for name,x in fm.items():
        lines.append('- '+name+': '+json.dumps(x))

    lines += ['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
