from pathlib import Path
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'labs/CROWDFADE_CF191G_MARKET_VS_CONFIRM_POSITIVE_SKEW_LAB_074/output/trades.csv'
OUT=Path(__file__).resolve().parent/'output'; OUT.mkdir(parents=True,exist_ok=True)

def metrics(x):
    r=x['R'].astype(float).to_numpy(); pos=r[r>0].sum(); neg=-r[r<0].sum(); eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0,eq]); dd=(peak[1:]-eq).max() if len(r) else np.nan
    return {'N':len(r),'WR':float((r>0).mean()) if len(r) else np.nan,'EV_R':float(r.mean()) if len(r) else np.nan,'PF':float(pos/neg) if neg>0 else np.inf,'SumR':float(r.sum()),'MaxDD_R':float(dd) if len(r) else np.nan,'InitialStopRate':float((x['reason']=='INITIAL_STOP').mean()) if len(r) else np.nan,'RightTail2R':float((r>=2).mean()) if len(r) else np.nan}

df=pd.read_csv(SRC)
df['delay_min']=(df.entry_ts-df.signal_ts)/60.0
df['year']=pd.to_datetime(df.signal_ts,unit='s',utc=True).dt.year
conf=df[df['mode']=='CONFIRM_CANONICAL'].copy()
raw=df[df['mode']=='MARKET_RAW'].copy()

# 1) descriptive delay buckets, frozen before looking at results
bins=[-1e-9,5,15,30,60,120,180,1e9]; labels=['0-5','5-15','15-30','30-60','60-120','120-180','>180']
conf['delay_bucket']=pd.cut(conf.delay_min,bins=bins,labels=labels,right=True)
rows=[]
for (period,cost,b),g in conf.groupby(['period','cost_model','delay_bucket'],observed=True,sort=False): rows.append({'period':period,'cost_model':cost,'delay_bucket':str(b),**metrics(g)})
pd.DataFrame(rows).to_csv(OUT/'delay_buckets.csv',index=False)

# 2) causal max-confirmation-age gates. Historical is selection surface; forward_2026 is validation only.
gates=[5,10,15,30,45,60,90,120,180]
rows=[]
for period in ['historical','forward_2026']:
  for cost in ['GROSS','IC','GETLEVERAGED']:
    base=conf[(conf.period==period)&(conf.cost_model==cost)].copy()
    for gate in gates:
      g=base[base.delay_min<=gate]
      m=metrics(g); m.update({'period':period,'cost_model':cost,'max_delay_min':gate,'retained':len(g)/len(base) if len(base) else np.nan}); rows.append(m)
gate_df=pd.DataFrame(rows); gate_df.to_csv(OUT/'max_delay_gate_sweep.csv',index=False)

# 3) side split and yearly stability
rows=[]
for (period,cost,side),g in conf.groupby(['period','cost_model','side']): rows.append({'period':period,'cost_model':cost,'side':int(side),**metrics(g)})
pd.DataFrame(rows).to_csv(OUT/'side_split.csv',index=False)
rows=[]
for (cost,year),g in conf[conf.period=='historical'].groupby(['cost_model','year']): rows.append({'cost_model':cost,'year':int(year),**metrics(g)})
pd.DataFrame(rows).to_csv(OUT/'year_stability.csv',index=False)

# 4) baseline raw vs confirm for traceability
rows=[]
for (period,cost,mode),g in df.groupby(['period','cost_model','mode']): rows.append({'period':period,'cost_model':cost,'mode':mode,**metrics(g)})
pd.DataFrame(rows).to_csv(OUT/'baseline.csv',index=False)

# Choose historical gate only if it improves EV and DD vs ungated confirmation and retains >=70% trades; tie-break larger retention.
sel=[]
for cost in ['IC','GETLEVERAGED']:
  base=metrics(conf[(conf.period=='historical')&(conf.cost_model==cost)])
  c=gate_df[(gate_df.period=='historical')&(gate_df.cost_model==cost)&(gate_df.retained>=.70)].copy()
  c['ev_gain']=c.EV_R-base['EV_R']; c['dd_gain']=base['MaxDD_R']-c.MaxDD_R
  eligible=c[(c.ev_gain>0)&(c.dd_gain>=0)].sort_values(['EV_R','retained'],ascending=[False,False])
  pick=eligible.iloc[0].to_dict() if len(eligible) else None
  sel.append((cost,base,pick))

lines=['# LAB076 — EXECUTION PROFITABILITY — RESULT','', 'Source: canonical LAB074 trade population. Signal and positive-skew management frozen.','', '## Historical gate selection']
for cost,base,pick in sel:
  lines += [f'### {cost}',f"Ungated CONFIRM: N={base['N']}, EV={base['EV_R']:+.6f}R, PF={base['PF']:.4f}, SumR={base['SumR']:+.2f}R, DD={base['MaxDD_R']:.2f}R."]
  if pick:
    lines += [f"Best preregistered max-confirm-age candidate: <= {int(pick['max_delay_min'])}m; retained={pick['retained']:.1%}; EV={pick['EV_R']:+.6f}R; PF={pick['PF']:.4f}; SumR={pick['SumR']:+.2f}R; DD={pick['MaxDD_R']:.2f}R."]
    f=gate_df[(gate_df.period=='forward_2026')&(gate_df.cost_model==cost)&(gate_df.max_delay_min==pick['max_delay_min'])].iloc[0]
    fb=metrics(conf[(conf.period=='forward_2026')&(conf.cost_model==cost)])
    lines += [f"Untouched forward-2026 at same gate: retained={f['retained']:.1%}; EV={f['EV_R']:+.6f}R vs ungated {fb['EV_R']:+.6f}R; PF={f['PF']:.4f}; SumR={f['SumR']:+.2f}R; DD={f['MaxDD_R']:.2f}R."]
  else: lines += ['No max-confirm-age gate passed the historical EV+DD+retention acceptance rule.']
  lines += ['']
lines += ['## Guardrail','A delay gate is promotable only if the historical-selected threshold also improves or preserves forward-2026 EV and does not materially worsen DD. No threshold is selected from forward data.','', 'See CSV outputs for delay buckets, gate sweep, side split, and yearly stability.']
(OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
