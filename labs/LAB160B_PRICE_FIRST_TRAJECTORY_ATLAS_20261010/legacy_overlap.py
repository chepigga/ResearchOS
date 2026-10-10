from pathlib import Path
import pandas as pd,numpy as np,json
R=Path(__file__).resolve().parents[2];O=R/'results/LAB160B_20261010'
s=pd.read_parquet(O/'LAB160B_states.parquet');r=pd.read_csv(O/'LAB160B_legacy_raw_signals.csv');r.entry_time=pd.to_datetime(r.entry_time,utc=True)
r['profile_shape_at_entry']=s['shape'].reindex(pd.DatetimeIndex(r.entry_time)).to_numpy()
assert r.profile_shape_at_entry.notna().all()
r['pass_lab159_shape']=~((r.source=='R48_HIGH')&(r.profile_shape_at_entry=='b'))
r.to_csv(O/'LAB160B_legacy_raw_signals.csv',index=False)
counts=[];signals=[];missed=[];checks=[]
cut=pd.Timestamp('2025-01-01',tz='UTC')
for h in [1,3,6,12,24,48]:
 d=pd.read_parquet(O/f'LAB160B_paths_{h}h.parquet')
 old=pd.read_parquet(R/f'results/LAB160_20261010/LAB160_labels_{h}h.parquet')
 valid=d.terminal_atr.notna()
 for x,y in [('terminal_atr','terminal_atr'),('up_mfe_atr','up_mfe_atr'),('down_mfe_atr','down_mfe_atr')]:
  error=float((d.loc[valid,x]-old.loc[valid,y]).abs().max());assert error<1e-10
  checks.append(dict(horizon_h=h,column=x,max_abs_error=error))
 # clock-defined nonoverlapping intervals; entire future window remains inside legacy scope
 q=d[d.fixed_anchor & d.terminal_atr.notna() & (d.index+pd.Timedelta(hours=h)<cut)].copy()
 q=q[q.path_class.str.startswith(('DIRECT','AFTER_PULLBACK','ORDER_UNCERTAIN'))]
 for variant,rr in [('RAW_A_B3_R48_EARLY',r),('RAW_PLUS_LAB159_SHAPE',r[r.pass_lab159_shape])]:
  covered=np.zeros(len(q),bool)
  for side in [-1,1]:
   idx=np.flatnonzero(q.dominant_side.to_numpy()==side);tt=q.index.asi8[idx]
   # latest allowed entry is the OPEN of the peak candle, not its already-observed close
   end=tt+(q.peak_minutes.to_numpy()[idx]-5)*60*10**9
   sig=np.sort(rr.loc[rr.side==side,'entry_time'].astype('int64').to_numpy())
   a=np.searchsorted(sig,tt,side='left');b=np.searchsorted(sig,end,side='right');covered[idx]=b>a
  q['covered']=covered
  for minimum in [1,2,3,5]:
   qq=q[q.max_excursion>=minimum]
   for name,v in [('ALL_RETAINED',qq)]+[(str(c),g) for c,g in qq.groupby('path_class')]:
    counts.append(dict(horizon_h=h,variant=variant,min_excursion_atr=minimum,path_class=name,nonoverlap_windows=len(v),with_same_side_raw_signal=int(v.covered.sum()),share_with_signal=float(v.covered.mean()) if len(v) else np.nan))
  if variant=='RAW_PLUS_LAB159_SHAPE':
   mm=q[(q.max_excursion>=3)&~q.covered].join(s[['z','oi4h_quantity','trend','shape','location']]);mm['horizon_h']=h
   missed.append(mm.reset_index()[['time','horizon_h','path_class','max_excursion','terminal_atr','prepeak_adverse','peak_minutes','z','oi4h_quantity','trend','shape','location']])
  at=d.reindex(pd.DatetimeIndex(rr.entry_time));at['source']=rr.source.to_numpy();at['signal_side']=rr.side.to_numpy()
  for (src,cls),v in at.groupby(['source','path_class']):signals.append(dict(horizon_h=h,variant=variant,source=src,path_class=cls,n=len(v),median_terminal_in_signal_direction=(v.terminal_atr*v.signal_side).median()))
pd.DataFrame(counts).to_csv(O/'LAB160B_legacy_opportunity_overlap.csv',index=False)
pd.DataFrame(signals).to_csv(O/'LAB160B_paths_at_legacy_signals.csv',index=False)
pd.concat(missed,ignore_index=True).to_csv(O/'LAB160B_uncovered_retained_windows.csv',index=False)
pd.DataFrame(checks).to_csv(O/'LAB160B_LAB160_numeric_parity.csv',index=False)
(O/'LAB160B_legacy_notes.json').write_text(json.dumps({'raw_n':len(r),'shape_pass_n':int(r.pass_lab159_shape.sum()),'by_source':r.source.value_counts().to_dict(),'scope':'2021-2024 only; original scripts TRAIN_END 2025-01-01','not_live_EA_coverage':True,'not_execution_or_profit_capture':True,'method':'nonoverlap UTC-clock windows; same-direction raw entry from anchor to peak-candle OPEN; no portfolio/concurrency filtering','parity':'LAB160 terminal and up/down MFE identical all six horizons'},indent=2))
print('coverage complete',len(r),int(r.pass_lab159_shape.sum()))
