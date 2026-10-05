from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p77=ROOT.parent/'CROWDFADE_BUY_OI_TAKER_DECOMP_LAB_077'/'run.py'
sp=importlib.util.spec_from_file_location('lab77',p77)
lab77=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab77)
lab77.DATA=DATA; lab77.OUT=OUT
lab54=lab77.lab54; lab53=lab77.lab53; lab43=lab77.lab43
lab54.DATA=DATA; lab53.DATA=DATA; lab43.DATA=DATA

FLAT=0.0002
PRIMARY_W=15
REPL_W=5
TP_GRID=[1.0,1.5,2.0,3.0]

def metrics(a):
    return lab43.metrics(np.asarray(a,float))

def add_price_returns(df,p):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    et=df.entry_ts.to_numpy(np.int64)
    entry_k=df.entry_k.to_numpy(np.int64)
    ep=C5[entry_k]
    for w in [5,15]:
        past_t=et-w*60
        j=np.searchsorted(ts,past_t,'right')-1
        out=np.full(len(df),np.nan)
        g=j>=0
        out[g]=ep[g]/C[np.asarray(j[g],dtype=int)]-1.0
        df[f'price_ch{w}']=out
    return df

def mechanism_row(oi,px,tk):
    if not (np.isfinite(oi) and np.isfinite(px) and np.isfinite(tk)):
        return 'NA'
    if px>0 and tk>0 and oi < -FLAT:
        return 'SHORT_COVERING'
    if px>0 and tk>0 and oi > FLAT:
        return 'NEW_LONG_EXPANSION'
    if px>0 and tk>0 and abs(oi)<=FLAT:
        return 'FLOW_BUY_OI_FLAT'
    if oi < -FLAT and tk<=0:
        return 'OI_DOWN_TAKER_WEAK'
    return 'CONTROL_OTHER'

def add_mechanisms(df):
    for w in [5,15]:
        df[f'mech_{w}']=[
          mechanism_row(o,p,t) for o,p,t in zip(df[f'oi_ch{w}'],df[f'price_ch{w}'],df[f'taker_delta{w}'])
        ]
    return df

def path_stats_and_fixed_tp(df,p):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    n=len(df)
    # horizon MFE/MAE in R units relative to initial stop geometry (1R=1.5 ATR)
    for h in [15,30,60,120,360]:
        mfe=np.full(n,np.nan); mae=np.full(n,np.nan)
        for i,r in df.iterrows():
            k=int(r.entry_k); ep=float(C5[k]); atr=float(A5[k]); t0=int(r.entry_ts)
            s=np.searchsorted(ts,t0,'right'); e=np.searchsorted(ts,t0+h*60,'right')
            if e<=s or not np.isfinite(atr) or atr<=0: continue
            hh=H[s:e]; ll=L[s:e]
            mfe[i]=np.nanmax((hh-ep)/(lab53.SL_ATR*atr))
            mae[i]=np.nanmax((ep-ll)/(lab53.SL_ATR*atr))
        df[f'mfeR_{h}m']=mfe; df[f'maeR_{h}m']=mae

    # first passage times and giveback flags
    for Rtar in [1.0,2.0,3.0]:
        tt=np.full(n,np.nan)
        for i,r in df.iterrows():
            k=int(r.entry_k); ep=float(C5[k]); atr=float(A5[k]); t0=int(r.entry_ts)
            target=ep+Rtar*lab53.SL_ATR*atr
            s=np.searchsorted(ts,t0,'right'); e=np.searchsorted(ts,t0+lab53.HOLD_S,'right')
            for q in range(s,min(e,len(ts))):
                if H[q]>=target:
                    tt[i]=(ts[q]-t0)/60.0; break
        df[f'time_to_{Rtar:g}R_min']=tt

    # fixed TP with same initial SL and 6h max hold, conservative same-bar tie => SL
    for Rtar in TP_GRID:
        rr=np.full(n,np.nan)
        outcome=[]
        for i,r in df.iterrows():
            k=int(r.entry_k); ep=float(C5[k]); atr=float(A5[k]); t0=int(r.entry_ts)
            sl=ep-lab53.SL_ATR*atr
            tp=ep+Rtar*lab53.SL_ATR*atr
            s=np.searchsorted(ts,t0,'right'); e=min(len(ts),np.searchsorted(ts,t0+lab53.HOLD_S,'right'))
            val=None; why='TIME'
            for q in range(s,e):
                hit_sl=L[q]<=sl; hit_tp=H[q]>=tp
                if hit_sl:
                    val=-1.0; why='SL'; break
                if hit_tp:
                    val=Rtar; why='TP'; break
            if val is None:
                ci=max(s-1,e-1)
                val=(C[ci]-ep)/(lab53.SL_ATR*atr)
            # same flat cost proxy as CF191g
            val -= (lab53.COST_BPS/10000.)*ep/(lab53.SL_ATR*atr)
            rr[i]=val
            outcome.append(why)
        df[f'fixed_tp_{Rtar:g}R_R']=rr
        df[f'fixed_tp_{Rtar:g}R_outcome']=outcome

    # giveback after reaching +1R/+2R under CURRENT runner result
    df['giveback_after_1R']=(df['time_to_1R_min'].notna() & (df.R < 0.5)).astype(int)
    df['giveback_after_2R']=(df['time_to_2R_min'].notna() & (df.R < 1.0)).astype(int)
    return df

def summarize(d,w,label):
    rows=[]
    for mech,g in d.groupby(f'mech_{w}'):
        if mech=='NA': continue
        m=metrics(g.R.to_numpy(float))
        row={
          'window':w,'period':label,'mechanism':mech,'N':len(g),
          'EV_current_R':m.get('EV',np.nan),'WR_current':m.get('WR',np.nan),'PF_current':m.get('PF',np.nan),
          'SumR_current':m.get('SumR',np.nan),'MaxDD_current_R':m.get('MaxDD_R',np.nan),
        }
        for h in [15,30,60,120,360]:
            row[f'MFE_R_{h}m']=float(g[f'mfeR_{h}m'].mean())
            row[f'MAE_R_{h}m']=float(g[f'maeR_{h}m'].mean())
        for rt in [1.0,2.0,3.0]:
            col=f'time_to_{rt:g}R_min'
            reached=g[col].notna()
            row[f'reach_{rt:g}R_pct']=float(reached.mean())
            row[f'time_to_{rt:g}R_median']=float(g.loc[reached,col].median()) if reached.any() else np.nan
        row['giveback_after_1R_pct']=float(g.giveback_after_1R.mean())
        row['giveback_after_2R_pct']=float(g.giveback_after_2R.mean())
        for rt in TP_GRID:
            fm=metrics(g[f'fixed_tp_{rt:g}R_R'].to_numpy(float))
            row[f'EV_fixed_{rt:g}R']=fm.get('EV',np.nan)
            row[f'PF_fixed_{rt:g}R']=fm.get('PF',np.nan)
        rows.append(row)
    return pd.DataFrame(rows)

def build():
    flow=lab77.load_flow_raw(); micro=lab77.load_micro()
    ft,fz=lab43.load_flow()
    hist_raw=lab43.load_hist(); sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    parts=[]
    for label,p in [('historical',hist),('forward_2026',fwd)]:
        # Exact LAB054/077 lineage and parity
        d=lab54.build_dataset(label,p,lab54.load_flow_meta(),lab54.load_1m_microstructure())
        d=d[d.side==1].copy().reset_index(drop=True)
        d=lab77.add_flow_5_15(d,flow,micro)
        d=lab77.add_exit_timing(d,p)
        d=add_price_returns(d,p)
        d=add_mechanisms(d)
        d=path_stats_and_fixed_tp(d,p)
        d['period']=label
        parts.append(d)
    return pd.concat(parts,ignore_index=True)

def comparison_table(s):
    wanted=['SHORT_COVERING','NEW_LONG_EXPANSION','FLOW_BUY_OI_FLAT','OI_DOWN_TAKER_WEAK','CONTROL_OTHER']
    return s[s.mechanism.isin(wanted)].copy()

def main():
    d=build()
    d.to_csv(OUT/'buy_flow_mechanism_events.csv',index=False)

    pooled=pd.concat([summarize(d,PRIMARY_W,'pooled'),summarize(d,REPL_W,'pooled')],ignore_index=True)
    pooled.to_csv(OUT/'mechanism_path_pooled.csv',index=False)

    splits=[]
    for period,g in d.groupby('period'):
        for w in [PRIMARY_W,REPL_W]:
            splits.append(summarize(g,w,period))
    split=pd.concat(splits,ignore_index=True)
    split.to_csv(OUT/'mechanism_path_period_split.csv',index=False)

    # Direct head-to-head deltas
    checks={}
    for w in [15,5]:
        checks[str(w)]={}
        for period,src in [('historical',split),('forward_2026',split),('pooled',pooled)]:
            z=src[(src.window==w)&(src.period==period)]
            a=z[z.mechanism=='SHORT_COVERING']
            b=z[z.mechanism=='NEW_LONG_EXPANSION']
            if len(a) and len(b):
                a=a.iloc[0]; b=b.iloc[0]
                checks[str(w)][period]={
                    'SC_N':int(a.N),'NLE_N':int(b.N),
                    'SC_EV':float(a.EV_current_R),'NLE_EV':float(b.EV_current_R),
                    'SC_MFE_60':float(a.MFE_R_60m),'NLE_MFE_60':float(b.MFE_R_60m),
                    'SC_MFE_360':float(a.MFE_R_360m),'NLE_MFE_360':float(b.MFE_R_360m),
                    'SC_time_1R':float(a.time_to_1R_median) if np.isfinite(a.time_to_1R_median) else None,
                    'NLE_time_1R':float(b.time_to_1R_median) if np.isfinite(b.time_to_1R_median) else None,
                    'SC_giveback_1R':float(a.giveback_after_1R_pct),'NLE_giveback_1R':float(b.giveback_after_1R_pct),
                    'SC_best_fixed_EV':float(max(a[f'EV_fixed_{x:g}R'] for x in TP_GRID)),
                    'NLE_best_fixed_EV':float(max(b[f'EV_fixed_{x:g}R'] for x in TP_GRID)),
                }

    result={
      'lab':'CROWDFADE_BUY_FLOW_MECHANISM_PATH_LAB_078',
      'scope':'CF191g BUY only; frozen signal/entry/current management; diagnostic path decomposition',
      'primary_window_min':15,'replication_window_min':5,
      'definitions':{
        'SHORT_COVERING':'Price>0 over window, taker_delta>0, dOI<-0.02%',
        'NEW_LONG_EXPANSION':'Price>0 over window, taker_delta>0, dOI>+0.02%',
        'FLOW_BUY_OI_FLAT':'Price>0, taker_delta>0, |dOI|<=0.02%',
        'OI_DOWN_TAKER_WEAK':'dOI<-0.02%, taker_delta<=0',
        'CONTROL_OTHER':'all remaining BUY trades'
      },
      'fixed_tp_test':'Same initial SL=1.5 ATR, 6h horizon, TP grid 1R/1.5R/2R/3R; same-bar SL/TP ambiguity resolves to SL.',
      'checks':checks,
      'limitations':['Post-hoc mechanism decomposition; no dynamic exit promoted here.',
                     '2026 Mar-Aug is reused forward-shadow/stress, not pristine OOS.',
                     'Historical path resolution is 1m; 2026 uses the frozen high-resolution price archive where available via lineage.',
                     'Price/OI/taker states are trailing and causal at entry; future path is used only for labels/outcomes.']
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    prim=comparison_table(pooled[pooled.window==15])
    repl=comparison_table(pooled[pooled.window==5])
    ps=comparison_table(split[split.window==15])
    lines=['# LAB078 — CrowdFade BUY Flow Mechanism Path','',
      'Signal, entry and current CF191g management are frozen. Diagnostic only.','',
      '## Primary: 15m flow mechanism','',prim.to_markdown(index=False),'',
      '## Replication: 5m flow mechanism','',repl.to_markdown(index=False),'',
      '## 15m historical vs forward 2026','',ps.to_markdown(index=False),'',
      '## Head-to-head checks','',json.dumps(checks,indent=2),'',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
