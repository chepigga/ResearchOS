from pathlib import Path
import ast,types,os,json,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/LAB160C_20261010';OUT.mkdir(exist_ok=True)
DATA=Path(os.environ.get('LAB160C_DATA',ROOT.parent/'data')).resolve();os.chdir(DATA)
L=ROOT/'labs';PREFIX=L/'LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py'
A=types.ModuleType('baseline124');A.__file__=str(PREFIX)
exec(compile(PREFIX.read_text().split('# Broader anti-crowd capitulation universe:')[0],str(PREFIX),'exec'),A.__dict__)
print('TAPE',len(A.b),'EXT80',A.EXT80,'OI70',A.OI70,flush=True)
# Reuse function bodies verbatim from frozen execution and profile sources, without unrelated top-level lab sweeps.
def functions(path,names,namespace):
 tree=ast.parse(path.read_text());nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names]
 assert len(nodes)==len(names)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
ns=dict(np=np,pd=pd,BT=A.BT,BO=A.BO,BH=A.BH,BL=A.BL,BC=A.BC,MAX_H_BARS=576,RISK=.25)
functions(L/'LAB155_ADDON_RISK_TRANSFER_20261009/run_lab155.py',['init_pos','total_mtm_at_open','total_mtm_at_close','stop_price','finish','evaluate_bar','transfer_first_stop','stats'],ns)
import re,zipfile
ps=dict(np=np,pd=pd,Path=Path,re=re,zipfile=zipfile,PROFILE_H=24,PROFILE_BINS=40)
profile_src=L/'LAB159_PROFILE_SHAPE_INCREMENTAL_REPLAY_20261010/run_lab159.py'
functions(profile_src,['norm','pick','load_zip','ptime','vap_profile','shape_name','shape_at_time'],ps)
exec(compile(profile_src.read_text().split('rawp=')[1].split('def vap_profile')[0].join(['rawp=','']),str(profile_src),'exec'),ps)
# Original recovered raw signals; resolve chronology against original LAB124 tape, not LAB160 atlas indices.
raw=pd.read_csv(ROOT/'results/LAB160B_20261010/LAB160B_legacy_raw_signals.csv');raw.entry_time=pd.to_datetime(raw.entry_time,utc=True)
raw=raw[['source','entry_time','entry_i','side','atr','pri']].copy()
assert (pd.DatetimeIndex(A.BT.iloc[raw.entry_i])==pd.DatetimeIndex(raw.entry_time)).all()
assert len(raw)==506
raw['key']=raw.source+'|'+raw.entry_time.astype(str)+'|'+raw.side.astype(str)
oldkeys=set(raw.key);atidx={t:i for i,t in enumerate(A.BT)}
# R48 source tape exactly matches LAB136 pre-compression tape; compression column is irrelevant for R48.
b=A.b[A.b.time<A.TRAIN_END].copy().reset_index(drop=True)
b=pd.merge_asof(b.sort_values('time'),A.f.loc[A.f.time<A.TRAIN_END,['time','oi']].sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta('5min')).dropna(subset=['oi']).reset_index(drop=True)
BC=b.close.to_numpy();BH=b.high.to_numpy();BL=b.low.to_numpy();BA=b.atr.to_numpy();OI=b.oi.to_numpy();BT=b.time
hi=b.high.shift(1).rolling(576,min_periods=576).max().to_numpy();lo=b.low.shift(1).rolling(576,min_periods=576).min().to_numpy()
rrows=[];last=-9999
for i in range(577,len(b)-576-7):
 if i-last<24:continue
 up=BC[i]>hi[i];down=BC[i]<lo[i]
 if up==down:continue
 side=1 if up else -1;boundary=hi[i] if up else lo[i];cl=BC[i+1:i+7];outs=cl>boundary if up else cl<boundary
 if outs.sum()<4:continue
 ei=i+7;last=i;t=BT.iloc[ei]
 rrows.append(dict(source='R48_HIGH',entry_time=t,entry_i=atidx[t],side=side,atr=BA[i],pri=2,mean_margin=float(np.mean((cl-boundary)*side/BA[i])),oi_change=OI[ei]/OI[i]-1,retest=bool(np.any(BL[i+1:i+7]<=boundary) if up else np.any(BH[i+1:i+7]>=boundary))))
r48=pd.DataFrame(rrows);r48['key']=r48.source+'|'+r48.entry_time.astype(str)+'|'+r48.side.astype(str)
margin=r48.mean_margin.quantile(.6);oit=r48.oi_change.quantile(.6)
high=(~r48.retest)&(r48.mean_margin>=margin)&(r48.oi_change>=oit)
assert set(r48.loc[high,'key'])==set(raw.loc[raw.source=='R48_HIGH','key'])
print('R48 universe',len(r48),'HIGH',high.sum(),'thresholds',margin,oit,flush=True)
# New A events; union preserves original crossings that a lower threshold would otherwise replace.
o50=A.b.loc[A.b.time<A.TRAIN_END,'oi4h'].quantile(.5)
def new_a(zmin,oimin):
 rows=[];bb=A.b
 ix=np.flatnonzero((np.abs(A.BZ[1:])>=zmin)&(np.abs(A.BZ[:-1])<zmin))+1
 for i in ix:
  if i>=len(bb)-578 or A.BT.iloc[i]>=A.TRAIN_END:continue
  side=-1 if A.BZ[i]>0 else 1;r=bb.iloc[i];ext=float(r.extension)
  if int(r.trend)==0 or int(r.trend)==side:continue
  if not((side>0 and ext<0)or(side<0 and ext>0)) or abs(ext)<A.EXT80 or r.oi4h<oimin:continue
  if A.phase(int(r.trend_age),int(r.impulse_age)) not in ['CONT','REACCEL']:continue
  ei,ti,strength=A.swing3_entry(i,side)
  if ei is None or A.BT.iloc[ei]>=A.TRAIN_END:continue
  rows.append(dict(source='A',entry_time=A.BT.iloc[ei],entry_i=ei,side=side,atr=A.BA[i],pri=0,signal_time=A.BT.iloc[i],signal_z=A.BZ[i],signal_oi4h=r.oi4h))
 d=pd.DataFrame(rows);d['key']=d.source+'|'+d.entry_time.astype(str)+'|'+d.side.astype(str)
 return d[~d.key.isin(oldkeys)].drop_duplicates('key')
sets={'OLD':raw.copy()}
for name,mask in [('R48_RETEST',(r48.mean_margin>=margin)&(r48.oi_change>=oit)),('R48_OI',(~r48.retest)&(r48.mean_margin>=margin)),('R48_BOTH',r48.mean_margin>=margin)]:
 sets[name]=pd.concat([raw,r48.loc[mask & ~r48.key.isin(oldkeys)]],ignore_index=True)
for name,z,oi in [('A_Z075',.75,A.OI70),('A_OI50',1,o50),('A_Z075_OI50',.75,o50)]:sets[name]=pd.concat([raw,new_a(z,oi)],ignore_index=True)
allraw=pd.concat(sets.values(),ignore_index=True).drop_duplicates('key');shapes={}
for t in sorted(allraw.entry_time.unique()):shapes[t]=ps['shape_at_time'](t)
for name,d in list(sets.items()):
 d=d.copy();d['event_id']=d.key+'#'+d.groupby('key').cumcount().astype(str);d['profile_shape']=d.entry_time.map(shapes);d['is_new']=~d.key.isin(oldkeys);sets[name]=d
 keep=~((d.source=='R48_HIGH')&(d.profile_shape=='b'))
 if name.startswith('A_'):keep &= ~((d.source=='A')&d.is_new&(d.profile_shape!='D'))
 sets[name+'_PROFILE']=d[keep].copy()
sets={k:sets[k] for k in ['OLD','OLD_PROFILE']+[k for k in sets if k not in ['OLD','OLD_PROFILE']]}
for name,d in sets.items():d.assign(variant=name).to_csv(OUT/f'raw_{name}.csv',index=False)
print('RAW COUNTS',{k:len(v) for k,v in sets.items()},flush=True)
# Same frozen trade execution functions, full chronological portfolio replay.
fn=types.SimpleNamespace(**ns)
def replay(d,cost):
 d=d.sort_values(['entry_i','pri']).reset_index(drop=True);by={}
 for _,r in d.iterrows():by.setdefault(int(r.entry_i),[]).append(r)
 active=[];closed=[];eq=[];realized=0.;skipped=0;adds=0
 start=int(raw.entry_i.min());end=min(max(int(v.entry_i.max()) for v in sets.values())+576,len(A.BT)-1)
 for i in range(start,end+1):
  for r in by.get(i,[]):
   allow=len(active)==0;addon=False
   if len(active)==1:allow=int(active[0]['side'])==int(r.side) and fn.total_mtm_at_open(active[0],i)>=0;addon=allow
   if allow:
    if addon:adds+=1;fn.transfer_first_stop(active[0],'LOCK2_LOCK025')
    p=fn.init_pos(r,cost,'LOCK2');p.update(addon_parent=addon,profile_shape=r.profile_shape,key=r.key,event_id=r.event_id,is_new=bool(r.is_new));active.append(p)
   else:skipped+=1
  alive=[]
  for p in active:
   done=fn.evaluate_bar(p,i)
   if done is None:alive.append(p)
   else:closed.append(done);realized+=done['net_r']
  active=alive;floating=sum(fn.total_mtm_at_close(p,i) for p in active)
  eq.append((A.BT.iloc[i],realized+floating,realized,floating,len(active)))
 return pd.DataFrame(closed),pd.DataFrame(eq,columns=['time','equity_r','realized_r','floating_r','open_count']),skipped,adds

def perf(t):
 x=t.net_r.to_numpy();p=x[x>0].sum();n=-x[x<0].sum()
 return dict(n=len(x),ev=float(x.mean()) if len(x) else None,pf=float(p/n) if n else None,total_r=float(x.sum()),wr=float((x>0).mean()) if len(x) else None)
summary=[];annual=[];attribution=[];alltr=[];monthly=[];standalone=[];baselines={};deltas=[];validations=[]
for cost in [7.5,2.81]:
 for name,d in sets.items():
  t,eq,sk,adds=replay(d,cost);p=fn.stats(t,eq);p.update(variant=name,cost_bps=cost,raw_n=len(d),new_raw=int(d.is_new.sum()),skipped=sk,addons=adds)
  # Fixed common 48-month denominator and initial equity zero for DD; baseline lineage parity retained separately.
  p['trades_month']=len(t)/48;p['r_month']=t.net_r.sum()/48;p['mtm_dd_pct_with_initial_zero']=float((np.maximum.accumulate(np.r_[0,eq.equity_r])[1:]-eq.equity_r).max()*.25)
  summary.append(p);t['variant']=name;t['cost_bps']=cost;alltr.append(t)
  for y,g in t.groupby(pd.to_datetime(t.entry_time).dt.year):annual.append(dict(variant=name,cost_bps=cost,year=int(y),**perf(g)))
  for group,g in t.groupby('is_new'):attribution.append(dict(variant=name,cost_bps=cost,cohort='NEW_RAW_ACCEPTED' if group else 'OLD_RAW_ACCEPTED',**perf(g)))
  # Realized monthly totals on exit time. Include zero months for paired comparisons.
  m=t.groupby(pd.to_datetime(t.exit_time).dt.strftime('%Y-%m')).net_r.sum().reindex(pd.period_range('2021-01','2024-12',freq='M').astype(str),fill_value=0)
  assert abs(m.sum()-t.net_r.sum())<1e-8
  for month,v in m.items():monthly.append(dict(cost_bps=cost,variant=name,month=month,total_r=v))
  if name in ['OLD','OLD_PROFILE']:baselines[(cost,name)]=t.copy()
  for base in ['OLD','OLD_PROFILE']:
   if (cost,base) not in baselines:continue
   bt=baselines[(cost,base)];common=set(t.event_id)&set(bt.event_id);add=t[~t.event_id.isin(bt.event_id)];removed=bt[~bt.event_id.isin(t.event_id)]
   delta_common=t[t.event_id.isin(common)].net_r.sum()-bt[bt.event_id.isin(common)].net_r.sum();delta=t.net_r.sum()-bt.net_r.sum()
   assert abs(delta-(add.net_r.sum()-removed.net_r.sum()+delta_common))<1e-8
   deltas.append(dict(cost_bps=cost,variant=name,baseline=base,delta_r=delta,delta_rmo=delta/48,added_executed_n=len(add),added_executed_r=add.net_r.sum(),removed_n=len(removed),removed_r=removed.net_r.sum(),common_outcome_delta_r=delta_common))
  print(cost,name,'N',len(t),'PF',round(p['pf'],3),'Rmo',round(p['r_month'],3),'DD',round(p['mtm_dd_pct'],3),flush=True)
  # Baseline reproduction is a mandatory gate before interpreting variants.
  if cost==7.5 and name in ['OLD','OLD_PROFILE']:
   target={'OLD':(300,.564,1.95,3.52,3.92),'OLD_PROFILE':(251,.695,2.27,3.64,2.47)}[name]
   assert len(t)==target[0],(name,'N',len(t),target)
   for col,exp,tol in zip(['ev','pf','r_month','mtm_dd_pct'],target[1:],[.001,.01,.01,.01]):assert abs(p[col]-exp)<tol,(name,col,p[col],exp)
   validations.append(dict(variant=name,cost=cost,baseline_parity=True))
 # New signals isolated with each variant's own signal-anchor ATR; different triggers can share an entry time.
 for variant,d in sets.items():
  for _,r in d[d.is_new].iterrows():
   p=fn.init_pos(r,cost,'LOCK2');done=None
   for i in range(int(r.entry_i),min(int(r.entry_i)+578,len(A.BT))):
    done=fn.evaluate_bar(p,i)
    if done is not None:break
   assert done is not None
   standalone.append(dict(variant=variant,key=r.key,source=r.source,entry_time=r.entry_time,atr=r.atr,profile_shape=r.profile_shape,cost_bps=cost,net_r=done['net_r']))
for name,rows in [('summary',summary),('annual',annual),('attribution',attribution),('monthly',monthly),('standalone_new',standalone),('portfolio_delta_decomposition',deltas)]:pd.DataFrame(rows).to_csv(OUT/f'LAB160C_{name}.csv',index=False)
pd.concat(alltr,ignore_index=True).to_csv(OUT/'LAB160C_trades.csv',index=False)
# Fixed monthly paired bootstrap, descriptive, not independent-trade CI.
mo=pd.DataFrame(monthly);cis=[];rng=np.random.default_rng(1603)
for cost in [7.5,2.81]:
 p=mo[mo.cost_bps==cost].pivot(index='month',columns='variant',values='total_r')
 for name in sets:
  for base in ['OLD','OLD_PROFILE']:
   diff=(p[name]-p[base]).to_numpy();idx=rng.integers(0,48,size=(2000,48));means=diff[idx].mean(axis=1)
   cis.append(dict(cost_bps=cost,variant=name,baseline=base,delta_rmo=diff.mean(),ci_low=np.quantile(means,.025),ci_high=np.quantile(means,.975),positive_months=int((diff>0).sum())))
pd.DataFrame(cis).to_csv(OUT/'LAB160C_delta_monthly_bootstrap.csv',index=False)
meta=dict(parent='2fc655be226af63035457d73b82a09893c27f377',period='2021-2024 development only',risk_pct=.25,raw_old=len(raw),r48_universe=len(r48),r48_high=int(high.sum()),r48_margin_q60=margin,r48_oi_q60=oit,A_EXT80=A.EXT80,A_OI70=A.OI70,A_OI50=o50,baseline_validations=validations,source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [DATA/'btc_5m.zip',DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip']})
(OUT/'LAB160C_meta.json').write_text(json.dumps(meta,indent=2));print('COMPLETE',flush=True)
