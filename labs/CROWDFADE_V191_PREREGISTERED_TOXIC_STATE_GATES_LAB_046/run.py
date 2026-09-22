from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Reuse LAB045/LAB044/LAB043 validated data loaders and v191/v192 management.
p45=Path(__file__).resolve().parents[1]/'CROWDFADE_V191_POSITIVE_SUBPOPULATION_ATTRIBUTION_LAB_045'/'run.py'
spec45=importlib.util.spec_from_file_location('lab045',p45)
lab045=importlib.util.module_from_spec(spec45); spec45.loader.exec_module(lab045)
lab045.DATA=DATA
lab045.lab44.DATA=DATA
lab045.lab44.lab43.DATA=DATA

lab44=lab045.lab44
lab43=lab44.lab43

BASE=0
SKIP_RAPID30=1
SKIP_HIGH_VOL=2
SKIP_BOTH=3
Z100_125_ONLY=4
Z100_125_SKIP_BOTH=5

NAMES={
0:'BASE_LAB045',
1:'SKIP_RAPID_REPEAT_30',
2:'SKIP_HIGH_VOL',
3:'SKIP_RAPID_REPEAT_30_AND_HIGH_VOL',
4:'Z100_125_ONLY',
5:'Z100_125_SKIP_RAPID_REPEAT_30_AND_HIGH_VOL'
}

def build_signal_features(p):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    atrpct=A5/C5
    s=pd.Series(atrpct)
    q33=s.shift(1).rolling(8640,min_periods=2880).quantile(0.33).to_numpy()
    q67=s.shift(1).rolling(8640,min_periods=2880).quantile(0.67).to_numpy()
    vol=np.zeros(len(dt5),np.int8)  # -1 low, 0 mid/unknown, +1 high
    for j in range(len(dt5)):
        if np.isfinite(q33[j]) and np.isfinite(q67[j]):
            if atrpct[j] <= q33[j]:
                vol[j]=-1
            elif atrpct[j] >= q67[j]:
                vol[j]=1
            else:
                vol[j]=0

    gap=np.full(len(dt5),np.nan)
    last_pos=-10**18; last_neg=-10**18
    for j,(t,z) in enumerate(zip(dt5,Z5)):
        if z>=1.0:
            if last_pos>-10**17:
                gap[j]=(t-last_pos)/60.0
            last_pos=t
        elif z<=-1.0:
            if last_neg>-10**17:
                gap[j]=(t-last_neg)/60.0
            last_neg=t
    return vol,gap

def gate_allows(variant,z,vol_state,gap_min):
    az=abs(z)
    rapid=np.isfinite(gap_min) and gap_min<=30.0
    high=(vol_state==1)
    lowz=(az>=1.0 and az<1.25)

    if variant==BASE: return True
    if variant==SKIP_RAPID30: return not rapid
    if variant==SKIP_HIGH_VOL: return not high
    if variant==SKIP_BOTH: return (not rapid) and (not high)
    if variant==Z100_125_ONLY: return lowz
    if variant==Z100_125_SKIP_BOTH: return lowz and (not rapid) and (not high)
    return True

def sim_variant(p,variant):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    vol,gap=build_signal_features(p)
    rows=[]
    k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False

    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts:
            k+=1; continue
        d=t//86400
        if d!=day:
            day=d; dc=0
        if dc>=lab44.MAXDAY:
            k+=1; continue

        z0=Z5[k]
        side=-1 if z0>=lab44.V191_Z else (1 if z0<=-lab44.V191_Z else 0)
        if side==0:
            k+=1; continue

        # Preregistered gate is evaluated at the original signal state, before occupancy changes.
        if not gate_allows(variant,z0,vol[k],gap[k]):
            k+=1; continue

        sig=C5[k]; atr=A5[k]
        if has and abs(sig-last)<lab44.PAUSE_ATR*la:
            k+=1; continue

        # Frozen LAB045 base: freshness45 + pre-confirm adverse<=0.75.
        target=sig+side*lab44.V191_CONFIRM_ATR*atr
        ps=np.searchsorted(ts,t+1)
        pe=np.searchsorted(ts,t+2700,'right')
        ci=-1; maxadv=0.; maxfav=0.
        for q in range(ps,min(len(ts),pe)):
            adv=((H[q]-sig) if side<0 else (sig-L[q]))/atr
            fav=((sig-L[q]) if side<0 else (H[q]-sig))/atr
            if adv>maxadv: maxadv=adv
            if fav>maxfav: maxfav=fav
            if maxadv>0.75:
                ci=-2
                break
            if (side>0 and C[q]>=target) or (side<0 and C[q]<=target):
                ci=q
                break

        if ci<0:
            k+=1; continue

        zi=np.searchsorted(dt5,ts[ci],'right')-1
        if zi<0:
            k+=1; continue
        cz=Z5[zi]

        # Original v191d confirmation consistency; ExitZ retained.
        if (side>0 and cz>=0.75) or (side<0 and cz<=-0.75):
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        entry=C[ci]
        rr,ex,reason=lab43.manage_v191(ts,H,L,C,dt5,Z5,ci,side,entry,atr,0.75)
        rows.append({
            'R':float(rr),
            'signal_ts':int(t),
            'entry_ts':int(ts[ci]),
            'exit_ts':int(ts[ex]),
            'side':int(side),
            'signal_z':float(z0),
            'signal_abs_z':float(abs(z0)),
            'confirm_z':float(cz),
            'confirm_age_min':float((ts[ci]-t)/60.0),
            'max_adverse_atr':float(maxadv),
            'response_ratio':float(maxfav/(maxadv+1e-9)),
            'vol_state':int(vol[k]),
            'prior_same_extreme_gap_min':float(gap[k]) if np.isfinite(gap[k]) else np.nan,
            'exit_reason':lab43.REASONS.get(int(reason),'?')
        })

        dc+=1
        last=entry; la=atr; has=True
        nextts=ts[ex]+1
        k=np.searchsorted(dt5,nextts)

    return pd.DataFrame(rows)

def metrics(df):
    return lab43.metrics(df.R.to_numpy(float)) if len(df) else {
        'N':0,'WR':0.,'EV':0.,'PF':0.,'SumR':0.,'MaxDD_R':0.,'R_DD':0.,'MaxConsecutiveLosses':0}

def period_stats(df,mode):
    if len(df)==0: return {}
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    key=t.dt.year.astype(str) if mode=='year' else t.dt.strftime('%Y-%m')
    return {str(k):metrics(g) for k,g in df.groupby(key)}

def summarize(df,mode):
    return {
      'all':metrics(df),
      'periods':period_stats(df,mode),
      'side':{
        'BUY':metrics(df[df.side>0]),
        'SELL':metrics(df[df.side<0])},
      'exit_reasons':{str(k):int(v) for k,v in df.exit_reason.value_counts().items()} if len(df) else {}
    }

def matched_vs_base(base,other):
    kb=set(zip(base.signal_ts.astype(np.int64),base.side.astype(int)))
    ko=set(zip(other.signal_ts.astype(np.int64),other.side.astype(int)))
    onlyb=base[[((int(x),int(y)) in (kb-ko)) for x,y in zip(base.signal_ts,base.side)]]
    onlyo=other[[((int(x),int(y)) in (ko-kb)) for x,y in zip(other.signal_ts,other.side)]]
    common=kb&ko
    bm={(int(x),int(y)):float(r) for x,y,r in zip(base.signal_ts,base.side,base.R)}
    om={(int(x),int(y)):float(r) for x,y,r in zip(other.signal_ts,other.side,other.R)}
    return {
      'N_base':int(len(base)),
      'N_variant':int(len(other)),
      'delta_N':int(len(other)-len(base)),
      'removed_signal_count':int(len(kb-ko)),
      'added_signal_count':int(len(ko-kb)),
      'common_signal_count':int(len(common)),
      'removed_trade_sumR':float(onlyb.R.sum()),
      'added_trade_sumR':float(onlyo.R.sum()),
      'common_signal_outcome_deltaR':float(sum(om[k]-bm[k] for k in common)),
      'full_sequence_deltaR':float(other.R.sum()-base.R.sum())
    }

def decision_verdict(h,f):
    hm=h['all']; fm=f['all']
    agg=(hm.get('N',0)>0 and fm.get('N',0)>0 and
         hm.get('EV',-1)>0 and hm.get('PF',0)>1.0 and
         fm.get('EV',-1)>0 and fm.get('PF',0)>1.0)
    hy=sum(1 for x in h.get('periods',{}).values() if x.get('SumR',0)>0)
    fy=sum(1 for x in f.get('periods',{}).values() if x.get('SumR',0)>0)
    ht=len(h.get('periods',{})); ft=len(f.get('periods',{}))
    if not agg:
        verdict='FAILED'
    elif hy>=4 and ht>=5 and fy>=4 and ft>=6:
        verdict='SUPPORTED'
    else:
        verdict='MIXED'
    return {
      'verdict':verdict,
      'positive_historical_years':hy,
      'historical_years_total':ht,
      'positive_2026_months':fy,
      'forward_months_total':ft
    }

def run_period(raw,ft,fz,start,end,label):
    p=lab43.prep(raw,ft,fz,start,end)
    out={}
    frames={}

    d192=lab43.df192(lab43.sim_v192(*p))
    d192.to_csv(OUT/f'{label}_V192_CANONICAL_CONTROL.csv',index=False)
    frames['V192_CANONICAL_CONTROL']=d192
    out['V192_CANONICAL_CONTROL']=lab43.summarize(d192,'year' if label=='historical' else 'month')

    full=lab44.make_df(lab44.sim(*p,lab44.FULL_V191F))
    full.to_csv(OUT/f'{label}_FULL_V191F_CONTROL.csv',index=False)
    frames['FULL_V191F_CONTROL']=full
    out['FULL_V191F_CONTROL']=lab44.summarize(full,'year' if label=='historical' else 'month')

    for v in range(6):
        d=sim_variant(p,v)
        d.to_csv(OUT/f'{label}_{NAMES[v]}.csv',index=False)
        frames[NAMES[v]]=d
        out[NAMES[v]]=summarize(d,'year' if label=='historical' else 'month')

    # Hard parity assertion: BASE must be byte-logically equivalent to LAB044 FRESH45_ADV.
    frozen=lab44.make_df(lab44.sim(*p,lab44.FRESH45_ADV))
    base=frames['BASE_LAB045']
    parity=(len(frozen)==len(base))
    if parity and len(base):
        parity = (
          np.array_equal(frozen[['signal_ts','side']].to_numpy(),base[['signal_ts','side']].to_numpy())
          and np.allclose(frozen.R.to_numpy(float),base.R.to_numpy(float),atol=1e-12,rtol=0)
        )
    if not parity:
        raise RuntimeError('LAB046 BASE parity failure vs LAB044 FRESH45_ADV')

    matched={}
    for name,d in frames.items():
        if name!='BASE_LAB045':
            matched[name]=matched_vs_base(base,d)
    return out,matched

def fmt(m):
    return f"N={m['N']} WR={m['WR']:.1%} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f} MCL={m['MaxConsecutiveLosses']}"

def main():
    ft,fz=lab43.load_flow()
    hist=lab43.load_hist()
    sec=lab43.load_sec()

    h,hm=run_period(hist,ft,fz,
        int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),'historical')
    f,fm=run_period(sec,ft,fz,
        int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),'forward')

    decisions={name:decision_verdict(h[name],f[name]) for name in NAMES.values()}

    result={
      'lab':'CROWDFADE_V191_PREREGISTERED_TOXIC_STATE_GATES_LAB_046',
      'preregistration':'PREREG.md committed before this replay; only the six registered variants are decision-tested.',
      'base':'v191d + freshness45 + adverse<=0.75 ATR + ExitZ retained',
      'method':'Full stateful causal replay for every variant; skipped signals alter occupancy and future reachability.',
      'pre_registered_gates':{
        'SKIP_RAPID_REPEAT_30':'skip signal if same-side |Z|>=1 extreme occurred <=30m ago',
        'SKIP_HIGH_VOL':'skip causal HIGH_VOL from lagged 30d ATR%-tercile state',
        'SKIP_RAPID_REPEAT_30_AND_HIGH_VOL':'apply both toxic-state skips',
        'Z100_125_ONLY':'accept only 1.00<=|Z|<1.25',
        'Z100_125_SKIP_RAPID_REPEAT_30_AND_HIGH_VOL':'low-Z bucket plus both toxic-state skips'
      },
      'historical':h,
      'forward_2026_shadow':f,
      'matched_vs_base':{'historical':hm,'forward_2026_shadow':fm},
      'decisions':decisions,
      'limitations':[
        'BTCUSDT only; ETH/SOL transfer not established.',
        'Historical 2021-2025 uses 1m OHLC; 2026 Mar-Aug uses second OHLC.',
        '2026 is reused forward-shadow/stress, not pristine OOS.',
        'All gate thresholds were fixed before this replay; no threshold search is performed here.',
        'Every candidate is a full stateful rerun; skipped signals change occupancy, pause state and future reachability.',
        'v191 MT5 is tick/timer-driven; this uses the same common research approximation as LAB043-045.',
        'v192 is immutable reference and reconstructed on the common replay frame.',
        'Flat 0.5bps research cost proxy; broker-specific IC/GetLeveraged execution remains a separate forward-validation question.'
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
          'hist_N':h[name]['all'].get('N',0),'hist_EV':h[name]['all'].get('EV',np.nan),
          'hist_PF':h[name]['all'].get('PF',np.nan),'hist_SumR':h[name]['all'].get('SumR',np.nan),
          'hist_DD':h[name]['all'].get('MaxDD_R',np.nan),
          'fwd_N':f[name]['all'].get('N',0),'fwd_EV':f[name]['all'].get('EV',np.nan),
          'fwd_PF':f[name]['all'].get('PF',np.nan),'fwd_SumR':f[name]['all'].get('SumR',np.nan),
          'fwd_DD':f[name]['all'].get('MaxDD_R',np.nan)
        })
    pd.DataFrame(drows).to_csv(OUT/'decision_table.csv',index=False)

    mrows=[]
    for period,matches in [('historical',hm),('2026',fm)]:
        for name,x in matches.items():
            mrows.append({'period':period,'variant':name,**x})
    pd.DataFrame(mrows).to_csv(OUT/'matched_reachability_vs_base.csv',index=False)

    lines=['# LAB046 — V191 PREREGISTERED TOXIC STATE GATES','',
      'Preregistration was committed before this replay. Only the six registered variants enter the decision table.','',
      'Base: **v191d + freshness45 + adverse<=0.75 ATR + ExitZ retained**.','',
      '**Full stateful causal rerun. No threshold search and no exit changes.**','',
      '## Full sample']
    for period,d in [('Historical 2021–2025',h),('2026 Mar–Aug shadow',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items():
            lines.append(f"- {name}: {fmt(v['all'])}")

    lines += ['','## Pre-registered decision table']
    for name,x in decisions.items():
        lines.append(
          f"- {name}: **{x['verdict']}**; positive years "
          f"{x['positive_historical_years']}/{x['historical_years_total']}; "
          f"positive 2026 months {x['positive_2026_months']}/{x['forward_months_total']}"
        )

    lines += ['','## Historical yearly sequence']
    for name,v in h.items():
        lines.append(f"- {name}: {json.dumps(v['periods'])}")

    lines += ['','## 2026 monthly sequence']
    for name,v in f.items():
        lines.append(f"- {name}: {json.dumps(v['periods'])}")

    lines += ['','## Stateful reachability delta vs BASE_LAB045 — historical']
    for name,x in hm.items():
        lines.append('- '+name+': '+json.dumps(x))

    lines += ['','## Stateful reachability delta vs BASE_LAB045 — 2026']
    for name,x in fm.items():
        lines.append('- '+name+': '+json.dumps(x))

    lines += ['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
