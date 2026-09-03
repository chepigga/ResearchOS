#!/usr/bin/env python3
"""BTC_PAXG_CROSS_ASSET_DIVERGENCE_AND_RESPONSE_LAB_001.

Causal event study: does PAXG add incremental information to BTC post-impulse
continuation/reversal? This is a context/router study, not a production strategy.
All features are known at a completed 15m bar; outcomes start at the next bar open.
"""
from __future__ import annotations
import hashlib, io, json, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED=20260903
OUT=Path(__file__).resolve().parent/'output'; CACHE=Path(__file__).resolve().parent/'cache'
OUT.mkdir(parents=True,exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)
START_MONTH='2021-01'; END_MONTH='2026-08'; INTERVAL='15m'
ROLL=30*24*4; IMPULSE_Q=.975; COOLDOWN=16; PAXG_STRONG_Z=.50
PRIMARY='4h'; HORIZONS={'15m':1,'1h':4,'4h':16,'24h':96}
BASE='https://data.binance.vision/data/spot/monthly/klines'
COLS=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_base','taker_quote','ignore']
BTC_ONLY=['impulse_dir','btc_z60','btc_z15','btc_vol_z','btc_range_z','btc_corr7d_lag','hour_sin','hour_cos']
PAXG_ADD=['paxg_z15','paxg_z60','paxg_pre60_z','paxg_accel_z','paxg_vol_z','paxg_range_z','paxg_corr7d','paxg_corr30d','paxg_signed_vs_impulse','paxg_pre_signed_vs_impulse']

def months(a,b): return [str(x) for x in pd.period_range(a,b,freq='M')]
def url(s,m): return f'{BASE}/{s}/{INTERVAL}/{s}-{INTERVAL}-{m}.zip'

def get_one(s,m):
    p=CACHE/f'{s}-{INTERVAL}-{m}.zip'
    if p.exists() and p.stat().st_size>100:return p
    for k in range(4):
        try:
            r=requests.get(url(s,m),timeout=45)
            if r.status_code==404:return None
            r.raise_for_status()
            if len(r.content)<100:return None
            p.write_bytes(r.content);return p
        except Exception as e:
            if k==3:
                print('WARN',s,m,e,file=sys.stderr);return None
            time.sleep(1.5*(k+1))

def downloads():
    syms=('BTCUSDT','PAXGUSDT'); out={s:[] for s in syms}
    jobs=[(s,m) for s in syms for m in months(START_MONTH,END_MONTH)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        fs={ex.submit(get_one,s,m):(s,m) for s,m in jobs}
        for f in as_completed(fs):
            s,m=fs[f]; p=f.result()
            if p:out[s].append(p)
    for s in out:
        out[s]=sorted(out[s]);print(s,len(out[s]),'monthly files')
    return out

def epoch(v):
    x=pd.to_numeric(v,errors='coerce'); med=x.dropna().median()
    unit='us' if np.isfinite(med) and med>1e14 else 'ms'
    return pd.to_datetime(x,unit=unit,utc=True,errors='coerce')

def read_month(p):
    with zipfile.ZipFile(p) as z:
        ns=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if not ns:return pd.DataFrame()
        raw=z.read(ns[0])
    d=pd.read_csv(io.BytesIO(raw),header=None,names=COLS)
    d['time']=epoch(d.open_time)
    for c in ['open','high','low','close','volume','quote_volume','trades']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    return d[['time','open','high','low','close','volume','quote_volume','trades']].dropna()

def load(paths):
    fs=[read_month(p) for p in paths]; fs=[x for x in fs if len(x)]
    if not fs:raise RuntimeError('No data')
    return pd.concat(fs,ignore_index=True).sort_values('time').drop_duplicates('time').set_index('time')

def rz(s,w=ROLL):
    mu=s.rolling(w,min_periods=max(100,w//4)).mean().shift(1)
    sd=s.rolling(w,min_periods=max(100,w//4)).std(ddof=0).shift(1)
    return (s-mu)/sd.replace(0,np.nan)

def panel(b,p):
    x=b.add_prefix('btc_').join(p.add_prefix('paxg_'),how='inner')
    x['btc_lr15']=np.log(x.btc_close).diff(); x['paxg_lr15']=np.log(x.paxg_close).diff()
    x['btc_lr60']=np.log(x.btc_close/x.btc_close.shift(4)); x['paxg_lr60']=np.log(x.paxg_close/x.paxg_close.shift(4))
    x['paxg_pre60']=x.paxg_lr60.shift(4)
    for a in ['btc','paxg']:
        x[f'{a}_z15']=rz(x[f'{a}_lr15']); x[f'{a}_z60']=rz(x[f'{a}_lr60'])
        x[f'{a}_vol_z']=rz(np.log1p(x[f'{a}_quote_volume']))
        rr=(x[f'{a}_high']-x[f'{a}_low'])/x[f'{a}_close']; x[f'{a}_range_z']=rz(rr)
    x['paxg_pre60_z']=rz(x.paxg_pre60); x['paxg_accel_z']=x.paxg_z60-x.paxg_pre60_z
    x['paxg_corr7d']=x.btc_lr15.rolling(7*96,min_periods=3*96).corr(x.paxg_lr15).shift(1)
    x['paxg_corr30d']=x.btc_lr15.rolling(30*96,min_periods=10*96).corr(x.paxg_lr15).shift(1)
    x['btc_corr7d_lag']=x.btc_lr15.rolling(7*96,min_periods=3*96).corr(x.btc_lr15.shift(1)).shift(1)
    h=x.index.hour+x.index.minute/60.;x['hour_sin']=np.sin(2*np.pi*h/24);x['hour_cos']=np.cos(2*np.pi*h/24)
    x['impulse_thr']=x.btc_lr60.abs().rolling(ROLL,min_periods=ROLL//2).quantile(IMPULSE_Q).shift(1)
    x['impulse_raw']=x.btc_lr60.abs()>=x.impulse_thr; x['impulse_dir']=np.sign(x.btc_lr60).astype(float)
    return x

def events(x):
    cand=np.flatnonzero(x.impulse_raw.fillna(False).to_numpy()); chosen=[];last=-10**9
    for i in cand:
        if i-last>=COOLDOWN:chosen.append(i);last=i
    e=x.iloc[chosen].copy();e['bar_i']=chosen;e['decision_time']=e.index
    e['entry_time']=x.index.to_series().shift(-1).iloc[chosen].to_numpy();e['entry']=x.btc_open.shift(-1).iloc[chosen].to_numpy()
    e['paxg_signed_vs_impulse']=e.impulse_dir*e.paxg_z60;e['paxg_pre_signed_vs_impulse']=e.impulse_dir*e.paxg_pre60_z
    st=np.full(len(e),'NEUTRAL',object);strong=e.paxg_z60.abs().to_numpy()>=PAXG_STRONG_Z
    same=(np.sign(e.paxg_z60)==e.impulse_dir).to_numpy()&strong;inv=(np.sign(e.paxg_z60)==-e.impulse_dir).to_numpy()&strong
    st[same]='ALIGNED';st[inv]='INVERSE';e['paxg_state']=st
    st=np.full(len(e),'NEUTRAL',object);strong=e.paxg_pre60_z.abs().to_numpy()>=PAXG_STRONG_Z
    same=(np.sign(e.paxg_pre60_z)==e.impulse_dir).to_numpy()&strong;inv=(np.sign(e.paxg_pre60_z)==-e.impulse_dir).to_numpy()&strong
    st[same]='ALIGNED_LEAD';st[inv]='INVERSE_LEAD';e['paxg_pre_state']=st
    for n,b in HORIZONS.items():
        fut=x.btc_close.shift(-b).iloc[chosen].to_numpy();raw=fut/e.entry.to_numpy()-1
        e[f'btc_fwd_{n}']=raw;e[f'cont_{n}']=raw*e.impulse_dir.to_numpy();e[f'rev_{n}']=-e[f'cont_{n}'];e[f'cont_win_{n}']=(e[f'cont_{n}']>0).astype(int)
    y=e.index.year;e['split']=np.where(y<=2024,'DEV_2021_2024',np.where(y==2025,'BRIDGE_2025','OOS_2026'))
    return e.replace([np.inf,-np.inf],np.nan).dropna(subset=['entry',f'cont_{PRIMARY}','btc_z60','paxg_z60'])

def ci(v,n=1200):
    a=v.dropna().to_numpy(float)
    if len(a)<2:return np.nan,np.nan,np.nan
    rr=np.random.default_rng(SEED+len(a)*17); means=a[rr.integers(0,len(a),size=(n,len(a)))].mean(1)
    lo,hi=np.quantile(means,[.025,.975]);return float(a.mean()),float(lo),float(hi)

def bins(e,col,h):
    rows=[]
    for sp in ['DEV_2021_2024','BRIDGE_2025','OOS_2026']:
        d=e[e.split==sp]
        groups=list(d.groupby(col))+[('ALL',d)]
        for state,g in groups:
            m,lo,hi=ci(g[f'cont_{h}'])
            rows.append(dict(split=sp,state_feature=col,state=state,horizon=h,n=len(g),cont_win_rate=g[f'cont_win_{h}'].mean(),cont_mean=m,cont_ci_lo=lo,cont_ci_hi=hi,cont_median=g[f'cont_{h}'].median(),rev_mean=-m if np.isfinite(m) else np.nan))
    return pd.DataFrame(rows)

def fit(d,feats,h):
    m=Pipeline([('imp',SimpleImputer(strategy='median')),('sc',StandardScaler()),('lr',LogisticRegression(C=.5,max_iter=3000,random_state=SEED))])
    m.fit(d[feats],d[f'cont_win_{h}'].astype(int));return m

def models(e,h):
    dev=e[e.split=='DEV_2021_2024'];mb=fit(dev,BTC_ONLY,h);ma=fit(dev,BTC_ONLY+PAXG_ADD,h)
    pdv=ma.predict_proba(dev[BTC_ONLY+PAXG_ADD])[:,1];q80=float(np.quantile(pdv,.8));q20=float(np.quantile(pdv,.2))
    rows=[];score=[]
    for sp in ['DEV_2021_2024','BRIDGE_2025','OOS_2026']:
        d=e[e.split==sp].copy();y=d[f'cont_win_{h}'].astype(int).to_numpy()
        pb=mb.predict_proba(d[BTC_ONLY])[:,1];pa=ma.predict_proba(d[BTC_ONLY+PAXG_ADD])[:,1]
        for typ,p in [('BTC_ONLY',pb),('BTC_PLUS_PAXG',pa)]:
            rows.append(dict(split=sp,horizon=h,model=typ,n=len(d),auc=roc_auc_score(y,p),brier=brier_score_loss(y,p),logloss=log_loss(y,p,labels=[0,1])))
        d['p_base']=pb;d['p_aug']=pa;d['aug_top20']=pa>=q80;d['aug_bottom20']=pa<=q20;score.append(d)
    return pd.DataFrame(rows),pd.concat(score)

def verdict(e,mm,s):
    def g(sp,mo,c):return float(mm[(mm.split==sp)&(mm.model==mo)].iloc[0][c])
    a25=g('BRIDGE_2025','BTC_PLUS_PAXG','auc')-g('BRIDGE_2025','BTC_ONLY','auc')
    a26=g('OOS_2026','BTC_PLUS_PAXG','auc')-g('OOS_2026','BTC_ONLY','auc')
    bd=g('OOS_2026','BTC_ONLY','brier')-g('OOS_2026','BTC_PLUS_PAXG','brier')
    o=s[s.split=='OOS_2026'];top=o[o.aug_top20];base=o[f'cont_win_{PRIMARY}'].mean();tw=top[f'cont_win_{PRIMARY}'].mean();tm,tl,th=ci(top[f'cont_{PRIMARY}'])
    def bm(sp,state):
        q=e[(e.split==sp)&(e.paxg_state==state)];return len(q),q[f'cont_{PRIMARY}'].mean()
    n25,i25=bm('BRIDGE_2025','INVERSE');n26,i26=bm('OOS_2026','INVERSE');all25=e[e.split=='BRIDGE_2025'][f'cont_{PRIMARY}'].mean();all26=e[e.split=='OOS_2026'][f'cont_{PRIMARY}'].mean()
    mech=np.isfinite(i25) and np.isfinite(i26) and (i25-all25)*(i26-all26)>0
    gates={'oos_events_ge_100':len(o)>=100,'paxg_auc_delta_2026_ge_0.02':a26>=.02,'paxg_auc_delta_bridge_positive':a25>0,'oos_brier_improves':bd>0,'oos_top20_lift_ge_0.05':(tw-base)>=.05 and len(top)>=20,'oos_top20_mean_positive':tm>0,'mechanism_transfer_same_sign':bool(mech)}
    n=sum(gates.values());v='PASS_INCREMENTAL_CONTEXT' if n==len(gates) else ('WATCH_WEAK_INCREMENTAL_CONTEXT' if n>=4 and gates['oos_events_ge_100'] else 'FAIL_NO_ROBUST_INCREMENTAL_CONTEXT')
    return dict(verdict=v,gates_passed=n,gates_total=len(gates),gates=gates,auc_delta_2025=a25,auc_delta_2026=a26,brier_improvement_2026=bd,oos_base_cont_win_rate=base,oos_top20_cont_win_rate=tw,oos_top20_lift=tw-base,oos_top20_n=len(top),oos_top20_mean_cont_return=tm,oos_top20_mean_ci=[tl,th],inverse_bridge_n=n25,inverse_oos_n=n26,inverse_bridge_mean=i25,inverse_oos_mean=i26)

def pct(x):return '—' if not np.isfinite(x) else f'{100*x:+.3f}%'
def report(x,e,b,mm,v):
    L=['# BTC_PAXG_CROSS_ASSET_DIVERGENCE_AND_RESPONSE_LAB_001','',f'**Frozen:** 2026-09-03  ',f'**Verdict:** **{v["verdict"]}**  ','**Role:** causal cross-asset context study; not a production entry strategy.','', '## 1. Data / causality','',f'- Binance Spot `BTCUSDT` + `PAXGUSDT`, {INTERVAL} completed klines.',f'- Synchronized coverage: `{x.index.min()}` → `{x.index.max()}`.',f'- Synchronized bars: **{len(x):,}**.',f'- Impulse: completed BTC 60m |return| >= prior 30d {IMPULSE_Q*100:.1f}th percentile.',f'- Cooldown: **{COOLDOWN*15/60:.0f}h**.','- Entry reference/outcomes begin at the next 15m open; PAXG is never forward-filled.','- Development 2021–2024; bridge 2025; untouched OOS 2026.','','## 2. Event census','']
    for k,n in e.groupby('split').size().items():L.append(f'- {k}: **{n:,}** events')
    L+=['','## 3. Primary 4h conditional response','']
    q=b[(b.horizon==PRIMARY)&(b.state_feature=='paxg_state')]
    for sp in ['DEV_2021_2024','BRIDGE_2025','OOS_2026']:
        L += [f'### {sp}','','| PAXG state | N | continuation WR | mean signed 4h | 95% CI |','|---|---:|---:|---:|---:|']
        z=q[q.split==sp]
        for state in ['ALL','INVERSE','NEUTRAL','ALIGNED']:
            r=z[z.state==state]
            if len(r):
                r=r.iloc[0];L.append(f'| {state} | {int(r.n)} | {100*r.cont_win_rate:.1f}% | {pct(r.cont_mean)} | [{pct(r.cont_ci_lo)}, {pct(r.cont_ci_hi)}] |')
        L.append('')
    L += ['## 4. Incremental model — BTC-only vs BTC+PAXG','','| Split | Model | N | AUC | Brier | LogLoss |','|---|---|---:|---:|---:|---:|']
    for _,r in mm[mm.horizon==PRIMARY].iterrows():L.append(f'| {r["split"]} | {r["model"]} | {int(r["n"])} | {r["auc"]:.4f} | {r["brier"]:.4f} | {r["logloss"]:.4f} |')
    L += ['',f'- 2025 AUC delta from PAXG: **{v["auc_delta_2025"]:+.4f}**.',f'- 2026 AUC delta from PAXG: **{v["auc_delta_2026"]:+.4f}**.',f'- 2026 Brier improvement: **{v["brier_improvement_2026"]:+.5f}**.',f'- 2026 baseline continuation WR: **{100*v["oos_base_cont_win_rate"]:.1f}%**.',f'- Frozen augmented top-20%: N **{v["oos_top20_n"]}**, WR **{100*v["oos_top20_cont_win_rate"]:.1f}%**, lift **{100*v["oos_top20_lift"]:+.1f} pp**, mean signed 4h **{pct(v["oos_top20_mean_cont_return"])}**.','','## 5. Promotion gates','']
    for k,z in v['gates'].items():L.append(f'- {"PASS" if z else "FAIL"} — `{k}`')
    L += ['',f'**Score: {v["gates_passed"]}/{v["gates_total"]} → {v["verdict"]}**','','## 6. Interpretation','','PAXG can only be promoted as a **router/context feature**, never as a standalone BTC signal. A positive result means BTC impulse outcomes become more separable when PAXG state is known; it does not authorize a trade, stop, or target.','','If WATCH/FAIL, do not rescue the result by tuning EMA periods, PAXG thresholds, impulse percentile, or horizon on 2026. A new mechanism requires a separately preregistered LAB.']
    (OUT/'REPORT.md').write_text('\n'.join(L),encoding='utf-8')

def main():
    f=downloads()
    if min(map(len,f.values()))<60:raise RuntimeError({k:len(v) for k,v in f.items()})
    x=panel(load(f['BTCUSDT']),load(f['PAXGUSDT']));e=events(x)
    b=pd.concat([bins(e,c,h) for c in ['paxg_state','paxg_pre_state'] for h in HORIZONS],ignore_index=True)
    ms=[];score=None
    for h in ['1h','4h','24h']:
        m,s=models(e,h);ms.append(m)
        if h==PRIMARY:score=s
    mm=pd.concat(ms,ignore_index=True);v=verdict(e,mm,score)
    keep=['decision_time','entry_time','split','impulse_dir','btc_lr60','btc_z60','paxg_z15','paxg_z60','paxg_pre60_z','paxg_accel_z','paxg_state','paxg_pre_state','paxg_corr7d','paxg_corr30d','btc_fwd_15m','btc_fwd_1h','btc_fwd_4h','btc_fwd_24h','cont_15m','cont_1h','cont_4h','cont_24h']
    e.reset_index(drop=True)[keep].to_csv(OUT/'events.csv',index=False);b.to_csv(OUT/'conditional_bins.csv',index=False);mm.to_csv(OUT/'model_metrics.csv',index=False)
    (OUT/'verdict.json').write_text(json.dumps(v,indent=2,allow_nan=True),encoding='utf-8');report(x,e,b,mm,v)
    man={'lab':'BTC_PAXG_CROSS_ASSET_DIVERGENCE_AND_RESPONSE_LAB_001','seed':SEED,'freeze':'2026-09-03','params':{'start_month':START_MONTH,'end_month':END_MONTH,'interval':INTERVAL,'impulse_quantile':IMPULSE_Q,'roll_bars':ROLL,'cooldown_bars':COOLDOWN,'paxg_strong_z':PAXG_STRONG_Z,'primary_horizon':PRIMARY},'counts':{'synchronized_bars':len(x),'events':len(e)},'output_sha256':{}}
    for p in sorted(OUT.iterdir()):
        if p.is_file():man['output_sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps(man,indent=2),encoding='utf-8');print((OUT/'REPORT.md').read_text())
if __name__=='__main__':main()
