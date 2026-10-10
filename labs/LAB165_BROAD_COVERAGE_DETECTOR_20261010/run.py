import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from pathlib import Path
import json,joblib,numpy as np,pandas as pd
from detector import emit,calibrate,AlertDetector
R=Path(__file__).resolve().parents[2];O=R/'results/LAB165_20261010';OLD=R/'results/LAB161_20261010';RATES=[2,4,8,12];MODELS=['PRICE','PRICE_CROWD_OI_PROFILE']
def main():
 d=pd.read_pickle(OLD/'LAB161_dataset.pkl');folds=json.loads((OLD/'LAB161_folds.json').read_text());signals=[];cal=[]
 for f in folds:
  year=f['year'];npz=np.load(OLD/f'predictions/{year}.npz');ti=pd.to_datetime(npz['time_ns'],utc=True);test=d.loc[ti];t=ti.asi8//60_000_000_000;calstart=pd.Timestamp(f['cal_start']);calend=pd.Timestamp(f['test_start'])-pd.Timedelta(hours=24);v=d[d.eligible&(d.index>=calstart)&(d.index<calend)];vt=v.index.asi8//60_000_000_000;days=(calend-calstart).total_seconds()/86400
  for name in MODELS:
   pack=joblib.load(OLD/f'models/{year}_{name}.joblib');pv=pack['model'].predict_proba(v[pack['features']].to_numpy(np.float32));vs=pv[:,1:].max(axis=1);pt=npz[name];score=pt[:,1:].max(axis=1);side=np.where(pt[:,1]>=pt[:,2],1,-1)
   assert pd.Timestamp(pack['fold']['train_last'])+pd.Timedelta(hours=24)<calstart
   for rate in RATES:
    th,actual=calibrate(vt,vs,days,rate);ix=emit(t,score,th);policy=f'{name}_R{rate}';q=test.iloc[ix][['close','atr','target','up_mfe','down_mfe']].copy();q['time']=q.index;q['year']=year;q['policy']=policy;q['family']=name;q['rate']=rate;q['side']=side[ix];q['score']=score[ix];signals.append(q.reset_index(drop=True));cal.append(dict(year=year,policy=policy,threshold=th,calibration_per_day=actual,test_per_day=len(ix)/f['test_days'],requested_per_day=rate,cooldown_minutes=60));assert len(ix)<2 or np.min(np.diff(t[ix]))>=60
    live=AlertDetector(th);out=[]
    for j in range(min(len(t),2000)):
     if live.on_closed_bar(int(t[j]),pt[j,1],pt[j,2]) is not None:out.append(j)
    assert np.array_equal(emit(t[:2000],score[:2000],th),np.array(out))
   print('scored',year,name,flush=True)
  for rate in RATES:
   ix=np.flatnonzero(t%(1440//rate)==0);q=test.iloc[ix][['close','atr','target','up_mfe','down_mfe']].copy();q['time']=q.index;q['year']=year;q['policy']=f'CLOCK_1H_MOMENTUM_R{rate}';q['family']='CLOCK_1H_MOMENTUM';q['rate']=rate;q['side']=np.where(test.iloc[ix].ret_12>=0,1,-1);q['score']=np.nan;signals.append(q.reset_index(drop=True))
 old=pd.read_csv(OLD/'LAB161_signals.csv',parse_dates=['time']);old=old[old.model.isin(MODELS)&(old.requested_per_day==2)].copy();old['family']=old.model;old['policy']=old.model+'_OLD6H_R2';old['rate']=2;signals.append(old[['time','year','policy','family','rate','side','score','close','atr','target','up_mfe','down_mfe']]);s=pd.concat(signals,ignore_index=True);s['clean_success']=s.target==np.where(s.side==1,1,2);s['mfe']=np.where(s.side==1,s.up_mfe,s.down_mfe);s['false_type']=np.select([s.clean_success,s.mfe>=3],['CLEAN','AFTER_ADVERSE'],default='NEVER3');s.to_csv(O/'signals.csv.gz',index=False,compression='gzip');pd.DataFrame(cal).to_csv(O/'thresholds.csv',index=False)
 waves=pd.read_csv(OLD/'LAB161_waves.csv',parse_dates=['start','peak','end']);waves=waves[waves.definition=='LEG_REV1ATR'];wm=[]
 for f in folds:
  year=f['year'];w=waves[(waves.start>=pd.Timestamp(f['test_start']))&(waves.end<=pd.Timestamp(f['test_last']))]
  for policy,q in s[s.year==year].groupby('policy'):
   q=q.sort_values('time');tt=q.time.astype('int64').to_numpy();side=q.side.to_numpy();price=q.close.to_numpy();atr=q.atr.to_numpy();clean=q.clean_success.to_numpy();hits=np.zeros(len(q),bool)
   for r in w.itertuples():
    left=np.searchsorted(tt,max(r.start,r.peak-pd.Timedelta(hours=24)).value);right=np.searchsorted(tt,r.peak.value);ix=np.arange(left,right);ix=ix[side[ix]==r.side];rem=r.side*(r.peak_price-price[ix])/atr[ix];good=ix[rem>=1];record=dict(year=year,policy=policy,move_id=r.move_id,covered1=bool(len(good)),covered2=bool((rem>=2).any()),covered3=bool((rem>=3).any()),clean_covered=bool(clean[good].any()),signals_on_wave=len(good),remaining_atr=np.nan,remaining_fraction=np.nan,first_signal=pd.NaT,week=r.start.strftime('%G-%V'))
    if len(good):
     j=good[0];hits[good]=True;record.update(remaining_atr=r.side*(r.peak_price-price[j])/atr[j],remaining_fraction=r.side*(r.peak_price-price[j])/abs(r.peak_price-r.start_price),first_signal=q.time.iloc[j])
    wm.append(record)
   s.loc[q.index,'matches_wave']=hits
 a=pd.DataFrame(wm);a.to_csv(O/'wave_matches.csv.gz',index=False,compression='gzip');s.to_csv(O/'signals.csv.gz',index=False,compression='gzip');metrics=[]
 for period,years in [('2024',[2024]),('2025',[2025]),('2026',[2026]),('CHECK_2025_26',[2025,2026]),('ALL_2024_26',[2024,2025,2026])]:
  for policy,q in s[s.year.isin(years)].groupby('policy'):
   z=a[a.year.isin(years)&(a.policy==policy)];hit=z[z.covered1];days=sum(f['test_days'] for f in folds if f['year'] in years);metrics.append(dict(period=period,policy=policy,signals=len(q),per_day=len(q)/days,waves=len(z),recognized=int(z.covered1.sum()),coverage_pct=z.covered1.mean()*100,coverage2_pct=z.covered2.mean()*100,coverage3_pct=z.covered3.mean()*100,clean_coverage_pct=z.clean_covered.mean()*100,false_pct=(~q.clean_success).mean()*100,never3_pct=(q.false_type=='NEVER3').mean()*100,after_adverse_pct=(q.false_type=='AFTER_ADVERSE').mean()*100,median_remaining_atr=hit.remaining_atr.median(),median_remaining_fraction=hit.remaining_fraction.median(),recognized_per100_signals=100*z.covered1.sum()/len(q),signals_matching_wave_pct=100*q.matches_wave.astype(bool).mean(),median_signals_per_recognized_wave=hit.signals_on_wave.median()))
 m=pd.DataFrame(metrics);m.to_csv(O/'metrics.csv',index=False)
 # LAB164 comparison on exact same wave universe. Prior union includes stages, not positions.
 oldmatches=pd.read_csv(R/'results/LAB164_20261010/wave_matches.csv');ids=set(a[a.year.isin([2025,2026])].move_id);oldids=set(oldmatches[oldmatches.split=='CHECK'].move_id)&ids
 overlap=[]
 for policy,q in a[a.year.isin([2025,2026])].groupby('policy'):
  covered=set(q[q.covered1].move_id);overlap.append(dict(policy=policy,waves=len(ids),lab164_recognized=len(oldids),lab165_recognized=len(covered),shared=len(oldids&covered),additional_vs164=len(covered-oldids),missed_old=len(oldids-covered)))
 pd.DataFrame(overlap).to_csv(O/'same_wave_comparison.csv',index=False)
 # Exact parity of old reference coverage with LAB161 metrics, and fixed-model prefix batch/live parity above.
 reference=pd.read_csv(OLD/'LAB161_wave_metrics.csv');ref=reference[(reference.definition=='LEG_REV1ATR')&(reference.requested_per_day==2)&reference.model.isin(MODELS)]
 for r in ref.itertuples():
  q=m[(m.period==str(r.year))&(m.policy==r.model+'_OLD6H_R2')].iloc[0];assert int(q.recognized)==r.covered1;assert q.waves==r.waves
 audit=dict(old_LAB161_coverage_exact_parity=True,live_batch_prefix_parity=True,cooldown_verified=True,train_calibration_purge_verified=True,models_frozen=True,production_changed=False,default_policy='PRICE_CROWD_OI_PROFILE_R4',default_status='research_alerts_not_trade_entries',default_in_sample_calibration='2026 uses2025 scores; no2027/live threshold calibrated',folds=folds);(O/'validation.json').write_text(json.dumps(audit,indent=2));print(m[m.period=='CHECK_2025_26'].to_string(index=False),flush=True)
if __name__=='__main__':main()
