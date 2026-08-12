from pathlib import Path
import json
import numpy as np
import pandas as pd

OUT=Path('u07_out'); OUT.mkdir(exist_ok=True)
EV='lab020_events.csv'
EP='u05_out/u05_episode_market_clock_map.csv'
WINDOWS=[24,48,72]

def pf(x):
 s=pd.Series(x).dropna(); gp=s[s>0].sum(); gl=-s[s<0].sum(); return float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan)

def core_label(e):
 e=e.copy(); e['branch']=''
 e.loc[(e.side=='BUY')&(e.H4_ST_AGE_BARS>58)&(e.H4_ST_DIR==-1),'branch']='BUY_TIER_A'
 e.loc[(e.side=='BUY')&(e.H4_ST_AGE_BARS>58)&(e.H4_ST_DIR==1),'branch']='BUY_TIER_B'
 e.loc[(e.side=='SELL')&(e.H4_ST_AGE_BARS>26)&(e.H4_ST_AGE_BARS<=50),'branch']='SELL_B3_RECENT'
 return e[e.branch!=''].copy()

def era(y):
 if y<=2022:return 'OLD_2020_22'
 if y==2023:return 'Y2023'
 return 'RECENT_2024_26'

def attach_prev_conflict(c,hours):
 c=c.sort_values('entry_time').copy(); prev_branch=[]; prev_time=[]; delta=[]
 for i,r in c.iterrows():
  z=c[(c.entry_time<r.entry_time)&(c.side!=r.side)&(c.entry_time>=r.entry_time-pd.Timedelta(hours=hours))]
  if len(z):
   q=z.iloc[-1]; prev_branch.append(q.branch); prev_time.append(q.entry_time); delta.append((r.entry_time-q.entry_time).total_seconds()/3600)
  else:
   prev_branch.append('NONE'); prev_time.append(pd.NaT); delta.append(np.nan)
 c[f'prev_opp_branch_{hours}h']=prev_branch; c[f'prev_opp_time_{hours}h']=prev_time; c[f'prev_opp_delta_{hours}h']=delta
 return c

def group_stats(c,window):
 col=f'prev_opp_branch_{window}h'; rows=[]
 for (er,b,pb),g in c.groupby(['era','branch',col],dropna=False):
  rows.append(dict(window_h=window,era=er,new_branch=b,prev_opposite_branch=pb,N=len(g),EV48=float(g.NET48_SPREAD_PCT.mean()),PF48=pf(g.NET48_SPREAD_PCT),WR48=float((g.NET48_SPREAD_PCT>0).mean()),STRESS_EV48=float(g.NET48_STRESS_PCT.mean()),STRESS_PF48=pf(g.NET48_STRESS_PCT)))
 # broad recent and full too
 for scope,ss in [('FULL_2020_26',c),('RECENT_2024_26',c[c.year>=2024])]:
  for (b,pb),g in ss.groupby(['branch',col],dropna=False):
   rows.append(dict(window_h=window,era=scope,new_branch=b,prev_opposite_branch=pb,N=len(g),EV48=float(g.NET48_SPREAD_PCT.mean()),PF48=pf(g.NET48_SPREAD_PCT),WR48=float((g.NET48_SPREAD_PCT>0).mean()),STRESS_EV48=float(g.NET48_STRESS_PCT.mean()),STRESS_PF48=pf(g.NET48_STRESS_PCT)))
 return pd.DataFrame(rows)

def oracle_active_core(ep,c,window=48):
 ep=ep.copy(); ep['signal_time']=pd.to_datetime(ep.signal_time); ep['oracle_utc']=ep.signal_time-pd.Timedelta(hours=3)
 rows=[]
 for q in ep.itertuples(index=False):
  active=c[(c.entry_time<=q.oracle_utc)&(c.entry_time>q.oracle_utc-pd.Timedelta(hours=window))]
  same=active[active.side==q.side]; opp=active[active.side!=q.side]
  rows.append(dict(episode15=q.episode15,oracle_utc=q.oracle_utc,side=q.side,oracle_state=q.unified_state,active_same='|'.join(same.branch.tolist()) if len(same) else 'NONE',active_opposite='|'.join(opp.branch.tolist()) if len(opp) else 'NONE',n_same=len(same),n_opp=len(opp)))
 return pd.DataFrame(rows)

def main():
 e=pd.read_csv(EV); e['entry_time']=pd.to_datetime(e.entry_time); e['year']=e.entry_time.dt.year
 c=core_label(e); c=c[(c.year>=2020)&(c.year<=2026)].copy(); c['era']=c.year.map(era)
 allstats=[]
 for w in WINDOWS:
  c=attach_prev_conflict(c,w); allstats.append(group_stats(c,w))
 pd.concat(allstats,ignore_index=True).to_csv(OUT/'u07_conflict_conditional_metrics.csv',index=False)
 c.to_csv(OUT/'u07_core_event_conflicts.csv',index=False)
 ep=pd.read_csv(EP); oa=oracle_active_core(ep,c,48); oa.to_csv(OUT/'u07_exact_oracle_active_core_48h.csv',index=False)
 # Focused 48h recent rows
 col='prev_opp_branch_48h'; recent=c[c.year>=2024]
 focus=[]
 for b in ['BUY_TIER_A','BUY_TIER_B','SELL_B3_RECENT']:
  g=recent[recent.branch==b]
  for state,z in [('NO_OPP',g[g[col]=='NONE']),('HAS_OPP',g[g[col]!='NONE'])]:
   focus.append(dict(branch=b,state=state,N=len(z),EV48=float(z.NET48_SPREAD_PCT.mean()) if len(z) else np.nan,PF48=pf(z.NET48_SPREAD_PCT),WR48=float((z.NET48_SPREAD_PCT>0).mean()) if len(z) else np.nan,STRESS_EV48=float(z.NET48_STRESS_PCT.mean()) if len(z) else np.nan))
 focus=pd.DataFrame(focus); focus.to_csv(OUT/'u07_recent_48h_focus.csv',index=False)
 summary={
  'core_events_full':c.branch.value_counts().to_dict(),
  'core_events_recent':recent.branch.value_counts().to_dict(),
  'recent_48h_focus':focus.to_dict('records'),
  'exact_oracle_48h_active_core':oa.to_dict('records'),
  'method':'Conflict is a newer opposite-side core signal arriving within fixed 24/48/72h window. No P&L thresholds optimized; frozen NET48 used.'
 }
 (OUT/'u07_summary.json').write_text(json.dumps(summary,indent=2,default=str))
 print('RECENT 48H FOCUS'); print(focus.to_string(index=False))
 print('\nEXACT ORACLE ACTIVE CORE'); print(oa.to_string(index=False))
 print('\nPAIR DETAILS RECENT 48H')
 z=pd.concat(allstats); print(z[(z.window_h==48)&(z.era=='RECENT_2024_26')].to_string(index=False))
 print('\nSUMMARY'); print(json.dumps(summary,indent=2,default=str))
if __name__=='__main__':main()
