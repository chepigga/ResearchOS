from pathlib import Path
import json
import numpy as np,pandas as pd
from run import structure,TFS
R=Path(__file__).resolve().parents[2];O=R/'results/LAB163_20261010';d=pd.read_pickle(R/'results/LAB162_20261010/LAB162_tape.pkl');cx=pd.read_pickle(O/'LAB163_context.pkl')
c=np.array([10,11,13,11,10,12,15,12,11,13,17,14,12,14,18,15,13.]);b=pd.DataFrame(dict(close=c,high=c+.5,low=c-.5),index=pd.date_range('2024-01-01',periods=len(c),freq='1h',tz='UTC'));z=structure(b);assert np.isnan(z.trend.iloc[9]) and z.trend.iloc[10]==1 and z.last_high.iloc[10]==15.5
assert np.allclose(structure(b.iloc[:11]),z.iloc[:11],equal_nan=True)
# At non-boundary closedM5 points, higher TF state must remain unchanged.
for tf,(freq,_) in TFS.items():
 if tf=='M5':continue
 changes=cx[tf+'_trend'].ne(cx[tf+'_trend'].shift())&cx[tf+'_trend'].notna()&cx[tf+'_trend'].shift().notna();t=cx.index[changes];assert (t==t.floor(freq)).all()
e=pd.read_csv(O/'LAB163_encounters.csv',parse_dates=['time']);old=pd.read_csv(R/'results/LAB162_20261010/LAB162_encounters.csv');assert len(e)==len(old) and np.array_equal(e.outcome,old.outcome)
s=pd.read_csv(O/'LAB163_scenarios.csv',parse_dates=['time','snapshot_time','break_time','reentry_time']);assert (s.snapshot_time<s.break_time).all() and (s.break_time<s.reentry_time).all() and (s.reentry_time<s.time).all();assert (s.route_atr>=.5).all() and (s.risk_atr>.1).all()
for mode,q in s.groupby('mode'):assert (q.sort_values('time').time.diff().dropna()>=pd.Timedelta(hours=6)).all()
for r in s.iloc[::7].itertuples():
 i=d.index.get_loc(r.time);j=d.index.get_loc(r.snapshot_time);assert np.isclose(r.poc,d.POC_HVN.iloc[j]);assert np.isclose(r.boundary,d.VAH.iloc[j] if r.side==-1 else d.VAL.iloc[j]);v=d.close.iloc[i+1:i+289].to_numpy();a=np.flatnonzero(r.side*(v-r.poc)>=0);b=np.flatnonzero(r.side*(v-r.stop)<=0);aa=a[0] if len(a) else 999;bb=b[0] if len(b) else 999;assert r.outcome==('TARGET' if aa<bb else ('STOP' if bb<aa else 'TIMEOUT'))
for bound in ['2024-01-01','2025-01-01']:
 t=pd.Timestamp(bound,tz='UTC');assert (s.loc[(s.time>=t-pd.Timedelta(hours=24))&(s.time<t),'split']=='PURGED').all()
val=dict(swing_confirmation_two_right_bars=True,prefix_invariance=True,higher_timeframe_update_boundaries=True,lab162_event_outcome_parity=True,frozen_profile_before_break=True,scenario_chronology=True,scenario_cooldown=True,route_and_risk_constraints=True,sampled_future_outcome_recalculation=True,purge=True);(O/'LAB163_validation.json').write_text(json.dumps(val,indent=2));print(json.dumps(val))
