#!/usr/bin/env python3
"""SELL_CORE_010 — AUTONOMOUS_FUNDING_Q4_STATE.

Preregistered after price-action SELL_CORE_004..009 failed to produce a stable SELL core.
This lab tests funding as an AUTONOMOUS state, not as a filter inside FVG/B3/CHoCH/v283.

Frozen funding context:
- Binance BTCUSDT perpetual funding, UTC, 8h observations.
- funding_3d = trailing mean of 9 funding observations.
- PRIMARY strict2000 percentile: exact SELL_CORE_001 convention; current funding_3d vs PREVIOUS 2000 valid
  funding_3d observations; inclusive ECDF mean(prev <= current); Q4 >= 0.75.
  This necessarily has a long warm-up and cannot cover 2019-2020.
- 8-year sensitivity expanding90: previous min(2000, available) funding_3d observations, minimum 90 previous
  observations, inclusive ECDF; causal and outcome-blind, but NEW in this lab (not legacy frozen logic).
- strict2000 midrank Q4 is tie-sensitivity only.

Autonomous strategy:
- state = Q4 only; no price/FVG/B3/CHoCH/v283/funding x other AND gates.
- periodic SELL every 8h while Q4 state is active.
- phase 0h: decision at funding timestamp; phase +4h: same known state carried four hours forward.
- execution = next H1 open STRICTLY after decision time.
- ATR for stop is known at decision time: Wilder ATR14 from completed H1 bars only.
- SL = 1.5 x H1 ATR14; no TP; 48h primary / 72h sensitivity.
- frozen ResearchOS BTC cost proxy = $27.5/BTC round-turn.
- risk diagnostic: maximum simultaneous initial-risk budget 0.5% per continuous funding-state episode.
  With 8h cadence and 48h hold, max six overlapping entries => 0.083333% initial risk per entry.

Inference / robustness:
- yearly EV/PF.
- phase 0/+4 paired robustness.
- bootstrap clusters / episode returns by continuous funding-state episode, not individual trades.
- Q1-Q3 periodic SELL is a baseline, not a gate.
- RV168 control is diagnostic only because no exact old RV168 formula was recoverable from frozen findings.
  Newly frozen here: sqrt(sum(last 168 completed H1 close-to-close log-return^2)).
- RV control: correlation, within-RV-quintile Q4 vs non-Q4, and episode-cluster bootstrap OLS
  R48 ~ Q4 + z(log RV168) + year fixed effects.

Data:
- binance_btc_flow.csv release asset 511572318, SHA256 e9501054d851fd6dfc605f97671c59f15afa9b259620191756c45af62031417e
- binance_btc_funding.csv asset 511572302, SHA256 df4dc9d6c0c28069e1f1a20c4d1f0ffb3d7195869aae151263ec8fff10052ef8
"""
from pathlib import Path
import numpy as np
import pandas as pd

OUT=Path('sell_core_010_out'); OUT.mkdir(exist_ok=True)
FLOW='binance_btc_flow.csv'; FUND='binance_btc_funding.csv'
COST_USD=27.5; STOP_ATR=1.5; HOLDS=(48,72); PHASES=(0,4)
EP_RISK_PCT=0.5; MAX_CONCURRENT=6; RISK_PER_TRADE_PCT=EP_RISK_PCT/MAX_CONCURRENT
BOOT=20000; REG_BOOT=5000; SEED=410010


def pf(x):
    z=pd.Series(x).dropna(); gp=float(z[z>0].sum()); gl=float(-z[z<0].sum())
    return gp/gl if gl>0 else (float('inf') if gp>0 else np.nan)


def wilder(s,n):
    return s.ewm(alpha=1/n,adjust=False,min_periods=n).mean()


def load_data():
    h=pd.read_csv(FLOW); f=pd.read_csv(FUND)
    h['time']=pd.to_datetime(h.time,format='%Y.%m.%d %H:%M',errors='coerce',utc=True).dt.tz_localize(None)
    f['time']=pd.to_datetime(f.time,format='%Y.%m.%d %H:%M',errors='coerce',utc=True).dt.tz_localize(None)
    for c in ['open','high','low','close']: h[c]=pd.to_numeric(h[c],errors='coerce')
    f['funding']=pd.to_numeric(f.funding,errors='coerce')
    h=h.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    f=f.dropna(subset=['time','funding']).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    # H1 indicators: values become known at close_time.
    h['close_time']=h.time+pd.Timedelta(hours=1)
    pc=h.close.shift(1)
    tr=pd.concat([h.high-h.low,(h.high-pc).abs(),(h.low-pc).abs()],axis=1).max(axis=1)
    h['atr14']=wilder(tr,14)
    lr=np.log(h.close/h.close.shift(1))
    h['rv168']=np.sqrt((lr*lr).rolling(168,min_periods=168).sum())
    return h,f


def funding_context(f):
    z=f.copy(); z['funding_3d']=z.funding.rolling(9,min_periods=9).mean()
    v=z.funding_3d.to_numpy(float); n=len(z)
    strict_inc=np.full(n,np.nan); strict_mid=np.full(n,np.nan); exp_inc=np.full(n,np.nan)
    for i in range(n):
        if not np.isfinite(v[i]): continue
        # Exact SELL_CORE_001 strict window.
        if i>=2008:
            prev=v[i-2000:i]
            if np.isfinite(prev).sum()==2000:
                strict_inc[i]=np.mean(prev<=v[i])
                strict_mid[i]=(np.sum(prev<v[i])+0.5*np.sum(prev==v[i]))/2000.0
        # New causal expanding warm-up, min 90 prior valid funding_3d observations, cap 2000.
        lo=max(0,i-2000); prev=v[lo:i]; prev=prev[np.isfinite(prev)]
        if len(prev)>=90: exp_inc[i]=np.mean(prev<=v[i])
    z['pct_strict2000']=strict_inc; z['pct_strict2000_midrank']=strict_mid; z['pct_expanding90']=exp_inc
    return z


def attach_completed_h1(rows,h):
    cols=['close_time','atr14','rv168']
    a=h[cols].dropna(subset=['close_time']).sort_values('close_time')
    x=rows.sort_values('decision_time').copy()
    return pd.merge_asof(x,a,left_on='decision_time',right_on='close_time',direction='backward')


def build_state_rows(fc,pct_col,method):
    z=fc.dropna(subset=[pct_col]).copy().sort_values('time')
    z['pctile']=z[pct_col].astype(float); z['q4']=(z.pctile>=.75).astype(int)
    # Continuous state episodes: state change or missing 8h clock gap.
    prev_t=z.time.shift(); prev_q=z.q4.shift()
    new=prev_t.isna() | z.q4.ne(prev_q) | ((z.time-prev_t)>pd.Timedelta(hours=8,minutes=1))
    z['state_episode_id']=new.cumsum().astype(int); z['method']=method
    return z


def make_signals(state,phase):
    x=state.copy(); x['funding_time']=x.time; x['decision_time']=x.time+pd.Timedelta(hours=phase); x['phase_h']=phase
    x['state_name']=np.where(x.q4.eq(1),'Q4','Q1_Q3')
    return x


def replay(rows,h):
    if len(rows)==0:return pd.DataFrame()
    ht=h.time.to_numpy('datetime64[ns]'); O=h.open.to_numpy(float); H=h.high.to_numpy(float); C=h.close.to_numpy(float)
    hc=h.close_time.to_numpy('datetime64[ns]'); HA=h.atr14.to_numpy(float); HR=h.rv168.to_numpy(float)
    out=[]
    for r in rows.sort_values('decision_time').itertuples(index=False):
        sig=pd.Timestamp(r.decision_time)
        # Entry strictly after decision; funding is known at the decision timestamp.
        j=int(np.searchsorted(ht,np.datetime64(sig),'right'))
        # ATR/RV known from completed H1 bars at decision, not from entry-hour future information.
        q=int(np.searchsorted(hc,np.datetime64(sig),'right')-1)
        if j>=len(h) or q<0 or not np.isfinite(HA[q]) or HA[q]<=0: continue
        entry=float(O[j]); sd=STOP_ATR*float(HA[q]); sl=entry+sd
        d=r._asdict(); d.update(entry_time=pd.Timestamp(h.time.iloc[j]),entry=entry,atr_h1=float(HA[q]),rv168=float(HR[q]) if np.isfinite(HR[q]) else np.nan,stop_dist=sd)
        for hh in HOLDS:
            endt=pd.Timestamp(h.time.iloc[j])+pd.Timedelta(hours=hh)
            je=int(np.searchsorted(ht,np.datetime64(endt),'left'))
            if je<=j or je>=len(h):
                d[f'R{hh}']=np.nan; d[f'pct{hh}']=np.nan; d[f'exit{hh}']='NA'; continue
            hit=np.flatnonzero(H[j:je]>=sl)
            if hit.size:
                rr=-1.0-COST_USD/sd; pct=-(sd/entry*100.0)-COST_USD/entry*100.0; ex='SL'
            else:
                exitp=float(O[je]); rr=(entry-exitp)/sd-COST_USD/sd; pct=(entry-exitp)/entry*100.0-COST_USD/entry*100.0; ex='TIME'
            d[f'R{hh}']=rr; d[f'pct{hh}']=pct; d[f'exit{hh}']=ex
        d['prop_return_pct48']=d.get('R48',np.nan)*RISK_PER_TRADE_PCT
        out.append(d)
    return pd.DataFrame(out)


def metric(g,method,phase,state,label='PERIODIC'):
    r={'method':method,'phase_h':phase,'state':state,'view':label,'N':len(g),'episodes':g.state_episode_id.nunique() if len(g) else 0}
    if len(g):
        span=(pd.Timestamp(g.funding_time.max())-pd.Timestamp(g.funding_time.min())).total_seconds()/604800
        r['trades_per_week']=len(g)/span if span>0 else np.nan
        r['median_episode_entries']=float(g.groupby('state_episode_id').size().median())
    else:r.update(trades_per_week=np.nan,median_episode_entries=np.nan)
    for hh in HOLDS:
        z=g[f'R{hh}'].dropna() if len(g) else pd.Series(dtype=float)
        r.update({f'EV_R{hh}':float(z.mean()) if len(z) else np.nan,f'PF{hh}':pf(z),f'WR{hh}':float((z>0).mean()) if len(z) else np.nan,
                  f'EV_pct{hh}':float(g[f'pct{hh}'].mean()) if len(g) else np.nan,f'SL_rate{hh}':float((g[f'exit{hh}']=='SL').mean()) if len(g) else np.nan})
    return r


def year_metrics(g,method,phase,state):
    rows=[]
    if len(g)==0:return rows
    x=g.copy(); x['year']=pd.to_datetime(x.funding_time).dt.year
    for y,gy in x.groupby('year'):
        r={'method':method,'phase_h':phase,'state':state,'year':int(y),'N':len(gy),'episodes':gy.state_episode_id.nunique()}
        for hh in HOLDS:
            z=gy[f'R{hh}'].dropna(); r.update({f'EV_R{hh}':float(z.mean()) if len(z) else np.nan,f'PF{hh}':pf(z),f'EV_pct{hh}':float(gy[f'pct{hh}'].mean())})
        rows.append(r)
    return rows


def episode_table(g):
    if len(g)==0:return pd.DataFrame()
    rows=[]
    for eid,e in g.groupby('state_episode_id'):
        rows.append({'state_episode_id':int(eid),'state':str(e.state.iloc[0] if 'state' in e else e.state_name.iloc[0]),
                     'start':pd.Timestamp(e.funding_time.min()),'end':pd.Timestamp(e.funding_time.max()),'N':len(e),
                     'mean_R48':float(e.R48.mean()),'sum_prop_pct48':float(e.prop_return_pct48.sum()),
                     'onset_rv168':float(e.sort_values('funding_time').rv168.iloc[0]) if pd.notna(e.sort_values('funding_time').rv168.iloc[0]) else np.nan})
    return pd.DataFrame(rows)


def boot_episode_returns(ep,seed):
    z=ep.sum_prop_pct48.dropna().to_numpy(float)
    if len(z)<4:return {'episodes':len(z),'mean_episode_return_pct':float(np.mean(z)) if len(z) else np.nan,'CI_lo':np.nan,'CI_hi':np.nan,'P_gt0':np.nan}
    rng=np.random.default_rng(seed); vals=np.empty(BOOT,float)
    for i in range(BOOT): vals[i]=rng.choice(z,size=len(z),replace=True).mean()
    return {'episodes':len(z),'mean_episode_return_pct':float(np.mean(z)),'CI_lo':float(np.quantile(vals,.025)),'CI_hi':float(np.quantile(vals,.975)),'P_gt0':float((vals>0).mean())}


def phase_pair(tr0,tr4,method):
    a=tr0[tr0.state_name=='Q4'][['funding_time','state_episode_id','R48','pct48']].copy()
    b=tr4[tr4.state_name=='Q4'][['funding_time','R48','pct48']].copy()
    p=a.merge(b,on='funding_time',suffixes=('_0','_4'))
    if len(p)==0:return pd.DataFrame(),{}
    p['delta_R48']=p.R48_4-p.R48_0; p['delta_pct48']=p.pct48_4-p.pct48_0
    # cluster bootstrap paired delta by funding episode
    ag=p.groupby('state_episode_id').delta_R48.agg(['sum','count']).to_numpy(float)
    rng=np.random.default_rng(SEED+700); vals=np.empty(BOOT,float)
    for i in range(BOOT):
        s=ag[rng.integers(0,len(ag),len(ag))].sum(axis=0); vals[i]=s[0]/s[1]
    stat={'method':method,'N_pairs':len(p),'episodes':p.state_episode_id.nunique(),'EV0_R48':float(p.R48_0.mean()),'EV4_R48':float(p.R48_4.mean()),
          'delta_4_minus_0_R48':float(p.delta_R48.mean()),'CI_lo':float(np.quantile(vals,.025)),'CI_hi':float(np.quantile(vals,.975)),'P_delta_gt0':float((vals>0).mean()),
          'corr_R48':float(p.R48_0.corr(p.R48_4))}
    return p,stat


def rv_diagnostic(alltr,method):
    x=alltr.dropna(subset=['rv168','R48']).copy()
    if len(x)<20:return pd.DataFrame(),{}
    x['logrv']=np.log(x.rv168.clip(lower=1e-12))
    # diagnostic global RV quintiles; never used as a trading threshold.
    x['rv_quintile']=pd.qcut(x.logrv,5,labels=['Q1','Q2','Q3','Q4','Q5'],duplicates='drop')
    rows=[]
    for q,g in x.groupby('rv_quintile',observed=True):
        for st,sg in g.groupby('state_name'):
            rows.append({'method':method,'rv_quintile':str(q),'state':st,'N':len(sg),'EV_R48':float(sg.R48.mean()),'PF48':pf(sg.R48),'EV_pct48':float(sg.pct48.mean())})
    corr=float(x.pctile.corr(x.logrv))
    return pd.DataFrame(rows),{'method':method,'N':len(x),'corr_funding_pctile_logRV168':corr,'Q4_mean_RV168':float(x[x.q4==1].rv168.mean()),'nonQ4_mean_RV168':float(x[x.q4==0].rv168.mean())}


def ols_beta_q4_cluster(x,seed):
    z=x.dropna(subset=['R48','rv168']).copy()
    if len(z)<50:return {'beta_q4':np.nan,'CI_lo':np.nan,'CI_hi':np.nan,'P_gt0':np.nan,'N':len(z),'episodes':z.state_episode_id.nunique()}
    z['logrv']=np.log(z.rv168.clip(lower=1e-12)); z['zlogrv']=(z.logrv-z.logrv.mean())/(z.logrv.std(ddof=0) or 1.0)
    years=sorted(z.funding_time.dt.year.unique()); basey=years[0]
    def design(d):
        cols=[np.ones(len(d)),d.q4.to_numpy(float),d.zlogrv.to_numpy(float)]
        for y in years[1:]: cols.append((d.funding_time.dt.year==y).to_numpy(float))
        return np.column_stack(cols)
    def fit(d):
        X=design(d); y=d.R48.to_numpy(float); return float(np.linalg.lstsq(X,y,rcond=None)[0][1])
    obs=fit(z); groups={eid:g for eid,g in z.groupby('state_episode_id')}; ids=np.array(list(groups))
    rng=np.random.default_rng(seed); vals=[]
    for _ in range(REG_BOOT):
        samp=rng.choice(ids,size=len(ids),replace=True)
        b=pd.concat([groups[e] for e in samp],ignore_index=True)
        # retain the original standardization and year columns available in the sample.
        try: vals.append(fit(b))
        except Exception: pass
    v=np.asarray(vals,float)
    return {'beta_q4':obs,'CI_lo':float(np.quantile(v,.025)) if len(v) else np.nan,'CI_hi':float(np.quantile(v,.975)) if len(v) else np.nan,
            'P_gt0':float((v>0).mean()) if len(v) else np.nan,'N':len(z),'episodes':len(ids),'base_year':int(basey)}


def run_method(fc,h,pct_col,method):
    state=build_state_rows(fc,pct_col,method)
    state.to_csv(OUT/f'funding_state_{method}.csv',index=False)
    alltr={}; metrics=[]; years=[]; boots=[]; rvrows=[]; rvsumm=[]
    for ph in PHASES:
        sig=make_signals(state,ph); sig=attach_completed_h1(sig,h)
        tr=replay(sig,h); tr.to_csv(OUT/f'trades_{method}_phase{ph}.csv',index=False); alltr[ph]=tr
        for st,g in tr.groupby('state_name'):
            metrics.append(metric(g,method,ph,st)); years+=year_metrics(g,method,ph,st)
            ep=episode_table(g); ep.to_csv(OUT/f'episodes_{method}_phase{ph}_{st}.csv',index=False)
            b=boot_episode_returns(ep,SEED+ph*100+(1 if st=='Q4' else 2)); b.update(method=method,phase_h=ph,state=st); boots.append(b)
        if ph==0:
            rd,rs=rv_diagnostic(tr,method); rvrows.append(rd); rvsumm.append(rs)
    pair,pstat=phase_pair(alltr[0],alltr[4],method); pair.to_csv(OUT/f'phase_pairs_{method}.csv',index=False)
    reg=ols_beta_q4_cluster(alltr[0],SEED+900)
    reg.update(method=method)
    return pd.DataFrame(metrics),pd.DataFrame(years),pd.DataFrame(boots),pd.concat(rvrows,ignore_index=True) if rvrows else pd.DataFrame(),pd.DataFrame(rvsumm),pd.DataFrame([pstat]),pd.DataFrame([reg])


def main():
    h,f=load_data(); fc=funding_context(f); fc.to_csv(OUT/'funding_context_full.csv',index=False)
    methods=[('pct_strict2000','STRICT2000_INCLUSIVE'),('pct_expanding90','EXPANDING90_INCLUSIVE'),('pct_strict2000_midrank','STRICT2000_MIDRANK')]
    M=[];Y=[];B=[];RV=[];RVS=[];P=[];REG=[]
    for col,name in methods:
        m,y,b,rv,rvs,p,reg=run_method(fc,h,col,name); M.append(m);Y.append(y);B.append(b);RV.append(rv);RVS.append(rvs);P.append(p);REG.append(reg)
    M=pd.concat(M,ignore_index=True);Y=pd.concat(Y,ignore_index=True);B=pd.concat(B,ignore_index=True);RV=pd.concat(RV,ignore_index=True);RVS=pd.concat(RVS,ignore_index=True);P=pd.concat(P,ignore_index=True);REG=pd.concat(REG,ignore_index=True)
    M.to_csv(OUT/'metrics.csv',index=False);Y.to_csv(OUT/'yearly.csv',index=False);B.to_csv(OUT/'episode_bootstrap.csv',index=False);RV.to_csv(OUT/'rv_quintiles.csv',index=False);RVS.to_csv(OUT/'rv_summary.csv',index=False);P.to_csv(OUT/'phase_robustness.csv',index=False);REG.to_csv(OUT/'rv_control_regression.csv',index=False)

    # Stability table: Q4, phase 0.
    stab=[]
    for method in M.method.unique():
        q=Y[(Y.method==method)&(Y.phase_h==0)&(Y.state=='Q4')]
        stab.append({'method':method,'years':len(q),'positive_R48_years':int((q.EV_R48>0).sum()),'positive_pct48_years':int((q.EV_pct48>0).sum()),'first_year':int(q.year.min()) if len(q) else np.nan,'last_year':int(q.year.max()) if len(q) else np.nan,'min_year_N':int(q.N.min()) if len(q) else 0})
    ST=pd.DataFrame(stab); ST.to_csv(OUT/'year_stability.csv',index=False)

    primary=M[(M.method=='STRICT2000_INCLUSIVE')&(M.phase_h==0)]
    expand=M[(M.method=='EXPANDING90_INCLUSIVE')&(M.phase_h==0)]
    report=['# SELL_CORE_010 — AUTONOMOUS_FUNDING_Q4_STATE','',
            '**Primary:** strict causal previous-2000 funding_3d percentile, autonomous 8h SELL while Q4.','',
            'Important: the old `funding Q4 SELL +1.17%, 8/8` finding was conditional on a large oracle population; it was not this autonomous strategy.','',
            '## Data / frozen mechanics','',
            f'- H1 flow bars: {len(h):,}, {h.time.min()} .. {h.time.max()} UTC.',
            f'- Funding observations: {len(f):,}, {f.time.min()} .. {f.time.max()} UTC.',
            '- funding_3d = 9 x 8h trailing mean; Q4 >= 75th causal percentile.',
            '- Strict2000 is exact SELL_CORE_001 percentile convention and therefore starts only after the 2000-observation warm-up.',
            '- Expanding90 is a newly preregistered causal extension solely to inspect 2019-2020; it is not legacy parity.',
            f'- Episode max-concurrent risk budget diagnostic: {EP_RISK_PCT:.2f}%; per 8h entry {RISK_PER_TRADE_PCT:.5f}%.','',
            '## Primary strict2000 phase-0 metrics','',primary.to_markdown(index=False),'',
            '## Expanding90 phase-0 metrics (8-calendar-year sensitivity)','',expand.to_markdown(index=False),'',
            '## Yearly Q4','',Y[(Y.phase_h==0)&(Y.state=='Q4')].to_markdown(index=False),'',
            '## Year stability','',ST.to_markdown(index=False),'',
            '## Phase robustness Q4: 0h vs +4h','',P.to_markdown(index=False),'',
            '## Episode bootstrap (0.5% max-concurrent episode risk diagnostic)','',B.to_markdown(index=False),'',
            '## RV168 diagnostic summary','',RVS.to_markdown(index=False),'',
            '## RV168-controlled Q4 coefficient','',REG.to_markdown(index=False),'',
            '## RV quintile decomposition (diagnostic only)','',RV.to_markdown(index=False),'',
            '## Frozen interpretation boundary','',
            '- PASS requires autonomous Q4 SELL to be positive in both R and price space, reasonably stable by year, survive +4h phase shift, and retain a positive Q4 coefficient after RV168/year control.',
            '- Expanding90 cannot rescue a failed strict2000 primary; it only answers the requested 2019-2026 causal-extension question.',
            '- No Funding x FVG/B3/CHoCH/v283 stacking is permitted in this lab.']
    (OUT/'REPORT.md').write_text('\n'.join(report)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
