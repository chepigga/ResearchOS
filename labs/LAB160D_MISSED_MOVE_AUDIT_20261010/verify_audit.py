from pathlib import Path
import ast,types,json
import pandas as pd,numpy as np
P=Path(__file__).with_name('run_audit.py');O=P.parents[2]/'results/LAB160D_20261010'
tree=ast.parse(P.read_text());nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ['legs','value']];ns=dict(pd=pd,np=np);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(P),'exec'),ns)
idx=pd.date_range('2021-01-01',periods=8,freq='5min',tz='UTC');c=np.array([100,102,105,103,100,97,99,101.]);f=pd.DataFrame(dict(close=c,atr=1),index=idx)
l=ns['legs'](f,1.);assert len(l)==2 and l[0]['amplitude_atr']==5 and l[1]['amplitude_atr']==8 and l[0]['peak']==l[1]['start']
f.close=200-c;mirror=ns['legs'](f,1.);assert [x['amplitude_atr'] for x in l]==[x['amplitude_atr'] for x in mirror] and [x['side'] for x in l]==[-x['side'] for x in mirror]
r=types.SimpleNamespace(entry_time=idx[0],exit_observed_time=idx[-1],cost_r=.1,net_r=3.4,partial_time=idx[3],side=1,entry=100,atr=1)
v=ns['value'];assert abs(v(r,idx[2],102)-1.9)<1e-10;assert abs(v(r,idx[4],105)-3.9)<1e-10;assert abs(v(r,idx[4],105)-v(r,idx[2],102)-2)<1e-10;assert v(r,idx[-1],200)==3.4
r.partial_time=idx[1];assert abs(v(r,idx[4],105)-v(r,idx[2],102)-1.5)<1e-10
m=pd.read_csv(O/'LAB160D_move_audit.csv',parse_dates=['start','peak','cutoff','end']);links=pd.read_csv(O/'LAB160D_move_trade_links.csv');summ=pd.read_csv(O/'LAB160D_summary.csv');cats=pd.read_csv(O/'LAB160D_categories.csv')
assert m.move_id.is_unique and (m.start<=m.cutoff).all() and (m.cutoff<=m.peak).all() and (m.peak<=m.end).all()
for name,q in m.groupby('definition'):
 assert int(summ[summ.definition==name].n.iloc[0])==len(q);assert cats[cats.definition==name].n.sum()==len(q)
 if name.startswith('LEG'):
  q=q.sort_values('start');assert (q.start.iloc[1:].reset_index(drop=True)>=q.peak.iloc[:-1].reset_index(drop=True)).all()
net=links.groupby('move_id').net_r_during_move.sum().reindex(m.move_id,fill_value=0).to_numpy();assert np.allclose(net,m.net_r_during_move)
assert (m.loc[m.positions_overlap==0,'net_r_during_move']==0).all()
assert m.loc[m.category=='PORTFOLIO_BLOCKED','portfolio_block_reasons'].notna().all()
validation=json.loads((O/'LAB160D_validation.json').read_text());validation.update(synthetic_partial_and_carried_mtm=True,synthetic_pivot_symmetry=True,pivot_nonoverlap=True,category_totals=True,trade_links_reconcile=True)
(O/'LAB160D_validation.json').write_text(json.dumps(validation,indent=2));print(json.dumps(validation))
