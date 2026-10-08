from pathlib import Path
import json,sys,pandas as pd
sys.path.append(str(Path(__file__).resolve().parent))
from common import *
O=Path('lab143_out');O.mkdir(exist_ok=True)
V=['BASE','D1','D2','L10','L20','L30']
def f(r,n):
 i=int(r.entry_i);s=int(r.side);a=float(r.atr);p=float(BO[i])
 if n=='BASE':return i,p
 if n[0]=='D':
  j=i+int(n[1]);return (j,float(BO[j])) if j<N else None
 q=int(n[1:])/100;p=p-s*q*a
 for j in range(i,min(i+72,N-1)+1):
  if (BL[j]<=p if s>0 else BH[j]>=p):return j,p
 return None
rows=[]
for cost in COSTS:
 for name in V:
  z=[]
  for _,r in ENTRIES.iterrows():
   x=f(r,name)
   if x is None:continue
   i,p=x;u=sim(i,int(r.side),float(r.atr),cost,tp=3,max_h=48,entry_price=p)
   d=r.to_dict();d.update(u);d['entry_time']=BT.iloc[i];z.append(d)
  t=pd.DataFrame(z);s=stats(t);s.update(cost_bps=cost,variant=name,fill_rate=len(t)/len(ENTRIES));rows.append(s)
S=pd.DataFrame(rows);S.to_csv(O/'LAB143_entry_surface.csv',index=False)
e=S[(S.cost_bps==7.5)&(S.pf>=1.5)&(S.dd_pct<=5)&(S.trades_month>=4)].sort_values('r_month',ascending=False)
best=e.iloc[0].variant if len(e) else 'BASE'
json.dump({'best':best},open(O/'LAB143_selection.json','w'),indent=2)
L=['# LAB143 ENTRY DISPLACEMENT','']
for cost in COSTS:
 L.append(f'## {cost:.2f}bps')
 for _,r in S[S.cost_bps==cost].sort_values('r_month',ascending=False).iterrows():
  L.append(f"- {r.variant}: N={int(r.n)}, fill={r.fill_rate:.1%}, PF={r.pf:.2f}, EV={r.ev:+.3f}R, R/mo={r.r_month:+.2f}, DD={r.dd_pct:.2f}%")
L+=['',f'Exploratory winner: **{best}**.']
(O/'LAB143_REPORT.md').write_text('\n'.join(L)+'\n');print('\n'.join(L))
