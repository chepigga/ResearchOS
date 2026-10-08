from pathlib import Path
import json,sys
import pandas as pd
sys.path.append(str(Path(__file__).resolve().parent))
from common import *
OUT=Path('lab142_out');OUT.mkdir(exist_ok=True)
best=json.loads(Path('lab141_out/LAB141_selection.json').read_text())['best']
cfg={
'TP3_H48':dict(tp=3,max_h=48),'TP4_H48':dict(tp=4,max_h=48),'TP5_H48':dict(tp=5,max_h=48),'TP6_H48':dict(tp=6,max_h=48),
'NO_TP_H48':dict(tp=None,max_h=48),'NO_TP_H72':dict(tp=None,max_h=72),
'RUN2_L05_CH15_H72':dict(tp=None,max_h=72,runner=True,act=2,lock=.5,ch=1.5),
'RUN2_L10_CH20_H72':dict(tp=None,max_h=72,runner=True,act=2,lock=1.0,ch=2.0)}[best]
V={'NO_REENTRY':(0,24),'RE1_12H':(1,12),'RE1_24H':(1,24),'RE2_24H':(2,24)}
def next_re(after_i,side,root,window):
 end=min(after_i+window*12,N-2)
 for j in range(after_i+1,end+1):
  if (BC[j]>root if side>0 else BC[j]<root):return j+1
 return None
rows=[];alltr=[]
for cost in COSTS:
 for name,(mx,window) in V.items():
  tr=[]
  for _,r in ENTRIES.iterrows():
   ei=int(r.entry_i);side=int(r.side);atr=float(r.atr);root=float(BO[ei]);attempt=0
   while True:
    z=sim(ei,side,atr,cost,**cfg);q=r.to_dict();q.update(z);q['attempt']=attempt;q['entry_time']=BT.iloc[ei];tr.append(q)
    if attempt>=mx or z['net_r']>=0 or z['reason'] not in ('SL','TRAIL'):break
    ni=next_re(int(z['exit_i']),side,root,window)
    if ni is None:break
    ei=ni;attempt+=1
  t=pd.DataFrame(tr);s=stats(t);s.update(cost_bps=cost,variant=name,reentries=int((t.attempt>0).sum()));rows.append(s)
  t['cost_bps']=cost;t['variant']=name;alltr.append(t)
S=pd.DataFrame(rows);S.to_csv(OUT/'LAB142_reentry_surface.csv',index=False);pd.concat(alltr).to_csv(OUT/'LAB142_trades.csv',index=False)
e=S[(S.cost_bps==7.5)&(S.pf>=1.45)&(S.dd_pct<=5)].sort_values(['r_month','pf'],ascending=False)
sel=e.iloc[0].variant if len(e) else 'NO_REENTRY'
L=['# LAB142 REENTRY','',f'Exit rule from LAB141: **{best}**. Reentry after stopped trade only; first M5 close back through original entry, then next M5 open.']
for cost in COSTS:
 L+=['',f'## {cost:.2f}bps']
 for _,r in S[S.cost_bps==cost].sort_values('r_month',ascending=False).iterrows():
  L.append(f"- {r.variant}: N={int(r.n)}, reentries={int(r.reentries)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, DD={r.dd_pct:.2f}%")
L+=['',f'Exploratory winner: **{sel}**.']
(OUT/'LAB142_REPORT.md').write_text('\n'.join(L)+'\n');(OUT/'LAB142_selection.json').write_text(json.dumps({'best':sel,'lab141_exit':best},indent=2));print('\n'.join(L))
