from pathlib import Path
import json, zipfile, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'/'all_1m'
SRC=ROOT.parent/'CROWDFADE_EXTREME_LS_TRAP_TRIGGER_LAB_089'/'output'/'dedup_events.csv'

CAND={1:15.0,-1:10.0}  # BUY 15m, SELL 10m
RESP_MIN=[1,3]
RESP_THR_ATR=0.10
LIMIT_RETRACE_ATR=0.25
LIMIT_TTL_MIN=10
HOLD_MIN=120
TPS=[1.5,2.0,2.5]
COST_BPS=[0.0,0.5,2.0]  # round-trip sensitivity proxies

def load_bars():
    rows=[]
    for zp in sorted(DATA.glob('BTCUSDT-1m-*.zip')):
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

def frozen_q50(d):
    keep=[]
    meta=[]
    for sd,w in CAND.items():
        tr=d[(d.dataset=='historical')&(d.side==sd)&(d.window_min==w)]
        qdls=float(tr.dls.quantile(.5)); qoi=float(tr.doi.quantile(.5)); qrej=float((-tr.price_crowd_R).quantile(.5))
        g=d[(d.side==sd)&(d.window_min==w)].copy()
        g=g[(g.dls>=qdls)&(g.doi>=qoi)&((-g.price_crowd_R)>=qrej)]
        keep.append(g)
        meta.append({'side':'BUY' if sd>0 else 'SELL','window_min':w,'dls_q50':qdls,'doi_q50':qoi,'reject_q50':qrej})
    return pd.concat(keep,ignore_index=True).sort_values('ts').reset_index(drop=True),meta

def next_bar_idx(ts_arr, decision_ts):
    return int(np.searchsorted(ts_arr, int(decision_ts), side='left'))

def find_entry(row,bars,ts_arr,mode):
    sd=int(row.side); atr=float(row.atr); t=int(row.ts)
    i=next_bar_idx(ts_arr,t)
    if i>=len(bars): return None
    decision_px=float(row.entry)
    if mode=='MARKET':
        return i,float(bars.open.iloc[i]),int(ts_arr[i]),'market'
    if mode.startswith('RESP'):
        mins=int(mode.replace('RESP',''))
        end_t=t+mins*60
        j=int(np.searchsorted(ts_arr,end_t,side='left'))
        if j>=len(bars): return None
        response=sd*(float(bars.close.iloc[j])-decision_px)/atr
        if response<RESP_THR_ATR: return None
        k=min(j+1,len(bars)-1)
        return k,float(bars.open.iloc[k]),int(ts_arr[k]),f'resp{mins}'
    if mode=='LIMIT':
        level=decision_px - sd*LIMIT_RETRACE_ATR*atr
        e=int(np.searchsorted(ts_arr,t+LIMIT_TTL_MIN*60,side='right'))
        for k in range(i,min(e,len(bars))):
            lo=float(bars.low.iloc[k]); hi=float(bars.high.iloc[k])
            if lo<=level<=hi:
                return k,float(level),int(ts_arr[k]),'limit'
        return None
    return None

def replay_trade(row,bars,ts_arr,mode,tpR):
    ent=find_entry(row,bars,ts_arr,mode)
    if ent is None:return {'filled':0}
    k,ep,ets,reason=ent
    sd=int(row.side); atr=float(row.atr)
    stop=ep-sd*atr; tp=ep+sd*tpR*atr
    end_t=ets+HOLD_MIN*60
    e=int(np.searchsorted(ts_arr,end_t,side='right'))
    exit_px=float(bars.close.iloc[min(e-1,len(bars)-1)]); exit_ts=int(ts_arr[min(e-1,len(bars)-1)]); outcome='TIME'
    mfe=0.0; mae=0.0
    for q in range(k,min(e,len(bars))):
        hi=float(bars.high.iloc[q]); lo=float(bars.low.iloc[q])
        fav=(hi-ep)/atr if sd>0 else (ep-lo)/atr
        adv=(ep-lo)/atr if sd>0 else (hi-ep)/atr
        mfe=max(mfe,fav); mae=max(mae,adv)
        hit_sl=(lo<=stop) if sd>0 else (hi>=stop)
        hit_tp=(hi>=tp) if sd>0 else (lo<=tp)
        if hit_sl or hit_tp:
            if hit_sl: # conservative same-bar ordering
                exit_px=stop; outcome='SL'
            else:
                exit_px=tp; outcome='TP'
            exit_ts=int(ts_arr[q]); break
    grossR=sd*(exit_px-ep)/atr
    res={'filled':1,'entry_ts':ets,'entry_px':ep,'exit_ts':exit_ts,'exit_px':exit_px,'outcome':outcome,'grossR':grossR,'mfeR':mfe,'maeR':mae}
    for bps in COST_BPS:
        costR=(ep*(bps/10000.0))/atr
        res[f'netR_{str(bps).replace(".","p")}bps']=grossR-costR
    return res

def metrics(g,col):
    x=g[col].to_numpy(float)
    if len(x)==0:return {'N':0}
    w=x[x>0].sum(); l=-x[x<0].sum()
    eq=np.cumsum(x); peak=np.maximum.accumulate(np.r_[0,eq]); dd=peak[1:]-eq
    return {'N':len(x),'EV_R':float(x.mean()),'WR':float((x>0).mean()),'PF':float(w/l) if l>0 else np.nan,
            'SumR':float(x.sum()),'MaxDD_R':float(dd.max()) if len(dd) else 0.0,
            'Recovery':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else np.nan}

def main():
    d=pd.read_csv(SRC)
    d,freeze=frozen_q50(d)
    bars=load_bars(); ts_arr=bars.ts_open.to_numpy(np.int64)
    rec=[]
    modes=['MARKET','RESP1','RESP3','LIMIT']
    for _,r in d.iterrows():
      for mode in modes:
        for tp in TPS:
          z=replay_trade(r,bars,ts_arr,mode,tp)
          rec.append({'dataset':r.dataset,'side':int(r.side),'signal_ts':int(r.ts),'window_min':float(r.window_min),
                      'mode':mode,'tpR':tp,'atr':float(r.atr),**z})
    x=pd.DataFrame(rec)
    x.to_csv(OUT/'execution_events.csv',index=False)

    rows=[]
    for (ds,sd,mode,tp),g0 in x.groupby(['dataset','side','mode','tpR']):
        fill_rate=float(g0.filled.mean()); g=g0[g0.filled==1].copy()
        for bps in COST_BPS:
            col=f'netR_{str(bps).replace(".","p")}bps'
            m=metrics(g.sort_values('entry_ts'),col)
            rows.append({'dataset':ds,'side':'BUY' if sd>0 else 'SELL','mode':mode,'tpR':tp,
                         'cost_bps_rt':bps,'signals':len(g0),'fill_rate':fill_rate,
                         'MFE_mean':float(g.mfeR.mean()) if len(g) else np.nan,
                         'MAE_mean':float(g.maeR.mean()) if len(g) else np.nan,**m})
    s=pd.DataFrame(rows); s.to_csv(OUT/'execution_summary.csv',index=False)

    # Monthly P/L for the exact standalone LAB089 bot configuration:
    # BUY MARKET TP2.5R, SELL MARKET TP2.0R, 0.5 bps RT proxy.
    live=x[(x.mode=='MARKET') & (x.filled==1) & (((x.side==1)&(x.tpR==2.5)) | ((x.side==-1)&(x.tpR==2.0)))].copy()
    live['month']=pd.to_datetime(live.entry_ts,unit='s',utc=True).dt.to_period('M').astype(str)
    live['netR']=live['netR_0p5bps']
    monthly_side=(live.groupby(['dataset','month','side'])
                    .agg(N=('netR','size'),SumR=('netR','sum'),EV_R=('netR','mean'),
                         WR=('netR',lambda z: float((z>0).mean())))
                    .reset_index())
    monthly_side['side']=monthly_side.side.map({1:'BUY',-1:'SELL'})
    monthly_total=(live.groupby(['dataset','month'])
                     .agg(N=('netR','size'),SumR=('netR','sum'),EV_R=('netR','mean'),
                          WR=('netR',lambda z: float((z>0).mean())))
                     .reset_index())
    monthly_side.to_csv(OUT/'monthly_profit_by_side.csv',index=False)
    monthly_total.to_csv(OUT/'monthly_profit_total.csv',index=False)

    # pooled side-aware candidate comparison and best historical per side, then unchanged 2026 report
    rank=[]
    hist=s[(s.dataset=='historical')&(s.cost_bps_rt==0.5)]
    for side in ['BUY','SELL']:
        h=hist[hist.side==side].sort_values(['EV_R','MaxDD_R'],ascending=[False,True])
        for n,(_,r) in enumerate(h.iterrows(),1):
            f=s[(s.dataset=='forward_2026')&(s.cost_bps_rt==0.5)&(s.side==side)&(s.mode==r.mode)&(s.tpR==r.tpR)]
            rank.append({'side':side,'rank_hist':n,'mode':r.mode,'tpR':r.tpR,
                         'hist_N':int(r.N),'hist_fill':float(r.fill_rate),'hist_EV':float(r.EV_R),'hist_PF':float(r.PF),'hist_DD':float(r.MaxDD_R),
                         'fwd_N':int(f.N.iloc[0]) if len(f) else 0,'fwd_fill':float(f.fill_rate.iloc[0]) if len(f) else np.nan,
                         'fwd_EV':float(f.EV_R.iloc[0]) if len(f) else np.nan,'fwd_PF':float(f.PF.iloc[0]) if len(f) else np.nan,'fwd_DD':float(f.MaxDD_R.iloc[0]) if len(f) else np.nan})
    rank=pd.DataFrame(rank); rank.to_csv(OUT/'historical_rank_forward_check.csv',index=False)

    summary={'lab':'LAB091_LAB089_EXECUTION_REPLAY',
             'frozen_trigger_q50':freeze,
             'entry_modes':{'MARKET':'next 1m open after LAB089 decision','RESP1':'1m response >= +0.10 ATR in trade direction, then next 1m open','RESP3':'3m response >= +0.10 ATR, then next 1m open','LIMIT':'0.25 ATR better-price retracement limit, TTL 10m'},
             'risk_model':'SL=1 ATR from actual fill; TP=1.5/2/2.5R; max hold=120m; same-bar SL/TP ambiguity resolved as SL',
             'cost_sensitivity_bps_rt':COST_BPS,
             'ranking_basis':'historical, 0.5 bps round-trip proxy, ranked by EV then lower MaxDD',
             'limitations':['Binance futures 1m execution proxy, not IC Markets broker-native spread/fills.',
                            'No concurrency/margin interaction; DD is sequential trade-outcome DD.',
                            '2026 Mar-Aug is reused diagnostic data, not pristine OOS.',
                            'Limit touch assumes fill at limit; real queue/slippage can be worse.']}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB091 — LAB089 EXECUTION REPLAY\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## Summary\n\n'+s.to_markdown(index=False)+'\n\n## Ranking\n\n'+rank.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
