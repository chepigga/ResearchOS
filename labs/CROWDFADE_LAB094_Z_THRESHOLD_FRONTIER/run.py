from pathlib import Path
import json, zipfile, importlib.util, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'
BARS=DATA/'all_1m'

# Reuse the exact upstream loaders used by LAB089, but remove the frozen Z>=2.5 gate.
p88=ROOT.parent/'CROWDFADE_LS_OI_PRICE_RESPONSE_TRAP_EDGE_LAB_088'/'run.py'
sp=importlib.util.spec_from_file_location('l88',p88)
l88=importlib.util.module_from_spec(sp); sp.loader.exec_module(l88)
l88.DATA=DATA; l88.OUT=OUT
l88.l54.DATA=DATA; l88.l54.lab53.DATA=DATA; l88.l43.DATA=DATA

BUY_W=15
SELL_W=10
OI_BASE=0.0002
PRICE_BASE=-0.10
COOLDOWN_MIN=30
HOLD_MIN=120
COST_BPS=0.5

# Frozen LAB089 TRAIN Q50 thresholds. DO NOT RETUNE BY Z.
BUY_DLS=0.02126813839258385
BUY_DOI=0.00255557325829865
BUY_REJ=0.49055696545663846
SELL_DLS=0.01238254048404960
SELL_DOI=0.00163770629408790
SELL_REJ=0.39040507500162810

GRID=np.round(np.arange(0.1,3.01,0.1),1)

def asof(a,q): return np.searchsorted(a,q,'right')-1

def load_sources():
    flow=l88.l54.load_flow_meta().copy()
    ft,fz=l88.l43.load_flow()
    hist=l88.l43.prep(l88.l43.load_hist(),ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=l88.l43.prep(l88.l43.load_sec(),ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    return flow,{'historical':hist,'forward_2026':fwd}

def build_precandidates(label,p,flow):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    # Lowest grid threshold only; higher Z levels are sliced later.
    f=flow[(flow.ts>=ts[0])&(flow.ts<=ts[-1])&(flow.z.abs()>=0.1)].copy().drop_duplicates('ts').reset_index(drop=True)
    fts=flow.ts.to_numpy(np.int64); ratio=flow.ratio.to_numpy(float); oi=flow.oi.to_numpy(float)
    rows=[]
    for _,r in f.iterrows():
        t=int(r.ts); z=float(r.z); crowd=1 if z>0 else -1; side=-crowd
        w=BUY_W if side>0 else SELL_W
        j=asof(ts,t); k=asof(dt5,t)
        if j<20 or k<2: continue
        atr=float(A5[k]); ep=float(C[j])
        if not np.isfinite(atr) or atr<=0: continue
        sec=int(w*60)
        fp=asof(fts,t-sec); jp=asof(ts,t-sec); fi=asof(fts,t)
        if fp<0 or jp<0 or fi<0 or oi[fp]<=0: continue
        dls=crowd*(ratio[fi]-ratio[fp])
        doi=oi[fi]/oi[fp]-1.0
        pr=crowd*(ep-float(C[jp]))/atr
        # Keep only mandatory LAB089 BASE excluding Z threshold itself.
        if not (dls>0 and doi>OI_BASE and pr<PRICE_BASE):
            continue
        rows.append({'dataset':label,'ts':t,'z':z,'abs_z':abs(z),'crowd_dir':crowd,'side':side,
                     'window_min':w,'atr':atr,'dls':dls,'doi':doi,'price_crowd_R':pr})
    return pd.DataFrame(rows)

def dedup_for_z(g,zthr):
    h=g[g.abs_z>=zthr].sort_values('ts')
    keep=[]; last={1:-10**18,-1:-10**18}
    for i,r in h.iterrows():
        sd=int(r.side)
        if int(r.ts)-last[sd] >= COOLDOWN_MIN*60:
            keep.append(i); last[sd]=int(r.ts)
    return h.loc[keep].copy()

def lab093_admit(g):
    if len(g)==0: return g
    buy=g.side==1; sell=g.side==-1
    A=np.zeros(len(g),dtype=bool); B=np.zeros(len(g),dtype=bool); C=np.zeros(len(g),dtype=bool)
    A[buy]=(g.loc[buy,'dls'].to_numpy()>=BUY_DLS)
    B[buy]=(g.loc[buy,'doi'].to_numpy()>=BUY_DOI)
    C[buy]=((-g.loc[buy,'price_crowd_R']).to_numpy()>=BUY_REJ)
    A[sell]=(g.loc[sell,'dls'].to_numpy()>=SELL_DLS)
    B[sell]=(g.loc[sell,'doi'].to_numpy()>=SELL_DOI)
    C[sell]=((-g.loc[sell,'price_crowd_R']).to_numpy()>=SELL_REJ)
    adm=np.zeros(len(g),dtype=bool)
    adm[buy]=(A[buy].astype(int)+B[buy].astype(int)+C[buy].astype(int)>=2)
    adm[sell]=A[sell]&C[sell]  # PRICE_LS
    out=g.copy()
    out['ls_q50']=A; out['oi_q50']=B; out['rej_q50']=C
    return out[adm].copy()

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

def replay(row,bars,tsa):
    sd=int(row.side); tpR=2.5 if sd>0 else 2.0; atr=float(row.atr); t=int(row.ts)
    k=int(np.searchsorted(tsa,t,side='left'))
    if k>=len(bars): return None
    ep=float(bars.open.iloc[k]); sl=ep-sd*atr; tp=ep+sd*tpR*atr
    e=int(np.searchsorted(tsa,t+HOLD_MIN*60,side='right'))
    qend=min(e,len(bars))
    exit_px=float(bars.close.iloc[max(k,min(qend-1,len(bars)-1))]); outcome='TIME'; exit_ts=int(tsa[max(k,min(qend-1,len(bars)-1))])
    for q in range(k,qend):
        hi=float(bars.high.iloc[q]); lo=float(bars.low.iloc[q])
        hs=(lo<=sl) if sd>0 else (hi>=sl)
        ht=(hi>=tp) if sd>0 else (lo<=tp)
        if hs or ht:
            if hs: exit_px=sl; outcome='SL'
            else: exit_px=tp; outcome='TP'
            exit_ts=int(tsa[q]); break
    gross=sd*(exit_px-ep)/atr
    cost=(ep*(COST_BPS/10000.0))/atr
    return {'entry_ts':int(tsa[k]),'exit_ts':exit_ts,'netR':gross-cost,'grossR':gross,'outcome':outcome}

def stats(g):
    x=g.netR.to_numpy(float)
    if len(x)==0:return {'N':0,'EV_R':np.nan,'PF':np.nan,'SumR':0,'MaxDD_R':np.nan,'WR':np.nan}
    w=x[x>0].sum(); l=-x[x<0].sum()
    eq=np.cumsum(x); pk=np.maximum.accumulate(np.r_[0,eq]); dd=pk[1:]-eq
    return {'N':len(x),'EV_R':float(x.mean()),'PF':float(w/l) if l>0 else np.nan,'SumR':float(x.sum()),
            'MaxDD_R':float(dd.max()),'WR':float((x>0).mean())}

def month_stats(g):
    if len(g)==0:return {'trades_per_month':0,'positive_months':0,'negative_months':0}
    z=g.copy(); z['month']=pd.to_datetime(z.entry_ts,unit='s',utc=True).dt.to_period('M').astype(str)
    m=z.groupby('month').agg(N=('netR','size'),SumR=('netR','sum')).reset_index()
    return {'trades_per_month':float(m.N.mean()),'median_trades_per_month':float(m.N.median()),
            'positive_months':int((m.SumR>0).sum()),'negative_months':int((m.SumR<0).sum()),
            'avg_month_R':float(m.SumR.mean())}

def main():
    flow,periods=load_sources()
    pre=pd.concat([build_precandidates(ds,p,flow) for ds,p in periods.items()],ignore_index=True)
    pre.to_csv(OUT/'pre_z_base_candidates.csv',index=False)

    bars=load_bars(); tsa=bars.ts_open.to_numpy(np.int64)
    rows=[]; evrows=[]
    for zthr in GRID:
        for ds in ['historical','forward_2026']:
            base=dedup_for_z(pre[pre.dataset==ds],float(zthr))
            adm=lab093_admit(base)
            ers=[]
            for _,r in adm.iterrows():
                e=replay(r,bars,tsa)
                if e is not None:
                    ers.append({'dataset':ds,'z_threshold':float(zthr),'side':int(r.side),'signal_ts':int(r.ts),
                                'abs_z':float(r.abs_z),'dls':float(r.dls),'doi':float(r.doi),
                                'rejectATR':float(-r.price_crowd_R),**e})
            eg=pd.DataFrame(ers)
            if len(eg): evrows.extend(eg.to_dict('records'))
            st=stats(eg.sort_values('entry_ts') if len(eg) else eg)
            mo=month_stats(eg)
            rows.append({'dataset':ds,'z_threshold':float(zthr),'baseN_after_dedup':len(base),'admittedN':len(adm),**st,**mo})

    summ=pd.DataFrame(rows)
    summ.to_csv(OUT/'z_frontier.csv',index=False)
    pd.DataFrame(evrows).to_csv(OUT/'z_frontier_events.csv',index=False)

    # Paired historical / forward table for easy diagnosis.
    h=summ[summ.dataset=='historical'].set_index('z_threshold')
    f=summ[summ.dataset=='forward_2026'].set_index('z_threshold')
    paired=[]
    for z in GRID:
        if z not in h.index or z not in f.index: continue
        paired.append({
          'z_threshold':z,
          'hist_N':int(h.loc[z,'N']),'hist_trades_mo':h.loc[z,'trades_per_month'],'hist_EV':h.loc[z,'EV_R'],'hist_PF':h.loc[z,'PF'],'hist_DD':h.loc[z,'MaxDD_R'],
          'fwd_N':int(f.loc[z,'N']),'fwd_trades_mo':f.loc[z,'trades_per_month'],'fwd_EV':f.loc[z,'EV_R'],'fwd_PF':f.loc[z,'PF'],'fwd_DD':f.loc[z,'MaxDD_R'],
          'fwd_positive_months':int(f.loc[z,'positive_months']),'fwd_negative_months':int(f.loc[z,'negative_months'])
        })
    pair=pd.DataFrame(paired)
    pair['min_PF']=pair[['hist_PF','fwd_PF']].min(axis=1)
    pair['min_EV']=pair[['hist_EV','fwd_EV']].min(axis=1)
    pair['pf15_both']=(pair.hist_PF>=1.5)&(pair.fwd_PF>=1.5)
    pair.to_csv(OUT/'z_frontier_paired.csv',index=False)

    # Local marginal effect: what happens when threshold is raised by 0.1.
    marg=pair.copy()
    for c in ['hist_N','hist_EV','hist_PF','fwd_N','fwd_EV','fwd_PF']:
        marg['d_'+c]=marg[c].diff()
    marg.to_csv(OUT/'z_marginal_effect.csv',index=False)

    result={
      'lab':'LAB094_Z_THRESHOLD_FRONTIER',
      'only_variable':'absolute Z threshold',
      'grid':[float(x) for x in GRID],
      'frozen_base':'directional dLS>0, dOI>+0.02%, price against crowd >0.10 ATR',
      'frozen_admission':'BUY ANY2 of Q50 LS/OI/rejection; SELL PRICE+LS Q50',
      'frozen_execution':'MARKET; SL1ATR; BUY TP2.5R; SELL TP2R; hold120m; 0.5bps RT proxy',
      'frozen_q50':{
        'BUY':{'dls':BUY_DLS,'doi':BUY_DOI,'rejectATR':BUY_REJ},
        'SELL':{'dls':SELL_DLS,'doi':SELL_DOI,'rejectATR':SELL_REJ}
      },
      'limitations':['2026 Mar-Aug reused diagnostic, not pristine OOS.',
                     'Q50 thresholds were frozen at LAB089 and intentionally not retuned.',
                     '30m dedup follows LAB089 lineage and is recomputed separately for each Z threshold.',
                     'Binance 1m execution proxy, not broker-native fills.']
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    (OUT/'REPORT.md').write_text('# LAB094 — Z THRESHOLD FRONTIER\n\n'+json.dumps(result,indent=2)+'\n\n## Paired results\n\n'+pair.to_markdown(index=False)+'\n\n## Marginal effect\n\n'+marg.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
