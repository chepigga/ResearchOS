from pathlib import Path
import ast
import pandas as pd,numpy as np
P=Path(__file__).with_name('run_audit.py');O=P.parents[2]/'results/LAB160D_20261010'
ns=dict(pd=pd,np=np);tree=ast.parse(P.read_text());exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='value'],type_ignores=[]),str(P),'exec'),ns);value=ns['value']
a=pd.read_csv(O/'LAB160D_move_audit.csv',parse_dates=['start','peak','cutoff','end']);p=pd.read_pickle(O/'LAB160D_price_tape.pkl');t=pd.read_csv(O/'LAB160D_execution_trades.csv',parse_dates=['entry_time','exit_observed_time','partial_time']);f=pd.Timedelta(minutes=5)
oppn=[];oppR=[]
for m in a.itertuples():
 q=t[(t.side!=m.side)&((t.entry_time<=m.cutoff) if m.definition.startswith('CLOCK') else (t.entry_time<m.cutoff))&(t.exit_observed_time>m.start)];price=float(p.loc[m.cutoff+f,'open']) if m.definition.startswith('CLOCK') else float(p.loc[m.cutoff,'close']);nr=0.
 for r in q.itertuples():nr+=value(r,m.cutoff,price)-(value(r,m.start,m.start_price) if r.entry_time<m.start else 0)
 oppn.append(len(q));oppR.append(nr)
a['opposite_positions_overlap']=oppn;a['opposite_net_r_during_move']=oppR;a['all_sides_net_r_during_move']=a.net_r_during_move+a.opposite_net_r_during_move
a.to_csv(O/'LAB160D_move_audit.csv',index=False)
s=pd.read_csv(O/'LAB160D_summary.csv').set_index('definition')
for name,q in a.groupby('definition'):
 s.loc[name,'opposite_position_pct']=(q.opposite_positions_overlap>0).mean()*100;s.loc[name,'any_direction_position_pct']=((q.positions_overlap+q.opposite_positions_overlap)>0).mean()*100;s.loc[name,'no_same_side_amplitude_share_pct']=q.loc[q.positions_overlap==0,'amplitude_atr'].sum()/q.amplitude_atr.sum()*100
s.reset_index().to_csv(O/'LAB160D_summary.csv',index=False)
# Single contemporaneous failed gate; later confirmation is NOT assumed to pass.
j=pd.read_csv(O/'LAB160D_gate_journal.csv',parse_dates=['signal_time','assessment_time','entry_time']);j=j[(j.stage=='GATED')&~j.failed_gates.fillna('').str.contains('|',regex=False)].copy()
rows=[]
for m in a[(a.definition=='LEG_REV1ATR')&(a.positions_overlap==0)].itertuples():
 q=j[(j.side==m.side)&(j.signal_time>=m.start-pd.Timedelta(hours=12))&(j.signal_time<=m.cutoff)&(j.assessment_time<=m.cutoff)]
 for (engine,gate),v in q.groupby(['engine','failed_gates']):rows.append(dict(move_id=m.move_id,engine=engine,single_failed_gate=gate,candidate_assessments=len(v)))
r=pd.DataFrame(rows);r.to_csv(O/'LAB160D_single_gate_near_misses.csv',index=False);r.groupby(['engine','single_failed_gate']).move_id.nunique().rename('moves').reset_index().to_csv(O/'LAB160D_single_gate_summary.csv',index=False)
print('ENRICHMENT COMPLETE')
