#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab124_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
MAX_H=48
SEARCH_BARS=72
COSTS=[2.81,7.5]

def norm(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())
def pick(cols,prefs):
    nc={norm(c):c for c in cols}
    for p in prefs:
        if norm(p) in nc:return nc[norm(p)]
    for p in prefs:
        pp=norm(p)
        for k,v in nc.items():
            if pp in k or k in pp:return v
    return None
def load_zip(zp):
    with zipfile.ZipFile(zp) as z:
        fs=[]
        for n in z.namelist():
            if not n.lower().endswith('.csv'): continue
            try:
                with z.open(n) as f:d=pd.read_csv(f)
                if len(d):fs.append(d)
            except: pass
        if not fs: raise RuntimeError(f'no csv in {zp}')
        common=set(fs[0].columns)
        for d in fs[1:]: common &= set(d.columns)
        if len(fs)>1 and len(common)>=4:
            cols=list(common); return pd.concat([d[cols] for d in fs],ignore_index=True)
        return fs[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# ---------------- data ----------------
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time']); rc=pick(f.columns,['count_long_short_ratio','ratio']); oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
f=f[[tc,rc,oic]].copy(); f['time']=ptime(f[tc]); f['ratio']=pd.to_numeric(f[rc],errors='coerce'); f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna().sort_values('time').drop_duplicates('time',keep='last')
f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean(); sd=f.ratio.rolling(72,min_periods=72).std(ddof=0)
f['z']=(f.ratio-mu)/sd.replace(0,np.nan)
f['dz60']=f.z-f.z.shift(12)
f['oi4h']=f.oi/f.oi.shift(48)-1

r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']);po=pick(r.columns,['open']);ph=pick(r.columns,['high']);pl=pick(r.columns,['low']);pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy(); p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean()
h1['ema20']=h1.close.ewm(span=20,adjust=False).mean()
h1['extension']=(h1.close-h1.ema20)/h1.atr
h1['close_time']=h1.time+pd.Timedelta(hours=1)

h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean();h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
h4prev=h4.close.shift(1)
h4tr=pd.concat([(h4.high-h4.low),(h4.high-h4prev).abs(),(h4.low-h4prev).abs()],axis=1).max(axis=1)
h4['atr14']=h4tr.rolling(14,min_periods=14).mean()
h4['body_atr']=(h4.close-h4.open)/h4.atr14
age=[];cur=0;pv=0
for v in h4.trend:
    if v!=0 and v==pv:cur+=1
    elif v!=0:cur=1
    else:cur=0
    age.append(cur);pv=v
h4['trend_age']=age
imp=((h4.body_atr.abs()>=0.8)&(np.sign(h4.body_atr)==h4.trend))
ia=[];cnt=999
for x in imp.fillna(False):
    cnt=0 if x else min(cnt+1,999); ia.append(cnt)
h4['impulse_age']=ia
h4['close_time']=h4.time+pd.Timedelta(hours=4)

b=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','extension']].dropna().sort_values('close_time'),
                left_on='time',right_on='close_time',direction='backward')
b=pd.merge_asof(b.sort_values('time'),h4[['close_time','trend','trend_age','impulse_age']].dropna().sort_values('close_time'),
                left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
b=pd.merge_asof(b.sort_values('time'),f[['time','z','dz60','oi4h']].dropna().sort_values('time'),
                on='time',direction='backward',tolerance=pd.Timedelta('5min'))
b=b.dropna(subset=['atr','extension','trend','trend_age','impulse_age','z','dz60','oi4h']).reset_index(drop=True)

trm=b.time<TRAIN_END
EXT80=float(b.loc[trm,'extension'].abs().quantile(.80))
EXT90=float(b.loc[trm,'extension'].abs().quantile(.90))
OI70=float(b.loc[trm,'oi4h'].quantile(.70))
OI85=float(b.loc[trm,'oi4h'].quantile(.85))

BT=b.time.reset_index(drop=True);BO=b.open.to_numpy(float);BH=b.high.to_numpy(float);BL=b.low.to_numpy(float);BC=b.close.to_numpy(float);BA=b.atr.to_numpy(float);BZ=b.z.to_numpy(float)

def phase(age,imp_age):
    if age<=3:return 'BIRTH'
    if imp_age<=2:return 'REACCEL'
    if age<=12:return 'CONT'
    if age<=24:return 'MATURE'
    return 'LATE'

def swing3_entry(i,side):
    for j in range(i+1,min(i+SEARCH_BARS,len(b)-2)+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:
                br=(BC[j]-ref)/BA[i]
                return j+1,j,br
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:
                br=(ref-BC[j])/BA[i]
                return j+1,j,br
    return None,None,np.nan

# Broader anti-crowd capitulation universe: same frozen CAP thresholds, all H4 phases.
cands=[]
last=len(b)-1-MAX_H*12-1
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1
    trend=int(b.trend.iloc[i]);age=int(b.trend_age.iloc[i]);imp_age=int(b.impulse_age.iloc[i]);ext=float(b.extension.iloc[i]);oi=float(b.oi4h.iloc[i]);atr=float(BA[i])
    if trend==0 or trend==side:continue
    ext_against=(side>0 and ext<0) or (side<0 and ext>0)
    if not ext_against or abs(ext)<EXT80 or oi<OI70:continue
    ei,ti,break_strength=swing3_entry(i,side)
    if ei is None:continue
    entry=float(BO[ei]);anchor=float(BC[i])
    phs=phase(age,imp_age)
    delay=(BT.iloc[ei]-BT.iloc[i]).total_seconds()/60
    entry_improvement=side*(entry-anchor)/atr
    # quality score: hand-crafted, no return fitting and no OOS tuning.
    score=0.0
    score += {'CONT':30,'REACCEL':24,'BIRTH':12,'MATURE':8,'LATE':10}[phs]
    # stronger anti-crowd imbalance earns points progressively
    az=abs(float(BZ[i]))
    score += 8 if az>=1.5 else 0
    score += 8 if az>=2.0 else 0
    score += 6 if az>=2.5 else 0
    # severity but capped: prior labs did not support blindly maximizing extension/OI
    score += 7 if abs(ext)>=EXT90 else 3
    score += 7 if oi>=OI85 else 3
    # trigger quality: decisive break, reasonable delay, and not chasing far in reversal direction
    score += min(max(break_strength,0),0.30)/0.30*10
    score += 8 if delay<=60 else (4 if delay<=120 else 0)
    score += 8 if entry_improvement<=0.10 else (4 if entry_improvement<=0.30 else 0)
    # crowd trajectory still pushing old crowd direction at signal -> better capitulation setup
    crowd_side=1 if BZ[i]>0 else -1
    dz_crowd=np.sign(float(b.dz60.iloc[i]))==crowd_side
    score += 5 if dz_crowd else 0
    score=min(score,100)
    cands.append(dict(signal_i=i,entry_i=ei,trigger_i=ti,signal_time=BT.iloc[i],entry_time=BT.iloc[ei],
                      split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',side=side,phase=phs,z=float(BZ[i]),
                      abs_z=az,ext_abs=abs(ext),oi4h=oi,break_strength=break_strength,delay_min=delay,
                      entry_improvement=entry_improvement,dz_crowd=dz_crowd,atr=atr,score=score))
df=pd.DataFrame(cands).sort_values('entry_time').reset_index(drop=True)

# TRAIN-only score cutoffs for A/B/C. Target is portfolio frequency expansion, not return maximization.
train_scores=df[df.split=='TRAIN'].score
qA=float(train_scores.quantile(.80))
qB=float(train_scores.quantile(.55))
qC=float(train_scores.quantile(.30))
df['tier']=np.where(df.score>=qA,'A',np.where(df.score>=qB,'B',np.where(df.score>=qC,'C','D')))
df.to_csv(OUT/'LAB124_scored_candidates.csv',index=False)

def sim_one(ei,side,atr,cost):
    entry=float(BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(b)-1)
    gross=side*(BC[end]-entry)/atr;reason='TIME';xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason='BOTH_STOP_FIRST';xi=j;break
        if hs:gross=-1;reason='SL';xi=j;break
        if ht:gross=3;reason='TP';xi=j;break
    return gross-(cost/10000.0)*entry/atr,reason,xi

# Portfolios: core+reaccel benchmark plus score tiers.
# Risk weighting: A=.50%, B=.33%, C=.20%; D excluded.
PORTS={
'BENCH_CORE_REACCEL': {'mode':'phase','phases':['CONT','REACCEL']},
'SCORE_A': {'mode':'tier','tiers':['A']},
'SCORE_AB': {'mode':'tier','tiers':['A','B']},
'SCORE_ABC': {'mode':'tier','tiers':['A','B','C']},
}
RISK={'A':0.50,'B':0.33,'C':0.20,'D':0.0}

alltr=[];summary=[]
for cost in COSTS:
    for pname,rule in PORTS.items():
        if rule['mode']=='phase':
            s=df[df.phase.isin(rule['phases'])].copy()
        else:
            s=df[df.tier.isin(rule['tiers'])].copy()
        s=s.sort_values('entry_time')
        open_until=pd.Timestamp.min.tz_localize('UTC');cumR=0.;cumPct=0.;eqR=[];eqPct=[];trs=[]
        for _,r in s.iterrows():
            if r.entry_time<open_until:continue
            net,reason,xi=sim_one(int(r.entry_i),int(r.side),float(r.atr),cost)
            risk=0.25 if pname=='BENCH_CORE_REACCEL' else RISK[r.tier]
            startR=cumR;startP=cumPct
            entry=float(BO[int(r.entry_i)])
            for j in range(int(r.entry_i),xi+1):
                mtm=int(r.side)*(BC[j]-entry)/r.atr-(cost/10000.0)*entry/r.atr
                if j==xi:mtm=net
                eqR.append((BT.iloc[j],startR+mtm))
                eqPct.append((BT.iloc[j],startP+mtm*risk))
            cumR+=net;cumPct+=net*risk;open_until=BT.iloc[xi]
            trs.append(dict(portfolio=pname,cost_bps=cost,phase=r.phase,tier=r.tier,score=r.score,split=r['split'],
                            signal_time=r.signal_time,entry_time=r.entry_time,exit_time=BT.iloc[xi],
                            side='BUY' if r.side>0 else 'SELL',net_r=net,risk_pct=risk,pnl_pct=net*risk,reason=reason))
        t=pd.DataFrame(trs)
        if t.empty:continue
        alltr.append(t)
        eq=pd.DataFrame(eqR,columns=['time','equity']).sort_values('time').drop_duplicates('time',keep='last')
        ep=pd.DataFrame(eqPct,columns=['time','equity']).sort_values('time').drop_duplicates('time',keep='last')
        maxdd=float((eq.equity.cummax()-eq.equity).max())
        maxddpct=float((ep.equity.cummax()-ep.equity).max())
        ep['day']=ep.time.dt.floor('D');prev=0.;daily=[]
        for d,g in ep.groupby('day'):
            daily.append(float(prev-g.equity.min()));prev=float(g.equity.iloc[-1])
        months=max((t.exit_time.max().year-t.entry_time.min().year)*12+t.exit_time.max().month-t.entry_time.min().month+1,1)
        for split in ['ALL','TRAIN','OOS']:
            q=t if split=='ALL' else t[t.split==split]
            if q.empty:continue
            pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
            summary.append(dict(portfolio=pname,cost_bps=cost,split=split,n=len(q),ev=float(q.net_r.mean()),
                                pf=float(pos/neg) if neg>0 else np.inf,wr=float((q.net_r>0).mean()),total_r=float(q.net_r.sum()),
                                total_pct=float(q.pnl_pct.sum()),trades_month=(len(t)/months if split=='ALL' else np.nan),
                                r_month=(t.net_r.sum()/months if split=='ALL' else np.nan),
                                pct_month=(t.pnl_pct.sum()/months if split=='ALL' else np.nan),
                                max_mtm_dd_r=(maxdd if split=='ALL' else np.nan),
                                max_mtm_dd_pct=(maxddpct if split=='ALL' else np.nan),
                                max_daily_dd_pct=(max(daily) if split=='ALL' else np.nan)))
pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB124_portfolio_trades.csv',index=False)
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB124_portfolio_summary.csv',index=False)

# Tier attribution
attr=[]
for cost in COSTS:
  for tier in ['A','B','C','D']:
    s=df[df.tier==tier].sort_values('entry_time')
    open_until=pd.Timestamp.min.tz_localize('UTC');rows=[]
    for _,r in s.iterrows():
        if r.entry_time<open_until:continue
        net,reason,xi=sim_one(int(r.entry_i),int(r.side),float(r.atr),cost);open_until=BT.iloc[xi]
        rows.append(dict(split=r['split'],net_r=net))
    t=pd.DataFrame(rows)
    if t.empty:continue
    for split in ['ALL','TRAIN','OOS']:
        q=t if split=='ALL' else t[t.split==split]
        if q.empty:continue
        pos=q.loc[q.net_r>0,'net_r'].sum();neg=-q.loc[q.net_r<0,'net_r'].sum()
        attr.append(dict(tier=tier,cost_bps=cost,split=split,n=len(q),ev=float(q.net_r.mean()),pf=float(pos/neg) if neg>0 else np.inf))
pd.DataFrame(attr).to_csv(OUT/'LAB124_tier_attribution.csv',index=False)

lines=['# LAB124 — ANTI-CROWD QUALITY SCORE','',
       f'Universe: frozen capitulation context, all H4 phases. ext>={EXT80:.2f} H1 ATR, OI4h>={OI70:+.3%}, then SWING3_BREAK.',
       'Score is hand-crafted from information known by entry: trend phase, |Z| stage, extension severity, OI severity, swing-break strength, trigger delay, entry chase, and whether crowd Z was still accelerating into the old direction.',
       'No return fitting and no OOS threshold tuning. TRAIN-only score quantiles define A/B/C/D.',
       f'Tiers: A >= {qA:.1f}; B >= {qB:.1f}; C >= {qC:.1f}; D below.',
       'Risk schedule for scored portfolio: A=0.50%, B=0.33%, C=0.20%, D=0. Benchmark CORE+REACCEL stays at 0.25%.',
       'Execution frozen: next M5 open after SWING3, SL=1 H1 ATR, TP=3R, max hold 48h, one position.',
       'Goal: reach ~3–4 trades/month without destroying PF/DD. Development OOS remains repeatedly inspected.','']

for cost in COSTS:
    lines.append(f'## Cost {cost} bps')
    for pname in PORTS:
        a=sm[(sm.portfolio==pname)&(sm.cost_bps==cost)&(sm.split=='ALL')]
        o=sm[(sm.portfolio==pname)&(sm.cost_bps==cost)&(sm.split=='OOS')]
        if len(a):
            aa=a.iloc[0];extra=''
            if len(o):
                oo=o.iloc[0];extra=f" | OOS N={int(oo.n)} EV={oo.ev:+.3f} PF={oo.pf:.2f}"
            lines.append(f"- {pname}: N={int(aa.n)} ({aa.trades_month:.2f}/mo) EV={aa.ev:+.3f} PF={aa.pf:.2f} R/mo={aa.r_month:+.2f} pct/mo={aa.pct_month:+.2f}% DD={aa.max_mtm_dd_pct:.2f}% daily={aa.max_daily_dd_pct:.2f}%{extra}")
    lines.append('')

lines.append('## Tier attribution @2.81bps')
ad=pd.DataFrame(attr)
for tier in ['A','B','C','D']:
    a=ad[(ad.tier==tier)&(ad.cost_bps==2.81)&(ad.split=='ALL')]
    o=ad[(ad.tier==tier)&(ad.cost_bps==2.81)&(ad.split=='OOS')]
    if len(a):
        aa=a.iloc[0];extra=''
        if len(o):
            oo=o.iloc[0];extra=f" | OOS N={int(oo.n)} EV={oo.ev:+.3f} PF={oo.pf:.2f}"
        lines.append(f"- {tier}: N={int(aa.n)} EV={aa.ev:+.3f} PF={aa.pf:.2f}{extra}")

(OUT/'LAB124_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB124_meta.json').write_text(json.dumps(dict(
    thresholds=dict(ext80=EXT80,ext90=EXT90,oi70=OI70,oi85=OI85,scoreA=qA,scoreB=qB,scoreC=qC),
    score='hand-crafted causal quality score; no return fitting',
    risk_pct=RISK,
    execution='SWING3_BREAK, next M5 open, SL1 H1 ATR, TP3R, 48h, one position',
    caveat='development OOS repeatedly inspected; not pristine validation'
),indent=2))
print('\n'.join(lines))
