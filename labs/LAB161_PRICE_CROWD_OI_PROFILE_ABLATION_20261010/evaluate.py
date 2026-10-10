from pathlib import Path
import json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/LAB161_20261010';MODELS=['PRICE','PRICE_CROWD','PRICE_CROWD_OI','PRICE_CROWD_OI_PROFILE']
def matching(w,s):
 start=max(w.start,w.peak-pd.Timedelta(hours=24));q=s[(s.time>=start)&(s.time<w.peak)&(s.side==w.side)].sort_values('time');res={f'covered_{k}':False for k in [1,2,3]};res.update(first_signal=pd.NaT,remaining_atr=np.nan,remaining_fraction=np.nan,lead_hours=np.nan,clean_covered_1=False)
 if len(q):
  rem=w.side*(w.peak_price-q.close)/q.atr
  for k in [1,2,3]:res[f'covered_{k}']=bool((rem>=k).any())
  good=q[rem>=1]
  if len(good):
   r=good.iloc[0];res.update(first_signal=r.time,remaining_atr=float(rem.loc[r.name]),remaining_fraction=float(w.side*(w.peak_price-r.close)/abs(w.peak_price-w.start_price)),lead_hours=(w.peak-r.time).total_seconds()/3600,clean_covered_1=bool(good.clean_success.any()))
 return res

def bootstrap_delta(v,n,seed=161):
 rng=np.random.default_rng(seed);a=np.asarray(v);b=np.asarray(n);ix=rng.integers(len(a),size=(1000,len(a)));z=a[ix].sum(axis=1)/b[ix].sum(axis=1);return float(a.sum()/b.sum()),float(np.quantile(z,.025)),float(np.quantile(z,.975))

def main():
 d=pd.read_pickle(OUT/'LAB161_dataset.pkl');s=pd.read_csv(OUT/'LAB161_signals.csv',parse_dates=['time']);s=s[s.model!='LEGACY_RAW_PROFILE'].copy();waves=pd.read_csv(OUT/'LAB161_waves.csv',parse_dates=['start','peak','end','cutoff']);folds=json.loads((OUT/'LAB161_folds.json').read_text());folds={x['year']:x for x in folds}
 legacy=pd.read_csv(ROOT/'results/LAB160B_20261010/LAB160B_legacy_raw_signals.csv',parse_dates=['entry_time']);legacy=legacy[(legacy.entry_time.dt.year==2024)&legacy.pass_lab159_shape].drop_duplicates(['entry_time','side']);eligible=d[d.eligible];legacy=legacy[legacy.entry_time.isin(eligible.index)&(legacy.entry_time<pd.Timestamp(folds[2024]['test_end']))];old=eligible.loc[legacy.entry_time,['close','atr','target','up_mfe','down_mfe','terminal','up_hit_minutes','down_hit_minutes']].reset_index(names='time');old['side']=legacy.side.to_numpy();old['year']=2024;old['model']='LEGACY_RAW_PROFILE';old['requested_per_day']=0;old['score']=np.nan;old['threshold']=np.nan;s=pd.concat([s,old],ignore_index=True)
 s['clean_success']=s.target==np.where(s.side==1,1,2);s['direction_mfe']=np.where(s.side==1,s.up_mfe,s.down_mfe);s['direction_mae']=np.where(s.side==1,s.down_mfe,s.up_mfe);s['direction_terminal']=s.side*s.terminal;s['any3']=s.direction_mfe>=3;s['false_type']=np.select([s.clean_success,s.any3],['CLEAN_3_BEFORE_1_5','REACHES_3_AFTER_ADVERSE'],default='NEVER_REACHES_3');s['signal_id']=['S%06d'%i for i in range(len(s))];s.to_csv(OUT/'LAB161_signals.csv',index=False)
 rows=[];signal_stats=[];wave_counts=[]
 for year,f in folds.items():
  start=pd.Timestamp(f['test_start']);last=pd.Timestamp(f['test_last']);ew=waves[(waves.start>=start)&(waves.end<=last)].copy();ei=eligible.loc[start:last].index
  ew['observable']=[bool(((ei>=max(r.start,r.peak-pd.Timedelta(hours=24)))&(ei<r.peak)).any()) for r in ew.itertuples()]
  for definition,wg in ew.groupby('definition'):wave_counts.append(dict(year=year,definition=definition,waves=len(wg),observable=int(wg.observable.sum())))
  for (model,rate),q in s[s.year==year].groupby(['model','requested_per_day']):
   signal_stats.append(dict(year=year,model=model,requested_per_day=rate,signals=len(q),signals_per_day=len(q)/f['test_days'],false_pct=100*(~q.clean_success).mean(),clean_pct=100*q.clean_success.mean(),never3_pct=100*(~q.any3).mean(),after_adverse3_pct=100*(q.any3&~q.clean_success).mean(),mfe_median=q.direction_mfe.median(),mae_median=q.direction_mae.median(),terminal_median=q.direction_terminal.median()))
   for w in ew.itertuples():rows.append(dict(year=year,model=model,requested_per_day=rate,move_id=w.move_id,definition=w.definition,start=w.start,peak=w.peak,amplitude_atr=w.amplitude_atr,observable=w.observable,**matching(w,q)))
 a=pd.DataFrame(rows);a.to_csv(OUT/'LAB161_wave_matches.csv',index=False);pd.DataFrame(wave_counts).to_csv(OUT/'LAB161_wave_denominators.csv',index=False);pd.DataFrame(signal_stats).to_csv(OUT/'LAB161_signal_metrics.csv',index=False)
 wm=[]
 for (year,model,rate,definition),q in a.groupby(['year','model','requested_per_day','definition']):
  hit=q[q.covered_1];wm.append(dict(year=year,model=model,requested_per_day=rate,definition=definition,waves=len(q),observable=int(q.observable.sum()),covered1=int(q.covered_1.sum()),covered2=int(q.covered_2.sum()),covered3=int(q.covered_3.sum()),coverage1_pct=100*q.covered_1.mean(),coverage2_pct=100*q.covered_2.mean(),coverage3_pct=100*q.covered_3.mean(),observable_coverage1_pct=100*q.covered_1.sum()/q.observable.sum(),clean_coverage1_pct=100*q.clean_covered_1.mean(),remaining_atr_median=hit.remaining_atr.median(),remaining_fraction_median=hit.remaining_fraction.median(),lead_hours_median=hit.lead_hours.median()))
 pd.DataFrame(wm).to_csv(OUT/'LAB161_wave_metrics.csv',index=False)
 # Paired weekly Brier deltas: negative means improvement. Same weeks and same observations.
 w=pd.read_csv(OUT/'LAB161_weekly_errors.csv');br=[]
 for year in [2024,2025,2026,'ALL']:
  ww=w if year=='ALL' else w[w.year==year];pivot=ww.pivot(index=['year','week'],columns='model',values='sum');n=ww[ww.model=='PRICE'].set_index(['year','week'])['count'].reindex(pivot.index)
  for previous,current in zip(['BASE_RATE']+MODELS[:-1],MODELS):
   delta,lo,hi=bootstrap_delta(pivot[current]-pivot[previous],n);br.append(dict(year=year,previous=previous,model=current,delta_brier=delta,ci_low=lo,ci_high=hi,weeks=len(n)))
 pd.DataFrame(br).to_csv(OUT/'LAB161_incremental_brier.csv',index=False)
 # Paired wave coverage and signal error intervals using calendar-week clusters.
 diffs=[]
 for rate in [.5,1.,2.]:
  for year in [2024,2025,2026,'ALL']:
   v=a[(a.requested_per_day==rate)&(a.definition=='LEG_REV1ATR')&a.model.isin(MODELS)];v=v if year=='ALL' else v[v.year==year];pv=v.pivot(index=['year','move_id','start'],columns='model',values='covered_1').astype(float);week=pd.DatetimeIndex(pv.index.get_level_values('start')).strftime('%G-%V')
   for prev,cur in zip(MODELS[:-1],MODELS[1:]):
    z=pd.DataFrame({'delta':(pv[cur]-pv[prev]).to_numpy(),'week':week});wk=z.groupby('week').delta.agg(['sum','count']);delta,lo,hi=bootstrap_delta(wk['sum'],wk['count']);diffs.append(dict(year=year,requested_per_day=rate,previous=prev,model=cur,delta_coverage_pp=100*delta,ci_low=100*lo,ci_high=100*hi))
 pd.DataFrame(diffs).to_csv(OUT/'LAB161_incremental_coverage.csv',index=False)
 pooled=[]
 for (model,rate),q in s.groupby(['model','requested_per_day']):
  v=a[(a.model==model)&(a.requested_per_day==rate)&(a.definition=='LEG_REV1ATR')];h=v[v.covered_1];days=sum(folds[y]['test_days'] for y in q.year.unique());week=q.time.dt.strftime('%G-%V');cl=pd.DataFrame({'false':(~q.clean_success).astype(int),'week':week}).groupby('week')['false'].agg(['sum','count']);_,fl,fh=bootstrap_delta(cl['sum'],cl['count']);pooled.append(dict(model=model,requested_per_day=rate,signals=len(q),signals_per_day=len(q)/days,false_pct=100*(~q.clean_success).mean(),false_ci_low=100*fl,false_ci_high=100*fh,never3_pct=100*(~q.any3).mean(),after_adverse3_pct=100*(q.any3&~q.clean_success).mean(),waves=len(v),covered1=int(v.covered_1.sum()),coverage1_pct=100*v.covered_1.mean(),coverage2_pct=100*v.covered_2.mean(),coverage3_pct=100*v.covered_3.mean(),clean_coverage1_pct=100*v.clean_covered_1.mean(),remaining_atr_median=h.remaining_atr.median(),remaining_fraction_median=h.remaining_fraction.median(),lead_hours_median=h.lead_hours.median(),covered_per100_signals=100*v.covered_1.sum()/len(q)))
 pd.DataFrame(pooled).to_csv(OUT/'LAB161_pooled.csv',index=False);print('EVALUATION COMPLETE');print(pd.DataFrame(pooled).query('requested_per_day==1').to_string(index=False))
if __name__=='__main__':main()
