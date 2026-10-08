#!/usr/bin/env python3
from __future__ import annotations
import re,zipfile,json
from pathlib import Path
import numpy as np,pandas as pd

OUT=Path("lab120_out"); OUT.mkdir(exist_ok=True)
FLOW_ZIP=Path("BTCUSDT_flow_2021-01-2026-08.csv.zip")
PRICE_ZIP=Path("btc_5m.zip")
SEC_ZIP=Path("BTCUSDT_sec.csv.zip")
TRAIN_END=pd.Timestamp("2025-01-01",tz="UTC")
H=48
SEARCH_BARS=72 # 6h on M5
COST_BPS=[0.0,2.81,7.5]

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
            if not n.lower().endswith('.csv'):continue
            try:
                with z.open(n) as f:d=pd.read_csv(f)
                if len(d):fs.append(d)
            except:pass
        if not fs:raise RuntimeError(f'no csv in {zp}')
        common=set(fs[0].columns)
        for d in fs[1:]:common &= set(d.columns)
        if len(fs)>1 and len(common)>=4:
            cols=list(common);return pd.concat([d[cols] for d in fs],ignore_index=True)
        return fs[0]
def ptime(s):
    if pd.api.types.is_numeric_dtype(s):
        x=pd.to_numeric(s,errors='coerce');med=float(x.dropna().median()) if x.notna().any() else 0
        return pd.to_datetime(x,unit=('ms' if med>1e11 else 's'),utc=True,errors='coerce')
    return pd.to_datetime(s,utc=True,errors='coerce')

# ---------- flow ----------
f=load_zip(FLOW_ZIP)
tc=pick(f.columns,['create_time','time','timestamp']);rc=pick(f.columns,['count_long_short_ratio','ratio']);oic=pick(f.columns,['sum_open_interest_value','sum_open_interest'])
f=f[[tc,rc,oic]].copy();f['time']=ptime(f[tc]);f['ratio']=pd.to_numeric(f[rc],errors='coerce');f['oi']=pd.to_numeric(f[oic],errors='coerce')
f=f.dropna(subset=['time','ratio','oi']).sort_values('time').drop_duplicates('time',keep='last')
f=f[(f.ratio>0)&(f.oi>0)].set_index('time').resample('5min').last().dropna().reset_index()
mu=f.ratio.rolling(72,min_periods=72).mean();sd=f.ratio.rolling(72,min_periods=72).std(ddof=0);f['z']=(f.ratio-mu)/sd.replace(0,np.nan)
f['oi_chg_4h']=f.oi/f.oi.shift(48)-1

# ---------- price ----------
r=load_zip(PRICE_ZIP)
pt=pick(r.columns,['time','timestamp','open_time']);po=pick(r.columns,['open']);ph=pick(r.columns,['high']);pl=pick(r.columns,['low']);pc=pick(r.columns,['close'])
p=r[[pt,po,ph,pl,pc]].copy();p['time']=ptime(p[pt])
for c,n in [(po,'open'),(ph,'high'),(pl,'low'),(pc,'close')]:p[n]=pd.to_numeric(p[c],errors='coerce')
p=p[['time','open','high','low','close']].dropna().sort_values('time').drop_duplicates('time',keep='last')
p=p.set_index('time').resample('5min').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()

# ---------- H1 / H4 ----------
h1=p.set_index('time').resample('60min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
pr=h1.close.shift(1)
tr=pd.concat([(h1.high-h1.low),(h1.high-pr).abs(),(h1.low-pr).abs()],axis=1).max(axis=1)
h1['atr']=tr.rolling(14,min_periods=14).mean();h1['ema20']=h1.close.ewm(span=20,adjust=False).mean();h1['extension_atr']=(h1.close-h1.ema20)/h1.atr
h1['close_time']=h1.time+pd.Timedelta(hours=1)

h4=p.set_index('time').resample('4h',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index()
h4['ema50']=h4.close.ewm(span=50,adjust=False).mean();h4['ema50_lag6']=h4.ema50.shift(6)
h4['trend']=np.where((h4.close>h4.ema50)&(h4.ema50>h4.ema50_lag6),1,np.where((h4.close<h4.ema50)&(h4.ema50<h4.ema50_lag6),-1,0))
h4prev=h4.close.shift(1)
h4tr=pd.concat([(h4.high-h4.low),(h4.high-h4prev).abs(),(h4.low-h4prev).abs()],axis=1).max(axis=1)
h4['atr14']=h4tr.rolling(14,min_periods=14).mean();h4['body_atr']=(h4.close-h4.open)/h4.atr14
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
    cnt=0 if x else min(cnt+1,999);ia.append(cnt)
h4['impulse_age']=ia
h4['close_time']=h4.time+pd.Timedelta(hours=4)

base=pd.merge_asof(p.sort_values('time'),h1[['close_time','atr','extension_atr']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward')
base=pd.merge_asof(base.sort_values('time'),h4[['close_time','trend','trend_age','impulse_age']].dropna().sort_values('close_time'),left_on='time',right_on='close_time',direction='backward',suffixes=('','_h4'))
base=pd.merge_asof(base.sort_values('time'),f[['time','z','oi_chg_4h']].dropna().sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min'))
base=base.dropna(subset=['atr','extension_atr','trend','trend_age','impulse_age','z','oi_chg_4h']).reset_index(drop=True)

# LAB119 frozen thresholds
trm=base.time<TRAIN_END
ext80=float(base.loc[trm,'extension_atr'].abs().quantile(.80))
oi70=float(base.loc[trm,'oi_chg_4h'].quantile(.70))

BT=base.time.reset_index(drop=True);BO=base.open.to_numpy(float);BH=base.high.to_numpy(float);BL=base.low.to_numpy(float);BC=base.close.to_numpy(float);BA=base.atr.to_numpy(float);BZ=base.z.to_numpy(float)

def phase(age,imp_age):
    if age<=3:return 'BIRTH_1_3'
    if imp_age<=2:return 'REACCEL_IMPULSE'
    if age<=12:return 'CONTINUATION_4_12'
    return 'OTHER'

# frozen universe: only two candidate phases from LAB119
events=[]
last=len(base)-1-H*12-1
for i in range(1,last):
    if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
    side=-1 if BZ[i]>0 else 1
    h4t=int(base.trend.iloc[i]);ext=float(base.extension_atr.iloc[i]);oi=float(base.oi_chg_4h.iloc[i])
    if h4t==0 or h4t==side:continue
    ext_against=(side>0 and ext<0) or (side<0 and ext>0)
    if not ext_against or abs(ext)<ext80 or oi<oi70:continue
    phs=phase(int(base.trend_age.iloc[i]),int(base.impulse_age.iloc[i]))
    if phs not in ['REACCEL_IMPULSE','CONTINUATION_4_12']:continue
    events.append(dict(i=i,signal_time=BT.iloc[i],split='TRAIN' if BT.iloc[i]<TRAIN_END else 'OOS',phase=phs,side=side,atr=float(BA[i]),anchor=float(BC[i]),z=float(BZ[i])))
ev=pd.DataFrame(events)

# ---------- 5m causal entry methods ----------
def find_entry(i,side,atr,anchor,method):
    end=min(i+SEARCH_BARS,len(base)-2)
    if method=='MARKET_Z':
        return i+1,i, np.nan
    if method=='SWING3_BREAK':
        for j in range(i+1,end+1):
            lo=max(i,j-3)
            if side>0:
                ref=float(np.max(BH[lo:j]))
                if BC[j]>ref:return j+1,j,ref
            else:
                ref=float(np.min(BL[lo:j]))
                if BC[j]<ref:return j+1,j,ref
        return None,None,np.nan
    if method=='FAILED_CONTINUATION_025':
        # First continuation by >=0.25 ATR against reversal side, then close through prior 3-bar swing in reversal direction.
        adv_hit=None
        for j in range(i+1,end+1):
            adv=((anchor-BL[j])>=0.25*atr) if side>0 else ((BH[j]-anchor)>=0.25*atr)
            if adv_hit is None and adv:adv_hit=j
            if adv_hit is not None and j>=adv_hit:
                lo=max(i,j-3)
                if side>0:
                    ref=float(np.max(BH[lo:j]))
                    if BC[j]>ref:return j+1,j,ref
                else:
                    ref=float(np.min(BL[lo:j]))
                    if BC[j]<ref:return j+1,j,ref
        return None,None,np.nan
    if method=='RECLAIM_050':
        adv_hit=None
        for j in range(i+1,end+1):
            adv=((anchor-BL[j])>=0.50*atr) if side>0 else ((BH[j]-anchor)>=0.50*atr)
            if adv_hit is None and adv:adv_hit=j
            if adv_hit is not None and ((BC[j]>=anchor) if side>0 else (BC[j]<=anchor)):
                return j+1,j,anchor
        return None,None,np.nan
    raise ValueError(method)

METHODS=['MARKET_Z','SWING3_BREAK','FAILED_CONTINUATION_025','RECLAIM_050']

def first_pass_from_entry(ei,side,entry,atr,fav,adv,hours=48):
    end=min(ei+hours*12-1,len(base)-1)
    for j in range(ei,end+1):
        fh=((BH[j]-entry)>=fav*atr) if side>0 else ((entry-BL[j])>=fav*atr)
        ah=((entry-BL[j])>=adv*atr) if side>0 else ((BH[j]-entry)>=adv*atr)
        if fh and ah:return 0
        if fh:return 1
        if ah:return -1
    return 0

def trade_R(ei,side,entry,atr,tp_r=3.0,stop_atr=1.0,hours=48,cost_bps=0.0):
    sl=entry-side*stop_atr*atr;tp=entry+side*stop_atr*tp_r*atr
    end=min(ei+hours*12-1,len(base)-1)
    gross=side*(BC[end]-entry)/(stop_atr*atr);reason='TIME'
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1.0;reason='BOTH_STOP_FIRST';break
        if hs:gross=-1.0;reason='SL';break
        if ht:gross=tp_r;reason='TP';break
    costR=(cost_bps/10000.0)*entry/(stop_atr*atr)
    return gross-costR,reason

rows=[]
for _,r in ev.iterrows():
    i=int(r.i);side=int(r.side);atr=float(r.atr);anchor=float(r.anchor)
    for m in METHODS:
        ei,ti,ref=find_entry(i,side,atr,anchor,m)
        if ei is None or ei>=len(base):continue
        entry=float(BO[ei])
        row=dict(signal_time=r.signal_time,split=r['split'],phase=r.phase,side='BUY' if side>0 else 'SELL',method=m,
                 trigger_time=BT.iloc[ti],entry_time=BT.iloc[ei],delay_min=(BT.iloc[ei]-r.signal_time).total_seconds()/60,
                 entry_vs_signal_atr=side*(entry-anchor)/atr)
        for fav,adv in [(2,.5),(3,1),(5,1.5)]:
            row[f'fp_{fav}_{adv}']=first_pass_from_entry(ei,side,entry,atr,fav,adv)
        for c in COST_BPS:
            rr,reason=trade_R(ei,side,entry,atr,3.0,1.0,48,c)
            row[f'R3_c{c}']=rr;row[f'exit_c{c}']=reason
        rows.append(row)
res=pd.DataFrame(rows);res.to_csv(OUT/'LAB120_entry_events.csv',index=False)

def summarize(g,cost):
    x=g[f'R3_c{cost}'].to_numpy(float)
    pos=x[x>0].sum();neg=-x[x<0].sum()
    return dict(n=len(g),trigger_rate=np.nan,median_delay_min=float(g.delay_min.median()),entry_improvement=float(g.entry_vs_signal_atr.mean()),
                p2_05=float((g['fp_2_0.5']==1).mean()),p3_1=float((g['fp_3_1']==1).mean()),p5_15=float((g['fp_5_1.5']==1).mean()),
                ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),tp_rate=float((g[f'exit_c{cost}']=='TP').mean()))

summary=[]
for split in ['TRAIN','OOS']:
    baseq=ev[ev.split==split]
    for phs in ['REACCEL_IMPULSE','CONTINUATION_4_12','ALL']:
        denom=len(baseq if phs=='ALL' else baseq[baseq.phase==phs])
        q=res[res.split==split]
        if phs!='ALL':q=q[q.phase==phs]
        for m in METHODS:
            g=q[q.method==m]
            if not len(g):continue
            for c in COST_BPS:
                d=summarize(g,c);d['trigger_rate']=len(g)/denom if denom else np.nan
                summary.append(dict(split=split,phase=phs,method=m,cost_bps=c,**d))
sm=pd.DataFrame(summary);sm.to_csv(OUT/'LAB120_summary.csv',index=False)

# ---------- second-level absorption/reversal timing on overlap ----------
# Use exact 1-second archive aggregated to 10s; only descriptive due short 2026 coverage.
sec_rows=[]
if SEC_ZIP.exists():
    parts=[]
    with zipfile.ZipFile(SEC_ZIP) as z:
        member=[n for n in z.namelist() if n.lower().endswith('.csv')][0]
        with z.open(member) as fh:
            for ch in pd.read_csv(fh,chunksize=1_000_000):
                ch=ch[['ts','o','h','l','c','bnot','snot']].copy()
                ch['bucket']=(pd.to_numeric(ch.ts,errors='coerce').astype('Int64')//10)*10
                for c in ['o','h','l','c','bnot','snot']:ch[c]=pd.to_numeric(ch[c],errors='coerce')
                ch=ch.dropna()
                g=ch.groupby('bucket',sort=False).agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last'),bnot=('bnot','sum'),snot=('snot','sum'))
                parts.append(g.reset_index())
    sec=pd.concat(parts,ignore_index=True).groupby('bucket',as_index=False).agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last'),bnot=('bnot','sum'),snot=('snot','sum')).sort_values('bucket').reset_index(drop=True)
    sec['time']=pd.to_datetime(sec.bucket,unit='s',utc=True)
    rb=sec.bnot.rolling(3,min_periods=3).sum();rs=sec.snot.rolling(3,min_periods=3).sum()
    sec['imb30']=(rb-rs)/(rb+rs).replace(0,np.nan)
    sct=sec.time.astype('int64').to_numpy()
    soo=sec.o.to_numpy(float);shi=sec.h.to_numpy(float);slo=sec.l.to_numpy(float);scc=sec.c.to_numpy(float);sim=sec.imb30.to_numpy(float)
    def sidx(t):return int(np.searchsorted(sct,pd.Timestamp(t).value,side='left'))
    for _,r in ev.iterrows():
        if r.signal_time<sec.time.iloc[0] or r.signal_time>sec.time.iloc[-1]-pd.Timedelta(hours=6):continue
        side=int(r.side);atr=float(r.atr);a=sidx(r.signal_time)+1;b=min(a+6*360,len(sec)-2)
        # absorption: opposing aggressive flow |imb|>=.35, then reversal to aligned >=.25 within 5m.
        opp=(-side*sim)>=0.35
        aligned=(side*sim)>=0.25
        found=None
        for j in np.flatnonzero(opp[a:b]):
            jj=a+int(j);e=min(jj+30,b)
            k=np.flatnonzero(aligned[jj+1:e])
            if len(k):
                found=jj+1+int(k[0]);break
        if found is not None:
            sec_rows.append(dict(signal_time=r.signal_time,split=r['split'],phase=r.phase,side='BUY' if side>0 else 'SELL',
                                 delay_min=(sec.time.iloc[found]-r.signal_time).total_seconds()/60,
                                 entry_time=sec.time.iloc[found+1],entry=float(soo[found+1])))
secdf=pd.DataFrame(sec_rows);secdf.to_csv(OUT/'LAB120_second_level_absorption_entries.csv',index=False)

lines=['# LAB120 — REACCEL CAPITULATION × ENTRY TIMING','',
f'Frozen universe from LAB119: CAP_BASE thresholds ext>={ext80:.2f} H1 ATR, OI4h>={oi70:+.3%}, only REACCEL_IMPULSE and CONTINUATION_4_12.',
'Entry methods are causal and searched up to 6h: MARKET_Z=next M5 open; SWING3_BREAK=first close through previous 3-bar swing in reversal direction; FAILED_CONTINUATION_025=at least 0.25 ATR continuation first, then swing3 break; RECLAIM_050=at least 0.50 ATR adverse excursion then close back through original signal price.',
'Primary tradability diagnostic: fixed SL=1.0 H1 ATR, TP=3R, max hold 48h, stop-first same-bar. Costs 0/2.81/7.5 bps. This is a timing comparison, not a final strategy optimization.',
'Second-level absorption/reversal entries are exported separately for 2026 overlap only; not mixed into the long-history ranking.','']

for phs in ['REACCEL_IMPULSE','CONTINUATION_4_12','ALL']:
    lines.append(f'## {phs}')
    for split in ['TRAIN','OOS']:
        lines.append(f'### {split}')
        for m in METHODS:
            a=sm[(sm.split==split)&(sm.phase==phs)&(sm.method==m)&(sm.cost_bps==2.81)]
            if len(a):
                r=a.iloc[0]
                lines.append(f"- {m}: rate={r.trigger_rate:.1%} N={int(r.n)} delay={r.median_delay_min:.0f}m entryΔ={r.entry_improvement:+.2f}ATR | +3/-1={r.p3_1:.1%} +5/-1.5={r.p5_15:.1%} | EV3R={r.ev:+.3f}R PF={r.pf:.2f} WR={r.wr:.1%}")
        lines.append('')
(OUT/'LAB120_REPORT.md').write_text('\n'.join(lines)+'\n')
(OUT/'LAB120_meta.json').write_text(json.dumps(dict(
    universe='LAB119 CAP_BASE, phases REACCEL_IMPULSE + CONTINUATION_4_12',
    ext80=ext80,oi70=oi70,search_hours=6,
    methods=METHODS,
    tradability_shell=dict(stop_atr=1.0,tp_r=3.0,max_hold_h=48,cost_bps=COST_BPS,same_bar='stop-first'),
    caveat='development OOS repeatedly inspected; CONTINUATION OOS is sparse; second-level overlap is 2026-only'
),indent=2))
print('\n'.join(lines))
