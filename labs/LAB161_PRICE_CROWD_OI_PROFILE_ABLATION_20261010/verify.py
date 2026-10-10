from pathlib import Path
import json,types
import numpy as np,pandas as pd
from prepare import outcomes
from evaluate import matching
from run_models import emit
OUT=Path(__file__).resolve().parents[2]/'results/LAB161_20261010'
# Exact temporal barrier fixtures: favorable, adverse-first, none, missing future.
a=np.ones(7);c=np.array([100.,101,103,102,102,102,102]);assert outcomes(c,a,6)[0,0]==1;assert outcomes(200-c,a,6)[0,0]==2
c=np.array([100.,98,103,102,102,102,102]);assert outcomes(c,a,6)[0,0]==0 and outcomes(c,a,6)[0,1]==3
c[4]=np.nan;assert np.isnan(outcomes(c,a,6)[0,0]);assert (outcomes(np.ones(7)*100,a,6)[0,:4]==0).all()
# End-point entries excluded, first actual eligible signal determines remaining distance.
st=pd.Timestamp('2024-01-01',tz='UTC');w=types.SimpleNamespace(start=st,peak=st+pd.Timedelta(hours=4),peak_price=104,start_price=100,side=1)
s=pd.DataFrame(dict(time=[w.peak],side=[1],close=[103],atr=[1],clean_success=[True]));assert not matching(w,s)['covered_1']
s.time=[st+pd.Timedelta(hours=2)];m=matching(w,s);assert m['covered_1'] and not m['covered_2'] and m['remaining_atr']==1
assert np.array_equal(emit(np.array([0,5,359,360,365,720]),np.ones(6),.5),np.array([0,3,5]))
s=pd.read_csv(OUT/'LAB161_signals.csv',parse_dates=['time']);a=pd.read_csv(OUT/'LAB161_wave_matches.csv',parse_dates=['start','peak','first_signal']);summary=pd.read_csv(OUT/'LAB161_wave_metrics.csv');d=pd.read_pickle(OUT/'LAB161_dataset.pkl');folds=json.loads((OUT/'LAB161_folds.json').read_text())
for f in folds:
 assert pd.Timestamp(f['train_last'])+pd.Timedelta(hours=24)<pd.Timestamp(f['cal_start']);assert pd.Timestamp(f['cal_last'])+pd.Timedelta(hours=24)<pd.Timestamp(f['test_start'])
 for name in ['PRICE','PRICE_CROWD','PRICE_CROWD_OI','PRICE_CROWD_OI_PROFILE']:
  for _,q in s[(s.year==f['year'])&(s.model==name)].groupby('requested_per_day'):assert (q.sort_values('time').time.diff().dropna()>=pd.Timedelta(hours=6)).all()
assert s.time.isin(d[d.eligible].index).all();assert (~a.covered_2|a.covered_1).all() and (~a.covered_3|a.covered_2).all();hit=a[a.covered_1];assert (hit.first_signal>=hit.start).all() and (hit.first_signal<hit.peak).all();assert ((hit.peak-hit.first_signal)<=pd.Timedelta(hours=24)).all();assert (hit.remaining_atr>=1).all();assert (hit.observable).all()
for r in summary.itertuples():
 q=a[(a.year==r.year)&(a.model==r.model)&(a.requested_per_day==r.requested_per_day)&(a.definition==r.definition)];assert len(q)==r.waves and int(q.covered_1.sum())==r.covered1
# Validate inherited primary waves against LAB160d on common completed 2021–2024 range.
w=pd.read_csv(OUT/'LAB161_waves.csv',parse_dates=['start','peak','end']);old=pd.read_csv(OUT.parent/'LAB160D_20261010/LAB160D_price_moves.csv',parse_dates=['start','peak','end']);old=old[old.definition.str.startswith('LEG')];keys=['definition','start','peak'];merged=old.merge(w,on=keys,suffixes=('_old','_new'));assert len(merged)==len(old);assert np.allclose(merged.amplitude_atr_old,merged.amplitude_atr_new)
result=dict(label_fixtures=True,pivot_endpoint_excluded=True,cooldown=True,purged_boundaries=True,common_feature_eligibility=True,coverage_nested=True,matching_within_horizon=True,wave_summary_reconciliation=True,lab160d_completed_wave_parity=len(old),causal_prefix_invariance=json.loads((OUT/'LAB161_data_audit.json').read_text())['causal_prefix_invariance'])
(OUT/'LAB161_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
