from pathlib import Path
from collections import Counter
import pandas as pd,numpy as np,json
O=Path(__file__).resolve().parents[2]/'results/LAB160C_20261010'
s=pd.read_csv(O/'LAB160C_summary.csv');t=pd.read_csv(O/'LAB160C_trades.csv');a=pd.read_csv(O/'LAB160C_attribution.csv');d=pd.read_csv(O/'LAB160C_portfolio_delta_decomposition.csv')
assert len(s)==40 and not s.duplicated(['variant','cost_bps']).any()
old=pd.read_csv(O/'raw_OLD.csv');oldp=pd.read_csv(O/'raw_OLD_PROFILE.csv');assert len(old)==506 and len(oldp)==450
assert old.duplicated('key').sum()==40
for name in s.variant.unique():
 r=pd.read_csv(O/f'raw_{name}.csv');assert not r.event_id.duplicated().any()
 if name not in ['OLD','OLD_PROFILE'] and not name.endswith('_PROFILE'):
  base=oldp if name.endswith('_NEW_ALL') else old
  assert Counter(base.event_id)<=Counter(r.event_id)
 for cost in [7.5,2.81]:
  st=s[(s.variant==name)&(s.cost_bps==cost)].iloc[0];q=t[(t.variant==name)&(t.cost_bps==cost)]
  assert len(q)==st.n and abs(q.net_r.sum()-st.total_r)<1e-8 and abs(st.r_month*48-st.total_r)<1e-8
  assert not q.event_id.duplicated().any()
  for _,row in q.iterrows():assert row.entry_i<=row.exit_i and pd.Timestamp(row.entry_time)<=pd.Timestamp(row.exit_time)
for _,r in d.iterrows():assert abs(r.delta_r-(r.added_executed_r-r.removed_r+r.common_outcome_delta_r))<1e-8
assert ((s.mtm_dd_pct_with_initial_zero-s.mtm_dd_pct).abs()<1e-8).all()
# Every isolated new-event outcome retains the exact variant's ATR and set membership.
stand=pd.read_csv(O/'LAB160C_standalone_new.csv')
for v in s.variant.unique():
 raw=pd.read_csv(O/f'raw_{v}.csv');raw=raw[raw.is_new].set_index('key')
 for cost in [7.5,2.81]:
  q=stand[(stand.variant==v)&(stand.cost_bps==cost)].set_index('key')
  assert set(q.index)==set(raw.index)
  if len(q):assert np.allclose(q.atr,raw.loc[q.index,'atr'])
result={'all_40_arms_present':True,'baseline_reproduced':True,'old_raw_multiplicity_preserved':True,'all_no_new_profile_arms_nested':True,'standalone_atr_per_variant_verified':True,'trade_timing_and_identity':True,'portfolio_delta_reconciles':True,'monthly_denominator_48':True,'dd_initial_zero_parity':True}
(O/'LAB160C_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
