from pathlib import Path
import json
import pandas as pd,numpy as np
from prepare import profile_nodes
from events import encounter_indices,LEVELS
O=Path(__file__).resolve().parents[2]/'results/LAB162_20261010'
# Two separated interior volume peaks, trough and B shape; price-only extreme bar has zero volume.
c=np.r_[np.full(143,60.),np.full(144,140.),100.];h=c+.5;l=c-.5;h[-1]=160;l[-1]=40;v=np.ones(288);v[-1]=0;pr=profile_nodes(h,l,c,v)[-1];assert pr[5]==3 and np.isfinite(pr[3:5]).all() and pr[6]<=.7
# Contact close is reference: a large contact move cannot itself count as future continuation.
n=100;c=np.full(n,99.5);h=c+.01;l=c-.01;a=np.ones(n);levels=np.full((n,1),100.);valid=np.ones(n,dtype=np.bool_);c[12]=99.8;h[13]=100.1;l[13]=99.8;c[13]=100.;c[14:]=101.2;events=encounter_indices(c,h,l,a,levels,valid);r=[r for r in events if r[0]==13][0];assert r[4]==1
c[13]=101.5;h[13]=101.5;c[14:]=100.;events=encounter_indices(c,h,l,a,levels,valid);r=[r for r in events if r[0]==13][0];assert r[4]==-1
s=pd.read_csv(O/'LAB162_encounters.csv',parse_dates=['time']);d=pd.read_pickle(O/'LAB162_tape.pkl');assert s.event_id.is_unique
for _,q in s.groupby(['level','side']):assert (q.time.sort_values().diff().dropna()>=pd.Timedelta(hours=6)).all()
for r in s.iloc[::37].itertuples():
 i=int(r.i);assert np.isclose(r.level_price,d[r.level].iloc[i-1]);assert d.oi_quantity.iloc[i-1]>0;future=r.side*(d.close.iloc[i+1:i+73].to_numpy()-d.close.iloc[i])/d.atr.iloc[i];hits=np.flatnonzero(abs(future)>=1);out=0 if len(hits)==0 else int(np.sign(future[hits[0]]));assert r.outcome==out
assert (s.pass_hit.astype(int)+s.reject_hit.astype(int)+s.unresolved.astype(int)==1).all()
for boundary in ['2024-01-01','2025-01-01']:
 t=pd.Timestamp(boundary,tz='UTC');assert (s.loc[(s.time>=t-pd.Timedelta(hours=6))&(s.time<t),'split']=='PURGED').all()
w=pd.read_csv(O/'LAB162_wave_anatomy.csv');tr=pd.read_csv(O/'LAB162_wave_trajectories.csv');mi=pd.read_csv(O/'LAB162_internal_legs.csv');assert w.move_id.is_unique;assert set(tr.move_id).issubset(set(w.move_id));assert set(mi.move_id).issubset(set(w.move_id))
for df in [w,tr,mi]:assert not np.isinf(df.select_dtypes(include='number').to_numpy()).any()
q=tr[(tr.anchor=='START')&(tr.position==0)];assert np.allclose(q.price_from_start_atr,0);assert np.allclose(q.oi_from_start_pct.dropna(),0)
audit=json.loads((O/'LAB162_data_audit.json').read_text());result=dict(profile_B_two_peak_fixture=True,contact_not_future_fixture=True,level_known_before_contact=True,cooldown=True,outcome_exclusive=True,sampled_outcome_recalculation=True,purged_boundaries=True,wave_rows_reconciled=True,no_infinite_trajectory_values=True,profile_prefix_invariance=audit['profile_node_prefix_invariance'],profile_price_level_parity=audit['poc_val_vah_lab161_parity']);(O/'LAB162_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
