from pathlib import Path
import json
import numpy as np,pandas as pd
from numba import njit
R=Path(__file__).resolve().parents[2];O=R/'results/LAB162_20261010';LEVELS=['POC_HVN','VAL','VAH','HVN2','LVN']
@njit
def encounter_indices(c,h,l,a,levels,valid):
 rows=[];last=np.full((levels.shape[1],2),-99999)
 for i in range(13,len(c)-72):
  if not valid[i-1] or not np.isfinite(a[i]) or a[i]<=0:continue
  scale=a[i-1]
  for k in range(levels.shape[1]):
   level=levels[i-1,k]
   if not np.isfinite(level):continue
   side=1 if level>c[i-6] else -1;sidx=0 if side==1 else 1
   if side*(level-c[i-6])<.25*scale or side*(level-c[i-1])<=.1*scale:continue
   if l[i]>level+.1*scale or h[i]<level-.1*scale or i-last[k,sidx]<72:continue
   last[k,sidx]=i;outcome=0;mx=0.;ma=0.;hit=0
   for j in range(1,73):
    v=side*(c[i+j]-c[i])/a[i];mx=max(mx,v);ma=max(ma,-v)
    if outcome==0:
     if v>=1:outcome=1;hit=j
     elif v<=-1:outcome=-1;hit=j
   rows.append((i,k,side,level,outcome,mx,ma,side*(c[i+12]-c[i])/a[i],side*(c[i+72]-c[i])/a[i],hit*5))
 return rows

def main():
 d=pd.read_pickle(O/'LAB162_tape.pkl');a=encounter_indices(*[d[k].to_numpy(float) for k in ['close','high','low','atr']],d[LEVELS].to_numpy(float),(d.eligible_features&d.POC_HVN.notna()&d.oi_quantity.notna()).to_numpy());e=pd.DataFrame(a,columns=['i','level_code','side','level_price','outcome','mfe_6h','mae_6h','terminal_1h','terminal_6h','hit_minutes']);e['i']=e.i.astype(int);ix=e.i.to_numpy();pre=d.iloc[ix-1].reset_index(drop=True);now=d.iloc[ix].reset_index(drop=True);e['time']=d.index[ix];e['side']=e.side.astype(int);e['level']=e.level_code.map(dict(enumerate(LEVELS)));e['event_id']=['E%06d'%j for j in range(len(e))];e['shape']=pre['shape'];e['legacy_shape']=pre.legacy_shape;e['shape_transition']=d['shape'].iloc[ix-13].fillna('NA').to_numpy()+'>'+pre['shape'];e['oi4h']=pre.oi_change_48;e['oi1h']=pre.oi_change_12;e['z']=pre.crowd_z;e['dz1h']=pre.crowd_dz_1h;e['atr']=now.atr;e['close']=now.close;e['approach_atr']=e.side*(e.level_price-d.close.iloc[ix-6].to_numpy())/pre.atr;e['close_vs_level_atr']=e.side*(now.close-e.level_price)/pre.atr;e['contact']=np.select([e.close_vs_level_atr>.1,e.close_vs_level_atr<-.1],['BREAK_CLOSE','REJECT_CLOSE'],default='AT_LEVEL');e['trend_alignment']=np.select([pre.trend_side==e.side,pre.trend_side==-e.side],['CONT','REV'],default='FLAT');e['oi_state']=np.select([e.oi4h>.0035,e.oi4h<-.0035],['BUILD','UNWIND'],default='STABLE');e['crowd_state']=np.select([e.z*e.side>.6,e.z*e.side<-.6],['WITH','AGAINST'],default='NEUTRAL');e['split']=np.select([e.time<pd.Timestamp('2024-01-01',tz='UTC'),e.time<pd.Timestamp('2025-01-01',tz='UTC')],['DISCOVERY','VALIDATION'],default='CHECK')
 for b in ['2024-01-01','2025-01-01']:
  t=pd.Timestamp(b,tz='UTC');e.loc[(e.time>=t-pd.Timedelta(hours=6))&(e.time<t),'split']='PURGED'
 e['week']=e.time.dt.strftime('%G-%V');e['pass_hit']=e.outcome==1;e['reject_hit']=e.outcome==-1;e['unresolved']=e.outcome==0;e.to_csv(O/'LAB162_encounters.csv',index=False)
 rows=[]
 for keys in [['level'],['level','contact'],['level','shape'],['level','contact','shape'],['level','oi_state'],['level','crowd_state'],['shape_transition']]:
  t=e[e.split!='PURGED'].groupby(['split']+keys).agg(n=('event_id','size'),weeks=('week','nunique'),pass_rate=('pass_hit','mean'),reject_rate=('reject_hit','mean'),unresolved=('unresolved','mean'),mfe_median=('mfe_6h','median'),mae_median=('mae_6h','median'),terminal6h_median=('terminal_6h','median')).reset_index();t['grouping']='+'.join(keys);rows.append(t)
 pd.concat(rows).to_csv(O/'LAB162_encounter_summaries.csv',index=False);print('ENCOUNTERS',len(e),'UNIQUE_TIMES',e.time.nunique(),e.groupby('split').size().to_dict(),flush=True)
if __name__=='__main__':main()
