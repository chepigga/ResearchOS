from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Reuse LAB045 enriched causal diagnostics and LAB044 frozen base replay.
p45=Path(__file__).resolve().parents[1]/'CROWDFADE_V191_POSITIVE_SUBPOPULATION_ATTRIBUTION_LAB_045'/'run.py'
spec=importlib.util.spec_from_file_location('lab045',p45)
lab45=importlib.util.module_from_spec(spec); spec.loader.exec_module(lab45)
lab45.DATA=DATA
lab45.lab44.DATA=DATA
lab45.lab44.lab43.DATA=DATA

# LAB046 is a pre-registered causal gate/risk-layer validation.
# Base shell is fixed LAB045:
# v191d + freshness45 + adverse<=0.75 ATR + ExitZ retained.
# No exit changes, no threshold search.

VARIANTS = [
    'BASE_LAB045',
    'HARD_SKIP_RAPID30',
    'HARD_SKIP_HIGHVOL',
    'HARD_SKIP_RAPID30_HIGHVOL',
    'HARD_Z100_125_ONLY',
    'HARD_Z100_125_PLUS_SKIP_RAPID30_HIGHVOL',
    'RISK_TIER_TOXIC_025',
    'RISK_TIER_TOXIC_050',
    'RISK_TIER_Z_AND_TOXIC'
]

def base_enriched(raw,ft,fz,start,end,label):
    df,p = lab45.enrich_base(raw,ft,fz,start,end,label+'_base')
    return df,p

def flags(df):
    x=df.copy()
    x['is_rapid30']=(x['mins_since_prior_same_extreme'].notna() & (x['mins_since_prior_same_extreme']<=30.0))
    x['is_highvol']=(x['vol_regime']=='HIGH_VOL')
    x['is_z100_125']=((x['signal_abs_z']>=1.00)&(x['signal_abs_z']<1.25))
    x['is_z125_200']=((x['signal_abs_z']>=1.25)&(x['signal_abs_z']<2.00))
    x['is_z200_plus']=(x['signal_abs_z']>=2.00)
    x['toxic_any']=x['is_rapid30']|x['is_highvol']
    return x

def apply_variant(df,name):
    x=flags(df).copy()
    if name=='BASE_LAB045':
        x['risk_mult']=1.0
        return x

    if name=='HARD_SKIP_RAPID30':
        x=x[~x.is_rapid30].copy(); x['risk_mult']=1.0; return x
    if name=='HARD_SKIP_HIGHVOL':
        x=x[~x.is_highvol].copy(); x['risk_mult']=1.0; return x
    if name=='HARD_SKIP_RAPID30_HIGHVOL':
        x=x[~x.toxic_any].copy(); x['risk_mult']=1.0; return x
    if name=='HARD_Z100_125_ONLY':
        x=x[x.is_z100_125].copy(); x['risk_mult']=1.0; return x
    if name=='HARD_Z100_125_PLUS_SKIP_RAPID30_HIGHVOL':
        x=x[x.is_z100_125 & ~x.toxic_any].copy(); x['risk_mult']=1.0; return x

    if name=='RISK_TIER_TOXIC_025':
        x['risk_mult']=np.where(x.toxic_any,0.25,1.0)
        return x
    if name=='RISK_TIER_TOXIC_050':
        x['risk_mult']=np.where(x.toxic_any,0.50,1.0)
        return x
    if name=='RISK_TIER_Z_AND_TOXIC':
        # Preserve all trades, but concentrate risk in the only cross-sample positive Z bucket.
        # Pre-registered map: Z1.00-1.25=1.0x, Z1.25-2.00=0.5x, Z>=2.00=0.25x;
        # any toxic state caps risk at 0.25x.
        rm=np.where(x.is_z100_125,1.0,np.where(x.is_z125_200,0.5,0.25))
        rm=np.minimum(rm,np.where(x.toxic_any,0.25,1.0))
        x['risk_mult']=rm
        return x
    raise ValueError(name)

def seq_metrics(df):
    if len(df)==0:
        return {'N':0,'WR':0.0,'EV':0.0,'PF':0.0,'SumR':0.0,'MaxDD_R':0.0,'R_DD':0.0,'MaxConsecutiveLosses':0,
                'AvgRiskMult':0.0,'EffectiveTradeUnits':0.0}
    r=(df.R.to_numpy(float)*df.risk_mult.to_numpy(float))
    m=lab45.lab44.lab43.metrics(r)
    m['RawEV']=float(df.R.mean())
    m['AvgRiskMult']=float(df.risk_mult.mean())
    m['EffectiveTradeUnits']=float(df.risk_mult.sum())
    m['N_raw']=int(len(df))
    return m

def period_metrics(df,kind):
    q=df.copy()
    t=pd.to_datetime(q.signal_ts,unit='s',utc=True)
    q['_period']=t.dt.year.astype(str) if kind=='year' else t.dt.strftime('%Y-%m')
    return {str(k):seq_metrics(g) for k,g in q.groupby('_period')}

def risk_mix(df):
    vc=df.risk_mult.value_counts().sort_index()
    return {str(float(k)):int(v) for k,v in vc.items()}

def run_period(raw,ft,fz,start,end,label):
    base,_=base_enriched(raw,ft,fz,start,end,label)
    out={}
    for name in VARIANTS:
        v=apply_variant(base,name)
        v.to_csv(OUT/f'{label}_{name}.csv',index=False)
        out[name]={
            'all':seq_metrics(v),
            'periods':period_metrics(v,'year' if label=='historical' else 'month'),
            'risk_mix':risk_mix(v),
            'kept_fraction':float(len(v)/len(base)) if len(base) else 0.0
        }
    return out

def fmt(m):
    return (f"N={m.get('N_raw',m.get('N',0))} Eff={m.get('EffectiveTradeUnits',0):.1f} "
            f"WR={m['WR']:.1%} EVw={m['EV']:+.4f} PF={m['PF']:.3f} "
            f"Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f} "
            f"AvgRisk={m.get('AvgRiskMult',1.0):.3f}")

def main():
    ft,fz=lab45.lab44.lab43.load_flow()
    hist=lab45.lab44.lab43.load_hist()
    sec=lab45.lab44.lab43.load_sec()

    h=run_period(hist,ft,fz,
        int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),'historical')
    f=run_period(sec,ft,fz,
        int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),'forward')

    result={
      'lab':'CROWDFADE_V191_PREREGISTERED_TOXIC_STATE_GATES_LAB_046',
      'base_shell':'v191d + freshness45 + adverse<=0.75 ATR + ExitZ retained',
      'variants':{
        'HARD_SKIP_RAPID30':'skip if prior same-side |Z|>=1 extreme occurred <=30m ago',
        'HARD_SKIP_HIGHVOL':'skip causal HIGH_VOL regime',
        'HARD_SKIP_RAPID30_HIGHVOL':'skip either rapid repeat or HIGH_VOL',
        'HARD_Z100_125_ONLY':'only 1.00<=|Z|<1.25',
        'HARD_Z100_125_PLUS_SKIP_RAPID30_HIGHVOL':'Z1.00-1.25 and non-toxic only',
        'RISK_TIER_TOXIC_025':'all trades retained; toxic_any=0.25x, otherwise1.0x',
        'RISK_TIER_TOXIC_050':'all trades retained; toxic_any=0.50x, otherwise1.0x',
        'RISK_TIER_Z_AND_TOXIC':'all trades retained; Z1.00-1.25=1x, 1.25-2.00=.5x, >=2=.25x; toxic_any caps at .25x'
      },
      'historical':h,'forward_2026_shadow':f,
      'limitations':[
        'BTCUSDT only.',
        '2021-2025 uses 1m OHLC; 2026 Mar-Aug uses second OHLC.',
        '2026 is reused forward-shadow/stress, not pristine OOS.',
        'All thresholds and risk multipliers were preregistered from LAB045; no within-LAB optimization.',
        'This LAB applies gates/risk weights to the frozen LAB045 trade sequence. It therefore validates selection/risk attribution on identical signal reachability, not a full re-simulation where skipped trades free occupancy and create new later signals.',
        'A full stateful reachability replay is required before EA promotion if any variant passes.',
        'v192 remains immutable canonical control and is not modified here.'
      ]}

    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))
    rows=[]
    for period,d in [('historical',h),('2026',f)]:
        for name,v in d.items():
            rows.append({'period':period,'variant':name,**v['all'],'kept_fraction':v['kept_fraction']})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)

    lines=['# LAB046 — V191 PREREGISTERED TOXIC STATE GATES','',
      'Base: **v191d + freshness45 + adverse<=0.75 ATR + ExitZ retained**.',
      '',
      'No exit change. No threshold search. Hard-gate and risk-tier branches are compared.',
      '',
      'IMPORTANT: this pass uses the identical LAB045 trade sequence with selection/risk weighting; any passing candidate must get a full stateful reachability replay before EA promotion.',
      '',
      '## Full sample']
    for period,d in [('Historical 2021–2025',h),('2026 Mar–Aug shadow',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items():
            lines.append(f"- {name}: {fmt(v['all'])}; kept={v['kept_fraction']:.1%}; risk_mix={json.dumps(v['risk_mix'])}")

    lines += ['','## Period consistency']
    for period,d in [('Historical',h),('2026',f)]:
        lines += ['',f'### {period}']
        for name,v in d.items():
            lines.append(f"- {name}: {json.dumps(v['periods'])}")

    lines += ['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
