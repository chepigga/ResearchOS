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
Z100_125_SKIP_HIGHVOL=5
Z100_125_SKIP_RAPID30=6
Z100_125_SKIP_BOTH=7

NAMES={
0:'BASE_LAB045',
1:'SKIP_RAPID_REPEAT_LE30M',
2:'SKIP_HIGH_VOL',
3:'SKIP_RAPID30_PLUS_HIGHVOL',
4:'Z100_125_ONLY',
5:'Z100_125_SKIP_HIGHVOL',
6:'Z100_125_SKIP_RAPID30',
7:'Z100_125_SKIP_BOTH'
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
    if variant==Z100_125_SKIP_HIGHVOL: return lowz and (not high)
    if variant==Z100_125_SKIP_RAPID30: return lowz and (not rapid)
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

def run_period(raw,ft,fz,start,end,label):
    p=lab43.prep(raw,ft,fz,start,end)
    out={}

    d192=lab43.df192(lab43.sim_v192(*p))
    d192.to_csv(OUT/f'{label}_V192_CANONICAL_CONTROL.csv',index=False)
    out['V192_CANONICAL_CONTROL']=lab43.summarize(d192,'year' if label=='historical' else 'month')

    full=lab44.make_df(lab44.sim(*p,lab44.FULL_V191F))
    full.to_csv(OUT/f'{label}_FULL_V191F_CONTROL.csv',index=False)
    out['FULL_V191F_CONTROL']=lab44.summarize(full,'year' if label=='historical' else 'month')

    for v in range(8):
        d=sim_variant(p,v)
        d.to_csv(OUT/f'{label}_{NAMES[v]}.csv',index=False)
        out[NAMES[v]]=summarize(d,'year' if label=='historical' else 'month')
    return out

def fmt(m):
    return f"N={m['N']} WR={m['WR']:.1%} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f} MCL={m['MaxConsecutiveLosses']}"

def main():
    ft,fz=lab43.load_flow()
    hist=lab43.load_hist()
    sec=lab43.load_sec()

    h=run_period(hist,ft,fz,
        int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),'historical')
    f=run_period(sec,ft,fz,
        int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),'forward')

    result={
      'lab':'CROWDFADE_V191_PREREGISTERED_TOXIC_STATE_GATES_LAB_046',
      'base':'v191d + freshness45 + adverse<=0.75 ATR + ExitZ retained',
      'method':'Full stateful causal replay for every variant; skipped signals alter occupancy and future reachability.',
      'pre_registered_gates':{
        'SKIP_RAPID_REPEAT_LE30M':'skip signal if same-side |Z|>=1 extreme occurred <=30m ago',
        'SKIP_HIGH_VOL':'skip causal HIGH_VOL from lagged 30d ATR%-tercile state',
        'SKIP_RAPID30_PLUS_HIGHVOL':'apply both skips',
        'Z100_125_ONLY':'accept only 1.00<=|Z|<1.25',
        'Z100_125_SKIP_HIGHVOL':'low-Z bucket plus skip HIGH_VOL',
        'Z100_125_SKIP_RAPID30':'low-Z bucket plus skip rapid repeat',
        'Z100_125_SKIP_BOTH':'low-Z bucket plus both toxic-state skips'
      },
      'historical':h,
      'forward_2026_shadow':f,
      'limitations':[
        'BTCUSDT only; ETH/SOL transfer not established.',
        'Historical 2021-2025 uses 1m OHLC; 2026 Mar-Aug uses second OHLC.',
        '2026 is reused forward-shadow/stress, not pristine OOS.',
        'All gates and thresholds were preregistered from LAB045; no threshold search is performed here.',
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

    lines=['# LAB046 — V191 PREREGISTERED TOXIC STATE GATES','',
      'Base: **v191d + freshness45 + adverse<=0.75 ATR + ExitZ retained**.',
      '',
      '**Full stateful causal rerun** for every candidate. No threshold search and no exit changes.',
      '',
      '## Full sample']
    for period,d in [('Historical 2021–2025',h),('2026 Mar–Aug shadow',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items():
            lines.append(f"- {name}: {fmt(v['all'])}")

    lines += ['','## Period consistency']
    for period,d in [('Historical',h),('2026',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items():
            lines.append(f"- {name}: {json.dumps(v['periods'])}")

    lines += ['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
