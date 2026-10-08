from pathlib import Path
import sys,pandas as pd
sys.path.append(str(Path(__file__).resolve().parent))
from common import *
O=Path('lab144_out');O.mkdir(exist_ok=True)
def raw():
 z=[]
 for _,r in A.a_ev.iterrows():z.append(dict(source='A',entry_i=ix(r.entry_time),entry_time=pd.Timestamp(r.entry_time),side=int(r.side),atr=float(r.atr)))
 for _,r in A.b_high.iterrows():z.append(dict(source='B3_HIGH',entry_i=ix(r.entry_time),entry_time=pd.Timestamp(r.entry_time),side=int(r.side),atr=float(r.atr)))
 h=R.df[(~R.df.retest)&(R.df.mean_margin>=R.thr['mean_margin_q60'])&(R.df.oi_change>=R.thr['oi_q60'])]
 for _,r in h.iterrows():z.append(dict(source='R48_HIGH',entry_i=ix(r.entry_time),entry_time=pd.Timestamp(r.entry_time),side=int(r.side),atr=float(r.atr)))
 return pd.DataFrame(z).sort_values(['entry_time','source'])
D=raw()
def run(cost,mode):
 z=[]
 for _,r in D.iterrows():
  q=r.to_dict();q.update(sim(int(r.entry_i),int(r.side),float(r.atr),cost,tp=3,max_h=48));z.append(q)
 t=pd.DataFrame(z).sort_values(['entry_time','source']);a=[];active=[]
 for _,r in t.iterrows():
  now=r.entry_time;active=[x for x in active if x[0]>now]
  if mode=='ONE':
   if active:continue
   cap=1
  else:
   cap=int(mode[-1])
   if any(x[1]==r.source for x in active):continue
   if len(active)>=cap:continue
  a.append(r);active.append((r.exit_time,r.source))
 return pd.DataFrame(a)
rows=[]
for cost in COSTS:
 for name in ['ONE','PER_ENGINE_CAP2','PER_ENGINE_CAP3']:
  t=run(cost,name);s=stats(t);cap=1 if name=='ONE' else int(name[-1]);s.update(cost_bps=cost,variant=name,max_open_risk_pct=cap*RISK);rows.append(s)
S=pd.DataFrame(rows);S.to_csv(O/'LAB144_capacity_surface.csv',index=False)
L=['# LAB144 PORTFOLIO CAPACITY','','Canonical entries + TP3/H48. One-position vs one-position-per-engine. DD is booked-trade DD, not full concurrent MTM DD.']
for cost in COSTS:
 L+=['',f'## {cost:.2f}bps']
 for _,r in S[S.cost_bps==cost].sort_values('r_month',ascending=False).iterrows():
  L.append(f"- {r.variant}: N={int(r.n)} ({r.trades_month:.2f}/mo), PF={r.pf:.2f}, EV={r.ev:+.3f}R, R/mo={r.r_month:+.2f}, booked DD={r.dd_pct:.2f}%, max open risk={r.max_open_risk_pct:.2f}%")
(O/'LAB144_REPORT.md').write_text('\n'.join(L)+'\n');print('\n'.join(L))
