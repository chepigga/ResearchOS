#!/usr/bin/env python3
"""GC_M1_ORDERFLOW_EDGE_DISCOVERY_003

Bounded historical discovery on raw GC trade flow already in the GC release.
This is NOT OOS certification. It searches a small preregistered mechanism set,
not an arbitrary threshold sweep.

Selection clock:
- Rithmic TRAIN: start -> 2026-08-20 00:00 UTC
- Rithmic VALID: 2026-08-20 -> 2026-09-06 22:00 UTC
- AMP same-clock metrics are feed-parity gates, not independent market validation.
- 2026-09-06 22:00 -> 2026-09-11 12:46 is LATE_CHECK_DISCOVERY_CLOCK.
- > 2026-09-11 12:46 is POST_CHECK (AMP has the useful extension).

Every candidate enters at exact next clock-contiguous M1 open after its completed
signal bar. No close-fill assumption, no XAU, no stops/targets.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path('research/gc')
OUT_JSON=ROOT/'GC_M1_ORDERFLOW_EDGE_DISCOVERY_003.json'
OUT_MD=ROOT/'GC_M1_ORDERFLOW_EDGE_DISCOVERY_003.md'
OUT_CSV=ROOT/'GC_M1_ORDERFLOW_EDGE_DISCOVERY_003_CANDIDATES.csv'
OUT_EVENTS=ROOT/'GC_M1_ORDERFLOW_EDGE_DISCOVERY_003_WINNER_EVENTS.csv'
RITH_URL='https://github.com/chepigga/ResearchOS/releases/download/GC/GC_RITHMIC_40D_003_GCZ6.zip'
RITH_SHA='b12465a783f36aac41b82a9f2a5c4e74bd2dcf7024ffc3636e8c41a8fd01e803'
AMP_URL='https://github.com/chepigga/ResearchOS/releases/download/GC/AMP_GC_HISTORY_EXPORTER_001_GCEZ26_20260806_182355__20260915_182355_TICKS.csv.zip'
AMP_SHA='81d675597368a9f6c78eee726ed547737366ffd8d8e54aa976bce50111db752b'
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
LATE_END=pd.Timestamp('2026-09-11T12:46:00Z')
HORIZONS=(5,15)

CANDIDATES=(
 'A_REV',
 'FAIL_Q20_REV',
 'OPPOSITE_BODY_REV',
 'REJECTION_REV',
 'SWEEP_REJECT_REV',
 'LOC_OPPOSITE_BODY_REV',
 'LOC_FAIL_Q20_REV',
 'A_CONT',
 'IMPACT_Q80_CONT',
 'BREAKOUT_CONT',
 'RANGE_IMPACT_CONT',
)


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def download(url,p):
 req=urllib.request.Request(url,headers={'User-Agent':'ResearchOS-GC-EDGE003/1.0'})
 with urllib.request.urlopen(req,timeout=180) as r,p.open('wb') as f: shutil.copyfileobj(r,f,1024*1024)

def prepare_ticks(t,feed):
 t=t.dropna(subset=['time_ms','price','volume']).copy()
 t=t[(t.price>0)&(t.volume>0)&t.aggressor.isin(['BUY','SELL'])]
 t=t.sort_values('time_ms',kind='mergesort').reset_index(drop=True)
 t['bar_ms']=(t.time_ms.astype('int64')//60000)*60000
 t['buy_size']=np.where(t.aggressor.eq('BUY'),t.volume,0.0)
 t['sell_size']=np.where(t.aggressor.eq('SELL'),t.volume,0.0)
 g=t.groupby('bar_ms',sort=True,observed=True)
 b=g.price.agg(open='first',high='max',low='min',close='last')
 b['buy_vol']=g.buy_size.sum(); b['sell_vol']=g.sell_size.sum(); b['volume']=b.buy_vol+b.sell_vol
 b['delta']=b.buy_vol-b.sell_vol
 b['delta_frac']=np.where(b.volume>0,b.delta/b.volume,0.0)
 # current-bar price-level concentration from raw trades
 lows=t.bar_ms.map(b.low); highs=t.bar_ms.map(b.high); rng=highs-lows
 lower=lows+.20*rng; upper=highs-.20*rng
 t['sell_lower']=np.where(t.aggressor.eq('SELL')&(t.price<=lower+1e-12),t.volume,0.0)
 t['buy_upper']=np.where(t.aggressor.eq('BUY')&(t.price>=upper-1e-12),t.volume,0.0)
 b['sell_lower']=t.groupby('bar_ms').sell_lower.sum(); b['buy_upper']=t.groupby('bar_ms').buy_upper.sum()
 b['sell_loc']=np.where(b.sell_vol>0,b.sell_lower/b.sell_vol,0.0)
 b['buy_loc']=np.where(b.buy_vol>0,b.buy_upper/b.buy_vol,0.0)
 pc=b.close.shift(1)
 b['tr']=pd.concat([(b.high-b.low),(b.high-pc).abs(),(b.low-pc).abs()],axis=1).max(axis=1); b.iloc[0,b.columns.get_loc('tr')]=np.nan
 b['atr14']=b.tr.rolling(14,min_periods=14).mean(); b['body_atr']=(b.close-b.open)/b.atr14
 b['range_atr']=(b.high-b.low)/b.atr14
 b['close_pos']=np.where((b.high-b.low)>0,(b.close-b.low)/(b.high-b.low),.5)
 # causal bar references
 for col,q,name in [('delta_frac',.10,'q10_delta'),('delta_frac',.90,'q90_delta'),('buy_vol',.75,'q75_buy'),('sell_vol',.75,'q75_sell'),('buy_loc',.75,'q75_buyloc'),('sell_loc',.75,'q75_sellloc'),('range_atr',.75,'q75_range')]:
  b[name]=b[col].shift(1).rolling(240,min_periods=240).quantile(q)
 b['prior20_low']=b.low.shift(1).rolling(20,min_periods=20).min(); b['prior20_high']=b.high.shift(1).rolling(20,min_periods=20).max()
 b=b.reset_index(); b['time']=pd.to_datetime(b.bar_ms,unit='ms',utc=True); b['feed']=feed
 # A states and causal impact quantiles among prior same-aggressor A only
 b['a_sell']=(b.delta_frac<=b.q10_delta)&(b.sell_vol>=b.q75_sell)
 b['a_buy']=(b.delta_frac>=b.q90_delta)&(b.buy_vol>=b.q75_buy)
 b['aggr']=''; b.loc[b.a_sell,'aggr']='SELL'; b.loc[b.a_buy,'aggr']='BUY'
 b['impact']=np.where(b.aggr.eq('SELL'),-(b.body_atr),np.where(b.aggr.eq('BUY'),b.body_atr,np.nan))
 b['impact_q20']=np.nan; b['impact_q80']=np.nan
 hist={'SELL':[],'BUY':[]}
 for i,row in b[b.aggr.ne('')].iterrows():
  h=hist[row.aggr]
  if len(h)>=15:
   b.at[i,'impact_q20']=float(np.quantile(h,.20)); b.at[i,'impact_q80']=float(np.quantile(h,.80))
  h.append(float(row.impact))
 return b

def load_rithmic(zp):
 frames=[]
 with zipfile.ZipFile(zp) as zf:
  for n in sorted(x for x in zf.namelist() if x.endswith('.csv.gz')):
   with zf.open(n) as raw,gzip.GzipFile(fileobj=raw) as gz:
    d=pd.read_csv(gz,usecols=['time_ms','price','volume','aggressor'])
   frames.append(d)
 t=pd.concat(frames,ignore_index=True); t.aggressor=t.aggressor.astype(str).str.upper()
 return prepare_ticks(t,'RITHMIC_RAW')
def load_amp(zp):
 with zipfile.ZipFile(zp) as zf:
  n=[x for x in zf.namelist() if x.lower().endswith('.csv')][0]
  with zf.open(n) as raw:
   d=pd.read_csv(io.TextIOWrapper(raw,encoding='utf-8-sig'),usecols=['time_msc','last','volume','volume_real','is_buy','is_sell'])
 vr=pd.to_numeric(d.volume_real,errors='coerce').fillna(0); vi=pd.to_numeric(d.volume,errors='coerce').fillna(0); vol=np.where(vr>0,vr,vi)
 ib=pd.to_numeric(d.is_buy,errors='coerce').fillna(0).astype(int).eq(1); ise=pd.to_numeric(d.is_sell,errors='coerce').fillna(0).astype(int).eq(1)
 ag=np.where(ib&~ise,'BUY',np.where(ise&~ib,'SELL','EXCLUDE'))
 t=pd.DataFrame({'time_ms':pd.to_numeric(d.time_msc,errors='coerce'),'price':pd.to_numeric(d['last'],errors='coerce'),'volume':vol,'aggressor':ag})
 return prepare_ticks(t,'AMP_CQG_RAW_EXCLUSIVE')

def candidate_mask_and_direction(b,name):
 A=b.aggr.ne(''); sell=b.aggr.eq('SELL'); buy=b.aggr.eq('BUY')
 rev=np.where(sell,1,np.where(buy,-1,0)); cont=-rev
 loc=np.where(sell,b.sell_loc,np.where(buy,b.buy_loc,np.nan)); qloc=np.where(sell,b.q75_sellloc,np.where(buy,b.q75_buyloc,np.nan))
 sweep=(sell&(b.low<=b.prior20_low))|(buy&(b.high>=b.prior20_high))
 reject=(sell&(b.close_pos>=.75))|(buy&(b.close_pos<=.25))
 breakout=(sell&(b.close_pos<=.25))|(buy&(b.close_pos>=.75))
 if name=='A_REV': m=A; direction=rev
 elif name=='FAIL_Q20_REV': m=A&b.impact_q20.notna()&(b.impact<=b.impact_q20); direction=rev
 elif name=='OPPOSITE_BODY_REV': m=A&(b.impact<=0); direction=rev
 elif name=='REJECTION_REV': m=A&reject; direction=rev
 elif name=='SWEEP_REJECT_REV': m=A&sweep&reject; direction=rev
 elif name=='LOC_OPPOSITE_BODY_REV': m=A&(loc>=qloc)&(b.impact<=0); direction=rev
 elif name=='LOC_FAIL_Q20_REV': m=A&(loc>=qloc)&b.impact_q20.notna()&(b.impact<=b.impact_q20); direction=rev
 elif name=='A_CONT': m=A; direction=cont
 elif name=='IMPACT_Q80_CONT': m=A&b.impact_q80.notna()&(b.impact>=b.impact_q80); direction=cont
 elif name=='BREAKOUT_CONT': m=A&sweep&breakout&(b.impact>0); direction=cont
 elif name=='RANGE_IMPACT_CONT': m=A&(b.range_atr>=b.q75_range)&(b.impact>0); direction=cont
 else: raise ValueError(name)
 return m,np.asarray(direction,int)

def build_events(b,name):
 mask,direction=candidate_mask_and_direction(b,name); idxs=np.flatnonzero(mask.to_numpy()); rows=[]
 for i in idxs:
  if i+1>=len(b): continue
  entry=b.iloc[i+1]
  if entry.time!=b.iloc[i].time+pd.Timedelta(minutes=1): continue
  atr=float(b.iloc[i].atr14)
  if not np.isfinite(atr) or atr<=0: continue
  d=int(direction[i]); ep=float(entry.open)
  row={'feed':b.iloc[i].feed,'candidate':name,'signal_time':b.iloc[i].time,'entry_time':entry.time,'direction':d,'side':'LONG' if d>0 else 'SHORT','atr14':atr,'entry':ep}
  for h in HORIZONS:
   j=i+h
   if j>=len(b) or b.iloc[j].time!=entry.time+pd.Timedelta(minutes=h-1): row[f'fwd_{h}m_atr']=np.nan
   else:
    px=float(b.iloc[j].close); row[f'fwd_{h}m_atr']=d*(px-ep)/atr
  rows.append(row)
 return pd.DataFrame(rows)

def period(df,label):
 t=pd.to_datetime(df.signal_time,utc=True)
 if label=='TRAIN': return df[t<TRAIN_END]
 if label=='VALID': return df[(t>=TRAIN_END)&(t<VALID_END)]
 if label=='LATE_CHECK': return df[(t>=VALID_END)&(t<=LATE_END)]
 if label=='POST_CHECK': return df[t>LATE_END]
 if label=='FULL': return df
 raise ValueError(label)
def metric(df,h):
 v=df[f'fwd_{h}m_atr'].dropna().to_numpy(float)
 side={}
 for s in ('LONG','SHORT'):
  sv=df.loc[df.side==s,f'fwd_{h}m_atr'].dropna().to_numpy(float); side[s]={'n':int(len(sv)),'ev':float(sv.mean()) if len(sv) else None}
 if len(v):
  tmp=df.dropna(subset=[f'fwd_{h}m_atr']).copy(); tmp['day']=pd.to_datetime(tmp.signal_time,utc=True).dt.date; daily=tmp.groupby('day')[f'fwd_{h}m_atr'].mean()
 else: daily=pd.Series(dtype=float)
 return {'n':int(len(v)),'ev':float(v.mean()) if len(v) else None,'median':float(np.median(v)) if len(v) else None,'wr':float((v>0).mean()*100) if len(v) else None,'days':int(len(daily)),'positive_days':int((daily>0).sum()),'side':side}
def summarize(events):
 return {p:{str(h):metric(period(events,p),h) for h in HORIZONS} for p in ('TRAIN','VALID','LATE_CHECK','POST_CHECK','FULL')}
def gate(rith,amp):
 rt5=rith['TRAIN']['5']; rt15=rith['TRAIN']['15']; rv5=rith['VALID']['5']; rv15=rith['VALID']['15']; av5=amp['VALID']['5']; av15=amp['VALID']['15']
 checks={
  'train_n_ge50':rt15['n']>=50,'valid_n_ge30':rv15['n']>=30,
  'train_5_pos':rt5['ev'] is not None and rt5['ev']>0,'train_15_pos':rt15['ev'] is not None and rt15['ev']>0,
  'valid_5_pos':rv5['ev'] is not None and rv5['ev']>0,'valid_15_pos':rv15['ev'] is not None and rv15['ev']>0,
  'valid_both_sides_15_pos':all(rv15['side'][s]['n']>=10 and rv15['side'][s]['ev'] is not None and rv15['side'][s]['ev']>0 for s in ('LONG','SHORT')),
  'valid_majority_positive_days_15':rv15['days']>0 and rv15['positive_days']*2>=rv15['days'],
  'amp_valid_feed_parity_5_pos':av5['ev'] is not None and av5['ev']>0,
  'amp_valid_feed_parity_15_pos':av15['ev'] is not None and av15['ev']>0,
 }
 checks['pass']=all(checks.values()); return checks

def main():
 work=ROOT/'_edge003_work'; work.mkdir(parents=True,exist_ok=True); rz=work/'rithmic.zip'; az=work/'amp.zip'
 if not rz.exists(): download(RITH_URL,rz)
 if not az.exists(): download(AMP_URL,az)
 if sha(rz)!=RITH_SHA or sha(az)!=AMP_SHA: raise SystemExit('source SHA mismatch')
 rb=load_rithmic(rz); ab=load_amp(az)
 results={}; rows=[]; events_cache={}
 for name in CANDIDATES:
  re=build_events(rb,name); ae=build_events(ab,name); events_cache[name]=(re,ae)
  rs=summarize(re); aas=summarize(ae); g=gate(rs,aas)
  results[name]={'rithmic':rs,'amp':aas,'gate':g}
  for feed,s in [('RITHMIC',rs),('AMP',aas)]:
   for p in ('TRAIN','VALID','LATE_CHECK','POST_CHECK','FULL'):
    rows.append({'candidate':name,'feed':feed,'period':p,'n':s[p]['15']['n'],'ev5':s[p]['5']['ev'],'ev15':s[p]['15']['ev'],'days15':s[p]['15']['days'],'positive_days15':s[p]['15']['positive_days'],'long_ev15':s[p]['15']['side']['LONG']['ev'],'short_ev15':s[p]['15']['side']['SHORT']['ev'],'gate_pass':g['pass']})
 passing=[n for n in CANDIDATES if results[n]['gate']['pass']]
 winner=None
 if passing:
  def score(n):
   r=results[n]
   return min(r['rithmic']['TRAIN']['15']['ev'],r['rithmic']['VALID']['15']['ev'],r['amp']['VALID']['15']['ev'])
  winner=max(passing,key=score)
 pd.DataFrame(rows).to_csv(OUT_CSV,index=False)
 if winner:
  re,ae=events_cache[winner]; pd.concat([re,ae],ignore_index=True).to_csv(OUT_EVENTS,index=False)
 else:
  pd.DataFrame(columns=['no_winner']).to_csv(OUT_EVENTS,index=False)
 out={'lab':'GC_M1_ORDERFLOW_EDGE_DISCOVERY_003','status':'HISTORICAL_DISCOVERY_NOT_OOS','candidate_set':list(CANDIDATES),'selection_uses':['Rithmic TRAIN','Rithmic VALID','AMP VALID feed-parity gate'],'late_checks_not_used_for_selection':['LATE_CHECK','POST_CHECK'],'passing':passing,'winner':winner,'results':results}
 OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
 lines=['# GC_M1_ORDERFLOW_EDGE_DISCOVERY_003','','Bounded historical discovery; **not OOS certification**. All entries are exact next M1 open.','',f'Passing candidates: **{passing if passing else "NONE"}**',f'Winner: **{winner or "NONE"}**','', '| Candidate | Gate | R Train 15m | R Valid 15m | AMP Valid 15m | Late 15m R/AMP | Post 15m AMP |','|---|---|---:|---:|---:|---:|---:|']
 for n in CANDIDATES:
  r=results[n]; f=lambda x:'NA' if x is None else f'{x:+.3f}'
  lines.append(f"| {n} | {'PASS' if r['gate']['pass'] else 'FAIL'} | {f(r['rithmic']['TRAIN']['15']['ev'])} | {f(r['rithmic']['VALID']['15']['ev'])} | {f(r['amp']['VALID']['15']['ev'])} | {f(r['rithmic']['LATE_CHECK']['15']['ev'])}/{f(r['amp']['LATE_CHECK']['15']['ev'])} | {f(r['amp']['POST_CHECK']['15']['ev'])} |")
 lines += ['','## Governance','','Rithmic and AMP are two representations of largely the same GC market, so cross-feed agreement is a parity/robustness check, not independent market OOS. LATE_CHECK and POST_CHECK were not used to select the winner. Any historical winner still requires a future untouched sample before promotion.']
 OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(OUT_MD.read_text())
if __name__=='__main__': main()
