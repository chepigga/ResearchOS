from pathlib import Path
import json, zipfile, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'
SRC094=ROOT.parent/'CROWDFADE_LAB094_Z_THRESHOLD_FRONTIER'/'output'/'pre_z_base_candidates.csv'

# Frozen LAB093 Q50 admission thresholds
BUY_DLS=0.02126813839258385
BUY_DOI=0.00255557325829865
BUY_REJ=0.49055696545663846
SELL_DLS=0.01238254048404960
SELL_DOI=0.00163770629408790
SELL_REJ=0.39040507500162810
COOLDOWN_MIN=30

LOOKBACKS=[30,60,120]
PULLBACKS=[0.10,0.20,0.30,0.50]
PROMINENCES=[0.50,0.75,1.00,1.50]
MAX_AGES=[10,20,30]

def load_flow():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:
            r=pd.read_csv(f,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r['t']=pd.to_datetime(r.create_time,utc=True,errors='coerce')
    r['oi']=pd.to_numeric(r.sum_open_interest,errors='coerce')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['t','ratio']).sort_values('t').drop_duplicates('t').reset_index(drop=True)
    mu=r.ratio.rolling(72,min_periods=72).mean()
    sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    r['ts']=r.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    return r[['ts','ratio','oi','z']].dropna().reset_index(drop=True)

def feat_one(ts,z,t,crowd,lb_min):
    # Causal: current observation is decision point; peak/trough must exist strictly before it.
    j=np.searchsorted(ts,t,'left')
    if j<=1:return None
    a=np.searchsorted(ts,t-lb_min*60,'left')
    if j-a<3:return None
    seg=z[a:j]  # exclude current => no lookahead / no self-peak
    st=ts[a:j]
    u=crowd*seg
    if len(u)<3 or not np.isfinite(u).all():return None
    pk=int(np.argmax(u))
    peak=float(u[pk]); peak_ts=int(st[pk])
    prior=u[:pk+1]
    if len(prior)<2:return None
    trough_before=float(np.min(prior))
    prominence=peak-trough_before
    now_idx=np.searchsorted(ts,t,'right')-1
    if now_idx<0:return None
    u_now=float(crowd*z[now_idx])
    pullback=peak-u_now
    peak_age=(t-peak_ts)/60.0
    start=float(u[0])
    rise_min=max((peak_ts-int(st[0]))/60.0,5.0)
    pre_slope=(peak-start)/rise_min
    return {'traj_peak_u':peak,'traj_now_u':u_now,'traj_prominence':prominence,
            'traj_pullback':pullback,'traj_peak_age_min':peak_age,
            'traj_pre_slope_per_min':pre_slope,'traj_peak_ts':peak_ts}

def lab093_admit(g):
    if len(g)==0:return g
    h=g.copy()
    buy=h.side==1; sell=h.side==-1
    A=np.zeros(len(h),bool);B=np.zeros(len(h),bool);C=np.zeros(len(h),bool)
    A[buy]=h.loc[buy,'dls'].to_numpy()>=BUY_DLS
    B[buy]=h.loc[buy,'doi'].to_numpy()>=BUY_DOI
    C[buy]=h.loc[buy,'rejectATR'].to_numpy()>=BUY_REJ
    A[sell]=h.loc[sell,'dls'].to_numpy()>=SELL_DLS
    B[sell]=h.loc[sell,'doi'].to_numpy()>=SELL_DOI
    C[sell]=h.loc[sell,'rejectATR'].to_numpy()>=SELL_REJ
    adm=np.zeros(len(h),bool)
    adm[buy]=(A[buy].astype(int)+B[buy].astype(int)+C[buy].astype(int)>=2)
    adm[sell]=A[sell]&C[sell]
    h['ls_q50']=A;h['oi_q50']=B;h['rej_q50']=C
    return h[adm].copy()

def dedup(g):
    if len(g)==0:return g
    h=g.sort_values('ts')
    keep=[];last={1:-10**18,-1:-10**18}
    for i,r in h.iterrows():
        sd=int(r.side);t=int(r.ts)
        if t-last[sd]>=COOLDOWN_MIN*60:
            keep.append(i);last[sd]=t
    return h.loc[keep].copy()

def stats(g):
    x=g.netR.to_numpy(float)
    if len(x)==0:return {'N':0,'EV_R':np.nan,'PF':np.nan,'SumR':0,'MaxDD_R':np.nan,'WR':np.nan}
    w=x[x>0].sum();l=-x[x<0].sum()
    eq=np.cumsum(x);pk=np.maximum.accumulate(np.r_[0,eq]);dd=pk[1:]-eq
    return {'N':len(x),'EV_R':float(x.mean()),'PF':float(w/l) if l>0 else np.nan,
            'SumR':float(x.sum()),'MaxDD_R':float(dd.max()),'WR':float((x>0).mean())}

def monthstats(g):
    if len(g)==0:return {'trades_per_month':0,'positive_months':0,'negative_months':0,'avg_month_R':np.nan}
    h=g.copy();h['month']=pd.to_datetime(h.entry_ts,unit='s',utc=True).dt.to_period('M').astype(str)
    m=h.groupby('month').agg(N=('netR','size'),SumR=('netR','sum')).reset_index()
    return {'trades_per_month':float(m.N.mean()),'positive_months':int((m.SumR>0).sum()),
            'negative_months':int((m.SumR<0).sum()),'avg_month_R':float(m.SumR.mean())}

def main():
    base=pd.read_csv(SRC094)
    base['rejectATR']=-base['price_crowd_R']
    flow=load_flow(); fts=flow.ts.to_numpy(np.int64); fz=flow.z.to_numpy(float)

    # Build causal trajectory features for every base candidate and lookback.
    feature_rows=[]
    for _,r in base.iterrows():
        crowd=-int(r.side)
        for lb in LOOKBACKS:
            f=feat_one(fts,fz,int(r.ts),crowd,lb)
            if f is not None:
                feature_rows.append({**r.to_dict(),'lookback_min':lb,**f})
    feat=pd.DataFrame(feature_rows)
    feat.to_csv(OUT/'trajectory_features.csv',index=False)

    rows=[]
    # Benchmark exact LAB093 fixed Z>=2.5 using same pre-Z base universe.
    for ds in ['historical','forward_2026']:
        g=base[(base.dataset==ds)&(base.abs_z>=2.5)].copy()
        g=dedup(g)
        g=lab093_admit(g).sort_values('entry_ts')
        rows.append({'kind':'BENCH_Z2P5','dataset':ds,'lookback_min':np.nan,'pullback':np.nan,
                     'prominence':np.nan,'max_age':np.nan,**stats(g),**monthstats(g)})

    # Trajectory trigger grid. No absolute-Z requirement.
    event_rows=[]
    for lb in LOOKBACKS:
      qlb=feat[feat.lookback_min==lb]
      for pb in PULLBACKS:
       for pr in PROMINENCES:
        for age in MAX_AGES:
         for ds in ['historical','forward_2026']:
            g=qlb[(qlb.dataset==ds)&
                  (qlb.traj_pullback>=pb)&
                  (qlb.traj_prominence>=pr)&
                  (qlb.traj_peak_age_min<=age)&
                  (qlb.traj_peak_age_min>=0)].copy()
            # First causal trigger in each 30m episode, then frozen LAB093 admission.
            g=dedup(g)
            g=lab093_admit(g).sort_values('entry_ts')
            if len(g):
                event_rows.extend(g.assign(trigger=f'L{lb}_PB{pb}_PR{pr}_A{age}').to_dict('records'))
            rows.append({'kind':'TRAJECTORY','dataset':ds,'lookback_min':lb,'pullback':pb,
                         'prominence':pr,'max_age':age,**stats(g),**monthstats(g)})

    res=pd.DataFrame(rows)
    res.to_csv(OUT/'trajectory_grid.csv',index=False)

    # Pair HIST/FWD. Rank using historical robustness first; forward is shown, not used to fit thresholds.
    tr=res[res.kind=='TRAJECTORY']
    H=tr[tr.dataset=='historical'].copy()
    F=tr[tr.dataset=='forward_2026'].copy()
    keys=['lookback_min','pullback','prominence','max_age']
    pair=H.merge(F,on=keys,suffixes=('_hist','_fwd'))
    pair['hist_target_20_50']=(pair.trades_per_month_hist>=20)&(pair.trades_per_month_hist<=50)
    pair['hist_pf15']=pair.PF_hist>=1.5
    pair['hist_score']=(100*pair.hist_pf15.astype(int)+50*pair.hist_target_20_50.astype(int)
                        +20*pair.EV_R_hist+5*pair.PF_hist-0.25*pair.MaxDD_R_hist)
    pair=pair.sort_values(['hist_score','PF_hist','EV_R_hist'],ascending=False)
    pair.to_csv(OUT/'trajectory_paired_ranked.csv',index=False)
    pair.head(25).to_csv(OUT/'top25_historical_selected_forward_check.csv',index=False)

    # Best candidates that transfer reasonably, only for diagnostic summary.
    diag=pair[(pair.PF_hist>=1.5)&(pair.EV_R_hist>0)&(pair.PF_fwd>=1.2)&(pair.EV_R_fwd>0)].copy()
    diag.to_csv(OUT/'robust_diagnostic_candidates.csv',index=False)

    pd.DataFrame(event_rows).to_csv(OUT/'trajectory_events_full.csv',index=False)

    bench=res[res.kind=='BENCH_Z2P5']
    summary={
      'lab':'LAB095_CAUSAL_Z_TRAJECTORY_PEAK_TROUGH',
      'hypothesis':'Trajectory / peak-trough reversal in Z may time crowd traps better than a fixed absolute Z gate.',
      'causal_definition':'For trade side, transform u=crowd_dir*Z. Use only observations strictly before decision time to find trailing directional peak. Trigger when current u has pulled back from that peak by >= pullback, peak prominence >= prominence, and peak age <= max_age.',
      'grid':{'lookback_min':LOOKBACKS,'pullback_Z':PULLBACKS,'prominence_Z':PROMINENCES,'max_peak_age_min':MAX_AGES},
      'absolute_Z_gate':'NONE for trajectory variants',
      'benchmark':'Frozen LAB093 with |Z|>=2.5',
      'frozen_other_logic':'LAB089 base excluding Z + LAB093 BUY ANY2 / SELL PRICE_LS + existing MARKET outcomes from LAB094',
      'benchmark_rows':bench.to_dict('records'),
      'methodology_note':'Candidate selection must be based on historical rows; 2026 is reused diagnostic transfer only and is not pristine OOS.',
      'limitations':['Multiple trajectory combinations are discovery and require freeze + future OOS.',
                     '2026 Mar-Aug is reused diagnostic data.',
                     'Trajectory test currently sits on the same non-Z LAB089 base universe: dLS>0, dOI>0.02%, price rejection>0.10ATR.',
                     'Execution outcomes are inherited from LAB094 Binance 1m proxy.']
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB095 — CAUSAL Z TRAJECTORY / PEAK-TROUGH\n\n'+json.dumps(summary,indent=2,default=float)+
                                 '\n\n## Top historical-selected candidates + forward check\n\n'+pair.head(25).to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
