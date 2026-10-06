from pathlib import Path
import json, zipfile, importlib.util, numpy as np, pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'; BARS=DATA/'all_1m'

# Reuse validated upstream data conventions.
p88=ROOT.parent/'CROWDFADE_LS_OI_PRICE_RESPONSE_TRAP_EDGE_LAB_088'/'run.py'
sp=importlib.util.spec_from_file_location('l88',p88)
l88=importlib.util.module_from_spec(sp); sp.loader.exec_module(l88)
l88.DATA=DATA; l88.OUT=OUT
l88.l54.DATA=DATA; l88.l54.lab53.DATA=DATA; l88.l43.DATA=DATA

LOOKBACKS=[15,30,60]
PROM=[0.50,0.75,1.00,1.50]
PULL=[0.10,0.20,0.30,0.50]
VARIANTS=['TRAJ_ONLY','TRAJ_OI','TRAJ_PRICE','TRAJ_OI_PRICE']
OI_BASE=0.0002
PRICE_REJECT_BASE=0.10
COOLDOWN_MIN=30
HOLD_MIN=120
COST_BPS=0.5

def asof(a,q): return np.searchsorted(a,q,'right')-1

def load_sources():
    flow=l88.l54.load_flow_meta().copy()
    ft,fz=l88.l43.load_flow()
    hist=l88.l43.prep(l88.l43.load_hist(),ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=l88.l43.prep(l88.l43.load_sec(),ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    return flow,{'historical':hist,'forward_2026':fwd}

def load_bars():
    rows=[]
    for zp in sorted(BARS.glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
        q.columns=['open_ms','open','high','low','close']
        q['ts_open']=(pd.to_numeric(q.open_ms,errors='coerce')//1000).astype('Int64')
        for c in ['open','high','low','close']: q[c]=pd.to_numeric(q[c],errors='coerce')
        q=q.dropna().copy(); q['ts_open']=q.ts_open.astype(np.int64)
        rows.append(q[['ts_open','open','high','low','close']])
    return pd.concat(rows,ignore_index=True).sort_values('ts_open').drop_duplicates('ts_open').reset_index(drop=True)

@njit(cache=True)
def replay_batch(sig_t, sides, atrs, tsa, opens, highs, lows, closes):
    n=len(sig_t)
    entry_ts=np.empty(n,np.int64); exit_ts=np.empty(n,np.int64)
    netR=np.empty(n,np.float64); grossR=np.empty(n,np.float64); outcome=np.empty(n,np.int8)
    for i in range(n):
        t=sig_t[i]; side=sides[i]; atr=atrs[i]
        k=np.searchsorted(tsa,t)
        if k>=len(tsa) or atr<=0:
            entry_ts[i]=-1; exit_ts[i]=-1; netR[i]=np.nan; grossR[i]=np.nan; outcome[i]=-1
            continue
        ep=opens[k]; tpR=2.5 if side>0 else 2.0
        sl=ep-side*atr; tp=ep+side*tpR*atr
        e=np.searchsorted(tsa,t+HOLD_MIN*60,side='right')
        qend=min(e,len(tsa))
        qi=max(k,min(qend-1,len(tsa)-1))
        xp=closes[qi]; xt=tsa[qi]; oc=0
        for q in range(k,qend):
            hi=highs[q]; lo=lows[q]
            hs=(lo<=sl) if side>0 else (hi>=sl)
            ht=(hi>=tp) if side>0 else (lo<=tp)
            if hs or ht:
                if hs:
                    xp=sl; oc=-1
                else:
                    xp=tp; oc=1
                xt=tsa[q]
                break
        gr=side*(xp-ep)/atr
        cost=(ep*(COST_BPS/10000.0))/atr
        entry_ts[i]=tsa[k]; exit_ts[i]=xt; grossR[i]=gr; netR[i]=gr-cost; outcome[i]=oc
    return entry_ts,exit_ts,netR,grossR,outcome

def causal_candidates(label,p,flow,bars,tsa,lookback):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    # flow contains 5m-ish ratio/OI observations and rolling Z.
    f=flow[(flow.ts>=ts[0])&(flow.ts<=ts[-1])].copy().dropna(subset=['z']).drop_duplicates('ts').reset_index(drop=True)
    ft=f.ts.to_numpy(np.int64); z=f.z.to_numpy(float); ratio=f.ratio.to_numpy(float); oi=f.oi.to_numpy(float)
    full_t=flow.ts.to_numpy(np.int64); full_oi=flow.oi.to_numpy(float)
    rows=[]
    nback=max(2,int(round(lookback/5)))
    for i in range(nback+1,len(f)):
        t=int(ft[i]); cur=float(z[i])
        past=z[i-nback:i]  # strictly prior values only
        if len(past)<nback or not np.all(np.isfinite(past)): continue
        j=asof(ts,t); k=asof(dt5,t)
        if j<20 or k<2: continue
        atr=float(A5[k])
        if not np.isfinite(atr) or atr<=0: continue

        # Causal SELL: prior positive peak, then confirmed drop from that peak.
        peak_idx=int(np.argmax(past)); peak=float(past[peak_idx])
        pre_peak=past[:peak_idx+1]
        peak_prom=peak-float(np.min(pre_peak)) if len(pre_peak) else 0.0
        peak_pull=peak-cur
        peak_slope=(peak-float(past[0]))/max(5.0,(peak_idx+1)*5.0)

        # Causal BUY: prior negative trough, then confirmed rebound from that trough.
        trough_idx=int(np.argmin(past)); trough=float(past[trough_idx])
        pre_trough=past[:trough_idx+1]
        trough_prom=float(np.max(pre_trough))-trough if len(pre_trough) else 0.0
        trough_pull=cur-trough
        trough_slope=(float(past[0])-trough)/max(5.0,(trough_idx+1)*5.0)

        for side in (1,-1):
            if side<0:
                extreme=peak
                prominence=peak_prom
                pullback=peak_pull
                slope=peak_slope
                # peak must be on LONG side and strictly before current.
                if not (peak>0 and peak_idx<=len(past)-1 and pullback>0): continue
                crowd=1
                w=10
            else:
                extreme=trough
                prominence=trough_prom
                pullback=trough_pull
                slope=trough_slope
                if not (trough<0 and trough_idx<=len(past)-1 and pullback>0): continue
                crowd=-1
                w=15

            sec=w*60
            fi=asof(full_t,t); fp=asof(full_t,t-sec); jp=asof(ts,t-sec)
            if fi<0 or fp<0 or jp<0 or full_oi[fp]<=0: continue
            doi=full_oi[fi]/full_oi[fp]-1.0
            pr=crowd*(float(C[j])-float(C[jp]))/atr
            reject=-pr
            rows.append({'dataset':label,'ts':t,'side':side,'lookback_min':lookback,
                         'z_current':cur,'z_extreme':extreme,'prominence':prominence,
                         'pullback':pullback,'pre_slope_per_min':slope,
                         'doi':doi,'rejectATR':reject,'atr':atr})
    return pd.DataFrame(rows)

def dedup(g):
    if len(g)==0:return g
    h=g.sort_values('ts'); keep=[]; last={1:-10**18,-1:-10**18}
    for i,r in h.iterrows():
        sd=int(r.side)
        if int(r.ts)-last[sd] >= COOLDOWN_MIN*60:
            keep.append(i); last[sd]=int(r.ts)
    return h.loc[keep].copy()

def metrics(g):
    x=g.netR.to_numpy(float)
    if len(x)==0:return {'N':0,'EV_R':np.nan,'PF':np.nan,'SumR':0,'MaxDD_R':np.nan,'WR':np.nan}
    w=x[x>0].sum(); l=-x[x<0].sum(); eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=pk[1:]-eq
    return {'N':len(x),'EV_R':float(x.mean()),'PF':float(w/l) if l>0 else np.nan,
            'SumR':float(x.sum()),'MaxDD_R':float(dd.max()),'WR':float((x>0).mean())}

def monthly(g):
    if len(g)==0:return {'trades_per_month':0,'positive_months':0,'negative_months':0}
    z=g.copy(); z['month']=pd.to_datetime(z.entry_ts,unit='s',utc=True).dt.to_period('M').astype(str)
    m=z.groupby('month').agg(N=('netR','size'),SumR=('netR','sum')).reset_index()
    return {'trades_per_month':float(m.N.mean()),'positive_months':int((m.SumR>0).sum()),
            'negative_months':int((m.SumR<0).sum()),'avg_month_R':float(m.SumR.mean())}

def apply_variant(g,variant):
    if variant=='TRAJ_ONLY': return g
    if variant=='TRAJ_OI': return g[g.doi>OI_BASE]
    if variant=='TRAJ_PRICE': return g[g.rejectATR>PRICE_REJECT_BASE]
    if variant=='TRAJ_OI_PRICE': return g[(g.doi>OI_BASE)&(g.rejectATR>PRICE_REJECT_BASE)]
    raise ValueError(variant)

def main():
    flow,periods=load_sources()
    bars=load_bars(); tsa=bars.ts_open.to_numpy(np.int64)

    raw=[]
    for lb in LOOKBACKS:
        for ds,p in periods.items():
            q=causal_candidates(ds,p,flow,bars,tsa,lb)
            if len(q): raw.append(q)
    raw=pd.concat(raw,ignore_index=True)

    # One compiled batch execution replay for all trajectory observations.
    bt=bars.ts_open.to_numpy(np.int64)
    bo=bars.open.to_numpy(float); bh=bars.high.to_numpy(float); bl=bars.low.to_numpy(float); bc=bars.close.to_numpy(float)
    et,xt,nr,gr,oc=replay_batch(raw.ts.to_numpy(np.int64),raw.side.to_numpy(np.int64),
                                raw.atr.to_numpy(float),bt,bo,bh,bl,bc)
    raw['entry_ts']=et; raw['exit_ts']=xt; raw['netR']=nr; raw['grossR']=gr
    raw['outcome']=np.where(oc==1,'TP',np.where(oc==-1,'SL','TIME'))
    raw=raw[np.isfinite(raw.netR)&(raw.entry_ts>=0)].copy()
    raw.to_csv(OUT/'trajectory_raw_candidates.csv',index=False)

    rows=[]
    for lb in LOOKBACKS:
      base=raw[raw.lookback_min==lb]
      for prom in PROM:
        for pull in PULL:
          shaped=base[(base.prominence>=prom)&(base.pullback>=pull)&(base.pre_slope_per_min>0)].copy()
          for variant in VARIANTS:
            vg=apply_variant(shaped,variant)
            for ds in ['historical','forward_2026']:
                dg=dedup(vg[vg.dataset==ds])
                rows.append({'lookback_min':lb,'prominence_min':prom,'pullback_min':pull,
                             'variant':variant,'dataset':ds,**metrics(dg.sort_values('entry_ts')),**monthly(dg)})

    res=pd.DataFrame(rows)
    res.to_csv(OUT/'trajectory_grid.csv',index=False)

    # Pair historical/forward and rank by robustness, not raw in-sample EV.
    h=res[res.dataset=='historical'].copy()
    f=res[res.dataset=='forward_2026'].copy()
    keys=['lookback_min','prominence_min','pullback_min','variant']
    pair=h.merge(f,on=keys,suffixes=('_hist','_fwd'))
    pair['minPF']=pair[['PF_hist','PF_fwd']].min(axis=1)
    pair['minEV']=pair[['EV_R_hist','EV_R_fwd']].min(axis=1)
    pair['all_fwd_positive']=pair.negative_months_fwd==0
    pair['score']=50*pair.minPF+25*pair.minEV+10*pair.all_fwd_positive.astype(int)-0.15*pair.MaxDD_R_hist
    pair=pair.sort_values('score',ascending=False)
    pair.to_csv(OUT/'trajectory_paired_ranked.csv',index=False)

    # Frequency band useful for a future visual indicator / live candidate.
    freq=pair[(pair.trades_per_month_hist>=20)&(pair.trades_per_month_hist<=50)&
              (pair.trades_per_month_fwd>=15)&(pair.trades_per_month_fwd<=50)].copy()
    freq.to_csv(OUT/'trajectory_frequency_20_50.csv',index=False)

    # Benchmark copied from LAB094 frozen LAB093 Z=2.5 output if available.
    bench_path=ROOT.parent/'CROWDFADE_LAB094_Z_THRESHOLD_FRONTIER'/'output'/'z_frontier_paired.csv'
    benchmark={}
    if bench_path.exists():
        b=pd.read_csv(bench_path); b=b[np.isclose(b.z_threshold,2.5)]
        if len(b): benchmark=b.iloc[0].to_dict()

    summary={
      'lab':'LAB095_CAUSAL_Z_TRAJECTORY_PEAK_TROUGH',
      'causality':'At timestamp t, extrema are computed only from Z observations strictly before t. Entry occurs only after current Z has reversed from the prior peak/trough by the tested pullback amount.',
      'grid':{'lookback_min':LOOKBACKS,'prominence_min':PROM,'pullback_min':PULL,'variants':VARIANTS},
      'fixed_execution':'MARKET next 1m open; SL1ATR; BUY TP2.5R; SELL TP2R; hold120m; 0.5bps RT proxy; 30m side cooldown',
      'benchmark_Z2p5_LAB093':benchmark,
      'limitations':['2026 Mar-Aug reused diagnostic, not pristine OOS.',
                     'Grid is research/discovery; selected trajectory parameters require later frozen validation.',
                     'Binance 1m execution proxy, not broker-native fills.']
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    top=pair.head(25)
    (OUT/'REPORT.md').write_text('# LAB095 — CAUSAL Z TRAJECTORY / PEAK-TROUGH\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## Top robust candidates\n\n'+top.to_markdown(index=False)+'\n\n## 20-50 trades/month candidates\n\n'+freq.head(40).to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
