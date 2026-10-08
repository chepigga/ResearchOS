from pathlib import Path
import json,sys
import pandas as pd
sys.path.append(str(Path(__file__).resolve().parent))
from common import *
OUT=Path('lab141_out');OUT.mkdir(exist_ok=True)
V={
'TP3_H48':dict(tp=3,max_h=48),
'TP4_H48':dict(tp=4,max_h=48),
'TP5_H48':dict(tp=5,max_h=48),
'TP6_H48':dict(tp=6,max_h=48),
'NO_TP_H48':dict(tp=None,max_h=48),
'NO_TP_H72':dict(tp=None,max_h=72),
'RUN2_L05_CH15_H72':dict(tp=None,max_h=72,runner=True,act=2,lock=.5,ch=1.5),
'RUN2_L10_CH20_H72':dict(tp=None,max_h=72,runner=True,act=2,lock=1.0,ch=2.0)}
rows=[];alltr=[]
for cost in COSTS:
 for name,kw in V.items():
  tr=[]
  for _,r in ENTRIES.iterrows():
   z=sim(int(r.entry_i),int(r.side),float(r.atr),cost,**kw)
   q=r.to_dict();q.update(z);tr.append(q)
  t=pd.DataFrame(tr);s=stats(t);s.update(cost_bps=cost,variant=name);rows.append(s)
  t['cost_bps']=cost;t['variant']=name;alltr.append(t)
S=pd.DataFrame(rows);S.to_csv(OUT/'LAB141_exit_surface.csv',index=False)
pd.concat(alltr).to_csv(OUT/'LAB141_trades.csv',index=False)
e=S[(S.cost_bps==7.5)&(S.pf>=1.50)&(S.dd_pct<=5)].sort_values(['r_month','pf'],ascending=False)
best=e.iloc[0].variant if len(e) else 'TP3_H48'
(OUT/'LAB141_selection.json').write_text(json.dumps({'best':best,'rule':'max stress R/month with PF>=1.50 DD<=5%'},indent=2))
L=['# LAB141 EXIT SURFACE','',f'Fixed cohort: {len(ENTRIES)} canonical LAB138 trades. No new signals.']
for cost in COSTS:
 L+=['',f'## {cost:.2f}bps']
 for _,r in S[S.cost_bps==cost].sort_values('r_month',ascending=False).iterrows():
  L.append(f"- {r.variant}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, DD={r.dd_pct:.2f}%")
L+=['',f'Exploratory winner: **{best}**.','TRAIN discovery only.']
(OUT/'LAB141_REPORT.md').write_text('\n'.join(L)+'\n')
print('\n'.join(L))
